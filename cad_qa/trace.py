"""Optional isolated CadQuery trace execution."""

from __future__ import annotations

import ast
import builtins
from dataclasses import asdict
import math
import multiprocessing as mp
from queue import Empty
import sys
import time
from typing import Any

from cad_qa.config import DatasetConfig
from cad_qa.hashing import sha256_json
from cad_qa.operation_graph import (
    extract_operation_graph,
    operation_graph_hash,
    operation_nodes_to_dicts,
)
from cad_qa.safety import safety_issues
from cad_qa.schema import SourceRecord, TraceRecord


def trace_source_record(
    source: SourceRecord,
    *,
    config: DatasetConfig,
    isolated: bool = True,
) -> TraceRecord:
    nodes, result_variable, graph_issues = extract_operation_graph(source.normalized_code)
    graph_status = "ok" if nodes and not graph_issues else ("partial" if nodes else "failed")
    graph_hash = operation_graph_hash(nodes)
    if graph_status == "failed":
        return _failed_trace(
            source,
            config,
            operation_nodes=operation_nodes_to_dicts(nodes),
            result_variable=result_variable,
            operation_graph_status=graph_status,
            failure_reason="operation_graph_unsupported",
            graph_hash=graph_hash,
        )

    issues = safety_issues(source.normalized_code)
    if issues:
        return _failed_trace(
            source,
            config,
            operation_nodes=operation_nodes_to_dicts(nodes),
            result_variable=result_variable,
            operation_graph_status=graph_status,
            failure_reason=issues[0],
            graph_hash=graph_hash,
        )

    if isolated:
        result = _trace_isolated(source.normalized_code, timeout_seconds=config.trace_timeout_seconds)
    else:
        result = _trace_worker_payload(source.normalized_code)
    if result["status"] != "ok":
        return _failed_trace(
            source,
            config,
            operation_nodes=operation_nodes_to_dicts(nodes),
            result_variable=result_variable,
            operation_graph_status=graph_status,
            failure_reason=str(result["failure_reason"]),
            graph_hash=graph_hash,
            environment=result.get("environment", {}),
        )

    snapshots = _attach_feature_ids(result["snapshots"], nodes)
    selector_tables = _attach_table_feature_ids(result.get("selector_tables", []), nodes)
    point_queries = _attach_table_feature_ids(result.get("point_queries", []), nodes)
    provenance_records = _attach_table_feature_ids(result.get("provenance_records", []), nodes)
    trace_payload = {
        "source_id": source.source_id,
        "graph_hash": graph_hash,
        "snapshots": snapshots,
        "selector_tables": selector_tables,
        "point_queries": point_queries,
        "provenance_records": provenance_records,
        "label_policy": asdict(config.label_policy),
        "environment": result["environment"],
    }
    return TraceRecord(
        trace_id="trace_" + sha256_json(trace_payload).removeprefix("sha256:")[:16],
        source_id=source.source_id,
        operation_graph_status=graph_status,
        execution_status="ok",
        result_variable=result_variable,
        operation_nodes=operation_nodes_to_dicts(nodes),
        snapshots=snapshots,
        label_policy=asdict(config.label_policy),
        environment=result["environment"],
        hashes={
            **source.hashes,
            "operation_graph_hash": graph_hash,
            "trace_hash": sha256_json(trace_payload),
            "config_hash": config.config_hash,
        },
        failure_reason=None,
        selector_tables=selector_tables,
        point_queries=point_queries,
        provenance_records=provenance_records,
    )


