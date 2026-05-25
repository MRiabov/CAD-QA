from __future__ import annotations

from cad_qa.ontology import build_graph
from cad_qa.source import source_record_from_mapping


CHAIN_SOURCE = """
import cadquery as cq
base = cq.Workplane("XY").box(10, 8, 4)
part = base.faces(">Z").workplane().center(1, -1).circle(2).cutBlind(-2)
boss = cq.Workplane("XY").circle(1).extrude(3)
result = part.union(boss)
"""


LOOP_SOURCE = """
import cadquery as cq
base = cq.Workplane("XY").box(8, 8, 4)
for face_tag in (">Z", "<Z"):
    base = base.faces(face_tag).workplane().center(0, 0).rect(2, 1).cutBlind(-1)
for z in (1, -1):
    base = base.faces(">Y").workplane().center(0, z).circle(0.5).cutBlind(-2)
result = base
"""


def _graph(source_id: str, code: str):
    return build_graph(source_record_from_mapping({"source_id": source_id, "normalized_code": code}))


def _operation_props(graph, target: str) -> list[dict]:
    return [
        node.properties
        for node in graph.nodes_by_type("operation")
        if node.properties["target"] == target
    ]


def test_cad_operation_extraction_preserves_full_chain_order_and_args() -> None:
    graph = _graph("src_chain_ops", CHAIN_SOURCE)

    assert [op["operation"] for op in _operation_props(graph, "base")] == ["Workplane", "box"]
    part_ops = _operation_props(graph, "part")
    assert [op["operation"] for op in part_ops] == [
        "faces",
        "workplane",
        "center",
        "circle",
        "cutBlind",
    ]
    assert [op["chain_index"] for op in part_ops] == [0, 1, 2, 3, 4]
    assert part_ops[0]["base"] == "base"
    assert part_ops[0]["args"] == [">Z"]
    assert part_ops[2]["args"] == [1, -1]
    assert part_ops[3]["args"] == [2]
    assert part_ops[4]["args"] == [-2]

    assert [op["operation"] for op in _operation_props(graph, "boss")] == [
        "Workplane",
        "circle",
        "extrude",
    ]
    assert _operation_props(graph, "result") == [
        {
            "target": "result",
            "operation": "union",
            "base": "part",
            "args": ["boss"],
            "kwargs": {},
            "chain_index": 0,
        }
    ]

    operation_ids = [node.id for node in graph.nodes_by_type("operation")]
    assert len(operation_ids) == len(set(operation_ids))
    assert graph.node("feature:part").properties["operation"] == "cutBlind"
    assert graph.node("feature:boss").properties["operation"] == "extrude"
    assert graph.node("feature:result").properties["operation"] == "union"
    assert _has_relation(graph, "feature:part", "operation:result", "input_to")
    assert _has_relation(graph, "feature:boss", "operation:result", "input_to")
    assert _has_relation(graph, "feature:part", "feature:result", "input_to")
    assert _has_relation(graph, "feature:boss", "feature:result", "input_to")
    assert _has_relation(graph, "workplane:part_center", "workplane:part", "derived_from")
    assert graph.node("workplane:part_center").properties["origin"] == [1.0, -1.0, 0.0]
    assert _has_relation(graph, "profile:part", "workplane:part_center", "located_on")
    assert _has_relation(graph, "operation:part:3:circle", "operation:part:4:cutBlind", "input_to")
    assert not _self_input_relations(graph)


def test_loop_unrolled_cad_operations_use_concrete_iteration_values_and_unique_ids() -> None:
    graph = _graph("src_loop_ops", LOOP_SOURCE)

    face_ops = [
        node.properties
        for node in graph.nodes_by_type("operation")
        if node.properties["operation"] == "faces"
    ]
    rect_ops = [
        node.properties
        for node in graph.nodes_by_type("operation")
        if node.properties["operation"] == "rect"
    ]
    center_ops = [
        node.properties
        for node in graph.nodes_by_type("operation")
        if node.properties["operation"] == "center"
    ]
    cut_ops = [
        node
        for node in graph.nodes_by_type("operation")
        if node.properties["operation"] == "cutBlind"
    ]

    assert [op["args"] for op in face_ops] == [[">Z"], ["<Z"], [">Y"], [">Y"]]
    assert [op["args"] for op in rect_ops] == [[2, 1], [2, 1]]
    assert [op["args"] for op in center_ops] == [[0, 0], [0, 0], [0, 1], [0, -1]]
    assert [node.properties["args"] for node in cut_ops] == [[-1], [-1], [-2], [-2]]
    assert len({node.id for node in cut_ops}) == 4

    feature_ops = [node.properties["operation"] for node in graph.nodes_by_type("feature")]
    assert feature_ops == ["box", "cutBlind", "cutBlind", "cutBlind", "cutBlind"]
    assert graph.diagnostics == [
        {"kind": "loop_unrolled", "source_line": 4, "iteration": 0, "value": ">Z"},
        {"kind": "loop_unrolled", "source_line": 4, "iteration": 1, "value": "<Z"},
        {"kind": "loop_unrolled", "source_line": 6, "iteration": 0, "value": 1},
        {"kind": "loop_unrolled", "source_line": 6, "iteration": 1, "value": -1},
    ]
    assert not _self_input_relations(graph)


def _has_relation(graph, source_id: str, target_id: str, relation_type: str) -> bool:
    return any(
        relation.source_id == source_id
        and relation.target_id == target_id
        and relation.type == relation_type
        for relation in graph.relations
    )


def _self_input_relations(graph) -> list[tuple[str, str]]:
    return [
        (relation.source_id, relation.target_id)
        for relation in graph.relations
        if relation.type == "input_to"
        and relation.source_id == relation.target_id
        and relation.source_id.startswith("feature:")
    ]
