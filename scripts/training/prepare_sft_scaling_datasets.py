"""Prepare deterministic row-count scaling subsets for answer-only SFT."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from cad_qa.hashing import sha256_text
from cad_qa.jsonio import read_jsonl, write_json, write_jsonl


DEFAULT_SIZES = (1000, 5000, 15000, 50000)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sizes", nargs="+", type=int, default=list(DEFAULT_SIZES))
    parser.add_argument("--train-splits", nargs="+", default=["train"])
    parser.add_argument("--eval-splits", nargs="+", default=["validation"])
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args(argv)

    train_rows = _load_splits(args.dataset_dir, args.train_splits)
    eval_rows = _load_splits(args.dataset_dir, args.eval_splits)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": "cadqa_sft_scaling_manifest_v1",
        "dataset_dir": str(args.dataset_dir),
        "seed": args.seed,
        "sizes": {},
    }
    for size in sorted(set(args.sizes)):
        selected = _stratified_rows(train_rows, target_count=size, seed=args.seed)
        name = f"train_{size}"
        scale_dir = args.output_dir / name
        scale_dir.mkdir(parents=True, exist_ok=True)
        train_examples = [_sft_example(row) for row in selected]
        eval_examples = [_sft_example(row) for row in eval_rows]
        write_jsonl(scale_dir / "train.jsonl", train_examples)
        write_jsonl(scale_dir / "validation.jsonl", eval_examples)
        item = {
            "requested_train_rows": size,
            "train_row_count": len(train_examples),
            "eval_row_count": len(eval_examples),
            "train_task_counts": dict(
                Counter(example["task_type"] for example in train_examples)
            ),
            "eval_task_counts": dict(
                Counter(example["task_type"] for example in eval_examples)
            ),
        }
        write_json(
            scale_dir / "sft_dataset_report.json",
            {"schema": "cadqa_sft_scaling_report_v1", "name": name, **item},
        )
        report["sizes"][name] = item
    write_json(args.output_dir / "sft_scaling_manifest.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))


def _load_splits(dataset_dir: Path, splits: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split in splits:
        path = dataset_dir / "jsonl" / f"{split}.jsonl"
        if path.exists():
            rows.extend(read_jsonl(path))
    return sorted(rows, key=lambda row: str(row["id"]))


def _stratified_rows(
    rows: list[dict[str, Any]], *, target_count: int, seed: int
) -> list[dict[str, Any]]:
    if target_count >= len(rows):
        return sorted(rows, key=lambda row: str(row["id"]))
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[str(row.get("task_type"))].append(row)
    ordered_by_task = {
        task: sorted(task_rows, key=lambda row: _stable_key(row, seed))
        for task, task_rows in by_task.items()
    }
    selected: list[dict[str, Any]] = []
    while len(selected) < target_count:
        changed = False
        for task in sorted(ordered_by_task):
            if ordered_by_task[task] and len(selected) < target_count:
                selected.append(ordered_by_task[task].pop(0))
                changed = True
        if not changed:
            break
    return sorted(selected, key=lambda row: str(row["id"]))


def _stable_key(row: dict[str, Any], seed: int) -> str:
    return sha256_text(f"{seed}:{row.get('id')}:{row.get('source_id')}")


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
