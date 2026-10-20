"""Deterministic group-safe release splits."""

from __future__ import annotations

from typing import Any

from dataset.source import source_family_from_path


SPLITS = ("train", "validation", "test")
POOLS = ("sft_train", "rl_train", "eval")
POOL_ASSIGNMENTS = ("sft_train", "rl_train", "eval_validation", "eval_test")
POOL_TO_SPLIT = {
    "sft_train": "train",
    "rl_train": "train",
    "eval_validation": "validation",
    "eval_test": "test",
}
ASSIGNMENT_TO_POOL = {
    "sft_train": "sft_train",
    "rl_train": "rl_train",
    "eval_validation": "eval",
    "eval_test": "eval",
}
PROTECTED_GROUP_KEYS = (
    "split_group",
    "counterfactual_group",
    "source_family",
    "family_id",
    "template_id",
)
REPORTED_PROVENANCE_KEYS = (
    "generator_id",
    "generator",
)
TARGET_POOL_SHARES = {
    "sft_train": 0.70,
    "rl_train": 0.15,
    "eval": 0.15,
}
TARGET_ASSIGNMENT_SHARES = {
    "sft_train": 0.70,
    "rl_train": 0.15,
    "eval_validation": 0.075,
    "eval_test": 0.075,
}
TARGET_SPLIT_SHARES = {
    "train": 0.85,
    "validation": 0.075,
    "test": 0.075,
}
ROW_SHARE_TOLERANCE = 0.05
MIN_ROWS_FOR_SHARE_WARNING = 100


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
    source_pools = manifest.get("pools", {})
    assigned = []
    for row in rows:
        source_id = str(_row_get(row, "source_id"))
        item = row.__dict__.copy() if hasattr(row, "__dict__") else dict(row)
        item["split"] = source_splits[source_id]
        if source_id in source_pools:
            item["pool"] = source_pools[source_id]
        assigned.append(item)
    return assigned


def split_manifest(rows: list[Any]) -> dict[str, Any]:
    source_groups = _source_groups(rows)
    source_pools = {
        source_id: group["pool"]
        for group in source_groups.values()
        for source_id in group["source_ids"]
    }
    sources = {
        source_id: group["split"]
        for group in source_groups.values()
        for source_id in group["source_ids"]
    }
    source_counts = {split: 0 for split in SPLITS}
    for split in sources.values():
        source_counts[split] += 1
    group_counts = {split: 0 for split in SPLITS}
    row_counts = {split: 0 for split in SPLITS}
    pool_source_counts = {pool: 0 for pool in POOLS}
    for pool in source_pools.values():
        pool_source_counts[pool] += 1
    pool_group_counts = {pool: 0 for pool in POOLS}
    pool_row_counts = {pool: 0 for pool in POOLS}
    total_rows = 0
    for group in source_groups.values():
        pool = group["pool"]
        split = group["split"]
        group_counts[split] += 1
        pool_group_counts[pool] += 1
        row_count = int(group.get("row_count", 0) or 0)
        row_counts[split] += row_count
        pool_row_counts[pool] += row_count
        total_rows += row_count
    row_shares = {
        split: (row_counts[split] / total_rows if total_rows else 0.0)
        for split in SPLITS
    }
    pool_row_shares = {
        pool: (pool_row_counts[pool] / total_rows if total_rows else 0.0)
        for pool in POOLS
    }
    return {
        "policy": "deterministic row-weighted 70/15/7.5/7.5 pool assignment over protected leakage/source groups: sft_train / rl_train / eval_validation / eval_test; groups are assigned to the pool with the largest remaining target row share, and the dataset split is derived as train (sft+rl), validation (eval_validation), test (eval_test); all rows sharing source family, counterfactual group, split_group, template/family id, or path-derived family stay together; broad generator provenance is reported but does not merge groups",
        "source_count": len(sources),
        "group_count": len(source_groups),
        "row_count": total_rows,
        "source_counts_by_split": source_counts,
        "group_counts_by_split": group_counts,
        "row_counts_by_split": row_counts,
        "row_shares_by_split": row_shares,
        "target_row_shares_by_split": dict(TARGET_SPLIT_SHARES),
        "source_counts_by_pool": pool_source_counts,
        "group_counts_by_pool": pool_group_counts,
        "row_counts_by_pool": pool_row_counts,
        "row_shares_by_pool": pool_row_shares,
        "target_row_shares_by_pool": dict(TARGET_POOL_SHARES),
        "sources": sources,
        "pools": source_pools,
        "source_groups": source_groups,
        "protected_group_keys": list(PROTECTED_GROUP_KEYS),
        "reported_provenance_keys": list(REPORTED_PROVENANCE_KEYS),
    }


