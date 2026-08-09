from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import AuditGenerationFailure, run_audit
from .clock import Clock
from .compare import EvaluationPolicyNotApproved, compare_benchmark_document
from .load_contract import load_json, load_problem_evidence_contract, sha256_file
from .model_adapter import ModelAdapterError, OpenAIResponsesAdapter
from .paths import EVAL_POLICY_PATH, EVAL_POLICY_SCHEMA_PATH
from .prompt import PROMPT_VERSION
from .transport_schema import build_transport_schema
from .validate_policy import validate_policy
from .validation import (
    ValidationFailure,
    ValidationIssue,
    load_and_validate_packet,
    raise_for_issues,
    validate_audit_document,
    validate_schema,
)


def _resolve_model(args: argparse.Namespace) -> str:
    model = args.model or os.environ.get("EVIDENCEGATE_MODEL")
    if not model:
        raise SystemExit("--model or EVIDENCEGATE_MODEL is required")
    return model


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _issue_dict(issue: ValidationIssue) -> dict[str, str]:
    return {"path": issue.path, "message": issue.message}


def _comparison_issue_dict(issue: Any) -> dict[str, str]:
    return {"category": issue.category, "path": issue.path, "message": issue.message}


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    import hashlib

    return hashlib.sha256(encoded).hexdigest()


def _validation_block(name: str, issues: list[ValidationIssue]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": not issues,
        "issues": [_issue_dict(issue) for issue in issues],
    }


def _expected_path_matches_fixture(expected_path: Path, fixture_name: str) -> bool:
    return expected_path.name == fixture_name.replace(".json", ".expected.json")


def _build_eval_report_base(
    *,
    args: argparse.Namespace,
    contract_hashes: dict[str, str],
    transport_schema: dict[str, Any],
    evaluation_policy: dict[str, Any] | None,
    timestamp: str,
    fixture_path: Path,
    expected_path: Path,
) -> dict[str, Any]:
    return {
        "schemaVersion": "1.0.0",
        "reportType": "problem-evidence-phase1-benchmark-evaluation",
        "runId": args.run_id,
        "timestamp": timestamp,
        "requestedModel": args.requested_model,
        "returnedModel": args.returned_model,
        "responseId": args.response_id,
        "promptVersion": PROMPT_VERSION,
        "promptHash": args.prompt_hash,
        "fixture": fixture_path.name,
        "expectedResult": expected_path.name,
        "hashes": {
            "SPEC.md": contract_hashes["SPEC.md"],
            "checklist.json": contract_hashes["checklist.json"],
            "evidence-packet.schema.json": contract_hashes["evidence-packet.schema.json"],
            "audit-finding.schema.json": contract_hashes["audit-finding.schema.json"],
            "transportSchema": _canonical_hash(transport_schema),
            "fixture": sha256_file(fixture_path) if fixture_path.exists() else None,
            "expectedResult": sha256_file(expected_path) if expected_path.exists() else None,
            "evaluationPolicy": _canonical_hash(evaluation_policy) if evaluation_policy else None,
        },
        "validationResults": [],
        "comparisonResults": {
            "passed": False,
            "issues": [],
        },
        "overallPassed": False,
        "automatedEvaluationBoundary": (
            "Automated success means the structured result matches approved benchmark policy. "
            "It does not prove that free-form rationale or impact prose is semantically correct. "
            "Human semantic review remains required."
        ),
    }


def audit_command(args: argparse.Namespace) -> int:
    contract = load_problem_evidence_contract()
    result = run_audit(
        packet_path=Path(args.packet),
        model=_resolve_model(args),
        adapter=OpenAIResponsesAdapter(),
        contract=contract,
        clock=Clock(),
    )
    _write_json(Path(args.output), result.document)
    print(f"wrote {args.output}")
    return 0


def validate_command(args: argparse.Namespace) -> int:
    contract = load_problem_evidence_contract()
    packet = load_and_validate_packet(Path(args.packet), contract.evidence_packet_schema)
    document = load_json(Path(args.finding))
    raise_for_issues(
        validate_audit_document(
            document=document,
            packet=packet,
            audit_schema=contract.audit_finding_schema,
            requirement_ids=contract.requirement_ids,
        )
    )
    print("validation passed")
    return 0


