from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

from evidencegate.problem_evidence.audit import AuditGenerationFailure, run_audit
from evidencegate.problem_evidence.clock import FixedClock
from evidencegate.problem_evidence.load_contract import load_json, load_problem_evidence_contract
from evidencegate.problem_evidence.model_adapter import (
    FakeModelAdapter,
    ModelFailure,
    OpenAIResponsesAdapter,
)
from evidencegate.problem_evidence.paths import AUDITOR_ROOT
from evidencegate.problem_evidence.transport_schema import MODEL_OWNED_FINDING_FIELDS


def _transport_from_expected(name: str) -> dict:
    expected = load_json(AUDITOR_ROOT / "expected" / name)
    return {
        "findings": [
            _transport_finding(finding)
            for finding in expected["findings"]
        ]
    }


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


class _ResponsesResource:
    def __init__(self, response=None, exc: Exception | None = None):
        self.response = response
        self.exc = exc
        self.request = None

    def create(self, **kwargs):
        self.request = kwargs
        if self.exc is not None:
            raise self.exc
        return self.response


class _Client:
    def __init__(self, response=None, exc: Exception | None = None):
        self.responses = _ResponsesResource(response=response, exc=exc)


def _message_response(*, content, status="completed", incomplete_reason=None):
    incomplete_details = (
        SimpleNamespace(reason=incomplete_reason) if incomplete_reason is not None else None
    )
    return SimpleNamespace(
        id="resp_123",
        model="returned-model",
        status=status,
        incomplete_details=incomplete_details,
        output=[SimpleNamespace(type="message", content=content)],
    )


def _output_text_response(payload: dict):
    return _message_response(
        content=[SimpleNamespace(type="output_text", text=json.dumps(payload))]
    )


def test_openai_responses_adapter_parses_completed_output_text_json() -> None:
    transport = _transport_from_expected("strong-evidence.expected.json")
    client = _Client(response=_output_text_response(transport))
    adapter = OpenAIResponsesAdapter(client=client)

    result = adapter.generate_audit_json(
        prompt="prompt",
        transport_schema={"type": "object"},
        model="requested-model",
    )

    assert result.transport_content == transport
    assert result.requested_model == "requested-model"
    assert result.returned_model == "returned-model"
    assert result.response_id == "resp_123"
    assert result.completion_status == "completed"
    assert client.responses.request["text"]["format"]["strict"] is True


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (
            _message_response(content=[SimpleNamespace(type="refusal", refusal="cannot comply")]),
            "refusal",
        ),
        (
            _message_response(content=[], status="incomplete", incomplete_reason="max_output_tokens"),
            "truncated",
        ),
        (
            _message_response(content=[], status="incomplete", incomplete_reason="content_filter"),
            "content_filtered",
        ),
        (
            _message_response(content=[SimpleNamespace(type="output_text", text="{bad json")]),
            "incomplete",
        ),
        (
            SimpleNamespace(
                id="resp_123",
                model="returned-model",
                status="completed",
                incomplete_details=None,
                output=[],
                output_text="",
            ),
            "incomplete",
        ),
    ],
)
def test_openai_responses_adapter_returns_typed_failures(response, reason) -> None:
    adapter = OpenAIResponsesAdapter(client=_Client(response=response))

    result = adapter.generate_audit_json(
        prompt="prompt",
        transport_schema={"type": "object"},
        model="requested-model",
    )

    assert isinstance(result, ModelFailure)
    assert result.reason == reason


def test_openai_responses_adapter_returns_api_failure_on_exception() -> None:
    adapter = OpenAIResponsesAdapter(client=_Client(exc=RuntimeError("boom")))

    result = adapter.generate_audit_json(
        prompt="prompt",
        transport_schema={"type": "object"},
        model="requested-model",
    )

    assert isinstance(result, ModelFailure)
    assert result.reason == "api_error"
    assert "boom" in result.message


def test_openai_adapter_failure_cannot_produce_final_document() -> None:
    contract = load_problem_evidence_contract()
    adapter = OpenAIResponsesAdapter(
        client=_Client(response=_message_response(content=[SimpleNamespace(type="output_text", text="{")]))
    )

    with pytest.raises(AuditGenerationFailure):
        run_audit(
            packet_path=AUDITOR_ROOT / "fixtures" / "strong-evidence.json",
            model="fake-model",
            adapter=adapter,
            contract=contract,
            clock=FixedClock("2026-08-05"),
        )
