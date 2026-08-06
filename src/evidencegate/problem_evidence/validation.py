from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .load_contract import load_json


@dataclass(frozen=True)
class ValidationIssue:
    message: str
    path: str = ""


class ValidationFailure(Exception):
    def __init__(self, issues: list[ValidationIssue]):
        super().__init__("validation failed")
        self.issues = issues

    def __str__(self) -> str:
        return "\n".join(
            f"{issue.path}: {issue.message}" if issue.path else issue.message
            for issue in self.issues
        )


def _json_pointer(path: Any) -> str:
    parts = [str(part).replace("~", "~0").replace("/", "~1") for part in path]
    return "/" + "/".join(parts) if parts else "/"


def validate_schema(instance: dict[str, Any], schema: dict[str, Any]) -> list[ValidationIssue]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        ValidationIssue(error.message, _json_pointer(error.path))
        for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    ]


def raise_for_issues(issues: list[ValidationIssue]) -> None:
    if issues:
        raise ValidationFailure(issues)


def load_and_validate_packet(path: Path, schema: dict[str, Any]) -> dict[str, Any]:
    packet = load_json(path)
    issues = validate_schema(packet, schema)
    for index, record in enumerate(packet.get("evidence", [])):
        expected = record.get("origin") == "synthetic"
        if record.get("synthetic") is not expected:
            issues.append(
                ValidationIssue(
                    "synthetic must equal whether origin is 'synthetic'",
                    f"/evidence/{index}/synthetic",
                )
            )
    raise_for_issues(issues)
    return packet


def validate_transport_content(
    transport_content: dict[str, Any],
    transport_schema: dict[str, Any],
) -> list[ValidationIssue]:
    return validate_schema(transport_content, transport_schema)


def validate_audit_document(
    *,
    document: dict[str, Any],
    packet: dict[str, Any],
    audit_schema: dict[str, Any],
    requirement_ids: list[str],
) -> list[ValidationIssue]:
    issues = validate_schema(document, audit_schema)
    findings = document.get("findings", [])

    actual_order = [finding.get("requirementId") for finding in findings]
    if actual_order != requirement_ids:
        issues.append(
            ValidationIssue(
                f"findings must be ordered exactly as {requirement_ids}; got {actual_order}",
                "/findings",
            )
        )

    if document.get("reviewStatus") != "provisional":
        issues.append(ValidationIssue("runtime reviewStatus must be provisional", "/reviewStatus"))
    if document.get("humanReviewed") is not False:
        issues.append(ValidationIssue("runtime humanReviewed must be false", "/humanReviewed"))
    if document.get("reviewedBy") is not None:
        issues.append(ValidationIssue("runtime reviewedBy must be null", "/reviewedBy"))
    if document.get("reviewedDate") is not None:
        issues.append(ValidationIssue("runtime reviewedDate must be null", "/reviewedDate"))

    if any(record.get("origin") == "synthetic" for record in packet.get("evidence", [])):
        notice = document.get("syntheticEvidenceNotice", "")
        if "synthetic" not in notice or "real-world" not in notice:
            issues.append(
                ValidationIssue(
                    "synthetic evidence notice must mention synthetic evidence and real-world limits",
                    "/syntheticEvidenceNotice",
                )
            )

    evidence_ids = {record["evidenceId"] for record in packet.get("evidence", [])}
    claim_ids = {claim["claimId"] for claim in packet.get("claims", [])}
    interpretation_ids = {
        interpretation["interpretationId"] for interpretation in packet.get("interpretations", [])
    }

    for finding_index, finding in enumerate(findings):
        path = f"/findings/{finding_index}"
        if finding.get("reviewNote") is not None:
            issues.append(ValidationIssue("runtime reviewNote must be null", f"{path}/reviewNote"))

        unknown_claims = sorted(set(finding.get("claimIds", [])) - claim_ids)
        if unknown_claims:
            issues.append(ValidationIssue(f"unknown claimIds: {unknown_claims}", f"{path}/claimIds"))

        support = set(finding.get("evidenceIds", []))
        contradictory = set(finding.get("contradictoryEvidenceIds", []))
        unknown_evidence = sorted((support | contradictory) - evidence_ids)
        if unknown_evidence:
            issues.append(
                ValidationIssue(
                    f"unknown evidence ids: {unknown_evidence}",
                    path,
                )
            )

        interpretation_references = sorted((support | contradictory) & interpretation_ids)
        if interpretation_references:
            issues.append(
                ValidationIssue(
                    f"interpretations cannot be cited as evidence: {interpretation_references}",
                    path,
                )
            )

        overlap = sorted(support & contradictory)
        if overlap:
            issues.append(
                ValidationIssue(
                    f"evidenceIds and contradictoryEvidenceIds must be disjoint: {overlap}",
                    path,
                )
            )

    return issues
