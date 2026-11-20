"""Validate the checked-in golden records against their documented format."""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from pathlib import Path
from typing import Any

GOLDEN_DIR = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "dataset"
    / "implementation"
    / "pipeline"
    / "testing"
    / "golden"
)

TOP_LEVEL_KEYS = {
    "schema_version",
    "golden_id",
    "construction",
    "program",
    "task",
    "clues",
    "answer",
}
CONSTRUCTION_KEYS = {
    "constructor_version",
    "construction_seed",
    "definition_schema_version",
    "graph_schema_version",
}
PROGRAM_KEYS = {"program_id", "program_sha256", "text"}
TASK_KEYS = {
    "target_category",
    "state_scope",
    "possible_answer_count",
    "task_reasoning_step_count",
    "answer_meaning",
    "native_answer_format",
    "answer_format",
    "geometry_required",
}
CLUE_KEYS = {
    "order",
    "clue_type",
    "clue_operand_form",
    "statement",
    "subject",
    "check",
    "narrows",
}
NARROWS_KEYS = {"before", "after"}
ANSWER_KEYS = {
    "gold_answer",
    "answer_unit",
    "tolerance",
    "scoring_rule",
    "answer_schema_version",
    "answer_evidence",
}
EVIDENCE_KEYS = {
    "evidence_kind",
    "evidence_rule",
    "evidence_refs",
    "answer_equivalent_set",
    "point_probe",
}
EQUIVALENT_ENTRY_KEYS = {"subject", "answer"}
EVIDENCE_REF_KINDS = {"node", "relation", "measurement"}
CLUE_TYPES = {"property", "relation", "comparison", "aggregation", "provenance"}
OPERAND_FORMS = {"named", "selected", "aggregated", "cross_state"}
EVIDENCE_KINDS = {"measured", "derived"}
SCORING_RULES = {"exact", "numeric_tolerance", "structured_exact"}
TARGET_CATEGORIES = {
    "cadquery_program",
    "operation",
    "feature",
    "solid_state",
    "face",
    "edge",
    "vertex",
    "edge_endpoint",
    "cadquery_profile",
    "cadquery_workplane",
    "path",
    "path_point",
    "path_segment",
    "region",
    "cadquery_selector_result",
    "scalar_value",
}
ANSWER_MEANINGS = {
    "identity",
    "volume",
    "area",
    "length",
    "distance",
    "angle",
    "count",
    "rank",
    "membership",
    "validity",
    "position",
    "extent",
    "cadquery_workplane_state",
    "material_change",
    "topology_change",
}
ANSWER_FORMATS = {
    "multiple_choice",
    "number",
    "integer",
    "yes_no",
    "coordinate",
    "bounding_box",
    "structured_object",
}
BINDING_KIND_TO_OPERAND_FORM = {
    "named": "named",
    "clue_result": "selected",
    "aggregated": "aggregated",
    "cross_state": "cross_state",
}
BINDING_KINDS = {
    "target",
    "clue_result",
    "named",
    "literal",
    "aggregated",
    "cross_state",
}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load_records() -> list[tuple[Path, dict[str, Any]]]:
    paths = sorted(GOLDEN_DIR.glob("*.json"))
    assert paths, f"no golden records under {GOLDEN_DIR}"
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n"), (
            f"{path.name}: golden record needs a trailing newline"
        )
        data = json.loads(text)
        assert isinstance(data, dict), f"{path.name}: top level is not an object"
        records.append((path, data))
    return records


def test_golden_records_are_discoverable() -> None:
    seen: set[str] = set()
    for path, data in load_records():
        golden_id = data.get("golden_id")
        assert isinstance(golden_id, str), f"{path.name}: golden_id is not a string"
        assert SLUG.match(golden_id), (
            f"{path.name}: golden_id {golden_id!r} is not a slug"
        )
        assert path.stem == golden_id, (
            f"{path.name}: file stem does not match golden_id {golden_id!r}"
        )
        assert golden_id not in seen, f"{path.name}: duplicate golden_id {golden_id!r}"
        seen.add(golden_id)


