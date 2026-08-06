from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .load_contract import load_json
from .paths import EVAL_POLICY_SCHEMA_PATH
from .validation import ValidationFailure, raise_for_issues, validate_schema


def validate_policy(path: Path) -> None:
    policy = load_json(path)
    schema = load_json(EVAL_POLICY_SCHEMA_PATH)
    issues = validate_schema(policy, schema)
    fixtures = policy.get("fixtures", [])
    for fixture_index, fixture_policy in enumerate(fixtures):
        actual = [item.get("requirementId") for item in fixture_policy.get("requirements", [])]
        expected = ["REQ-1", "REQ-2", "REQ-3", "REQ-4", "REQ-5"]
        if actual != expected:
            from .validation import ValidationIssue

            issues.append(
                ValidationIssue(
                    f"requirements must be ordered exactly as {expected}; got {actual}",
                    f"/fixtures/{fixture_index}/requirements",
                )
            )
    raise_for_issues(issues)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("policy")
    args = parser.parse_args(argv)
    try:
        validate_policy(Path(args.policy))
    except ValidationFailure as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("policy validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
