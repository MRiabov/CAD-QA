"""Source records and JSONL loading."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cad_qa.io import read_jsonl


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
    return SourceRecord(
        source_id=str(source_id),
        source_code=normalized,
        source_path=str(source_path) if source_path else None,
        source_hash=source_hash,
        metadata=metadata,
    )


def load_sources_jsonl(path: Path, *, limit: int | None = None) -> list[SourceRecord]:
    records = [source_record_from_mapping(row) for row in read_jsonl(path)]
    return records[:limit] if limit is not None else records


def source_to_dict(source: SourceRecord) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "source_code": source.source_code,
        "source_path": source.source_path,
        "source_hash": source.source_hash,
        "metadata": source.metadata or {},
    }
