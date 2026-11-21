"""Parent side of kernel execution: limits, throttling, canonical IDs, typed facts.

Implements the subset of 02b this experiment needs (solid states, entity tables with
fingerprint-derived entity IDs, face/edge/vertex incidence, face adjacency), following
docs/dataset/implementation/pipeline/extraction/canonicalization.md for numbers and hashes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

from pydantic import BaseModel, Field

from experiments.old.cq_query_scratch.models import (
    EdgeFact,
    FaceFact,
    FaceFingerprint,
    Point3,
    ProgramFacts,
    QueryExecution,
    SolidStateFact,
    VertexFact,
)

log = logging.getLogger(__name__)

CHILD_TIMEOUT_S = 30.0
CHILD_MEMORY_BYTES = 2 * 1024**3
MAX_CONCURRENT_CHILDREN = int(os.environ.get("CQ_SCRATCH_KERNEL_WORKERS", "4"))
PAUSE_AFTER_CHILD_S = float(os.environ.get("CQ_SCRATCH_KERNEL_PAUSE_S", "0"))
_child_slots = threading.BoundedSemaphore(MAX_CONCURRENT_CHILDREN)
_RESULT_MARKER = "\n__RESULT__"


class ChildOutcome(BaseModel):
    ok: bool
    payload: dict = Field(default_factory=dict)
    error_type: str | None = None
    message: str | None = None
    timed_out: bool = False


def run_child(mode: str, request: BaseModel, timeout_s: float = CHILD_TIMEOUT_S) -> ChildOutcome:
    """Run kernel_child in a throttled child process; failures are data."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write(request.model_dump_json())
        in_path = fh.name
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    # prlimit wrapper instead of preexec_fn, which is unsafe with the eval thread pool.
    cmd = ["prlimit", f"--as={CHILD_MEMORY_BYTES}", sys.executable, "-m",
           "experiments.old.cq_query_scratch.kernel_child", mode, in_path]
    repo_root = Path(__file__).resolve().parents[3]
    with _child_slots:
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_s, env=env, cwd=repo_root
            )
        except subprocess.TimeoutExpired:
            return ChildOutcome(ok=False, error_type="timeout", message=f">{timeout_s}s", timed_out=True)
        finally:
            os.unlink(in_path)
            time.sleep(PAUSE_AFTER_CHILD_S)
    if _RESULT_MARKER not in proc.stdout:
        tail = (proc.stderr or "")[-1500:]
        kind = "memory" if "MemoryError" in tail or proc.returncode in (-9, 137) else "child_crash"
        return ChildOutcome(ok=False, error_type=kind, message=tail)
    out = json.loads(proc.stdout.rsplit(_RESULT_MARKER, 1)[1])
    if not out.get("ok"):
        return ChildOutcome(ok=False, error_type=out.get("error_type"), message=out.get("message"))
    return ChildOutcome(ok=True, payload=out)


# ---------------------------------------------------------------- canonicalization


def canon_number(x: float) -> str:
    """9-decimal round-half-even, -0 -> 0, decimal string without exponent or trailing zeros."""
    if x != x or x in (float("inf"), float("-inf")):
        raise ValueError("non-finite value")
    d = Decimal(repr(x)).quantize(Decimal("1e-9"), rounding=ROUND_HALF_EVEN)
    if d == 0:
        return "0"
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def round9(x: float) -> float:
    return float(canon_number(x))


def round_point(p: list[float]) -> Point3:
    return (round9(p[0]), round9(p[1]), round9(p[2]))


def canonical_json(value) -> str:
    """canonical_json from canonicalization.md; floats are emitted as canonical decimal tokens."""
    match value:
        case bool():
            return "true" if value else "false"
        case None:
            return "null"
        case int():
            return str(value)
        case float():
            return canon_number(value)
        case str():
            return json.dumps(value, ensure_ascii=True)
        case list() | tuple():
            return "[" + ",".join(canonical_json(v) for v in value) + "]"
        case dict():
            items = sorted(value.items())
            return "{" + ",".join(f"{json.dumps(k)}:{canonical_json(v)}" for k, v in items) + "}"
    raise TypeError(type(value).__name__)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def entity_id(state_id: str, category: str, fields: dict) -> tuple[str, str]:
    fp_json = canonical_json({"category": category, "fields": fields})
    fp_sha = _sha("cadqa.fingerprint.v1\0" + fp_json)
    return "ent:" + _sha(f"cadqa.entity.v1\0{state_id}\0{category}\0{fp_sha}"), fp_json


# ---------------------------------------------------------------- extraction


class AssignmentInfo(BaseModel):
    order: int = Field(ge=0)
    var: str = Field(min_length=1, max_length=64)
    receiver_var: str | None = None
    method: str = Field(min_length=1, max_length=64)
    source_line: int = Field(ge=1)


