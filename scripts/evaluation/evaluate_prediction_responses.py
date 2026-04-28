"""Normalize and grade closed-book CAD-QA prediction response artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cad_qa.baselines import evaluate_predictions
from cad_qa.jsonio import read_jsonl, write_json
from cad_qa.predictions import read_prediction_artifact


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--label", default="closed_book")
    args = parser.parse_args(argv)

    rows = read_jsonl(args.rows)
    predictions = read_prediction_artifact(args.responses)
    metrics = evaluate_predictions(rows, predictions)
    missing = sorted({str(row["id"]) for row in rows} - set(predictions))
    extra = sorted(set(predictions) - {str(row["id"]) for row in rows})
    report = {
        "schema": "cadqa_prediction_evaluation_report_v1",
        "label": args.label,
        "rows": str(args.rows),
        "responses": str(args.responses),
        "row_count": len(rows),
        "prediction_count": len(predictions),
        "missing_prediction_count": len(missing),
        "extra_prediction_count": len(extra),
        "missing_predictions": missing[:100],
        "extra_predictions": extra[:100],
        "metrics": metrics,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "normalized_predictions.json", predictions)
    write_json(args.output_dir / "prediction_metrics.json", metrics)
    write_json(args.output_dir / "prediction_evaluation_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