def trace_source_records_bounded(
    sources: list[SourceRecord],
    *,
    config: DatasetConfig,
    worker_count: int | None = None,
) -> list[TraceRecord]:
    """Trace sources in bounded worker processes, preserving input order."""
    worker_count = max(1, worker_count or config.worker_count)
    if worker_count <= 1:
        return [trace_source_record(source, config=config, isolated=True) for source in sources]

    context = mp.get_context("spawn")
    pending = list(enumerate(sources))
    running: list[dict[str, Any]] = []
    results: list[TraceRecord | None] = [None] * len(sources)

    def start_next() -> None:
        if not pending:
            return
        index, source = pending.pop(0)
        queue: mp.Queue = context.Queue(maxsize=1)
        process = context.Process(target=_trace_record_worker, args=(source, config, queue))
        process.start()
        running.append({"index": index, "source": source, "queue": queue, "process": process, "started_at": time.monotonic()})

    for _ in range(min(worker_count, len(pending))):
        start_next()

    while running:
        made_progress = False
        for job in list(running):
            process: mp.Process = job["process"]
            elapsed = time.monotonic() - float(job["started_at"])
            if process.is_alive() and elapsed <= config.trace_timeout_seconds:
                continue
            source: SourceRecord = job["source"]
            if process.is_alive():
                process.terminate()
                process.join(1.0)
                result = _timeout_trace(source, config)
            else:
                process.join()
                result = _trace_from_worker_queue(source, config, job["queue"], process.exitcode)
            running.remove(job)
            results[int(job["index"])] = result
            made_progress = True
            start_next()
        if not made_progress:
            time.sleep(0.05)

    return [trace for trace in results if trace is not None]


def _trace_record_worker(source: SourceRecord, config: DatasetConfig, queue: mp.Queue) -> None:
    queue.put(trace_source_record(source, config=config, isolated=False))


def _trace_from_worker_queue(source: SourceRecord, config: DatasetConfig, queue: mp.Queue, exitcode: int | None) -> TraceRecord:
    if exitcode != 0:
        return _timeout_trace(source, config, failure_reason="worker_crash")
    try:
        value = queue.get_nowait()
    except Empty:
        return _timeout_trace(source, config, failure_reason="worker_crash")
    if isinstance(value, TraceRecord):
        return value
    return _timeout_trace(source, config, failure_reason="worker_crash")


def _timeout_trace(source: SourceRecord, config: DatasetConfig, failure_reason: str = "execution_timeout") -> TraceRecord:
    nodes, result_variable, _ = extract_operation_graph(source.normalized_code)
    return _failed_trace(
        source,
        config,
        operation_nodes=operation_nodes_to_dicts(nodes),
        result_variable=result_variable,
        operation_graph_status="ok" if nodes else "failed",
        failure_reason=failure_reason,
        graph_hash=operation_graph_hash(nodes),
    )


def _trace_isolated(code: str, *, timeout_seconds: float) -> dict[str, Any]:
    context = mp.get_context("spawn")
    queue: mp.Queue = context.Queue(maxsize=1)
    process = context.Process(target=_worker_main, args=(code, queue))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(1.0)
        return {"status": "error", "failure_reason": "execution_timeout", "environment": _base_environment()}
    if process.exitcode != 0:
        return {"status": "error", "failure_reason": "worker_crash", "environment": _base_environment()}
    try:
        return queue.get_nowait()
    except Empty:
        return {"status": "error", "failure_reason": "worker_crash", "environment": _base_environment()}


def _worker_main(code: str, queue: mp.Queue) -> None:
    try:
        queue.put(_trace_worker_payload(code))
    except Exception as exc:
        queue.put({"status": "error", "failure_reason": f"unknown_error:{type(exc).__name__}", "environment": _base_environment()})


