"""Compile a task definition into its gold CadQuery query.

The query runs after the program in the same namespace and assigns ``answer``. Each typed check
compiles to one list filter with the same tolerances the definitions use, so a kernel run of the
gold query must reproduce the gold answer computed from extracted facts.
"""

from __future__ import annotations

from experiments.old.cq_query_scratch.models import (
    COMPARISON_REL_TOL,
    FACE_MATCH_AREA_REL_TOL,
    FACE_MATCH_CENTER_TOL,
    PARALLEL_TOLERANCE_DEG,
    AnswerStepKind,
    Axis,
    CheckKind,
    ClueCheck,
    Comparator,
    EntityCategory,
    Extreme,
    Measure,
    ProgramFacts,
    TaskDefinition,
)

PREAMBLE = f'''import math
import cadquery as cq

_COS = math.cos(math.radians({PARALLEL_TOLERANCE_DEG}))
_SIN = math.sin(math.radians({PARALLEL_TOLERANCE_DEG}))
_S = result.val()


def _dir(x):
    if x.geomType() == "PLANE":
        return x.normalAt()
    return (x.endPoint() - x.startPoint()).normalized()


def _tol(v):
    return {COMPARISON_REL_TOL} * max(1.0, abs(v))


def _same_face(f, g):
    return (f.Center() - g.Center()).Length <= {FACE_MATCH_CENTER_TOL} and abs(f.Area() - g.Area()) <= {FACE_MATCH_AREA_REL_TOL} * max(1.0, abs(g.Area()))


def _modified_solid(receiver):
    try:
        s = receiver.findSolid()
    except ValueError:
        return None
    return s if isinstance(s, cq.Shape) and s.Solids() else None
'''

AXIS_CODE = {Axis.X: "cq.Vector(1, 0, 0)", Axis.Y: "cq.Vector(0, 1, 0)", Axis.Z: "cq.Vector(0, 0, 1)"}
LIST_CODE = {EntityCategory.FACE: "_S.Faces()", EntityCategory.EDGE: "_S.Edges()",
             EntityCategory.VERTEX: "_S.Vertices()"}


def measure_code(m: Measure, x: str) -> str:
    match m:
        case Measure.AREA:
            return f"{x}.Area()"
        case Measure.LENGTH:
            return f"{x}.Length()"
        case Measure.RADIUS:
            return f"{x}.radius()"
        case Measure.CENTER_X:
            return f"{x}.Center().x"
        case Measure.CENTER_Y:
            return f"{x}.Center().y"
        case Measure.CENTER_Z:
            return f"{x}.Center().z"


def _filter(cond: str) -> list[str]:
    return [f"_c = [x for x in _c if {cond}]"]


def check_code(c: ClueCheck, a: str | None) -> list[str]:
    """Lines that narrow ``_c`` by one check; ``a`` is the anchor variable name."""
    match c.kind:
        case CheckKind.GEOM_KIND:
            return _filter(f'x.geomType() == "{c.geom_kind}"')
        case CheckKind.AXIS_PARALLEL:
            return _filter(f"abs(_dir(x).dot({AXIS_CODE[c.axis]})) >= _COS")
        case CheckKind.AXIS_PERPENDICULAR:
            return _filter(f"abs(_dir(x).dot({AXIS_CODE[c.axis]})) <= _SIN")
        case CheckKind.AXIS_FACING:
            sign = "" if c.positive else "-"
            return _filter(f"{sign}_dir(x).dot({AXIS_CODE[c.axis]}) >= _COS")
        case CheckKind.THRESHOLD:
            op = ">" if c.comparator == Comparator.GREATER else "<"
            return _filter(f"{measure_code(c.measure, 'x')} {op} {c.threshold!r}")
        case CheckKind.EXTREME:
            fn = "max" if c.extreme == Extreme.MAX else "min"
            m = measure_code(c.measure, "x")
            return [f"_best = {fn}({m} for x in _c)", *_filter(f"abs({m} - _best) <= _tol(_best)")]
        case CheckKind.CREATED_BY:
            before = f"_modified_solid({c.receiver_var})" if c.receiver_var else "None"
            return [f"_after = {c.operation_var}.val().Faces()",
                    f"_before_solid = {before}",
                    "_before = _before_solid.Faces() if _before_solid is not None else []",
                    *_filter("any(_same_face(x, g) for g in _after) and not any(_same_face(x, g) for g in _before)")]
        case CheckKind.ADJACENT_TO_ANCHOR:
            return _filter(f"not x.isSame({a}) and any(e.isSame(h) for e in x.Edges() for h in {a}.Edges())")
        case CheckKind.PARALLEL_TO_ANCHOR:
            return _filter(f"not x.isSame({a}) and abs(_dir(x).dot(_dir({a}))) >= _COS")
        case CheckKind.PERPENDICULAR_TO_ANCHOR:
            return _filter(f"not x.isSame({a}) and abs(_dir(x).dot(_dir({a}))) <= _SIN")
        case CheckKind.EDGE_OF_ANCHOR_FACE:
            return _filter(f"any(x.isSame(h) for h in {a}.Edges())")
        case CheckKind.VERTEX_OF_ANCHOR_FACE | CheckKind.ENDPOINT_OF_ANCHOR_EDGE:
            return _filter(f"any(x.isSame(h) for h in {a}.Vertices())")
        case CheckKind.FACE_HAS_ANCHOR_EDGE:
            return _filter(f"any(e.isSame({a}) for e in x.Edges())")
        case CheckKind.SHARES_VERTEX_WITH_ANCHOR:
            return _filter(f"not x.isSame({a}) and any(v.isSame(w) for v in x.Vertices() for w in {a}.Vertices())")
        case CheckKind.EDGE_HAS_ANCHOR_VERTEX | CheckKind.FACE_HAS_ANCHOR_VERTEX:
            return _filter(f"any(v.isSame({a}) for v in x.Vertices())")
        case CheckKind.COMPARE_TO_ANCHOR:
            ma = measure_code(c.measure, a)
            if c.comparator == Comparator.GREATER:
                return _filter(f"{measure_code(c.measure, 'x')} > {ma} + _tol({ma})")
            return _filter(f"{measure_code(c.measure, 'x')} < {ma} - _tol({ma})")
    raise ValueError(c.kind)


