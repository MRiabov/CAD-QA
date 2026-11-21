"""Deterministic task-definition construction (03b schema, scratch scope).

A task is an ordered list of segments. Each segment narrows one entity category of the final
solid state with typed task clues. Every non-final segment ends at exactly one entity, which
becomes the labeled anchor (A, B, ...) that the next segment's first clue relates to. The final
segment ends at one entity (measurement answer) or a set (count answer).

Every choice is the first valid option in sha256(seed | program | step count | slot | position |
option) order. Python's ``random`` is not used.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Iterator

from pydantic import BaseModel, Field

from experiments.old.cq_query_scratch.models import (
    COMPARISON_REL_TOL,
    FACE_MATCH_AREA_REL_TOL,
    FACE_MATCH_CENTER_TOL,
    PARALLEL_TOLERANCE_DEG,
    SEED,
    AnswerFormat,
    AnswerMeaning,
    AnswerStep,
    AnswerStepKind,
    Axis,
    CheckKind,
    ClueCheck,
    ClueResult,
    Comparator,
    EdgeFact,
    Entity,
    EntityCategory,
    Extreme,
    FaceFact,
    FaceFingerprint,
    Measure,
    Point3,
    ProgramFacts,
    Segment,
    SolidStateFact,
    TargetCategory,
    TaskClue,
    TaskDefinition,
    TaskValidity,
    clue_type_of,
)

COS_TOL = math.cos(math.radians(PARALLEL_TOLERANCE_DEG))
SIN_TOL = math.sin(math.radians(PARALLEL_TOLERANCE_DEG))
AXIS_VECTORS: dict[Axis, Point3] = {Axis.X: (1.0, 0.0, 0.0), Axis.Y: (0.0, 1.0, 0.0), Axis.Z: (0.0, 0.0, 1.0)}
SEARCH_BUDGET = 4000
LABELS = "ABCD"
MAX_SEGMENT_CLUES = 4

ANSWER_SPECS: dict[AnswerStepKind, tuple[AnswerMeaning, AnswerFormat]] = {
    AnswerStepKind.FINAL_VOLUME: (AnswerMeaning.VOLUME, AnswerFormat.NUMBER),
    AnswerStepKind.FINAL_SURFACE_AREA: (AnswerMeaning.AREA, AnswerFormat.NUMBER),
    AnswerStepKind.FINAL_CENTER: (AnswerMeaning.POSITION, AnswerFormat.COORDINATE),
    AnswerStepKind.FINAL_FACE_COUNT: (AnswerMeaning.COUNT, AnswerFormat.INTEGER),
    AnswerStepKind.FINAL_EDGE_COUNT: (AnswerMeaning.COUNT, AnswerFormat.INTEGER),
    AnswerStepKind.STATE_VOLUME: (AnswerMeaning.VOLUME, AnswerFormat.NUMBER),
    AnswerStepKind.OPERATION_VOLUME_CHANGE: (AnswerMeaning.MATERIAL_CHANGE, AnswerFormat.NUMBER),
    AnswerStepKind.OPERATION_FACE_COUNT_CHANGE: (AnswerMeaning.TOPOLOGY_CHANGE, AnswerFormat.INTEGER),
    AnswerStepKind.ENTITY_AREA: (AnswerMeaning.AREA, AnswerFormat.NUMBER),
    AnswerStepKind.ENTITY_LENGTH: (AnswerMeaning.LENGTH, AnswerFormat.NUMBER),
    AnswerStepKind.ENTITY_RADIUS: (AnswerMeaning.LENGTH, AnswerFormat.NUMBER),
    AnswerStepKind.ENTITY_CENTER: (AnswerMeaning.POSITION, AnswerFormat.COORDINATE),
    AnswerStepKind.DISTANCE_TO_ANCHOR: (AnswerMeaning.DISTANCE, AnswerFormat.NUMBER),
    AnswerStepKind.SET_COUNT: (AnswerMeaning.COUNT, AnswerFormat.INTEGER),
}

FINAL_ANSWERS: dict[EntityCategory, list[AnswerStepKind]] = {
    EntityCategory.FACE: [AnswerStepKind.ENTITY_AREA, AnswerStepKind.ENTITY_CENTER,
                          AnswerStepKind.DISTANCE_TO_ANCHOR, AnswerStepKind.SET_COUNT],
    EntityCategory.EDGE: [AnswerStepKind.ENTITY_LENGTH, AnswerStepKind.ENTITY_RADIUS, AnswerStepKind.ENTITY_CENTER,
                          AnswerStepKind.DISTANCE_TO_ANCHOR, AnswerStepKind.SET_COUNT],
    EntityCategory.VERTEX: [AnswerStepKind.ENTITY_CENTER, AnswerStepKind.DISTANCE_TO_ANCHOR,
                            AnswerStepKind.SET_COUNT],
}

# Anchor relations allowed from (anchor category, target category).
ANCHOR_CHECKS: dict[tuple[EntityCategory, EntityCategory], list[CheckKind]] = {
    (EntityCategory.FACE, EntityCategory.FACE): [CheckKind.ADJACENT_TO_ANCHOR, CheckKind.PARALLEL_TO_ANCHOR,
                                                 CheckKind.PERPENDICULAR_TO_ANCHOR, CheckKind.COMPARE_TO_ANCHOR],
    (EntityCategory.FACE, EntityCategory.EDGE): [CheckKind.EDGE_OF_ANCHOR_FACE],
    (EntityCategory.FACE, EntityCategory.VERTEX): [CheckKind.VERTEX_OF_ANCHOR_FACE],
    (EntityCategory.EDGE, EntityCategory.FACE): [CheckKind.FACE_HAS_ANCHOR_EDGE],
    (EntityCategory.EDGE, EntityCategory.EDGE): [CheckKind.SHARES_VERTEX_WITH_ANCHOR, CheckKind.PARALLEL_TO_ANCHOR,
                                                 CheckKind.PERPENDICULAR_TO_ANCHOR, CheckKind.COMPARE_TO_ANCHOR],
    (EntityCategory.EDGE, EntityCategory.VERTEX): [CheckKind.ENDPOINT_OF_ANCHOR_EDGE],
    (EntityCategory.VERTEX, EntityCategory.EDGE): [CheckKind.EDGE_HAS_ANCHOR_VERTEX],
    (EntityCategory.VERTEX, EntityCategory.FACE): [CheckKind.FACE_HAS_ANCHOR_VERTEX],
}


class SegmentPlan(BaseModel):
    category: EntityCategory
    length: int = Field(ge=1, le=MAX_SEGMENT_CLUES)


class BuiltClue(BaseModel):
    check: ClueCheck
    before: int = Field(ge=1)
    after: int = Field(ge=1)


class GenerationFailure(BaseModel):
    program_id: str
    step_count: int
    slot: int
    reason: str = Field(min_length=1, max_length=80)


def _h(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in (SEED, *parts)).encode()).hexdigest()


def _hash_order(items: list, *key_parts: object, key=lambda x: x) -> list:
    return sorted(items, key=lambda x: _h(*key_parts, key(x)))


def _dot(a: Point3, b: Point3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _dist(a: Point3, b: Point3) -> float:
    return math.dist(a, b)


def _category(e: Entity) -> EntityCategory:
    match e:
        case FaceFact():
            return EntityCategory.FACE
        case EdgeFact():
            return EntityCategory.EDGE
    return EntityCategory.VERTEX


def _faces_match(a: FaceFingerprint | FaceFact, b: FaceFingerprint) -> bool:
    return _dist(a.center, b.center) <= FACE_MATCH_CENTER_TOL and abs(a.area - b.area) <= (
        FACE_MATCH_AREA_REL_TOL * max(1.0, abs(b.area)))


class FactIndex:
    """Read-only lookup over one program's final solid state (the 02c slice the tasks need)."""

    def __init__(self, pf: ProgramFacts) -> None:
        self.pf = pf
        self.by_category: dict[EntityCategory, list[Entity]] = {
            EntityCategory.FACE: list(pf.faces), EntityCategory.EDGE: list(pf.edges),
            EntityCategory.VERTEX: list(pf.vertices)}
        self.adjacent: dict[str, set[str]] = {}
        for a, b in pf.adjacent_face_pairs:
            self.adjacent.setdefault(a, set()).add(b)
            self.adjacent.setdefault(b, set()).add(a)
        self.final_state = next(s for s in pf.states if s.state_id == pf.final_state_id)
        self.created: dict[str, set[str]] = {}
        for s in pf.states:
            ids = {f.entity_id for f in pf.faces if any(_faces_match(f, g) for g in s.faces)
                   and not any(_faces_match(f, g) for g in s.before_faces)}
            if ids:
                self.created[s.result_var] = ids
        self.state_by_var: dict[str, SolidStateFact] = {s.result_var: s for s in pf.states}


