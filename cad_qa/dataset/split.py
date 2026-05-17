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
