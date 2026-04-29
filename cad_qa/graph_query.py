"""Typed graph-query IR construction and deterministic resolution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

from cad_qa.config import DatasetConfig
from cad_qa.schema import OperationNode, TraceRecord

GRAPH_VERSION = "cadqa_typed_graph_v1"
QUERY_IR_VERSION = "cadqa_graph_query_ir_v1"


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


def build_typed_query_graph(nodes: list[OperationNode], trace: TraceRecord) -> dict[str, Any]:
    """Build a public-safe typed graph from operation nodes and trace metadata."""

    sorted_nodes = sorted((node for node in nodes if node.status == "ok"), key=lambda node: node.step_index)
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
        graph_nodes.append(_feature_graph_node(node, snapshot=snapshot, previous_snapshot=previous_snapshot))
        for input_feature in node.input_features:
            graph_edges.append(
                {
                    "source": f"feature:{input_feature}",
                    "target": f"feature:{node.feature_id}",
                    "edge_type": "input_to",
                }
            )

    for before, after in zip(sorted_nodes, sorted_nodes[1:], strict=False):
        graph_edges.append({"source": f"feature:{before.feature_id}", "target": f"feature:{after.feature_id}", "edge_type": "before"})
        graph_edges.append({"source": f"feature:{after.feature_id}", "target": f"feature:{before.feature_id}", "edge_type": "after"})

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
    candidates = _candidate_feature_nodes(graph, normalized_ir)
    if not candidates:
        return _failed_resolution(normalized_ir, "empty_candidate_set", candidates=[])

    aggregate = normalized_ir.get("aggregate") if isinstance(normalized_ir.get("aggregate"), dict) else {}
    aggregate_op = aggregate.get("op")
    if aggregate_op in {"argmax", "argmin"}:
        return _resolve_arg_extreme(normalized_ir, candidates, aggregate, config=config)
    if aggregate_op == "count":
        resolved_ids = [str(node["feature_id"]) for node in candidates]
        graph_query = _resolved_query_payload(normalized_ir, candidates, resolved_ids=resolved_ids, measured_values=[])
        return GraphQueryResolution(
            status="ok",
            answer=len(candidates),
            answer_type="integer",
            choices=None,
            target_feature_id=None,
            graph_query=graph_query,
            diagnostics={"resolver_status": "ok", "candidate_count": len(candidates), "resolved_ids": resolved_ids},
        )

    if len(candidates) != 1:
        return _failed_resolution(normalized_ir, "ambiguous_candidate_set", candidates=candidates)
    node = candidates[0]
    answer = _field_value(node, str(normalized_ir.get("return", {}).get("field", "feature_id")))
    return _resolution_from_answer(normalized_ir, candidates, answer, target_feature_id=str(node["feature_id"]), config=config)


def default_graph_query_irs(graph: dict[str, Any]) -> list[dict[str, Any]]:
    if not _feature_nodes_with_metric(graph, "metrics.abs_signed_volume_delta"):
        return []
    return [
        {
            "ir_version": QUERY_IR_VERSION,
            "query_id": "default_abs_volume_delta_argmax",
            "query_type": "feature_select",
            "target_node_type": "feature",
            "filters": [
                {"field": "metrics.abs_signed_volume_delta", "op": "exists"},
                {"field": "metrics.abs_signed_volume_delta", "op": "gt", "value": 0.0},
            ],
            "aggregate": {"op": "argmax", "metric": "metrics.abs_signed_volume_delta"},
            "return": {"field": "feature_id"},
            "prompt_template": "largest_abs_signed_volume_delta_feature",
        },
        {
            "ir_version": QUERY_IR_VERSION,
            "query_id": "default_snapshot_feature_count",
            "query_type": "feature_count",
            "target_node_type": "feature",
            "filters": [{"field": "metrics.snapshot_id", "op": "exists"}],
            "aggregate": {"op": "count"},
            "return": {"field": "count"},
            "prompt_template": "snapshot_feature_count",
        },
    ]


def graph_query_prompt(ir: dict[str, Any], resolution: GraphQueryResolution, code: str) -> str:
    template = ir.get("prompt_template")
    if template == "snapshot_feature_count":
        question = "Given the CadQuery script below, how many traced features have an intermediate geometry snapshot?"
        return f"{question} Answer with exactly one non-negative integer.\n\n```python\n{code}```"

    if template == "largest_abs_signed_volume_delta_feature":
        question = (
            "Given the CadQuery script below, which traced feature has the largest absolute signed volume delta "
            "among features with measured adjacent snapshots?"
        )
    else:
        question = str(ir.get("question") or "Given the CadQuery script below, resolve the stored graph query.")

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
    sorted_snapshots = sorted(snapshots, key=lambda item: int(item.get("step_index", 0)))
    previous_by_feature: dict[str, dict[str, Any]] = {}
    for previous, current in zip(sorted_snapshots, sorted_snapshots[1:], strict=False):
        feature_id = current.get("feature_id")
        if isinstance(feature_id, str):
            previous_by_feature[feature_id] = previous
    return previous_by_feature


def _delta_metrics(snapshot: dict[str, Any], previous_snapshot: dict[str, Any]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if _finite_number(snapshot.get("volume")) and _finite_number(previous_snapshot.get("volume")):
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


def _normalize_ir(ir: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(ir)
    normalized.setdefault("ir_version", QUERY_IR_VERSION)
    normalized.setdefault("query_type", "feature_select")
    normalized.setdefault("target_node_type", "feature")
    normalized.setdefault("filters", [])
    normalized.setdefault("return", {"field": "feature_id"})
    return normalized


def _candidate_feature_nodes(graph: dict[str, Any], ir: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = [
        dict(node)
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("node_type") == ir.get("target_node_type", "feature")
    ]
    for filter_spec in ir.get("filters", []):
        if isinstance(filter_spec, dict):
            nodes = [node for node in nodes if _matches_filter(node, filter_spec, graph)]
    return sorted(nodes, key=lambda item: (int(item.get("step_index", 0)), str(item.get("feature_id", ""))))


def _matches_filter(node: dict[str, Any], filter_spec: dict[str, Any], graph: dict[str, Any]) -> bool:
    op = filter_spec.get("op")
    if op == "after_ordinal":
        anchor = _ordinal_feature(graph, str(filter_spec.get("operation")), int(filter_spec.get("ordinal", 1)))
        return anchor is not None and int(node.get("step_index", -1)) > int(anchor.get("step_index", -1))
    if op == "before_ordinal":
        anchor = _ordinal_feature(graph, str(filter_spec.get("operation")), int(filter_spec.get("ordinal", 1)))
        return anchor is not None and int(node.get("step_index", -1)) < int(anchor.get("step_index", -1))

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
        return _finite_number(value) and _finite_number(expected) and float(value) > float(expected)
    if op == "gte":
        return _finite_number(value) and _finite_number(expected) and float(value) >= float(expected)
    if op == "lt":
        return _finite_number(value) and _finite_number(expected) and float(value) < float(expected)
    if op == "lte":
        return _finite_number(value) and _finite_number(expected) and float(value) <= float(expected)
    return False


def _ordinal_feature(graph: dict[str, Any], operation: str, ordinal: int) -> dict[str, Any] | None:
    matches = [
        node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("node_type") == "feature" and node.get("operation") == operation
    ]
    matches = sorted(matches, key=lambda item: int(item.get("step_index", 0)))
    if ordinal < 1 or ordinal > len(matches):
        return None
    return matches[ordinal - 1]


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
    ties = [item for item in measured if math.isclose(float(item["value"]), best_value, rel_tol=0.0, abs_tol=0.0)]
    if len(ties) > 1:
        return _failed_resolution(ir, "ambiguous_metric_tie", candidates=candidates, measured_values=measured)
    answer_feature_id = str(measured[0]["feature_id"])
    selected = next(node for node in candidates if node.get("feature_id") == answer_feature_id)
    answer = _field_value(selected, str(ir.get("return", {}).get("field", "feature_id")))
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
    graph_query = _resolved_query_payload(ir, candidates, resolved_ids=resolved_ids, measured_values=measured_values or [])
    choices = [str(node["feature_id"]) for node in candidates] if answer_type == "choice" else None
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
        numeric_tolerance=config.label_policy.linear_tolerance_mm if answer_type == "number" else None,
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
        "aggregation": ir.get("aggregate", {}).get("op") if isinstance(ir.get("aggregate"), dict) else None,
        "metric": ir.get("aggregate", {}).get("metric") if isinstance(ir.get("aggregate"), dict) else None,
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
    graph_query = _resolved_query_payload(ir, candidates, resolved_ids=[], measured_values=measured_values or [])
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


def _feature_nodes_with_metric(graph: dict[str, Any], metric: str) -> list[dict[str, Any]]:
    return [
        node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("node_type") == "feature" and _finite_number(_field_value(node, metric))
    ]


def _field_value(node: dict[str, Any], path: str) -> Any:
    current: Any = node
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _answer_type(answer: Any) -> str | None:
    if isinstance(answer, int) and not isinstance(answer, bool):
        return "integer"
    if isinstance(answer, (int, float)) and not isinstance(answer, bool) and math.isfinite(float(answer)):
        return "number"
    if isinstance(answer, str):
        return "choice"
    return None


def _answer_instruction(answer_type: str | None) -> str:
    if answer_type == "integer":
        return "Answer with exactly one non-negative integer."
    if answer_type == "number":
        return "Answer with exactly one finite number."
    return "Answer with exactly one listed feature ID."


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))
