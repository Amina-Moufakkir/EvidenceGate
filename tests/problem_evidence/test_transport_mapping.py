from __future__ import annotations

import copy

import pytest

from evidencegate.problem_evidence.assembly import assemble_audit_document
from evidencegate.problem_evidence.clock import FixedClock
from evidencegate.problem_evidence.load_contract import load_json, load_problem_evidence_contract
from evidencegate.problem_evidence.paths import AUDITOR_ROOT
from evidencegate.problem_evidence.transport_schema import (
    MODEL_OWNED_FINDING_FIELDS,
    RUNTIME_DOCUMENT_FIELDS,
    assert_strict_structured_outputs_compatible,
    assert_transport_mapping_covers_canonical,
    build_transport_schema,
)
from evidencegate.problem_evidence.validation import (
    raise_for_issues,
    validate_audit_document,
    validate_transport_content,
)


def _transport_from_expected(name: str) -> dict:
    expected = load_json(AUDITOR_ROOT / "expected" / name)
    findings = []
    for finding in expected["findings"]:
        transport_finding = {}
        for field in MODEL_OWNED_FINDING_FIELDS:
            if field in finding:
                transport_finding[field] = copy.deepcopy(finding[field])
            elif field == "blockingReasons":
                transport_finding[field] = []
            else:
                raise AssertionError(f"missing required transport field {field}")
        findings.append(transport_finding)
    return {"findings": findings}


def test_transport_schema_maps_every_canonical_field() -> None:
    contract = load_problem_evidence_contract()
    assert_transport_mapping_covers_canonical(contract.audit_finding_schema)
    transport_schema = build_transport_schema(contract.audit_finding_schema)

    assert set(transport_schema["properties"]) == {"findings"}
    assert_strict_structured_outputs_compatible(transport_schema)
    finding_properties = transport_schema["properties"]["findings"]["items"]["properties"]
    assert set(transport_schema["required"]) == {"findings"}
    assert set(transport_schema["properties"]["findings"]["items"]["required"]) == set(
        finding_properties
    )
    assert "reviewNote" not in finding_properties
    for field in RUNTIME_DOCUMENT_FIELDS:
        assert field not in transport_schema["properties"]


def test_transport_mapping_drift_fails() -> None:
    contract = load_problem_evidence_contract()
    drifted = copy.deepcopy(contract.audit_finding_schema)
    drifted["$defs"]["auditFinding"]["properties"]["newPolicyField"] = {"type": "string"}

    with pytest.raises(AssertionError):
        assert_transport_mapping_covers_canonical(drifted)


def test_assembled_document_validates_against_canonical_schema() -> None:
    contract = load_problem_evidence_contract()
    packet_path = AUDITOR_ROOT / "fixtures" / "strong-evidence.json"
    packet = load_json(packet_path)
    transport = _transport_from_expected("strong-evidence.expected.json")
    transport_schema = build_transport_schema(contract.audit_finding_schema)
    raise_for_issues(validate_transport_content(transport, transport_schema))

    document = assemble_audit_document(
        packet=packet,
        transport_content=transport,
        packet_path=packet_path,
        generated_by="test-adapter",
        clock=FixedClock("2026-08-05"),
    )

    assert document["reviewStatus"] == "provisional"
    assert document["schemaVersion"] == "2.0.0"
    assert document["humanReviewed"] is False
    assert document["generatedDate"] == "2026-08-05"
    assert document["reviewedBy"] is None
    assert document["reviewedDate"] is None
    assert "synthetic" in document["syntheticEvidenceNotice"]
    assert all(finding["reviewNote"] is None for finding in document["findings"])
    assert all("nonContributingEvidence" in finding for finding in document["findings"])
    raise_for_issues(
        validate_audit_document(
            document=document,
            packet=packet,
            audit_schema=contract.audit_finding_schema,
            requirement_ids=contract.requirement_ids,
        )
    )
