from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
AUDITOR_ROOT = PACKAGE_ROOT / "auditors" / "problem-evidence"
SPEC_PATH = AUDITOR_ROOT / "SPEC.md"
CHECKLIST_PATH = AUDITOR_ROOT / "checklist.json"
EVIDENCE_PACKET_SCHEMA_PATH = AUDITOR_ROOT / "schema" / "evidence-packet.schema.json"
AUDIT_FINDING_SCHEMA_PATH = AUDITOR_ROOT / "schema" / "audit-finding.schema.json"
EVAL_POLICY_PATH = AUDITOR_ROOT / "eval-policy" / "phase1-benchmark-policy.json"
EVAL_POLICY_SCHEMA_PATH = AUDITOR_ROOT / "eval-policy" / "phase1-benchmark-policy.schema.json"
