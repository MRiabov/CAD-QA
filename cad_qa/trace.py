"""CadQuery trace execution and snapshot measurement."""

from __future__ import annotations

import ast
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
import importlib.util
import math
import multiprocessing as mp
from queue import Empty
import sys
import time
from typing import Any

from cad_qa.source import SourceRecord, source_record_from_mapping


TRACE_FAILURE_REASONS = {
    "cadquery_unavailable",
    "source_parse_error",
    "source_exec_error",
    "missing_result",
    "invalid_cadquery_type",
    "non_solid_result",
    "zero_or_negative_volume",
    "non_finite_bbox",
    "timeout",
    "worker_crash",
    "unknown_error",
}


@dataclass(frozen=True)
class TraceRecord:
    source_id: str
    execution_status: str = "not_run"
    snapshots: list[dict[str, Any]] | None = None
    operation_effects: list[dict[str, Any]] | None = None
    selector_results: list[dict[str, Any]] | None = None
    environment: dict[str, Any] | None = None
    failure_reason: str | None = None


@dataclass
class _RunningTrace:
    index: int
    source: SourceRecord
    process: mp.Process
    queue: mp.Queue
    started_at: float


class CadQueryTraceError(RuntimeError):
    def __init__(self, failure_reason: str, message: str) -> None:
        super().__init__(message)
        self.failure_reason = failure_reason


def cadquery_available() -> bool:
    return importlib.util.find_spec("cadquery") is not None


def cadquery_version() -> str | None:
    if not cadquery_available():
        return None
    import cadquery as cq

    return getattr(cq, "__version__", None)


def ocp_version() -> str | None:
    try:
        import OCP
    except Exception:
        return None
    return getattr(OCP, "__version__", None)


def trace_source(
    source: SourceRecord | Mapping[str, Any],
    *,
    timeout_seconds: float = 10.0,
    isolated: bool = True,
) -> TraceRecord:
    """Execute one source and return bounded kernel-backed trace evidence."""

    record = _coerce_source(source)
    if isolated:
        return _trace_source_isolated(record, timeout_seconds=timeout_seconds)
    return _trace_source_in_process(record, timeout_seconds=timeout_seconds)


def trace_sources_bounded(
    sources: list[SourceRecord | Mapping[str, Any]],
    *,
    timeout_seconds: float = 10.0,
    worker_count: int = 1,
    progress: Callable[[int, int], None] | None = None,
    on_result: Callable[[int, SourceRecord, TraceRecord], None] | None = None,
) -> list[TraceRecord]:
    """Trace sources with bounded isolated workers and input-order results."""

    records = [_coerce_source(source) for source in sources]
    if not records:
        return []
    if worker_count <= 1:
        results: list[TraceRecord] = []
        for index, record in enumerate(records):
            result = trace_source(record, timeout_seconds=timeout_seconds)
            results.append(result)
            if on_result is not None:
                on_result(index, record, result)
            if progress is not None:
                progress(len(results), len(records))
        return results

    context = _trace_context()
    pending = list(enumerate(records))
    running: list[_RunningTrace] = []
    results: list[TraceRecord | None] = [None] * len(records)
    completed = 0
    worker_count = max(1, worker_count)

    def start_next() -> None:
        if not pending:
            return
        index, record = pending.pop(0)
        queue: mp.Queue = context.Queue(maxsize=1)
        process = context.Process(target=_trace_worker, args=(record, queue, timeout_seconds))
        process.start()
        running.append(
            _RunningTrace(
                index=index,
                source=record,
                process=process,
                queue=queue,
                started_at=time.monotonic(),
            )
        )

    for _ in range(min(worker_count, len(pending))):
        start_next()

    while running:
        made_progress = False
        now = time.monotonic()
        for job in list(running):
            if job.process.is_alive() and now - job.started_at <= timeout_seconds:
                continue
            if job.process.is_alive():
                job.process.terminate()
                job.process.join(1.0)
                result = _failed_trace(job.source, "timeout", timeout_seconds=timeout_seconds)
            else:
                job.process.join()
                result = _record_from_completed_worker(job, timeout_seconds=timeout_seconds)
            running.remove(job)
            results[job.index] = result
            completed += 1
            made_progress = True
            if on_result is not None:
                on_result(job.index, job.source, result)
            if progress is not None:
                progress(completed, len(records))
            start_next()
        if not made_progress:
            time.sleep(0.05)

    return [record for record in results if record is not None]


