"""Dataset export orchestration."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from cad_qa.config import DatasetConfig
from cad_qa.fixtures import smoke_traces
from cad_qa.jsonio import write_json, write_jsonl
from cad_qa.materialize import materialize_rows, rows_to_dicts
from cad_qa.schema import SourceRecord, TraceRecord
from cad_qa.source import source_manifest_hash
from cad_qa.splits import assign_row_splits, leakage_audit, split_manifest


def export_dataset(
    pairs: Iterable[tuple[SourceRecord, TraceRecord]],
    *,
    output_dir: Path,
    config: DatasetConfig,
) -> dict[str, object]:
    pairs = list(pairs)
    sources = [source for source, _ in pairs]
    traces = [trace for _, trace in pairs]
    row_dicts = rows_to_dicts(
        [
            row
            for source, trace in pairs
            for row in materialize_rows(source, trace, config=config)
        ]
    )
    row_dicts = assign_row_splits(row_dicts, config.seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "sources.jsonl", sources)
    write_jsonl(output_dir / "traces.jsonl", traces)
    _write_split_jsonl(output_dir / "jsonl", row_dicts)
    manifest = split_manifest(row_dicts)
    write_json(output_dir / "split_manifest.json", manifest)
    failure_rows = [
        {
            "source_id": trace.source_id,
            "trace_id": trace.trace_id,
            "failure_reason": trace.failure_reason,
            "execution_status": trace.execution_status,
            "operation_graph_status": trace.operation_graph_status,
        }
        for trace in traces
        if trace.execution_status != "ok" or trace.failure_reason
    ]
    write_jsonl(output_dir / "failure_manifest.jsonl", failure_rows)
    metadata = _metadata(row_dicts, sources, traces, config=config)
    write_json(output_dir / "metadata.json", metadata)
    return metadata


def export_smoke_dataset(*, output_dir: Path, config: DatasetConfig) -> dict[str, object]:
    return export_dataset(smoke_traces(config), output_dir=output_dir, config=config)


def _write_split_jsonl(jsonl_dir: Path, rows: list[dict[str, object]]) -> None:
    by_split: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_split[str(row["split"])].append(row)
    for split, split_rows in sorted(by_split.items()):
        write_jsonl(jsonl_dir / f"{split}.jsonl", sorted(split_rows, key=lambda row: str(row["id"])))


def _metadata(
    rows: list[dict[str, object]],
    sources: list[SourceRecord],
    traces: list[TraceRecord],
    *,
    config: DatasetConfig,
) -> dict[str, object]:
    return {
        "schema": "cadqa_dataset_metadata_v1",
        "dataset_name": config.dataset_name,
        "dataset_version": config.dataset_version,
        "row_count": len(rows),
        "source_count": len(sources),
        "trace_count": len(traces),
        "row_counts_by_split": dict(Counter(str(row.get("split")) for row in rows)),
        "row_counts_by_task_type": dict(Counter(str(row.get("task_type")) for row in rows)),
        "row_counts_by_requires": dict(Counter(tag for row in rows for tag in _list_field(row, "requires"))),
        "row_counts_by_difficulty_tag": dict(Counter(tag for row in rows for tag in _list_field(row, "difficulty_tags"))),
        "source_manifest_hash": source_manifest_hash(sources),
        "generation_config_hash": config.config_hash,
        "label_policy": asdict(config.label_policy),
        "execution_environment": {
            "trace_environments": sorted({str(trace.environment) for trace in traces}),
        },
        "cadevolve_source_metadata": {
            "license": config.license,
            "source_policy": "local_or_adjacent_source_tree_preferred",
        },
        "known_limitations": [
            "CadQuery execution is optional and depends on the local environment.",
            "Feature provenance rows are conservative and require stored provenance records.",
            "Smoke fixtures are for golden validation and do not replace CADEvolve release data.",
        ],
        "leakage_audit": leakage_audit(rows),
    }


def _list_field(row: dict[str, object], key: str) -> list[str]:
    value = row.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
