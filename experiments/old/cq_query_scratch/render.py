"""04-style rendering: all model-facing copy comes from prompts.yaml; no LLM in the loop."""

from __future__ import annotations

import hashlib
import string
from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from experiments.old.cq_query_scratch.models import (
    AnswerStepKind,
    CheckKind,
    ClueCheck,
    Comparator,
    EntityCategory,
    Extreme,
    Measure,
    ProgramFacts,
    TaskDefinition,
)

PROMPTS_PATH = Path(__file__).with_name("prompts.yaml")
KIND_WORDS = {"PLANE": "planar", "CYLINDER": "cylindrical", "CONE": "conical", "SPHERE": "spherical",
              "TORUS": "toroidal", "BSPLINE": "a spline surface", "LINE": "straight", "CIRCLE": "circular",
              "ELLIPSE": "elliptical"}
EDGE_KIND_WORDS = {"BSPLINE": "a spline curve"}
MEASURE_WORDS = {Measure.AREA: "area", Measure.LENGTH: "length", Measure.RADIUS: "radius",
                 Measure.CENTER_X: "center of mass x coordinate", Measure.CENTER_Y: "center of mass y coordinate",
                 Measure.CENTER_Z: "center of mass z coordinate"}
PLURALS = {EntityCategory.FACE: "faces", EntityCategory.EDGE: "edges", EntityCategory.VERTEX: "vertices"}
CENTER_MEASURES = {Measure.CENTER_X, Measure.CENTER_Y, Measure.CENTER_Z}
DIRECTION_CHECKS = {CheckKind.AXIS_PARALLEL, CheckKind.AXIS_PERPENDICULAR, CheckKind.AXIS_FACING,
                    CheckKind.PARALLEL_TO_ANCHOR, CheckKind.PERPENDICULAR_TO_ANCHOR}


class RenderedPrompt(BaseModel):
    system: str = Field(min_length=1)
    user: str = Field(min_length=1)


@cache
def prompts() -> dict:
    return yaml.safe_load(PROMPTS_PATH.read_text())


def prompts_sha256() -> str:
    return hashlib.sha256(PROMPTS_PATH.read_bytes()).hexdigest()


def fill(template: str, **values: object) -> str:
    """Format a template, rejecting missing or extra placeholders."""
    fields = {f for _, f, _, _ in string.Formatter().parse(template) if f}
    if fields != set(values):
        raise ValueError(f"placeholder mismatch: template {sorted(fields)} vs values {sorted(values)}")
    return template.format(**values)


def _num(x: float) -> str:
    """Thresholds are rounded to 3 decimals at construction; print exactly that value."""
    return f"{x:.3f}".rstrip("0").rstrip(".")


def _comparator_word(c: ClueCheck) -> str:
    greater = c.comparator == Comparator.GREATER
    match c.kind, c.measure:
        case CheckKind.THRESHOLD, _:
            return "greater than" if greater else "less than"
        case _, Measure.LENGTH:
            return "longer than" if greater else "shorter than"
    return "larger than" if greater else "smaller than"


def clue_text(c: ClueCheck, cat: EntityCategory, anchor: str | None, anchor_cat: EntityCategory | None) -> str:
    t = prompts()["dataset"]["clues"]
    match c.kind:
        case CheckKind.GEOM_KIND:
            word = (EDGE_KIND_WORDS if cat == EntityCategory.EDGE else {}).get(c.geom_kind) or \
                KIND_WORDS.get(c.geom_kind, f"of type {c.geom_kind}")
            return fill(t["geom_kind"], category=cat.value, kind_word=word)
        case CheckKind.AXIS_PARALLEL | CheckKind.AXIS_PERPENDICULAR:
            return fill(t[f"{c.kind.value}_{cat.value}"], axis=c.axis.value.upper())
        case CheckKind.AXIS_FACING:
            return fill(t["axis_facing"], sign="+" if c.positive else "-", axis=c.axis.value.upper())
        case CheckKind.THRESHOLD:
            return fill(t["threshold"], category=cat.value, measure=MEASURE_WORDS[c.measure],
                        comparator=_comparator_word(c), threshold=_num(c.threshold))
        case CheckKind.EXTREME:
            highest = c.measure in CENTER_MEASURES
            word = ("highest" if highest else "largest") if c.extreme == Extreme.MAX else \
                ("lowest" if highest else "smallest")
            return fill(t["extreme"], plural=PLURALS[cat], category=cat.value, extreme=word,
                        measure=MEASURE_WORDS[c.measure])
        case CheckKind.CREATED_BY:
            return fill(t["created_by"], method=c.method, line=c.source_line, var=c.operation_var)
        case CheckKind.PARALLEL_TO_ANCHOR | CheckKind.PERPENDICULAR_TO_ANCHOR:
            return fill(t[c.kind.value], category=cat.value, anchor_category=anchor_cat.value, anchor=anchor)
        case CheckKind.COMPARE_TO_ANCHOR:
            return fill(t["compare_to_anchor"], category=cat.value, measure=MEASURE_WORDS[c.measure],
                        comparator=_comparator_word(c), anchor_category=anchor_cat.value, anchor=anchor)
    return fill(t[c.kind.value], anchor=anchor)