def trace_report(records: list[TraceRecord]) -> dict[str, Any]:
    statuses = Counter(record.execution_status for record in records)
    failures = Counter(record.failure_reason for record in records if record.failure_reason)
    return {
        "trace_count": len(records),
        "ok_count": statuses.get("ok", 0),
        "failed_count": len(records) - statuses.get("ok", 0),
        "statuses": dict(sorted(statuses.items())),
        "failure_reasons": dict(sorted(failures.items())),
        "snapshot_count": sum(len(record.snapshots or []) for record in records),
        "operation_effect_count": sum(len(record.operation_effects or []) for record in records),
        "selector_result_count": sum(len(record.selector_results or []) for record in records),
    }


def object_to_shape(value: Any) -> Any:
    import cadquery as cq

    if isinstance(value, cq.Workplane):
        values = value.vals()
        if not values:
            raise CadQueryTraceError("missing_result", "CadQuery Workplane produced no values")
        non_shape_types = [
            type(selected).__name__
            for selected in values
            if not _is_shape_like(selected)
        ]
        if non_shape_types:
            raise CadQueryTraceError(
                "invalid_cadquery_type",
                "CadQuery Workplane produced non-shape values: "
                + ", ".join(sorted(set(non_shape_types))),
            )
        if len(values) == 1:
            return values[0]
        return cq.Compound.makeCompound(values)
    if _is_shape_like(value):
        return value
    raise CadQueryTraceError(
        "invalid_cadquery_type",
        f"unsupported result type: {type(value).__name__}",
    )


def _is_shape_like(value: Any) -> bool:
    return all(hasattr(value, name) for name in ("Volume", "BoundingBox", "ShapeType"))


def measure_shape(shape: Any) -> dict[str, Any]:
    try:
        if hasattr(shape, "isValid") and not shape.isValid():
            raise CadQueryTraceError("non_solid_result", "shape is not valid")
        shape_type = str(shape.ShapeType())
        if shape_type not in {"Solid", "Compound"}:
            raise CadQueryTraceError(
                "non_solid_result",
                f"expected Solid or Compound, got {shape_type}",
            )
        volume = float(shape.Volume())
        if not math.isfinite(volume) or volume <= 0.0:
            raise CadQueryTraceError(
                "zero_or_negative_volume",
                f"shape volume is not positive finite: {volume}",
            )
        bbox = _bounding_box_from_shape(shape)
    except CadQueryTraceError:
        raise
    except Exception as exc:
        raise CadQueryTraceError("unknown_error", str(exc)) from exc
    return {
        "shape_type": shape_type,
        "volume": volume,
        "bbox": bbox,
        "topology": _topology_counts(shape),
    }


def _trace_source_isolated(source: SourceRecord, *, timeout_seconds: float) -> TraceRecord:
    context = _trace_context()
    queue: mp.Queue = context.Queue(maxsize=1)
    process = context.Process(target=_trace_worker, args=(source, queue, timeout_seconds))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(1.0)
        return _failed_trace(source, "timeout", timeout_seconds=timeout_seconds)
    if process.exitcode != 0:
        return _failed_trace(source, "worker_crash", timeout_seconds=timeout_seconds)
    try:
        result = queue.get_nowait()
    except Empty:
        return _failed_trace(source, "worker_crash", timeout_seconds=timeout_seconds)
    return _trace_record_from_worker_result(source, result, timeout_seconds=timeout_seconds)


def _trace_source_in_process(source: SourceRecord, *, timeout_seconds: float) -> TraceRecord:
    try:
        result = _execute_source_trace(source)
    except CadQueryTraceError as exc:
        return _failed_trace(source, exc.failure_reason, timeout_seconds=timeout_seconds)
    except Exception:
        return _failed_trace(source, "unknown_error", timeout_seconds=timeout_seconds)
    return TraceRecord(
        source_id=source.source_id,
        execution_status="ok",
        snapshots=result["snapshots"],
        operation_effects=result["operation_effects"],
        selector_results=result["selector_results"],
        environment=_environment(timeout_seconds=timeout_seconds),
        failure_reason=None,
    )


