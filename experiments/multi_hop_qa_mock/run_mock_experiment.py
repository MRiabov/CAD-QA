"""Score the isolated Multi-Hop CAD-QA mock experiment.

This script intentionally has no project imports. It is a sandbox helper for
the JSON/JSONL artifacts in this directory, not part of the main CAD-QA
pipeline.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    samples = {item["sample_id"]: item for item in read_jsonl(args.samples)}
    responses = list(read_jsonl(args.responses))
    models = read_json(args.models)
    critical_judges = {
        item["model_id"]
        for item in models.get("local_mock_judges", [])
        if item.get("critical")
    }

    solver_rows = score_solvers(samples, responses)
    judge_rows = score_judges(responses, critical_judges)
    solver_summary = summarize_solvers(solver_rows)
    judge_summary = summarize_judges(judge_rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "solver_summary.json", solver_summary)
    write_json(args.output_dir / "judge_summary.json", judge_summary)
    write_report(
        args.output_dir / "mock_experiment_report.md",
        samples=samples,
        solver_rows=solver_rows,
        judge_rows=judge_rows,
        solver_summary=solver_summary,
        judge_summary=judge_summary,
    )

    print(f"Wrote {args.output_dir / 'solver_summary.json'}")
    print(f"Wrote {args.output_dir / 'judge_summary.json'}")
    print(f"Wrote {args.output_dir / 'mock_experiment_report.md'}")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
    return rows


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def normalize_answer(value: Any) -> str:
    return str(value).strip().lower()


def score_solvers(
    samples: dict[str, dict[str, Any]], responses: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for response in responses:
        if response.get("response_type") != "solver":
            continue
        sample_id = str(response.get("sample_id"))
        sample = samples.get(sample_id)
        if sample is None:
            rows.append(
                {
                    **response,
                    "correct": False,
                    "error": "unknown_sample_id",
                }
            )
            continue
        parsed = normalize_answer(response.get("parsed_answer"))
        gold = normalize_answer(sample.get("gold_answer"))
        rows.append(
            {
                **response,
                "gold_answer": sample.get("gold_answer"),
                "correct": parsed == gold,
                "error": None,
            }
        )
    return rows


def score_judges(
    responses: list[dict[str, Any]], critical_judges: set[str]
) -> list[dict[str, Any]]:
    rows = []
    for response in responses:
        if response.get("response_type") != "judge":
            continue
        model_id = str(response.get("model_id"))
        rows.append(
            {
                **response,
                "critical": model_id in critical_judges,
            }
        )
    return rows


def summarize_solvers(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_model: dict[str, Counter[str]] = defaultdict(Counter)
    by_sample: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        model_id = str(row["model_id"])
        sample_id = str(row["sample_id"])
        key = "correct" if row["correct"] else "incorrect"
        by_model[model_id][key] += 1
        by_model[model_id]["total"] += 1
        by_sample[sample_id][key] += 1
        by_sample[sample_id]["total"] += 1

    return {
        "overall": ratio_summary(
            Counter(
                {
                    "correct": sum(1 for row in rows if row["correct"]),
                    "incorrect": sum(1 for row in rows if not row["correct"]),
                    "total": len(rows),
                }
            )
        ),
        "by_model": {
            model_id: ratio_summary(counts)
            for model_id, counts in sorted(by_model.items())
        },
        "by_sample": {
            sample_id: ratio_summary(counts)
            for sample_id, counts in sorted(by_sample.items())
        },
    }


def summarize_judges(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_sample: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_model: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        sample_id = str(row["sample_id"])
        model_id = str(row["model_id"])
        passed = bool(row.get("pass"))
        by_sample[sample_id].append(row)
        by_model[model_id]["pass" if passed else "fail"] += 1
        by_model[model_id]["total"] += 1

    sample_gate = {}
    for sample_id, sample_rows in sorted(by_sample.items()):
        critical_failures = [
            row
            for row in sample_rows
            if row.get("critical") and not bool(row.get("pass"))
        ]
        sample_gate[sample_id] = {
            "critical_pass": not critical_failures,
            "critical_failures": [
                {
                    "model_id": row["model_id"],
                    "failure_reason": row.get("failure_reason"),
                    "actionable_revision": row.get("actionable_revision"),
                }
                for row in critical_failures
            ],
            "judge_count": len(sample_rows),
        }

    return {
        "by_model": {
            model_id: {
                "pass": counts["pass"],
                "fail": counts["fail"],
                "total": counts["total"],
                "pass_rate": round(counts["pass"] / counts["total"], 4)
                if counts["total"]
                else 0.0,
            }
            for model_id, counts in sorted(by_model.items())
        },
        "sample_gate": sample_gate,
    }


def ratio_summary(counts: Counter[str]) -> dict[str, Any]:
    total = counts["total"]
    correct = counts["correct"]
    return {
        "correct": correct,
        "incorrect": counts["incorrect"],
        "total": total,
        "accuracy": round(correct / total, 4) if total else 0.0,
    }


def write_report(
    path: Path,
    *,
    samples: dict[str, dict[str, Any]],
    solver_rows: list[dict[str, Any]],
    judge_rows: list[dict[str, Any]],
    solver_summary: dict[str, Any],
    judge_summary: dict[str, Any],
) -> None:
    solver_by_sample: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in solver_rows:
        solver_by_sample[str(row["sample_id"])].append(row)
    judge_by_sample: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in judge_rows:
        judge_by_sample[str(row["sample_id"])].append(row)

    lines = [
        "# Multi-Hop QA Mock Experiment Report",
        "",
        "This report is generated from mocked solver and judge responses.",
        "",
        "## Solver Summary",
        "",
        f"- Overall accuracy: {solver_summary['overall']['accuracy']}",
        "",
        "## Sample Review",
        "",
    ]
    for sample_id, sample in sorted(samples.items()):
        gate = judge_summary["sample_gate"].get(sample_id, {})
        lines.extend(
            [
                f"### {sample_id}",
                "",
                f"- Gold answer: `{sample['gold_answer']}`",
                f"- Expected difficulty: `{sample.get('expected_difficulty')}`",
                f"- Critical judge pass: `{gate.get('critical_pass')}`",
                "",
                "Question:",
                "",
            ]
        )
        lines.extend(f"> {line}" for line in sample.get("question_lines", []))
        lines.extend(["", "Solver responses:", ""])
        for row in solver_by_sample.get(sample_id, []):
            mark = "correct" if row["correct"] else "wrong"
            lines.append(
                f"- `{row['model_id']}`: `{row.get('parsed_answer')}` ({mark})"
            )
        lines.extend(["", "Judge notes:", ""])
        for row in judge_by_sample.get(sample_id, []):
            status = "pass" if row.get("pass") else "fail"
            reason = row.get("failure_reason") or "none"
            action = row.get("actionable_revision") or "none"
            lines.append(f"- `{row['model_id']}`: {status}, reason: {reason}")
            if action != "none":
                lines.append(f"  Revision: {action}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