def measure(e: Entity, m: Measure) -> float | None:
    match m:
        case Measure.AREA:
            return e.area if isinstance(e, FaceFact) else None
        case Measure.LENGTH:
            return e.length if isinstance(e, EdgeFact) else None
        case Measure.RADIUS:
            return e.radius if isinstance(e, EdgeFact) else None
        case Measure.CENTER_X:
            return e.center[0]
        case Measure.CENTER_Y:
            return e.center[1]
        case Measure.CENTER_Z:
            return e.center[2]


def _direction(e: Entity) -> Point3 | None:
    match e:
        case FaceFact(kind="PLANE"):
            return e.normal
        case EdgeFact(kind="LINE"):
            return e.direction
    return None


def _tol(v: float) -> float:
    return COMPARISON_REL_TOL * max(1.0, abs(v))


def apply_check(c: ClueCheck, cands: list[Entity], idx: FactIndex, anchor: Entity | None) -> list[Entity]:
    match c.kind:
        case CheckKind.GEOM_KIND:
            return [e for e in cands if getattr(e, "kind", None) == c.geom_kind]
        case CheckKind.AXIS_PARALLEL:
            ax = AXIS_VECTORS[c.axis]
            return [e for e in cands if (d := _direction(e)) and abs(_dot(d, ax)) >= COS_TOL]
        case CheckKind.AXIS_PERPENDICULAR:
            ax = AXIS_VECTORS[c.axis]
            return [e for e in cands if (d := _direction(e)) and abs(_dot(d, ax)) <= SIN_TOL]
        case CheckKind.AXIS_FACING:
            ax, sign = AXIS_VECTORS[c.axis], 1.0 if c.positive else -1.0
            return [e for e in cands if (d := _direction(e)) and sign * _dot(d, ax) >= COS_TOL]
        case CheckKind.THRESHOLD:
            vals = [(e, measure(e, c.measure)) for e in cands]
            if c.comparator == Comparator.GREATER:
                return [e for e, v in vals if v is not None and v > c.threshold]
            return [e for e, v in vals if v is not None and v < c.threshold]
        case CheckKind.EXTREME:
            vals = [(e, v) for e in cands if (v := measure(e, c.measure)) is not None]
            if not vals:
                return []
            best = max(v for _, v in vals) if c.extreme == Extreme.MAX else min(v for _, v in vals)
            return [e for e, v in vals if abs(v - best) <= _tol(best)]
        case CheckKind.CREATED_BY:
            ids = idx.created.get(c.operation_var, set())
            return [e for e in cands if e.entity_id in ids]
        case CheckKind.ADJACENT_TO_ANCHOR:
            return [e for e in cands if e.entity_id in idx.adjacent.get(anchor.entity_id, set())]
        case CheckKind.PARALLEL_TO_ANCHOR | CheckKind.PERPENDICULAR_TO_ANCHOR:
            da = _direction(anchor)
            if da is None:
                return []
            par = c.kind == CheckKind.PARALLEL_TO_ANCHOR
            return [e for e in cands if e.entity_id != anchor.entity_id and (d := _direction(e))
                    and (abs(_dot(d, da)) >= COS_TOL if par else abs(_dot(d, da)) <= SIN_TOL)]
        case CheckKind.EDGE_OF_ANCHOR_FACE | CheckKind.VERTEX_OF_ANCHOR_FACE:
            ids = set(anchor.edge_ids if c.kind == CheckKind.EDGE_OF_ANCHOR_FACE else anchor.vertex_ids)
            return [e for e in cands if e.entity_id in ids]
        case CheckKind.FACE_HAS_ANCHOR_EDGE:
            return [e for e in cands if anchor.entity_id in e.edge_ids]
        case CheckKind.SHARES_VERTEX_WITH_ANCHOR:
            av = set(anchor.vertex_ids)
            return [e for e in cands if e.entity_id != anchor.entity_id and av & set(e.vertex_ids)]
        case CheckKind.ENDPOINT_OF_ANCHOR_EDGE:
            return [e for e in cands if e.entity_id in anchor.vertex_ids]
        case CheckKind.EDGE_HAS_ANCHOR_VERTEX | CheckKind.FACE_HAS_ANCHOR_VERTEX:
            return [e for e in cands if anchor.entity_id in e.vertex_ids]
        case CheckKind.COMPARE_TO_ANCHOR:
            a = measure(anchor, c.measure)
            vals = [(e, measure(e, c.measure)) for e in cands]
            if c.comparator == Comparator.GREATER:
                return [e for e, v in vals if v is not None and v > a + _tol(a)]
            return [e for e, v in vals if v is not None and v < a - _tol(a)]
    raise ValueError(c.kind)


