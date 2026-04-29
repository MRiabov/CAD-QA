"""Write a Markdown dataset card from CAD-QA release artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from cad_qa.jsonio import read_json, read_jsonl
from cad_qa.validation import validate_dataset_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--baseline-metrics", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    metadata = read_json(args.dataset_dir / "metadata.json")
    validation = validate_dataset_dir(args.dataset_dir)
    failures = (
        read_jsonl(args.dataset_dir / "failure_manifest.jsonl")
        if (args.dataset_dir / "failure_manifest.jsonl").exists()
        else []
    )
    baselines = (
        read_json(args.baseline_metrics)
        if args.baseline_metrics and args.baseline_metrics.exists()
        else None
    )
    card = _card(metadata, validation, failures, baselines)
    output = args.output or args.dataset_dir / "DATASET_CARD.md"
    output.write_text(card, encoding="utf-8")
    print(output)


def _card(
    metadata: dict[str, object],
    validation: dict[str, object],
    failures: list[dict[str, object]],
    baselines: object,
) -> str:
    lines = [
        "# CAD-QA Dataset Card",
        "",
        f"Dataset version: `{metadata.get('dataset_version')}`",
        f"Rows: `{metadata.get('row_count')}`",
        f"Sources: `{metadata.get('source_count')}`",
        f"Traces: `{metadata.get('trace_count')}`",
        f"Source manifest hash: `{metadata.get('source_manifest_hash')}`",
        f"Generation config hash: `{metadata.get('generation_config_hash')}`",
        "",
        "## Task Counts",
        "",
        _table(metadata.get("row_counts_by_task_type", {}), "Task", "Rows"),
        "",
        "## Split Counts",
        "",
        _table(metadata.get("row_counts_by_split", {}), "Split", "Rows"),
        "",
        "## Validation",
        "",
        f"Status: `{validation.get('status')}`",
        f"Leakage audit: `{validation.get('leakage_audit', {}).get('status') if isinstance(validation.get('leakage_audit'), dict) else 'unknown'}`",
        f"Failure records: `{len(failures)}`",
        "",
        "## Label Policy",
        "",
        "```json",
        _jsonish(metadata.get("label_policy", {})),
        "```",
        "",
        "## Known Limitations",
        "",
    ]
    for item in (
        metadata.get("known_limitations", [])
        if isinstance(metadata.get("known_limitations"), list)
        else []
    ):
        lines.append(f"- {item}")
    if baselines is not None:
        lines.extend(["", "## Baselines", "", "```json", _jsonish(baselines), "```"])
    lines.append("")
    return "\n".join(lines)


def _table(values: object, key_title: str, value_title: str) -> str:
    if not isinstance(values, dict):
        return f"| {key_title} | {value_title} |\n| --- | --- |"
    body = [f"| {key_title} | {value_title} |", "| --- | --- |"]
    for key, value in sorted(values.items()):
        body.append(f"| `{key}` | {value} |")
    return "\n".join(body)


def _jsonish(value: object) -> str:
    import json

    return json.dumps(value, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
