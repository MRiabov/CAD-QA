"""Validate the root measurement tolerance policy against its documented schema."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = ROOT / "tolerance.yaml"

UNITS = {
    "millimetre",
    "square_millimetre",
    "cubic_millimetre",
    "degree",
    "radian",
    "unitless",
}
KINDS = {"exact", "absolute", "relative"}


def test_tolerance_policy() -> None:
    policy = yaml.safe_load(TOLERANCE.read_text(encoding="utf-8"))

    assert set(policy) == {"version", "policy"}
    assert isinstance(policy["version"], int)
    assert policy["version"] > 0

    entries = policy["policy"]
    assert set(entries) == UNITS
    for unit, entry in entries.items():
        assert set(entry) <= {"kind", "value"}, unit
        assert entry["kind"] in KINDS, unit
        if entry["kind"] == "exact":
            assert "value" not in entry, unit
        else:
            assert "value" in entry, unit
            assert entry["value"] >= 0, unit

    assert entries["unitless"]["kind"] == "exact"
