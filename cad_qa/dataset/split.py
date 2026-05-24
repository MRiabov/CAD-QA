"""Deterministic group-safe release splits."""

from __future__ import annotations

from typing import Any

from cad_qa.source import source_family_from_path


SPLITS = ("train", "validation", "test")
PROTECTED_GROUP_KEYS = (
    "split_group",
    "counterfactual_group",
    "source_family",
    "family_id",
    "template_id",
    "generator_id",
    "generator",
)


def split_for_source(source_id: str) -> str:
    return "train"


def assign_splits(rows: list[Any]) -> dict[str, list[Any]]:
    source_splits = _source_split_map(rows)
    grouped = {split: [] for split in SPLITS}
    for row in rows:
        source_id = row.source_id if hasattr(row, "source_id") else row["source_id"]
        grouped[source_splits[source_id]].append(row)
    return grouped


def rows_with_assigned_splits(rows: list[Any], manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    manifest = manifest or split_manifest(rows)
    source_splits = manifest["sources"]
    assigned = []
    for row in rows:
        item = row.__dict__.copy() if hasattr(row, "__dict__") else dict(row)
        item["split"] = source_splits[str(_row_get(row, "source_id"))]
        assigned.append(item)
    return assigned


def split_manifest(rows: list[Any]) -> dict[str, Any]:
    sources = _source_split_map(rows)
    source_groups = _source_groups(rows)
    counts = {split: 0 for split in SPLITS}
    for split in sources.values():
        counts[split] += 1
    group_counts = {split: 0 for split in SPLITS}
    for group in source_groups.values():
        group_counts[group["split"]] += 1
    return {
        "policy": "deterministic 70/15/15 approximation over protected source groups; all rows sharing source family, generator, counterfactual group, split_group, or path-derived family stay together",
        "source_count": len(sources),
        "group_count": len(source_groups),
        "source_counts_by_split": counts,
        "group_counts_by_split": group_counts,
        "sources": sources,
        "source_groups": source_groups,
        "protected_group_keys": list(PROTECTED_GROUP_KEYS),
    }


def split_audit(rows: list[Any], manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check that concrete row splits match the group-safe split manifest."""

    manifest = manifest or split_manifest(rows)
    row_sources = {str(_row_get(row, "source_id")) for row in rows}
    manifest_sources = {str(source_id): split for source_id, split in manifest.get("sources", {}).items()}
    missing_manifest_sources = sorted(row_sources - set(manifest_sources))
    orphan_manifest_sources = sorted(set(manifest_sources) - row_sources)
    row_split_mismatches = []
    for row in rows:
        source_id = str(_row_get(row, "source_id"))
        expected_split = manifest_sources.get(source_id)
        actual_split = _row_get(row, "split")
        if actual_split not in (None, "") and expected_split is not None and actual_split != expected_split:
            row_split_mismatches.append(
                {
                    "row_id": _row_get(row, "row_id"),
                    "source_id": source_id,
                    "expected_split": expected_split,
                    "actual_split": actual_split,
                }
            )

    label_splits: dict[str, set[str]] = {}
    for row in rows:
        source_id = str(_row_get(row, "source_id"))
        split = manifest_sources.get(source_id)
        if split is None:
            continue
        for label in _protected_labels(row):
            label_splits.setdefault(label, set()).add(split)
    protected_label_split_leaks = {
        label: sorted(splits)
        for label, splits in sorted(label_splits.items())
        if len(splits) > 1
    }

    errors = []
    if missing_manifest_sources:
        errors.append({"error": "missing_manifest_sources", "source_ids": missing_manifest_sources})
    if orphan_manifest_sources:
        errors.append({"error": "orphan_manifest_sources", "source_ids": orphan_manifest_sources})
    if row_split_mismatches:
        errors.append({"error": "row_split_mismatch", "rows": row_split_mismatches})
    if protected_label_split_leaks:
        errors.append({"error": "protected_label_split_leak", "labels": protected_label_split_leaks})

    warnings = []
    group_count = int(manifest.get("group_count") or 0)
    group_counts = manifest.get("group_counts_by_split", {})
    if group_count >= 3:
        empty_splits = [split for split in SPLITS if int(group_counts.get(split, 0) or 0) == 0]
        if empty_splits:
            warnings.append({"warning": "empty_split_bucket", "splits": empty_splits})

    return {
        "valid": not errors,
        "row_count": len(rows),
        "source_count": len(row_sources),
        "group_count": group_count,
        "protected_group_keys": list(PROTECTED_GROUP_KEYS),
        "source_counts_by_split": manifest.get("source_counts_by_split", {}),
        "group_counts_by_split": group_counts,
        "missing_manifest_sources": missing_manifest_sources,
        "orphan_manifest_sources": orphan_manifest_sources,
        "row_split_mismatches": row_split_mismatches,
        "protected_label_split_leaks": protected_label_split_leaks,
        "errors": errors,
        "warnings": warnings,
    }


def _source_split_map(rows: list[Any]) -> dict[str, str]:
    source_groups = _source_groups(rows)
    return {
        source_id: group["split"]
        for group in source_groups.values()
        for source_id in group["source_ids"]
    }


def _source_groups(rows: list[Any]) -> dict[str, dict[str, Any]]:
    source_labels: dict[str, set[str]] = {}
    label_to_sources: dict[str, list[str]] = {}
    for row in rows:
        source_id = str(_row_get(row, "source_id"))
        labels = _protected_labels(row)
        source_labels.setdefault(source_id, set()).update(labels)
        for label in labels:
            label_to_sources.setdefault(label, []).append(source_id)

    parent = {source_id: source_id for source_id in source_labels}

    def find(source_id: str) -> str:
        while parent[source_id] != source_id:
            parent[source_id] = parent[parent[source_id]]
            source_id = parent[source_id]
        return source_id

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    for sources in label_to_sources.values():
        head = sources[0]
        for source_id in sources[1:]:
            union(head, source_id)

    components: dict[str, list[str]] = {}
    for source_id in sorted(source_labels):
        components.setdefault(find(source_id), []).append(source_id)

    group_ids = {
        root: _group_id(source_ids, source_labels)
        for root, source_ids in components.items()
    }
    group_splits = _group_split_map(sorted(group_ids.values()))
    groups: dict[str, dict[str, Any]] = {}
    for root, source_ids in sorted(components.items(), key=lambda item: group_ids[item[0]]):
        group_id = group_ids[root]
        labels = sorted({label for source_id in source_ids for label in source_labels[source_id]})
        groups[group_id] = {
            "split": group_splits[group_id],
            "source_ids": source_ids,
            "protected_labels": labels,
        }
    return groups


def _group_split_map(group_ids: list[str]) -> dict[str, str]:
    if len(group_ids) < 3:
        return {group_id: "train" for group_id in group_ids}
    train_count = max(1, int(round(len(group_ids) * 0.7)))
    validation_count = max(1, int(round(len(group_ids) * 0.15)))
    if train_count + validation_count >= len(group_ids):
        train_count = max(1, len(group_ids) - 2)
        validation_count = 1
    mapping: dict[str, str] = {}
    for index, group_id in enumerate(group_ids):
        if index < train_count:
            mapping[group_id] = "train"
        elif index < train_count + validation_count:
            mapping[group_id] = "validation"
        else:
            mapping[group_id] = "test"
    return mapping


def _protected_labels(row: Any) -> set[str]:
    labels: set[str] = set()
    metadata = _row_get(row, "source_metadata") or {}
    for key in PROTECTED_GROUP_KEYS:
        value = _row_get(row, key)
        if value is None and isinstance(metadata, dict):
            value = metadata.get(key)
        if value not in (None, ""):
            labels.add(f"{key}:{value}")
    source_path = _row_get(row, "source_path")
    if source_path:
        labels.add(f"path_family:{source_family_from_path(str(source_path))}")
    if not labels:
        labels.add(f"source:{_row_get(row, 'source_id')}")
    return labels


def _group_id(source_ids: list[str], source_labels: dict[str, set[str]]) -> str:
    public_labels = sorted(
        label
        for source_id in source_ids
        for label in source_labels[source_id]
        if not label.startswith("source:")
    )
    if public_labels:
        return public_labels[0]
    return f"source:{source_ids[0]}"


def _row_get(row: Any, key: str) -> Any:
    if hasattr(row, key):
        return getattr(row, key)
    return row.get(key) if isinstance(row, dict) else None
