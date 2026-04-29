"""Optional isolated CadQuery trace execution."""

from __future__ import annotations

import ast
import builtins
from dataclasses import asdict
import math
import multiprocessing as mp
from queue import Empty
import re
import sys
import time
from typing import Any

from cad_qa.config import DatasetConfig
from cad_qa.cache import load_cached_trace, store_cached_trace
from cad_qa.hashing import sha256_json
from cad_qa.operation_graph import (
    extract_operation_graph,
    operation_graph_hash,
    operation_nodes_to_dicts,
)
from cad_qa.safety import safety_issues
from cad_qa.schema import SourceRecord, TraceRecord
from cad_qa.scheduler import schedule_and_label_descriptors

GENERATED_SELECTOR_PROBES: tuple[tuple[str, str | None], ...] = (
    ("faces", None),
    ("faces", '">X"'),
    ("faces", '"<X"'),
    ("faces", '"+X"'),
    ("faces", '"-X"'),
    ("faces", '"#X"'),
    ("faces", '">Y"'),
    ("faces", '"<Y"'),
    ("faces", '"+Y"'),
    ("faces", '"-Y"'),
    ("faces", '"#Y"'),
    ("faces", '">Z"'),
    ("faces", '"<Z"'),
    ("faces", '"+Z"'),
    ("faces", '"-Z"'),
    ("faces", '"#Z"'),
    ("faces", '"%PLANE"'),
    ("faces", '"%CYLINDER"'),
    ("edges", None),
    ("edges", '"|X"'),
    ("edges", '"|Y"'),
    ("edges", '"|Z"'),
    ("edges", '">X"'),
    ("edges", '"<X"'),
    ("edges", '"+X"'),
    ("edges", '"-X"'),
    ("edges", '"#X"'),
    ("edges", '">Y"'),
    ("edges", '"<Y"'),
    ("edges", '"+Y"'),
    ("edges", '"-Y"'),
    ("edges", '"#Y"'),
    ("edges", '">Z"'),
    ("edges", '"<Z"'),
    ("edges", '"+Z"'),
    ("edges", '"-Z"'),
    ("edges", '"#Z"'),
    ("edges", '"%LINE"'),
    ("edges", '"%CIRCLE"'),
    ("vertices", None),
    ("vertices", '">X"'),
    ("vertices", '"<X"'),
    ("vertices", '">Y"'),
    ("vertices", '"<Y"'),
    ("vertices", '">Z"'),
    ("vertices", '"<Z"'),
)

POINT_MEMBERSHIP_SIGFIGS = 4
NEAR_BOUNDARY_AABB_MARGIN_RATIO = 0.01


def trace_source_record(
    source: SourceRecord,
    *,
    config: DatasetConfig,
    isolated: bool = True,
) -> TraceRecord:
    nodes, result_variable, graph_issues = extract_operation_graph(
        source.normalized_code
    )
    graph_status = (
        "ok" if nodes and not graph_issues else ("partial" if nodes else "failed")
    )
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
        result = _trace_isolated(
            source.normalized_code,
            config=config,
            timeout_seconds=config.trace_timeout_seconds,
        )
    else:
        result = _trace_worker_payload(source.normalized_code, config=config)
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
    selector_tables = _attach_table_feature_ids(
        result.get("selector_tables", []), nodes
    )
    point_queries = _attach_table_feature_ids(result.get("point_queries", []), nodes)
    provenance_records = _attach_table_feature_ids(
        result.get("provenance_records", []), nodes
    )
    topology_matches = _attach_table_feature_ids(
        result.get("topology_matches", []), nodes
    )
    graph_queries = _attach_table_feature_ids(result.get("graph_queries", []), nodes)
    spatial_queries = _attach_table_feature_ids(
        result.get("spatial_queries", []), nodes
    )
    bbox_region_queries = _attach_table_feature_ids(
        result.get("bbox_region_queries", []), nodes
    )
    validity_probes = _attach_table_feature_ids(
        result.get("validity_probes", []), nodes
    )
    candidate_descriptors = _attach_descriptor_feature_ids(
        result.get("candidate_descriptors", []), nodes
    )
    sampling_manifest = dict(result.get("sampling_manifest") or {})
    trace_payload = {
        "source_id": source.source_id,
        "graph_hash": graph_hash,
        "snapshots": snapshots,
        "selector_tables": selector_tables,
        "point_queries": point_queries,
        "candidate_descriptors": candidate_descriptors,
        "sampling_manifest": sampling_manifest,
        "provenance_records": provenance_records,
        "topology_matches": topology_matches,
        "graph_queries": graph_queries,
        "spatial_queries": spatial_queries,
        "bbox_region_queries": bbox_region_queries,
        "validity_probes": validity_probes,
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
        topology_matches=topology_matches,
        graph_queries=graph_queries,
        spatial_queries=spatial_queries,
        bbox_region_queries=bbox_region_queries,
        validity_probes=validity_probes,
        candidate_descriptors=candidate_descriptors,
        sampling_manifest=sampling_manifest,
    )


