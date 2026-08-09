# Problem Evidence Auditor — Specification

**Phase 0 contract.** This document, `checklist.json`, `schema/`, `fixtures/` and `expected/` constitute the contract, policies, schemas and benchmark fixtures for the Problem Evidence Auditor. None of them is an operational agent, and none of them executes: this layer is the definition of correct behaviour, written down before anything was built that could quietly redefine it.

A Phase 1 runtime now implements that definition. It lives in `src/evidencegate/problem_evidence/`, is specified in `PHASE1.md`, depends on `jsonschema` and `openai`, and can call a model through an opt-in adapter. It is offline-tested and **not formally accepted**, and zero live-model evaluations have been performed. This document remains authoritative over it: where the runtime and this specification disagree, this specification owns policy semantics and the runtime is the defect.

---

## 1. Purpose

The Problem Evidence Auditor evaluates a **structured product-evidence packet** against a fixed set of requirements about the problem a team believes exists. Its unit of analysis is the pair *(requirement, supplied packet)*.

For each requirement it answers one question: **does what is actually in this packet establish this requirement?** It reports one of four statuses, cites the specific evidence records that drove it, names what is missing in concrete terms, preserves any conflict it found, and proposes one observable action whose outcome could change the finding.

It audits the evidence. It does not audit the product, the market, the team, or the odds.

---

## 2. Authority hierarchy

Three files carry authority over different things. Where they appear to disagree, the owner wins and the disagreement is a defect to be repaired in the non-owning file.

| Artifact | Owns | Does not own |
|---|---|---|
| `schema/*.json` | **Structure.** Field names, types, enums, required fields, ID formats, what a valid packet and a valid finding look like. | What any status means, or when to assign one. |
| `checklist.json` | **Requirement definitions and configurable thresholds.** The five requirements, their questions, their pass/partial/fail/not-testable conditions, accepted and insufficient evidence types, default severities, suggested verification tests, and every tunable number with its documented rationale. | Status semantics, gating rules, scope of authority. |
| `SPEC.md` (this file) | **Policy semantics.** What the statuses mean, how the three checks combine, how contradiction is handled, what the auditor may and may not conclude, what remains undecided. | Field structure, per-requirement condition text, threshold values. |

A number that can be tuned lives in `checklist.json` with its rationale. A rule about meaning lives here.

---

## 3. Responsibilities

The auditor must:

1. Evaluate each of the five requirements independently and emit **exactly one finding per requirement**, always, however empty the packet.
2. Distinguish **definition quality** (is the claim specific and testable?) from **evidence strength** (do the records support it?) from **contradiction** (do records conflict with it?), and report all three.
3. Cite supplied evidence by `evidenceId` for every conclusion, or state explicitly that evidence is absent.
4. Keep supporting, conflicting, and non-contributing records in **separate structured roles**, never merged or netted off.
5. Name missing evidence as **concrete, obtainable artifacts**, not as abstractions.
6. Propose a verification test that names an **observable outcome**, including what result would falsify the claim.
7. Assess **provenance limitations recorded inside the packet** — recall bias, leading questions, self-selection, single-site coverage, unknown segment fit — because these are properties of the supplied records.
8. Flag findings that require human judgment, and flag situations the rubric does not cover.

---

## 4. Non-responsibilities

The auditor must not:

1. Produce a product-success score, a roll-up, or any aggregate across requirements. There is no total.
2. Judge whether the product will succeed, whether the market is attractive, or whether the team should proceed.
3. Evaluate **product demand** — pilots of the proposed product, willingness to pay for it, or interest in it. Out of scope by policy (§13, Policy 10).
4. Supply world knowledge. If the packet does not contain it, the auditor does not know it.
5. Invent customer facts, interview results, market evidence, causal explanations, or certainty.
6. Infer causation from correlation, sequence, or a participant's opinion.
7. Extract claims from prose. Claims are supplied packet input.
8. Judge the **evidence-collection strategy** — whether the team researched the right things, in the right order, with the right method. That is outside its authority. The boundary is in §5.
9. Treat synthetic evidence as real market evidence, under any circumstances.

