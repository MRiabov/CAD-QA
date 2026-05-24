"""Bounded graph-hop query synthesis over ontology graphs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from cad_qa.ontology.nodes import Node, OntologyGraph
from cad_qa.query.ir import QueryProgram
from cad_qa.query.predicate_catalog import (
    merge_sampled_parameters,
    metric_axis,
    measurement_predicate,
    nodes_matching_related_metric_compare,
    related_metric_compare_predicate,
    relation_predicate,
)


GEOMETRY_MARGIN_EPSILON = 1e-6


@dataclass(frozen=True)
class ExtremeFamilySpec:
    family_id: str
    target_type: str
    relation: str
    relation_clause_id: str
    measurement_clause_id: str
    metrics: tuple[str, ...]


@dataclass(frozen=True)
class ViableExtreme:
    spec: ExtremeFamilySpec
    candidates: list[Node]
    metric: str
    aggregation: str
    tie_break_metric: str | None = None
    tie_break_aggregation: str | None = None


@dataclass(frozen=True)
class SelectorCountFamilySpec:
    family_id: str
    relation: str
    selected_type: str
    relation_clause_id: str
    related_metric_clause_id: str
    selected_count_clause_id: str
    related_metrics: tuple[str, ...]


@dataclass(frozen=True)
class ViableSelectorCount:
    spec: SelectorCountFamilySpec
    metric: str
    operator: str
    value: float
    aggregation: str
    candidate_ids: tuple[str, ...]


EXTREME_FAMILY_SPECS = (
    ExtremeFamilySpec(
        family_id="parameterized_kernel_face_extreme",
        target_type="face",
        relation="has_kernel_stable_face_id",
        relation_clause_id="has_parameterized_face_set",
        measurement_clause_id="has_parameterized_face_metric",
        metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
            "face_area",
        ),
    ),
    ExtremeFamilySpec(
        family_id="parameterized_kernel_edge_extreme",
        target_type="edge",
        relation="has_kernel_stable_edge_id",
        relation_clause_id="has_parameterized_edge_set",
        measurement_clause_id="has_parameterized_edge_metric",
        metrics=(
            "midpoint_x",
            "midpoint_y",
            "midpoint_z",
            "midpoint_distance_to_origin",
            "edge_length",
        ),
    ),
)

SELECTOR_COUNT_FAMILY_SPECS = (
    SelectorCountFamilySpec(
        family_id="parameterized_kernel_face_selector_count",
        relation="has_kernel_stable_face_id",
        selected_type="face",
        relation_clause_id="has_parameterized_face_selection",
        related_metric_clause_id="has_parameterized_selected_face_metric_threshold",
        selected_count_clause_id="has_parameterized_selected_count",
        related_metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
            "face_area",
        ),
    ),
    SelectorCountFamilySpec(
        family_id="parameterized_kernel_edge_selector_count",
        relation="has_kernel_stable_edge_id",
        selected_type="edge",
        relation_clause_id="has_parameterized_edge_selection",
        related_metric_clause_id="has_parameterized_selected_edge_metric_threshold",
        selected_count_clause_id="has_parameterized_selected_count",
        related_metrics=(
            "midpoint_x",
            "midpoint_y",
            "midpoint_z",
            "midpoint_distance_to_origin",
            "edge_length",
        ),
    ),
)


def synthesize_graph_hop_queries(graph: OntologyGraph) -> list[QueryProgram]:
    """Create deterministic parameterized graph-hop queries from graph evidence."""

    queries: list[QueryProgram] = []
    for spec in EXTREME_FAMILY_SPECS:
        viable = _viable_extremes(graph, spec)
        if not viable:
            continue
        choice = viable[_stable_choice_index(graph.graph_id, spec.family_id, len(viable))]
        query = _query_for_extreme(graph, choice)
        if query is not None:
            queries.append(query)
    for spec in SELECTOR_COUNT_FAMILY_SPECS:
        viable = _viable_selector_counts(graph, spec)
        if not viable:
            continue
        choice = viable[_stable_choice_index(graph.graph_id, spec.family_id, len(viable))]
        query = _query_for_selector_count(graph, choice)
        if query is not None:
            queries.append(query)
    return queries


def _viable_extremes(graph: OntologyGraph, spec: ExtremeFamilySpec) -> list[ViableExtreme]:
    candidates = graph.nodes_by_type(spec.target_type)
    relation = relation_predicate(
        graph,
        candidates,
        clause_id=spec.relation_clause_id,
        relation=spec.relation,
        target_type="selector",
    )
    if relation is None:
        return []
    relation_candidates = _apply_relation_clause(graph, candidates, spec.relation)
    viable: list[ViableExtreme] = []
    for metric in spec.metrics:
        measurement = measurement_predicate(
            graph,
            relation_candidates,
            clause_id=spec.measurement_clause_id,
            metric=metric,
        )
        if measurement is None:
            continue
        metric_candidates = _nodes_with_numeric_measurement(graph, relation_candidates, metric)
        if len(metric_candidates) < 2:
            continue
        for aggregation in ("argmax", "argmin"):
            if _has_unique_extreme(graph, metric_candidates, metric, aggregation):
                viable.append(ViableExtreme(spec, metric_candidates, metric, aggregation))
                continue
            tied = _extreme_nodes(graph, metric_candidates, metric, aggregation)
            for tie_break_metric, tie_break_aggregation in _viable_tie_breaks(
                graph,
                spec,
                tied,
                primary_metric=metric,
            ):
                viable.append(
                    ViableExtreme(
                        spec,
                        metric_candidates,
                        metric,
                        aggregation,
                        tie_break_metric=tie_break_metric,
                        tie_break_aggregation=tie_break_aggregation,
                    )
                )
    return sorted(
        viable,
        key=lambda item: (
            item.metric,
            item.aggregation,
            item.tie_break_metric or "",
            item.tie_break_aggregation or "",
            [node.id for node in item.candidates],
        ),
    )


def _query_for_extreme(graph: OntologyGraph, viable: ViableExtreme) -> QueryProgram | None:
    spec = viable.spec
    broad_candidates = graph.nodes_by_type(spec.target_type)
    relation = relation_predicate(
        graph,
        broad_candidates,
        clause_id=spec.relation_clause_id,
        relation=spec.relation,
        target_type="selector",
    )
    if relation is None:
        return None
    relation_candidates = _apply_relation_clause(graph, broad_candidates, spec.relation)
    measurement = measurement_predicate(
        graph,
        relation_candidates,
        clause_id=spec.measurement_clause_id,
        metric=viable.metric,
    )
    if measurement is None:
        return None
    direction = "max" if viable.aggregation == "argmax" else "min"
    sampled = merge_sampled_parameters(
        {
            "target_type": [spec.target_type],
            "final_selector": [f"{direction}:{viable.metric}"],
            "aggregation_metric": [viable.metric],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "synthesis_strategy": ["bounded_parameterized_extreme_v1"],
        },
        relation.sampled_parameters,
        measurement.sampled_parameters,
    )
    if viable.tie_break_metric and viable.tie_break_aggregation:
        tie_break_direction = "max" if viable.tie_break_aggregation == "argmax" else "min"
        sampled = merge_sampled_parameters(
            sampled,
            {
                "tie_break_metric": [viable.tie_break_metric],
                "tie_break_direction": [tie_break_direction],
                "tie_break_selector": [f"{tie_break_direction}:{viable.tie_break_metric}"],
            },
        )
    axis = metric_axis(viable.metric)
    if axis is not None:
        sampled = merge_sampled_parameters(sampled, {"aggregation_axis": [axis]})
    tie_break_axis = metric_axis(viable.tie_break_metric) if viable.tie_break_metric else None
    if tie_break_axis is not None:
        sampled = merge_sampled_parameters(sampled, {"tie_break_axis": [tie_break_axis]})
    return QueryProgram(
        query_id=f"{graph.graph_id}:synth:{spec.family_id}",
        target_type=spec.target_type,
        clauses=[
            relation.clause,
            measurement.clause,
        ],
        aggregation=viable.aggregation,
        aggregation_metric=viable.metric,
        tie_break_aggregation=viable.tie_break_aggregation,
        tie_break_metric=viable.tie_break_metric,
        hop_count=3,
        difficulty="cad_browsecomp",
        min_individual_clause_candidates=2,
        sampled_parameters=sampled,
    )


def _viable_selector_counts(graph: OntologyGraph, spec: SelectorCountFamilySpec) -> list[ViableSelectorCount]:
    selectors = _nodes_with_numeric_measurement(graph, graph.nodes_by_type("selector"), "selected_count")
    relation = relation_predicate(
        graph,
        selectors,
        clause_id=spec.relation_clause_id,
        relation=spec.relation,
        target_type=spec.selected_type,
    )
    if relation is None:
        return []
    relation_candidates = _apply_relation_clause(graph, selectors, spec.relation)
    viable: list[ViableSelectorCount] = []
    for metric in spec.related_metrics:
        thresholds = _related_metric_thresholds(graph, relation_candidates, relation=spec.relation, metric=metric)
        for operator, value in thresholds:
            predicate = related_metric_compare_predicate(
                graph,
                relation_candidates,
                clause_id=spec.related_metric_clause_id,
                relation=spec.relation,
                target_type=spec.selected_type,
                metric=metric,
                operator=operator,
                value=value,
            )
            if predicate is None or predicate.candidate_count_after >= len(relation_candidates):
                continue
            narrowed = nodes_matching_related_metric_compare(
                graph,
                relation_candidates,
                relation=spec.relation,
                target_type=spec.selected_type,
                metric=metric,
                operator=operator,
                value=value,
            )
            if len(narrowed) < 2:
                continue
            for aggregation in ("argmax", "argmin"):
                if _has_unique_extreme(graph, narrowed, "selected_count", aggregation):
                    viable.append(
                        ViableSelectorCount(
                            spec=spec,
                            metric=metric,
                            operator=operator,
                            value=value,
                            aggregation=aggregation,
                            candidate_ids=tuple(node.id for node in narrowed),
                        )
                    )
    return sorted(
        viable,
        key=lambda item: (
            item.metric,
            item.operator,
            item.value,
            item.aggregation,
            item.candidate_ids,
        ),
    )


def _query_for_selector_count(graph: OntologyGraph, viable: ViableSelectorCount) -> QueryProgram | None:
    spec = viable.spec
    selectors = _nodes_with_numeric_measurement(graph, graph.nodes_by_type("selector"), "selected_count")
    relation = relation_predicate(
        graph,
        selectors,
        clause_id=spec.relation_clause_id,
        relation=spec.relation,
        target_type=spec.selected_type,
    )
    if relation is None:
        return None
    relation_candidates = _apply_relation_clause(graph, selectors, spec.relation)
    related_metric = related_metric_compare_predicate(
        graph,
        relation_candidates,
        clause_id=spec.related_metric_clause_id,
        relation=spec.relation,
        target_type=spec.selected_type,
        metric=viable.metric,
        operator=viable.operator,
        value=viable.value,
    )
    selected_count = measurement_predicate(
        graph,
        relation_candidates,
        clause_id=spec.selected_count_clause_id,
        metric="selected_count",
    )
    if related_metric is None or selected_count is None:
        return None
    direction = "max" if viable.aggregation == "argmax" else "min"
    sampled = merge_sampled_parameters(
        {
            "target_type": ["selector"],
            "selected_entity_type": [spec.selected_type],
            "final_selector": [f"{direction}:selected_count"],
            "aggregation_metric": ["selected_count"],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "synthesis_strategy": ["selector_count_narrowing_v1"],
        },
        relation.sampled_parameters,
        related_metric.sampled_parameters,
        selected_count.sampled_parameters,
    )
    axis = metric_axis(viable.metric)
    if axis is not None:
        sampled = merge_sampled_parameters(sampled, {"narrowing_axis": [axis]})
    return QueryProgram(
        query_id=f"{graph.graph_id}:synth:{spec.family_id}",
        target_type="selector",
        clauses=[
            relation.clause,
            related_metric.clause,
            selected_count.clause,
        ],
        aggregation=viable.aggregation,
        aggregation_metric="selected_count",
        hop_count=4,
        difficulty="cad_browsecomp",
        min_individual_clause_candidates=2,
        sampled_parameters=sampled,
    )


def _apply_relation_clause(graph: OntologyGraph, candidates: list[Node], relation_type: str) -> list[Node]:
    return [
        node
        for node in candidates
        if any(edge.source_id == node.id and edge.type == relation_type for edge in graph.relations)
    ]


def _related_metric_thresholds(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    relation: str,
    metric: str,
) -> list[tuple[str, float]]:
    values = sorted(
        {
            round(float(measurement.value), 6)
            for node in candidates
            for edge in graph.relations
            if edge.source_id == node.id and edge.type == relation
            for measurement in graph.measurements_for(edge.target_id, metric)
            if isinstance(measurement.value, (int, float))
        }
    )
    thresholds: list[tuple[str, float]] = []
    for value in values:
        if any(candidate_value < value for candidate_value in values):
            thresholds.append(("<", value))
        if any(candidate_value > value for candidate_value in values):
            thresholds.append((">", value))
    return thresholds[:24]


def _nodes_with_numeric_measurement(graph: OntologyGraph, candidates: list[Node], metric: str) -> list[Node]:
    return [
        node
        for node in candidates
        if isinstance(_measurement_value(graph, node.id, metric), (int, float))
    ]


def _has_unique_extreme(
    graph: OntologyGraph,
    candidates: list[Node],
    metric: str,
    aggregation: str,
) -> bool:
    scores = [
        float(value)
        for node in candidates
        if isinstance((value := _measurement_value(graph, node.id, metric)), (int, float))
    ]
    if len(scores) < 2:
        return False
    ordered = sorted(scores, reverse=aggregation == "argmax")
    return abs(ordered[0] - ordered[1]) > GEOMETRY_MARGIN_EPSILON


def _extreme_nodes(
    graph: OntologyGraph,
    candidates: list[Node],
    metric: str,
    aggregation: str,
) -> list[Node]:
    scored = [
        (float(value), node)
        for node in candidates
        if isinstance((value := _measurement_value(graph, node.id, metric)), (int, float))
    ]
    if not scored:
        return []
    target = max(score for score, _ in scored) if aggregation == "argmax" else min(score for score, _ in scored)
    return [node for score, node in scored if abs(score - target) <= GEOMETRY_MARGIN_EPSILON]


def _viable_tie_breaks(
    graph: OntologyGraph,
    spec: ExtremeFamilySpec,
    tied: list[Node],
    *,
    primary_metric: str,
) -> list[tuple[str, str]]:
    if len(tied) < 2:
        return []
    viable = []
    for metric in spec.metrics:
        if metric == primary_metric:
            continue
        metric_candidates = _nodes_with_numeric_measurement(graph, tied, metric)
        if len(metric_candidates) < 2:
            continue
        for aggregation in ("argmax", "argmin"):
            if _has_unique_extreme(graph, metric_candidates, metric, aggregation):
                viable.append((metric, aggregation))
    return sorted(viable)


def _measurement_value(graph: OntologyGraph, entity_id: str, metric: str) -> Any:
    measurements = graph.measurements_for(entity_id, metric)
    return measurements[0].value if measurements else None


def _stable_choice_index(graph_id: str, family_id: str, count: int) -> int:
    digest = hashlib.sha256(f"{graph_id}:{family_id}".encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % count
