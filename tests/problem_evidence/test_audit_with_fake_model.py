from __future__ import annotations

import copy

import pytest

from evidencegate.problem_evidence.audit import AuditGenerationFailure, run_audit
from evidencegate.problem_evidence.clock import FixedClock
from evidencegate.problem_evidence.load_contract import load_json, load_problem_evidence_contract
from evidencegate.problem_evidence.model_adapter import FakeModelAdapter, ModelFailure
from evidencegate.problem_evidence.paths import AUDITOR_ROOT
from evidencegate.problem_evidence.transport_schema import MODEL_OWNED_FINDING_FIELDS


def _transport_from_expected(name: str) -> dict:
    expected = load_json(AUDITOR_ROOT / "expected" / name)
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


def test_run_audit_with_fake_model_assembles_provisional_document() -> None:
    contract = load_problem_evidence_contract()
    result = run_audit(
        packet_path=AUDITOR_ROOT / "fixtures" / "contradictory-evidence.json",
        model="fake-model",
        adapter=FakeModelAdapter(
            transport_content=_transport_from_expected("contradictory-evidence.expected.json")
        ),
        contract=contract,
        clock=FixedClock("2026-08-05"),
    )

    assert result.document["reviewStatus"] == "provisional"
    assert result.document["humanReviewed"] is False
    assert result.document["packetId"] == "ccpa-contradictory-001"
    assert result.returned_model == "fake-model"
    assert result.response_id == "fake-response"


def test_run_audit_rejects_adapter_failure_before_document_output() -> None:
    contract = load_problem_evidence_contract()
    adapter = FakeModelAdapter(
        failure=ModelFailure(
            reason="refusal",
            requested_model="fake-model",
            message="model refused",
        )
    )

    with pytest.raises(AuditGenerationFailure):
        run_audit(
            packet_path=AUDITOR_ROOT / "fixtures" / "contradictory-evidence.json",
            model="fake-model",
            adapter=adapter,
            contract=contract,
            clock=FixedClock("2026-08-05"),
        )
