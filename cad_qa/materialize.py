"""Public task-row materialization from source and trace metadata."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json
import math
from typing import Any

from cad_qa.config import DatasetConfig
from cad_qa.graph_query import (
    build_typed_query_graph,
    default_graph_query_irs,
    graph_query_prompt,
    resolve_graph_query,
)
from cad_qa.hashing import sha256_json
from cad_qa.operation_graph import operation_signature_hash
from cad_qa.scheduler import exported_row_manifest, schedule_descriptors
from cad_qa.schema import OperationNode, PublicTaskRow, SourceRecord, TraceRecord

POINT_MEMBERSHIP_CHOICES = ["inside", "outside", "on_boundary"]


def materialize_rows(
    source: SourceRecord,
    trace: TraceRecord,
    *,
    config: DatasetConfig,
) -> list[PublicTaskRow]:
    rows, _ = materialize_rows_with_manifest(source, trace, config=config)
    return rows


def materialize_rows_with_manifest(
    source: SourceRecord,
    trace: TraceRecord,
    *,
    config: DatasetConfig,
) -> tuple[list[PublicTaskRow], dict[str, Any]]:
    row_descriptors = _public_row_descriptors(
        _materialize_all_rows(source, trace, config=config)
    )
    scheduled = schedule_descriptors(
        row_descriptors,
        seed=config.seed,
        max_per_source=config.max_rows_per_source,
        max_per_task_type=config.max_rows_per_source_task_type,
        scope=f"public_rows:{source.source_id}:{trace.trace_id}",
    )
    kept_descriptors = _dedupe_scheduled_public_row_descriptors(
        scheduled.selected_descriptors
    )
    selected_rows = [descriptor["payload"] for descriptor in kept_descriptors]
    return selected_rows, exported_row_manifest(row_descriptors, kept_descriptors)


def _materialize_all_rows(
    source: SourceRecord,
    trace: TraceRecord,
    *,
    config: DatasetConfig,
) -> list[PublicTaskRow]:
    nodes = [_node_from_dict(item) for item in trace.operation_nodes]
    rows: list[PublicTaskRow] = []
    rows.extend(_operation_count_rows(source, trace, nodes, config=config))
    rows.extend(_workplane_rows(source, trace, nodes, config=config))
    rows.extend(_snapshot_rows(source, trace, config=config))
    rows.extend(_selector_rows(source, trace, config=config))
    rows.extend(_point_rows(source, trace, config=config))
    rows.extend(_provenance_rows(source, trace, nodes, config=config))
    rows.extend(_graph_query_rows(source, trace, nodes, config=config))
    rows.extend(_spatial_distance_rows(source, trace, config=config))
    rows.extend(_bbox_region_rows(source, trace, config=config))
    rows.extend(_validity_failure_rows(source, trace, config=config))
    return rows


def _public_row_descriptors(rows: list[PublicTaskRow]) -> list[dict[str, Any]]:
    descriptors: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        descriptors.append(
            {
                "descriptor_id": f"public_row_{index}_{row.id}",
                "task_type": row.task_type,
                "stratum": _row_scheduling_stratum(row),
                "target_feature_id": row.target_feature_id,
                "label_cost": 1,
                "payload": row,
                "row_index": index,
            }
        )
    return descriptors


def _dedupe_scheduled_public_row_descriptors(
    descriptors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    seen_row_ids: set[str] = set()
    for descriptor in descriptors:
        row = descriptor.get("payload")
        row_id = getattr(row, "id", None)
        if not isinstance(row_id, str) or not row_id:
            kept.append(descriptor)
            continue
        if row_id in seen_row_ids:
            continue
        seen_row_ids.add(row_id)
        kept.append(descriptor)
    return kept


def _row_scheduling_stratum(row: PublicTaskRow) -> str:
    if row.task_type == "graph_query":
        ir = row.labels.get("graph_query", {}).get("ir", {})
        if isinstance(ir, dict):
            return str(ir.get("query_type") or ir.get("query_id") or "graph_query")
    if row.task_type == "selector_count":
        selector = row.labels.get("selector_result", {})
        if isinstance(selector, dict):
            return str(selector.get("selector_origin") or "source")
    if row.task_type == "point_membership":
        query = row.labels.get("point_query", {})
        if isinstance(query, dict):
            return str(query.get("sampling_stratum") or query.get("sample_source"))
    if row.difficulty_tags:
        return str(row.difficulty_tags[0])
    return row.task_type


def _workplane_rows(
    source: SourceRecord,
    trace: TraceRecord,
    nodes: list[OperationNode],
    *,
    config: DatasetConfig,
) -> list[PublicTaskRow]:
    rows: list[PublicTaskRow] = []
    for node in nodes:
        if node.status != "ok" or node.operation not in {"Workplane", "workplane"}:
            continue
        frame = _coordinate_frame(node)
        choices = [
            "XY",
            "YZ",
            "XZ",
            "front",
            "back",
            "left",
            "right",
            "top",
            "bottom",
            "inherited",
            "unknown",
        ]
        if frame not in choices:
            choices.append(frame)
        rows.append(
            _row(
                source,
                trace,
                config=config,
                task_type="coordinate_frame",
                target_feature_id=node.feature_id,
                prompt=(
                    "Given the CadQuery script below, what coordinate frame or workplane name is established "
                    f"by feature `{node.feature_id}`? Answer with exactly one listed token.\n\n"
                    f"Choices: {', '.join(choices)}\n\n"
                    f"```python\n{source.normalized_code}```"
                ),
                answer_type="enum",
                answer=frame,
                choices=choices,
                unit=None,
                numeric_tolerance=None,
                requires=["cadquery_syntax", "workplane_reasoning"],
                difficulty_tags=["coordinate_frame"],
                labels={
                    "operation_node": asdict(node),
                    "coordinate_frame": frame,
                    "answer_status": "ok",
                    "failure_reason": None,
                },
                diagnostics={"answer_status": "ok", "failure_reason": None},
                parse_policy="strict_enum_v1",
            )
        )
        state = {
            "feature_id": node.feature_id,
            "operation": node.operation,
            "base": node.base,
            "coordinate_frame": frame,
        }
        rows.append(
            _row(
                source,
                trace,
                config=config,
                task_type="workplane_state",
                target_feature_id=node.feature_id,
                prompt=(
                    "Given the CadQuery script below, return the workplane state for "
                    f"feature `{node.feature_id}` as JSON with keys feature_id, operation, base, and coordinate_frame.\n\n"
                    f"```python\n{source.normalized_code}```"
                ),
                answer_type="json",
                answer=state,
                choices=None,
                unit=None,
                numeric_tolerance=None,
                requires=["cadquery_syntax", "workplane_reasoning"],
                difficulty_tags=["workplane_state"],
                labels={
                    "operation_node": asdict(node),
                    "workplane_state": state,
                    "answer_status": "ok",
                    "failure_reason": None,
                },
                diagnostics={"answer_status": "ok", "failure_reason": None},
                parse_policy="strict_json_v1",
            )
        )
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
        labels = {
            "operation": operation,
            "operation_count": answer,
            "answer_status": "ok",
            "failure_reason": None,
        }
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


def _snapshot_rows(
    source: SourceRecord, trace: TraceRecord, *, config: DatasetConfig
) -> list[PublicTaskRow]:
    rows: list[PublicTaskRow] = []
    snapshots = sorted(trace.snapshots, key=lambda item: int(item.get("step_index", 0)))
    for position, snapshot in enumerate(snapshots):
        previous = snapshots[position - 1] if position > 0 else None
        feature_id = str(snapshot.get("feature_id"))
        if snapshot.get("bbox") is not None:
            answer_bbox = _round_bbox(snapshot["bbox"])
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
                    answer=answer_bbox,
                    choices=None,
                    unit="mm",
                    numeric_tolerance=config.label_policy.bbox_tolerance_mm,
                    requires=["cadquery_syntax", "bbox_reasoning"],
                    difficulty_tags=["symbolic_arithmetic"],
                    labels={
                        "bbox_after": snapshot["bbox"],
                        "answer_status": "ok",
                        "failure_reason": None,
                    },
                    diagnostics={
                        "answer_status": "ok",
                        "failure_reason": None,
                        "snapshot_id": snapshot.get("snapshot_id"),
                    },
                    parse_policy="strict_json_bbox_v1",
                )
            )
        if snapshot.get("volume") is not None and (
            previous is None or previous.get("volume") is not None
        ):
            before = 0.0 if previous is None else float(previous["volume"])
            after = float(snapshot["volume"])
            delta = after - before
            answer_delta = _round_sigfig_number(delta)
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
                    answer=answer_delta,
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
                    diagnostics={
                        "answer_status": "ok",
                        "failure_reason": None,
                        "snapshot_id": snapshot.get("snapshot_id"),
                    },
                    parse_policy="numeric_4_sigfig_v1",
                )
            )
        topology = snapshot.get("topology")
        if isinstance(topology, dict):
            for key in (
                "solid_count",
                "face_count",
                "edge_count",
                "vertex_count",
                "wire_count",
            ):
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
                            labels={
                                "topology_after": topology,
                                "topology_key": key,
                                "answer_status": "ok",
                                "failure_reason": None,
                            },
                            diagnostics={
                                "answer_status": "ok",
                                "failure_reason": None,
                                "snapshot_id": snapshot.get("snapshot_id"),
                            },
                            parse_policy="strict_integer_v1",
                        )
                    )
    return rows


def _selector_rows(
    source: SourceRecord, trace: TraceRecord, *, config: DatasetConfig
) -> list[PublicTaskRow]:
    rows: list[PublicTaskRow] = []
    for table in trace.selector_tables:
        count = table.get("selected_count")
        if not isinstance(count, int) or count < 0:
            continue
        target = table.get("target_feature_id")
        origin = str(table.get("selector_origin") or "source")
        selector_expression = table.get("selector_expression")
        if origin == "generated" and target:
            selector_question = (
                "Given the CadQuery script below, if selector "
                f"`{selector_expression}` were evaluated after feature `{target}`, "
                "how many entities would it select?"
            )
        else:
            selector_question = (
                "Given the CadQuery script below, how many entities are selected by "
                f"`{selector_expression}`?"
            )
        rows.append(
            _row(
                source,
                trace,
                config=config,
                task_type="selector_count",
                target_feature_id=str(target) if target else None,
                prompt=(
                    f"{selector_question} Answer with exactly one non-negative integer.\n\n"
                    f"```python\n{source.normalized_code}```"
                ),
                answer_type="integer",
                answer=count,
                choices=None,
                unit=None,
                numeric_tolerance=None,
                requires=["cadquery_syntax", "selector_semantics"],
                difficulty_tags=[
                    "selector_semantics",
                    "hypothetical_selector" if origin == "generated" else "source_selector",
                ],
                labels={
                    "selector_result": table,
                    "answer_status": "ok",
                    "failure_reason": None,
                },
                diagnostics={"answer_status": "ok", "failure_reason": None},
                parse_policy="strict_integer_v1",
            )
        )
    return rows


def _point_rows(
    source: SourceRecord, trace: TraceRecord, *, config: DatasetConfig
) -> list[PublicTaskRow]:
    rows: list[PublicTaskRow] = []
    for query in trace.point_queries:
        answer = query.get("point_classification")
        if answer not in POINT_MEMBERSHIP_CHOICES:
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
                    f"`{point}` as one of inside, outside, or on_boundary at the target state. "
                    "Answer with exactly one allowed token.\n\n"
                    f"```python\n{source.normalized_code}```"
                ),
                answer_type="enum",
                answer=answer,
                choices=POINT_MEMBERSHIP_CHOICES,
                unit=None,
                numeric_tolerance=None,
                requires=["cadquery_syntax", "point_membership"],
                difficulty_tags=_point_membership_tags(query, str(answer)),
                labels={
                    "point_query": query,
                    "answer_status": "ok",
                    "failure_reason": None,
                },
                diagnostics={"answer_status": "ok", "failure_reason": None},
                parse_policy="strict_enum_v1",
                provenance_overrides={
                    "point_sampling_group_id": _point_sampling_group_id(
                        source, query, str(answer)
                    )
                },
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
        answer = (
            record.get("first_contributor_feature_id")
            or record.get("answer_feature_id")
            or record.get("feature_id")
        )
        if not isinstance(answer, str):
            continue
        choices = [*feature_choices]
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
                    "that first contributed to the target's creation or existence. "
                    "Answer with exactly one listed feature ID. "
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
                labels={
                    "provenance": record,
                    "answer_status": "ok",
                    "failure_reason": None,
                },
                diagnostics={"answer_status": "ok", "failure_reason": None},
                parse_policy="strict_enum_v1",
            )
        )
    return rows


def _graph_query_rows(
    source: SourceRecord,
    trace: TraceRecord,
    nodes: list[OperationNode],
    *,
    config: DatasetConfig,
) -> list[PublicTaskRow]:
    graph = build_typed_query_graph(nodes, trace)
    records = list(trace.graph_queries) or default_graph_query_irs(graph)
    rows: list[PublicTaskRow] = []
    for record in records:
        if record.get("status", "ok") != "ok":
            continue
        if _is_graph_query_ir(record):
            resolution = resolve_graph_query(graph, record, config=config)
            if resolution.status != "ok" or resolution.answer_type is None:
                continue
            answer = (
                _round_sigfig_number(resolution.answer)
                if resolution.answer_type == "number"
                else resolution.answer
            )
            rows.append(
                _row(
                    source,
                    trace,
                    config=config,
                    task_type="graph_query",
                    target_feature_id=resolution.target_feature_id,
                    prompt=graph_query_prompt(
                        record, resolution, source.normalized_code
                    ),
                    answer_type=resolution.answer_type,
                    answer=answer,
                    choices=resolution.choices,
                    unit=resolution.unit,
                    numeric_tolerance=resolution.numeric_tolerance,
                    requires=["cadquery_syntax", "operation_graph", "graph_query"],
                    difficulty_tags=["graph_query", "multi_hop"],
                    labels={
                        "graph_query": resolution.graph_query,
                        "answer_status": "ok",
                        "failure_reason": None,
                    },
                    diagnostics={
                        "answer_status": "ok",
                        "failure_reason": None,
                        **resolution.diagnostics,
                    },
                    parse_policy=_parse_policy_for_answer_type(resolution.answer_type),
                )
            )
            continue
        answer = record.get("answer")
        if not isinstance(answer, str):
            continue
        choices = [str(item) for item in record.get("choices") or []]
        if choices and answer not in choices:
            continue
        graph_query = dict(record.get("graph_query") or record.get("ir") or {})
        rows.append(
            _row(
                source,
                trace,
                config=config,
                task_type="graph_query",
                target_feature_id=_optional_str(record.get("target_feature_id")),
                prompt=(
                    f"{record.get('prompt') or record.get('question')}\n\n"
                    "Answer with exactly one listed feature ID.\n\n"
                    f"Choices: {', '.join(choices)}\n\n"
                    f"```python\n{source.normalized_code}```"
                ),
                answer_type="choice",
                answer=answer,
                choices=choices or None,
                unit=None,
                numeric_tolerance=None,
                requires=["cadquery_syntax", "operation_graph", "graph_query"],
                difficulty_tags=["graph_query", "multi_hop"],
                labels={
                    "graph_query": graph_query,
                    "answer_status": "ok",
                    "failure_reason": None,
                },
                diagnostics={
                    "answer_status": "ok",
                    "failure_reason": None,
                    "resolver_status": record.get("resolver_status", "ok"),
                    "query_id": record.get("query_id"),
                },
                parse_policy="strict_enum_v1",
            )
        )
    return rows


def _spatial_distance_rows(
    source: SourceRecord, trace: TraceRecord, *, config: DatasetConfig
) -> list[PublicTaskRow]:
    records = list(trace.spatial_queries)
    rows: list[PublicTaskRow] = []
    for record in records:
        if record.get("status", "ok") != "ok":
            continue
        answer = record.get("answer")
        if not _finite_number(answer):
            continue
        reference_a = record.get("reference_a")
        reference_b = record.get("reference_b")
        if not isinstance(reference_a, dict) or not isinstance(reference_b, dict):
            continue
        rows.append(
            _row(
                source,
                trace,
                config=config,
                task_type="spatial_distance",
                target_feature_id=_optional_str(record.get("target_feature_id")),
                prompt=_spatial_distance_prompt(source.normalized_code, record, reference_a, reference_b),
                answer_type="number",
                answer=_round_sigfig_number(answer),
                choices=None,
                unit="mm",
                numeric_tolerance=config.label_policy.spatial_distance_tolerance_mm,
                requires=[
                    "cadquery_syntax",
                    "spatial_references",
                    "distance_reasoning",
                ],
                difficulty_tags=["spatial_distance"],
                labels={
                "spatial_query": {
                    "query_kind": record.get("query_kind"),
                        "reference_a": reference_a,
                        "reference_b": reference_b,
                        "raw_distance": answer,
                    },
                    "answer_status": "ok",
                    "failure_reason": None,
                },
                diagnostics={
                    "answer_status": "ok",
                    "failure_reason": None,
                    "reference_status": record.get("reference_status", "ok"),
                    "query_id": record.get("query_id"),
                },
                parse_policy="numeric_4_sigfig_v1",
            )
        )
    return rows


def _bbox_region_rows(
    source: SourceRecord, trace: TraceRecord, *, config: DatasetConfig
) -> list[PublicTaskRow]:
    records = list(trace.bbox_region_queries) or _default_bbox_region_queries(trace)
    rows: list[PublicTaskRow] = []
    for record in records:
        if record.get("status", "ok") != "ok":
            continue
        answer = record.get("answer")
        region = record.get("region")
        if not isinstance(answer, int) or answer < 0 or not isinstance(region, dict):
            continue
        rows.append(
            _row(
                source,
                trace,
                config=config,
                task_type="bbox_region_query",
                target_feature_id=_optional_str(record.get("target_feature_id")),
                prompt=(
                    "Given the CadQuery script below, use this world-coordinate bounding-box query window "
                    f"`{_json_compact(_round_bbox(region))}`. How many vertices are inside the region? "
                    "Answer with exactly one non-negative integer.\n\n"
                    f"```python\n{source.normalized_code}```"
                ),
                answer_type="integer",
                answer=answer,
                choices=None,
                unit=None,
                numeric_tolerance=None,
                requires=["cadquery_syntax", "bbox_region_query", "topology_count"],
                difficulty_tags=["bbox_region_query"],
                labels={
                    "spatial_query": {
                        "query_kind": record.get(
                            "query_kind", "bbox_region_entity_count"
                        ),
                        "region": region,
                        "predicate": record.get("predicate", "inside"),
                        "entity_type": record.get("entity_type", "vertex"),
                        "label_method": record.get(
                            "label_method", "topology_count_for_full_snapshot_bbox"
                        ),
                    },
                    "answer_status": "ok",
                    "failure_reason": None,
                },
                diagnostics={
                    "answer_status": "ok",
                    "failure_reason": None,
                    "query_id": record.get("query_id"),
                    "overlap_tolerance_mm": config.label_policy.bbox_region_overlap_tolerance_mm,
                },
                parse_policy="strict_integer_v1",
            )
        )
    return rows


def _default_bbox_region_queries(trace: TraceRecord) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for snapshot in sorted(
        trace.snapshots, key=lambda item: int(item.get("step_index", 0))
    ):
        topology = snapshot.get("topology")
        bbox = snapshot.get("bbox")
        feature_id = snapshot.get("feature_id")
        if (
            not isinstance(topology, dict)
            or not isinstance(bbox, dict)
            or not isinstance(feature_id, str)
        ):
            continue
        vertex_count = topology.get("vertex_count")
        if not isinstance(vertex_count, int) or vertex_count < 0:
            continue
        records.append(
            {
                "query_id": f"default_bbox_vertices_{feature_id}",
                "target_feature_id": feature_id,
                "query_kind": "bbox_region_entity_count",
                "region": bbox,
                "predicate": "inside",
                "entity_type": "vertex",
                "answer": vertex_count,
                "label_method": "topology_count_for_full_snapshot_bbox",
            }
        )
    return records


def _validity_failure_rows(
    source: SourceRecord, trace: TraceRecord, *, config: DatasetConfig
) -> list[PublicTaskRow]:
    records = list(trace.validity_probes) or [
        _default_validity_probe(trace, config=config)
    ]
    rows: list[PublicTaskRow] = []
    for record in records:
        if record.get("status", "ok") != "ok":
            continue
        answer = record.get("answer")
        answer_type = _infer_advanced_answer_type(answer)
        if answer_type is None:
            continue
        numeric_tolerance = (
            config.label_policy.linear_tolerance_mm if answer_type == "number" else None
        )
        choices = [str(item) for item in record.get("choices") or []] or (
            ["valid", "invalid", "inconclusive"] if answer_type == "enum" else None
        )
        if answer_type == "enum" and (
            not isinstance(answer, str) or (choices and answer not in choices)
        ):
            continue
        row_answer = _round_sigfig_number(answer) if answer_type == "number" else answer
        rows.append(
            _row(
                source,
                trace,
                config=config,
                task_type="validity_failure_prediction",
                target_feature_id=_optional_str(record.get("target_feature_id")),
                prompt=(
                    f"{record.get('prompt') or record.get('question')}\n\n"
                    f"```python\n{source.normalized_code}```"
                ),
                answer_type=answer_type,
                answer=row_answer,
                choices=choices,
                unit=record.get("unit")
                if isinstance(record.get("unit"), str)
                else None,
                numeric_tolerance=numeric_tolerance,
                requires=["cadquery_syntax", "validity_reasoning"],
                difficulty_tags=[
                    "validity_failure_prediction",
                    str(record.get("question_kind", "validity")),
                ],
                labels={
                    "validity_result": {
                        "question_kind": record.get("question_kind", "script_validity"),
                        "probe_target": record.get("probe_target"),
                        "prior_state_validity": record.get("prior_state_validity"),
                        "post_probe_validity": record.get(
                            "post_probe_validity", answer
                        ),
                        "failure_stage": record.get("failure_stage"),
                        "failure_type": record.get("failure_type"),
                        "threshold": record.get("threshold"),
                    },
                    "answer_status": "ok",
                    "failure_reason": None,
                },
                diagnostics={
                    "answer_status": "ok",
                    "failure_reason": None,
                    "query_id": record.get("query_id"),
                    "repeat_count": record.get(
                        "repeat_count", config.label_policy.validity_probe_repeat_count
                    ),
                    "probe_status": record.get("probe_status", "stable"),
                },
                parse_policy=_parse_policy_for_answer_type(answer_type),
            )
        )
    return rows


def _default_validity_probe(
    trace: TraceRecord, *, config: DatasetConfig
) -> dict[str, Any]:
    answer = (
        "valid"
        if trace.execution_status == "ok" and trace.failure_reason is None
        else "invalid"
    )
    return {
        "query_id": "default_script_validity",
        "question_kind": "script_validity",
        "question": (
            "Given the CadQuery script below, does the traced script produce a valid final shape? "
            "Answer with exactly one token: valid, invalid, or inconclusive."
        ),
        "answer": answer,
        "choices": ["valid", "invalid", "inconclusive"],
        "prior_state_validity": "valid",
        "post_probe_validity": answer,
        "failure_stage": None if answer == "valid" else "execution",
        "failure_type": trace.failure_reason,
        "repeat_count": config.label_policy.validity_probe_repeat_count,
        "probe_status": "stable",
    }


def _infer_advanced_answer_type(answer: Any) -> str | None:
    if isinstance(answer, int) and not isinstance(answer, bool):
        return "integer"
    if (
        isinstance(answer, (int, float))
        and not isinstance(answer, bool)
        and math.isfinite(float(answer))
    ):
        return "number"
    if isinstance(answer, str):
        return "enum"
    return None


def _parse_policy_for_answer_type(answer_type: str) -> str:
    if answer_type == "integer":
        return "strict_integer_v1"
    if answer_type == "number":
        return "numeric_4_sigfig_v1"
    return "strict_enum_v1"


def _is_graph_query_ir(record: dict[str, Any]) -> bool:
    return (
        record.get("ir_version") == "cadqa_graph_query_ir_v1"
        or "query_type" in record
        or "aggregate" in record
        or "filters" in record
    )


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
    provenance_overrides: dict[str, Any] | None = None,
) -> PublicTaskRow:
    prompt_hash = sha256_json(
        {"task_type": task_type, "target": target_feature_id, "prompt": prompt}
    )
    provenance = _provenance(source, trace)
    if provenance_overrides:
        provenance.update(provenance_overrides)
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
        id="cadqa_"
        + task_type
        + "_"
        + sha256_json(row_payload).removeprefix("sha256:")[:16],
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


def _coordinate_frame(node: OperationNode) -> str:
    if node.operation == "workplane":
        return "inherited"
    if not node.args_repr:
        return "unknown"
    first = node.args_repr[0].strip()
    if (first.startswith("'") and first.endswith("'")) or (
        first.startswith('"') and first.endswith('"')
    ):
        return first[1:-1]
    return first


def _point_membership_tags(query: dict[str, Any], answer: str) -> list[str]:
    tags = ["point_membership"]
    if _is_near_boundary_query(query, answer):
        tags.append("near_boundary")
    return tags


def _point_sampling_group_id(
    source: SourceRecord, query: dict[str, Any], answer: str
) -> str:
    stratum = str(
        query.get("sampling_stratum") or query.get("sample_source") or "unknown"
    )
    if _is_near_boundary_query(query, answer):
        return f"near_boundary:{source.source_id}:{stratum}"
    return f"point_sample:{source.source_id}:{stratum}"


def _is_near_boundary_query(query: dict[str, Any], answer: str) -> bool:
    stratum = f"{query.get('sampling_stratum')} {query.get('sample_source')}".lower()
    return answer == "on_boundary" or "boundary" in stratum


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _valid_point(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 3
        and all(_finite_number(item) for item in value)
    )


def _json_compact(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _spatial_reference_description(reference: dict[str, Any]) -> str:
    name = str(reference.get("name", "reference"))
    if _valid_point(reference.get("point")):
        return f"`{name}` point `{_json_compact(reference['point'])}`"
    point = reference.get("axis_point") or reference.get("centerline_point")
    direction = reference.get("axis_direction") or reference.get("centerline_direction")
    if _valid_point(point) and _valid_point(direction):
        kind = str(reference.get("reference_kind") or "axis")
        return f"`{name}` {kind} with point `{_json_compact(point)}` and direction `{_json_compact(direction)}`"
    return f"`{name}` reference `{_json_compact(reference)}`"


def _spatial_distance_prompt(
    code: str,
    record: dict[str, Any],
    reference_a: dict[str, Any],
    reference_b: dict[str, Any],
) -> str:
    query_kind = record.get("query_kind")
    if query_kind == "axis_component_distance":
        axis = str(record.get("component_axis", "X")).upper()
        question = (
            f"Given the CadQuery script below, what is the world-coordinate {axis} distance in millimetres "
            f"between {_spatial_reference_description(reference_a)} and {_spatial_reference_description(reference_b)}?"
        )
    elif query_kind == "centerline_to_centerline_distance":
        question = (
            "Given the CadQuery script below, what is the shortest distance in millimetres "
            f"between {_spatial_reference_description(reference_a)} and {_spatial_reference_description(reference_b)}?"
        )
    else:
        question = (
            "Given the CadQuery script below, what is the world-coordinate distance in millimetres "
            f"between {_spatial_reference_description(reference_a)} and {_spatial_reference_description(reference_b)}?"
        )
    return f"{question} Answer with exactly one finite number.\n\n```python\n{code}```"


def _round_bbox(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    rounded: dict[str, Any] = {}
    for key, coordinates in value.items():
        if key in {"min", "max"} and isinstance(coordinates, list):
            rounded[key] = [_round_sigfig_number(item) for item in coordinates]
        else:
            rounded[key] = coordinates
    return rounded


def _round_sigfig_number(value: Any, digits: int = 4) -> Any:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return value
    numeric = float(value)
    if not math.isfinite(numeric):
        return value
    if numeric == 0:
        return 0.0
    places = digits - math.floor(math.log10(abs(numeric))) - 1
    rounded = round(numeric, places)
    if rounded == 0:
        return 0.0
    if places <= 0 and float(rounded).is_integer():
        return int(rounded)
    return rounded


def rows_to_dicts(rows: list[PublicTaskRow]) -> list[dict[str, Any]]:
    return [asdict(row) for row in rows]
