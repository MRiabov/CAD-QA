"""Deterministic query resolver."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from cad_qa.ontology.nodes import Measurement, Node, OntologyGraph
from cad_qa.query.answers import (
    answer_spec_with_candidate_labels,
    answer_spec_with_selector_expression_choices,
    candidate_label_entity_ids,
    format_gold_answer,
)
from cad_qa.query.candidates import candidate_ids, initial_candidates
from cad_qa.query.difficulty import difficulty_for_hops
from cad_qa.query.ir import CandidateSetTrace, Clause, QueryProgram, QueryResolution
from cad_qa.query.predicate_catalog import nodes_matching_related_metric_compare
from cad_qa.query.synthesis import synthesize_graph_hop_queries


GEOMETRY_MARGIN_EPSILON = 1e-6
VALUE_MATCH_TOLERANCE = 1e-6
VALUE_BUCKET_DECIMALS = 6
REFERENCE_FEATURE_DISTANCE_METRIC = "distance_to_reference_feature_centroid"


def resolve_query(graph: OntologyGraph, query: QueryProgram) -> QueryResolution:
    query = replace(query, difficulty=query.difficulty or difficulty_for_hops(query.hop_count))
    candidates = initial_candidates(graph, query.target_type)
    steps: list[dict[str, Any]] = [
        {"step": "initial", "candidate_ids": candidate_ids(candidates)}
    ]
    relation_families: set[str] = set()
    measurement_scopes: set[str] = set()
    for clause in query.clauses:
        before = candidate_ids(candidates)
        candidates = _apply_clause(graph, candidates, clause)
        after = candidate_ids(candidates)
        if clause.relation:
            relation_families.add(clause.relation)
        if clause.metric:
            measurement_scopes.update(_measurement_scopes_for_clause(graph, candidates, clause))
        steps.append(
            {
                "step": clause.id,
                "kind": clause.kind,
                "before": before,
                "after": after,
                "text": clause.text,
            }
        )
        if query.hop_count >= 3 and len(after) < query.min_individual_clause_candidates:
            trace = CandidateSetTrace(
                query.query_id,
                steps,
                after,
                "failed",
                "clue_too_narrow",
            )
            return QueryResolution(
                query_program=query,
                gold_answer=None,
                candidate_trace=trace,
                relation_families=sorted(relation_families),
                measurement_scopes=sorted(measurement_scopes),
                verifier_status="failed",
            )
    if query.aggregation:
        before = candidate_ids(candidates)
        candidates = _apply_primary_aggregation(graph, candidates, query)
        steps.append(
            {
                "step": "aggregation",
                "aggregation": query.aggregation,
                "metric": query.aggregation_metric,
                "rank": query.aggregation_rank,
                "before": before,
                "after": candidate_ids(candidates),
            }
        )
        if query.aggregation_metric:
            measurement_scopes.update(
                measurement.scope
                for node in candidates
                for measurement in graph.measurements_for(node.id, query.aggregation_metric)
            )
        if len(candidates) > 1 and query.tie_break_aggregation and query.tie_break_metric:
            before_tie_break = candidate_ids(candidates)
            candidates = _apply_metric_aggregation(
                graph,
                candidates,
                aggregation=query.tie_break_aggregation,
                metric=query.tie_break_metric,
            )
            steps.append(
                {
                    "step": "tie_break_aggregation",
                    "aggregation": query.tie_break_aggregation,
                    "metric": query.tie_break_metric,
                    "before": before_tie_break,
                    "after": candidate_ids(candidates),
                }
            )
            measurement_scopes.update(
                measurement.scope
                for node in candidates
                for measurement in graph.measurements_for(node.id, query.tie_break_metric)
            )
    status = "resolved"
    failure_reason = None
    if not candidates:
        status = "failed"
        failure_reason = "no_candidates"
    elif query.reject_unless_unique and len(candidates) != 1:
        status = "failed"
        failure_reason = "not_unique"
    final_candidate_ids = candidate_ids(candidates)
    trace = CandidateSetTrace(query.query_id, steps, final_candidate_ids, status, failure_reason)
    choice_answer_modes = {"candidate_label", "selector_expression_choice"}
    if status == "resolved" and getattr(query.answer_spec, "mode", None) in choice_answer_modes:
        label_entity_ids = candidate_label_entity_ids(steps, final_candidate_ids)
        if len(label_entity_ids) > query.answer_spec.max_candidate_labels:
            status = "failed"
            failure_reason = "too_many_candidate_labels"
            trace = CandidateSetTrace(query.query_id, steps, final_candidate_ids, status, failure_reason)
        elif getattr(query.answer_spec, "mode", None) == "selector_expression_choice":
            selector_spec = answer_spec_with_selector_expression_choices(
                graph,
                query.answer_spec,
                candidates[0].id,
                label_entity_ids,
            )
            if selector_spec is not None:
                query = replace(query, answer_spec=selector_spec)
            else:
                query = replace(query, answer_spec=replace(query.answer_spec, mode="candidate_label"))
                query = replace(
                    query,
                    answer_spec=answer_spec_with_candidate_labels(query.answer_spec, label_entity_ids),
                )
        else:
            query = replace(
                query,
                answer_spec=answer_spec_with_candidate_labels(query.answer_spec, label_entity_ids),
            )
    gold_answer = format_gold_answer(graph, query, candidates[0]) if status == "resolved" else None
    return QueryResolution(
        query_program=query,
        gold_answer=gold_answer,
        candidate_trace=trace,
        relation_families=sorted(relation_families),
        measurement_scopes=sorted(measurement_scopes),
        verifier_status=status,
    )


def smoke_queries(graph: OntologyGraph) -> list[QueryProgram]:
    queries: list[QueryProgram] = []
    operations = graph.nodes_by_type("operation")
    profiles = graph.nodes_by_type("profile")
    workplanes = graph.nodes_by_type("workplane")
    faces = graph.nodes_by_type("face")
    edges = graph.nodes_by_type("edge")
    edge_endpoints = graph.nodes_by_type("edge_endpoint")
    paths = graph.nodes_by_type("path")
    path_points = graph.nodes_by_type("path_point")
    path_segments = graph.nodes_by_type("path_segment")
    selectors = graph.nodes_by_type("selector")
    material_regions = graph.nodes_by_type("material_region")
    void_regions = graph.nodes_by_type("void_region")
    features = graph.nodes_by_type("feature")
    if operations:
        first = min(operations, key=lambda node: node.properties.get("chain_index", 0))
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q0:first_operation",
                target_type="operation",
                clauses=[
                    Clause(
                        id="operation_target",
                        kind="property_equals",
                        metric="target",
                        value=first.properties.get("target"),
                    ),
                    Clause(
                        id="operation_name",
                        kind="property_equals",
                        metric="operation",
                        value=first.properties.get("operation"),
                    )
                ],
                hop_count=0,
                difficulty="low",
            )
        )
    if workplanes:
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q1:highest_workplane",
                target_type="workplane",
                aggregation="argmax",
                aggregation_metric="origin_z",
                hop_count=1,
                difficulty="low",
            )
        )
    if profiles and workplanes:
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q2:profile_on_workplane",
                target_type="profile",
                clauses=[
                    Clause(
                        id="located_on_workplane",
                        kind="has_relation",
                        relation="located_on",
                        target_type="workplane",
                    )
                ],
                aggregation="argmax",
                aggregation_metric="workplane_origin_z",
                hop_count=2,
                difficulty="bridge",
            )
        )
    if len(profiles) >= 3 and workplanes:
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:cad_browsecomp_profile",
                target_type="profile",
                clauses=[
                    Clause(
                        id="located_on_explicit_or_default_workplane",
                        kind="has_relation",
                        relation="located_on",
                        target_type="workplane",
                    ),
                    Clause(
                        id="has_profile_area",
                        kind="has_measurement",
                        metric="area",
                    ),
                    Clause(
                        id="has_workplane_z",
                        kind="has_measurement",
                        metric="workplane_origin_z",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="workplane_origin_z",
                hop_count=3,
                difficulty="cad_browsecomp",
            )
        )
    if faces:
        selected_face_candidates = [face for face in faces if face.properties.get("stable_selector")]
        first_face = sorted(selected_face_candidates or faces, key=lambda node: node.properties.get("stable_selector", ""))[0]
        selector_text = first_face.properties.get("stable_selector")
        selector_relation = (
            "has_kernel_stable_face_id"
            if any(relation.type == "has_kernel_stable_face_id" for relation in graph.relations)
            else "selected_by"
        )
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q2:selected_face",
                target_type="face",
                clauses=[
                    Clause(
                        id="stable_selector",
                        kind="property_equals",
                        metric="stable_selector",
                        value=selector_text,
                    ),
                    Clause(
                        id="has_selector",
                        kind="has_relation",
                        relation=selector_relation,
                        target_type="selector",
                    ),
                ],
                hop_count=2,
                difficulty="bridge",
            )
        )
    kernel_faces_with_bbox_z = [
        face
        for face in _nodes_with_numeric_measurement(graph, faces, "bbox_max_z")
        if any(
            relation.source_id == face.id and relation.type == "has_kernel_stable_face_id"
            for relation in graph.relations
        )
    ]
    if len(kernel_faces_with_bbox_z) >= 2 and _has_unique_extreme(graph, kernel_faces_with_bbox_z, "bbox_max_z", "argmax"):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:highest_kernel_selected_face",
                target_type="face",
                clauses=[
                    Clause(
                        id="has_kernel_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_face_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_selected_face_bbox",
                        kind="has_measurement",
                        metric="bbox_max_z",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="bbox_max_z",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    kernel_faces_with_center_distance = [
        face
        for face in _nodes_with_numeric_measurement(graph, faces, "distance_to_origin")
        if any(
            relation.source_id == face.id and relation.type == "has_kernel_stable_face_id"
            for relation in graph.relations
        )
    ]
    if (
        len(kernel_faces_with_center_distance) >= 2
        and _has_unique_extreme(
            graph,
            kernel_faces_with_center_distance,
            "distance_to_origin",
            "argmin",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q4:nearest_kernel_selected_face_center_to_origin",
                target_type="face",
                clauses=[
                    Clause(
                        id="has_kernel_face_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_face_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_origin_distance_relation",
                        kind="has_relation",
                        relation="distance_to",
                        target_type="origin",
                    ),
                    Clause(
                        id="has_face_center_distance",
                        kind="has_measurement",
                        metric="distance_to_origin",
                    ),
                ],
                aggregation="argmin",
                aggregation_metric="distance_to_origin",
                hop_count=4,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    kernel_faces_with_area = [
        face
        for face in _nodes_with_numeric_measurement(graph, faces, "face_area")
        if any(
            relation.source_id == face.id and relation.type == "has_kernel_stable_face_id"
            for relation in graph.relations
        )
    ]
    if (
        len(kernel_faces_with_area) >= 2
        and _has_unique_extreme(
            graph,
            kernel_faces_with_area,
            "face_area",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q5:largest_kernel_selected_face_area",
                target_type="face",
                clauses=[
                    Clause(
                        id="has_kernel_face_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_face_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_face_area",
                        kind="has_measurement",
                        metric="face_area",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="face_area",
                hop_count=4,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    equal_area_faces = _largest_equal_value_group(graph, kernel_faces_with_area, "face_area")
    if (
        len(equal_area_faces) >= 2
        and _has_unique_extreme(
            graph,
            equal_area_faces,
            "bbox_max_z",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q6:highest_equal_area_kernel_selected_face",
                target_type="face",
                clauses=[
                    Clause(
                        id="has_kernel_face_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_face_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_face_area_value",
                        kind="has_measurement",
                        metric="face_area",
                        value=_measurement_bucket_value(graph, equal_area_faces[0].id, "face_area"),
                    ),
                    Clause(
                        id="has_face_bbox_z",
                        kind="has_measurement",
                        metric="bbox_max_z",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="bbox_max_z",
                hop_count=4,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    equal_center_z_faces = _largest_equal_value_group(graph, kernel_faces_with_center_distance, "coordinate_z")
    if (
        len(equal_center_z_faces) >= 2
        and _has_unique_extreme(
            graph,
            equal_center_z_faces,
            "distance_to_origin",
            "argmin",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q17:nearest_equal_center_z_kernel_selected_face",
                target_type="face",
                clauses=[
                    Clause(
                        id="has_kernel_face_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_face_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_face_center_z_value",
                        kind="has_measurement",
                        metric="coordinate_z",
                        value=_measurement_bucket_value(graph, equal_center_z_faces[0].id, "coordinate_z"),
                    ),
                    Clause(
                        id="has_face_center_distance",
                        kind="has_measurement",
                        metric="distance_to_origin",
                    ),
                ],
                aggregation="argmin",
                aggregation_metric="distance_to_origin",
                hop_count=4,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    z_flat_positive_kernel_faces = [
        face
        for face in kernel_faces_with_bbox_z
        if any(relation.source_id == face.id and relation.type == "opposite_to" for relation in graph.relations)
        and any(relation.source_id == face.id and relation.type == "adjacent_to" for relation in graph.relations)
        and any(relation.source_id == face.id and relation.type == "perpendicular_to" for relation in graph.relations)
        and isinstance(_measurement_value(graph, face.id, "bbox_span_z"), (int, float))
        and _measurement_value(graph, face.id, "bbox_span_z") < GEOMETRY_MARGIN_EPSILON
        and isinstance(_measurement_value(graph, face.id, "bbox_max_x"), (int, float))
        and _measurement_value(graph, face.id, "bbox_max_x") > GEOMETRY_MARGIN_EPSILON
    ]
    if (
        len(z_flat_positive_kernel_faces) >= 2
        and _has_unique_extreme(
            graph,
            z_flat_positive_kernel_faces,
            "bbox_max_z",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q7:highest_positive_x_flat_opposite_adjacent_perpendicular_kernel_face",
                target_type="face",
                clauses=[
                    Clause(
                        id="has_kernel_face_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_face_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_opposite_face_relation",
                        kind="has_relation",
                        relation="opposite_to",
                        target_type="face",
                    ),
                    Clause(
                        id="has_adjacent_face_relation",
                        kind="has_relation",
                        relation="adjacent_to",
                        target_type="face",
                    ),
                    Clause(
                        id="has_perpendicular_face_relation",
                        kind="has_relation",
                        relation="perpendicular_to",
                        target_type="face",
                    ),
                    Clause(
                        id="flat_in_global_z",
                        kind="metric_compare",
                        metric="bbox_span_z",
                        operator="<",
                        value=GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="positive_x_extent",
                        kind="metric_compare",
                        metric="bbox_max_x",
                        operator=">",
                        value=GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="has_face_bbox_z",
                        kind="has_measurement",
                        metric="bbox_max_z",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="bbox_max_z",
                hop_count=6,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    kernel_selectors_with_counts = [
        selector
        for selector in _nodes_with_numeric_measurement(graph, selectors, "selected_count")
        if any(
            relation.source_id == selector.id and relation.type == "has_kernel_stable_face_id"
            for relation in graph.relations
        )
    ]
    if (
        len(kernel_selectors_with_counts) >= 2
        and _has_unique_extreme(graph, kernel_selectors_with_counts, "selected_count", "argmax")
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_kernel_selector_count",
                target_type="selector",
                clauses=[
                    Clause(
                        id="has_kernel_selected_faces",
                        kind="has_relation",
                        relation="has_kernel_stable_face_id",
                        target_type="face",
                    ),
                    Clause(
                        id="has_selected_count",
                        kind="has_measurement",
                        metric="selected_count",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="selected_count",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    kernel_edges_with_bbox_z = [
        edge
        for edge in _nodes_with_numeric_measurement(graph, edges, "bbox_max_z")
        if any(
            relation.source_id == edge.id and relation.type == "has_kernel_stable_edge_id"
            for relation in graph.relations
        )
    ]
    if len(kernel_edges_with_bbox_z) >= 2 and _has_unique_extreme(graph, kernel_edges_with_bbox_z, "bbox_max_z", "argmax"):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:highest_kernel_selected_edge",
                target_type="edge",
                clauses=[
                    Clause(
                        id="has_kernel_edge_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_edge_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_selected_edge_bbox",
                        kind="has_measurement",
                        metric="bbox_max_z",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="bbox_max_z",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    negative_y_x_edges = [
        edge
        for edge in kernel_edges_with_bbox_z
        if isinstance(_measurement_value(graph, edge.id, "bbox_span_x"), (int, float))
        and _measurement_value(graph, edge.id, "bbox_span_x") > GEOMETRY_MARGIN_EPSILON
        and isinstance(_measurement_value(graph, edge.id, "bbox_max_y"), (int, float))
        and _measurement_value(graph, edge.id, "bbox_max_y") < -GEOMETRY_MARGIN_EPSILON
    ]
    if (
        len(negative_y_x_edges) >= 2
        and _has_unique_extreme(
            graph,
            negative_y_x_edges,
            "bbox_max_z",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q8:highest_negative_y_x_span_opposite_intersecting_adjacent_perpendicular_kernel_edge",
                target_type="edge",
                clauses=[
                    Clause(
                        id="has_kernel_edge_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_edge_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_perpendicular_edge_relation",
                        kind="has_relation",
                        relation="perpendicular_to",
                        target_type="edge",
                    ),
                    Clause(
                        id="has_adjacent_edge_relation",
                        kind="has_relation",
                        relation="adjacent_to",
                        target_type="edge",
                    ),
                    Clause(
                        id="has_intersection_edge_relation",
                        kind="has_relation",
                        relation="intersects",
                        target_type="edge",
                    ),
                    Clause(
                        id="has_opposite_edge_relation",
                        kind="has_relation",
                        relation="opposite_to",
                        target_type="edge",
                    ),
                    Clause(
                        id="has_x_span",
                        kind="metric_compare",
                        metric="bbox_span_x",
                        operator=">",
                        value=GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="on_negative_y_side",
                        kind="metric_compare",
                        metric="bbox_max_y",
                        operator="<",
                        value=-GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="has_edge_bbox_z",
                        kind="has_measurement",
                        metric="bbox_max_z",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="bbox_max_z",
                hop_count=6,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    positive_z_x_span_midpoint_edges = [
        edge
        for edge in _nodes_with_numeric_measurement(graph, kernel_edges_with_bbox_z, "midpoint_y")
        if any(
            relation.source_id == edge.id and relation.type == "distance_to"
            for relation in graph.relations
        )
        and isinstance(_measurement_value(graph, edge.id, "midpoint_distance_to_origin"), (int, float))
        and isinstance(_measurement_value(graph, edge.id, "bbox_span_x"), (int, float))
        and _measurement_value(graph, edge.id, "bbox_span_x") > GEOMETRY_MARGIN_EPSILON
        and isinstance(_measurement_value(graph, edge.id, "midpoint_z"), (int, float))
        and _measurement_value(graph, edge.id, "midpoint_z") > GEOMETRY_MARGIN_EPSILON
    ]
    if (
        len(positive_z_x_span_midpoint_edges) >= 2
        and _has_unique_extreme(
            graph,
            positive_z_x_span_midpoint_edges,
            "midpoint_y",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q9:highest_y_positive_z_x_span_kernel_edge_midpoint",
                target_type="edge",
                clauses=[
                    Clause(
                        id="has_kernel_edge_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_edge_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_origin_distance_relation",
                        kind="has_relation",
                        relation="distance_to",
                        target_type="origin",
                    ),
                    Clause(
                        id="has_midpoint_distance",
                        kind="has_measurement",
                        metric="midpoint_distance_to_origin",
                    ),
                    Clause(
                        id="has_x_span",
                        kind="metric_compare",
                        metric="bbox_span_x",
                        operator=">",
                        value=GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="positive_midpoint_z",
                        kind="metric_compare",
                        metric="midpoint_z",
                        operator=">",
                        value=GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="has_midpoint_y",
                        kind="has_measurement",
                        metric="midpoint_y",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="midpoint_y",
                hop_count=6,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    positive_z_short_edges = [
        edge
        for edge in _nodes_with_numeric_measurement(graph, kernel_edges_with_bbox_z, "edge_length")
        if isinstance(_measurement_value(graph, edge.id, "midpoint_z"), (int, float))
        and _measurement_value(graph, edge.id, "midpoint_z") > GEOMETRY_MARGIN_EPSILON
        and isinstance(_measurement_value(graph, edge.id, "edge_length"), (int, float))
        and isinstance(_measurement_value(graph, edge.id, "midpoint_distance_to_origin"), (int, float))
        and _measurement_value(graph, edge.id, "edge_length")
        < _measurement_value(graph, edge.id, "midpoint_distance_to_origin")
        and isinstance(_measurement_value(graph, edge.id, "midpoint_x"), (int, float))
    ]
    if (
        len(positive_z_short_edges) >= 2
        and _has_unique_extreme(
            graph,
            positive_z_short_edges,
            "midpoint_x",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q10:rightmost_short_positive_z_kernel_edge",
                target_type="edge",
                clauses=[
                    Clause(
                        id="has_kernel_edge_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_edge_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_edge_length",
                        kind="has_measurement",
                        metric="edge_length",
                    ),
                    Clause(
                        id="positive_midpoint_z",
                        kind="metric_compare",
                        metric="midpoint_z",
                        operator=">",
                        value=GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="edge_length_less_than_midpoint_distance",
                        kind="metric_ratio_compare",
                        metric="edge_length",
                        operator="<",
                        value=1.0,
                        reference_metric="midpoint_distance_to_origin",
                    ),
                    Clause(
                        id="has_midpoint_x",
                        kind="has_measurement",
                        metric="midpoint_x",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="midpoint_x",
                hop_count=6,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    longer_positive_z_edges = [
        edge
        for edge in _nodes_with_numeric_measurement(graph, kernel_edges_with_bbox_z, "midpoint_y")
        if any(
            relation.source_id == edge.id and relation.type == "longer_than"
            for relation in graph.relations
        )
        and isinstance(_measurement_value(graph, edge.id, "midpoint_z"), (int, float))
        and _measurement_value(graph, edge.id, "midpoint_z") > GEOMETRY_MARGIN_EPSILON
    ]
    if (
        len(longer_positive_z_edges) >= 2
        and _has_unique_extreme(
            graph,
            longer_positive_z_edges,
            "midpoint_y",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q11:frontmost_longer_positive_z_kernel_edge",
                target_type="edge",
                clauses=[
                    Clause(
                        id="has_kernel_edge_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_edge_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="longer_than_another_kernel_edge",
                        kind="has_relation",
                        relation="longer_than",
                        target_type="edge",
                    ),
                    Clause(
                        id="positive_midpoint_z",
                        kind="metric_compare",
                        metric="midpoint_z",
                        operator=">",
                        value=GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="has_midpoint_y",
                        kind="has_measurement",
                        metric="midpoint_y",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="midpoint_y",
                hop_count=6,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    equal_length_edges = _largest_equal_value_group(
        graph,
        _nodes_with_numeric_measurement(graph, kernel_edges_with_bbox_z, "edge_length"),
        "edge_length",
    )
    if (
        len(equal_length_edges) >= 2
        and len(_nodes_with_numeric_measurement(graph, equal_length_edges, "midpoint_y")) >= 2
        and _has_unique_extreme(
            graph,
            equal_length_edges,
            "midpoint_y",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q14:frontmost_equal_length_kernel_edge",
                target_type="edge",
                clauses=[
                    Clause(
                        id="has_kernel_edge_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_edge_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_edge_length_value",
                        kind="has_measurement",
                        metric="edge_length",
                        value=_measurement_bucket_value(graph, equal_length_edges[0].id, "edge_length"),
                    ),
                    Clause(
                        id="has_midpoint_y",
                        kind="has_measurement",
                        metric="midpoint_y",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="midpoint_y",
                hop_count=4,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    reference_feature = _reference_feature_for_unique_nearest(
        graph,
        features,
        equal_length_edges,
        target_point_metric="midpoint",
        reference_point_metric="centroid",
    )
    if reference_feature is not None:
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q16:nearest_equal_length_edge_to_reference_feature_centroid",
                target_type="edge",
                clauses=[
                    Clause(
                        id="has_kernel_edge_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_edge_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_edge_length_value",
                        kind="has_measurement",
                        metric="edge_length",
                        value=_measurement_bucket_value(graph, equal_length_edges[0].id, "edge_length"),
                    ),
                    Clause(
                        id="reference_feature_volume_and_centroid",
                        kind="reference_measurement",
                        metric=REFERENCE_FEATURE_DISTANCE_METRIC,
                        value=_reference_feature_prompt_value(graph, reference_feature),
                    ),
                    Clause(
                        id="has_edge_midpoint_for_reference_distance",
                        kind="has_measurement",
                        metric="midpoint",
                    ),
                ],
                aggregation="argmin",
                aggregation_metric=REFERENCE_FEATURE_DISTANCE_METRIC,
                hop_count=5,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    equal_midpoint_distance_edges = _largest_equal_value_group(
        graph,
        _nodes_with_numeric_measurement(graph, kernel_edges_with_bbox_z, "midpoint_y"),
        "midpoint_distance_to_origin",
    )
    if (
        len(equal_midpoint_distance_edges) >= 2
        and _has_unique_extreme(
            graph,
            equal_midpoint_distance_edges,
            "midpoint_y",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q15:frontmost_equal_midpoint_distance_kernel_edge",
                target_type="edge",
                clauses=[
                    Clause(
                        id="has_kernel_edge_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_edge_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_midpoint_distance_value",
                        kind="has_measurement",
                        metric="midpoint_distance_to_origin",
                        value=_measurement_bucket_value(
                            graph,
                            equal_midpoint_distance_edges[0].id,
                            "midpoint_distance_to_origin",
                        ),
                    ),
                    Clause(
                        id="has_midpoint_y",
                        kind="has_measurement",
                        metric="midpoint_y",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="midpoint_y",
                hop_count=4,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    same_length_longer_positive_z_edges = [
        edge
        for edge in _nodes_with_numeric_measurement(graph, kernel_edges_with_bbox_z, "midpoint_y")
        if any(
            relation.source_id == edge.id and relation.type == "same_length_as"
            for relation in graph.relations
        )
        and any(
            relation.source_id == edge.id and relation.type == "longer_than"
            for relation in graph.relations
        )
        and isinstance(_measurement_value(graph, edge.id, "midpoint_z"), (int, float))
        and _measurement_value(graph, edge.id, "midpoint_z") > GEOMETRY_MARGIN_EPSILON
    ]
    if (
        len(same_length_longer_positive_z_edges) >= 2
        and _has_unique_extreme(
            graph,
            same_length_longer_positive_z_edges,
            "midpoint_y",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q12:frontmost_same_length_longer_positive_z_kernel_edge",
                target_type="edge",
                clauses=[
                    Clause(
                        id="has_kernel_edge_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_edge_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="same_length_as_another_kernel_edge",
                        kind="has_relation",
                        relation="same_length_as",
                        target_type="edge",
                    ),
                    Clause(
                        id="longer_than_another_kernel_edge",
                        kind="has_relation",
                        relation="longer_than",
                        target_type="edge",
                    ),
                    Clause(
                        id="positive_midpoint_z",
                        kind="metric_compare",
                        metric="midpoint_z",
                        operator=">",
                        value=GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="has_midpoint_y",
                        kind="has_measurement",
                        metric="midpoint_y",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="midpoint_y",
                hop_count=6,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    shorter_positive_z_edges = [
        edge
        for edge in _nodes_with_numeric_measurement(graph, kernel_edges_with_bbox_z, "midpoint_x")
        if any(
            relation.source_id == edge.id and relation.type == "shorter_than"
            for relation in graph.relations
        )
        and isinstance(_measurement_value(graph, edge.id, "midpoint_z"), (int, float))
        and _measurement_value(graph, edge.id, "midpoint_z") > GEOMETRY_MARGIN_EPSILON
    ]
    if (
        len(shorter_positive_z_edges) >= 2
        and _has_unique_extreme(
            graph,
            shorter_positive_z_edges,
            "midpoint_x",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q13:rightmost_shorter_positive_z_kernel_edge",
                target_type="edge",
                clauses=[
                    Clause(
                        id="has_kernel_edge_selector_identity",
                        kind="has_relation",
                        relation="has_kernel_stable_edge_id",
                        target_type="selector",
                    ),
                    Clause(
                        id="shorter_than_another_kernel_edge",
                        kind="has_relation",
                        relation="shorter_than",
                        target_type="edge",
                    ),
                    Clause(
                        id="positive_midpoint_z",
                        kind="metric_compare",
                        metric="midpoint_z",
                        operator=">",
                        value=GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="has_midpoint_x",
                        kind="has_measurement",
                        metric="midpoint_x",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="midpoint_x",
                hop_count=6,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    positive_x_negative_y_endpoints = [
        endpoint
        for endpoint in _nodes_with_numeric_measurement(graph, edge_endpoints, "coordinate_z")
        if any(
            relation.source_id == endpoint.id and relation.type == "endpoint_of"
            for relation in graph.relations
        )
        and isinstance(_measurement_value(graph, endpoint.id, "coordinate_x"), (int, float))
        and _measurement_value(graph, endpoint.id, "coordinate_x") > GEOMETRY_MARGIN_EPSILON
        and isinstance(_measurement_value(graph, endpoint.id, "coordinate_y"), (int, float))
        and _measurement_value(graph, endpoint.id, "coordinate_y") < -GEOMETRY_MARGIN_EPSILON
    ]
    if (
        len(positive_x_negative_y_endpoints) >= 2
        and _has_unique_extreme(
            graph,
            positive_x_negative_y_endpoints,
            "coordinate_z",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q5:highest_positive_x_negative_y_contained_kernel_edge_endpoint",
                target_type="edge_endpoint",
                clauses=[
                    Clause(
                        id="endpoint_of_kernel_selected_edge",
                        kind="has_relation",
                        relation="endpoint_of",
                        target_type="edge",
                    ),
                    Clause(
                        id="contained_in_kernel_selected_edge",
                        kind="has_relation",
                        relation="contained_in",
                        target_type="edge",
                    ),
                    Clause(
                        id="has_origin_distance_relation",
                        kind="has_relation",
                        relation="distance_to",
                        target_type="origin",
                    ),
                    Clause(
                        id="positive_x_endpoint",
                        kind="metric_compare",
                        metric="coordinate_x",
                        operator=">",
                        value=GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="negative_y_endpoint",
                        kind="metric_compare",
                        metric="coordinate_y",
                        operator="<",
                        value=-GEOMETRY_MARGIN_EPSILON,
                    ),
                    Clause(
                        id="has_endpoint_z",
                        kind="has_measurement",
                        metric="coordinate_z",
                    ),
                    Clause(
                        id="has_endpoint_distance",
                        kind="has_measurement",
                        metric="distance_to_origin",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="coordinate_z",
                hop_count=5,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    equal_z_endpoints = _largest_equal_value_group(
        graph,
        _nodes_with_numeric_measurement(graph, edge_endpoints, "distance_to_origin"),
        "coordinate_z",
    )
    if (
        len(equal_z_endpoints) >= 2
        and _has_unique_extreme(
            graph,
            equal_z_endpoints,
            "distance_to_origin",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q6:farthest_equal_z_kernel_edge_endpoint",
                target_type="edge_endpoint",
                clauses=[
                    Clause(
                        id="endpoint_of_kernel_selected_edge",
                        kind="has_relation",
                        relation="endpoint_of",
                        target_type="edge",
                    ),
                    Clause(
                        id="has_endpoint_z_value",
                        kind="has_measurement",
                        metric="coordinate_z",
                        value=_measurement_bucket_value(graph, equal_z_endpoints[0].id, "coordinate_z"),
                    ),
                    Clause(
                        id="has_endpoint_distance",
                        kind="has_measurement",
                        metric="distance_to_origin",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="distance_to_origin",
                hop_count=4,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    kernel_edge_selectors_with_counts = [
        selector
        for selector in _nodes_with_numeric_measurement(graph, selectors, "selected_count")
        if any(
            relation.source_id == selector.id and relation.type == "has_kernel_stable_edge_id"
            for relation in graph.relations
        )
    ]
    if (
        len(kernel_edge_selectors_with_counts) >= 2
        and _has_unique_extreme(graph, kernel_edge_selectors_with_counts, "selected_count", "argmax")
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_kernel_edge_selector_count",
                target_type="selector",
                clauses=[
                    Clause(
                        id="has_kernel_selected_edges",
                        kind="has_relation",
                        relation="has_kernel_stable_edge_id",
                        target_type="edge",
                    ),
                    Clause(
                        id="has_selected_edge_count",
                        kind="has_measurement",
                        metric="selected_count",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="selected_count",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    if paths:
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q2:path_nearest_origin",
                target_type="path",
                clauses=[
                    Clause(
                        id="has_initial_tangent",
                        kind="has_relation",
                        relation="has_path_tangent",
                        target_type="path",
                    ),
                    Clause(
                        id="has_nearest_origin_distance",
                        kind="has_measurement",
                        metric="nearest_point_distance_to_origin",
                    ),
                ],
                aggregation="argmin",
                aggregation_metric="nearest_point_distance_to_origin",
                hop_count=2,
                difficulty="bridge",
            )
        )
    path_points_with_distance = _nodes_with_numeric_measurement(graph, path_points, "distance_to_origin")
    if (
        len(path_points_with_distance) >= 2
        and _has_unique_extreme(graph, path_points_with_distance, "distance_to_origin", "argmin")
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:nearest_path_point_to_origin",
                target_type="path_point",
                clauses=[
                    Clause(
                        id="point_on_visible_path",
                        kind="has_relation",
                        relation="point_on_path",
                        target_type="path",
                    ),
                    Clause(
                        id="has_distance_to_origin",
                        kind="has_measurement",
                        metric="distance_to_origin",
                    ),
                ],
                aggregation="argmin",
                aggregation_metric="distance_to_origin",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    path_points_with_z = _nodes_with_numeric_measurement(graph, path_points, "coordinate_z")
    if (
        len(path_points_with_z) >= 2
        and _has_unique_extreme(graph, path_points_with_z, "coordinate_z", "argmax")
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:highest_path_point",
                target_type="path_point",
                clauses=[
                    Clause(
                        id="point_on_visible_path",
                        kind="has_relation",
                        relation="point_on_path",
                        target_type="path",
                    ),
                    Clause(
                        id="has_path_point_z",
                        kind="has_measurement",
                        metric="coordinate_z",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="coordinate_z",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    path_segments_with_length = _nodes_with_numeric_measurement(graph, path_segments, "segment_length")
    if (
        len(path_segments_with_length) >= 2
        and _has_unique_extreme(graph, path_segments_with_length, "segment_length", "argmax")
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:longest_path_segment",
                target_type="path_segment",
                clauses=[
                    Clause(
                        id="segment_on_visible_path",
                        kind="has_relation",
                        relation="segment_on_path",
                        target_type="path",
                    ),
                    Clause(
                        id="has_segment_length",
                        kind="has_measurement",
                        metric="segment_length",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="segment_length",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    if selectors and any(relation.type == "same_selected_face_as" for relation in graph.relations):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:latest_repeated_selector",
                target_type="selector",
                clauses=[
                    Clause(
                        id="same_face_as_another_selector",
                        kind="has_relation",
                        relation="same_selected_face_as",
                        target_type="selector",
                    ),
                    Clause(
                        id="has_selector_operation_index",
                        kind="has_measurement",
                        metric="operation_index",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="operation_index",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    if len(_nodes_with_numeric_measurement(graph, features, "volume")) >= 2:
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q2:largest_compiled_volume_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_compiled_volume",
                        kind="has_measurement",
                        metric="volume",
                    ),
                    Clause(
                        id="has_compiled_bbox_height",
                        kind="has_measurement",
                        metric="bbox_span_z",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="volume",
                hop_count=2,
                difficulty="bridge",
            )
        )
        equal_volume_features = _largest_equal_value_group(
            graph,
            _nodes_with_numeric_measurement(graph, features, "centroid_z"),
            "volume",
        )
        if (
            len(equal_volume_features) >= 2
            and _has_unique_extreme(
                graph,
                equal_volume_features,
                "centroid_z",
                "argmax",
                min_margin=GEOMETRY_MARGIN_EPSILON,
            )
        ):
            queries.append(
                QueryProgram(
                    query_id=f"{graph.graph_id}:q4:highest_equal_volume_feature",
                    target_type="feature",
                    clauses=[
                        Clause(
                            id="has_compiled_volume_value",
                            kind="has_measurement",
                            metric="volume",
                            value=_measurement_bucket_value(graph, equal_volume_features[0].id, "volume"),
                        ),
                        Clause(
                            id="has_compiled_centroid",
                            kind="has_measurement",
                            metric="centroid_z",
                        ),
                    ],
                    aggregation="argmax",
                    aggregation_metric="centroid_z",
                    hop_count=3,
                    difficulty="cad_browsecomp",
                    min_individual_clause_candidates=2,
                )
            )
        equal_centroid_z_features = _largest_equal_value_group(
            graph,
            _nodes_with_numeric_measurement(graph, features, "volume"),
            "centroid_z",
        )
        if (
            len(equal_centroid_z_features) >= 2
            and _has_unique_extreme(
                graph,
                equal_centroid_z_features,
                "volume",
                "argmax",
                min_margin=GEOMETRY_MARGIN_EPSILON,
            )
        ):
            queries.append(
                QueryProgram(
                    query_id=f"{graph.graph_id}:q5:largest_equal_centroid_height_feature",
                    target_type="feature",
                    clauses=[
                        Clause(
                            id="has_compiled_centroid_value",
                            kind="has_measurement",
                            metric="centroid_z",
                            value=_measurement_bucket_value(
                                graph,
                                equal_centroid_z_features[0].id,
                                "centroid_z",
                            ),
                        ),
                        Clause(
                            id="has_compiled_volume",
                            kind="has_measurement",
                            metric="volume",
                        ),
                    ],
                    aggregation="argmax",
                    aggregation_metric="volume",
                    hop_count=3,
                    difficulty="cad_browsecomp",
                    min_individual_clause_candidates=2,
                )
            )
        equal_bbox_height_features = _largest_equal_value_group(
            graph,
            _nodes_with_numeric_measurement(graph, features, "volume"),
            "bbox_span_z",
        )
        if (
            len(equal_bbox_height_features) >= 2
            and _has_unique_extreme(
                graph,
                equal_bbox_height_features,
                "volume",
                "argmax",
                min_margin=GEOMETRY_MARGIN_EPSILON,
            )
        ):
            queries.append(
                QueryProgram(
                    query_id=f"{graph.graph_id}:q6:largest_equal_bbox_height_feature",
                    target_type="feature",
                    clauses=[
                        Clause(
                            id="has_compiled_bbox_height_value",
                            kind="has_measurement",
                            metric="bbox_span_z",
                            value=_measurement_bucket_value(
                                graph,
                                equal_bbox_height_features[0].id,
                                "bbox_span_z",
                            ),
                        ),
                        Clause(
                            id="has_compiled_volume",
                            kind="has_measurement",
                            metric="volume",
                        ),
                    ],
                    aggregation="argmax",
                    aggregation_metric="volume",
                    hop_count=3,
                    difficulty="cad_browsecomp",
                    min_individual_clause_candidates=2,
                )
            )
        equal_centroid_x_features = _largest_equal_value_group(
            graph,
            _nodes_with_numeric_measurement(graph, features, "volume"),
            "centroid_x",
        )
        if (
            len(equal_centroid_x_features) >= 2
            and _has_unique_extreme(
                graph,
                equal_centroid_x_features,
                "volume",
                "argmax",
                min_margin=GEOMETRY_MARGIN_EPSILON,
            )
        ):
            queries.append(
                QueryProgram(
                    query_id=f"{graph.graph_id}:q7:largest_equal_centroid_x_feature",
                    target_type="feature",
                    clauses=[
                        Clause(
                            id="has_compiled_centroid_x_value",
                            kind="has_measurement",
                            metric="centroid_x",
                            value=_measurement_bucket_value(
                                graph,
                                equal_centroid_x_features[0].id,
                                "centroid_x",
                            ),
                        ),
                        Clause(
                            id="has_compiled_volume",
                            kind="has_measurement",
                            metric="volume",
                        ),
                    ],
                    aggregation="argmax",
                    aggregation_metric="volume",
                    hop_count=3,
                    difficulty="cad_browsecomp",
                    min_individual_clause_candidates=2,
                )
            )
        equal_centroid_y_features = _largest_equal_value_group(
            graph,
            _nodes_with_numeric_measurement(graph, features, "volume"),
            "centroid_y",
        )
        if (
            len(equal_centroid_y_features) >= 2
            and _has_unique_extreme(
                graph,
                equal_centroid_y_features,
                "volume",
                "argmax",
                min_margin=GEOMETRY_MARGIN_EPSILON,
            )
        ):
            queries.append(
                QueryProgram(
                    query_id=f"{graph.graph_id}:q8:largest_equal_centroid_y_feature",
                    target_type="feature",
                    clauses=[
                        Clause(
                            id="has_compiled_centroid_y_value",
                            kind="has_measurement",
                            metric="centroid_y",
                            value=_measurement_bucket_value(
                                graph,
                                equal_centroid_y_features[0].id,
                                "centroid_y",
                            ),
                        ),
                        Clause(
                            id="has_compiled_volume",
                            kind="has_measurement",
                            metric="volume",
                        ),
                    ],
                    aggregation="argmax",
                    aggregation_metric="volume",
                    hop_count=3,
                    difficulty="cad_browsecomp",
                    min_individual_clause_candidates=2,
                )
            )
    centroid_features = _nodes_with_numeric_measurement(graph, features, "centroid_z")
    if (
        len(centroid_features) >= 2
        and _has_unique_extreme(
            graph,
            centroid_features,
            "centroid_z",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:highest_centroid_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_compiled_centroid",
                        kind="has_measurement",
                        metric="centroid_z",
                    ),
                    Clause(
                        id="has_compiled_volume_for_centroid",
                        kind="has_measurement",
                        metric="volume",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="centroid_z",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    topology_face_features = _nodes_with_numeric_measurement(graph, features, "topology_faces")
    if (
        len(topology_face_features) >= 2
        and _has_unique_extreme(graph, topology_face_features, "topology_faces", "argmax")
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_compiled_face_count_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_compiled_face_count",
                        kind="has_measurement",
                        metric="topology_faces",
                    ),
                    Clause(
                        id="has_volume_for_face_count",
                        kind="has_measurement",
                        metric="volume",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="topology_faces",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    positive_volume_delta_features = [
        feature
        for feature in _nodes_with_numeric_measurement(graph, features, "signed_volume_delta")
        if _measurement_value(graph, feature.id, "signed_volume_delta") > GEOMETRY_MARGIN_EPSILON
    ]
    if (
        len(positive_volume_delta_features) >= 2
        and _has_unique_extreme(
            graph,
            positive_volume_delta_features,
            "signed_volume_delta",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_positive_volume_delta_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_positive_volume_delta",
                        kind="metric_compare",
                        metric="signed_volume_delta",
                        operator=">",
                        value=0.0,
                    ),
                    Clause(
                        id="has_bbox_delta",
                        kind="has_measurement",
                        metric="bbox_delta_span_z",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="signed_volume_delta",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    removed_volume_delta_features = [
        feature
        for feature in _nodes_with_numeric_measurement(graph, features, "signed_volume_delta")
        if _measurement_value(graph, feature.id, "signed_volume_delta") < -GEOMETRY_MARGIN_EPSILON
    ]
    if (
        len(removed_volume_delta_features) >= 2
        and _has_unique_extreme(
            graph,
            removed_volume_delta_features,
            "signed_volume_delta",
            "argmin",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_removed_volume_delta_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_negative_volume_delta",
                        kind="metric_compare",
                        metric="signed_volume_delta",
                        operator="<",
                        value=0.0,
                    ),
                    Clause(
                        id="has_removed_volume_magnitude",
                        kind="has_measurement",
                        metric="volume_delta_magnitude",
                    ),
                ],
                aggregation="argmin",
                aggregation_metric="signed_volume_delta",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    bbox_delta_features = [
        feature
        for feature in _nodes_with_numeric_measurement(graph, features, "bbox_delta_span_z")
        if _measurement_value(graph, feature.id, "bbox_delta_span_z") > GEOMETRY_MARGIN_EPSILON
        and isinstance(_measurement_value(graph, feature.id, "signed_volume_delta"), (int, float))
    ]
    if (
        len(bbox_delta_features) >= 2
        and _has_unique_extreme(
            graph,
            bbox_delta_features,
            "bbox_delta_span_z",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_bbox_height_delta_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_positive_bbox_height_delta",
                        kind="metric_compare",
                        metric="bbox_delta_span_z",
                        operator=">",
                        value=0.0,
                    ),
                    Clause(
                        id="has_volume_delta_for_bbox_delta",
                        kind="has_measurement",
                        metric="signed_volume_delta",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="bbox_delta_span_z",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    bbox_expansion_features = [
        feature
        for feature in _nodes_with_numeric_measurement(graph, features, "bbox_delta_max_span")
        if _measurement_value(graph, feature.id, "bbox_delta_max_span") > GEOMETRY_MARGIN_EPSILON
        and isinstance(_measurement_value(graph, feature.id, "signed_volume_delta"), (int, float))
    ]
    if (
        len(bbox_expansion_features) >= 2
        and _has_unique_extreme(
            graph,
            bbox_expansion_features,
            "bbox_delta_max_span",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_bbox_expansion_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_bbox_expansion",
                        kind="metric_compare",
                        metric="bbox_delta_max_span",
                        operator=">",
                        value=0.0,
                    ),
                    Clause(
                        id="has_volume_delta_for_bbox_expansion",
                        kind="has_measurement",
                        metric="signed_volume_delta",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="bbox_delta_max_span",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    bbox_min_z_delta_features = [
        feature
        for feature in _nodes_with_numeric_measurement(graph, features, "bbox_delta_min_z")
        if _measurement_value(graph, feature.id, "bbox_delta_min_z") > GEOMETRY_MARGIN_EPSILON
        and isinstance(_measurement_value(graph, feature.id, "signed_volume_delta"), (int, float))
    ]
    if (
        len(bbox_min_z_delta_features) >= 2
        and _has_unique_extreme(
            graph,
            bbox_min_z_delta_features,
            "bbox_delta_min_z",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_bbox_min_z_delta_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_positive_bbox_min_z_delta",
                        kind="metric_compare",
                        metric="bbox_delta_min_z",
                        operator=">",
                        value=0.0,
                    ),
                    Clause(
                        id="has_volume_delta_for_bbox_min_z_delta",
                        kind="has_measurement",
                        metric="signed_volume_delta",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="bbox_delta_min_z",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    centroid_delta_features = [
        feature
        for feature in _nodes_with_numeric_measurement(graph, features, "centroid_delta_z")
        if _measurement_value(graph, feature.id, "centroid_delta_z") > GEOMETRY_MARGIN_EPSILON
    ]
    if (
        len(centroid_delta_features) >= 2
        and _has_unique_extreme(
            graph,
            centroid_delta_features,
            "centroid_delta_z",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_upward_centroid_delta_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_positive_centroid_delta",
                        kind="metric_compare",
                        metric="centroid_delta_z",
                        operator=">",
                        value=0.0,
                    ),
                    Clause(
                        id="has_volume_delta_for_centroid_delta",
                        kind="has_measurement",
                        metric="signed_volume_delta",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="centroid_delta_z",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    centroid_shift_features = [
        feature
        for feature in _nodes_with_numeric_measurement(graph, features, "centroid_delta_magnitude")
        if _measurement_value(graph, feature.id, "centroid_delta_magnitude") > GEOMETRY_MARGIN_EPSILON
        and isinstance(_measurement_value(graph, feature.id, "signed_volume_delta"), (int, float))
    ]
    if (
        len(centroid_shift_features) >= 2
        and _has_unique_extreme(
            graph,
            centroid_shift_features,
            "centroid_delta_magnitude",
            "argmax",
            min_margin=GEOMETRY_MARGIN_EPSILON,
        )
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_centroid_shift_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_centroid_shift",
                        kind="metric_compare",
                        metric="centroid_delta_magnitude",
                        operator=">",
                        value=0.0,
                    ),
                    Clause(
                        id="has_volume_delta_for_centroid_shift",
                        kind="has_measurement",
                        metric="signed_volume_delta",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="centroid_delta_magnitude",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    if len(_nodes_with_numeric_measurement(graph, features, "topology_delta_faces")) >= 2:
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_face_count_delta_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_positive_face_delta",
                        kind="metric_compare",
                        metric="topology_delta_faces",
                        operator=">",
                        value=0.0,
                    ),
                    Clause(
                        id="has_volume_delta",
                        kind="has_measurement",
                        metric="signed_volume_delta",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="topology_delta_faces",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    edge_delta_features = [
        feature
        for feature in _nodes_with_numeric_measurement(graph, features, "topology_delta_edges")
        if _measurement_value(graph, feature.id, "topology_delta_edges") > 0
        and isinstance(_measurement_value(graph, feature.id, "signed_volume_delta"), (int, float))
    ]
    if (
        len(edge_delta_features) >= 2
        and _has_unique_extreme(graph, edge_delta_features, "topology_delta_edges", "argmax")
    ):
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_edge_count_delta_feature",
                target_type="feature",
                clauses=[
                    Clause(
                        id="has_positive_edge_delta",
                        kind="metric_compare",
                        metric="topology_delta_edges",
                        operator=">",
                        value=0.0,
                    ),
                    Clause(
                        id="has_volume_delta_for_edge_delta",
                        kind="has_measurement",
                        metric="signed_volume_delta",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="topology_delta_edges",
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=2,
            )
        )
    if material_regions:
        has_kernel_material = any(relation.type == "has_kernel_material_region_geometry" for relation in graph.relations)
        material_relation = "has_kernel_material_region_geometry" if has_kernel_material else "has_material_region_geometry"
        material_metric = "volume" if has_kernel_material else "centroid_z"
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_added_region",
                target_type="material_region",
                clauses=[
                    Clause(
                        id="has_region_geometry",
                        kind="has_relation",
                        relation=material_relation,
                        target_type="material_region",
                    ),
                    Clause(
                        id=f"has_region_{material_metric}",
                        kind="has_measurement",
                        metric=material_metric,
                    ),
                ],
                aggregation="argmax",
                aggregation_metric=material_metric,
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=1 if has_kernel_material else 3,
            )
        )
        equal_material_regions = _largest_equal_value_group(
            graph,
            _nodes_with_numeric_measurement(graph, material_regions, "centroid_z"),
            "volume",
        )
        if (
            len(equal_material_regions) >= 2
            and _has_unique_extreme(
                graph,
                equal_material_regions,
                "centroid_z",
                "argmax",
                min_margin=GEOMETRY_MARGIN_EPSILON,
            )
        ):
            queries.append(
                QueryProgram(
                    query_id=f"{graph.graph_id}:q4:highest_equal_volume_added_region",
                    target_type="material_region",
                    clauses=[
                        Clause(
                            id="has_region_geometry",
                            kind="has_relation",
                            relation=material_relation,
                            target_type="material_region",
                        ),
                        Clause(
                            id="has_region_volume_value",
                            kind="has_measurement",
                            metric="volume",
                            value=_measurement_bucket_value(graph, equal_material_regions[0].id, "volume"),
                        ),
                        Clause(
                            id="has_region_centroid_z",
                            kind="has_measurement",
                            metric="centroid_z",
                        ),
                    ],
                    aggregation="argmax",
                    aggregation_metric="centroid_z",
                    hop_count=4,
                    difficulty="cad_browsecomp",
                    min_individual_clause_candidates=2,
                )
            )
    if void_regions:
        has_kernel_void = any(relation.type == "has_kernel_void_region_geometry" for relation in graph.relations)
        void_relation = "has_kernel_void_region_geometry" if has_kernel_void else "has_void_region_geometry"
        void_metric = "volume" if has_kernel_void else "operation_index"
        queries.append(
            QueryProgram(
                query_id=f"{graph.graph_id}:q3:largest_removed_region",
                target_type="void_region",
                clauses=[
                    Clause(
                        id="has_void_geometry",
                        kind="has_relation",
                        relation=void_relation,
                        target_type="void_region",
                    ),
                    Clause(
                        id=f"has_void_{void_metric}",
                        kind="has_measurement",
                        metric=void_metric,
                    ),
                ],
                aggregation="argmax",
                aggregation_metric=void_metric,
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=1 if has_kernel_void else 3,
            )
        )
        equal_void_regions = _largest_equal_value_group(
            graph,
            _nodes_with_numeric_measurement(graph, void_regions, "centroid_z"),
            "volume",
        )
        if (
            len(equal_void_regions) >= 2
            and _has_unique_extreme(
                graph,
                equal_void_regions,
                "centroid_z",
                "argmax",
                min_margin=GEOMETRY_MARGIN_EPSILON,
            )
        ):
            queries.append(
                QueryProgram(
                    query_id=f"{graph.graph_id}:q4:highest_equal_volume_removed_region",
                    target_type="void_region",
                    clauses=[
                        Clause(
                            id="has_void_geometry",
                            kind="has_relation",
                            relation=void_relation,
                            target_type="void_region",
                        ),
                        Clause(
                            id="has_void_volume_value",
                            kind="has_measurement",
                            metric="volume",
                            value=_measurement_bucket_value(graph, equal_void_regions[0].id, "volume"),
                        ),
                        Clause(
                            id="has_void_centroid_z",
                            kind="has_measurement",
                            metric="centroid_z",
                        ),
                    ],
                    aggregation="argmax",
                    aggregation_metric="centroid_z",
                    hop_count=4,
                    difficulty="cad_browsecomp",
                    min_individual_clause_candidates=2,
                )
            )
    queries.extend(synthesize_graph_hop_queries(graph))
    return queries


def _nodes_with_numeric_measurement(graph: OntologyGraph, nodes: list[Node], metric: str) -> list[Node]:
    result: list[Node] = []
    for node in nodes:
        value = _measurement_value(graph, node.id, metric)
        if isinstance(value, (int, float)):
            result.append(node)
    return result


def _has_unique_extreme(
    graph: OntologyGraph,
    nodes: list[Node],
    metric: str,
    aggregation: str,
    *,
    min_margin: float = 0.0,
) -> bool:
    scores = [
        float(value)
        for node in nodes
        if isinstance((value := _measurement_value(graph, node.id, metric)), (int, float))
    ]
    if not scores:
        return False
    ordered = sorted(scores, reverse=aggregation == "argmax")
    if len(ordered) < 2:
        return True
    return abs(ordered[0] - ordered[1]) > min_margin


def _apply_clause(graph: OntologyGraph, candidates: list[Node], clause: Clause) -> list[Node]:
    if clause.kind == "property_equals" and clause.metric:
        return [
            node
            for node in candidates
            if node.properties.get(clause.metric) == clause.value
        ]
    if clause.kind == "has_relation" and clause.relation:
        return [
            node
            for node in candidates
            if any(
                clause.target_type is None
                or ((target := graph.node(relation.target_id)) is not None and target.type == clause.target_type)
                for relation in graph.relations_from(node.id, clause.relation)
            )
        ]
    if clause.kind == "has_measurement" and clause.metric:
        if clause.value is None:
            return [node for node in candidates if _has_measurement(graph, node.id, clause.metric)]
        return [
            node
            for node in candidates
            if _measurement_matches(graph, node.id, clause.metric, clause.value)
        ]
    if clause.kind == "reference_measurement":
        return candidates if _reference_clause_matches(graph, clause) else []
    if clause.kind == "metric_compare" and clause.metric and clause.operator:
        return [
            node
            for node in candidates
            if _compare(_measurement_value(graph, node.id, clause.metric), clause.operator, clause.value)
        ]
    if clause.kind == "metric_ratio_compare" and clause.metric and clause.reference_metric and clause.operator:
        return [
            node
            for node in candidates
            if _compare_metric_ratio(
                _measurement_value(graph, node.id, clause.metric),
                clause.operator,
                _measurement_value(graph, node.id, clause.reference_metric),
                clause.value,
            )
        ]
    if clause.kind == "related_metric_compare" and clause.relation and clause.target_type and clause.metric and clause.operator:
        return nodes_matching_related_metric_compare(
            graph,
            candidates,
            relation=clause.relation,
            target_type=clause.target_type,
            metric=clause.metric,
            operator=clause.operator,
            value=clause.value,
        )
    return candidates


def _apply_primary_aggregation(graph: OntologyGraph, candidates: list[Node], query: QueryProgram) -> list[Node]:
    if not query.aggregation_metric or not candidates:
        return candidates
    if query.aggregation_metric == REFERENCE_FEATURE_DISTANCE_METRIC:
        return _apply_reference_feature_distance_aggregation(graph, candidates, query)
    if query.aggregation in {"rank_asc", "rank_desc"}:
        return _apply_metric_rank_aggregation(
            graph,
            candidates,
            aggregation=query.aggregation,
            metric=query.aggregation_metric,
            rank=query.aggregation_rank,
        )
    return _apply_metric_aggregation(
        graph,
        candidates,
        aggregation=query.aggregation,
        metric=query.aggregation_metric,
    )


def _apply_metric_aggregation(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    aggregation: str | None,
    metric: str,
) -> list[Node]:
    scored: list[tuple[float, Node]] = []
    for node in candidates:
        value = _measurement_value(graph, node.id, metric)
        if isinstance(value, (int, float)):
            scored.append((float(value), node))
    if not scored:
        return []
    target = max(score for score, _ in scored) if aggregation == "argmax" else min(score for score, _ in scored)
    return [node for score, node in scored if score == target]


def _apply_metric_rank_aggregation(
    graph: OntologyGraph,
    candidates: list[Node],
    *,
    aggregation: str | None,
    metric: str,
    rank: int | None,
) -> list[Node]:
    scored: list[tuple[float, Node]] = []
    for node in candidates:
        value = _measurement_value(graph, node.id, metric)
        if isinstance(value, (int, float)):
            scored.append((float(value), node))
    if not scored or rank is None or rank < 1:
        return []
    if aggregation not in {"rank_asc", "rank_desc"}:
        return _apply_metric_aggregation(graph, candidates, aggregation=aggregation, metric=metric)
    return _ranked_nodes(scored, rank=rank, descending=aggregation == "rank_desc")


def _ranked_nodes(scored: list[tuple[float, Node]], *, rank: int, descending: bool) -> list[Node]:
    ordered = sorted(scored, key=lambda item: (-item[0] if descending else item[0], item[1].id))
    if rank > len(ordered):
        return []
    target = ordered[rank - 1][0]
    return [node for score, node in scored if abs(score - target) <= VALUE_MATCH_TOLERANCE]


def _apply_reference_feature_distance_aggregation(
    graph: OntologyGraph,
    candidates: list[Node],
    query: QueryProgram,
) -> list[Node]:
    reference_point = _reference_point_from_query(graph, query)
    if reference_point is None:
        return []
    target_point_metric = _target_point_metric_from_query(query)
    scored: list[tuple[float, Node]] = []
    for node in candidates:
        point = _point_measurement(graph, node.id, target_point_metric)
        if point is not None:
            scored.append((_point_distance(point, reference_point), node))
    if not scored:
        return []
    if query.aggregation in {"rank_asc", "rank_desc"}:
        return _ranked_nodes(
            scored,
            rank=query.aggregation_rank or 0,
            descending=query.aggregation == "rank_desc",
        )
    target = min(score for score, _ in scored) if query.aggregation == "argmin" else max(score for score, _ in scored)
    return [node for score, node in scored if abs(score - target) <= VALUE_MATCH_TOLERANCE]


def _measurement_value(graph: OntologyGraph, entity_id: str, metric: str) -> Any:
    measurements: list[Measurement] = graph.measurements_for(entity_id, metric)
    return measurements[0].value if measurements else None


def _measurement_scopes_for_clause(graph: OntologyGraph, candidates: list[Node], clause: Clause) -> set[str]:
    if not clause.metric:
        return set()
    if clause.kind == "related_metric_compare" and clause.relation and clause.target_type:
        return {
            measurement.scope
            for node in candidates
            for edge in graph.relations_from(node.id, clause.relation)
            for target in [graph.node(edge.target_id)]
            if target is not None and target.type == clause.target_type
            for measurement in graph.measurements_for(target.id, clause.metric)
        }
    return {
        measurement.scope
        for node in candidates
        for metric in _measurement_scope_metrics(clause.metric)
        for measurement in graph.measurements_for(node.id, metric)
    }


def _has_measurement(graph: OntologyGraph, entity_id: str, metric: str) -> bool:
    if graph.measurements_for(entity_id, metric):
        return True
    return all(graph.measurements_for(entity_id, component) for component in _point_metric_components(metric))


def _measurement_scope_metrics(metric: str) -> tuple[str, ...]:
    components = _point_metric_components(metric)
    return (metric, *components) if components else (metric,)


def _point_metric_components(metric: str) -> tuple[str, ...]:
    return {
        "bbox_center": ("bbox_center_x", "bbox_center_y", "bbox_center_z"),
        "centroid": ("centroid_x", "centroid_y", "centroid_z"),
        "midpoint": ("midpoint_x", "midpoint_y", "midpoint_z"),
        "coordinate": ("coordinate_x", "coordinate_y", "coordinate_z"),
    }.get(metric, ())


def _measurement_matches(graph: OntologyGraph, entity_id: str, metric: str, expected: Any) -> bool:
    value = _measurement_value(graph, entity_id, metric)
    if isinstance(value, (int, float)) and isinstance(expected, (int, float)):
        return abs(float(value) - float(expected)) <= VALUE_MATCH_TOLERANCE
    return value == expected


def _reference_clause_matches(graph: OntologyGraph, clause: Clause) -> bool:
    if not isinstance(clause.value, dict):
        return False
    reference_id = clause.value.get("reference_id")
    if not isinstance(reference_id, str):
        return False
    reference_type = str(clause.value.get("reference_type", "feature"))
    reference = graph.node(reference_id)
    if reference is None or reference.type != reference_type:
        return False
    anchor_metrics = clause.value.get("reference_anchor_metrics")
    anchor_values = clause.value.get("reference_anchor_values")
    if isinstance(anchor_metrics, list) and isinstance(anchor_values, dict):
        return all(
            isinstance(metric, str)
            and _measurement_matches(graph, reference_id, metric, anchor_values.get(metric))
            for metric in anchor_metrics
        )
    expected_volume = clause.value.get("reference_volume")
    expected_centroid_z = clause.value.get("reference_centroid_z")
    return (
        _measurement_matches(graph, reference_id, "volume", expected_volume)
        and _measurement_matches(graph, reference_id, "centroid_z", expected_centroid_z)
        and _point_measurement(graph, reference_id, "centroid") is not None
    )


def _largest_equal_value_group(graph: OntologyGraph, nodes: list[Node], metric: str) -> list[Node]:
    groups: dict[float, list[Node]] = {}
    for node in nodes:
        bucket = _measurement_bucket_value(graph, node.id, metric)
        if bucket is not None:
            groups.setdefault(bucket, []).append(node)
    if not groups:
        return []
    return max(groups.values(), key=lambda group: (len(group), candidate_ids(group)))


def _reference_feature_for_unique_nearest(
    graph: OntologyGraph,
    reference_features: list[Node],
    target_nodes: list[Node],
    *,
    target_point_metric: str,
    reference_point_metric: str,
) -> Node | None:
    targets = [
        node
        for node in target_nodes
        if _point_measurement(graph, node.id, target_point_metric) is not None
    ]
    if len(targets) < 2:
        return None
    reference_key_counts = _reference_feature_key_counts(graph, reference_features)
    for reference in sorted(reference_features, key=lambda node: node.id):
        reference_key = _reference_feature_key(graph, reference.id)
        if None in reference_key or reference_key_counts.get(reference_key, 0) != 1:
            continue
        reference_point = _point_measurement(graph, reference.id, reference_point_metric)
        if reference_point is None:
            continue
        distances = [
            _point_distance(_point_measurement(graph, target.id, target_point_metric), reference_point)
            for target in targets
        ]
        ordered = sorted(distances)
        if len(ordered) >= 2 and abs(ordered[0] - ordered[1]) > GEOMETRY_MARGIN_EPSILON:
            return reference
    return None


def _reference_feature_prompt_value(graph: OntologyGraph, reference: Node) -> dict[str, Any]:
    return {
        "reference_id": reference.id,
        "reference_volume": _measurement_bucket_value(graph, reference.id, "volume"),
        "reference_centroid_z": _measurement_bucket_value(graph, reference.id, "centroid_z"),
    }


def _reference_feature_key_counts(graph: OntologyGraph, features: list[Node]) -> dict[tuple[float | None, float | None], int]:
    counts: dict[tuple[float | None, float | None], int] = {}
    for feature in features:
        key = _reference_feature_key(graph, feature.id)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _reference_feature_key(graph: OntologyGraph, feature_id: str) -> tuple[float | None, float | None]:
    return (
        _measurement_bucket_value(graph, feature_id, "volume"),
        _measurement_bucket_value(graph, feature_id, "centroid_z"),
    )


def _reference_point_from_query(graph: OntologyGraph, query: QueryProgram) -> list[float] | None:
    reference_point_metric = _sampled_parameter_value(query, "reference_point_metric") or "centroid"
    for clause in query.clauses:
        if clause.kind == "reference_measurement" and isinstance(clause.value, dict):
            reference_id = clause.value.get("reference_id")
            if isinstance(reference_id, str):
                return _point_measurement(graph, reference_id, reference_point_metric)
    return None


def _target_point_metric_from_query(query: QueryProgram) -> str:
    return _sampled_parameter_value(query, "target_point_metric") or "midpoint"


def _sampled_parameter_value(query: QueryProgram, key: str) -> str | None:
    raw = query.sampled_parameters.get(key)
    values = raw if isinstance(raw, list) else [raw]
    for value in values:
        if value is not None:
            return str(value)
    return None


def _point_measurement(graph: OntologyGraph, entity_id: str, metric: str) -> list[float] | None:
    value = _measurement_value(graph, entity_id, metric)
    if isinstance(value, list) and len(value) >= 3:
        return _numeric_point(value[:3])
    scalar_names = {
        "bbox_center": ("bbox_center_x", "bbox_center_y", "bbox_center_z"),
        "centroid": ("centroid_x", "centroid_y", "centroid_z"),
        "midpoint": ("midpoint_x", "midpoint_y", "midpoint_z"),
        "coordinate": ("coordinate_x", "coordinate_y", "coordinate_z"),
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


def _measurement_bucket_value(graph: OntologyGraph, entity_id: str, metric: str) -> float | None:
    value = _measurement_value(graph, entity_id, metric)
    if not isinstance(value, (int, float)):
        return None
    bucket = round(float(value), VALUE_BUCKET_DECIMALS)
    return 0.0 if bucket == 0.0 else bucket


def _compare(value: Any, operator: str, expected: Any) -> bool:
    if not isinstance(value, (int, float)):
        return False
    if operator == ">":
        return value > expected
    if operator == ">=":
        return value >= expected
    if operator == "<":
        return value < expected
    if operator == "<=":
        return value <= expected
    if operator == "==":
        if isinstance(expected, (int, float)):
            return abs(float(value) - float(expected)) <= VALUE_MATCH_TOLERANCE
        return value == expected
    return False


def _compare_metric_ratio(value: Any, operator: str, reference: Any, ratio: Any) -> bool:
    if not isinstance(reference, (int, float)) or not isinstance(ratio, (int, float)):
        return False
    return _compare(value, operator, float(reference) * float(ratio))
