"""Bounded graph-hop query synthesis over ontology graphs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from cad_qa.ontology.nodes import Node, OntologyGraph
from cad_qa.query.ir import Clause, QueryProgram
from cad_qa.query.predicate_catalog import (
    measurement_bucket_value,
    measurement_value_predicate,
    merge_sampled_parameters,
    metric_axis,
    measurement_predicate,
    nodes_matching_measurement_value,
    nodes_matching_related_metric_compare,
    related_metric_compare_predicate,
    relation_predicate,
)


GEOMETRY_MARGIN_EPSILON = 1e-6
REFERENCE_FEATURE_DISTANCE_METRIC = "distance_to_reference_feature_centroid"


@dataclass(frozen=True)
class ExtremeFamilySpec:
    family_id: str
    target_type: str
    relation: str | None
    relation_clause_id: str | None
    measurement_clause_id: str
    metrics: tuple[str, ...]
    relation_target_type: str | None = "selector"
    allow_rank: bool = False


@dataclass(frozen=True)
class ViableExtreme:
    spec: ExtremeFamilySpec
    candidates: list[Node]
    metric: str
    aggregation: str
    aggregation_rank: int | None = None
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


@dataclass(frozen=True)
class EqualValueExtremeFamilySpec:
    family_id: str
    target_type: str
    relation: str | None
    relation_clause_id: str | None
    equal_value_clause_id: str
    selector_metric_clause_id: str
    equal_metrics: tuple[str, ...]
    selector_metrics: tuple[str, ...]
    relation_target_type: str | None = "selector"
    extra_relation: str | None = None
    extra_relation_clause_id: str | None = None
    extra_relation_target_type: str | None = None


@dataclass(frozen=True)
class ViableEqualValueExtreme:
    spec: EqualValueExtremeFamilySpec
    equal_metric: str
    equal_value: float
    selector_metric: str
    aggregation: str
    candidate_ids: tuple[str, ...]


@dataclass(frozen=True)
class ReferenceDistanceFamilySpec:
    family_id: str
    target_type: str
    relation: str | None
    relation_clause_id: str | None
    relation_target_type: str | None
    equal_value_clause_id: str
    reference_clause_id: str
    target_point_clause_id: str
    equal_metric: str
    target_point_metric: str
    reference_type: str
    reference_point_metric: str


@dataclass(frozen=True)
class ViableReferenceDistance:
    spec: ReferenceDistanceFamilySpec
    equal_value: float
    reference_id: str
    aggregation: str
    candidate_ids: tuple[str, ...]


@dataclass(frozen=True)
class RelationExtremeFamilySpec:
    family_id: str
    target_type: str
    base_relation: str
    base_relation_clause_id: str
    base_relation_target_type: str
    relations: tuple[str, ...]
    relation_clause_id: str
    measurement_clause_id: str
    metrics: tuple[str, ...]
    relation_target_type: str


@dataclass(frozen=True)
class ViableRelationExtreme:
    spec: RelationExtremeFamilySpec
    relation: str
    metric: str
    aggregation: str
    candidate_ids: tuple[str, ...]


EXTREME_FAMILY_SPECS = (
    ExtremeFamilySpec(
        family_id="parameterized_feature_extreme",
        target_type="feature",
        relation=None,
        relation_clause_id=None,
        measurement_clause_id="has_parameterized_feature_metric",
        metrics=(
            "volume",
            "centroid_x",
            "centroid_y",
            "centroid_z",
            "bbox_span_z",
            "topology_faces",
            "topology_edges",
        ),
    ),
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
    ExtremeFamilySpec(
        family_id="parameterized_path_point_extreme",
        target_type="path_point",
        relation="point_on_path",
        relation_clause_id="has_parameterized_path_point_set",
        measurement_clause_id="has_parameterized_path_point_metric",
        metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
        ),
        relation_target_type="path",
    ),
    ExtremeFamilySpec(
        family_id="parameterized_path_segment_extreme",
        target_type="path_segment",
        relation="segment_on_path",
        relation_clause_id="has_parameterized_path_segment_set",
        measurement_clause_id="has_parameterized_path_segment_metric",
        metrics=("segment_length",),
        relation_target_type="path",
    ),
)

RANK_FAMILY_SPECS = (
    ExtremeFamilySpec(
        family_id="parameterized_feature_rank",
        target_type="feature",
        relation=None,
        relation_clause_id=None,
        measurement_clause_id="has_parameterized_feature_metric",
        metrics=(
            "volume",
            "centroid_x",
            "centroid_y",
            "centroid_z",
            "bbox_span_z",
            "topology_faces",
            "topology_edges",
        ),
        allow_rank=True,
    ),
    ExtremeFamilySpec(
        family_id="parameterized_kernel_face_rank",
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
        allow_rank=True,
    ),
    ExtremeFamilySpec(
        family_id="parameterized_kernel_edge_rank",
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
        allow_rank=True,
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

EQUAL_VALUE_EXTREME_FAMILY_SPECS = (
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_face_metric_extreme",
        target_type="face",
        relation="has_kernel_stable_face_id",
        relation_clause_id="has_parameterized_face_set",
        equal_value_clause_id="has_parameterized_equal_face_metric_value",
        selector_metric_clause_id="has_parameterized_face_metric",
        equal_metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
            "face_area",
        ),
        selector_metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
            "face_area",
        ),
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_feature_metric_extreme",
        target_type="feature",
        relation=None,
        relation_clause_id=None,
        equal_value_clause_id="has_parameterized_equal_feature_metric_value",
        selector_metric_clause_id="has_parameterized_feature_metric",
        equal_metrics=(
            "volume",
            "centroid_x",
            "centroid_y",
            "centroid_z",
            "bbox_span_z",
        ),
        selector_metrics=(
            "volume",
            "centroid_x",
            "centroid_y",
            "centroid_z",
            "bbox_span_z",
        ),
        relation_target_type=None,
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_material_region_metric_extreme",
        target_type="material_region",
        relation="has_kernel_material_region_geometry",
        relation_clause_id="has_region_geometry",
        equal_value_clause_id="has_region_volume_value",
        selector_metric_clause_id="has_region_centroid_z",
        equal_metrics=("volume",),
        selector_metrics=("centroid_z",),
        relation_target_type="material_region",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_void_region_metric_extreme",
        target_type="void_region",
        relation="has_kernel_void_region_geometry",
        relation_clause_id="has_void_geometry",
        equal_value_clause_id="has_void_volume_value",
        selector_metric_clause_id="has_void_centroid_z",
        equal_metrics=("volume",),
        selector_metrics=("centroid_z",),
        relation_target_type="void_region",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_edge_metric_extreme",
        target_type="edge",
        relation="has_kernel_stable_edge_id",
        relation_clause_id="has_parameterized_edge_set",
        equal_value_clause_id="has_parameterized_equal_edge_metric_value",
        selector_metric_clause_id="has_parameterized_edge_metric",
        equal_metrics=(
            "midpoint_x",
            "midpoint_y",
            "midpoint_z",
            "midpoint_distance_to_origin",
            "edge_length",
        ),
        selector_metrics=(
            "midpoint_x",
            "midpoint_y",
            "midpoint_z",
            "midpoint_distance_to_origin",
            "edge_length",
        ),
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_endpoint_metric_extreme",
        target_type="edge_endpoint",
        relation="endpoint_of",
        relation_clause_id="has_parameterized_endpoint_set",
        equal_value_clause_id="has_parameterized_equal_endpoint_metric_value",
        selector_metric_clause_id="has_parameterized_endpoint_metric",
        equal_metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
        ),
        selector_metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
        ),
        relation_target_type="edge",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_contained_endpoint_metric_extreme",
        target_type="edge_endpoint",
        relation="endpoint_of",
        relation_clause_id="has_parameterized_endpoint_set",
        equal_value_clause_id="has_parameterized_equal_endpoint_metric_value",
        selector_metric_clause_id="has_parameterized_endpoint_metric",
        equal_metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
        ),
        selector_metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
        ),
        relation_target_type="edge",
        extra_relation="contained_in",
        extra_relation_clause_id="has_parameterized_contained_endpoint_set",
        extra_relation_target_type="edge",
    ),
)

RELATION_EXTREME_FAMILY_SPECS = (
    RelationExtremeFamilySpec(
        family_id="parameterized_face_spatial_relation_extreme",
        target_type="face",
        base_relation="has_kernel_stable_face_id",
        base_relation_clause_id="has_parameterized_face_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "intersects",
            "opposite_to",
            "perpendicular_to",
        ),
        relation_clause_id="has_parameterized_face_spatial_relation",
        measurement_clause_id="has_parameterized_face_metric",
        metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
            "face_area",
        ),
        relation_target_type="face",
    ),
    RelationExtremeFamilySpec(
        family_id="parameterized_edge_spatial_relation_extreme",
        target_type="edge",
        base_relation="has_kernel_stable_edge_id",
        base_relation_clause_id="has_parameterized_edge_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "intersects",
            "opposite_to",
            "perpendicular_to",
        ),
        relation_clause_id="has_parameterized_edge_spatial_relation",
        measurement_clause_id="has_parameterized_edge_metric",
        metrics=(
            "midpoint_x",
            "midpoint_y",
            "midpoint_z",
            "midpoint_distance_to_origin",
            "edge_length",
        ),
        relation_target_type="edge",
    ),
)

REFERENCE_DISTANCE_FAMILY_SPECS = (
    ReferenceDistanceFamilySpec(
        family_id="parameterized_face_reference_feature_distance",
        target_type="face",
        relation="has_kernel_stable_face_id",
        relation_clause_id="has_parameterized_face_set",
        relation_target_type="selector",
        equal_value_clause_id="has_parameterized_equal_face_metric_value",
        reference_clause_id="reference_feature_volume_and_centroid",
        target_point_clause_id="has_face_center_for_reference_distance",
        equal_metric="face_area",
        target_point_metric="face_center",
        reference_type="feature",
        reference_point_metric="centroid",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_edge_reference_feature_distance",
        target_type="edge",
        relation="has_kernel_stable_edge_id",
        relation_clause_id="has_parameterized_edge_set",
        relation_target_type="selector",
        equal_value_clause_id="has_parameterized_equal_edge_metric_value",
        reference_clause_id="reference_feature_volume_and_centroid",
        target_point_clause_id="has_edge_midpoint_for_reference_distance",
        equal_metric="edge_length",
        target_point_metric="midpoint",
        reference_type="feature",
        reference_point_metric="centroid",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_feature_reference_feature_distance",
        target_type="feature",
        relation=None,
        relation_clause_id=None,
        relation_target_type=None,
        equal_value_clause_id="has_parameterized_equal_feature_metric_value",
        reference_clause_id="reference_feature_volume_and_centroid",
        target_point_clause_id="has_feature_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="feature",
        reference_point_metric="centroid",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_endpoint_reference_feature_distance",
        target_type="edge_endpoint",
        relation="endpoint_of",
        relation_clause_id="has_parameterized_endpoint_set",
        relation_target_type="edge",
        equal_value_clause_id="has_parameterized_equal_endpoint_metric_value",
        reference_clause_id="reference_feature_volume_and_centroid",
        target_point_clause_id="has_endpoint_for_reference_distance",
        equal_metric="coordinate_z",
        target_point_metric="coordinate",
        reference_type="feature",
        reference_point_metric="centroid",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_material_region_reference_feature_distance",
        target_type="material_region",
        relation="has_kernel_material_region_geometry",
        relation_clause_id="has_region_geometry",
        relation_target_type="material_region",
        equal_value_clause_id="has_region_volume_value",
        reference_clause_id="reference_feature_volume_and_centroid",
        target_point_clause_id="has_region_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="feature",
        reference_point_metric="centroid",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_void_region_reference_feature_distance",
        target_type="void_region",
        relation="has_kernel_void_region_geometry",
        relation_clause_id="has_void_geometry",
        relation_target_type="void_region",
        equal_value_clause_id="has_void_volume_value",
        reference_clause_id="reference_feature_volume_and_centroid",
        target_point_clause_id="has_void_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="feature",
        reference_point_metric="centroid",
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
    for spec in RANK_FAMILY_SPECS:
        viable = _viable_ranks(graph, spec)
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
    for spec in EQUAL_VALUE_EXTREME_FAMILY_SPECS:
        viable = _viable_equal_value_extremes(graph, spec)
        if not viable:
            continue
        choice = viable[_stable_choice_index(graph.graph_id, spec.family_id, len(viable))]
        query = _query_for_equal_value_extreme(graph, choice)
        if query is not None:
            queries.append(query)
    for spec in RELATION_EXTREME_FAMILY_SPECS:
        viable = _viable_relation_extremes(graph, spec)
        if not viable:
            continue
        choice = viable[_stable_choice_index(graph.graph_id, spec.family_id, len(viable))]
        query = _query_for_relation_extreme(graph, choice)
        if query is not None:
            queries.append(query)
    for spec in REFERENCE_DISTANCE_FAMILY_SPECS:
        viable = _viable_reference_distances(graph, spec)
        if not viable:
            continue
        choice = viable[_stable_choice_index(graph.graph_id, spec.family_id, len(viable))]
        query = _query_for_reference_distance(graph, choice)
        if query is not None:
            queries.append(query)
    return queries


def _viable_extremes(graph: OntologyGraph, spec: ExtremeFamilySpec) -> list[ViableExtreme]:
    candidates = graph.nodes_by_type(spec.target_type)
    relation_candidates = _relation_filtered_candidates(graph, candidates, spec)
    if relation_candidates is None:
        return []
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
            item.aggregation_rank or 0,
            item.tie_break_metric or "",
            item.tie_break_aggregation or "",
            [node.id for node in item.candidates],
        ),
    )


def _viable_ranks(graph: OntologyGraph, spec: ExtremeFamilySpec) -> list[ViableExtreme]:
    candidates = graph.nodes_by_type(spec.target_type)
    if not spec.allow_rank:
        return []
    relation_candidates = _relation_filtered_candidates(graph, candidates, spec)
    if relation_candidates is None:
        return []
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
        if len(metric_candidates) < 3:
            continue
        for aggregation in ("rank_desc", "rank_asc"):
            for rank in range(2, min(len(metric_candidates), 4) + 1):
                if _has_unique_rank(graph, metric_candidates, metric, aggregation, rank):
                    viable.append(ViableExtreme(spec, metric_candidates, metric, aggregation, aggregation_rank=rank))
    return sorted(
        viable,
        key=lambda item: (
            item.metric,
            item.aggregation,
            item.aggregation_rank or 0,
            [node.id for node in item.candidates],
        ),
    )


def _query_for_extreme(graph: OntologyGraph, viable: ViableExtreme) -> QueryProgram | None:
    spec = viable.spec
    broad_candidates = graph.nodes_by_type(spec.target_type)
    relation = _relation_instance(graph, broad_candidates, spec)
    if spec.relation is not None and relation is None:
        return None
    relation_candidates = _apply_relation_clause(graph, broad_candidates, spec.relation) if spec.relation is not None else broad_candidates
    measurement = measurement_predicate(
        graph,
        relation_candidates,
        clause_id=spec.measurement_clause_id,
        metric=viable.metric,
    )
    if measurement is None:
        return None
    direction = "max" if viable.aggregation in {"argmax", "rank_desc"} else "min"
    final_selector = (
        f"rank:{viable.aggregation_rank}:{direction}:{viable.metric}"
        if viable.aggregation_rank is not None
        else f"{direction}:{viable.metric}"
    )
    sampled = merge_sampled_parameters(
        {
            "target_type": [spec.target_type],
            "final_selector": [final_selector],
            "aggregation_metric": [viable.metric],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "prompt_wording_variant": [_prompt_wording_variant(graph.graph_id, spec.family_id)],
            "synthesis_strategy": [
                "bounded_parameterized_rank_v1"
                if viable.aggregation_rank is not None
                else "bounded_parameterized_extreme_v1"
            ],
        },
        measurement.sampled_parameters,
    )
    if relation is not None:
        sampled = merge_sampled_parameters(sampled, relation.sampled_parameters)
    if viable.aggregation_rank is not None:
        sampled = merge_sampled_parameters(
            sampled,
            {
                "aggregation_rank": [str(viable.aggregation_rank)],
                "rank_direction": [direction],
            },
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
            clause
            for clause in (
                relation.clause if relation is not None else None,
                measurement.clause,
            )
            if clause is not None
        ],
        aggregation=viable.aggregation,
        aggregation_metric=viable.metric,
        aggregation_rank=viable.aggregation_rank,
        tie_break_aggregation=viable.tie_break_aggregation,
        tie_break_metric=viable.tie_break_metric,
        hop_count=2 + int(relation is not None),
        difficulty="cad_browsecomp",
        min_individual_clause_candidates=2,
        sampled_parameters=sampled,
    )


def _relation_instance(
    graph: OntologyGraph,
    candidates: list[Node],
    spec: ExtremeFamilySpec,
) -> Any | None:
    if spec.relation is None or spec.relation_clause_id is None or spec.relation_target_type is None:
        return None
    return relation_predicate(
        graph,
        candidates,
        clause_id=spec.relation_clause_id,
        relation=spec.relation,
        target_type=spec.relation_target_type,
    )


def _relation_filtered_candidates(
    graph: OntologyGraph,
    candidates: list[Node],
    spec: ExtremeFamilySpec,
) -> list[Node] | None:
    if spec.relation is None:
        return candidates
    relation = _relation_instance(graph, candidates, spec)
    if relation is None:
        return None
    return _apply_relation_clause(graph, candidates, spec.relation)


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
            "prompt_wording_variant": [_prompt_wording_variant(graph.graph_id, spec.family_id)],
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


def _viable_equal_value_extremes(
    graph: OntologyGraph,
    spec: EqualValueExtremeFamilySpec,
) -> list[ViableEqualValueExtreme]:
    candidates = graph.nodes_by_type(spec.target_type)
    if spec.relation is not None and spec.relation_clause_id is not None and spec.relation_target_type is not None:
        relation = relation_predicate(
            graph,
            candidates,
            clause_id=spec.relation_clause_id,
            relation=spec.relation,
            target_type=spec.relation_target_type,
        )
        if relation is None:
            return []
        relation_candidates = _apply_relation_clause(graph, candidates, spec.relation)
    else:
        relation_candidates = candidates
    if (
        spec.extra_relation is not None
        and spec.extra_relation_clause_id is not None
        and spec.extra_relation_target_type is not None
    ):
        extra_relation = relation_predicate(
            graph,
            relation_candidates,
            clause_id=spec.extra_relation_clause_id,
            relation=spec.extra_relation,
            target_type=spec.extra_relation_target_type,
        )
        if extra_relation is None:
            return []
        relation_candidates = _apply_relation_clause(graph, relation_candidates, spec.extra_relation)
    viable: list[ViableEqualValueExtreme] = []
    for equal_metric in spec.equal_metrics:
        for equal_value, equal_nodes in _equal_measurement_groups(graph, relation_candidates, equal_metric):
            value_predicate = measurement_value_predicate(
                graph,
                relation_candidates,
                clause_id=spec.equal_value_clause_id,
                metric=equal_metric,
                value=equal_value,
            )
            if value_predicate is None:
                continue
            for selector_metric in spec.selector_metrics:
                if selector_metric == equal_metric:
                    continue
                measurement = measurement_predicate(
                    graph,
                    equal_nodes,
                    clause_id=spec.selector_metric_clause_id,
                    metric=selector_metric,
                )
                if measurement is None:
                    continue
                metric_candidates = _nodes_with_numeric_measurement(graph, equal_nodes, selector_metric)
                if len(metric_candidates) < 2:
                    continue
                for aggregation in ("argmax", "argmin"):
                    if _has_unique_extreme(graph, metric_candidates, selector_metric, aggregation):
                        viable.append(
                            ViableEqualValueExtreme(
                                spec=spec,
                                equal_metric=equal_metric,
                                equal_value=equal_value,
                                selector_metric=selector_metric,
                                aggregation=aggregation,
                                candidate_ids=tuple(node.id for node in metric_candidates),
                            )
                        )
    return sorted(
        viable,
        key=lambda item: (
            item.equal_metric,
            item.equal_value,
            item.selector_metric,
            item.aggregation,
            item.candidate_ids,
        ),
    )


def _query_for_equal_value_extreme(graph: OntologyGraph, viable: ViableEqualValueExtreme) -> QueryProgram | None:
    spec = viable.spec
    broad_candidates = graph.nodes_by_type(spec.target_type)
    relation = None
    extra_relation = None
    relation_candidates = broad_candidates
    if spec.relation is not None and spec.relation_clause_id is not None and spec.relation_target_type is not None:
        relation = relation_predicate(
            graph,
            broad_candidates,
            clause_id=spec.relation_clause_id,
            relation=spec.relation,
            target_type=spec.relation_target_type,
        )
        if relation is None:
            return None
        relation_candidates = _apply_relation_clause(graph, broad_candidates, spec.relation)
    if (
        spec.extra_relation is not None
        and spec.extra_relation_clause_id is not None
        and spec.extra_relation_target_type is not None
    ):
        extra_relation = relation_predicate(
            graph,
            relation_candidates,
            clause_id=spec.extra_relation_clause_id,
            relation=spec.extra_relation,
            target_type=spec.extra_relation_target_type,
        )
        if extra_relation is None:
            return None
        relation_candidates = _apply_relation_clause(graph, relation_candidates, spec.extra_relation)
    equal_value = measurement_value_predicate(
        graph,
        relation_candidates,
        clause_id=spec.equal_value_clause_id,
        metric=viable.equal_metric,
        value=viable.equal_value,
    )
    if equal_value is None:
        return None
    equal_candidates = nodes_matching_measurement_value(
        graph,
        relation_candidates,
        metric=viable.equal_metric,
        value=viable.equal_value,
    )
    selector_metric = measurement_predicate(
        graph,
        equal_candidates,
        clause_id=spec.selector_metric_clause_id,
        metric=viable.selector_metric,
    )
    if selector_metric is None:
        return None
    direction = "max" if viable.aggregation == "argmax" else "min"
    sampled = merge_sampled_parameters(
        {
            "target_type": [spec.target_type],
            "final_selector": [f"{direction}:{viable.selector_metric}"],
            "aggregation_metric": [viable.selector_metric],
            "equal_measurement_metric": [viable.equal_metric],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "prompt_wording_variant": [_prompt_wording_variant(graph.graph_id, spec.family_id)],
            "synthesis_strategy": ["equal_measurement_narrowing_v1"],
        },
        equal_value.sampled_parameters,
        selector_metric.sampled_parameters,
    )
    if relation is not None:
        sampled = merge_sampled_parameters(sampled, relation.sampled_parameters)
    if extra_relation is not None:
        sampled = merge_sampled_parameters(sampled, extra_relation.sampled_parameters)
    selector_axis = metric_axis(viable.selector_metric)
    if selector_axis is not None:
        sampled = merge_sampled_parameters(sampled, {"aggregation_axis": [selector_axis]})
    equal_axis = metric_axis(viable.equal_metric)
    if equal_axis is not None:
        sampled = merge_sampled_parameters(sampled, {"equal_measurement_axis": [equal_axis]})
    return QueryProgram(
        query_id=f"{graph.graph_id}:synth:{spec.family_id}",
        target_type=spec.target_type,
        clauses=[
            clause
            for clause in (
                relation.clause if relation is not None else None,
                extra_relation.clause if extra_relation is not None else None,
                equal_value.clause,
                selector_metric.clause,
            )
            if clause is not None
        ],
        aggregation=viable.aggregation,
        aggregation_metric=viable.selector_metric,
        hop_count=3 + int(relation is not None) + int(extra_relation is not None),
        difficulty="cad_browsecomp",
        min_individual_clause_candidates=2,
        sampled_parameters=sampled,
    )


def _viable_relation_extremes(
    graph: OntologyGraph,
    spec: RelationExtremeFamilySpec,
) -> list[ViableRelationExtreme]:
    candidates = graph.nodes_by_type(spec.target_type)
    base_relation = relation_predicate(
        graph,
        candidates,
        clause_id=spec.base_relation_clause_id,
        relation=spec.base_relation,
        target_type=spec.base_relation_target_type,
    )
    if base_relation is None:
        return []
    base_candidates = _apply_relation_clause(graph, candidates, spec.base_relation)
    viable: list[ViableRelationExtreme] = []
    for relation_name in spec.relations:
        relation = relation_predicate(
            graph,
            base_candidates,
            clause_id=spec.relation_clause_id,
            relation=relation_name,
            target_type=spec.relation_target_type,
        )
        if relation is None:
            continue
        relation_candidates = _apply_relation_clause(graph, base_candidates, relation_name)
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
                    viable.append(
                        ViableRelationExtreme(
                            spec=spec,
                            relation=relation_name,
                            metric=metric,
                            aggregation=aggregation,
                            candidate_ids=tuple(node.id for node in metric_candidates),
                        )
                    )
    return sorted(
        viable,
        key=lambda item: (
            item.relation,
            item.metric,
            item.aggregation,
            item.candidate_ids,
        ),
    )


def _query_for_relation_extreme(graph: OntologyGraph, viable: ViableRelationExtreme) -> QueryProgram | None:
    spec = viable.spec
    broad_candidates = graph.nodes_by_type(spec.target_type)
    base_relation = relation_predicate(
        graph,
        broad_candidates,
        clause_id=spec.base_relation_clause_id,
        relation=spec.base_relation,
        target_type=spec.base_relation_target_type,
    )
    if base_relation is None:
        return None
    base_candidates = _apply_relation_clause(graph, broad_candidates, spec.base_relation)
    relation = relation_predicate(
        graph,
        base_candidates,
        clause_id=spec.relation_clause_id,
        relation=viable.relation,
        target_type=spec.relation_target_type,
    )
    if relation is None:
        return None
    relation_candidates = _apply_relation_clause(graph, base_candidates, viable.relation)
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
            "spatial_relation": [viable.relation],
            "final_selector": [f"{direction}:{viable.metric}"],
            "aggregation_metric": [viable.metric],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "prompt_wording_variant": [_prompt_wording_variant(graph.graph_id, spec.family_id)],
            "synthesis_strategy": ["spatial_relation_extreme_v1"],
        },
        relation.sampled_parameters,
        measurement.sampled_parameters,
    )
    axis = metric_axis(viable.metric)
    if axis is not None:
        sampled = merge_sampled_parameters(sampled, {"aggregation_axis": [axis]})
    return QueryProgram(
        query_id=f"{graph.graph_id}:synth:{spec.family_id}",
        target_type=spec.target_type,
        clauses=[
            base_relation.clause,
            relation.clause,
            measurement.clause,
        ],
        aggregation=viable.aggregation,
        aggregation_metric=viable.metric,
        hop_count=4,
        difficulty="cad_browsecomp",
        min_individual_clause_candidates=2,
        sampled_parameters=sampled,
    )


def _viable_reference_distances(
    graph: OntologyGraph,
    spec: ReferenceDistanceFamilySpec,
) -> list[ViableReferenceDistance]:
    candidates = graph.nodes_by_type(spec.target_type)
    if spec.relation is not None and spec.relation_clause_id is not None and spec.relation_target_type is not None:
        relation = relation_predicate(
            graph,
            candidates,
            clause_id=spec.relation_clause_id,
            relation=spec.relation,
            target_type=spec.relation_target_type,
        )
        if relation is None:
            return []
        relation_candidates = _apply_relation_clause(graph, candidates, spec.relation)
    else:
        relation_candidates = candidates
    references = _unique_reference_features(graph, graph.nodes_by_type(spec.reference_type))
    if not references:
        return []
    viable: list[ViableReferenceDistance] = []
    for equal_value, equal_nodes in _equal_measurement_groups(graph, relation_candidates, spec.equal_metric):
        equal_node_ids = {node.id for node in equal_nodes}
        target_nodes = [
            node
            for node in equal_nodes
            if _point_measurement(graph, node.id, spec.target_point_metric) is not None
        ]
        if len(target_nodes) < 2:
            continue
        if measurement_value_predicate(
            graph,
            relation_candidates,
            clause_id=spec.equal_value_clause_id,
            metric=spec.equal_metric,
            value=equal_value,
        ) is None:
            continue
        for reference in references:
            reference_point = _point_measurement(graph, reference.id, spec.reference_point_metric)
            if reference_point is None:
                continue
            if reference.id in equal_node_ids:
                continue
            distances = [
                _point_distance(_point_measurement(graph, target.id, spec.target_point_metric), reference_point)
                for target in target_nodes
            ]
            ordered = sorted(distances)
            if len(ordered) >= 2 and abs(ordered[0] - ordered[1]) > GEOMETRY_MARGIN_EPSILON:
                viable.append(
                    ViableReferenceDistance(
                        spec=spec,
                        equal_value=equal_value,
                        reference_id=reference.id,
                        aggregation="argmin",
                        candidate_ids=tuple(node.id for node in target_nodes),
                    )
                )
            ordered_desc = sorted(distances, reverse=True)
            if len(ordered_desc) >= 2 and abs(ordered_desc[0] - ordered_desc[1]) > GEOMETRY_MARGIN_EPSILON:
                viable.append(
                    ViableReferenceDistance(
                        spec=spec,
                        equal_value=equal_value,
                        reference_id=reference.id,
                        aggregation="argmax",
                        candidate_ids=tuple(node.id for node in target_nodes),
                    )
                )
    return sorted(
        viable,
        key=lambda item: (
            item.equal_value,
            item.reference_id,
            item.aggregation,
            item.candidate_ids,
        ),
    )


def _query_for_reference_distance(graph: OntologyGraph, viable: ViableReferenceDistance) -> QueryProgram | None:
    spec = viable.spec
    broad_candidates = graph.nodes_by_type(spec.target_type)
    relation = None
    relation_candidates = broad_candidates
    if spec.relation is not None and spec.relation_clause_id is not None and spec.relation_target_type is not None:
        relation = relation_predicate(
            graph,
            broad_candidates,
            clause_id=spec.relation_clause_id,
            relation=spec.relation,
            target_type=spec.relation_target_type,
        )
        if relation is None:
            return None
        relation_candidates = _apply_relation_clause(graph, broad_candidates, spec.relation)
    equal_value = measurement_value_predicate(
        graph,
        relation_candidates,
        clause_id=spec.equal_value_clause_id,
        metric=spec.equal_metric,
        value=viable.equal_value,
    )
    if equal_value is None:
        return None
    equal_candidates = nodes_matching_measurement_value(
        graph,
        relation_candidates,
        metric=spec.equal_metric,
        value=viable.equal_value,
    )
    target_point = measurement_predicate(
        graph,
        equal_candidates,
        clause_id=spec.target_point_clause_id,
        metric=spec.target_point_metric,
    )
    reference = graph.node(viable.reference_id)
    if target_point is None or reference is None:
        return None
    reference_value = _reference_feature_prompt_value(graph, reference)
    direction = "min" if viable.aggregation == "argmin" else "max"
    sampled = merge_sampled_parameters(
        {
            "target_type": [spec.target_type],
            "reference_type": [spec.reference_type],
            "reference_metric": [REFERENCE_FEATURE_DISTANCE_METRIC],
            "reference_point_metric": [spec.reference_point_metric],
            "target_point_metric": [spec.target_point_metric],
            "reference_anchor_id": [viable.reference_id],
            "reference_anchor_metric": ["centroid_z", "volume"],
            "reference_anchor_signature": [_reference_anchor_signature(reference_value)],
            "reference_anchor_value_bucket": [
                f"centroid_z:{_value_bucket(reference_value.get('reference_centroid_z'))}",
                f"volume:{_value_bucket(reference_value.get('reference_volume'))}",
            ],
            "final_selector": [f"{direction}:{REFERENCE_FEATURE_DISTANCE_METRIC}"],
            "aggregation_metric": [REFERENCE_FEATURE_DISTANCE_METRIC],
            "equal_measurement_metric": [spec.equal_metric],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "prompt_wording_variant": [_prompt_wording_variant(graph.graph_id, spec.family_id)],
            "synthesis_strategy": ["reference_distance_narrowing_v1"],
        },
        equal_value.sampled_parameters,
        target_point.sampled_parameters,
    )
    if relation is not None:
        sampled = merge_sampled_parameters(sampled, relation.sampled_parameters)
    return QueryProgram(
        query_id=f"{graph.graph_id}:synth:{spec.family_id}",
        target_type=spec.target_type,
        clauses=[
            clause
            for clause in (
                relation.clause if relation is not None else None,
                equal_value.clause,
                Clause(
                    id=spec.reference_clause_id,
                    kind="reference_measurement",
                    metric=REFERENCE_FEATURE_DISTANCE_METRIC,
                    value=reference_value,
                ),
                target_point.clause,
            )
            if clause is not None
        ],
        aggregation=viable.aggregation,
        aggregation_metric=REFERENCE_FEATURE_DISTANCE_METRIC,
        hop_count=4 + int(relation is not None),
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


def _equal_measurement_groups(
    graph: OntologyGraph,
    candidates: list[Node],
    metric: str,
) -> list[tuple[float, list[Node]]]:
    groups: dict[float, list[Node]] = {}
    for node in candidates:
        bucket = measurement_bucket_value(_measurement_value(graph, node.id, metric))
        if bucket is not None:
            groups.setdefault(bucket, []).append(node)
    return sorted(
        (
            (value, sorted(nodes, key=lambda node: node.id))
            for value, nodes in groups.items()
            if len(nodes) >= 2
        ),
        key=lambda item: (item[0], [node.id for node in item[1]]),
    )


def _unique_reference_features(graph: OntologyGraph, features: list[Node]) -> list[Node]:
    counts: dict[tuple[float | None, float | None], int] = {}
    keyed: list[tuple[Node, tuple[float | None, float | None]]] = []
    for feature in features:
        key = _reference_feature_key(graph, feature.id)
        keyed.append((feature, key))
        counts[key] = counts.get(key, 0) + 1
    return [
        feature
        for feature, key in sorted(keyed, key=lambda item: item[0].id)
        if None not in key
        and counts.get(key, 0) == 1
        and _point_measurement(graph, feature.id, "centroid") is not None
    ]


def _reference_feature_prompt_value(graph: OntologyGraph, reference: Node) -> dict[str, Any]:
    return {
        "reference_id": reference.id,
        "reference_volume": measurement_bucket_value(_measurement_value(graph, reference.id, "volume")),
        "reference_centroid_z": measurement_bucket_value(_measurement_value(graph, reference.id, "centroid_z")),
    }


def _reference_feature_key(graph: OntologyGraph, feature_id: str) -> tuple[float | None, float | None]:
    return (
        measurement_bucket_value(_measurement_value(graph, feature_id, "volume")),
        measurement_bucket_value(_measurement_value(graph, feature_id, "centroid_z")),
    )


def _reference_anchor_signature(reference_value: dict[str, Any]) -> str:
    return (
        "feature:"
        f"centroid_z={_value_bucket(reference_value.get('reference_centroid_z'))}|"
        f"volume={_value_bucket(reference_value.get('reference_volume'))}"
    )


def _point_measurement(graph: OntologyGraph, entity_id: str, metric: str) -> list[float] | None:
    value = _measurement_value(graph, entity_id, metric)
    if isinstance(value, list) and len(value) >= 3:
        return _numeric_point(value[:3])
    scalar_names = {
        "centroid": ("centroid_x", "centroid_y", "centroid_z"),
        "midpoint": ("midpoint_x", "midpoint_y", "midpoint_z"),
    }.get(metric)
    if scalar_names is None:
        return None
    return _numeric_point([_measurement_value(graph, entity_id, name) for name in scalar_names])


def _numeric_point(values: list[Any]) -> list[float] | None:
    point: list[float] = []
    for component in values:
        if not isinstance(component, (int, float)):
            return None
        point.append(float(component))
    return point


def _point_distance(first: list[float] | None, second: list[float] | None) -> float:
    if first is None or second is None:
        return float("inf")
    return sum((first[index] - second[index]) ** 2 for index in range(3)) ** 0.5


def _value_bucket(value: Any) -> str:
    bucket = measurement_bucket_value(value)
    return f"{bucket:.6g}" if bucket is not None else str(value)


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


def _has_unique_rank(
    graph: OntologyGraph,
    candidates: list[Node],
    metric: str,
    aggregation: str,
    rank: int,
) -> bool:
    ranked = _rank_nodes(graph, candidates, metric, aggregation, rank)
    return len(ranked) == 1


def _rank_nodes(
    graph: OntologyGraph,
    candidates: list[Node],
    metric: str,
    aggregation: str,
    rank: int,
) -> list[Node]:
    scored = [
        (float(value), node)
        for node in candidates
        if isinstance((value := _measurement_value(graph, node.id, metric)), (int, float))
    ]
    if rank < 1 or rank > len(scored):
        return []
    descending = aggregation == "rank_desc"
    ordered = sorted(scored, key=lambda item: (-item[0] if descending else item[0], item[1].id))
    target = ordered[rank - 1][0]
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


def _prompt_wording_variant(graph_id: str, family_id: str) -> str:
    return str(_stable_choice_index(graph_id, f"{family_id}:prompt_wording", 3))