### 4.1 The provenance boundary

These are easily confused and the distinction matters:

**Inside authority** — assessing what the supplied records are: this interview was recruited from a self-selected group; this question supplied its own answer; this export covers eight weeks; this source's segment fit is unknown; this loss log records no buyer reason. These are facts about the packet, and reading them is the job.

**Outside authority** — judging the research programme: the team should have run a survey first; three interviews was the wrong number to plan for; this segment was a poor choice; the team should have talked to buyers instead of owners. These are recommendations about how to do research, and the auditor has no basis for them.

The line: the auditor may say *"this record cannot answer this question, and here is the artifact that could."* It may not say *"you researched this badly."*

---

## 5. Inputs and outputs

**Input** — one evidence packet conforming to `schema/evidence-packet.schema.json`. Three collections are kept strictly separate and must not be merged:

- `claims[]` — the propositions to be audited, supplied by the team.
- `evidence[]` — raw records only: what was observed, measured, quoted, or contained in an artifact.
- `interpretations[]` — human readings of the evidence. The auditor may *report* an interpretation, and must never *cite* one as support for a status.

**Output** — one result document conforming to `schema/audit-finding.schema.json`: exactly five findings, in requirement order, plus a mandatory synthetic-evidence notice whenever any record has `origin: "synthetic"`.

The finding fields are the agreed `AuditFinding` interface. Contract extensions are `claimIds`, `nonContributingEvidence`, `subAssessments`, `offSegmentSignal`, `blockingReasons`, `policyGap`, and `reviewNote`. Finding documents use schema version `2.0.0`; the required `nonContributingEvidence` role is a breaking addition to the earlier output contract. There is **no numeric confidence**, because nothing has been defined or calibrated that such a number would mean.

---

## 6. The three checks

### 6.1 Definition-quality check

Operates on the **claim text**. Asks: is this claim specific, scoped and falsifiable? Could a stated observation contradict it?

Fails when the claim is vague ("way too long"), unbounded, tautological, or self-sealing — as when the segment definition includes the problem being tested, so no company can be both in-segment and problem-free.

### 6.2 Evidence-strength check

Operates on the **evidence records**. Asks: do these records establish the claim at its stated scope?

Fails when records are absent, off-target, unsuitable in kind, below the configured source minimum, or too narrow in coverage for the claim's scope.

### 6.3 Contradiction check

Operates across both. Asks: does any record **conflict with** the claim, as opposed to merely failing to support it?

This is not a weaker form of the other two. A packet can have excellent evidence and a contradiction; a packet can have no evidence and no contradiction at all.

### 6.4 How they combine — the definition gate

**A failed definition check gates the overall requirement status to `not-testable`.** Evidence cannot be measured against a claim that no observation could contradict.

The evidence assessment is still run and **preserved in `subAssessments.evidenceAssessment` with `gatedByDefinitionFailure: true`**, so supplied evidence is never hidden by a gate. The reader sees both that the claim needs rewriting and what material exists.

A deterministic definition failure **does not** set `requiresHumanDecision` (§13, Policy 6).

### 6.5 Two derived rules

Neither was in the original policy set; both follow from it and are recorded here because they change outcomes.

**Segment attribution.** When REQ-1's definition check fails, the segment has no boundaries, so no record can be attributed to it. Every other requirement then faces an evidence-suitability problem: records from sources whose `segmentFit` is `unknown` cannot be assigned to a population that does not exist. This contributes to `not-testable` **through the evidence path, not through the definition gate** — REQ-2's own claim may be perfectly well defined. The two routes to `not-testable` must not be conflated in the rationale.

**Segment-fit contribution.** A record whose `segmentFit` is `partial` may contribute to `partial`, but cannot independently produce `pass` or independently falsify a claim about the full segment. If every otherwise relevant record is partial-fit, the status ceiling is `partial`. `requiresHumanDecision` is true when the partial fit materially affects interpretation. A record whose fit is `out-of-segment` can neither support nor falsify a segment-scoped claim; it is preserved in `offSegmentSignal` and excluded from both evidence lists. Applying exclusion in only one direction would allow no-fit data to fail a claim it cannot address — the mirror image of the error Policy 9 prevents.