def _measures_for(cat: EntityCategory, cands: list[Entity]) -> list[Measure]:
    centers = [Measure.CENTER_X, Measure.CENTER_Y, Measure.CENTER_Z]
    match cat:
        case EntityCategory.FACE:
            return [Measure.AREA, *centers]
        case EntityCategory.EDGE:
            out = [Measure.LENGTH, *centers]
            if all(isinstance(e, EdgeFact) and e.radius for e in cands):
                out.append(Measure.RADIUS)
            return out
    return centers


def _threshold_checks(cands: list[Entity], m: Measure) -> Iterator[ClueCheck]:
    vals = sorted({v for e in cands if (v := measure(e, m)) is not None})
    for a, b in zip(vals, vals[1:]):
        t = round((a + b) / 2, 3)
        if all(abs(v - t) >= _tol(t) for v in vals):
            for comp in Comparator:
                yield ClueCheck(kind=CheckKind.THRESHOLD, measure=m, comparator=comp, threshold=t)


def _extreme_checks(cands: list[Entity], m: Measure) -> Iterator[ClueCheck]:
    vals = sorted(v for e in cands if (v := measure(e, m)) is not None)
    if len(vals) >= 2 and len(vals) == len(cands):
        if vals[-1] - vals[-2] > _tol(vals[-1]):
            yield ClueCheck(kind=CheckKind.EXTREME, measure=m, extreme=Extreme.MAX)
        if vals[1] - vals[0] > _tol(vals[0]):
            yield ClueCheck(kind=CheckKind.EXTREME, measure=m, extreme=Extreme.MIN)


