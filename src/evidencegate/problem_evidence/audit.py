from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .assembly import assemble_audit_document
from .clock import Clock
from .load_contract import ProblemEvidenceContract
from .model_adapter import ModelAdapter, ModelFailure
from .prompt import build_prompt
from .transport_schema import build_transport_schema
from .validation import (
    ValidationFailure,
    load_and_validate_packet,
    raise_for_issues,
    validate_audit_document,
    validate_transport_content,
)


@dataclass(frozen=True)
class AuditRunResult:
    document: dict
    requested_model: str
    returned_model: str
    response_id: str | None
    completion_status: str


class AuditGenerationFailure(Exception):
    pass


def run_audit(
    *,
    packet_path: Path,
    model: str,
    adapter: ModelAdapter,
    contract: ProblemEvidenceContract,
    clock: Clock,
) -> AuditRunResult:
    packet = load_and_validate_packet(packet_path, contract.evidence_packet_schema)
    transport_schema = build_transport_schema(contract.audit_finding_schema)
    prompt = build_prompt(
        spec=contract.spec,
        checklist=contract.checklist,
        transport_schema=transport_schema,
        packet=packet,
    )
    model_result = adapter.generate_audit_json(
        prompt=prompt,
        transport_schema=transport_schema,
        model=model,
    )
    if isinstance(model_result, ModelFailure):
        raise AuditGenerationFailure(model_result.message)

    raise_for_issues(validate_transport_content(model_result.transport_content, transport_schema))
    document = assemble_audit_document(
        packet=packet,
        transport_content=model_result.transport_content,
        packet_path=packet_path,
        generated_by=f"EvidenceGate Phase 1 via {model_result.returned_model}",
        clock=clock,
    )
    raise_for_issues(
        validate_audit_document(
            document=document,
            packet=packet,
            audit_schema=contract.audit_finding_schema,
            requirement_ids=contract.requirement_ids,
        )
    )
    return AuditRunResult(
        document=document,
        requested_model=model_result.requested_model,
        returned_model=model_result.returned_model,
        response_id=model_result.response_id,
        completion_status=model_result.completion_status,
    )
