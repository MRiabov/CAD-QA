"""Answer contracts for resolved CAD-QA query targets."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from cad_qa.ontology.nodes import Node, OntologyGraph


DEFAULT_DECIMALS = 6


@dataclass(frozen=True)
class AnswerSpec:
    mode: str = "entity_id"
    answer_format: str = "entity_id"
    metric: str | None = None
    decimals: int = DEFAULT_DECIMALS
    candidate_labels: dict[str, str] = field(default_factory=dict)
    candidate_set: str = "prefinal"
    max_candidate_labels: int = 64


def normalize_answer_spec(
    value: Any,
    *,
    target_type: str | None = None,
    answer_type: str | None = None,
) -> AnswerSpec:
    if isinstance(value, AnswerSpec):
        return value
    if isinstance(value, Mapping):
        return AnswerSpec(
            mode=str(value.get("mode") or answer_type or "entity_id"),
            answer_format=str(
                value.get("answer_format")
                or answer_type
                or value.get("mode")
                or "entity_id"
            ),
            metric=str(value["metric"]) if value.get("metric") is not None else None,
            decimals=int(value.get("decimals", DEFAULT_DECIMALS)),
            candidate_labels={
                str(entity_id): str(label)
                for entity_id, label in (value.get("candidate_labels") or {}).items()
            },
            candidate_set=str(value.get("candidate_set") or "prefinal"),
            max_candidate_labels=int(value.get("max_candidate_labels", 64)),
        )
    if answer_type and answer_type != "entity_id":
        return _spec_from_answer_type(answer_type)
    return AnswerSpec()


def synthesis_answer_spec_for_target_type(target_type: str, graph: OntologyGraph | None = None) -> AnswerSpec:
    if target_type in {"feature", "operation", "profile", "workplane", "material_region", "void_region"}:
        return AnswerSpec(mode="source_ref", answer_format="text")
    if target_type in {"vertex", "path_point"}:
        return AnswerSpec(mode="coordinate", answer_format="coordinate", metric="coordinate")
    if target_type == "edge_endpoint":
        if graph is not None and _target_type_has_full_coordinates(graph, target_type):
            return AnswerSpec(mode="coordinate", answer_format="coordinate", metric="coordinate")
        return AnswerSpec(mode="candidate_label", answer_format="candidate_label")
    if target_type in {"edge", "face", "selector", "path_segment"}:
        return AnswerSpec(mode="candidate_label", answer_format="candidate_label")
    return AnswerSpec()


def target_type_label(target_type: str | None) -> str:
    if target_type == "edge_endpoint":
        return "edge endpoint"
    if target_type == "material_region":
        return "added-material region"
    if target_type == "void_region":
        return "removed-material region"
    return str(target_type or "entity").replace("_", " ")


def answer_instruction(spec: AnswerSpec, *, target_type: str | None = None) -> str:
    if spec.mode == "source_ref":
        return "Return exactly one source variable name, for example `wp7`."
    if spec.mode == "coordinate":
        return f"Return exactly one coordinate tuple of the {target_type_label(target_type)}, for example `(0, 1, 3)`."
    if spec.mode == "number":
        return "Return exactly one number, for example `12.5`."
    if spec.mode == "candidate_label":
        return "Return exactly one candidate label from the list above, for example `A`."
    if spec.mode == "boolean":
        return "Return exactly one boolean value: `true` or `false`."
    if spec.mode == "integer":
        return "Return exactly one integer, for example `7`."
    return "Return exactly one entity_id."


def format_gold_answer(graph: OntologyGraph, query: Any, node: Node) -> Any:
    spec = normalize_answer_spec(
        getattr(query, "answer_spec", None),
        target_type=getattr(query, "target_type", None),
        answer_type=getattr(query, "answer_type", None),
    )
    if spec.mode == "source_ref":
        return _source_ref_answer(node)
    if spec.mode == "coordinate":
        return _coordinate_answer(graph, node, spec)
    if spec.mode == "number":
        return _number_answer(graph, node, spec)
    if spec.mode == "boolean":
        return bool(_number_answer(graph, node, spec)) if spec.metric else bool(node.id)
    if spec.mode == "integer":
        return int(round(float(_number_answer(graph, node, spec))))
    if spec.mode == "candidate_label":
        label = spec.candidate_labels.get(node.id)
        if label is None:
            raise ValueError(f"missing candidate label for {node.id}")
        return label
    return node.id


def answer_spec_with_candidate_labels(spec: AnswerSpec, candidate_ids: list[str]) -> AnswerSpec:
    return replace(spec, candidate_labels={entity_id: _candidate_label(index) for index, entity_id in enumerate(candidate_ids)})


def candidate_label_entity_ids(trace_steps: list[dict[str, Any]], final_candidates: list[str]) -> list[str]:
    if not final_candidates:
        return []
    final_set = set(final_candidates)
    for step in reversed(trace_steps):
        before = _step_candidates(step, "before") or _step_candidates(step, "candidate_ids")
        after = _step_candidates(step, "after")
        if before and (set(after) == final_set or step.get("step") in {"aggregation", "tie_break_aggregation"}):
            return before
    for step in trace_steps:
        candidates = _step_candidates(step, "candidate_ids") or _step_candidates(step, "after")
        if candidates:
            return candidates
    return list(final_candidates)


def candidate_label_lines(graph: OntologyGraph, query: Any) -> list[str]:
    spec = normalize_answer_spec(
        getattr(query, "answer_spec", None),
        target_type=getattr(query, "target_type", None),
        answer_type=getattr(query, "answer_type", None),
    )
    if spec.mode != "candidate_label" or not spec.candidate_labels:
        return []
    ordered = sorted(spec.candidate_labels.items(), key=lambda item: _label_sort_key(item[1]))
    return [
        f"{label}: {_candidate_description(graph, entity_id)}"
        for entity_id, label in ordered
    ]


def _spec_from_answer_type(answer_type: str) -> AnswerSpec:
    if answer_type == "coordinate":
        return AnswerSpec(mode="coordinate", answer_format="coordinate", metric="coordinate")
    if answer_type == "number":
        return AnswerSpec(mode="number", answer_format="number")
    if answer_type == "boolean":
        return AnswerSpec(mode="boolean", answer_format="boolean")
    if answer_type == "integer":
        return AnswerSpec(mode="integer", answer_format="integer")
    if answer_type == "text":
        return AnswerSpec(mode="source_ref", answer_format="text")
    if answer_type == "candidate_label":
        return AnswerSpec(mode="candidate_label", answer_format="candidate_label")
    return AnswerSpec(mode=answer_type, answer_format=answer_type)


def _source_ref_answer(node: Node) -> str:
    target = node.properties.get("target") or node.properties.get("operation_target")
    if target is not None:
        return str(target)
    prefix = f"{node.type}:"
    if node.id.startswith(prefix):
        return node.id.removeprefix(prefix).split(":", 1)[0]
    return node.label or node.id


def _coordinate_answer(graph: OntologyGraph, node: Node, spec: AnswerSpec) -> list[float]:
    metric = spec.metric or "coordinate"
    value = _measurement_value(graph, node.id, metric)
    if value is None:
        value = node.properties.get(metric)
    if value is None and metric == "coordinate":
        components = [
            _measurement_value(graph, node.id, f"coordinate_{axis}")
            for axis in ("x", "y", "z")
        ]
        if all(component is not None for component in components):
            value = components
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"missing coordinate answer for {node.id}")
    return [_clean_number(float(component), spec.decimals) for component in value]


def _number_answer(graph: OntologyGraph, node: Node, spec: AnswerSpec) -> float:
    if not spec.metric:
        raise ValueError("number answer spec requires a metric")
    value = _measurement_value(graph, node.id, spec.metric)
    if value is None:
        value = node.properties.get(spec.metric)
    if not isinstance(value, (int, float)):
        raise ValueError(f"missing numeric answer for {node.id}:{spec.metric}")
    return _clean_number(float(value), spec.decimals)


def _measurement_value(graph: OntologyGraph, entity_id: str, metric: str) -> Any:
    measurements = graph.measurements_for(entity_id, metric)
    if not measurements:
        return None
    return measurements[0].value


def _target_type_has_full_coordinates(graph: OntologyGraph, target_type: str) -> bool:
    nodes = graph.nodes_by_type(target_type)
    if not nodes:
        return False
    return all(_point_value(graph, node.id, "coordinate") is not None for node in nodes)


def _candidate_description(graph: OntologyGraph, entity_id: str) -> str:
    node = graph.node(entity_id)
    node_type = node.type if node is not None else entity_id.split(":", 1)[0]
    if node_type == "edge":
        return _edge_description(graph, entity_id, node)
    if node_type == "face":
        return _face_description(graph, entity_id, node)
    if node_type == "path_segment":
        return _path_segment_description(graph, entity_id, node)
    if node_type == "selector":
        return _selector_description(graph, entity_id, node)
    if node_type in {"vertex", "edge_endpoint", "path_point"}:
        coordinate = _point_value(graph, entity_id, "coordinate")
        parts = [f"coordinates {_format_point(coordinate)}"] if coordinate is not None else []
        if not parts:
            parts.extend(_point_component_parts(graph, entity_id, "coordinate", "coordinate"))
        return "; ".join(parts) if parts else _fallback_description(entity_id, node)
    return _fallback_description(entity_id, node)


def _edge_description(graph: OntologyGraph, entity_id: str, node: Node | None) -> str:
    midpoint = _point_value(graph, entity_id, "midpoint")
    length = _measurement_value(graph, entity_id, "edge_length")
    bbox = node.properties.get("bbox") if node is not None else None
    endpoints = _bbox_edge_endpoints(bbox)
    parts = []
    if endpoints is not None:
        parts.append(f"endpoints {_format_point(endpoints[0])} to {_format_point(endpoints[1])}")
    if midpoint is not None:
        parts.append(f"midpoint {_format_point(midpoint)}")
    else:
        parts.extend(_point_component_parts(graph, entity_id, "midpoint", "midpoint"))
    if isinstance(length, (int, float)):
        parts.append(f"length {_format_number(float(length))}")
    return "; ".join(parts) if parts else _fallback_description(entity_id, node)


def _face_description(graph: OntologyGraph, entity_id: str, node: Node | None) -> str:
    center = _point_value(graph, entity_id, "coordinate")
    area = _measurement_value(graph, entity_id, "face_area")
    bbox = node.properties.get("bbox") if node is not None else None
    parts = []
    if center is not None:
        parts.append(f"center {_format_point(center)}")
    else:
        parts.extend(_point_component_parts(graph, entity_id, "center", "coordinate"))
    if isinstance(area, (int, float)):
        parts.append(f"area {_format_number(float(area))}")
    bbox_text = _bbox_description(bbox)
    if bbox_text:
        parts.append(bbox_text)
    return "; ".join(parts) if parts else _fallback_description(entity_id, node)


def _path_segment_description(graph: OntologyGraph, entity_id: str, node: Node | None) -> str:
    start = node.properties.get("start") if node is not None else None
    end = node.properties.get("end") if node is not None else None
    midpoint = _point_value(graph, entity_id, "segment_midpoint") or _point_value(graph, entity_id, "midpoint")
    length = _measurement_value(graph, entity_id, "segment_length")
    parts = []
    if _is_point(start) and _is_point(end):
        parts.append(f"endpoints {_format_point(start)} to {_format_point(end)}")
    if midpoint is not None:
        parts.append(f"midpoint {_format_point(midpoint)}")
    else:
        parts.extend(_point_component_parts(graph, entity_id, "midpoint", "segment_midpoint"))
    if isinstance(length, (int, float)):
        parts.append(f"length {_format_number(float(length))}")
    return "; ".join(parts) if parts else _fallback_description(entity_id, node)


def _selector_description(graph: OntologyGraph, entity_id: str, node: Node | None) -> str:
    if node is None:
        return "selector candidate"
    props = node.properties
    parts = []
    selector_text = props.get("selector_label") or props.get("selector_text") or props.get("stable_selector")
    if selector_text is not None:
        parts.append(f"selector {selector_text!r}")
    selector_kind = props.get("selector_kind") or props.get("kind")
    if selector_kind is not None:
        parts.append(f"type {selector_kind}")
    for metric in (
        "selected_count",
        "selected_edge_count",
        "selected_face_count",
        "selected_vertex_count",
    ):
        value = _measurement_value(graph, entity_id, metric)
        if isinstance(value, (int, float)):
            parts.append(f"{metric.replace('_', ' ')} {_format_number(float(value))}")
            break
    parts.extend(_selection_geometry_parts(graph, entity_id))
    return "; ".join(parts) if parts else _fallback_description(entity_id, node)


def _point_value(graph: OntologyGraph, entity_id: str, metric: str) -> list[float | int] | None:
    value = _measurement_value(graph, entity_id, metric)
    node = graph.node(entity_id)
    if value is None and node is not None:
        value = node.properties.get(metric)
    if _is_point(value):
        return [_clean_number(float(component), DEFAULT_DECIMALS) for component in value]
    return None


def _point_component_parts(graph: OntologyGraph, entity_id: str, label: str, metric_prefix: str) -> list[str]:
    parts = []
    for axis in ("x", "y", "z"):
        value = _measurement_value(graph, entity_id, f"{metric_prefix}_{axis}")
        if isinstance(value, (int, float)):
            parts.append(f"{label} {axis.upper()} {_format_number(float(value))}")
    return parts


def _selection_geometry_parts(graph: OntologyGraph, entity_id: str) -> list[str]:
    metric_groups = (
        ("selected face center Z", "selected_face_min_coordinate_z", "selected_face_max_coordinate_z"),
        ("selected face area", "selected_face_min_face_area", "selected_face_max_face_area"),
        ("selected face distance to origin", "selected_face_min_distance_to_origin", "selected_face_max_distance_to_origin"),
        ("selected edge length", "selected_edge_min_edge_length", "selected_edge_max_edge_length"),
        ("selected edge midpoint Y", "selected_edge_min_midpoint_y", "selected_edge_max_midpoint_y"),
        ("selected edge midpoint distance to origin", "selected_edge_min_midpoint_distance_to_origin", "selected_edge_max_midpoint_distance_to_origin"),
        ("selected vertex Z", "selected_vertex_min_coordinate_z", "selected_vertex_max_coordinate_z"),
        ("selected vertex distance to origin", "selected_vertex_min_distance_to_origin", "selected_vertex_max_distance_to_origin"),
    )
    parts = []
    for label, min_metric, max_metric in metric_groups:
        min_value = _measurement_value(graph, entity_id, min_metric)
        max_value = _measurement_value(graph, entity_id, max_metric)
        if isinstance(min_value, (int, float)) and isinstance(max_value, (int, float)):
            parts.append(f"{label} range {_format_number(float(min_value))} to {_format_number(float(max_value))}")
    return parts[:3]


def _is_point(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == 3 and all(isinstance(item, (int, float)) for item in value)


def _bbox_edge_endpoints(bbox: Any) -> list[list[float | int]] | None:
    if not isinstance(bbox, dict):
        return None
    minimum = bbox.get("min")
    maximum = bbox.get("max")
    if not (_is_point(minimum) and _is_point(maximum)):
        return None
    spans = [abs(float(maximum[index]) - float(minimum[index])) for index in range(3)]
    if sum(span > 1e-6 for span in spans) != 1:
        return None
    return [
        [_clean_number(float(component), DEFAULT_DECIMALS) for component in minimum],
        [_clean_number(float(component), DEFAULT_DECIMALS) for component in maximum],
    ]


def _bbox_description(bbox: Any) -> str | None:
    if not isinstance(bbox, dict):
        return None
    minimum = bbox.get("min")
    maximum = bbox.get("max")
    if not (_is_point(minimum) and _is_point(maximum)):
        return None
    return f"bbox {_format_point(minimum)} to {_format_point(maximum)}"


def _fallback_description(entity_id: str, node: Node | None) -> str:
    if node is not None and node.label and node.label != entity_id and ":" not in str(node.label):
        return str(node.label)
    if node is not None:
        return f"{node.type.replace('_', ' ')} candidate"
    return "unlabeled candidate"


def _candidate_label(index: int) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    label = ""
    value = index
    while True:
        label = letters[value % 26] + label
        value = value // 26 - 1
        if value < 0:
            return label


def _label_sort_key(label: str) -> tuple[int, str]:
    return (len(label), label)


def _step_candidates(step: dict[str, Any], key: str) -> list[str]:
    value = step.get(key)
    return [str(item) for item in value] if isinstance(value, list) else []


def _format_point(point: list[Any] | tuple[Any, ...]) -> str:
    return "(" + ", ".join(_format_number(float(component)) for component in point) + ")"


def _format_number(value: float) -> str:
    cleaned = _clean_number(value, DEFAULT_DECIMALS)
    return str(cleaned)


def _clean_number(value: float, decimals: int) -> float | int:
    rounded = round(value, decimals)
    if rounded == 0:
        rounded = 0.0
    if float(rounded).is_integer():
        return int(rounded)
    return rounded
