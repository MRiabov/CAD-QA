"""Create a deterministic task-balanced CAD-QA JSONL subset."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from cad_qa.hashing import sha256_text
from cad_qa.jsonio import read_jsonl, write_json, write_jsonl


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--splits", nargs="+", default=["train", "validation"])
    parser.add_argument("--max-rows-per-task", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": "cadqa_balanced_subset_report_v1",
        "source_dataset_dir": str(args.dataset_dir),
        "max_rows_per_task": args.max_rows_per_task,
        "seed": args.seed,
        "splits": {},
    }
    for split in args.splits:
        rows = _load_split(args.dataset_dir, split)
        balanced = _balanced_rows(rows, max_rows_per_task=args.max_rows_per_task, seed=args.seed)
        write_jsonl(args.output_dir / f"{split}.jsonl", balanced)
        report["splits"][split] = {
            "input_count": len(rows),
            "output_count": len(balanced),
            "input_task_counts": dict(Counter(str(row.get("task_type")) for row in rows)),
            "output_task_counts": dict(Counter(str(row.get("task_type")) for row in balanced)),
        }
    write_json(args.output_dir / "balance_report.json", report)
    print(report)


def _load_split(dataset_dir: Path, split: str) -> list[dict[str, Any]]:
    path = dataset_dir / "jsonl" / f"{split}.jsonl"
    return read_jsonl(path) if path.exists() else []


def _balanced_rows(rows: list[dict[str, Any]], *, max_rows_per_task: int, seed: int) -> list[dict[str, Any]]:
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[str(row.get("task_type"))].append(row)
    selected: list[dict[str, Any]] = []
    for task, task_rows in sorted(by_task.items()):
        ordered = sorted(task_rows, key=lambda row: _stable_order_key(row, seed))
        selected.extend(ordered[:max_rows_per_task])
    return sorted(selected, key=lambda row: (str(row.get("split")), str(row.get("task_type")), str(row.get("id"))))


def _stable_order_key(row: dict[str, Any], seed: int) -> str:
    return sha256_text(f"{seed}:{row.get('id')}:{row.get('source_id')}")


if __name__ == "__main__":
    main()
