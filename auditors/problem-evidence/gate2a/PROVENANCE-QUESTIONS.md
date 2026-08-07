# Provenance questions exposed by the Gate 2A-P pilot

**No production provenance schema is defined or frozen here.** This records what the pilot exposed.

## What the pilot exposed

Obligation part `OP-070-c` — *the windows must actually have been fixed before the events were
inspected* — cannot be given a rule. It requires real-world chronology, and the repository has no
source that could establish it.

`OP-006-f` and `OP-070-b` are enforceable **only** because they were narrowed to *declared* ordering:
they test what the submitted structured output represents, not what happened.

## Why the current packet cannot answer it

`schema/evidence-packet.schema.json` exposes `collectedDate`, `collectionMethod`, `proximity`,
`source`, `supersession`, `scope`, and `limitations`. It has **no** field recording when a method,
analysis window, or threshold was *defined* relative to inspection. Searches for `predefin`,
`preregist`, `protocol`, `definedAt`, `methodDate`, `recordedAt`, and `timestamp` return **zero**
occurrences.

`collectedDate` records when evidence was **collected**, not when a window was **chosen**, and it is
self-declared inside the packet — which places it *inside* the trust boundary rather than outside it.

**A populated provenance field is evidence about provenance. It is never proof of trust.**

## Minimum questions any future provenance contract must answer

1. Who recorded this, and are they independent of the party whose behavior is judged?
2. When was it recorded, and by whose clock?
3. In what system, under whose operational control?
4. Can the record be altered after the fact, and is alteration detectable?
5. What remains unprovable even when every field is populated?

## Candidate concepts (unranked, not a schema)

Method-definition timestamp; recorder identity distinct from `source`; mutability class
(append-only vs mutable); integrity reference binding content to a stable record identity; declared
clock authority; event-source configuration identity.

## Two stages, and they must not be collapsed

**Stage 1 — trust establishment (external, human or authority).** Approve and pin: the event source;
the producing system or actor; capture semantics; clock assumptions; mutability or append-only
behavior; evidence identity; integrity controls; configuration identity; known tampering risks;
approved scope of use.

**Stage 2 — deterministic comparison.** Only after Stage 1 may an evaluator compare recorded event
values. A timestamp comparison proves ordering **within the approved evidence model**. It cannot
independently prove that the event really occurred, that the timestamp was honestly generated, that
the source was uncompromised, that the clock was correct, or that no relevant event was omitted.

The evaluator cannot establish its own trust boundary.

## Handling of degraded evidence — never a pass

Absent, incomplete, conflicting, or untrusted provenance all yield `indeterminate`. Never
`obligation_violation`, never `obligation_satisfied`, and never `not_applicable` — absence of
evidence cannot establish non-applicability.

## Open risks

- Whether a **self-authored** evidence packet can carry trustworthy provenance at all is unresolved:
  the recorder and the audited party may be the same, which no field can fix.
- Synthetic fixtures cannot carry real provenance. Generating synthetic provenance and describing it
  as real evidence is prohibited.
- Even an approved source leaves residual risk: administrative backdating, clock skew, and
  same-timestamp events that remain unordered.

## Owner decision required

Whether to pursue a provenance contract at all, given the self-authorship problem above. Until that
is decided, `observedEventPrecedes` stays **unsupported** and dependent obligations stay
**unresolved**.
