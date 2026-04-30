"""Leakage and split audit helpers."""

from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any


def leakage_audit(rows: list[dict[str, Any]], split_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    source_to_splits: dict[str, set[str]] = defaultdict(set)
    prompt_hash_to_rows: dict[str, list[str]] = defaultdict(list)
    query_id_to_splits: dict[str, set[str]] = defaultdict(set)
    manifest_sources = (split_manifest or {}).get("sources", {})
    for row in rows:
        split = manifest_sources.get(row["source_id"], row.get("split", "unknown"))
        source_to_splits[row["source_id"]].add(split)
        prompt_hash = hashlib.sha256(str(row["prompt"]).encode("utf-8")).hexdigest()
        prompt_hash_to_rows[prompt_hash].append(row["row_id"])
        query_id = row.get("query_program", {}).get("query_id")
        if query_id:
            query_id_to_splits[query_id].add(split)
    source_leaks = {
        source_id: sorted(splits)
        for source_id, splits in source_to_splits.items()
        if len(splits) > 1
    }
    duplicate_prompt_rows = {
        digest: row_ids
        for digest, row_ids in prompt_hash_to_rows.items()
        if len(row_ids) > 1
    }
    query_leaks = {
        query_id: sorted(splits)
        for query_id, splits in query_id_to_splits.items()
        if len(splits) > 1
    }
    return {
        "valid": not source_leaks and not duplicate_prompt_rows and not query_leaks,
        "row_count": len(rows),
        "source_count": len(source_to_splits),
        "source_split_leaks": source_leaks,
        "duplicate_prompt_rows": duplicate_prompt_rows,
        "query_id_split_leaks": query_leaks,
    }
