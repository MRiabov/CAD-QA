"""Release-scale verifier and quarantine reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cad_qa.dataset.audit import leakage_audit
from cad_qa.dataset.public import public_private_audit
from cad_qa.dataset.quarantine import quarantine_report
from cad_qa.dataset.report import dataset_report, failure_report
from cad_qa.dataset.split import split_manifest
from cad_qa.dataset.validate import validate_rows
from cad_qa.io import read_jsonl, write_json


def release_verifier_report(
    rows: list[dict[str, Any]],
    *,
    failures: list[dict[str, Any]] | None = None,
    split: dict[str, Any] | None = None,
    public_rows: list[dict[str, Any]] | None = None,
    private_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate release-readiness gates and verifier/quarantine taxonomy."""

    split = split or split_manifest(rows)
    dataset = dataset_report(rows)
    validation = validate_rows(rows)
    release_validation = validate_rows(rows, release=True)
    leakage = leakage_audit(rows, split)
    quarantine = quarantine_report(rows)
    failures_by_reason = failure_report(failures or [])
    public_private = public_private_audit(public_rows, private_rows) if public_rows is not None and private_rows is not None else None
    stop_gates = {
        "row_validation": validation["valid"],
        "release_validation": release_validation["valid"],
        "leakage_audit": leakage["valid"],
        "no_quarantined_rows": quarantine["quarantine_count"] == 0,
        "public_private_audit": public_private["valid"] if public_private is not None else None,
    }
    blocking = [name for name, passed in stop_gates.items() if passed is False]
    return {
        "row_count": len(rows),
        "valid_for_release": not blocking,
        "blocking_gates": blocking,
        "stop_gates": stop_gates,
        "dataset": dataset,
        "validation": validation,
        "release_validation": release_validation,
        "leakage_audit": leakage,
        "quarantine": quarantine,
        "failure_report": failures_by_reason,
        "split_manifest": split,
        "public_private_audit": public_private,
    }


def release_verifier_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CAD-QA Release Verifier Report",
        "",
        f"- Rows: {report['row_count']}",
        f"- Valid for release: {str(report['valid_for_release']).lower()}",
        f"- Blocking gates: {report['blocking_gates']}",
        "",
        "## Stop Gates",
        "",
        _json_block(report["stop_gates"]),
        "",
        "## Dataset",
        "",
        _json_block(
            {
                "hop_counts": report["dataset"].get("hop_counts", {}),
                "difficulty_buckets": report["dataset"].get("difficulty_buckets", {}),
                "relation_families": report["dataset"].get("relation_families", {}),
                "measurement_scopes": report["dataset"].get("measurement_scopes", {}),
                "evidence_tiers": report["dataset"].get("evidence_tiers", {}),
                "release_ready": report["dataset"].get("release_ready", {}),
            }
        ),
        "",
        "## Quarantine",
        "",
        _json_block(report["quarantine"]),
        "",
        "## Verifier Failures",
        "",
        _json_block(report["failure_report"]),
        "",
        "## Validation",
        "",
        _json_block(
            {
                "validation": report["validation"],
                "release_validation": report["release_validation"],
                "leakage_audit": report["leakage_audit"],
                "public_private_audit": report.get("public_private_audit"),
            }
        ),
        "",
    ]
    return "\n".join(lines)


def write_release_verifier_report(
    dataset_dir: Path,
    *,
    out: Path | None = None,
) -> dict[str, Any]:
    rows = read_jsonl(dataset_dir / "rows.jsonl")
    failure_path = dataset_dir / "failure_manifest.jsonl"
    failures = read_jsonl(failure_path) if failure_path.exists() else []
    split_path = dataset_dir / "split_manifest.json"
    split = json.loads(split_path.read_text(encoding="utf-8")) if split_path.exists() else None
    public_path = dataset_dir / "public.jsonl"
    private_path = dataset_dir / "private.jsonl"
    public = read_jsonl(public_path) if public_path.exists() else None
    private = read_jsonl(private_path) if private_path.exists() else None
    report = release_verifier_report(
        rows,
        failures=failures,
        split=split,
        public_rows=public,
        private_rows=private,
    )
    output_dir = out or dataset_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "release_verifier_report.json", report)
    (output_dir / "RELEASE_VERIFIER_REPORT.md").write_text(release_verifier_markdown(report), encoding="utf-8")
    return report


def _json_block(value: Any) -> str:
    return "```json\n" + json.dumps(value, indent=2, sort_keys=True) + "\n```"
