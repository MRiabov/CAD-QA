"""Bounded graph-hop query synthesis over ontology graphs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Any, Callable, TypeVar

from cad_qa.ontology.nodes import Node, OntologyGraph
from cad_qa.query.answers import synthesis_answer_spec_for_target_type
from cad_qa.query.ir import Clause, QueryProgram
from cad_qa.query.predicate_catalog import (
    PredicateInstance,
    measurement_bucket_value,
    merge_sampled_parameters,
    metric_axis,
    nodes_matching_related_metric_compare,
    related_metric_compare_predicate,
    relation_predicate,
)


GEOMETRY_MARGIN_EPSILON = 1e-6
REFERENCE_FEATURE_DISTANCE_METRIC = "distance_to_reference_feature_centroid"
MAX_SYNTHESIZED_RANK = 6
MAX_REFERENCE_DISTANCE_ANCHORS = 64
MAX_METRIC_COMPARE_THRESHOLDS = 12
MAX_RELATED_METRIC_COMPARE_THRESHOLDS = 24
T = TypeVar("T")

MATERIAL_REGION_METRICS = (
    "volume",
    "centroid_x",
    "centroid_y",
    "centroid_z",
    "bbox_center_x",
    "bbox_center_y",
    "bbox_center_z",
    "bbox_span_x",
    "bbox_span_y",
    "bbox_span_z",
    "topology_faces",
    "topology_edges",
)

VOID_REGION_METRICS = (
    "volume",
    "centroid_x",
    "centroid_y",
    "centroid_z",
    "volume_delta_magnitude",
    "bbox_delta_span_x",
    "bbox_delta_span_y",
    "bbox_delta_span_z",
    "bbox_delta_center_z",
    "bbox_delta_max_span",
    "topology_delta_faces",
    "topology_delta_edges",
    "topology_delta_vertices",
)


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
    compare_metric: str | None = None
    compare_operator: str | None = None
    compare_value: float | None = None


@dataclass(frozen=True)
class SelectorCountFamilySpec:
    family_id: str
    relation: str
    selected_type: str
    relation_clause_id: str
    selector_relation_clause_id: str
    related_metric_clause_id: str
    selected_count_clause_id: str
    related_metrics: tuple[str, ...]
    selector_relations: tuple[str, ...] = ()
    selector_tie_break_metrics: tuple[str, ...] = ()
    allow_rank: bool = False


@dataclass(frozen=True)
class ViableSelectorCount:
    spec: SelectorCountFamilySpec
    metric: str
    operator: str
    value: float
    aggregation: str
    candidate_ids: tuple[str, ...]
    selector_relation: str | None = None
    aggregation_rank: int | None = None
    tie_break_metric: str | None = None
    tie_break_aggregation: str | None = None


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
    selection_mode: str = "extreme"


@dataclass(frozen=True)
class ViableEqualValueExtreme:
    spec: EqualValueExtremeFamilySpec
    equal_metric: str
    equal_value: float
    selector_metric: str
    aggregation: str
    candidate_ids: tuple[str, ...]
    aggregation_rank: int | None = None


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
    selection_mode: str = "extreme"


@dataclass(frozen=True)
class ViableReferenceDistance:
    spec: ReferenceDistanceFamilySpec
    equal_value: float
    reference_id: str
    aggregation: str
    candidate_ids: tuple[str, ...]
    aggregation_rank: int | None = None


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
    selection_mode: str = "extreme"


@dataclass(frozen=True)
class ViableRelationExtreme:
    spec: RelationExtremeFamilySpec
    relation: str
    metric: str
    aggregation: str
    candidate_ids: tuple[str, ...]
    aggregation_rank: int | None = None
    tie_break_metric: str | None = None
    tie_break_aggregation: str | None = None
    compare_metric: str | None = None
    compare_operator: str | None = None
    compare_value: float | None = None


@dataclass(frozen=True)
class RelationChainFamilySpec:
    family_id: str
    target_type: str
    base_relation: str
    base_relation_clause_id: str
    base_relation_target_type: str
    relations: tuple[str, ...]
    chain_lengths: tuple[int, ...]
    relation_clause_id: str
    measurement_clause_id: str
    metrics: tuple[str, ...]
    relation_target_type: str
    selection_mode: str = "extreme"


@dataclass(frozen=True)
class ViableRelationChainExtreme:
    spec: RelationChainFamilySpec
    relation_chain: tuple[str, ...]
    metric: str
    aggregation: str
    candidate_ids: tuple[str, ...]
    aggregation_rank: int | None = None
    tie_break_metric: str | None = None
    tie_break_aggregation: str | None = None


@dataclass(frozen=True)
class FeatureEffectDeltaFamilySpec:
    family_id: str
    compare_clause_id: str
    selector_metric_clause_id: str
    metrics: tuple[str, ...]
    selector_metrics: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ViableFeatureEffectDeltaExtreme:
    spec: FeatureEffectDeltaFamilySpec
    compare_metric: str
    operator: str
    selector_metric: str
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
        family_id="parameterized_kernel_vertex_extreme",
        target_type="vertex",
        relation="has_kernel_stable_vertex_id",
        relation_clause_id="has_parameterized_vertex_set",
        measurement_clause_id="has_parameterized_vertex_metric",
        metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
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
        metrics=(
            "segment_length",
            "midpoint_distance_to_origin",
        ),
        relation_target_type="path",
    ),
    ExtremeFamilySpec(
        family_id="parameterized_material_region_extreme",
        target_type="material_region",
        relation="has_kernel_material_region_geometry",
        relation_clause_id="has_region_geometry",
        measurement_clause_id="has_parameterized_material_region_metric",
        metrics=MATERIAL_REGION_METRICS,
        relation_target_type="material_region",
    ),
    ExtremeFamilySpec(
        family_id="parameterized_void_region_extreme",
        target_type="void_region",
        relation="has_kernel_void_region_geometry",
        relation_clause_id="has_void_geometry",
        measurement_clause_id="has_parameterized_void_region_metric",
        metrics=VOID_REGION_METRICS,
        relation_target_type="void_region",
    ),
)

FEATURE_EFFECT_DELTA_METRIC_OPERATORS = {
    "signed_volume_delta": (">", "<"),
    "volume_delta_magnitude": (">",),
    "bbox_delta_span_z": (">",),
    "bbox_delta_max_span": (">",),
    "bbox_delta_min_z": (">",),
    "centroid_delta_z": (">",),
    "centroid_delta_magnitude": (">",),
    "topology_delta_faces": (">",),
    "topology_delta_edges": (">",),
}

FEATURE_EFFECT_DELTA_FAMILY_SPECS = (
    FeatureEffectDeltaFamilySpec(
        family_id="parameterized_feature_effect_delta_extreme",
        compare_clause_id="has_parameterized_feature_effect_delta",
        selector_metric_clause_id="has_parameterized_feature_effect_metric",
        metrics=tuple(FEATURE_EFFECT_DELTA_METRIC_OPERATORS),
        selector_metrics=(
            "volume",
            "centroid_x",
            "centroid_y",
            "centroid_z",
            "bbox_span_x",
            "bbox_span_y",
            "bbox_span_z",
            "bbox_center_x",
            "bbox_center_y",
            "bbox_center_z",
            "topology_faces",
            "topology_edges",
        ),
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
    ExtremeFamilySpec(
        family_id="parameterized_kernel_vertex_rank",
        target_type="vertex",
        relation="has_kernel_stable_vertex_id",
        relation_clause_id="has_parameterized_vertex_set",
        measurement_clause_id="has_parameterized_vertex_metric",
        metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
        ),
        allow_rank=True,
    ),
    ExtremeFamilySpec(
        family_id="parameterized_endpoint_rank",
        target_type="edge_endpoint",
        relation="endpoint_of",
        relation_clause_id="has_parameterized_endpoint_set",
        measurement_clause_id="has_parameterized_endpoint_metric",
        metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
        ),
        relation_target_type="edge",
        allow_rank=True,
    ),
    ExtremeFamilySpec(
        family_id="parameterized_path_point_rank",
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
        allow_rank=True,
    ),
    ExtremeFamilySpec(
        family_id="parameterized_path_segment_rank",
        target_type="path_segment",
        relation="segment_on_path",
        relation_clause_id="has_parameterized_path_segment_set",
        measurement_clause_id="has_parameterized_path_segment_metric",
        metrics=(
            "segment_length",
            "midpoint_distance_to_origin",
        ),
        relation_target_type="path",
        allow_rank=True,
    ),
    ExtremeFamilySpec(
        family_id="parameterized_material_region_rank",
        target_type="material_region",
        relation="has_kernel_material_region_geometry",
        relation_clause_id="has_region_geometry",
        measurement_clause_id="has_parameterized_material_region_metric",
        metrics=MATERIAL_REGION_METRICS,
        relation_target_type="material_region",
        allow_rank=True,
    ),
    ExtremeFamilySpec(
        family_id="parameterized_void_region_rank",
        target_type="void_region",
        relation="has_kernel_void_region_geometry",
        relation_clause_id="has_void_geometry",
        measurement_clause_id="has_parameterized_void_region_metric",
        metrics=VOID_REGION_METRICS,
        relation_target_type="void_region",
        allow_rank=True,
    ),
)

SELECTOR_COUNT_FAMILY_SPECS = (
    SelectorCountFamilySpec(
        family_id="parameterized_kernel_face_selector_count",
        relation="has_kernel_stable_face_id",
        selected_type="face",
        relation_clause_id="has_parameterized_face_selection",
        selector_relation_clause_id="has_parameterized_selector_relation",
        related_metric_clause_id="has_parameterized_selected_face_metric_threshold",
        selected_count_clause_id="has_parameterized_selected_count",
        related_metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
            "face_area",
        ),
        selector_relations=("same_selected_face_as", "same_selected_entity_as"),
        selector_tie_break_metrics=(
            "selected_face_max_coordinate_x",
            "selected_face_min_coordinate_x",
            "selected_face_max_coordinate_y",
            "selected_face_min_coordinate_y",
            "selected_face_max_coordinate_z",
            "selected_face_min_coordinate_z",
            "selected_face_max_face_area",
            "selected_face_min_face_area",
        ),
    ),
    SelectorCountFamilySpec(
        family_id="parameterized_kernel_edge_selector_count",
        relation="has_kernel_stable_edge_id",
        selected_type="edge",
        relation_clause_id="has_parameterized_edge_selection",
        selector_relation_clause_id="has_parameterized_selector_relation",
        related_metric_clause_id="has_parameterized_selected_edge_metric_threshold",
        selected_count_clause_id="has_parameterized_selected_count",
        related_metrics=(
            "midpoint_x",
            "midpoint_y",
            "midpoint_z",
            "midpoint_distance_to_origin",
            "edge_length",
        ),
        selector_relations=("same_selected_entity_as",),
        selector_tie_break_metrics=(
            "selected_edge_max_midpoint_x",
            "selected_edge_min_midpoint_x",
            "selected_edge_max_midpoint_y",
            "selected_edge_min_midpoint_y",
            "selected_edge_max_midpoint_z",
            "selected_edge_min_midpoint_z",
            "selected_edge_max_edge_length",
            "selected_edge_min_edge_length",
            "selected_edge_max_midpoint_distance_to_origin",
            "selected_edge_min_midpoint_distance_to_origin",
        ),
    ),
    SelectorCountFamilySpec(
        family_id="parameterized_kernel_vertex_selector_count",
        relation="has_kernel_stable_vertex_id",
        selected_type="vertex",
        relation_clause_id="has_parameterized_vertex_selection",
        selector_relation_clause_id="has_parameterized_selector_relation",
        related_metric_clause_id="has_parameterized_selected_vertex_metric_threshold",
        selected_count_clause_id="has_parameterized_selected_count",
        related_metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
        ),
        selector_relations=("same_selected_entity_as",),
        selector_tie_break_metrics=(
            "selected_vertex_max_coordinate_x",
            "selected_vertex_min_coordinate_x",
            "selected_vertex_max_coordinate_y",
            "selected_vertex_min_coordinate_y",
            "selected_vertex_max_coordinate_z",
            "selected_vertex_min_coordinate_z",
            "selected_vertex_max_distance_to_origin",
            "selected_vertex_min_distance_to_origin",
        ),
    ),
)

SELECTOR_COUNT_RANK_FAMILY_SPECS = (
    SelectorCountFamilySpec(
        family_id="parameterized_kernel_face_selector_count_rank",
        relation="has_kernel_stable_face_id",
        selected_type="face",
        relation_clause_id="has_parameterized_face_selection",
        selector_relation_clause_id="has_parameterized_selector_relation",
        related_metric_clause_id="has_parameterized_selected_face_metric_threshold",
        selected_count_clause_id="has_parameterized_selected_count",
        related_metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
            "face_area",
        ),
        selector_relations=("same_selected_face_as", "same_selected_entity_as"),
        selector_tie_break_metrics=(
            "selected_face_max_coordinate_x",
            "selected_face_min_coordinate_x",
            "selected_face_max_coordinate_y",
            "selected_face_min_coordinate_y",
            "selected_face_max_coordinate_z",
            "selected_face_min_coordinate_z",
            "selected_face_max_face_area",
            "selected_face_min_face_area",
        ),
        allow_rank=True,
    ),
    SelectorCountFamilySpec(
        family_id="parameterized_kernel_edge_selector_count_rank",
        relation="has_kernel_stable_edge_id",
        selected_type="edge",
        relation_clause_id="has_parameterized_edge_selection",
        selector_relation_clause_id="has_parameterized_selector_relation",
        related_metric_clause_id="has_parameterized_selected_edge_metric_threshold",
        selected_count_clause_id="has_parameterized_selected_count",
        related_metrics=(
            "midpoint_x",
            "midpoint_y",
            "midpoint_z",
            "midpoint_distance_to_origin",
            "edge_length",
        ),
        selector_relations=("same_selected_entity_as",),
        selector_tie_break_metrics=(
            "selected_edge_max_midpoint_x",
            "selected_edge_min_midpoint_x",
            "selected_edge_max_midpoint_y",
            "selected_edge_min_midpoint_y",
            "selected_edge_max_midpoint_z",
            "selected_edge_min_midpoint_z",
            "selected_edge_max_edge_length",
            "selected_edge_min_edge_length",
            "selected_edge_max_midpoint_distance_to_origin",
            "selected_edge_min_midpoint_distance_to_origin",
        ),
        allow_rank=True,
    ),
    SelectorCountFamilySpec(
        family_id="parameterized_kernel_vertex_selector_count_rank",
        relation="has_kernel_stable_vertex_id",
        selected_type="vertex",
        relation_clause_id="has_parameterized_vertex_selection",
        selector_relation_clause_id="has_parameterized_selector_relation",
        related_metric_clause_id="has_parameterized_selected_vertex_metric_threshold",
        selected_count_clause_id="has_parameterized_selected_count",
        related_metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
        ),
        selector_relations=("same_selected_entity_as",),
        selector_tie_break_metrics=(
            "selected_vertex_max_coordinate_x",
            "selected_vertex_min_coordinate_x",
            "selected_vertex_max_coordinate_y",
            "selected_vertex_min_coordinate_y",
            "selected_vertex_max_coordinate_z",
            "selected_vertex_min_coordinate_z",
            "selected_vertex_max_distance_to_origin",
            "selected_vertex_min_distance_to_origin",
        ),
        allow_rank=True,
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
        equal_value_clause_id="has_parameterized_equal_material_region_metric_value",
        selector_metric_clause_id="has_parameterized_material_region_metric",
        equal_metrics=MATERIAL_REGION_METRICS,
        selector_metrics=MATERIAL_REGION_METRICS,
        relation_target_type="material_region",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_void_region_metric_extreme",
        target_type="void_region",
        relation="has_kernel_void_region_geometry",
        relation_clause_id="has_void_geometry",
        equal_value_clause_id="has_void_volume_value",
        selector_metric_clause_id="has_parameterized_void_region_metric",
        equal_metrics=VOID_REGION_METRICS,
        selector_metrics=VOID_REGION_METRICS,
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
        family_id="parameterized_equal_vertex_metric_extreme",
        target_type="vertex",
        relation="has_kernel_stable_vertex_id",
        relation_clause_id="has_parameterized_vertex_set",
        equal_value_clause_id="has_parameterized_equal_vertex_metric_value",
        selector_metric_clause_id="has_parameterized_vertex_metric",
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
        family_id="parameterized_equal_path_point_metric_extreme",
        target_type="path_point",
        relation="point_on_path",
        relation_clause_id="has_parameterized_path_point_set",
        equal_value_clause_id="has_parameterized_equal_path_point_metric_value",
        selector_metric_clause_id="has_parameterized_path_point_metric",
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
        relation_target_type="path",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_path_segment_metric_extreme",
        target_type="path_segment",
        relation="segment_on_path",
        relation_clause_id="has_parameterized_path_segment_set",
        equal_value_clause_id="has_parameterized_equal_path_segment_metric_value",
        selector_metric_clause_id="has_parameterized_path_segment_metric",
        equal_metrics=("segment_length",),
        selector_metrics=("midpoint_distance_to_origin",),
        relation_target_type="path",
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

EQUAL_VALUE_RANK_FAMILY_SPECS = (
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_feature_metric_rank",
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
        selection_mode="rank",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_material_region_metric_rank",
        target_type="material_region",
        relation="has_kernel_material_region_geometry",
        relation_clause_id="has_region_geometry",
        equal_value_clause_id="has_parameterized_equal_material_region_metric_value",
        selector_metric_clause_id="has_parameterized_material_region_metric",
        equal_metrics=MATERIAL_REGION_METRICS,
        selector_metrics=MATERIAL_REGION_METRICS,
        relation_target_type="material_region",
        selection_mode="rank",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_void_region_metric_rank",
        target_type="void_region",
        relation="has_kernel_void_region_geometry",
        relation_clause_id="has_void_geometry",
        equal_value_clause_id="has_parameterized_equal_void_region_metric_value",
        selector_metric_clause_id="has_parameterized_void_region_metric",
        equal_metrics=VOID_REGION_METRICS,
        selector_metrics=VOID_REGION_METRICS,
        relation_target_type="void_region",
        selection_mode="rank",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_face_metric_rank",
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
        selection_mode="rank",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_edge_metric_rank",
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
        selection_mode="rank",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_vertex_metric_rank",
        target_type="vertex",
        relation="has_kernel_stable_vertex_id",
        relation_clause_id="has_parameterized_vertex_set",
        equal_value_clause_id="has_parameterized_equal_vertex_metric_value",
        selector_metric_clause_id="has_parameterized_vertex_metric",
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
        selection_mode="rank",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_path_point_metric_rank",
        target_type="path_point",
        relation="point_on_path",
        relation_clause_id="has_parameterized_path_point_set",
        equal_value_clause_id="has_parameterized_equal_path_point_metric_value",
        selector_metric_clause_id="has_parameterized_path_point_metric",
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
        relation_target_type="path",
        selection_mode="rank",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_path_segment_metric_rank",
        target_type="path_segment",
        relation="segment_on_path",
        relation_clause_id="has_parameterized_path_segment_set",
        equal_value_clause_id="has_parameterized_equal_path_segment_metric_value",
        selector_metric_clause_id="has_parameterized_path_segment_metric",
        equal_metrics=("segment_length", "midpoint_distance_to_origin"),
        selector_metrics=("segment_length", "midpoint_distance_to_origin"),
        relation_target_type="path",
        selection_mode="rank",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_equal_endpoint_metric_rank",
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
        selection_mode="rank",
    ),
    EqualValueExtremeFamilySpec(
        family_id="parameterized_contained_endpoint_metric_rank",
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
        selection_mode="rank",
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
            "coplanar_with",
            "intersects",
            "opposite_to",
            "parallel_to",
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
            "coaxial_with",
            "intersects",
            "longer_than",
            "opposite_to",
            "parallel_to",
            "perpendicular_to",
            "same_length_as",
            "shorter_than",
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
    RelationExtremeFamilySpec(
        family_id="parameterized_endpoint_containment_relation_extreme",
        target_type="edge_endpoint",
        base_relation="endpoint_of",
        base_relation_clause_id="has_parameterized_endpoint_set",
        base_relation_target_type="edge",
        relations=("contained_in",),
        relation_clause_id="has_parameterized_contained_endpoint_set",
        measurement_clause_id="has_parameterized_endpoint_metric",
        metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
        ),
        relation_target_type="edge",
    ),
)

RELATION_RANK_FAMILY_SPECS = (
    RelationExtremeFamilySpec(
        family_id="parameterized_face_spatial_relation_rank",
        target_type="face",
        base_relation="has_kernel_stable_face_id",
        base_relation_clause_id="has_parameterized_face_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "coplanar_with",
            "intersects",
            "opposite_to",
            "parallel_to",
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
        selection_mode="rank",
    ),
    RelationExtremeFamilySpec(
        family_id="parameterized_edge_spatial_relation_rank",
        target_type="edge",
        base_relation="has_kernel_stable_edge_id",
        base_relation_clause_id="has_parameterized_edge_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "coaxial_with",
            "intersects",
            "longer_than",
            "opposite_to",
            "parallel_to",
            "perpendicular_to",
            "same_length_as",
            "shorter_than",
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
        selection_mode="rank",
    ),
    RelationExtremeFamilySpec(
        family_id="parameterized_endpoint_containment_relation_rank",
        target_type="edge_endpoint",
        base_relation="endpoint_of",
        base_relation_clause_id="has_parameterized_endpoint_set",
        base_relation_target_type="edge",
        relations=("contained_in",),
        relation_clause_id="has_parameterized_contained_endpoint_set",
        measurement_clause_id="has_parameterized_endpoint_metric",
        metrics=(
            "coordinate_x",
            "coordinate_y",
            "coordinate_z",
            "distance_to_origin",
        ),
        relation_target_type="edge",
        selection_mode="rank",
    ),
)

RELATION_TIE_BREAK_FAMILY_SPECS = (
    RelationExtremeFamilySpec(
        family_id="parameterized_face_spatial_relation_tie_break_extreme",
        target_type="face",
        base_relation="has_kernel_stable_face_id",
        base_relation_clause_id="has_parameterized_face_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "coplanar_with",
            "intersects",
            "opposite_to",
            "parallel_to",
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
        selection_mode="tie_break",
    ),
    RelationExtremeFamilySpec(
        family_id="parameterized_edge_spatial_relation_tie_break_extreme",
        target_type="edge",
        base_relation="has_kernel_stable_edge_id",
        base_relation_clause_id="has_parameterized_edge_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "coaxial_with",
            "intersects",
            "longer_than",
            "opposite_to",
            "parallel_to",
            "perpendicular_to",
            "same_length_as",
            "shorter_than",
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
        selection_mode="tie_break",
    ),
)

RELATION_CHAIN_EXTREME_FAMILY_SPECS = (
    RelationChainFamilySpec(
        family_id="parameterized_face_spatial_relation_chain_extreme",
        target_type="face",
        base_relation="has_kernel_stable_face_id",
        base_relation_clause_id="has_parameterized_face_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "coplanar_with",
            "intersects",
            "opposite_to",
            "parallel_to",
            "perpendicular_to",
        ),
        chain_lengths=(2,),
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
    RelationChainFamilySpec(
        family_id="parameterized_edge_spatial_relation_chain_extreme",
        target_type="edge",
        base_relation="has_kernel_stable_edge_id",
        base_relation_clause_id="has_parameterized_edge_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "coaxial_with",
            "intersects",
            "longer_than",
            "opposite_to",
            "parallel_to",
            "perpendicular_to",
            "same_length_as",
            "shorter_than",
        ),
        chain_lengths=(2,),
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

RELATION_CHAIN_RANK_FAMILY_SPECS = (
    RelationChainFamilySpec(
        family_id="parameterized_face_spatial_relation_chain_rank",
        target_type="face",
        base_relation="has_kernel_stable_face_id",
        base_relation_clause_id="has_parameterized_face_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "coplanar_with",
            "intersects",
            "opposite_to",
            "parallel_to",
            "perpendicular_to",
        ),
        chain_lengths=(2,),
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
        selection_mode="rank",
    ),
    RelationChainFamilySpec(
        family_id="parameterized_edge_spatial_relation_chain_rank",
        target_type="edge",
        base_relation="has_kernel_stable_edge_id",
        base_relation_clause_id="has_parameterized_edge_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "coaxial_with",
            "intersects",
            "longer_than",
            "opposite_to",
            "parallel_to",
            "perpendicular_to",
            "same_length_as",
            "shorter_than",
        ),
        chain_lengths=(2,),
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
        selection_mode="rank",
    ),
)

RELATION_CHAIN_TIE_BREAK_FAMILY_SPECS = (
    RelationChainFamilySpec(
        family_id="parameterized_face_spatial_relation_chain_tie_break_extreme",
        target_type="face",
        base_relation="has_kernel_stable_face_id",
        base_relation_clause_id="has_parameterized_face_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "coplanar_with",
            "intersects",
            "opposite_to",
            "parallel_to",
            "perpendicular_to",
        ),
        chain_lengths=(2,),
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
        selection_mode="tie_break",
    ),
    RelationChainFamilySpec(
        family_id="parameterized_edge_spatial_relation_chain_tie_break_extreme",
        target_type="edge",
        base_relation="has_kernel_stable_edge_id",
        base_relation_clause_id="has_parameterized_edge_set",
        base_relation_target_type="selector",
        relations=(
            "adjacent_to",
            "coaxial_with",
            "intersects",
            "longer_than",
            "opposite_to",
            "parallel_to",
            "perpendicular_to",
            "same_length_as",
            "shorter_than",
        ),
        chain_lengths=(2,),
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
        selection_mode="tie_break",
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
        family_id="parameterized_face_reference_face_distance",
        target_type="face",
        relation="has_kernel_stable_face_id",
        relation_clause_id="has_parameterized_face_set",
        relation_target_type="selector",
        equal_value_clause_id="has_parameterized_equal_face_metric_value",
        reference_clause_id="reference_face_area_and_center",
        target_point_clause_id="has_face_center_for_reference_distance",
        equal_metric="face_area",
        target_point_metric="face_center",
        reference_type="face",
        reference_point_metric="face_center",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_face_reference_edge_distance",
        target_type="face",
        relation="has_kernel_stable_face_id",
        relation_clause_id="has_parameterized_face_set",
        relation_target_type="selector",
        equal_value_clause_id="has_parameterized_equal_face_metric_value",
        reference_clause_id="reference_edge_length_and_midpoint",
        target_point_clause_id="has_face_center_for_reference_distance",
        equal_metric="face_area",
        target_point_metric="face_center",
        reference_type="edge",
        reference_point_metric="midpoint",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_face_reference_endpoint_distance",
        target_type="face",
        relation="has_kernel_stable_face_id",
        relation_clause_id="has_parameterized_face_set",
        relation_target_type="selector",
        equal_value_clause_id="has_parameterized_equal_face_metric_value",
        reference_clause_id="reference_endpoint_coordinates",
        target_point_clause_id="has_face_center_for_reference_distance",
        equal_metric="face_area",
        target_point_metric="face_center",
        reference_type="edge_endpoint",
        reference_point_metric="coordinate",
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
        family_id="parameterized_edge_reference_face_distance",
        target_type="edge",
        relation="has_kernel_stable_edge_id",
        relation_clause_id="has_parameterized_edge_set",
        relation_target_type="selector",
        equal_value_clause_id="has_parameterized_equal_edge_metric_value",
        reference_clause_id="reference_face_area_and_center",
        target_point_clause_id="has_edge_midpoint_for_reference_distance",
        equal_metric="edge_length",
        target_point_metric="midpoint",
        reference_type="face",
        reference_point_metric="face_center",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_edge_reference_edge_distance",
        target_type="edge",
        relation="has_kernel_stable_edge_id",
        relation_clause_id="has_parameterized_edge_set",
        relation_target_type="selector",
        equal_value_clause_id="has_parameterized_equal_edge_metric_value",
        reference_clause_id="reference_edge_length_and_midpoint",
        target_point_clause_id="has_edge_midpoint_for_reference_distance",
        equal_metric="edge_length",
        target_point_metric="midpoint",
        reference_type="edge",
        reference_point_metric="midpoint",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_edge_reference_endpoint_distance",
        target_type="edge",
        relation="has_kernel_stable_edge_id",
        relation_clause_id="has_parameterized_edge_set",
        relation_target_type="selector",
        equal_value_clause_id="has_parameterized_equal_edge_metric_value",
        reference_clause_id="reference_endpoint_coordinates",
        target_point_clause_id="has_edge_midpoint_for_reference_distance",
        equal_metric="edge_length",
        target_point_metric="midpoint",
        reference_type="edge_endpoint",
        reference_point_metric="coordinate",
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
        family_id="parameterized_feature_reference_face_distance",
        target_type="feature",
        relation=None,
        relation_clause_id=None,
        relation_target_type=None,
        equal_value_clause_id="has_parameterized_equal_feature_metric_value",
        reference_clause_id="reference_face_area_and_center",
        target_point_clause_id="has_feature_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="face",
        reference_point_metric="face_center",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_feature_reference_edge_distance",
        target_type="feature",
        relation=None,
        relation_clause_id=None,
        relation_target_type=None,
        equal_value_clause_id="has_parameterized_equal_feature_metric_value",
        reference_clause_id="reference_edge_length_and_midpoint",
        target_point_clause_id="has_feature_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="edge",
        reference_point_metric="midpoint",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_feature_reference_endpoint_distance",
        target_type="feature",
        relation=None,
        relation_clause_id=None,
        relation_target_type=None,
        equal_value_clause_id="has_parameterized_equal_feature_metric_value",
        reference_clause_id="reference_endpoint_coordinates",
        target_point_clause_id="has_feature_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="edge_endpoint",
        reference_point_metric="coordinate",
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
        family_id="parameterized_endpoint_reference_face_distance",
        target_type="edge_endpoint",
        relation="endpoint_of",
        relation_clause_id="has_parameterized_endpoint_set",
        relation_target_type="edge",
        equal_value_clause_id="has_parameterized_equal_endpoint_metric_value",
        reference_clause_id="reference_face_area_and_center",
        target_point_clause_id="has_endpoint_for_reference_distance",
        equal_metric="coordinate_z",
        target_point_metric="coordinate",
        reference_type="face",
        reference_point_metric="face_center",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_endpoint_reference_edge_distance",
        target_type="edge_endpoint",
        relation="endpoint_of",
        relation_clause_id="has_parameterized_endpoint_set",
        relation_target_type="edge",
        equal_value_clause_id="has_parameterized_equal_endpoint_metric_value",
        reference_clause_id="reference_edge_length_and_midpoint",
        target_point_clause_id="has_endpoint_for_reference_distance",
        equal_metric="coordinate_z",
        target_point_metric="coordinate",
        reference_type="edge",
        reference_point_metric="midpoint",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_endpoint_reference_endpoint_distance",
        target_type="edge_endpoint",
        relation="endpoint_of",
        relation_clause_id="has_parameterized_endpoint_set",
        relation_target_type="edge",
        equal_value_clause_id="has_parameterized_equal_endpoint_metric_value",
        reference_clause_id="reference_endpoint_coordinates",
        target_point_clause_id="has_endpoint_for_reference_distance",
        equal_metric="coordinate_z",
        target_point_metric="coordinate",
        reference_type="edge_endpoint",
        reference_point_metric="coordinate",
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
        family_id="parameterized_material_region_reference_face_distance",
        target_type="material_region",
        relation="has_kernel_material_region_geometry",
        relation_clause_id="has_region_geometry",
        relation_target_type="material_region",
        equal_value_clause_id="has_region_volume_value",
        reference_clause_id="reference_face_area_and_center",
        target_point_clause_id="has_region_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="face",
        reference_point_metric="face_center",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_material_region_reference_edge_distance",
        target_type="material_region",
        relation="has_kernel_material_region_geometry",
        relation_clause_id="has_region_geometry",
        relation_target_type="material_region",
        equal_value_clause_id="has_region_volume_value",
        reference_clause_id="reference_edge_length_and_midpoint",
        target_point_clause_id="has_region_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="edge",
        reference_point_metric="midpoint",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_material_region_reference_endpoint_distance",
        target_type="material_region",
        relation="has_kernel_material_region_geometry",
        relation_clause_id="has_region_geometry",
        relation_target_type="material_region",
        equal_value_clause_id="has_region_volume_value",
        reference_clause_id="reference_endpoint_coordinates",
        target_point_clause_id="has_region_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="edge_endpoint",
        reference_point_metric="coordinate",
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
    ReferenceDistanceFamilySpec(
        family_id="parameterized_void_region_reference_face_distance",
        target_type="void_region",
        relation="has_kernel_void_region_geometry",
        relation_clause_id="has_void_geometry",
        relation_target_type="void_region",
        equal_value_clause_id="has_void_volume_value",
        reference_clause_id="reference_face_area_and_center",
        target_point_clause_id="has_void_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="face",
        reference_point_metric="face_center",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_void_region_reference_edge_distance",
        target_type="void_region",
        relation="has_kernel_void_region_geometry",
        relation_clause_id="has_void_geometry",
        relation_target_type="void_region",
        equal_value_clause_id="has_void_volume_value",
        reference_clause_id="reference_edge_length_and_midpoint",
        target_point_clause_id="has_void_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="edge",
        reference_point_metric="midpoint",
    ),
    ReferenceDistanceFamilySpec(
        family_id="parameterized_void_region_reference_endpoint_distance",
        target_type="void_region",
        relation="has_kernel_void_region_geometry",
        relation_clause_id="has_void_geometry",
        relation_target_type="void_region",
        equal_value_clause_id="has_void_volume_value",
        reference_clause_id="reference_endpoint_coordinates",
        target_point_clause_id="has_void_centroid_for_reference_distance",
        equal_metric="volume",
        target_point_metric="centroid",
        reference_type="edge_endpoint",
        reference_point_metric="coordinate",
    ),
)

_GENERIC_REFERENCE_DISTANCE_TARGETS = (
    {
        "family_id": "parameterized_face_reference_entity_distance",
        "target_type": "face",
        "relation": "has_kernel_stable_face_id",
        "relation_clause_id": "has_parameterized_face_set",
        "relation_target_type": "selector",
        "equal_value_clause_id": "has_parameterized_equal_face_metric_value",
        "target_point_clause_id": "has_face_center_for_reference_distance",
        "equal_metric": "face_area",
        "target_point_metric": "face_center",
    },
    {
        "family_id": "parameterized_edge_reference_entity_distance",
        "target_type": "edge",
        "relation": "has_kernel_stable_edge_id",
        "relation_clause_id": "has_parameterized_edge_set",
        "relation_target_type": "selector",
        "equal_value_clause_id": "has_parameterized_equal_edge_metric_value",
        "target_point_clause_id": "has_edge_midpoint_for_reference_distance",
        "equal_metric": "edge_length",
        "target_point_metric": "midpoint",
    },
    {
        "family_id": "parameterized_vertex_reference_entity_distance",
        "target_type": "vertex",
        "relation": "has_kernel_stable_vertex_id",
        "relation_clause_id": "has_parameterized_vertex_set",
        "relation_target_type": "selector",
        "equal_value_clause_id": "has_parameterized_equal_vertex_metric_value",
        "target_point_clause_id": "has_vertex_for_reference_distance",
        "equal_metric": "coordinate_z",
        "target_point_metric": "coordinate",
    },
    {
        "family_id": "parameterized_feature_reference_entity_distance",
        "target_type": "feature",
        "relation": None,
        "relation_clause_id": None,
        "relation_target_type": None,
        "equal_value_clause_id": "has_parameterized_equal_feature_metric_value",
        "target_point_clause_id": "has_feature_centroid_for_reference_distance",
        "equal_metric": "volume",
        "target_point_metric": "centroid",
    },
    {
        "family_id": "parameterized_feature_reference_entity_distance",
        "target_type": "feature",
        "relation": None,
        "relation_clause_id": None,
        "relation_target_type": None,
        "equal_value_clause_id": "has_parameterized_equal_feature_metric_value",
        "target_point_clause_id": "has_feature_bbox_center_for_reference_distance",
        "equal_metric": "bbox_span_z",
        "target_point_metric": "bbox_center",
    },
    {
        "family_id": "parameterized_endpoint_reference_entity_distance",
        "target_type": "edge_endpoint",
        "relation": "endpoint_of",
        "relation_clause_id": "has_parameterized_endpoint_set",
        "relation_target_type": "edge",
        "equal_value_clause_id": "has_parameterized_equal_endpoint_metric_value",
        "target_point_clause_id": "has_endpoint_for_reference_distance",
        "equal_metric": "coordinate_z",
        "target_point_metric": "coordinate",
    },
    {
        "family_id": "parameterized_path_point_reference_entity_distance",
        "target_type": "path_point",
        "relation": "point_on_path",
        "relation_clause_id": "has_parameterized_path_point_set",
        "relation_target_type": "path",
        "equal_value_clause_id": "has_parameterized_equal_path_point_metric_value",
        "target_point_clause_id": "has_path_point_for_reference_distance",
        "equal_metric": "coordinate_z",
        "target_point_metric": "coordinate",
    },
    {
        "family_id": "parameterized_path_point_reference_entity_distance",
        "target_type": "path_point",
        "relation": "point_on_path",
        "relation_clause_id": "has_parameterized_path_point_set",
        "relation_target_type": "path",
        "equal_value_clause_id": "has_parameterized_equal_path_point_metric_value",
        "target_point_clause_id": "has_path_point_for_reference_distance",
        "equal_metric": "coordinate_x",
        "target_point_metric": "coordinate",
    },
    {
        "family_id": "parameterized_path_point_reference_entity_distance",
        "target_type": "path_point",
        "relation": "point_on_path",
        "relation_clause_id": "has_parameterized_path_point_set",
        "relation_target_type": "path",
        "equal_value_clause_id": "has_parameterized_equal_path_point_metric_value",
        "target_point_clause_id": "has_path_point_for_reference_distance",
        "equal_metric": "coordinate_y",
        "target_point_metric": "coordinate",
    },
    {
        "family_id": "parameterized_path_segment_reference_entity_distance",
        "target_type": "path_segment",
        "relation": "segment_on_path",
        "relation_clause_id": "has_parameterized_path_segment_set",
        "relation_target_type": "path",
        "equal_value_clause_id": "has_parameterized_equal_path_segment_metric_value",
        "target_point_clause_id": "has_path_segment_midpoint_for_reference_distance",
        "equal_metric": "segment_length",
        "target_point_metric": "segment_midpoint",
    },
    {
        "family_id": "parameterized_material_region_reference_entity_distance",
        "target_type": "material_region",
        "relation": "has_kernel_material_region_geometry",
        "relation_clause_id": "has_region_geometry",
        "relation_target_type": "material_region",
        "equal_value_clause_id": "has_region_volume_value",
        "target_point_clause_id": "has_region_centroid_for_reference_distance",
        "equal_metric": "volume",
        "target_point_metric": "centroid",
    },
    {
        "family_id": "parameterized_material_region_reference_entity_distance",
        "target_type": "material_region",
        "relation": "has_kernel_material_region_geometry",
        "relation_clause_id": "has_region_geometry",
        "relation_target_type": "material_region",
        "equal_value_clause_id": "has_region_volume_value",
        "target_point_clause_id": "has_region_bbox_center_for_reference_distance",
        "equal_metric": "bbox_span_z",
        "target_point_metric": "bbox_center",
    },
    {
        "family_id": "parameterized_void_region_reference_entity_distance",
        "target_type": "void_region",
        "relation": "has_kernel_void_region_geometry",
        "relation_clause_id": "has_void_geometry",
        "relation_target_type": "void_region",
        "equal_value_clause_id": "has_void_volume_value",
        "target_point_clause_id": "has_void_centroid_for_reference_distance",
        "equal_metric": "volume",
        "target_point_metric": "centroid",
    },
    {
        "family_id": "parameterized_void_region_reference_entity_distance",
        "target_type": "void_region",
        "relation": "has_kernel_void_region_geometry",
        "relation_clause_id": "has_void_geometry",
        "relation_target_type": "void_region",
        "equal_value_clause_id": "has_void_volume_value",
        "target_point_clause_id": "has_void_bbox_center_for_reference_distance",
        "equal_metric": "bbox_span_z",
        "target_point_metric": "bbox_center",
    },
)

_GENERIC_REFERENCE_DISTANCE_REFERENCES = (
    ("feature", "reference_feature_volume_and_centroid", "centroid"),
    ("feature", "reference_feature_volume_and_bbox_center", "bbox_center"),
    ("face", "reference_face_area_and_center", "face_center"),
    ("edge", "reference_edge_length_and_midpoint", "midpoint"),
    ("edge_endpoint", "reference_endpoint_coordinates", "coordinate"),
    ("material_region", "reference_material_region_volume_and_centroid", "centroid"),
    ("material_region", "reference_material_region_volume_and_bbox_center", "bbox_center"),
    ("void_region", "reference_void_region_volume_and_centroid", "centroid"),
    ("void_region", "reference_void_region_volume_and_bbox_center", "bbox_center"),
)


_PATH_REFERENCE_DISTANCE_TARGETS = (
    {
        "family_prefix": "parameterized_path_point_reference",
        "target_type": "path_point",
        "relation": "point_on_path",
        "relation_clause_id": "has_parameterized_path_point_set",
        "relation_target_type": "path",
        "equal_value_clause_id": "has_parameterized_equal_path_point_metric_value",
        "target_point_clause_id": "has_path_point_for_reference_distance",
        "equal_metric": "coordinate_z",
        "target_point_metric": "coordinate",
    },
    {
        "family_prefix": "parameterized_path_segment_reference",
        "target_type": "path_segment",
        "relation": "segment_on_path",
        "relation_clause_id": "has_parameterized_path_segment_set",
        "relation_target_type": "path",
        "equal_value_clause_id": "has_parameterized_equal_path_segment_metric_value",
        "target_point_clause_id": "has_path_segment_midpoint_for_reference_distance",
        "equal_metric": "segment_length",
        "target_point_metric": "segment_midpoint",
    },
)

_PATH_REFERENCE_DISTANCE_REFERENCES = (
    ("face", "reference_face_area_and_center", "face_center"),
    ("edge", "reference_edge_length_and_midpoint", "midpoint"),
    ("edge_endpoint", "reference_endpoint_coordinates", "coordinate"),
    ("material_region", "reference_material_region_volume_and_centroid", "centroid"),
    ("void_region", "reference_void_region_volume_and_centroid", "centroid"),
)


_REGION_REFERENCE_DISTANCE_TARGET_TYPES = {
    "feature",
    "face",
    "edge",
    "edge_endpoint",
    "material_region",
    "void_region",
}

_REGION_REFERENCE_DISTANCE_REFERENCES = (
    ("material_region", "reference_material_region_volume_and_centroid", "centroid"),
    ("void_region", "reference_void_region_volume_and_centroid", "centroid"),
)


def _path_reference_distance_family_specs() -> tuple[ReferenceDistanceFamilySpec, ...]:
    specs: list[ReferenceDistanceFamilySpec] = []
    for target in _PATH_REFERENCE_DISTANCE_TARGETS:
        for reference_type, reference_clause_id, reference_point_metric in _PATH_REFERENCE_DISTANCE_REFERENCES:
            specs.append(
                ReferenceDistanceFamilySpec(
                    family_id=f"{target['family_prefix']}_{_reference_family_suffix(reference_type)}_distance",
                    target_type=str(target["target_type"]),
                    relation=str(target["relation"]),
                    relation_clause_id=str(target["relation_clause_id"]),
                    relation_target_type=str(target["relation_target_type"]),
                    equal_value_clause_id=str(target["equal_value_clause_id"]),
                    reference_clause_id=reference_clause_id,
                    target_point_clause_id=str(target["target_point_clause_id"]),
                    equal_metric=str(target["equal_metric"]),
                    target_point_metric=str(target["target_point_metric"]),
                    reference_type=reference_type,
                    reference_point_metric=reference_point_metric,
                )
            )
    return tuple(specs)


def _reference_family_suffix(reference_type: str) -> str:
    return "endpoint" if reference_type == "edge_endpoint" else reference_type


def _region_reference_distance_family_specs() -> tuple[ReferenceDistanceFamilySpec, ...]:
    specs: list[ReferenceDistanceFamilySpec] = []
    for target in _GENERIC_REFERENCE_DISTANCE_TARGETS:
        if str(target["target_type"]) not in _REGION_REFERENCE_DISTANCE_TARGET_TYPES:
            continue
        family_prefix = str(target["family_id"]).removesuffix("_entity_distance")
        for reference_type, reference_clause_id, reference_point_metric in _REGION_REFERENCE_DISTANCE_REFERENCES:
            specs.append(
                ReferenceDistanceFamilySpec(
                    family_id=f"{family_prefix}_{reference_type}_distance",
                    target_type=str(target["target_type"]),
                    relation=target["relation"],
                    relation_clause_id=target["relation_clause_id"],
                    relation_target_type=target["relation_target_type"],
                    equal_value_clause_id=str(target["equal_value_clause_id"]),
                    reference_clause_id=reference_clause_id,
                    target_point_clause_id=str(target["target_point_clause_id"]),
                    equal_metric=str(target["equal_metric"]),
                    target_point_metric=str(target["target_point_metric"]),
                    reference_type=reference_type,
                    reference_point_metric=reference_point_metric,
                )
            )
    return tuple(specs)


def _generic_reference_distance_family_specs() -> tuple[ReferenceDistanceFamilySpec, ...]:
    specs: list[ReferenceDistanceFamilySpec] = []
    for target in _GENERIC_REFERENCE_DISTANCE_TARGETS:
        for reference_type, reference_clause_id, reference_point_metric in _GENERIC_REFERENCE_DISTANCE_REFERENCES:
            for family_id, selection_mode in (
                (str(target["family_id"]), "extreme"),
                (f"{str(target['family_id']).removesuffix('_distance')}_distance_rank", "rank"),
            ):
                specs.append(
                    ReferenceDistanceFamilySpec(
                        family_id=family_id,
                        target_type=str(target["target_type"]),
                        relation=target["relation"],
                        relation_clause_id=target["relation_clause_id"],
                        relation_target_type=target["relation_target_type"],
                        equal_value_clause_id=str(target["equal_value_clause_id"]),
                        reference_clause_id=reference_clause_id,
                        target_point_clause_id=str(target["target_point_clause_id"]),
                        equal_metric=str(target["equal_metric"]),
                        target_point_metric=str(target["target_point_metric"]),
                        reference_type=reference_type,
                        reference_point_metric=reference_point_metric,
                        selection_mode=selection_mode,
                    )
                )
    return tuple(specs)


REFERENCE_DISTANCE_FAMILY_SPECS = (
    REFERENCE_DISTANCE_FAMILY_SPECS
    + _path_reference_distance_family_specs()
    + _region_reference_distance_family_specs()
    + _generic_reference_distance_family_specs()
)


def synthesize_graph_hop_queries(
    graph: OntologyGraph,
    *,
    max_per_family: int = 1,
) -> list[QueryProgram]:
    """Create deterministic parameterized graph-hop queries from graph evidence."""

    queries: list[QueryProgram] = []
    for spec in EXTREME_FAMILY_SPECS:
        viable = _viable_extremes(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_extreme, max_per_family))
    for spec in RANK_FAMILY_SPECS:
        viable = _viable_ranks(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_extreme, max_per_family))
    for spec in FEATURE_EFFECT_DELTA_FAMILY_SPECS:
        viable = _viable_feature_effect_delta_extremes(graph, spec)
        queries.extend(
            _queries_from_viable(
                graph,
                spec.family_id,
                viable,
                _query_for_feature_effect_delta_extreme,
                max_per_family,
            )
        )
    for spec in SELECTOR_COUNT_FAMILY_SPECS:
        viable = _viable_selector_counts(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_selector_count, max_per_family))
    for spec in SELECTOR_COUNT_RANK_FAMILY_SPECS:
        viable = _viable_selector_counts(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_selector_count, max_per_family))
    for spec in EQUAL_VALUE_EXTREME_FAMILY_SPECS:
        viable = _viable_equal_value_extremes(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_equal_value_extreme, max_per_family))
    for spec in EQUAL_VALUE_RANK_FAMILY_SPECS:
        viable = _viable_equal_value_extremes(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_equal_value_extreme, max_per_family))
    for spec in RELATION_EXTREME_FAMILY_SPECS:
        viable = _viable_relation_extremes(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_relation_extreme, max_per_family))
    for spec in RELATION_RANK_FAMILY_SPECS:
        viable = _viable_relation_extremes(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_relation_extreme, max_per_family))
    for spec in RELATION_TIE_BREAK_FAMILY_SPECS:
        viable = _viable_relation_extremes(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_relation_extreme, max_per_family))
    for spec in RELATION_CHAIN_EXTREME_FAMILY_SPECS:
        viable = _viable_relation_chain_extremes(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_relation_chain_extreme, max_per_family))
    for spec in RELATION_CHAIN_RANK_FAMILY_SPECS:
        viable = _viable_relation_chain_extremes(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_relation_chain_extreme, max_per_family))
    for spec in RELATION_CHAIN_TIE_BREAK_FAMILY_SPECS:
        viable = _viable_relation_chain_extremes(graph, spec)
        queries.extend(_queries_from_viable(graph, spec.family_id, viable, _query_for_relation_chain_extreme, max_per_family))
    for family_id, specs in _reference_distance_specs_by_family():
        viable = [
            candidate
            for spec in specs
            for candidate in _viable_reference_distances(graph, spec)
        ]
        queries.extend(_queries_from_viable(graph, family_id, viable, _query_for_reference_distance, max_per_family))
    return queries


def _queries_from_viable(
    graph: OntologyGraph,
    family_id: str,
    viable: list[T],
    builder: Callable[[OntologyGraph, T], QueryProgram | None],
    max_per_family: int,
) -> list[QueryProgram]:
    choices = _sample_viable_choices(graph.graph_id, family_id, viable, max_per_family)
    queries: list[QueryProgram] = []
    multi_variant = len(choices) > 1
    for index, choice in enumerate(choices):
        query = builder(graph, choice)
        if query is not None:
            queries.append(_with_query_variant(query, index) if multi_variant else query)
    return queries


def _sample_viable_choices(
    graph_id: str,
    family_id: str,
    viable: list[T],
    max_per_family: int,
) -> list[T]:
    if not viable:
        return []
    limit = max(1, max_per_family)
    start = _stable_choice_index(graph_id, family_id, len(viable))
    ordered = [viable[(start + offset) % len(viable)] for offset in range(len(viable))]
    if any(hasattr(item, "compare_metric") for item in ordered):
        direct_unrotated = [item for item in viable if getattr(item, "compare_metric", None) is None]
        direct_start = _stable_choice_index(graph_id, family_id, len(direct_unrotated)) if direct_unrotated else 0
        direct = [
            direct_unrotated[(direct_start + offset) % len(direct_unrotated)]
            for offset in range(len(direct_unrotated))
        ]
        compared = [item for item in ordered if getattr(item, "compare_metric", None) is not None]
        if limit == 1 and direct:
            return direct[:1]
        seeded: list[T] = []
        if direct:
            seeded.append(direct[0])
        if compared and len(seeded) < limit:
            seeded.append(compared[0])
        seen = {id(item) for item in seeded}
        for item in ordered:
            if len(seeded) >= limit:
                break
            if id(item) not in seen:
                seeded.append(item)
                seen.add(id(item))
        return seeded
    return ordered[:limit]


def _with_query_variant(query: QueryProgram, index: int) -> QueryProgram:
    prefix, family_id = query.query_id.rsplit(":", 1)
    return replace(query, query_id=f"{prefix}:v{index}:{family_id}")


def _reference_distance_specs_by_family() -> tuple[tuple[str, tuple[ReferenceDistanceFamilySpec, ...]], ...]:
    grouped: dict[str, list[ReferenceDistanceFamilySpec]] = {}
    for spec in REFERENCE_DISTANCE_FAMILY_SPECS:
        grouped.setdefault(spec.family_id, []).append(spec)
    return tuple((family_id, tuple(specs)) for family_id, specs in grouped.items())


def _viable_extremes(graph: OntologyGraph, spec: ExtremeFamilySpec) -> list[ViableExtreme]:
    candidates = graph.nodes_by_type(spec.target_type)
    relation_candidates = _relation_filtered_candidates(graph, candidates, spec)
    if relation_candidates is None:
        return []
    viable = _viable_extremes_for_candidates(graph, spec, relation_candidates)
    for compare_metric in spec.metrics:
        for operator, value in _metric_thresholds(graph, relation_candidates, compare_metric):
            compare = _metric_compare_predicate_cached(
                graph,
                relation_candidates,
                clause_id=_direct_metric_compare_clause_id(spec),
                metric=compare_metric,
                operator=operator,
                value=value,
            )
            if compare is None:
                continue
            narrowed = _nodes_matching_metric_compare_cached(
                graph,
                relation_candidates,
                metric=compare_metric,
                operator=operator,
                value=value,
            )
            if len(narrowed) >= len(relation_candidates):
                continue
            viable.extend(
                _viable_extremes_for_candidates(
                    graph,
                    spec,
                    narrowed,
                    compare_metric=compare_metric,
                    compare_operator=operator,
                    compare_value=value,
                )
            )
    return _sort_viable_extremes(viable)


def _viable_extremes_for_candidates(
    graph: OntologyGraph,
    spec: ExtremeFamilySpec,
    candidates: list[Node],
    *,
    compare_metric: str | None = None,
    compare_operator: str | None = None,
    compare_value: float | None = None,
) -> list[ViableExtreme]:
    viable: list[ViableExtreme] = []
    for metric in spec.metrics:
        if metric == compare_metric:
            continue
        measurement = _measurement_predicate_cached(
            graph,
            candidates,
            clause_id=spec.measurement_clause_id,
            metric=metric,
        )
        if measurement is None:
            continue
        metric_candidates = _nodes_with_numeric_measurement(graph, candidates, metric)
        if len(metric_candidates) < 2:
            continue
        for aggregation in ("argmax", "argmin"):
            if _has_unique_extreme(graph, metric_candidates, metric, aggregation):
                viable.append(
                    ViableExtreme(
                        spec,
                        metric_candidates,
                        metric,
                        aggregation,
                        compare_metric=compare_metric,
                        compare_operator=compare_operator,
                        compare_value=compare_value,
                    )
                )
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
                        compare_metric=compare_metric,
                        compare_operator=compare_operator,
                        compare_value=compare_value,
                    )
                )
    return viable


def _viable_ranks(graph: OntologyGraph, spec: ExtremeFamilySpec) -> list[ViableExtreme]:
    candidates = graph.nodes_by_type(spec.target_type)
    if not spec.allow_rank:
        return []
    relation_candidates = _relation_filtered_candidates(graph, candidates, spec)
    if relation_candidates is None:
        return []
    viable = _viable_ranks_for_candidates(graph, spec, relation_candidates)
    for compare_metric in spec.metrics:
        for operator, value in _metric_thresholds(graph, relation_candidates, compare_metric):
            compare = _metric_compare_predicate_cached(
                graph,
                relation_candidates,
                clause_id=_direct_metric_compare_clause_id(spec),
                metric=compare_metric,
                operator=operator,
                value=value,
            )
            if compare is None:
                continue
            narrowed = _nodes_matching_metric_compare_cached(
                graph,
                relation_candidates,
                metric=compare_metric,
                operator=operator,
                value=value,
            )
            if len(narrowed) >= len(relation_candidates):
                continue
            viable.extend(
                _viable_ranks_for_candidates(
                    graph,
                    spec,
                    narrowed,
                    compare_metric=compare_metric,
                    compare_operator=operator,
                    compare_value=value,
                )
            )
    return _sort_viable_extremes(viable)


def _viable_ranks_for_candidates(
    graph: OntologyGraph,
    spec: ExtremeFamilySpec,
    candidates: list[Node],
    *,
    compare_metric: str | None = None,
    compare_operator: str | None = None,
    compare_value: float | None = None,
) -> list[ViableExtreme]:
    viable: list[ViableExtreme] = []
    for metric in spec.metrics:
        if metric == compare_metric:
            continue
        measurement = _measurement_predicate_cached(
            graph,
            candidates,
            clause_id=spec.measurement_clause_id,
            metric=metric,
        )
        if measurement is None:
            continue
        metric_candidates = _nodes_with_numeric_measurement(graph, candidates, metric)
        if len(metric_candidates) < 3:
            continue
        for aggregation in ("rank_desc", "rank_asc"):
            for rank in range(2, min(len(metric_candidates), MAX_SYNTHESIZED_RANK) + 1):
                if _has_unique_rank(graph, metric_candidates, metric, aggregation, rank):
                    viable.append(
                        ViableExtreme(
                            spec,
                            metric_candidates,
                            metric,
                            aggregation,
                            aggregation_rank=rank,
                            compare_metric=compare_metric,
                            compare_operator=compare_operator,
                            compare_value=compare_value,
                        )
                    )
    return viable


def _sort_viable_extremes(viable: list[ViableExtreme]) -> list[ViableExtreme]:
    return sorted(
        viable,
        key=lambda item: (
            item.metric,
            item.aggregation,
            item.aggregation_rank or 0,
            item.compare_metric or "",
            item.compare_operator or "",
            item.compare_value if item.compare_value is not None else 0.0,
            item.tie_break_metric or "",
            item.tie_break_aggregation or "",
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
    compare = None
    if viable.compare_metric and viable.compare_operator and viable.compare_value is not None:
        compare = _metric_compare_predicate_cached(
            graph,
            relation_candidates,
            clause_id=_direct_metric_compare_clause_id(spec),
            metric=viable.compare_metric,
            operator=viable.compare_operator,
            value=viable.compare_value,
        )
        if compare is None:
            return None
        relation_candidates = _nodes_matching_metric_compare_cached(
            graph,
            relation_candidates,
            metric=viable.compare_metric,
            operator=viable.compare_operator,
            value=viable.compare_value,
        )
    measurement = _measurement_predicate_cached(
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
            "synthesis_strategy": [_extreme_strategy(viable)],
        },
        compare.sampled_parameters if compare is not None else {},
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
        answer_spec=synthesis_answer_spec_for_target_type(spec.target_type, graph),
        clauses=[
            clause
            for clause in (
                relation.clause if relation is not None else None,
                compare.clause if compare is not None else None,
                measurement.clause,
            )
            if clause is not None
        ],
        aggregation=viable.aggregation,
        aggregation_metric=viable.metric,
        aggregation_rank=viable.aggregation_rank,
        tie_break_aggregation=viable.tie_break_aggregation,
        tie_break_metric=viable.tie_break_metric,
        hop_count=2 + int(relation is not None) + int(compare is not None),
        difficulty="cad_browsecomp",
        min_individual_clause_candidates=2,
        sampled_parameters=sampled,
    )


def _viable_feature_effect_delta_extremes(
    graph: OntologyGraph,
    spec: FeatureEffectDeltaFamilySpec,
) -> list[ViableFeatureEffectDeltaExtreme]:
    candidates = graph.nodes_by_type("feature")
    viable: list[ViableFeatureEffectDeltaExtreme] = []
    for compare_metric in spec.metrics:
        for operator in FEATURE_EFFECT_DELTA_METRIC_OPERATORS[compare_metric]:
            compare = _metric_compare_predicate_cached(
                graph,
                candidates,
                clause_id=spec.compare_clause_id,
                metric=compare_metric,
                operator=operator,
                value=0.0,
            )
            if compare is None:
                continue
            narrowed = _nodes_matching_metric_compare_cached(
                graph,
                candidates,
                metric=compare_metric,
                operator=operator,
                value=0.0,
            )
            selector_metrics = tuple(dict.fromkeys((*spec.metrics, *(spec.selector_metrics or ()))))
            for selector_metric in selector_metrics:
                selector = _measurement_predicate_cached(
                    graph,
                    narrowed,
                    clause_id=spec.selector_metric_clause_id,
                    metric=selector_metric,
                )
                if selector is None:
                    continue
                metric_candidates = _nodes_with_numeric_measurement(graph, narrowed, selector_metric)
                if len(metric_candidates) < 2:
                    continue
                for aggregation in ("argmax", "argmin"):
                    if _has_unique_extreme(graph, metric_candidates, selector_metric, aggregation):
                        viable.append(
                            ViableFeatureEffectDeltaExtreme(
                                spec=spec,
                                compare_metric=compare_metric,
                                operator=operator,
                                selector_metric=selector_metric,
                                aggregation=aggregation,
                                candidate_ids=tuple(node.id for node in metric_candidates),
                            )
                        )
    return sorted(
        viable,
        key=lambda item: (
            item.compare_metric,
            item.operator,
            item.selector_metric,
            item.aggregation,
            item.candidate_ids,
        ),
    )


def _query_for_feature_effect_delta_extreme(
    graph: OntologyGraph,
    viable: ViableFeatureEffectDeltaExtreme,
) -> QueryProgram | None:
    spec = viable.spec
    candidates = graph.nodes_by_type("feature")
    compare = _metric_compare_predicate_cached(
        graph,
        candidates,
        clause_id=spec.compare_clause_id,
        metric=viable.compare_metric,
        operator=viable.operator,
        value=0.0,
    )
    if compare is None:
        return None
    narrowed = _nodes_matching_metric_compare_cached(
        graph,
        candidates,
        metric=viable.compare_metric,
        operator=viable.operator,
        value=0.0,
    )
    selector = _measurement_predicate_cached(
        graph,
        narrowed,
        clause_id=spec.selector_metric_clause_id,
        metric=viable.selector_metric,
    )
    if selector is None:
        return None
    direction = "max" if viable.aggregation == "argmax" else "min"
    sampled = merge_sampled_parameters(
        {
            "target_type": ["feature"],
            "final_selector": [f"{direction}:{viable.selector_metric}"],
            "aggregation_metric": [viable.selector_metric],
            "effect_delta_metric": [viable.compare_metric],
            "effect_delta_sign": ["negative" if viable.operator == "<" else "positive"],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "prompt_wording_variant": [_prompt_wording_variant(graph.graph_id, spec.family_id)],
            "synthesis_strategy": ["feature_effect_delta_extreme_v1"],
        },
        compare.sampled_parameters,
        selector.sampled_parameters,
    )
    compare_axis = metric_axis(viable.compare_metric)
    if compare_axis is not None:
        sampled = merge_sampled_parameters(sampled, {"effect_delta_axis": [compare_axis]})
    selector_axis = metric_axis(viable.selector_metric)
    if selector_axis is not None:
        sampled = merge_sampled_parameters(sampled, {"aggregation_axis": [selector_axis]})
    return QueryProgram(
        query_id=f"{graph.graph_id}:synth:{spec.family_id}",
        target_type="feature",
        answer_spec=synthesis_answer_spec_for_target_type("feature", graph),
        clauses=[
            compare.clause,
            selector.clause,
        ],
        aggregation=viable.aggregation,
        aggregation_metric=viable.selector_metric,
        hop_count=3,
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
    for selector_relation, selector_candidates in _selector_count_contexts(graph, relation_candidates, spec):
        for metric in spec.related_metrics:
            predicates = [
                *(_related_metric_thresholds(graph, selector_candidates, relation=spec.relation, metric=metric)),
                *(
                    ("==", value)
                    for value in _related_metric_equal_values(
                        graph,
                        selector_candidates,
                        relation=spec.relation,
                        metric=metric,
                    )
                ),
            ]
            for operator, value in predicates:
                predicate = related_metric_compare_predicate(
                    graph,
                    selector_candidates,
                    clause_id=spec.related_metric_clause_id,
                    relation=spec.relation,
                    target_type=spec.selected_type,
                    metric=metric,
                    operator=operator,
                    value=value,
                )
                if predicate is None:
                    continue
                if selector_relation is None and predicate.candidate_count_after >= len(selector_candidates):
                    continue
                narrowed = nodes_matching_related_metric_compare(
                    graph,
                    selector_candidates,
                    relation=spec.relation,
                    target_type=spec.selected_type,
                    metric=metric,
                    operator=operator,
                    value=value,
                )
                if len(narrowed) < 2:
                    continue
                if not spec.allow_rank:
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
                                    selector_relation=selector_relation,
                                )
                            )
                            continue
                        tied = _extreme_nodes(graph, narrowed, "selected_count", aggregation)
                        for tie_break_metric, tie_break_aggregation in _viable_tie_break_metrics(
                            graph,
                            spec.selector_tie_break_metrics,
                            tied,
                            primary_metric="selected_count",
                        ):
                            viable.append(
                                ViableSelectorCount(
                                    spec=spec,
                                    metric=metric,
                                    operator=operator,
                                    value=value,
                                    aggregation=aggregation,
                                    candidate_ids=tuple(node.id for node in narrowed),
                                    selector_relation=selector_relation,
                                    tie_break_metric=tie_break_metric,
                                    tie_break_aggregation=tie_break_aggregation,
                                )
                            )
                if spec.allow_rank:
                    for aggregation in ("rank_desc", "rank_asc"):
                        for rank in range(2, min(len(narrowed), MAX_SYNTHESIZED_RANK) + 1):
                            if _has_unique_rank(graph, narrowed, "selected_count", aggregation, rank):
                                viable.append(
                                    ViableSelectorCount(
                                        spec=spec,
                                        metric=metric,
                                        operator=operator,
                                        value=value,
                                        aggregation=aggregation,
                                        candidate_ids=tuple(node.id for node in narrowed),
                                        selector_relation=selector_relation,
                                        aggregation_rank=rank,
                                    )
                                )
                                continue
                            tied = _rank_nodes(graph, narrowed, "selected_count", aggregation, rank)
                            for tie_break_metric, tie_break_aggregation in _viable_tie_break_metrics(
                                graph,
                                spec.selector_tie_break_metrics,
                                tied,
                                primary_metric="selected_count",
                            ):
                                viable.append(
                                    ViableSelectorCount(
                                        spec=spec,
                                        metric=metric,
                                        operator=operator,
                                        value=value,
                                        aggregation=aggregation,
                                        candidate_ids=tuple(node.id for node in narrowed),
                                        selector_relation=selector_relation,
                                        aggregation_rank=rank,
                                        tie_break_metric=tie_break_metric,
                                        tie_break_aggregation=tie_break_aggregation,
                                    )
                                )
    return sorted(
        viable,
        key=lambda item: (
            item.selector_relation or "",
            item.metric,
            item.operator,
            item.value,
            item.aggregation,
            item.aggregation_rank or 0,
            item.tie_break_metric or "",
            item.tie_break_aggregation or "",
            item.candidate_ids,
        ),
    )


def _selector_count_contexts(
    graph: OntologyGraph,
    relation_candidates: list[Node],
    spec: SelectorCountFamilySpec,
) -> list[tuple[str | None, list[Node]]]:
    contexts: list[tuple[str | None, list[Node]]] = [(None, relation_candidates)]
    for selector_relation in spec.selector_relations:
        predicate = relation_predicate(
            graph,
            relation_candidates,
            clause_id=spec.selector_relation_clause_id,
            relation=selector_relation,
            target_type="selector",
        )
        if predicate is None or predicate.candidate_count_after >= len(relation_candidates):
            continue
        narrowed = _apply_relation_clause(graph, relation_candidates, selector_relation)
        if len(narrowed) >= 2:
            contexts.append((selector_relation, narrowed))
    return contexts


def _related_metric_equal_values(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    relation: str,
    metric: str,
) -> list[float]:
    counts: dict[float, int] = {}
    for node in candidates:
        buckets = {
            measurement_bucket_value(measurement.value)
            for edge in graph.relations_from(node.id, relation)
            for measurement in graph.measurements_for(edge.target_id, metric)
            if isinstance(measurement.value, (int, float))
        }
        for bucket in buckets:
            if bucket is not None:
                counts[bucket] = counts.get(bucket, 0) + 1
    return sorted(value for value, count in counts.items() if count >= 2)[:24]


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
    selector_relation = None
    selector_candidates = relation_candidates
    if viable.selector_relation is not None:
        selector_relation = relation_predicate(
            graph,
            relation_candidates,
            clause_id=spec.selector_relation_clause_id,
            relation=viable.selector_relation,
            target_type="selector",
        )
        if selector_relation is None:
            return None
        selector_candidates = _apply_relation_clause(graph, relation_candidates, viable.selector_relation)
    related_metric = related_metric_compare_predicate(
        graph,
        selector_candidates,
        clause_id=spec.related_metric_clause_id,
        relation=spec.relation,
        target_type=spec.selected_type,
        metric=viable.metric,
        operator=viable.operator,
        value=viable.value,
    )
    selected_count = _measurement_predicate_cached(
        graph,
        selector_candidates,
        clause_id=spec.selected_count_clause_id,
        metric="selected_count",
    )
    if related_metric is None or selected_count is None:
        return None
    direction = "max" if viable.aggregation in {"argmax", "rank_desc"} else "min"
    final_selector = (
        f"rank:{viable.aggregation_rank}:{direction}:selected_count"
        if viable.aggregation_rank is not None
        else f"{direction}:selected_count"
    )
    sampled = merge_sampled_parameters(
        {
            "target_type": ["selector"],
            "selected_entity_type": [spec.selected_type],
            "final_selector": [final_selector],
            "aggregation_metric": ["selected_count"],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "prompt_wording_variant": [_prompt_wording_variant(graph.graph_id, spec.family_id)],
            "synthesis_strategy": [
                _selector_count_synthesis_strategy(viable)
            ],
        },
        relation.sampled_parameters,
        selector_relation.sampled_parameters if selector_relation is not None else {},
        (
            {
                "selector_relation": [viable.selector_relation],
                "narrowing_mode": ["selector_relation"],
            }
            if viable.selector_relation is not None
            else {"narrowing_mode": ["related_metric_compare"]}
        ),
        related_metric.sampled_parameters,
        selected_count.sampled_parameters,
    )
    axis = metric_axis(viable.metric)
    if axis is not None:
        sampled = merge_sampled_parameters(sampled, {"narrowing_axis": [axis]})
    if viable.aggregation_rank is not None:
        sampled = merge_sampled_parameters(
            sampled,
            {
                "aggregation_rank": [str(viable.aggregation_rank)],
                "rank_direction": [direction],
            },
        )
    if viable.tie_break_metric is not None and viable.tie_break_aggregation is not None:
        tie_break_direction = "max" if viable.tie_break_aggregation == "argmax" else "min"
        sampled = merge_sampled_parameters(
            sampled,
            {
                "tie_break_metric": [viable.tie_break_metric],
                "tie_break_direction": [tie_break_direction],
                "tie_break_selector": [f"{tie_break_direction}:{viable.tie_break_metric}"],
            },
        )
    tie_break_axis = metric_axis(viable.tie_break_metric) if viable.tie_break_metric else None
    if tie_break_axis is not None:
        sampled = merge_sampled_parameters(sampled, {"tie_break_axis": [tie_break_axis]})
    return QueryProgram(
        query_id=f"{graph.graph_id}:synth:{spec.family_id}",
        target_type="selector",
        answer_spec=synthesis_answer_spec_for_target_type("selector", graph),
        clauses=[
            clause
            for clause in (
                relation.clause,
                selector_relation.clause if selector_relation is not None else None,
                related_metric.clause,
                selected_count.clause,
            )
            if clause is not None
        ],
        aggregation=viable.aggregation,
        aggregation_metric="selected_count",
        aggregation_rank=viable.aggregation_rank,
        tie_break_aggregation=viable.tie_break_aggregation,
        tie_break_metric=viable.tie_break_metric,
        hop_count=4 + int(selector_relation is not None),
        difficulty="cad_browsecomp",
        min_individual_clause_candidates=2,
        sampled_parameters=sampled,
    )


def _selector_count_synthesis_strategy(viable: ViableSelectorCount) -> str:
    prefix = (
        "selector_count_rank_narrowing"
        if viable.aggregation_rank is not None
        else "selector_count_narrowing"
    )
    if viable.tie_break_metric is not None:
        return f"{prefix}_tie_break_v1"
    return f"{prefix}_v1"


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
            value_predicate = _measurement_value_predicate_cached(
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
                measurement = _measurement_predicate_cached(
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
                if spec.selection_mode == "rank":
                    if len(metric_candidates) < 3:
                        continue
                    for aggregation in ("rank_desc", "rank_asc"):
                        for rank in range(2, min(len(metric_candidates), MAX_SYNTHESIZED_RANK) + 1):
                            if _has_unique_rank(graph, metric_candidates, selector_metric, aggregation, rank):
                                viable.append(
                                    ViableEqualValueExtreme(
                                        spec=spec,
                                        equal_metric=equal_metric,
                                        equal_value=equal_value,
                                        selector_metric=selector_metric,
                                        aggregation=aggregation,
                                        candidate_ids=tuple(node.id for node in metric_candidates),
                                        aggregation_rank=rank,
                                    )
                                )
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
            item.aggregation_rank or 0,
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
    equal_value = _measurement_value_predicate_cached(
        graph,
        relation_candidates,
        clause_id=spec.equal_value_clause_id,
        metric=viable.equal_metric,
        value=viable.equal_value,
    )
    if equal_value is None:
        return None
    equal_candidates = _nodes_matching_measurement_value_cached(
        graph,
        relation_candidates,
        metric=viable.equal_metric,
        value=viable.equal_value,
    )
    selector_metric = _measurement_predicate_cached(
        graph,
        equal_candidates,
        clause_id=spec.selector_metric_clause_id,
        metric=viable.selector_metric,
    )
    if selector_metric is None:
        return None
    direction = "max" if viable.aggregation in {"argmax", "rank_desc"} else "min"
    final_selector = (
        f"rank:{viable.aggregation_rank}:{direction}:{viable.selector_metric}"
        if viable.aggregation_rank is not None
        else f"{direction}:{viable.selector_metric}"
    )
    sampled = merge_sampled_parameters(
        {
            "target_type": [spec.target_type],
            "final_selector": [final_selector],
            "aggregation_metric": [viable.selector_metric],
            "equal_measurement_metric": [viable.equal_metric],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "prompt_wording_variant": [_prompt_wording_variant(graph.graph_id, spec.family_id)],
            "synthesis_strategy": [
                "equal_measurement_rank_narrowing_v1"
                if viable.aggregation_rank is not None
                else "equal_measurement_narrowing_v1"
            ],
        },
        equal_value.sampled_parameters,
        selector_metric.sampled_parameters,
    )
    if viable.aggregation_rank is not None:
        sampled = merge_sampled_parameters(
            sampled,
            {
                "aggregation_rank": [str(viable.aggregation_rank)],
                "rank_direction": [direction],
            },
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
        answer_spec=synthesis_answer_spec_for_target_type(spec.target_type, graph),
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
        aggregation_rank=viable.aggregation_rank,
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
        viable.extend(
            _viable_relation_extremes_for_candidates(
                graph,
                spec,
                relation_name=relation_name,
                relation_candidates=relation_candidates,
            )
        )
        for compare_metric in spec.metrics:
            for operator, value in _metric_thresholds(graph, relation_candidates, compare_metric):
                compare = _metric_compare_predicate_cached(
                    graph,
                    relation_candidates,
                    clause_id=_relation_metric_compare_clause_id(spec),
                    metric=compare_metric,
                    operator=operator,
                    value=value,
                )
                if compare is None:
                    continue
                narrowed = _nodes_matching_metric_compare_cached(
                    graph,
                    relation_candidates,
                    metric=compare_metric,
                    operator=operator,
                    value=value,
                )
                if len(narrowed) >= len(relation_candidates):
                    continue
                viable.extend(
                    _viable_relation_extremes_for_candidates(
                        graph,
                        spec,
                        relation_name=relation_name,
                        relation_candidates=narrowed,
                        compare_metric=compare_metric,
                        compare_operator=operator,
                        compare_value=value,
                    )
                )
    return sorted(
        viable,
        key=lambda item: (
            item.relation,
            item.metric,
            item.aggregation,
            item.aggregation_rank or 0,
            item.compare_metric or "",
            item.compare_operator or "",
            item.compare_value if item.compare_value is not None else 0.0,
            item.tie_break_metric or "",
            item.tie_break_aggregation or "",
            item.candidate_ids,
        ),
    )


def _viable_relation_extremes_for_candidates(
    graph: OntologyGraph,
    spec: RelationExtremeFamilySpec,
    *,
    relation_name: str,
    relation_candidates: list[Node],
    compare_metric: str | None = None,
    compare_operator: str | None = None,
    compare_value: float | None = None,
) -> list[ViableRelationExtreme]:
    viable: list[ViableRelationExtreme] = []
    for metric in spec.metrics:
        if compare_metric == metric:
            continue
        measurement = _measurement_predicate_cached(
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
        if spec.selection_mode == "rank" and len(metric_candidates) < 3:
            continue
        if spec.selection_mode == "tie_break":
            for aggregation in ("argmax", "argmin"):
                if _has_unique_extreme(graph, metric_candidates, metric, aggregation):
                    continue
                tied = _extreme_nodes(graph, metric_candidates, metric, aggregation)
                for tie_break_metric, tie_break_aggregation in _viable_tie_break_metrics(
                    graph,
                    spec.metrics,
                    tied,
                    primary_metric=metric,
                ):
                    viable.append(
                        ViableRelationExtreme(
                            spec=spec,
                            relation=relation_name,
                            metric=metric,
                            aggregation=aggregation,
                            candidate_ids=tuple(node.id for node in metric_candidates),
                            aggregation_rank=None,
                            tie_break_metric=tie_break_metric,
                            tie_break_aggregation=tie_break_aggregation,
                            compare_metric=compare_metric,
                            compare_operator=compare_operator,
                            compare_value=compare_value,
                        )
                    )
            continue
        aggregations = (
            ("rank_desc", "rank_asc")
            if spec.selection_mode == "rank"
            else ("argmax", "argmin")
        )
        scored = _scored_node_ids(graph, metric_candidates, metric)
        for aggregation in aggregations:
            if spec.selection_mode == "rank":
                for rank in _unique_scored_rank_positions(scored, aggregation):
                    viable.append(
                        ViableRelationExtreme(
                            spec=spec,
                            relation=relation_name,
                            metric=metric,
                            aggregation=aggregation,
                            candidate_ids=tuple(node.id for node in metric_candidates),
                            aggregation_rank=rank,
                            compare_metric=compare_metric,
                            compare_operator=compare_operator,
                            compare_value=compare_value,
                        )
                    )
                continue
            if _has_unique_scored_extreme(scored, aggregation):
                viable.append(
                    ViableRelationExtreme(
                        spec=spec,
                        relation=relation_name,
                        metric=metric,
                        aggregation=aggregation,
                        candidate_ids=tuple(node.id for node in metric_candidates),
                        compare_metric=compare_metric,
                        compare_operator=compare_operator,
                        compare_value=compare_value,
                    )
                )
    return viable


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
    compare = None
    if viable.compare_metric and viable.compare_operator and viable.compare_value is not None:
        compare = _metric_compare_predicate_cached(
            graph,
            relation_candidates,
            clause_id=_relation_metric_compare_clause_id(spec),
            metric=viable.compare_metric,
            operator=viable.compare_operator,
            value=viable.compare_value,
        )
        if compare is None:
            return None
        relation_candidates = _nodes_matching_metric_compare_cached(
            graph,
            relation_candidates,
            metric=viable.compare_metric,
            operator=viable.compare_operator,
            value=viable.compare_value,
        )
    measurement = _measurement_predicate_cached(
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
            "spatial_relation": [viable.relation],
            "final_selector": [final_selector],
            "aggregation_metric": [viable.metric],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "prompt_wording_variant": [_prompt_wording_variant(graph.graph_id, spec.family_id)],
            "synthesis_strategy": [_relation_extreme_strategy(viable)],
        },
        relation.sampled_parameters,
        compare.sampled_parameters if compare is not None else {},
        measurement.sampled_parameters,
    )
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
        answer_spec=synthesis_answer_spec_for_target_type(spec.target_type, graph),
        clauses=[
            clause
            for clause in (
                base_relation.clause,
                relation.clause,
                compare.clause if compare is not None else None,
                measurement.clause,
            )
            if clause is not None
        ],
        aggregation=viable.aggregation,
        aggregation_metric=viable.metric,
        aggregation_rank=viable.aggregation_rank,
        tie_break_aggregation=viable.tie_break_aggregation,
        tie_break_metric=viable.tie_break_metric,
        hop_count=4,
        difficulty="cad_browsecomp",
        min_individual_clause_candidates=2,
        sampled_parameters=sampled,
    )


def _viable_relation_chain_extremes(
    graph: OntologyGraph,
    spec: RelationChainFamilySpec,
) -> list[ViableRelationChainExtreme]:
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
    viable: list[ViableRelationChainExtreme] = []
    for relation_chain in _relation_chains(spec.relations, spec.chain_lengths):
        chain_candidates = base_candidates
        narrowed_by_chain = False
        chain_is_viable = True
        for relation_name in relation_chain:
            relation = relation_predicate(
                graph,
                chain_candidates,
                clause_id=spec.relation_clause_id,
                relation=relation_name,
                target_type=spec.relation_target_type,
            )
            if relation is None:
                chain_is_viable = False
                break
            next_candidates = _apply_relation_clause(graph, chain_candidates, relation_name)
            narrowed_by_chain = narrowed_by_chain or len(next_candidates) < len(chain_candidates)
            chain_candidates = next_candidates
        if not chain_is_viable or not narrowed_by_chain:
            continue
        for metric in spec.metrics:
            measurement = _measurement_predicate_cached(
                graph,
                chain_candidates,
                clause_id=spec.measurement_clause_id,
                metric=metric,
            )
            if measurement is None:
                continue
            metric_candidates = _nodes_with_numeric_measurement(graph, chain_candidates, metric)
            if len(metric_candidates) < 2:
                continue
            if spec.selection_mode == "tie_break":
                for aggregation in ("argmax", "argmin"):
                    if _has_unique_extreme(graph, metric_candidates, metric, aggregation):
                        continue
                    tied = _extreme_nodes(graph, metric_candidates, metric, aggregation)
                    for tie_break_metric, tie_break_aggregation in _viable_tie_break_metrics(
                        graph,
                        spec.metrics,
                        tied,
                        primary_metric=metric,
                    ):
                        viable.append(
                            ViableRelationChainExtreme(
                                spec=spec,
                                relation_chain=relation_chain,
                                metric=metric,
                                aggregation=aggregation,
                                candidate_ids=tuple(node.id for node in metric_candidates),
                                tie_break_metric=tie_break_metric,
                                tie_break_aggregation=tie_break_aggregation,
                            )
                        )
                continue
            if spec.selection_mode == "rank":
                if len(metric_candidates) < 3:
                    continue
                for aggregation in ("rank_desc", "rank_asc"):
                    for rank in range(2, min(len(metric_candidates), MAX_SYNTHESIZED_RANK) + 1):
                        if _has_unique_rank(graph, metric_candidates, metric, aggregation, rank):
                            viable.append(
                                ViableRelationChainExtreme(
                                    spec=spec,
                                    relation_chain=relation_chain,
                                    metric=metric,
                                    aggregation=aggregation,
                                    candidate_ids=tuple(node.id for node in metric_candidates),
                                    aggregation_rank=rank,
                                )
                            )
                continue
            for aggregation in ("argmax", "argmin"):
                if _has_unique_extreme(graph, metric_candidates, metric, aggregation):
                    viable.append(
                        ViableRelationChainExtreme(
                            spec=spec,
                            relation_chain=relation_chain,
                            metric=metric,
                            aggregation=aggregation,
                            candidate_ids=tuple(node.id for node in metric_candidates),
                        )
                    )
    return sorted(
        viable,
        key=lambda item: (
            item.relation_chain,
            item.metric,
            item.aggregation,
            item.aggregation_rank or 0,
            item.tie_break_metric or "",
            item.tie_break_aggregation or "",
            item.candidate_ids,
        ),
    )


def _query_for_relation_chain_extreme(
    graph: OntologyGraph,
    viable: ViableRelationChainExtreme,
) -> QueryProgram | None:
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
    relation_candidates = _apply_relation_clause(graph, broad_candidates, spec.base_relation)
    relation_instances = []
    for index, relation_name in enumerate(viable.relation_chain, start=1):
        relation = relation_predicate(
            graph,
            relation_candidates,
            clause_id=f"{spec.relation_clause_id}_{index}",
            relation=relation_name,
            target_type=spec.relation_target_type,
        )
        if relation is None:
            return None
        relation_instances.append(relation)
        relation_candidates = _apply_relation_clause(graph, relation_candidates, relation_name)
    measurement = _measurement_predicate_cached(
        graph,
        relation_candidates,
        clause_id=spec.measurement_clause_id,
        metric=viable.metric,
    )
    if measurement is None:
        return None
    direction = "max" if viable.aggregation in {"argmax", "rank_desc"} else "min"
    relation_chain = ">".join(viable.relation_chain)
    final_selector = (
        f"rank:{viable.aggregation_rank}:{direction}:{viable.metric}"
        if viable.aggregation_rank is not None
        else f"{direction}:{viable.metric}"
    )
    sampled = merge_sampled_parameters(
        {
            "target_type": [spec.target_type],
            "spatial_relation_chain": [relation_chain],
            "spatial_relation_chain_length": [str(len(viable.relation_chain))],
            "final_selector": [final_selector],
            "aggregation_metric": [viable.metric],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "prompt_wording_variant": [_prompt_wording_variant(graph.graph_id, spec.family_id)],
            "synthesis_strategy": [
                "spatial_relation_chain_rank_v1"
                if viable.aggregation_rank is not None
                else (
                    "spatial_relation_chain_tie_break_extreme_v1"
                    if viable.tie_break_metric is not None
                    else "spatial_relation_chain_extreme_v1"
                )
            ],
        },
        base_relation.sampled_parameters,
        *(relation.sampled_parameters for relation in relation_instances),
        measurement.sampled_parameters,
    )
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
        answer_spec=synthesis_answer_spec_for_target_type(spec.target_type, graph),
        clauses=[
            base_relation.clause,
            *(relation.clause for relation in relation_instances),
            measurement.clause,
        ],
        aggregation=viable.aggregation,
        aggregation_metric=viable.metric,
        aggregation_rank=viable.aggregation_rank,
        tie_break_aggregation=viable.tie_break_aggregation,
        tie_break_metric=viable.tie_break_metric,
        hop_count=3 + len(viable.relation_chain),
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
    references = _unique_reference_anchors(
        graph,
        graph.nodes_by_type(spec.reference_type),
        reference_type=spec.reference_type,
        reference_point_metric=spec.reference_point_metric,
    )
    references = _sample_reference_distance_anchors(graph.graph_id, spec, references)
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
        if _measurement_value_predicate_cached(
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
            if spec.selection_mode == "rank":
                scored = tuple(zip((node.id for node in target_nodes), distances, strict=True))
                if len(scored) < 2:
                    continue
                for aggregation in ("rank_asc", "rank_desc"):
                    for rank in range(2, min(len(scored), MAX_SYNTHESIZED_RANK) + 1):
                        if _has_unique_scored_rank(scored, aggregation, rank):
                            viable.append(
                                ViableReferenceDistance(
                                    spec=spec,
                                    equal_value=equal_value,
                                    reference_id=reference.id,
                                    aggregation=aggregation,
                                    candidate_ids=tuple(node.id for node in target_nodes),
                                    aggregation_rank=rank,
                                )
                            )
                continue
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
            item.aggregation_rank or 0,
            item.candidate_ids,
        ),
    )


def _sample_reference_distance_anchors(
    graph_id: str,
    spec: ReferenceDistanceFamilySpec,
    references: list[Node],
) -> list[Node]:
    if len(references) <= MAX_REFERENCE_DISTANCE_ANCHORS:
        return references
    sample_key = (
        f"{spec.family_id}:"
        f"{spec.target_type}:"
        f"{spec.equal_metric}:"
        f"{spec.target_point_metric}:"
        f"{spec.reference_type}:"
        f"{spec.reference_point_metric}:"
        f"{spec.selection_mode}"
    )
    start = _stable_choice_index(graph_id, sample_key, len(references))
    ordered = [references[(start + offset) % len(references)] for offset in range(len(references))]
    return ordered[:MAX_REFERENCE_DISTANCE_ANCHORS]


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
    equal_value = _measurement_value_predicate_cached(
        graph,
        relation_candidates,
        clause_id=spec.equal_value_clause_id,
        metric=spec.equal_metric,
        value=viable.equal_value,
    )
    if equal_value is None:
        return None
    equal_candidates = _nodes_matching_measurement_value_cached(
        graph,
        relation_candidates,
        metric=spec.equal_metric,
        value=viable.equal_value,
    )
    target_point = _measurement_predicate_cached(
        graph,
        equal_candidates,
        clause_id=spec.target_point_clause_id,
        metric=spec.target_point_metric,
    )
    reference = graph.node(viable.reference_id)
    if target_point is None or reference is None:
        return None
    reference_value = _reference_anchor_prompt_value(
        graph,
        reference,
        reference_type=spec.reference_type,
        reference_point_metric=spec.reference_point_metric,
    )
    reference_metrics = _reference_anchor_metrics(
        spec.reference_type,
        reference_point_metric=spec.reference_point_metric,
    )
    direction = "min" if viable.aggregation in {"argmin", "rank_asc"} else "max"
    canonical_family = _canonical_reference_distance_family(spec)
    final_selector = (
        f"rank:{viable.aggregation_rank}:{direction}:{REFERENCE_FEATURE_DISTANCE_METRIC}"
        if viable.aggregation_rank is not None
        else f"{direction}:{REFERENCE_FEATURE_DISTANCE_METRIC}"
    )
    sampled = merge_sampled_parameters(
        {
            "target_type": [spec.target_type],
            "reference_type": [spec.reference_type],
            "reference_metric": [REFERENCE_FEATURE_DISTANCE_METRIC],
            "reference_point_metric": [spec.reference_point_metric],
            "target_point_metric": [spec.target_point_metric],
            "reference_anchor_id": [viable.reference_id],
            "reference_anchor_metric": list(reference_metrics),
            "reference_anchor_signature": [_reference_anchor_signature(reference_value)],
            "reference_anchor_value_bucket": [
                f"{metric}:{_value_bucket(reference_value.get('reference_anchor_values', {}).get(metric))}"
                for metric in reference_metrics
            ],
            "final_selector": [final_selector],
            "aggregation_metric": [REFERENCE_FEATURE_DISTANCE_METRIC],
            "equal_measurement_metric": [spec.equal_metric],
            "extremum_direction": [direction],
            "predicate_catalog_version": ["v1"],
            "prompt_wording_variant": [_prompt_wording_variant(graph.graph_id, spec.family_id)],
            "synthesis_strategy": [
                "reference_distance_rank_narrowing_v1"
                if viable.aggregation_rank is not None
                else "reference_distance_narrowing_v1"
            ],
        },
        equal_value.sampled_parameters,
        target_point.sampled_parameters,
    )
    if canonical_family is not None:
        sampled = merge_sampled_parameters(sampled, {"canonical_prompt_family": [canonical_family]})
    if viable.aggregation_rank is not None:
        sampled = merge_sampled_parameters(
            sampled,
            {
                "aggregation_rank": [str(viable.aggregation_rank)],
                "rank_direction": [direction],
            },
        )
    if relation is not None:
        sampled = merge_sampled_parameters(sampled, relation.sampled_parameters)
    return QueryProgram(
        query_id=f"{graph.graph_id}:synth:{spec.family_id}",
        target_type=spec.target_type,
        answer_spec=synthesis_answer_spec_for_target_type(spec.target_type, graph),
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
        aggregation_rank=viable.aggregation_rank,
        hop_count=4 + int(relation is not None),
        difficulty="cad_browsecomp",
        min_individual_clause_candidates=2,
        sampled_parameters=sampled,
    )


def _canonical_reference_distance_family(spec: ReferenceDistanceFamilySpec) -> str | None:
    if spec.family_id.endswith("_reference_entity_distance_rank"):
        return "parameterized_reference_entity_distance_rank"
    if spec.family_id.endswith("_reference_entity_distance"):
        return "parameterized_reference_entity_distance"
    return None


def _apply_relation_clause(graph: OntologyGraph, candidates: list[Node], relation_type: str) -> list[Node]:
    return [
        node
        for node in candidates
        if graph.relations_from(node.id, relation_type)
    ]


def _relation_chains(relations: tuple[str, ...], chain_lengths: tuple[int, ...]) -> list[tuple[str, ...]]:
    chains: list[tuple[str, ...]] = []
    for chain_length in sorted(chain_lengths):
        if chain_length < 2:
            continue
        chains.extend(_relation_chains_of_length(relations, chain_length, ()))
    return chains


def _relation_chains_of_length(
    relations: tuple[str, ...],
    chain_length: int,
    prefix: tuple[str, ...],
) -> list[tuple[str, ...]]:
    if len(prefix) == chain_length:
        return [prefix]
    chains: list[tuple[str, ...]] = []
    for relation in relations:
        if relation in prefix:
            continue
        chains.extend(_relation_chains_of_length(relations, chain_length, (*prefix, relation)))
    return chains


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
            for edge in graph.relations_from(node.id, relation)
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
    return thresholds[:MAX_RELATED_METRIC_COMPARE_THRESHOLDS]


def _metric_thresholds(
    graph: OntologyGraph,
    candidates: list[Node],
    metric: str,
) -> list[tuple[str, float]]:
    values = sorted(
        {
            round(float(value), 6)
            for node in candidates
            if isinstance((value := _measurement_value(graph, node.id, metric)), (int, float))
        }
    )
    thresholds: list[tuple[str, float]] = []
    for value in values:
        if any(candidate_value < value for candidate_value in values):
            thresholds.append(("<", value))
        if any(candidate_value > value for candidate_value in values):
            thresholds.append((">", value))
    return thresholds[:MAX_METRIC_COMPARE_THRESHOLDS]


def _nodes_with_numeric_measurement(graph: OntologyGraph, candidates: list[Node], metric: str) -> list[Node]:
    cache = getattr(graph, "_cached_query_numeric_node_ids", None)
    if cache is None:
        cache = {}
        graph._cached_query_numeric_node_ids = cache
    key = (tuple(node.id for node in candidates), metric)
    if key in cache:
        return [
            node
            for node_id in cache[key]
            if (node := graph.node(node_id)) is not None
        ]
    node_ids = tuple(
        node.id
        for node in candidates
        if isinstance(_measurement_value(graph, node.id, metric), (int, float))
    )
    cache[key] = node_ids
    return [
        node
        for node_id in node_ids
        if (node := graph.node(node_id)) is not None
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


def _unique_reference_anchors(
    graph: OntologyGraph,
    references: list[Node],
    *,
    reference_type: str,
    reference_point_metric: str,
) -> list[Node]:
    counts: dict[tuple[float | None, ...], int] = {}
    keyed: list[tuple[Node, tuple[float | None, ...]]] = []
    for reference in references:
        key = _reference_anchor_key(
            graph,
            reference.id,
            reference_type=reference_type,
            reference_point_metric=reference_point_metric,
        )
        keyed.append((reference, key))
        counts[key] = counts.get(key, 0) + 1
    return [
        reference
        for reference, key in sorted(keyed, key=lambda item: item[0].id)
        if None not in key
        and counts.get(key, 0) == 1
        and _point_measurement(graph, reference.id, reference_point_metric) is not None
    ]


def _reference_anchor_prompt_value(
    graph: OntologyGraph,
    reference: Node,
    *,
    reference_type: str,
    reference_point_metric: str,
) -> dict[str, Any]:
    metrics = _reference_anchor_metrics(reference_type, reference_point_metric=reference_point_metric)
    values = {
        metric: measurement_bucket_value(_measurement_value(graph, reference.id, metric))
        for metric in metrics
    }
    return {
        "reference_id": reference.id,
        "reference_type": reference_type,
        "reference_anchor_metrics": list(metrics),
        "reference_anchor_values": values,
        "reference_volume": values.get("volume"),
        "reference_centroid_z": values.get("centroid_z"),
        "reference_bbox_center_x": values.get("bbox_center_x"),
        "reference_bbox_center_y": values.get("bbox_center_y"),
        "reference_bbox_center_z": values.get("bbox_center_z"),
        "reference_face_area": values.get("face_area"),
        "reference_face_center_z": values.get("coordinate_z"),
        "reference_edge_length": values.get("edge_length"),
        "reference_edge_midpoint_x": values.get("midpoint_x"),
        "reference_edge_midpoint_y": values.get("midpoint_y"),
        "reference_edge_midpoint_z": values.get("midpoint_z"),
        "reference_endpoint_x": values.get("coordinate_x"),
        "reference_endpoint_y": values.get("coordinate_y"),
        "reference_endpoint_z": values.get("coordinate_z"),
        "reference_region_volume": values.get("volume"),
        "reference_region_centroid_x": values.get("centroid_x"),
        "reference_region_centroid_y": values.get("centroid_y"),
        "reference_region_centroid_z": values.get("centroid_z"),
        "reference_region_bbox_center_x": values.get("bbox_center_x"),
        "reference_region_bbox_center_y": values.get("bbox_center_y"),
        "reference_region_bbox_center_z": values.get("bbox_center_z"),
    }


def _reference_anchor_metrics(
    reference_type: str,
    *,
    reference_point_metric: str = "centroid",
) -> tuple[str, ...]:
    if reference_type == "face":
        return ("face_area", "coordinate_z")
    if reference_type == "edge":
        return ("edge_length", "midpoint_x", "midpoint_y", "midpoint_z")
    if reference_type == "edge_endpoint":
        return ("coordinate_x", "coordinate_y", "coordinate_z")
    if reference_point_metric == "bbox_center" and reference_type in {"feature", "material_region", "void_region"}:
        return ("bbox_center_x", "bbox_center_y", "bbox_center_z", "volume")
    if reference_type in {"material_region", "void_region"}:
        return ("volume", "centroid_x", "centroid_y", "centroid_z")
    return ("volume", "centroid_z")


def _reference_anchor_key(
    graph: OntologyGraph,
    reference_id: str,
    *,
    reference_type: str,
    reference_point_metric: str = "centroid",
) -> tuple[float | None, ...]:
    return tuple(
        measurement_bucket_value(_measurement_value(graph, reference_id, metric))
        for metric in _reference_anchor_metrics(reference_type, reference_point_metric=reference_point_metric)
    )


def _reference_anchor_signature(reference_value: dict[str, Any]) -> str:
    reference_type = str(reference_value.get("reference_type", "feature"))
    values = reference_value.get("reference_anchor_values")
    if not isinstance(values, dict):
        values = {
            "centroid_z": reference_value.get("reference_centroid_z"),
            "volume": reference_value.get("reference_volume"),
        }
    parts = "|".join(
        f"{metric}={_value_bucket(values.get(metric))}"
        for metric in sorted(values)
    )
    return f"{reference_type}:{parts}"


def _point_measurement(graph: OntologyGraph, entity_id: str, metric: str) -> list[float] | None:
    cache = getattr(graph, "_cached_query_point_measurements", None)
    if cache is None:
        cache = {}
        graph._cached_query_point_measurements = cache
    key = (entity_id, metric)
    if key in cache:
        return cache[key]
    value = _measurement_value(graph, entity_id, metric)
    if isinstance(value, list) and len(value) >= 3:
        point = _numeric_point(value[:3])
        cache[key] = point
        return point
    scalar_names = {
        "bbox_center": ("bbox_center_x", "bbox_center_y", "bbox_center_z"),
        "centroid": ("centroid_x", "centroid_y", "centroid_z"),
        "midpoint": ("midpoint_x", "midpoint_y", "midpoint_z"),
        "coordinate": ("coordinate_x", "coordinate_y", "coordinate_z"),
    }.get(metric)
    if scalar_names is None:
        cache[key] = None
        return None
    point = _numeric_point([_measurement_value(graph, entity_id, name) for name in scalar_names])
    cache[key] = point
    return point


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
    scores = [score for score, _ in _scored_node_ids(graph, candidates, metric)]
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
    scored = _scored_node_ids(graph, candidates, metric)
    if not scored:
        return []
    target = max(score for score, _ in scored) if aggregation == "argmax" else min(score for score, _ in scored)
    return [
        node
        for score, node_id in scored
        if abs(score - target) <= GEOMETRY_MARGIN_EPSILON
        and (node := graph.node(node_id)) is not None
    ]


def _has_unique_rank(
    graph: OntologyGraph,
    candidates: list[Node],
    metric: str,
    aggregation: str,
    rank: int,
) -> bool:
    return rank in _unique_scored_rank_positions(_scored_node_ids(graph, candidates, metric), aggregation)


def _has_unique_scored_rank(
    scored: tuple[tuple[str, float], ...],
    aggregation: str,
    rank: int,
) -> bool:
    if rank < 1 or rank > len(scored):
        return False
    descending = aggregation == "rank_desc"
    ordered = sorted(scored, key=lambda item: (-item[1] if descending else item[1], item[0]))
    target = ordered[rank - 1][1]
    return sum(1 for _, score in scored if abs(score - target) <= GEOMETRY_MARGIN_EPSILON) == 1


def _unique_scored_rank_positions(
    scored: tuple[tuple[float, str], ...],
    aggregation: str,
) -> list[int]:
    if len(scored) < 2:
        return []
    descending = aggregation == "rank_desc"
    ordered = sorted(scored, key=lambda item: (-item[0] if descending else item[0], item[1]))
    ranks: list[int] = []
    for rank in range(2, min(len(ordered), MAX_SYNTHESIZED_RANK) + 1):
        target = ordered[rank - 1][0]
        previous_tied = rank > 1 and abs(ordered[rank - 2][0] - target) <= GEOMETRY_MARGIN_EPSILON
        next_tied = rank < len(ordered) and abs(ordered[rank][0] - target) <= GEOMETRY_MARGIN_EPSILON
        if not previous_tied and not next_tied:
            ranks.append(rank)
    return ranks


def _has_unique_scored_extreme(scored: tuple[tuple[float, str], ...], aggregation: str) -> bool:
    if len(scored) < 2:
        return False
    scores = sorted((score for score, _ in scored), reverse=aggregation == "argmax")
    return abs(scores[0] - scores[1]) > GEOMETRY_MARGIN_EPSILON


def _rank_nodes(
    graph: OntologyGraph,
    candidates: list[Node],
    metric: str,
    aggregation: str,
    rank: int,
) -> list[Node]:
    scored = _scored_node_ids(graph, candidates, metric)
    if rank < 1 or rank > len(scored):
        return []
    descending = aggregation == "rank_desc"
    ordered = sorted(scored, key=lambda item: (-item[0] if descending else item[0], item[1]))
    target = ordered[rank - 1][0]
    return [
        node
        for score, node_id in scored
        if abs(score - target) <= GEOMETRY_MARGIN_EPSILON
        and (node := graph.node(node_id)) is not None
    ]


def _scored_node_ids(
    graph: OntologyGraph,
    candidates: list[Node],
    metric: str,
) -> tuple[tuple[float, str], ...]:
    cache = getattr(graph, "_cached_query_scored_node_ids", None)
    if cache is None:
        cache = {}
        graph._cached_query_scored_node_ids = cache
    key = (tuple(node.id for node in candidates), metric)
    if key in cache:
        return cache[key]
    scored = tuple(
        (float(value), node.id)
        for node in candidates
        if isinstance((value := _measurement_value(graph, node.id, metric)), (int, float))
    )
    cache[key] = scored
    return scored


def _viable_tie_breaks(
    graph: OntologyGraph,
    spec: ExtremeFamilySpec,
    tied: list[Node],
    *,
    primary_metric: str,
) -> list[tuple[str, str]]:
    return _viable_tie_break_metrics(graph, spec.metrics, tied, primary_metric=primary_metric)


def _viable_tie_break_metrics(
    graph: OntologyGraph,
    metrics: tuple[str, ...],
    tied: list[Node],
    *,
    primary_metric: str,
) -> list[tuple[str, str]]:
    if len(tied) < 2:
        return []
    viable = []
    for metric in metrics:
        if metric == primary_metric:
            continue
        metric_candidates = _nodes_with_numeric_measurement(graph, tied, metric)
        if len(metric_candidates) < 2:
            continue
        for aggregation in ("argmax", "argmin"):
            if _has_unique_extreme(graph, metric_candidates, metric, aggregation):
                viable.append((metric, aggregation))
    return sorted(viable)


def _relation_metric_compare_clause_id(spec: RelationExtremeFamilySpec) -> str:
    return _metric_compare_clause_id(spec.target_type, spec.measurement_clause_id)


def _direct_metric_compare_clause_id(spec: ExtremeFamilySpec) -> str:
    return _metric_compare_clause_id(spec.target_type, spec.measurement_clause_id)


def _metric_compare_clause_id(target_type: str, fallback_measurement_clause_id: str) -> str:
    if target_type == "feature":
        return "has_parameterized_feature_metric_threshold"
    if target_type == "face":
        return "has_parameterized_face_metric_threshold"
    if target_type == "edge":
        return "has_parameterized_edge_metric_threshold"
    if target_type == "vertex":
        return "has_parameterized_vertex_metric_threshold"
    if target_type == "edge_endpoint":
        return "has_parameterized_endpoint_metric_threshold"
    if target_type == "path_point":
        return "has_parameterized_path_point_metric_threshold"
    if target_type == "path_segment":
        return "has_parameterized_path_segment_metric_threshold"
    if target_type == "material_region":
        return "has_parameterized_material_region_metric_threshold"
    if target_type == "void_region":
        return "has_parameterized_void_region_metric_threshold"
    return f"{fallback_measurement_clause_id}_threshold"


def _measurement_predicate_cached(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    clause_id: str,
    metric: str,
) -> PredicateInstance | None:
    after = _nodes_with_measurement_cached(graph, candidates, metric)
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


def _measurement_value_predicate_cached(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    clause_id: str,
    metric: str,
    value: float,
) -> PredicateInstance | None:
    after = _nodes_matching_measurement_value_cached(
        graph,
        candidates,
        metric=metric,
        value=value,
    )
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


def _nodes_with_measurement_cached(
    graph: OntologyGraph,
    candidates: list[Node],
    metric: str,
) -> list[Node]:
    cache = getattr(graph, "_cached_query_measurement_node_ids", None)
    if cache is None:
        cache = {}
        graph._cached_query_measurement_node_ids = cache
    key = (tuple(node.id for node in candidates), metric)
    if key in cache:
        return [
            node
            for node_id in cache[key]
            if (node := graph.node(node_id)) is not None
        ]
    node_ids = tuple(
        node.id
        for node in candidates
        if _has_measurement_cached(graph, node.id, metric)
    )
    cache[key] = node_ids
    return [
        node
        for node_id in node_ids
        if (node := graph.node(node_id)) is not None
    ]


def _has_measurement_cached(graph: OntologyGraph, entity_id: str, metric: str) -> bool:
    if _measurement_values(graph, entity_id, metric):
        return True
    return all(_measurement_values(graph, entity_id, component) for component in _point_metric_components(metric))


def _point_metric_components(metric: str) -> tuple[str, ...]:
    return {
        "bbox_center": ("bbox_center_x", "bbox_center_y", "bbox_center_z"),
        "centroid": ("centroid_x", "centroid_y", "centroid_z"),
        "midpoint": ("midpoint_x", "midpoint_y", "midpoint_z"),
        "coordinate": ("coordinate_x", "coordinate_y", "coordinate_z"),
    }.get(metric, ())


def _nodes_matching_measurement_value_cached(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    metric: str,
    value: float,
) -> list[Node]:
    cache = getattr(graph, "_cached_query_equal_measurement_node_ids", None)
    if cache is None:
        cache = {}
        graph._cached_query_equal_measurement_node_ids = cache
    key = (tuple(node.id for node in candidates), metric, value)
    if key in cache:
        return [
            node
            for node_id in cache[key]
            if (node := graph.node(node_id)) is not None
        ]
    node_ids = tuple(
        node.id
        for node in candidates
        if any(_value_matches(measured, value) for measured in _measurement_values(graph, node.id, metric))
    )
    cache[key] = node_ids
    return [
        node
        for node_id in node_ids
        if (node := graph.node(node_id)) is not None
    ]


def _metric_compare_predicate_cached(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    clause_id: str,
    metric: str,
    operator: str,
    value: float,
) -> PredicateInstance | None:
    after = _nodes_matching_metric_compare_cached(
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


def _nodes_matching_metric_compare_cached(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    metric: str,
    operator: str,
    value: float,
) -> list[Node]:
    cache = getattr(graph, "_cached_query_metric_compare_node_ids", None)
    if cache is None:
        cache = {}
        graph._cached_query_metric_compare_node_ids = cache
    key = (tuple(node.id for node in candidates), metric, operator, value)
    if key in cache:
        return [
            node
            for node_id in cache[key]
            if (node := graph.node(node_id)) is not None
        ]
    node_ids = tuple(
        node.id
        for node in candidates
        if any(_numeric_compare(measured, operator, value) for measured in _measurement_values(graph, node.id, metric))
    )
    cache[key] = node_ids
    return [
        node
        for node_id in node_ids
        if (node := graph.node(node_id)) is not None
    ]


def _value_matches(measured: object, expected: float) -> bool:
    return isinstance(measured, (int, float)) and abs(float(measured) - expected) <= GEOMETRY_MARGIN_EPSILON


def _numeric_compare(value: Any, operator: str, threshold: float) -> bool:
    if not isinstance(value, (int, float)):
        return False
    actual = float(value)
    if operator == "<":
        return actual < threshold
    if operator == "<=":
        return actual <= threshold
    if operator == ">":
        return actual > threshold
    if operator == ">=":
        return actual >= threshold
    if operator == "==":
        return abs(actual - threshold) <= GEOMETRY_MARGIN_EPSILON
    if operator == "!=":
        return abs(actual - threshold) > GEOMETRY_MARGIN_EPSILON
    return False


def _extreme_strategy(viable: ViableExtreme) -> str:
    prefix = "bounded_parameterized_metric_compare" if viable.compare_metric is not None else "bounded_parameterized"
    if viable.aggregation_rank is not None:
        return f"{prefix}_rank_v1"
    if viable.tie_break_metric is not None:
        return f"{prefix}_tie_break_extreme_v1"
    return f"{prefix}_extreme_v1"


def _relation_extreme_strategy(viable: ViableRelationExtreme) -> str:
    prefix = "spatial_relation_metric_compare" if viable.compare_metric is not None else "spatial_relation"
    if viable.aggregation_rank is not None:
        return f"{prefix}_rank_v1"
    if viable.tie_break_metric is not None:
        return f"{prefix}_tie_break_extreme_v1"
    return f"{prefix}_extreme_v1"


def _measurement_value(graph: OntologyGraph, entity_id: str, metric: str) -> Any:
    values = _measurement_values(graph, entity_id, metric)
    return values[0] if values else None


def _measurement_values(graph: OntologyGraph, entity_id: str, metric: str) -> tuple[Any, ...]:
    cache = getattr(graph, "_cached_query_measurement_values", None)
    if cache is None:
        cache = {}
        graph._cached_query_measurement_values = cache
    key = (entity_id, metric)
    if key in cache:
        return cache[key]
    values = tuple(measurement.value for measurement in graph.measurements_for(entity_id, metric))
    cache[key] = values
    return values


def _stable_choice_index(graph_id: str, family_id: str, count: int) -> int:
    digest = hashlib.sha256(f"{graph_id}:{family_id}".encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % count


def _prompt_wording_variant(graph_id: str, family_id: str) -> str:
    return str(_stable_choice_index(graph_id, f"{family_id}:prompt_wording", 3))