---

## 7. Status semantics

| Status | Means | Does not mean |
|---|---|---|
| `pass` | Supplied evidence satisfies the documented requirement at the claim's stated scope. | The claim is true in the world; the product will work; no further work is needed. |
| `partial` | Relevant evidence exists but is limited, weak, mixed, or does not cover the full requirement. | Roughly half true. It is a statement about coverage and conflict, not a midpoint. |
| `fail` | Supplied evidence demonstrates this requirement is not met, or directly falsifies the claim at its defined scope and threshold. | The product idea is invalid. One requirement failed. |
| `not-testable` | The packet lacks enough suitable evidence to evaluate the requirement, or the claim is not falsifiable as written. | The claim is false. Absence is not refutation. |

**`missing evidence ≠ contradictory evidence`** is the single most important boundary in this spec. `not-testable` and `fail` must never be substituted for each other. A finding that records missing evidence must leave `contradictoryEvidenceIds` empty unless a genuine conflict exists independently.

**Non-contributing evidence remains visible without changing either side of the finding.** Each record in `nonContributingEvidence` is classified as `unsuitable` or `non-qualifying`, has an `unresolved` or `not-applicable` relationship to the requirement, uses the schema's closed reason-code catalog, and includes a rationale. Its `evidenceId` appears in neither support nor contradiction lists and never affects their source counts. The required array is present even when empty so omission cannot silently impersonate assessment.

**Severity** expresses the **consequence of leaving this gap unresolved**. It takes `none` on passing findings. It is not a measure of how badly the requirement failed and not a priority ranking across requirements.

**`requiresHumanDecision`** is set for credible contradictions, policy gaps, and borderline interpretations. It is deliberately *not* set for deterministic outcomes — a definition failure, a source count below the configured minimum, or a supersession that follows the stated rule — so that the flag keeps meaning something.

**`missingEvidence` on a `pass`** records a residual limitation, not a defect in the finding. Every non-`pass` finding must name at least one concrete missing artifact.

---

## 8. What qualifies as evidence

Evidence is a **record of something that happened**: an artifact the work produced, a measurement, an observation, or an account of a specific occurrence.

The following are recorded in the packet but are **not evidence for any status**. Evidence records of these kinds are placed in `nonContributingEvidence` when they bear on the finding; interpretations remain in their separate packet collection and are never cited as evidence:

- **Internal assertions.** The team's own belief, written in a brief. Writing a belief down does not convert it into an observation.
- **Interpretations.** Held in a separate collection by design. May be reported; never cited as support.
- **Stated intent and hypothetical willingness to pay.** These record what someone said they might do. They may never support REQ-5, which asks what has already been spent.
- **Secondary sources without methodology.** An assertion in an article or on a vendor's page is not an observation of any company.

Synthetic records are evidence for **fixture** packets only (§13, Policy 2).

---

## 9. Evidence model — five axes, not one ranking

There is **no universal linear ranking of evidence**. A payment record is decisive for commitment and irrelevant to frequency; a time log is the reverse. A single ordering would force one of those judgments to be wrong.

Records are described by five independent axes, all recorded in the packet, all reported separately:

**Category** — what kind of thing the record is: `instrumented-record`, `business-artifact`, `resource-commitment-record`, `direct-observation`, `anchored-self-report`, `generalized-self-report`, `stated-intent`, `secondary-source`, `internal-assertion`. A category is a description, not a grade.

**Proximity** — how far the record sits from the behaviour it describes: `generated-by-the-behavior` → `observed-directly` → `recalled-specific` → `recalled-general` → `hypothetical` → `secondary` → `asserted`. This axis *is* ordered, and it is the only one that is.

