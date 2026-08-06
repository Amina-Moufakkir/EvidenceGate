from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .clock import Clock


def build_synthetic_evidence_notice(packet: dict[str, Any]) -> str:
    packet_id = packet["packetId"]
    if any(record.get("origin") == "synthetic" for record in packet.get("evidence", [])):
        return (
            f"At least one evidence record in packet {packet_id} has origin 'synthetic'. "
            "These findings are provisional model output about the supplied packet only; "
            "they do not establish real-world validity, market truth, product demand, or production accuracy."
        )
    return (
        f"No evidence record in packet {packet_id} has origin 'synthetic'. "
        "These findings are provisional model output about the supplied packet only."
    )


def assemble_audit_document(
    *,
    packet: dict[str, Any],
    transport_content: dict[str, Any],
    packet_path: Path,
    generated_by: str,
    clock: Clock,
) -> dict[str, Any]:
    findings = deepcopy(transport_content["findings"])
    for finding in findings:
        finding["reviewNote"] = None

    return {
        "schemaVersion": "1.0.0",
        "fixture": packet_path.name,
        "packetId": packet["packetId"],
        "packetPurpose": packet["packetPurpose"],
        "reviewStatus": "provisional",
        "humanReviewed": False,
        "reviewedBy": None,
        "reviewedDate": None,
        "generatedBy": generated_by,
        "generatedDate": clock.today_iso(),
        "syntheticEvidenceNotice": build_synthetic_evidence_notice(packet),
        "findings": findings,
    }
