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


def write_parquet_records(path: Path, rows: Iterable[Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [json.dumps(to_jsonable(row), sort_keys=True) for row in rows]
    table = pa.table({RECORD_JSON_COLUMN: pa.array(payload, type=pa.string())})
    pq.write_table(table, path, compression="zstd")
    return len(payload)


def read_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".parquet":
        return read_parquet_records(path)
    if path.suffix == ".jsonl":
        return read_jsonl(path)
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
