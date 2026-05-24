"""YAML-backed prompt templates."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "prompt-templates.yaml"


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
        "metric_labels",
        "clause_templates",
    ):
        if key not in data:
            raise ValueError(f"{PROMPT_TEMPLATE_PATH} missing required key: {key}")
    return data


PROMPT_VERSION = str(prompt_template_registry()["version"])
CHECKLIST_TEMPLATE_ID = str(prompt_template_registry()["checklist_template_id"])


def checklist_prompt(source_code: str, clues: list[str], answer_format: str) -> str:
    shell = _string_template("prompt_shells", "checklist")
    clue_lines = "\n".join(f"- {clue}" for clue in clues)
    return shell.format(
        source_code=source_code.rstrip(),
        clue_lines=clue_lines,
        answer_format=answer_format,
    ).rstrip()


def clause_prompt(clause: Any, *, query: Any | None = None) -> str:
    templates = _template_mapping("clause_templates")
    template_key = _clause_template_key(clause, query, templates)
    if template_key is None:
        clause_id = getattr(clause, "id", None) or "<missing>"
        raise KeyError(f"missing prompt template for clause id: {clause_id}")
    return templates[template_key].format(**_clause_format_values(clause, query))


def aggregation_prompt(aggregation: str, metric: str) -> str:
    templates = _template_mapping("aggregation_templates")
    template = templates.get(f"{aggregation}.{metric}") or _string_template("aggregation_templates", aggregation)
    return template.format(metric=metric, metric_label=metric_label(metric))


def metric_label(metric: str) -> str:
    labels = _template_mapping("metric_labels")
    return labels.get(metric, metric.replace("_", " "))


def no_clause_prompt(target_type: str) -> str:
    template = _string_template("fallback_templates", "no_clause_target")
    return template.format(target_type=target_type)


def _clause_template_key(clause: Any, query: Any | None, templates: dict[str, str]) -> str | None:
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
        values["metric_label"] = metric_label(values["metric"])
    if query is not None:
        values["query_id"] = getattr(query, "query_id", None)
        values["query_target_type"] = getattr(query, "target_type", None)
    return values


def _string_template(section: str, key: str) -> str:
    mapping = _template_mapping(section)
    if key not in mapping:
        raise KeyError(f"missing prompt template: {section}.{key}")
    return mapping[key]


def _template_mapping(section: str) -> dict[str, str]:
    value = prompt_template_registry().get(section)
    if not isinstance(value, dict):
        raise ValueError(f"{PROMPT_TEMPLATE_PATH} section must be a mapping: {section}")
    if not all(isinstance(key, str) and isinstance(template, str) for key, template in value.items()):
        raise ValueError(f"{PROMPT_TEMPLATE_PATH} section must map strings to strings: {section}")
    return value
