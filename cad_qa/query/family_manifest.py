"""Intended query-family manifest loading and release coverage checks."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml


DEFAULT_FAMILY_MANIFEST = Path(__file__).with_name("family_specs.yaml")
VALID_FAMILY_STATUSES = {"release", "calibration", "review_only"}
RELEASE_STATUSES = {"release"}
NON_RELEASE_STATUSES = VALID_FAMILY_STATUSES - RELEASE_STATUSES


def load_family_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or DEFAULT_FAMILY_MANIFEST
    if not manifest_path.exists():
        return {
            "schema_version": 1,
            "path": str(manifest_path),
            "exists": False,
            "families": {},
        }
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    families = {}
    for family in payload.get("families", []):
        family_id = str(family["id"])
        status = str(family.get("status", "release"))
        if status not in VALID_FAMILY_STATUSES:
            raise ValueError(f"unknown family status for {family_id}: {status}")
        families[family_id] = {
            "id": family_id,
            "status": status,
            "title": str(family.get("title", family_id)),
            "target_type": family.get("target_type"),
            "minimum_hops": family.get("minimum_hops"),
            "maximum_hops": family.get("maximum_hops"),
            "notes": family.get("notes"),
        }
    return {
        "schema_version": payload.get("schema_version", 1),
        "path": str(manifest_path),
        "exists": True,
        "families": families,
    }


def intended_family_coverage_report(
    rows: list[dict[str, Any]],
    *,
    manifest_path: Path | None = None,
    enforce: bool = False,
) -> dict[str, Any]:
    manifest = load_family_manifest(manifest_path)
    families = manifest["families"]
    generated_counts = Counter(_prompt_family(row) for row in rows)
    generated = sorted(generated_counts)
    release_families = sorted(
        family_id for family_id, spec in families.items() if spec["status"] in RELEASE_STATUSES
    )
    non_release_families = sorted(
        family_id for family_id, spec in families.items() if spec["status"] in NON_RELEASE_STATUSES
    )
    zero_row_release_families = sorted(set(release_families) - set(generated))
    generated_release_families = sorted(set(generated) & set(release_families))
    generated_non_release_families = sorted(set(generated) & set(non_release_families))
    unknown_generated_families = sorted(family for family in generated if family not in families)
    valid = True
    if enforce:
        valid = (
            manifest["exists"]
            and not zero_row_release_families
            and not generated_non_release_families
            and not unknown_generated_families
        )
    return {
        "valid": valid,
        "enforced": enforce,
        "manifest_path": manifest["path"],
        "manifest_exists": manifest["exists"],
        "generated_family_count": len(generated),
        "generated_families": generated,
        "generated_family_counts": dict(sorted(generated_counts.items())),
        "intended_release_family_count": len(release_families),
        "intended_release_families": release_families,
        "generated_release_family_count": len(generated_release_families),
        "generated_release_families": generated_release_families,
        "non_release_families": non_release_families,
        "zero_row_release_families": zero_row_release_families,
        "generated_non_release_families": generated_non_release_families,
        "unknown_generated_families": unknown_generated_families,
        "families_by_status": {
            status: sorted(family_id for family_id, spec in families.items() if spec["status"] == status)
            for status in sorted(VALID_FAMILY_STATUSES)
        },
    }


def _prompt_family(row: dict[str, Any]) -> str:
    query = row.get("query_program")
    if isinstance(query, dict):
        query_id = query.get("query_id")
        if isinstance(query_id, str) and ":" in query_id:
            return query_id.rsplit(":", 1)[-1]
    row_id = row.get("row_id")
    if isinstance(row_id, str) and ":" in row_id:
        return row_id.rsplit(":", 1)[-1]
    return "unknown"
