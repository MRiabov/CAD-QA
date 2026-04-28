"""Build a task-transfer matrix from evaluation metric artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from cad_qa.jsonio import read_json, write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metric", action="append", required=True, help="TRAIN_FAMILY=path/to/prediction_metrics.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    report = build_transfer_matrix(args.metric)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "task_transfer_matrix.json", report)
    _write_csv(args.output_dir / "task_transfer_matrix.csv", report["cells"])
    print(json.dumps(report, indent=2, sort_keys=True))


def build_transfer_matrix(metric_specs: list[str]) -> dict[str, Any]:
    cells = []
    for spec in metric_specs:
        train_family, path = _parse_spec(spec)
        metrics = read_json(path)
        by_task = metrics.get("by_task_type") if isinstance(metrics.get("by_task_type"), dict) else {}
        for eval_family, item in sorted(by_task.items()):
            if not isinstance(item, dict):
                continue
            cells.append(
                {
                    "train_family": train_family,
                    "eval_family": eval_family,
                    "row_count": int(item.get("row_count", 0)),
                    "accuracy": float(item.get("accuracy", 0.0)),
                    "invalid_output_rate": float(item.get("invalid_output_rate", 0.0)),
                    "metric_path": str(path),
                }
            )
    return {
        "schema": "cadqa_task_transfer_matrix_v1",
        "cell_count": len(cells),
        "train_families": sorted({cell["train_family"] for cell in cells}),
        "eval_families": sorted({cell["eval_family"] for cell in cells}),
        "cells": cells,
    }


def _parse_spec(spec: str) -> tuple[str, Path]:
    if "=" not in spec:
        raise ValueError("--metric must be TRAIN_FAMILY=path")
    label, path = spec.split("=", 1)
    if not label:
        raise ValueError("TRAIN_FAMILY label must not be empty")
    return label, Path(path)


def _write_csv(path: Path, cells: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["train_family", "eval_family", "row_count", "accuracy", "invalid_output_rate", "metric_path"],
        )
        writer.writeheader()
        writer.writerows(cells)


if __name__ == "__main__":
    main()
