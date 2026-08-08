# Phase 1 Implementation Specification: Problem Evidence Auditor Runtime

## Objective

Build the first operational vertical slice for the Problem Evidence Auditor:

Evidence packet JSON -> input schema validation -> model semantic audit -> deterministic assembly of final audit document -> output and integrity validation -> benchmark comparison against approved Phase 0 results.

Phase 0 is authoritative. `SPEC.md` owns policy semantics, `checklist.json` owns requirement definitions and configurable thresholds, and schemas own structure. Resolved OPEN-04, OPEN-06, and OPEN-07 remain binding.

## Non-Goals

No web UI, dashboard, database, authentication, multi-agent orchestration, production deployment, real commercial-cleaning packet, or additional auditors. Do not rewrite approved expected results.

## Technology

Use Python with `jsonschema`, `openai`, `pytest`, and stdlib `argparse`, `json`, `pathlib`, `hashlib`, `datetime`, `os`, and `uuid`.

No dependency installation occurs until implementation approval.

## Proposed Structure

```text
pyproject.toml
auditors/problem-evidence/PHASE1.md
auditors/problem-evidence/eval-policy/phase1-benchmark-policy.json
src/evidencegate/problem_evidence/
  __init__.py
  cli.py
  paths.py
  load_contract.py
  validation.py
  prompt.py
  transport_schema.py
  assembly.py
  model_adapter.py
  audit.py
  compare.py
  clock.py
tests/problem_evidence/
  test_validation.py
  test_transport_mapping.py
  test_prompt.py
  test_compare.py
  test_audit_with_fake_model.py
  test_live_model_optional.py
```

## CLI

```text
evidencegate-problem-audit audit --packet PATH --output PATH --model MODEL
evidencegate-problem-audit audit --packet PATH --output PATH
```

The second form requires `EVIDENCEGATE_MODEL`. There is no silent hard-coded model default.

For the first controlled live evaluation, explicitly request `gpt-5.6-sol` if the account has access. Do not silently substitute another model. If unavailable, report that and require an explicit alternate model choice.

```text
evidencegate-problem-audit validate --packet PATH --finding PATH
evidencegate-problem-audit eval --runs 5 --model MODEL --output-dir .evidencegate/eval
```

Eval artifacts and raw model outputs remain ignored local files.

## Model-Owned Content And Runtime-Owned Metadata

The model generates only model-owned semantic finding content: findings, rationale, impact, recommendation, verification behavior, evidence placement, sub-assessments, blocking reasons, off-segment signal, and policy gap.

The model must not control these canonical fields.

Document-level runtime-owned fields:

- `/reviewStatus`
- `/humanReviewed`
- `/reviewedBy`
- `/reviewedDate`
- `/generatedBy`
- `/generatedDate`
- `/syntheticEvidenceNotice`

Finding-level runtime-owned field, injected into every item in `/findings`:

- `/findings/{index}/reviewNote`

Runtime injects those canonical fields before final validation:

- `/reviewStatus`: `"provisional"`
- `/humanReviewed`: `false`
- `/reviewedBy`: `null`
- `/reviewedDate`: `null`
- `/generatedBy`: runner and adapter identifier
- `/generatedDate`: date from injectable clock
- `/syntheticEvidenceNotice`: deterministic notice when required by Phase 0
- `/findings/{index}/reviewNote`: `null`

The final assembled document is then validated against `audit-finding.schema.json`.

## Model Adapter Result Envelope

A successful adapter call returns a typed result containing:

- parsed transport content;
- requested model;
- returned model identifier;
- response identifier when available;
- completion status.

Refusal, incomplete output, token truncation, content filtering, and API failure must return typed failure results or raise defined adapter errors. They are never valid semantic output and must never produce a final audit document.

No business logic lives in the adapter.

## Structured Output

Do not assume the Phase 0 Draft 2020-12 schema is directly usable as an OpenAI Structured Outputs schema.