**Requirement-fit** — whether the record addresses this requirement's question at all: direct, indirect, or not relevant. **Checked before proximity.** A flawless instrumented time log has zero fit for the commitment requirement. `declaredRelevance` in the packet is an author's pointer; the auditor derives its own fit and must not defer to it.

**Independence and scope** — how many genuinely independent sources (shared `sourceId` or a referral chain means not independent), how they were recruited, whether they fall inside the segment, what period is covered, and whether the researcher's question was leading.

**Origin** — `field` or `synthetic`. Governs whether the record may contribute toward `pass` at all.

### 9.1 How the axes combine

1. **Fit first.** No fit, no contribution, whatever the record's quality.
2. **Then proximity**, relative to what the claim asserts. A claim about duration needs a record that measured duration.
3. **Then scope**, against the claim's scope (§10). Corroboration cannot establish a distribution however good the records are.
4. **Origin caps** everything (§13, Policy 2).
5. **Category and limitations** shape the rationale — they explain *why* a record sits where it does.

### 9.2 Explicit supersession

Evidence is superseded only when the packet explicitly declares the relationship in the newer record's `supersession[]` entry and every condition holds: the newer evidence explicitly corrects, replaces or invalidates the older evidence; both address the same subject, measure, scope and applicable timeframe; the newer record has equal or stronger provenance; and it directly falsifies the claim at its defined threshold.

Source identity, timestamps, category or proximity never imply supersession. If any condition is absent or false, both records remain in the assessment. Credible conflict then produces `partial` with `requiresHumanDecision: true` under §11. A valid explicit supersession is deterministic and does not alone set `requiresHumanDecision`; the displaced record is preserved in `nonContributingEvidence` with the `explicitly-superseded` reason code and the relationship is described in the rationale and contradiction sub-assessment.

---

## 10. Claim scope and sufficiency

Every claim declares a `claimScope`, and scope determines what would be sufficient. The values and their configured minimums live in `checklist.json`.

| Scope | Asserts | Sufficient when |
|---|---|---|
| `definition` | The claim itself is decidable | The boundaries can be applied to a named case without further clarification |
| `instance` | The behaviour occurred | One credibly recorded occurrence from an in-segment source |
| `recurrence` | It recurs for an individual | The configured minimum of independent in-segment sources, each covering at least the claim's stated period |
| `narrow-pattern` | It holds across some in-segment sources | The configured minimum of independent in-segment sources, directly relevant |
| `prevalence` / `segment-wide` | A distribution over the population | A documented sampling frame **and** timeframe coverage. Corroborating individual records are never sufficient — the ceiling without a sampling frame is `partial`. |

**One interview may support an individual observation but cannot establish a general market pattern.** That rule is enforced structurally by this table, not as a special case.

---

## 11. Rules for conflicting evidence

1. **Conflict is preserved, never averaged.** Two records measuring 41 minutes and 185 minutes do not become "about two hours". Both appear, both are described, and the disagreement is the finding.
2. **`fail` requires direct falsification** at the claim's defined scope and threshold. Credible mixed evidence produces `partial` with `requiresHumanDecision: true`.
3. **Conflict types are named** in `subAssessments.contradictionAssessment.conflictType`: `measurement-vs-self-report`, `cross-source-disagreement`, `behavior-vs-stated-intent`, `direct-negation`.
4. **A record may conflict with itself**, and the conflict is preserved rather than resolved — a five-week subscription that was paid for and then cancelled is both prior expenditure and withdrawn commitment.
5. **Off-segment records never contradict** (§6.5).
6. **Absence never contradicts.** A missing record goes in `missingEvidence` and nowhere else.

---

## 12. Rules against unsupported conclusions

