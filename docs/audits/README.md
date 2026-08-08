# Audit history

An **append-only governance history** of the reviews that gated each published checkpoint of this repository.

It also carries the standing policy governing those reviews: what a record must contain, when a finding is disclosed, and what a record of a false pass must preserve.

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

## Coordinated disclosure

**The default maximum private-remediation window is 90 days.** A finding may be held privately while it is being remediated, and 90 days is the longest that default holds.

It is a default **maximum**, not a fixed deadline, and it moves in both directions:

- **Extension.** Where circumstances justify additional private-remediation time, the window may be extended past 90 days.
- **Acceleration.** Where circumstances justify disclosure before the window ends, a finding may be disclosed early.

**Whenever the default timeline is extended or accelerated, the justification is preserved** with the finding it applies to, under the same append-only rules as everything else in this directory. A departure from the default stays visible as a departure, and its reason stays readable afterwards.

An extension or acceleration is permitted when circumstances justify it. The reason for departing from the default must be recorded and preserved with the finding. Nothing here converts 90 days into an inflexible deadline.

**Deliberately unspecified.** This policy fixes the window and the accountability that attaches to changing it. It does not name who decides an extension or an acceleration, what event starts the window, who is notified or how, or any list of circumstances that qualify. Those remain undecided, and they are recorded as undecided rather than filled in with a plausible answer — an invented decision-maker or trigger would read as approved policy without ever having been decided.

## False passes

A **false pass** is an audit result that reported success where reality did not support it. It is the most valuable thing this history can hold and the easiest to lose, because once it is corrected the tidy version of events is that the audit worked.

A record of a false pass preserves all five of the following. **A record that omits any one of them does not satisfy this policy**, and the omission is not cured by the other four being thorough.

| Element | What it preserves |
|---|---|
| Incorrect result | The result as originally produced — the passing verdict itself, not paraphrased into a near miss |
| Reality mismatch | What was actually true, and how it contradicts that result |
| Root cause | Why the audit produced a pass — the mechanism, not the category |
| Correction | What was changed to produce the correct result |
| Regression test | The specific test that now fails if the same false pass recurs |

**The historical failure is preserved, not rewritten.** A false-pass record is never revised into an account in which the original audit succeeded, caught the problem, or merely stated it imprecisely. The wrong result stays in the record as it was produced, for the same reason a `PUBLICATION BLOCKED` verdict stays as issued: it is the evidence that this gate can fail, and a history showing no failures is indistinguishable from one that hides them.

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

## Disclosure timing
<omit unless the 90-day default was extended or accelerated; if it was, state which and the justification>

## False pass
<omit unless this record concerns a false pass; if it does, all five elements are required>
- Incorrect result:
- Reality mismatch:
- Root cause:
- Correction:
- Regression test:

## Authority states at the time of this record
<design review / bridge / classification / lifecycle / formal acceptance — and confirmation none changed>
```

Rules for a new entry:

1. Never edit an earlier record's verdict, findings, or digests. Add a new record and link it.
2. Quote the package digest in full. Truncated digests prove nothing.
3. State plainly what the verification could **not** establish.
4. Say explicitly whether any authority state changed. In almost every case the answer should be no.
5. A record of a false pass carries **all five** elements from **False passes** above. Four of five is not a false-pass record, however well written the four are.
6. Where the 90-day default was extended or accelerated, record which it was and the justification for it, in the record for the finding it applies to.
