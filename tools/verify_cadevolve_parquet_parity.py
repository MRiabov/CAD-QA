"""Verify parity between a CADEvolve parquet cache and an extracted tree.

The slow naive approach rescans every Python file with normalize_source_text.
This tool instead:
  1. reads only parquet paths (one column),
  2. walks the extracted tree in parallel per top-level subtree with os.scandir,
  3. diffs path sets without reading file bodies,
  4. reads content only for the small filesystem-only delta, and
  5. stat-checks parquet paths in chunked parallel batches.

Example:
    uv run python tools/verify_cadevolve_parquet_parity.py \
      --root data/cadevolve_extracted \
      --parquet data/cadevolve_sources.parquet
"""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from cad_qa.source import _looks_like_cadquery_source, _normalize_archive_path, normalize_source_text

DEFAULT_MAX_MEMBER_BYTES = 1_000_000
DEFAULT_WORKERS = min(64, max(8, (os.cpu_count() or 4) * 4))
DEFAULT_STAT_CHUNK_SIZE = 10_000


@dataclass
class FilesystemScan:
    file_count: int = 0
    python_under_limit: list[str] = field(default_factory=list)
    skipped_non_python: int = 0
    skipped_large: int = 0


def main() -> int:
    args = _parse_args()
    summary = verify_cadevolve_parquet_parity(
        args.root,
        args.parquet,
        max_member_bytes=args.max_member_bytes,
        workers=args.workers,
        stat_chunk_size=args.stat_chunk_size,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["full_parity"] else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Extracted CADEvolve directory")
    parser.add_argument("--parquet", type=Path, required=True, help="CADEvolve source parquet cache")
    parser.add_argument("--max-member-bytes", type=int, default=DEFAULT_MAX_MEMBER_BYTES)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--stat-chunk-size", type=int, default=DEFAULT_STAT_CHUNK_SIZE)
    return parser.parse_args()


def verify_cadevolve_parquet_parity(
    root: Path,
    parquet_path: Path,
    *,
    max_member_bytes: int = DEFAULT_MAX_MEMBER_BYTES,
    workers: int = DEFAULT_WORKERS,
    stat_chunk_size: int = DEFAULT_STAT_CHUNK_SIZE,
) -> dict[str, Any]:
    timings: dict[str, float] = {}
    started = time.perf_counter()

    parquet_set, parquet_rows = _load_parquet_paths(parquet_path)
    timings["parquet_paths_seconds"] = round(time.perf_counter() - started, 3)

    scan_started = time.perf_counter()
    filesystem_scan = _scan_extracted_tree_parallel(root, max_member_bytes=max_member_bytes, workers=workers)
    timings["filesystem_scan_seconds"] = round(time.perf_counter() - scan_started, 3)

    diff_started = time.perf_counter()
    py_set = set(filesystem_scan.python_under_limit)
    only_parquet = sorted(parquet_set - py_set)
    only_fs = sorted(py_set - parquet_set)
    overlap = parquet_set & py_set
    timings["set_diff_seconds"] = round(time.perf_counter() - diff_started, 3)

    classify_started = time.perf_counter()
    non_cadquery, cadquery_missing_from_parquet = _classify_filesystem_only(
        root,
        only_fs,
        workers=workers,
    )
    timings["classify_delta_seconds"] = round(time.perf_counter() - classify_started, 3)

    stat_started = time.perf_counter()
    missing_on_disk = _missing_parquet_paths_parallel(
        root,
        parquet_set,
        workers=workers,
        chunk_size=stat_chunk_size,
    )
    timings["parquet_stat_seconds"] = round(time.perf_counter() - stat_started, 3)

    expected_included = len(filesystem_scan.python_under_limit) - len(non_cadquery)
    full_parity = (
        not only_parquet
        and not cadquery_missing_from_parquet
        and len(non_cadquery) == len(only_fs)
        and not missing_on_disk
        and parquet_rows == len(parquet_set)
        and parquet_rows == expected_included
    )

    timings["total_seconds"] = round(time.perf_counter() - started, 3)
    return {
        "root": str(root),
        "parquet": str(parquet_path),
        "parquet_rows": parquet_rows,
        "parquet_unique_paths": len(parquet_set),
        "filesystem_file_count": filesystem_scan.file_count,
        "filesystem_python_under_limit": len(filesystem_scan.python_under_limit),
        "filesystem_skipped_non_python": filesystem_scan.skipped_non_python,
        "filesystem_skipped_large": filesystem_scan.skipped_large,
        "filesystem_non_cadquery_excluded": len(non_cadquery),
        "expected_included_from_filesystem": expected_included,
        "overlap_paths": len(overlap),
        "only_parquet_paths": len(only_parquet),
        "only_filesystem_paths": len(only_fs),
        "parquet_paths_missing_on_disk": len(missing_on_disk),
        "cadquery_on_disk_missing_from_parquet": len(cadquery_missing_from_parquet),
        "row_count_match": parquet_rows == expected_included,
        "full_parity": full_parity,
        "workers": workers,
        "stat_chunk_size": stat_chunk_size,
        "timings_seconds": timings,
        "sample_non_cadquery": non_cadquery[:5],
        "sample_cadquery_missing_from_parquet": cadquery_missing_from_parquet[:5],
        "sample_missing_on_disk": missing_on_disk[:5],
    }


def _load_parquet_paths(parquet_path: Path) -> tuple[set[str], int]:
    table = pq.read_table(parquet_path, columns=["normalized_archive_member_path"], memory_map=True)
    column = table.column(0)
    parquet_rows = len(column)
    parquet_set = {
        _normalize_archive_path(str(value))
        for value in column.to_pylist()
        if value is not None
    }
    return parquet_set, parquet_rows


def _scan_extracted_tree_parallel(
    root: Path,
    *,
    max_member_bytes: int,
    workers: int,
) -> FilesystemScan:
    subtrees = [entry for entry in root.iterdir() if entry.is_dir()]
    if not subtrees:
        subtrees = [root]

    merged = FilesystemScan()
    walk_workers = min(workers, len(subtrees))
    with ThreadPoolExecutor(max_workers=walk_workers) as pool:
        futures = [
            pool.submit(_scan_subtree, subtree, root, max_member_bytes=max_member_bytes)
            for subtree in subtrees
        ]
        for future in as_completed(futures):
            part = future.result()
            merged.file_count += part.file_count
            merged.skipped_non_python += part.skipped_non_python
            merged.skipped_large += part.skipped_large
            merged.python_under_limit.extend(part.python_under_limit)
    return merged


def _scan_subtree(subtree: Path, root: Path, *, max_member_bytes: int) -> FilesystemScan:
    result = FilesystemScan()
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

                    result.file_count += 1
                    rel = _normalize_archive_path(str(Path(entry.path).relative_to(root)))
                    if Path(entry.path).suffix != ".py":
                        result.skipped_non_python += 1
                        continue
                    try:
                        size = entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
                    if size > max_member_bytes:
                        result.skipped_large += 1
                        continue
                    result.python_under_limit.append(rel)
        except OSError:
            continue
    return result


def _classify_filesystem_only(
    root: Path,
    only_fs: list[str],
    *,
    workers: int,
) -> tuple[list[str], list[str]]:
    if not only_fs:
        return [], []

    non_cadquery: list[str] = []
    cadquery_missing_from_parquet: list[str] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(only_fs))) as pool:
        futures = {pool.submit(_classify_single_path, root, rel): rel for rel in only_fs}
        for future in as_completed(futures):
            rel, kind = future.result()
            if kind == "non_cadquery":
                non_cadquery.append(rel)
            else:
                cadquery_missing_from_parquet.append(rel)
    non_cadquery.sort()
    cadquery_missing_from_parquet.sort()
    return non_cadquery, cadquery_missing_from_parquet


def _classify_single_path(root: Path, rel: str) -> tuple[str, str]:
    path = root / rel
    source_code = normalize_source_text(path.read_text(encoding="utf-8", errors="replace"))
    if _looks_like_cadquery_source(source_code):
        return rel, "cadquery_missing_from_parquet"
    return rel, "non_cadquery"


def _missing_parquet_paths_parallel(
    root: Path,
    parquet_paths: set[str],
    *,
    workers: int,
    chunk_size: int,
) -> list[str]:
    if not parquet_paths:
        return []

    chunks = _chunked(sorted(parquet_paths), chunk_size)
    missing: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_missing_paths_chunk, root, chunk) for chunk in chunks]
        for future in as_completed(futures):
            missing.extend(future.result())
    missing.sort()
    return missing


def _missing_paths_chunk(root: Path, rel_paths: list[str]) -> list[str]:
    missing: list[str] = []
    for rel in rel_paths:
        if not (root / rel).is_file():
            missing.append(rel)
    return missing


def _chunked(values: list[str], chunk_size: int) -> list[list[str]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    return [values[index : index + chunk_size] for index in range(0, len(values), chunk_size)]


if __name__ == "__main__":
    raise SystemExit(main())