def _trace_worker_payload(code: str) -> dict[str, Any]:
    started = time.monotonic()
    try:
        import cadquery as cq  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return {"status": "error", "failure_reason": "cadquery_unavailable", "environment": _base_environment()}

    environment = _base_environment()
    environment["cadquery_version"] = getattr(cq, "__version__", None)
    try:
        import OCP  # type: ignore[import-not-found]

        environment["ocp_version"] = getattr(OCP, "__version__", None)
    except Exception:
        environment["ocp_version"] = None

    namespace: dict[str, Any] = {"cq": cq, "cadquery": cq, "__builtins__": _safe_builtins()}
    snapshots: list[dict[str, Any]] = []
    selector_tables: list[dict[str, Any]] = []
    point_queries: list[dict[str, Any]] = []
    provenance_records: list[dict[str, Any]] = []
    try:
        tree = ast.parse(code)
        for statement_index, statement in enumerate(tree.body):
            exec(compile(ast.Module([statement], []), "<cadqa-trace>", "exec"), namespace)
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
                target = statement.targets[0].id
                if target in namespace:
                    snapshot = _snapshot_for_object(namespace[target], target, statement_index)
                    if snapshot is not None:
                        snapshots.append(snapshot)
                        selector_tables.extend(_selector_tables_for_statement(statement, snapshot, namespace))
            elif isinstance(statement, ast.Expr):
                selector = _selector_table_for_expr(statement, namespace, statement_index)
                if selector is not None:
                    selector_tables.append(selector)
        point_queries = _point_queries_for_final_state(namespace, snapshots)
        provenance_records = _conservative_provenance_records(snapshots)
    except Exception as exc:
        return {
            "status": "error",
            "failure_reason": f"source_exec_error:{type(exc).__name__}",
            "environment": environment,
            "snapshots": snapshots,
            "selector_tables": selector_tables,
            "point_queries": point_queries,
            "provenance_records": provenance_records,
        }
    environment["elapsed_seconds"] = round(time.monotonic() - started, 6)
    return {
        "status": "ok",
        "snapshots": snapshots,
        "selector_tables": selector_tables,
        "point_queries": point_queries,
        "provenance_records": provenance_records,
        "environment": environment,
    }


def _snapshot_for_object(obj: Any, target: str, step_index: int) -> dict[str, Any] | None:
    shape = _shape_from_object(obj)
    if shape is None:
        return None
    volume = _call_number(shape, "Volume")
    bbox = _bbox(shape)
    topology = _topology(shape)
    return {
        "snapshot_id": f"snap_{target}_{step_index:04d}",
        "feature_id": target,
        "step_index": step_index,
        "shape_status": "ok" if volume is not None or bbox is not None else "failed",
        "volume": volume,
        "bbox": bbox,
        "topology": topology,
        "entity_ids": None,
        "diagnostics": {"snapshot_target": target},
    }


def _shape_from_object(obj: Any) -> Any | None:
    if obj is None:
        return None
    if hasattr(obj, "val"):
        try:
            return obj.val()
        except Exception:
            return None
    if hasattr(obj, "Volume") or hasattr(obj, "BoundingBox"):
        return obj
    return None


def _call_number(obj: Any, name: str) -> float | None:
    method = getattr(obj, name, None)
    if method is None:
        return None
    try:
        value = method()
        return float(value)
    except Exception:
        return None


def _bbox(shape: Any) -> dict[str, list[float]] | None:
    try:
        box = shape.BoundingBox()
        return {
            "min": [float(box.xmin), float(box.ymin), float(box.zmin)],
            "max": [float(box.xmax), float(box.ymax), float(box.zmax)],
        }
    except Exception:
        return None


def _topology(shape: Any) -> dict[str, int | None]:
    return {
        "solid_count": _count(shape, "Solids"),
        "face_count": _count(shape, "Faces"),
        "edge_count": _count(shape, "Edges"),
        "vertex_count": _count(shape, "Vertices"),
        "wire_count": _count(shape, "Wires"),
        "planar_face_count": None,
        "cylindrical_face_count": None,
        "circular_edge_count": None,
        "x_parallel_edge_count": None,
        "y_parallel_edge_count": None,
        "z_parallel_edge_count": None,
    }


def _count(shape: Any, method_name: str) -> int:
    method = getattr(shape, method_name, None)
    if method is None:
        return 0
    try:
        return len(method())
    except Exception:
        return 0


def _selector_tables_for_statement(
    statement: ast.Assign,
    snapshot: dict[str, Any],
    namespace: dict[str, Any],
) -> list[dict[str, Any]]:
    calls = [node for node in ast.walk(statement.value) if isinstance(node, ast.Call)]
    tables: list[dict[str, Any]] = []
    for call in calls:
        if isinstance(call.func, ast.Attribute) and call.func.attr in {"faces", "edges", "vertices", "wires", "solids"}:
            tables.append(_selector_table_from_call(call, snapshot.get("feature_id"), namespace))
    return tables


