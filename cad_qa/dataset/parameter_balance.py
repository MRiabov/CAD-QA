"""Sampled-parameter balance reports for benchmark release gates."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from cad_qa.dataset.sft import prompt_family
from cad_qa.query.family_manifest import DEFAULT_FAMILY_MANIFEST, load_family_manifest

AXES = ("x", "y", "z")
DIRECTIONS = ("min", "max")
AXIS_DIRECTION_DIMENSIONS = {"aggregation_axis", "clause_axis", "extremum_direction"}
DEFAULT_ENFORCED_DIMENSIONS = {
    "target_type",
    "final_selector",
    "aggregation_metric",
    "clause_relation",
    "clause_metric",
    "clause_target_type",
    "comparison_operator",
    "reference_metric",
    "measurement_value_bucket",
}
EXPECTED_VALUES = {
    "aggregation_axis": AXES,
    "clause_axis": AXES,
    "extremum_direction": DIRECTIONS,
}


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
    for row in rows:
        family = prompt_family(row)
        if release_families and family not in release_families:
            continue
        rows_by_family[family].append(row)

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
        valid = manifest["exists"] and not violations
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
        "violations": violations,
        "families": family_reports,
    }


def row_sampled_parameters(row: dict[str, Any]) -> dict[str, list[str]]:
    """Extract currently observable sampled parameters from a row's query program."""

    query = row.get("query_program") or {}
    params: dict[str, set[str]] = defaultdict(set)
    _add(params, "target_type", query.get("target_type"))
    aggregation = query.get("aggregation")
    aggregation_metric = query.get("aggregation_metric")
    if isinstance(aggregation, str):
        direction = _aggregation_direction(aggregation)
        _add(params, "extremum_direction", direction)
        _add(params, "final_selector", f"{direction or aggregation}:{aggregation_metric or 'none'}")
    _add(params, "aggregation_metric", aggregation_metric)
    _add(params, "aggregation_axis", _metric_axis(aggregation_metric))

    for clause in query.get("clauses") or []:
        if not isinstance(clause, dict):
            continue
        metric = clause.get("metric")
        _add(params, "clause_relation", clause.get("relation"))
        _add(params, "clause_metric", metric)
        _add(params, "clause_axis", _metric_axis(metric))
        _add(params, "clause_target_type", clause.get("target_type"))
        _add(params, "comparison_operator", clause.get("operator"))
        _add(params, "reference_metric", clause.get("reference_metric"))
        if clause.get("value") is not None:
            _add(params, "measurement_value_bucket", f"{metric or 'value'}:{_value_bucket(clause.get('value'))}")

    return {key: sorted(values) for key, values in sorted(params.items()) if values}


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


def _add(params: dict[str, set[str]], dimension: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str):
        if value:
            params[dimension].add(value)
        return
    params[dimension].add(str(value))


def _aggregation_direction(aggregation: str) -> str | None:
    if aggregation == "argmax":
        return "max"
    if aggregation == "argmin":
        return "min"
    return None


def _metric_axis(metric: Any) -> str | None:
    if not isinstance(metric, str):
        return None
    tokens = [token for token in metric.lower().replace("-", "_").split("_") if token]
    for token in reversed(tokens):
        if token in AXES:
            return token
    return None


def _value_bucket(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (int, str, bool)):
        return str(value)
    return type(value).__name__


def _largest_counter_item(counts: Counter[str]) -> tuple[str | None, int]:
    if not counts:
        return None, 0
    item, count = max(counts.items(), key=lambda entry: (entry[1], entry[0]))
    return item, count