def candidate_checks(cat: EntityCategory, cands: list[Entity], idx: FactIndex, anchor: Entity | None,
                     anchor_only: bool) -> list[ClueCheck]:
    out: list[ClueCheck] = []
    if anchor is not None:
        for kind in ANCHOR_CHECKS.get((_category(anchor), cat), []):
            match kind:
                case CheckKind.COMPARE_TO_ANCHOR:
                    m = Measure.AREA if cat == EntityCategory.FACE else Measure.LENGTH
                    out += [ClueCheck(kind=kind, measure=m, comparator=c) for c in Comparator]
                case CheckKind.PARALLEL_TO_ANCHOR | CheckKind.PERPENDICULAR_TO_ANCHOR:
                    if _direction(anchor) and all(_direction(e) for e in cands):
                        out.append(ClueCheck(kind=kind))
                case _:
                    out.append(ClueCheck(kind=kind))
    if anchor_only:
        return out
    if cat in (EntityCategory.FACE, EntityCategory.EDGE):
        out += [ClueCheck(kind=CheckKind.GEOM_KIND, geom_kind=k) for k in sorted({e.kind for e in cands})]
        if all(_direction(e) for e in cands):
            for ax in Axis:
                out += [ClueCheck(kind=CheckKind.AXIS_PARALLEL, axis=ax),
                        ClueCheck(kind=CheckKind.AXIS_PERPENDICULAR, axis=ax)]
                if cat == EntityCategory.FACE:
                    out += [ClueCheck(kind=CheckKind.AXIS_FACING, axis=ax, positive=p) for p in (True, False)]
    if cat == EntityCategory.FACE:
        for var in sorted(idx.created):
            s = idx.state_by_var[var]
            out.append(ClueCheck(kind=CheckKind.CREATED_BY, operation_var=var, receiver_var=s.receiver_var,
                                 method=s.method, source_line=s.source_line))
    for m in _measures_for(cat, cands):
        out += list(_threshold_checks(cands, m))
        out += list(_extreme_checks(cands, m))
    return out


