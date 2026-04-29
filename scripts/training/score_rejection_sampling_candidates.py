"""Score bounded rejection-sampling candidates with CAD-QA verifier rewards."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cad_qa.jsonio import read_jsonl, write_json, write_jsonl
from cad_qa.rewards import score_candidate_records, select_best_candidates


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-candidates-per-row", type=int, default=16)
    args = parser.parse_args(argv)

    rows = read_jsonl(args.rows)
    candidates = read_jsonl(args.candidates)
    scored, report = score_candidate_records(
        rows, candidates, max_candidates_per_row=args.max_candidates_per_row
    )
    selected = select_best_candidates(scored)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "candidate_rewards.jsonl", scored)
    write_jsonl(args.output_dir / "selected_candidates.jsonl", selected)
    write_json(args.output_dir / "reward_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["candidate_count"] == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
