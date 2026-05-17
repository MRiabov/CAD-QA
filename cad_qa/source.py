"""Source records and JSONL loading."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cad_qa.io import read_jsonl


PROTECTED_SOURCE_GROUP_KEYS = (
    "split_group",
    "counterfactual_group",
    "source_family",
    "family_id",
    "template_id",
    "generator_id",
    "generator",
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


def source_family_from_path(path: str) -> str:
    """Derive a stable CADEvolve-style family label from an archive member path."""

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


def source_manifest(sources: list[SourceRecord]) -> dict[str, Any]:
    """Build an auditable manifest for normalized source records."""

    source_ids = [source.source_id for source in sources]
    hashes = [source.source_hash for source in sources if source.source_hash]
    source_id_counts = Counter(source_ids)
    hash_to_sources: dict[str, list[str]] = defaultdict(list)
    source_id_to_hashes: dict[str, set[str]] = defaultdict(set)
    group_members: dict[str, dict[str, list[str]]] = {
        key: defaultdict(list) for key in [*PROTECTED_SOURCE_GROUP_KEYS, "path_family"]
    }
    metadata_coverage = {key: 0 for key in [*PROTECTED_SOURCE_GROUP_KEYS, "path_family"]}
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
    }


def source_audit(sources: list[SourceRecord]) -> dict[str, Any]:
    """Audit source manifests for identity and split-hygiene risks."""

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
