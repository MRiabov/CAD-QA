"""Compile mock ontology relation atoms into translator packets.

This is the missing pre-translator layer for the mock experiment:

    ontology/trace atoms -> canonical clue text -> optional LLM translator

The compiler is intentionally simple. It demonstrates which parts can be
deterministic and where the real generator would need richer rule coverage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology-packets", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    sources = {row["source_id"]: row for row in read_jsonl(args.sources)}
    packets = list(read_jsonl(args.ontology_packets))
    compiled = [compile_packet(packet, sources[packet["source_id"]]) for packet in packets]

    args.output_json.write_text(json.dumps(compiled, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(compiled, packets), encoding="utf-8")
    print(f"wrote {args.output_json}")
    print(f"wrote {args.output_md}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
    return rows


def compile_packet(packet: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    approved_clues = [compile_clause(clause) for clause in packet["raw_clauses"]]
    allowed_terms = sorted(
        {
            term
            for clue in approved_clues
            for term in clue.get("allowed_terms", [])
        }
    )
    return {
        "sample_id": packet["sample_id"],
        "packet_version": "cadqa_translator_input_compiled_mock_v0",
        "role": "question_translator",
        "source_id": packet["source_id"],
        "public_source_code": "\n".join(source["code_lines"]),
        "render_request": {
            "style": packet["style"],
            "answer_type": packet["answer_type"],
            "answer_instruction": packet["answer_instruction"],
            "audience": "CAD benchmark model reading CadQuery code",
            "target_difficulty": packet["target_difficulty"],
            "rewrite_goal": (
                "Rewrite the canonical clues into a natural public question "
                "without adding facts or exposing forbidden strings."
            ),
        },
        "approved_clues": [
            {
                "clause_id": clue["clause_id"],
                "constraint_type": clue["constraint_type"],
                "canonical_text": clue["canonical_text"],
                "leakage_risk": clue.get("leakage_risk", "normal"),
            }
            for clue in approved_clues
        ],
        "allowed_terms": allowed_terms,
        "forbidden_question_strings": packet["forbidden_question_strings"],
        "forbidden_content": [
            "Do not reveal the gold answer.",
            "Do not mention hidden predicates, candidate sets, evidence chains, verifier status, or distractor analysis.",
            "Do not add new CAD facts that are not present in approved_clues.",
            "Do not ask for an explanation or chain of thought.",
            "Do not refer to source line numbers.",
        ],
        "output_schema": {
            "question": "string",
            "clue_map": [{"clause_id": "string", "text_span": "string"}],
            "self_check": {
                "forbidden_strings_present": "boolean",
                "unsupported_cad_facts": "array",
                "ambiguous_phrases": "array",
            },
        },
    }


def compile_clause(clause: dict[str, Any]) -> dict[str, Any]:
    relation = clause["relation"]
    args = clause["arguments"]
    phrase, terms, leakage_risk = verbalize(relation, args)
    return {
        "clause_id": clause["clause_id"],
        "constraint_type": clause["constraint_type"],
        "relation": relation,
        "canonical_text": phrase,
        "allowed_terms": terms,
        "leakage_risk": leakage_risk,
    }


def verbalize(relation: str, args: dict[str, Any]) -> tuple[str, list[str], str]:
    if relation == "operation_with_material_effect":
        operation = str(args["operation"])
        effect = str(args["material_effect"])
        entity = str(args.get("entity_label", "feature"))
        return (
            f"The target is a {effect} {operation} {entity}.",
            ["target", effect, operation, entity],
            "normal",
        )

    if relation == "operation_has_prior_count":
        operation = pluralize(str(args["operation"]))
        prior_count = number_word(int(args["prior_count"]))
        scope = str(args.get("scope", "sequence"))
        return (
            f"The target comes after {prior_count} earlier {operation} in the {scope}.",
            ["target", operation, scope],
            "normal",
        )

    if relation == "feature_placed_from_selected_face":
        face_role = str(args["face_role"])
        state = str(args["source_state"])
        via = str(args["via"])
        return (
            f"The target is placed from a {via} made from the {face_role} of the {state}.",
            ["target", via, face_role, state],
            "normal",
        )

    if relation == "parameter_sign_in_pattern":
        parameter = str(args["parameter"])
        axis = str(args["axis"])
        sign = str(args["sign"])
        scope = str(args["scope"])
        return (
            f"The target's {parameter} lies on the {sign}-{axis} side of the {scope}.",
            ["target", parameter, f"{sign}-{axis}", scope],
            "normal",
        )

    if relation == "metric_bundle":
        material_effect = str(args["material_effect"])
        bbox_effect = str(args["bbox_effect"])
        return (
            f"The target {material_effect} and {bbox_effect}.",
            ["target", material_effect, bbox_effect],
            "normal",
        )

    if relation == "profile_operation_extruded_feature":
        profile_operation = str(args["profile_operation"])
        object_label = str(args["object_label"])
        negative = " and not ".join(str(item) for item in args.get("negative_classes", []))
        return (
            f"The target is an extruded {object_label}, not {negative}.",
            ["target", "extruded", object_label, profile_operation, negative],
            "normal",
        )

    if relation == "profile_and_feature_parameters":
        profile_name = str(args["profile_parameter_name"])
        profile_value = args["profile_parameter_value"]
        feature_name = str(args["feature_parameter_name"])
        feature_value = args["feature_parameter_value"]
        return (
            f"The target uses {profile_name} {profile_value} and {feature_name} {feature_value}.",
            ["target", profile_name, str(profile_value), feature_name, str(feature_value)],
            "normal",
        )

    if relation == "argmax_workplane_coordinate":
        reference = str(args["reference"])
        coordinate = str(args["coordinate"])
        entity_set = str(args["entity_set"])
        return (
            f"The target's {reference} has the greatest {coordinate} coordinate among the {entity_set}.",
            ["target", reference, coordinate, entity_set],
            "normal",
        )

    if relation == "input_to_accumulated_union":
        target_label = str(args["target_label"])
        leakage_risk = str(args.get("leakage_risk", "normal"))
        return (
            f"The target feeds the {target_label}.",
            ["target", target_label],
            leakage_risk,
        )

    if relation == "profile_operation_cut_kind":
        object_label = str(args["object_label"])
        negative = " or ".join(str(item) for item in args.get("negative_classes", []))
        return (
            f"The target is a {object_label}, not a {negative}.",
            ["target", object_label, negative],
            "normal",
        )

    if relation == "selector_face_axis_direction":
        direction = str(args["direction"])
        axis = str(args["axis"])
        entity_label = str(args["entity_label"])
        return (
            f"The target is made from the {direction}-{axis} {entity_label}.",
            ["target", f"{direction}-{axis}", entity_label],
            "normal",
        )

    if relation == "rect_parameters_symbolic":
        width_description = str(args["width_description"])
        height_expression = str(args["height_expression"])
        return (
            f"The target's rectangle uses the {width_description} for one side and {height_expression} for the other.",
            ["target", "rectangle", width_description, height_expression],
            "normal",
        )

    if relation == "loop_member_coordinate_sign":
        sign = str(args["sign"])
        axis = str(args["axis"])
        entity_set = str(args["entity_set"])
        return (
            f"The target is the {sign}-{axis} member of the {entity_set}.",
            ["target", f"{sign}-{axis}", entity_set],
            "normal",
        )

    raise ValueError(f"unsupported relation: {relation}")


def pluralize(word: str) -> str:
    if word.endswith("s"):
        return word
    return f"{word}s"


def number_word(value: int) -> str:
    words = {
        0: "zero",
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
    }
    return words.get(value, str(value))


def render_markdown(compiled: list[dict[str, Any]], raw_packets: list[dict[str, Any]]) -> str:
    raw_by_sample = {packet["sample_id"]: packet for packet in raw_packets}
    lines = [
        "# Ontology To Translator Packet Compilation",
        "",
        "This file shows the missing layer: low-level ontology relation atoms are",
        "compiled into canonical clue text before any LLM translator is called.",
        "",
    ]
    for packet in compiled:
        raw = raw_by_sample[packet["sample_id"]]
        lines.extend(
            [
                f"## {packet['sample_id']}",
                "",
                "### Raw Ontology Clauses",
                "",
                "```json",
                json.dumps(raw["raw_clauses"], indent=2),
                "```",
                "",
                "### Compiled Canonical Clues",
                "",
            ]
        )
        for clue in packet["approved_clues"]:
            lines.append(
                f"- `{clue['clause_id']}` `{clue['constraint_type']}` "
                f"`{clue['leakage_risk']}`: {clue['canonical_text']}"
            )
        lines.extend(
            [
                "",
                "### Translator Receives",
                "",
                "- public source code",
                "- answer type and answer instruction",
                "- compiled canonical clues",
                "- forbidden strings/content",
                "- output schema",
                "",
                "It still does not receive gold answers, predicates, candidate sets,",
                "evidence chains, distractors, or verifier status.",
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
