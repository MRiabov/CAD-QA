"""Reusable graph predicates for query synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cad_qa.ontology.nodes import Node, OntologyGraph
from cad_qa.query.ir import Clause

VALUE_BUCKET_DECIMALS = 6
VALUE_MATCH_TOLERANCE = 1e-6


@dataclass(frozen=True)
class PredicateInstance:
    """A reusable verifier clause with its candidate effect."""

    id: str
    clause: Clause
    candidate_count_before: int
    candidate_count_after: int
    sampled_parameters: dict[str, list[str]] = field(default_factory=dict)


def relation_predicate(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    clause_id: str,
    relation: str,
    target_type: str,
) -> PredicateInstance | None:
    """Instantiate a relation predicate if it preserves at least two candidates."""

    after = [
        node
        for node in candidates
        if any(
            edge.source_id == node.id
            and edge.type == relation
            and (target := graph.node(edge.target_id)) is not None
            and target.type == target_type
            for edge in graph.relations
        )
    ]
    if len(after) < 2:
        return None
    return PredicateInstance(
        id=f"relation:{relation}:{target_type}",
        clause=Clause(
            id=clause_id,
            kind="has_relation",
            relation=relation,
            target_type=target_type,
        ),
        candidate_count_before=len(candidates),
        candidate_count_after=len(after),
        sampled_parameters={
            "narrowing_predicate_sequence": [f"relation:{relation}:{target_type}"],
            "clause_relation": [relation],
            "clause_target_type": [target_type],
        },
    )


def measurement_predicate(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    clause_id: str,
    metric: str,
) -> PredicateInstance | None:
    """Instantiate a measurement-presence predicate if it preserves distractors."""

    after = [
        node
        for node in candidates
        if _has_measurement(graph, node.id, metric)
    ]
    if len(after) < 2:
        return None
    params: dict[str, list[str]] = {
        "narrowing_predicate_sequence": [f"measurement:{metric}"],
        "clause_metric": [metric],
    }
    axis = metric_axis(metric)
    if axis is not None:
        params["clause_axis"] = [axis]
    return PredicateInstance(
        id=f"measurement:{metric}",
        clause=Clause(
            id=clause_id,
            kind="has_measurement",
            metric=metric,
        ),
        candidate_count_before=len(candidates),
        candidate_count_after=len(after),
        sampled_parameters=params,
    )


def _has_measurement(graph: OntologyGraph, entity_id: str, metric: str) -> bool:
    if graph.measurements_for(entity_id, metric):
        return True
    return all(graph.measurements_for(entity_id, component) for component in _point_metric_components(metric))


def _point_metric_components(metric: str) -> tuple[str, ...]:
    return {
        "bbox_center": ("bbox_center_x", "bbox_center_y", "bbox_center_z"),
        "centroid": ("centroid_x", "centroid_y", "centroid_z"),
        "midpoint": ("midpoint_x", "midpoint_y", "midpoint_z"),
        "coordinate": ("coordinate_x", "coordinate_y", "coordinate_z"),
    }.get(metric, ())


def measurement_value_predicate(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    clause_id: str,
    metric: str,
    value: float,
) -> PredicateInstance | None:
    """Instantiate an equal-value measurement predicate if it preserves distractors."""

    after = nodes_matching_measurement_value(graph, candidates, metric=metric, value=value)
    if len(after) < 2:
        return None
    params: dict[str, list[str]] = {
        "narrowing_predicate_sequence": [f"equal_measurement:{metric}"],
        "clause_metric": [metric],
        "comparison_operator": ["=="],
        "equal_measurement_metric": [metric],
        "measurement_value_bucket": [f"{metric}:{_value_bucket(value)}"],
    }
    axis = metric_axis(metric)
    if axis is not None:
        params["clause_axis"] = [axis]
    return PredicateInstance(
        id=f"equal_measurement:{metric}:{_value_bucket(value)}",
        clause=Clause(
            id=clause_id,
            kind="has_measurement",
            metric=metric,
            value=value,
        ),
        candidate_count_before=len(candidates),
        candidate_count_after=len(after),
        sampled_parameters=params,
    )


def metric_compare_predicate(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    clause_id: str,
    metric: str,
    operator: str,
    value: float,
) -> PredicateInstance | None:
    """Instantiate a direct metric-comparison predicate if it preserves distractors."""

    after = nodes_matching_metric_compare(
        graph,
        candidates,
        metric=metric,
        operator=operator,
        value=value,
    )
    if len(after) < 2:
        return None
    params: dict[str, list[str]] = {
        "narrowing_predicate_sequence": [f"metric_compare:{metric}:{operator}"],
        "clause_metric": [metric],
        "comparison_operator": [operator],
        "measurement_value_bucket": [f"{metric}:{_value_bucket(value)}"],
    }
    axis = metric_axis(metric)
    if axis is not None:
        params["clause_axis"] = [axis]
    return PredicateInstance(
        id=f"metric_compare:{metric}:{operator}:{_value_bucket(value)}",
        clause=Clause(
            id=clause_id,
            kind="metric_compare",
            metric=metric,
            operator=operator,
            value=value,
        ),
        candidate_count_before=len(candidates),
        candidate_count_after=len(after),
        sampled_parameters=params,
    )


def related_metric_compare_predicate(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    clause_id: str,
    relation: str,
    target_type: str,
    metric: str,
    operator: str,
    value: float,
) -> PredicateInstance | None:
    """Instantiate a predicate over measurements on related graph entities."""

    after = nodes_matching_related_metric_compare(
        graph,
        candidates,
        relation=relation,
        target_type=target_type,
        metric=metric,
        operator=operator,
        value=value,
    )
    if len(after) < 2:
        return None
    params: dict[str, list[str]] = {
        "narrowing_predicate_sequence": [f"related_metric_compare:{relation}:{target_type}:{metric}:{operator}"],
        "clause_relation": [relation],
        "clause_target_type": [target_type],
        "clause_metric": [metric],
        "comparison_operator": [operator],
        "measurement_value_bucket": [f"{metric}:{value:.6g}"],
    }
    axis = metric_axis(metric)
    if axis is not None:
        params["clause_axis"] = [axis]
    return PredicateInstance(
        id=f"related_metric_compare:{relation}:{target_type}:{metric}:{operator}:{value:.6g}",
        clause=Clause(
            id=clause_id,
            kind="related_metric_compare",
            relation=relation,
            target_type=target_type,
            metric=metric,
            operator=operator,
            value=value,
        ),
        candidate_count_before=len(candidates),
        candidate_count_after=len(after),
        sampled_parameters=params,
    )


def nodes_matching_measurement_value(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    metric: str,
    value: float,
) -> list[Node]:
    return [
        node
        for node in candidates
        if any(_value_matches(measurement.value, value) for measurement in graph.measurements_for(node.id, metric))
    ]


def nodes_matching_metric_compare(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    metric: str,
    operator: str,
    value: float,
) -> list[Node]:
    return [
        node
        for node in candidates
        if any(_compare(measurement.value, operator, value) for measurement in graph.measurements_for(node.id, metric))
    ]


def nodes_matching_related_metric_compare(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    relation: str,
    target_type: str,
    metric: str,
    operator: str,
    value: float,
) -> list[Node]:
    return [
        node
        for node in candidates
        if any(
            edge.source_id == node.id
            and edge.type == relation
            and (target := graph.node(edge.target_id)) is not None
            and target.type == target_type
            and any(_compare(measurement.value, operator, value) for measurement in graph.measurements_for(target.id, metric))
            for edge in graph.relations
        )
    ]


def merge_sampled_parameters(*mappings: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = {}
    for mapping in mappings:
        for key, values in mapping.items():
            merged.setdefault(key, set()).update(str(value) for value in values if str(value))
    return {key: sorted(values) for key, values in sorted(merged.items()) if values}


def metric_axis(metric: str) -> str | None:
    tokens = [token for token in metric.lower().replace("-", "_").split("_") if token]
    for token in reversed(tokens):
        if token in {"x", "y", "z"}:
            return token
    return None


def measurement_bucket_value(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    bucket = round(float(value), VALUE_BUCKET_DECIMALS)
    return 0.0 if bucket == 0.0 else bucket


def _compare(measured: object, operator: str, expected: float) -> bool:
    if not isinstance(measured, (int, float)):
        return False
    value = float(measured)
    if operator == ">":
        return value > expected
    if operator == "<":
        return value < expected
    if operator == ">=":
        return value >= expected
    if operator == "<=":
        return value <= expected
    if operator == "==":
        return abs(value - expected) <= 1e-6
    return False


def _value_matches(measured: object, expected: float) -> bool:
    return isinstance(measured, (int, float)) and abs(float(measured) - expected) <= VALUE_MATCH_TOLERANCE


def _value_bucket(value: float) -> str:
    bucket = measurement_bucket_value(value)
    return f"{bucket:.6g}" if bucket is not None else str(value)
