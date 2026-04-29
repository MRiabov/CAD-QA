"""Typed graph-query IR construction and deterministic resolution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

from cad_qa.config import DatasetConfig
from cad_qa.schema import OperationNode, TraceRecord

GRAPH_VERSION = "cadqa_typed_graph_v1"
QUERY_IR_VERSION = "cadqa_graph_query_ir_v1"
MAX_DEFAULT_RELATION_QUERIES = 32


@dataclass(frozen=True)
class GraphQueryResolution:
    status: str
    answer: Any
    answer_type: str | None
    choices: list[str] | None
    target_feature_id: str | None
    graph_query: dict[str, Any]
    diagnostics: dict[str, Any]
    unit: str | None = None
    numeric_tolerance: float | None = None


def build_typed_query_graph(
    nodes: list[OperationNode], trace: TraceRecord
) -> dict[str, Any]:
    """Build a public-safe typed graph from operation nodes and trace metadata."""

    sorted_nodes = sorted(
        (node for node in nodes if node.status == "ok"),
        key=lambda node: node.step_index,
    )
    snapshots_by_feature = {
        str(snapshot["feature_id"]): snapshot
        for snapshot in trace.snapshots
        if isinstance(snapshot.get("feature_id"), str)
    }
    previous_snapshot_by_feature = _previous_snapshots(trace.snapshots)
    graph_nodes: list[dict[str, Any]] = []
    graph_edges: list[dict[str, Any]] = []

    for node in sorted_nodes:
        snapshot = snapshots_by_feature.get(node.feature_id)
        previous_snapshot = previous_snapshot_by_feature.get(node.feature_id)
        graph_nodes.append(
            _feature_graph_node(
                node, snapshot=snapshot, previous_snapshot=previous_snapshot
            )
        )
        for input_feature in node.input_features:
            graph_edges.append(
                {
                    "source": f"feature:{input_feature}",
                    "target": f"feature:{node.feature_id}",
                    "edge_type": "input_to",
                }
            )

    for before, after in zip(sorted_nodes, sorted_nodes[1:], strict=False):
        graph_edges.append(
            {
                "source": f"feature:{before.feature_id}",
                "target": f"feature:{after.feature_id}",
                "edge_type": "before",
            }
        )
        graph_edges.append(
            {
                "source": f"feature:{after.feature_id}",
                "target": f"feature:{before.feature_id}",
                "edge_type": "after",
            }
        )

    for table in trace.selector_tables:
        target = table.get("target_feature_id")
        if isinstance(target, str):
            graph_edges.append(
                {
                    "source": f"selector:{len(graph_edges)}",
                    "target": f"feature:{target}",
                    "edge_type": "selected_by",
                    "selector_expression": table.get("selector_expression"),
                    "selected_count": table.get("selected_count"),
                }
            )

    for record in trace.provenance_records:
        target = record.get("target_feature_id")
        answer = record.get("answer_feature_id") or record.get("feature_id")
        if isinstance(target, str) and isinstance(answer, str):
            graph_edges.append(
                {
                    "source": f"feature:{answer}",
                    "target": f"feature:{target}",
                    "edge_type": str(record.get("provenance_relation") or "provenance"),
                    "provenance_confidence": record.get("provenance_confidence"),
                    "matching_method": record.get("matching_method"),
                }
            )

    return {
        "graph_version": GRAPH_VERSION,
        "source_id": trace.source_id,
        "trace_id": trace.trace_id,
        "nodes": graph_nodes,
        "edges": graph_edges,
    }


def resolve_graph_query(
    graph: dict[str, Any],
    ir: dict[str, Any],
    *,
    config: DatasetConfig,
) -> GraphQueryResolution:
    normalized_ir = _normalize_ir(ir)
    if normalized_ir.get("query_type") == "relation_exists":
        return _resolve_relation_exists(normalized_ir, graph)
    candidates = _candidate_feature_nodes(graph, normalized_ir)
    if not candidates:
        return _failed_resolution(normalized_ir, "empty_candidate_set", candidates=[])

    aggregate = (
        normalized_ir.get("aggregate")
        if isinstance(normalized_ir.get("aggregate"), dict)
        else {}
    )
    aggregate_op = aggregate.get("op")
    if aggregate_op in {"argmax", "argmin"}:
        return _resolve_arg_extreme(normalized_ir, candidates, aggregate, config=config)
    if aggregate_op == "count":
        resolved_ids = [str(node["feature_id"]) for node in candidates]
        graph_query = _resolved_query_payload(
            normalized_ir, candidates, resolved_ids=resolved_ids, measured_values=[]
        )
        return GraphQueryResolution(
            status="ok",
            answer=len(candidates),
            answer_type="integer",
            choices=None,
            target_feature_id=None,
            graph_query=graph_query,
            diagnostics={
                "resolver_status": "ok",
                "candidate_count": len(candidates),
                "resolved_ids": resolved_ids,
            },
        )

    if len(candidates) != 1:
        return _failed_resolution(
            normalized_ir, "ambiguous_candidate_set", candidates=candidates
        )
    node = candidates[0]
    answer = _field_value(
        node, str(normalized_ir.get("return", {}).get("field", "feature_id"))
    )
    return _resolution_from_answer(
        normalized_ir,
        candidates,
        answer,
        target_feature_id=str(node["feature_id"]),
        config=config,
    )


def default_graph_query_irs(graph: dict[str, Any]) -> list[dict[str, Any]]:
    queries = []
    if _feature_nodes_with_metric(graph, "metrics.abs_signed_volume_delta"):
        queries.append(
            {
                "ir_version": QUERY_IR_VERSION,
                "query_id": "default_abs_volume_delta_argmax",
                "query_type": "feature_select",
                "target_node_type": "feature",
                "filters": [
                    {"field": "metrics.abs_signed_volume_delta", "op": "exists"},
                    {
                        "field": "metrics.abs_signed_volume_delta",
                        "op": "gt",
                        "value": 0.0,
                    },
                ],
                "aggregate": {
                    "op": "argmax",
                    "metric": "metrics.abs_signed_volume_delta",
                },
                "return": {"field": "feature_id"},
                "prompt_template": "largest_abs_signed_volume_delta_feature",
            }
        )
    queries.extend(
        _operation_metric_after_ordinal_irs(
            graph,
            operation="box",
            metric="metrics.signed_volume_delta",
            return_field="metrics.signed_volume_delta",
            unit="mm^3",
        )
    )
    if _operation_count(graph, "box") >= 2:
        queries.extend(
            [
                {
                    "ir_version": QUERY_IR_VERSION,
                    "query_id": "default_box_bbox_volume_argmax",
                    "query_type": "feature_select",
                    "target_node_type": "feature",
                    "filters": [
                        {"field": "operation", "op": "eq", "value": "box"},
                        {"field": "metrics.bbox_volume", "op": "exists"},
                    ],
                    "aggregate": {"op": "argmax", "metric": "metrics.bbox_volume"},
                    "return": {"field": "feature_id"},
                    "prompt_template": "box_largest_bbox_volume_feature",
                },
                {
                    "ir_version": QUERY_IR_VERSION,
                    "query_id": "default_box_bbox_y_extent_argmax",
                    "query_type": "feature_select",
                    "target_node_type": "feature",
                    "filters": [
                        {"field": "operation", "op": "eq", "value": "box"},
                        {"field": "metrics.bbox_extent_y", "op": "exists"},
                    ],
                    "aggregate": {"op": "argmax", "metric": "metrics.bbox_extent_y"},
                    "return": {"field": "feature_id"},
                    "prompt_template": "box_largest_bbox_y_extent_feature",
                },
            ]
        )
    if _feature_nodes_with_metric(graph, "metrics.axis_length"):
        queries.append(
            {
                "ir_version": QUERY_IR_VERSION,
                "query_id": "default_axis_length_of_largest_positive_volume_delta",
                "query_type": "feature_metric",
                "target_node_type": "feature",
                "filters": [
                    {"field": "metrics.signed_volume_delta", "op": "exists"},
                    {"field": "metrics.signed_volume_delta", "op": "gt", "value": 0.0},
                    {"field": "metrics.axis_length", "op": "exists"},
                ],
                "aggregate": {"op": "argmax", "metric": "metrics.signed_volume_delta"},
                "return": {"field": "metrics.axis_length"},
                "unit": "mm",
                "prompt_template": "axis_length_of_largest_positive_volume_delta",
            }
        )
    for topology_key in ("face_count", "edge_count", "vertex_count"):
        metric = f"metrics.topology_delta.{topology_key}"
        if not _feature_nodes_with_metric(graph, metric):
            continue
        queries.append(
            {
                "ir_version": QUERY_IR_VERSION,
                "query_id": f"default_{topology_key}_delta_argmax",
                "query_type": "feature_select",
                "target_node_type": "feature",
                "filters": [
                    {"field": metric, "op": "exists"},
                    {"field": metric, "op": "gt", "value": 0},
                ],
                "aggregate": {"op": "argmax", "metric": metric},
                "return": {"field": "feature_id"},
                "prompt_template": f"largest_{topology_key}_increase_feature",
            }
        )
    queries.extend(_default_relation_exists_irs(graph))
    return queries


def graph_query_prompt(
    ir: dict[str, Any], resolution: GraphQueryResolution, code: str
) -> str:
    template = ir.get("prompt_template")
    if template == "largest_abs_signed_volume_delta_feature":
        question = (
            "Given the CadQuery script below, which feature causes the largest absolute volume change?"
        )
    elif template == "operation_metric_immediately_after_ordinal":
        question = _operation_metric_after_ordinal_question(ir)
    elif template == "box_largest_bbox_volume_feature":
        question = (
            "Given the CadQuery script below, of the box features, which one has the larger bounding-box volume?"
        )
    elif template == "box_largest_bbox_y_extent_feature":
        question = (
            "Given the CadQuery script below, of the box features, which one changes the bounding box more on the Y axis?"
        )
    elif template == "axis_length_of_largest_positive_volume_delta":
        question = (
            "Given the CadQuery script below, what is the axis length of the feature that adds the most volume?"
        )
    elif template == "largest_face_count_increase_feature":
        question = (
            "Given the CadQuery script below, which feature increases the face count the most?"
        )
    elif template == "largest_edge_count_increase_feature":
        question = (
            "Given the CadQuery script below, which feature increases the edge count the most?"
        )
    elif template == "largest_vertex_count_increase_feature":
        question = (
            "Given the CadQuery script below, which feature increases the vertex count the most?"
        )
    elif template == "relation_exists":
        question = _relation_exists_question(ir)
    else:
        question = str(
            ir.get("question")
            or "Given the CadQuery script below, resolve the stored graph query."
        )

    choices = resolution.choices or []
    choices_text = f"\n\nChoices: {', '.join(choices)}" if choices else ""
    answer_instruction = _answer_instruction(resolution.answer_type)
    return f"{question} {answer_instruction}{choices_text}\n\n```python\n{code}```"


def _feature_graph_node(
    node: OperationNode,
    *,
    snapshot: dict[str, Any] | None,
    previous_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if snapshot:
        metrics["snapshot_id"] = snapshot.get("snapshot_id")
        metrics["volume"] = snapshot.get("volume")
        metrics["bbox"] = snapshot.get("bbox")
        metrics["topology"] = snapshot.get("topology")
        metrics.update(_bbox_metrics(snapshot.get("bbox")))
    metrics.update(_operation_metrics(node))
    if snapshot and previous_snapshot:
        metrics.update(_delta_metrics(snapshot, previous_snapshot))
    return {
        "id": f"feature:{node.feature_id}",
        "node_type": "feature",
        "feature_id": node.feature_id,
        "operation": node.operation,
        "step_index": node.step_index,
        "source_line": node.source_line,
        "target": node.target,
        "base": node.base,
        "args_repr": list(node.args_repr),
        "input_features": list(node.input_features),
        "metrics": metrics,
        "operation_node": asdict(node),
    }


def _previous_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    sorted_snapshots = sorted(
        snapshots, key=lambda item: int(item.get("step_index", 0))
    )
    previous_by_feature: dict[str, dict[str, Any]] = {}
    for previous, current in zip(sorted_snapshots, sorted_snapshots[1:], strict=False):
        feature_id = current.get("feature_id")
        if isinstance(feature_id, str):
            previous_by_feature[feature_id] = previous
    return previous_by_feature


def _delta_metrics(
    snapshot: dict[str, Any], previous_snapshot: dict[str, Any]
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if _finite_number(snapshot.get("volume")) and _finite_number(
        previous_snapshot.get("volume")
    ):
        delta = float(snapshot["volume"]) - float(previous_snapshot["volume"])
        metrics["signed_volume_delta"] = delta
        metrics["abs_signed_volume_delta"] = abs(delta)
    topology = snapshot.get("topology")
    previous_topology = previous_snapshot.get("topology")
    if isinstance(topology, dict) and isinstance(previous_topology, dict):
        topology_delta: dict[str, int] = {}
        for key, value in topology.items():
            previous_value = previous_topology.get(key)
            if isinstance(value, int) and isinstance(previous_value, int):
                topology_delta[key] = value - previous_value
        metrics["topology_delta"] = topology_delta
    return metrics


def _operation_metric_after_ordinal_irs(
    graph: dict[str, Any],
    *,
    operation: str,
    metric: str,
    return_field: str,
    unit: str | None,
) -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []
    for ordinal in range(1, _operation_count(graph, operation) + 1):
        if _immediately_after_ordinal_feature_with_metric(
            graph, operation=operation, ordinal=ordinal, metric=metric
        ) is None:
            continue
        metric_name = metric.rsplit(".", 1)[-1]
        queries.append(
            {
                "ir_version": QUERY_IR_VERSION,
                "query_id": (
                    "operation_metric_immediately_after_ordinal"
                    f"__{operation}__{ordinal}__{metric_name}"
                ),
                "query_type": "feature_metric",
                "target_node_type": "feature",
                "filters": [
                    {
                        "op": "immediately_after_ordinal",
                        "operation": operation,
                        "ordinal": ordinal,
                    },
                    {"field": metric, "op": "exists"},
                ],
                "return": {"field": return_field},
                "unit": unit,
                "prompt_template": "operation_metric_immediately_after_ordinal",
            }
        )
    return queries


def _operation_metric_after_ordinal_question(ir: dict[str, Any]) -> str:
    ordinal_filter = next(
        (
            item
            for item in ir.get("filters", [])
            if isinstance(item, dict)
            and item.get("op") == "immediately_after_ordinal"
        ),
        {},
    )
    operation = str(ordinal_filter.get("operation", "operation"))
    ordinal = int(ordinal_filter.get("ordinal", 1))
    metric = str(ir.get("return", {}).get("field", "metric"))
    metric_label = _metric_question_label(metric)
    return (
        "Given the CadQuery script below, "
        f"how much {metric_label} is caused by the feature immediately after "
        f"{operation} #{ordinal}?"
    )


def _bbox_metrics(bbox: Any) -> dict[str, Any]:
    if not isinstance(bbox, dict):
        return {}
    minimum = bbox.get("min")
    maximum = bbox.get("max")
    if not _finite_triplet(minimum) or not _finite_triplet(maximum):
        return {}
    extents = [
        float(high) - float(low)
        for low, high in zip(minimum, maximum, strict=True)
    ]
    return {
        "bbox_extent_x": extents[0],
        "bbox_extent_y": extents[1],
        "bbox_extent_z": extents[2],
        "bbox_volume": extents[0] * extents[1] * extents[2],
        "length": max(extents),
    }


def _operation_metrics(node: OperationNode) -> dict[str, Any]:
    numeric_args = [_literal_number(arg) for arg in node.args_repr]
    metrics: dict[str, Any] = {"numeric_args": numeric_args}
    if node.operation == "box" and len(numeric_args) >= 3 and all(
        value is not None for value in numeric_args[:3]
    ):
        x, y, z = (float(value) for value in numeric_args[:3])
        metrics.update(
            {
                "parameter_x": x,
                "parameter_y": y,
                "parameter_z": z,
                "parameter_volume": x * y * z,
                "axis_length": max(abs(x), abs(y), abs(z)),
            }
        )
    if (
        node.operation in {"extrude", "cut_blind"}
        and numeric_args
        and numeric_args[0] is not None
    ):
        metrics["axis_length"] = abs(float(numeric_args[0]))
    return metrics


def _normalize_ir(ir: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(ir)
    normalized.setdefault("ir_version", QUERY_IR_VERSION)
    normalized.setdefault("query_type", "feature_select")
    normalized.setdefault("target_node_type", "feature")
    normalized.setdefault("filters", [])
    normalized.setdefault("return", {"field": "feature_id"})
    return normalized


def _default_relation_exists_irs(graph: dict[str, Any]) -> list[dict[str, Any]]:
    feature_nodes = _sorted_feature_nodes(graph)
    if len(feature_nodes) < 2:
        return []
    queries: list[dict[str, Any]] = []
    for left, right in zip(feature_nodes, feature_nodes[1:], strict=False):
        queries.append(
            _relation_exists_ir(
                relation="before",
                source_feature_id=str(left["feature_id"]),
                target_feature_id=str(right["feature_id"]),
                expected="yes",
            )
        )
        queries.append(
            _relation_exists_ir(
                relation="before",
                source_feature_id=str(right["feature_id"]),
                target_feature_id=str(left["feature_id"]),
                expected="no",
            )
        )
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict) or edge.get("edge_type") != "input_to":
            continue
        source = _feature_id_from_graph_ref(edge.get("source"))
        target = _feature_id_from_graph_ref(edge.get("target"))
        if source is None or target is None:
            continue
        queries.append(
            _relation_exists_ir(
                relation="input_to",
                source_feature_id=source,
                target_feature_id=target,
                expected="yes",
            )
        )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        key = str(query["query_id"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(query)
        if len(deduped) >= MAX_DEFAULT_RELATION_QUERIES:
            break
    return deduped


def _relation_exists_ir(
    *,
    relation: str,
    source_feature_id: str,
    target_feature_id: str,
    expected: str,
) -> dict[str, Any]:
    return {
        "ir_version": QUERY_IR_VERSION,
        "query_id": (
            f"relation_exists__{relation}__{source_feature_id}__{target_feature_id}"
        ),
        "query_type": "relation_exists",
        "target_node_type": "feature_pair",
        "relation": relation,
        "source_feature_id": source_feature_id,
        "target_feature_id": target_feature_id,
        "expected_answer": expected,
        "return": {"field": "relation_exists"},
        "prompt_template": "relation_exists",
    }


def _resolve_relation_exists(
    ir: dict[str, Any], graph: dict[str, Any]
) -> GraphQueryResolution:
    relation = str(ir.get("relation"))
    source = str(ir.get("source_feature_id"))
    target = str(ir.get("target_feature_id"))
    exists = _graph_relation_exists(graph, relation, source, target)
    answer = "yes" if exists else "no"
    graph_query = {
        "graph_version": GRAPH_VERSION,
        "ir": ir,
        "query_type": "relation_exists",
        "target_entity_type": "feature_pair",
        "filters": [],
        "aggregation": None,
        "metric": None,
        "candidate_ids": [source, target],
        "resolved_ids": [source, target] if exists else [],
        "measured_values": [],
        "relation": relation,
        "resolution_status": "ok",
    }
    return GraphQueryResolution(
        status="ok",
        answer=answer,
        answer_type="enum",
        choices=["yes", "no"],
        target_feature_id=target,
        graph_query=graph_query,
        diagnostics={
            "resolver_status": "ok",
            "candidate_count": 2,
            "resolved_ids": graph_query["resolved_ids"],
            "relation": relation,
        },
    )


def _graph_relation_exists(
    graph: dict[str, Any], relation: str, source: str, target: str
) -> bool:
    if relation == "before":
        source_node = _feature_node_by_id(graph, source)
        target_node = _feature_node_by_id(graph, target)
        return (
            source_node is not None
            and target_node is not None
            and int(source_node.get("step_index", -1))
            < int(target_node.get("step_index", -1))
        )
    source_ref = f"feature:{source}"
    target_ref = f"feature:{target}"
    return any(
        isinstance(edge, dict)
        and edge.get("edge_type") == relation
        and edge.get("source") == source_ref
        and edge.get("target") == target_ref
        for edge in graph.get("edges", [])
    )


def _relation_exists_question(ir: dict[str, Any]) -> str:
    relation = str(ir.get("relation", "related_to")).replace("_", " ")
    source = str(ir.get("source_feature_id"))
    target = str(ir.get("target_feature_id"))
    if ir.get("relation") == "before":
        return (
            "Given the CadQuery script below, does feature "
            f"`{source}` occur before feature `{target}` in the operation graph?"
        )
    if ir.get("relation") == "input_to":
        return (
            "Given the CadQuery script below, is feature "
            f"`{source}` an input to feature `{target}` in the operation graph?"
        )
    return (
        "Given the CadQuery script below, does feature "
        f"`{source}` have relation `{relation}` to feature `{target}`?"
    )


def _candidate_feature_nodes(
    graph: dict[str, Any], ir: dict[str, Any]
) -> list[dict[str, Any]]:
    nodes = [
        dict(node)
        for node in graph.get("nodes", [])
        if isinstance(node, dict)
        and node.get("node_type") == ir.get("target_node_type", "feature")
    ]
    for filter_spec in ir.get("filters", []):
        if isinstance(filter_spec, dict):
            nodes = [
                node for node in nodes if _matches_filter(node, filter_spec, graph)
            ]
    return sorted(
        nodes,
        key=lambda item: (
            int(item.get("step_index", 0)),
            str(item.get("feature_id", "")),
        ),
    )


def _matches_filter(
    node: dict[str, Any], filter_spec: dict[str, Any], graph: dict[str, Any]
) -> bool:
    op = filter_spec.get("op")
    if op == "after_ordinal":
        anchor = _ordinal_feature(
            graph, str(filter_spec.get("operation")), int(filter_spec.get("ordinal", 1))
        )
        return anchor is not None and int(node.get("step_index", -1)) > int(
            anchor.get("step_index", -1)
        )
    if op == "immediately_after_ordinal":
        anchor = _ordinal_feature(
            graph, str(filter_spec.get("operation")), int(filter_spec.get("ordinal", 1))
        )
        return anchor is not None and int(node.get("step_index", -1)) == int(
            anchor.get("step_index", -1)
        ) + 1
    if op == "before_ordinal":
        anchor = _ordinal_feature(
            graph, str(filter_spec.get("operation")), int(filter_spec.get("ordinal", 1))
        )
        return anchor is not None and int(node.get("step_index", -1)) < int(
            anchor.get("step_index", -1)
        )

    field = str(filter_spec.get("field", ""))
    value = _field_value(node, field)
    expected = filter_spec.get("value")
    if op == "exists":
        return value is not None
    if op == "eq":
        return value == expected
    if op == "neq":
        return value != expected
    if op == "in":
        return isinstance(expected, list) and value in expected
    if op == "gt":
        return (
            _finite_number(value)
            and _finite_number(expected)
            and float(value) > float(expected)
        )
    if op == "gte":
        return (
            _finite_number(value)
            and _finite_number(expected)
            and float(value) >= float(expected)
        )
    if op == "lt":
        return (
            _finite_number(value)
            and _finite_number(expected)
            and float(value) < float(expected)
        )
    if op == "lte":
        return (
            _finite_number(value)
            and _finite_number(expected)
            and float(value) <= float(expected)
        )
    return False


def _ordinal_feature(
    graph: dict[str, Any], operation: str, ordinal: int
) -> dict[str, Any] | None:
    matches = [
        node
        for node in graph.get("nodes", [])
        if isinstance(node, dict)
        and node.get("node_type") == "feature"
        and node.get("operation") == operation
    ]
    matches = sorted(matches, key=lambda item: int(item.get("step_index", 0)))
    if ordinal < 1 or ordinal > len(matches):
        return None
    return matches[ordinal - 1]


def _operation_count(graph: dict[str, Any], operation: str) -> int:
    return sum(
        1
        for node in graph.get("nodes", [])
        if isinstance(node, dict)
        and node.get("node_type") == "feature"
        and node.get("operation") == operation
    )


def _sorted_feature_nodes(graph: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [
            node
            for node in graph.get("nodes", [])
            if isinstance(node, dict) and node.get("node_type") == "feature"
        ],
        key=lambda item: (
            int(item.get("step_index", 0)),
            str(item.get("feature_id", "")),
        ),
    )


def _feature_node_by_id(graph: dict[str, Any], feature_id: str) -> dict[str, Any] | None:
    for node in graph.get("nodes", []):
        if (
            isinstance(node, dict)
            and node.get("node_type") == "feature"
            and node.get("feature_id") == feature_id
        ):
            return node
    return None


def _feature_id_from_graph_ref(value: Any) -> str | None:
    if not isinstance(value, str) or not value.startswith("feature:"):
        return None
    feature_id = value.removeprefix("feature:")
    return feature_id or None


def _immediately_after_ordinal_feature_with_metric(
    graph: dict[str, Any], *, operation: str, ordinal: int, metric: str
) -> dict[str, Any] | None:
    anchor = _ordinal_feature(graph, operation, ordinal)
    if anchor is None:
        return None
    target_step = int(anchor.get("step_index", -1)) + 1
    for node in graph.get("nodes", []):
        if not isinstance(node, dict) or node.get("node_type") != "feature":
            continue
        if int(node.get("step_index", -1)) != target_step:
            continue
        if _field_value(node, metric) is not None:
            return node
    return None


def _resolve_arg_extreme(
    ir: dict[str, Any],
    candidates: list[dict[str, Any]],
    aggregate: dict[str, Any],
    *,
    config: DatasetConfig,
) -> GraphQueryResolution:
    metric = str(aggregate.get("metric", ""))
    measured = [
        {"feature_id": str(node["feature_id"]), "value": _field_value(node, metric)}
        for node in candidates
        if _finite_number(_field_value(node, metric))
    ]
    if not measured:
        return _failed_resolution(ir, "missing_metric_values", candidates=candidates)
    reverse = aggregate.get("op") == "argmax"
    measured = sorted(measured, key=lambda item: float(item["value"]), reverse=reverse)
    best_value = float(measured[0]["value"])
    ties = [
        item
        for item in measured
        if math.isclose(float(item["value"]), best_value, rel_tol=0.0, abs_tol=0.0)
    ]
    if len(ties) > 1:
        return _failed_resolution(
            ir, "ambiguous_metric_tie", candidates=candidates, measured_values=measured
        )
    answer_feature_id = str(measured[0]["feature_id"])
    selected = next(
        node for node in candidates if node.get("feature_id") == answer_feature_id
    )
    answer = _field_value(
        selected, str(ir.get("return", {}).get("field", "feature_id"))
    )
    return _resolution_from_answer(
        ir,
        candidates,
        answer,
        target_feature_id=answer_feature_id,
        config=config,
        measured_values=measured,
    )


def _resolution_from_answer(
    ir: dict[str, Any],
    candidates: list[dict[str, Any]],
    answer: Any,
    *,
    target_feature_id: str | None,
    config: DatasetConfig,
    measured_values: list[dict[str, Any]] | None = None,
) -> GraphQueryResolution:
    answer_type = _answer_type(answer)
    resolved_ids = [target_feature_id] if target_feature_id else []
    graph_query = _resolved_query_payload(
        ir, candidates, resolved_ids=resolved_ids, measured_values=measured_values or []
    )
    choices = (
        [str(node["feature_id"]) for node in candidates]
        if answer_type == "choice"
        else None
    )
    return GraphQueryResolution(
        status="ok",
        answer=answer,
        answer_type=answer_type,
        choices=choices,
        target_feature_id=target_feature_id,
        graph_query=graph_query,
        diagnostics={
            "resolver_status": "ok",
            "candidate_count": len(candidates),
            "resolved_ids": resolved_ids,
            "measured_value_count": len(measured_values or []),
        },
        unit=str(ir.get("unit")) if isinstance(ir.get("unit"), str) else None,
        numeric_tolerance=config.label_policy.linear_tolerance_mm
        if answer_type == "number"
        else None,
    )


def _resolved_query_payload(
    ir: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    resolved_ids: list[str | None],
    measured_values: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "graph_version": GRAPH_VERSION,
        "ir": ir,
        "query_type": ir.get("query_type"),
        "target_entity_type": ir.get("target_node_type"),
        "filters": ir.get("filters", []),
        "aggregation": ir.get("aggregate", {}).get("op")
        if isinstance(ir.get("aggregate"), dict)
        else None,
        "metric": ir.get("aggregate", {}).get("metric")
        if isinstance(ir.get("aggregate"), dict)
        else None,
        "candidate_ids": [str(node["feature_id"]) for node in candidates],
        "resolved_ids": [item for item in resolved_ids if item is not None],
        "measured_values": measured_values,
        "resolution_status": "ok",
    }


def _failed_resolution(
    ir: dict[str, Any],
    reason: str,
    *,
    candidates: list[dict[str, Any]],
    measured_values: list[dict[str, Any]] | None = None,
) -> GraphQueryResolution:
    graph_query = _resolved_query_payload(
        ir, candidates, resolved_ids=[], measured_values=measured_values or []
    )
    graph_query["resolution_status"] = reason
    return GraphQueryResolution(
        status=reason,
        answer=None,
        answer_type=None,
        choices=None,
        target_feature_id=None,
        graph_query=graph_query,
        diagnostics={"resolver_status": reason, "candidate_count": len(candidates)},
    )


def _feature_nodes_with_metric(
    graph: dict[str, Any], metric: str
) -> list[dict[str, Any]]:
    return [
        node
        for node in graph.get("nodes", [])
        if isinstance(node, dict)
        and node.get("node_type") == "feature"
        and _finite_number(_field_value(node, metric))
    ]


def _field_value(node: dict[str, Any], path: str) -> Any:
    current: Any = node
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _metric_question_label(metric: str) -> str:
    labels = {
        "metrics.signed_volume_delta": "signed volume delta",
        "metrics.abs_signed_volume_delta": "absolute signed volume delta",
        "metrics.axis_length": "axis length",
    }
    return labels.get(metric, metric.removeprefix("metrics.").replace("_", " "))


def _literal_number(value: str) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _finite_triplet(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 3
        and all(_finite_number(item) for item in value)
    )


def _answer_type(answer: Any) -> str | None:
    if isinstance(answer, int) and not isinstance(answer, bool):
        return "integer"
    if (
        isinstance(answer, (int, float))
        and not isinstance(answer, bool)
        and math.isfinite(float(answer))
    ):
        return "number"
    if isinstance(answer, str):
        return "choice"
    return None


def _answer_instruction(answer_type: str | None) -> str:
    if answer_type == "integer":
        return "Answer with exactly one non-negative integer."
    if answer_type == "number":
        return "Answer with exactly one finite number."
    if answer_type == "enum":
        return "Answer with exactly one allowed token."
    return "Answer with exactly one listed feature ID."


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )
