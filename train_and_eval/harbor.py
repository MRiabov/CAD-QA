"""Harbor Query verifier runner and grader for CAD-QA rows.

Harbor task *export* lives in ``dataset/harbor.py``; this module owns the
run/grade side: loading an agent submission, scoring it with the CAD-QA grader,
and writing the Harbor Query verifier artifacts.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from dataset.io import write_json, write_jsonl
from train_and_eval.grading.grade import grade_public_private


def grade_harbor_task(
    task_dir: Path,
    *,
    app_dir: Path | None = None,
    logs_dir: Path | None = None,
) -> dict[str, Any]:
    """Run CAD-QA grading for one materialized Harbor task directory."""

    return grade_harbor_answer_files(
        public_path=task_dir / "workspace" / "row_public.json",
        private_path=task_dir / "expected" / "private.json",
        app_dir=app_dir or Path("/app"),
        logs_dir=logs_dir or Path("/logs/verifier"),
    )


def grade_harbor_answer_files(
    *,
    public_path: Path,
    private_path: Path,
    app_dir: Path,
    logs_dir: Path,
) -> dict[str, Any]:
    """Grade `/app/answer.json` or `/app/answer.txt` with CAD-QA's grader."""

    public = _read_json(public_path)
    private = _read_json(private_path)
    submission = _load_submission(app_dir)
    responses = []
    if submission["status"] == "ok":
        response: dict[str, Any] = {
            "row_id": public["row_id"],
            "answer": submission["answer"],
        }
        if submission.get("confidence") is not None:
            response["confidence"] = submission["confidence"]
        responses.append(response)
    grade = grade_public_private([public], [private], responses)
    graded = grade["graded"][0] if grade["graded"] else {}
    parse_invalid = bool(graded.get("error", "").startswith("parse_error:")) if graded.get("error") else False
    invalid_output = submission["status"] != "ok" or parse_invalid
    reward = 1 if graded.get("correct") is True and not invalid_output else 0
    artifact = {
        "reward": reward,
        "harbor": {
            "submission_status": submission["status"],
            "submission_error": submission.get("error"),
            "invalid_output": invalid_output,
            "invalid_output_reason": submission.get("error") or (graded.get("error") if parse_invalid else None),
        },
        "metrics": {key: value for key, value in grade.items() if key != "graded"},
        "graded": grade["graded"],
    }
    logs_dir.mkdir(parents=True, exist_ok=True)
    write_json(logs_dir / "cadqa_grade.json", artifact)
    write_jsonl(logs_dir / "graded_responses.jsonl", grade["graded"])
    (logs_dir / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    return artifact


def export_harbor_atif(
    responses: list[dict[str, Any]],
    public_rows: list[dict[str, Any]],
    private_rows: list[dict[str, Any]],
    out: Path,
) -> dict[str, Any]:
    """Export graded response/trajectory records for Harbor ATIF workflows."""

    grade = grade_public_private(public_rows, private_rows, responses)
    response_by_id = {response.get("row_id"): response for response in responses}
    public_by_id = {row["row_id"]: row for row in public_rows}
    records: list[dict[str, Any]] = []
    for graded in grade["graded"]:
        row_id = graded["row_id"]
        response = response_by_id.get(row_id, {})
        public = public_by_id.get(row_id, {})
        records.append(
            {
                "row_id": row_id,
                "reward": 1 if graded["correct"] else 0,
                "correct": graded["correct"],
                "invalid_output": bool(graded.get("error", "").startswith("parse_error:")) if graded.get("error") else False,
                "error": graded.get("error"),
                "prompt": public.get("prompt"),
                "answer": response.get("answer", response.get("response")),
                "confidence": response.get("confidence"),
                "atif": response.get("atif") or response.get("trajectory"),
                "trajectory_path": response.get("trajectory_path"),
            }
        )
    out.mkdir(parents=True, exist_ok=True)
    write_jsonl(out / "atif_records.jsonl", records)
    report = {
        "response_count": len(responses),
        "record_count": len(records),
        "metrics": {key: value for key, value in grade.items() if key != "graded"},
    }
    write_json(out / "atif_report.json", report)
    return report


def run_harbor_verifier_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grade_cadqa.py")
    parser.add_argument("--public", type=Path)
    parser.add_argument("--private", type=Path)
    parser.add_argument("--app-dir", type=Path, default=Path("/app"))
    parser.add_argument("--logs-dir", type=Path, default=Path("/logs/verifier"))
    args = parser.parse_args(argv)
    public_path = args.public or _first_existing(
        [
            Path("/app/row_public.json"),
            Path("/tests/row_public.json"),
            Path("/workspace/row_public.json"),
            Path(__file__).resolve().parents[1] / "workspace" / "row_public.json",
            Path(__file__).resolve().parents[1] / "tests" / "row_public.json",
        ]
    )
    private_path = args.private or _first_existing(
        [
            Path("/expected/private.json"),
            Path("/tests/expected/private.json"),
            Path("/solution/expected/private.json"),
            Path(__file__).resolve().parents[1] / "expected" / "private.json",
            Path(__file__).resolve().parents[1] / "tests" / "expected" / "private.json",
        ]
    )
    if public_path is None or private_path is None:
        args.logs_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            args.logs_dir / "cadqa_grade.json",
            {
                "reward": 0,
                "harbor": {
                    "submission_status": "verifier_error",
                    "submission_error": "missing public or private row fixture",
                    "invalid_output": True,
                },
            },
        )
        (args.logs_dir / "reward.txt").write_text("0\n", encoding="utf-8")
        return 2
    grade_harbor_answer_files(
        public_path=public_path,
        private_path=private_path,
        app_dir=args.app_dir,
        logs_dir=args.logs_dir,
    )
    return 0


def _load_submission(app_dir: Path) -> dict[str, Any]:
    answer_json = app_dir / "answer.json"
    answer_txt = app_dir / "answer.txt"
    has_json = answer_json.exists()
    has_txt = answer_txt.exists()
    if has_json and has_txt:
        return {"status": "duplicate", "error": "duplicate_output_files"}
    if not has_json and not has_txt:
        return {"status": "missing", "error": "missing_answer_file"}
    if has_json:
        try:
            payload = json.loads(answer_json.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return {"status": "invalid", "error": f"invalid_answer_json:{type(exc).__name__}"}
        if not isinstance(payload, dict) or "answer" not in payload:
            return {"status": "invalid", "error": "answer_json_missing_answer"}
        confidence = payload.get("confidence")
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = None
            if confidence is not None and not math.isfinite(confidence):
                confidence = None
        answer = payload["answer"]
        return {
            "status": "ok",
            "answer": json.dumps(answer, sort_keys=True) if isinstance(answer, (dict, list)) else str(answer),
            "confidence": confidence,
        }
    return {"status": "ok", "answer": answer_txt.read_text(encoding="utf-8")}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None
