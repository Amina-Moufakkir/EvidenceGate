# Phase 1 — F-1 correction verification — 2026-08-08

- Date: 2026-08-08
- Branch: `feat/problem-evidence-phase1`
- Audited state: the corrected F-1 candidate, verified unstaged and then published
- Commit: `feed42d779e0d46bbe3dcdd01b30c13dff460db4`
- Package digest: `2ca61669d68ec0ead018df8a34788eed851accefe1b8eeff81f6da4f00797162`
- Verdict: corrections verified against the artifacts; accepted for commit and publication
- Source report SHA-256: `d4b6e250b5d02b98a0eb4be7d4b1213dd48eb77f2e30667dbe683928afdadd77`
- Resolves: [2026-08-08-phase1-f1-pre-publication-audit.md](2026-08-08-phase1-f1-pre-publication-audit.md)

**Scope note on the source report.** The report hashed above documents the correction pass as it stood at package digest `b9fb48e2…`. One further correction followed it. That correction, its digest, and its verification are documented in this record.

## What this record does and does not mean

**F-1 implementation checkpoint published.** A body of work was accepted as correct enough to publish to a branch: the artifacts reconcile, the tests pass, and the documentation no longer contradicts the data.

**Formal Phase 1 acceptance was not granted.** It is a distinct decision and it has not been made. `contracts/lifecycle-state.json` continues to record formal Phase 1 acceptance as not a repository state at all — it requires detached external authority and cannot be conferred by a repository boolean, a committed approval file, design approval, operational permission, runtime activation, diagnostic hashes, fixture passes, or model-evaluation results. Nothing in this record changes that.

## Correction sequence and superseded digests

| Stage | Package digest | Status |
|---|---|---|
| Baseline at commit `5f55850b9bface5fcb37034e4920800957d6b4e3` | `2b7d8238afbc3266a2b4fa20774209cf00dae60b943d90633166c5b73c95549c` | superseded |
| F-1 candidate accepted at internal review checkpoint | `c25ced6e5e5670dcd6ba93ab8cd188d7e4c0a4d6d25c466b7646e980f247f77a` | superseded — the state the pre-publication audit blocked |
| After the pre-publication correction pass | `b9fb48e288995e33670adbfed9ac7a3f19f6f698da48d400cddcd61c794dedfb` | superseded — the state the source report documents |
| After the final `OP-006-g` documentation correction | `2ca61669d68ec0ead018df8a34788eed851accefe1b8eeff81f6da4f00797162` | **final — published** |

The transition from the baseline commit to the audited F-1 candidate was the substantive F-1 implementation and changed multiple manifest members. Each of the two later correction transitions — from `c25ced6e5e5670dcd6ba93ab8cd188d7e4c0a4d6d25c466b7646e980f247f77a` to `b9fb48e288995e33670adbfed9ac7a3f19f6f698da48d400cddcd61c794dedfb`, and from that digest to `2ca61669d68ec0ead018df8a34788eed851accefe1b8eeff81f6da4f00797162` — changed exactly one of the 22 manifest members: `auditors/problem-evidence/gate2a/README.md`. After each correction, only the digest fields in all three authority records were rebound. Neither correction altered an obligation part, atomic behavior rule, traceability edge, coverage figure, schema, `contractVersion`, or `ruleVersion`.

## How each audit finding was answered

**F-1 — closed.** The root `README.md` now distinguishes the completed Phase 0 contract, the implemented but not formally accepted Phase 1 runtime, the opt-in and unused live-model path, and the draft Gate 2A design artifacts. The layout section now names the previously omitted trees. `SPEC.md` rescoped its no-execution claim to the Phase 0 contract layer and names the runtime it governs. Neither file is a Gate 2A manifest member, so neither affected any digest.

**F-2 — closed, in two passes.** The defects originally captured under F-2 were corrected: 22 → 33 governed rule definitions, 12 → 18 finding-capable designs, "only one is a source obligation" → none of the four, and the nonexistent `OP-055-h` replaced with `OP-055-m`. A further defect with the same root cause, not caught by the original audit, was found while strengthening the regression test: the same document described `OP-006-g` as a `source_obligation`, where the artifact records `evaluation_precondition` with a `human-review-obligation` coverage state. It was corrected to name both authoritative fields, producing the final published digest.

