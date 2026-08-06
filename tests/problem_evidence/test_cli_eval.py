from __future__ import annotations

import copy
import json
from pathlib import Path

from evidencegate.problem_evidence.assembly import assemble_audit_document
from evidencegate.problem_evidence.cli import main
from evidencegate.problem_evidence.clock import FixedClock
from evidencegate.problem_evidence.load_contract import load_json, load_problem_evidence_contract, sha256_file
from evidencegate.problem_evidence.paths import AUDITOR_ROOT, EVAL_POLICY_PATH
from evidencegate.problem_evidence.transport_schema import MODEL_OWNED_FINDING_FIELDS


FIXED_RUN_ID = "eval-test-run"
FIXED_TIMESTAMP = "2026-08-05T12:00:00+00:00"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _transport_from_expected(expected: dict) -> dict:
    return {
        "findings": [
            {
                field: copy.deepcopy(finding[field])
                for field in MODEL_OWNED_FINDING_FIELDS
                if field in finding
            }
            for finding in expected["findings"]
        ]
    }


def _generated_document(fixture: str) -> dict:
    packet_path = AUDITOR_ROOT / "fixtures" / fixture
    expected = load_json(AUDITOR_ROOT / "expected" / fixture.replace(".json", ".expected.json"))
    return assemble_audit_document(
        packet=load_json(packet_path),
        transport_content=_transport_from_expected(expected),
        packet_path=packet_path,
        generated_by="test",
        clock=FixedClock("2026-08-05"),
    )


def _eval_args(
    *,
    fixture: str,
    finding_path: Path,
    output_path: Path,
    expected_path: Path | None = None,
    policy_path: Path | None = None,
) -> list[str]:
    expected_path = expected_path or AUDITOR_ROOT / "expected" / fixture.replace(".json", ".expected.json")
    args = [
        "eval",
        "--packet",
        str(AUDITOR_ROOT / "fixtures" / fixture),
        "--finding",
        str(finding_path),
        "--expected",
        str(expected_path),
        "--output",
        str(output_path),
        "--requested-model",
        "fake-requested",
        "--returned-model",
        "fake-returned",
        "--response-id",
        "fake-response",
        "--prompt-hash",
        "fake-prompt-hash",
        "--run-id",
        FIXED_RUN_ID,
        "--timestamp",
        FIXED_TIMESTAMP,
    ]
    if policy_path is not None:
        args.extend(["--policy", str(policy_path)])
    return args


def test_eval_cli_writes_complete_passing_report(tmp_path) -> None:
    finding_path = tmp_path / "generated.json"
    output_path = tmp_path / "report.json"
    _write_json(finding_path, _generated_document("strong-evidence.json"))

    exit_code = main(
        _eval_args(
            fixture="strong-evidence.json",
            finding_path=finding_path,
            output_path=output_path,
        )
    )

    report = load_json(output_path)
    assert exit_code == 0
    assert report["overallPassed"] is True
    assert report["requestedModel"] == "fake-requested"
    assert report["returnedModel"] == "fake-returned"
    assert report["responseId"] == "fake-response"
    assert report["promptVersion"] == "problem-evidence-phase1-v0"
    assert report["promptHash"] == "fake-prompt-hash"
    assert report["runId"] == FIXED_RUN_ID
    assert report["timestamp"] == FIXED_TIMESTAMP
    assert report["comparisonResults"]["passed"] is True
    assert all(block["passed"] for block in report["validationResults"])
    assert "Human semantic review remains required" in report["automatedEvaluationBoundary"]

    contract = load_problem_evidence_contract()
    assert report["hashes"]["SPEC.md"] == contract.hashes["SPEC.md"]
    assert report["hashes"]["checklist.json"] == contract.hashes["checklist.json"]
    assert report["hashes"]["evidence-packet.schema.json"] == contract.hashes[
        "evidence-packet.schema.json"
    ]
    assert report["hashes"]["audit-finding.schema.json"] == contract.hashes[
        "audit-finding.schema.json"
    ]
    assert len(report["hashes"]["transportSchema"]) == 64
    assert report["hashes"]["fixture"] == sha256_file(
        AUDITOR_ROOT / "fixtures" / "strong-evidence.json"
    )
    assert report["hashes"]["expectedResult"] == sha256_file(
        AUDITOR_ROOT / "expected" / "strong-evidence.expected.json"
    )
    assert len(report["hashes"]["evaluationPolicy"]) == 64


