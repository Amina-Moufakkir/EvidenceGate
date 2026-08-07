"""Offline structural validation for the Gate 2A-P draft design package.

These tests establish STRUCTURAL conformance only. They cannot establish that the source prose was
completely or correctly decomposed, that obligation parts are genuinely independent, or that a
human-required classification is substantively correct. Those questions are invariant X-8 and
require owner review.

No live model call, no network access, no external mutation.
"""
from __future__ import annotations

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
    ("records/design-review-record.example.json", "schema/design-review-record.schema.json"),
    ("records/bridge-authority-record.example.json", "schema/bridge-authority-record.schema.json"),
    ("records/classification-authority-record.example.json",
     "schema/classification-authority-record.schema.json"),
    ("manifest.json", "schema/package-manifest.schema.json"),
]
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


def load(rel: str) -> dict:
    return json.loads((GATE / rel).read_text())


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
    open_locations: list[str] = []

    def walk(node: object, path: str) -> None:
        if not isinstance(node, dict):
            return
        is_object = node.get("type") == "object" or "properties" in node
        closed = node.get("additionalProperties")
        if is_object and closed is not False and not isinstance(closed, dict):
            open_locations.append(path)
        for keyword in ("properties", "$defs", "patternProperties"):
            for name, child in (node.get(keyword) or {}).items():
                walk(child, f"{path}/{keyword}/{name}")
        for keyword in ("items", "not", "if", "then", "else", "contains", "propertyNames"):
            walk(node.get(keyword), f"{path}/{keyword}")
        for keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
            for index, child in enumerate(node.get(keyword) or []):
                walk(child, f"{path}/{keyword}/{index}")

    walk(load(schema_rel), "#")
    assert not open_locations, open_locations


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


def test_gate_2a_f_was_not_started(records: list[dict]) -> None:
    assert len(records) == 7
    assert load("statements/source-statement-records.json")["scope"] == "pilot-subset"


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


def test_pilot_totals_reconcile(parts, rules, records) -> None:
    report = load("statements/coverage-report.json")
    states = Counter(p["coverageState"] for p in parts)
    derivations = Counter(p["derivationBasis"] for p in parts)
    rule_derivations = Counter(r["derivationBasis"] for r in rules)
    classes = Counter(r["classification"] for r in rules)
    decomposition = Counter(r["decompositionStatus"] for r in records)

    st, ob, ru = report["statementTotals"], report["obligationTotals"], report["ruleTotals"]
    assert st["selected"] == st["recordsCreated"] == len(records) == 7
    assert st["fullyDecomposed"] == decomposition["fully_decomposed"]
    assert st["partiallyDecomposed"] == decomposition["partially_decomposed"]
    assert st["fullyDecomposed"] + st["partiallyDecomposed"] == 7

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

    assert sum(report["statementClassification"].values()) == 7


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


def test_only_ss_026_declares_an_evidence_contract(parts) -> None:
    with_contract = [p["obligationPartId"] for p in parts if p["evidenceContract"] is not None]
    assert with_contract == ["OP-026-a"], with_contract


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
def test_approval_state_is_external_to_the_design_artifacts() -> None:
    forbidden = ("reviewStatus", "humanReviewed", "reviewedBy", "reviewedDate", "designApproved")
    for instance_rel, _ in PAIRS:
        if instance_rel.startswith("records/"):
            continue
        blob = json.dumps(load(instance_rel))
        for field in forbidden:
            assert f'"{field}"' not in blob, (instance_rel, field)


def test_design_review_record_is_pending_and_digest_bound() -> None:
    record = load("records/design-review-record.example.json")
    assert record["reviewStatus"] == "pending-owner-review"
    assert record["humanReviewOccurred"] is False
    assert record["designApproved"] is False
    assert record["reviewerRepresentation"] is None
    assert record["reviewedArtifactPath"].endswith("manifest.json")
    assert len(record["reviewedArtifactDigest"]) == 64
    assert len(record["doesNotEstablish"]) >= 7


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
    excluded = {e["path"] for e in manifest["exclusions"]}
    assert "auditors/problem-evidence/gate2a/manifest.json" in excluded
    assert any("design-review-record" in path for path in excluded)
    assert any("bridge-authority-record" in path for path in excluded)
    assert all(e["reason"] for e in manifest["exclusions"])
    assert not any(path in listed for path in excluded)


def test_package_digest_recomputes_and_matches_the_review_record() -> None:
    manifest = load("manifest.json")
    files: dict[str, str] = {}
    for subdirectory in MANIFEST_DIRS:
        for path in sorted((GATE / subdirectory).glob("*.json")):
            rel = f"auditors/problem-evidence/gate2a/{subdirectory}/{path.name}"
            files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    for document in sorted(MANIFEST_DOCS):
        rel = f"auditors/problem-evidence/gate2a/{document}"
        files[rel] = hashlib.sha256((GATE / document).read_bytes()).hexdigest()

    assert files == manifest["includedFiles"], "per-file digests must be current"
    expected = hashlib.sha256(json.dumps(
        files, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    assert manifest["packageDigest"] == expected
    assert load("records/design-review-record.example.json")["reviewedArtifactDigest"] == expected
    assert load("records/bridge-authority-record.example.json")["governedArtifactDigest"] == expected


def test_lifecycle_dimensions_remain_closed() -> None:
    lifecycle = load("contracts/lifecycle-state.json")
    assert lifecycle["designReview"]["currentState"] == "pending-owner-review"
    assert lifecycle["designReview"]["stateHeldExternally"] is True
    assert lifecycle["operationalComparatorUse"]["currentState"] == "prohibited"
    assert lifecycle["operationalComparatorUse"]["changeableByGate2AP"] is False
    assert lifecycle["runtimeEnforcement"]["currentState"] == "disabled"
    assert lifecycle["runtimeEnforcement"]["changeableByGate2AP"] is False
    assert lifecycle["modelCompatibility"]["currentState"] == "unresolved-offline"
    assert lifecycle["formalPhase1Acceptance"]["representedAsRepositoryState"] is False


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