class ExtractionError(RuntimeError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def extract_program(
    *, source_id: str, collection: str, family_id: str, program_id: str, program_sha256: str,
    program_text: str, assignments: list[AssignmentInfo], final_var: str,
) -> ProgramFacts:
    from experiments.old.cq_query_scratch.kernel_child import ExtractRequest

    req = ExtractRequest(
        program_text=program_text, assignment_vars=[a.var for a in assignments],
        receivers={a.var: a.receiver_var for a in assignments if a.receiver_var}, final_var=final_var,
    )
    out = run_child("extract", req)
    if not out.ok:
        raise ExtractionError(out.error_type or "unknown", out.message or "")
    raw_states: dict = out.payload["states"]
    by_var = {a.var: a for a in assignments}
    states = []
    for var, s in raw_states.items():
        a = by_var[var]
        op_id = f"op:{a.order:06d}"
        b = s["before"]
        states.append(
            SolidStateFact(
                state_id=f"state:{op_id}", operation_id=op_id, result_var=var, receiver_var=a.receiver_var,
                method=a.method, source_line=a.source_line, volume=round9(s["volume"]), area=round9(s["area"]),
                center=round_point(s["center"]), face_count=s["face_count"], edge_count=s["edge_count"],
                vertex_count=s["vertex_count"],
                faces=[FaceFingerprint(center=round_point(f["center"]), area=round9(f["area"])) for f in s["faces"]],
                has_before_solid=b is not None, before_volume=round9(b["volume"]) if b else 0.0,
                before_face_count=b["face_count"] if b else 0,
                before_faces=[FaceFingerprint(center=round_point(f["center"]), area=round9(f["area"]))
                              for f in (b["faces"] if b else [])],
            )
        )
    states.sort(key=lambda s: s.operation_id)
    final_state = next((s for s in states if s.result_var == final_var), None)
    if final_state is None:
        raise ExtractionError("missing_state", final_var)
    sid = final_state.state_id
    raw = out.payload["final"]

    vertex_ids, vertices = [], []
    for v in raw["vertices"]:
        point = round_point(v["point"])
        eid, _ = entity_id(sid, "vertex", {"point": list(point)})
        vertex_ids.append(eid)
        vertices.append(VertexFact(entity_id=eid, point=point))
    edge_ids, edges = [], []
    for e in raw["edges"]:
        start, end, length = round_point(e["start"]), round_point(e["end"]), round9(e["length"])
        eid, _ = entity_id(sid, "edge", {"start": list(start), "end": list(end), "length": length})
        edge_ids.append(eid)
        edges.append(
            EdgeFact(
                entity_id=eid, kind=e["kind"], length=length, center=round_point(e["center"]), start=start, end=end,
                direction=round_point(e["direction"]) if e["direction"] else None,
                radius=round9(e["radius"]) if e["radius"] else None,
                vertex_ids=sorted(vertex_ids[i] for i in e["vertices"]),
            )
        )
    faces = []
    for f in raw["faces"]:
        center, area, normal = round_point(f["center"]), round9(f["area"]), round_point(f["normal"])
        bbox_min, bbox_max = round_point(f["bbox_min"]), round_point(f["bbox_max"])
        fields = {"centroid": list(center), "area": area, "normal": list(normal),
                  "bbox": {"min": list(bbox_min), "max": list(bbox_max)}}
        eid, _ = entity_id(sid, "face", fields)
        faces.append(
            FaceFact(
                entity_id=eid, kind=f["kind"], area=area, center=center, normal=normal, bbox_min=bbox_min,
                bbox_max=bbox_max, edge_ids=sorted(edge_ids[i] for i in f["edges"]),
                vertex_ids=sorted(vertex_ids[i] for i in f["vertices"]),
            )
        )
    for ids, cat in ((vertex_ids, "vertex"), (edge_ids, "edge"), ([f.entity_id for f in faces], "face")):
        if len(set(ids)) != len(ids):
            raise ExtractionError("fingerprint_collision", cat)
    edge_to_faces: dict[str, list[str]] = {}
    for f in faces:
        for e in f.edge_ids:
            edge_to_faces.setdefault(e, []).append(f.entity_id)
    pairs = {tuple(sorted((a, b))) for fs in edge_to_faces.values() for a in fs for b in fs if a != b}
    return ProgramFacts(
        program_id=program_id, program_sha256=program_sha256, source_id=source_id, collection=collection,
        family_id=family_id, program_text=program_text, final_var=final_var, final_state_id=sid, states=states,
        faces=sorted(faces, key=lambda x: x.entity_id), edges=sorted(edges, key=lambda x: x.entity_id),
        vertices=sorted(vertices, key=lambda x: x.entity_id), adjacent_face_pairs=sorted(pairs),
    )


def run_queries(program_text: str, queries: list[str], timeout_s: float | None = None,
                explore: bool = False) -> list[QueryExecution]:
    """Run queries after one program execution. A child-level failure fails every query."""
    from experiments.old.cq_query_scratch.kernel_child import QueriesRequest

    out = run_child("queries", QueriesRequest(program_text=program_text, queries=queries, explore=explore),
                    timeout_s=timeout_s or CHILD_TIMEOUT_S + 5.0 * len(queries))
    if not out.ok:
        return [QueryExecution(ok=False, error_type=out.error_type, message=out.message, timed_out=out.timed_out)
                for _ in queries]
    return [QueryExecution(**r) for r in out.payload["results"]]
