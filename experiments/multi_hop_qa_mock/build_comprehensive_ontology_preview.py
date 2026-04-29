"""Build a comprehensive mock ontology-to-clue preview.

This preview is intentionally outside the main CAD-QA pipeline. It selects one
or two long CadEvolve-style scripts, then emits deterministic canonical clues
covering every node type and relation type listed in
specs/multi-hop-qa-task-spec.md.

The output is for design review. It is not claiming that every clue is currently
available from production trace labels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


NODE_TYPES = [
    "source",
    "feature",
    "operation",
    "parameter",
    "workplane",
    "sketch",
    "profile",
    "solid",
    "face",
    "edge",
    "vertex",
    "axis",
    "centerline",
    "material_region",
    "selector",
    "measurement",
]

MIN_TEMPORAL_SIDE_RANGE = 5
MIN_INDIVIDUAL_CANDIDATE_COUNT = 5

RELATION_TYPES = [
    "before",
    "after",
    "immediately_before",
    "immediately_after",
    "input_to",
    "created_by",
    "modified_by",
    "deleted_by",
    "bounded_by",
    "selected_by",
    "located_on",
    "parallel_to",
    "perpendicular_to",
    "coaxial_with",
    "adjacent_to",
    "contained_in",
    "intersects",
    "translated_by",
    "rotated_by",
    "scaled_by",
    "parameter_of",
    "has_measurement",
    "adds_material_to",
    "removes_material_from",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources-jsonl",
        type=Path,
        default=Path("data/cadqa_cadevolve_rc_10/sources.jsonl"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-count", type=int, default=2)
    args = parser.parse_args()

    sources = select_sources(args.sources_jsonl, args.source_count)
    preview = build_preview(sources)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "comprehensive_ontology_preview.json"
    md_path = args.output_dir / "comprehensive_ontology_preview.md"
    json_path.write_text(json.dumps(preview, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(preview), encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


def select_sources(path: Path, source_count: int) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"missing source file: {path}")
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
        line_count = len(str(row.get("normalized_code", "")).splitlines())
        rows.append(
            {
                "source_id": row["source_id"],
                "source_family": row.get("generator_id"),
                "path": row.get("normalized_archive_member_path")
                or row.get("archive_member_path"),
                "line_count": line_count,
                "code": row["normalized_code"],
                "has_selector_cuts": ".faces(" in row["normalized_code"]
                and any(
                    token in row["normalized_code"]
                    for token in (".cutBlind(", ".cutThruAll(", ".hole(")
                ),
                "has_repeated_bosses": "splineApprox" in row["normalized_code"]
                and ".union(" in row["normalized_code"]
                and ".extrude(" in row["normalized_code"],
            }
        )
    long_bosses = [
        row for row in rows if row["line_count"] >= 40 and row["has_repeated_bosses"]
    ]
    selector_cuts = [row for row in rows if row["has_selector_cuts"]]

    selected = []
    if long_bosses:
        selected.append(
            sorted(long_bosses, key=lambda item: (-item["line_count"], item["source_id"]))[
                0
            ]
        )
    if source_count > 1 and selector_cuts:
        selector_choice = sorted(
            selector_cuts,
            key=lambda item: (
                item["source_id"] == selected[0]["source_id"] if selected else False,
                -item["line_count"],
                item["source_id"],
            ),
        )[0]
        if selector_choice not in selected:
            selected.append(selector_choice)

    if len(selected) < source_count:
        for row in sorted(rows, key=lambda item: (-item["line_count"], item["source_id"])):
            if row not in selected and row["line_count"] >= 40:
                selected.append(row)
            if len(selected) >= source_count:
                break
    selected = selected[:source_count]
    if not selected:
        raise SystemExit(f"no usable preview sources found in {path}")
    return selected


def build_preview(sources: list[dict[str, Any]]) -> dict[str, Any]:
    primary = sources[0]
    secondary = sources[1] if len(sources) > 1 else sources[0]
    node_examples = node_coverage(primary, secondary)
    relation_examples = relation_coverage(primary, secondary)
    parameter_examples = parameter_entry_exit_coverage(primary, secondary)
    return {
        "schema_version": "cadqa_comprehensive_ontology_preview_v0",
        "source_selection": sources,
        "source_pattern_survey": source_pattern_survey(),
        "coverage_summary": {
            "node_type_count": len(NODE_TYPES),
            "relation_type_count": len(RELATION_TYPES),
            "min_individual_candidate_count": MIN_INDIVIDUAL_CANDIDATE_COUNT,
            "covered_node_types": [item["node_type"] for item in node_examples],
            "covered_relation_types": [item["relation_type"] for item in relation_examples],
        },
        "node_type_clues": node_examples,
        "relation_clues": relation_examples,
        "parameter_entry_exit_clues": parameter_examples,
        "individual_prompt_previews": individual_prompt_previews(
            node_examples, relation_examples, parameter_examples
        ),
        "question_preview_sets": question_preview_sets(relation_examples),
    }


def node_coverage(
    primary: dict[str, Any], secondary: dict[str, Any]
) -> list[dict[str, Any]]:
    examples = {
        "source": ("source:primary", primary["source_id"], "the selected CadEvolve source script"),
        "feature": ("feature:wp37", primary["source_id"], "the variable assigned by one of the repeated `.extrude(...)` calls"),
        "operation": ("operation:extrude", primary["source_id"], "an `.extrude(...)` call that follows a `.circle(...)` call"),
        "parameter": ("parameter:radius_5", primary["source_id"], "the numeric `5` passed to a repeated `.circle(5)` call"),
        "workplane": ("workplane:boss_plane_high_z", primary["source_id"], "the `cq.Workplane(cq.Plane(...))` call whose plane origin has the largest Z value among the repeated boss planes"),
        "sketch": ("sketch:star_points", secondary["source_id"], "the list of 2D points returned by `star_points(...)` and then passed to `.polyline(...)`"),
        "profile": ("profile:circle_r5", primary["source_id"], "a circle made by `.circle(5)` immediately before an `.extrude(...)` call"),
        "solid": ("solid:accumulated_body", primary["source_id"], "the running object produced by repeatedly calling `.union(...)`"),
        "face": ("face:+Y", secondary["source_id"], "a face selected by `.faces(\">Y\")` before a cut"),
        "edge": ("edge:circular_boss_rim", primary["source_id"], "an edge selected by `.edges(...)` or created around a `.circle(...).extrude(...)` feature"),
        "vertex": ("vertex:profile_start", primary["source_id"], "a point on the circular profile made by `.circle(5)`"),
        "axis": ("axis:global_Z", primary["source_id"], "the Z coordinate used in the `cq.Vector(..., ..., z)` plane origins"),
        "centerline": ("centerline:swept_wire", primary["source_id"], "the path wire created by `splineApprox(...)` and used by `.sweep(...)`"),
        "material_region": ("material_region:boss_added", primary["source_id"], "the new solid volume introduced by an `.extrude(...)` that is later joined with `.union(...)`"),
        "selector": ("selector:faces_pos_y", secondary["source_id"], "the `.faces(\">Y\")` selector used before a cut operation"),
        "measurement": ("measurement:bbox_delta", secondary["source_id"], "whether a cut changes the final object's outer bounding box"),
    }
    rows = []
    for node_type in NODE_TYPES:
        node_id, source_id, label = examples[node_type]
        rows.append(
            {
                "node_type": node_type,
                "mock_node_id": node_id,
                "source_id": source_id,
                "canonical_clue": f"The target is {label}.",
                "preview_question_fragment": f"the {label}",
                "candidate_count": mock_node_candidate_count(node_type),
                "passes_individual_candidate_gate": (
                    mock_node_candidate_count(node_type)
                    >= MIN_INDIVIDUAL_CANDIDATE_COUNT
                ),
            }
        )
    return rows


def mock_node_candidate_count(node_type: str) -> int:
    counts = {
        "source": 2,
        "feature": 12,
        "operation": 11,
        "parameter": 14,
        "workplane": 12,
        "sketch": 2,
        "profile": 12,
        "solid": 5,
        "face": 4,
        "edge": 12,
        "vertex": 12,
        "axis": 6,
        "centerline": 6,
        "material_region": 12,
        "selector": 4,
        "measurement": 8,
    }
    return counts[node_type]


def relation_coverage(
    primary: dict[str, Any], secondary: dict[str, Any]
) -> list[dict[str, Any]]:
    p = primary["source_id"]
    s = secondary["source_id"]
    p_ops = parse_operation_sequence(primary["code"])
    before_anchor = temporal_anchor(
        p_ops,
        operation="extrude",
        direction="before",
        min_side_range=MIN_TEMPORAL_SIDE_RANGE,
    )
    after_anchor = temporal_anchor(
        p_ops,
        operation="extrude",
        direction="after",
        min_side_range=MIN_TEMPORAL_SIDE_RANGE,
    )
    immediate_before_anchor = last_operation_anchor(p_ops, operation="union")
    immediate_after_anchor = ordinal_anchor(p_ops, operation="circle", ordinal=4)
    rows = [
        relation(
            "before",
            p,
            "feature:early_boss_extrude",
            before_anchor["feature_id"],
            (
                "The target occurs before "
                f"{before_anchor['public_label']}."
            ),
            diagnostics={
                "side_range": before_anchor["side_range"],
                "min_side_range": MIN_TEMPORAL_SIDE_RANGE,
                "guard": "reject if fewer than min_side_range operations exist before anchor",
            },
            candidate_count=before_anchor["side_range"],
        ),
        relation(
            "after",
            p,
            "feature:late_boss_extrude",
            after_anchor["feature_id"],
            (
                "The target occurs after "
                f"{after_anchor['public_label']}."
            ),
            diagnostics={
                "side_range": after_anchor["side_range"],
                "min_side_range": MIN_TEMPORAL_SIDE_RANGE,
                "guard": "reject if fewer than min_side_range operations exist after anchor",
            },
            candidate_count=after_anchor["side_range"],
        ),
        relation(
            "immediately_before",
            p,
            immediate_before_anchor["previous_feature_id"],
            immediate_before_anchor["feature_id"],
            (
                "The target is the operation immediately before "
                f"{immediate_before_anchor['public_label']}."
            ),
            "high",
            candidate_count=1,
        ),
        relation(
            "immediately_after",
            p,
            immediate_after_anchor["next_feature_id"],
            immediate_after_anchor["feature_id"],
            (
                "The target is the operation immediately after "
                f"{immediate_after_anchor['public_label']}."
            ),
            candidate_count=1,
        ),
        relation("input_to", p, "feature:wp37", "operation:final_union", "The target is one of the objects passed into a later `.union(...)` call.", "high", candidate_count=1),
        relation("created_by", p, "material_region:boss_added", "feature:wp37", "The target is an `.extrude(...)` call that creates a new solid before that solid is joined with `.union(...)`.", candidate_count=12),
        relation("modified_by", s, "face:+Y", "feature:slot_cut", "The target is a cut made from a `.faces(\">Y\")` workplane, so it changes that side of the box.", candidate_count=4),
        relation("deleted_by", s, "material_region:slot_removed", "feature:slot_cut", "The target is a `.cutBlind(...)` or `.cutThruAll()` call that removes material from the box.", candidate_count=4),
        relation("bounded_by", p, "edge:circular_boss_rim", "face:boss_side", "The target creates a boundary visible from a preceding shape call, such as `.circle(...)` before `.extrude(...)` or `.rect(...)` before a cut.", candidate_count=12),
        relation("selected_by", s, "face:+Y", "selector:faces_pos_y", "The target uses `.faces(\">Y\")` before making a workplane or cut.", candidate_count=2),
        relation("located_on", p, "profile:circle_r5", "workplane:boss_plane_high_z", "The target is a `.circle(...)` call made on one of the repeated `cq.Workplane(cq.Plane(...))` planes.", candidate_count=12),
        relation("parallel_to", p, "axis:boss_plane_normal", "axis:global_Z", "The target uses a direction vector that is parallel to one of the script's coordinate axes, such as a `normal=(..., ..., z)` or an edge selector like `\"|Z\"`.", candidate_count=8),
        relation("perpendicular_to", p, "axis:boss_plane_xdir", "axis:boss_plane_normal", "The target's plane uses an `xDir` vector perpendicular to its `normal` vector.", candidate_count=8),
        relation("coaxial_with", p, "centerline:boss", "axis:boss_plane_normal", "The target extrusion follows the normal direction of the workplane where its circle was drawn.", candidate_count=8),
        relation("adjacent_to", s, "face:+Y", "edge:slot_boundary", "The target cut is made on the same side face that contains the boundary of the resulting slot.", candidate_count=4),
        relation("contained_in", s, "vertex:slot_corner", "face:+Y", "The target cut produces slot-corner points on the selected side face.", candidate_count=4),
        relation("intersects", s, "profile:slot_rect", "face:+Y", "The target's rectangle is drawn on a selected side face before the cut is applied.", candidate_count=4),
        relation("translated_by", s, "profile:slot_rect", "parameter:zpos", "The target rectangle is centered at either `zpos` or `-zpos` before the cut.", candidate_count=4),
        relation("rotated_by", p, "workplane:boss_plane", "parameter:plane_normal", "The target uses a `cq.Plane(...)` with an explicit `normal=...` vector rather than a default XY workplane.", candidate_count=12),
        relation("scaled_by", s, "profile:star_shape", "parameter:R_out", "The target uses a size variable such as `R_out`, `R`, or `tab_w` to scale geometry before a `.polyline(...)`, `.rect(...)`, or `.extrude(...)` call.", candidate_count=6),
        relation("parameter_of", s, "parameter:R_out", "profile:star_shape", "The target uses a named size parameter in a later geometry call such as `.polyline(...)`, `.rect(...)`, `.box(...)`, or `.extrude(...)`.", candidate_count=8),
        relation("has_measurement", s, "feature:slot_cut", "measurement:bbox_delta", "The target is a cut whose effect can be checked by comparing the outer bounding box before and after the operation.", candidate_count=8),
        relation("adds_material_to", p, "feature:wp37", "solid:accumulated_body", "The target is an `.extrude(...)` result that is later added to the running object with `.union(...)`.", candidate_count=12),
        relation("removes_material_from", s, "feature:slot_cut", "solid:base_box", "The target is a cut operation that removes material from the original box.", candidate_count=4),
    ]
    assert [row["relation_type"] for row in rows] == RELATION_TYPES
    return rows


def source_pattern_survey() -> list[dict[str, Any]]:
    return [
        {
            "pattern_id": "array_boss_helix_wire",
            "visible_code_shapes": [
                "`splineApprox(...)` path wire",
                "repeated `cq.Workplane(cq.Plane(...))` calls",
                "repeated `.circle(...).extrude(...)` bosses",
                "repeated `.union(...)` accumulation",
            ],
            "wording_implications": [
                "Use 'path wire' instead of centerline unless a centerline label exists.",
                "Use 'running object produced by repeated `.union(...)` calls' instead of accumulated body.",
                "Avoid final-union clues unless the individual candidate gate passes.",
            ],
        },
        {
            "pattern_id": "box_star_slots",
            "visible_code_shapes": [
                "box dimensions assigned to variables",
                "point lists built by trigonometry",
                "face selectors such as `.faces(\">Y\")` and `.faces(\">X\")`",
                "polyline through-cuts",
                "rectangular blind cuts at `zpos` and `-zpos`",
            ],
            "wording_implications": [
                "Use 'points later passed to `.polyline(...)`' instead of star profile.",
                "Use selector text only when enough matching selectors exist.",
                "Use `zpos`/`-zpos` wording only when the repeated pair has enough candidates.",
            ],
        },
        {
            "pattern_id": "tabs_fillets_chamfers",
            "visible_code_shapes": [
                "box base",
                "selected faces used to place tabs",
                "rectangular `.extrude(..., combine=False)` tabs",
                "`.edges(...)` followed by `.fillet(...)`",
                "`.edges().chamfer(...)` on a base body",
            ],
            "wording_implications": [
                "Use 'the object created with `combine=False` and later joined' for tab solids.",
                "Use explicit `.edges(...)` selector wording for fillet/chamfer clues.",
                "Do not assume the model knows topology terms like rim, side face, or material region unless tied to visible calls.",
            ],
        },
    ]


def parse_operation_sequence(code: str) -> list[dict[str, Any]]:
    operations = []
    for line_number, line in enumerate(code.splitlines(), start=1):
        stripped = line.strip()
        if "=" not in stripped or "." not in stripped:
            continue
        target = stripped.split("=", 1)[0].strip()
        operation = operation_name(stripped)
        if not operation:
            continue
        operations.append(
            {
                "feature_id": target,
                "operation": operation,
                "source_line": line_number,
                "index": len(operations),
            }
        )
    return operations


def operation_name(line: str) -> str | None:
    before_paren = line.split("(", 1)[0]
    if "." not in before_paren:
        return None
    return before_paren.rsplit(".", 1)[-1].strip()


def ordinal_anchor(
    operations: list[dict[str, Any]], *, operation: str, ordinal: int
) -> dict[str, Any]:
    matches = [item for item in operations if item["operation"] == operation]
    if len(matches) < ordinal:
        raise ValueError(f"source has fewer than {ordinal} {operation} operations")
    match = matches[ordinal - 1]
    next_item = operations[match["index"] + 1] if match["index"] + 1 < len(operations) else match
    previous_item = operations[match["index"] - 1] if match["index"] > 0 else match
    return {
        **match,
        "next_feature_id": next_item["feature_id"],
        "previous_feature_id": previous_item["feature_id"],
        "public_label": f"the {ordinal_word(ordinal)} {operation} operation",
    }


def temporal_anchor(
    operations: list[dict[str, Any]],
    *,
    operation: str,
    direction: str,
    min_side_range: int,
) -> dict[str, Any]:
    matches = [item for item in operations if item["operation"] == operation]
    if direction == "before":
        allowed = [item for item in matches if item["index"] >= min_side_range]
        if not allowed:
            raise ValueError(
                f"no {operation} anchor has {min_side_range} operations before it"
            )
        match = allowed[0]
    elif direction == "after":
        allowed = [
            item
            for item in matches
            if len(operations) - item["index"] - 1 >= min_side_range
        ]
        if not allowed:
            raise ValueError(
                f"no {operation} anchor has {min_side_range} operations after it"
            )
        match = allowed[-1]
    else:
        raise ValueError(f"unsupported temporal direction: {direction}")

    ordinal = matches.index(match) + 1
    return {
        **match,
        "public_label": f"the {ordinal_word(ordinal)} {operation} operation",
        "side_range": (
            match["index"]
            if direction == "before"
            else len(operations) - match["index"] - 1
        ),
    }


def last_operation_anchor(
    operations: list[dict[str, Any]], *, operation: str
) -> dict[str, Any]:
    matches = [item for item in operations if item["operation"] == operation]
    if not matches:
        raise ValueError(f"source has no {operation} operations")
    match = matches[-1]
    previous = operations[match["index"] - 1] if match["index"] > 0 else match
    return {
        **match,
        "previous_feature_id": previous["feature_id"],
        "public_label": f"the final {operation} operation",
    }


def ordinal_word(value: int) -> str:
    words = {
        1: "first",
        2: "second",
        3: "third",
        4: "fourth",
        5: "fifth",
        6: "sixth",
        7: "seventh",
        8: "eighth",
        9: "ninth",
        10: "tenth",
    }
    if value in words:
        return words[value]
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def relation(
    relation_type: str,
    source_id: str,
    source_node: str,
    target_node: str,
    canonical_clue: str,
    leakage_risk: str = "normal",
    diagnostics: dict[str, Any] | None = None,
    candidate_count: int = 6,
) -> dict[str, Any]:
    return {
        "relation_type": relation_type,
        "source_id": source_id,
        "source_node": source_node,
        "target_node": target_node,
        "canonical_clue": canonical_clue,
        "preview_question_fragment": canonical_clue.removeprefix("The ").rstrip("."),
        "leakage_risk": leakage_risk,
        "candidate_count": candidate_count,
        "passes_individual_candidate_gate": candidate_count
        >= MIN_INDIVIDUAL_CANDIDATE_COUNT,
        "diagnostics": diagnostics or {},
    }


def parameter_entry_exit_coverage(
    primary: dict[str, Any], secondary: dict[str, Any]
) -> list[dict[str, Any]]:
    return [
        {
            "case_id": "parameter_as_entry_node_to_profile",
            "source_id": secondary["source_id"],
            "entry_node": "parameter:R_out",
            "exit_node": "profile:star_shape",
            "relation_type": "parameter_of",
            "canonical_clue": "The target uses the outer radius parameter in points that are later passed to `.polyline(...)`.",
            "candidate_count": 4,
        },
        {
            "case_id": "parameter_as_entry_node_to_operation",
            "source_id": primary["source_id"],
            "entry_node": "parameter:extrude_distance_8",
            "exit_node": "operation:extrude",
            "relation_type": "parameter_of",
            "canonical_clue": "The target operation uses extrusion distance 8 as an input parameter.",
            "candidate_count": 12,
        },
        {
            "case_id": "parameter_as_exit_node_from_operation",
            "source_id": primary["source_id"],
            "entry_node": "operation:circle",
            "exit_node": "parameter:radius_5",
            "relation_type": "parameter_of",
            "canonical_clue": "The target parameter is the radius emitted by the circle operation descriptor.",
            "candidate_count": 12,
        },
        {
            "case_id": "parameter_as_exit_node_from_measurement",
            "source_id": secondary["source_id"],
            "entry_node": "measurement:bbox_delta",
            "exit_node": "parameter:bbox_delta_zero",
            "relation_type": "has_measurement",
            "canonical_clue": "The target parameter is derived from a zero bounding-box delta measurement.",
            "candidate_count": 8,
        },
    ]


def question_preview_sets(relation_examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks = [
        ("temporal_and_input", ["before", "immediately_before", "input_to"]),
        ("geometry_and_selector", ["selected_by", "located_on", "adjacent_to", "contained_in"]),
        ("metric_and_material", ["has_measurement", "adds_material_to", "removes_material_from"]),
        ("transform_and_parameter", ["translated_by", "rotated_by", "scaled_by", "parameter_of"]),
    ]
    by_relation = {row["relation_type"]: row for row in relation_examples}
    sets = []
    for set_id, relation_names in chunks:
        relation_rows = [by_relation[name] for name in relation_names]
        clues = [row["canonical_clue"] for row in relation_rows]
        failing = [
            row["relation_type"]
            for row in relation_rows
            if not row["passes_individual_candidate_gate"]
        ]
        sets.append(
            {
                "set_id": set_id,
                "relation_types": relation_names,
                "passes_individual_candidate_gate": not failing,
                "failing_relation_types": failing,
                "canonical_prompt": (
                    "Given the CadQuery script, identify the feature that satisfies all "
                    "of these constraints:\n- "
                    + "\n- ".join(clues)
                    + "\nReturn exactly one feature ID."
                ),
            }
        )
    return sets


def individual_prompt_previews(
    node_examples: list[dict[str, Any]],
    relation_examples: list[dict[str, Any]],
    parameter_examples: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "node_type_prompts": [
            {
                "id": f"node_prompt__{row['node_type']}",
                "coverage": row["node_type"],
                "candidate_count": row["candidate_count"],
                "passes_individual_candidate_gate": row[
                    "passes_individual_candidate_gate"
                ],
                "canonical_prompt": (
                    "Given the CadQuery script, identify the entity described by "
                    f"this clue: {row['canonical_clue']}\n"
                    "Return exactly one entity ID."
                ),
            }
            for row in node_examples
        ],
        "relation_prompts": [
            {
                "id": f"relation_prompt__{row['relation_type']}",
                "coverage": row["relation_type"],
                "leakage_risk": row["leakage_risk"],
                "candidate_count": row["candidate_count"],
                "passes_individual_candidate_gate": row[
                    "passes_individual_candidate_gate"
                ],
                "canonical_prompt": (
                    "Given the CadQuery script, identify the feature or entity "
                    "that satisfies this relation clue:\n"
                    f"- {row['canonical_clue']}\n"
                    "Return exactly one ID."
                ),
            }
            for row in relation_examples
        ],
        "parameter_entry_exit_prompts": [
            {
                "id": f"parameter_prompt__{row['case_id']}",
                "coverage": row["case_id"],
                "candidate_count": row["candidate_count"],
                "passes_individual_candidate_gate": row["candidate_count"]
                >= MIN_INDIVIDUAL_CANDIDATE_COUNT,
                "canonical_prompt": (
                    "Given the CadQuery script, identify the parameter or entity "
                    "described by this clue:\n"
                    f"- {row['canonical_clue']}\n"
                    "Return exactly one ID."
                ),
            }
            for row in parameter_examples
        ],
    }


def render_markdown(preview: dict[str, Any]) -> str:
    lines = [
        "# Comprehensive Ontology Preview",
        "",
        "This preview is generated deterministically from mock ontology coverage.",
        "It is intended for judging the clue vocabulary before adding it to the",
        "main generator.",
        "",
        "Public clue wording rule: every clue should be understandable from the",
        "shown script alone by a small model. Ontology terms such as",
        "`material_region`, `measurement`, `profile`, or `accumulated body` are",
        "not acceptable in public prompts unless the wording also ties them to",
        "visible CadQuery constructs such as `.extrude(...)`, `.union(...)`,",
        "`.faces(...)`, `.polyline(...)`, or bounding-box comparisons.",
        "",
        "## Selected Sources",
        "",
    ]
    for source in preview["source_selection"]:
        lines.extend(
            [
                f"### {source['source_id']}",
                "",
                f"- Path: `{source['path']}`",
                f"- Family: `{source['source_family']}`",
                f"- Line count: `{source['line_count']}`",
                "",
                "```python",
                source["code"],
                "```",
                "",
            ]
        )

    lines.extend(["## Source Pattern Survey", ""])
    for pattern in preview["source_pattern_survey"]:
        lines.extend([f"### {pattern['pattern_id']}", "", "Visible code shapes:", ""])
        for item in pattern["visible_code_shapes"]:
            lines.append(f"- {item}")
        lines.extend(["", "Wording implications:", ""])
        for item in pattern["wording_implications"]:
            lines.append(f"- {item}")
        lines.append("")

    lines.extend(
        [
        "## Node Type Clue Coverage",
        "",
            "| Node Type | Mock Node | Source | Candidates | Gate | Canonical Clue |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in preview["node_type_clues"]:
        lines.append(
            f"| `{row['node_type']}` | `{row['mock_node_id']}` | `{row['source_id']}` | {row['candidate_count']} | {gate_label(row['passes_individual_candidate_gate'])} | {row['canonical_clue']} |"
        )

    lines.extend(
        [
            "",
            "## Relation Clue Coverage",
            "",
            "| Relation | Source Node | Target Node | Candidates | Gate | Risk | Guard | Canonical Clue |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in preview["relation_clues"]:
        diagnostics = row.get("diagnostics") or {}
        guard = ""
        if diagnostics:
            guard = (
                f"side_range={diagnostics.get('side_range')}; "
                f"min={diagnostics.get('min_side_range')}"
            )
        lines.append(
            f"| `{row['relation_type']}` | `{row['source_node']}` | `{row['target_node']}` | {row['candidate_count']} | {gate_label(row['passes_individual_candidate_gate'])} | `{row['leakage_risk']}` | {guard} | {row['canonical_clue']} |"
        )

    lines.extend(
        [
            "",
            "## Parameter Entry And Exit Coverage",
            "",
            "| Case | Entry Node | Relation | Exit Node | Candidates | Gate | Canonical Clue |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in preview["parameter_entry_exit_clues"]:
        passes = row["candidate_count"] >= MIN_INDIVIDUAL_CANDIDATE_COUNT
        lines.append(
            f"| `{row['case_id']}` | `{row['entry_node']}` | `{row['relation_type']}` | `{row['exit_node']}` | {row['candidate_count']} | {gate_label(passes)} | {row['canonical_clue']} |"
        )

    lines.extend(["", "## Canonical Question Preview Sets", ""])
    for row in preview["question_preview_sets"]:
        lines.extend(
            [
                f"### {row['set_id']}",
                "",
                f"- Relations: {', '.join(f'`{name}`' for name in row['relation_types'])}",
                f"- Individual clue gate: {gate_label(row['passes_individual_candidate_gate'])}",
                f"- Failing relation types: {', '.join(f'`{name}`' for name in row['failing_relation_types']) or 'none'}",
                "",
                "```text",
                row["canonical_prompt"],
                "```",
                "",
            ]
        )

    lines.extend(["", "## Individual Prompt Previews", ""])
    prompt_groups = preview["individual_prompt_previews"]
    for title, key in (
        ("Node Type Prompts", "node_type_prompts"),
        ("Relation Prompts", "relation_prompts"),
        ("Parameter Entry/Exit Prompts", "parameter_entry_exit_prompts"),
    ):
        lines.extend([f"### {title}", ""])
        for row in prompt_groups[key]:
            risk = f" risk=`{row['leakage_risk']}`" if "leakage_risk" in row else ""
            gate = ""
            if "passes_individual_candidate_gate" in row:
                gate = (
                    f" candidates=`{row['candidate_count']}` "
                    f"gate={gate_label(row['passes_individual_candidate_gate'])}"
                )
            lines.extend(
                [
                    f"#### `{row['id']}` coverage=`{row['coverage']}`{risk}{gate}",
                    "",
                    "```text",
                    row["canonical_prompt"],
                    "```",
                    "",
                ]
            )

    return "\n".join(lines)


def gate_label(passes: bool) -> str:
    return "`pass`" if passes else "`reject`"


if __name__ == "__main__":
    main()
