from cad_qa.baselines import baseline_predictions, run_baselines
from cad_qa.config import DatasetConfig
from cad_qa.fixtures import smoke_traces
from cad_qa.graph_query import (
    build_typed_query_graph,
    default_graph_query_irs,
    graph_query_prompt,
    resolve_graph_query,
)
from cad_qa.materialize import materialize_rows, rows_to_dicts
from cad_qa.materialize import _node_from_dict
from cad_qa.parse import grade_candidate
from cad_qa.schema import validate_public_row


def test_typed_graph_query_resolver_supports_filters_and_aggregation():
    config = DatasetConfig()
    source, trace = smoke_traces(config)[1]
    nodes = [_node_from_dict(item) for item in trace.operation_nodes]
    graph = build_typed_query_graph(nodes, trace)
    ir = {
        "ir_version": "cadqa_graph_query_ir_v1",
        "query_type": "feature_select",
        "target_node_type": "feature",
        "filters": [
            {"op": "after_ordinal", "operation": "box", "ordinal": 1},
            {"field": "metrics.abs_signed_volume_delta", "op": "exists"},
            {"field": "metrics.abs_signed_volume_delta", "op": "gt", "value": 0.0},
        ],
        "aggregate": {"op": "argmax", "metric": "metrics.abs_signed_volume_delta"},
        "return": {"field": "feature_id"},
    }

    resolution = resolve_graph_query(graph, ir, config=config)

    assert resolution.status == "ok"
    assert resolution.answer == "wp3"
    assert resolution.choices == ["wp3"]
    assert resolution.graph_query["candidate_ids"] == ["wp3"]
    assert resolution.graph_query["resolved_ids"] == ["wp3"]
    assert resolution.graph_query["measured_values"][0]["feature_id"] == "wp3"


def test_advanced_diagnostic_rows_are_materialized_from_smoke_traces():
    config = DatasetConfig()
    rows = [
        row
        for source, trace in smoke_traces(config)
        for row in materialize_rows(source, trace, config=config)
    ]
    task_types = {row.task_type for row in rows}

    assert {
        "graph_query",
        "spatial_distance",
        "bbox_region_query",
        "validity_failure_prediction",
    } <= task_types

    graph_row = next(
        row
        for row in rows
        if row.task_type == "graph_query"
        and row.labels["graph_query"]["ir"]["query_id"]
        == "default_abs_volume_delta_argmax"
    )
    assert graph_row.answer == "wp1"
    assert graph_row.labels["graph_query"]["aggregation"] == "argmax"
    assert (
        graph_row.labels["graph_query"]["ir"]["ir_version"] == "cadqa_graph_query_ir_v1"
    )
    assert not validate_public_row(rows_to_dicts([graph_row])[0])

    topology_graph_rows = [
        row
        for row in rows
        if row.task_type == "graph_query"
        and row.labels["graph_query"]["ir"]["query_id"]
        in {
            "default_face_count_delta_argmax",
            "default_edge_count_delta_argmax",
            "default_vertex_count_delta_argmax",
        }
    ]
    assert {
        row.labels["graph_query"]["ir"]["query_id"] for row in topology_graph_rows
    } == {
        "default_face_count_delta_argmax",
        "default_edge_count_delta_argmax",
        "default_vertex_count_delta_argmax",
    }
    for topology_graph_row in topology_graph_rows:
        assert "count" in topology_graph_row.prompt
        assert grade_candidate(rows_to_dicts([topology_graph_row])[0], str(topology_graph_row.answer))["correct"]

    edge_count_graph_row = next(
        row for row in topology_graph_rows if "edge count" in row.prompt and row.answer == "wp3"
    )
    assert edge_count_graph_row.answer == "wp3"

    human_note_query_ids = {
        row.labels["graph_query"]["ir"]["query_id"]
        for row in rows
        if row.task_type == "graph_query"
    }
    assert {
        "operation_metric_immediately_after_ordinal__box__2__signed_volume_delta",
        "default_box_bbox_volume_argmax",
        "default_box_bbox_y_extent_argmax",
        "default_axis_length_of_largest_positive_volume_delta",
    } <= human_note_query_ids
    relation_row = next(
        row
        for row in rows
        if row.task_type == "graph_query"
        and row.labels["graph_query"]["ir"]["query_id"].startswith(
            "relation_exists__before__"
        )
    )
    assert relation_row.answer in {"yes", "no"}
    assert relation_row.choices == ["yes", "no"]
    assert "occur before" in relation_row.prompt

    second_box_delta = next(
        row
        for row in rows
        if row.task_type == "graph_query"
        and row.labels["graph_query"]["ir"]["query_id"]
        == "operation_metric_immediately_after_ordinal__box__2__signed_volume_delta"
    )
    assert second_box_delta.answer == 40.0
    assert second_box_delta.unit == "mm^3"
    assert "box #2" in second_box_delta.prompt

    ordinal_words = ("first", "second", "third", "fourth", "fifth")
    ordinal_rows = [
        row
        for row in rows
        if row.task_type in {"graph_query", "spatial_distance"}
    ]
    for row in ordinal_rows:
        public_query_id = (
            row.labels.get("graph_query", {}).get("ir", {}).get("query_id")
            or row.diagnostics.get("query_id")
            or ""
        )
        assert not any(word in public_query_id for word in ordinal_words)
        assert not any(word in row.prompt.lower() for word in ordinal_words)

    distance_query_ids = {
        row.diagnostics["query_id"]
        for row in rows
        if row.task_type == "spatial_distance"
    }
    assert distance_query_ids == {
        "component_distance__hole__1__hole__3__x",
        "centerline_distance__hole__1__hole__2",
    }
    assert not any(query_id.startswith("default_point_distance_") for query_id in distance_query_ids)
    distance_row = next(
        row
        for row in rows
        if row.task_type == "spatial_distance"
        and row.diagnostics["query_id"] == "component_distance__hole__1__hole__3__x"
    )
    assert distance_row.answer == 3.0
    assert distance_row.unit == "mm"
    assert grade_candidate(rows_to_dicts([distance_row])[0], "3")["correct"]

    region_row = next(
        row for row in rows if row.task_type == "bbox_region_query" and row.answer == 8
    )
    assert region_row.answer == 8
    assert region_row.labels["spatial_query"]["predicate"] == "inside"

    validity_row = next(
        row for row in rows if row.task_type == "validity_failure_prediction"
    )
    assert validity_row.answer == "valid"
    assert validity_row.choices == ["valid", "invalid", "inconclusive"]


