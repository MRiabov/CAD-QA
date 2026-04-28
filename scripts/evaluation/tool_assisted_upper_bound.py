"""Evaluate the trace-label oracle as a tool-assisted CAD-QA upper bound."""

from __future__ import annotations

import argparse
from pathlib import Path

from cad_qa.baselines import baseline_predictions, evaluate_predictions
from cad_qa.jsonio import read_jsonl, write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    rows = read_jsonl(args.rows)
    predictions = baseline_predictions(rows, name="oracle")
    metrics = evaluate_predictions(rows, predictions)
    report = {
        "schema": "cadqa_tool_assisted_upper_bound_v1",
        "mode": "trace_label_oracle",
        "input_rows": str(args.rows),
        "metrics": metrics,
        "interpretation": (
            "This is an oracle/tool upper bound that serializes stored structured "
            "answers. It validates parsing and aggregation, not model reasoning."
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "tool_assisted_upper_bound.json", report)
    write_json(args.output_dir / "oracle_predictions.json", predictions)
    print(report)


if __name__ == "__main__":
    main()
