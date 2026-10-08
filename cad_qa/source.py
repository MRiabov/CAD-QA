"""CadQuery program records and JSONL loading."""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
import re
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq

from cad_qa.io import iter_records, read_records


PROTECTED_SOURCE_GROUP_KEYS = (
    "split_group",
    "counterfactual_group",
    "source_family",
    "family_id",
    "template_id",
)
REPORTED_SOURCE_PROVENANCE_KEYS = (
    "generator_id",
    "generator",
)
DEFAULT_CADEVOLVE_CACHE_WORKERS = min(64, max(8, (os.cpu_count() or 4) * 4))
DEFAULT_CADEVOLVE_CACHE_READ_BATCH = 512
DEFAULT_CADEVOLVE_SOURCE_PARQUET_BATCH = 10_000


@dataclass(frozen=True)
class _CadevolveDirectoryCandidate:
    member_path: str
    abs_path: Path


@dataclass
class _CadevolveDirectoryProcessResult:
    skipped_code_contains: bool = False
    skipped_non_cadquery: bool = False
    row: dict[str, Any] | None = None


GEOMETRY_SOURCE_FEATURE_TAGS = (
    "path_curve",
    "kernel_vertex_selector",
    "kernel_face_selector",
    "kernel_edge_selector",
    "void_cut",
    "profile_polyline",
)
_CADQUERY_METHOD_TAGS = (
    ("path_curve", ("spline", "splineApprox", "parametricCurve")),
    ("kernel_vertex_selector", ("vertices",)),
    ("kernel_face_selector", ("faces",)),
    ("kernel_edge_selector", ("edges",)),
    ("void_cut", ("cut", "cutThruAll", "cutBlind", "hole", "cboreHole", "cskHole")),
    ("profile_polyline", ("polyline",)),
)
CADEVOLVE_SOURCE_CACHE_COLUMNS = (
    "source_id",
    "normalized_archive_member_path",
    "normalized_code",
    "source",
    "source_subtree",
    "source_collection",
    "path_family",
    "source_feature_tags",
    "generator_id",
    "normalized_source_code_hash",
)
_CADEVOLVE_SOURCE_CACHE_SCHEMA = pa.schema(
    [
        pa.field("source_id", pa.string()),
        pa.field("normalized_archive_member_path", pa.string()),
        pa.field("normalized_code", pa.string()),
        pa.field("source", pa.string()),
        pa.field("source_subtree", pa.string()),
        pa.field("source_collection", pa.string()),
        pa.field("path_family", pa.string()),
        pa.field("source_feature_tags", pa.list_(pa.string())),
        pa.field("generator_id", pa.string()),
        pa.field("normalized_source_code_hash", pa.string()),
    ]
)


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    source_code: str
    source_path: str | None = None
    source_hash: str | None = None
    metadata: dict[str, Any] | None = None


def normalize_source_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [line.rstrip() for line in lines]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def short_hash(text: str, length: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def source_record_from_mapping(data: dict[str, Any]) -> SourceRecord:
    code = data.get("normalized_code") or data.get("source_code") or data.get("raw_code")
    if not isinstance(code, str) or not code.strip():
        raise ValueError("source row is missing normalized_code/source_code/raw_code")
    normalized = normalize_source_text(code)
    source_hash = "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    source_path = (
        data.get("normalized_archive_member_path")
        or data.get("archive_member_path")
        or data.get("source_path")
    )
    source_id = data.get("source_id") or "src_" + short_hash(
        f"{source_path or ''}\n{source_hash}"
    )
    metadata = {
        key: value
        for key, value in data.items()
        if key
        not in {
            "source_id",
            "normalized_code",
            "source_code",
            "raw_code",
            "normalized_archive_member_path",
            "archive_member_path",
            "source_path",
        }
    }
    if source_path and "path_family" not in metadata:
        metadata["path_family"] = source_family_from_path(str(source_path))
    return SourceRecord(
        source_id=str(source_id),
        source_code=normalized,
        source_path=str(source_path) if source_path else None,
        source_hash=source_hash,
        metadata=metadata,
    )


def load_sources_jsonl(path: Path, *, limit: int | None = None) -> list[SourceRecord]:
    records = [source_record_from_mapping(row) for row in read_records(path)]
    return records[:limit] if limit is not None else records


