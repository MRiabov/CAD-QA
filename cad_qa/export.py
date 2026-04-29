"""Dataset export orchestration."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from cad_qa.config import DatasetConfig
from cad_qa.fixtures import smoke_traces
from cad_qa.jsonio import write_json, write_jsonl
from cad_qa.materialize import materialize_rows_with_manifest, rows_to_dicts
from cad_qa.scheduler import merge_manifests
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
    rows = []
    public_row_manifests = []
    for source, trace in pairs:
        materialized_rows, manifest = materialize_rows_with_manifest(
            source, trace, config=config
        )
        rows.extend(materialized_rows)
        public_row_manifests.append(manifest)
    row_dicts = rows_to_dicts(rows)
    row_dicts = assign_row_splits(row_dicts, config.seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "sources.jsonl", sources)
    write_jsonl(output_dir / "traces.jsonl", traces)
    _write_split_jsonl(output_dir / "jsonl", row_dicts)
    parquet_report = _write_parquet_files(output_dir / "parquet", row_dicts)
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
    metadata = _metadata(
        row_dicts,
        sources,
        traces,
        config=config,
        parquet_report=parquet_report,
        public_row_manifests=public_row_manifests,
    )
    write_json(output_dir / "metadata.json", metadata)
    return metadata


def export_smoke_dataset(
    *, output_dir: Path, config: DatasetConfig
) -> dict[str, object]:
    return export_dataset(smoke_traces(config), output_dir=output_dir, config=config)


def _write_split_jsonl(jsonl_dir: Path, rows: list[dict[str, object]]) -> None:
    by_split: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_split[str(row["split"])].append(row)
    for split, split_rows in sorted(by_split.items()):
        write_jsonl(
            jsonl_dir / f"{split}.jsonl",
            sorted(split_rows, key=lambda row: str(row["id"])),
        )


def _metadata(
    rows: list[dict[str, object]],
    sources: list[SourceRecord],
    traces: list[TraceRecord],
    *,
    config: DatasetConfig,
    parquet_report: dict[str, object],
    public_row_manifests: list[dict[str, object]],
) -> dict[str, object]:
    scheduling_manifest = merge_manifests(
        [
            *[dict(trace.sampling_manifest or {}) for trace in traces],
            *[dict(manifest) for manifest in public_row_manifests],
        ]
    )
    return {
        "schema": "cadqa_dataset_metadata_v1",
        "dataset_name": config.dataset_name,
        "dataset_version": config.dataset_version,
        "row_count": len(rows),
        "source_count": len(sources),
        "trace_count": len(traces),
        "row_counts_by_split": dict(Counter(str(row.get("split")) for row in rows)),
        "row_counts_by_task_type": dict(
            Counter(str(row.get("task_type")) for row in rows)
        ),
        "descriptor_counts_by_task_type": scheduling_manifest[
            "descriptor_counts_by_task_type"
        ],
        "scheduled_label_counts_by_task_type": scheduling_manifest[
            "scheduled_label_counts_by_task_type"
        ],
        "label_failure_counts_by_task_type": scheduling_manifest[
            "label_failure_counts_by_task_type"
        ],
        "exported_row_counts_by_task_type": scheduling_manifest[
            "exported_row_counts_by_task_type"
        ],
        "row_counts_by_requires": dict(
            Counter(tag for row in rows for tag in _list_field(row, "requires"))
        ),
        "row_counts_by_difficulty_tag": dict(
            Counter(tag for row in rows for tag in _list_field(row, "difficulty_tags"))
        ),
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
        "parquet_export": parquet_report,
    }


def _list_field(row: dict[str, object], key: str) -> list[str]:
    value = row.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _write_parquet_files(
    parquet_dir: Path, rows: list[dict[str, object]]
) -> dict[str, object]:
    parquet_dir.mkdir(parents=True, exist_ok=True)
    try:
        import pyarrow as pa  # type: ignore[import-not-found]
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        marker = parquet_dir / "PARQUET_NOT_WRITTEN.md"
        marker.write_text(
            "Parquet export requires the optional `parquet` extra: `uv run --extra parquet ...`.\n",
            encoding="utf-8",
        )
        return {"status": "skipped", "reason": "pyarrow_unavailable", "files": []}

    by_split: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_split[str(row["split"])].append(row)
    files = []
    for split, split_rows in sorted(by_split.items()):
        path = parquet_dir / f"{split}.parquet"
        try:
            table = pa.Table.from_pylist(
                sorted(split_rows, key=lambda row: str(row["id"]))
            )
            pq.write_table(table, path)
        except (pa.ArrowException, TypeError, ValueError) as exc:
            marker = parquet_dir / "PARQUET_NOT_WRITTEN.md"
            marker.write_text(
                "Parquet export was skipped because pyarrow could not infer a stable schema "
                f"for heterogeneous CAD-QA rows: {type(exc).__name__}: {exc}\n",
                encoding="utf-8",
            )
            return {
                "status": "skipped",
                "reason": "pyarrow_schema_inference_failed",
                "files": [],
            }
        files.append(str(path.name))
    return {"status": "written", "files": files}