def _step1_answer(task: TaskDefinition) -> str:
    s = task.answer_step
    before = f"_modified_solid({s.receiver_var})" if s.receiver_var else "None"
    match s.kind:
        case AnswerStepKind.FINAL_VOLUME:
            return "answer = _S.Volume()"
        case AnswerStepKind.FINAL_SURFACE_AREA:
            return "answer = _S.Area()"
        case AnswerStepKind.FINAL_CENTER:
            return "answer = _S.Center().toTuple()"
        case AnswerStepKind.FINAL_FACE_COUNT:
            return "answer = len(_S.Faces())"
        case AnswerStepKind.FINAL_EDGE_COUNT:
            return "answer = len(_S.Edges())"
        case AnswerStepKind.STATE_VOLUME:
            return f"answer = {s.operation_var}.val().Volume()"
        case AnswerStepKind.OPERATION_VOLUME_CHANGE:
            return (f"_b = {before}\n"
                    f"answer = {s.operation_var}.val().Volume() - (_b.Volume() if _b is not None else 0.0)")
        case AnswerStepKind.OPERATION_FACE_COUNT_CHANGE:
            return (f"_b = {before}\n"
                    f"answer = len({s.operation_var}.val().Faces()) - (len(_b.Faces()) if _b is not None else 0)")
    raise ValueError(s.kind)


def _final_answer(task: TaskDefinition) -> str:
    s = task.answer_step
    match s.kind:
        case AnswerStepKind.ENTITY_AREA:
            return "answer = _c[0].Area()"
        case AnswerStepKind.ENTITY_LENGTH:
            return "answer = _c[0].Length()"
        case AnswerStepKind.ENTITY_RADIUS:
            return "answer = _c[0].radius()"
        case AnswerStepKind.ENTITY_CENTER:
            return "answer = _c[0].Center().toTuple()"
        case AnswerStepKind.DISTANCE_TO_ANCHOR:
            return f"answer = (_c[0].Center() - _{s.anchor_label}.Center()).Length"
        case AnswerStepKind.SET_COUNT:
            return "answer = len(_c)"
    raise ValueError(s.kind)


def compile_query(task: TaskDefinition, pf: ProgramFacts) -> str:
    lines = [PREAMBLE]
    if not task.segments:
        lines.append(_step1_answer(task))
        return "\n".join(lines) + "\n"
    anchor: str | None = None
    for seg in task.segments:
        first, last = seg.clues[0].order, seg.clues[-1].order
        lines.append(f"# Clues {first}-{last}: {seg.category.value} {seg.label}")
        lines.append(f"_c = list({LIST_CODE[seg.category]})")
        for clue in seg.clues:
            lines += check_code(clue.check, anchor)
        anchor = f"_{seg.label}"
        if seg is not task.segments[-1]:
            lines.append(f"{anchor} = _c[0]")
    lines.append(_final_answer(task))
    return "\n".join(lines) + "\n"
