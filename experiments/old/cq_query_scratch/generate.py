"""Generate, select, and kernel-verify task definitions for each task reasoning step count."""

from __future__ import annotations

import hashlib
import logging
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, Field

from experiments.old.cq_query_scratch.definitions import (
    FactIndex,
    GenerationFailure,
    build_task,
)
from experiments.old.cq_query_scratch.grading import answers_match
from experiments.old.cq_query_scratch.kernel import MAX_CONCURRENT_CHILDREN, run_queries
from experiments.old.cq_query_scratch.models import (
    SEED,
    ProgramFacts,
    Rejection,
    TaskDefinition,
)

log = logging.getLogger(__name__)

SLOTS_PER_PROGRAM = 6
MAX_PER_PROGRAM = 3


class StepCountStats(BaseModel):
    step_count: int = Field(ge=1)
    attempts: int = Field(default=0, ge=0)
    constructed: int = Field(default=0, ge=0)
    duplicates: int = Field(default=0, ge=0)
    construction_failures: dict[str, int] = Field(default_factory=dict)
    gold_verified: int = Field(default=0, ge=0)
    gold_failures: dict[str, int] = Field(default_factory=dict)
    accepted: int = Field(default=0, ge=0)


def construct(facts: list[ProgramFacts], step_count: int, stats: StepCountStats) -> list[TaskDefinition]:
    seen: set[str] = set()
    out: list[TaskDefinition] = []
    failures: Counter[str] = Counter()
    for pf in facts:
        idx = FactIndex(pf)
        for slot in range(SLOTS_PER_PROGRAM):
            stats.attempts += 1
            result = build_task(pf, idx, step_count, slot)
            if isinstance(result, GenerationFailure):
                failures[result.reason] += 1
                continue
            if result.task_id in seen:
                stats.duplicates += 1
                continue
            seen.add(result.task_id)
            out.append(result)
    stats.constructed = len(out)
    stats.construction_failures = dict(sorted(failures.items()))
    return out


def select_and_verify(tasks: list[TaskDefinition], facts_by_id: dict[str, ProgramFacts], quota: int,
                      stats: StepCountStats, rejections: list[Rejection]) -> list[TaskDefinition]:
    """Accept up to ``quota`` tasks in identity-hash order, <= MAX_PER_PROGRAM per program,
    keeping only tasks whose gold query reproduces the gold answer in a fresh kernel run."""
    ordered = sorted(tasks, key=lambda t: hashlib.sha256((SEED + t.task_id).encode()).hexdigest())
    accepted: list[TaskDefinition] = []
    per_program: Counter[str] = Counter()
    gold_failures: Counter[str] = Counter()
    cursor = 0
    while len(accepted) < quota and cursor < len(ordered):
        batch: dict[str, list[TaskDefinition]] = defaultdict(list)
        need = quota - len(accepted)
        while cursor < len(ordered) and sum(len(v) for v in batch.values()) < need:
            t = ordered[cursor]
            cursor += 1
            if per_program[t.program_id] + len(batch[t.program_id]) >= MAX_PER_PROGRAM:
                continue
            batch[t.program_id].append(t)
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_CHILDREN) as pool:
            futures = {pid: pool.submit(run_queries, facts_by_id[pid].program_text, [t.gold_query for t in batch[pid]])
                       for pid in sorted(batch)}
        for program_id in sorted(batch):
            group = batch[program_id]
            results = futures[program_id].result()
            for t, r in zip(group, results):
                ok = r.ok and answers_match(r.answer, t.gold_answer, t.native_answer_format, t.tolerance_rel,
                                            t.tolerance_abs)
                if ok:
                    t.validity.gold_query_reproduces_answer = True
                    accepted.append(t)
                    per_program[program_id] += 1
                    continue
                reason = "gold_query_mismatch" if r.ok else f"gold_query_error:{r.error_type}"
                gold_failures[reason] += 1
                rejections.append(Rejection(stage="03b_gold_query", subject=t.task_id, reason=reason[:80],
                                            detail=f"gold={t.gold_answer} got={r.answer} {r.message or ''}"[:2000]))
        log.info("step %d: accepted %d/%d (cursor %d/%d)", stats.step_count, len(accepted), quota, cursor,
                 len(ordered))
    stats.gold_verified = len(accepted)
    stats.gold_failures = dict(sorted(gold_failures.items()))
    accepted = accepted[:quota]
    stats.accepted = len(accepted)
    return sorted(accepted, key=lambda t: hashlib.sha256((SEED + t.task_id).encode()).hexdigest())
