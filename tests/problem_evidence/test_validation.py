from __future__ import annotations

import copy

from evidencegate.problem_evidence.assembly import assemble_audit_document
from evidencegate.problem_evidence.clock import FixedClock
from evidencegate.problem_evidence.load_contract import load_json, load_problem_evidence_contract
from evidencegate.problem_evidence.paths import AUDITOR_ROOT
from evidencegate.problem_evidence.transport_schema import MODEL_OWNED_FINDING_FIELDS
from evidencegate.problem_evidence.validation import (
    load_and_validate_packet,
    validate_audit_document,
)


def _document() -> tuple[dict, dict, list[str], dict]:
    contract = load_problem_evidence_contract()
    packet_path = AUDITOR_ROOT / "fixtures" / "missing-evidence.json"
    packet = load_json(packet_path)
    expected = load_json(AUDITOR_ROOT / "expected" / "missing-evidence.expected.json")
    transport = {
        "findings": [
            _transport_finding(finding)
            for finding in expected["findings"]
        ]
    }
    document = assemble_audit_document(
        packet=packet,
        transport_content=transport,
        packet_path=packet_path,
        generated_by="test",
        clock=FixedClock("2026-08-05"),
    )
    return document, packet, contract.requirement_ids, contract.audit_finding_schema


def _transport_finding(finding: dict) -> dict:
    transport_finding = {}
    for field in MODEL_OWNED_FINDING_FIELDS:
        if field in finding:
            transport_finding[field] = copy.deepcopy(finding[field])
        elif field == "blockingReasons":
            transport_finding[field] = []
        else:
            raise AssertionError(f"missing required transport field {field}")
    return transport_finding


def _messages(issues):
    return [issue.message for issue in issues]


def test_packet_validation_enforces_synthetic_origin_consistency(tmp_path) -> None:
    contract = load_problem_evidence_contract()
    packet = load_json(AUDITOR_ROOT / "fixtures" / "strong-evidence.json")
    packet["evidence"][0]["synthetic"] = False
    packet_path = tmp_path / "bad-packet.json"
    import json

    packet_path.write_text(json.dumps(packet), encoding="utf-8")

    try:
        load_and_validate_packet(packet_path, contract.evidence_packet_schema)
    except Exception as exc:
        assert "synthetic must equal" in str(exc)
    else:
        raise AssertionError("expected validation failure")


def test_validation_rejects_bad_order_unknown_ids_overlap_and_approval_metadata() -> None:
    document, packet, requirement_ids, schema = _document()
    document["reviewStatus"] = "approved"
    document["humanReviewed"] = True
    document["findings"][0], document["findings"][1] = document["findings"][1], document["findings"][0]
    document["findings"][0]["claimIds"].append("CL-999")
    document["findings"][0]["evidenceIds"] = ["EV-999", "EV-001"]
    document["findings"][0]["contradictoryEvidenceIds"] = ["EV-001"]

    messages = _messages(
        validate_audit_document(
            document=document,
            packet=packet,
            audit_schema=schema,
            requirement_ids=requirement_ids,
        )
    )

    assert any("findings must be ordered" in message for message in messages)
    assert any("runtime reviewStatus must be provisional" in message for message in messages)
    assert any("runtime humanReviewed must be false" in message for message in messages)
    assert any("unknown claimIds" in message for message in messages)
    assert any("unknown evidence ids" in message for message in messages)
    assert any("must be disjoint" in message for message in messages)

def test_validation_rejects_missing_synthetic_notice_and_review_note() -> None:
    document, packet, requirement_ids, schema = _document()
    document["syntheticEvidenceNotice"] = "placeholder"
    document["findings"][0]["reviewNote"] = "approved by model"

    messages = _messages(
        validate_audit_document(
            document=document,
            packet=packet,
            audit_schema=schema,
            requirement_ids=requirement_ids,
        )
    )

    assert any("synthetic evidence notice" in message for message in messages)
    assert any("runtime reviewNote must be null" in message for message in messages)


def test_validation_rejects_non_contributing_unknown_overlap_and_duplicates() -> None:
    document, packet, requirement_ids, schema = _document()
    document["findings"][0]["nonContributingEvidence"] = [
        {
            "evidenceId": "EV-001",
            "qualification": "unsuitable",
            "relationshipStatus": "not-applicable",
            "reasonCodes": ["internal-assertion"],
            "rationale": "The record is the team's own assertion.",
        },
        {
            "evidenceId": "EV-001",
            "qualification": "unsuitable",
            "relationshipStatus": "not-applicable",
            "reasonCodes": ["internal-assertion"],
            "rationale": "A duplicate disposition for the same record.",
        },
        {
            "evidenceId": "EV-999",
            "qualification": "unsuitable",
            "relationshipStatus": "not-applicable",
            "reasonCodes": ["requirement-fit-none"],
            "rationale": "This id is not in the packet.",
        },
    ]
    document["findings"][0]["evidenceIds"] = ["EV-001"]

    messages = _messages(
        validate_audit_document(
            document=document,
            packet=packet,
            audit_schema=schema,
            requirement_ids=requirement_ids,
        )
    )

    assert any("unknown evidence ids" in message for message in messages)
    assert any("must be disjoint" in message for message in messages)
    assert any("at most once" in message for message in messages)
