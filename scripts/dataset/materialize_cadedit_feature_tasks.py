"""Materialize conservative CADEditQA feature-to-edit rows from provenance QA rows."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from cad_qa.hashing import sha256_json
from cad_qa.jsonio import read_jsonl, write_json, write_jsonl
from cad_qa.splits import assign_row_splits, split_manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset-version", default="cadeditqa-v0.1")
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args(argv)

    source_rows = _load_rows(args.dataset_dir)
    rows = materialize_feature_to_edit_rows(
        source_rows, dataset_version=args.dataset_version
    )
    rows = assign_row_splits(rows, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_split_jsonl(args.output_dir / "jsonl", rows)
    write_json(args.output_dir / "split_manifest.json", split_manifest(rows))
    report = {
        "schema": "cadeditqa_feature_to_edit_report_v1",
        "source_dataset_dir": str(args.dataset_dir),
        "dataset_version": args.dataset_version,
        "row_count": len(rows),
        "row_counts_by_split": dict(Counter(str(row.get("split")) for row in rows)),
        "row_counts_by_source": dict(
            Counter(str(row.get("source_id")) for row in rows)
        ),
    }
    write_json(args.output_dir / "metadata.json", report)
    print(report)


def materialize_feature_to_edit_rows(
    rows: list[dict[str, Any]], *, dataset_version: str
) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if row.get("task_type") != "feature_provenance_choice":
            continue
        answer = row.get("answer")
        choices = row.get("choices")
        if (
            answer == "ambiguous_or_merged"
            or not isinstance(answer, str)
            or not isinstance(choices, list)
        ):
            continue
        provenance_label = (
            row.get("labels") if isinstance(row.get("labels"), dict) else {}
        )
        provenance_record = (
            provenance_label.get("provenance")
            if isinstance(provenance_label.get("provenance"), dict)
            else {}
        )
        target = (
            provenance_record.get("target_description")
            or row.get("target_feature_id")
            or "the described target"
        )
        prompt = (
            "Given the CadQuery script and target description below, choose the feature ID that should be edited "
            "to affect the target region with the smallest provenance-consistent change. "
            "Answer with exactly one listed feature ID.\n\n"
            f"Target: {target}\n\n"
            f"Choices: {', '.join(str(choice) for choice in choices if choice != 'ambiguous_or_merged')}\n\n"
            f"{_code_block(row.get('prompt'))}"
        )
        valid_choices = [
            str(choice) for choice in choices if choice != "ambiguous_or_merged"
        ]
        prompt_hash = sha256_json(
            {
                "task_type": "feature_to_edit",
                "source_row_id": row.get("id"),
                "prompt": prompt,
            }
        )
        row_payload = {
            "dataset_version": dataset_version,
            "task_type": "feature_to_edit",
            "source_id": row.get("source_id"),
            "trace_id": row.get("trace_id"),
            "target_feature_id": row.get("target_feature_id"),
            "answer": answer,
            "prompt_hash": prompt_hash,
        }
        provenance = dict(
            row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        )
        provenance["source_cadqa_row_id"] = row.get("id")
        output.append(
            {
                "id": "cadedit_feature_to_edit_"
                + sha256_json(row_payload).removeprefix("sha256:")[:16],
                "dataset_version": dataset_version,
                "task_type": "feature_to_edit",
                "source_id": row.get("source_id"),
                "trace_id": row.get("trace_id"),
                "target_feature_id": row.get("target_feature_id"),
                "split": row.get("split", "train"),
                "prompt": prompt,
                "answer_type": "choice",
                "answer": answer,
                "choices": valid_choices,
                "unit": None,
                "numeric_tolerance": None,
                "requires": ["cadquery_syntax", "feature_provenance", "edit_locality"],
                "difficulty_tags": ["cadeditqa", "feature_to_edit"],
                "labels": {
                    "answer_status": "ok",
                    "failure_reason": None,
                    "source_cadqa_row_id": row.get("id"),
                    "target_description": target,
                    "provenance_relation": provenance_record.get("provenance_relation"),
                },
                "diagnostics": {
                    "answer_status": "ok",
                    "failure_reason": None,
                    "source_task_type": row.get("task_type"),
                },
                "provenance": provenance,
                "hashes": {
                    **(
                        row.get("hashes") if isinstance(row.get("hashes"), dict) else {}
                    ),
                    "prompt_hash": prompt_hash,
                },
                "parse_policy": "strict_enum_v1",
            }
        )
    return output


def _load_rows(dataset_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((dataset_dir / "jsonl").glob("*.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def _write_split_jsonl(jsonl_dir: Path, rows: list[dict[str, Any]]) -> None:
    by_split: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_split.setdefault(str(row["split"]), []).append(row)
    for split, split_rows in sorted(by_split.items()):
        write_jsonl(
            jsonl_dir / f"{split}.jsonl",
            sorted(split_rows, key=lambda row: str(row["id"])),
        )


def _code_block(prompt: Any) -> str:
    text = str(prompt or "")
    marker = "```python\n"
    start = text.find(marker)
    if start == -1:
        return text
    return text[start:]


if __name__ == "__main__":
    main()