def _trace_worker(source: SourceRecord, queue: mp.Queue, timeout_seconds: float) -> None:
    try:
        result = _execute_source_trace(source)
        queue.put({"status": "ok", **result})
    except CadQueryTraceError as exc:
        queue.put({"status": "error", "failure_reason": exc.failure_reason})
    except Exception:
        queue.put({"status": "error", "failure_reason": "unknown_error"})


def _execute_source_trace(source: SourceRecord) -> dict[str, Any]:
    if not cadquery_available():
        raise CadQueryTraceError("cadquery_unavailable", "cadquery is not installed")
    import cadquery as cq

    try:
        tree = ast.parse(source.source_code, filename=source.source_path or "<cadqa-source>")
    except SyntaxError as exc:
        raise CadQueryTraceError("source_parse_error", str(exc)) from exc

    namespace: dict[str, Any] = {
        "__builtins__": __builtins__,
        "__name__": "__cadqa_trace__",
        "cadquery": cq,
        "cq": cq,
        "math": math,
    }
    snapshots: list[dict[str, Any]] = []
    selector_results: list[dict[str, Any]] = []
    operation_index = 0
    selector_index = 0

    for statement in tree.body:
        before = set(namespace)
        try:
            module = ast.Module(body=[statement], type_ignores=[])
            ast.fix_missing_locations(module)
            compiled = compile(module, source.source_path or "<cadqa-source>", "exec")
            exec(compiled, namespace)
        except Exception as exc:
            raise CadQueryTraceError("source_exec_error", str(exc)) from exc
        targets = _assigned_names(statement, namespace, before)
        selector_text = _selector_text_for_statement(statement)
        for target in targets:
            selector_result = _selector_result_for_value(
                namespace.get(target),
                target=target,
                selector_text=selector_text,
                source_line=getattr(statement, "lineno", None),
                selector_index=selector_index,
            )
            if selector_result is not None:
                selector_results.append(selector_result)
                selector_index += 1
            snapshot = _snapshot_for_value(
                namespace.get(target),
                target=target,
                source_line=getattr(statement, "lineno", None),
                operation_index=operation_index,
            )
            if snapshot is None:
                continue
            snapshots.append(snapshot)
            operation_index += 1

    final_snapshot = _select_final_snapshot(namespace, snapshots)
    if final_snapshot is None:
        raise CadQueryTraceError("missing_result", "no measurable CadQuery result was produced")
    if final_snapshot.get("step") != "final":
        snapshots.append({**final_snapshot, "step": "final"})
    operation_effects = _snapshot_effects(snapshots)
    return {"snapshots": snapshots, "operation_effects": operation_effects, "selector_results": selector_results}


def _snapshot_for_value(
    value: Any,
    *,
    target: str,
    source_line: int | None,
    operation_index: int,
) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        shape = object_to_shape(value)
        measured = measure_shape(shape)
    except CadQueryTraceError as exc:
        if exc.failure_reason in {"invalid_cadquery_type", "missing_result", "non_solid_result"}:
            return None
        raise
    return {
        "step": "assignment",
        "target": target,
        "source_line": source_line,
        "operation_index": operation_index,
        **measured,
    }


