from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from .transport_schema import build_transport_schema
from .validation import ValidationIssue, validate_schema


POLICY_APPROVAL_REQUIRED_MESSAGE = (
    "Benchmark recommendation and verification comparison is blocked until "
    "phase1-benchmark-policy.json has been reviewed and approved by a human."
)

STRUCTURAL_FIELDS = [
    "requirementId",
    "claimIds",
    "status",
    "evidenceIds",
    "contradictoryEvidenceIds",
    "severity",
    "requiresHumanDecision",
    "blockingReasons",
    "policyGap",
]

SUB_ASSESSMENT_FIELDS = {
    "definitionQuality": ["verdict", "missingDefinitionElements"],
    "evidenceAssessment": [
        "verdict",
        "independentDirectlyRelevantSources",
        "sourceIds",
        "gatedByDefinitionFailure",
    ],
    "contradictionAssessment": ["verdict", "conflictType"],
}

EVIDENCE_ID_PATTERN = re.compile(r"EV-\d{3}")
IssueCategory = Literal["structural", "policy"]


class EvaluationPolicyNotApproved(Exception):
    pass


@dataclass(frozen=True)
class ComparisonIssue:
    category: IssueCategory
    path: str
    message: str


@dataclass(frozen=True)
class BenchmarkComparisonReport:
    fixture: str
    transport_schema_hash: str
    evaluation_policy_hash: str
    issues: list[ComparisonIssue]

    @property
    def passed(self) -> bool:
        return not self.issues


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_pointer(*parts: str | int) -> str:
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def _policy_approval_issues(policy: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if policy.get("reviewStatus") != "approved":
        issues.append(ValidationIssue("evaluation policy must be approved", "/reviewStatus"))
    if policy.get("humanReviewed") is not True:
        issues.append(ValidationIssue("evaluation policy must be human reviewed", "/humanReviewed"))
    if not isinstance(policy.get("reviewedBy"), str) or not policy.get("reviewedBy"):
        issues.append(ValidationIssue("approved policy must name a reviewer", "/reviewedBy"))
    if not isinstance(policy.get("reviewedDate"), str) or not policy.get("reviewedDate"):
        issues.append(ValidationIssue("approved policy must have a review date", "/reviewedDate"))
    return issues


def require_reviewed_evaluation_policy(policy: dict[str, Any]) -> None:
    issues = _policy_approval_issues(policy)
    if issues:
        raise EvaluationPolicyNotApproved(POLICY_APPROVAL_REQUIRED_MESSAGE)


def validate_approved_evaluation_policy(
    policy: dict[str, Any],
    policy_schema: dict[str, Any],
) -> list[ValidationIssue]:
    issues = validate_schema(policy, policy_schema)
    issues.extend(_policy_approval_issues(policy))
    return issues


def _policy_by_fixture_and_requirement(policy: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    mapping = {}
    for fixture in policy.get("fixtures", []):
        fixture_name = fixture.get("fixture")
        for requirement in fixture.get("requirements", []):
            mapping[(fixture_name, requirement.get("requirementId"))] = requirement
    return mapping


def _finding_by_requirement(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {finding["requirementId"]: finding for finding in document.get("findings", [])}


def _compare_value(
    *,
    issues: list[ComparisonIssue],
    expected: Any,
    actual: Any,
    path: str,
    category: IssueCategory = "structural",
) -> None:
    if actual != expected:
        issues.append(
            ComparisonIssue(
                category=category,
                path=path,
                message=f"expected {expected!r}, got {actual!r}",
            )
        )


def _compare_off_segment_signal(
    *,
    issues: list[ComparisonIssue],
    expected: str | None,
    actual: str | None,
    path: str,
) -> None:
    if expected is None or actual is None:
        _compare_value(issues=issues, expected=expected, actual=actual, path=path)
        return

    expected_ids = sorted(set(EVIDENCE_ID_PATTERN.findall(expected)))
    actual_ids = sorted(set(EVIDENCE_ID_PATTERN.findall(actual)))
    if expected_ids or actual_ids:
        _compare_value(issues=issues, expected=expected_ids, actual=actual_ids, path=path)
        return

    _compare_value(issues=issues, expected=expected, actual=actual, path=path)


def _compare_sub_assessments(
    *,
    issues: list[ComparisonIssue],
    expected: dict[str, Any],
    actual: dict[str, Any],
    finding_index: int,
) -> None:
    for assessment_name, fields in SUB_ASSESSMENT_FIELDS.items():
        expected_assessment = expected.get("subAssessments", {}).get(assessment_name, {})
        actual_assessment = actual.get("subAssessments", {}).get(assessment_name, {})
        for field in fields:
            _compare_value(
                issues=issues,
                expected=expected_assessment.get(field),
                actual=actual_assessment.get(field),
                path=_json_pointer(
                    "findings", finding_index, "subAssessments", assessment_name, field
                ),
            )


def _compare_policy_owned_text(
    *,
    issues: list[ComparisonIssue],
    expected_finding: dict[str, Any],
    actual_finding: dict[str, Any],
    policy_requirement: dict[str, Any],
    finding_index: int,
) -> None:
    if not policy_requirement.get("expectedRecommendationActionType"):
        issues.append(
            ComparisonIssue(
                category="policy",
                path=_json_pointer("findings", finding_index),
                message="approved policy is missing expectedRecommendationActionType",
            )
        )
    if not policy_requirement.get("requiredVerificationBehavior"):
        issues.append(
            ComparisonIssue(
                category="policy",
                path=_json_pointer("findings", finding_index),
                message="approved policy is missing requiredVerificationBehavior",
            )
        )

    _compare_value(
        issues=issues,
        expected=expected_finding.get("recommendation"),
        actual=actual_finding.get("recommendation"),
        path=_json_pointer("findings", finding_index, "recommendation"),
        category="policy",
    )
    _compare_value(
        issues=issues,
        expected=expected_finding.get("verificationTest"),
        actual=actual_finding.get("verificationTest"),
        path=_json_pointer("findings", finding_index, "verificationTest"),
        category="policy",
    )

    prohibited = policy_requirement.get("prohibitedSubstitutions", [])
    combined_text = " ".join(
        [
            str(actual_finding.get("recommendation", "")),
            str(actual_finding.get("verificationTest", "")),
        ]
    ).lower()
    for prohibited_item in prohibited:
        if prohibited_item.lower() in combined_text:
            issues.append(
                ComparisonIssue(
                    category="policy",
                    path=_json_pointer("findings", finding_index),
                    message=f"contains prohibited substitution: {prohibited_item}",
                )
            )


def compare_benchmark_document(
    *,
    actual_document: dict[str, Any],
    expected_document: dict[str, Any],
    evaluation_policy: dict[str, Any],
    evaluation_policy_schema: dict[str, Any],
    audit_finding_schema: dict[str, Any],
) -> BenchmarkComparisonReport:
    policy_issues = validate_approved_evaluation_policy(
        evaluation_policy,
        evaluation_policy_schema,
    )
    if policy_issues:
        raise EvaluationPolicyNotApproved(POLICY_APPROVAL_REQUIRED_MESSAGE)

    fixture = expected_document["fixture"]
    transport_schema = build_transport_schema(audit_finding_schema)
    report = BenchmarkComparisonReport(
        fixture=fixture,
        transport_schema_hash=_canonical_hash(transport_schema),
        evaluation_policy_hash=_canonical_hash(evaluation_policy),
        issues=[],
    )

    issues = report.issues
    _compare_value(
        issues=issues,
        expected=fixture,
        actual=actual_document.get("fixture"),
        path="/fixture",
    )
    _compare_value(
        issues=issues,
        expected=expected_document.get("packetId"),
        actual=actual_document.get("packetId"),
        path="/packetId",
    )
    if "synthetic" not in str(actual_document.get("syntheticEvidenceNotice", "")).lower():
        issues.append(
            ComparisonIssue(
                category="structural",
                path="/syntheticEvidenceNotice",
                message="synthetic evidence notice must mention synthetic evidence",
            )
        )

    policy_mapping = _policy_by_fixture_and_requirement(evaluation_policy)
    actual_by_requirement = _finding_by_requirement(actual_document)

    for finding_index, expected_finding in enumerate(expected_document.get("findings", [])):
        requirement_id = expected_finding["requirementId"]
        actual_finding = actual_by_requirement.get(requirement_id)
        if actual_finding is None:
            issues.append(
                ComparisonIssue(
                    category="structural",
                    path=_json_pointer("findings", finding_index),
                    message=f"missing finding for {requirement_id}",
                )
            )
            continue

        for field in STRUCTURAL_FIELDS:
            _compare_value(
                issues=issues,
                expected=expected_finding.get(field),
                actual=actual_finding.get(field),
                path=_json_pointer("findings", finding_index, field),
            )

        _compare_off_segment_signal(
            issues=issues,
            expected=expected_finding.get("offSegmentSignal"),
            actual=actual_finding.get("offSegmentSignal"),
            path=_json_pointer("findings", finding_index, "offSegmentSignal"),
        )
        _compare_sub_assessments(
            issues=issues,
            expected=expected_finding,
            actual=actual_finding,
            finding_index=finding_index,
        )

        policy_requirement = policy_mapping.get((fixture, requirement_id))
        if policy_requirement is None:
            issues.append(
                ComparisonIssue(
                    category="policy",
                    path=_json_pointer("findings", finding_index),
                    message=f"approved policy has no mapping for {fixture} {requirement_id}",
                )
            )
            continue
        _compare_policy_owned_text(
            issues=issues,
            expected_finding=expected_finding,
            actual_finding=actual_finding,
            policy_requirement=policy_requirement,
            finding_index=finding_index,
        )

    return report