def split_audit(rows: list[Any], manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check that concrete row splits match the group-safe split manifest."""

    manifest = manifest or split_manifest(rows)
    row_sources = {str(_row_get(row, "source_id")) for row in rows}
    manifest_sources = {str(source_id): split for source_id, split in manifest.get("sources", {}).items()}
    manifest_pools = {str(source_id): pool for source_id, pool in manifest.get("pools", {}).items()}
    missing_manifest_sources = sorted(row_sources - set(manifest_sources))
    orphan_manifest_sources = sorted(set(manifest_sources) - row_sources)
    row_split_mismatches = []
    row_pool_mismatches = []
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
        expected_pool = manifest_pools.get(source_id)
        actual_pool = _row_get(row, "pool")
        if actual_pool not in (None, "") and expected_pool is not None and actual_pool != expected_pool:
            row_pool_mismatches.append(
                {
                    "row_id": _row_get(row, "row_id"),
                    "source_id": source_id,
                    "expected_pool": expected_pool,
                    "actual_pool": actual_pool,
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
    if row_pool_mismatches:
        errors.append({"error": "row_pool_mismatch", "rows": row_pool_mismatches})
    if protected_label_split_leaks:
        errors.append({"error": "protected_label_split_leak", "labels": protected_label_split_leaks})

    warnings = []
    group_count = int(manifest.get("group_count") or 0)
    group_counts = manifest.get("group_counts_by_split", {})
    row_counts = manifest.get("row_counts_by_split", {})
    row_shares = manifest.get("row_shares_by_split", {})
    pool_group_counts = manifest.get("group_counts_by_pool", {})
    pool_row_counts = manifest.get("row_counts_by_pool", {})
    pool_row_shares = manifest.get("row_shares_by_pool", {})
    if group_count >= 3:
        empty_splits = [split for split in SPLITS if int(group_counts.get(split, 0) or 0) == 0]
        if empty_splits:
            warnings.append({"warning": "empty_split_bucket", "splits": empty_splits})
        empty_pools = [pool for pool in POOLS if int(pool_group_counts.get(pool, 0) or 0) == 0]
        if empty_pools:
            warnings.append({"warning": "empty_pool_bucket", "pools": empty_pools})
    row_count = int(manifest.get("row_count") or len(rows))
    if row_count >= MIN_ROWS_FOR_SHARE_WARNING:
        drifted = []
        for split in SPLITS:
            share = float(row_shares.get(split, 0.0) or 0.0)
            target = TARGET_SPLIT_SHARES[split]
            if abs(share - target) > ROW_SHARE_TOLERANCE:
                drifted.append(
                    {
                        "split": split,
                        "share": round(share, 4),
                        "target": target,
                        "deviation": round(share - target, 4),
                    }
                )
        if drifted:
            warnings.append({"warning": "row_share_deviation", "splits": drifted})
        pool_drifted = []
        for pool in POOLS:
            share = float(pool_row_shares.get(pool, 0.0) or 0.0)
            target = TARGET_POOL_SHARES[pool]
            if abs(share - target) > ROW_SHARE_TOLERANCE:
                pool_drifted.append(
                    {
                        "pool": pool,
                        "share": round(share, 4),
                        "target": target,
                        "deviation": round(share - target, 4),
                    }
                )
        if pool_drifted:
            warnings.append({"warning": "pool_row_share_deviation", "pools": pool_drifted})

    return {
        "valid": not errors,
        "row_count": len(rows),
        "source_count": len(row_sources),
        "group_count": group_count,
        "protected_group_keys": list(PROTECTED_GROUP_KEYS),
        "reported_provenance_keys": list(REPORTED_PROVENANCE_KEYS),
        "source_counts_by_split": manifest.get("source_counts_by_split", {}),
        "group_counts_by_split": group_counts,
        "row_counts_by_split": row_counts,
        "row_shares_by_split": row_shares,
        "source_counts_by_pool": manifest.get("source_counts_by_pool", {}),
        "group_counts_by_pool": pool_group_counts,
        "row_counts_by_pool": pool_row_counts,
        "row_shares_by_pool": pool_row_shares,
        "missing_manifest_sources": missing_manifest_sources,
        "orphan_manifest_sources": orphan_manifest_sources,
        "row_split_mismatches": row_split_mismatches,
        "row_pool_mismatches": row_pool_mismatches,
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
    source_row_counts: dict[str, int] = {}
    for row in rows:
        source_id = str(_row_get(row, "source_id"))
        labels = _protected_labels(row)
        source_labels.setdefault(source_id, set()).update(labels)
        source_row_counts[source_id] = source_row_counts.get(source_id, 0) + 1
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
    group_row_counts = {
        group_ids[root]: sum(source_row_counts.get(source_id, 0) for source_id in source_ids)
        for root, source_ids in components.items()
    }
    group_pools = _group_pool_map(sorted(group_ids.values()), group_row_counts)
    groups: dict[str, dict[str, Any]] = {}
    for root, source_ids in sorted(components.items(), key=lambda item: group_ids[item[0]]):
        group_id = group_ids[root]
        labels = sorted({label for source_id in source_ids for label in source_labels[source_id]})
        assignment = group_pools[group_id]
        groups[group_id] = {
            "pool": ASSIGNMENT_TO_POOL[assignment],
            "split": POOL_TO_SPLIT[assignment],
            "assignment": assignment,
            "source_ids": source_ids,
            "protected_labels": labels,
            "row_count": group_row_counts[group_id],
        }
    return groups


def _group_pool_map(
    group_ids: list[str],
    group_row_counts: dict[str, int] | None = None,
) -> dict[str, str]:
    if not group_ids:
        return {}
    if len(group_ids) < 3:
        return {group_id: "sft_train" for group_id in group_ids}

    row_counts = {
        group_id: max(1, int((group_row_counts or {}).get(group_id, 1)))
        for group_id in group_ids
    }
    total_rows = sum(row_counts.values())
    targets = {
        pool: total_rows * TARGET_ASSIGNMENT_SHARES[pool]
        for pool in POOL_ASSIGNMENTS
    }
    current = {pool: 0 for pool in POOL_ASSIGNMENTS}
    mapping: dict[str, str] = {}
    for group_id in sorted(group_ids):
        pool = max(
            POOL_ASSIGNMENTS,
            key=lambda candidate: (
                targets[candidate] - current[candidate],
                -POOL_ASSIGNMENTS.index(candidate),
            ),
        )
        mapping[group_id] = pool
        current[pool] += row_counts[group_id]

    for pool in POOL_ASSIGNMENTS:
        if any(assigned == pool for assigned in mapping.values()):
            continue
        donor_pools = [
            candidate
            for candidate in POOL_ASSIGNMENTS
            if sum(1 for assigned in mapping.values() if assigned == candidate) > 1
        ]
        if not donor_pools:
            break
        donor = max(
            donor_pools,
            key=lambda candidate: (
                sum(1 for assigned in mapping.values() if assigned == candidate),
                -POOL_ASSIGNMENTS.index(candidate),
            ),
        )
        donor_group = min(
            (group_id for group_id, assigned in mapping.items() if assigned == donor),
            key=lambda group_id: (row_counts[group_id], group_id),
        )
        mapping[donor_group] = pool
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