def trace_source_records_bounded(
    sources: list[SourceRecord],
    *,
    config: DatasetConfig,
    worker_count: int | None = None,
    cache_dir: Any | None = None,
) -> list[TraceRecord]:
    """Trace sources in bounded worker processes, preserving input order."""
    cached_results: list[TraceRecord | None] = [
        load_cached_trace(cache_dir, source, config) for source in sources
    ]
    uncached: list[tuple[int, SourceRecord]] = [
        (index, source)
        for index, (source, cached) in enumerate(
            zip(sources, cached_results, strict=True)
        )
        if cached is None
    ]
    if not uncached:
        return [trace for trace in cached_results if trace is not None]

    worker_count = max(1, worker_count or config.worker_count)
    if worker_count <= 1:
        for index, source in uncached:
            trace = trace_source_record(source, config=config, isolated=True)
            store_cached_trace(cache_dir, source, config, trace)
            cached_results[index] = trace
        return [trace for trace in cached_results if trace is not None]

    context = mp.get_context("spawn")
    pending = list(uncached)
    running: list[dict[str, Any]] = []
    results: list[TraceRecord | None] = [None] * len(sources)

    def start_next() -> None:
        if not pending:
            return
        index, source = pending.pop(0)
        queue: mp.Queue = context.Queue(maxsize=1)
        process = context.Process(
            target=_trace_record_worker, args=(source, config, queue)
        )
        process.start()
        running.append(
            {
                "index": index,
                "source": source,
                "queue": queue,
                "process": process,
                "started_at": time.monotonic(),
            }
        )

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
                result = _trace_from_worker_queue(
                    source, config, job["queue"], process.exitcode
                )
            running.remove(job)
            store_cached_trace(cache_dir, source, config, result)
            results[int(job["index"])] = result
            made_progress = True
            start_next()
        if not made_progress:
            time.sleep(0.05)

    for index, trace in enumerate(results):
        if trace is not None:
            cached_results[index] = trace
    return [trace for trace in cached_results if trace is not None]


def _trace_record_worker(
    source: SourceRecord, config: DatasetConfig, queue: mp.Queue
) -> None:
    queue.put(trace_source_record(source, config=config, isolated=False))


def _trace_from_worker_queue(
    source: SourceRecord, config: DatasetConfig, queue: mp.Queue, exitcode: int | None
) -> TraceRecord:
    if exitcode != 0:
        return _timeout_trace(source, config, failure_reason="worker_crash")
    try:
        value = queue.get_nowait()
    except Empty:
        return _timeout_trace(source, config, failure_reason="worker_crash")
    if isinstance(value, TraceRecord):
        return value
    return _timeout_trace(source, config, failure_reason="worker_crash")


def _timeout_trace(
    source: SourceRecord,
    config: DatasetConfig,
    failure_reason: str = "execution_timeout",
) -> TraceRecord:
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


def _trace_isolated(
    code: str, *, config: DatasetConfig, timeout_seconds: float
) -> dict[str, Any]:
    context = mp.get_context("spawn")
    queue: mp.Queue = context.Queue(maxsize=1)
    process = context.Process(target=_worker_main, args=(code, config, queue))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(1.0)
        return {
            "status": "error",
            "failure_reason": "execution_timeout",
            "environment": _base_environment(),
        }
    if process.exitcode != 0:
        return {
            "status": "error",
            "failure_reason": "worker_crash",
            "environment": _base_environment(),
        }
    try:
        return queue.get_nowait()
    except Empty:
        return {
            "status": "error",
            "failure_reason": "worker_crash",
            "environment": _base_environment(),
        }


def _worker_main(code: str, config: DatasetConfig, queue: mp.Queue) -> None:
    try:
        queue.put(_trace_worker_payload(code, config=config))
    except Exception as exc:
        queue.put(
            {
                "status": "error",
                "failure_reason": f"unknown_error:{type(exc).__name__}",
                "environment": _base_environment(),
            }
        )