def _selector_result_for_value(
    value: Any,
    *,
    target: str,
    selector_text: str | None,
    source_line: int | None,
    selector_index: int,
) -> dict[str, Any] | None:
    if selector_text is None or value is None:
        return None
    try:
        import cadquery as cq
    except Exception:
        return None
    if not isinstance(value, cq.Workplane):
        return None
    try:
        values = value.vals()
    except Exception:
        return None
    if not values:
        return {
            "target": target,
            "selector": selector_text,
            "source_line": source_line,
            "selector_index": selector_index,
            "selected_count": 0,
            "shape_types": [],
            "bbox_signatures": [],
            "evidence": "cadquery_selector_result",
        }
    shape_types: list[str] = []
    bbox_signatures: list[dict[str, list[float]] | None] = []
    for selected in values:
        shape_type = getattr(selected, "ShapeType", None)
        shape_types.append(str(shape_type()) if callable(shape_type) else type(selected).__name__)
        try:
            bbox_signatures.append(_bounding_box_from_shape(selected))
        except CadQueryTraceError:
            bbox_signatures.append(None)
    return {
        "target": target,
        "selector": selector_text,
        "source_line": source_line,
        "selector_index": selector_index,
        "selected_count": len(values),
        "shape_types": shape_types,
        "bbox_signatures": bbox_signatures,
        "evidence": "cadquery_selector_result",
    }


