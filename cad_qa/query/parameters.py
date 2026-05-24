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
    "rank_direction",
}
DEFAULT_ENFORCED_DIMENSIONS = {
    "target_type",
    "final_selector",
    "aggregation_metric",
    "aggregation_rank",
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
    "rank_direction": DIRECTIONS,
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
        if query.get("aggregation_rank") is not None:
            _add(params, "aggregation_rank", query.get("aggregation_rank"))
            _add(params, "rank_direction", direction)
            _add(
                params,
                "final_selector",
                f"rank:{query.get('aggregation_rank')}:{direction or aggregation}:{aggregation_metric or 'none'}",
            )
        else:
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
        if clause.get("kind") == "reference_measurement":
            _add_reference_measurement_parameters(params, query, clause)
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


def _add_reference_measurement_parameters(
    params: dict[str, set[str]],
    query: Mapping[str, Any],
    clause: Mapping[str, Any],
) -> None:
    metric = clause.get("metric")
    _add(params, "reference_metric", metric)
    reference_info = _reference_metric_info(metric)
    _add(params, "reference_type", reference_info.get("reference_type"))
    _add(params, "reference_point_metric", reference_info.get("reference_point_metric"))
    _add(params, "target_point_metric", reference_info.get("target_point_metric") or _target_point_metric(query))
    value = clause.get("value")
    if not isinstance(value, Mapping):
        return
    reference_id = value.get("reference_id")
    if isinstance(reference_id, str) and ":" in reference_id:
        _add(params, "reference_type", reference_id.split(":", 1)[0])
    _add(params, "reference_anchor_id", reference_id)
    anchor_metrics = []
    for key in sorted(value):
        if key == "reference_id":
            continue
        metric_name = str(key).removeprefix("reference_")
        bucket = _value_bucket(value[key])
        _add(params, "reference_anchor_metric", metric_name)
        _add(params, "reference_anchor_value_bucket", f"{metric_name}:{bucket}")
        anchor_metrics.append(f"{metric_name}={bucket}")
    if anchor_metrics:
        reference_type = sorted(params.get("reference_type", []))[0] if params.get("reference_type") else "reference"
        _add(params, "reference_anchor_signature", f"{reference_type}:{'|'.join(anchor_metrics)}")


def _aggregation_direction(aggregation: str) -> str | None:
    if aggregation in {"argmax", "rank_desc"}:
        return "max"
    if aggregation in {"argmin", "rank_asc"}:
        return "min"
    return None


def _reference_metric_info(metric: Any) -> dict[str, str]:
    if metric == "distance_to_reference_feature_centroid":
        return {
            "reference_type": "feature",
            "reference_point_metric": "centroid",
            "target_point_metric": "midpoint",
        }
    return {}


def _target_point_metric(query: Mapping[str, Any]) -> str | None:
    target_type = query.get("target_type")
    if target_type == "edge":
        return "midpoint"
    if target_type == "face":
        return "center"
    if target_type in {"vertex", "edge_endpoint", "path_point"}:
        return "point"
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
