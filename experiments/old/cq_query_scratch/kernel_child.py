"""Child-process CadQuery runner (02b execution boundary: process isolation, not a sandbox).

Modes:
- ``extract``: run a program and dump raw solid-state and final-state topology facts.
- ``queries``: run a program once, then each query in a shallow copy of its namespace.

The parent (``kernel.py``) owns limits, canonical IDs, and typing of the output.
"""

from __future__ import annotations

import json
import math
import sys
import traceback

from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    program_text: str = Field(min_length=1)
    assignment_vars: list[str]
    receivers: dict[str, str] = Field(default_factory=dict, description="var -> receiver var")
    final_var: str = Field(min_length=1)


class QueriesRequest(BaseModel):
    program_text: str = Field(min_length=1)
    queries: list[str]
    explore: bool = Field(default=False, description="Return repr(answer) of any type and captured stdout.")


def _p(v) -> list[float]:
    return [float(v.x), float(v.y), float(v.z)]


def _single_shape(value):
    import cadquery as cq

    if isinstance(value, cq.Workplane):
        shapes = [o for o in value.vals() if isinstance(o, cq.Shape)]
        if len(shapes) != 1:
            return None
        value = shapes[0]
    if isinstance(value, cq.Shape) and value.Solids():
        return value
    return None


def _before_solid(receiver):
    """The solid an operation modified: what receiver.findSolid() returns (None if no solid)."""
    import cadquery as cq

    if not isinstance(receiver, cq.Workplane):
        return None
    try:
        solid = receiver.findSolid()
    except ValueError:
        return None
    return solid if isinstance(solid, cq.Shape) and solid.Solids() else None


def _state_dump(shape) -> dict:
    faces = shape.Faces()
    return {
        "volume": shape.Volume(),
        "area": shape.Area(),
        "center": _p(shape.Center()),
        "face_count": len(faces),
        "edge_count": len(shape.Edges()),
        "vertex_count": len(shape.Vertices()),
        "faces": [{"center": _p(f.Center()), "area": f.Area()} for f in faces],
    }


def _index_of(shape, pool, by_hash) -> int:
    for i in by_hash.get(shape.hashCode(), []):
        if pool[i].isSame(shape):
            return i
    raise RuntimeError("unmapped_entity")


def _final_dump(shape) -> dict:
    faces, edges, vertices = shape.Faces(), shape.Edges(), shape.Vertices()
    e_hash: dict[int, list[int]] = {}
    for i, e in enumerate(edges):
        e_hash.setdefault(e.hashCode(), []).append(i)
    v_hash: dict[int, list[int]] = {}
    for i, v in enumerate(vertices):
        v_hash.setdefault(v.hashCode(), []).append(i)
    face_rows = []
    for f in faces:
        bb = f.BoundingBox()
        face_rows.append(
            {
                "kind": f.geomType(),
                "area": f.Area(),
                "center": _p(f.Center()),
                "normal": _p(f.normalAt()),
                "bbox_min": [bb.xmin, bb.ymin, bb.zmin],
                "bbox_max": [bb.xmax, bb.ymax, bb.zmax],
                "edges": sorted({_index_of(e, edges, e_hash) for e in f.Edges()}),
                "vertices": sorted({_index_of(v, vertices, v_hash) for v in f.Vertices()}),
            }
        )
    edge_rows = []
    for e in edges:
        kind = e.geomType()
        start, end = e.startPoint(), e.endPoint()
        direction = None
        if kind == "LINE":
            d = end - start
            if d.Length > 0:
                direction = _p(d.normalized())
        edge_rows.append(
            {
                "kind": kind,
                "length": e.Length(),
                "center": _p(e.Center()),
                "start": _p(start),
                "end": _p(end),
                "direction": direction,
                "radius": e.radius() if kind == "CIRCLE" else None,
                "vertices": sorted({_index_of(v, vertices, v_hash) for v in e.Vertices()}),
            }
        )
    vertex_rows = [{"point": _p(v.Center())} for v in vertices]
    return {"faces": face_rows, "edges": edge_rows, "vertices": vertex_rows}


def run_extract(req: ExtractRequest) -> dict:
    ns: dict = {}
    exec(compile(req.program_text, "<program>", "exec"), ns)
    states = {}
    for var in req.assignment_vars:
        shape = _single_shape(ns.get(var))
        if shape is not None:
            states[var] = _state_dump(shape)
            receiver = req.receivers.get(var)
            before = _before_solid(ns.get(receiver)) if receiver else None
            states[var]["before"] = _state_dump(before) if before is not None else None
    final = _single_shape(ns.get(req.final_var))
    if final is None:
        return {"ok": False, "error_type": "non_single_solid_final", "message": req.final_var}
    return {"ok": True, "states": states, "final": _final_dump(final)}


def _jsonable_answer(value):
    import cadquery as cq

    if isinstance(value, cq.Vector):
        return _p(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("non-finite answer")
        return value
    if isinstance(value, (tuple, list)) and all(isinstance(x, (int, float)) for x in value):
        return [float(x) for x in value]
    if hasattr(value, "item"):  # numpy scalar
        return _jsonable_answer(value.item())
    raise TypeError(f"unsupported answer type {type(value).__name__}")


def run_queries(req: QueriesRequest) -> dict:
    import contextlib
    import io

    ns: dict = {}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(req.program_text, "<program>", "exec"), ns)
    results = []
    for query in req.queries:
        local = dict(ns)
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                exec(compile(query, "<query>", "exec"), local)
            if req.explore:
                results.append({"ok": True, "stdout": out.getvalue()[-4000:],
                                "repr_text": repr(local["answer"])[:4000] if "answer" in local else "<not assigned>"})
                continue
            if "answer" not in local:
                results.append({"ok": False, "error_type": "NoAnswer", "message": "answer was not assigned"})
                continue
            results.append({"ok": True, "answer": _jsonable_answer(local["answer"])})
        except Exception as exc:  # model code: every failure is data
            results.append(
                {
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "message": "".join(traceback.format_exception_only(exc)).strip()[-2000:],
                    "stdout": out.getvalue()[-4000:],
                }
            )
    return {"ok": True, "results": results}


def main() -> int:
    mode, in_path = sys.argv[1], sys.argv[2]
    raw = json.loads(open(in_path).read())
    try:
        match mode:
            case "extract":
                out = run_extract(ExtractRequest(**raw))
            case "queries":
                out = run_queries(QueriesRequest(**raw))
            case _:
                raise SystemExit(f"unknown mode {mode}")
    except Exception as exc:
        out = {"ok": False, "error_type": type(exc).__name__, "message": str(exc)[-2000:]}
    sys.stdout.write("\n__RESULT__" + json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