def eval_command(args: argparse.Namespace) -> int:
    if not args.requested_model or not args.returned_model:
        print("--requested-model and --returned-model are required", file=sys.stderr)
        return 2

    args.run_id = args.run_id or str(uuid.uuid4())
    timestamp = args.timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    contract = load_problem_evidence_contract()
    transport_schema = build_transport_schema(contract.audit_finding_schema)
    packet_path = Path(args.packet)
    finding_path = Path(args.finding)
    expected_path = Path(args.expected)
    policy_path = Path(args.policy)
    policy_schema_path = Path(args.policy_schema)

    evaluation_policy = None
    try:
        evaluation_policy = load_json(policy_path)
    except Exception:
        pass
    report = _build_eval_report_base(
        args=args,
        contract_hashes=contract.hashes,
        transport_schema=transport_schema,
        evaluation_policy=evaluation_policy,
        timestamp=timestamp,
        fixture_path=packet_path,
        expected_path=expected_path,
    )

    exit_code = 0
    packet = None
    generated_document = None
    expected_document = None
    policy_schema = None

    try:
        packet = load_and_validate_packet(packet_path, contract.evidence_packet_schema)
        report["validationResults"].append(_validation_block("evidencePacket", []))
    except Exception as exc:
        exit_code = 1
        report["validationResults"].append(
            _validation_block("evidencePacket", [ValidationIssue(str(exc), str(packet_path))])
        )

    try:
        generated_document = load_json(finding_path)
        issues: list[ValidationIssue] = []
        if packet is not None:
            issues = validate_audit_document(
                document=generated_document,
                packet=packet,
                audit_schema=contract.audit_finding_schema,
                requirement_ids=contract.requirement_ids,
            )
        report["validationResults"].append(_validation_block("generatedAuditDocument", issues))
        if issues:
            exit_code = 1
    except Exception as exc:
        exit_code = 1
        report["validationResults"].append(
            _validation_block("generatedAuditDocument", [ValidationIssue(str(exc), str(finding_path))])
        )

    try:
        expected_document = load_json(expected_path)
        issues = validate_schema(expected_document, contract.audit_finding_schema)
        report["validationResults"].append(_validation_block("approvedExpectedResult", issues))
        if issues:
            exit_code = 1
    except Exception as exc:
        exit_code = 1
        report["validationResults"].append(
            _validation_block("approvedExpectedResult", [ValidationIssue(str(exc), str(expected_path))])
        )

    mismatch_issues: list[ValidationIssue] = []
    if packet_path.name not in {"strong-evidence.json", "missing-evidence.json", "contradictory-evidence.json"}:
        mismatch_issues.append(ValidationIssue("unknown benchmark fixture", "/fixture"))
    if not _expected_path_matches_fixture(expected_path, packet_path.name):
        mismatch_issues.append(
            ValidationIssue("expected result filename does not match fixture filename", "/expected")
        )
    if expected_document is not None and expected_document.get("fixture") != packet_path.name:
        mismatch_issues.append(
            ValidationIssue("expected result fixture field does not match packet filename", "/expected/fixture")
        )
    if generated_document is not None and generated_document.get("fixture") != packet_path.name:
        mismatch_issues.append(
            ValidationIssue("generated audit fixture field does not match packet filename", "/finding/fixture")
        )
    report["validationResults"].append(_validation_block("benchmarkPairing", mismatch_issues))
    if mismatch_issues:
        exit_code = 1

    try:
        policy_schema = load_json(policy_schema_path)
        validate_policy(policy_path)
        policy_issues = []
        if evaluation_policy is not None:
            policy_issues = validate_schema(evaluation_policy, policy_schema)
        report["validationResults"].append(_validation_block("evaluationPolicy", policy_issues))
        if policy_issues:
            exit_code = 1
    except Exception as exc:
        exit_code = 1
        report["validationResults"].append(
            _validation_block("evaluationPolicy", [ValidationIssue(str(exc), str(policy_path))])
        )

    if (
        exit_code == 0
        and generated_document is not None
        and expected_document is not None
        and evaluation_policy is not None
        and policy_schema is not None
    ):
        try:
            comparison = compare_benchmark_document(
                actual_document=generated_document,
                expected_document=expected_document,
                evaluation_policy=evaluation_policy,
                evaluation_policy_schema=policy_schema,
                audit_finding_schema=contract.audit_finding_schema,
            )
            report["hashes"]["transportSchema"] = comparison.transport_schema_hash
            report["hashes"]["evaluationPolicy"] = comparison.evaluation_policy_hash
            report["comparisonResults"] = {
                "passed": comparison.passed,
                "issues": [_comparison_issue_dict(issue) for issue in comparison.issues],
            }
            exit_code = 0 if comparison.passed else 1
        except EvaluationPolicyNotApproved as exc:
            report["comparisonResults"]["issues"].append(
                {"category": "policy", "path": "/evaluationPolicy", "message": str(exc)}
            )
            exit_code = 1

    report["overallPassed"] = (
        exit_code == 0
        and all(block["passed"] for block in report["validationResults"])
        and report["comparisonResults"]["passed"]
    )
    if not report["overallPassed"]:
        exit_code = 1

    _write_json(Path(args.output), report)
    print(f"wrote {args.output}")
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evidencegate-problem-audit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit")
    audit.add_argument("--packet", required=True)
    audit.add_argument("--output", required=True)
    audit.add_argument("--model")
    audit.set_defaults(func=audit_command)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--packet", required=True)
    validate.add_argument("--finding", required=True)
    validate.set_defaults(func=validate_command)

    eval_parser = subparsers.add_parser("eval")
    eval_parser.add_argument("--packet", required=True)
    eval_parser.add_argument("--finding", required=True)
    eval_parser.add_argument("--expected", required=True)
    eval_parser.add_argument("--output", required=True)
    eval_parser.add_argument("--requested-model")
    eval_parser.add_argument("--returned-model")
    eval_parser.add_argument("--response-id")
    eval_parser.add_argument("--prompt-hash")
    eval_parser.add_argument("--run-id")
    eval_parser.add_argument("--timestamp")
    eval_parser.add_argument("--policy", default=str(EVAL_POLICY_PATH))
    eval_parser.add_argument("--policy-schema", default=str(EVAL_POLICY_SCHEMA_PATH))
    eval_parser.set_defaults(func=eval_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValidationFailure, AuditGenerationFailure, ModelAdapterError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
