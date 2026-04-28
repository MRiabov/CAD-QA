"""Bounded verifier rewards for CAD-QA candidate completions."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from cad_qa.parse import grade_candidate


def score_candidate(row: dict[str, Any], candidate: str) -> dict[str, Any]:
    """Score one candidate with parser-backed verifier rewards."""

    grade = grade_candidate(row, candidate)
    if not grade["valid"]:
        reward = -1.0
        reason = "parse_failure"
    elif grade["correct"]:
        reward = 1.0
        reason = "verifier_pass"
    else:
        reward = -0.25
        reason = "verifier_fail"
    return {
        "reward": reward,
        "reward_reason": reason,
        "valid": bool(grade["valid"]),
        "correct": bool(grade["correct"]),
        "parsed": grade.get("parsed"),
        "error": grade.get("error"),
    }


def score_candidate_records(
    rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    max_candidates_per_row: int = 16,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Score bounded candidate records and return scored rows plus summary."""

    rows_by_id = {str(row["id"]): row for row in rows}
    seen_by_row: dict[str, int] = defaultdict(int)
    scored: list[dict[str, Any]] = []
    skipped = Counter()
    for index, record in enumerate(candidates):
        row_id = _row_id(record)
        if row_id is None:
            skipped["missing_row_id"] += 1
            continue
        row = rows_by_id.get(row_id)
        if row is None:
            skipped["unknown_row_id"] += 1
            continue
        if seen_by_row[row_id] >= max_candidates_per_row:
            skipped["max_candidates_per_row"] += 1
            continue
        seen_by_row[row_id] += 1
        candidate = _candidate_text(record)
        score = score_candidate(row, candidate)
        scored.append(
            {
                "row_id": row_id,
                "candidate_id": str(record.get("candidate_id") or f"{row_id}:{seen_by_row[row_id] - 1}"),
                "candidate": candidate,
                "rank_input": index,
                "task_type": row.get("task_type"),
                "split": row.get("split"),
                **score,
            }
        )
    selected = select_best_candidates(scored)
    report = reward_report(rows, scored, selected, skipped=dict(skipped), max_candidates_per_row=max_candidates_per_row)
    return scored, report


def select_best_candidates(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_row: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in scored:
        by_row[str(item["row_id"])].append(item)
    selected = []
    for row_id, items in sorted(by_row.items()):
        best = max(items, key=lambda item: (float(item["reward"]), bool(item["valid"]), -int(item["rank_input"])))
        selected.append({**best, "selection": "best_of_candidates"})
    return selected


def reward_report(
    rows: list[dict[str, Any]],
    scored: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    *,
    skipped: dict[str, int],
    max_candidates_per_row: int,
) -> dict[str, Any]:
    row_ids = {str(row["id"]) for row in rows}
    scored_row_ids = {str(item["row_id"]) for item in scored}
    selected_row_ids = {str(item["row_id"]) for item in selected}
    return {
        "schema": "cadqa_rejection_sampling_reward_report_v1",
        "row_count": len(rows),
        "candidate_count": len(scored),
        "selected_count": len(selected),
        "coverage": len(scored_row_ids) / len(row_ids) if row_ids else 0.0,
        "selected_coverage": len(selected_row_ids) / len(row_ids) if row_ids else 0.0,
        "candidate_accuracy": _rate(scored, "correct"),
        "candidate_valid_rate": _rate(scored, "valid"),
        "selected_accuracy": _rate(selected, "correct"),
        "selected_valid_rate": _rate(selected, "valid"),
        "mean_candidate_reward": _mean_reward(scored),
        "mean_selected_reward": _mean_reward(selected),
        "skipped": skipped,
        "max_candidates_per_row": max_candidates_per_row,
        "by_task_type": _group_report(selected, "task_type"),
        "by_split": _group_report(selected, "split"),
    }


def _group_report(items: list[dict[str, Any]], field: str) -> dict[str, dict[str, float | int]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        groups[str(item.get(field))].append(item)
    return {
        group: {
            "row_count": len(group_items),
            "accuracy": _rate(group_items, "correct"),
            "valid_rate": _rate(group_items, "valid"),
            "mean_reward": _mean_reward(group_items),
        }
        for group, group_items in sorted(groups.items())
    }


def _rate(items: list[dict[str, Any]], field: str) -> float:
    return sum(1 for item in items if item.get(field)) / len(items) if items else 0.0


def _mean_reward(items: list[dict[str, Any]]) -> float:
    return sum(float(item.get("reward", 0.0)) for item in items) / len(items) if items else 0.0


def _row_id(record: dict[str, Any]) -> str | None:
    for key in ("row_id", "id", "custom_id"):
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _candidate_text(record: dict[str, Any]) -> str:
    for key in ("candidate", "prediction", "answer", "completion", "text", "output_text"):
        value = record.get(key)
        if value is not None:
            return str(value)
    return ""