def test_golden_record_shape() -> None:
    for path, data in load_records():
        assert set(data) == TOP_LEVEL_KEYS, (
            f"{path.name}: top-level keys {sorted(data)} do not match {sorted(TOP_LEVEL_KEYS)}"
        )
        assert (
            isinstance(data["schema_version"], int) and data["schema_version"] >= 1
        ), f"{path.name}: schema_version must be a positive integer"

        construction = data["construction"]
        assert set(construction) == CONSTRUCTION_KEYS, (
            f"{path.name}: construction keys {sorted(construction)} do not match "
            f"{sorted(CONSTRUCTION_KEYS)}"
        )
        for key in (
            "constructor_version",
            "definition_schema_version",
            "graph_schema_version",
        ):
            value = construction[key]
            assert isinstance(value, str) and value.strip(), (
                f"{path.name}: construction.{key} must be a non-empty string"
            )
        seed = construction["construction_seed"]
        assert isinstance(seed, int) and not isinstance(seed, bool) and seed >= 0, (
            f"{path.name}: construction.construction_seed must be a non-negative integer"
        )

        program = data["program"]
        assert set(program) == PROGRAM_KEYS, (
            f"{path.name}: program keys {sorted(program)} do not match {sorted(PROGRAM_KEYS)}"
        )

        task = data["task"]
        assert set(task) == TASK_KEYS, (
            f"{path.name}: task keys {sorted(task)} do not match {sorted(TASK_KEYS)}"
        )
        assert task["target_category"] in TARGET_CATEGORIES, (
            f"{path.name}: unknown target_category {task['target_category']!r}"
        )
        assert task["state_scope"] == "final", (
            f"{path.name}: P0 state_scope must be 'final'"
        )
        assert (
            isinstance(task["possible_answer_count"], int)
            and task["possible_answer_count"] > 0
        ), f"{path.name}: possible_answer_count must be a positive integer"
        assert (
            isinstance(task["task_reasoning_step_count"], int)
            and task["task_reasoning_step_count"] >= 1
        ), f"{path.name}: task_reasoning_step_count must be a positive integer"
        assert task["answer_meaning"] in ANSWER_MEANINGS, (
            f"{path.name}: unknown answer_meaning {task['answer_meaning']!r}"
        )
        assert task["native_answer_format"] in ANSWER_FORMATS, (
            f"{path.name}: unknown native_answer_format {task['native_answer_format']!r}"
        )
        assert task["answer_format"] in ANSWER_FORMATS, (
            f"{path.name}: unknown answer_format {task['answer_format']!r}"
        )
        assert isinstance(task["geometry_required"], bool), (
            f"{path.name}: geometry_required must be a boolean"
        )

        clues = data["clues"]
        assert isinstance(clues, list) and clues, (
            f"{path.name}: clues must be a non-empty list"
        )
        for clue in clues:
            assert set(clue) == CLUE_KEYS, (
                f"{path.name}: clue keys {sorted(clue)} do not match {sorted(CLUE_KEYS)}"
            )
            assert set(clue["narrows"]) == NARROWS_KEYS, (
                f"{path.name}: narrows keys must be {sorted(NARROWS_KEYS)}"
            )
            assert isinstance(clue["statement"], str) and clue["statement"].strip(), (
                f"{path.name}: clue statement must be a non-empty string"
            )
            assert (
                isinstance(clue["subject"], dict)
                and clue["subject"].get("kind") in BINDING_KINDS
            ), f"{path.name}: clue subject must be a typed binding"
            assert isinstance(clue["check"], dict) and clue["check"], (
                f"{path.name}: clue check must be a non-empty object"
            )

        answer = data["answer"]
        assert set(answer) == ANSWER_KEYS, (
            f"{path.name}: answer keys {sorted(answer)} do not match {sorted(ANSWER_KEYS)}"
        )
        assert set(answer["answer_evidence"]) == EVIDENCE_KEYS, (
            f"{path.name}: answer_evidence keys {sorted(answer['answer_evidence'])} do not "
            f"match {sorted(EVIDENCE_KEYS)}"
        )


def test_golden_record_program_identity() -> None:
    for path, data in load_records():
        program = data["program"]
        text = program["text"]
        assert isinstance(text, str) and text, f"{path.name}: program text is empty"
        assert "\r" not in text, f"{path.name}: program text contains a carriage return"
        assert not text.startswith("\ufeff"), (
            f"{path.name}: program text starts with a BOM"
        )
        assert text.endswith("\n"), (
            f"{path.name}: program text needs one trailing newline"
        )
        assert not text.endswith("\n\n"), (
            f"{path.name}: program text has two trailing newlines"
        )

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert SHA256.match(program["program_sha256"]), (
            f"{path.name}: program_sha256 is not a lower-case SHA-256"
        )
        assert program["program_sha256"] == digest, (
            f"{path.name}: program_sha256 does not match the program text"
        )
        assert program["program_id"] == f"cadqaprog:{digest}", (
            f"{path.name}: program_id does not match program_sha256"
        )


