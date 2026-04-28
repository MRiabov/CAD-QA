"""Prepare answer-only SFT chat JSONL from public CAD-QA rows."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from cad_qa.jsonio import read_jsonl, write_json, write_jsonl


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--train-splits", nargs="+", default=["train"])
    parser.add_argument("--eval-splits", nargs="+", default=["validation"])
    parser.add_argument("--max-train-rows", type=int)
    parser.add_argument("--max-eval-rows", type=int)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    train_rows = _load_splits(args.dataset_dir, args.train_splits)
    eval_rows = _load_splits(args.dataset_dir, args.eval_splits)
    if args.max_train_rows:
        train_rows = train_rows[: args.max_train_rows]
    if args.max_eval_rows:
        eval_rows = eval_rows[: args.max_eval_rows]

    train_examples = [_sft_example(row) for row in train_rows]
    eval_examples = [_sft_example(row) for row in eval_rows]
    write_jsonl(args.output_dir / "train.jsonl", train_examples)
    write_jsonl(args.output_dir / "validation.jsonl", eval_examples)
    report = {
        "schema": "cadqa_answer_sft_dataset_report_v1",
        "train_row_count": len(train_examples),
        "eval_row_count": len(eval_examples),
        "train_splits": args.train_splits,
        "eval_splits": args.eval_splits,
        "train_task_counts": dict(Counter(example["task_type"] for example in train_examples)),
        "eval_task_counts": dict(Counter(example["task_type"] for example in eval_examples)),
        "max_prompt_chars": max([len(example["messages"][0]["content"]) for example in train_examples + eval_examples] or [0]),
        "max_answer_chars": max([len(example["messages"][1]["content"]) for example in train_examples + eval_examples] or [0]),
    }
    write_json(args.output_dir / "sft_dataset_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))


def _load_splits(dataset_dir: Path, splits: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split in splits:
        path = dataset_dir / "jsonl" / f"{split}.jsonl"
        if path.exists():
            rows.extend(read_jsonl(path))
    return sorted(rows, key=lambda row: str(row["id"]))


def _sft_example(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": row["id"],
        "task_type": row["task_type"],
        "split": row["split"],
        "prompt_hash": row.get("hashes", {}).get("prompt_hash"),
        "answer": row["answer"],
        "answer_type": row["answer_type"],
        "parse_policy": row["parse_policy"],
        "messages": [
            {"role": "user", "content": row["prompt"]},
            {"role": "assistant", "content": _answer_to_text(row["answer"])},
        ],
    }


def _answer_to_text(answer: Any) -> str:
    if isinstance(answer, dict):
        return json.dumps(answer, separators=(",", ":"), sort_keys=True)
    return str(answer)


if __name__ == "__main__":
    main()
