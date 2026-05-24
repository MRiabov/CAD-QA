"""Sampled-parameter balance reports for benchmark release gates."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from cad_qa.dataset.sft import prompt_family
from cad_qa.query.family_manifest import DEFAULT_FAMILY_MANIFEST, load_family_manifest
from cad_qa.query.parameters import (
    AXIS_DIRECTION_DIMENSIONS,
    DEFAULT_ENFORCED_DIMENSIONS,
    EXPECTED_VALUES,
    normalize_sampled_parameters,
    sampled_parameters_from_query,
)


def parameter_balance_report(
    rows: list[dict[str, Any]],
    *,
    family_manifest: Path | None = DEFAULT_FAMILY_MANIFEST,
    max_parameter_value_share: float | None = None,
    min_axis_direction_share: float | None = None,
    enforce: bool = False,
) -> dict[str, Any]:
    """Report whether sampled query parameters collapse within release families."""

    manifest = load_family_manifest(family_manifest)
    specs = manifest["families"]
    release_families = {
        family_id
        for family_id, spec in specs.items()
        if spec.get("status") == "release"
    }
    rows_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    metadata_missing_rows = []
    for row in rows:
        family = prompt_family(row)
        if release_families and family not in release_families:
            continue
        rows_by_family[family].append(row)
        query = row.get("query_program") if isinstance(row.get("query_program"), dict) else {}
        if not normalize_sampled_parameters(query.get("sampled_parameters")):
            metadata_missing_rows.append(
                {
                    "row_id": row.get("row_id"),
                    "prompt_family": family,
                    "query_id": query.get("query_id"),
                }
            )

    family_reports = []
    violations = []
    for family in sorted(rows_by_family):
        family_report = _family_parameter_report(
            family,
            rows_by_family[family],
            specs.get(family, {}),
            max_parameter_value_share=max_parameter_value_share,
            min_axis_direction_share=min_axis_direction_share,
        )
        family_reports.append(family_report)
        violations.extend(
            {
                "prompt_family": family,
                **violation,
            }
            for violation in family_report["violations"]
        )

    valid = True
    if enforce:
        valid = manifest["exists"] and not violations and not metadata_missing_rows
    return {
        "valid": valid,
        "enforced": enforce,
        "manifest_path": manifest["path"],
        "manifest_exists": manifest["exists"],
        "row_count": sum(len(items) for items in rows_by_family.values()),
        "release_family_count": len(rows_by_family),
        "max_parameter_value_share": max_parameter_value_share,
        "min_axis_direction_share": min_axis_direction_share,
        "enforced_dimensions": sorted(DEFAULT_ENFORCED_DIMENSIONS),
        "axis_direction_dimensions": sorted(AXIS_DIRECTION_DIMENSIONS),
        "sampled_parameter_metadata_missing_count": len(metadata_missing_rows),
        "sampled_parameter_metadata_missing_rows": metadata_missing_rows[:50],
        "violations": violations,
        "families": family_reports,
    }


def row_sampled_parameters(row: dict[str, Any]) -> dict[str, list[str]]:
    """Extract currently observable sampled parameters from a row's query program."""

    query = row.get("query_program") or {}
    return sampled_parameters_from_query(query)


def _family_parameter_report(
    family: str,
    rows: list[dict[str, Any]],
    spec: dict[str, Any],
    *,
    max_parameter_value_share: float | None,
    min_axis_direction_share: float | None,
) -> dict[str, Any]:
    counters: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        for dimension, values in row_sampled_parameters(row).items():
            for value in values:
                counters[dimension][value] += 1

    ignored_dimensions = _ignored_dimensions(spec)
    dimension_reports = []
    violations = []
    for dimension in sorted(counters):
        counts = counters[dimension]
        total = sum(counts.values())
        largest_value, largest_count = _largest_counter_item(counts)
        largest_share = largest_count / total if total else 0.0
        report = {
            "dimension": dimension,
            "ignored": dimension in ignored_dimensions,
            "counts": dict(sorted(counts.items())),
            "total": total,
            "largest_value": largest_value,
            "largest_count": largest_count,
            "largest_share": largest_share,
        }
        if dimension in AXIS_DIRECTION_DIMENSIONS:
            expected = EXPECTED_VALUES.get(dimension, ())
            expected_shares = {
                value: counts.get(value, 0) / total if total else 0.0
                for value in expected
            }
            undercovered = [
                {"value": value, "share": share}
                for value, share in expected_shares.items()
                if min_axis_direction_share is not None and share < min_axis_direction_share
            ]
            report["expected_values"] = list(expected)
            report["expected_value_shares"] = expected_shares
            report["minimum_expected_value_share"] = min_axis_direction_share
            report["undercovered_expected_values"] = undercovered
            if undercovered and dimension not in ignored_dimensions:
                violations.append(
                    {
                        "dimension": dimension,
                        "reason": "axis_or_direction_undercovered",
                        "undercovered_expected_values": undercovered,
                    }
                )
        elif dimension in DEFAULT_ENFORCED_DIMENSIONS:
            report["maximum_allowed_largest_share"] = max_parameter_value_share
            if (
                max_parameter_value_share is not None
                and largest_share > max_parameter_value_share
                and dimension not in ignored_dimensions
            ):
                violations.append(
                    {
                        "dimension": dimension,
                        "reason": "parameter_value_dominates",
                        "largest_value": largest_value,
                        "largest_share": largest_share,
                        "maximum_allowed_largest_share": max_parameter_value_share,
                    }
                )
        dimension_reports.append(report)

    return {
        "prompt_family": family,
        "row_count": len(rows),
        "ignored_dimensions": sorted(ignored_dimensions),
        "dimensions": dimension_reports,
        "violations": violations,
        "valid": not violations,
    }


def _ignored_dimensions(spec: dict[str, Any]) -> set[str]:
    balance = spec.get("parameter_balance") if isinstance(spec.get("parameter_balance"), dict) else {}
    ignored = set(balance.get("ignored_dimensions") or [])
    ignored.update(balance.get("geometry_limited_dimensions") or [])
    return {str(value) for value in ignored}


def _largest_counter_item(counts: Counter[str]) -> tuple[str | None, int]:
    if not counts:
        return None, 0
    item, count = max(counts.items(), key=lambda entry: (entry[1], entry[0]))
    return item, count