**F-3 — closed.** `SPEC.md` definition-of-done item 7 now scopes provisional review metadata to the pre-approval condition; item 8 states the current approved state. The two are no longer mutually exclusive.

**F-4 — closed.** "Four rules declare antecedents" corrected to five, with `BR-055-fail-criterion` added.

**F-5 — closed.** The layout block now names all three authority-record examples with their non-approved states.

**F-7 — documentation half addressed; the finding remains deferred.** `SPEC.md` and `PHASE1.md` now disclose prompt injection as an unmitigated limitation, state that structural validation cannot detect it, and record that the runtime-owned metadata boundary is unaffected. No isolation or injection resistance is claimed, and none was implemented. The prompt builder and its version identifier were not changed.

**F-6, F-8, F-9 — deferred, untouched**, along with dependency pinning and F-2 batch work.

## Regression protection added

One test node was added to the Gate 2A suite and then strengthened twice, rather than accumulating separate tests:

`tests/gate2a/test_gate2a_contracts.py::test_gate2a_readme_prose_matches_the_derived_artifact_totals`

It derives every expected value from the JSON artifacts and checks the Gate 2A README against them, never the reverse. It rejects any obligation-part or rule identifier named in that README which does not exist in the artifacts; it isolates the human-judgment bullet and requires its declared count, its listed identifier set, and its stated source-obligation count to match the derived values exactly, so an identifier appearing elsewhere in the document cannot satisfy it; and it requires the `OP-006-g` sentence to name both authoritative fields with the artifact's values.

Each assertion was falsified against in-memory mutations of the README text and the parts data. No mutated artifact was written to disk. During that exercise two mutations initially reported a false pass because the mutation strings did not match the file's actual line wrapping; both were re-targeted and re-run, and both then failed as intended. That is recorded here rather than omitted.

## Verification basis

All digests were recomputed independently from source bytes rather than by invoking the package's own tests.

- **All 22 manifest members** independently matched their declared digests.
- **Package digest** recomputed to `2ca61669d68ec0ead018df8a34788eed851accefe1b8eeff81f6da4f00797162`, matching the manifest.
- **All three authority records** bind to that digest.
- **Gate 2A collection: 197.** **Repository-wide collection: 243.**
- **Final tests: `242 passed, 1 skipped`.**
- **The skip remained the explicit opt-in live-model test**, gated on both `OPENAI_API_KEY` and `EVIDENCEGATE_LIVE_MODEL_TESTS=1`. No xfail, no additional skip, no live model was invoked at any point.
- The staged inventory was verified as exactly the 14 intended files before committing; the working tree was clean afterwards; the push was a fast-forward with no amend and no force.

**GitHub CI is not configured for this repository.** There is no workflow directory, no registered status context and no check run on the published commit. The combined-status API reports `pending` with a total of zero, which is its default for a commit with no contexts — not a queued job. **All verification was local.**

**What this could not establish.** The same limit as the audit it resolves: structural verification is not semantic proof. It cannot establish that the decomposition is semantically complete, that obligation parts are genuinely independent, or that a human-required classification is substantively correct. Invariant X-8 still requires owner review. Automated agreement among artifacts authored together demonstrates internal consistency and nothing more.

## Authority states after publication

| Dimension | State | Changed? |
|---|---|---|
| Design review | `pending-owner-review` | no |
| Bridge authority | `not-granted` | no |
| Classification authority | `not-approved` | no |
| Runtime enforcement | `disabled` | no |
| Operational comparator use | `prohibited` | no |
| Model compatibility | `unresolved-offline` | no |
| Formal Phase 1 acceptance | not a repository state | no — not granted |

`contractVersion` remains `0.14.0-draft`; `ruleVersion` remains `0.13.0-draft`. Every non-digest field in all three authority records was preserved, including the previously accepted classification scope naming all six contract-bearing obligation parts.

**PR #1 remained open and draft** throughout. Its description and metadata were not modified, it was not marked ready, and it was not merged.
