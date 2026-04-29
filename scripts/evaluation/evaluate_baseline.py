"""Run CAD-QA baselines and persist metrics/predictions."""

from __future__ import annotations

import argparse
from pathlib import Path

from cad_qa.baselines import baseline_predictions, evaluate_predictions, run_baselines
from cad_qa.jsonio import read_jsonl, write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--baseline", action="append")
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args(argv)

    rows = read_jsonl(args.rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not args.baseline:
        metrics = run_baselines(rows, seed=args.seed)
        baselines = list(metrics)
    else:
        baselines = args.baseline
        metrics = {}
        for name in baselines:
            predictions = baseline_predictions(rows, name=name, seed=args.seed)
            metrics[name] = evaluate_predictions(rows, predictions)
    write_json(args.output_dir / "baseline_metrics.json", metrics)
    for name in baselines:
        predictions = baseline_predictions(rows, name=name, seed=args.seed)
        write_json(args.output_dir / f"{name}_predictions.json", predictions)
        write_json(
            args.output_dir / f"{name}_graded.json",
            evaluate_predictions(rows, predictions),
        )
    print(metrics)


if __name__ == "__main__":
    main()
