"""Validate the root release-check policy against its documented schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ROOT / "checks.yaml"
BALANCE = ROOT / "balance.yaml"

CHECK_KEYS = {"id", "requirement", "arithmetic", "scope", "dimension", "disposition"}

BOUNDS = {
    "coverage": set(),
    "count_floor": {"minimum"},
    "share_range": {"minimum", "maximum"},
    "relative_range": {"below", "above"},
    "share_target": {"target", "tolerance"},
    "set_equal": {"values", "to"},
}
REQUIRED_BOUNDS = {
    "coverage": set(),
    "count_floor": {"minimum"},
    "share_range": set(),
    "relative_range": {"below", "above"},
    "share_target": {"target", "tolerance"},
    "set_equal": set(),
}

SCOPES = {"release", "per_step"}
DISPOSITIONS = {"enforced", "reported", "deferred"}
DIMENSIONS = {
    "answer_format",
    "answer_meaning",
    "clue_operand_form",
    "clue_type",
    "correct_answer",
    "geometry_required",
    "program_id",
    "split",
    "target_category",
    "task_count",
    "task_reasoning_step_count",
    "warmup",
}
REQUIREMENTS = {
    "DS-37",
    "PRD-8",
    "R-4",
    "R-7",
    "R-8",
    "R-9",
    "R-10",
    "R-11",
    "R-12",
    "R-15",
    "release-contract-3",
}
DERIVED_SETS = {"one_step_tasks"}


def resolve(path: str, balance: dict[str, Any]) -> Any:
    node: Any = balance
    for part in path.split("."):
        assert isinstance(node, dict), f"{path}: {part} is not under a mapping"
        assert part in node, f"{path}: no {part}"
        node = node[part]
    return node


def test_check_policy() -> None:
    policy = yaml.safe_load(CHECKS.read_text())
    balance = yaml.safe_load(BALANCE.read_text())

    assert set(policy) == {"version", "checks"}
    assert isinstance(policy["version"], int)
    assert policy["version"] > 0

    checks = policy["checks"]
    assert checks

    ids = [check["id"] for check in checks]
    assert len(ids) == len(set(ids)), "duplicate check id"

    for check in checks:
        arithmetic = check["arithmetic"]
        assert arithmetic in BOUNDS, check["id"]
        bound_keys = set(check) - CHECK_KEYS

        assert bound_keys <= BOUNDS[arithmetic], (check["id"], bound_keys)
        assert REQUIRED_BOUNDS[arithmetic] <= bound_keys, (check["id"], bound_keys)

        assert check["scope"] in SCOPES, check["id"]
        assert check["dimension"] in DIMENSIONS, check["id"]
        assert check["disposition"] in DISPOSITIONS, check["id"]

        requirement = check["requirement"]
        assert isinstance(requirement, list) and requirement, check["id"]
        assert set(requirement) <= REQUIREMENTS, (check["id"], requirement)

        if arithmetic == "share_range":
            assert bound_keys, f"{check['id']}: a share range needs a bound"
        if arithmetic == "set_equal":
            assert bound_keys in ({"values"}, {"to"}), check["id"]
            if "to" in check:
                assert check["to"] in DERIVED_SETS, check["id"]
            if "values" in check:
                assert isinstance(check["values"], list) and check["values"]

        for key in bound_keys - {"values", "to"}:
            bound = check[key]
            if isinstance(bound, str):
                resolve(bound, balance)

    cited = {item for check in checks for item in check["requirement"]}
    assert cited == REQUIREMENTS, REQUIREMENTS - cited
