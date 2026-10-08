"""YAML-backed prompt templates."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from dataset.query.answers import AnswerSpec, answer_instruction, normalize_answer_spec, target_type_label


PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "prompt-templates.yaml"
TemplateEntry = str | list[str]


@lru_cache(maxsize=1)
def prompt_template_registry() -> dict[str, Any]:
    data = yaml.safe_load(PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{PROMPT_TEMPLATE_PATH} must contain a YAML mapping")
    for key in (
        "version",
        "checklist_template_id",
        "prompt_shells",
        "fallback_templates",
        "aggregation_templates",
        "tie_break_templates",
        "metric_labels",
        "clause_templates",
    ):
        if key not in data:
            raise ValueError(f"{PROMPT_TEMPLATE_PATH} missing required key: {key}")
    return data


PROMPT_VERSION = str(prompt_template_registry()["version"])
CHECKLIST_TEMPLATE_ID = str(prompt_template_registry()["checklist_template_id"])


def checklist_prompt(
    source_code: str,
    clues: list[str],
    answer_format: str,
    *,
    target_type: str | None = None,
    answer_spec: AnswerSpec | dict[str, Any] | None = None,
    candidate_lines: list[str] | None = None,
) -> str:
    shell = _string_template("prompt_shells", "checklist")
    clue_lines = "\n".join(f"- {clue}" for clue in clues)
    rendered_candidate_lines = _candidate_lines(candidate_lines or [])
    spec = normalize_answer_spec(answer_spec, target_type=target_type, answer_type=answer_format)
    prompt = shell.format(
        source_code=source_code.rstrip(),
        clue_lines=clue_lines,
        candidate_lines=rendered_candidate_lines,
        answer_format=answer_format,
        target_type_label=target_type_label(target_type),
        answer_instruction=answer_instruction(spec, target_type=target_type),
    ).rstrip()
    return prompt.replace("\n\n\nReturn exactly", "\n\nReturn exactly")


def clause_prompt(clause: Any, *, query: Any | None = None) -> str:
    templates = _template_mapping("clause_templates")
    template_key = clause_template_key(clause, query=query)
    if template_key is None:
        clause_id = getattr(clause, "id", None) or "<missing>"
        raise KeyError(f"missing prompt template for clause id: {clause_id}")
    return _select_template(templates[template_key], query=query).format(**_clause_format_values(clause, query))


def _candidate_lines(lines: list[str]) -> str:
    if not lines:
        return ""
    rendered = "\n".join(f"- {line}" for line in lines)
    return f"\nCandidate labels:\n{rendered}"


def aggregation_prompt(aggregation: str, metric: str, *, rank: int | None = None, query: Any | None = None) -> str:
    templates = _template_mapping("aggregation_templates")
    template = _select_template(templates[aggregation_template_key(aggregation, metric)], query=query)
    target_type = getattr(query, "target_type", None) if query is not None else None
    return template.format(
        metric=metric,
        metric_label=metric_label(metric, target_type=target_type),
        rank=rank,
        rank_label=_rank_label(rank),
        target_point_label=metric_label(_sampled_parameter_value(query, "target_point_metric") or "midpoint"),
        reference_type_label=_entity_type_label(_sampled_parameter_value(query, "reference_type") or "feature"),
        reference_point_label=metric_label(_sampled_parameter_value(query, "reference_point_metric") or "centroid"),
    )


def tie_break_prompt(aggregation: str, metric: str, *, query: Any | None = None) -> str:
    templates = _template_mapping("tie_break_templates")
    template = _select_template(templates[tie_break_template_key(aggregation, metric)], query=query)
    target_type = getattr(query, "target_type", None) if query is not None else None
    return template.format(metric=metric, metric_label=metric_label(metric, target_type=target_type))


def clause_template_key(clause: Any, *, query: Any | None = None) -> str | None:
    """Return the YAML template key used for a rendered Gold query predicate."""

    return _clause_template_key(clause, query, _template_mapping("clause_templates"))


def clause_template_id(clause: Any, *, query: Any | None = None) -> str | None:
    """Return the rendered YAML clue-template identifier, including wording variant."""

    key = clause_template_key(clause, query=query)
    if key is None:
        return None
    return _template_id_with_variant(key, _template_mapping("clause_templates")[key], query)


def aggregation_template_key(aggregation: str, metric: str) -> str:
    """Return the YAML template key used for an aggregation clue."""

    templates = _template_mapping("aggregation_templates")
    key = f"{aggregation}.{metric}"
    return key if key in templates else aggregation


def aggregation_template_id(aggregation: str, metric: str, *, query: Any | None = None) -> str:
    """Return the rendered aggregation-template identifier, including wording variant."""

    key = aggregation_template_key(aggregation, metric)
    return _template_id_with_variant(key, _template_mapping("aggregation_templates")[key], query)


def tie_break_template_key(aggregation: str, metric: str) -> str:
    """Return the YAML template key used for a tie-break clue."""

    templates = _template_mapping("tie_break_templates")
    key = f"{aggregation}.{metric}"
    return key if key in templates else aggregation


def tie_break_template_id(aggregation: str, metric: str, *, query: Any | None = None) -> str:
    """Return the rendered tie-break template identifier, including wording variant."""

    key = tie_break_template_key(aggregation, metric)
    return _template_id_with_variant(key, _template_mapping("tie_break_templates")[key], query)


def metric_label(metric: str, *, target_type: str | None = None) -> str:
    if target_type == "face":
        face_label = _face_metric_label(metric)
        if face_label is not None:
            return face_label
    labels = _template_mapping("metric_labels")
    value = labels.get(metric)
    if isinstance(value, list):
        return value[0]
    return value if isinstance(value, str) else metric.replace("_", " ")


def metric_subject_label(metric: str, *, target_type: str | None = None) -> str:
    if target_type == "face" and metric in {
        "coordinate_x",
        "coordinate_y",
        "coordinate_z",
        "distance_to_origin",
    }:
        return "face center"
    return target_type.replace("_", " ") if isinstance(target_type, str) and target_type else "entity"


def metric_property_label(metric: str, *, target_type: str | None = None) -> str:
    if target_type == "face":
        return {
            "coordinate_x": "X coordinate",
            "coordinate_y": "Y coordinate",
            "coordinate_z": "Z coordinate",
            "distance_to_origin": "distance to the global origin",
            "face_area": "surface area",
        }.get(metric, metric_label(metric))
    return metric_label(metric, target_type=target_type)


def _face_metric_label(metric: str) -> str | None:
    return {
        "coordinate_x": "face center X coordinate",
        "coordinate_y": "face center Y coordinate",
        "coordinate_z": "face center Z coordinate",
        "distance_to_origin": "face center distance to the global origin",
        "face_area": "surface area",
    }.get(metric)


def _entity_type_label(entity_type: str) -> str:
    if entity_type == "edge_endpoint":
        return "endpoint"
    if entity_type == "material_region":
        return "added-material region"
    if entity_type == "void_region":
        return "removed-material region"
    return entity_type.replace("_", " ")


def no_clause_prompt(target_type: str) -> str:
    template = _string_template("fallback_templates", "no_clause_target")
    return template.format(target_type=target_type)


def _clause_template_key(clause: Any, query: Any | None, templates: dict[str, TemplateEntry]) -> str | None:
    clause_id = getattr(clause, "id", None)
    if not clause_id:
        return None
    target_type = getattr(query, "target_type", None) if query is not None else None
    query_id = getattr(query, "query_id", None) if query is not None else None
    keys = []
    if isinstance(query_id, str) and ":" in query_id:
        keys.append(f"{query_id.rsplit(':', 1)[-1]}.{clause_id}")
    if target_type:
        keys.append(f"{target_type}.{clause_id}")
    keys.append(str(clause_id))
    return next((key for key in keys if key in templates), None)


def _clause_format_values(clause: Any, query: Any | None) -> dict[str, Any]:
    values = {
        "id": getattr(clause, "id", None),
        "kind": getattr(clause, "kind", None),
        "relation": getattr(clause, "relation", None),
        "target_type": getattr(clause, "target_type", None),
        "metric": getattr(clause, "metric", None),
        "reference_metric": getattr(clause, "reference_metric", None),
        "operator": getattr(clause, "operator", None),
        "value": getattr(clause, "value", None),
    }
    if isinstance(values["value"], dict):
        values.update(values["value"])
    if isinstance(values["metric"], str):
        metric_target_type = _clause_metric_target_type(clause, query)
        values["metric_label"] = metric_label(values["metric"], target_type=metric_target_type)
        values["metric_subject_label"] = metric_subject_label(values["metric"], target_type=metric_target_type)
        values["metric_property_label"] = metric_property_label(values["metric"], target_type=metric_target_type)
    if isinstance(values["relation"], str):
        values["relation_label"] = relation_label(values["relation"])
    if isinstance(values["operator"], str):
        values["operator_label"] = _operator_label(values["operator"])
    if query is not None:
        values["query_id"] = getattr(query, "query_id", None)
        values["query_target_type"] = getattr(query, "target_type", None)
    return values


def _clause_metric_target_type(clause: Any, query: Any | None) -> str | None:
    clause_id = getattr(clause, "id", None)
    if clause_id in {
        "has_parameterized_selected_face_metric_threshold",
        "has_parameterized_face_metric",
        "has_parameterized_face_metric_threshold",
        "has_parameterized_equal_face_metric_value",
    }:
        return "face"
    return getattr(query, "target_type", None) if query is not None else None


def _string_template(section: str, key: str) -> str:
    mapping = _template_mapping(section)
    if key not in mapping:
        raise KeyError(f"missing prompt template: {section}.{key}")
    return _select_template(mapping[key])


def _template_mapping(section: str) -> dict[str, TemplateEntry]:
    value = prompt_template_registry().get(section)
    if not isinstance(value, dict):
        raise ValueError(f"{PROMPT_TEMPLATE_PATH} section must be a mapping: {section}")
    if not all(isinstance(key, str) and _valid_template_entry(template) for key, template in value.items()):
        raise ValueError(f"{PROMPT_TEMPLATE_PATH} section must map strings to strings or string lists: {section}")
    return value


def _valid_template_entry(value: Any) -> bool:
    return isinstance(value, str) or (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item for item in value)
    )


def _select_template(entry: TemplateEntry, *, query: Any | None = None) -> str:
    if isinstance(entry, str):
        return entry
    index = _wording_variant_index(query)
    return entry[index % len(entry)]


def _template_id_with_variant(key: str, entry: TemplateEntry, query: Any | None) -> str:
    if isinstance(entry, str) or not _has_explicit_wording_variant(query):
        return key
    return f"{key}.variant_{_wording_variant_index(query) % len(entry)}"


def _has_explicit_wording_variant(query: Any | None) -> bool:
    sampled = getattr(query, "sampled_parameters", None)
    return isinstance(sampled, Mapping) and "prompt_wording_variant" in sampled


def _wording_variant_index(query: Any | None) -> int:
    sampled = getattr(query, "sampled_parameters", None)
    if not isinstance(sampled, Mapping):
        return 0
    raw = sampled.get("prompt_wording_variant")
    values = raw if isinstance(raw, list) else [raw]
    for value in values:
        if value is None:
            continue
        text = str(value).removeprefix("variant_")
        if text.isdigit():
            return int(text)
    return 0


def _operator_label(operator: str) -> str:
    return {
        ">": "greater than",
        ">=": "at least",
        "<": "less than",
        "<=": "at most",
        "==": "equal to",
    }.get(operator, operator)


def relation_label(relation: str) -> str:
    return {
        "adjacent_to": "adjacent to",
        "coaxial_with": "coaxial with",
        "coplanar_with": "coplanar with",
        "intersects": "intersecting",
        "opposite_to": "opposite to",
        "perpendicular_to": "perpendicular to",
        "parallel_to": "parallel to",
        "same_length_as": "the same length as",
        "longer_than": "longer than",
        "shorter_than": "shorter than",
        "same_selected_face_as": "selects the same face as",
        "same_selected_entity_as": "selects the same model entity as",
        "contained_in": "contained in",
        "endpoint_of": "an endpoint of",
    }.get(relation, relation.replace("_", " "))


def _sampled_parameter_value(query: Any | None, key: str) -> str | None:
    sampled = getattr(query, "sampled_parameters", None)
    if not isinstance(sampled, Mapping):
        return None
    raw = sampled.get(key)
    values = raw if isinstance(raw, list) else [raw]
    for value in values:
        if value is not None:
            return str(value)
    return None


def _rank_label(rank: int | None) -> str:
    if rank is None:
        return ""
    if 10 <= rank % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    return f"{rank}{suffix}"