def _selector_table_for_expr(statement: ast.Expr, namespace: dict[str, Any], statement_index: int) -> dict[str, Any] | None:
    del statement_index
    if isinstance(statement.value, ast.Call) and isinstance(statement.value.func, ast.Attribute):
        if statement.value.func.attr in {"faces", "edges", "vertices", "wires", "solids"}:
            return _selector_table_from_call(statement.value, None, namespace)
    return None


def _selector_table_from_call(call: ast.Call, target_feature_id: Any, namespace: dict[str, Any]) -> dict[str, Any]:
    expression = ast.unparse(call)
    entity_type = call.func.attr.removesuffix("s") if isinstance(call.func, ast.Attribute) else "entity"
    selected_count: int | None = None
    raw_entity_ids: list[str] = []
    status = "recorded_expression"
    try:
        selected = eval(compile(ast.Expression(call), "<cadqa-selector>", "eval"), namespace)  # noqa: S307
        selected_count = _selected_count(selected)
        raw_entity_ids = [f"{entity_type}_{index:04d}" for index in range(selected_count)]
        status = "ok"
    except Exception as exc:
        status = f"selector_eval_failed:{type(exc).__name__}"
    return {
        "selector_expression": expression,
        "target_feature_id": target_feature_id,
        "entity_type": entity_type,
        "raw_entity_ids": raw_entity_ids,
        "dedup_entity_ids": raw_entity_ids,
        "selected_count": selected_count,
        "status": status,
    }


def _selected_count(selected: Any) -> int:
    if hasattr(selected, "vals"):
        try:
            return len(selected.vals())
        except Exception:
            pass
    objects = getattr(selected, "objects", None)
    if isinstance(objects, list):
        return len(objects)
    if isinstance(selected, (list, tuple, set)):
        return len(selected)
    return 1 if selected is not None else 0


