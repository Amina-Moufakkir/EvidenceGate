# Audit history

An **append-only governance history** of the reviews that gated each published checkpoint of this repository.

Records are added, never edited to change their conclusion. **An original verdict is never rewritten after the problems it found are corrected.** A `PUBLICATION BLOCKED` verdict stays `PUBLICATION BLOCKED` forever; what changes is that a later record documents how it was resolved, and the index links the two. Rewriting the verdict would destroy the only evidence that the gate ever caught anything.

## What each record must contain

| Field | Meaning |
|---|---|
| Audited state | Exactly what was reviewed — working tree, staged candidate, or published commit |
| Commit | The commit SHA, where one applies; a working-tree candidate has none |
| Package digest | The Gate 2A package digest of the audited state |
| Verdict | The conclusion as originally issued, unmodified |
| Resolution | What happened afterwards, and which record documents it |
| Verification basis | How the conclusions were checked, and what that check could not establish |

## Checkpoint acceptance is not authority

Two different things are recorded here and they must not be read as one.

**An implementation checkpoint** means the owner accepted a body of work as correct enough to publish to a branch. It says the artifacts reconcile, the tests pass, and the documentation does not contradict the data.

**Formal authority** — design-review approval, bridge authority, classification authority, runtime enforcement, operational comparator use, model-compatibility approval, and formal Phase 1 acceptance — is none of that. Those states live in external records under `auditors/problem-evidence/gate2a/records/` and in `contracts/lifecycle-state.json`, they are held outside the reviewed content on purpose, and **no entry in this history has ever granted one**. Publishing a commit changes what is in the repository; it does not change what is authorized.

## Private raw reports

The full audit reports are long working documents held privately outside version control. They are **not committed**. `/docs/audits/raw/` is git-ignored so ordinary Git staging excludes local copies.

Each record therefore identifies its source report by **SHA-256 only**. That is enough to prove a later copy is the same document, without publishing its contents or revealing where it is stored. The records in this directory are sanitized summaries: they carry the governance evidence and omit local paths, environment details, and command logs.

## Index

| Date | Scope | Audited state | Verdict | Package digest | Record | Resolution |
|---|---|---|---|---|---|---|
| 2026-08-08 | Full-project pre-publication audit of the Gate 2A F-1 candidate | Unpublished working tree on `feat/problem-evidence-phase1`, baseline commit `5f55850b9bface5fcb37034e4920800957d6b4e3` | **`PUBLICATION BLOCKED`** (as issued; not amended) | `c25ced6e5e5670dcd6ba93ab8cd188d7e4c0a4d6d25c466b7646e980f247f77a` | [2026-08-08-phase1-f1-pre-publication-audit.md](records/2026-08-08-phase1-f1-pre-publication-audit.md) | Blockers corrected; resolved by the correction-verification record below and published in `feed42d779e0d46bbe3dcdd01b30c13dff460db4` |
| 2026-08-08 | Verification of the corrections that answered the audit above | Corrected candidate, published as commit `feed42d779e0d46bbe3dcdd01b30c13dff460db4` | Corrections verified; accepted for commit and publication | `2ca61669d68ec0ead018df8a34788eed851accefe1b8eeff81f6da4f00797162` | [2026-08-08-phase1-f1-correction-verification.md](records/2026-08-08-phase1-f1-correction-verification.md) | Closes the two blockers from the audit above. **F-1 implementation checkpoint published. Formal Phase 1 acceptance not granted.** |

Read the two rows together. The first row's verdict is the historical fact that publication was blocked. The second row is the historical fact that the blockers were fixed and verified. Neither replaces the other.

## Template for future entries

Add a row to the index and a record under `records/` named `YYYY-MM-DD-<scope-slug>.md`. Keep the record to the evidence; leave the working detail in the private report.

```markdown
# <Scope> — <Date>

- Date:
- Branch:
- Audited state:            # working tree / staged candidate / published commit
- Commit:                   # SHA, or "none — unpublished working tree"
- Package digest:
- Verdict:                  # exactly as issued
- Source report SHA-256:
- Resolution:               # "open", or what closed it and which record documents that

## Findings
<counts by classification, finding IDs, one-line conclusions>

## Verification basis
<what was checked, how, and what the check could not establish>

## Authority states at the time of this record
<design review / bridge / classification / lifecycle / formal acceptance — and confirmation none changed>
```

Rules for a new entry:

1. Never edit an earlier record's verdict, findings, or digests. Add a new record and link it.
2. Quote the package digest in full. Truncated digests prove nothing.
3. State plainly what the verification could **not** establish.
4. Say explicitly whether any authority state changed. In almost every case the answer should be no.
