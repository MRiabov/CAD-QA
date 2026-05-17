"""Release dataset export helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from cad_qa.dataset.audit import leakage_audit
from cad_qa.dataset.public import write_public_private_artifacts
from cad_qa.dataset.quarantine import quarantine_report
from cad_qa.dataset.release_report import write_release_verifier_report
from cad_qa.dataset.report import dataset_card_markdown, dataset_report, failure_report
from cad_qa.dataset.split import split_manifest
from cad_qa.dataset.validate import validate_dataset_dir
from cad_qa.io import write_json, write_jsonl


def export_release_dataset(rows: list[dict[str, Any]], *, out: Path, source_dataset: Path | None = None) -> dict[str, Any]:
    release_ready_rows = [row for row in rows if row.get("release_ready") is True]
    release_rows, duplicate_exclusions = _dedupe_release_prompts(release_ready_rows)
    if not release_rows:
        raise ValueError("no release-ready rows found")
    out.mkdir(parents=True, exist_ok=True)
    write_jsonl(out / "rows.jsonl", release_rows)
    public_private = write_public_private_artifacts(release_rows, out)
    split_rows: dict[str, list[dict[str, Any]]] = {}
    for row in release_rows:
        split_rows.setdefault(row.get("split", "unsplit"), []).append(row)
    for split, items in sorted(split_rows.items()):
        write_jsonl(out / "jsonl" / f"{split}.jsonl", items)

    manifest = split_manifest(release_rows)
    write_json(out / "split_manifest.json", manifest)
    report = dataset_report(release_rows)
    report["split_manifest"] = manifest
    if source_dataset is not None:
        report["source_dataset"] = str(source_dataset)
    report["excluded_quarantine_count"] = len(rows) - len(release_ready_rows)
    report["excluded_duplicate_prompt_count"] = len(duplicate_exclusions)
    write_json(out / "dataset_report.json", report)
    write_json(
        out / "release_exclusions.json",
        {
            "excluded_quarantine_count": len(rows) - len(release_ready_rows),
            "excluded_duplicate_prompt_count": len(duplicate_exclusions),
            "duplicate_prompt_exclusions": duplicate_exclusions,
        },
    )

    validation = validate_dataset_dir(out, release=True)
    audit = leakage_audit(release_rows, manifest)
    write_json(out / "leakage_audit.json", audit)
    quarantine = quarantine_report(release_rows)
    write_json(out / "quarantine_report.json", quarantine)
    failures = failure_report([])
    write_json(out / "failure_report.json", failures)
    (out / "DATASET_CARD.md").write_text(
        dataset_card_markdown(
            dataset_path=out,
            report=report,
            validation=validation,
            audit=audit,
            failures=failures,
        ),
        encoding="utf-8",
    )
    verifier_report = write_release_verifier_report(out)
    return {
        "row_count": len(release_rows),
        "excluded_quarantine_count": len(rows) - len(release_ready_rows),
        "excluded_duplicate_prompt_count": len(duplicate_exclusions),
        "valid": validation["valid"] and audit["valid"],
        "out": str(out),
        "dataset": report,
        "validation": validation,
        "leakage_audit": audit,
        "quarantine": quarantine,
        "public_private": public_private,
        "verifier_report": verifier_report,
    }


def _dedupe_release_prompts(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen: dict[str, str | None] = {}
    kept: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for row in rows:
        prompt_hash = hashlib.sha256(str(row.get("prompt", "")).encode("utf-8")).hexdigest()
        kept_row_id = seen.get(prompt_hash)
        if kept_row_id is not None:
            exclusions.append(
                {
                    "prompt_hash": prompt_hash,
                    "kept_row_id": kept_row_id,
                    "dropped_row_id": row.get("row_id"),
                }
            )
            continue
        seen[prompt_hash] = row.get("row_id")
        kept.append(row)
    return kept, exclusions