def _check_key(c: ClueCheck) -> str:
    return json.dumps(c.model_dump(mode="json", exclude_none=True), sort_keys=True)


def _apply_all(checks: list[ClueCheck], cat: EntityCategory, idx: FactIndex, anchor: Entity | None) -> list[Entity]:
    cands = idx.by_category[cat]
    for c in checks:
        cands = apply_check(c, cands, idx, anchor)
    return cands


class _Search:
    def __init__(self, idx: FactIndex, key: tuple) -> None:
        self.idx, self.key, self.budget = idx, key, SEARCH_BUDGET

    def segment(self, plan: SegmentPlan, anchor: Entity | None, want_set: bool, pos: str) -> list[BuiltClue] | None:
        start = self.idx.by_category[plan.category]
        return self._dfs(plan, anchor, want_set, pos, start, [])

    def _dfs(self, plan: SegmentPlan, anchor, want_set: bool, pos: str, cands: list[Entity],
             built: list[BuiltClue]) -> list[BuiltClue] | None:
        i = len(built)
        remaining = plan.length - i - 1
        opts = candidate_checks(plan.category, cands, self.idx, anchor, anchor_only=(i == 0 and anchor is not None))
        # Choose a check kind first, then an option within it, so numerous
        # threshold options do not crowd out rarer clue kinds; kinds already used in the segment go last.
        used = Counter(b.check.kind for b in built)
        opts.sort(key=lambda c: (used[c.kind], _h(*self.key, pos, i, c.kind), _h(*self.key, pos, i, _check_key(c))))
        for c in opts:
            self.budget -= 1
            if self.budget <= 0:
                return None
            after = apply_check(c, cands, self.idx, anchor)
            n = len(after)
            if not 1 <= n < len(cands):
                continue
            if remaining == 0:
                if (want_set and n < 2) or (not want_set and n != 1):
                    continue
            elif n < remaining + 1 + int(want_set):
                continue
            nxt = [*built, BuiltClue(check=c, before=len(cands), after=n)]
            if remaining == 0:
                if self._necessary(plan, anchor, [b.check for b in nxt], after):
                    return nxt
                continue
            found = self._dfs(plan, anchor, want_set, pos, after, nxt)
            if found is not None:
                return found
            if self.budget <= 0:
                return None
        return None

    def _necessary(self, plan: SegmentPlan, anchor, checks: list[ClueCheck], result: list[Entity]) -> bool:
        want = {e.entity_id for e in result}
        for j in range(len(checks)):
            rest = checks[:j] + checks[j + 1:]
            if {e.entity_id for e in _apply_all(rest, plan.category, self.idx, anchor)} == want:
                return False
        return True


