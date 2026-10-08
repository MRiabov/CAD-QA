"""Small artifact I/O helpers for graph-first CAD-QA artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

import pyarrow as pa
import pyarrow.parquet as pq


RECORD_JSON_COLUMN = "record_json"
EMPTY_RECORD_COLUMN = "_cadqa_empty"
COLUMNAR_RECORD_FORMAT = "columnar_v1"
RECORD_FORMAT_METADATA_KEY = b"cadqa.record_format"
JSON_COLUMNS_METADATA_KEY = b"cadqa.json_columns"


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
        json_columns = _json_encoded_columns(table.schema.metadata)
        return [_decode_columnar_row(dict(row), json_columns) for row in table.to_pylist()]
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
        json_columns = _json_encoded_columns(parquet_file.schema_arrow.metadata)
        for batch in parquet_file.iter_batches(batch_size=batch_size):
            for row in batch.to_pylist():
                yield _decode_columnar_row(dict(row), json_columns)
        return
    for batch in parquet_file.iter_batches(batch_size=batch_size, columns=[RECORD_JSON_COLUMN]):
        column = batch.column(0)
        for value in column.to_pylist():
            if isinstance(value, str) and value.strip():
                yield json.loads(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(to_jsonable(value), sort_keys=True)


def _json_encoded_columns(metadata: dict[bytes, bytes] | None) -> set[str]:
    if not metadata or JSON_COLUMNS_METADATA_KEY not in metadata:
        return set()
    payload = metadata[JSON_COLUMNS_METADATA_KEY].decode("utf-8")
    return set(json.loads(payload))


def _decode_columnar_row(row: dict[str, Any], json_columns: set[str]) -> dict[str, Any]:
    decoded = dict(row)
    for column in json_columns:
        value = decoded.get(column)
        if isinstance(value, str) and value.strip():
            decoded[column] = json.loads(value)
    return decoded


def _record_rows(rows: Iterable[Any]) -> list[dict[str, Any]]:
    return [to_jsonable(row) for row in rows]


def _ordered_record_keys(rows: list[dict[str, Any]]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                keys.append(key)
                seen.add(key)
    return keys


def _column_array(values: list[Any]) -> tuple[pa.Array, bool]:
    try:
        column = pa.array(values)
        if _has_empty_struct_type(column.type):
            raise pa.ArrowTypeError("empty struct columns are not parquet-writable")
        return column, False
    except (pa.ArrowInvalid, pa.ArrowTypeError, TypeError, ValueError):
        encoded = [_json_dumps(value) if value is not None else None for value in values]
        return pa.array(encoded, type=pa.string()), True


def _has_empty_struct_type(data_type: pa.DataType) -> bool:
    if pa.types.is_struct(data_type):
        return data_type.num_fields == 0 or any(_has_empty_struct_type(data_type.field(index).type) for index in range(data_type.num_fields))
    if pa.types.is_list(data_type) or pa.types.is_large_list(data_type):
        return _has_empty_struct_type(data_type.value_type)
    return False


def _columnar_record_table(rows: list[dict[str, Any]]) -> pa.Table:
    if not rows:
        table = pa.table({EMPTY_RECORD_COLUMN: pa.array([], type=pa.bool_())})
        metadata = dict(table.schema.metadata or {})
        metadata[RECORD_FORMAT_METADATA_KEY] = COLUMNAR_RECORD_FORMAT.encode("utf-8")
        metadata[JSON_COLUMNS_METADATA_KEY] = b"[]"
        return table.replace_schema_metadata(metadata)
    keys = _ordered_record_keys(rows)
    columns: dict[str, pa.Array] = {}
    json_columns: list[str] = []
    for key in keys:
        values = [row.get(key) for row in rows]
        column, json_encoded = _column_array(values)
        columns[key] = column
        if json_encoded:
            json_columns.append(key)
    table = pa.table(columns)
    metadata = dict(table.schema.metadata or {})
    metadata[RECORD_FORMAT_METADATA_KEY] = COLUMNAR_RECORD_FORMAT.encode("utf-8")
    metadata[JSON_COLUMNS_METADATA_KEY] = json.dumps(json_columns, sort_keys=True).encode("utf-8")
    return table.replace_schema_metadata(metadata)


def write_parquet_records(path: Path, rows: Iterable[Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _record_rows(rows)
    table = _columnar_record_table(payload)
    pq.write_table(table, path, compression="zstd")
    return len(payload)


def write_parquet_records_batched(path: Path, rows: Iterable[Any], *, batch_size: int = 1000) -> int:
    return write_parquet_records(path, rows)


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
