from __future__ import annotations

import json
from typing import Any


PROMPT_VERSION = "problem-evidence-phase1-v0"


def build_prompt(
    *,
    spec: str,
    checklist: dict[str, Any],
    transport_schema: dict[str, Any],
    packet: dict[str, Any],
) -> str:
    return "\n\n".join(
        [
            f"Prompt version: {PROMPT_VERSION}",
            "You are the Problem Evidence Auditor. Return only JSON matching the transport schema.",
            "Authority hierarchy: schemas own structure, checklist owns requirement definitions and configurable thresholds, SPEC.md owns policy semantics.",
            "Emit exactly five findings in order: REQ-1, REQ-2, REQ-3, REQ-4, REQ-5.",
            "Use only supplied packet claims and evidence. Do not use world knowledge. Do not extract claims from prose.",
            "Keep supporting evidenceIds and contradictoryEvidenceIds separate. Absence is not contradiction.",
            "Do not cite interpretations as evidence. You may discuss unsupported interpretations in prose if relevant.",
            "Do not evaluate product demand, pilots, or willingness to pay for the proposed product.",
            "Synthetic evidence may contribute toward pass only when packetPurpose is fixture.",
            "Resolved policies are binding: OPEN-04 explicit qualifying supersession only; OPEN-06 bounded partial segment fit; OPEN-07 deterministic claim mismatch blocking.",
            "Runtime-owned metadata is not part of your output: review status, human review fields, generated fields, synthetic-evidence notice, and reviewNote are injected later.",
            "SPEC.md:\n" + spec,
            "checklist.json:\n" + json.dumps(checklist, indent=2, sort_keys=True),
            "transport schema:\n" + json.dumps(transport_schema, indent=2, sort_keys=True),
            "evidence packet:\n" + json.dumps(packet, indent=2, sort_keys=True),
        ]
    )
