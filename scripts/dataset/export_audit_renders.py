"""Export optional SVG audit renders for a small dataset sample."""

from __future__ import annotations

import argparse
import ast
from multiprocessing import Process, Queue
from pathlib import Path
from queue import Empty
from typing import Any

from cad_qa.hashing import sha256_text
from cad_qa.jsonio import read_jsonl, write_json
from cad_qa.safety import safety_issues
from cad_qa.trace import _safe_builtins  # Reuse the trace worker execution sandbox.


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    report = export_audit_renders(
        args.dataset_dir,
        output_dir=args.output_dir,
        limit=args.limit,
        timeout_seconds=args.timeout_seconds,
        dry_run=args.dry_run,
    )
    print(report)


def export_audit_renders(
    dataset_dir: Path,
    *,
    output_dir: Path,
    limit: int = 16,
    timeout_seconds: float = 15.0,
    dry_run: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    svg_dir = output_dir / "svg"
    svg_dir.mkdir(exist_ok=True)
    sources = _records_by_key(dataset_dir / "sources.jsonl", "source_id")
    traces = _records_by_key(dataset_dir / "traces.jsonl", "source_id")
    render_items = []
    for source_id, source in sorted(sources.items())[:limit]:
        trace = traces.get(source_id, {})
        render_id = "render_" + sha256_text(f"{source_id}:{trace.get('trace_id')}").removeprefix("sha256:")[:16]
        svg_path = svg_dir / f"{render_id}.svg"
        if dry_run:
            item = _item(source, trace, render_id, svg_path, status="planned", failure_reason=None)
        else:
            result = _render_with_timeout(source.get("normalized_code", ""), trace.get("result_variable"), svg_path, timeout_seconds)
            item = _item(source, trace, render_id, svg_path, status=result["status"], failure_reason=result.get("failure_reason"))
        render_items.append(item)
    report = {
        "schema": "cadqa_audit_render_manifest_v1",
        "dataset_dir": str(dataset_dir),
        "output_dir": str(output_dir),
        "dry_run": dry_run,
        "requested_limit": limit,
        "render_count": len(render_items),
        "rendered_count": sum(1 for item in render_items if item["status"] == "rendered"),
        "items": render_items,
    }
    write_json(output_dir / "audit_render_manifest.json", report)
    return report


def _records_by_key(path: Path, key: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {str(row.get(key)): row for row in read_jsonl(path)}


def _item(
    source: dict[str, Any],
    trace: dict[str, Any],
    render_id: str,
    svg_path: Path,
    *,
    status: str,
    failure_reason: str | None,
) -> dict[str, Any]:
    return {
        "render_id": render_id,
        "source_id": source.get("source_id"),
        "trace_id": trace.get("trace_id"),
        "result_variable": trace.get("result_variable"),
        "status": status,
        "failure_reason": failure_reason,
        "svg_path": str(Path("svg") / svg_path.name),
        "camera": {"projection": "cadquery_default_svg"},
    }


def _render_with_timeout(code: str, result_variable: Any, svg_path: Path, timeout_seconds: float) -> dict[str, Any]:
    queue: Queue = Queue()
    process = Process(target=_render_worker, args=(code, str(result_variable or "result"), str(svg_path), queue))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(1.0)
        return {"status": "failed", "failure_reason": "render_timeout"}
    if process.exitcode != 0:
        return {"status": "failed", "failure_reason": "render_worker_crash"}
    try:
        return queue.get_nowait()
    except Empty:
        return {"status": "failed", "failure_reason": "render_worker_no_result"}


def _render_worker(code: str, result_variable: str, svg_path: str, queue: Queue) -> None:
    issues = safety_issues(code)
    if issues:
        queue.put({"status": "failed", "failure_reason": "safety_issues:" + ",".join(issues)})
        return
    try:
        import cadquery as cq  # type: ignore[import-not-found]
        from cadquery import exporters  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        queue.put({"status": "failed", "failure_reason": "cadquery_unavailable"})
        return
    namespace: dict[str, Any] = {"cq": cq, "cadquery": cq, "__builtins__": _safe_builtins()}
    try:
        tree = ast.parse(code)
        for statement in tree.body:
            exec(compile(ast.Module([statement], []), "<cadqa-render>", "exec"), namespace)
        obj = namespace.get(result_variable) or namespace.get("result")
        if obj is None:
            queue.put({"status": "failed", "failure_reason": "missing_result_variable"})
            return
        exporters.export(obj, svg_path)
    except Exception as exc:
        queue.put({"status": "failed", "failure_reason": f"render_error:{type(exc).__name__}"})
        return
    queue.put({"status": "rendered", "failure_reason": None})


if __name__ == "__main__":
    main()
