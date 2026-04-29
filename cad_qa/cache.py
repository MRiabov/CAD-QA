"""Small JSONL-backed caches for expensive generation artifacts."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from cad_qa.config import DatasetConfig
from cad_qa.hashing import sha256_json
from cad_qa.schema import SourceRecord, TraceRecord


def trace_cache_key(source: SourceRecord, config: DatasetConfig) -> str:
    return sha256_json(
        {
            "source_id": source.source_id,
            "normalized_source_code_hash": source.hashes.get(
                "normalized_source_code_hash"
            ),
            "config_hash": config.config_hash,
            "trace_timeout_seconds": config.trace_timeout_seconds,
        }
    ).removeprefix("sha256:")


def trace_cache_path(
    cache_dir: Path, source: SourceRecord, config: DatasetConfig
) -> Path:
    key = trace_cache_key(source, config)
    return cache_dir / "traces" / key[:2] / f"{key}.json"


def load_cached_trace(
    cache_dir: Path | None, source: SourceRecord, config: DatasetConfig
) -> TraceRecord | None:
    if cache_dir is None:
        return None
    path = trace_cache_path(cache_dir, source, config)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return trace_record_from_dict(data)
    except Exception:
        return None


def store_cached_trace(
    cache_dir: Path | None,
    source: SourceRecord,
    config: DatasetConfig,
    trace: TraceRecord,
) -> None:
    if cache_dir is None:
        return
    path = trace_cache_path(cache_dir, source, config)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(asdict(trace), sort_keys=True) + "\n", encoding="utf-8"
    )
    tmp_path.replace(path)


def trace_record_from_dict(data: dict[str, Any]) -> TraceRecord:
    return TraceRecord(
        trace_id=str(data["trace_id"]),
        source_id=str(data["source_id"]),
        operation_graph_status=str(data["operation_graph_status"]),
        execution_status=str(data["execution_status"]),
        result_variable=data.get("result_variable"),
        operation_nodes=list(data.get("operation_nodes") or []),
        snapshots=list(data.get("snapshots") or []),
        label_policy=dict(data.get("label_policy") or {}),
        environment=dict(data.get("environment") or {}),
        hashes=dict(data.get("hashes") or {}),
        failure_reason=data.get("failure_reason"),
        selector_tables=list(data.get("selector_tables") or []),
        point_queries=list(data.get("point_queries") or []),
        provenance_records=list(data.get("provenance_records") or []),
        topology_matches=list(data.get("topology_matches") or []),
        graph_queries=list(data.get("graph_queries") or []),
        spatial_queries=list(data.get("spatial_queries") or []),
        bbox_region_queries=list(data.get("bbox_region_queries") or []),
        validity_probes=list(data.get("validity_probes") or []),
        candidate_descriptors=list(data.get("candidate_descriptors") or []),
        sampling_manifest=dict(data.get("sampling_manifest") or {}),
    )
