"""Machine-readable test-evidence gates for generated release families."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from dataset.release.sft import prompt_family
from dataset.query.family_manifest import DEFAULT_FAMILY_MANIFEST, load_family_manifest

DEFAULT_FAMILY_TEST_EVIDENCE = Path(__file__).parents[1] / "query" / "family_test_evidence.yaml"
REQUIRED_TEST_EVIDENCE_KINDS = (
    "positive_generation",
    "failure_or_quarantine",
    "release_report_accounting",
)


def load_family_test_evidence(path: Path | None = None) -> dict[str, Any]:
    evidence_path = path or DEFAULT_FAMILY_TEST_EVIDENCE
    if not evidence_path.exists():
        return {
            "schema_version": 1,
            "path": str(evidence_path),
            "exists": False,
            "families": {},
        }
    if evidence_path.suffix == ".json":
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    else:
        payload = yaml.safe_load(evidence_path.read_text(encoding="utf-8")) or {}
    families = {}
    for family in payload.get("families", []):
        family_id = str(family["id"])
        families[family_id] = {
            "id": family_id,
            "positive_generation": _string_list(family.get("positive_generation")),
            "failure_or_quarantine": _string_list(family.get("failure_or_quarantine")),
            "release_report_accounting": _string_list(family.get("release_report_accounting")),
            "notes": family.get("notes"),
        }
    return {
        "schema_version": payload.get("schema_version", 1),
        "path": str(evidence_path),
        "exists": True,
        "families": families,
    }


def family_test_evidence_gate_report(
    rows: list[dict[str, Any]],
    *,
    evidence_path: Path | None = DEFAULT_FAMILY_TEST_EVIDENCE,
    family_manifest: Path | None = DEFAULT_FAMILY_MANIFEST,
    enforce: bool = False,
) -> dict[str, Any]:
    """Validate test evidence for generated release families."""

    manifest = load_family_manifest(family_manifest)
    evidence = load_family_test_evidence(evidence_path)
    release_families = {
        family_id
        for family_id, spec in manifest["families"].items()
        if spec.get("status") == "release"
    }
    generated_release_families = sorted(
        {
            prompt_family(row)
            for row in rows
            if not release_families or prompt_family(row) in release_families
        }
    )
    violations = []
    if not evidence["exists"]:
        violations.append({"reason": "missing_family_test_evidence"})
    family_reports = []
    for family in generated_release_families:
        item = evidence["families"].get(family, {})
        missing_kinds = [
            kind
            for kind in REQUIRED_TEST_EVIDENCE_KINDS
            if not item.get(kind)
        ]
        family_reports.append(
            {
                "prompt_family": family,
                "positive_generation": item.get("positive_generation") or [],
                "failure_or_quarantine": item.get("failure_or_quarantine") or [],
                "release_report_accounting": item.get("release_report_accounting") or [],
                "missing_evidence_kinds": missing_kinds,
                "valid": not missing_kinds,
            }
        )
        if missing_kinds:
            violations.append(
                {
                    "reason": "missing_family_test_evidence_kinds",
                    "prompt_family": family,
                    "missing_evidence_kinds": missing_kinds,
                }
            )
    valid = True
    if enforce:
        valid = manifest["exists"] and evidence["exists"] and not violations
    return {
        "valid": valid,
        "enforced": enforce,
        "manifest_path": manifest["path"],
        "manifest_exists": manifest["exists"],
        "evidence_path": evidence["path"],
        "evidence_exists": evidence["exists"],
        "required_evidence_kinds": list(REQUIRED_TEST_EVIDENCE_KINDS),
        "generated_release_family_count": len(generated_release_families),
        "violations": violations,
        "families": family_reports,
    }


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item)]
    return [str(value)] if str(value) else []
