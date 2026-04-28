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
    assignments = {group: assign_split_for_group(group, seed) for group in groups}
    if len(groups) > 1 and "validation" not in set(assignments.values()):
        train_groups = [group for group in groups if assignments[group] == "train"]
        candidate_groups = train_groups or groups
        assignments[max(candidate_groups, key=lambda group: _stable_bucket(group, seed))] = "validation"
    updated: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        copy["split"] = assignments[split_group(row)]
        provenance = dict(copy.get("provenance") or {})
        provenance.setdefault("split_group", split_group(row))
        copy["provenance"] = provenance
        updated.append(copy)
    return updated


def _stable_bucket(group_id: str, seed: int) -> int:
    digest = sha256_text(f"{seed}:{group_id}").removeprefix("sha256:")
    return int(digest[:8], 16)


def leakage_audit(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, dict[str, set[str]]] = {key: defaultdict(set) for key in PROTECTED_SPLIT_KEYS}
    for row in rows:
        split = str(row.get("split"))
        provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
        for key in PROTECTED_SPLIT_KEYS:
            value = provenance.get(key) or labels.get(key) or row.get(key)
            if value not in (None, ""):
                values[key][str(value)].add(split)
    violations = []
    protected_tests = {
        "test_generator_heldout",
        "test_source_subtree_heldout",
        "test_operation_heldout",
        "test_topology_heldout",
        "test_near_boundary",
    }
    for key, value_splits in values.items():
        for value, splits in sorted(value_splits.items()):
            if len(splits & protected_tests) and len(splits) > 1:
                violations.append({"key": key, "value": value, "splits": sorted(splits)})
    return {
        "status": "pass" if not violations else "fail",
        "violations": violations,
        "checked_keys": list(PROTECTED_SPLIT_KEYS),
    }


def split_manifest(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    manifest_rows = []
    for row in rows:
        provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        manifest_rows.append(
            {
                "row_id": row.get("id"),
                "split": row.get("split"),
                "source_id": row.get("source_id"),
                "generator_id": provenance.get("generator_id"),
                "source_subtree": provenance.get("source_subtree"),
                "normalized_source_code_hash": provenance.get("normalized_source_code_hash"),
                "operation_signature_hash": provenance.get("operation_signature_hash"),
                "topology_signature_hash": provenance.get("topology_signature_hash"),
                "counterfactual_group_id": provenance.get("counterfactual_group_id"),
                "point_sampling_group_id": provenance.get("point_sampling_group_id"),
                "split_group": provenance.get("split_group"),
            }
        )
    return {"schema": "cadqa_split_manifest_v1", "rows": manifest_rows}
