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
    loaded_family_manifest: dict[str, Any] | None = None,
    max_parameter_value_share: float | None = None,
    min_axis_direction_share: float | None = None,
    enforce: bool = False,
) -> dict[str, Any]:
    """Report whether sampled query parameters collapse within release families."""

    manifest = loaded_family_manifest or load_family_manifest(family_manifest)
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
        "minimum_expected_share_dimensions": sorted(AXIS_DIRECTION_DIMENSIONS),
        "default_enforced_dimensions": sorted(DEFAULT_ENFORCED_DIMENSIONS),
        "enforced_dimensions": sorted(DEFAULT_ENFORCED_DIMENSIONS),
        "axis_direction_dimensions": sorted(AXIS_DIRECTION_DIMENSIONS),
        "sampled_parameter_metadata_missing_count": len(metadata_missing_rows),
        "sampled_parameter_metadata_missing_rows": metadata_missing_rows[:50],
        "violation_count": len(violations),
        "violation_reason_counts": dict(Counter(violation["reason"] for violation in violations).most_common()),
        "violation_dimension_counts": dict(Counter(violation["dimension"] for violation in violations).most_common()),
        "violation_family_counts": dict(Counter(violation["prompt_family"] for violation in violations).most_common()),
        "violations": violations,
        "families": family_reports,
    }


def row_sampled_parameters(row: dict[str, Any]) -> dict[str, list[str]]:
    """Extract currently observable sampled parameters from a row's query program."""

    cached = row.get("_sampled_parameters_cache")
    if isinstance(cached, dict):
        return cached
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

    balance = _balance_spec(spec)
    ignored_dimensions = _ignored_dimensions(balance)
    required_dimensions = _required_dimensions(balance)
    configured_enforced_dimensions = _configured_enforced_dimensions(balance)
    enforced_dimensions = configured_enforced_dimensions if balance else DEFAULT_ENFORCED_DIMENSIONS
    expected_values_by_dimension = _configured_expected_values(balance)
    if spec.get("target_type") and "target_type" not in expected_values_by_dimension:
        expected_values_by_dimension["target_type"] = [str(spec["target_type"])]
    dimension_reports = []
    violations = []
    for dimension in sorted(required_dimensions - set(counters) - ignored_dimensions):
        violations.append(
            {
                "dimension": dimension,
                "reason": "required_parameter_dimension_missing",
            }
        )
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
            "required": dimension in required_dimensions,
        }
        expected = expected_values_by_dimension.get(dimension)
        has_single_structural_expected = False
        enforces_min_expected_share = dimension in AXIS_DIRECTION_DIMENSIONS
        if expected is not None or enforces_min_expected_share:
            expected = expected or EXPECTED_VALUES.get(dimension, ())
            has_single_structural_expected = len(expected) == 1
            expected_shares = {
                value: counts.get(value, 0) / total if total else 0.0
                for value in expected
            }
            undercovered = [
                {"value": value, "share": share}
                for value, share in expected_shares.items()
                if (
                    enforces_min_expected_share
                    and not has_single_structural_expected
                    and min_axis_direction_share is not None
                    and share < min_axis_direction_share
                )
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
        if dimension in enforced_dimensions:
            report["maximum_allowed_largest_share"] = max_parameter_value_share
            if (
                max_parameter_value_share is not None
                and largest_share > max_parameter_value_share
                and dimension not in ignored_dimensions
                and not has_single_structural_expected
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
        "required_dimensions": sorted(required_dimensions),
        "configured_enforced_dimensions": sorted(configured_enforced_dimensions),
        "uses_default_enforced_dimensions": not bool(balance),
        "dimensions": dimension_reports,
        "violations": violations,
        "valid": not violations,
    }


def _balance_spec(spec: dict[str, Any]) -> dict[str, Any]:
    balance = spec.get("parameter_balance")
    return balance if isinstance(balance, dict) else {}


def _ignored_dimensions(balance: dict[str, Any]) -> set[str]:
    ignored = set(balance.get("ignored_dimensions") or [])
    ignored.update(balance.get("geometry_limited_dimensions") or [])
    return {str(value) for value in ignored}


def _required_dimensions(balance: dict[str, Any]) -> set[str]:
    return {str(value) for value in balance.get("required_dimensions") or []}


def _configured_enforced_dimensions(balance: dict[str, Any]) -> set[str]:
    return {str(value) for value in balance.get("enforced_dimensions") or []}


def _configured_expected_values(balance: dict[str, Any]) -> dict[str, list[str]]:
    configured = balance.get("expected_values")
    if not isinstance(configured, dict):
        return {}
    result: dict[str, list[str]] = {}
    for dimension, values in configured.items():
        value_list = values if isinstance(values, list) else [values]
        normalized = [str(value) for value in value_list if value is not None and str(value)]
        if normalized:
            result[str(dimension)] = normalized
    return result


def _largest_counter_item(counts: Counter[str]) -> tuple[str | None, int]:
    if not counts:
        return None, 0
    item, count = max(counts.items(), key=lambda entry: (entry[1], entry[0]))
    return item, count