Define an API-compatible transport schema for model-owned content. The existing `audit-finding.schema.json` remains the final validation authority after deterministic assembly.

Use the OpenAI Responses API with strict Structured Outputs through `text.format`. The adapter must explicitly handle refusals, incomplete output, token truncation, content filtering, and API errors. Any failed response exits non-zero and must never produce a final audit file.

Tests must prove:

- every transport field maps into the canonical document;
- the assembled document validates against `audit-finding.schema.json`;
- no canonical policy field is silently discarded;
- schema divergence causes a test failure.

## Prompt Strategy

Load `SPEC.md`, `checklist.json`, the transport schema, and the packet. Normal audit prompts must not include approved expected files.

The prompt must state the authority hierarchy, five ordered findings, packet-only evidence, separate support/conflict/non-contributing roles, no world knowledge, no product-demand conclusions, fixture-only synthetic pass behavior, runtime-owned metadata, and binding OPEN-04/06/07 rules.

## Validation Categories

Structural invariants enforceable by code:

- input conforms to `evidence-packet.schema.json`;
- assembled output conforms to `audit-finding.schema.json`;
- exactly five findings in REQ-1 through REQ-5 order;
- referenced `claimIds` and evidence IDs exist in the packet;
- `evidenceIds`, `contradictoryEvidenceIds`, and `nonContributingEvidence` are pairwise disjoint;
- non-contributing evidence IDs are unique per finding and never affect support or contradiction counts;
- synthetic-evidence notice is present when required by Phase 0;
- runtime metadata is provisional and never claims human approval.

Policy semantics judged by auditor and benchmark:

- status selection;
- evidence placement;
- contradiction handling;
- OPEN-04 supersession;
- OPEN-06 partial segment fit;
- OPEN-07 claim mismatch;
- REQ-2 instance scope and REQ-3 calendar-week behavior.

Prose semantics requiring explicit evaluation rule or human review:

- rationale adequacy;
- recommendation meaning;
- verification-test correctness;
- whether `policyGap` names a genuinely uncovered case.

No new invariant may be enforced just because current fixtures happen to satisfy it. Each enforced invariant must cite Phase 0 schema or SPEC authority.

## Evaluation Policy Artifact And Approval Gate

Recommendation and verification semantics must not be hidden inside ad hoc comparator predicates.

Codex must add a separate artifact:

```text
auditors/problem-evidence/eval-policy/phase1-benchmark-policy.json
```

The artifact must have a version or policy identifier and explicitly map each applicable fixture and requirement to:

- expected recommendation action type;
- required verification behavior;
- prohibited substitutions.

Implementation must proceed in this order:

1. Codex drafts `phase1-benchmark-policy.json`.
2. Codex provides schema-validation and review instructions for that artifact.
3. Implementation pauses for human review.
4. Only after approval may the comparator encode and enforce those rules.

Codex must not label the artifact human-reviewed before that review occurs.

## Benchmark Comparison

Strictly compare policy-critical structured content:

- `requirementId`;
- `claimIds`;
- `status`;
- `evidenceIds`;
- `contradictoryEvidenceIds`;
- `nonContributingEvidence`;
- ID-bearing or categorical `offSegmentSignal` content;
- `severity`;
- `requiresHumanDecision`;
- `blockingReasons`;
- `policyGap`;
- categorical or ID-bearing sub-assessment fields.

Also structurally validate the synthetic-evidence notice.

The evaluation must catch incorrect verification behavior for REQ-2 instance scope, REQ-3 predefined calendar-week buckets, OPEN-04 supersession, OPEN-06 partial segment fit, and OPEN-07 claim mismatch.

The comparator implements only reviewed rules from `phase1-benchmark-policy.json`. It must not invent recommendation or verification expectations internally.

Rationale prose need not match exactly. One representative successful output per fixture requires human semantic review before Phase 1 acceptance. Automated comparison is not proof that prose reasoning is correct.