def _trace_worker_payload(
    code: str, *, config: DatasetConfig | None = None
) -> dict[str, Any]:
    started = time.monotonic()
    config = config or DatasetConfig()
    try:
        import cadquery as cq  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return {
            "status": "error",
            "failure_reason": "cadquery_unavailable",
            "environment": _base_environment(),
        }

    environment = _base_environment()
    environment["cadquery_version"] = getattr(cq, "__version__", None)
    try:
        import OCP  # type: ignore[import-not-found]

        environment["ocp_version"] = getattr(OCP, "__version__", None)
    except Exception:
        environment["ocp_version"] = None

    namespace: dict[str, Any] = {
        "cq": cq,
        "cadquery": cq,
        "__cadqa_label_policy": asdict(config.label_policy),
        "__builtins__": _safe_builtins(),
    }
    snapshots: list[dict[str, Any]] = []
    selector_tables: list[dict[str, Any]] = []
    point_queries: list[dict[str, Any]] = []
    candidate_descriptors: list[dict[str, Any]] = []
    sampling_manifest: dict[str, Any] = {}
    provenance_records: list[dict[str, Any]] = []
    topology_matches: list[dict[str, Any]] = []
    try:
        tree = ast.parse(code)
        for statement_index, statement in enumerate(tree.body):
            exec(
                compile(ast.Module([statement], []), "<cadqa-trace>", "exec"), namespace
            )
            if (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
            ):
                target = statement.targets[0].id
                if target in namespace:
                    snapshot = _snapshot_for_object(
                        namespace[target], target, statement_index
                    )
                    if snapshot is not None:
                        snapshots.append(snapshot)
                        selector_tables.extend(
                            _selector_tables_for_statement(
                                statement, snapshot, namespace
                            )
                        )
                        candidate_descriptors.extend(
                            _generated_selector_descriptors_for_snapshot(snapshot)
                        )
            elif isinstance(statement, ast.Expr):
                selector = _selector_table_for_expr(
                    statement, namespace, statement_index
                )
                if selector is not None:
                    selector_tables.append(selector)
        candidate_descriptors.extend(_point_query_descriptors_for_snapshots(snapshots))
        scheduled = schedule_and_label_descriptors(
            candidate_descriptors,
            labeler=lambda descriptor: _evaluate_runtime_descriptor(
                descriptor, namespace
            ),
            seed=config.seed,
            max_per_source=config.max_runtime_probe_labels_per_source,
            max_per_task_type=config.max_runtime_probe_labels_per_task_type,
            scope=sha256_json({"runtime_probe_schedule": code}),
        )
        sampling_manifest = scheduled.manifest
        for descriptor, payload in zip(
            scheduled.selected_descriptors, scheduled.labeled_payloads, strict=True
        ):
            if descriptor.get("task_type") == "selector_count":
                selector_tables.append(payload)
            elif descriptor.get("task_type") == "point_membership":
                point_queries.append(payload)
        topology_matches = _adjacent_topology_matches(snapshots)
        provenance_records = [
            *_conservative_provenance_records(snapshots),
            *_lineage_provenance_records(snapshots, topology_matches),
        ]
    except Exception as exc:
        return {
            "status": "error",
            "failure_reason": f"source_exec_error:{type(exc).__name__}",
            "environment": environment,
            "snapshots": snapshots,
            "selector_tables": selector_tables,
            "point_queries": point_queries,
            "candidate_descriptors": candidate_descriptors,
            "sampling_manifest": sampling_manifest,
            "provenance_records": provenance_records,
            "topology_matches": topology_matches,
        }
    environment["elapsed_seconds"] = round(time.monotonic() - started, 6)
    return {
        "status": "ok",
        "snapshots": snapshots,
        "selector_tables": selector_tables,
        "point_queries": point_queries,
        "candidate_descriptors": candidate_descriptors,
        "sampling_manifest": sampling_manifest,
        "provenance_records": provenance_records,
        "topology_matches": topology_matches,
        "environment": environment,
    }


