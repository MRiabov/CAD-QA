"""Deterministic descriptor scheduling for trace probes and public rows."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import random
from typing import Any, Callable

from cad_qa.hashing import sha256_json


Descriptor = dict[str, Any]
Labeler = Callable[[Descriptor], Any | None]


@dataclass(frozen=True)
class ScheduleResult:
    selected_descriptors: list[Descriptor]
    labeled_payloads: list[Any]
    manifest: dict[str, Any]


def schedule_descriptors(
    descriptors: list[Descriptor],
    *,
    seed: int,
    max_per_source: int,
    max_per_task_type: int,
    scope: str,
) -> ScheduleResult:
    """Select descriptors with deterministic bucket-balanced sampling."""

    selected = _scheduled_descriptor_attempts(
        descriptors,
        seed=seed,
        max_per_source=max_per_source,
        max_per_task_type=max_per_task_type,
        scope=scope,
    )
    manifest = _base_manifest(descriptors)
    _increment_manifest_counter(
        manifest, "scheduled_label_counts_by_task_type", selected
    )
    _increment_manifest_counter(manifest, "label_success_counts_by_task_type", selected)
    return ScheduleResult(
        selected_descriptors=selected,
        labeled_payloads=[descriptor.get("payload") for descriptor in selected],
        manifest=manifest,
    )


def schedule_and_label_descriptors(
    descriptors: list[Descriptor],
    *,
    labeler: Labeler,
    seed: int,
    max_per_source: int,
    max_per_task_type: int,
    scope: str,
) -> ScheduleResult:
    """Schedule descriptors and evaluate them, backfilling failed labels."""

    attempts = _scheduled_descriptor_attempts(
        descriptors,
        seed=seed,
        max_per_source=len(descriptors),
        max_per_task_type=len(descriptors),
        scope=scope,
    )
    manifest = _base_manifest(descriptors)
    selected: list[Descriptor] = []
    payloads: list[Any] = []
    failures: list[dict[str, Any]] = []
    success_by_task: Counter[str] = Counter()

    for descriptor in attempts:
        if len(selected) >= max_per_source:
            break
        task_type = _task_type(descriptor)
        if success_by_task[task_type] >= max_per_task_type:
            continue
        _increment_count(manifest, "scheduled_label_counts_by_task_type", task_type)
        try:
            payload = labeler(descriptor)
        except Exception as exc:  # pragma: no cover - defensive boundary
            payload = None
            failure_reason = f"labeler_error:{type(exc).__name__}"
        else:
            failure_reason = _failure_reason(payload)
        if payload is None:
            _increment_count(manifest, "label_failure_counts_by_task_type", task_type)
            failures.append(
                {
                    "descriptor_id": descriptor.get("descriptor_id"),
                    "task_type": task_type,
                    "stratum": _stratum(descriptor),
                    "failure_reason": failure_reason or "label_failed",
                }
            )
            continue
        selected.append(descriptor)
        payloads.append(payload)
        success_by_task[task_type] += 1
        _increment_count(manifest, "label_success_counts_by_task_type", task_type)

    manifest["label_failures"] = failures
    return ScheduleResult(
        selected_descriptors=selected,
        labeled_payloads=payloads,
        manifest=manifest,
    )


def exported_row_manifest(
    descriptors: list[Descriptor], selected: list[Descriptor]
) -> dict[str, Any]:
    manifest = _base_manifest(descriptors)
    _increment_manifest_counter(
        manifest, "scheduled_label_counts_by_task_type", selected
    )
    _increment_manifest_counter(manifest, "label_success_counts_by_task_type", selected)
    _increment_manifest_counter(manifest, "exported_row_counts_by_task_type", selected)
    return manifest


def merge_manifests(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "descriptor_counts_by_task_type",
        "scheduled_label_counts_by_task_type",
        "label_success_counts_by_task_type",
        "label_failure_counts_by_task_type",
        "exported_row_counts_by_task_type",
    )
    merged: dict[str, Any] = {key: {} for key in keys}
    failures: list[dict[str, Any]] = []
    for manifest in manifests:
        for key in keys:
            for task_type, count in dict(manifest.get(key) or {}).items():
                merged[key][str(task_type)] = merged[key].get(str(task_type), 0) + int(
                    count
                )
        failures.extend(list(manifest.get("label_failures") or []))
    if failures:
        merged["label_failures"] = failures
    return merged


def _scheduled_descriptor_attempts(
    descriptors: list[Descriptor],
    *,
    seed: int,
    max_per_source: int,
    max_per_task_type: int,
    scope: str,
) -> list[Descriptor]:
    if max_per_source <= 0 or max_per_task_type <= 0:
        return []
    rng = _rng(seed, scope)
    buckets: dict[tuple[str, str], list[Descriptor]] = defaultdict(list)
    for descriptor in descriptors:
        buckets[(_task_type(descriptor), _stratum(descriptor))].append(descriptor)
    bucket_keys = sorted(buckets)
    selected: list[Descriptor] = []
    selected_by_task: Counter[str] = Counter()
    cursor = 0

    while bucket_keys and len(selected) < max_per_source:
        key = bucket_keys[cursor % len(bucket_keys)]
        bucket = buckets[key]
        task_type = key[0]
        if selected_by_task[task_type] >= max_per_task_type:
            bucket_keys = [item for item in bucket_keys if item[0] != task_type]
            if not bucket_keys:
                break
            cursor %= len(bucket_keys)
            continue
        if not bucket:
            bucket_keys.pop(cursor % len(bucket_keys))
            if not bucket_keys:
                break
            cursor %= len(bucket_keys)
            continue
        descriptor = bucket.pop(rng.randrange(len(bucket)))
        selected.append(descriptor)
        selected_by_task[task_type] += 1
        cursor += 1
    return selected


def _base_manifest(descriptors: list[Descriptor]) -> dict[str, Any]:
    return {
        "descriptor_counts_by_task_type": dict(
            Counter(_task_type(descriptor) for descriptor in descriptors)
        ),
        "scheduled_label_counts_by_task_type": {},
        "label_success_counts_by_task_type": {},
        "label_failure_counts_by_task_type": {},
        "exported_row_counts_by_task_type": {},
    }


def _increment_manifest_counter(
    manifest: dict[str, Any], key: str, descriptors: list[Descriptor]
) -> None:
    for task_type, count in Counter(_task_type(item) for item in descriptors).items():
        manifest[key][task_type] = manifest[key].get(task_type, 0) + count


def _increment_count(manifest: dict[str, Any], key: str, task_type: str) -> None:
    manifest[key][task_type] = manifest[key].get(task_type, 0) + 1


def _rng(seed: int, scope: str) -> random.Random:
    digest = sha256_json({"seed": seed, "scope": scope}).removeprefix("sha256:")
    return random.Random(int(digest[:16], 16))


def _task_type(descriptor: Descriptor) -> str:
    return str(descriptor.get("task_type") or "unknown")


def _stratum(descriptor: Descriptor) -> str:
    return str(descriptor.get("stratum") or "default")


def _failure_reason(payload: Any | None) -> str | None:
    if payload is None:
        return "label_failed"
    if isinstance(payload, dict):
        status = payload.get("status")
        if isinstance(status, str) and status != "ok":
            return status
    return None