def test_eval_cli_policy_critical_mismatch_returns_nonzero(tmp_path) -> None:
    document = _generated_document("strong-evidence.json")
    document["findings"][1]["verificationTest"] = "Require recurrence before REQ-2 can pass."
    finding_path = tmp_path / "generated.json"
    output_path = tmp_path / "report.json"
    _write_json(finding_path, document)

    exit_code = main(
        _eval_args(
            fixture="strong-evidence.json",
            finding_path=finding_path,
            output_path=output_path,
        )
    )

    report = load_json(output_path)
    assert exit_code == 1
    assert report["overallPassed"] is False
    assert report["comparisonResults"]["passed"] is False
    assert any(
        issue["path"].endswith("/verificationTest")
        for issue in report["comparisonResults"]["issues"]
    )


def test_eval_cli_unapproved_policy_returns_nonzero(tmp_path) -> None:
    policy = load_json(EVAL_POLICY_PATH)
    policy["reviewStatus"] = "human-review-required"
    policy["humanReviewed"] = False
    policy["reviewedBy"] = None
    policy["reviewedDate"] = None
    policy_path = tmp_path / "policy.json"
    finding_path = tmp_path / "generated.json"
    output_path = tmp_path / "report.json"
    _write_json(policy_path, policy)
    _write_json(finding_path, _generated_document("missing-evidence.json"))

    exit_code = main(
        _eval_args(
            fixture="missing-evidence.json",
            finding_path=finding_path,
            output_path=output_path,
            policy_path=policy_path,
        )
    )

    report = load_json(output_path)
    assert exit_code == 1
    assert report["overallPassed"] is False
    assert any(block["name"] == "evaluationPolicy" and block["passed"] for block in report["validationResults"])
    assert any(
        issue["path"] == "/evaluationPolicy" for issue in report["comparisonResults"]["issues"]
    )


def test_eval_cli_invalid_generated_audit_returns_nonzero(tmp_path) -> None:
    document = _generated_document("missing-evidence.json")
    document["reviewStatus"] = "approved"
    document["humanReviewed"] = True
    finding_path = tmp_path / "generated.json"
    output_path = tmp_path / "report.json"
    _write_json(finding_path, document)

    exit_code = main(
        _eval_args(
            fixture="missing-evidence.json",
            finding_path=finding_path,
            output_path=output_path,
        )
    )

    report = load_json(output_path)
    assert exit_code == 1
    assert report["overallPassed"] is False
    generated_block = next(
        block for block in report["validationResults"] if block["name"] == "generatedAuditDocument"
    )
    assert generated_block["passed"] is False
    assert any("runtime reviewStatus" in issue["message"] for issue in generated_block["issues"])


def test_eval_cli_fixture_expected_mismatch_returns_nonzero(tmp_path) -> None:
    finding_path = tmp_path / "generated.json"
    output_path = tmp_path / "report.json"
    _write_json(finding_path, _generated_document("strong-evidence.json"))

    exit_code = main(
        _eval_args(
            fixture="strong-evidence.json",
            finding_path=finding_path,
            output_path=output_path,
            expected_path=AUDITOR_ROOT / "expected" / "missing-evidence.expected.json",
        )
    )

    report = load_json(output_path)
    assert exit_code == 1
    pairing_block = next(
        block for block in report["validationResults"] if block["name"] == "benchmarkPairing"
    )
    assert pairing_block["passed"] is False
    assert any("does not match" in issue["message"] for issue in pairing_block["issues"])


def test_eval_cli_missing_model_provenance_returns_nonzero(tmp_path) -> None:
    finding_path = tmp_path / "generated.json"
    output_path = tmp_path / "report.json"
    _write_json(finding_path, _generated_document("strong-evidence.json"))

    exit_code = main(
        [
            "eval",
            "--packet",
            str(AUDITOR_ROOT / "fixtures" / "strong-evidence.json"),
            "--finding",
            str(finding_path),
            "--expected",
            str(AUDITOR_ROOT / "expected" / "strong-evidence.expected.json"),
            "--output",
            str(output_path),
            "--requested-model",
            "fake-requested",
        ]
    )

    assert exit_code == 2
    assert not output_path.exists()
