"""Evaluate a prediction JSON file against a CAD-QA row JSONL file."""

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
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    rows = read_jsonl(args.rows)
    predictions = read_prediction_artifact(args.predictions)
    metrics = evaluate_predictions(rows, predictions)
    write_json(args.output, metrics)
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
