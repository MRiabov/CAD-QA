"""Validate the root prompt-template artifact against its documented schema."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

PROMPTS = Path(__file__).resolve().parents[1] / "prompts.yaml"

TOP_LEVEL_KEYS = {"schema_version", "version", "namespaces"}
NAMESPACE_KEYS = {"labels", "templates"}
TEMPLATE_KEYS = {"variants", "placeholders"}
NAMESPACES = {"dataset", "evaluation"}

PLACEHOLDER_FORMS = {
    "text",
    "number",
    "integer",
    "boolean",
    "coordinate",
    "reference",
    "list",
    "numbered_list",
    "code",
}
PLACEHOLDER = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")
P0_LABEL_TABLES = {
    "target_category",
    "metric",
    "comparator",
    "relation",
    "unit",
    "position_parameter",
    "counted_entity",
    "frame",
    "choice_label",
}
HIDDEN_PLACEHOLDERS = {
    "gold_answer",
    "answer",
    "answer_sha256",
    "answer_evidence",
    "task_id",
    "program_id",
    "program_sha256",
    "node_id",
    "relation_id",
    "clue_id",
}
UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)

REQUIRED_IDS = {
    "dataset.prompt_shell",
    "dataset.question.identity",
    "dataset.question.volume",
    "dataset.question.area",
    "dataset.question.length",
    "dataset.question.distance",
    "dataset.question.angle",
    "dataset.question.count",
    "dataset.question.membership",
    "dataset.question.position",
    "dataset.question.extent",
    "dataset.question.material_change",
    "dataset.question.topology_change",
    "dataset.clue.property.threshold",
    "dataset.clue.property.range",
    "dataset.clue.relation",
    "dataset.clue.comparison",
    "dataset.clue.provenance.operation",
    "dataset.clue.provenance.profile",
    "dataset.clue.provenance.workplane",
    "dataset.choice.description",
    "dataset.answer_instruction.multiple_choice",
    "dataset.answer_instruction.number.with_unit",
    "dataset.answer_instruction.number.unitless",
    "dataset.answer_instruction.integer",
    "dataset.answer_instruction.boolean",
    "dataset.answer_instruction.coordinate",
    "dataset.answer_instruction.bounding_box",
    "evaluation.system.no_cadquery",
    "evaluation.submission.answer",
}

FRAME_CONVENTION = (
    "Directions use the program frame: +x is right, +y is back, +z is up."
)


class _UniqueKeyLoader(yaml.SafeLoader):
    """A YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate key {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def load_prompts() -> dict[str, Any]:
    data = yaml.load(PROMPTS.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    assert isinstance(data, dict)
    return data


def test_prompt_templates_file_shape() -> None:
    data = load_prompts()
    assert set(data) == TOP_LEVEL_KEYS
    assert isinstance(data["schema_version"], int)
    assert data["schema_version"] >= 1
    assert isinstance(data["version"], str)
    assert data["version"].strip()
    assert isinstance(data["namespaces"], dict)
    assert set(data["namespaces"]) == NAMESPACES


def test_prompt_template_namespaces_and_templates() -> None:
    data = load_prompts()
    seen_ids: set[str] = set()
    for namespace_name, namespace in data["namespaces"].items():
        assert set(namespace) == NAMESPACE_KEYS
        labels = namespace["labels"]
        assert isinstance(labels, dict)
        if namespace_name == "dataset":
            assert set(labels) == P0_LABEL_TABLES
        else:
            assert labels == {}
        for table_name, table in labels.items():
            assert isinstance(table_name, str) and table_name
            assert isinstance(table, dict) and table
            for key, label in table.items():
                assert isinstance(key, str) and key
                assert isinstance(label, str) and label.strip()

        templates = namespace["templates"]
        assert isinstance(templates, dict) and templates
        for template_id, template in templates.items():
            assert template_id.startswith(f"{namespace_name}.")
            assert template_id not in seen_ids
            seen_ids.add(template_id)
            assert set(template) == TEMPLATE_KEYS

            variants = template["variants"]
            assert isinstance(variants, list) and variants
            placeholders = template["placeholders"]
            assert isinstance(placeholders, dict)
            for name, form in placeholders.items():
                assert isinstance(name, str) and name
                assert name not in HIDDEN_PLACEHOLDERS
                assert isinstance(form, str) and form
                if form.startswith("label."):
                    table_name = form.removeprefix("label.")
                    assert table_name in labels, (
                        f"{template_id}: unknown label table {table_name}"
                    )
                else:
                    assert form in PLACEHOLDER_FORMS, (
                        f"{template_id}: unknown placeholder form {form}"
                    )

            for variant in variants:
                assert isinstance(variant, str) and variant.strip()
                assert not UUID.search(variant), (
                    f"{template_id}: hidden identifier in variant"
                )
                used = set(PLACEHOLDER.findall(variant))
                assert used == set(placeholders), (
                    f"{template_id}: variant placeholders {sorted(used)} do not "
                    f"match declarations {sorted(placeholders)}"
                )
                stripped = PLACEHOLDER.sub("", variant)
                assert "{{" not in stripped and "}}" not in stripped, (
                    f"{template_id}: malformed placeholder braces"
                )


def test_required_prompt_templates_exist() -> None:
    data = load_prompts()
    ids = {
        template_id
        for namespace in data["namespaces"].values()
        for template_id in namespace["templates"]
    }
    assert REQUIRED_IDS <= ids


def test_prompt_shell_frame_convention() -> None:
    data = load_prompts()
    shell = data["namespaces"]["dataset"]["templates"]["dataset.prompt_shell"]
    assert len(shell["variants"]) == 1
    assert shell["variants"][0].startswith(FRAME_CONVENTION)
