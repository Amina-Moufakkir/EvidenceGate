"""Offline structural validation for the Gate 2A-P draft design package.

These tests establish STRUCTURAL conformance only. They cannot establish that the source prose was
completely or correctly decomposed, that obligation parts are genuinely independent, or that a
human-required classification is substantively correct. Those questions are invariant X-8 and
require owner review.

No live model call, no network access, no external mutation.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "auditors/problem-evidence/gate2a"
POLICY = ROOT / "auditors/problem-evidence/eval-policy/phase1-benchmark-policy.json"

PAIRS = [
    ("statements/source-statement-records.json", "schema/source-statement-record.schema.json"),
    ("statements/obligation-parts.json", "schema/obligation-part.schema.json"),
    ("statements/atomic-behavior-rules.json", "schema/atomic-behavior-rule.schema.json"),
    ("statements/traceability-map.json", "schema/traceability-map.schema.json"),
    ("statements/coverage-report.json", "schema/coverage-report.schema.json"),
    ("contracts/outcome-taxonomy.json", "schema/outcome-taxonomy.schema.json"),
    ("contracts/operator-set.json", "schema/operator-set.schema.json"),
    ("contracts/lifecycle-state.json", "schema/lifecycle-state.schema.json"),
    ("records/design-review-record.json", "schema/design-review-record.schema.json"),
    ("records/lifecycle-state-record.json", "schema/lifecycle-state-record.schema.json"),
    ("records/design-review-record.example.json", "schema/design-review-record.schema.json"),
    ("records/bridge-authority-record.example.json", "schema/bridge-authority-record.schema.json"),
    ("records/classification-authority-record.example.json",
     "schema/classification-authority-record.schema.json"),
    ("manifest.json", "schema/package-manifest.schema.json"),
]
# Exclusion from the package digest is not exclusion from validation: every excluded record above is
# schema-validated here and subject to the cross-record integrity rules at the end of this module.
EXCLUSION_PATHS = (
    "auditors/problem-evidence/gate2a/manifest.json",
    "auditors/problem-evidence/gate2a/records/design-review-record.json",
    "auditors/problem-evidence/gate2a/records/lifecycle-state-record.json",
    "auditors/problem-evidence/gate2a/records/design-review-record.example.json",
    "auditors/problem-evidence/gate2a/records/bridge-authority-record.example.json",
    "auditors/problem-evidence/gate2a/records/classification-authority-record.example.json",
    "tests/gate2a/test_gate2a_contracts.py",
)
EXCLUDED_RECORD_RELS = (
    "records/design-review-record.json",
    "records/lifecycle-state-record.json",
    "records/design-review-record.example.json",
    "records/bridge-authority-record.example.json",
    "records/classification-authority-record.example.json",
)
CONTRACT_VERSION = "0.15.0-draft"
PACKAGE_VERSION = "0.3.0-draft"

# The owner decision recorded in this branch. The artifact itself is private and lives outside the
# repository; only its SHA-256 is ever committed, so a later copy can be proven identical without
# publishing its contents.
APPROVAL_TIMESTAMP = "2026-08-09T03:08:24Z"
APPROVAL_ARTIFACT_SHA256 = "92af4c29fbaa604d8baa9a5605133521e1acc005902ff11d8908696ec1d55da3"
APPROVED_REVIEWER_REPRESENTATION = (
    "Repository owner — represented in this record; authorization evidenced separately by a "
    "private approval artifact SHA-256.")
APPROVED_SCOPE_OF_DECISION = (
    "Owner approval of the Gate 2A semantic design for the bound package digest. Invariant X-8 "
    "received owner review. Findings F-6 through F-9 remain deferred. This decision grants no "
    "authority beyond the approved semantic design.")
PENDING_SCOPE_OF_DECISION = (
    "No owner review has occurred. This record binds the candidate package digest under review "
    "and asserts no approval.")
APPROVED_EVIDENCE_STATEMENT = (
    "The repository owner approved the exact bound Gate 2A semantic-design package digest. "
    "Authorization evidence is the SHA-256 of a separately preserved private approval artifact.")
MUTABLE_STATE_KEYS = ("currentState", "designApproved", "humanReviewOccurred", "reviewStatus",
                      "humanReviewed", "reviewedBy", "reviewedDate")
ALLOWED_RESULTS = {
    "normative": {"obligation_satisfied", "obligation_violation", "indeterminate", "evaluator_error"},
    "normative_conditional": {"obligation_satisfied", "obligation_violation", "condition_not_met",
                              "indeterminate", "evaluator_error"},
    "proxy": {"proxy_condition_met", "proxy_condition_not_met", "indeterminate", "evaluator_error"},
    "precondition": {"precondition_available", "precondition_unavailable", "evaluator_error"},
}
RESULT_CLASS = {"source_obligation": "normative", "evaluation_proxy": "proxy",
                "evaluation_precondition": "precondition"}
MANIFEST_DIRS = ("schema", "contracts", "statements")
MANIFEST_DOCS = ("PROVENANCE-QUESTIONS.md", "README.md")

FROZEN_STATEMENT_TOTAL = 87
PILOT_N = 7
SCOPE_BEARING = (
    "statements/source-statement-records.json",
    "statements/obligation-parts.json",
    "statements/atomic-behavior-rules.json",
    "statements/coverage-report.json",
)


def expected_scope_for(n: int) -> str:
    """Total over the legal range of N, so the mapping is biconditional by construction."""
    if n == PILOT_N:
        return "pilot-subset"
    if n == FROZEN_STATEMENT_TOTAL:
        return "full-set-87"
    return "expansion-in-progress"


def scope_and_count_violations(package: dict) -> list[str]:
    """Pure deterministic validator. Returns stable violation codes, never raises.

    `package` maps each SCOPE_BEARING relative path to its in-memory payload. Both positive and
    negative tests call this, so the derivation of N lives in exactly one place.
    """
    codes: list[str] = []
    records = package["statements/source-statement-records.json"]["records"]
    ids = [r["sourceStatementId"] for r in records]
    unique = set(ids)
    n = len(unique)

    if len(ids) != len(unique):
        codes.append("DUPLICATE_SOURCE_STATEMENT_ID")
    if not (PILOT_N <= n <= FROZEN_STATEMENT_TOTAL):
        codes.append("N_OUT_OF_RANGE")

    totals = package["statements/coverage-report.json"]["statementTotals"]
    if totals["selected"] != n:
        codes.append("SELECTED_NOT_DERIVED_N")
    if totals["recordsCreated"] != n:
        codes.append("RECORDS_CREATED_NOT_DERIVED_N")
    if totals["statementsRemaining"] != FROZEN_STATEMENT_TOTAL - n:
        codes.append("REMAINING_NOT_DERIVED_N")
    if totals["recordsCreated"] + totals["statementsRemaining"] != FROZEN_STATEMENT_TOTAL:
        codes.append("COUNTS_DO_NOT_SUM_TO_87")

    scopes = {rel: package[rel]["scope"] for rel in SCOPE_BEARING}
    if len(set(scopes.values())) != 1:
        codes.append("SCOPE_DISAGREEMENT")
    else:
        actual = next(iter(scopes.values()))
        if actual != expected_scope_for(n):
            codes.append("SCOPE_DOES_NOT_MATCH_N")

    known = {r["sourceStatementId"] for r in records}
    if any(p["sourceStatementId"] not in known
           for p in package["statements/obligation-parts.json"]["parts"]):
        codes.append("ORPHAN_OBLIGATION_PART_STATEMENT")
    trace = package.get("statements/traceability-map.json")
    if trace and any(e["sourceStatementId"] not in known for e in trace["edges"]):
        codes.append("ORPHAN_TRACEABILITY_STATEMENT")
    return codes


def load_package() -> dict:
    rels = SCOPE_BEARING + ("statements/traceability-map.json",)
    return {rel: load(rel) for rel in rels}


def load(rel: str) -> dict:
    return json.loads((GATE / rel).read_text())


def walk_keys(node: object):
    """Yield every object key reachable in a JSON document, at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk_keys(item)


def compute_member_digests() -> dict[str, str]:
    files: dict[str, str] = {}
    for subdirectory in MANIFEST_DIRS:
        for path in sorted((GATE / subdirectory).glob("*.json")):
            files[f"auditors/problem-evidence/gate2a/{subdirectory}/{path.name}"] = \
                hashlib.sha256(path.read_bytes()).hexdigest()
    for document in sorted(MANIFEST_DOCS):
        files[f"auditors/problem-evidence/gate2a/{document}"] = \
            hashlib.sha256((GATE / document).read_bytes()).hexdigest()
    return files


