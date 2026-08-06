from __future__ import annotations

from evidencegate.problem_evidence.load_contract import load_json, load_problem_evidence_contract
from evidencegate.problem_evidence.paths import AUDITOR_ROOT
from evidencegate.problem_evidence.prompt import PROMPT_VERSION, build_prompt
from evidencegate.problem_evidence.transport_schema import build_transport_schema


def test_prompt_contains_phase1_boundaries_and_excludes_expected_results() -> None:
    contract = load_problem_evidence_contract()
    packet = load_json(AUDITOR_ROOT / "fixtures" / "strong-evidence.json")
    prompt = build_prompt(
        spec=contract.spec,
        checklist=contract.checklist,
        transport_schema=build_transport_schema(contract.audit_finding_schema),
        packet=packet,
    )

    assert PROMPT_VERSION in prompt
    assert "OPEN-04" in prompt
    assert "OPEN-06" in prompt
    assert "OPEN-07" in prompt
    assert "Do not use world knowledge" in prompt
    assert "Runtime-owned metadata is not part of your output" in prompt
    assert "strong-evidence.expected.json" not in prompt
