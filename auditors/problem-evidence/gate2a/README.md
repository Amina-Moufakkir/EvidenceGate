# Gate 2A — Contract, Representative Pilot, and Gate 2A-F batch F-1 (draft)

**Status: draft design artifacts awaiting owner review.** Nothing here is approved, operational, or
enforced. Creating or correcting these files did not approve them.

Gate 2A-P defines the contracts by which the 87 frozen v15 boundary statements can later be
decomposed into reviewable obligations and rules, and proved those contracts against a
seven-statement pilot. Gate 2A-F applies them to the remaining statements in authorized batches.
**13 of the 87 frozen statements are represented; 74 remain.** **Neither Gate 2A-P completion nor
batch F-1 is Gate 2A completion.** Gate 2A-F is in progress: batch F-1 added six statements
(SS-004, SS-009, SS-010, SS-027, SS-028, SS-039). Batches F-2 onward are not authorized and have
not been started.

## Layout

```
gate2a/
  manifest.json  explicit package manifest and package digest
  schema/        contract schemas (Draft 2020-12)
  contracts/     outcome taxonomy, operator set, lifecycle dimensions
  statements/    the 13 represented statements (7 pilot + 6 from batch F-1)
  records/       three external authority-record examples, all non-approved:
                 design-review (pending-owner-review), bridge-authority (not-granted),
                 classification-authority (not-approved)
```

## Three kinds of obligation — the central distinction

Earlier drafts conflated what the frozen source requires with what an evaluator needs and with what
this repository happens to make observable. Every obligation part now carries a `derivationBasis`:

| Basis | Meaning | Counts as source-derived coverage? |
|---|---|---|
| `source_obligation` | required by the frozen statement text | **yes** |
| `evaluation_precondition` | input the evaluator needs; not a source requirement | **no** |
| `evaluation_proxy` | an observable stand-in for a source obligation the repository cannot observe directly | **no** |

### Result vocabulary is fixed by derivation basis

| Basis | `resultClass` | Permitted results |
|---|---|---|
| `source_obligation` | `normative` | `obligation_satisfied`, `obligation_violation`, `indeterminate`, `evaluator_error` — plus `condition_not_met` when the rule declares an antecedent |
| `evaluation_proxy` | `proxy` | `proxy_condition_met`, `proxy_condition_not_met`, `indeterminate`, `evaluator_error` |
| `evaluation_precondition` | `precondition` | `precondition_available`, `precondition_unavailable`, `evaluator_error` |

**A proxy can no more prove satisfaction than violation.** Without granted bridge authority a proxy
establishes only that its own proxy condition held — never that the source obligation passed or
failed. Proxy and precondition results are never obligation compliance, never product findings, and
never source-derived coverage.

**Bridge authority is not stored here.** Rules carry `bridgeAuthorityRequired: true` and a reference
to an external record; any grant lives in `records/bridge-authority-record.example.json`, which is
digest-bound and currently `not-granted`.

Worked cases: declaring an EV-004 validation step is a **proxy** for actually validating EV-004;
declared plan order is a **proxy** for real chronology, whose source obligation `OP-070-c` — sourced
to the exact phrase *"before inspecting events"* — remains a **normative source obligation** with an
**unresolved** disposition, unsupported until trustworthy chronology is externally approved.

`SS-026` shows the other shape. `OP-026-a` is genuinely normative and carries an explicit
`evidenceContract`: it remains source-derived **only if** it evaluates a complete, approved inventory
of every candidate REQ-5 input using trusted classifications. Missing, incomplete, or untrusted
classification yields `indeterminate`. If that contract is abandoned the rule becomes a proxy and
source-derived executable-rule coverage drops from 18 to 17. No approved classification exists today,
so the rule currently returns `indeterminate`.

Five further source obligations depend on exactly the same inventory-and-classification structure, so
each now carries a structured `evidenceContract` rather than describing one in prose. The complete
contract-bearing set is `OP-004-a`, `OP-009-a`, `OP-026-a`, `OP-027-a`, `OP-028-a` and `OP-039-a`,
each scoped to its own statement: REQ-1 inputs and screening-sheet identification, supersession
inputs and justification-basis classification, REQ-5 inputs and willingness-to-pay classification,
REQ-5 inputs and proposed-product-demand classification, commitment records and
withdrawn-or-declined classification, and REQ-2 evidence-treatment inputs and absence-basis
classification. Every one of them requires a complete inventory and a trusted classification, yields
`indeterminate` rather than satisfied when either is missing, and names the same external
classification-authority record. Each remains a source obligation; only a nonconforming
implementation reading an incomplete or self-declared classification would be a proxy. `OP-010-a`
deliberately carries **no** contract: the frozen statement supplies EV-015's out-of-segment status
directly, so that obligation depends on no inventory and no classification.

