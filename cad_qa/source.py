"""CADEvolve and synthetic source record loading."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import re
import tarfile
from typing import Iterable

from cad_qa.config import DatasetConfig
from cad_qa.hashing import sha256_json, sha256_text, short_hash
from cad_qa.schema import SourceRecord

EXECUTABLE_PREFIXES = ("CADEvolve-P/", "CADEvolve-C/")
DEFAULT_ADJACENT_SOURCE_DIRS = (
    Path("../CADEvolve"),
    Path("../CADEvolve/data/cadevolve_sources"),
    Path("../big-build123d-dataset/cadevolve-cq-translation/translated"),
)


def normalize_source_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def normalize_archive_path(path: str | Path) -> str:
    normalized = str(path).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def load_source_dir(
    source_dir: Path,
    *,
    config: DatasetConfig,
    limit: int | None = None,
    offset: int = 0,
) -> list[SourceRecord]:
    files = discover_cadevolve_sources(source_dir)
    selected = files[max(0, offset) : None if limit is None else max(0, offset) + limit]
    records: list[SourceRecord] = []
    for relative_path in selected:
        code = (source_dir / relative_path).read_text(
            encoding="utf-8", errors="replace"
        )
        records.append(
            source_record_from_code(
                relative_path, code, source="cadevolve", config=config
            )
        )
    return records


def load_source_archive(
    archive_path: Path,
    *,
    config: DatasetConfig,
    limit: int | None = None,
    offset: int = 0,
) -> list[SourceRecord]:
    """Load a bounded executable-source subset from a CADEvolve tar archive."""
    if not archive_path.exists():
        raise FileNotFoundError(f"archive not found: {archive_path}")
    selected: list[tuple[str, bytes]] = []
    offset = max(0, offset)
    with tarfile.open(archive_path, "r:*") as archive:
        members = [
            member
            for member in archive.getmembers()
            if member.isfile()
            and _is_executable_cadevolve_path(normalize_archive_path(member.name))
        ]
        members.sort(key=lambda member: normalize_archive_path(member.name))
        end = None if limit is None else offset + limit
        for member in members[offset:end]:
            handle = archive.extractfile(member)
            if handle is None:
                continue
            selected.append((normalize_archive_path(member.name), handle.read()))
    return [
        source_record_from_code(
            path,
            data.decode("utf-8", errors="replace"),
            source="cadevolve",
            config=config,
        )
        for path, data in selected
    ]


def find_adjacent_source_dir(start: Path | None = None) -> Path | None:
    root = (start or Path.cwd()).resolve()
    for candidate in DEFAULT_ADJACENT_SOURCE_DIRS:
        resolved = (root / candidate).resolve()
        if resolved.exists() and discover_cadevolve_sources(resolved):
            return resolved
    return None


def discover_cadevolve_sources(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        raise FileNotFoundError(f"source directory not found: {source_dir}")
    candidates: list[Path] = []
    for prefix in EXECUTABLE_PREFIXES:
        root = source_dir / prefix
        if root.exists():
            candidates.extend(
                path.relative_to(source_dir) for path in root.rglob("*.py")
            )
    return sorted(candidates, key=lambda path: normalize_archive_path(path))


def _is_executable_cadevolve_path(path: str) -> bool:
    normalized = normalize_archive_path(path)
    return normalized.endswith(".py") and any(
        normalized.startswith(prefix) for prefix in EXECUTABLE_PREFIXES
    )


def source_record_from_code(
    path: str | Path,
    code: str,
    *,
    source: str,
    config: DatasetConfig,
    license_value: str | None = None,
) -> SourceRecord:
    normalized_path = normalize_archive_path(path)
    normalized_code = normalize_source_text(code)
    raw_hash = sha256_text(code)
    normalized_hash = sha256_text(normalized_code)
    source_id = "src_" + short_hash(
        {"path": normalized_path, "hash": normalized_hash}, 16
    )
    return SourceRecord(
        source_id=source_id,
        source=source,
        archive_member_path=normalized_path if source == "cadevolve" else None,
        normalized_archive_member_path=normalized_path
        if source == "cadevolve"
        else None,
        source_subtree=_source_subtree(normalized_path)
        if source == "cadevolve"
        else "synthetic",
        generator_id=_generator_id(normalized_path)
        if source == "cadevolve"
        else "synthetic_golden",
        license=license_value or config.license,
        raw_code=code,
        normalized_code=normalized_code,
        hashes={
            "raw_source_code_hash": raw_hash,
            "normalized_source_code_hash": normalized_hash,
            "config_hash": config.config_hash,
        },
    )


def source_manifest_hash(records: Iterable[SourceRecord]) -> str:
    return sha256_json(
        [
            {
                "source_id": record.source_id,
                "path": record.normalized_archive_member_path,
                "hash": record.hashes["normalized_source_code_hash"],
            }
            for record in records
        ]
    )


def _source_subtree(path: str) -> str | None:
    return path.split("/", 1)[0] if path else None


def _generator_id(path: str) -> str | None:
    parts = [part for part in path.split("/")[:2] if part]
    if not parts:
        return None
    slug = re.sub(r"[^A-Za-z0-9_]+", "_", "_".join(parts)).strip("_").lower()
    return f"cadevolve_{slug}"


def source_record_dict(record: SourceRecord) -> dict[str, object]:
    return asdict(record)
