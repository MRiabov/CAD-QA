"""Benchmark current graph JSON payloads against a columnar Polars projection.

The current graph shard parquet format stores CAD graph entities, relations, and
measurements as JSON strings inside top-level parquet columns. This script
measures that hot-path cost against a flattened, no-JSON intermediate layout
for the columns most frequently needed by graph analysis and query synthesis:
entity/relation/measurement identity and CAD graph entity type, and
relation type metadata.

Example:
    uv run python tools/bench_graph_columnar.py \
      --shard runs/current_cadevolve1000_10k_regen_20260613/graph/graphs/part-00000.parquet \
      --out-dir /tmp/cadqa-graph-columnar-bench \
      --repeats 3
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import polars as pl
import psutil


def main() -> int:
    args = _parse_args()
    if args.phase:
        _run_phase(args)
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    convert_result = _spawn_phase(args, "convert")
    results.append(convert_result)

    for _ in range(args.repeats):
        results.append(_spawn_phase(args, "current-json"))
    for _ in range(args.repeats):
        results.append(_spawn_phase(args, "columnar-polars"))

    summary = _summarize(results)
    report = {
        "shard": str(args.shard),
        "out_dir": str(args.out_dir),
        "repeats": args.repeats,
        "workload": "CAD graph entity/relation/measurement count aggregates",
        "notes": [
            "current-json reads the existing graph shard and json.loads nodes/relations/measurements.",
            "columnar-polars reads flattened node/relation/measurement parquet tables with Polars lazy scans.",
            "convert is the one-time cost to build the flattened projection from the existing JSON-in-parquet shard.",
        ],
        "results": results,
        "summary": summary,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--phase", choices=["convert", "current-json", "columnar-polars"])
    return parser.parse_args()


def _spawn_phase(args: argparse.Namespace, phase: str) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--shard",
        str(args.shard),
        "--out-dir",
        str(args.out_dir),
        "--phase",
        phase,
    ]
    env = dict(os.environ)
    env.setdefault("POLARS_MAX_THREADS", str(os.cpu_count() or 1))
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
    return json.loads(completed.stdout)


def _run_phase(args: argparse.Namespace) -> None:
    monitor = _MemoryMonitor()
    monitor.start()
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    try:
        if args.phase == "convert":
            payload = _convert_graph_shard(args.shard, args.out_dir)
        elif args.phase == "current-json":
            payload = _current_json_workload(args.shard)
        elif args.phase == "columnar-polars":
            payload = _columnar_polars_workload(args.out_dir)
        else:
            raise AssertionError(args.phase)
    finally:
        wall_seconds = time.perf_counter() - wall_start
        cpu_seconds = time.process_time() - cpu_start
        monitor.stop()

    result = {
        "phase": args.phase,
        "wall_seconds": wall_seconds,
        "cpu_seconds": cpu_seconds,
        "max_rss_mb": max(_ru_maxrss_mb(), monitor.max_rss_mb),
        **payload,
    }
    print(json.dumps(result, sort_keys=True))


def _convert_graph_shard(shard: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    node_rows: list[dict[str, Any]] = []
    relation_rows: list[dict[str, Any]] = []
    measurement_rows: list[dict[str, Any]] = []

    frame = pl.read_parquet(shard, columns=["graph_id", "nodes", "relations", "measurements"])
    for row in frame.iter_rows(named=True):
        graph_id = str(row["graph_id"])
        for node in json.loads(row["nodes"]):
            node_rows.append(
                {
                    "graph_id": graph_id,
                    "node_id": _string_or_none(node.get("id")),
                    "node_type": _string_or_none(node.get("type")),
                    "label": _string_or_none(node.get("label")),
                    "source_ref": _string_or_none(node.get("source_ref")),
                }
            )
        for relation in json.loads(row["relations"]):
            relation_rows.append(
                {
                    "graph_id": graph_id,
                    "source_id": _string_or_none(relation.get("source_id")),
                    "target_id": _string_or_none(relation.get("target_id")),
                    "relation_type": _string_or_none(relation.get("type")),
                    "evidence": _string_or_none(relation.get("evidence")),
                }
            )
        for measurement in json.loads(row["measurements"]):
            value = measurement.get("value")
            measurement_rows.append(
                {
                    "graph_id": graph_id,
                    "entity_id": _string_or_none(measurement.get("entity_id")),
                    "measurement_name": _string_or_none(measurement.get("name")),
                    "scope": _string_or_none(measurement.get("scope")),
                    "unit": _string_or_none(measurement.get("unit")),
                    "value_float": _float_or_none(value),
                    "value_kind": type(value).__name__,
                }
            )

    nodes = pl.DataFrame(node_rows)
    relations = pl.DataFrame(relation_rows)
    measurements = pl.DataFrame(measurement_rows)
    nodes.write_parquet(out_dir / "nodes.parquet", compression="zstd")
    relations.write_parquet(out_dir / "relations.parquet", compression="zstd")
    measurements.write_parquet(out_dir / "measurements.parquet", compression="zstd")
    return {
        "graph_count": frame.height,
        "node_count": nodes.height,
        "relation_count": relations.height,
        "measurement_count": measurements.height,
        "columnar_bytes": _path_size(out_dir / "nodes.parquet")
        + _path_size(out_dir / "relations.parquet")
        + _path_size(out_dir / "measurements.parquet"),
        "source_bytes": _path_size(shard),
    }


def _current_json_workload(shard: Path) -> dict[str, Any]:
    frame = pl.read_parquet(shard, columns=["graph_id", "nodes", "relations", "measurements"])
    node_type_counts: dict[str, int] = {}
    relation_type_counts: dict[str, int] = {}
    measurement_scope_counts: dict[str, int] = {}
    measurement_name_counts: dict[str, int] = {}
    node_count = 0
    relation_count = 0
    measurement_count = 0
    for row in frame.iter_rows(named=True):
        nodes = json.loads(row["nodes"])
        relations = json.loads(row["relations"])
        measurements = json.loads(row["measurements"])
        node_count += len(nodes)
        relation_count += len(relations)
        measurement_count += len(measurements)
        for node in nodes:
            _increment(node_type_counts, node.get("type"))
        for relation in relations:
            _increment(relation_type_counts, relation.get("type"))
        for measurement in measurements:
            _increment(measurement_scope_counts, measurement.get("scope"))
            _increment(measurement_name_counts, measurement.get("name"))
    return {
        "graph_count": frame.height,
        "node_count": node_count,
        "relation_count": relation_count,
        "measurement_count": measurement_count,
        "node_type_count": len(node_type_counts),
        "relation_type_count": len(relation_type_counts),
        "measurement_scope_count": len(measurement_scope_counts),
        "measurement_name_count": len(measurement_name_counts),
    }


def _columnar_polars_workload(out_dir: Path) -> dict[str, Any]:
    nodes = pl.scan_parquet(out_dir / "nodes.parquet")
    relations = pl.scan_parquet(out_dir / "relations.parquet")
    measurements = pl.scan_parquet(out_dir / "measurements.parquet")
    node_counts = nodes.group_by("node_type").len().collect()
    relation_counts = relations.group_by("relation_type").len().collect()
    measurement_scope_counts = measurements.group_by("scope").len().collect()
    measurement_name_counts = measurements.group_by("measurement_name").len().collect()
    totals = pl.concat(
        [
            nodes.select(pl.n_unique("graph_id").alias("graph_count"), pl.len().alias("node_count")),
            relations.select(pl.n_unique("graph_id").alias("graph_count"), pl.len().alias("relation_count")),
            measurements.select(pl.n_unique("graph_id").alias("graph_count"), pl.len().alias("measurement_count")),
        ],
        how="diagonal",
    ).collect()
    return {
        "graph_count": int(totals["graph_count"].max()),
        "node_count": int(totals["node_count"].sum()),
        "relation_count": int(totals["relation_count"].sum()),
        "measurement_count": int(totals["measurement_count"].sum()),
        "node_type_count": node_counts.height,
        "relation_type_count": relation_counts.height,
        "measurement_scope_count": measurement_scope_counts.height,
        "measurement_name_count": measurement_name_counts.height,
    }


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for phase in sorted({result["phase"] for result in results}):
        phase_results = [result for result in results if result["phase"] == phase]
        summary[phase] = {
            "runs": len(phase_results),
            "wall_seconds_min": min(result["wall_seconds"] for result in phase_results),
            "wall_seconds_median": _median(result["wall_seconds"] for result in phase_results),
            "cpu_seconds_median": _median(result["cpu_seconds"] for result in phase_results),
            "max_rss_mb_median": _median(result["max_rss_mb"] for result in phase_results),
        }
    if "current-json" in summary and "columnar-polars" in summary:
        current = summary["current-json"]["wall_seconds_median"]
        columnar = summary["columnar-polars"]["wall_seconds_median"]
        summary["columnar_speedup_vs_current_json"] = current / columnar if columnar else None
    return summary


def _increment(counts: dict[str, int], value: Any) -> None:
    key = str(value)
    counts[key] = counts.get(key, 0) + 1


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return repr(value)


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _path_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def _median(values: Any) -> float:
    ordered = sorted(float(value) for value in values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _ru_maxrss_mb() -> float:
    # Linux reports kilobytes; macOS reports bytes. This repo is run on Linux.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


class _MemoryMonitor:
    def __init__(self) -> None:
        self._process = psutil.Process()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self.max_rss_mb = 0.0

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)

    def _sample(self) -> None:
        while not self._stop.is_set():
            try:
                self.max_rss_mb = max(self.max_rss_mb, self._process.memory_info().rss / (1024 * 1024))
            except psutil.Error:
                return
            self._stop.wait(0.01)


if __name__ == "__main__":
    raise SystemExit(main())
