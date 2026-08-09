# Phase 1 — F-1 full-project pre-publication audit — 2026-08-08

- Date: 2026-08-08
- Branch: `feat/problem-evidence-phase1`
- Audited state: unpublished F-1 working-tree candidate (11 modified files, all unstaged)
- Baseline commit: `5f55850b9bface5fcb37034e4920800957d6b4e3`
- Commit: none — the audited state was never committed in this form
- Package digest audited: `c25ced6e5e5670dcd6ba93ab8cd188d7e4c0a4d6d25c466b7646e980f247f77a`
- **Verdict as issued: `PUBLICATION BLOCKED`**
- Source report SHA-256: `29d651edce8ce5731ecd94c22778b2200caab9bca32799bcfa7e4b4af82fed26`
- Resolution: blockers corrected; verified in [2026-08-08-phase1-f1-correction-verification.md](2026-08-08-phase1-f1-correction-verification.md); published as `feed42d779e0d46bbe3dcdd01b30c13dff460db4`

**This verdict has not been amended.** It is preserved as issued. Publication *was* blocked at the time of this audit, and the record of that is the point of keeping it.

## Scope

Read-only inspection of the whole project — intent, architecture, schemas, data contracts, authority boundaries, tests, packaging and publication readiness — against the accepted F-1 working-tree candidate rather than against the published commit alone. No file was modified during the audit.

## Findings

| Classification | Count | IDs |
|---|---|---|
| `BLOCKER` | 2 | F-1, F-2 |
| `PRE-PUBLICATION CORRECTION` | 2 | F-3, F-4 |
| `DEFERRED HARDENING` | 4 | F-6, F-7, F-8, F-9 |
| `COSMETIC` | 1 | F-5 |
| `NOT A FINDING` — investigated, confirmed correct | 9 | C-1 … C-9 |

### Blockers

**F-1 — `BLOCKER`.** The root `README.md` and `SPEC.md` stated the project had no runtime, no model calls, no dependencies and no application code. All four clauses were false: a Phase 1 runtime existed, with two declared dependencies, a console-script entry point and an OpenAI Responses adapter. The layout section omitted several whole directory trees. The front page understated the project's own network-calling surface.

**F-2 — `BLOCKER`.** Inside `auditors/problem-evidence/gate2a/README.md` — a digest-bound manifest member — one bullet block asserted 22 governed rule definitions where the same document's table and `coverage-report.json` said 33; 12 finding-capable designs where they said 18; one source obligation with a human-required disposition where both said zero; and it referenced `OP-055-h`, an obligation part that does not exist. Two of these were introduced by the F-1 work itself, which updated the table and left the bullet behind.

### Pre-publication corrections

**F-3.** `SPEC.md` definition-of-done items 7 and 8 required mutually exclusive review-metadata values for the same three files, so no artifact could satisfy both.

**F-4.** The same Gate 2A README stated that four rules declare antecedents; five do. `BR-055-fail-criterion` was omitted from an enumeration whose purpose is completeness.

### Cosmetic

**F-5.** The Gate 2A README layout block named one authority record where three exist.

### Deferred hardening

**F-6.** The one artifact whose approval actually gates comparator enforcement carries that approval in-band and self-attested, rather than in a detached digest-bound record as Gate 2A requires of its own artifacts.

**F-7.** Untrusted packet content is concatenated into the model prompt with no isolation, and the threat was undocumented. Structural validation cannot detect an injected semantic verdict; it does prevent a generated document claiming human approval.

**F-8.** "Must never conclude satisfaction while prerequisites are unresolved" is declared in a data `limitations` string, not enforced by schema or test. Inert while no evaluator is implemented.

**F-9.** The known Gate 1 coverage-schema cardinality observation, re-verified: the schema pins `statementCounts` to constants without constraining the nested arrays. Independently recounted — 87 declared, 87 present — so the published artifact is truthful. Deferred and embargoed under a standing owner ruling; **not** treated as invalidating Gate 1.

### Investigated and confirmed correct

C-1 supporting obligations do not silently replace primary source obligations · C-2 no proxy is represented as proof of its source obligation · C-3 the six non-null evidence contracts are justified and `OP-010-a` correctly has none · C-4 13 represented / 74 remaining is truthful · C-5 46 obligation parts and 33 rules reconcile, identity I5 holds · C-6 `SS-026` and `SS-027` remain correctly separated under owner decision D2 · C-7 `indeterminate`, failure, unsupported and approval states are used consistently · C-8 no circular dependency or circular proof · C-9 no secrets in tracked files or reachable history.

## The central conclusion

**The machine-readable layer reconciled completely. Both publication blockers were documentation defects.**

Every artifact digest matched, the package digest recomputed to its declared value, referential closure held with no dangling reference, the counts reconciled independently, and all authority states were correctly held outside the reviewed content. Nothing in the data was wrong. What blocked publication was prose that contradicted the data — including prose inside a digest-bound member of the package.

## Verification basis

Read-only inspection of all 71 tracked files at the audited state: documentation, schemas, statement artifacts, authority records, packaging, and the Phase 1 runtime source. Digests were recomputed independently from source bytes rather than by invoking the package's own tests. Counts were re-derived from the JSON. Referential closure was checked exhaustively across statements, obligation parts, rules and traceability edges. The full test suite and both collection commands were run. A credential-pattern scan covered all tracked files and all reachable commits and returned nothing.

**What this could not establish.** Deterministic validation establishes structural properties only. It cannot establish that every semantic obligation in the frozen source prose was identified, that obligation parts are genuinely independent, that a rule preserves its statement's complete meaning, or that a human-required classification is substantively correct. That is invariant X-8 and requires owner review. A passing suite is not semantic proof.

## Authority states at the time of this audit

Design review `pending-owner-review` · bridge authority `not-granted` · classification authority `not-approved` · runtime enforcement `disabled` · operational comparator use `prohibited` · model compatibility `unresolved-offline` · formal Phase 1 acceptance not represented as a repository state.

**No authority state was changed by this audit**, which was read-only throughout.

## Known incompleteness of this audit

F-2 as originally issued captured the stale totals, source-obligation count, and nonexistent identifier described above. A further defect with the same documentation-drift root cause was found later, while strengthening the regression test: the same Gate 2A README also described `OP-006-g` as a `source_obligation`, where the artifact records `evaluation_precondition` with a `human-review-obligation` coverage state. It would have been reported under F-2 had it been caught here. It is recorded in the correction-verification record. This audit was therefore incomplete on its own terms, and that is preserved rather than quietly folded into the original finding.