1. Every conclusion cites `evidenceId`s or states explicitly that evidence is absent.
2. No causation from correlation, co-occurrence, sequence, or opinion. A loss log showing late proposals that were lost establishes co-occurrence; the buyer's own dated statement establishes the link. Where only co-occurrence exists, the rationale must say so.
3. A participant's stated reason is **their statement about their reasoning**, which is the strongest form of stated reason available and still not an observed cause.
4. No numeric confidence, no probability, no score.
5. No extrapolation past the claim's declared scope, even when the records are strong.
6. Interpretations flagged `causal-claim`, `prediction` or `speculation` are, by construction, unsupported unless separately evidenced. Where the packet contains one bearing on a finding, the auditor names it and says what would be needed to support it.
7. **A `fail` on one requirement says nothing about the other four**, and nothing about the product.

---

## 13. Policy decisions of record

Ten policies were decided by the project owner and are binding. Recorded here so that later changes are visible as changes.

1. **Definition gate.** A failed definition check gates the requirement to `not-testable`; the evidence assessment is preserved as a structured sub-assessment. (§6.4)
2. **Synthetic evidence.** Fixture packets may produce `pass`. `packetPurpose` is `fixture` or `audit`; each record carries `origin`. In an `audit` packet, synthetic evidence cannot contribute toward `pass`. (§9)
3. **Two independent, directly relevant sources** is the configurable provisional minimum for narrow qualitative pattern claims. Not sufficient for quantitative prevalence or segment-wide claims without adequate scope and timeframe coverage. (§10)
4. **`fail` requires counterevidence that directly falsifies** the claim at its defined scope and threshold. Credible mixed evidence produces `partial` with `requiresHumanDecision: true`. (§11)
5. **Severity is the consequence of an unresolved gap**, and takes `none` on passing findings. (§7)
6. **`requiresHumanDecision`** is for credible contradictions, policy gaps and borderline interpretations. A deterministic definition failure alone does not set it. (§7)
7. **REQ-5 measures demonstrated commitment to the existing problem** — prior spending, sustained workaround behaviour, staff allocation, or another documented use of a scarce resource. Stated intent, hypothetical willingness to pay, and commitment to the proposed product do not count.
8. **REQ-2 is instance-scoped.** One credibly observed instance establishes that the behaviour exists. REQ-3 separately evaluates frequency and recurrence.
9. **Good off-segment evidence produces `not-testable`** for the stated segment, with the off-segment signal preserved explicitly. (§6.5)
10. **Problem evidence only.** Product demand, pilots of the proposed product, and willingness to pay for it are out of scope. (§4)
11. **Partial segment fit is bounded.** Partial-fit evidence may contribute only up to `partial`, cannot independently pass or falsify a full-segment claim, and materially interpretive partial fit requires human decision. (§6.5)
12. **Claim/requirement mismatch is a deterministic block.** Emit `not-testable` with a structured blocking reason and direct the user to restate or replace the claim. The mismatch alone is not a policy gap or human judgment call. (§17, OPEN-07)
13. **Visible non-contributing evidence has its own role.** Unsuitable, non-qualifying, or explicitly superseded evidence that bears on a finding is preserved in `nonContributingEvidence`, never coerced into support or contradiction, and never counted toward either side. The three evidence roles are pairwise disjoint.

---

## 14. The five requirements

Full conditions, accepted and insufficient evidence types, default severities and suggested tests are in `checklist.json`. Summary:

| ID | Name | Check type | Asks | Default severity |
|---|---|---|---|---|
| REQ-1 | Target-customer specificity | definition-quality | Could a given company be sorted in or out of the segment without further discussion? | high |
| REQ-2 | Evidence of observed problem behavior | evidence-strength | Is there a record of the behaviour actually occurring? (instance-scoped) | high |
| REQ-3 | Evidence of problem frequency | evidence-strength | How often does it recur, over a period long enough to see the claimed rate? | high |
| REQ-4 | Evidence of business cost or consequence | evidence-strength | What consequence did the problem produce, documented rather than inferred? | medium |
| REQ-5 | Evidence of meaningful customer commitment | composite | What scarce resource has already been spent on the **existing problem**? | medium |

---

## 15. Version 2 finding-schema definition of done

Phase 0 is complete when all of the following hold. Items 1–7 are verifiable mechanically; 8 is not, and is the gate that matters.

