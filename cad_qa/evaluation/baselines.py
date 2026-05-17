"""Minimal baseline helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from typing import Any


def oracle_answer(row: dict[str, object]) -> object:
    return row.get("gold_answer")


def first_candidate_answer(row: dict[str, Any]) -> object:
    candidates = row.get("candidate_trace", {}).get("steps", [{}])[0].get("candidate_ids", [])
    return candidates[0] if candidates else None


def majority_answer(rows: list[dict[str, Any]]) -> object:
    counts: Counter[str] = Counter(_stable_key(row.get("gold_answer")) for row in rows)
    if not counts:
        return None
    return _unstable_key(counts.most_common(1)[0][0])


def first_static_candidate_answer(row: dict[str, Any]) -> object:
    for step in row.get("candidate_trace", {}).get("steps", []):
        before = step.get("before") or step.get("candidate_ids") or []
        after = step.get("after") or step.get("candidate_ids") or []
        if len(after) < len(before):
            return after[0] if after else None
    return first_candidate_answer(row)


def run_baselines(rows: list[dict[str, Any]]) -> dict[str, Any]:
    majority = majority_answer(rows)
    baselines = {
        "oracle": oracle_answer,
        "first_candidate": first_candidate_answer,
        "first_static_filter": first_static_candidate_answer,
        "majority": lambda row: majority,
        "null": lambda row: None,
    }
    results: dict[str, Any] = {}
    for name, fn in baselines.items():
        correct = 0
        predictions = []
        for row in rows:
            prediction = fn(row)
            predictions.append({"row_id": row["row_id"], "prediction": prediction})
            correct += int(prediction == row.get("gold_answer"))
        results[name] = {
            "accuracy": correct / len(rows) if rows else 0.0,
            "correct": correct,
            "total": len(rows),
            "by_hop": _breakdown(rows, predictions, "logical_hop_count"),
            "by_static_hop": _breakdown(rows, predictions, "static_hop_count"),
            "by_geometry_hop": _breakdown(rows, predictions, "geometry_hop_count"),
            "by_difficulty": _breakdown(rows, predictions, "difficulty_bucket"),
            "predictions": predictions,
        }
    return results


def _breakdown(rows: list[dict[str, Any]], predictions: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    predictions_by_row_id = {prediction["row_id"]: prediction.get("prediction") for prediction in predictions}
    for row in rows:
        bucket = str(row.get(key, "unknown"))
        grouped[bucket]["total"] += 1
        grouped[bucket]["correct"] += int(predictions_by_row_id.get(row["row_id"]) == row.get("gold_answer"))
    return {
        bucket: {
            "accuracy": counts["correct"] / counts["total"] if counts["total"] else 0.0,
            "correct": counts["correct"],
            "total": counts["total"],
        }
        for bucket, counts in sorted(grouped.items())
    }


def _stable_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _unstable_key(value: str) -> Any:
    return json.loads(value)
