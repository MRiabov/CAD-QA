"""Survey non-feature relation opportunities across CadEvolve sources.

This script is intentionally outside the main generation pipeline. It samples
source programs, extracts lightweight static entity/relation opportunities, and
reports which non-feature relations are already supported, only specified, or
still necessary to add.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CURRENT_RELATIONS = {
    "before",
    "after",
    "input_to",
    "created_by",
    "modified_by",
    "deleted_by",
    "bounded_by",
    "selected_by",
    "has_measurement",
    "parameter_of",
}

SPEC_ONLY_RELATIONS = {
    "combines",
    "uses_profile",
    "used_by",
    "located_on",
    "parallel_to",
    "not_parallel_to",
    "perpendicular_to",
    "orthogonal_to",
    "coaxial_with",
    "adjacent_to",
    "opposite_to",
    "contained_in",
    "intersects",
    "translated_by",
    "rotated_by",
    "scaled_by",
    "has_normal",
    "has_centroid",
    "has_coordinate",
    "distance_to",
    "nearest_tangent_to",
    "adds_material_to",
    "removes_material_from",
}

SPEC_RELATIONS = CURRENT_RELATIONS | SPEC_ONLY_RELATIONS

MISSING_BUT_NECESSARY = {
    "has_profile_geometry",
    "has_profile_application_effect",
    "has_workplane_frame",
    "has_stable_face_id",
    "has_stable_edge_id",
    "has_stable_vertex_id",
    "has_material_region_geometry",
    "has_void_region_geometry",
    "same_selected_face_as",
    "has_sketch_center",
    "has_path_tangent",
    "nearest_point_on_path",
    "matches_profile_metric",
}

PROFILE_OPS = {"circle", "rect", "polyline", "polygon", "ellipse"}
FEATURE_OPS = {
    "box",
    "extrude",
    "sweep",
    "loft",
    "revolve",
    "union",
    "cut",
    "cutBlind",
    "cutThruAll",
    "hole",
    "fillet",
    "chamfer",
    "shell",
}
SELECTOR_OPS = {"faces", "edges", "vertices", "solids", "wires"}
WORKPLANE_OPS = {"Workplane", "workplane", "transformed"}
PATH_OPS = {"splineApprox", "threePointArc", "sagittaArc", "lineTo", "moveTo"}
CUT_OPS = {"cut", "cutBlind", "cutThruAll", "hole"}
ADDITIVE_OPS = {"box", "extrude", "sweep", "loft", "revolve"}


@dataclass(frozen=True)
class Entity:
    entity_id: str
    entity_type: str
    source_id: str
    label: str
    line: int
    op: str | None = None


@dataclass(frozen=True)
class Relation:
    relation: str
    source: str
    target: str
    support: str
    evidence: str


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources-jsonl",
        type=Path,
        default=Path("data/cadqa_cadevolve_rc_10/sources.jsonl"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-count", type=int, default=10)
    parser.add_argument("--entities-per-source", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260429)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    sources = load_sources(args.sources_jsonl)
    selected = select_diverse_sources(sources, args.source_count, rng)
    surveys = [
        survey_source(row, args.entities_per_source, rng)
        for row in selected
    ]
    report = build_report(args, surveys)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "non_feature_relation_gap_survey.json"
    md_path = args.output_dir / "non_feature_relation_gap_survey.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


def load_sources(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        code = row["normalized_code"]
        rows.append(
            {
                "source_id": row["source_id"],
                "path": row.get("normalized_archive_member_path")
                or row.get("archive_member_path"),
                "family": row.get("generator_id"),
                "code": code,
                "line_count": len(code.splitlines()),
                "ops": sorted(set(re.findall(r"\.([A-Za-z_][A-Za-z0-9_]*)\(", code))),
                "has_selectors": ".faces(" in code or ".edges(" in code,
                "has_profiles": any(f".{op}(" in code for op in PROFILE_OPS),
                "has_sweep_path": "splineApprox" in code or ".sweep(" in code,
                "has_cuts": any(f".{op}(" in code for op in CUT_OPS),
                "has_unions": ".union(" in code,
                "has_planes": "cq.Plane(" in code,
            }
        )
    return rows


def select_diverse_sources(
    sources: list[dict[str, Any]], count: int, rng: random.Random
) -> list[dict[str, Any]]:
    buckets = [
        lambda row: row["has_sweep_path"] and row["has_unions"],
        lambda row: row["has_selectors"] and row["has_cuts"],
        lambda row: row["has_planes"],
        lambda row: row["has_profiles"],
        lambda row: row["has_cuts"],
    ]
    selected: list[dict[str, Any]] = []
    for pred in buckets:
        candidates = [row for row in sources if pred(row) and row not in selected]
        if candidates:
            selected.append(rng.choice(candidates))
        if len(selected) >= count:
            return selected
    remaining = [row for row in sources if row not in selected]
    rng.shuffle(remaining)
    selected.extend(remaining[: max(0, count - len(selected))])
    return selected[:count]


def survey_source(
    row: dict[str, Any], entities_per_source: int, rng: random.Random
) -> dict[str, Any]:
    entities, relations = extract_static_graph(row)
    sampled = choose_entities(entities, relations, entities_per_source, rng)
    relation_names = sorted({rel.relation for rel in relations})
    missing = infer_missing_needed(row, entities, relations)
    return {
        "source_id": row["source_id"],
        "path": row["path"],
        "family": row["family"],
        "line_count": row["line_count"],
        "visible_ops": row["ops"],
        "sampled_entities": [entity.__dict__ for entity in sampled],
        "relation_opportunities": [
            rel.__dict__ for rel in relations if rel.source in {e.entity_id for e in sampled}
        ][:30],
        "all_relation_types_observed": relation_names,
        "missing_needed_relations": sorted(missing),
    }


def extract_static_graph(row: dict[str, Any]) -> tuple[list[Entity], list[Relation]]:
    code = row["code"]
    source_id = row["source_id"]
    tree = ast.parse(code)
    entities: list[Entity] = []
    relations: list[Relation] = []
    var_entity: dict[str, Entity] = {}
    last_profile: Entity | None = None
    last_workplane: Entity | None = None
    last_selector: Entity | None = None
    last_path: Entity | None = None
    previous_feature: Entity | None = None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not node.targets:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        name = target.id
        call_chain = flatten_call_chain(node.value)
        if not call_chain:
            continue

        base_vars = sorted(extract_name_refs(node.value) - {name})
        for op, call in call_chain:
            line = getattr(call, "lineno", getattr(node, "lineno", 0))
            entity_type = classify_entity_type(op)
            entity = Entity(
                entity_id=f"{source_id}:{name}:{op}:{line}",
                entity_type=entity_type,
                source_id=source_id,
                label=f"{name} = {op}(...)",
                line=line,
                op=op,
            )
            entities.append(entity)
            var_entity[name] = entity

            if previous_feature and entity_type in {"feature", "solid", "profile", "workplane"}:
                relations.append(relation("after", entity, previous_feature, "current"))
                relations.append(relation("before", previous_feature, entity, "current"))

            for base in base_vars:
                if base in var_entity:
                    relations.append(relation("input_to", var_entity[base], entity, "current"))

            for arg_name in sorted(extract_name_refs_from_args(call)):
                param = Entity(
                    entity_id=f"{source_id}:parameter:{arg_name}:{line}",
                    entity_type="parameter",
                    source_id=source_id,
                    label=f"parameter `{arg_name}` used by {name}",
                    line=line,
                    op=None,
                )
                entities.append(param)
                relations.append(relation("parameter_of", param, entity, "current"))

            if entity_type == "workplane":
                last_workplane = entity
                if "Plane" in ast.unparse(call):
                    relations.append(
                        relation(
                            "has_normal",
                            entity,
                            literal_entity(source_id, "direction", "plane_normal", line, entities),
                            "spec_only",
                            "explicit cq.Plane normal",
                        )
                    )
                    relations.append(
                        relation(
                            "has_workplane_frame",
                            entity,
                            literal_entity(source_id, "measurement", "workplane_frame", line, entities),
                            "missing_needed",
                            "frame extraction needed for profile/world geometry",
                        )
                    )
            elif entity_type == "selector":
                last_selector = entity
                face = selector_entity(source_id, call, line, entities)
                if face:
                    relations.append(relation("selected_by", face, entity, "current"))
                    if last_workplane:
                        relations.append(relation("located_on", last_workplane, face, "spec_only"))
            elif entity_type == "profile":
                if last_workplane:
                    relations.append(relation("located_on", entity, last_workplane, "spec_only"))
                relations.append(
                    relation(
                        "has_profile_geometry",
                        entity,
                        literal_entity(source_id, "measurement", "profile_intrinsic_geometry", line, entities),
                        "missing_needed",
                        "area/perimeter/centroid/bbox/edge-count extraction",
                    )
                )
                last_profile = entity
            elif entity_type == "path":
                last_path = entity
                relations.append(
                    relation(
                        "has_path_tangent",
                        entity,
                        literal_entity(source_id, "direction", "path_tangent", line, entities),
                        "missing_needed",
                        "needed for sweep path tangent questions",
                    )
                )
            elif entity_type in {"feature", "solid"}:
                if last_profile and op in {"extrude", "sweep", "loft", "revolve", "cut", "cutBlind", "cutThruAll", "hole"}:
                    relations.append(relation("uses_profile", entity, last_profile, "spec_only"))
                    relations.append(relation("used_by", last_profile, entity, "spec_only"))
                if last_selector:
                    relations.append(relation("input_to", last_selector, entity, "current"))
                if op == "union":
                    relations.append(relation("combines", entity, entity, "spec_only"))
                    relations.append(relation("adds_material_to", entity, entity, "spec_only"))
                if op in CUT_OPS:
                    relations.append(relation("removes_material_from", entity, entity, "spec_only"))
                    relations.append(
                        relation(
                            "has_void_region_geometry",
                            entity,
                            literal_entity(source_id, "void_region", "removed_void", line, entities),
                            "missing_needed",
                            "cut void geometry",
                        )
                    )
                if op in ADDITIVE_OPS:
                    relations.append(relation("created_by", entity, entity, "current"))
                    relations.append(
                        relation(
                            "has_material_region_geometry",
                            entity,
                            literal_entity(source_id, "material_region", "added_material", line, entities),
                            "missing_needed",
                            "added-material geometry",
                        )
                    )
                relations.append(
                    relation(
                        "has_measurement",
                        entity,
                        literal_entity(source_id, "measurement", "volume_bbox_topology_delta", line, entities),
                        "current",
                    )
                )
                relations.append(
                    relation(
                        "has_centroid",
                        entity,
                        literal_entity(source_id, "centroid", "feature_centroid", line, entities),
                        "spec_only",
                    )
                )
                if last_path and op == "sweep":
                    relations.append(relation("uses_profile", entity, last_profile or entity, "spec_only"))
                    relations.append(relation("input_to", last_path, entity, "current"))

            if entity_type in {"feature", "solid"}:
                previous_feature = entity

    return dedupe_entities(entities), dedupe_relations(relations)


def flatten_call_chain(node: ast.AST) -> list[tuple[str, ast.Call]]:
    out: list[tuple[str, ast.Call]] = []

    def visit(expr: ast.AST) -> None:
        if isinstance(expr, ast.Call):
            visit(expr.func)
            op = call_name(expr)
            if op:
                out.append((op, expr))
        elif isinstance(expr, ast.Attribute):
            visit(expr.value)

    visit(node)
    return out


def call_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def classify_entity_type(op: str) -> str:
    if op in PROFILE_OPS:
        return "profile"
    if op in SELECTOR_OPS:
        return "selector"
    if op in WORKPLANE_OPS:
        return "workplane"
    if op in PATH_OPS:
        return "path"
    if op in FEATURE_OPS:
        return "solid" if op in {"box", "extrude", "sweep", "loft", "revolve", "union"} else "feature"
    return "operation"


def extract_name_refs(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def extract_name_refs_from_args(call: ast.Call) -> set[str]:
    refs: set[str] = set()
    for arg in list(call.args) + [kw.value for kw in call.keywords]:
        refs.update(extract_name_refs(arg))
    return refs


def literal_entity(
    source_id: str,
    entity_type: str,
    label: str,
    line: int,
    entities: list[Entity],
) -> Entity:
    entity = Entity(
        entity_id=f"{source_id}:{entity_type}:{label}:{line}",
        entity_type=entity_type,
        source_id=source_id,
        label=label.replace("_", " "),
        line=line,
        op=None,
    )
    entities.append(entity)
    return entity


def selector_entity(
    source_id: str, call: ast.Call, line: int, entities: list[Entity]
) -> Entity | None:
    if not call.args:
        return None
    try:
        selector = ast.literal_eval(call.args[0])
    except Exception:
        selector = ast.unparse(call.args[0])
    kind = "face" if call_name(call) == "faces" else "edge"
    return literal_entity(source_id, kind, f"{kind}_{selector}", line, entities)


def relation(
    name: str,
    source: Entity,
    target: Entity,
    support: str,
    evidence: str | None = None,
) -> Relation:
    if support == "current" and name not in CURRENT_RELATIONS:
        support = "spec_only" if name in SPEC_RELATIONS else "missing_needed"
    if support == "spec_only" and name not in SPEC_RELATIONS:
        support = "missing_needed"
    return Relation(
        relation=name,
        source=source.entity_id,
        target=target.entity_id,
        support=support,
        evidence=evidence or f"{source.label} -> {target.label}",
    )


def dedupe_entities(entities: list[Entity]) -> list[Entity]:
    seen = set()
    out = []
    for entity in entities:
        if entity.entity_id in seen:
            continue
        seen.add(entity.entity_id)
        out.append(entity)
    return out


def dedupe_relations(relations: list[Relation]) -> list[Relation]:
    seen = set()
    out = []
    for rel in relations:
        key = (rel.relation, rel.source, rel.target, rel.support)
        if key in seen:
            continue
        seen.add(key)
        out.append(rel)
    return out


def choose_entities(
    entities: list[Entity],
    relations: list[Relation],
    count: int,
    rng: random.Random,
) -> list[Entity]:
    by_id = {entity.entity_id: entity for entity in entities}
    degree = Counter()
    for rel in relations:
        degree[rel.source] += 1
        degree[rel.target] += 1
    typed: dict[str, list[Entity]] = defaultdict(list)
    for entity in entities:
        if degree[entity.entity_id] > 0:
            typed[entity.entity_type].append(entity)

    preferred_types = [
        "profile",
        "workplane",
        "selector",
        "face",
        "solid",
        "path",
        "material_region",
        "measurement",
        "feature",
        "parameter",
    ]
    selected: list[Entity] = []
    for entity_type in preferred_types:
        options = sorted(
            typed.get(entity_type, []),
            key=lambda entity: (-degree[entity.entity_id], entity.line, entity.entity_id),
        )
        if options:
            selected.append(rng.choice(options[: min(5, len(options))]))
        if len(selected) >= count:
            return selected

    remaining = [entity for entity in entities if entity.entity_id not in {e.entity_id for e in selected}]
    remaining.sort(key=lambda entity: (-degree[entity.entity_id], entity.line, entity.entity_id))
    selected.extend(remaining[: max(0, count - len(selected))])
    return selected[:count]


def infer_missing_needed(
    row: dict[str, Any], entities: list[Entity], relations: list[Relation]
) -> set[str]:
    missing = {rel.relation for rel in relations if rel.support == "missing_needed"}
    entity_types = {entity.entity_type for entity in entities}
    if "profile" in entity_types:
        missing.add("has_profile_geometry")
        missing.add("has_sketch_center")
    if row["has_selectors"]:
        missing.update({"has_stable_face_id", "same_selected_face_as"})
    if row["has_cuts"]:
        missing.update({"has_void_region_geometry", "has_profile_application_effect"})
    if row["has_unions"] or any(entity.entity_type == "solid" for entity in entities):
        missing.add("has_material_region_geometry")
    if row["has_sweep_path"]:
        missing.update({"has_path_tangent", "nearest_point_on_path"})
    if row["has_planes"]:
        missing.add("has_workplane_frame")
    return missing


def build_report(args: argparse.Namespace, surveys: list[dict[str, Any]]) -> dict[str, Any]:
    relation_counts = Counter()
    support_counts = Counter()
    missing_counts = Counter()
    entity_counts = Counter()
    for survey in surveys:
        for entity in survey["sampled_entities"]:
            entity_counts[entity["entity_type"]] += 1
        for rel in survey["relation_opportunities"]:
            relation_counts[rel["relation"]] += 1
            support_counts[rel["support"]] += 1
        missing_counts.update(survey["missing_needed_relations"])

    return {
        "schema_version": "cadqa_non_feature_relation_gap_survey_v0",
        "seed": args.seed,
        "source_count": len(surveys),
        "entities_per_source": args.entities_per_source,
        "current_relations": sorted(CURRENT_RELATIONS),
        "spec_only_relations": sorted(SPEC_ONLY_RELATIONS),
        "missing_but_necessary_relation_families": sorted(MISSING_BUT_NECESSARY),
        "summary": {
            "sampled_entity_type_counts": dict(sorted(entity_counts.items())),
            "observed_relation_counts": dict(sorted(relation_counts.items())),
            "support_counts": dict(sorted(support_counts.items())),
            "missing_needed_counts": dict(missing_counts.most_common()),
        },
        "surveys": surveys,
        "recommendations": recommendations(missing_counts),
    }


def recommendations(missing_counts: Counter[str]) -> list[dict[str, str]]:
    priority = [
        ("has_profile_geometry", "Implement AST/CadQuery profile extraction for circle, rect, polyline, and bounded helper point lists."),
        ("has_profile_application_effect", "Link profiles to operation deltas so profile clues can refer to the effect of the cut/extrude."),
        ("has_workplane_frame", "Persist workplane origin, axes, normal, and frame transforms for every profile."),
        ("has_stable_face_id", "Persist selector-result face IDs and conservative adjacent-snapshot face matching."),
        ("has_material_region_geometry", "Represent added material regions from extrude/sweep/union with centroid, bbox, volume, and adjacency hooks."),
        ("has_void_region_geometry", "Represent removed void regions from cutBlind/cutThruAll/hole with volume, bbox, intersections, and selected face."),
        ("has_path_tangent", "Extract source-defined or fitted path tangents for sweep/helix questions."),
        ("same_selected_face_as", "Add equality joins over selector-result entities across operations."),
    ]
    rows = []
    for name, action in priority:
        rows.append(
            {
                "relation_family": name,
                "observed_need_count": str(missing_counts.get(name, 0)),
                "recommendation": action,
            }
        )
    return rows


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Non-Feature Relation Gap Survey",
        "",
        f"- Seed: `{report['seed']}`",
        f"- Sources sampled: `{report['source_count']}`",
        f"- Entities per source: `{report['entities_per_source']}`",
        "",
        "## Summary",
        "",
        "### Sampled Entity Types",
        "",
        "| Entity Type | Count |",
        "|---|---:|",
    ]
    for name, count in report["summary"]["sampled_entity_type_counts"].items():
        lines.append(f"| `{name}` | {count} |")
    lines.extend(["", "### Relation Opportunities By Support", "", "| Support | Count |", "|---|---:|"])
    for name, count in report["summary"]["support_counts"].items():
        lines.append(f"| `{name}` | {count} |")
    lines.extend(["", "### Observed Relation Types", "", "| Relation | Count |", "|---|---:|"])
    for name, count in report["summary"]["observed_relation_counts"].items():
        lines.append(f"| `{name}` | {count} |")
    lines.extend(["", "### Missing But Necessary Families", "", "| Family | Count |", "|---|---:|"])
    for name, count in report["summary"]["missing_needed_counts"].items():
        lines.append(f"| `{name}` | {count} |")
    lines.extend(["", "## Recommendations", "", "| Relation Family | Observed Need | Recommendation |", "|---|---:|---|"])
    for row in report["recommendations"]:
        lines.append(
            f"| `{row['relation_family']}` | {row['observed_need_count']} | {row['recommendation']} |"
        )
    lines.extend(["", "## Per-Source Samples", ""])
    for survey in report["surveys"]:
        lines.extend(
            [
                f"### `{survey['source_id']}`",
                "",
                f"- Path: `{survey['path']}`",
                f"- Lines: `{survey['line_count']}`",
                f"- Visible ops: `{', '.join(survey['visible_ops'][:18])}`",
                "",
                "| Sampled Entity | Type | Line |",
                "|---|---|---:|",
            ]
        )
        for entity in survey["sampled_entities"]:
            lines.append(
                f"| `{entity['label']}` | `{entity['entity_type']}` | {entity['line']} |"
            )
        lines.extend(["", "| Relation | Support | Evidence |", "|---|---|---|"])
        for rel in survey["relation_opportunities"][:10]:
            evidence = rel["evidence"].replace("|", "\\|")
            lines.append(f"| `{rel['relation']}` | `{rel['support']}` | {evidence} |")
        lines.extend(["", "Missing/necessary relation families: " + ", ".join(f"`{x}`" for x in survey["missing_needed_relations"]), ""])
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    main()
