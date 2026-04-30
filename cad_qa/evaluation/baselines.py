"""Minimal baseline helpers."""

from __future__ import annotations

from typing import Any


def oracle_answer(row: dict[str, object]) -> object:
    return row.get("gold_answer")


def first_candidate_answer(row: dict[str, Any]) -> object:
    candidates = row.get("candidate_trace", {}).get("steps", [{}])[0].get("candidate_ids", [])
    return candidates[0] if candidates else None


def run_baselines(rows: list[dict[str, Any]]) -> dict[str, Any]:
    baselines = {
        "oracle": oracle_answer,
        "first_candidate": first_candidate_answer,
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
            "predictions": predictions,
        }
    return results
