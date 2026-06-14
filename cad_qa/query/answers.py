"""Answer contracts for resolved CAD-QA query targets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from cad_qa.ontology.nodes import Node, OntologyGraph


DEFAULT_DECIMALS = 6


@dataclass(frozen=True)
class AnswerSpec:
    mode: str = "entity_id"
    answer_format: str = "entity_id"
    metric: str | None = None
    decimals: int = DEFAULT_DECIMALS


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
        )
    if answer_type and answer_type != "entity_id":
        return _spec_from_answer_type(answer_type)
    return AnswerSpec()


def synthesis_answer_spec_for_target_type(target_type: str) -> AnswerSpec:
    if target_type in {"feature", "operation", "profile", "workplane", "material_region", "void_region"}:
        return AnswerSpec(mode="source_ref", answer_format="text")
    if target_type in {"vertex", "path_point"}:
        return AnswerSpec(mode="coordinate", answer_format="coordinate", metric="coordinate")
    return AnswerSpec()


def target_type_label(target_type: str | None) -> str:
    if target_type == "edge_endpoint":
        return "edge endpoint"
    if target_type == "material_region":
        return "added-material region"
    if target_type == "void_region":
        return "removed-material region"
    return str(target_type or "entity").replace("_", " ")


def answer_instruction(spec: AnswerSpec) -> str:
    if spec.mode == "source_ref":
        return "Return exactly one source variable name, for example `wp7`."
    if spec.mode == "coordinate":
        return "Return exactly one coordinate tuple, for example `(0, 1, 3)`."
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
    return node.id


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


def _clean_number(value: float, decimals: int) -> float | int:
    rounded = round(value, decimals)
    if rounded == 0:
        rounded = 0.0
    if float(rounded).is_integer():
        return int(rounded)
    return rounded