def compute_package_digest(files: dict[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def parts() -> list[dict]:
    return load("statements/obligation-parts.json")["parts"]


@pytest.fixture(scope="module")
def rules() -> list[dict]:
    return load("statements/atomic-behavior-rules.json")["rules"]


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return load("statements/source-statement-records.json")["records"]


# --------------------------------------------------------------------- schema conformance
@pytest.mark.parametrize("schema_rel", sorted({s for _, s in PAIRS}))
def test_schema_meta_validates_against_draft_2020_12(schema_rel: str) -> None:
    schema = load(schema_rel)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("instance_rel,schema_rel", PAIRS)
def test_instance_validates_against_declared_schema(instance_rel: str, schema_rel: str) -> None:
    validator = Draft202012Validator(load(schema_rel), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(load(instance_rel)), key=lambda e: list(e.path))
    assert not errors, [f"{list(e.path)}: {e.message}" for e in errors[:5]]


@pytest.mark.parametrize("schema_rel", sorted({s for _, s in PAIRS}))
def test_every_object_location_is_closed(schema_rel: str) -> None:
    """Every object DEFINITION must be closed.

    `if` / `then` / `else` subschemas are constraint overlays on an object defined elsewhere, not
    definitions of their own. Setting `additionalProperties: false` inside one would forbid every
    property the overlay does not itself restate, which is the opposite of what closure means.
    Closure for those objects is enforced at the enclosing definition, which this walk still
    checks. `test_conditional_branches_sit_inside_a_closed_object` proves that enclosure holds.
    """
    open_locations: list[str] = []

    def walk(node: object, path: str, in_overlay: bool = False) -> None:
        if not isinstance(node, dict):
            return
        is_object = node.get("type") == "object" or "properties" in node
        closed = node.get("additionalProperties")
        if is_object and not in_overlay and closed is not False and not isinstance(closed, dict):
            open_locations.append(path)
        for keyword in ("properties", "$defs", "patternProperties"):
            for name, child in (node.get(keyword) or {}).items():
                walk(child, f"{path}/{keyword}/{name}", in_overlay)
        for keyword in ("items", "not", "contains", "propertyNames"):
            walk(node.get(keyword), f"{path}/{keyword}", in_overlay)
        for keyword in ("if", "then", "else"):
            walk(node.get(keyword), f"{path}/{keyword}", True)
        for keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
            for index, child in enumerate(node.get(keyword) or []):
                walk(child, f"{path}/{keyword}/{index}", in_overlay)

    walk(load(schema_rel), "#")
    assert not open_locations, open_locations


def test_conditional_branches_sit_inside_a_closed_object() -> None:
    """A schema that uses if/then overlays must close the object those overlays constrain."""
    checked = []
    for schema_rel in sorted({s for _, s in PAIRS}):
        schema = load(schema_rel)
        if not any(isinstance(branch, dict) and ("if" in branch or "then" in branch)
                   for branch in schema.get("allOf", []) or []):
            continue
        checked.append(schema_rel)
        assert schema.get("type") == "object", schema_rel
        assert schema.get("additionalProperties") is False, schema_rel
    assert checked, "expected at least one schema to use conditional branches"


# --------------------------------------------------------------------- frozen source fidelity
def test_source_statements_match_the_frozen_policy_verbatim(records: list[dict]) -> None:
    policy = json.loads(POLICY.read_text())
    ordered: list[tuple[str, str, str, str]] = []
    for fixture_name in ("contradictory-evidence.json", "missing-evidence.json", "strong-evidence.json"):
        block = next(f for f in policy["fixtures"] if f["fixture"] == fixture_name)
        for requirement in block["requirements"]:
            for text in requirement["requiredVerificationBehavior"]:
                ordered.append((fixture_name, requirement["requirementId"],
                                "requiredVerificationBehavior", text))
            for text in requirement["prohibitedSubstitutions"]:
                ordered.append((fixture_name, requirement["requirementId"],
                                "prohibitedSubstitution", text))

    assert len(ordered) == 87, "the frozen boundary must remain exactly 87 statements"

    for record in records:
        fixture, requirement_id, statement_type, text = ordered[record["v15Index"] - 1]
        assert record["sourceStatementId"] == f"SS-{record['v15Index']:03d}"
        assert (record["fixture"], record["requirementId"], record["statementType"]) == (
            fixture, requirement_id, statement_type)
        assert record["statementText"] == text
        expected = hashlib.sha256(json.dumps(
            {"fixture": fixture, "requirementId": requirement_id,
             "statementType": statement_type, "statement": text},
            sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
        assert record["statementDigest"] == expected


def test_committed_package_satisfies_every_scope_and_count_invariant() -> None:
    """Replaces test_gate_2a_f_was_not_started: derived, so it stays valid before and after F-1."""
    assert scope_and_count_violations(load_package()) == []


def test_no_duplicate_source_statement_records(records: list[dict]) -> None:
    ids = [r["sourceStatementId"] for r in records]
    assert len(ids) == len(set(ids)) == len(records)


def test_declared_counts_match_derived_n(records: list[dict]) -> None:
    n = len({r["sourceStatementId"] for r in records})
    totals = load("statements/coverage-report.json")["statementTotals"]
    assert totals["selected"] == n
    assert totals["recordsCreated"] == n
    assert totals["statementsRemaining"] == FROZEN_STATEMENT_TOTAL - n


def test_represented_plus_remaining_is_eighty_seven() -> None:
    totals = load("statements/coverage-report.json")["statementTotals"]
    assert totals["recordsCreated"] + totals["statementsRemaining"] == FROZEN_STATEMENT_TOTAL


def test_scope_value_matches_derived_statement_count(records: list[dict]) -> None:
    n = len({r["sourceStatementId"] for r in records})
    assert load("statements/coverage-report.json")["scope"] == expected_scope_for(n)


def test_all_scope_bearing_instances_agree() -> None:
    assert len({load(rel)["scope"] for rel in SCOPE_BEARING}) == 1


def test_every_referenced_statement_exists(parts, records) -> None:
    known = {r["sourceStatementId"] for r in records}
    assert {p["sourceStatementId"] for p in parts} <= known
    assert {e["sourceStatementId"] for e in load("statements/traceability-map.json")["edges"]} <= known


def test_scope_enum_is_closed() -> None:
    allowed = {"pilot-subset", "expansion-in-progress", "full-set-87"}
    for rel, schema_rel in (
        ("statements/source-statement-records.json", "schema/source-statement-record.schema.json"),
        ("statements/obligation-parts.json", "schema/obligation-part.schema.json"),
        ("statements/atomic-behavior-rules.json", "schema/atomic-behavior-rule.schema.json"),
        ("statements/coverage-report.json", "schema/coverage-report.schema.json"),
    ):
        assert set(load(schema_rel)["properties"]["scope"]["enum"]) == allowed
        assert load(rel)["scope"] in allowed


def _with_n(package: dict, n: int) -> dict:
    """Grow or shrink the record population to exactly n unique IDs."""
    pkg = copy.deepcopy(package)
    records = pkg["statements/source-statement-records.json"]["records"]
    template = records[0]
    while len(records) < n:
        clone = copy.deepcopy(template)
        clone["sourceStatementId"] = f"SS-{900 + len(records):03d}"
        records.append(clone)
    del records[n:]
    known = {r["sourceStatementId"] for r in records}
    pkg["statements/obligation-parts.json"]["parts"] = [
        p for p in pkg["statements/obligation-parts.json"]["parts"]
        if p["sourceStatementId"] in known]
    pkg["statements/traceability-map.json"]["edges"] = [
        e for e in pkg["statements/traceability-map.json"]["edges"]
        if e["sourceStatementId"] in known]
    totals = pkg["statements/coverage-report.json"]["statementTotals"]
    totals["selected"] = totals["recordsCreated"] = n
    totals["statementsRemaining"] = FROZEN_STATEMENT_TOTAL - n
    return pkg


def _with_scope(package: dict, scope: str, only: str | None = None) -> dict:
    pkg = copy.deepcopy(package)
    for rel in SCOPE_BEARING:
        if only is None or rel == only:
            pkg[rel]["scope"] = scope
    return pkg


def _duplicate_id(package: dict) -> dict:
    pkg = copy.deepcopy(package)
    records = pkg["statements/source-statement-records.json"]["records"]
    clone = copy.deepcopy(records[1])
    clone["sourceStatementId"] = records[0]["sourceStatementId"]
    clone["statementText"] = clone["statementText"] + " (differing content)"
    records.append(clone)
    return pkg


def _totals(package: dict, **kw) -> dict:
    pkg = copy.deepcopy(package)
    pkg["statements/coverage-report.json"]["statementTotals"].update(kw)
    return pkg


def _orphan(package: dict, where: str) -> dict:
    pkg = copy.deepcopy(package)
    if where == "part":
        pkg["statements/obligation-parts.json"]["parts"][0]["sourceStatementId"] = "SS-999"
    else:
        pkg["statements/traceability-map.json"]["edges"][0]["sourceStatementId"] = "SS-999"
    return pkg


NEGATIVE_CASES = [
    ("duplicate-id",            _duplicate_id,                                    "DUPLICATE_SOURCE_STATEMENT_ID"),
    # Every N/scope case states BOTH coordinates, so a case can never silently become a no-op
    # because the committed baseline moved. F-1 moved it from (7, pilot-subset) to
    # (13, expansion-in-progress) and four baseline-relative cases stopped falsifying anything.
    ("n7-expansion",            lambda p: _with_scope(_with_n(p, 7), "expansion-in-progress"), "SCOPE_DOES_NOT_MATCH_N"),
    ("n7-full",                 lambda p: _with_scope(_with_n(p, 7), "full-set-87"),  "SCOPE_DOES_NOT_MATCH_N"),
    ("n8-pilot",                lambda p: _with_scope(_with_n(p, 8), "pilot-subset"),  "SCOPE_DOES_NOT_MATCH_N"),
    ("n13-pilot",               lambda p: _with_scope(_with_n(p, 13), "pilot-subset"), "SCOPE_DOES_NOT_MATCH_N"),
    ("n86-pilot",               lambda p: _with_scope(_with_n(p, 86), "pilot-subset"), "SCOPE_DOES_NOT_MATCH_N"),
    ("n8-full",                 lambda p: _with_scope(_with_n(p, 8), "full-set-87"),  "SCOPE_DOES_NOT_MATCH_N"),
    ("n13-full",                lambda p: _with_scope(_with_n(p, 13), "full-set-87"), "SCOPE_DOES_NOT_MATCH_N"),
    ("n86-full",                lambda p: _with_scope(_with_n(p, 86), "full-set-87"), "SCOPE_DOES_NOT_MATCH_N"),
    ("n87-pilot",               lambda p: _with_scope(_with_n(p, 87), "pilot-subset"), "SCOPE_DOES_NOT_MATCH_N"),
    ("n87-expansion",           lambda p: _with_scope(_with_n(p, 87), "expansion-in-progress"), "SCOPE_DOES_NOT_MATCH_N"),
    ("drift-records",           lambda p: _with_scope(p, "full-set-87", SCOPE_BEARING[0]), "SCOPE_DISAGREEMENT"),
    ("drift-parts",             lambda p: _with_scope(p, "full-set-87", SCOPE_BEARING[1]), "SCOPE_DISAGREEMENT"),
    ("drift-rules",             lambda p: _with_scope(p, "full-set-87", SCOPE_BEARING[2]), "SCOPE_DISAGREEMENT"),
    ("drift-coverage",          lambda p: _with_scope(p, "full-set-87", SCOPE_BEARING[3]), "SCOPE_DISAGREEMENT"),
    ("stale-selected",          lambda p: _totals(p, selected=6),                  "SELECTED_NOT_DERIVED_N"),
    ("stale-recordsCreated",    lambda p: _totals(p, recordsCreated=6),            "RECORDS_CREATED_NOT_DERIVED_N"),
    ("stale-remaining",         lambda p: _totals(p, statementsRemaining=79),      "REMAINING_NOT_DERIVED_N"),
    ("sum-87-but-wrong-n",      lambda p: _totals(p, recordsCreated=8, statementsRemaining=79), "RECORDS_CREATED_NOT_DERIVED_N"),
    ("sum-not-87",             lambda p: _totals(p, statementsRemaining=70),      "COUNTS_DO_NOT_SUM_TO_87"),
    ("orphan-part",             lambda p: _orphan(p, "part"),                     "ORPHAN_OBLIGATION_PART_STATEMENT"),
    ("orphan-traceability",     lambda p: _orphan(p, "edge"),                     "ORPHAN_TRACEABILITY_STATEMENT"),
]


@pytest.mark.parametrize("label,mutate,expected_code",
                         NEGATIVE_CASES, ids=[c[0] for c in NEGATIVE_CASES])
def test_falsified_payloads_are_rejected(label, mutate, expected_code) -> None:
    """Each case must be rejected for ITS invariant, so an unrelated defect cannot pass it."""
    assert scope_and_count_violations(load_package()) == [], "baseline must be clean"
    assert expected_code in scope_and_count_violations(mutate(load_package())), label


@pytest.mark.parametrize("label,mutate,expected_code",
                         NEGATIVE_CASES, ids=[c[0] for c in NEGATIVE_CASES])
def test_every_negative_case_actually_mutates_the_baseline(label, mutate, expected_code) -> None:
    """A case that no longer changes anything cannot falsify anything, however green it looks."""
    baseline = load_package()
    assert mutate(load_package()) != baseline, label


def test_unknown_fourth_scope_value_is_rejected_by_schema() -> None:
    from jsonschema import Draft202012Validator
    payload = copy.deepcopy(load("statements/coverage-report.json"))
    payload["scope"] = "some-other-scope"
    errors = list(Draft202012Validator(load("schema/coverage-report.schema.json")).iter_errors(payload))
    assert any("scope" in list(e.path) for e in errors)


# --------------------------------------------------------------------- structural integrity
def test_identifiers_are_unique(parts, rules, records) -> None:
    for collection, key in ((records, "sourceStatementId"), (parts, "obligationPartId"),
                            (rules, "ruleId")):
        identifiers = [item[key] for item in collection]
        assert len(identifiers) == len(set(identifiers)), key


def test_every_reference_resolves(parts, rules, records) -> None:
    statement_ids = {r["sourceStatementId"] for r in records}
    part_ids = {p["obligationPartId"] for p in parts}
    for part in parts:
        assert part["sourceStatementId"] in statement_ids
        assert set(part["dependsOn"]) <= part_ids
    for rule in rules:
        assert rule["primaryObligationPart"] in part_ids
        assert set(rule["supportingObligationParts"]) <= part_ids
    for edge in load("statements/traceability-map.json")["edges"]:
        assert edge["sourceStatementId"] in statement_ids
        assert edge["obligationPartId"] in part_ids


def test_each_rule_has_exactly_one_primary_obligation_part(rules) -> None:
    primaries = [r["primaryObligationPart"] for r in rules]
    assert len(primaries) == len(set(primaries))
    for rule in rules:
        assert rule["primaryObligationPart"] not in rule["supportingObligationParts"]
        if rule["supportingObligationParts"]:
            assert rule["supportingRelationshipJustification"], rule["ruleId"]


def test_no_rule_is_classified_composite(rules) -> None:
    assert {r["classification"] for r in rules} <= {"deterministic", "model-assisted"}


def test_no_orphaned_rules(rules, parts) -> None:
    covered = {p["obligationPartId"] for p in parts if p["coverageState"] == "rule-covered"}
    assert {r["primaryObligationPart"] for r in rules} == covered


def test_no_statement_has_an_empty_obligation_inventory(parts, records) -> None:
    counts = Counter(p["sourceStatementId"] for p in parts)
    for record in records:
        assert counts[record["sourceStatementId"]] >= 1, record["sourceStatementId"]


def test_unresolved_statement_still_has_obligation_parts(parts, records) -> None:
    for record in records:
        if record["statementClassification"] == "unresolved":
            owned = [p for p in parts if p["sourceStatementId"] == record["sourceStatementId"]]
            assert owned
            assert any(p["coverageState"] == "unresolved" for p in owned)


def test_unresolved_parts_record_why_they_cannot_be_resolved(parts) -> None:
    for part in parts:
        if part["coverageState"] == "unresolved":
            for field in ("unresolvedTerm", "missingAuthorityOrDependency",
                          "whyRepositoryCannotResolve", "requiredOwnerDecisionOrEvidence"):
                assert part[field], (part["obligationPartId"], field)
            assert part["possibleLaterClassifications"]
            assert part["evaluatorResponsibility"] == "none"


def test_human_review_obligations_are_documented_and_not_unresolved(parts) -> None:
    human = [p for p in parts if p["coverageState"] == "human-review-obligation"]
    assert human
    for part in human:
        assert part["evaluatorResponsibility"] == "human"
        assert part["humanJudgmentRequired"]
        assert part["whyAutomationInsufficient"]
        assert part["unresolvedTerm"] is None


def test_decomposition_and_coverage_are_governed_independently(parts, records) -> None:
    """A statement may be fully decomposed and still carry unresolved obligations."""
    block = load("statements/coverage-report.json")["statementDecompositionVsCoverage"]
    fully = sum(1 for r in records if r["decompositionStatus"] == "fully_decomposed")
    with_unresolved = sum(
        1 for r in records
        if any(p["coverageState"] == "unresolved"
               for p in parts if p["sourceStatementId"] == r["sourceStatementId"]))
    assert block["statementsFullyDecomposed"] == fully
    assert block["statementsContainingUnresolvedParts"] == with_unresolved
    assert block["unresolvedPartsTotal"] == sum(
        1 for p in parts if p["coverageState"] == "unresolved")
    # the two axes are independent: fully decomposed statements DO carry unresolved parts
    assert with_unresolved > 0 and fully > 0
    assert block["decompositionAssurance"] == "unconfirmed-pending-owner-review"


def test_decomposition_status_follows_representation_not_coverage(parts, records) -> None:
    for record in records:
        if not record["unrepresentedObligations"]:
            assert record["decompositionStatus"] == "fully_decomposed", record["sourceStatementId"]
        assert record["decompositionAssurance"] == "unconfirmed-pending-owner-review"


def test_ss_006_represents_the_conditional_conclusion(parts) -> None:
    part = next(p for p in parts if p["obligationPartId"] == "OP-006-n")
    assert part["derivationBasis"] == "source_obligation"
    assert "establishing instance-scoped existence" in part["normativeObligation"]
    assert "OP-006-g" in part["dependsOn"]


def test_ss_060_represents_all_three_obligations(parts) -> None:
    owned = {p["obligationPartId"]: p for p in parts if p["sourceStatementId"] == "SS-060"}
    assert set(owned) == {"OP-060-a", "OP-060-b", "OP-060-c"}
    assert "with team sorting" in owned["OP-060-a"]["normativeObligation"]
    assert "underspecified boundary" in owned["OP-060-c"]["normativeObligation"]
    assert "pass to partial" in owned["OP-060-b"]["normativeObligation"]


def test_ss_033_keeps_the_adjectival_scope_of_the_source(parts) -> None:
    part = next(p for p in parts if p["obligationPartId"] == "OP-033-b")
    assert "adjectival" in part["normativeObligation"]
    assert any("NOT source-derived" in limit for limit in part["knownLimitations"])


def test_ss_055_pass_criterion_is_one_conjunctive_obligation(parts, rules) -> None:
    """The four qualifications are predicates, not independent normative obligations."""
    owned = {p["obligationPartId"] for p in parts if p["sourceStatementId"] == "SS-055"}
    assert not (owned & {"OP-055-h", "OP-055-i", "OP-055-j", "OP-055-k"}), (
        "the retired qualification-split IDs must not reappear")
    criterion = next(p for p in parts if p["obligationPartId"] == "OP-055-a")
    assert len(criterion["qualifyingPredicates"]) == 4
    rule = next(r for r in rules if r["primaryObligationPart"] == "OP-055-a")
    assert rule["outcomeCodes"] == ["PASS_QUALIFYING_COUNT_BELOW_MINIMUM"], (
        "insufficient qualifying count is the only normative violation")
    assert len(rule["diagnosticExclusionReasons"]) == 4


def test_ss_055_predicates_are_diagnostic_exclusions_not_violations(rules) -> None:
    """A non-qualifying source is excluded from the count, never itself a violation."""
    rule = next(r for r in rules if r["ruleId"] == "BR-055-pass-criterion")
    excluded_codes = {d["code"] for d in rule["diagnosticExclusionReasons"]}
    assert excluded_codes == {"PASS_SOURCE_NOT_INDEPENDENT", "PASS_SOURCE_OUT_OF_SEGMENT",
                              "PASS_COMMITMENT_FORM_NOT_QUALIFYING",
                              "PASS_COMMITMENT_NOT_TO_EXISTING_PROBLEM"}
    assert not (excluded_codes & set(rule["outcomeCodes"])), (
        "an exclusion reason must never also be a violation code")
    for reason in rule["diagnosticExclusionReasons"]:
        assert reason["establishedBy"], reason["code"]
        assert "excluded from the qualifying count" in reason["effect"]


def test_ss_055_evaluator_contract_specifies_completeness_and_trust(rules) -> None:
    contract = next(r for r in rules if r["ruleId"] == "BR-055-pass-criterion")["evaluatorContract"]
    assert contract["candidateInventoryCompletenessRequired"] is True
    assert contract["trustedPredicateClassificationRequired"] is True
    assert contract["resultWhenInventoryIncomplete"] == "indeterminate"
    assert contract["resultWhenPredicateClassificationMissingOrUntrusted"] == "indeterminate"
    outcomes = {e["outcome"] for e in contract["workedExamples"]}
    assert outcomes == {"obligation_satisfied", "obligation_violation", "indeterminate"}


def test_ss_055_credibility_is_an_evaluation_method_not_a_workflow_obligation(parts) -> None:
    owned = {p["obligationPartId"] for p in parts if p["sourceStatementId"] == "SS-055"}
    assert "OP-055-l" not in owned, "credibility must not be a separate ordering obligation"
    g = next(p for p in parts if p["obligationPartId"] == "OP-055-g")
    assert g["normativeObligation"] == "Credible evidence on both sides must yield partial."
    assert g["humanInputRequired"], "credibility is supplied by human review"
    assert "before" not in g["normativeObligation"], "no workflow ordering is imposed"


def test_op_006_n_declares_its_validation_prerequisites(parts, rules) -> None:
    part = next(p for p in parts if p["obligationPartId"] == "OP-006-n")
    for prerequisite in ("OP-006-g", "OP-006-h", "OP-006-i", "OP-006-j", "OP-006-k",
                         "OP-006-l", "OP-006-m"):
        assert prerequisite in part["dependsOn"], prerequisite
    rule = next(r for r in rules if r["primaryObligationPart"] == "OP-006-n")
    assert set(part["dependsOn"]) <= set(rule["supportingObligationParts"])


def test_ss_033_obligation_is_the_property_not_the_label(parts) -> None:
    obligation = next(p for p in parts if p["obligationPartId"] == "OP-033-b")
    assert "non-decidable adjectival term" in obligation["normativeObligation"]
    assert "labelled" not in obligation["normativeObligation"]
    precondition = next(p for p in parts if p["obligationPartId"] == "OP-033-a")
    assert precondition["derivationBasis"] == "evaluation_precondition"
    assert "trusted decidability classification" in precondition["normativeObligation"]


def test_ss_070_definition_obligation_preserves_window_properties(parts) -> None:
    part = next(p for p in parts if p["obligationPartId"] == "OP-070-d")
    text = part["normativeObligation"].lower()
    for attribute in ("eight", "consecutive", "calendar-week"):
        assert attribute in text, attribute


# ------------------------------------------------- C6: source / precondition / proxy separation
def test_every_obligation_part_declares_a_derivation_basis(parts) -> None:
    allowed = {"source_obligation", "evaluation_precondition", "evaluation_proxy"}
    for part in parts:
        assert part["derivationBasis"] in allowed, part["obligationPartId"]


def test_proxy_parts_name_what_they_proxy_and_their_limitation(parts) -> None:
    proxies = [p for p in parts if p["derivationBasis"] == "evaluation_proxy"]
    assert proxies, "the pilot must demonstrate the proxy disposition"
    for part in proxies:
        assert part["proxiedSourceObligation"], part["obligationPartId"]
        assert part["proxyLimitation"], part["obligationPartId"]


def test_non_proxy_parts_do_not_claim_a_proxied_obligation(parts) -> None:
    for part in parts:
        if part["derivationBasis"] != "evaluation_proxy":
            assert part["proxiedSourceObligation"] is None, part["obligationPartId"]
            assert part["proxyLimitation"] is None, part["obligationPartId"]


def test_only_source_obligations_count_as_source_derived_coverage(rules) -> None:
    for rule in rules:
        expected = rule["derivationBasis"] == "source_obligation"
        assert rule["countsAsSourceDerivedCoverage"] is expected, rule["ruleId"]


def test_result_vocabulary_is_fixed_by_derivation_basis(rules) -> None:
    """A proxy can no more emit obligation_satisfied than obligation_violation."""
    for rule in rules:
        expected_class = RESULT_CLASS[rule["derivationBasis"]]
        assert rule["resultClass"] == expected_class, rule["ruleId"]
        key = expected_class
        if expected_class == "normative" and rule["hasAntecedent"]:
            key = "normative_conditional"
        assert set(rule["expectedOutcomes"]) == ALLOWED_RESULTS[key], rule["ruleId"]


def test_only_source_obligation_rules_may_emit_normative_outcomes(rules) -> None:
    normative = {"obligation_satisfied", "obligation_violation", "not_applicable"}
    for rule in rules:
        if rule["derivationBasis"] != "source_obligation":
            leaked = normative & set(rule["expectedOutcomes"])
            assert not leaked, (rule["ruleId"], sorted(leaked))


def test_proxy_rules_require_external_bridge_authority(rules) -> None:
    proxies = [r for r in rules if r["derivationBasis"] == "evaluation_proxy"]
    assert proxies, "the pilot must demonstrate the proxy disposition"
    for rule in proxies:
        assert rule["bridgeAuthorityRequired"] is True, rule["ruleId"]
        assert rule["normativeOutcomeRequiresBridgeAuthority"] is True, rule["ruleId"]
        assert rule["bridgeAuthorityRecordRef"], rule["ruleId"]


def test_no_rule_embeds_mutable_authority_state(rules) -> None:
    for rule in rules:
        assert "bridgeAuthorityGranted" not in rule, rule["ruleId"]
        assert "outcomesGatedPendingBridgeAuthority" not in rule, rule["ruleId"]


def test_bridge_authority_record_is_external_and_not_granted() -> None:
    record = load("records/bridge-authority-record.example.json")
    assert record["authorityStatus"] == "not-granted"
    assert record["grantedBy"] is None and record["grantedTimestamp"] is None
    assert record["grantedForRuleIds"] == []
    assert record["governedArtifactPath"].endswith("manifest.json")
    assert len(record["governedArtifactDigest"]) == 64


def test_precondition_rules_report_input_availability_only(rules) -> None:
    preconditions = [r for r in rules if r["derivationBasis"] == "evaluation_precondition"]
    assert preconditions, "the pilot must demonstrate the precondition disposition"
    for rule in preconditions:
        assert set(rule["expectedOutcomes"]) == ALLOWED_RESULTS["precondition"], rule["ruleId"]
        assert rule["bridgeAuthorityRequired"] is False


def test_rule_derivation_matches_its_primary_obligation_part(rules, parts) -> None:
    by_id = {p["obligationPartId"]: p for p in parts}
    for rule in rules:
        assert rule["derivationBasis"] == by_id[rule["primaryObligationPart"]]["derivationBasis"], rule["ruleId"]


# ------------------------------------------------------------- C3: no unsourced threshold terms
def test_op_034_a_imposes_no_unsourced_threshold_requirement(parts, rules) -> None:
    part = next(p for p in parts if p["obligationPartId"] == "OP-034-a")
    text = f"{part['normativeObligation']} {part['observableInvariant']}".lower()
    assert "numeric" not in text
    assert "unit" not in text
    rule = next(r for r in rules if r["primaryObligationPart"] == "OP-034-a")
    assert not any("UNIT" in code for code in rule["outcomeCodes"])


# --------------------------------------------------------------------- C5: EV-004 scope restored
def test_ss_006_proxy_parts_keep_ev_004_scope(parts) -> None:
    """All six EV-004 proxy parts, OP-006-a through OP-006-f, stay EV-004 scoped."""
    scoped = [p for p in parts if p["obligationPartId"] in
              ("OP-006-a", "OP-006-b", "OP-006-c", "OP-006-d", "OP-006-e", "OP-006-f")]
    assert len(scoped) == 6
    for part in scoped:
        assert "EV-004" in part["normativeObligation"], part["obligationPartId"]
        assert part["derivationBasis"] == "evaluation_proxy", part["obligationPartId"]
        assert part["coverageState"] == "rule-covered", part["obligationPartId"]
    credibility = next(p for p in parts if p["obligationPartId"] == "OP-006-g")
    assert credibility["derivationBasis"] == "evaluation_precondition"
    assert credibility["coverageState"] == "human-review-obligation"


# --------------------------------------------------------------------- C1 + C2: honest coverage
def test_no_rule_claims_any_rule_fixture(rules) -> None:
    for rule in rules:
        assert rule["ruleFixtures"] == [], rule["ruleId"]


def test_fixture_evidence_is_reported_as_intended_association_only(rules) -> None:
    fixture = load("statements/coverage-report.json")["fixtureEvidence"]
    associated = sum(1 for r in rules if r["intendedEvidencePacketAssociation"])
    assert fixture["actualRuleFixtures"] == 0
    assert fixture["rulesWithIntendedEvidencePacketAssociation"] == associated
    assert "not fixture coverage" in fixture["note"]


def test_evaluator_maturity_separates_design_from_implementation(rules) -> None:
    maturity = load("statements/coverage-report.json")["evaluatorMaturity"]
    assert maturity["mechanismDefined"] == len(rules)
    assert maturity["evaluatorImplemented"] == 0
    assert maturity["behaviourExecutedInTests"] == 0
    assert maturity["liveModelEvaluationPerformed"] == 0
    assert maturity["reliabilityEvidenceEstablished"] == 0
    for rule in rules:
        assert rule["evaluatorMechanism"] == "defined"
        assert rule["evaluatorImplemented"] is False
        assert rule["behaviourExecutedInTests"] is False


def test_statement_and_rule_totals_reconcile(parts, rules, records) -> None:
    report = load("statements/coverage-report.json")
    states = Counter(p["coverageState"] for p in parts)
    derivations = Counter(p["derivationBasis"] for p in parts)
    rule_derivations = Counter(r["derivationBasis"] for r in rules)
    classes = Counter(r["classification"] for r in rules)
    decomposition = Counter(r["decompositionStatus"] for r in records)

    st, ob, ru = report["statementTotals"], report["obligationTotals"], report["ruleTotals"]
    derived_n = len({r["sourceStatementId"] for r in records})
    assert st["selected"] == st["recordsCreated"] == len(records) == derived_n
    assert st["fullyDecomposed"] == decomposition["fully_decomposed"]
    assert st["partiallyDecomposed"] == decomposition["partially_decomposed"]
    assert st["fullyDecomposed"] + st["partiallyDecomposed"] == derived_n

    assert ob["identified"] == len(parts)
    assert (ob["sourceObligation"] + ob["evaluationPrecondition"]
            + ob["evaluationProxy"]) == ob["identified"]
    assert (ob["ruleCovered"] + ob["humanReviewObligation"]
            + ob["unresolved"]) == ob["identified"]
    assert ob["sourceObligation"] == derivations["source_obligation"]
    assert ob["evaluationProxy"] == derivations["evaluation_proxy"]
    assert ob["ruleCovered"] == states["rule-covered"] == len(rules)

    assert ru["proposed"] == len(rules)
    assert ru["deterministicDesign"] + ru["modelAssistedDesign"] == ru["proposed"]
    assert ru["deterministicDesign"] == classes["deterministic"]
    assert (ru["sourceDerivedExecutableRuleCoverage"] + ru["preconditionRules"]
            + ru["proxyRules"]) == ru["proposed"]
    assert ru["sourceDerivedExecutableRuleCoverage"] == rule_derivations["source_obligation"]
    assert ru["rulesPermittedToEmitNormativeOutcomes"] == rule_derivations["source_obligation"]

    # source-obligation coverage: executable rules are only part of the total
    src = [p for p in parts if p["derivationBasis"] == "source_obligation"]
    soc = report["sourceObligationCoverage"]
    by_state = Counter(p["coverageState"] for p in src)
    assert soc["sourceObligationParts"] == len(src)
    fpa = report["findingPolicyAccounting"]
    findings_capable = sum(1 for r in rules if r["canProduceProductFinding"])
    assert fpa["totalRuleDesigns"] == len(rules)
    assert fpa["normativeRuleDesignsCapableOfProductFindings"] == findings_capable
    assert fpa["diagnosticOnlyRuleDesigns"] == len(rules) - findings_capable
    assert (fpa["diagnosticProxyRules"] + fpa["diagnosticPreconditionRules"]
            == fpa["diagnosticOnlyRuleDesigns"])
    assert fpa["reviewPolicyGovernsRuleDefinitions"] == len(rules)
    assert soc["representedByRules"] == by_state["rule-covered"]
    assert soc["humanRequiredDispositions"] == by_state["human-review-obligation"]
    assert soc["unresolvedDispositions"] == by_state["unresolved"]
    assert (soc["representedByRules"] + soc["humanRequiredDispositions"]
            + soc["unresolvedDispositions"]) == soc["sourceObligationParts"]

    assert sum(report["statementClassification"].values()) == derived_n


def test_no_full_set_rule_count_is_extrapolated() -> None:
    report = load("statements/coverage-report.json")
    assert report["fullSetAtomicRuleTotal"] == "unknown"
    assert report["extrapolationPermitted"] is False
    assert "130" not in json.dumps(report)


def test_the_three_review_axes_stay_separate(parts, rules) -> None:
    """Human-required source obligations, governed rule definitions, and finding-capable rules differ."""
    axes = load("statements/coverage-report.json")["axisSeparation"]
    human_obligations = sum(1 for p in parts
                            if p["coverageState"] == "human-review-obligation"
                            and p["derivationBasis"] == "source_obligation")
    findings_capable = sum(1 for r in rules if r["canProduceProductFinding"])
    assert axes["humanRequiredSourceObligations"] == human_obligations
    assert axes["ruleDesignsGovernedByReviewPolicy"] == len(rules)
    assert axes["ruleDesignsCapableOfProducingFindings"] == findings_capable
    assert len({human_obligations, len(rules), findings_capable}) == 3


def test_only_source_obligation_rules_can_produce_product_findings(rules) -> None:
    for rule in rules:
        expected = rule["derivationBasis"] == "source_obligation"
        assert rule["canProduceProductFinding"] is expected, rule["ruleId"]


def test_op_070_c_is_sourced_to_the_exact_frozen_phrase(parts) -> None:
    part = next(p for p in parts if p["obligationPartId"] == "OP-070-c")
    assert part["sourceClauseReference"] == "before inspecting events"
    assert "purpose" not in part["sourceClauseReference"]
    assert part["derivationBasis"] == "source_obligation"
    assert part["coverageState"] == "unresolved"


def test_ss_070_carries_both_source_obligations(parts) -> None:
    """A declared workflow step is only a proxy for definition and for ordering alike."""
    owned = {p["obligationPartId"]: p for p in parts if p["sourceStatementId"] == "SS-070"}
    definition = owned["OP-070-d"]
    assert definition["derivationBasis"] == "source_obligation"
    assert definition["coverageState"] == "unresolved"
    assert definition["sourceClauseReference"] == "Define eight consecutive calendar-week windows"
    ordering = owned["OP-070-c"]
    assert ordering["derivationBasis"] == "source_obligation"
    # each proxy names the distinct source obligation it stands in for
    assert "OP-070-d" in owned["OP-070-a"]["proxiedSourceObligation"]
    assert "OP-070-c" in owned["OP-070-b"]["proxiedSourceObligation"]


def test_ss_026_evidence_contract_is_explicit(parts) -> None:
    contract = next(p for p in parts if p["obligationPartId"] == "OP-026-a")["evidenceContract"]
    assert contract is not None
    assert contract["completeInventoryRequired"] is True
    assert contract["trustedClassificationRequired"] is True
    assert contract["resultWhenInventoryIncomplete"] == "indeterminate"
    assert contract["resultWhenClassificationMissingOrUntrusted"] == "indeterminate"
    assert contract["classificationAuthorityRecordRef"]
    # mutable authority state must not be embedded in the obligation part
    assert "classificationApprovalStatus" not in contract


def test_classification_authority_is_external_and_not_approved() -> None:
    record = load("records/classification-authority-record.example.json")
    assert record["authorityStatus"] == "not-approved"
    assert record["approvedBy"] is None and record["approvedTimestamp"] is None
    assert record["approvedForObligationPartIds"] == []
    assert len(record["governedArtifactDigest"]) == 64


def test_op_026_a_stays_source_derived_regardless_of_classification(parts, rules) -> None:
    """Unavailable classification makes the evaluation indeterminate, not the obligation a proxy."""
    part = next(p for p in parts if p["obligationPartId"] == "OP-026-a")
    assert part["derivationBasis"] == "source_obligation"
    rule = next(r for r in rules if r["primaryObligationPart"] == "OP-026-a")
    assert rule["derivationBasis"] == "source_obligation"
    assert rule["canProduceProductFinding"] is True
    assert "indeterminate" in rule["expectedOutcomes"]


def test_conditional_rules_never_report_vacuous_satisfaction(rules) -> None:
    """A false antecedent yields condition_not_met, never obligation_satisfied."""
    taxonomy = load("contracts/outcome-taxonomy.json")
    assert not any(o["outcome"] == "condition_not_met" for o in taxonomy["normativeOutcomes"]), (
        "condition_not_met is a diagnostic activation result, not a normative conclusion")
    entry = next(o for o in taxonomy["diagnosticActivationResults"]
                 if o["outcome"] == "condition_not_met")
    assert entry["isPass"] is False
    assert entry["isProductFinding"] is False
    assert entry["countsAsObligationCompliance"] is False
    assert taxonomy["vacuousSatisfactionPolicy"]
    conditional = [r for r in rules if r["hasAntecedent"]]
    assert conditional, "the pilot must demonstrate conditional rules"
    for rule in conditional:
        assert "condition_not_met" in rule["expectedOutcomes"], rule["ruleId"]
    for rule in rules:
        if not rule["hasAntecedent"]:
            assert "condition_not_met" not in rule["expectedOutcomes"], rule["ruleId"]


def test_br_006_false_antecedent_is_not_satisfaction(rules) -> None:
    contract = next(r for r in rules
                    if r["ruleId"] == "BR-006-credible-establishes-existence")["evaluatorContract"]
    not_credible = next(e for e in contract["workedExamples"] if "not credible" in e["scenario"])
    assert not_credible["outcome"] == "condition_not_met"


def test_op_060_a_is_a_precondition_not_a_source_obligation(parts) -> None:
    """'any material classification disagreement' is a condition, not a command to judge."""
    part = next(p for p in parts if p["obligationPartId"] == "OP-060-a")
    assert part["derivationBasis"] == "evaluation_precondition"
    assert part["coverageState"] == "human-review-obligation"
    assert "must be judged" not in part["normativeObligation"]
    for consequence_id in ("OP-060-b", "OP-060-c"):
        consequence = next(p for p in parts if p["obligationPartId"] == consequence_id)
        assert consequence["derivationBasis"] == "source_obligation"
        assert "OP-060-a" in consequence["dependsOn"]


def test_ss_055_credibility_has_an_explicit_precondition(parts, rules) -> None:
    precondition = next(p for p in parts if p["obligationPartId"] == "OP-055-m")
    assert precondition["derivationBasis"] == "evaluation_precondition"
    assert precondition["coverageState"] == "human-review-obligation"
    g = next(p for p in parts if p["obligationPartId"] == "OP-055-g")
    assert "OP-055-m" in g["dependsOn"]
    rule = next(r for r in rules if r["ruleId"] == "BR-055-partial-on-two-sided-credible")
    assert "OP-055-m" in rule["supportingObligationParts"]
    assert "no internal mechanism" in rule["evaluatorContract"]["exclusionSemantics"]
    outcomes = {e["outcome"] for e in rule["evaluatorContract"]["workedExamples"]}
    assert {"indeterminate", "condition_not_met", "obligation_satisfied",
            "obligation_violation"} == outcomes


def test_ss_055_partial_implication_follows_the_frozen_verb_yields(parts, rules) -> None:
    """The clause is 'credible evidence on both sides yields partial': credibility is the antecedent."""
    part = next(p for p in parts if p["obligationPartId"] == "OP-055-g")
    assert part["normativeObligation"] == "Credible evidence on both sides must yield partial."
    rule = next(r for r in rules if r["ruleId"] == "BR-055-partial-on-two-sided-credible")
    antecedent = rule["diagnosticExclusionReasons"][0]
    assert antecedent["predicate"] == "the evidence on both sides is credible"
    assert rule["outcomeCodes"] == ["TWO_SIDED_CREDIBLE_NOT_PARTIAL"]

    examples = {e["outcome"]: e["scenario"] for e in rule["evaluatorContract"]["workedExamples"]}
    assert "missing or untrusted" in examples["indeterminate"]
    assert "not credible" in examples["condition_not_met"]
    # the violation is credible-on-both-sides WITHOUT a partial, not the converse
    assert "both sides determined credible" in examples["obligation_violation"]
    assert "not partial" in examples["obligation_violation"]
    assert "both sides determined credible" in examples["obligation_satisfied"]


def test_ss_055_fail_criterion_is_one_conjunction(parts, rules) -> None:
    """The comparable-credibility fragment is a conjunct, not an independent obligation."""
    criterion = next(p for p in parts if p["obligationPartId"] == "OP-055-e")
    assert len(criterion["qualifyingPredicates"]) == 2
    assert "OP-055-f" in criterion["dependsOn"]
    precondition = next(p for p in parts if p["obligationPartId"] == "OP-055-f")
    assert precondition["derivationBasis"] == "evaluation_precondition"
    assert precondition["coverageState"] == "human-review-obligation"
    rule = next(r for r in rules if r["ruleId"] == "BR-055-fail-criterion")
    assert rule["outcomeCodes"] == ["FAIL_RECORDED_WITHOUT_QUALIFYING_CRITERIA"]
    assert rule["hasAntecedent"] is True


def test_no_source_obligation_carries_a_human_disposition(parts) -> None:
    """Package-specific invariant for these seven pilot statements, NOT a universal modelling rule.

    Across SS-006, SS-026, SS-033, SS-034, SS-055, SS-060 and SS-070 every frozen fragment that reads
    as a condition turned out to be evaluator input rather than an obligation. Other statements may
    well contain a source obligation that genuinely requires human judgment; this test must not be
    generalised to the full 87 during Gate 2A-F without re-deriving it.
    """
    breakdown = load("statements/coverage-report.json")["humanRequiredBreakdown"]
    human = [p for p in parts if p["coverageState"] == "human-review-obligation"]
    assert breakdown["asSourceObligations"] == 0
    assert breakdown["asEvaluationPreconditions"] == len(human)
    for part in human:
        assert part["derivationBasis"] == "evaluation_precondition", part["obligationPartId"]


def test_op_006_g_is_a_precondition_not_a_source_obligation(parts) -> None:
    """The frozen text states a condition, not a command to judge credibility."""
    part = next(p for p in parts if p["obligationPartId"] == "OP-006-g")
    assert part["derivationBasis"] == "evaluation_precondition"
    assert part["coverageState"] == "human-review-obligation"
    assert "must be judged" not in part["normativeObligation"]
    consequence = next(p for p in parts if p["obligationPartId"] == "OP-006-n")
    assert consequence["derivationBasis"] == "source_obligation"
    assert "OP-006-g" in consequence["dependsOn"]


def test_human_required_breakdown_separates_source_from_precondition(parts) -> None:
    breakdown = load("statements/coverage-report.json")["humanRequiredBreakdown"]
    human = [p for p in parts if p["coverageState"] == "human-review-obligation"]
    source = sum(1 for p in human if p["derivationBasis"] == "source_obligation")
    precondition = sum(1 for p in human if p["derivationBasis"] == "evaluation_precondition")
    assert breakdown["humanRequiredParts"] == len(human)
    assert breakdown["asSourceObligations"] == source
    assert breakdown["asEvaluationPreconditions"] == precondition
    assert source + precondition == len(human)


def test_br_006_conditional_outcomes_are_explicit(rules) -> None:
    contract = next(r for r in rules
                    if r["ruleId"] == "BR-006-credible-establishes-existence")["evaluatorContract"]
    scenarios = {e["scenario"]: e["outcome"] for e in contract["workedExamples"]}
    assert len(scenarios) == 4
    outcomes = list(scenarios.values())
    assert outcomes.count("indeterminate") == 2, "missing credibility and incomplete validation"
    assert "condition_not_met" in outcomes, "not credible is neither violation nor satisfaction"
    assert "obligation_satisfied" not in outcomes, "no vacuous satisfaction"
    assert "obligation_violation" in outcomes, "credible but consequence absent is a violation"


def test_ss_055_independence_declaration_cannot_authenticate_itself(rules) -> None:
    rule = next(r for r in rules if r["ruleId"] == "BR-055-pass-criterion")
    independence = next(d for d in rule["diagnosticExclusionReasons"]
                        if d["code"] == "PASS_SOURCE_NOT_INDEPENDENT")
    assert "cannot authenticate itself" in independence["establishedBy"]
    assert "indeterminate" in independence["establishedBy"]
    assert "does not cause exclusion" in rule["evaluatorContract"]["exclusionSemantics"]


def test_ss_006_validation_obligations_are_source_not_only_proxies(parts) -> None:
    """Each declared-validation proxy has a corresponding source obligation."""
    owned = {p["obligationPartId"]: p for p in parts if p["sourceStatementId"] == "SS-006"}
    for proxy_id, source_id in (("OP-006-a", "OP-006-h"), ("OP-006-b", "OP-006-i"),
                                ("OP-006-c", "OP-006-j"), ("OP-006-d", "OP-006-k"),
                                ("OP-006-e", "OP-006-l"), ("OP-006-f", "OP-006-m")):
        proxy, source = owned[proxy_id], owned[source_id]
        assert proxy["derivationBasis"] == "evaluation_proxy", proxy_id
        assert source["derivationBasis"] == "source_obligation", source_id
        assert source["coverageState"] == "unresolved", source_id
        assert source_id in proxy["proxiedSourceObligation"], proxy_id


def test_every_source_clause_is_verbatim_from_its_frozen_statement(parts, records) -> None:
    """Exact source-clause fidelity: no paraphrase, no ellipsis, no invented wording."""
    text_by_statement = {r["sourceStatementId"]: r["statementText"] for r in records}
    for part in parts:
        clause = part["sourceClauseReference"]
        if part["derivationBasis"] == "evaluation_precondition":
            continue  # preconditions legitimately have no source clause
        statement = text_by_statement[part["sourceStatementId"]]
        for fragment in (f.strip() for f in clause.split("|")):
            fragment = fragment.strip("'\"")
            assert fragment in statement, (part["obligationPartId"], fragment)
        assert "..." not in clause and "…" not in clause, part["obligationPartId"]


# Every source obligation whose enforcement depends on a complete inventory plus a trusted
# classification, mapped to the statement-specific terms its inventory scope must actually name.
# A part absent from this map must carry no contract; a part present must carry a conforming one.
INVENTORY_DEPENDENT_CONTRACTS = {
    "OP-004-a": ("REQ-1", "screening sheet"),
    "OP-009-a": ("EV-003", "supersession"),
    "OP-026-a": ("REQ-5", "declared sourceCategory"),
    "OP-027-a": ("REQ-5", "proposed-product demand"),
    "OP-028-a": ("commitment record", "withdraw"),
    "OP-039-a": ("REQ-2", "absence of occurrence evidence"),
}


def test_inventory_dependent_source_obligations_declare_evidence_contracts(parts) -> None:
    """The contract-bearing set is exactly six, and each contract is specific, complete and bound."""
    owned = {p["obligationPartId"]: p for p in parts}
    with_contract = [p["obligationPartId"] for p in parts if p["evidenceContract"] is not None]

    # exact set: rejects both a missing contract and an unexpected extra one
    assert sorted(with_contract) == sorted(INVENTORY_DEPENDENT_CONTRACTS), with_contract
    assert len(with_contract) == 6, with_contract

    # OP-010-a depends on no inventory: the frozen statement supplies EV-015's status directly
    assert owned["OP-010-a"]["evidenceContract"] is None
    assert not owned["OP-010-a"]["dependsOn"]

    scopes = []
    for part_id, required_terms in INVENTORY_DEPENDENT_CONTRACTS.items():
        part = owned[part_id]
        contract = part["evidenceContract"]
        assert contract is not None, part_id

        # incomplete inventory or absent/untrusted classification must never read as satisfied
        assert contract["completeInventoryRequired"] is True, part_id
        assert contract["trustedClassificationRequired"] is True, part_id
        assert contract["resultWhenInventoryIncomplete"] == "indeterminate", part_id
        assert contract["resultWhenClassificationMissingOrUntrusted"] == "indeterminate", part_id

        # authority is referenced, never embedded: an approval state here would be self-granted
        assert contract["classificationAuthorityRecordRef"] == \
            "records/classification-authority-record.example.json", part_id
        for forbidden in ("classificationApprovalStatus", "approvedBy", "authorityStatus"):
            assert forbidden not in contract, (part_id, forbidden)

        # the obligation stays source-derived; only a nonconforming evaluator would be a proxy
        assert part["derivationBasis"] == "source_obligation", part_id
        assert part["proxiedSourceObligation"] is None, part_id
        assert "proxy" in contract["remainsSourceDerivedOnlyIf"].lower(), part_id
        assert "indeterminate" in contract["currentStatus"].lower(), part_id

        # statement-specific, not boilerplate: the scope must name this statement's own subject
        scope = contract["inventoryScope"]
        assert len(scope) >= 40, part_id
        for term in required_terms:
            assert term.lower() in scope.lower(), (part_id, term)
        scopes.append(scope)

    # no two contracts may share a scope, which is how generic filler would show up
    assert len(set(scopes)) == len(scopes), "inventory scopes must be statement-specific"

    # a contract stated only in prose is unenforceable: none may survive anywhere in the package
    for part in parts:
        for limitation in part["knownLimitations"]:
            assert "structured evidenceContract block" not in limitation, part["obligationPartId"]


def test_finding_policy_records_zero_implementation_and_zero_findings() -> None:
    accounting = load("statements/coverage-report.json")["findingPolicyAccounting"]
    assert accounting["currentlyImplementedEvaluators"] == 0
    assert accounting["actualGeneratedFindings"] == 0


def test_gate_1_policy_mismatch_is_documented_and_not_modified() -> None:
    deferred = load("statements/coverage-report.json")["deferredRemediation"]
    entry = next(d for d in deferred if d["id"] == "DR-1")
    assert entry["modifiedInThisPass"] is False
    assert "phase1-behavior-coverage.json" in entry["affectedArtifact"]
    assert entry["deferredTo"] == "pre-Gate 2B remediation"


def test_ss_026_normative_rule_depends_on_an_approved_classification(parts, rules) -> None:
    obligation = next(p for p in parts if p["obligationPartId"] == "OP-026-a")
    precondition = next(p for p in parts if p["obligationPartId"] == "OP-026-b")
    assert obligation["derivationBasis"] == "source_obligation"
    assert obligation["dependsOn"] == ["OP-026-b"]
    assert precondition["derivationBasis"] == "evaluation_precondition"
    rule = next(r for r in rules if r["ruleId"] == "BR-026-no-wtp-substitution")
    assert rule["supportingObligationParts"] == ["OP-026-b"]
    assert rule["knownUnsupportedCases"], "undeclared prose must be recorded as unsupported"


# --------------------------------------------------------------------- C7 + outcome taxonomy
def test_outcome_taxonomy_separates_three_result_vocabularies() -> None:
    taxonomy = load("contracts/outcome-taxonomy.json")
    assert {k: v for k, v in taxonomy["resultClassByDerivation"].items() if k != "note"} == RESULT_CLASS
    normative = {o["outcome"]: o for o in taxonomy["normativeOutcomes"]}
    assert "condition_not_met" not in normative
    assert taxonomy["resultClassByDerivation"]["note"]
    proxy = {o["outcome"]: o for o in taxonomy["proxyResults"]}
    precondition = {o["outcome"]: o for o in taxonomy["preconditionResults"]}

    assert normative["obligation_satisfied"]["isPass"] is True
    assert normative["obligation_satisfied"]["countsAsObligationCompliance"] is True
    for name in ("obligation_violation", "indeterminate", "evaluator_error", "not_applicable"):
        assert normative[name]["isPass"] is False, name

    # no proxy or precondition result is ever a pass, a product finding, or compliance
    for group in (proxy, precondition):
        for name, entry in group.items():
            assert entry["isPass"] is False, name
            assert entry["isProductFinding"] is False, name
            assert entry["countsAsObligationCompliance"] is False, name

    assert "obligation_satisfied" not in proxy and "obligation_violation" not in proxy
    assert "obligation_satisfied" not in precondition

    conflations = taxonomy["prohibitedConflations"]
    assert len(conflations) == len(set(conflations)), "prohibited conflations must not be duplicated"
    assert len(conflations) >= 10


def test_not_applicable_unreachability_is_documented(rules) -> None:
    taxonomy = load("contracts/outcome-taxonomy.json")
    assert taxonomy["notApplicableReachability"]
    for rule in rules:
        assert rule["applicability"]["predicateApproved"] is False, rule["ruleId"]
        assert "not_applicable" not in rule["expectedOutcomes"], rule["ruleId"]


def test_every_rule_can_report_evaluator_error_and_never_acts_automatically(rules) -> None:
    for rule in rules:
        assert "evaluator_error" in rule["expectedOutcomes"], rule["ruleId"]
        assert rule["mayBeActedUponAutomatically"] is False
        if rule["derivationBasis"] != "evaluation_precondition":
            assert "indeterminate" in rule["expectedOutcomes"], rule["ruleId"]


def test_observed_chronology_is_unsupported_and_unused_by_any_rule(rules) -> None:
    operators = {o["operator"]: o for o in load("contracts/operator-set.json")["operators"]}
    assert operators["declaredStepPrecedes"]["supportStatus"] == "usable-in-design"
    observed = operators["observedEventPrecedes"]
    assert observed["supportStatus"] == "unsupported"
    assert observed["trustEstablishment"]["establishedInRepository"] is False
    assert observed["degradedEvidenceOutcome"] == "indeterminate"
    for rule in rules:
        assert rule["orderingOperator"] != "observedEventPrecedes", rule["ruleId"]
        assert rule["provenanceRequirement"]["approvedEventSourceAvailable"] is False


# --------------------------------------------------------------------- C4 + lifecycle
def test_class_a_digest_member_instances_assert_no_mutable_state() -> None:
    """Class A: digest-member INSTANCES may not carry approval or current-state keys.

    A recursive key walk, not a text search: a schema is allowed to define this vocabulary and
    documentation is allowed to discuss it. Only an instance asserting it is prohibited.
    """
    for instance_rel, _ in PAIRS:
        if instance_rel.startswith("records/") or instance_rel == "manifest.json":
            continue
        for key in walk_keys(load(instance_rel)):
            assert key not in MUTABLE_STATE_KEYS, (instance_rel, key)


def test_class_b_lifecycle_schema_cannot_admit_current_state() -> None:
    """Class B: the schema may name the vocabulary, but must not admit a currentState instance."""
    schema = load("schema/lifecycle-state.schema.json")
    for dimension in ("designReview", "operationalComparatorUse", "runtimeEnforcement",
                      "modelCompatibility"):
        node = schema["properties"][dimension]
        assert "currentState" not in node["properties"], dimension
        assert "currentState" not in node["required"], dimension
        assert node["additionalProperties"] is False, dimension
    assert schema["properties"]["designReview"]["properties"]["allowedStates"]["const"] == [
        "pending-owner-review", "design-approved"]


def test_class_c_documentation_does_not_assert_current_state() -> None:
    """Class C: prose may name states; it may not present one as current repository fact."""
    readme = (GATE / "README.md").read_text(encoding="utf-8")
    assert "| Current state |" not in readme
    assert "records/lifecycle-state-record.json" in readme


def test_design_review_example_record_is_pending_and_digest_bound() -> None:
    record = load("records/design-review-record.example.json")
    assert record["recordRole"] == "illustrative-example"
    assert record["reviewStatus"] == "pending-owner-review"
    assert record["humanReviewOccurred"] is False
    assert record["designApproved"] is False
    assert record["reviewerRepresentation"] is None
    assert record["reviewTimestamp"] is None
    assert record["reviewedArtifactPath"].endswith("manifest.json")
    assert len(record["reviewedArtifactDigest"]) == 64
    assert len(record["doesNotEstablish"]) == 7
    for absent in ("approvalScope", "invariantsReviewed", "deferredFindings",
                   "authorizationEvidence"):
        assert absent not in record


def test_authoritative_design_review_record_is_approved_and_evidenced() -> None:
    """The committed authoritative record carries the owner decision for the bound digest."""
    record = load("records/design-review-record.json")
    assert record["recordRole"] == "authoritative"
    assert record["reviewStatus"] == "design-approved"
    assert record["humanReviewOccurred"] is True
    assert record["designApproved"] is True
    assert record["reviewerRepresentation"] == APPROVED_REVIEWER_REPRESENTATION
    assert record["reviewTimestamp"] == APPROVAL_TIMESTAMP
    assert record["scopeOfDecision"] == APPROVED_SCOPE_OF_DECISION
    assert record["approvalScope"] == "gate2a-semantic-design"
    assert record["invariantsReviewed"] == ["X-8"]
    assert record["deferredFindings"] == ["F-6", "F-7", "F-8", "F-9"]

    evidence = record["authorizationEvidence"]
    assert evidence["evidenceKind"] == "private-approval-artifact-sha256"
    assert evidence["artifactSha256"] == APPROVAL_ARTIFACT_SHA256
    assert evidence["statement"] == APPROVED_EVIDENCE_STATEMENT

    # Approval changes what is authorized; it changes none of the non-authorizations.
    assert record["doesNotEstablish"] == CANONICAL_DOES_NOT_ESTABLISH
    assert len(record["nonAuthorizations"]) == 7
    assert all(value is False for value in record["nonAuthorizations"].values())


def test_manifest_membership_is_explicit_and_complete() -> None:
    manifest = load("manifest.json")
    listed = set(manifest["includedFiles"])
    expected = set()
    for subdirectory in MANIFEST_DIRS:
        for path in (GATE / subdirectory).glob("*.json"):
            expected.add(f"auditors/problem-evidence/gate2a/{subdirectory}/{path.name}")
    for document in MANIFEST_DOCS:
        expected.add(f"auditors/problem-evidence/gate2a/{document}")
    assert listed == expected, sorted(listed ^ expected)
    assert "auditors/problem-evidence/gate2a/PROVENANCE-QUESTIONS.md" in listed
    assert "auditors/problem-evidence/gate2a/README.md" in listed
    excluded_list = [e["path"] for e in manifest["exclusions"]]
    excluded = set(excluded_list)
    assert len(excluded_list) == len(excluded), "exclusion paths must be unique"
    assert excluded == set(EXCLUSION_PATHS)
    assert all(e["reason"] for e in manifest["exclusions"])
    assert not any(path in listed for path in excluded)
    for path in excluded_list:
        assert (ROOT / path).is_file(), f"excluded path must exist on disk: {path}"


def test_package_digest_recomputes_and_every_detached_record_binds_it() -> None:
    manifest = load("manifest.json")
    files = compute_member_digests()
    assert files == manifest["includedFiles"], "per-file digests must be current"
    expected = compute_package_digest(files)
    assert manifest["packageDigest"] == expected
    assert load("records/design-review-record.json")["reviewedArtifactDigest"] == expected
    assert load("records/lifecycle-state-record.json")["governedArtifactDigest"] == expected
    assert load("records/design-review-record.example.json")["reviewedArtifactDigest"] == expected
    assert load("records/bridge-authority-record.example.json")["governedArtifactDigest"] == expected
    assert load("records/classification-authority-record.example.json")[
        "governedArtifactDigest"] == expected


def test_lifecycle_contract_declares_dimensions_without_state() -> None:
    lifecycle = load("contracts/lifecycle-state.json")
    assert lifecycle["stateRecordPath"].endswith("records/lifecycle-state-record.json")
    assert lifecycle["designReview"]["stateHeldExternally"] is True
    assert lifecycle["designReview"]["allowedStates"] == ["pending-owner-review", "design-approved"]
    assert lifecycle["operationalComparatorUse"]["changeableByGate2AP"] is False
    assert lifecycle["runtimeEnforcement"]["changeableByGate2AP"] is False
    assert lifecycle["modelCompatibility"]["changeableByGate2AP"] is False
    assert lifecycle["formalPhase1Acceptance"]["representedAsRepositoryState"] is False
    for dimension in ("designReview", "operationalComparatorUse", "runtimeEnforcement",
                      "modelCompatibility"):
        assert "currentState" not in lifecycle[dimension], dimension


def test_lifecycle_record_holds_state_and_non_design_dimensions_stay_closed() -> None:
    record = load("records/lifecycle-state-record.json")
    assert record["designReview"]["currentState"] == "design-approved"
    assert record["designReview"]["currentState"] in record["designReview"]["allowedStates"]
    assert record["operationalComparatorUse"]["currentState"] == "prohibited"
    assert record["runtimeEnforcement"]["currentState"] == "disabled"
    assert record["modelCompatibility"]["currentState"] == "unresolved-offline"
    assert record["formalPhase1Acceptance"]["representedAsRepositoryState"] is False


def test_x4_is_a_digest_transfer_invariant() -> None:
    invariants = {i["id"]: i for i in load("contracts/lifecycle-state.json")["crossDimensionalInvariants"]}
    x4 = invariants["X-4"]
    assert x4["enforcedBy"] == "deterministic-cross-document"
    assert "does not approve or supersede a different package digest" in x4["invariant"]
    assert "superseded" not in json.dumps(load("contracts/lifecycle-state.json")).replace(
        "supersede a different", "")


def test_semantic_invariants_are_declared_human_review_not_deterministic() -> None:
    invariants = load("contracts/lifecycle-state.json")["crossDimensionalInvariants"]
    by_id = {i["id"]: i for i in invariants}
    assert by_id["X-8"]["enforcedBy"] == "human-review"
    assert any(i["enforcedBy"] == "deterministic-cross-document" for i in invariants)
    assert any(i["enforcedBy"] == "json-schema" for i in invariants)


def test_gate_1_artifacts_are_not_referenced_as_authoritative_traceability() -> None:
    trace = load("statements/traceability-map.json")
    assert trace["traceabilityKey"] == "sourceStatementId"
    assert trace["semanticCriteriaIdsAuthoritative"] is False
    assert "semanticCriteriaIds" not in json.dumps(load("statements/atomic-behavior-rules.json"))


# ===================================================================== F-1: first Gate 2A-F batch
F1_STATEMENTS = ("SS-004", "SS-009", "SS-010", "SS-027", "SS-028", "SS-039")
F1_ORDER = ("SS-004", "SS-006", "SS-009", "SS-010", "SS-026", "SS-027", "SS-028",
            "SS-033", "SS-034", "SS-039", "SS-055", "SS-060", "SS-070")
FUTURE_DEMAND_FAMILY = ("SS-056", "SS-085", "SS-087")


def frozen_statements() -> list[tuple[str, str, str, str]]:
    """The 87 frozen statements in the repository's canonical order."""
    policy = json.loads(POLICY.read_text())
    ordered: list[tuple[str, str, str, str]] = []
    for fixture_name in ("contradictory-evidence.json", "missing-evidence.json",
                         "strong-evidence.json"):
        block = next(f for f in policy["fixtures"] if f["fixture"] == fixture_name)
        for requirement in block["requirements"]:
            for text in requirement["requiredVerificationBehavior"]:
                ordered.append((fixture_name, requirement["requirementId"],
                                "requiredVerificationBehavior", text))
            for text in requirement["prohibitedSubstitutions"]:
                ordered.append((fixture_name, requirement["requirementId"],
                                "prohibitedSubstitution", text))
    return ordered


def test_f1_added_exactly_the_six_authorized_statements(records) -> None:
    present = {r["sourceStatementId"] for r in records}
    assert set(F1_STATEMENTS) <= present
    assert present == set(F1_ORDER), sorted(present ^ set(F1_ORDER))


def test_f1_statements_carry_the_exact_frozen_metadata(records) -> None:
    """Fixture, requirement, type, wording and stable number, all read from the frozen policy."""
    ordered = frozen_statements()
    expected = {
        "SS-004": ("contradictory-evidence.json", "REQ-1", "prohibitedSubstitution"),
        "SS-009": ("contradictory-evidence.json", "REQ-2", "prohibitedSubstitution"),
        "SS-010": ("contradictory-evidence.json", "REQ-2", "prohibitedSubstitution"),
        "SS-027": ("contradictory-evidence.json", "REQ-5", "prohibitedSubstitution"),
        "SS-028": ("contradictory-evidence.json", "REQ-5", "prohibitedSubstitution"),
        "SS-039": ("missing-evidence.json", "REQ-2", "prohibitedSubstitution"),
    }
    by_id = {r["sourceStatementId"]: r for r in records}
    for statement_id, (fixture, requirement_id, statement_type) in expected.items():
        record = by_id[statement_id]
        assert record["v15Index"] == int(statement_id[3:])
        assert (record["fixture"], record["requirementId"], record["statementType"]) == (
            fixture, requirement_id, statement_type)
        assert record["statementText"] == ordered[record["v15Index"] - 1][3]


def test_f1_statement_digests_reconcile(records) -> None:
    ordered = frozen_statements()
    for record in records:
        fixture, requirement_id, statement_type, text = ordered[record["v15Index"] - 1]
        expected = hashlib.sha256(json.dumps(
            {"fixture": fixture, "requirementId": requirement_id,
             "statementType": statement_type, "statement": text},
            sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
        assert record["statementDigest"] == expected, record["sourceStatementId"]
    assert len({r["statementDigest"] for r in records}) == len(records)


def test_f1_records_stay_in_canonical_stable_number_order(records) -> None:
    ids = [r["sourceStatementId"] for r in records]
    assert ids == list(F1_ORDER)
    assert [r["v15Index"] for r in records] == sorted(r["v15Index"] for r in records)
    assert len(set(ids)) == len(ids)


def test_f1_accounting_is_thirteen_represented_and_seventy_four_remaining() -> None:
    report = load("statements/coverage-report.json")
    totals = report["statementTotals"]
    assert totals["selected"] == totals["recordsCreated"] == 13
    assert totals["statementsRemaining"] == 74
    assert totals["recordsCreated"] + totals["statementsRemaining"] == FROZEN_STATEMENT_TOTAL
    assert report["scope"] == "expansion-in-progress"
    assert report["fullSetAtomicRuleTotal"] == "unknown"
    for rel in SCOPE_BEARING:
        assert load(rel)["scope"] == "expansion-in-progress", rel


def test_f1_full_set_scope_is_rejected_while_statements_remain() -> None:
    """74 statements remain, so full-set-87 must not be emittable."""
    package = load_package()
    assert scope_and_count_violations(package) == []
    falsified = _with_scope(package, "full-set-87")
    assert "SCOPE_DOES_NOT_MATCH_N" in scope_and_count_violations(falsified)


def test_f1_new_parts_and_rules_close_referentially(parts, rules, records) -> None:
    statement_ids = {r["sourceStatementId"] for r in records}
    part_ids = {p["obligationPartId"] for p in parts}
    rule_ids = {r["ruleId"] for r in rules}
    new_parts = [p for p in parts if p["sourceStatementId"] in F1_STATEMENTS]
    assert len(new_parts) == 11
    for part in new_parts:
        assert part["sourceStatementId"] in statement_ids
        assert set(part["dependsOn"]) <= part_ids
        assert part["coverageState"] == "rule-covered"
    new_rules = [r for r in rules if r["primaryObligationPart"] in
                 {p["obligationPartId"] for p in new_parts}]
    assert len(new_rules) == 11
    assert len({r["ruleId"] for r in new_rules}) == 11
    assert {r["ruleId"] for r in new_rules} <= rule_ids
    for rule in new_rules:
        assert set(rule["supportingObligationParts"]) <= part_ids


def test_f1_source_clauses_are_verbatim_substrings_of_their_statements(parts, records) -> None:
    by_id = {r["sourceStatementId"]: r for r in records}
    checked = 0
    for part in parts:
        if part["sourceStatementId"] in F1_STATEMENTS \
                and part["derivationBasis"] == "source_obligation":
            statement = by_id[part["sourceStatementId"]]["statementText"]
            assert part["sourceClauseReference"] in statement, part["obligationPartId"]
            checked += 1
    assert checked == 6, "one source-obligation part per new statement"


def test_f1_derivation_basis_and_result_class_agree(parts, rules) -> None:
    by_part = {p["obligationPartId"]: p for p in parts}
    for rule in rules:
        part = by_part[rule["primaryObligationPart"]]
        if part["sourceStatementId"] not in F1_STATEMENTS:
            continue
        assert rule["derivationBasis"] == part["derivationBasis"], rule["ruleId"]
        assert rule["resultClass"] == RESULT_CLASS[rule["derivationBasis"]], rule["ruleId"]
        key = rule["resultClass"]
        if key == "normative" and rule["hasAntecedent"]:
            key = "normative_conditional"
        assert set(rule["expectedOutcomes"]) == ALLOWED_RESULTS[key], rule["ruleId"]
        assert rule["countsAsSourceDerivedCoverage"] is (
            rule["derivationBasis"] == "source_obligation")
        assert rule["canProduceProductFinding"] is (
            rule["derivationBasis"] == "source_obligation")


def test_f1_preserves_identity_i5(parts, rules) -> None:
    """atomic-rule count == rule-covered obligation-part count, before and after the batch."""
    rule_covered = [p for p in parts if p["coverageState"] == "rule-covered"]
    assert len(rule_covered) == len(rules) == 33
    assert {p["obligationPartId"] for p in rule_covered} == {
        r["primaryObligationPart"] for r in rules}


def test_f1_leaves_no_orphans(parts, rules, records) -> None:
    statement_ids = {r["sourceStatementId"] for r in records}
    part_ids = {p["obligationPartId"] for p in parts}
    assert {p["sourceStatementId"] for p in parts} <= statement_ids
    assert {r["primaryObligationPart"] for r in rules} <= part_ids
    for edge in load("statements/traceability-map.json")["edges"]:
        assert edge["sourceStatementId"] in statement_ids
        assert edge["obligationPartId"] in part_ids
        if edge["ruleId"] is not None:
            assert edge["ruleId"] in {r["ruleId"] for r in rules}


def test_f1_recorded_totals_equal_independently_derived_totals(parts, rules, records) -> None:
    report = load("statements/coverage-report.json")
    states = Counter(p["coverageState"] for p in parts)
    derivations = Counter(p["derivationBasis"] for p in parts)
    rule_derivations = Counter(r["derivationBasis"] for r in rules)
    ob, ru = report["obligationTotals"], report["ruleTotals"]
    assert ob["identified"] == len(parts) == 46
    assert ob["sourceObligation"] == derivations["source_obligation"] == 27
    assert ob["evaluationPrecondition"] == derivations["evaluation_precondition"] == 11
    assert ob["evaluationProxy"] == derivations["evaluation_proxy"] == 8
    assert ob["ruleCovered"] == states["rule-covered"] == 33
    assert ru["proposed"] == len(rules) == 33
    assert ru["sourceDerivedExecutableRuleCoverage"] == rule_derivations["source_obligation"] == 18
    assert ru["preconditionRules"] == rule_derivations["evaluation_precondition"] == 7
    assert ru["proxyRules"] == rule_derivations["evaluation_proxy"] == 8
    assert report["evaluatorMaturity"]["mechanismDefined"] == len(rules)
    assert sum(report["statementClassification"].values()) == len(records) == 13


def test_f1_manifest_membership_and_exclusions_are_unchanged() -> None:
    manifest = load("manifest.json")
    assert len(manifest["includedFiles"]) == 23
    assert len(manifest["exclusions"]) == 7
    assert manifest["contractVersion"] == CONTRACT_VERSION
    assert manifest["packageVersion"] == PACKAGE_VERSION


def test_only_design_review_advanced_every_other_authority_is_unchanged() -> None:
    """Design review is approved. Nothing else moved, and the illustrative example never moves."""
    assert load("records/design-review-record.json")["reviewStatus"] == "design-approved"
    assert load("records/design-review-record.example.json")["reviewStatus"] == \
        "pending-owner-review"
    assert load("records/bridge-authority-record.example.json")["authorityStatus"] == "not-granted"
    assert load("records/classification-authority-record.example.json")["authorityStatus"] == \
        "not-approved"


def test_f1_versions_are_unchanged(rules) -> None:
    for rel in ("statements/source-statement-records.json", "statements/obligation-parts.json",
                "statements/atomic-behavior-rules.json", "statements/traceability-map.json",
                "statements/coverage-report.json"):
        assert load(rel)["contractVersion"] == CONTRACT_VERSION, rel
    assert {r["ruleVersion"] for r in rules} == {"0.13.0-draft"}


F1_MUTATIONS = [
    ("drop-a-new-record", lambda p: _drop_record(p, "SS-027")),
    ("drop-a-new-part", lambda p: _drop_part(p, "OP-027-a")),
    ("drop-a-new-edge", lambda p: _drop_edge(p, "OP-027-a")),
    ("stale-thirteen-remaining", lambda p: _totals(p, statementsRemaining=80)),
    ("scope-left-at-pilot", lambda p: _with_scope(p, "pilot-subset")),
]


def _drop_record(package: dict, statement_id: str) -> dict:
    pkg = copy.deepcopy(package)
    doc = pkg["statements/source-statement-records.json"]
    doc["records"] = [r for r in doc["records"] if r["sourceStatementId"] != statement_id]
    return pkg


def _drop_part(package: dict, part_id: str) -> dict:
    pkg = copy.deepcopy(package)
    doc = pkg["statements/obligation-parts.json"]
    doc["parts"] = [p for p in doc["parts"] if p["obligationPartId"] != part_id]
    return pkg


def _drop_edge(package: dict, part_id: str) -> dict:
    pkg = copy.deepcopy(package)
    doc = pkg["statements/traceability-map.json"]
    doc["edges"] = [e for e in doc["edges"] if e["obligationPartId"] != part_id]
    return pkg


@pytest.mark.parametrize("label,mutate", F1_MUTATIONS, ids=[c[0] for c in F1_MUTATIONS])
def test_f1_accounting_mutations_are_caught(label, mutate) -> None:
    assert scope_and_count_violations(load_package()) == [], "baseline must be clean"
    falsified = mutate(load_package())
    if label == "drop-a-new-edge":
        # a dropped edge does not change N; it breaks the traceability path instead
        edges = falsified["statements/traceability-map.json"]["edges"]
        assert not any(e["obligationPartId"] == "OP-027-a" for e in edges)
        assert any(e["obligationPartId"] == "OP-027-a"
                   for e in load("statements/traceability-map.json")["edges"])
    elif label == "drop-a-new-part":
        parts = falsified["statements/obligation-parts.json"]["parts"]
        rules = load("statements/atomic-behavior-rules.json")["rules"]
        covered = {p["obligationPartId"] for p in parts if p["coverageState"] == "rule-covered"}
        assert {r["primaryObligationPart"] for r in rules} != covered, "I5 must break"
    else:
        assert scope_and_count_violations(falsified) != [], label


# ------------------------------------------------------- owner decision D2: SS-026 versus SS-027
def test_d2_ss_026_and_ss_027_remain_separate_records(records) -> None:
    by_id = {r["sourceStatementId"]: r for r in records}
    assert "SS-026" in by_id and "SS-027" in by_id
    assert by_id["SS-026"]["v15Index"] == 26 and by_id["SS-027"]["v15Index"] == 27
    assert by_id["SS-026"]["statementText"] != by_id["SS-027"]["statementText"]
    assert by_id["SS-026"]["statementDigest"] != by_id["SS-027"]["statementDigest"]


def test_d2_each_statement_owns_its_source_obligation_part(parts) -> None:
    for statement_id, part_id in (("SS-026", "OP-026-a"), ("SS-027", "OP-027-a")):
        owned = [p for p in parts if p["sourceStatementId"] == statement_id
                 and p["derivationBasis"] == "source_obligation"]
        assert [p["obligationPartId"] for p in owned] == [part_id]


def test_d2_each_rule_covered_part_owns_exactly_one_rule(parts, rules) -> None:
    for statement_id in ("SS-026", "SS-027"):
        owned = [p["obligationPartId"] for p in parts
                 if p["sourceStatementId"] == statement_id and p["coverageState"] == "rule-covered"]
        assert len(owned) == 2
        for part_id in owned:
            matching = [r for r in rules if r["primaryObligationPart"] == part_id]
            assert len(matching) == 1, part_id


def test_d2_neither_statement_reuses_the_others_identifiers(parts, rules) -> None:
    ss026_parts = {p["obligationPartId"] for p in parts if p["sourceStatementId"] == "SS-026"}
    ss027_parts = {p["obligationPartId"] for p in parts if p["sourceStatementId"] == "SS-027"}
    assert ss026_parts == {"OP-026-a", "OP-026-b"}
    assert ss027_parts == {"OP-027-a", "OP-027-b"}
    assert not (ss026_parts & ss027_parts)
    ss026_rules = {r["ruleId"] for r in rules if r["primaryObligationPart"] in ss026_parts}
    ss027_rules = {r["ruleId"] for r in rules if r["primaryObligationPart"] in ss027_parts}
    assert not (ss026_rules & ss027_rules)
    # neither rule may reach into the other statement's parts, in any role
    for rule in rules:
        if rule["primaryObligationPart"] in ss026_parts:
            assert not (set(rule["supportingObligationParts"]) & ss027_parts), rule["ruleId"]
        if rule["primaryObligationPart"] in ss027_parts:
            assert not (set(rule["supportingObligationParts"]) & ss026_parts), rule["ruleId"]


def test_d2_both_source_clauses_are_verbatim(parts, records) -> None:
    by_id = {r["sourceStatementId"]: r["statementText"] for r in records}
    for statement_id, part_id in (("SS-026", "OP-026-a"), ("SS-027", "OP-027-a")):
        part = next(p for p in parts if p["obligationPartId"] == part_id)
        assert part["sourceClauseReference"] in by_id[statement_id], part_id


def test_d2_both_traceability_paths_close_independently() -> None:
    edges = load("statements/traceability-map.json")["edges"]
    for statement_id, primaries in (("SS-026", {"OP-026-a", "OP-026-b"}),
                                    ("SS-027", {"OP-027-a", "OP-027-b"})):
        owned = [e for e in edges if e["sourceStatementId"] == statement_id]
        assert {e["obligationPartId"] for e in owned if e["role"] == "primary"} == primaries
        assert all(e["ruleId"] for e in owned if e["role"] in ("primary", "supporting"))
        # no edge of one statement may name the other statement's part
        other = {"SS-026": "OP-027", "SS-027": "OP-026"}[statement_id]
        assert not any(e["obligationPartId"].startswith(other) for e in owned)


def test_d2_overlap_does_not_break_uniqueness_or_identity_i5(parts, rules) -> None:
    part_ids = [p["obligationPartId"] for p in parts]
    rule_ids = [r["ruleId"] for r in rules]
    assert len(part_ids) == len(set(part_ids))
    assert len(rule_ids) == len(set(rule_ids))
    rule_covered = {p["obligationPartId"] for p in parts if p["coverageState"] == "rule-covered"}
    assert rule_covered == {r["primaryObligationPart"] for r in rules}


def test_d2_ss_027_is_not_narrowed_to_willingness_to_pay(parts, rules) -> None:
    part = next(p for p in parts if p["obligationPartId"] == "OP-027-a")
    text = f"{part['normativeObligation']} {part['observableInvariant']}".lower()
    assert "demand for the proposed product" in text or "demand for a proposed product" in text
    assert "willingness to pay" not in part["normativeObligation"].lower()
    assert "willingness to pay" not in part["observableInvariant"].lower()
    rule = next(r for r in rules if r["primaryObligationPart"] == "OP-027-a")
    assert any("PROPOSED_PRODUCT_DEMAND" in code for code in rule["outcomeCodes"])
    assert not any("WTP" in code for code in rule["outcomeCodes"])


def test_d2_ss_026_is_not_broadened_beyond_willingness_to_pay(parts, rules) -> None:
    part = next(p for p in parts if p["obligationPartId"] == "OP-026-a")
    assert "willingness-to-pay" in part["observableInvariant"].lower()
    assert "demand" not in part["observableInvariant"].lower()
    rule = next(r for r in rules if r["primaryObligationPart"] == "OP-026-a")
    assert rule["outcomeCodes"] == ["WTP_SUBSTITUTED_FOR_COMMITMENT", "WTP_CLASSIFICATION_INCOMPLETE"]


def test_d2_intentional_redundancy_is_stated_not_silent(parts) -> None:
    part = next(p for p in parts if p["obligationPartId"] == "OP-027-a")
    joined = " ".join(part["knownLimitations"]).lower()
    assert "d2" in joined
    assert "op-026-a" in joined


def test_d2_removing_either_side_breaks_reconciliation(parts, rules, records) -> None:
    for statement_id, part_id, rule_id in (
            ("SS-026", "OP-026-a", "BR-026-no-wtp-substitution"),
            ("SS-027", "OP-027-a", "BR-027-no-proposed-product-demand-as-commitment")):
        remaining_records = [r for r in records if r["sourceStatementId"] != statement_id]
        assert len(remaining_records) == len(records) - 1
        surviving = {r["sourceStatementId"] for r in remaining_records}
        assert any(p["sourceStatementId"] not in surviving for p in parts), statement_id
        remaining_parts = [p for p in parts if p["obligationPartId"] != part_id]
        covered = {p["obligationPartId"] for p in remaining_parts
                   if p["coverageState"] == "rule-covered"}
        assert {r["primaryObligationPart"] for r in rules} != covered, part_id
        remaining_rules = [r for r in rules if r["ruleId"] != rule_id]
        covered_all = {p["obligationPartId"] for p in parts if p["coverageState"] == "rule-covered"}
        assert {r["primaryObligationPart"] for r in remaining_rules} != covered_all, rule_id
        edges = [e for e in load("statements/traceability-map.json")["edges"]
                 if e["sourceStatementId"] == statement_id]
        assert edges and all(e["obligationPartId"].startswith(f"OP-{statement_id[3:]}")
                             for e in edges)


def test_d2_future_demand_family_statements_stay_unrepresented(parts, rules, records) -> None:
    """D2 was selected for SS-026/SS-027 only; SS-056, SS-085 and SS-087 remain unscheduled."""
    present = {r["sourceStatementId"] for r in records}
    for statement_id in FUTURE_DEMAND_FAMILY:
        assert statement_id not in present, statement_id
        assert not any(p["sourceStatementId"] == statement_id for p in parts), statement_id
        index = statement_id[3:]
        assert not any(p["obligationPartId"].startswith(f"OP-{index}") for p in parts), statement_id
        assert not any(r["primaryObligationPart"].startswith(f"OP-{index}")
                       for r in rules), statement_id
        assert not any(e["sourceStatementId"] == statement_id
                       for e in load("statements/traceability-map.json")["edges"]), statement_id


# ------------------------------------ documentation consistency: gate2a/README.md prose versus data
# A package whose JSON reconciles perfectly can still tell a human reader the wrong number. Every
# value below is derived from the artifacts; the README is checked against it, never the reverse.
NUMBER_WORDS = {"Three": 3, "Four": 4, "Five": 5, "Six": 6, "Seven": 7, "Eight": 8}


def test_gate2a_readme_prose_matches_the_derived_artifact_totals(parts, rules) -> None:
    import re

    readme = (GATE / "README.md").read_text(encoding="utf-8")
    report = load("statements/coverage-report.json")
    part_ids = {p["obligationPartId"] for p in parts}
    rule_ids = {r["ruleId"] for r in rules}

    # every identifier the prose names must exist: this is what a dangling OP-055-h looks like
    named_parts = set(re.findall(r"OP-\d{3}-[a-z]", readme))
    named_rules = set(re.findall(r"BR-\d{3}-[a-z0-9-]+?(?=[`\s,.])", readme))
    assert named_parts <= part_ids, sorted(named_parts - part_ids)
    assert named_rules <= rule_ids, sorted(named_rules - rule_ids)

    # rule-count claims, derived rather than restated
    governed = report["findingPolicyAccounting"]["reviewPolicyGovernsRuleDefinitions"]
    finding_capable = sum(1 for r in rules if r["canProduceProductFinding"])
    assert governed == len(rules)
    assert finding_capable == report["findingPolicyAccounting"][
        "normativeRuleDesignsCapableOfProductFindings"]
    assert f"**{governed}** rule definitions are governed by the review policy" in readme
    assert f"**{finding_capable}** rule designs can actually produce a reviewable product finding" \
        in readme

    # The human-review claim is checked as an isolated block. Asking only whether an ID appears
    # somewhere in the README would pass a bullet that dropped one, added one, or miscounted.
    human = [p for p in parts if p["coverageState"] == "human-review-obligation"]
    human_parts = {p["obligationPartId"] for p in human}
    assert len(human_parts) == 4, sorted(human_parts)
    assert all(p["derivationBasis"] == "evaluation_precondition" for p in human), \
        sorted((p["obligationPartId"], p["derivationBasis"]) for p in human)
    assert report["sourceObligationCoverage"]["humanRequiredDispositions"] == 0

    # isolate the bullet: from its declared count up to the start of the governed-rule bullet
    bullet = re.search(
        r"- \*\*(\d+)\*\* parts require human judgment"
        r"(.*?)(?=- \*\*\d+\*\* rule definitions are governed)",
        readme, re.S)
    assert bullet is not None, "human-judgment bullet not found in README"
    declared_count, block = int(bullet.group(1)), bullet.group(2)
    listed = set(re.findall(r"OP-\d{3}-[a-z]", block))

    assert declared_count == len(human_parts), (declared_count, sorted(human_parts))
    assert listed == human_parts, sorted(listed ^ human_parts)
    assert "none of them is a source obligation" in block
    stated_source = re.search(
        r"Source\s+obligations with a human-required disposition: \*\*(\d+)\*\*", block)
    assert stated_source is not None, "the bullet must state its source-obligation count"
    assert int(stated_source.group(1)) == \
        report["sourceObligationCoverage"]["humanRequiredDispositions"]

    # the SS-006 credibility sentence must name both authoritative fields, read from the artifact
    op_006_g = next(p for p in parts if p["obligationPartId"] == "OP-006-g")
    statement = re.search(r"`OP-006-g` \(credibility\)(.*?)\.\s", readme, re.S)
    assert statement is not None, "OP-006-g credibility statement not found in README"
    stated_basis = re.search(r"derivation basis `([a-z_]+)`", statement.group(1))
    stated_state = re.search(r"coverage state\s+`([a-z-]+)`", statement.group(1))
    assert stated_basis is not None and stated_state is not None, statement.group(1)
    assert stated_basis.group(1) == op_006_g["derivationBasis"], stated_basis.group(1)
    assert stated_state.group(1) == op_006_g["coverageState"], stated_state.group(1)

    # the antecedent enumeration must be complete and correctly counted
    sentence = re.search(r"(\w+) rules declare antecedents:(.*?)\.\n", readme, re.S)
    assert sentence is not None, "antecedent enumeration missing from README"
    antecedent = {r["ruleId"] for r in rules if r["hasAntecedent"]}
    assert NUMBER_WORDS[sentence.group(1)] == len(antecedent), sentence.group(1)
    assert set(re.findall(r"BR-\d{3}-[a-z0-9-]+?(?=[`\s,.])", sentence.group(2))) == antecedent


# ------------------------------------------------------------------ cross-record integrity
# JSON Schema validates one document at a time. Every rule below is a relation BETWEEN documents,
# so none of them can live in a schema. Signature verification is deliberately absent: a git
# signature is not a property of JSON and belongs to a separate repository-level check.

CANONICAL_DOES_NOT_ESTABLISH = [
    "Formal Phase 1 acceptance",
    "Gate 2C model-compatibility approval",
    "Bridge authority",
    "Classification authority",
    "Runtime enforcement",
    "Operational comparator use",
    "Production readiness",
]
NON_AUTHORIZATION_KEYS = [
    "grantsFormalPhase1Acceptance",
    "grantsGate2CModelCompatibility",
    "grantsBridgeAuthority",
    "grantsClassificationAuthority",
    "enablesRuntimeEnforcement",
    "permitsOperationalComparatorUse",
    "impliesProductionReadiness",
]
APPROVED_INVARIANTS = ["X-8"]
APPROVED_DEFERRALS = ["F-6", "F-7", "F-8", "F-9"]
ACCEPTED_EVIDENCE_KIND = "private-approval-artifact-sha256"
MANIFEST_PATH = "auditors/problem-evidence/gate2a/manifest.json"

CROSS_RECORD_CODES = {
    "DIGEST_BINDING_MISMATCH",
    "PATH_BINDING_MISMATCH",
    "VERSION_BINDING_MISMATCH",
    "VERSION_NOT_DERIVED_FROM_MANIFEST",
    "LIFECYCLE_PENDING_WITH_APPROVED_REVIEW",
    "LIFECYCLE_APPROVED_WITHOUT_APPROVED_REVIEW",
    "AUTHORITATIVE_RECORD_NOT_EXACTLY_ONE",
    "DERIVATION_REFERENCE_MISMATCH",
    "INVARIANT_SCOPE_NOT_EXACTLY_X8",
    "DEFERRAL_SET_NOT_EXACTLY_F6_F9",
    "NON_AUTHORIZATION_TRUE",
    "NON_DESIGN_DIMENSION_CHANGED",
    "CURRENT_STATE_NOT_IN_ALLOWED_STATES",
    "DIGEST_MEMBER_ASSERTS_MUTABLE_STATE",
    "EXCLUSION_SET_MISMATCH",
    "EXCLUDED_FILE_MISSING",
    "AUTHORIZATION_EVIDENCE_INVALID",
    "AUTHORIZATION_EVIDENCE_INSUFFICIENT_FOR_APPROVAL",
    "PROSE_FIELD_NOT_CANONICAL",
}


def cross_record_violations(bundle: dict) -> list[str]:
    """Pure deterministic cross-document validator. Returns sorted stable violation codes.

    No filesystem, no git, no clock: everything it needs is in the bundle.
    """
    codes: set[str] = set()
    manifest = bundle["manifest"]
    lifecycle = bundle["lifecycle_record"]
    reviews = bundle["review_records"]
    digest = bundle["recomputed_digest"]
    package_version = manifest.get("packageVersion")

    detached = [("lifecycle", lifecycle, "governedArtifactDigest", "governedArtifactPath",
                 "governedArtifactVersion")]
    for record in reviews:
        detached.append((record.get("recordId"), record, "reviewedArtifactDigest",
                         "reviewedArtifactPath", "reviewedArtifactVersion"))

    for _name, record, digest_key, path_key, version_key in detached:
        if record.get(digest_key) != digest:
            codes.add("DIGEST_BINDING_MISMATCH")
        if record.get(path_key) != MANIFEST_PATH:
            codes.add("PATH_BINDING_MISMATCH")
        if version_key in record and record.get(version_key) != package_version:
            codes.add("VERSION_NOT_DERIVED_FROM_MANIFEST")

    authoritative = [r for r in reviews if r.get("recordRole") == "authoritative"]
    if len(authoritative) != 1:
        codes.add("AUTHORITATIVE_RECORD_NOT_EXACTLY_ONE")

    if authoritative:
        primary = authoritative[0]
        if primary.get("reviewedArtifactVersion") != lifecycle.get("governedArtifactVersion"):
            codes.add("VERSION_BINDING_MISMATCH")
        if primary.get("reviewedArtifactDigest") != lifecycle.get("governedArtifactDigest"):
            codes.add("DIGEST_BINDING_MISMATCH")

        design = lifecycle.get("designReview", {})
        if design.get("derivedFromRecordId") != primary.get("recordId"):
            codes.add("DERIVATION_REFERENCE_MISMATCH")

        current = design.get("currentState")
        approved = primary.get("reviewStatus") == "design-approved"
        if current == "pending-owner-review" and approved:
            codes.add("LIFECYCLE_PENDING_WITH_APPROVED_REVIEW")
        if current == "design-approved" and not approved:
            codes.add("LIFECYCLE_APPROVED_WITHOUT_APPROVED_REVIEW")
        if current not in design.get("allowedStates", []):
            codes.add("CURRENT_STATE_NOT_IN_ALLOWED_STATES")

        # Approval-only obligations. Conditional by design: a pending baseline must never be
        # required to carry fields that are valid only after approval.
        if approved:
            if primary.get("invariantsReviewed") != APPROVED_INVARIANTS:
                codes.add("INVARIANT_SCOPE_NOT_EXACTLY_X8")
            if primary.get("deferredFindings") != APPROVED_DEFERRALS:
                codes.add("DEFERRAL_SET_NOT_EXACTLY_F6_F9")
            evidence = primary.get("authorizationEvidence")
            if not isinstance(evidence, dict) or "artifactSha256" not in evidence \
                    or "statement" not in evidence:
                codes.add("AUTHORIZATION_EVIDENCE_INVALID")
            elif evidence.get("evidenceKind") != ACCEPTED_EVIDENCE_KIND:
                codes.add("AUTHORIZATION_EVIDENCE_INSUFFICIENT_FOR_APPROVAL")
            if not primary.get("reviewerRepresentation") or not primary.get("reviewTimestamp"):
                codes.add("AUTHORIZATION_EVIDENCE_INVALID")
        else:
            for approval_only in ("approvalScope", "invariantsReviewed", "deferredFindings",
                                  "authorizationEvidence"):
                if approval_only in primary:
                    codes.add("AUTHORIZATION_EVIDENCE_INVALID")

    for record in reviews:
        non_auth = record.get("nonAuthorizations", {})
        if any(non_auth.get(key) is not False for key in NON_AUTHORIZATION_KEYS):
            codes.add("NON_AUTHORIZATION_TRUE")
        if record.get("doesNotEstablish") != CANONICAL_DOES_NOT_ESTABLISH:
            codes.add("PROSE_FIELD_NOT_CANONICAL")
        if len(CANONICAL_DOES_NOT_ESTABLISH) != len(NON_AUTHORIZATION_KEYS):
            codes.add("PROSE_FIELD_NOT_CANONICAL")

    pinned = {"operationalComparatorUse": "prohibited", "runtimeEnforcement": "disabled",
              "modelCompatibility": "unresolved-offline"}
    for dimension, expected in pinned.items():
        if lifecycle.get(dimension, {}).get("currentState") != expected:
            codes.add("NON_DESIGN_DIMENSION_CHANGED")
    if lifecycle.get("formalPhase1Acceptance", {}).get("representedAsRepositoryState") is not False:
        codes.add("NON_DESIGN_DIMENSION_CHANGED")

    for rel, document in bundle["member_instances"].items():
        for key in walk_keys(document):
            if key in MUTABLE_STATE_KEYS:
                codes.add("DIGEST_MEMBER_ASSERTS_MUTABLE_STATE")

    exclusion_paths = [e["path"] for e in manifest.get("exclusions", [])]
    if sorted(exclusion_paths) != sorted(EXCLUSION_PATHS) \
            or len(exclusion_paths) != len(set(exclusion_paths)):
        codes.add("EXCLUSION_SET_MISMATCH")
    for path in exclusion_paths:
        if path not in bundle["present_paths"]:
            codes.add("EXCLUDED_FILE_MISSING")

    return sorted(codes)


def build_bundle() -> dict:
    files = compute_member_digests()
    member_instances = {rel: load(rel) for rel, _ in PAIRS
                        if not rel.startswith("records/") and rel != "manifest.json"}
    return {
        "manifest": load("manifest.json"),
        "lifecycle_record": load("records/lifecycle-state-record.json"),
        "review_records": [load("records/design-review-record.json"),
                           load("records/design-review-record.example.json")],
        "member_instances": member_instances,
        "present_paths": {p for p in EXCLUSION_PATHS if (ROOT / p).is_file()},
        "recomputed_digest": compute_package_digest(files),
    }


@pytest.fixture()
def bundle() -> dict:
    return build_bundle()


def test_cross_record_baseline_is_clean(bundle) -> None:
    assert cross_record_violations(bundle) == []


def _primary(b: dict) -> dict:
    return next(r for r in b["review_records"] if r["recordRole"] == "authoritative")


def _revert_to_pending(record: dict) -> dict:
    """Turn an approved record into a COHERENT pending one.

    Not a status flip: a record left pending while still carrying approval-only fields would be
    caught by the pending-branch rule instead of the rule under test, so the mutation would prove
    the wrong thing. Non-authorizations are preserved because they are state-independent.
    """
    record["reviewStatus"] = "pending-owner-review"
    record["humanReviewOccurred"] = False
    record["designApproved"] = False
    record["reviewerRepresentation"] = None
    record["reviewTimestamp"] = None
    record["scopeOfDecision"] = PENDING_SCOPE_OF_DECISION
    for approval_only in ("approvalScope", "invariantsReviewed", "deferredFindings",
                          "authorizationEvidence"):
        record.pop(approval_only, None)
    return record


def _m_digest(b):        _primary(b)["reviewedArtifactDigest"] = "f" * 64; return b
def _m_path(b):          b["lifecycle_record"]["governedArtifactPath"] = "wrong/manifest.json"; return b
def _m_version_split(b): b["lifecycle_record"]["governedArtifactVersion"] = "9.9.9-draft"; return b
def _m_version_src(b):   b["manifest"]["packageVersion"] = "9.9.9-draft"; return b
def _m_pending_approved(b):
    b["lifecycle_record"]["designReview"]["currentState"] = "pending-owner-review"; return b
def _m_approved_no_record(b):
    _revert_to_pending(_primary(b)); return b
def _m_two_authoritative(b):
    b["review_records"][1]["recordRole"] = "authoritative"; return b
def _m_derivation(b):    b["lifecycle_record"]["designReview"]["derivedFromRecordId"] = "other"; return b
def _m_invariants(b):    _primary(b)["invariantsReviewed"] = ["X-8", "X-7"]; return b
def _m_deferrals(b):     _primary(b)["deferredFindings"] = ["F-6", "F-7", "F-8"]; return b
def _m_non_auth(b):
    _primary(b)["nonAuthorizations"]["enablesRuntimeEnforcement"] = True; return b
def _m_non_design(b):
    b["lifecycle_record"]["runtimeEnforcement"]["currentState"] = "enabled"; return b
def _m_allowed_states(b):
    b["lifecycle_record"]["designReview"]["allowedStates"] = ["pending-owner-review"]; return b
def _m_member_state(b):
    b["member_instances"]["contracts/lifecycle-state.json"]["designReview"]["currentState"] = "design-approved"
    return b
def _m_exclusions(b):
    b["manifest"]["exclusions"] = b["manifest"]["exclusions"][:-1]; return b
def _m_missing_file(b):
    b["present_paths"] = set(b["present_paths"]) - {MANIFEST_PATH}; return b
def _m_evidence_invalid(b):
    _primary(b)["authorizationEvidence"].pop("artifactSha256"); return b
def _m_evidence_weak(b):
    _primary(b)["authorizationEvidence"]["evidenceKind"] = "representation-only"; return b
def _m_prose(b):
    _primary(b)["doesNotEstablish"] = ["a", "b", "c", "d", "e", "f", "g"]; return b


CROSS_MUTATIONS = [
    ("digest-binding",          _m_digest,             "DIGEST_BINDING_MISMATCH"),
    ("path-binding",            _m_path,               "PATH_BINDING_MISMATCH"),
    ("version-disagreement",    _m_version_split,      "VERSION_BINDING_MISMATCH"),
    ("version-not-derived",     _m_version_src,        "VERSION_NOT_DERIVED_FROM_MANIFEST"),
    ("pending-with-approved",   _m_pending_approved,   "LIFECYCLE_PENDING_WITH_APPROVED_REVIEW"),
    ("approved-without-record", _m_approved_no_record, "LIFECYCLE_APPROVED_WITHOUT_APPROVED_REVIEW"),
    ("two-authoritative",       _m_two_authoritative,  "AUTHORITATIVE_RECORD_NOT_EXACTLY_ONE"),
    ("derivation-reference",    _m_derivation,         "DERIVATION_REFERENCE_MISMATCH"),
    ("wrong-invariant-scope",   _m_invariants,         "INVARIANT_SCOPE_NOT_EXACTLY_X8"),
    ("wrong-deferral-set",      _m_deferrals,          "DEFERRAL_SET_NOT_EXACTLY_F6_F9"),
    ("non-authorization-true",  _m_non_auth,           "NON_AUTHORIZATION_TRUE"),
    ("non-design-dimension",    _m_non_design,         "NON_DESIGN_DIMENSION_CHANGED"),
    ("state-outside-allowed",   _m_allowed_states,     "CURRENT_STATE_NOT_IN_ALLOWED_STATES"),
    ("member-asserts-state",    _m_member_state,       "DIGEST_MEMBER_ASSERTS_MUTABLE_STATE"),
    ("exclusion-set",           _m_exclusions,         "EXCLUSION_SET_MISMATCH"),
    ("excluded-file-missing",   _m_missing_file,       "EXCLUDED_FILE_MISSING"),
    ("evidence-invalid",        _m_evidence_invalid,   "AUTHORIZATION_EVIDENCE_INVALID"),
    ("evidence-insufficient",   _m_evidence_weak,      "AUTHORIZATION_EVIDENCE_INSUFFICIENT_FOR_APPROVAL"),
    ("prose-not-canonical",     _m_prose,              "PROSE_FIELD_NOT_CANONICAL"),
]


@pytest.mark.parametrize("name,mutate,expected", CROSS_MUTATIONS, ids=[m[0] for m in CROSS_MUTATIONS])
def test_cross_record_rule_is_falsifiable(name, mutate, expected) -> None:
    baseline = build_bundle()
    assert cross_record_violations(baseline) == [], name
    mutated = mutate(copy.deepcopy(baseline))
    assert mutated != baseline, f"{name}: mutation did not change the bundle"
    assert expected in cross_record_violations(mutated), name


def test_every_cross_record_code_has_a_falsifying_mutation() -> None:
    covered = {expected for _, _, expected in CROSS_MUTATIONS}
    assert covered == CROSS_RECORD_CODES, sorted(covered ^ CROSS_RECORD_CODES)


@pytest.mark.parametrize("rel", EXCLUDED_RECORD_RELS)
def test_mutating_an_excluded_record_leaves_the_package_digest_unchanged(rel, tmp_path) -> None:
    """Property, not a static violation: exclusion means the digest cannot see these files."""
    path = GATE / rel
    original = path.read_bytes()
    before = compute_package_digest(compute_member_digests())
    try:
        document = json.loads(original)
        document["recordId"] = document["recordId"] + "-mutated-for-test"
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        assert path.read_bytes() != original, f"{rel}: mutation did not change the record"
        after = compute_package_digest(compute_member_digests())
        assert after == before, f"{rel}: mutating an excluded record changed the package digest"
    finally:
        path.write_bytes(original)
    assert path.read_bytes() == original
    assert compute_package_digest(compute_member_digests()) == before
