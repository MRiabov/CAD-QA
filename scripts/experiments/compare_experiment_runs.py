"""Build comparison tables from CAD-QA experiment metric artifacts."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from cad_qa.jsonio import read_json, write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs", nargs="+", type=Path, help="Metric JSON files or run directories."
    )
    parser.add_argument(
        "--label", action="append", help="Optional labels matching inputs order."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    labels = args.label or []
    if labels and len(labels) != len(args.inputs):
        raise SystemExit("--label must be provided once per input when used")
    report = build_comparison_report(args.inputs, labels=labels)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "experiment_comparison.json", report)
    _write_csv(args.output_dir / "headline_comparison.csv", report["headline_rows"])
    _write_csv(
        args.output_dir / "task_family_comparison.csv", report["task_family_rows"]
    )
    _write_csv(args.output_dir / "split_comparison.csv", report["split_rows"])
    _write_markdown(args.output_dir / "experiment_comparison.md", report)
    print(report)


def build_comparison_report(
    inputs: list[Path], *, labels: list[str] | None = None
) -> dict[str, Any]:
    labels = labels or []
    records: list[dict[str, Any]] = []
    for index, path in enumerate(inputs):
        label = labels[index] if index < len(labels) else _default_label(path)
        records.extend(_metric_records(path, label=label))

    headline_rows = [_headline_row(record) for record in records]
    task_rows = [
        _group_row(
            record, group_name=task_type, metrics=metrics, group_kind="task_type"
        )
        for record in records
        for task_type, metrics in sorted(
            _dict_field(record["metrics"], "by_task_type").items()
        )
    ]
    split_rows = [
        _group_row(record, group_name=split, metrics=metrics, group_kind="split")
        for record in records
        for split, metrics in sorted(_dict_field(record["metrics"], "by_split").items())
    ]
    best = max(
        headline_rows,
        key=lambda row: (float(row["accuracy"]), -float(row["invalid_output_rate"])),
        default=None,
    )
    return {
        "schema": "cadqa_experiment_comparison_v1",
        "status": "pass" if headline_rows else "empty",
        "input_count": len(inputs),
        "metric_record_count": len(records),
        "best_by_accuracy": best,
        "headline_rows": sorted(
            headline_rows, key=lambda row: (str(row["run"]), str(row["system"]))
        ),
        "task_family_rows": sorted(
            task_rows,
            key=lambda row: (
                str(row["task_type"]),
                str(row["run"]),
                str(row["system"]),
            ),
        ),
        "split_rows": sorted(
            split_rows,
            key=lambda row: (str(row["split"]), str(row["run"]), str(row["system"])),
        ),
    }


def _metric_records(path: Path, *, label: str) -> list[dict[str, Any]]:
    metrics_path = _resolve_metrics_path(path)
    if metrics_path is None:
        return [_non_metric_record(path, label=label)]
    metrics = read_json(metrics_path)
    if _looks_like_metric(metrics):
        return [
            {
                "run": label,
                "system": metrics_path.stem,
                "metrics": metrics,
                "path": str(metrics_path),
            }
        ]
    if isinstance(metrics, dict):
        return [
            {
                "run": label,
                "system": str(name),
                "metrics": value,
                "path": str(metrics_path),
            }
            for name, value in sorted(metrics.items())
            if isinstance(value, dict) and _looks_like_metric(value)
        ]
    return []


def _resolve_metrics_path(path: Path) -> Path | None:
    if path.is_file():
        return path
    candidates = [
        path / "baseline_metrics.json",
        path / "evaluation_metrics.json",
        path / "metrics.json",
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def _non_metric_record(path: Path, *, label: str) -> dict[str, Any]:
    status_path = path / "run_status.json"
    train_result_path = path / "train_result.json"
    payload = {}
    if status_path.exists():
        payload["run_status"] = read_json(status_path)
    if train_result_path.exists():
        payload["train_result"] = read_json(train_result_path)
    return {
        "run": label,
        "system": path.name,
        "metrics": {
            "row_count": 0,
            "accuracy": 0.0,
            "invalid_output_rate": 0.0,
            "by_task_type": {},
            "by_split": {},
            "non_metric_payload": payload,
        },
        "path": str(path),
    }


def _looks_like_metric(value: Any) -> bool:
    return isinstance(value, dict) and {
        "row_count",
        "accuracy",
        "invalid_output_rate",
    } <= set(value)


def _headline_row(record: dict[str, Any]) -> dict[str, Any]:
    metrics = record["metrics"]
    return {
        "run": record["run"],
        "system": record["system"],
        "row_count": int(metrics.get("row_count", 0)),
        "accuracy": float(metrics.get("accuracy", 0.0)),
        "invalid_output_rate": float(metrics.get("invalid_output_rate", 0.0)),
        "path": record["path"],
    }


def _group_row(
    record: dict[str, Any], *, group_name: str, metrics: Any, group_kind: str
) -> dict[str, Any]:
    metrics = metrics if isinstance(metrics, dict) else {}
    return {
        "run": record["run"],
        "system": record["system"],
        group_kind: group_name,
        "row_count": int(metrics.get("row_count", 0)),
        "accuracy": float(metrics.get("accuracy", 0.0)),
        "invalid_output_rate": float(metrics.get("invalid_output_rate", 0.0)),
    }


def _dict_field(metrics: dict[str, Any], field: str) -> dict[str, Any]:
    value = metrics.get(field)
    return value if isinstance(value, dict) else {}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# CAD-QA Experiment Comparison",
        "",
        f"Status: `{report['status']}`",
        f"Metric records: `{report['metric_record_count']}`",
        "",
        "## Headline",
        "",
        "| Run | System | Rows | Accuracy | Invalid output rate |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in report["headline_rows"]:
        lines.append(
            f"| {row['run']} | {row['system']} | {row['row_count']} | "
            f"{row['accuracy']:.4f} | {row['invalid_output_rate']:.4f} |"
        )
    best = report.get("best_by_accuracy")
    if best:
        lines.extend(["", f"Best by accuracy: `{best['run']}/{best['system']}`."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _default_label(path: Path) -> str:
    return path.name if path.is_dir() else path.stem


if __name__ == "__main__":
    main()
