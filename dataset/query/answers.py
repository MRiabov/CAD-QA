"""Answer contracts for resolved CAD-QA query targets."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from dataset.ontology.nodes import Node, CadGraph


DEFAULT_DECIMALS = 6
DEFAULT_MAX_CANDIDATE_LABELS = 7


@dataclass(frozen=True)
class AnswerSpec:
    mode: str = "entity_id"
    answer_format: str = "entity_id"
    metric: str | None = None
    decimals: int = DEFAULT_DECIMALS
    candidate_labels: dict[str, str] = field(default_factory=dict)
    candidate_texts: dict[str, str] = field(default_factory=dict)
    candidate_set: str = "prefinal"
    max_candidate_labels: int = DEFAULT_MAX_CANDIDATE_LABELS


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
            candidate_texts={
                str(entity_id): str(text)
                for entity_id, text in (value.get("candidate_texts") or {}).items()
            },
            candidate_set=str(value.get("candidate_set") or "prefinal"),
            max_candidate_labels=int(value.get("max_candidate_labels", DEFAULT_MAX_CANDIDATE_LABELS)),
        )
    if answer_type and answer_type != "entity_id":
        return _spec_from_answer_type(answer_type)
    return AnswerSpec()


def synthesis_answer_spec_for_target_type(target_type: str, graph: CadGraph | None = None) -> AnswerSpec:
    if target_type in {"feature", "operation", "profile", "workplane", "material_region", "void_region"}:
        if target_type == "void_region":
            return AnswerSpec(mode="candidate_label", answer_format="candidate_label")
        return AnswerSpec(mode="source_ref", answer_format="text")
    if target_type in {"vertex", "path_point"}:
        return AnswerSpec(mode="coordinate", answer_format="coordinate", metric="coordinate")
    if target_type == "edge_endpoint":
        if graph is not None and _target_type_has_full_coordinates(graph, target_type):
            return AnswerSpec(mode="coordinate", answer_format="coordinate", metric="coordinate")
        return AnswerSpec(mode="candidate_label", answer_format="candidate_label")
    if target_type in {"edge", "face", "selector", "path_segment"}:
        if target_type == "selector" and graph is not None and _target_type_has_any_selector_expression(graph, target_type):
            return AnswerSpec(mode="selector_expression_choice", answer_format="candidate_label")
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
    if spec.mode == "selector_expression_choice":
        return "Return exactly one candidate label from the selector-expression choices above, for example `A`."
    if spec.mode == "boolean":
        return "Return exactly one boolean value: `true` or `false`."
    if spec.mode == "integer":
        return "Return exactly one integer, for example `7`."
    return "Return exactly one entity_id."


def source_ref_is_publicly_unambiguous(graph: CadGraph, node: Node) -> bool:
    answer = _source_ref_answer(node)
    if not answer or ":" in answer:
        return False
    source = str(graph.source.get("source_code") or graph.source.get("normalized_code") or "")
    if source:
        return source.count(f"{answer} =") <= 1
    return sum(1 for candidate in graph.nodes_by_type(node.type) if _source_ref_answer(candidate) == answer) <= 1


def format_gold_answer(graph: CadGraph, query: Any, node: Node) -> Any:
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
    if spec.mode == "selector_expression_choice":
        label = spec.candidate_labels.get(node.id)
        if label is None:
            raise ValueError(f"missing selector-expression candidate label for {node.id}")
        return label
    return node.id


def answer_spec_with_candidate_labels(
    graph: CadGraph,
    spec: AnswerSpec,
    candidate_ids: list[str],
    gold_entity_id: str,
    *,
    aggregation: str | None = None,
    aggregation_metric: str | None = None,
    aggregation_rank: int | None = None,
) -> AnswerSpec:
    bounded_ids = _bounded_candidate_ids(
        graph,
        candidate_ids,
        gold_entity_id,
        spec.max_candidate_labels,
        aggregation=aggregation,
        aggregation_metric=aggregation_metric,
        aggregation_rank=aggregation_rank,
    )
    offset = _stable_index(f"{gold_entity_id}:candidate_label", len(bounded_ids))
    ordered_ids = _rotate(bounded_ids, offset)
    return replace(spec, candidate_labels={entity_id: _candidate_label(index) for index, entity_id in enumerate(ordered_ids)})


def answer_spec_with_selector_expression_choices(
    graph: CadGraph,
    spec: AnswerSpec,
    gold_entity_id: str,
    candidate_entity_ids: list[str],
    *,
    aggregation: str | None = None,
    aggregation_metric: str | None = None,
    aggregation_rank: int | None = None,
) -> AnswerSpec | None:
    candidate_texts = selector_expression_choice_texts(graph, gold_entity_id, candidate_entity_ids)
    if candidate_texts is None:
        return None
    candidate_ids = _bounded_candidate_ids(
        graph,
        list(candidate_texts),
        gold_entity_id,
        spec.max_candidate_labels,
        aggregation=aggregation,
        aggregation_metric=aggregation_metric,
        aggregation_rank=aggregation_rank,
    )
    candidate_texts = {entity_id: candidate_texts[entity_id] for entity_id in candidate_ids}
    if len(candidate_ids) < 2:
        return None
    offset = _stable_index(f"{graph.graph_id}:{gold_entity_id}:selector_expression_choice", len(candidate_ids))
    ordered_ids = _rotate(candidate_ids, offset)
    return replace(
        spec,
        candidate_labels={entity_id: _candidate_label(index) for index, entity_id in enumerate(ordered_ids)},
        candidate_texts=candidate_texts,
    )


def candidate_label_entity_ids(trace_steps: list[dict[str, Any]], final_candidates: list[str]) -> list[str]:
    if not final_candidates:
        return []
    final_set = set(final_candidates)
    for step in reversed(trace_steps):
        if step.get("step") == "tie_break_aggregation":
            continue
        before = _step_candidates(step, "before") or _step_candidates(step, "candidate_ids")
        after = _step_candidates(step, "after")
        if before and (set(after) == final_set or step.get("step") == "aggregation"):
            return before
    for step in trace_steps:
        candidates = _step_candidates(step, "candidate_ids") or _step_candidates(step, "after")
        if candidates:
            return candidates
    return list(final_candidates)


def candidate_label_lines(graph: CadGraph, query: Any) -> list[str]:
    spec = normalize_answer_spec(
        getattr(query, "answer_spec", None),
        target_type=getattr(query, "target_type", None),
        answer_type=getattr(query, "answer_type", None),
    )
    if spec.mode != "candidate_label" or not spec.candidate_labels:
        if spec.mode != "selector_expression_choice" or not spec.candidate_labels:
            return []
    ordered = sorted(spec.candidate_labels.items(), key=lambda item: _label_sort_key(item[1]))
    if spec.mode == "selector_expression_choice":
        return [
            f"{label}: `{selector_expression}`"
            for entity_id, label in ordered
            if (selector_expression := spec.candidate_texts.get(entity_id) or selector_expression_for_entity(graph, entity_id)) is not None
        ]
    metric_names = _query_description_metrics(query)
    return [
        f"{label}: {_candidate_description(graph, entity_id, metric_names=metric_names)}"
        for entity_id, label in ordered
    ]


def selector_expression_choice_texts(
    graph: CadGraph,
    gold_entity_id: str,
    candidate_entity_ids: list[str],
) -> dict[str, str] | None:
    node = graph.node(gold_entity_id)
    if node is None or node.type != "selector":
        return None
    gold = selector_expression_for_entity(graph, gold_entity_id)
    if gold is None:
        return None
    options = {gold_entity_id: gold}
    seen = {gold}
    for candidate_id in candidate_entity_ids:
        if candidate_id == gold_entity_id:
            continue
        expression = selector_expression_for_entity(graph, candidate_id)
        if expression is None or expression in seen:
            continue
        options[candidate_id] = expression
        seen.add(expression)
    if len(options) < 2:
        return None
    return options


def _bounded_candidate_ids(
    graph: CadGraph,
    candidate_ids: list[str],
    gold_entity_id: str,
    max_candidate_labels: int,
    *,
    aggregation: str | None = None,
    aggregation_metric: str | None = None,
    aggregation_rank: int | None = None,
) -> list[str]:
    if max_candidate_labels < 1:
        raise ValueError("max_candidate_labels must be positive")
    unique_ids = list(dict.fromkeys(candidate_ids))
    if gold_entity_id not in unique_ids:
        unique_ids.insert(0, gold_entity_id)
    if len(unique_ids) <= max_candidate_labels:
        return unique_ids
    consistent_ids = _aggregation_consistent_candidate_ids(
        graph,
        unique_ids,
        gold_entity_id,
        max_candidate_labels,
        aggregation=aggregation,
        aggregation_metric=aggregation_metric,
        aggregation_rank=aggregation_rank,
    )
    if consistent_ids is not None:
        return consistent_ids
    distractors = [
        entity_id
        for entity_id in unique_ids
        if entity_id != gold_entity_id and _has_informative_candidate_description(graph, entity_id)
    ]
    if len(distractors) < max_candidate_labels - 1:
        distractors.extend(
            entity_id
            for entity_id in unique_ids
            if entity_id != gold_entity_id and entity_id not in set(distractors)
        )
    offset = _stable_index(f"{gold_entity_id}:candidate_distractors", len(distractors))
    rotated = _rotate(distractors, offset)
    return [gold_entity_id, *rotated[: max_candidate_labels - 1]]


def _aggregation_consistent_candidate_ids(
    graph: CadGraph,
    candidate_ids: list[str],
    gold_entity_id: str,
    max_candidate_labels: int,
    *,
    aggregation: str | None,
    aggregation_metric: str | None,
    aggregation_rank: int | None,
) -> list[str] | None:
    if aggregation_metric is None or aggregation not in {"argmax", "argmin", "rank_desc", "rank_asc"}:
        return None
    scored = [
        (entity_id, value)
        for entity_id in candidate_ids
        if isinstance((value := _measurement_value(graph, entity_id, aggregation_metric)), (int, float))
    ]
    if gold_entity_id not in {entity_id for entity_id, _ in scored}:
        return None
    descending = aggregation in {"argmax", "rank_desc"}
    ordered_scored = sorted(
        ((entity_id, float(value)) for entity_id, value in scored),
        key=lambda item: (-item[1] if descending else item[1], item[0]),
    )
    if aggregation in {"rank_desc", "rank_asc"}:
        if (
            aggregation_rank is None
            or aggregation_rank < 1
            or aggregation_rank > max_candidate_labels
            or aggregation_rank > len(ordered_scored)
        ):
            return None
        target_score = ordered_scored[aggregation_rank - 1][1]
        gold_score = float(next(value for entity_id, value in scored if entity_id == gold_entity_id))
        if abs(gold_score - target_score) > 1e-6:
            return None
        if descending:
            preceding = [entity_id for entity_id, score in ordered_scored if score > target_score + 1e-6]
            tied = [entity_id for entity_id, score in ordered_scored if abs(score - target_score) <= 1e-6]
            following = [entity_id for entity_id, score in ordered_scored if score < target_score - 1e-6]
        else:
            preceding = [entity_id for entity_id, score in ordered_scored if score < target_score - 1e-6]
            tied = [entity_id for entity_id, score in ordered_scored if abs(score - target_score) <= 1e-6]
            following = [entity_id for entity_id, score in ordered_scored if score > target_score + 1e-6]
        needed_tied = aggregation_rank - len(preceding)
        if needed_tied < 1:
            return None
        selected_tied = tied[:needed_tied]
        if gold_entity_id not in selected_tied:
            selected_tied.append(gold_entity_id)
        selected = [*preceding, *selected_tied]
        if len(selected) > max_candidate_labels:
            return None
        for entity_id in following:
            if len(selected) >= max_candidate_labels:
                break
            selected.append(entity_id)
        return selected

    gold_score = float(next(value for entity_id, value in scored if entity_id == gold_entity_id))
    if aggregation == "argmax":
        eligible = [entity_id for entity_id, value in scored if float(value) <= gold_score + 1e-6]
    else:
        eligible = [entity_id for entity_id, value in scored if float(value) >= gold_score - 1e-6]
    if gold_entity_id not in eligible:
        eligible.insert(0, gold_entity_id)
    eligible_distractors = [
        entity_id
        for entity_id in eligible
        if entity_id != gold_entity_id and _has_informative_candidate_description(graph, entity_id)
    ]
    if len(eligible_distractors) < max_candidate_labels - 1:
        known = set(eligible_distractors)
        eligible_distractors.extend(
            entity_id
            for entity_id in eligible
            if entity_id != gold_entity_id and entity_id not in known
        )
    offset = _stable_index(f"{gold_entity_id}:aggregation_consistent_distractors", len(eligible_distractors))
    return [gold_entity_id, *_rotate(eligible_distractors, offset)[: max_candidate_labels - 1]]


def _has_informative_candidate_description(graph: CadGraph, entity_id: str) -> bool:
    description = _candidate_description(graph, entity_id)
    return description not in {
        "edge candidate",
        "face candidate",
        "path segment candidate",
        "selector candidate",
        "unlabeled candidate",
    }


def selector_expression_for_entity(graph: CadGraph, entity_id: str) -> str | None:
    node = graph.node(entity_id)
    if node is None:
        return None
    if node.type == "selector":
        return _selector_expression_for_selector(graph, node)
    if node.type in {"edge", "face", "vertex"}:
        selector = _selector_for_selected_entity(graph, node)
        if selector is None:
            return None
        expression = _selector_expression_for_selector(graph, selector)
        if expression is None:
            return None
        index = node.properties.get("selector_index")
        if isinstance(index, int):
            return f"{expression}[{index}]"
        return expression
    return None


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
    if answer_type == "selector_expression_choice":
        return AnswerSpec(mode="selector_expression_choice", answer_format="candidate_label")
    return AnswerSpec(mode=answer_type, answer_format=answer_type)


def _source_ref_answer(node: Node) -> str:
    target = node.properties.get("target") or node.properties.get("operation_target")
    if target is not None:
        return str(target)
    prefix = f"{node.type}:"
    if node.id.startswith(prefix):
        return node.id.removeprefix(prefix).split(":", 1)[0]
    return node.label or node.id


def _coordinate_answer(graph: CadGraph, node: Node, spec: AnswerSpec) -> list[float]:
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


def _number_answer(graph: CadGraph, node: Node, spec: AnswerSpec) -> float:
    if not spec.metric:
        raise ValueError("number answer spec requires a metric")
    value = _measurement_value(graph, node.id, spec.metric)
    if value is None:
        value = node.properties.get(spec.metric)
    if not isinstance(value, (int, float)):
        raise ValueError(f"missing numeric answer for {node.id}:{spec.metric}")
    return _clean_number(float(value), spec.decimals)


def _measurement_value(graph: CadGraph, entity_id: str, metric: str) -> Any:
    measurements = graph.measurements_for(entity_id, metric)
    if not measurements:
        return None
    return measurements[0].value


def _target_type_has_full_coordinates(graph: CadGraph, target_type: str) -> bool:
    nodes = graph.nodes_by_type(target_type)
    if not nodes:
        return False
    return all(_point_value(graph, node.id, "coordinate") is not None for node in nodes)


def _target_type_has_any_selector_expression(graph: CadGraph, target_type: str) -> bool:
    nodes = graph.nodes_by_type(target_type)
    return any(selector_expression_for_entity(graph, node.id) is not None for node in nodes)


def _selector_expression_for_selector(graph: CadGraph, selector: Node) -> str | None:
    parts = _selector_expression_parts(graph, selector)
    if parts is None:
        return None
    return _selector_expression_from_parts(*parts)


def _selector_expression_parts(graph: CadGraph, selector: Node) -> tuple[str, str, str | None] | None:
    operation = _selector_operation(graph, selector.id)
    selector_kind = str(
        (operation.properties.get("operation") if operation is not None else None)
        or selector.properties.get("selector_kind")
        or ""
    )
    if selector_kind not in {"faces", "edges", "vertices"}:
        return None
    base = operation.properties.get("base") if operation is not None else _snapshot_selector_base(graph, selector)
    if not isinstance(base, str) or not base:
        return None
    args = operation.properties.get("args") if operation is not None else None
    selector_text = args[0] if isinstance(args, list) and args else selector.properties.get("selector")
    return base, selector_kind, str(selector_text) if selector_text not in (None, "") else None


def _selector_expression_from_parts(base: str, selector_kind: str, selector_text: str | None) -> str:
    if selector_text is None or selector_text == "":
        return f"{base}.{selector_kind}()"
    return f"{base}.{selector_kind}({_quoted_selector_text(str(selector_text))})"


def _selector_operation(graph: CadGraph, selector_id: str) -> Node | None:
    for relation in graph.relations:
        if relation.source_id != selector_id or relation.type != "selected_by":
            continue
        node = graph.node(relation.target_id)
        if node is not None and node.type == "operation":
            return node
    return None


def _selector_for_selected_entity(graph: CadGraph, node: Node) -> Node | None:
    selector_relations = {
        "selected_by",
        f"has_kernel_stable_{node.type}_id",
        "has_stable_face_id",
    }
    for relation in graph.relations:
        if relation.source_id != node.id or relation.type not in selector_relations:
            continue
        selector = graph.node(relation.target_id)
        if selector is not None and selector.type == "selector":
            return selector
    return None


def _snapshot_selector_base(graph: CadGraph, selector: Node) -> str | None:
    feature_id = selector.properties.get("feature_id")
    if isinstance(feature_id, str):
        feature = graph.node(feature_id)
        if feature is not None:
            source_ref = _source_ref_answer(feature)
            if source_ref and ":" not in source_ref:
                return source_ref
        if feature_id.startswith("feature:"):
            candidate = feature_id.removeprefix("feature:").split(":", 1)[0]
            if candidate:
                return candidate
    label = selector.properties.get("selector_label")
    if isinstance(label, str):
        parts = label.split()
        if len(parts) == 2 and parts[1] in {"faces", "edges", "vertices"} and ":" not in parts[0]:
            return parts[0]
    return None


def _quoted_selector_text(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _query_description_metrics(query: Any) -> list[str]:
    metrics: list[str] = []
    for value in (
        getattr(query, "aggregation_metric", None),
        getattr(query, "tie_break_metric", None),
    ):
        if isinstance(value, str) and value:
            metrics.append(value)
    for clause in getattr(query, "clauses", []) or []:
        for attr in ("metric", "reference_metric"):
            value = getattr(clause, attr, None)
            if isinstance(value, str) and value:
                metrics.append(value)
    spec = normalize_answer_spec(
        getattr(query, "answer_spec", None),
        target_type=getattr(query, "target_type", None),
        answer_type=getattr(query, "answer_type", None),
    )
    if spec.metric:
        metrics.append(spec.metric)
    return list(dict.fromkeys(metrics))


def _candidate_description(
    graph: CadGraph,
    entity_id: str,
    *,
    metric_names: list[str] | None = None,
) -> str:
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
    if node_type in {"feature", "operation", "profile", "workplane", "material_region", "void_region"}:
        return _source_like_description(graph, entity_id, node, metric_names or [])
    return _fallback_description(entity_id, node)


def _edge_description(graph: CadGraph, entity_id: str, node: Node | None) -> str:
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
    midpoint_distance = _measurement_value(graph, entity_id, "midpoint_distance_to_origin")
    if isinstance(midpoint_distance, (int, float)):
        parts.append(f"midpoint distance to origin {_format_number(float(midpoint_distance))}")
    return "; ".join(parts) if parts else _fallback_description(entity_id, node)


def _face_description(graph: CadGraph, entity_id: str, node: Node | None) -> str:
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
    distance = _measurement_value(graph, entity_id, "distance_to_origin")
    if isinstance(distance, (int, float)):
        parts.append(f"distance to origin {_format_number(float(distance))}")
    bbox_text = _bbox_description(bbox)
    if bbox_text:
        parts.append(bbox_text)
    return "; ".join(parts) if parts else _fallback_description(entity_id, node)


def _path_segment_description(graph: CadGraph, entity_id: str, node: Node | None) -> str:
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


def _selector_description(graph: CadGraph, entity_id: str, node: Node | None) -> str:
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


def _point_value(graph: CadGraph, entity_id: str, metric: str) -> list[float | int] | None:
    value = _measurement_value(graph, entity_id, metric)
    node = graph.node(entity_id)
    if value is None and node is not None:
        value = node.properties.get(metric)
    if _is_point(value):
        return [_clean_number(float(component), DEFAULT_DECIMALS) for component in value]
    return None


def _point_component_parts(graph: CadGraph, entity_id: str, label: str, metric_prefix: str) -> list[str]:
    parts = []
    for axis in ("x", "y", "z"):
        value = _measurement_value(graph, entity_id, f"{metric_prefix}_{axis}")
        if isinstance(value, (int, float)):
            parts.append(f"{label} {axis.upper()} {_format_number(float(value))}")
    return parts


def _selection_geometry_parts(graph: CadGraph, entity_id: str) -> list[str]:
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


def _source_like_description(
    graph: CadGraph,
    entity_id: str,
    node: Node | None,
    metric_names: list[str],
) -> str:
    if node is None:
        return _fallback_description(entity_id, node)
    parts = []
    source_ref = _source_ref_answer(node)
    if source_ref and ":" not in source_ref:
        parts.append(f"source variable {source_ref}")
    if node.source_ref is not None:
        parts.append(f"source line {node.source_ref}")
    operation = node.properties.get("operation") or node.properties.get("kind") or node.properties.get("plane")
    if operation is not None:
        parts.append(f"{node.type.replace('_', ' ')} operation {operation}")
    for key, label in (("step_index", "step"), ("operation_index", "operation index")):
        value = node.properties.get(key)
        if isinstance(value, (int, float)):
            parts.append(f"{label} {_format_number(float(value))}")
    for metric in metric_names:
        metric_text = _metric_value_description(graph, entity_id, metric)
        if metric_text is not None:
            parts.append(metric_text)
    return "; ".join(list(dict.fromkeys(parts))) if parts else _fallback_description(entity_id, node)


def _metric_value_description(graph: CadGraph, entity_id: str, metric: str) -> str | None:
    value = _measurement_value(graph, entity_id, metric)
    if value is None:
        node = graph.node(entity_id)
        value = node.properties.get(metric) if node is not None else None
    label = metric.replace("_", " ")
    if isinstance(value, (int, float)):
        return f"{label} {_format_candidate_metric_number(float(value))}"
    if _is_point(value):
        return f"{label} {_format_point(value)}"
    bbox_text = _bbox_description(value)
    if bbox_text:
        return f"{label} {bbox_text}"
    return None


def _format_candidate_metric_number(value: float) -> str:
    cleaned = _clean_number(value, DEFAULT_DECIMALS)
    if cleaned == 0 and value != 0:
        return f"{value:.6e}"
    return str(cleaned)


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


def _stable_index(key: str, count: int) -> int:
    if count <= 0:
        return 0
    return sum(ord(char) for char in key) % count


def _rotate(values: list[str], offset: int) -> list[str]:
    if not values:
        return []
    shift = offset % len(values)
    return values[shift:] + values[:shift]


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
