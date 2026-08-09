from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from evidencegate.problem_evidence.compare import (
    EvaluationPolicyNotApproved,
    compare_benchmark_document,
    require_reviewed_evaluation_policy,
)
from evidencegate.problem_evidence.load_contract import load_json, load_problem_evidence_contract
from evidencegate.problem_evidence.paths import AUDITOR_ROOT, EVAL_POLICY_PATH, EVAL_POLICY_SCHEMA_PATH
from evidencegate.problem_evidence.validate_policy import validate_policy
from evidencegate.problem_evidence.validation import raise_for_issues, validate_schema


def _policy() -> dict:
    return load_json(EVAL_POLICY_PATH)


def _schema() -> dict:
    return load_json(EVAL_POLICY_SCHEMA_PATH)


def _expected(fixture: str) -> dict:
    expected_name = fixture.replace(".json", ".expected.json")
    return load_json(AUDITOR_ROOT / "expected" / expected_name)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _compare(actual: dict, expected: dict):
    contract = load_problem_evidence_contract()
    return compare_benchmark_document(
        actual_document=actual,
        expected_document=expected,
        evaluation_policy=_policy(),
        evaluation_policy_schema=_schema(),
        audit_finding_schema=contract.audit_finding_schema,
    )


def _finding(document: dict, requirement_id: str) -> dict:
    for finding in document["findings"]:
        if finding["requirementId"] == requirement_id:
            return finding
    raise AssertionError(f"missing finding {requirement_id}")


def _messages(report) -> list[str]:
    return [issue.message for issue in report.issues]


def test_unapproved_evaluation_policy_copy_validates_but_blocks_comparator_rules(tmp_path) -> None:
    policy = _policy()
    policy["reviewStatus"] = "human-review-required"
    policy["humanReviewed"] = False
    policy["reviewedBy"] = None
    policy["reviewedDate"] = None
    policy_path = tmp_path / "phase1-benchmark-policy.json"
    _write_json(policy_path, policy)

    validate_policy(policy_path)
    with pytest.raises(EvaluationPolicyNotApproved):
        require_reviewed_evaluation_policy(policy)


def test_approved_canonical_policy_enables_benchmark_comparison() -> None:
    validate_policy(EVAL_POLICY_PATH)
    policy = _policy()

    require_reviewed_evaluation_policy(policy)
    expected = _expected("strong-evidence.json")
    report = _compare(copy.deepcopy(expected), expected)

    assert report.passed
    assert report.fixture == "strong-evidence.json"
    assert len(report.transport_schema_hash) == 64
    assert len(report.evaluation_policy_hash) == 64


@pytest.mark.parametrize(
    ("metadata", "expected_error"),
    [
        (
            {
                "reviewStatus": "human-review-required",
                "humanReviewed": True,
                "reviewedBy": None,
                "reviewedDate": None,
            },
            True,
        ),
        (
            {
                "reviewStatus": "approved",
                "humanReviewed": False,
                "reviewedBy": "Amina Moufakkir",
                "reviewedDate": "2026-08-05",
            },
            True,
        ),
        (
            {
                "reviewStatus": "approved",
                "humanReviewed": True,
                "reviewedBy": None,
                "reviewedDate": "2026-08-05",
            },
            True,
        ),
        (
            {
                "reviewStatus": "human-review-required",
                "humanReviewed": False,
                "reviewedBy": "Amina Moufakkir",
                "reviewedDate": None,
            },
            True,
        ),
    ],
)
def test_policy_schema_rejects_inconsistent_review_metadata(metadata, expected_error) -> None:
    policy = _policy()
    policy.update(metadata)

    issues = validate_schema(policy, _schema())

    assert bool(issues) is expected_error


def test_structural_comparison_detects_policy_critical_field_mismatch() -> None:
    expected = _expected("strong-evidence.json")
    actual = copy.deepcopy(expected)
    _finding(actual, "REQ-5")["evidenceIds"] = ["EV-010"]

    report = _compare(actual, expected)

    assert not report.passed
    assert any("/findings/4/evidenceIds" == issue.path for issue in report.issues)


def test_non_contributing_evidence_mismatch_is_detected() -> None:
    expected = _expected("missing-evidence.json")
    actual = copy.deepcopy(expected)
    _finding(actual, "REQ-2")["nonContributingEvidence"] = []

    report = _compare(actual, expected)

    assert not report.passed
    assert any(
        issue.path == "/findings/1/nonContributingEvidence"
        for issue in report.issues
    )


def test_owner_approved_semantic_audit_corrections_are_canonical() -> None:
    contradictory = _expected("contradictory-evidence.json")
    missing = _expected("missing-evidence.json")
    strong = _expected("strong-evidence.json")

    contradictory_req2 = _finding(contradictory, "REQ-2")
    assert contradictory_req2["status"] == "pass"
    assert contradictory_req2["contradictoryEvidenceIds"] == []
    assert [
        item["evidenceId"] for item in contradictory_req2["nonContributingEvidence"]
    ] == ["EV-003"]

    contradictory_req3 = _finding(contradictory, "REQ-3")
    assert contradictory_req3["status"] == "fail"
    assert contradictory_req3["evidenceIds"] == []
    assert [
        item["evidenceId"] for item in contradictory_req3["nonContributingEvidence"]
    ] == ["EV-007"]

    contradictory_req5 = _finding(contradictory, "REQ-5")
    assert contradictory_req5["subAssessments"]["contradictionAssessment"][
        "conflictType"
    ] == "cross-source-disagreement"

    missing_req2 = _finding(missing, "REQ-2")
    assert {
        item["evidenceId"] for item in missing_req2["nonContributingEvidence"]
    } == {"EV-001", "EV-004", "EV-006"}

    strong_req3 = _finding(strong, "REQ-3")
    assert strong_req3["status"] == "partial"
    assert strong_req3["requiresHumanDecision"] is False


