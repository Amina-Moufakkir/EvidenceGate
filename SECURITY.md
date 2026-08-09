# Security Policy

EvidenceGate is a pre-release research repository. No part of it is production-ready, and
nothing in it holds operational authority. Phase 1 runtime code is implemented and tested
offline but has not met the acceptance gate in `auditors/problem-evidence/PHASE1.md`. Gate 2A
artifacts are drafts pending owner review. Runtime enforcement is disabled and operational
comparator use is prohibited.

Pre-release does not mean risk-free. The runtime reads an API credential from the environment,
reads and writes local files, depends on third-party packages, and can send supplied packet
content to an external model provider. Those are real surfaces and reports about them are welcome.

## Supported versions

EvidenceGate has no supported production release. There is no released or tagged version, and no
version of this repository is designated for production use.

If you report an issue, please name the commit you examined.

## Reporting a vulnerability

**Please report privately. Do not open a public issue for a suspected vulnerability.**

Use GitHub's private vulnerability reporting for this repository — the **Report a vulnerability**
button under the repository's **Security** tab. That keeps the report private while it is assessed.

Helpful to include, as far as you have it:

- the affected component or file;
- the conditions under which it is reachable;
- the impact you believe it has;
- a reproduction.

**A reproduction is not required.** A clear description of a reachable weakness is a valid report.

## Scope

### In scope

- Exposure of credentials or other secrets, including through error text, generated files, or
  provenance fields.
- Packet or model content causing effects beyond semantic influence on the audit result —
  unintended local or external action, reading or writing files outside the invoked paths,
  or escalation of what the runtime is permitted to do.
- Alteration of runtime-owned metadata by packet or model content. **Runtime-owned review and
  generation metadata is designed to remain outside packet and model control.** A report showing
  that packet or model content can alter it is in scope.
- Integrity failures in the artifacts that gate review: manifest or package-digest binding that
  can be made to accept content it did not cover, or an authority state that can be changed
  without the external record that is supposed to confer it.
- A reachable, exploitable path through a dependency or the supply chain.
- An incorrect audit result that arises from a security-boundary bypass, a malicious-input path,
  an authority escalation, or a comparable integrity failure.

### Known baseline behavior

The behaviors below are documented current limitations of a pre-release system. They are recorded
here so you can tell them apart from the thing we do want to hear about.

**The distinction is impact, not topic.** A report that demonstrates only the baseline behavior
described below is unlikely to change our understanding. A report showing impact beyond that
baseline is in scope, and these topics are explicitly not excluded from the scope list above.

- **Semantic influence through packet text.** The prompt builder places the supplied evidence
  packet directly into the model prompt, so instruction-like text in any free-text packet field
  may influence model-owned semantic output — status, severity, and every prose field. No
  isolation or injection resistance is implemented. This is documented in `SPEC.md`
  (limitation 9) and `auditors/problem-evidence/PHASE1.md`.
  *Beyond the baseline:* packet content that causes secret exposure, unintended local or external
  action, alteration of runtime-owned metadata, or any other trust-boundary violation.

- **Audit results that are semantically wrong.** On their own these are correctness defects, not
  vulnerabilities; please open a normal issue.
  *Beyond the baseline:* a wrong result produced through a security-boundary bypass, a
  malicious-input path, an authority escalation, or a comparable integrity failure.

## Disclosure

Repository review governance, including coordinated-disclosure rules and unresolved timing
parameters, is documented in [`docs/audits/README.md`](docs/audits/README.md).

That document is authoritative for repository review governance. It does not currently establish
a reporter-facing deadline calculable from the date a report is submitted or acknowledged.

## What this file does not do

This file explains how to submit a security report and which issues are in scope. It grants no
approval, no operational authorization, and no formal acceptance of any part of this repository,
and it makes no guarantee that the system is secure.
