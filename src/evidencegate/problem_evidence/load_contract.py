from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import paths


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class ProblemEvidenceContract:
    spec: str
    checklist: dict[str, Any]
    evidence_packet_schema: dict[str, Any]
    audit_finding_schema: dict[str, Any]
    hashes: dict[str, str]

    @property
    def requirement_ids(self) -> list[str]:
        return [item["requirementId"] for item in self.checklist["requirements"]]

    @property
    def requirement_names(self) -> dict[str, str]:
        return {item["requirementId"]: item["name"] for item in self.checklist["requirements"]}


def load_problem_evidence_contract() -> ProblemEvidenceContract:
    return ProblemEvidenceContract(
        spec=load_text(paths.SPEC_PATH),
        checklist=load_json(paths.CHECKLIST_PATH),
        evidence_packet_schema=load_json(paths.EVIDENCE_PACKET_SCHEMA_PATH),
        audit_finding_schema=load_json(paths.AUDIT_FINDING_SCHEMA_PATH),
        hashes={
            "SPEC.md": sha256_file(paths.SPEC_PATH),
            "checklist.json": sha256_file(paths.CHECKLIST_PATH),
            "evidence-packet.schema.json": sha256_file(paths.EVIDENCE_PACKET_SCHEMA_PATH),
            "audit-finding.schema.json": sha256_file(paths.AUDIT_FINDING_SCHEMA_PATH),
        },
    )