def _select_final_snapshot(
    namespace: dict[str, Any],
    snapshots: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for target in ("result", "shape", "solid", "part", "model", "base"):
        if target not in namespace:
            continue
        shape = object_to_shape(namespace[target])
        measured = measure_shape(shape)
        return {
            "step": "assignment",
            "target": target,
            "source_line": None,
            "operation_index": len(snapshots),
            **measured,
        }
    return snapshots[-1] if snapshots else None


def _assigned_names(statement: ast.stmt, namespace: dict[str, Any], before: set[str]) -> list[str]:
    names: list[str] = []
    if isinstance(statement, ast.Assign):
        for target in statement.targets:
            names.extend(_target_names(target))
    elif isinstance(statement, ast.AnnAssign):
        names.extend(_target_names(statement.target))
    elif isinstance(statement, ast.AugAssign):
        names.extend(_target_names(statement.target))
    elif isinstance(statement, (ast.For, ast.AsyncFor, ast.With, ast.Try, ast.If)):
        names.extend(_body_assigned_names(statement))
    else:
        names.extend(name for name in namespace.keys() - before if not name.startswith("__"))
    seen: set[str] = set()
    ordered = []
    for name in names:
        if name in namespace and name not in seen:
            ordered.append(name)
            seen.add(name)
    return ordered


def _target_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for item in target.elts:
            names.extend(_target_names(item))
        return names
    return []


def _body_assigned_names(statement: ast.stmt) -> list[str]:
    names: list[str] = []
    for node in ast.walk(statement):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                names.extend(_target_names(target))
        elif isinstance(node, ast.AnnAssign):
            names.extend(_target_names(node.target))
        elif isinstance(node, ast.AugAssign):
            names.extend(_target_names(node.target))
    return names


def _selector_text_for_statement(statement: ast.stmt) -> str | None:
    for node in ast.walk(statement):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "faces":
            continue
        if not node.args:
            return ""
        try:
            value = ast.literal_eval(node.args[0])
        except Exception:
            return ast.unparse(node.args[0])
        return str(value)
    return None


def _snapshot_effects(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    effects: list[dict[str, Any]] = []
    measured = [snapshot for snapshot in snapshots if snapshot.get("volume") is not None]
    for index, (before, after) in enumerate(zip(measured, measured[1:])):
        effects.append(
            {
                "effect_index": index,
                "from_target": before.get("target"),
                "to_target": after.get("target"),
                "source_line": after.get("source_line"),
                "signed_volume_delta": float(after["volume"]) - float(before["volume"]),
                "bbox_delta": _bbox_delta(before.get("bbox"), after.get("bbox")),
                "topology_delta": _topology_delta(before.get("topology"), after.get("topology")),
                "evidence": "cadquery_assignment_snapshot_delta",
            }
        )
    return effects


def _bbox_delta(before: Any, after: Any) -> dict[str, list[float | None]]:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return {"min": [None, None, None], "max": [None, None, None]}
    return {
        "min": [
            _optional_delta(before.get("min", [None] * 3), after.get("min", [None] * 3), index)
            for index in range(3)
        ],
        "max": [
            _optional_delta(before.get("max", [None] * 3), after.get("max", [None] * 3), index)
            for index in range(3)
        ],
    }


def _topology_delta(before: Any, after: Any) -> dict[str, int | None]:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return {}
    keys = sorted(set(before) | set(after))
    return {
        key: (
            int(after[key]) - int(before[key])
            if before.get(key) is not None and after.get(key) is not None
            else None
        )
        for key in keys
    }


def _optional_delta(before: Any, after: Any, index: int) -> float | None:
    try:
        lhs = before[index]
        rhs = after[index]
    except Exception:
        return None
    if lhs is None or rhs is None:
        return None
    return float(rhs) - float(lhs)


def _bounding_box_from_shape(shape: Any) -> dict[str, list[float]]:
    try:
        bbox = shape.BoundingBox()
        result = {
            "min": [float(bbox.xmin), float(bbox.ymin), float(bbox.zmin)],
            "max": [float(bbox.xmax), float(bbox.ymax), float(bbox.zmax)],
        }
    except Exception as exc:
        raise CadQueryTraceError("non_finite_bbox", str(exc)) from exc
    values = [*result["min"], *result["max"]]
    if not all(math.isfinite(value) for value in values):
        raise CadQueryTraceError("non_finite_bbox", f"bbox contains non-finite values: {result}")
    return result


def _topology_counts(shape: Any) -> dict[str, int | None]:
    return {
        "solids": _shape_count(shape, "Solids"),
        "shells": _shape_count(shape, "Shells"),
        "faces": _shape_count(shape, "Faces"),
        "wires": _shape_count(shape, "Wires"),
        "edges": _shape_count(shape, "Edges"),
        "vertices": _shape_count(shape, "Vertices"),
    }


def _shape_count(shape: Any, method_name: str) -> int | None:
    method = getattr(shape, method_name, None)
    if method is None:
        return None
    try:
        return len(method())
    except Exception:
        return None


def _record_from_completed_worker(job: _RunningTrace, *, timeout_seconds: float) -> TraceRecord:
    if job.process.exitcode != 0:
        return _failed_trace(job.source, "worker_crash", timeout_seconds=timeout_seconds)
    try:
        result = job.queue.get_nowait()
    except Empty:
        return _failed_trace(job.source, "worker_crash", timeout_seconds=timeout_seconds)
    return _trace_record_from_worker_result(job.source, result, timeout_seconds=timeout_seconds)


def _trace_record_from_worker_result(
    source: SourceRecord,
    result: dict[str, Any],
    *,
    timeout_seconds: float,
) -> TraceRecord:
    if result.get("status") == "error":
        return _failed_trace(
            source,
            str(result.get("failure_reason") or "unknown_error"),
            timeout_seconds=timeout_seconds,
        )
    return TraceRecord(
        source_id=source.source_id,
        execution_status="ok",
        snapshots=result["snapshots"],
        operation_effects=result["operation_effects"],
        selector_results=result.get("selector_results", []),
        environment=_environment(timeout_seconds=timeout_seconds),
        failure_reason=None,
    )


def _failed_trace(
    source: SourceRecord,
    failure_reason: str,
    *,
    timeout_seconds: float,
) -> TraceRecord:
    if failure_reason not in TRACE_FAILURE_REASONS:
        failure_reason = "unknown_error"
    return TraceRecord(
        source_id=source.source_id,
        execution_status="failed",
        snapshots=[],
        operation_effects=[],
        selector_results=[],
        environment=_environment(timeout_seconds=timeout_seconds),
        failure_reason=failure_reason,
    )


def _environment(*, timeout_seconds: float) -> dict[str, Any]:
    return {
        "cadquery_available": cadquery_available(),
        "cadquery_version": cadquery_version(),
        "ocp_version": ocp_version(),
        "timeout_seconds": timeout_seconds,
    }


def _trace_context() -> mp.context.BaseContext:
    main_file = getattr(sys.modules.get("__main__"), "__file__", None)
    if main_file and main_file.startswith("<") and "fork" in mp.get_all_start_methods():
        return mp.get_context("fork")
    return mp.get_context("spawn")


def _coerce_source(source: SourceRecord | Mapping[str, Any]) -> SourceRecord:
    if isinstance(source, SourceRecord):
        return source
    return source_record_from_mapping(dict(source))