def test_structured_sub_assessment_mismatch_is_detected_without_rationale_matching() -> None:
    expected = _expected("strong-evidence.json")
    actual = copy.deepcopy(expected)
    _finding(actual, "REQ-3")["subAssessments"]["contradictionAssessment"][
        "conflictType"
    ] = None
    _finding(actual, "REQ-3")["rationale"] = "Different prose is allowed."

    report = _compare(actual, expected)

    assert not report.passed
    assert any("conflictType" in issue.path for issue in report.issues)
    assert not any(issue.path.endswith("/rationale") for issue in report.issues)


def test_req2_instance_scope_violation_is_detected() -> None:
    expected = _expected("strong-evidence.json")
    actual = copy.deepcopy(expected)
    _finding(actual, "REQ-2")[
        "verificationTest"
    ] = "Require recurrence across the segment before REQ-2 can pass."

    report = _compare(actual, expected)

    assert any(issue.category == "policy" for issue in report.issues)


def test_req3_predefined_calendar_week_bucket_violation_is_detected() -> None:
    expected = _expected("strong-evidence.json")
    actual = copy.deepcopy(expected)
    _finding(actual, "REQ-3")[
        "verificationTest"
    ] = "Use the period-wide mean proposals per week instead of fixed week buckets."

    report = _compare(actual, expected)

    assert any(issue.path.endswith("/verificationTest") for issue in report.issues)


def test_open04_supersession_violation_is_detected() -> None:
    expected = _expected("contradictory-evidence.json")
    actual = copy.deepcopy(expected)
    _finding(actual, "REQ-3")[
        "verificationTest"
    ] = "Treat newer instrumented records as automatically superseding older estimates."

    report = _compare(actual, expected)

    assert any(issue.category == "policy" for issue in report.issues)


def test_open06_partial_segment_fit_violation_is_detected() -> None:
    expected = _expected("strong-evidence.json")
    actual = copy.deepcopy(expected)
    _finding(actual, "REQ-4")["status"] = "pass"
    _finding(actual, "REQ-4")["requiresHumanDecision"] = False

    report = _compare(actual, expected)

    messages = _messages(report)
    assert any("expected 'partial'" in message for message in messages)
    assert any("expected True" in message for message in messages)


def test_open07_claim_mismatch_violation_is_detected() -> None:
    expected = _expected("missing-evidence.json")
    actual = copy.deepcopy(expected)
    _finding(actual, "REQ-5")["blockingReasons"] = []

    report = _compare(actual, expected)

    assert any(issue.path.endswith("/blockingReasons") for issue in report.issues)


def test_required_recommendation_behavior_violation_is_detected() -> None:
    expected = _expected("missing-evidence.json")
    actual = copy.deepcopy(expected)
    _finding(actual, "REQ-4")["recommendation"] = "Collect a generic owner survey."

    report = _compare(actual, expected)

    assert any(issue.path.endswith("/recommendation") for issue in report.issues)


def test_required_verification_threshold_violation_is_detected() -> None:
    expected = _expected("missing-evidence.json")
    actual = copy.deepcopy(expected)
    _finding(actual, "REQ-3")[
        "verificationTest"
    ] = "One proposal per month is enough to support the recurrence claim."

    report = _compare(actual, expected)

    assert any(issue.path.endswith("/verificationTest") for issue in report.issues)


def test_prohibited_substitution_violation_is_detected() -> None:
    expected = _expected("strong-evidence.json")
    actual = copy.deepcopy(expected)
    _finding(actual, "REQ-5")[
        "recommendation"
    ] = "Do not treat proposed-product demand as REQ-5 evidence."

    report = _compare(actual, expected)

    assert any("prohibited substitution" in issue.message for issue in report.issues)


def test_all_phase0_expected_files_pass_benchmark_comparison() -> None:
    for fixture in [
        "strong-evidence.json",
        "missing-evidence.json",
        "contradictory-evidence.json",
    ]:
        expected = _expected(fixture)
        report = _compare(copy.deepcopy(expected), expected)
        assert report.passed, report.issues


def test_policy_validator_keeps_requirement_order_check(tmp_path) -> None:
    policy = _policy()
    policy["fixtures"][0]["requirements"][0], policy["fixtures"][0]["requirements"][1] = (
        policy["fixtures"][0]["requirements"][1],
        policy["fixtures"][0]["requirements"][0],
    )
    path = tmp_path / "bad-order-policy.json"
    _write_json(path, policy)

    with pytest.raises(Exception) as exc:
        validate_policy(path)

    assert "requirements must be ordered" in str(exc.value)