def _point_queries_for_final_state(namespace: dict[str, Any], snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not snapshots:
        return []
    final_snapshot = snapshots[-1]
    bbox = final_snapshot.get("bbox")
    if not isinstance(bbox, dict):
        return []
    final_object = _final_object(namespace, str(final_snapshot.get("feature_id")))
    shape = _shape_from_object(final_object)
    if shape is None:
        return []
    minimum = bbox.get("min")
    maximum = bbox.get("max")
    if not (_finite_triplet(minimum) and _finite_triplet(maximum)):
        return []
    center = [(float(minimum[i]) + float(maximum[i])) / 2.0 for i in range(3)]
    span = max(max(float(maximum[i]) - float(minimum[i]), 1.0) for i in range(3))
    outside = [float(maximum[0]) + 0.25 * span, center[1], center[2]]
    candidates = [("bbox_center", center), ("bbox_outside_x", outside)]
    rows: list[dict[str, Any]] = []
    for stratum, point in candidates:
        classification = _classify_point(shape, point, namespace)
        if classification is None:
            continue
        rows.append(
            {
                "point": point,
                "target_feature_id": final_snapshot.get("feature_id"),
                "point_classification": classification,
                "sampling_stratum": "deep_inside" if classification == "inside" else "deep_outside",
                "classifier": "cadquery_shape_isInside",
                "sample_source": stratum,
            }
        )
    return rows


def _final_object(namespace: dict[str, Any], fallback_name: str) -> Any:
    for name in ("result", "shape", "solid", "part", fallback_name):
        if name in namespace:
            return namespace[name]
    return None


def _classify_point(shape: Any, point: list[float], namespace: dict[str, Any]) -> str | None:
    vector = point
    cq = namespace.get("cq") or namespace.get("cadquery")
    if cq is not None and hasattr(cq, "Vector"):
        try:
            vector = cq.Vector(*point)
        except Exception:
            vector = point
    method = getattr(shape, "isInside", None)
    if method is None:
        return None
    try:
        inside = bool(method(vector, 1e-6))
    except TypeError:
        try:
            inside = bool(method(point, 1e-6))
        except Exception:
            return None
    except Exception:
        return None
    return "inside" if inside else "outside"


def _conservative_provenance_records(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for previous, current in zip(snapshots, snapshots[1:], strict=False):
        before = previous.get("volume")
        after = current.get("volume")
        if not (isinstance(before, (int, float)) and isinstance(after, (int, float))):
            continue
        delta = float(after) - float(before)
        if math.isclose(delta, 0.0, abs_tol=1e-6):
            continue
        relation = "created_by" if delta > 0 else "deleted_by"
        records.append(
            {
                "target_description": f"material region changed by {current.get('feature_id')}",
                "target_feature_id": current.get("feature_id"),
                "provenance_relation": relation,
                "answer_feature_id": current.get("feature_id"),
                "matching_method": "adjacent_snapshot_volume_delta",
                "provenance_confidence": 0.6,
            }
        )
    return records


def _finite_triplet(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 3 and all(isinstance(item, (int, float)) and math.isfinite(float(item)) for item in value)


def _attach_feature_ids(snapshots: list[dict[str, Any]], nodes: list[Any]) -> list[dict[str, Any]]:
    target_to_node = {node.target: node for node in nodes if node.target}
    updated: list[dict[str, Any]] = []
    for snapshot in snapshots:
        copy = dict(snapshot)
        target = copy.get("feature_id")
        node = target_to_node.get(str(target))
        if node is not None:
            copy["feature_id"] = node.feature_id
            copy["step_index"] = node.step_index
            copy["snapshot_id"] = f"snap_{node.feature_id}_{node.step_index:04d}"
        updated.append(copy)
    return updated


def _attach_table_feature_ids(records: list[dict[str, Any]], nodes: list[Any]) -> list[dict[str, Any]]:
    target_to_feature = {node.target: node.feature_id for node in nodes if node.target}
    updated: list[dict[str, Any]] = []
    for record in records:
        copy = dict(record)
        for key in ("target_feature_id", "answer_feature_id", "feature_id"):
            value = copy.get(key)
            if value in target_to_feature:
                copy[key] = target_to_feature[value]
        updated.append(copy)
    return updated


def _safe_builtins() -> dict[str, Any]:
    allowed_names = {
        "abs",
        "bool",
        "dict",
        "enumerate",
        "float",
        "int",
        "len",
        "list",
        "max",
        "min",
        "pow",
        "range",
        "round",
        "set",
        "str",
        "sum",
        "tuple",
        "zip",
        "__import__",
    }
    return {name: getattr(builtins, name) for name in allowed_names if hasattr(builtins, name)}


def _base_environment() -> dict[str, Any]:
    return {"python_version": sys.version.split()[0], "cadquery_version": None, "ocp_version": None}


def _failed_trace(
    source: SourceRecord,
    config: DatasetConfig,
    *,
    operation_nodes: list[dict[str, Any]],
    result_variable: str | None,
    operation_graph_status: str,
    failure_reason: str,
    graph_hash: str,
    environment: dict[str, Any] | None = None,
) -> TraceRecord:
    payload = {
        "source_id": source.source_id,
        "failure_reason": failure_reason,
        "graph_hash": graph_hash,
        "config_hash": config.config_hash,
    }
    return TraceRecord(
        trace_id="trace_" + sha256_json(payload).removeprefix("sha256:")[:16],
        source_id=source.source_id,
        operation_graph_status=operation_graph_status,
        execution_status="failed",
        result_variable=result_variable,
        operation_nodes=operation_nodes,
        snapshots=[],
        label_policy=asdict(config.label_policy),
        environment=environment or _base_environment(),
        hashes={
            **source.hashes,
            "operation_graph_hash": graph_hash,
            "trace_hash": sha256_json(payload),
            "config_hash": config.config_hash,
        },
        failure_reason=failure_reason,
    )
