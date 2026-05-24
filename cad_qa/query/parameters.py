"""Sampled-parameter extraction for query programs."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

AXES = ("x", "y", "z")
DIRECTIONS = ("min", "max")
AXIS_DIRECTION_DIMENSIONS = {
    "aggregation_axis",
    "clause_axis",
    "extremum_direction",
    "tie_break_axis",
    "tie_break_direction",
}
DEFAULT_ENFORCED_DIMENSIONS = {
    "target_type",
    "final_selector",
    "aggregation_metric",
    "tie_break_metric",
    "tie_break_selector",
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
    "tie_break_axis": AXES,
    "tie_break_direction": DIRECTIONS,
}


def sampled_parameters_from_query(query: Mapping[str, Any]) -> dict[str, list[str]]:
    """Extract serializable sampled-parameter metadata from a query mapping."""

    explicit = normalize_sampled_parameters(query.get("sampled_parameters"))
    if explicit:
        return explicit

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
    tie_break_aggregation = query.get("tie_break_aggregation")
    tie_break_metric = query.get("tie_break_metric")
    if isinstance(tie_break_aggregation, str):
        direction = _aggregation_direction(tie_break_aggregation)
        _add(params, "tie_break_direction", direction)
        _add(params, "tie_break_selector", f"{direction or tie_break_aggregation}:{tie_break_metric or 'none'}")
    _add(params, "tie_break_metric", tie_break_metric)
    _add(params, "tie_break_axis", _metric_axis(tie_break_metric))

    for clause in query.get("clauses") or []:
        if not isinstance(clause, Mapping):
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


def normalize_sampled_parameters(value: Any) -> dict[str, list[str]]:
    """Normalize explicit sampled-parameter metadata to sorted string lists."""

    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, list[str]] = {}
    for dimension, raw_values in value.items():
        values = raw_values if isinstance(raw_values, list) else [raw_values]
        normalized_values = sorted(
            str(item)
            for item in values
            if item is not None and str(item)
        )
        if normalized_values:
            normalized[str(dimension)] = normalized_values
    return normalized


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
