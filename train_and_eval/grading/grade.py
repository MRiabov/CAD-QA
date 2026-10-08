"""Simple exact grading."""

from __future__ import annotations

from collections import Counter, defaultdict
import math
from typing import Any

from train_and_eval.grading.parse import parse_answer


def exact_match(gold: Any, predicted: Any) -> bool:
    return gold == predicted


def grade_responses(rows: list[dict[str, Any]], responses: list[dict[str, Any]]) -> dict[str, Any]:
    row_ids = {row["row_id"] for row in rows}
    response_by_id: dict[str, dict[str, Any]] = {}
    duplicate_response_count = 0
    extra_response_count = 0
    for response in responses:
        row_id = response.get("row_id")
        if row_id not in row_ids:
            extra_response_count += 1
        if row_id in response_by_id:
            duplicate_response_count += 1
        if row_id is not None:
            response_by_id[row_id] = response
    graded: list[dict[str, Any]] = []
    errors: Counter[str] = Counter()
    by_difficulty: dict[str, Counter[str]] = defaultdict(Counter)
    by_hop: dict[str, Counter[str]] = defaultdict(Counter)
    by_static_hop: dict[str, Counter[str]] = defaultdict(Counter)
    by_geometry_hop: dict[str, Counter[str]] = defaultdict(Counter)
    by_relation_family: dict[str, Counter[str]] = defaultdict(Counter)
    by_measurement_scope: dict[str, Counter[str]] = defaultdict(Counter)
    confidence_items: list[tuple[float, bool]] = []
    response_count = 0
    parse_error_count = 0
    correct = 0
    for row in rows:
        response = response_by_id.get(row["row_id"])
        parsed = None
        is_correct = False
        error = None
        confidence = _parse_confidence(response)
        if response is not None:
            response_count += 1
        if row.get("gold_answer") is None:
            error = row.get("_gold_error", "missing_gold_answer")
        elif response is None:
            error = "missing_response"
        else:
            raw = str(response.get("answer", response.get("response", "")))
            try:
                parsed = parse_answer(raw, row["answer_format"])
                is_correct = exact_match(row["gold_answer"], parsed)
            except Exception as exc:  # noqa: BLE001
                error = f"parse_error:{type(exc).__name__}"
                parse_error_count += 1
            if confidence is not None:
                confidence_items.append((confidence, is_correct))
        if error:
            errors[error] += 1
        correct += int(is_correct)
        key = "correct" if is_correct else "incorrect"
        by_difficulty[row["difficulty_bucket"]][key] += 1
        by_hop[str(row["logical_hop_count"])][key] += 1
        by_static_hop[str(row.get("static_hop_count", "unknown"))][key] += 1
        by_geometry_hop[str(row.get("geometry_hop_count", "unknown"))][key] += 1
        for relation_family in row.get("relation_families", []) or ["none"]:
            by_relation_family[relation_family][key] += 1
        for measurement_scope in row.get("measurement_scopes", []) or ["none"]:
            by_measurement_scope[measurement_scope][key] += 1
        graded.append(
            {
                "row_id": row["row_id"],
                "gold_answer": row["gold_answer"],
                "parsed_answer": parsed,
                "confidence": confidence,
                "correct": is_correct,
                "error": error,
            }
        )
    total = len(rows)
    missing_response_count = total - response_count
    return {
        "accuracy": correct / total if total else 0.0,
        "correct": correct,
        "total": total,
        "input_response_count": len(responses),
        "response_count": response_count,
        "extra_response_count": extra_response_count,
        "duplicate_response_count": duplicate_response_count,
        "missing_response_count": missing_response_count,
        "missing_response_rate": missing_response_count / total if total else 0.0,
        "invalid_output_count": parse_error_count,
        "invalid_output_rate": parse_error_count / response_count if response_count else 0.0,
        "calibration": _calibration_metrics(confidence_items),
        "errors": dict(errors),
        "by_difficulty": {key: _counter_metrics(value) for key, value in sorted(by_difficulty.items())},
        "by_hop": {key: _counter_metrics(value) for key, value in sorted(by_hop.items())},
        "by_static_hop": {key: _counter_metrics(value) for key, value in sorted(by_static_hop.items())},
        "by_geometry_hop": {key: _counter_metrics(value) for key, value in sorted(by_geometry_hop.items())},
        "by_relation_family": {
            key: _counter_metrics(value) for key, value in sorted(by_relation_family.items())
        },
        "by_measurement_scope": {
            key: _counter_metrics(value) for key, value in sorted(by_measurement_scope.items())
        },
        "graded": graded,
    }


def grade_public_private(
    public_rows: list[dict[str, Any]],
    private_rows: list[dict[str, Any]],
    responses: list[dict[str, Any]],
) -> dict[str, Any]:
    private_by_id = {row["row_id"]: row for row in private_rows}
    merged: list[dict[str, Any]] = []
    for public in public_rows:
        private = private_by_id.get(public["row_id"])
        if private is None:
            row = {**public, "gold_answer": None, "_gold_error": "missing_private_key"}
        else:
            row = {
                **public,
                "gold_answer": private["gold_answer"],
                "answer_format": private.get("answer_format", public["answer_format"]),
            }
        merged.append(row)
    return grade_responses(merged, responses)


def _parse_confidence(response: dict[str, Any] | None) -> float | None:
    if response is None or "confidence" not in response:
        return None
    try:
        value = float(response["confidence"])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return min(1.0, max(0.0, value))


def _calibration_metrics(items: list[tuple[float, bool]]) -> dict[str, Any] | None:
    if not items:
        return None
    buckets: list[dict[str, Any]] = []
    brier_sum = 0.0
    ece_sum = 0.0
    for index in range(5):
        lower = index / 5
        upper = (index + 1) / 5
        in_bucket = [
            (confidence, correct)
            for confidence, correct in items
            if _in_calibration_bucket(confidence, lower, upper, include_upper=index == 4)
        ]
        if not in_bucket:
            continue
        mean_confidence = sum(confidence for confidence, _ in in_bucket) / len(in_bucket)
        accuracy = sum(int(correct) for _, correct in in_bucket) / len(in_bucket)
        ece_sum += (len(in_bucket) / len(items)) * abs(accuracy - mean_confidence)
        buckets.append(
            {
                "lower": lower,
                "upper": upper,
                "count": len(in_bucket),
                "mean_confidence": mean_confidence,
                "accuracy": accuracy,
            }
        )
    for confidence, correct in items:
        brier_sum += (confidence - float(correct)) ** 2
    return {
        "count": len(items),
        "mean_confidence": sum(confidence for confidence, _ in items) / len(items),
        "accuracy": sum(int(correct) for _, correct in items) / len(items),
        "brier_score": brier_sum / len(items),
        "expected_calibration_error": ece_sum,
        "buckets": buckets,
    }


def _in_calibration_bucket(
    confidence: float,
    lower: float,
    upper: float,
    *,
    include_upper: bool,
) -> bool:
    if include_upper:
        return lower <= confidence <= upper
    return lower <= confidence < upper


def _counter_metrics(counter: Counter[str]) -> dict[str, Any]:
    total = counter["correct"] + counter["incorrect"]
    return {
        "accuracy": counter["correct"] / total if total else 0.0,
        "correct": counter["correct"],
        "total": total,
    }
