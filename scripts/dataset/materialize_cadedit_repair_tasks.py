"""Materialize conservative CADEditQA selector repair rows from CAD-QA labels."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from cad_qa.hashing import sha256_json
from cad_qa.jsonio import read_jsonl, write_json, write_jsonl
from cad_qa.splits import assign_row_splits, split_manifest


SELECTOR_DISTRACTORS = ['faces(">Z")', 'faces("<Z")', 'edges("|Z")', 'vertices()']


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset-version", default="cadeditqa-v0.1")
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args(argv)

    source_rows = _load_rows(args.dataset_dir)
    rows = materialize_selector_repair_rows(source_rows, dataset_version=args.dataset_version)
    rows = assign_row_splits(rows, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_split_jsonl(args.output_dir / "jsonl", rows)
    write_json(args.output_dir / "split_manifest.json", split_manifest(rows))
    report = {
        "schema": "cadeditqa_repair_task_report_v1",
        "source_dataset_dir": str(args.dataset_dir),
        "dataset_version": args.dataset_version,
        "row_count": len(rows),
        "row_counts_by_task_type": dict(Counter(str(row.get("task_type")) for row in rows)),
        "row_counts_by_split": dict(Counter(str(row.get("split")) for row in rows)),
    }
    write_json(args.output_dir / "metadata.json", report)
    print(report)


def materialize_selector_repair_rows(rows: list[dict[str, Any]], *, dataset_version: str) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if row.get("task_type") != "selector_count":
            continue
        labels = row.get("labels") if isinstance(row.get("labels"), dict) else {}
        selector = labels.get("selector_result") if isinstance(labels.get("selector_result"), dict) else {}
        expression = selector.get("selector_expression")
        selected_count = selector.get("selected_count")
        if not isinstance(expression, str) or not isinstance(selected_count, int):
            continue
        choices = _selector_choices(expression)
        prompt = (
            "Given the CadQuery script below, choose the selector expression that repairs the selection "
            f"to match the recorded target count `{selected_count}` for the same target feature. "
            "Answer with exactly one listed selector expression.\n\n"
            f"Choices: {', '.join(choices)}\n\n"
            f"{_code_block(row.get('prompt'))}"
        )
        prompt_hash = sha256_json({"task_type": "selector_repair", "source_row_id": row.get("id"), "prompt": prompt})
        row_payload = {
            "dataset_version": dataset_version,
            "task_type": "selector_repair",
            "source_id": row.get("source_id"),
            "trace_id": row.get("trace_id"),
            "target_feature_id": row.get("target_feature_id"),
            "answer": expression,
            "prompt_hash": prompt_hash,
        }
        provenance = dict(row.get("provenance") if isinstance(row.get("provenance"), dict) else {})
        provenance["source_cadqa_row_id"] = row.get("id")
        output.append(
            {
                "id": "cadedit_selector_repair_" + sha256_json(row_payload).removeprefix("sha256:")[:16],
                "dataset_version": dataset_version,
                "task_type": "selector_repair",
                "source_id": row.get("source_id"),
                "trace_id": row.get("trace_id"),
                "target_feature_id": row.get("target_feature_id"),
                "split": row.get("split", "train"),
                "prompt": prompt,
                "answer_type": "choice",
                "answer": expression,
                "choices": choices,
                "unit": None,
                "numeric_tolerance": None,
                "requires": ["cadquery_syntax", "selector_semantics", "edit_repair"],
                "difficulty_tags": ["cadeditqa", "selector_repair"],
                "labels": {
                    "answer_status": "ok",
                    "failure_reason": None,
                    "source_cadqa_row_id": row.get("id"),
                    "target_selected_count": selected_count,
                    "selector_result": selector,
                },
                "diagnostics": {"answer_status": "ok", "failure_reason": None, "source_task_type": row.get("task_type")},
                "provenance": provenance,
                "hashes": {**(row.get("hashes") if isinstance(row.get("hashes"), dict) else {}), "prompt_hash": prompt_hash},
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
        write_jsonl(jsonl_dir / f"{split}.jsonl", sorted(split_rows, key=lambda row: str(row["id"])))


def _selector_choices(answer: str) -> list[str]:
    choices = [answer]
    for candidate in SELECTOR_DISTRACTORS:
        if candidate not in choices:
            choices.append(candidate)
    return choices


def _code_block(prompt: Any) -> str:
    text = str(prompt or "")
    marker = "```python\n"
    start = text.find(marker)
    if start == -1:
        return text
    return text[start:]


if __name__ == "__main__":
    main()
