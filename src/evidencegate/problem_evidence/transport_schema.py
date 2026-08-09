from __future__ import annotations

from copy import deepcopy
from typing import Any

MODEL_OWNED_FINDING_FIELDS = [
    "requirementId",
    "requirement",
    "status",
    "evidenceIds",
    "contradictoryEvidenceIds",
    "nonContributingEvidence",
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


def _require_every_object_property(schema: Any) -> None:
    if not isinstance(schema, dict):
        return

    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        schema["required"] = list(properties)
        schema["additionalProperties"] = False
        for property_schema in properties.values():
            _require_every_object_property(property_schema)

    if schema.get("type") == "array":
        _require_every_object_property(schema.get("items"))

    for combiner in ("anyOf", "oneOf", "allOf"):
        for option in schema.get(combiner, []):
            _require_every_object_property(option)


def build_transport_schema(audit_finding_schema: dict[str, Any]) -> dict[str, Any]:
    finding_schema = deepcopy(audit_finding_schema["$defs"]["auditFinding"])
    finding_schema["properties"] = {
        field: schema
        for field, schema in finding_schema["properties"].items()
        if field in MODEL_OWNED_FINDING_FIELDS
    }

    transport_schema = {
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
    _require_every_object_property(transport_schema)
    return transport_schema


def assert_strict_structured_outputs_compatible(schema: dict[str, Any]) -> None:
    def walk(node: Any, path: str) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "object":
            properties = node.get("properties")
            if not isinstance(properties, dict):
                raise AssertionError(f"{path}: object schema must define properties")
            if node.get("additionalProperties") is not False:
                raise AssertionError(f"{path}: object schema must set additionalProperties false")
            if set(node.get("required") or []) != set(properties):
                raise AssertionError(f"{path}: every object property must be required")
            for name, child in properties.items():
                walk(child, f"{path}/properties/{name}")
        if node.get("type") == "array":
            walk(node.get("items"), f"{path}/items")
        for combiner in ("anyOf", "oneOf", "allOf"):
            for index, option in enumerate(node.get(combiner, [])):
                walk(option, f"{path}/{combiner}/{index}")

    walk(schema, "#")


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
