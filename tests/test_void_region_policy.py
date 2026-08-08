from __future__ import annotations

from cad_qa.dataset.materialize import materialize_row
from cad_qa.ontology.nodes import Measurement, Node, OntologyGraph, Relation
from cad_qa.query.resolver import resolve_query
from cad_qa.query.synthesis import synthesize_graph_hop_queries


def _void_region_graph(count: int = 2, *, include_targets: bool = True) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:void-region-policy",
        source={
            "source_id": "void-region-policy",
            "source_code": "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)",
        },
    )
    for index in range(count):
        target = f"cut_{index}"
        node_id = f"void_region:{target}"
        properties = {"operation": "cut"}
        if include_targets:
            properties["target"] = target
        graph.add_node(
            Node(
                node_id,
                "void_region",
                node_id,
                properties=properties,
            )
        )
        graph.add_relation(Relation(node_id, node_id, "has_kernel_void_region_geometry"))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "volume", 10.0 + index, "mm^3"))
        graph.add_measurement(Measurement(node_id, "entity_geometry", "centroid_x", float(index), "mm"))
    return graph


def _feature_graph(count: int) -> OntologyGraph:
    graph = OntologyGraph(
        graph_id="graph:rank-budget",
        source={
            "source_id": "rank-budget",
            "source_code": "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)",
        },
    )
    for index in range(count):
        node_id = f"feature:feature_{index}"
        graph.add_node(Node(node_id, "feature", node_id))
        graph.add_measurement(Measurement(node_id, "snapshot_state", "volume", float(index + 1), "mm^3"))
    return graph


def test_void_region_selection_is_multiple_choice() -> None:
    graph = _void_region_graph()

    query = next(
        query
        for query in synthesize_graph_hop_queries(graph)
        if query.query_id.rsplit(":", 1)[-1] == "parameterized_void_region_extreme"
    )
    resolution = resolve_query(graph, query)
    row = materialize_row(graph, resolution)

    assert resolution.verifier_status == "resolved"
    assert row.answer_format == "candidate_label"
    assert row.query_program["answer_spec"]["mode"] == "candidate_label"
    assert len(row.query_program["answer_spec"]["candidate_labels"]) <= 7
    assert "Candidate labels:" in row.prompt
    assert row.query_program["aggregation"] in {"argmax", "argmin"}
    assert row.query_program["aggregation_rank"] is None


def test_void_region_volume_is_answered_for_a_given_operation() -> None:
    graph = _void_region_graph()

    query = next(
        query
        for query in synthesize_graph_hop_queries(graph)
        if query.query_id.rsplit(":", 1)[-1] == "parameterized_void_region_volume"
    )
    resolution = resolve_query(graph, query)
    row = materialize_row(graph, resolution)

    assert resolution.verifier_status == "resolved"
    assert row.answer_format == "number"
    operation_target = query.sampled_parameters["operation_target"][0]
    assert operation_target in {"cut_0", "cut_1"}
    assert row.gold_answer == float(operation_target.rsplit("_", 1)[-1]) + 10.0
    assert row.query_program["answer_spec"]["metric"] == "volume"
    assert row.query_program["aggregation"] is None
    assert f"modeling operation `{operation_target}`" in row.prompt
    assert "Return exactly one number" in row.prompt


def test_void_region_rank_families_are_not_generated() -> None:
    graph = _void_region_graph(count=8)

    family_ids = {query.query_id.rsplit(":", 1)[-1] for query in synthesize_graph_hop_queries(graph)}

    assert "parameterized_void_region_rank" not in family_ids
    assert "parameterized_equal_void_region_metric_rank" not in family_ids
    assert "parameterized_void_region_reference_entity_distance_rank" not in family_ids


def test_synthesis_skips_void_region_volume_without_operation_target() -> None:
    graph = _void_region_graph(include_targets=False)

    family_ids = {query.query_id.rsplit(":", 1)[-1] for query in synthesize_graph_hop_queries(graph)}

    assert "parameterized_void_region_volume" not in family_ids


def test_synthesis_skips_void_region_volume_for_reassigned_operation_target() -> None:
    graph = _void_region_graph(count=1)
    duplicate_id = "void_region:cut_0:1"
    graph.add_node(Node(duplicate_id, "void_region", duplicate_id, properties={"target": "cut_0"}))
    graph.add_relation(Relation(duplicate_id, duplicate_id, "has_kernel_void_region_geometry"))
    graph.add_measurement(Measurement(duplicate_id, "entity_geometry", "volume", 20.0, "mm^3"))

    family_ids = {query.query_id.rsplit(":", 1)[-1] for query in synthesize_graph_hop_queries(graph)}

    assert "parameterized_void_region_volume" not in family_ids


def test_rank_generation_skips_candidate_sets_larger_than_public_choice_budget() -> None:
    graph = _feature_graph(count=8)

    family_ids = {query.query_id.rsplit(":", 1)[-1] for query in synthesize_graph_hop_queries(graph)}

    assert "parameterized_feature_rank" not in family_ids