def test_golden_record_clue_chain() -> None:
    for path, data in load_records():
        task = data["task"]
        clues = data["clues"]

        orders = [clue["order"] for clue in clues]
        assert orders == list(range(1, len(clues) + 1)), (
            f"{path.name}: clue orders {orders} are not 1..{len(clues)}"
        )
        assert clues[0]["narrows"]["before"] == task["possible_answer_count"], (
            f"{path.name}: the first clue does not start from possible_answer_count"
        )
        for earlier, later in itertools.pairwise(clues):
            assert earlier["narrows"]["after"] == later["narrows"]["before"], (
                f"{path.name}: clue {earlier['order']} does not end where clue "
                f"{later['order']} starts"
            )

        for clue in clues:
            before = clue["narrows"]["before"]
            after = clue["narrows"]["after"]
            assert isinstance(before, int) and isinstance(after, int), (
                f"{path.name}: clue {clue['order']} narrows counts must be integers"
            )
            assert before > after >= 1, (
                f"{path.name}: clue {clue['order']} must strictly narrow and leave a candidate"
            )
            assert clue["clue_type"] in CLUE_TYPES, (
                f"{path.name}: clue {clue['order']} has unknown clue_type "
                f"{clue['clue_type']!r}"
            )

            form = clue["clue_operand_form"]
            if clue["clue_type"] == "property":
                assert form is None, (
                    f"{path.name}: property clue {clue['order']} must have no operand form"
                )
            else:
                assert form in OPERAND_FORMS, (
                    f"{path.name}: clue {clue['order']} has unknown operand form {form!r}"
                )

            if clue["clue_type"] == "relation":
                binding = clue["check"].get("object")
                assert (
                    isinstance(binding, dict)
                    and binding.get("kind") in BINDING_KIND_TO_OPERAND_FORM
                ), (
                    f"{path.name}: relation clue {clue['order']} needs a typed object binding"
                )
                assert BINDING_KIND_TO_OPERAND_FORM[binding["kind"]] == form, (
                    f"{path.name}: relation clue {clue['order']} operand form does not match "
                    f"its object binding"
                )
                assert isinstance(clue["check"].get("relation_type"), str), (
                    f"{path.name}: relation clue {clue['order']} needs a relation_type"
                )
                if "direction" in clue["check"]:
                    assert clue["check"]["direction"] in {
                        "subject_to_object",
                        "object_to_subject",
                    }, (
                        f"{path.name}: relation clue {clue['order']} has unknown direction "
                        f"{clue['check']['direction']!r}"
                    )
            elif clue["clue_type"] == "comparison":
                binding = clue["check"].get("reference")
                assert (
                    isinstance(binding, dict)
                    and binding.get("kind") in BINDING_KIND_TO_OPERAND_FORM
                ), (
                    f"{path.name}: comparison clue {clue['order']} needs a typed reference binding"
                )
                assert BINDING_KIND_TO_OPERAND_FORM[binding["kind"]] == form, (
                    f"{path.name}: comparison clue {clue['order']} operand form does not match "
                    f"its reference binding"
                )

        answer_step = 0 if task["answer_meaning"] == "identity" else 1
        expected_steps = len(clues) + answer_step
        assert task["task_reasoning_step_count"] == expected_steps, (
            f"{path.name}: task_reasoning_step_count is "
            f"{task['task_reasoning_step_count']}, expected {expected_steps}"
        )

        equivalent_set = data["answer"]["answer_evidence"]["answer_equivalent_set"]
        assert clues[-1]["narrows"]["after"] == len(equivalent_set), (
            f"{path.name}: the last clue leaves {clues[-1]['narrows']['after']} candidates "
            f"but the answer-equivalent set has {len(equivalent_set)} entries"
        )


