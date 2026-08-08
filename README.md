# EvidenceGate

An evidence-based product auditing system. It identifies unsupported product assumptions, missing proof, contradictory evidence, and the next validation step.

EvidenceGate evaluates **evidence packets** — not products. It reports what supplied records establish, what they only partly establish, what they contradict, and what cannot be evaluated at all. It never invents customer facts, market evidence, interview results, causal explanations, or certainty.

## Status

**Phase 0 contract: complete and owner-approved.** `SPEC.md`, `checklist.json`, the two schemas, three synthetic fixtures and three expected-result files define correct behaviour. They were written before anything was built that could quietly redefine them.

**Phase 1 runtime: implemented and offline-tested. Not formally accepted.** There is application code (`src/evidencegate/`), there are two runtime dependencies (`jsonschema`, `openai`), and there is model-call capability — an OpenAI Responses adapter behind a CLI. The whole test suite runs offline with fake adapters and no network access.

What that does and does not mean:

- **Offline-tested** means the structural contract holds: packet validation, transport-to-canonical mapping, deterministic assembly, runtime-owned metadata injection, adapter failure envelopes, and benchmark comparison all have tests that run without an API call.
- **Not formally accepted** means the Phase 1 acceptance gate in `auditors/problem-evidence/PHASE1.md` has not been met. That gate requires 5/5 matching live runs per fixture and human semantic review of representative prose. `eval-policy/model-compatibility-policy.json` records `acceptanceBlocked: true`, and Gate 2A's `contracts/lifecycle-state.json` records formal Phase 1 acceptance as not a repository state at all.
- **The live-model path is opt-in and unused.** `audit` requires an explicit `--model` or `EVIDENCEGATE_MODEL`; there is no silent default. Live tests are skipped unless `OPENAI_API_KEY` and `EVIDENCEGATE_LIVE_MODEL_TESTS=1` are both set. **Zero live-model evaluations have been performed at this checkpoint.**

**Gate 2A design artifacts: draft, pending owner review.** Nothing under `auditors/problem-evidence/gate2a/` is approved, operational, or enforced. Runtime enforcement is disabled and operational comparator use is prohibited.

Nothing here is production-ready, and no part of this repository holds operational authority over anything.

## Layout

```
README.md                    This file
pyproject.toml               Packaging, dependencies, console script
auditors/
  problem-evidence/          The Problem Evidence Auditor
    SPEC.md                  Purpose, policy semantics, open-policy register
    PHASE1.md                Phase 1 runtime implementation specification
    checklist.json           The five requirements and configurable thresholds
    schema/
      evidence-packet.schema.json    Input structure
      audit-finding.schema.json      Output structure
    fixtures/                Synthetic benchmark packets
      strong-evidence.json
      missing-evidence.json
      contradictory-evidence.json
    expected/                Human-approved Phase 0 benchmark results
    eval-policy/             Evaluation policy and Gate 1 draft policy artifacts
      phase1-benchmark-policy.json   Approved benchmark comparison rules
      REVIEW.md                      Review record for that policy
      phase1-behavior-policy.json    Gate 1 draft, human review required
      phase1-behavior-coverage.json  Gate 1 draft, human review required
      model-compatibility-policy.json  Gate 1 draft, acceptance blocked
    gate2a/                  Gate 2A draft design package (pending owner review)
      manifest.json          Explicit package manifest and package digest
      schema/                Contract schemas (Draft 2020-12)
      contracts/             Outcome taxonomy, operator set, lifecycle dimensions
      statements/            Represented frozen statements, obligations, rules
      records/               External authority-record examples (all non-approved)
src/
  evidencegate/problem_evidence/   Phase 1 runtime: CLI, validation, prompt,
                                   transport schema, assembly, model adapter,
                                   comparator, contract loading
tests/
  problem_evidence/          Phase 1 runtime tests (offline, fake adapters)
  gate2a/                    Gate 2A design-package structural validation
docs/
  audits/
    README.md                Audit governance: record requirements, coordinated
                             disclosure, false-pass preservation
    records/                 One record per review, verdicts preserved as issued
```

## Authority

Three artifacts own three different things. Where they disagree, the owner wins.

- **`schema/*.json`** owns structure — fields, types, enums, ID formats.
- **`checklist.json`** owns requirement definitions and configurable thresholds, each with its rationale.
- **`SPEC.md`** owns policy semantics — status meanings, gating, contradiction handling, scope of authority.

Those three own the auditor. **Repository review governance is separate and lives in `docs/audits/README.md`** — what an audit record must contain, the coordinated-disclosure policy, and what a record of a false pass must preserve. It governs how reviews are recorded and disclosed; it confers no authority over auditor structure, requirement definitions, or policy semantics.

## Components

### Problem Evidence Auditor — `auditors/problem-evidence/`

Evaluates five requirements about the problem a team believes exists: target-customer specificity, observed problem behavior, problem frequency, business cost or consequence, and demonstrated customer commitment. Each produces one finding with a status of `pass`, `partial`, `fail`, or `not-testable`.

Product demand, willingness to pay for the proposed product, and pilots of it are out of scope by policy.

## Reading the fixtures

Every record in every fixture carries `"synthetic": true` and `"origin": "synthetic"`. They exist to exercise the auditor's reasoning paths. **A `pass` on a synthetic fixture says the packet's logic holds — nothing more.** No fixture in this repository is real market evidence. References to small commercial cleaning companies are part of a synthetic evaluation scenario; they do not represent an existing product or a validated market conclusion.

## Reading the expected results

Files in `expected/` carry `reviewStatus: "approved"` and `humanReviewed: true`. Human policy review found no unresolved finding-level disagreement, but the files are still **not empirical ground truth** — they were generated by the same process that authored the rubric and the fixtures they are checked against. Approval establishes the accepted Phase 0 policy outcomes; it does not calibrate thresholds or demonstrate real-world validity. `SPEC.md` §18 records what that circularity does and does not permit anyone to conclude.

Each finding retains a null `reviewNote` because review found no unresolved finding-level disagreement. Future disagreement should be recorded per finding rather than hidden by the document-level status.

## What is undecided

`SPEC.md` §17 holds the open-policy register: eight decisions that require human judgment, each with the default currently in force. Nothing important is silently decided.
