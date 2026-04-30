"""Deterministic group-safe smoke splits."""

from __future__ import annotations

from typing import Any


SPLITS = ("train", "validation", "test")


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
    counts = {split: 0 for split in SPLITS}
    for split in sources.values():
        counts[split] += 1
    return {
        "policy": "sorted source_id deterministic 70/15/15 approximation; all rows from a source stay together",
        "source_count": len(sources),
        "source_counts_by_split": counts,
        "sources": sources,
    }


def _source_split_map(rows: list[Any]) -> dict[str, str]:
    source_ids = sorted(
        {
            row.source_id if hasattr(row, "source_id") else row["source_id"]
            for row in rows
        }
    )
    if len(source_ids) < 3:
        return {source_id: "train" for source_id in source_ids}
    train_count = max(1, int(round(len(source_ids) * 0.7)))
    validation_count = max(1, int(round(len(source_ids) * 0.15)))
    if train_count + validation_count >= len(source_ids):
        train_count = max(1, len(source_ids) - 2)
        validation_count = 1
    mapping: dict[str, str] = {}
    for index, source_id in enumerate(source_ids):
        if index < train_count:
            mapping[source_id] = "train"
        elif index < train_count + validation_count:
            mapping[source_id] = "validation"
        else:
            mapping[source_id] = "test"
    return mapping