def test_golden_record_answer_evidence() -> None:
    for path, data in load_records():
        task = data["task"]
        answer = data["answer"]
        evidence = answer["answer_evidence"]

        assert isinstance(answer["gold_answer"], str) and answer["gold_answer"], (
            f"{path.name}: gold_answer must be non-empty canonical text"
        )
        assert answer["scoring_rule"] in SCORING_RULES, (
            f"{path.name}: unknown scoring_rule {answer['scoring_rule']!r}"
        )
        assert (
            isinstance(answer["answer_schema_version"], str)
            and answer["answer_schema_version"].strip()
        ), f"{path.name}: answer_schema_version must be a non-empty string"

        assert evidence["evidence_kind"] in EVIDENCE_KINDS, (
            f"{path.name}: unknown evidence_kind {evidence['evidence_kind']!r}"
        )
        assert (
            isinstance(evidence["evidence_rule"], str)
            and evidence["evidence_rule"].strip()
        ), f"{path.name}: evidence_rule must be a non-empty string"

        refs = evidence["evidence_refs"]
        assert isinstance(refs, list) and refs, (
            f"{path.name}: evidence_refs must be non-empty"
        )
        ref_subjects: set[str] = set()
        for ref in refs:
            assert isinstance(ref, dict), (
                f"{path.name}: every evidence ref must be an object"
            )
            assert ref.get("kind") in EVIDENCE_REF_KINDS, (
                f"{path.name}: unknown evidence ref kind {ref.get('kind')!r}"
            )
            if ref["kind"] == "measurement":
                assert (
                    isinstance(ref.get("measurement"), str)
                    and ref["measurement"].strip()
                ), f"{path.name}: a measurement ref needs a measurement name"
            if isinstance(ref.get("subject"), dict):
                ref_subjects.add(json.dumps(ref["subject"], sort_keys=True))

        entries = evidence["answer_equivalent_set"]
        assert isinstance(entries, list) and entries, (
            f"{path.name}: answer_equivalent_set must be non-empty"
        )
        subjects: list[str] = []
        for entry in entries:
            assert set(entry) == EQUIVALENT_ENTRY_KEYS, (
                f"{path.name}: answer-equivalent entry keys {sorted(entry)} do not match "
                f"{sorted(EQUIVALENT_ENTRY_KEYS)}"
            )
            assert isinstance(entry["subject"], dict), (
                f"{path.name}: answer-equivalent subject must be an entity descriptor"
            )
            assert isinstance(entry["answer"], str) and entry["answer"], (
                f"{path.name}: answer-equivalent answer must be non-empty canonical text"
            )
            assert entry["answer"] == answer["gold_answer"], (
                f"{path.name}: answer-equivalent entry does not give the gold answer"
            )
            subjects.append(json.dumps(entry["subject"], sort_keys=True))

        assert len(subjects) == len(set(subjects)), (
            f"{path.name}: answer_equivalent_set repeats a subject"
        )
        assert set(subjects) <= ref_subjects, (
            f"{path.name}: every answer-equivalent subject needs an evidence ref"
        )

        if task["answer_meaning"] == "membership":
            assert isinstance(evidence["point_probe"], dict), (
                f"{path.name}: a membership answer needs a point probe"
            )
        else:
            assert evidence["point_probe"] is None, (
                f"{path.name}: point_probe is only for a membership answer"
            )

        tolerance = answer["tolerance"]
        if answer["scoring_rule"] == "exact":
            assert tolerance is None, f"{path.name}: an exact answer has no tolerance"
        else:
            assert isinstance(tolerance, dict), (
                f"{path.name}: tolerance must be an object"
            )
            assert set(tolerance) == {"kind", "value"}, (
                f"{path.name}: tolerance keys must be kind and value"
            )
            assert tolerance["kind"] in {"absolute", "relative"}, (
                f"{path.name}: unknown tolerance kind {tolerance['kind']!r}"
            )
            value = tolerance["value"]
            assert (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and value > 0
            ), f"{path.name}: tolerance value must be a positive number"

        if task["answer_format"] != "multiple_choice":
            assert task["answer_format"] == task["native_answer_format"], (
                f"{path.name}: answer_format differs from native_answer_format without "
                f"multiple choice"
            )
        if task["answer_meaning"] in {"volume", "area", "length", "distance", "angle"}:
            assert (
                isinstance(answer["answer_unit"], str) and answer["answer_unit"].strip()
            ), f"{path.name}: a measurement answer needs an answer_unit"
