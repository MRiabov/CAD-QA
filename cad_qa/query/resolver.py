"""Deterministic query resolver."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from cad_qa.ontology.nodes import Measurement, Node, OntologyGraph
from cad_qa.query.candidates import candidate_ids, initial_candidates
from cad_qa.query.difficulty import difficulty_for_hops
from cad_qa.query.ir import CandidateSetTrace, Clause, QueryProgram, QueryResolution


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
            measurement_scopes.update(
                measurement.scope
                for node in candidates
                for measurement in graph.measurements_for(node.id, clause.metric)
            )
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
        candidates = _apply_aggregation(graph, candidates, query)
        steps.append(
            {
                "step": "aggregation",
                "aggregation": query.aggregation,
                "metric": query.aggregation_metric,
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
    status = "resolved"
    failure_reason = None
    if not candidates:
        status = "failed"
        failure_reason = "no_candidates"
    elif query.reject_unless_unique and len(candidates) != 1:
        status = "failed"
        failure_reason = "not_unique"
    trace = CandidateSetTrace(query.query_id, steps, candidate_ids(candidates), status, failure_reason)
    gold_answer = candidates[0].id if status == "resolved" else None
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
    paths = graph.nodes_by_type("path")
    selectors = graph.nodes_by_type("selector")
    material_regions = graph.nodes_by_type("material_region")
    void_regions = graph.nodes_by_type("void_region")
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
                        text=f"The target operation assigns `{first.properties.get('target')}`.",
                    ),
                    Clause(
                        id="operation_name",
                        kind="property_equals",
                        metric="operation",
                        value=first.properties.get("operation"),
                        text=f"The target operation is the `{first.properties.get('operation')}(...)` call in that assignment chain.",
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
                        text="The target profile is drawn on a CadQuery workplane.",
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
                        text="The target profile is made from a visible `.circle(...)`, `.rect(...)`, or `.polyline(...)` call on a workplane.",
                    ),
                    Clause(
                        id="has_profile_area",
                        kind="has_measurement",
                        metric="area",
                        text="The target has a computable profile area.",
                    ),
                    Clause(
                        id="has_workplane_z",
                        kind="has_measurement",
                        metric="workplane_origin_z",
                        text="The target is on a workplane whose origin Z coordinate can be compared.",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="workplane_origin_z",
                hop_count=3,
                difficulty="cad_browsecomp",
            )
        )
    if faces:
        first_face = sorted(faces, key=lambda node: node.properties.get("stable_selector", ""))[0]
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
                        text=f"The target face is selected by the visible `.faces({selector_text!r})` selector.",
                    ),
                    Clause(
                        id="has_selector",
                        kind="has_relation",
                        relation=selector_relation,
                        target_type="selector",
                        text="The target has a stable selector result extracted from the script.",
                    ),
                ],
                hop_count=2,
                difficulty="bridge",
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
                        text="The target path has an initial tangent derived from the first two visible path points.",
                    ),
                    Clause(
                        id="has_nearest_origin_distance",
                        kind="has_measurement",
                        metric="nearest_point_distance_to_origin",
                        text="The target path has a nearest visible path point to the global origin.",
                    ),
                ],
                aggregation="argmin",
                aggregation_metric="nearest_point_distance_to_origin",
                hop_count=2,
                difficulty="bridge",
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
                        text="The target selector resolves to the same stable face as another visible `.faces(...)` selector.",
                    ),
                    Clause(
                        id="has_selector_operation_index",
                        kind="has_measurement",
                        metric="operation_index",
                        text="The target selector has a visible operation-order position that can be compared.",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric="operation_index",
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
                        text="The target is an added-volume region from an `.extrude(...)` or `.sweep(...)` feature.",
                    ),
                    Clause(
                        id=f"has_region_{material_metric}",
                        kind="has_measurement",
                        metric=material_metric,
                        text="The target has an added-volume measurement that can be compared.",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric=material_metric,
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=1 if has_kernel_material else 3,
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
                        text="The target is a removed-volume region from a visible cut operation.",
                    ),
                    Clause(
                        id=f"has_void_{void_metric}",
                        kind="has_measurement",
                        metric=void_metric,
                        text="The target has a removed-volume discriminator that can be compared.",
                    ),
                ],
                aggregation="argmax",
                aggregation_metric=void_metric,
                hop_count=3,
                difficulty="cad_browsecomp",
                min_individual_clause_candidates=1 if has_kernel_void else 3,
            )
        )
    return queries


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
                relation.source_id == node.id
                and relation.type == clause.relation
                and (clause.target_type is None or (graph.node(relation.target_id) and graph.node(relation.target_id).type == clause.target_type))
                for relation in graph.relations
            )
        ]
    if clause.kind == "has_measurement" and clause.metric:
        return [node for node in candidates if graph.measurements_for(node.id, clause.metric)]
    if clause.kind == "metric_compare" and clause.metric and clause.operator:
        return [
            node
            for node in candidates
            if _compare(_measurement_value(graph, node.id, clause.metric), clause.operator, clause.value)
        ]
    return candidates


def _apply_aggregation(graph: OntologyGraph, candidates: list[Node], query: QueryProgram) -> list[Node]:
    if not query.aggregation_metric or not candidates:
        return candidates
    scored: list[tuple[float, Node]] = []
    for node in candidates:
        value = _measurement_value(graph, node.id, query.aggregation_metric)
        if isinstance(value, (int, float)):
            scored.append((float(value), node))
    if not scored:
        return []
    target = max(score for score, _ in scored) if query.aggregation == "argmax" else min(score for score, _ in scored)
    return [node for score, node in scored if score == target]


def _measurement_value(graph: OntologyGraph, entity_id: str, metric: str) -> Any:
    measurements: list[Measurement] = graph.measurements_for(entity_id, metric)
    return measurements[0].value if measurements else None


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
        return value == expected
    return False
