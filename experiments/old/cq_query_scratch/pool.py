"""Program pool: 01b selection rules and 01d normalization on a small pool, plus an
approximate 02a accepted-subset check. Old 2026-10-19 artifacts only pick programs.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import re
import subprocess
import time
from pathlib import Path

import pyarrow.parquet as pq
from pydantic import BaseModel, Field

from experiments.old.cq_query_scratch.kernel import (
    AssignmentInfo,
    ExtractionError,
    extract_program,
)
from experiments.old.cq_query_scratch.models import SEED, PoolEntry, ProgramFacts, Rejection

log = logging.getLogger(__name__)

RUFF_BIN = Path(__file__).resolve().parents[3] / ".venv" / "bin" / "ruff"
MIN_FINAL_FACES = 8
FORBIDDEN_SELECTOR_METHODS = {"wires", "solids"}


class CandidateProgram(BaseModel):
    source_id: str = Field(min_length=1, max_length=64)
    collection: str = Field(min_length=1, max_length=64)
    path_family: str = Field(min_length=1, max_length=400)
    code_hash: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1)


class AcceptedSubset(BaseModel):
    assignments: list[AssignmentInfo]
    final_var: str = Field(min_length=1, max_length=64)


class SubsetRejected(ValueError):
    pass


def family_id(collection: str, path_family: str, source_id: str) -> str:
    """01b family derivation from the last path_family component."""
    last = path_family.rstrip("/").split("/")[-1].removesuffix(".py")
    match collection:
        case c if c.endswith("-core"):
            return "cadevolve:" + re.sub(r"[^a-z0-9]", "", re.sub(r"_\d+$", "", last).lower())
        case c if c.startswith("ABC"):
            return "abc:" + re.sub(r"_trimesh_\d+$", "", last)
        case c if c.startswith("ShapeNet"):
            return "shapenet:" + last
    return f"unknown:{source_id}"


def normalize(code: str) -> str:
    """01d: ast.unparse, pinned ruff format (isolated config), exactly one trailing newline."""
    text = code.replace("\r\n", "\n").lstrip("﻿")
    unparsed = ast.unparse(ast.parse(text))
    out = subprocess.run([str(RUFF_BIN), "format", "--isolated", "-"], input=unparsed, capture_output=True,
                         text=True, check=True)
    return out.stdout.rstrip("\n") + "\n"


def ruff_version() -> str:
    return subprocess.run([str(RUFF_BIN), "--version"], capture_output=True, text=True, check=True).stdout.strip()


def check_accepted_subset(program_text: str) -> AcceptedSubset:
    """Approximation of the 02a P0/P1 accepted subset (not the full method allowlist)."""
    tree = ast.parse(program_text)
    assignments: list[AssignmentInfo] = []
    aliases: dict[str, str] = {}
    seen: set[str] = set()
    for order, stmt in enumerate(tree.body):
        match stmt:
            case ast.Import(names=[ast.alias(name="cadquery", asname="cq")]):
                continue
            case ast.Assign(targets=[ast.Name(id=var)], value=value):
                if var in seen:
                    raise SubsetRejected(f"duplicate_target:{var}")
                seen.add(var)
                for node in ast.walk(value):
                    if isinstance(node, (ast.Lambda, ast.ListComp, ast.GeneratorExp, ast.DictComp, ast.SetComp)):
                        raise SubsetRejected("expression_not_allowed")
                match value:
                    case ast.Name(id=src):
                        aliases[var] = src
                    case ast.Call(func=ast.Attribute(value=ast.Name(id=receiver), attr=method)):
                        if method in FORBIDDEN_SELECTOR_METHODS:
                            raise SubsetRejected(f"selector_scope:{method}")
                        assignments.append(AssignmentInfo(
                            order=order, var=var, receiver_var=None if receiver == "cq" else receiver,
                            method=method, source_line=stmt.lineno))
                    case ast.Call(func=ast.Attribute(value=ast.Call())):
                        raise SubsetRejected("chained_call")
                    case _:
                        raise SubsetRejected("unsupported_assignment")
            case _:
                raise SubsetRejected(f"statement_not_allowed:{type(stmt).__name__}")
    if "result" not in seen:
        raise SubsetRejected("missing_final_result")
    final = "result"
    while final in aliases:
        final = aliases[final]
    return AcceptedSubset(assignments=assignments, final_var=final)


def _final_alias(code: str) -> str:
    aliases = {}
    for st in ast.parse(code).body:
        if isinstance(st, ast.Assign) and isinstance(st.value, ast.Name) and isinstance(st.targets[0], ast.Name):
            aliases[st.targets[0].id] = st.value.id
    final = "result"
    while final in aliases:
        final = aliases[final]
    return final


def old_graph_final_face_counts(regen_dir: Path, cache_path: Path) -> dict[str, int]:
    """source_id -> number of final-state kernel faces in the old graph (alias-resolved)."""
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    counts: dict[str, int] = {}
    for shard in sorted((regen_dir / "graph" / "graphs").glob("*.parquet")):
        table = pq.read_table(shard, columns=["source", "nodes"])
        for row in table.to_pylist():
            final = _final_alias(row["source"]["source_code"])
            key = f"snapshot:{final}:faces"
            nodes = json.loads(row["nodes"])
            counts[row["source"]["source_id"]] = sum(
                1 for n in nodes if n["type"] == "face" and n["properties"].get("stable_selector") == key)
        del table
        log.info("indexed old graph shard %s", shard.name)
        time.sleep(2.0)  # thermal throttle
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(counts, sort_keys=True))
    return counts


def load_candidates(regen_dir: Path, graph_counts: dict[str, int], rejections: list[Rejection]) -> list[CandidateProgram]:
    traces = {
        r["source_id"]: r for r in pq.read_table(
            regen_dir / "traces_combined.parquet", columns=["source_id", "execution_status", "snapshots"]).to_pylist()
    }
    rows = pq.read_table(regen_dir / "sources.parquet", columns=[
        "source_id", "source_subtree", "source_collection", "path_family", "normalized_source_code_hash",
        "normalized_code"]).to_pylist()
    out: list[CandidateProgram] = []
    for r in rows:
        sid = r["source_id"]
        if r["source_subtree"] != "CADEvolve-C":
            rejections.append(Rejection(stage="pool", subject=sid, reason="tier_not_c"))
            continue
        tr = traces.get(sid)
        if not tr or tr["execution_status"] != "ok" or not tr["snapshots"]:
            rejections.append(Rejection(stage="pool", subject=sid, reason="old_trace_failed"))
            continue
        trace_faces = tr["snapshots"][-1]["topology"]["faces"]
        if graph_counts.get(sid, 0) == 0 or graph_counts[sid] != trace_faces:
            rejections.append(Rejection(stage="pool", subject=sid, reason="old_graph_final_faces_missing"))
            continue
        out.append(CandidateProgram(source_id=sid, collection=r["source_collection"], path_family=r["path_family"],
                                    code_hash=r["normalized_source_code_hash"], code=r["normalized_code"]))
    return out


def order_candidates(cands: list[CandidateProgram], rejections: list[Rejection]) -> list[CandidateProgram]:
    """01b: dedupe within collection (smallest source_id), family cap 2, sha256(seed||source_id) order."""
    by_key: dict[tuple[str, str], CandidateProgram] = {}
    for c in sorted(cands, key=lambda c: c.source_id):
        key = (c.collection, c.code_hash)
        if key in by_key:
            rejections.append(Rejection(stage="pool", subject=c.source_id, reason="duplicate_code_hash"))
            continue
        by_key[key] = c
    ordered = sorted(by_key.values(), key=lambda c: hashlib.sha256((SEED + c.source_id).encode()).hexdigest())
    per_family: dict[str, int] = {}
    out = []
    for c in ordered:
        fam = family_id(c.collection, c.path_family, c.source_id)
        if per_family.get(fam, 0) >= 2:
            rejections.append(Rejection(stage="pool", subject=c.source_id, reason="family_cap"))
            continue
        per_family[fam] = per_family.get(fam, 0) + 1
        out.append(c)
    return out


def build_pool(regen_dir: Path, out_dir: Path, target: int) -> tuple[list[PoolEntry], list[ProgramFacts], list[Rejection]]:
    rejections: list[Rejection] = []
    counts = old_graph_final_face_counts(regen_dir, out_dir / "old_graph_final_face_counts.json")
    ordered = order_candidates(load_candidates(regen_dir, counts, rejections), rejections)
    log.info("pool candidates after 01b rules: %d", len(ordered))
    entries: list[PoolEntry] = []
    facts: list[ProgramFacts] = []
    for c in ordered:
        if len(entries) >= target:
            break
        try:
            text = normalize(c.code)
            subset = check_accepted_subset(text)
        except (SyntaxError, subprocess.CalledProcessError, SubsetRejected) as exc:
            rejections.append(Rejection(stage="02a_subset", subject=c.source_id, reason=str(exc)[:80] or "rejected"))
            continue
        sha = hashlib.sha256(text.encode()).hexdigest()
        fam = family_id(c.collection, c.path_family, c.source_id)
        try:
            pf = extract_program(source_id=c.source_id, collection=c.collection, family_id=fam,
                                 program_id=f"cadqaprog:{sha}", program_sha256=sha, program_text=text,
                                 assignments=subset.assignments, final_var=subset.final_var)
        except ExtractionError as exc:
            rejections.append(Rejection(stage="02b_extract", subject=c.source_id, reason=exc.reason[:80],
                                        detail=exc.detail[:2000]))
            continue
        if len(pf.faces) < MIN_FINAL_FACES:
            rejections.append(Rejection(stage="pool", subject=c.source_id, reason="too_few_final_faces"))
            continue
        entries.append(PoolEntry(source_id=c.source_id, collection=c.collection, family_id=fam,
                                 program_id=pf.program_id, program_sha256=sha,
                                 order_key=hashlib.sha256((SEED + c.source_id).encode()).hexdigest(),
                                 final_face_count=len(pf.faces)))
        facts.append(pf)
        log.info("pool %d/%d: %s (%s, %d faces)", len(entries), target, c.source_id, c.collection, len(pf.faces))
    return entries, facts, rejections