def cadevolve_tar_source_rows(
    tar_path: Path,
    *,
    limit: int | None = None,
    path_prefixes: list[str] | None = None,
    path_contains: list[str] | None = None,
    code_contains: list[str] | None = None,
    max_member_bytes: int = 1_000_000,
    stratify_by_tags: bool = False,
    min_per_tag: int = 0,
    complete_stratified_scan: bool = False,
    workers: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Extract normalized CadQuery program rows from the upstream CadQuery program corpus archive."""

    if stratify_by_tags or limit is not None:
        return _cadevolve_tar_source_rows_sequential(
            tar_path,
            limit=limit,
            path_prefixes=path_prefixes,
            path_contains=path_contains,
            code_contains=code_contains,
            max_member_bytes=max_member_bytes,
            stratify_by_tags=stratify_by_tags,
            min_per_tag=min_per_tag,
            complete_stratified_scan=complete_stratified_scan,
        )
    return _cadevolve_tar_source_rows_full_scan(
        tar_path,
        path_prefixes=path_prefixes,
        path_contains=path_contains,
        code_contains=code_contains,
        max_member_bytes=max_member_bytes,
        workers=workers,
    )


def _cadevolve_tar_source_rows_sequential(
    tar_path: Path,
    *,
    limit: int | None = None,
    path_prefixes: list[str] | None = None,
    path_contains: list[str] | None = None,
    code_contains: list[str] | None = None,
    max_member_bytes: int = 1_000_000,
    stratify_by_tags: bool = False,
    min_per_tag: int = 0,
    complete_stratified_scan: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Extract normalized CadQuery program rows from the upstream CadQuery program corpus archive."""

    prefixes = tuple(_normalize_archive_path(prefix) for prefix in path_prefixes or [] if prefix)
    path_needles = tuple(value.lower() for value in path_contains or [] if value)
    code_needles = tuple(value.lower() for value in code_contains or [] if value)
    rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    stats = {
        "archive_path": str(tar_path),
        "member_count": 0,
        "python_member_count": 0,
        "candidate_count": 0,
        "included_count": 0,
        "skipped_non_python_count": 0,
        "skipped_prefix_count": 0,
        "skipped_path_contains_count": 0,
        "skipped_large_member_count": 0,
        "skipped_code_contains_count": 0,
        "skipped_non_cadquery_count": 0,
        "limit": limit,
        "max_member_bytes": max_member_bytes,
        "path_prefixes": list(prefixes),
        "path_contains": list(path_needles),
        "code_contains": list(code_needles),
        "selection_policy": "geometry_tag_stratified" if stratify_by_tags else "archive_order",
        "candidate_scan_exhausted": True,
        "complete_stratified_scan": complete_stratified_scan,
        "geometry_feature_tags": list(GEOMETRY_SOURCE_FEATURE_TAGS),
        "min_per_geometry_tag": max(1, min_per_tag) if stratify_by_tags else min_per_tag,
    }
    with tarfile.open(tar_path, "r:*") as archive:
        for member in archive:
            stats["member_count"] += 1
            if not stratify_by_tags and limit is not None and len(rows) >= limit:
                break
            if not member.isfile():
                continue
            member_path = _normalize_archive_path(member.name)
            if prefixes and not any(_archive_path_matches_prefix(member_path, prefix) for prefix in prefixes):
                stats["skipped_prefix_count"] += 1
                continue
            if path_needles and not any(needle in member_path.lower() for needle in path_needles):
                stats["skipped_path_contains_count"] += 1
                continue
            if not member_path.endswith(".py"):
                stats["skipped_non_python_count"] += 1
                continue
            stats["python_member_count"] += 1
            if member.size > max_member_bytes:
                stats["skipped_large_member_count"] += 1
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            source_code = normalize_source_text(handle.read().decode("utf-8", errors="replace"))
            if code_needles and not any(needle in source_code.lower() for needle in code_needles):
                stats["skipped_code_contains_count"] += 1
                continue
            if not _looks_like_cadquery_source(source_code):
                stats["skipped_non_cadquery_count"] += 1
                continue
            row = _cadevolve_source_row(member_path, source_code)
            if stratify_by_tags:
                candidate_rows.append(row)
                if (
                    not complete_stratified_scan
                    and _stratified_selection_ready(
                        candidate_rows,
                        limit=limit,
                        min_per_tag=max(1, min_per_tag),
                    )
                ):
                    stats["candidate_scan_exhausted"] = False
                    break
            else:
                rows.append(row)
    if stratify_by_tags:
        rows = _select_stratified_source_rows(
            candidate_rows,
            limit=limit,
            min_per_tag=max(1, min_per_tag),
        )
    else:
        candidate_rows = rows
    stats["candidate_count"] = len(candidate_rows)
    stats["included_count"] = len(rows)
    stats["candidate_geometry_feature_tag_counts"] = _source_feature_tag_counts(candidate_rows)
    stats["selected_geometry_feature_tag_counts"] = _source_feature_tag_counts(rows)
    return rows, stats


def _cadevolve_tar_source_rows_full_scan(
    tar_path: Path,
    *,
    path_prefixes: list[str] | None = None,
    path_contains: list[str] | None = None,
    code_contains: list[str] | None = None,
    max_member_bytes: int = 1_000_000,
    workers: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    prefixes = tuple(_normalize_archive_path(prefix) for prefix in path_prefixes or [] if prefix)
    path_needles = tuple(value.lower() for value in path_contains or [] if value)
    code_needles = tuple(value.lower() for value in code_contains or [] if value)
    worker_count = _resolve_cadevolve_cache_workers(workers)
    stats = {
        "archive_path": str(tar_path),
        "member_count": 0,
        "python_member_count": 0,
        "candidate_count": 0,
        "included_count": 0,
        "skipped_non_python_count": 0,
        "skipped_prefix_count": 0,
        "skipped_path_contains_count": 0,
        "skipped_large_member_count": 0,
        "skipped_code_contains_count": 0,
        "skipped_non_cadquery_count": 0,
        "limit": None,
        "max_member_bytes": max_member_bytes,
        "path_prefixes": list(prefixes),
        "path_contains": list(path_needles),
        "code_contains": list(code_needles),
        "selection_policy": "archive_order",
        "candidate_scan_exhausted": True,
        "complete_stratified_scan": False,
        "geometry_feature_tags": list(GEOMETRY_SOURCE_FEATURE_TAGS),
        "min_per_geometry_tag": 0,
    }
    candidates: list[tuple[str, tarfile.TarInfo]] = []
    with tarfile.open(tar_path, "r:*") as archive:
        for member in archive:
            stats["member_count"] += 1
            if not member.isfile():
                continue
            member_path = _normalize_archive_path(member.name)
            if prefixes and not any(_archive_path_matches_prefix(member_path, prefix) for prefix in prefixes):
                stats["skipped_prefix_count"] += 1
                continue
            if path_needles and not any(needle in member_path.lower() for needle in path_needles):
                stats["skipped_path_contains_count"] += 1
                continue
            if not member_path.endswith(".py"):
                stats["skipped_non_python_count"] += 1
                continue
            stats["python_member_count"] += 1
            if member.size > max_member_bytes:
                stats["skipped_large_member_count"] += 1
                continue
            candidates.append((member_path, member))

    rows: list[dict[str, Any]] = []
    read_batch_size = max(DEFAULT_CADEVOLVE_CACHE_READ_BATCH, worker_count * 8)
    with tarfile.open(tar_path, "r:*") as archive:
        for chunk in _chunked(candidates, read_batch_size):
            payloads: list[tuple[str, str]] = []
            for member_path, member in chunk:
                handle = archive.extractfile(member)
                if handle is None:
                    continue
                payloads.append(
                    (
                        member_path,
                        handle.read().decode("utf-8", errors="replace"),
                    )
                )
            if worker_count <= 1:
                chunk_results = [
                    _cadevolve_source_row_from_text(member_path, source_text, code_needles=code_needles)
                    for member_path, source_text in payloads
                ]
            else:
                with ThreadPoolExecutor(max_workers=worker_count) as pool:
                    chunk_results = list(
                        pool.map(
                            lambda payload: _cadevolve_source_row_from_text(
                                payload[0],
                                payload[1],
                                code_needles=code_needles,
                            ),
                            payloads,
                        )
                    )
            for result in chunk_results:
                if result.skipped_code_contains:
                    stats["skipped_code_contains_count"] += 1
                    continue
                if result.skipped_non_cadquery:
                    stats["skipped_non_cadquery_count"] += 1
                    continue
                if result.row is not None:
                    rows.append(result.row)
                    stats["included_count"] += 1

    stats["candidate_count"] = len(rows)
    stats["candidate_geometry_feature_tag_counts"] = _source_feature_tag_counts(rows)
    stats["selected_geometry_feature_tag_counts"] = _source_feature_tag_counts(rows)
    return rows, stats


def cadevolve_directory_source_rows(
    root_path: Path,
    *,
    path_prefixes: list[str] | None = None,
    path_contains: list[str] | None = None,
    code_contains: list[str] | None = None,
    max_member_bytes: int = 1_000_000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build normalized CadQuery program rows from a directory extracted from the upstream CadQuery program corpus archive."""

    stats = cadevolve_directory_scan_stats(
        root_path,
        path_prefixes=path_prefixes,
        path_contains=path_contains,
        code_contains=code_contains,
        max_member_bytes=max_member_bytes,
    )
    rows = list(
        iter_cadevolve_directory_source_rows(
            root_path,
            stats=stats,
            path_prefixes=path_prefixes,
            path_contains=path_contains,
            code_contains=code_contains,
            max_member_bytes=max_member_bytes,
        )
    )
    stats["selected_geometry_feature_tag_counts"] = _source_feature_tag_counts(rows)
    return rows, stats


def cadevolve_directory_scan_stats(
    root_path: Path,
    *,
    path_prefixes: list[str] | None = None,
    path_contains: list[str] | None = None,
    code_contains: list[str] | None = None,
    max_member_bytes: int = 1_000_000,
) -> dict[str, Any]:
    prefixes = tuple(_normalize_archive_path(prefix) for prefix in path_prefixes or [] if prefix)
    path_needles = tuple(value.lower() for value in path_contains or [] if value)
    code_needles = tuple(value.lower() for value in code_contains or [] if value)
    return {
        "root_path": str(root_path),
        "file_count": 0,
        "python_file_count": 0,
        "included_count": 0,
        "skipped_non_python_count": 0,
        "skipped_prefix_count": 0,
        "skipped_path_contains_count": 0,
        "skipped_large_member_count": 0,
        "skipped_code_contains_count": 0,
        "skipped_non_cadquery_count": 0,
        "max_member_bytes": max_member_bytes,
        "path_prefixes": list(prefixes),
        "path_contains": list(path_needles),
        "code_contains": list(code_needles),
        "selection_policy": "directory_order",
        "geometry_feature_tags": list(GEOMETRY_SOURCE_FEATURE_TAGS),
        "selected_geometry_feature_tag_counts": {tag: 0 for tag in GEOMETRY_SOURCE_FEATURE_TAGS},
    }


def iter_cadevolve_directory_source_rows(
    root_path: Path,
    *,
    stats: dict[str, Any] | None = None,
    path_prefixes: list[str] | None = None,
    path_contains: list[str] | None = None,
    code_contains: list[str] | None = None,
    max_member_bytes: int = 1_000_000,
    workers: int | None = None,
):
    """Yield normalized CadQuery program rows from a directory extracted from the upstream CadQuery program corpus archive."""

    prefixes = tuple(_normalize_archive_path(prefix) for prefix in path_prefixes or [] if prefix)
    path_needles = tuple(value.lower() for value in path_contains or [] if value)
    code_needles = tuple(value.lower() for value in code_contains or [] if value)
    if stats is None:
        stats = cadevolve_directory_scan_stats(
            root_path,
            path_prefixes=path_prefixes,
            path_contains=path_contains,
            code_contains=code_contains,
            max_member_bytes=max_member_bytes,
        )
    worker_count = _resolve_cadevolve_cache_workers(workers)
    tag_counts = Counter(stats.get("selected_geometry_feature_tag_counts", {}))
    file_entries = _collect_cadevolve_directory_files(root_path, workers=worker_count)
    candidates = _cadevolve_directory_candidates(
        file_entries,
        prefixes=prefixes,
        path_needles=path_needles,
        max_member_bytes=max_member_bytes,
        stats=stats,
    )
    process_chunk_size = max(DEFAULT_CADEVOLVE_CACHE_READ_BATCH, worker_count * 8)

    def consume_result(result: _CadevolveDirectoryProcessResult) -> dict[str, Any] | None:
        if result.skipped_code_contains:
            stats["skipped_code_contains_count"] += 1
            return None
        if result.skipped_non_cadquery:
            stats["skipped_non_cadquery_count"] += 1
            return None
        row = result.row
        if row is None:
            return None
        stats["included_count"] += 1
        tag_counts.update(row.get("source_feature_tags", []))
        stats["selected_geometry_feature_tag_counts"] = {
            tag: tag_counts.get(tag, 0) for tag in GEOMETRY_SOURCE_FEATURE_TAGS
        }
        return row

    if worker_count <= 1:
        for candidate in candidates:
            row = consume_result(_process_cadevolve_directory_candidate(candidate, code_needles=code_needles))
            if row is not None:
                yield row
        return

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        for chunk in _chunked(candidates, process_chunk_size):
            for result in pool.map(
                lambda candidate: _process_cadevolve_directory_candidate(candidate, code_needles=code_needles),
                chunk,
            ):
                row = consume_result(result)
                if row is not None:
                    yield row


def cadevolve_source_table_rows(
    table_path: Path,
    *,
    limit: int | None = None,
    path_prefixes: list[str] | None = None,
    path_contains: list[str] | None = None,
    code_contains: list[str] | None = None,
    exclude_source_ids: set[str] | None = None,
    stratify_by_tags: bool = False,
    min_per_tag: int = 0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select normalized CadQuery program rows from a cached parquet table."""

    prefixes = tuple(_normalize_archive_path(prefix) for prefix in path_prefixes or [] if prefix)
    path_needles = tuple(value.lower() for value in path_contains or [] if value)
    code_needles = tuple(value.lower() for value in code_contains or [] if value)
    selected_rows: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    excluded = set(exclude_source_ids or set())
    selected_tag_counts: Counter[str] = Counter()
    first_candidate_rows: list[dict[str, Any]] = []
    rows_by_tag: dict[str, list[dict[str, Any]]] = {tag: [] for tag in GEOMETRY_SOURCE_FEATURE_TAGS}
    candidate_tag_counts: Counter[str] = Counter()
    stats = {
        "source_table_path": str(table_path),
        "table_row_count": 0,
        "candidate_count": 0,
        "included_count": 0,
        "skipped_prefix_count": 0,
        "skipped_path_contains_count": 0,
        "skipped_code_contains_count": 0,
        "skipped_excluded_source_count": 0,
        "excluded_source_count": len(excluded),
        "limit": limit,
        "path_prefixes": list(prefixes),
        "path_contains": list(path_needles),
        "code_contains": list(code_needles),
        "selection_policy": "geometry_tag_stratified" if stratify_by_tags else "table_order",
        "geometry_feature_tags": list(GEOMETRY_SOURCE_FEATURE_TAGS),
        "min_per_geometry_tag": max(1, min_per_tag) if stratify_by_tags else min_per_tag,
        "candidate_scan_exhausted": True,
    }
    for row in iter_records(table_path):
        stats["table_row_count"] += 1
        member_path = _normalize_archive_path(
            str(row.get("normalized_archive_member_path") or row.get("archive_member_path") or row.get("source_path") or "")
        )
        source_code = str(row.get("normalized_code") or row.get("source_code") or row.get("raw_code") or "")
        if prefixes and not any(_archive_path_matches_prefix(member_path, prefix) for prefix in prefixes):
            stats["skipped_prefix_count"] += 1
            continue
        if path_needles and not any(needle in member_path.lower() for needle in path_needles):
            stats["skipped_path_contains_count"] += 1
            continue
        if code_needles and not any(needle in source_code.lower() for needle in code_needles):
            stats["skipped_code_contains_count"] += 1
            continue
        normalized_row = dict(row)
        source_id = str(normalized_row.get("source_id") or "")
        if source_id and source_id in excluded:
            stats["skipped_excluded_source_count"] += 1
            continue
        if not isinstance(normalized_row.get("source_feature_tags"), list):
            normalized_row["source_feature_tags"] = source_geometry_feature_tags(source_code)
        tags = [tag for tag in normalized_row.get("source_feature_tags", []) if isinstance(tag, str)]
        candidate_tag_counts.update(tags)
        stats["candidate_count"] += 1
        if stratify_by_tags:
            if limit is None or len(first_candidate_rows) < limit:
                first_candidate_rows.append(normalized_row)
            for tag in GEOMETRY_SOURCE_FEATURE_TAGS:
                if tag in tags and len(rows_by_tag[tag]) < max(1, min_per_tag):
                    rows_by_tag[tag].append(normalized_row)
        else:
            if limit is None or len(selected_rows) < limit:
                selected_rows.append(normalized_row)
                selected_ids.add(str(normalized_row.get("source_id", "")))
                selected_tag_counts.update(tags)
            if limit is not None and len(selected_rows) >= limit:
                stats["candidate_scan_exhausted"] = False
                break

    if stratify_by_tags:
        selected_rows = _select_cached_stratified_rows(
            rows_by_tag,
            first_candidate_rows,
            limit=limit,
            selected_ids=selected_ids,
            selected_tag_counts=selected_tag_counts,
        )
    else:
        selected_rows = selected_rows
    stats["included_count"] = len(selected_rows)
    stats["candidate_geometry_feature_tag_counts"] = {
        tag: candidate_tag_counts.get(tag, 0) for tag in GEOMETRY_SOURCE_FEATURE_TAGS
    }
    stats["selected_geometry_feature_tag_counts"] = {
        tag: selected_tag_counts.get(tag, 0) for tag in GEOMETRY_SOURCE_FEATURE_TAGS
    }
    return selected_rows, stats


def write_cadevolve_source_cache_parquet(
    path: Path,
    rows: Iterable[dict[str, Any]],
    *,
    batch_size: int = DEFAULT_CADEVOLVE_SOURCE_PARQUET_BATCH,
) -> int:
    """Write upstream CadQuery program corpus rows as real parquet columns, not JSON blobs."""

    path.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    batch: list[dict[str, Any]] = []
    count = 0

    def flush() -> None:
        nonlocal batch, count, writer
        if not batch:
            return
        table = pa.Table.from_pylist(
            [_cadevolve_source_cache_row(row) for row in batch],
            schema=_CADEVOLVE_SOURCE_CACHE_SCHEMA,
        )
        if writer is None:
            writer = pq.ParquetWriter(path, table.schema, compression="zstd")
        writer.write_table(table)
        count += len(batch)
        batch = []

    try:
        for row in rows:
            batch.append(row)
            if len(batch) >= batch_size:
                flush()
        flush()
    finally:
        if writer is not None:
            writer.close()
    return count


def source_geometry_feature_tags(source_code: str) -> list[str]:
    """Return CadQuery program-level geometry hints used to keep rare release families reachable."""

    tags: list[str] = []
    for tag, methods in _CADQUERY_METHOD_TAGS:
        if any(_calls_method(source_code, method) for method in methods):
            tags.append(tag)
    return tags


def _cadevolve_source_row(member_path: str, source_code: str) -> dict[str, Any]:
    source_hash = "sha256:" + hashlib.sha256(source_code.encode("utf-8")).hexdigest()
    source_id = "src_" + short_hash(f"{member_path}\n{source_hash}")
    source_subtree, source_collection = _cadevolve_path_parts(member_path)
    return {
        "source_id": source_id,
        "normalized_code": source_code,
        "normalized_archive_member_path": member_path,
        "source": "cadevolve",
        "source_subtree": source_subtree,
        "source_collection": source_collection,
        "path_family": source_family_from_path(member_path),
        "source_feature_tags": source_geometry_feature_tags(source_code),
        "generator_id": "_".join(
            part.lower().replace("-", "_")
            for part in ("cadevolve", source_subtree, source_collection)
            if part
        ),
        "hashes": {"normalized_source_code_hash": source_hash},
    }


def _cadevolve_source_cache_row(row: dict[str, Any]) -> dict[str, Any]:
    source_code = str(row.get("normalized_code") or row.get("source_code") or row.get("raw_code") or "")
    source_hash = row.get("normalized_source_code_hash")
    hashes = row.get("hashes")
    if not isinstance(source_hash, str) and isinstance(hashes, dict):
        source_hash = hashes.get("normalized_source_code_hash")
    if not isinstance(source_hash, str):
        source_hash = "sha256:" + hashlib.sha256(source_code.encode("utf-8")).hexdigest()
    return {
        "source_id": str(row.get("source_id") or ""),
        "normalized_archive_member_path": str(
            row.get("normalized_archive_member_path") or row.get("archive_member_path") or row.get("source_path") or ""
        ),
        "normalized_code": normalize_source_text(source_code) if source_code else "",
        "source": str(row.get("source") or "cadevolve"),
        "source_subtree": str(row.get("source_subtree") or ""),
        "source_collection": str(row.get("source_collection") or ""),
        "path_family": str(row.get("path_family") or ""),
        "source_feature_tags": [
            str(tag)
            for tag in row.get("source_feature_tags", [])
            if isinstance(tag, str)
        ],
        "generator_id": str(row.get("generator_id") or ""),
        "normalized_source_code_hash": source_hash,
    }


def source_to_dict(source: SourceRecord) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "source_code": source.source_code,
        "source_path": source.source_path,
        "source_hash": source.source_hash,
        "metadata": source.metadata or {},
    }


def source_family_from_path(path: str) -> str:
    """Derive a stable family label from an archive member path in the upstream CadQuery program corpus."""

    normalized = path.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    if len(parts) < 3:
        return normalized
    stem = parts[2]
    if "__" in stem:
        stem = stem.split("__", 1)[0]
    if "+r" in stem:
        stem = stem.split("+r", 1)[0]
    return "/".join([*parts[:2], stem])


def _normalize_archive_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _resolve_cadevolve_cache_workers(workers: int | None) -> int:
    if workers is None:
        return DEFAULT_CADEVOLVE_CACHE_WORKERS
    return max(1, workers)


def _chunked(values: list[Any], chunk_size: int) -> list[list[Any]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    return [values[index : index + chunk_size] for index in range(0, len(values), chunk_size)]


def _collect_cadevolve_directory_files(root_path: Path, *, workers: int) -> list[tuple[str, Path]]:
    subtrees = [entry for entry in root_path.iterdir() if entry.is_dir()]
    if not subtrees:
        subtrees = [root_path]

    collected: list[tuple[str, Path]] = []
    walk_workers = min(workers, len(subtrees))
    with ThreadPoolExecutor(max_workers=walk_workers) as pool:
        for part in pool.map(lambda subtree: _walk_cadevolve_subtree_files(subtree, root_path), subtrees):
            collected.extend(part)
    collected.sort(key=lambda item: item[0])
    return collected


def _walk_cadevolve_subtree_files(subtree: Path, root_path: Path) -> list[tuple[str, Path]]:
    collected: list[tuple[str, Path]] = []
    stack = [subtree]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            continue
                    except OSError:
                        continue
                    rel = _normalize_archive_path(str(Path(entry.path).relative_to(root_path)))
                    collected.append((rel, Path(entry.path)))
        except OSError:
            continue
    return collected


def _cadevolve_directory_candidates(
    file_entries: list[tuple[str, Path]],
    *,
    prefixes: tuple[str, ...],
    path_needles: tuple[str, ...],
    max_member_bytes: int,
    stats: dict[str, Any],
) -> list[_CadevolveDirectoryCandidate]:
    candidates: list[_CadevolveDirectoryCandidate] = []
    for member_path, abs_path in file_entries:
        stats["file_count"] += 1
        if prefixes and not any(_archive_path_matches_prefix(member_path, prefix) for prefix in prefixes):
            stats["skipped_prefix_count"] += 1
            continue
        if path_needles and not any(needle in member_path.lower() for needle in path_needles):
            stats["skipped_path_contains_count"] += 1
            continue
        if abs_path.suffix != ".py":
            stats["skipped_non_python_count"] += 1
            continue
        stats["python_file_count"] += 1
        try:
            size = abs_path.stat().st_size
        except OSError:
            continue
        if size > max_member_bytes:
            stats["skipped_large_member_count"] += 1
            continue
        candidates.append(_CadevolveDirectoryCandidate(member_path=member_path, abs_path=abs_path))
    return candidates


def _process_cadevolve_directory_candidate(
    candidate: _CadevolveDirectoryCandidate,
    *,
    code_needles: tuple[str, ...],
) -> _CadevolveDirectoryProcessResult:
    source_text = candidate.abs_path.read_text(encoding="utf-8", errors="replace")
    return _cadevolve_source_row_from_text(candidate.member_path, source_text, code_needles=code_needles)


def _cadevolve_source_row_from_text(
    member_path: str,
    source_text: str,
    *,
    code_needles: tuple[str, ...],
) -> _CadevolveDirectoryProcessResult:
    source_code = normalize_source_text(source_text)
    if code_needles and not any(needle in source_code.lower() for needle in code_needles):
        return _CadevolveDirectoryProcessResult(skipped_code_contains=True)
    if not _looks_like_cadquery_source(source_code):
        return _CadevolveDirectoryProcessResult(skipped_non_cadquery=True)
    return _CadevolveDirectoryProcessResult(row=_cadevolve_source_row(member_path, source_code))


def _cadevolve_path_parts(path: str) -> tuple[str, str]:
    parts = [part for part in _normalize_archive_path(path).split("/") if part]
    source_subtree = parts[0] if parts else "unknown"
    source_collection = parts[1] if len(parts) > 1 else "unknown"
    return source_subtree, source_collection


def _archive_path_matches_prefix(path: str, prefix: str) -> bool:
    normalized_path = _normalize_archive_path(path)
    normalized_prefix = _normalize_archive_path(prefix).rstrip("/")
    return normalized_path == normalized_prefix or normalized_path.startswith(normalized_prefix + "/")


def _looks_like_cadquery_source(source_code: str) -> bool:
    lowered = source_code.lower()
    return "cadquery" in lowered or "cq." in source_code


def _calls_method(source_code: str, method: str) -> bool:
    return re.search(rf"\.{re.escape(method)}\s*\(", source_code, flags=re.IGNORECASE) is not None


def _source_feature_tag_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(
        tag
        for row in rows
        for tag in row.get("source_feature_tags", [])
        if isinstance(tag, str)
    )
    return {tag: counts.get(tag, 0) for tag in GEOMETRY_SOURCE_FEATURE_TAGS}


def _select_stratified_source_rows(
    rows: list[dict[str, Any]],
    *,
    limit: int | None,
    min_per_tag: int,
) -> list[dict[str, Any]]:
    if limit is None:
        return list(rows)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    selected_tag_counts: Counter[str] = Counter()

    def add_row(row: dict[str, Any]) -> bool:
        if len(selected) >= limit:
            return False
        source_id = str(row.get("source_id", ""))
        if source_id in selected_ids:
            return False
        selected.append(row)
        selected_ids.add(source_id)
        selected_tag_counts.update(
            tag
            for tag in row.get("source_feature_tags", [])
            if isinstance(tag, str)
        )
        return True

    for tag in GEOMETRY_SOURCE_FEATURE_TAGS:
        if len(selected) >= limit:
            break
        for row in rows:
            if len(selected) >= limit or selected_tag_counts[tag] >= min_per_tag:
                break
            if tag in row.get("source_feature_tags", []):
                add_row(row)

    for row in rows:
        if len(selected) >= limit:
            break
        add_row(row)
    return selected


def _select_cached_stratified_rows(
    rows_by_tag: dict[str, list[dict[str, Any]]],
    first_candidate_rows: list[dict[str, Any]],
    *,
    limit: int | None,
    selected_ids: set[str],
    selected_tag_counts: Counter[str],
) -> list[dict[str, Any]]:
    if limit is None:
        selected_tag_counts.update(
            tag
            for row in first_candidate_rows
            for tag in row.get("source_feature_tags", [])
            if isinstance(tag, str)
        )
        selected_ids.update(str(row.get("source_id", "")) for row in first_candidate_rows)
        return list(first_candidate_rows)

    selected: list[dict[str, Any]] = []

    def add_row(row: dict[str, Any]) -> bool:
        if len(selected) >= limit:
            return False
        source_id = str(row.get("source_id", ""))
        if source_id in selected_ids:
            return False
        selected.append(row)
        selected_ids.add(source_id)
        selected_tag_counts.update(
            tag
            for tag in row.get("source_feature_tags", [])
            if isinstance(tag, str)
        )
        return True

    for tag in GEOMETRY_SOURCE_FEATURE_TAGS:
        for row in rows_by_tag.get(tag, []):
            if len(selected) >= limit:
                break
            add_row(row)
    for row in first_candidate_rows:
        if len(selected) >= limit:
            break
        add_row(row)
    return selected


def _stratified_selection_ready(
    rows: list[dict[str, Any]],
    *,
    limit: int | None,
    min_per_tag: int,
) -> bool:
    if limit is None or len(rows) < limit:
        return False
    tag_counts = _source_feature_tag_counts(rows)
    if any(tag_counts[tag] < min_per_tag for tag in GEOMETRY_SOURCE_FEATURE_TAGS):
        return False
    return len(_select_stratified_source_rows(rows, limit=limit, min_per_tag=min_per_tag)) >= limit


def source_manifest(sources: list[SourceRecord]) -> dict[str, Any]:
    """Build an auditable manifest for normalized CadQuery program records."""

    source_ids = [source.source_id for source in sources]
    hashes = [source.source_hash for source in sources if source.source_hash]
    source_id_counts = Counter(source_ids)
    hash_to_sources: dict[str, list[str]] = defaultdict(list)
    source_id_to_hashes: dict[str, set[str]] = defaultdict(set)
    grouped_metadata_keys = [*PROTECTED_SOURCE_GROUP_KEYS, *REPORTED_SOURCE_PROVENANCE_KEYS, "path_family"]
    group_members: dict[str, dict[str, list[str]]] = {
        key: defaultdict(list) for key in grouped_metadata_keys
    }
    metadata_coverage = {key: 0 for key in grouped_metadata_keys}
    missing_path_source_ids: list[str] = []
    ungrouped_source_ids: list[str] = []

    for source in sources:
        metadata = source.metadata or {}
        if source.source_hash:
            hash_to_sources[source.source_hash].append(source.source_id)
            source_id_to_hashes[source.source_id].add(source.source_hash)
        if not source.source_path:
            missing_path_source_ids.append(source.source_id)
        labels = _source_group_labels(source)
        if not labels:
            ungrouped_source_ids.append(source.source_id)
        for key in metadata_coverage:
            value = metadata.get(key)
            if value in (None, "") and key == "path_family" and source.source_path:
                value = source_family_from_path(source.source_path)
            if value in (None, ""):
                continue
            metadata_coverage[key] += 1
            group_members[key][str(value)].append(source.source_id)

    duplicate_source_ids = {
        source_id: count
        for source_id, count in sorted(source_id_counts.items())
        if count > 1
    }
    duplicate_hashes = {
        digest: sorted(ids)
        for digest, ids in sorted(hash_to_sources.items())
        if len(set(ids)) > 1
    }
    source_id_hash_conflicts = {
        source_id: sorted(hashes)
        for source_id, hashes in sorted(source_id_to_hashes.items())
        if len(hashes) > 1
    }
    groups = {
        key: {
            "group_count": len(values),
            "groups": {
                value: sorted(ids)
                for value, ids in sorted(values.items())
            },
        }
        for key, values in group_members.items()
        if values
    }
    return {
        "source_count": len(sources),
        "unique_source_id_count": len(set(source_ids)),
        "unique_source_hash_count": len(set(hashes)),
        "duplicate_source_ids": duplicate_source_ids,
        "duplicate_hashes": duplicate_hashes,
        "source_id_hash_conflicts": source_id_hash_conflicts,
        "missing_path_source_ids": sorted(missing_path_source_ids),
        "ungrouped_source_ids": sorted(ungrouped_source_ids),
        "metadata_coverage": metadata_coverage,
        "groups": groups,
        "protected_group_keys": list(PROTECTED_SOURCE_GROUP_KEYS),
        "reported_provenance_keys": list(REPORTED_SOURCE_PROVENANCE_KEYS),
    }


def source_audit(sources: list[SourceRecord]) -> dict[str, Any]:
    """Audit CadQuery program manifests for identity and split-hygiene risks."""

    manifest = source_manifest(sources)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for source_id, count in manifest["duplicate_source_ids"].items():
        errors.append({"error": "duplicate_source_id", "source_id": source_id, "count": count})
    for source_id, hashes in manifest["source_id_hash_conflicts"].items():
        errors.append({"error": "source_id_hash_conflict", "source_id": source_id, "hashes": hashes})
    for digest, source_ids in manifest["duplicate_hashes"].items():
        warnings.append({"warning": "duplicate_normalized_source_hash", "source_hash": digest, "source_ids": source_ids})
    if manifest["missing_path_source_ids"]:
        warnings.append(
            {
                "warning": "missing_source_path",
                "count": len(manifest["missing_path_source_ids"]),
                "source_ids": manifest["missing_path_source_ids"][:10],
            }
        )
    if manifest["ungrouped_source_ids"]:
        warnings.append(
            {
                "warning": "missing_protected_group_metadata",
                "count": len(manifest["ungrouped_source_ids"]),
                "source_ids": manifest["ungrouped_source_ids"][:10],
            }
        )
    return {
        "valid": not errors,
        "source_count": manifest["source_count"],
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "manifest": manifest,
    }


def _source_group_labels(source: SourceRecord) -> set[str]:
    metadata = source.metadata or {}
    labels = {
        f"{key}:{metadata[key]}"
        for key in PROTECTED_SOURCE_GROUP_KEYS
        if metadata.get(key) not in (None, "")
    }
    if source.source_path:
        labels.add(f"path_family:{metadata.get('path_family') or source_family_from_path(source.source_path)}")
    return labels