## Reliability Protocol

Run 5 live generations per fixture, 15 total.

Phase 1 acceptance requires:

- 5/5 runs per fixture matching every strict policy-critical field;
- 100% structural and integrity validation;
- zero false claims of human approval;
- human semantic review of one representative successful output per fixture.

These repeated synthetic-fixture runs are a benchmark consistency gate, not statistical calibration or evidence of production accuracy.

Every eval report records:

- requested model;
- returned model identifier;
- response identifier when available;
- prompt version or hash;
- run identifier;
- timestamp;
- validation results;
- comparison results;
- hash of `SPEC.md`;
- hash of `checklist.json`;
- hash of `evidence-packet.schema.json`;
- hash of `audit-finding.schema.json`;
- hash of the transport schema;
- hash of `phase1-benchmark-policy.json`;
- hash of the fixture file;
- hash of the approved expected file.

The evaluation-policy hash is required because changing that artifact can change the pass/fail verdict.

## Testing

Unit tests cover validation failures, transport-to-canonical mapping, runtime-owned metadata injection, injectable clock behavior, adapter result envelopes, comparator disagreements, and reviewed eval-policy rule application.

Integration tests use fake adapters and require no API calls.

Live tests are skipped unless `OPENAI_API_KEY`, `EVIDENCEGATE_LIVE_MODEL_TESTS=1`, and `--model` or `EVIDENCEGATE_MODEL` are present.

## Security And Errors

Secrets come only from environment variables. Do not log secrets. Network access is isolated to the live model adapter. Approved benchmarks are read-only inputs by convention.

**Prompt injection is an unmitigated limitation.** The prompt builder places the supplied evidence packet directly into the model prompt, so instruction-like text written into any free-text packet field — claim text, evidence description, recorded limitation, interpretation — may influence model-owned semantic output: `status`, `severity`, `requiresHumanDecision`, evidence placement, and all prose fields. No isolation, delimiting, or injection resistance is implemented, and structural validation cannot detect it, because distinguishing an injected verdict from an honest one is a semantic judgment. The runtime-owned metadata boundary is unaffected: `reviewStatus`, `humanReviewed`, `reviewedBy`, `reviewedDate` and `reviewNote` are injected after the model returns and re-validated before output, so an injected packet can never produce a document claiming human approval.

Failures produce non-zero exits and concise diagnostics with path, JSON pointer where possible, fixture, run ID, response ID when available, and requirement ID where applicable.

## Implementation Sequence

1. Add packaging and CLI skeleton.
2. Implement contract loading and hashing.
3. Implement transport schema and mapping tests.
4. Implement deterministic assembly with injectable clock.
5. Implement structural validation.
6. Implement prompt builder.
7. Implement fake adapter.
8. Implement OpenAI Responses adapter.
9. Draft `phase1-benchmark-policy.json`.
10. Provide validation and review instructions for that artifact.
11. Pause for human review and approval.
12. After approval, implement comparator enforcement of reviewed rules.
13. Add tests and optional live eval command.
14. Run Phase 0 validation plus Phase 1 tests.

## Acceptance Criteria

Phase 1 is accepted when the CLI audits one packet into a provisional canonical document, validates all structural invariants, compares benchmarks using reviewed evaluation rules, passes tests without live API calls, and meets the 5/5 repeated-run benchmark gate with human semantic review.

## Resolved Implementation Decisions

- No silent model default; require `--model` or `EVIDENCEGATE_MODEL`.
- First controlled live evaluation explicitly requests `gpt-5.6-sol` if available.
- If `gpt-5.6-sol` is unavailable, report that and require an explicit alternate model choice.
- Recommendation and verification rules live in the reviewed eval-policy artifact.
- Acceptance requires 5/5 per fixture.
- Raw live outputs and eval artifacts stay ignored local files.
