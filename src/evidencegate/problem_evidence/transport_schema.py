from __future__ import annotations

from copy import deepcopy
from typing import Any

MODEL_OWNED_FINDING_FIELDS = [
    "requirementId",
    "requirement",
    "status",
    "evidenceIds",
    "contradictoryEvidenceIds",
    "missingEvidence",
    "severity",
    "rationale",
    "impact",
    "recommendation",
    "verificationTest",
    "requiresHumanDecision",
    "claimIds",
    "blockingReasons",
    "subAssessments",
    "offSegmentSignal",
    "policyGap",
]

RUNTIME_DOCUMENT_FIELDS = {
    "reviewStatus",
    "humanReviewed",
    "reviewedBy",
    "reviewedDate",
    "generatedBy",
    "generatedDate",
    "syntheticEvidenceNotice",
}

RUNTIME_FINDING_FIELDS = {"reviewNote"}


def build_transport_schema(audit_finding_schema: dict[str, Any]) -> dict[str, Any]:
    finding_schema = deepcopy(audit_finding_schema["$defs"]["auditFinding"])
    finding_schema["required"] = [
        field
        for field in finding_schema["required"]
        if field in MODEL_OWNED_FINDING_FIELDS
    ]
    finding_schema["properties"] = {
        field: schema
        for field, schema in finding_schema["properties"].items()
        if field in MODEL_OWNED_FINDING_FIELDS
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["findings"],
        "properties": {
            "findings": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": finding_schema,
            }
        },
    }


def assert_transport_mapping_covers_canonical(audit_finding_schema: dict[str, Any]) -> None:
    document_fields = set(audit_finding_schema["properties"])
    expected_document_fields = RUNTIME_DOCUMENT_FIELDS | {
        "schemaVersion",
        "fixture",
        "packetId",
        "packetPurpose",
        "findings",
    }
    if document_fields != expected_document_fields:
        missing = sorted(document_fields - expected_document_fields)
        extra = sorted(expected_document_fields - document_fields)
        raise AssertionError(f"document field mapping drifted: missing={missing}, extra={extra}")

    finding_fields = set(audit_finding_schema["$defs"]["auditFinding"]["properties"])
    expected_finding_fields = set(MODEL_OWNED_FINDING_FIELDS) | RUNTIME_FINDING_FIELDS
    if finding_fields != expected_finding_fields:
        missing = sorted(finding_fields - expected_finding_fields)
        extra = sorted(expected_finding_fields - finding_fields)
        raise AssertionError(f"finding field mapping drifted: missing={missing}, extra={extra}")