def test_numeric_ordinal_graph_query_defaults_support_fifth_box():
    graph = {
        "graph_version": "cadqa_typed_graph_v1",
        "source_id": "synthetic",
        "trace_id": "trace",
        "nodes": [
            {
                "id": f"feature:box_{index}",
                "node_type": "feature",
                "feature_id": f"box_{index}",
                "operation": "box",
                "step_index": index,
                "metrics": {},
            }
            for index in range(1, 6)
        ]
        + [
            {
                "id": "feature:feature_after_box_5",
                "node_type": "feature",
                "feature_id": "feature_after_box_5",
                "operation": "extrude",
                "step_index": 6,
                "metrics": {
                    "signed_volume_delta": 12.5,
                    "abs_signed_volume_delta": 12.5,
                },
            }
        ],
        "edges": [],
    }

    fifth_box_query = next(
        query
        for query in default_graph_query_irs(graph)
        if query["query_id"]
        == "operation_metric_immediately_after_ordinal__box__5__signed_volume_delta"
    )
    resolution = resolve_graph_query(graph, fifth_box_query, config=DatasetConfig())
    prompt = graph_query_prompt(fifth_box_query, resolution, "result = feature_after_box_5")

    assert resolution.status == "ok"
    assert resolution.answer == 12.5
    assert resolution.target_feature_id == "feature_after_box_5"
    assert fifth_box_query["filters"][0]["ordinal"] == 5
    assert "box #5" in prompt
    assert "fifth" not in prompt.lower()


def test_relation_graph_query_defaults_include_all_zero_volume_delta_graph():
    graph = {
        "graph_version": "cadqa_typed_graph_v1",
        "source_id": "synthetic",
        "trace_id": "trace",
        "nodes": [
            {
                "id": "feature:wp0",
                "node_type": "feature",
                "feature_id": "wp0",
                "operation": "Workplane",
                "step_index": 0,
                "metrics": {
                    "signed_volume_delta": 0.0,
                    "abs_signed_volume_delta": 0.0,
                },
            },
            {
                "id": "feature:wp1",
                "node_type": "feature",
                "feature_id": "wp1",
                "operation": "box",
                "step_index": 1,
                "metrics": {
                    "signed_volume_delta": 0.0,
                    "abs_signed_volume_delta": 0.0,
                },
            },
        ],
        "edges": [
            {
                "source": "feature:wp0",
                "target": "feature:wp1",
                "edge_type": "input_to",
            }
        ],
    }

    queries = default_graph_query_irs(graph)
    relation_queries = [
        query for query in queries if query["query_type"] == "relation_exists"
    ]

    assert relation_queries
    abs_query = next(
        query
        for query in queries
        if query["query_id"] == "default_abs_volume_delta_argmax"
    )
    resolution = resolve_graph_query(graph, abs_query, config=DatasetConfig())
    assert resolution.status == "empty_candidate_set"


def test_advanced_diagnostic_naive_baseline_is_available():
    config = DatasetConfig()
    source, trace = smoke_traces(config)[1]
    rows = rows_to_dicts(materialize_rows(source, trace, config=config))

    predictions = baseline_predictions(rows, name="advanced_diagnostic_naive")
    metrics = run_baselines(rows)

    assert "advanced_diagnostic_naive" in metrics
    assert set(predictions) == {row["id"] for row in rows}