### `SS-026` and `SS-027` — owner-selected D2, intentional and explicit

`SS-026` (*"Do not substitute willingness to pay for the proposed product"*) and `SS-027` (*"Do not
use demand for a proposed product as evidence of existing-problem commitment"*) are separate frozen
statements whose enforceable invariants normalize to the same product-demand boundary. The owner
selected **D2**: two distinct source obligations, each with its own obligation part, its own atomic
rule and its own traceability path. Neither statement is folded into the other, so neither can
disappear from the 87-statement accounting and statement-level coverage stays independently
traceable.

The redundancy is deliberate and is recorded rather than hidden. Scope is preserved in both
directions: `OP-026-a` stays scoped to willingness to pay, `OP-027-a` is scoped to proposed-product
demand — of which willingness to pay is one species — and neither is widened or narrowed to match
the other. D1 (one shared rule) and D3 (one obligation citing two statements) remain unselected;
D3 is not representable under the current schema in any case. `SS-056`, `SS-085` and `SS-087` belong
to the same product-demand family, are **not** classified by this decision, and remain
unrepresented.

`SS-070` carries **two** distinct source obligations, because a declared workflow step is only a proxy
for either fact: `OP-070-d` — the windows must genuinely be defined — and `OP-070-c` — that definition
must precede inspection. Both are `source_obligation` with `unresolved` dispositions. `OP-070-a` and
`OP-070-b` are their respective proxies.

## Decomposition model

```
frozen source statement  →  source-statement record  →  obligation parts  →  atomic rules
        (87, frozen)              (SS-###)                 (OP-###-x)          (BR-...)
```

Obligation parts are inventoried **before** any rule. Each rule maps to exactly one **primary**
obligation part; supporting parts require explicit justification. `composite` is not a valid rule
classification.

| Coverage disposition | Meaning |
|---|---|
| `rule-covered` | an atomic rule exists |
| `human-review-obligation` | inherently requires human judgment; no fictional rule is invented, and it is **not** unresolved |
| `unresolved` | a normative term or authority is missing; no reliable rule can be defined yet |

## Accounting

**13 of 87** frozen statements represented; **74 remain**. 13 statements → **46 obligation parts**
→ **33 atomic rules**, 4 human-review obligations, 9 unresolved parts. Reconciliation:
`33 + 4 + 9 = 46`. `scope` is `expansion-in-progress`, and no full-set rule total is asserted.

**Implication direction follows the frozen verb, not a house style.** *"Fail **requires** the
configured counterevidence-source minimum and no comparably credible qualifying commitment"* runs from
the recorded result to the evidence: `fail ⇒ both conjuncts`. *"credible evidence on both sides
**yields** partial"* runs the other way: `credible on both sides ⇒ partial`. Reading either against its
own verb inverts the obligation, so each conditional rule records its antecedent explicitly.

By derivation: **27** source obligations · **11** evaluation preconditions · **8** evaluation proxies.
Rules: **18** source-derived (the only rules permitted to emit normative outcomes) · **7** precondition
· **8** proxy.

**Source-obligation coverage — the two numbers are different:**

| Measure | Value |
|---|---|
| Source obligations represented by executable rules | **18** |
| Source obligations with a human-required disposition | **0** |
| Source obligations with an unresolved disposition | **9** |
| **Total source obligations** | **27** |

18 is *executable-rule* coverage, not total source-obligation coverage.

**Decomposition and coverage are governed independently.** `decompositionStatus` records whether every
identified normative obligation is *represented* by a part. Coverage records whether a represented
obligation has an approved *enforcement mechanism*. A statement can be fully decomposed and still carry
unresolved obligations — three do. All 13 are `fully_decomposed`; 9 parts remain `unresolved`. Neither
implies the other and the counts are never summed.

Every record carries `decompositionAssurance: "unconfirmed-pending-owner-review"`, because no validator
can establish semantic completeness. Classification: 7 deterministic, 4 composite, 1 model-assisted,
1 unresolved.

No full-set rule-count estimate is made, and none may be extrapolated from this pilot.

## Finding capability — three distinct measures

| Measure | Value |
|---|---|
| Total rule designs | **33** |
| Normative rule designs capable of producing a product finding | **18** |
| Diagnostic-only rule designs (8 proxy + 7 precondition) | **15** |
| Rule definitions governed by the review policy | **33** |
| Currently implemented evaluators | **0** |
| Actual generated findings | **0** |
| Outputs qualifying as findings | only normative outcomes from the 18 normative rules |

Describing all 33 rules as "producing findings" would be wrong: 15 structurally cannot, and none can
today because no evaluator is implemented and no finding has been generated.

**Deferred remediation DR-1.** Gate 1 `phase1-behavior-coverage.json` expresses the review policy per
*source statement*, while findings are produced per *rule*. That mismatch is documented in
`statements/coverage-report.json` and deferred to pre-Gate 2B remediation. **No Gate 1 artifact was
modified in this pass.**

## Evaluator maturity — stated separately, never merged

| Level | Count / 33 |
|---|---|
| Evaluator mechanism defined | 33 |
| Evaluator implemented | **0** |
| Behaviour executed in tests | **0** |
| Live-model evaluation performed | **0** |
| Reliability evidence established | **0** |

## SS-006 — six source obligations, six proxies, one human judgment

The frozen statement's operative verb is *validate*, so each validation is a source obligation in its
own right; a declared step is only a proxy for it.

| Source obligation (unresolved) | Proxy (rule-covered) | Clause |
|---|---|---|
| `OP-006-h` provenance actually validated | `OP-006-a` | *"First validate EV-004's provenance"* |
| `OP-006-i` measurement boundaries actually validated | `OP-006-b` | *"complete active-assembly measurement boundaries"* |
| `OP-006-j` segment fit actually validated | `OP-006-c` | *"segment fit"* |
| `OP-006-k` threshold actually validated | `OP-006-d` | *"threshold"* |
| `OP-006-l` supersession status actually validated | `OP-006-e` | *"and supersession status"* |
| `OP-006-m` validations actually performed before establishing existence | `OP-006-f` | *"First validate"* + *"if it remains credible, it establishes instance-scoped existence"* |

`OP-006-g` (credibility) has derivation basis `evaluation_precondition` and coverage state
`human-review-obligation`. No additional rule is created merely to represent an unresolved source
obligation.

## Source-clause fidelity, and its limits

Every source-obligation and proxy clause is a **verbatim substring** of its frozen statement — no
paraphrase, no ellipsis. Only `evaluation_precondition` parts carry no source clause. A test enforces
this.

**A verbatim-substring check cannot establish semantic fidelity.** It cannot detect an obligation that
omits a qualification, broadens the source, skips an intermediate consequence, or misses the
statement's ultimate conclusion. Four such defects were found by owner review, not by any test, and
corrected: SS-006's conditional conclusion, SS-060's intermediate consequence, SS-033's broadened
scope, and SS-055's and SS-070's dropped qualifications. Semantic completeness remains **X-8**, an
owner-review invariant.

## Predicates, preconditions, and evaluation method

Three modelling devices keep obligations from multiplying incorrectly:

- **Qualifying predicates** narrow *which inputs count* toward one obligation. SS-055's pass criterion
  is a single conjunction — independent, in-segment, qualifying commitment, existing problem. A source
  failing any predicate is **excluded from the qualifying count**; its presence is never itself a
  violation. The only normative violation is `PASS_QUALIFYING_COUNT_BELOW_MINIMUM`; the four predicate
  codes are **diagnostic exclusion reasons**. With a minimum of three: three qualifying plus two
  out-of-segment sources → `obligation_satisfied`; two qualifying plus one out-of-segment →
  `obligation_violation`; incomplete inventory or untrusted classification → `indeterminate`.
- **Evaluation preconditions** supply evidence the evaluator needs. SS-033's obligation is the
  *property* (a non-decidable adjectival term must not serve as a boundary); the decidability
  classification is evidence, and missing or untrusted classification yields `indeterminate`.
- **Human input** is an evaluation *method*, not a new obligation. SS-055's two-sided partial requires
  credible evidence on both sides; it does not require that credibility be judged in any particular
  order. Absent determinations make the rule indeterminate.

## No vacuous satisfaction

When a conditional rule's antecedent is false, the result is **`condition_not_met`**, never
`obligation_satisfied`. It is a **diagnostic activation result**, not a normative conclusion: the
taxonomy keeps it in `diagnosticActivationResults`, outside the `normativeOutcomes` enum. A false condition means the consequence was never activated — not that the
obligation was fulfilled. `condition_not_met` carries `countsAsObligationCompliance: false`, so it can
never inflate compliance totals, and it is distinct from `indeterminate`, which means the antecedent
could not be evaluated at all. Five rules declare antecedents: `BR-006-credible-establishes-existence`,
`BR-055-fail-criterion`, `BR-055-partial-on-two-sided-credible`,
`BR-060-underspecified-boundary-recorded`, and `BR-060-material-disagreement-downgrades`.

## Fixture evidence

**There are zero rule fixtures.** `ruleFixtures` is empty on every rule.
`intendedEvidencePacketAssociation` names Gate 0 evidence packets, which carry no rule-outcome
evidence; it records an intended future association and is **not** fixture coverage.

## Two human-review axes are separate

- **4** parts require human judgment, and **none of them is a source obligation**. All four —
  `OP-006-g`, `OP-055-f`, `OP-055-m` and `OP-060-a` — are **evaluation preconditions** with human
  dispositions: the frozen text states conditions — *"if it remains credible"*, *"and no comparably
  credible qualifying commitment within this packet"*, *"credible evidence on both sides"*,
  *"any material classification disagreement"* — not commands to perform judgments. Source
  obligations with a human-required disposition: **0**.
- **33** rule definitions are governed by the review policy.
- **18** rule designs can actually produce a reviewable product finding.

Three different measures. None explains another, and they are never combined.

## What a validator run does and does not establish

Deterministic validation establishes **structural** properties only: ID uniqueness, reference
validity, cardinality, schema conformance, declared coverage disposition, absence of orphans,
reconciliation of recorded totals, required-field presence, allowed enum values, digest correctness.

It **cannot** establish that every semantic obligation in the source prose was identified, that two
obligation parts are genuinely independent, that an obligation was not subtly omitted, that a rule
preserves the statement's complete meaning, or that a human-required classification is substantively
correct. That is invariant **X-8** and requires owner review.

**A successful schema or validator run is not semantic proof.**

## Approval state lives outside the artifact

Design artifacts carry no `reviewStatus`, `humanReviewed`, or `designApproved` field. Review state
lives in `records/`, referencing `manifest.json` and its package digest. The review record is
excluded from that digest, so updating a review never mutates the reviewed content; any substantive
change produces a new digest and requires a new review record.

`manifest.json` lists all **22** included files with per-file digests and documents each exclusion.
Included: **12** `schema/`, **3** `contracts/`, **5** `statements/`, and **2** Markdown documents. Excluded
and documented: `manifest.json` itself (self-reference), `records/design-review-record.example.json`,
`records/bridge-authority-record.example.json`, and
`records/classification-authority-record.example.json` (authority state must sit outside reviewed
content), and `tests/gate2a/` (outside the package).

Package file inventory: **22 digest members + 3 excluded records + 1 excluded manifest = 26 files
under `gate2a/`**, plus **1 test module** outside it — **27 files in the reviewed Gate 2A scope**.

## Lifecycle dimensions

| Dimension | Current state | Changeable by Gate 2A-P |
|---|---|---|
| Design review | `pending-owner-review` | no |
| Operational comparator use | `prohibited` | no |
| Runtime enforcement | `disabled` | no (Gate 2B) |
| Model compatibility | `unresolved-offline` | no (Gate 2C) |
| Formal Phase 1 acceptance | not a repository state at all | no — requires detached authority |

## Ordering

`declaredStepPrecedes` is usable in design and proves only what the submitted output represents.
`observedEventPrecedes` is **unsupported**: no approved, independently produced, tamper-evident event
source exists. See `PROVENANCE-QUESTIONS.md`. A model's declared step order is never observed
chronology.

## `not_applicable`

Currently unreachable by every pilot rule: it may be assigned only when an approved applicability
predicate evaluates false, and every rule carries `predicateApproved: false`. It is retained so that
evidence absence can never be routed to it — absence yields `indeterminate`.

## Deferred, and not done here

`blockingReasons` always-present remains the approved **target** contract. A-2 did not implement
that separate remediation: no `blockingReasons` requirement or instance value changed, no related
benchmark or hash was regenerated, and no producer or consumer was modified for it.

## Versioning policy

Draft contract versioning policy: until the contract
reaches 1.0, `contractVersion` uses `0.MINOR.PATCH-draft`. Increment MINOR for any substantive
change to the accepted contract, including adding or removing required properties or changing an
allowed-value set. Increment PATCH only for a correction that leaves the set of accepted instances
unchanged. Repository paths, prose, digests, and authority-state bindings alone do not change
`contractVersion`. `ruleVersion` is independent and changes only when the atomic-rule data contract
or rule semantics change.