def _compositions(n: int) -> list[list[int]]:
    out: list[list[int]] = []

    def rec(left: int, parts: list[int]) -> None:
        if left == 0:
            out.append(parts)
            return
        for p in range(2, min(MAX_SEGMENT_CLUES, left) + 1):
            if len(parts) < 3:
                rec(left - p, [*parts, p])

    rec(n, [])
    return out


def _category_sequences(k: int) -> list[list[EntityCategory]]:
    seqs: list[list[EntityCategory]] = [[c] for c in EntityCategory]
    for _ in range(k - 1):
        seqs = [[*s, c] for s in seqs for c in EntityCategory if (s[-1], c) in ANCHOR_CHECKS]
    return seqs


def _answer_value(kind: AnswerStepKind, final: Entity | None, result: list[Entity], anchor: Entity | None):
    match kind:
        case AnswerStepKind.ENTITY_AREA:
            return final.area
        case AnswerStepKind.ENTITY_LENGTH:
            return final.length
        case AnswerStepKind.ENTITY_RADIUS:
            return final.radius
        case AnswerStepKind.ENTITY_CENTER:
            return final.center
        case AnswerStepKind.DISTANCE_TO_ANCHOR:
            return _dist(final.center, anchor.center)
        case AnswerStepKind.SET_COUNT:
            return len(result)
    raise ValueError(kind)


def _identity(pf: ProgramFacts, segments: list[Segment], step: AnswerStep) -> str:
    body = {"program_sha256": pf.program_sha256,
            "segments": [{"category": s.category, "checks": [c.check.model_dump(mode="json") for c in s.clues]}
                         for s in segments],
            "answer_step": step.model_dump(mode="json")}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def _finish(pf: ProgramFacts, target: TargetCategory, segments: list[Segment], step: AnswerStep, gold,
            clue_count: int) -> TaskDefinition:
    from experiments.old.cq_query_scratch.compile_query import compile_query

    meaning, fmt = ANSWER_SPECS[step.kind]
    ident = _identity(pf, segments, step)
    task = TaskDefinition(
        task_id="cqt_" + ident[:16], definition_sha256="0" * 64, program_id=pf.program_id,
        program_sha256=pf.program_sha256, source_id=pf.source_id, cadevolve_program_family_id=pf.family_id,
        target_category=target, segments=segments, answer_meaning=meaning, answer_step=step,
        native_answer_format=fmt, gold_answer=gold, clue_step_count=clue_count,
        task_reasoning_step_count=clue_count + 1,
        validity=TaskValidity(every_clue_narrows=True, every_clue_necessary=True, unique_answer=True,
                              geometry_required=True),
        gold_query="pending", provenance={"constructor": "segments-v1", "seed": SEED})
    task.gold_query = compile_query(task, pf)
    task.definition_sha256 = hashlib.sha256(task.model_dump_json(exclude={"prompt"}).encode()).hexdigest()
    return task


def build_step1(pf: ProgramFacts, idx: FactIndex, slot: int) -> TaskDefinition | None:
    kinds = [k for k in ANSWER_SPECS if k.value.startswith(("final_", "state_", "operation_"))]
    kind = _hash_order(kinds, pf.program_id, 1, slot)[0]
    fs = idx.final_state
    step = AnswerStep(kind=kind)
    target = TargetCategory.SOLID_STATE
    match kind:
        case AnswerStepKind.FINAL_VOLUME:
            gold = fs.volume
        case AnswerStepKind.FINAL_SURFACE_AREA:
            gold = fs.area
        case AnswerStepKind.FINAL_CENTER:
            gold = fs.center
        case AnswerStepKind.FINAL_FACE_COUNT:
            gold = fs.face_count
        case AnswerStepKind.FINAL_EDGE_COUNT:
            gold = fs.edge_count
        case _:
            states = [s for s in pf.states if s.result_var != pf.final_var and
                      (kind == AnswerStepKind.STATE_VOLUME or s.has_before_solid)]
            if not states:
                return None
            s = _hash_order(states, pf.program_id, 1, slot, "state", key=lambda s: s.result_var)[0]
            step = AnswerStep(kind=kind, operation_var=s.result_var, receiver_var=s.receiver_var, method=s.method,
                              source_line=s.source_line)
            match kind:
                case AnswerStepKind.STATE_VOLUME:
                    gold = s.volume
                case AnswerStepKind.OPERATION_VOLUME_CHANGE:
                    gold, target = s.volume - s.before_volume, TargetCategory.OPERATION
                case _:
                    gold, target = s.face_count - s.before_face_count, TargetCategory.OPERATION
    return _finish(pf, target, [], step, gold, 0)


