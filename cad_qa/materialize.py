"""Public task-row materialization from source and trace metadata."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any

from cad_qa.config import DatasetConfig
from cad_qa.hashing import sha256_json
from cad_qa.operation_graph import operation_signature_hash
from cad_qa.schema import OperationNode, PublicTaskRow, SourceRecord, TraceRecord

def materialize_rows(
    source: SourceRecord,
    trace: TraceRecord,
    *,
    config: DatasetConfig,
) -> list[PublicTaskRow]:
    nodes = [_node_from_dict(item) for item in trace.operation_nodes]
    rows: list[PublicTaskRow] = []
    rows.extend(_operation_count_rows(source, trace, nodes, config=config))
    rows.extend(_snapshot_rows(source, trace, config=config))
    rows.extend(_selector_rows(source, trace, config=config))
    rows.extend(_point_rows(source, trace, config=config))
    rows.extend(_provenance_rows(source, trace, nodes, config=config))
    return rows


def _operation_count_rows(
    source: SourceRecord,
    trace: TraceRecord,
    nodes: list[OperationNode],
    *,
    config: DatasetConfig,
) -> list[PublicTaskRow]:
    counts = Counter(node.operation for node in nodes if node.status == "ok")
    operations = sorted(set(counts) | {"extrude", "cut", "box", "hole", "fillet"})
    rows: list[PublicTaskRow] = []
    for operation in operations:
        answer = counts.get(operation, 0)
        labels = {"operation": operation, "operation_count": answer, "answer_status": "ok", "failure_reason": None}
        rows.append(
            _row(
                source,
                trace,
                config=config,
                task_type="operation_count",
                target_feature_id=None,
                prompt=(
                    "Given the CadQuery script below, count the normalized CadQuery "
                    f"operations named `{operation}`. Answer with exactly one non-negative integer.\n\n"
                    f"```python\n{source.normalized_code}```"
                ),
                answer_type="integer",
                answer=answer,
                choices=None,
                unit=None,
                numeric_tolerance=None,
                requires=["cadquery_syntax", "operation_graph"],
                difficulty_tags=["static_code"],
                labels=labels,
                diagnostics={"answer_status": "ok", "failure_reason": None},
                parse_policy="strict_integer_v1",
            )
        )
    return rows


def _snapshot_rows(source: SourceRecord, trace: TraceRecord, *, config: DatasetConfig) -> list[PublicTaskRow]:
    rows: list[PublicTaskRow] = []
    snapshots = sorted(trace.snapshots, key=lambda item: int(item.get("step_index", 0)))
    previous_by_index: dict[int, dict[str, Any]] = {}
    for snapshot in snapshots:
        index = int(snapshot.get("step_index", 0))
        previous = snapshots[index - 1] if index > 0 and index - 1 < len(snapshots) else None
        previous_by_index[index] = previous or {}
        feature_id = str(snapshot.get("feature_id"))
        if snapshot.get("bbox") is not None:
            rows.append(
                _row(
                    source,
                    trace,
                    config=config,
                    task_type="bbox_after_step",
                    target_feature_id=feature_id,
                    prompt=(
                        "Given the CadQuery script below, what is the world-coordinate axis-aligned "
                        f"bounding box after feature `{feature_id}`? Answer as JSON with `min` and `max` arrays.\n\n"
                        f"```python\n{source.normalized_code}```"
                    ),
                    answer_type="bbox",
                    answer=snapshot["bbox"],
                    choices=None,
                    unit="mm",
                    numeric_tolerance=config.label_policy.bbox_tolerance_mm,
                    requires=["cadquery_syntax", "bbox_reasoning"],
                    difficulty_tags=["symbolic_arithmetic"],
                    labels={"bbox_after": snapshot["bbox"], "answer_status": "ok", "failure_reason": None},
                    diagnostics={"answer_status": "ok", "failure_reason": None, "snapshot_id": snapshot.get("snapshot_id")},
                    parse_policy="strict_json_bbox_v1",
                )
            )
        if snapshot.get("volume") is not None and previous and previous.get("volume") is not None:
            before = float(previous["volume"])
            after = float(snapshot["volume"])
            delta = after - before
            rows.append(
                _row(
                    source,
                    trace,
                    config=config,
                    task_type="signed_volume_delta",
                    target_feature_id=feature_id,
                    prompt=(
                        "Given the CadQuery script below, what is the signed volume delta caused by "
                        f"feature `{feature_id}`? Positive adds material and negative removes material. "
                        "Answer with exactly one finite number.\n\n"
                        f"```python\n{source.normalized_code}```"
                    ),
                    answer_type="number",
                    answer=delta,
                    choices=None,
                    unit="mm^3",
                    numeric_tolerance=config.label_policy.volume_tolerance_abs_mm3,
                    requires=["cadquery_syntax", "volume_delta"],
                    difficulty_tags=_volume_tags(delta),
                    labels={
                        "volume_before": before,
                        "volume_after": after,
                        "signed_volume_delta": delta,
                        "answer_status": "ok",
                        "failure_reason": None,
                    },
                    diagnostics={"answer_status": "ok", "failure_reason": None, "snapshot_id": snapshot.get("snapshot_id")},
                    parse_policy="numeric_4_sigfig_v1",
                )
            )
        topology = snapshot.get("topology")
        if isinstance(topology, dict):
            for key in ("solid_count", "face_count", "edge_count", "vertex_count", "wire_count"):
                value = topology.get(key)
                if isinstance(value, int) and value >= 0:
                    rows.append(
                        _row(
                            source,
                            trace,
                            config=config,
                            task_type="topology_count_after_step",
                            target_feature_id=feature_id,
                            prompt=(
                                "Given the CadQuery script below, what is the "
                                f"`{key}` after feature `{feature_id}`? Answer with exactly one non-negative integer.\n\n"
                                f"```python\n{source.normalized_code}```"
                            ),
                            answer_type="integer",
                            answer=value,
                            choices=None,
                            unit=None,
                            numeric_tolerance=None,
                            requires=["cadquery_syntax", "topology_count"],
                            difficulty_tags=["topology_count"],
                            labels={"topology_after": topology, "topology_key": key, "answer_status": "ok", "failure_reason": None},
                            diagnostics={"answer_status": "ok", "failure_reason": None, "snapshot_id": snapshot.get("snapshot_id")},
                            parse_policy="strict_integer_v1",
                        )
                    )
    return rows


def _selector_rows(source: SourceRecord, trace: TraceRecord, *, config: DatasetConfig) -> list[PublicTaskRow]:
    rows: list[PublicTaskRow] = []
    for table in trace.selector_tables:
        count = table.get("selected_count")
        if not isinstance(count, int) or count < 0:
            continue
        target = table.get("target_feature_id")
        rows.append(
            _row(
                source,
                trace,
                config=config,
                task_type="selector_count",
                target_feature_id=str(target) if target else None,
                prompt=(
                    "Given the CadQuery script below, how many entities are selected by "
                    f"`{table.get('selector_expression')}`? Answer with exactly one non-negative integer.\n\n"
                    f"```python\n{source.normalized_code}```"
                ),
                answer_type="integer",
                answer=count,
                choices=None,
                unit=None,
                numeric_tolerance=None,
                requires=["cadquery_syntax", "selector_semantics"],
                difficulty_tags=["selector_semantics"],
                labels={"selector_result": table, "answer_status": "ok", "failure_reason": None},
                diagnostics={"answer_status": "ok", "failure_reason": None},
                parse_policy="strict_integer_v1",
            )
        )
    return rows


def _point_rows(source: SourceRecord, trace: TraceRecord, *, config: DatasetConfig) -> list[PublicTaskRow]:
    rows: list[PublicTaskRow] = []
    for query in trace.point_queries:
        answer = query.get("point_classification")
        if answer not in {"inside", "outside", "on_boundary", "ambiguous"}:
            continue
        point = query.get("point")
        target = query.get("target_feature_id")
        rows.append(
            _row(
                source,
                trace,
                config=config,
                task_type="point_membership",
                target_feature_id=str(target) if target else None,
                prompt=(
                    "Given the CadQuery script below, classify point "
                    f"`{point}` as one of inside, outside, on_boundary, or ambiguous at the target state. "
                    "Answer with exactly one allowed token.\n\n"
                    f"```python\n{source.normalized_code}```"
                ),
                answer_type="enum",
                answer=answer,
                choices=["inside", "outside", "on_boundary", "ambiguous"],
                unit=None,
                numeric_tolerance=None,
                requires=["cadquery_syntax", "point_membership"],
                difficulty_tags=["point_membership"],
                labels={"point_query": query, "answer_status": "ok", "failure_reason": None},
                diagnostics={"answer_status": "ok", "failure_reason": None},
                parse_policy="strict_enum_v1",
            )
        )
    return rows


def _provenance_rows(
    source: SourceRecord,
    trace: TraceRecord,
    nodes: list[OperationNode],
    *,
    config: DatasetConfig,
) -> list[PublicTaskRow]:
    rows: list[PublicTaskRow] = []
    feature_choices = [node.feature_id for node in nodes if node.status == "ok"]
    for record in trace.provenance_records:
        answer = record.get("answer_feature_id") or record.get("feature_id")
        relation = record.get("provenance_relation")
        if relation == "ambiguous_or_merged":
            answer = "ambiguous_or_merged"
        if not isinstance(answer, str):
            continue
        choices = [*feature_choices, "ambiguous_or_merged"]
        if answer not in choices:
            continue
        rows.append(
            _row(
                source,
                trace,
                config=config,
                task_type="feature_provenance_choice",
                target_feature_id=record.get("target_feature_id"),
                prompt=(
                    "Given the CadQuery script below and the described target, choose the feature ID "
                    "that best matches the recorded provenance, or answer ambiguous_or_merged. "
                    f"Target: {record.get('target_description', 'unspecified')}.\n\n"
                    f"Choices: {', '.join(choices)}\n\n"
                    f"```python\n{source.normalized_code}```"
                ),
                answer_type="choice",
                answer=answer,
                choices=choices,
                unit=None,
                numeric_tolerance=None,
                requires=["cadquery_syntax", "feature_provenance"],
                difficulty_tags=["feature_provenance"],
                labels={"provenance": record, "answer_status": "ok", "failure_reason": None},
                diagnostics={"answer_status": "ok", "failure_reason": None},
                parse_policy="strict_enum_v1",
            )
        )
    return rows


def _row(
    source: SourceRecord,
    trace: TraceRecord,
    *,
    config: DatasetConfig,
    task_type: str,
    target_feature_id: str | None,
    prompt: str,
    answer_type: str,
    answer: Any,
    choices: list[str] | None,
    unit: str | None,
    numeric_tolerance: float | None,
    requires: list[str],
    difficulty_tags: list[str],
    labels: dict[str, Any],
    diagnostics: dict[str, Any],
    parse_policy: str,
) -> PublicTaskRow:
    prompt_hash = sha256_json({"task_type": task_type, "target": target_feature_id, "prompt": prompt})
    provenance = _provenance(source, trace)
    row_payload = {
        "dataset_version": config.dataset_version,
        "task_type": task_type,
        "source_id": source.source_id,
        "trace_id": trace.trace_id,
        "target_feature_id": target_feature_id,
        "answer": answer,
        "prompt_hash": prompt_hash,
    }
    return PublicTaskRow(
        id="cadqa_" + task_type + "_" + sha256_json(row_payload).removeprefix("sha256:")[:16],
        dataset_version=config.dataset_version,
        task_type=task_type,
        source_id=source.source_id,
        trace_id=trace.trace_id,
        target_feature_id=target_feature_id,
        split="train",
        prompt=prompt,
        answer_type=answer_type,
        answer=answer,
        choices=choices,
        unit=unit,
        numeric_tolerance=numeric_tolerance,
        requires=requires,
        difficulty_tags=difficulty_tags,
        labels=labels,
        diagnostics=diagnostics,
        provenance=provenance,
        hashes={**trace.hashes, "prompt_hash": prompt_hash},
        parse_policy=parse_policy,
    )


def _provenance(source: SourceRecord, trace: TraceRecord) -> dict[str, Any]:
    nodes = [_node_from_dict(item) for item in trace.operation_nodes]
    op_sig = operation_signature_hash(nodes)
    return {
        "source": source.source,
        "source_id": source.source_id,
        "generator_id": source.generator_id,
        "source_subtree": source.source_subtree,
        "normalized_archive_member_path": source.normalized_archive_member_path,
        "normalized_source_code_hash": source.hashes.get("normalized_source_code_hash"),
        "operation_signature_hash": op_sig,
        "topology_signature_hash": _topology_signature_hash(trace),
        "counterfactual_group_id": None,
        "point_sampling_group_id": None,
    }


def _topology_signature_hash(trace: TraceRecord) -> str | None:
    if not trace.snapshots:
        return None
    topology = trace.snapshots[-1].get("topology")
    if not isinstance(topology, dict):
        return None
    return sha256_json(topology)


def _node_from_dict(item: dict[str, Any]) -> OperationNode:
    return OperationNode(
        feature_id=str(item["feature_id"]),
        step_index=int(item["step_index"]),
        source_line=item.get("source_line"),
        target=item.get("target"),
        base=item.get("base"),
        operation=str(item["operation"]),
        args_repr=list(item.get("args_repr") or []),
        input_features=list(item.get("input_features") or []),
        status=str(item.get("status", "ok")),
    )


def _volume_tags(delta: float) -> list[str]:
    if delta < 0:
        return ["boolean_cut"]
    if delta > 0:
        return ["symbolic_arithmetic"]
    return ["kernel_sensitive"]


def rows_to_dicts(rows: list[PublicTaskRow]) -> list[dict[str, Any]]:
    return [asdict(row) for row in rows]
