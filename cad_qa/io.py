"""Small artifact I/O helpers for graph-first CAD-QA artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq


RECORD_JSON_COLUMN = "record_json"


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(to_jsonable(row), sort_keys=True) + "\n")
            count += 1
    return count


def read_parquet_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    table = pq.read_table(path)
    if RECORD_JSON_COLUMN not in table.column_names:
        return [dict(row) for row in table.to_pylist()]
    return [
        json.loads(value)
        for value in table.column(RECORD_JSON_COLUMN).to_pylist()
        if isinstance(value, str) and value.strip()
    ]


def iter_parquet_records(path: Path, *, batch_size: int = 1000):
    if not path.exists():
        raise FileNotFoundError(path)
    parquet_file = pq.ParquetFile(path)
    if RECORD_JSON_COLUMN not in parquet_file.schema.names:
        for batch in parquet_file.iter_batches(batch_size=batch_size):
            for row in batch.to_pylist():
                yield dict(row)
        return
    for batch in parquet_file.iter_batches(batch_size=batch_size, columns=[RECORD_JSON_COLUMN]):
        column = batch.column(0)
        for value in column.to_pylist():
            if isinstance(value, str) and value.strip():
                yield json.loads(value)


def write_parquet_records(path: Path, rows: Iterable[Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [json.dumps(to_jsonable(row), sort_keys=True) for row in rows]
    table = pa.table({RECORD_JSON_COLUMN: pa.array(payload, type=pa.string())})
    pq.write_table(table, path, compression="zstd")
    return len(payload)


def write_parquet_records_batched(path: Path, rows: Iterable[Any], *, batch_size: int = 1000) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    batch: list[str] = []
    count = 0

    def flush() -> None:
        nonlocal batch, count, writer
        if not batch:
            return
        table = pa.table({RECORD_JSON_COLUMN: pa.array(batch, type=pa.string())})
        if writer is None:
            writer = pq.ParquetWriter(path, table.schema, compression="zstd")
        writer.write_table(table)
        count += len(batch)
        batch = []

    try:
        for row in rows:
            batch.append(json.dumps(to_jsonable(row), sort_keys=True))
            if len(batch) >= batch_size:
                flush()
        flush()
    finally:
        if writer is not None:
            writer.close()
    return count


def read_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".parquet":
        return read_parquet_records(path)
    if path.suffix == ".jsonl":
        return read_jsonl(path)
    raise ValueError(f"unsupported record artifact format: {path}")


def iter_records(path: Path, *, batch_size: int = 1000):
    if path.suffix == ".parquet":
        yield from iter_parquet_records(path, batch_size=batch_size)
        return
    if path.suffix == ".jsonl":
        yield from read_jsonl(path)
        return
    raise ValueError(f"unsupported record artifact format: {path}")


def write_records(path: Path, rows: Iterable[Any]) -> int:
    if path.suffix == ".parquet":
        return write_parquet_records(path, rows)
    if path.suffix == ".jsonl":
        return write_jsonl(path, rows)
    raise ValueError(f"unsupported record artifact format: {path}")


def record_artifact_path(directory: Path, stem: str, *, prefer: str = "parquet") -> Path:
    suffix = ".parquet" if prefer == "parquet" else ".jsonl"
    return directory / f"{stem}{suffix}"


def existing_record_artifact_path(directory: Path, stem: str) -> Path:
    parquet_path = directory / f"{stem}.parquet"
    if parquet_path.exists():
        return parquet_path
    jsonl_path = directory / f"{stem}.jsonl"
    if jsonl_path.exists():
        return jsonl_path
    return parquet_path


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_jsonable(data), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