def _definition_keys(task: TaskDefinition) -> list[str]:
    keys = ["final_shape"]
    checks = [c.check for s in task.segments for c in s.clues]
    a = task.answer_step.kind
    if any(c.measure in CENTER_MEASURES for c in checks) or a in {
            AnswerStepKind.FINAL_CENTER, AnswerStepKind.ENTITY_CENTER, AnswerStepKind.DISTANCE_TO_ANCHOR}:
        keys.append("center_of_mass")
    if any(c.kind == CheckKind.GEOM_KIND for c in checks):
        keys.append("kinds")
    if any(c.kind in DIRECTION_CHECKS for c in checks):
        keys.append("direction")
    if any(c.kind == CheckKind.ADJACENT_TO_ANCHOR for c in checks):
        keys.append("adjacent")
    if any(c.kind == CheckKind.COMPARE_TO_ANCHOR for c in checks):
        keys.append("comparison")
    if any(c.kind == CheckKind.CREATED_BY for c in checks) or a in {
            AnswerStepKind.OPERATION_VOLUME_CHANGE, AnswerStepKind.OPERATION_FACE_COUNT_CHANGE}:
        keys.append("modified_solid")
    if any(c.kind == CheckKind.CREATED_BY for c in checks):
        keys.append("created_by")
    return keys


def _answer_text(task: TaskDefinition) -> str:
    t = prompts()["dataset"]["answers"]
    s = task.answer_step
    match s.kind:
        case AnswerStepKind.STATE_VOLUME | AnswerStepKind.OPERATION_VOLUME_CHANGE | \
                AnswerStepKind.OPERATION_FACE_COUNT_CHANGE:
            return fill(t[s.kind.value], method=s.method, line=s.source_line, var=s.operation_var)
        case AnswerStepKind.ENTITY_CENTER:
            return fill(t["entity_center"], category=task.segments[-1].category.value)
        case AnswerStepKind.DISTANCE_TO_ANCHOR:
            prev = task.segments[-2]
            return fill(t["distance_to_anchor"], category=task.segments[-1].category.value,
                        anchor_category=prev.category.value, anchor=prev.label)
        case AnswerStepKind.SET_COUNT:
            seg = task.segments[-1]
            return fill(t["set_count"], plural=PLURALS[seg.category], first=seg.clues[0].order,
                        last=seg.clues[-1].order)
    return fill(t[s.kind.value])


def render_task_text(task: TaskDefinition, pf: ProgramFacts) -> str:
    d = prompts()["dataset"]
    lines = [fill(d["task_intro"], program_text=pf.program_text).rstrip("\n")]
    prev = None
    for i, seg in enumerate(task.segments):
        last_seg = i == len(task.segments) - 1
        first, last = seg.clues[0].order, seg.clues[-1].order
        if not last_seg:
            lines.append(fill(d["segment_anchor"], first=first, last=last, category=seg.category.value,
                              label=seg.label))
        elif task.answer_step.kind == AnswerStepKind.SET_COUNT:
            lines.append(fill(d["segment_set"], first=first, last=last, plural=PLURALS[seg.category]))
        else:
            lines.append(fill(d["segment_target"], first=first, last=last, category=seg.category.value))
        for clue in seg.clues:
            text = clue_text(clue.check, seg.category, prev.label if prev else None, prev.category if prev else None)
            lines.append(fill(d["clue_line"], order=clue.order, text=text))
        prev = seg
    lines.append(_answer_text(task))
    lines.append("")
    lines.append(d["definitions_header"])
    lines += [d["definitions"][k] for k in _definition_keys(task)]
    return "\n".join(lines)


def render_prompt(task: TaskDefinition, max_runs: int | None = None) -> RenderedPrompt:
    """Single-shot prompt, or the agentic prompt when ``max_runs`` is given."""
    e = prompts()["eval"]
    answer_type = e["answer_types"][task.native_answer_format.value]
    instruction = (fill(e["instruction"], answer_type=answer_type) if max_runs is None
                   else fill(e["instruction_agentic"], answer_type=answer_type, max_runs=max_runs))
    user = "\n\n".join([task.prompt, instruction.rstrip("\n"), e["cheat_sheet"].rstrip("\n")])
    return RenderedPrompt(system=e["system"].rstrip("\n"), user=user)