def _snapshot_for_object(
    obj: Any, target: str, step_index: int
) -> dict[str, Any] | None:
    shape = _shape_from_object(obj)
    if shape is None:
        return None
    volume = _call_number(shape, "Volume")
    bbox = _bbox(shape)
    topology = _topology(shape)
    entity_ids, entity_signatures = _entity_ids_and_signatures(shape, topology)
    return {
        "snapshot_id": f"snap_{target}_{step_index:04d}",
        "feature_id": target,
        "step_index": step_index,
        "shape_status": "ok" if volume is not None or bbox is not None else "failed",
        "volume": volume,
        "bbox": bbox,
        "topology": topology,
        "entity_ids": entity_ids,
        "diagnostics": {
            "snapshot_target": target,
            "entity_signatures": entity_signatures,
        },
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


def _entity_ids_and_signatures(
    shape: Any,
    topology: dict[str, int | None],
) -> tuple[dict[str, list[str]], dict[str, list[dict[str, Any]]]]:
    ids = {
        "faces": [
            f"face_{index:04d}" for index in range(int(topology.get("face_count") or 0))
        ],
        "edges": [
            f"edge_{index:04d}" for index in range(int(topology.get("edge_count") or 0))
        ],
        "vertices": [
            f"vertex_{index:04d}"
            for index in range(int(topology.get("vertex_count") or 0))
        ],
    }
    signatures: dict[str, list[dict[str, Any]]] = {}
    total_entities = sum(len(values) for values in ids.values())
    if total_entities > 24:
        return ids, signatures
    for entity_type, method_name in (
        ("face", "Faces"),
        ("edge", "Edges"),
        ("vertex", "Vertices"),
    ):
        entities = _entities(shape, method_name)
        signatures[entity_type] = [
            {
                "entity_id": f"{entity_type}_{index:04d}",
                "entity_type": entity_type,
                "geometry_type": _geometry_type(entity),
                "center": _center(entity),
                "measure": _entity_measure(entity),
            }
            for index, entity in enumerate(entities)
        ]
    return ids, signatures


def _entities(shape: Any, method_name: str) -> list[Any]:
    method = getattr(shape, method_name, None)
    if method is None:
        return []
    try:
        return list(method())
    except Exception:
        return []


def _geometry_type(entity: Any) -> str | None:
    method = getattr(entity, "geomType", None)
    if method is None:
        return None
    try:
        return str(method())
    except Exception:
        return None


def _center(entity: Any) -> list[float] | None:
    method = getattr(entity, "Center", None)
    if method is None:
        return None
    try:
        center = method()
        return [float(center.x), float(center.y), float(center.z)]
    except Exception:
        return None


def _entity_measure(entity: Any) -> float | None:
    for method_name in ("Area", "Length", "Volume"):
        value = _call_number(entity, method_name)
        if value is not None:
            return value
    return None


def _selector_tables_for_statement(
    statement: ast.Assign,
    snapshot: dict[str, Any],
    namespace: dict[str, Any],
) -> list[dict[str, Any]]:
    calls = [node for node in ast.walk(statement.value) if isinstance(node, ast.Call)]
    tables: list[dict[str, Any]] = []
    for call in calls:
        if isinstance(call.func, ast.Attribute) and call.func.attr in {
            "faces",
            "edges",
            "vertices",
            "wires",
            "solids",
        }:
            tables.append(
                _selector_table_from_call(call, snapshot.get("feature_id"), namespace)
            )
    return tables


def _selector_table_for_expr(
    statement: ast.Expr, namespace: dict[str, Any], statement_index: int
) -> dict[str, Any] | None:
    del statement_index
    if isinstance(statement.value, ast.Call) and isinstance(
        statement.value.func, ast.Attribute
    ):
        if statement.value.func.attr in {
            "faces",
            "edges",
            "vertices",
            "wires",
            "solids",
        }:
            return _selector_table_from_call(statement.value, None, namespace)
    return None


def _generated_selector_tables_for_snapshot(
    snapshot: dict[str, Any],
    namespace: dict[str, Any],
) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    for descriptor in _generated_selector_descriptors_for_snapshot(snapshot):
        table = _evaluate_generated_selector_descriptor(descriptor, namespace)
        if table.get("status") == "ok":
            tables.append(table)
    return tables


def _generated_selector_descriptors_for_snapshot(
    snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    target = snapshot.get("feature_id")
    if not isinstance(target, str):
        return []
    descriptors: list[dict[str, Any]] = []
    for method_name, selector_arg in GENERATED_SELECTOR_PROBES:
        expression = (
            f"{target}.{method_name}()"
            if selector_arg is None
            else f"{target}.{method_name}({selector_arg})"
        )
        entity_type = _selector_entity_type(method_name)
        payload = {
            "selector_expression": expression,
            "target_feature_id": target,
            "entity_type": entity_type,
            "selector_origin": "generated",
            "snapshot_id": snapshot.get("snapshot_id"),
            "step_index": snapshot.get("step_index"),
        }
        descriptors.append(
            {
                "descriptor_id": "runtime_selector_"
                + sha256_json(payload).removeprefix("sha256:")[:16],
                "task_type": "selector_count",
                "stratum": f"generated_{entity_type}",
                "target_feature_id": target,
                "label_cost": 1,
                "payload": payload,
            }
        )
    return descriptors


def _selector_table_from_call(
    call: ast.Call, target_feature_id: Any, namespace: dict[str, Any]
) -> dict[str, Any]:
    expression = ast.unparse(call)
    entity_type = (
        _selector_entity_type(call.func.attr)
        if isinstance(call.func, ast.Attribute)
        else "entity"
    )
    return _selector_table_from_expression(
        expression,
        target_feature_id,
        namespace,
        selector_origin="source",
        entity_type=entity_type,
    )


def _evaluate_generated_selector_descriptor(
    descriptor: dict[str, Any], namespace: dict[str, Any]
) -> dict[str, Any]:
    payload = dict(descriptor.get("payload") or {})
    expression = str(payload.get("selector_expression") or "")
    target_feature_id = payload.get("target_feature_id")
    entity_type = str(payload.get("entity_type") or "entity")
    table = _selector_table_from_expression(
        expression,
        target_feature_id,
        namespace,
        selector_origin="generated",
        entity_type=entity_type,
    )
    table["descriptor_id"] = descriptor.get("descriptor_id")
    table["snapshot_id"] = payload.get("snapshot_id")
    table["step_index"] = payload.get("step_index")
    return table


def _selector_entity_type(method_name: str) -> str:
    if method_name == "vertices":
        return "vertex"
    return method_name.removesuffix("s")


def _selector_table_from_expression(
    expression: str,
    target_feature_id: Any,
    namespace: dict[str, Any],
    *,
    selector_origin: str,
    entity_type: str,
) -> dict[str, Any]:
    selected_count: int | None = None
    raw_entity_ids: list[str] = []
    status = "recorded_expression"
    try:
        selected = eval(
            compile(ast.parse(expression, mode="eval"), "<cadqa-selector>", "eval"),
            namespace,
        )  # noqa: S307
        selected_count = _selected_count(selected)
        raw_entity_ids = [
            f"{entity_type}_{index:04d}" for index in range(selected_count)
        ]
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
        "selector_origin": selector_origin,
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


def _point_queries_for_snapshots(
    namespace: dict[str, Any], snapshots: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for descriptor in _point_query_descriptors_for_snapshots(snapshots):
        query = _evaluate_point_descriptor(descriptor, namespace)
        if query is not None:
            rows.append(query)
    return rows


def _point_query_descriptors_for_snapshots(
    snapshots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    descriptors: list[dict[str, Any]] = []
    for snapshot in snapshots:
        descriptors.extend(_point_query_descriptors_for_snapshot(snapshot))
    return descriptors


def _point_query_descriptors_for_snapshot(
    snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    bbox = snapshot.get("bbox")
    target = snapshot.get("feature_id")
    if not isinstance(bbox, dict) or not isinstance(target, str):
        return []
    minimum = bbox.get("min")
    maximum = bbox.get("max")
    if not (_finite_triplet(minimum) and _finite_triplet(maximum)):
        return []
    min_values = [float(value) for value in minimum]
    max_values = [float(value) for value in maximum]
    center = [(min_values[i] + max_values[i]) / 2.0 for i in range(3)]
    side_lengths = [max_values[i] - min_values[i] for i in range(3)]
    max_side_length = max(side_lengths)
    if max_side_length <= 0.0:
        return []
    spans = [max(side_lengths[i], 1.0) for i in range(3)]
    span = max(spans)
    quarter = [min_values[i] + 0.25 * spans[i] for i in range(3)]
    outside_x = [max_values[0] + 0.25 * span, center[1], center[2]]
    outside_diagonal = [max_values[i] + 0.10 * span for i in range(3)]
    candidates = [
        ("aabb_center", center, "aabb_uniform_inside"),
        ("aabb_quarter", quarter, "aabb_uniform_inside"),
        ("expanded_aabb_outside_x", outside_x, "expanded_aabb_outside"),
        ("expanded_aabb_outside_diagonal", outside_diagonal, "expanded_aabb_outside"),
    ]
    adaptive_margin = max_side_length * NEAR_BOUNDARY_AABB_MARGIN_RATIO
    candidates.extend(
        _adaptive_near_boundary_point_candidates(
            min_values,
            max_values,
            center,
            side_lengths,
            adaptive_margin,
        )
    )
    descriptors: list[dict[str, Any]] = []
    for sample_source, point, intended_stratum in candidates:
        rounded_point = _round_point_sigfig(point)
        payload = {
            "point": rounded_point,
            "target_feature_id": target,
            "intended_sampling_stratum": intended_stratum,
            "sample_source": sample_source,
            "snapshot_id": snapshot.get("snapshot_id"),
            "step_index": snapshot.get("step_index"),
            "coordinate_frame": "world",
            "nearest_entity_diagnostics": _nearest_entity_diagnostics(
                snapshot, rounded_point
            ),
            "point_export_sigfigs": POINT_MEMBERSHIP_SIGFIGS,
            "adaptive_boundary_margin_mm": adaptive_margin,
            "max_aabb_side_length_mm": max_side_length,
        }
        descriptors.append(
            {
                "descriptor_id": "runtime_point_"
                + sha256_json(payload).removeprefix("sha256:")[:16],
                "task_type": "point_membership",
                "stratum": intended_stratum,
                "target_feature_id": target,
                "label_cost": 1,
                "payload": payload,
            }
        )
    return descriptors


def _point_queries_for_snapshot(
    namespace: dict[str, Any], snapshot: dict[str, Any]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for descriptor in _point_query_descriptors_for_snapshot(snapshot):
        query = _evaluate_point_descriptor(descriptor, namespace)
        if query is not None:
            rows.append(query)
    return rows


def _evaluate_point_descriptor(
    descriptor: dict[str, Any], namespace: dict[str, Any]
) -> dict[str, Any] | None:
    payload = dict(descriptor.get("payload") or {})
    target = payload.get("target_feature_id")
    point = payload.get("point")
    if not isinstance(target, str) or not _finite_triplet(point):
        return None
    shape = _shape_from_object(namespace.get(target))
    if shape is None:
        return None
    point_values = _round_point_sigfig([float(value) for value in point])
    classification = _classify_point(shape, point_values, namespace)
    if classification is None:
        return None
    intended_stratum = str(payload.get("intended_sampling_stratum") or "unknown")
    return {
        "descriptor_id": descriptor.get("descriptor_id"),
        "point": point_values,
        "target_feature_id": target,
        "point_classification": classification,
        "sampling_stratum": _point_sampling_stratum(
            intended_stratum, classification
        ),
        "classifier": "occ_face_distance_then_cadquery_shape_isInside",
        "sample_source": payload.get("sample_source"),
        "snapshot_id": payload.get("snapshot_id"),
        "step_index": payload.get("step_index"),
        "coordinate_frame": payload.get("coordinate_frame", "world"),
        "nearest_entity_diagnostics": payload.get("nearest_entity_diagnostics"),
        "point_export_sigfigs": payload.get("point_export_sigfigs"),
        "adaptive_boundary_margin_mm": payload.get("adaptive_boundary_margin_mm"),
        "max_aabb_side_length_mm": payload.get("max_aabb_side_length_mm"),
    }


def _adaptive_near_boundary_point_candidates(
    minimum: list[float],
    maximum: list[float],
    center: list[float],
    side_lengths: list[float],
    margin: float,
) -> list[tuple[str, list[float], str]]:
    if margin <= 0.0:
        return []
    axis = max(range(3), key=lambda index: side_lengths[index])
    if side_lengths[axis] <= 2.0 * margin:
        return []
    axis_name = "xyz"[axis]
    candidates: list[tuple[str, list[float], str]] = []
    near_min_inside = list(center)
    near_min_inside[axis] = minimum[axis] + margin
    near_max_inside = list(center)
    near_max_inside[axis] = maximum[axis] - margin
    near_min_outside = list(center)
    near_min_outside[axis] = minimum[axis] - margin
    near_max_outside = list(center)
    near_max_outside[axis] = maximum[axis] + margin
    candidates.extend(
        [
            (
                f"near_boundary_inside_min_{axis_name}",
                near_min_inside,
                "near_boundary_inside",
            ),
            (
                f"near_boundary_inside_max_{axis_name}",
                near_max_inside,
                "near_boundary_inside",
            ),
            (
                f"near_boundary_outside_min_{axis_name}",
                near_min_outside,
                "near_boundary_outside",
            ),
            (
                f"near_boundary_outside_max_{axis_name}",
                near_max_outside,
                "near_boundary_outside",
            ),
        ]
    )
    return candidates


def _nearest_entity_diagnostics(
    snapshot: dict[str, Any], point: list[float]
) -> dict[str, Any] | None:
    signatures = _snapshot_entity_signatures(snapshot)
    best: tuple[dict[str, Any], float] | None = None
    for entities in signatures.values():
        for entity in entities:
            center = entity.get("center")
            if not _finite_triplet(center):
                continue
            distance = (
                sum(
                    (float(left) - float(right)) ** 2
                    for left, right in zip(point, center, strict=True)
                )
                ** 0.5
            )
            if best is None or distance < best[1]:
                best = (entity, distance)
    if best is None:
        return None
    entity, distance = best
    return {
        "entity_id": entity.get("entity_id"),
        "entity_type": entity.get("entity_type"),
        "geometry_type": entity.get("geometry_type"),
        "center": entity.get("center"),
        "distance_to_center": distance,
        "method": "entity_signature_center_distance",
    }


def _point_sampling_stratum(intended_stratum: str, classification: str) -> str:
    if intended_stratum == "expanded_aabb_outside":
        return "expanded_aabb_outside"
    if intended_stratum.startswith("near_boundary_"):
        if classification in {"inside", "outside"}:
            return f"near_boundary_{classification}"
        return "near_boundary"
    if classification == "inside":
        return "deep_inside"
    if classification == "outside":
        return "deep_outside"
    return classification


def _evaluate_runtime_descriptor(
    descriptor: dict[str, Any], namespace: dict[str, Any]
) -> dict[str, Any] | None:
    task_type = descriptor.get("task_type")
    if task_type == "selector_count":
        table = _evaluate_generated_selector_descriptor(descriptor, namespace)
        return table if table.get("status") == "ok" else None
    if task_type == "point_membership":
        return _evaluate_point_descriptor(descriptor, namespace)
    return None


def _classify_point(
    shape: Any, point: list[float], namespace: dict[str, Any]
) -> str | None:
    boundary_tolerance = _point_boundary_tolerance(namespace)
    boundary_distance = _point_boundary_distance(shape, point)
    if boundary_distance is not None and boundary_distance <= boundary_tolerance:
        return "on_boundary"
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


def _point_boundary_tolerance(namespace: dict[str, Any]) -> float:
    policy = namespace.get("__cadqa_label_policy")
    if isinstance(policy, dict):
        value = policy.get("point_boundary_tolerance_mm")
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
    return 1e-5


def _point_boundary_distance(shape: Any, point: list[float]) -> float | None:
    try:
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex  # type: ignore[import-not-found]
        from OCP.BRepExtrema import BRepExtrema_DistShapeShape  # type: ignore[import-not-found]
        from OCP.gp import gp_Pnt  # type: ignore[import-not-found]
    except Exception:
        return None
    try:
        vertex = BRepBuilderAPI_MakeVertex(gp_Pnt(*point)).Vertex()
    except Exception:
        return None
    boundary_shapes = _boundary_shapes(shape)
    distances: list[float] = []
    for boundary_shape in boundary_shapes:
        wrapped = getattr(boundary_shape, "wrapped", boundary_shape)
        try:
            distance = BRepExtrema_DistShapeShape(vertex, wrapped)
            distance.Perform()
            if distance.IsDone():
                value = float(distance.Value())
                if math.isfinite(value):
                    distances.append(value)
        except Exception:
            continue
    return min(distances) if distances else None


def _boundary_shapes(shape: Any) -> list[Any]:
    faces = getattr(shape, "Faces", None)
    if callable(faces):
        try:
            face_values = list(faces())
        except Exception:
            face_values = []
        if face_values:
            return face_values
    return [shape]


def _conservative_provenance_records(
    snapshots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
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
                "contributor_feature_ids": [current.get("feature_id")],
                "first_contributor_feature_id": current.get("feature_id"),
                "first_contributor_rule": "min_step_index",
                "matching_method": "adjacent_snapshot_volume_delta",
                "provenance_confidence": 0.6,
            }
        )
    return records


def _lineage_provenance_records(
    snapshots: list[dict[str, Any]],
    topology_matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    feature_order = _feature_order_from_snapshots(snapshots)
    matches_by_target = _topology_matches_by_target(topology_matches)
    lineage: dict[tuple[str, str, str], list[str]] = {}
    for snapshot_index, snapshot in enumerate(snapshots):
        feature_id = snapshot.get("feature_id")
        if not isinstance(feature_id, str):
            continue
        signatures = _snapshot_entity_signatures(snapshot)
        for entity_type, entities in signatures.items():
            for entity in entities:
                entity_id = entity.get("entity_id")
                if not isinstance(entity_id, str):
                    continue
                entity_key = (feature_id, entity_type, entity_id)
                matches = matches_by_target.get(entity_key, [])
                previous_contributors: list[str] = []
                for match in matches:
                    from_feature = match.get("from_feature_id")
                    from_entity = match.get("from_entity_id")
                    if not isinstance(from_feature, str) or not isinstance(
                        from_entity, str
                    ):
                        continue
                    from_key = (from_feature, entity_type, from_entity)
                    previous_contributors.extend(
                        lineage.get(from_key) or [from_feature]
                    )

                contributors = _ordered_unique([*previous_contributors, feature_id])
                lineage[entity_key] = contributors
                if snapshot_index == 0:
                    continue
                first = _first_feature_id(contributors, feature_order)
                if first is None:
                    continue
                relation = _lineage_relation(matches, previous_contributors)
                confidence_values = [
                    float(match.get("confidence"))
                    for match in matches
                    if isinstance(match.get("confidence"), (int, float))
                ]
                records.append(
                    {
                        "target_description": (
                            f"{entity_type} `{entity_id}` in snapshot `{feature_id}`"
                        ),
                        "target_feature_id": feature_id,
                        "provenance_relation": relation,
                        "answer_feature_id": first,
                        "contributor_feature_ids": contributors,
                        "first_contributor_feature_id": first,
                        "first_contributor_rule": "min_step_index",
                        "matching_method": (
                            "entity_lineage_contributor_set"
                            if matches
                            else "unmatched_adjacent_entity"
                        ),
                        "provenance_confidence": (
                            min(confidence_values) if confidence_values else 0.6
                        ),
                        "topology_matches": matches,
                    }
                )
    return records


def _topology_match_provenance_records(
    topology_matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    feature_order = _feature_order_from_matches(topology_matches)
    for target_key, matches in _topology_matches_by_target(topology_matches).items():
        to_feature, entity_type, to_entity_id = target_key
        from_contributors = [
            str(match.get("from_feature_id"))
            for match in matches
            if isinstance(match.get("from_feature_id"), str)
        ]
        contributors = _ordered_unique(
            [
                *from_contributors,
                to_feature,
            ]
        )
        first = _first_feature_id(contributors, feature_order)
        if first is None:
            continue
        confidence_values = [
            float(match.get("confidence"))
            for match in matches
            if isinstance(match.get("confidence"), (int, float))
        ]
        relation = _lineage_relation(matches, from_contributors)
        representative = matches[0]
        records.append(
            {
                "target_description": (
                    f"{entity_type} `{to_entity_id}` inherited from adjacent snapshot"
                ),
                "target_feature_id": to_feature,
                "provenance_relation": relation,
                "answer_feature_id": first,
                "contributor_feature_ids": contributors,
                "first_contributor_feature_id": first,
                "first_contributor_rule": "min_step_index",
                "matching_method": representative.get("matching_method")
                or "adjacent_topology_match",
                "provenance_confidence": (
                    min(confidence_values) if confidence_values else 0.5
                ),
                "topology_matches": matches,
            }
        )
    return records


def _feature_order_from_snapshots(
    snapshots: list[dict[str, Any]],
) -> dict[str, int]:
    order: dict[str, int] = {}
    for fallback_index, snapshot in enumerate(snapshots):
        feature_id = snapshot.get("feature_id")
        if not isinstance(feature_id, str):
            continue
        step_index = snapshot.get("step_index")
        order[feature_id] = (
            int(step_index) if isinstance(step_index, int) else fallback_index
        )
    return order


def _feature_order_from_matches(
    topology_matches: list[dict[str, Any]],
) -> dict[str, int]:
    feature_ids: list[str] = []
    for match in topology_matches:
        for key in ("from_feature_id", "to_feature_id"):
            feature_id = match.get(key)
            if isinstance(feature_id, str):
                feature_ids.append(feature_id)
    return {
        feature_id: index
        for index, feature_id in enumerate(
            sorted(_ordered_unique(feature_ids), key=_feature_sort_key)
        )
    }


def _topology_matches_by_target(
    topology_matches: list[dict[str, Any]],
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for match in topology_matches:
        to_feature = match.get("to_feature_id")
        entity_type = match.get("entity_type") or "entity"
        to_entity = match.get("to_entity_id")
        if not (
            isinstance(to_feature, str)
            and isinstance(entity_type, str)
            and isinstance(to_entity, str)
        ):
            continue
        grouped.setdefault((to_feature, entity_type, to_entity), []).append(match)
    return grouped


def _lineage_relation(
    matches: list[dict[str, Any]], previous_contributors: list[str]
) -> str:
    if not matches:
        return "created_by"
    previous_entities = {
        (match.get("from_feature_id"), match.get("from_entity_id"))
        for match in matches
    }
    if len(previous_entities) > 1 or len(set(previous_contributors)) > 1:
        return "bounded_by"
    return "inherited_from"


def _first_feature_id(
    feature_ids: list[str], feature_order: dict[str, int]
) -> str | None:
    valid = [feature_id for feature_id in feature_ids if isinstance(feature_id, str)]
    if not valid:
        return None
    return min(
        valid,
        key=lambda feature_id: (
            feature_order.get(feature_id, 10**9),
            _feature_sort_key(feature_id),
        ),
    )


def _feature_sort_key(feature_id: str) -> tuple[str, int, str]:
    match = re.search(r"(\d+)$", feature_id)
    if match:
        return (feature_id[: match.start()], int(match.group(1)), feature_id)
    return (feature_id, -1, feature_id)


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if not isinstance(value, str) or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def _adjacent_topology_matches(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for previous, current in zip(snapshots, snapshots[1:], strict=False):
        previous_signatures = _snapshot_entity_signatures(previous)
        current_signatures = _snapshot_entity_signatures(current)
        for entity_type in ("face", "edge", "vertex"):
            records.extend(
                _match_entity_type(
                    previous,
                    current,
                    previous_signatures.get(entity_type, []),
                    current_signatures.get(entity_type, []),
                )
            )
    return records


def _snapshot_entity_signatures(
    snapshot: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    diagnostics = snapshot.get("diagnostics")
    if not isinstance(diagnostics, dict):
        return {}
    signatures = diagnostics.get("entity_signatures")
    return signatures if isinstance(signatures, dict) else {}


def _match_entity_type(
    previous: dict[str, Any],
    current: dict[str, Any],
    previous_entities: list[dict[str, Any]],
    current_entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    unmatched_current = list(current_entities)
    matches: list[dict[str, Any]] = []
    for previous_entity in previous_entities:
        best = _best_entity_match(previous_entity, unmatched_current)
        if best is None:
            continue
        current_entity, score = best
        if score > 1e-4:
            continue
        unmatched_current.remove(current_entity)
        matches.append(
            {
                "from_feature_id": previous.get("feature_id"),
                "to_feature_id": current.get("feature_id"),
                "from_entity_id": previous_entity.get("entity_id"),
                "to_entity_id": current_entity.get("entity_id"),
                "entity_type": current_entity.get("entity_type"),
                "matching_method": "geometry_signature_nearest",
                "confidence": max(0.0, 1.0 - min(score * 10000.0, 1.0)),
                "score": score,
            }
        )
    return matches


def _best_entity_match(
    previous_entity: dict[str, Any],
    current_entities: list[dict[str, Any]],
) -> tuple[dict[str, Any], float] | None:
    candidates = [
        (current_entity, _entity_signature_distance(previous_entity, current_entity))
        for current_entity in current_entities
        if current_entity.get("geometry_type") == previous_entity.get("geometry_type")
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[1])


def _entity_signature_distance(left: dict[str, Any], right: dict[str, Any]) -> float:
    distance = 0.0
    left_center = left.get("center")
    right_center = right.get("center")
    if _finite_triplet(left_center) and _finite_triplet(right_center):
        distance += (
            sum(
                (float(a) - float(b)) ** 2
                for a, b in zip(left_center, right_center, strict=True)
            )
            ** 0.5
        )
    left_measure = left.get("measure")
    right_measure = right.get("measure")
    if isinstance(left_measure, (int, float)) and isinstance(
        right_measure, (int, float)
    ):
        scale = max(abs(float(left_measure)), abs(float(right_measure)), 1.0)
        distance += abs(float(left_measure) - float(right_measure)) / scale
    return distance


def _finite_triplet(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 3
        and all(
            isinstance(item, (int, float)) and math.isfinite(float(item))
            for item in value
        )
    )


def _round_point_sigfig(point: list[float]) -> list[float]:
    return [
        float(_round_sigfig_number(coordinate, POINT_MEMBERSHIP_SIGFIGS))
        for coordinate in point
    ]


def _round_sigfig_number(value: float, digits: int) -> float | int:
    if value == 0:
        return 0.0
    places = digits - math.floor(math.log10(abs(value))) - 1
    rounded = round(value, places)
    if rounded == 0:
        return 0.0
    if places <= 0 and float(rounded).is_integer():
        return int(rounded)
    return rounded


def _attach_feature_ids(
    snapshots: list[dict[str, Any]], nodes: list[Any]
) -> list[dict[str, Any]]:
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


def _attach_table_feature_ids(
    records: list[dict[str, Any]], nodes: list[Any]
) -> list[dict[str, Any]]:
    target_to_feature = {node.target: node.feature_id for node in nodes if node.target}
    updated: list[dict[str, Any]] = []
    for record in records:
        copy = dict(record)
        for key in (
            "target_feature_id",
            "answer_feature_id",
            "feature_id",
            "first_contributor_feature_id",
        ):
            value = copy.get(key)
            if value in target_to_feature:
                copy[key] = target_to_feature[value]
        contributors = copy.get("contributor_feature_ids")
        if isinstance(contributors, list):
            copy["contributor_feature_ids"] = [
                target_to_feature.get(value, value) for value in contributors
            ]
        for key in ("topology_match", "topology_matches"):
            value = copy.get(key)
            if isinstance(value, dict):
                copy[key] = _attach_match_feature_ids(value, target_to_feature)
            elif isinstance(value, list):
                copy[key] = [
                    _attach_match_feature_ids(item, target_to_feature)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
        updated.append(copy)
    return updated


def _attach_match_feature_ids(
    record: dict[str, Any], target_to_feature: dict[str, str]
) -> dict[str, Any]:
    copy = dict(record)
    for key in ("from_feature_id", "to_feature_id", "target_feature_id"):
        value = copy.get(key)
        if value in target_to_feature:
            copy[key] = target_to_feature[value]
    return copy


def _attach_descriptor_feature_ids(
    descriptors: list[dict[str, Any]], nodes: list[Any]
) -> list[dict[str, Any]]:
    target_to_feature = {node.target: node.feature_id for node in nodes if node.target}
    updated: list[dict[str, Any]] = []
    for descriptor in descriptors:
        copy = dict(descriptor)
        value = copy.get("target_feature_id")
        if value in target_to_feature:
            copy["target_feature_id"] = target_to_feature[value]
        payload = copy.get("payload")
        if isinstance(payload, dict):
            payload_copy = dict(payload)
            payload_value = payload_copy.get("target_feature_id")
            if payload_value in target_to_feature:
                payload_copy["target_feature_id"] = target_to_feature[payload_value]
                expression = payload_copy.get("selector_expression")
                if isinstance(expression, str) and isinstance(payload_value, str):
                    payload_copy["selector_expression"] = expression.replace(
                        payload_value, payload_copy["target_feature_id"], 1
                    )
            copy["payload"] = payload_copy
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
    return {
        name: getattr(builtins, name)
        for name in allowed_names
        if hasattr(builtins, name)
    }


def _base_environment() -> dict[str, Any]:
    return {
        "python_version": sys.version.split()[0],
        "cadquery_version": None,
        "ocp_version": None,
    }


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
