"""Release dataset export helpers."""

from __future__ import annotations

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
    release_rows = [row for row in rows if row.get("release_ready") is True]
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
    report["excluded_quarantine_count"] = len(rows) - len(release_rows)
    write_json(out / "dataset_report.json", report)

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
        "excluded_quarantine_count": len(rows) - len(release_rows),
        "valid": validation["valid"],
        "out": str(out),
        "dataset": report,
        "validation": validation,
        "leakage_audit": audit,
        "quarantine": quarantine,
        "public_private": public_private,
        "verifier_report": verifier_report,
    }
