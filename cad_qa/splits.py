"""Deterministic group-safe split assignment and leakage checks."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from cad_qa.hashing import sha256_text

DEFAULT_SPLIT_THRESHOLDS = (
    (80, "train"),
    (90, "validation"),
    (100, "test_random"),
)

PROTECTED_HOLDOUT_FRACTION = 0.1

PROTECTED_SPLIT_KEYS = (
    "source_id",
    "generator_id",
    "source_subtree",
    "normalized_source_code_hash",
    "operation_signature_hash",
    "topology_signature_hash",
    "counterfactual_group_id",
    "point_sampling_group_id",
    "split_group",
)

PROTECTED_SPLIT_AUDIT_KEYS = {
    "test_generator_heldout": {
        "source_id",
        "normalized_source_code_hash",
        "generator_id",
        "split_group",
    },
    "test_source_subtree_heldout": {
        "source_id",
        "normalized_source_code_hash",
        "source_subtree",
        "split_group",
    },
    "test_operation_heldout": {
        "source_id",
        "normalized_source_code_hash",
        "operation_signature_hash",
        "split_group",
    },
    "test_topology_heldout": {
        "source_id",
        "normalized_source_code_hash",
        "topology_signature_hash",
        "split_group",
    },
    "test_near_boundary": {
        "source_id",
        "normalized_source_code_hash",
        "point_sampling_group_id",
        "split_group",
    },
}


def assign_split_for_group(group_id: str, seed: int) -> str:
    digest = sha256_text(f"{seed}:{group_id}").removeprefix("sha256:")
    bucket = int(digest[:8], 16) % 100
    for threshold, split in DEFAULT_SPLIT_THRESHOLDS:
        if bucket < threshold:
            return split
    return "test_random"


def split_group(row: dict[str, Any]) -> str:
    provenance = row.get("provenance", {})
    if not isinstance(provenance, dict):
        return str(row.get("source_id"))
    for key in ("counterfactual_group_id", "source_id", "normalized_source_code_hash"):
        value = provenance.get(key) or row.get(key)
        if value:
            return str(value)
    return str(row.get("source_id"))


def assign_row_splits(rows: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    groups = sorted({split_group(row) for row in rows})
    group_metadata = _group_metadata(rows)
    protected_values = _protected_holdout_values(
        group_metadata, seed, total_group_count=len(groups)
    )
    assignments = {
        group: _protected_split_for_group(group_metadata[group], protected_values)
        or assign_split_for_group(group, seed)
        for group in groups
    }
    if len(groups) > 1 and "validation" not in set(assignments.values()):
        train_groups = [group for group in groups if assignments[group] == "train"]
        candidate_groups = train_groups or groups
        assignments[
            max(candidate_groups, key=lambda group: _stable_bucket(group, seed))
        ] = "validation"
    updated: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        copy["split"] = assignments[split_group(row)]
        provenance = dict(copy.get("provenance") or {})
        provenance.setdefault("split_group", split_group(row))
        copy["provenance"] = provenance
        updated.append(copy)
    return updated


def _group_metadata(rows: list[dict[str, Any]]) -> dict[str, dict[str, set[str]]]:
    metadata: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        group = split_group(row)
        provenance = (
            row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        )
        for key in (
            "generator_id",
            "source_subtree",
            "operation_signature_hash",
            "topology_signature_hash",
            "point_sampling_group_id",
        ):
            value = provenance.get(key)
            if value not in (None, ""):
                metadata[group][key].add(str(value))
    return metadata


def _protected_holdout_values(
    group_metadata: dict[str, dict[str, set[str]]],
    seed: int,
    total_group_count: int,
) -> dict[str, set[str]]:
    split_by_key = {
        "generator_id": "test_generator_heldout",
        "source_subtree": "test_source_subtree_heldout",
        "operation_signature_hash": "test_operation_heldout",
        "topology_signature_hash": "test_topology_heldout",
        "point_sampling_group_id": "test_near_boundary",
    }
    selected: dict[str, set[str]] = {split: set() for split in split_by_key.values()}
    for key, split in split_by_key.items():
        values = sorted(
            {
                value
                for metadata in group_metadata.values()
                for value in metadata.get(key, set())
            }
        )
        if key == "point_sampling_group_id":
            if total_group_count >= 3:
                selected[split].update(
                    value for value in values if value.startswith("near_boundary:")
                )
            continue
        if len(values) < 3:
            continue
        target_count = max(1, round(len(values) * PROTECTED_HOLDOUT_FRACTION))
        ordered = sorted(
            values, key=lambda value: _stable_bucket(f"{key}:{value}", seed)
        )
        selected[split].update(ordered[:target_count])
    return selected


def _protected_split_for_group(
    metadata: dict[str, set[str]],
    protected_values: dict[str, set[str]],
) -> str | None:
    checks = (
        ("point_sampling_group_id", "test_near_boundary"),
        ("topology_signature_hash", "test_topology_heldout"),
        ("operation_signature_hash", "test_operation_heldout"),
        ("generator_id", "test_generator_heldout"),
        ("source_subtree", "test_source_subtree_heldout"),
    )
    for key, split in checks:
        if metadata.get(key, set()) & protected_values.get(split, set()):
            return split
    return None


def _stable_bucket(group_id: str, seed: int) -> int:
    digest = sha256_text(f"{seed}:{group_id}").removeprefix("sha256:")
    return int(digest[:8], 16)


def leakage_audit(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, dict[str, set[str]]] = {
        key: defaultdict(set) for key in PROTECTED_SPLIT_KEYS
    }
    for row in rows:
        split = str(row.get("split"))
        provenance = (
            row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        )
        labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
        for key in PROTECTED_SPLIT_KEYS:
            value = provenance.get(key) or labels.get(key) or row.get(key)
            if value not in (None, ""):
                values[key][str(value)].add(split)
    violations = []
    for key, value_splits in values.items():
        for value, splits in sorted(value_splits.items()):
            protected_splits = {
                split
                for split in splits
                if key in PROTECTED_SPLIT_AUDIT_KEYS.get(split, set())
            }
            if protected_splits and len(splits) > 1:
                violations.append(
                    {"key": key, "value": value, "splits": sorted(splits)}
                )
    return {
        "status": "pass" if not violations else "fail",
        "violations": violations,
        "checked_keys": list(PROTECTED_SPLIT_KEYS),
    }


def split_manifest(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    manifest_rows = []
    for row in rows:
        provenance = (
            row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        )
        manifest_rows.append(
            {
                "row_id": row.get("id"),
                "split": row.get("split"),
                "source_id": row.get("source_id"),
                "generator_id": provenance.get("generator_id"),
                "source_subtree": provenance.get("source_subtree"),
                "normalized_source_code_hash": provenance.get(
                    "normalized_source_code_hash"
                ),
                "operation_signature_hash": provenance.get("operation_signature_hash"),
                "topology_signature_hash": provenance.get("topology_signature_hash"),
                "counterfactual_group_id": provenance.get("counterfactual_group_id"),
                "point_sampling_group_id": provenance.get("point_sampling_group_id"),
                "split_group": provenance.get("split_group"),
            }
        )
    return {"schema": "cadqa_split_manifest_v1", "rows": manifest_rows}