1. `SPEC.md`, `checklist.json`, both schemas, three fixtures and three expected-result files exist at the paths above.
2. Every fixture validates against `schema/evidence-packet.schema.json`.
3. Every expected-result file validates against `schema/audit-finding.schema.json`.
4. Every fixture produces **exactly five** findings, one per requirement, in requirement order.
5. Every `evidenceId` referenced in any expected file **exists in that file's fixture**; `evidenceIds`, `contradictoryEvidenceIds`, and `nonContributingEvidence` are pairwise disjoint; and each non-contributing evidence ID appears at most once per finding.
6. Every non-`pass` finding names at least one concrete missing artifact and an observable verification test; the `missing-evidence` fixture produces no contradiction claims anywhere.
7. Every record in every fixture carries `"synthetic": true` and `"origin": "synthetic"`, and every expected file carries the synthetic-evidence notice. **Before owner approval** each expected file carries `reviewStatus: "provisional"` and `humanReviewed: false` — that is the pre-approval condition, and it is also the state the Phase 1 runtime injects into every document it generates, which may never claim approval it does not have.
8. **The project owner has reviewed and approved all expected results.** Approval moves the files out of the item 7 pre-approval condition: each now carries `reviewStatus: "approved"` and `humanReviewed: true`, which is their current state. `reviewNote` remains null because no unresolved finding-level disagreement remains. This approval accepts the Phase 0 policy outcomes and does not empirically calibrate thresholds. The legitimate open-policy questions below remain open.

Explicitly **not** in v1: any runtime, any model call, any generated TypeScript types, numeric confidence, cross-requirement aggregation, and any packet built from real evidence.

---

## 16. Known limitations

1. **Everything here is untested against reality.** Three synthetic packets, authored alongside the rubric that reads them, are an internal consistency check.
2. **Thresholds are reasoned, not calibrated.** The two-source minimum is an argument about corroboration, not a result from data.
3. **The auditor cannot detect a fabricated packet.** It reads what it is given. A packet that describes interviews that never happened audits identically to one that describes interviews that did.
4. **Requirement independence is imposed.** REQ-3 and REQ-5 clearly interact in the contradictory fixture — owners declined to spend because volume was low. The output structure records that connection only in prose.
5. **Only five requirements.** A packet can pass all five and describe a problem nobody will pay to solve, which is a different auditor's job.
6. **No handling of packet evolution.** Re-auditing after new evidence arrives, and what happens to a finding that was `not-testable` and is now `fail`, is undesigned.
7. **`limitations` is author-supplied.** A packet whose author does not record a leading question hides it from the auditor. The auditor can read a limitation; it cannot detect an unrecorded one.
8. **Synthetic fixtures contain only failure modes their author anticipated.** Real packets will contain confusions not represented here.
9. **Untrusted packet text can influence the model's semantic judgments.** The Phase 1 runtime places the supplied packet directly into the model prompt, so instruction-like text written into a claim, an evidence description, a recorded limitation or an interpretation may steer model-owned fields — `status`, `severity`, `requiresHumanDecision`, and every prose field. This is prompt injection, and it is distinct from limitation 3: fabrication misleads by content, injection subverts by control. **No mitigation for it is implemented.** Structural validation does not detect it, because a status is a semantic judgment and no structural check can distinguish an injected verdict from an honest one. What structural validation does prevent is a generated document claiming review it does not have: `reviewStatus`, `humanReviewed`, `reviewedBy`, `reviewedDate` and `reviewNote` are runtime-owned, injected after the model returns, and re-validated before the document is written.

---

## 17. Open-policy register

Unresolved decisions requiring human judgment. Each names a default that is currently in force, so nothing is silently decided.

**OPEN-01 — Does REQ-1's failure cascade explicitly?**
Currently REQ-1's definition failure reaches other requirements only through segment attribution (§6.5), and each requirement is assessed on its own claim. An alternative is an explicit cascade flag. *Default in force: no explicit cascade; attribution handled per requirement.*