def build_task(pf: ProgramFacts, idx: FactIndex, step_count: int, slot: int) -> TaskDefinition | GenerationFailure:
    """Construct one task with exactly ``step_count`` task reasoning steps, deterministically."""
    if step_count == 1:
        t = build_step1(pf, idx, slot)
        return t or GenerationFailure(program_id=pf.program_id, step_count=1, slot=slot, reason="no_named_target")
    clue_count = step_count - 1
    key = (pf.program_id, step_count, slot)
    search = _Search(idx, key)
    for parts in _hash_order(_compositions(clue_count), *key, "parts", key=str):
        for cats in _hash_order(_category_sequences(len(parts)), *key, "cats", parts, key=str):
            for answer_kind in _hash_order(FINAL_ANSWERS[cats[-1]], *key, "answer", parts, cats):
                if answer_kind == AnswerStepKind.DISTANCE_TO_ANCHOR and len(parts) == 1:
                    continue
                want_set = answer_kind == AnswerStepKind.SET_COUNT
                segments: list[Segment] = []
                anchor: Entity | None = None
                order = 0
                result: list[Entity] = []
                for si, (length, cat) in enumerate(zip(parts, cats)):
                    last = si == len(parts) - 1
                    built = search.segment(SegmentPlan(category=cat, length=length), anchor,
                                           want_set=last and want_set, pos=f"{parts}{cats}{answer_kind}{si}")
                    if built is None:
                        break
                    result = _apply_all([b.check for b in built], cat, idx, anchor)
                    clues = []
                    for b in built:
                        order += 1
                        clues.append(TaskClue(
                            clue_id=f"c{order}", order=order, clue_type=clue_type_of(b.check.kind),
                            subject_category=cat, anchor_label=LABELS[si - 1] if anchor is not None and b.check.kind
                            in {k for v in ANCHOR_CHECKS.values() for k in v} else None,
                            check=b.check, result=ClueResult(before_count=b.before, after_count=b.after)))
                    segments.append(Segment(label=LABELS[si], category=cat, clues=clues,
                                            bound_entity_ids=[e.entity_id for e in result]))
                    if not last:
                        anchor = result[0]
                else:
                    final = result[0] if len(result) == 1 else None
                    if answer_kind == AnswerStepKind.ENTITY_RADIUS and not (isinstance(final, EdgeFact)
                                                                           and final.radius):
                        continue
                    prev = anchor
                    gold = _answer_value(answer_kind, final, result, prev)
                    target = (TargetCategory.SCALAR_VALUE if want_set else TargetCategory(cats[-1].value))
                    step = AnswerStep(kind=answer_kind,
                                      anchor_label=segments[-2].label if answer_kind ==
                                      AnswerStepKind.DISTANCE_TO_ANCHOR else None)
                    return _finish(pf, target, segments, step, gold, clue_count)
                if search.budget <= 0:
                    return GenerationFailure(program_id=pf.program_id, step_count=step_count, slot=slot,
                                             reason="search_budget_exhausted")
    return GenerationFailure(program_id=pf.program_id, step_count=step_count, slot=slot, reason="no_valid_chain")