**OPEN-02 — Should `partial` be subdivided?**
`partial` currently covers three different situations: below the source minimum, credible conflict, and coverage narrower than the claim. These lead to very different next actions. *Default in force: one `partial`, distinguished in `subAssessments`.*

**OPEN-03 — Is two independent sources the right minimum?**
It is an argument about corroboration, not a calibrated number. It may be too low for `narrow-pattern` claims and is certainly not meaningful for prevalence. *Default in force: 2, configurable in `checklist.json`.*

**OPEN-04 — Explicit supersession. RESOLVED.**
Supersession is deterministic only when the newer record explicitly declares that it corrects, replaces or invalidates the older record and every condition in §9.2 is satisfied. It is never inferred from source identity or chronology. *Approved rule in force: explicit qualifying supersession only.* The contradictory fixture deliberately does not supersede its period-free self-report and therefore preserves the conflict.

**OPEN-05 — Severity when a requirement is `not-testable`.**
Currently the requirement's `defaultSeverity` is emitted, meaning the consequence of not knowing. An alternative is to treat unknown consequence as unknown severity (`null`). *Default in force: `defaultSeverity`.*

**OPEN-06 — Partial segment fit. RESOLVED.**
Partial-fit evidence may contribute to `partial`; it cannot independently produce `pass` or independently falsify a full-segment claim. When all relevant evidence is partial-fit, the status ceiling is `partial`. Material interpretive dependence sets `requiresHumanDecision: true`. No-fit evidence can neither support nor contradict. *Approved rule in force: bounded partial contribution.* The strong fixture exercises this in REQ-4.

**OPEN-07 — Claim/requirement mismatch. RESOLVED.**
When a supplied claim addresses a different requirement or falls outside this auditor's scope, the result is `not-testable` with a structured `blockingReasons` value such as `claim-requirement-mismatch` or `claim-out-of-scope`. The recommendation must restate or replace the claim rather than request more evidence for the mismatched claim. A deterministic mismatch alone does not set `requiresHumanDecision`. `policyGap` remains null unless a genuinely uncovered case exists. *Approved rule in force: structured deterministic blocking reason.*

**OPEN-08 — Who authors expected results going forward?**
For Phase 0, the same process authored the rubric, the fixtures and the expected results (§18). *Default in force: single author, `reviewStatus: provisional` until reviewed.*

---

## 18. Circular validation

The rubric, the fixtures and the expected results in this directory were produced by one process. Agreement among them demonstrates internal consistency and nothing else. This section exists so that fact is recorded next to the artifacts rather than discovered later.

**Live risks:**

1. **Fixture-to-rubric leakage.** The fixtures were written by the author of the conditions that read them. Mitigation applied: evidence content is written in practitioner voice — buyer emails, timesheets, cancellation notes — and avoids the rubric's vocabulary. Partially effective at best.
2. **Answer keys hardening into ground truth.** Mitigation applied: explicit review state, a `reviewNote` field per finding, item 8 of the definition of done, and the statement that human benchmark approval is not empirical calibration. **The metric worth tracking is the reviewer's disagreement rate with these expectations, not the auditor's agreement rate with them.**
3. **Overfitting to three fixtures.** `checklist.json` conditions were written before the fixtures; later edits to it should be treated as spec changes and noted.
4. **Ambiguity laundering.** Anything the author had to decide while writing appears in §17 rather than being silently resolved. Two derived rules that emerged during construction are called out in §6.5 rather than buried.
5. **Synthetic realism bias.** The fixtures contain the failure modes their author knows about. Real packets will contain others.
6. **Correlated blind spots.** A model executing this rubric later shares the priors of the model that wrote it. A self-audit will not surface them.

**What would actually reduce this:** one fixture authored by someone other than the rubric's author; one packet built from real evidence, held out entirely; and an adversarial fixture designed specifically to make the rubric produce a confidently wrong answer.

**The honest claim at the end of Phase 0** is: *the rubric is internally consistent and produces its intended statuses on three cases its own author designed.* Nothing beyond that has been shown.
