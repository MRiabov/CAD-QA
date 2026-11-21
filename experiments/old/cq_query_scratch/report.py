"""Per-step-count funnel and accuracy report (report.md)."""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from experiments.old.cq_query_scratch.generate import StepCountStats
from experiments.old.cq_query_scratch.models import (
    GradeResult,
    ModelCall,
    Outcome,
    TaskDefinition,
)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (center - half, center + half)


def _pct(k: int, n: int) -> str:
    if n == 0:
        return "-"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.0f}% [{100 * lo:.0f}, {100 * hi:.0f}]"


def _breakdown(title: str, keyed: dict[str, list[GradeResult]]) -> list[str]:
    lines = [f"### {title}", "", "| Value | n | Correct |", "|---|---|---|"]
    for key in sorted(keyed):
        gs = keyed[key]
        lines.append(f"| {key} | {len(gs)} | {_pct(sum(g.outcome == Outcome.CORRECT for g in gs), len(gs))} |")
    return [*lines, ""]


def build_report(stats: list[StepCountStats], tasks: list[TaskDefinition], grades: list[GradeResult],
                 calls: list[ModelCall]) -> str:
    by_task = {t.task_id: t for t in tasks}
    calls_by_task = {c.task_id: c for c in calls}
    grades_by_step: dict[int, list[GradeResult]] = defaultdict(list)
    for g in grades:
        grades_by_step[g.task_reasoning_step_count].append(g)
    out = ["# CadQuery-query scratch experiment: report", "",
           "## Funnel per task reasoning step count", "",
           "| Step count | Attempts | Constructed | Gold verified | Accepted | Evaluated | Tool call | Executed | "
           "Correct (95% CI) |", "|---|---|---|---|---|---|---|---|---|"]
    for s in sorted(stats, key=lambda s: s.step_count):
        gs = grades_by_step.get(s.step_count, [])
        tool = sum(g.outcome not in (Outcome.NO_TOOL_CALL, Outcome.API_ERROR) for g in gs)
        executed = sum(g.outcome in (Outcome.CORRECT, Outcome.WRONG, Outcome.LITERAL_ANSWER) for g in gs)
        correct = sum(g.outcome == Outcome.CORRECT for g in gs)
        out.append(f"| {s.step_count} | {s.attempts} | {s.constructed} | {s.gold_verified} | {s.accepted} | "
                   f"{len(gs)} | {tool} | {executed} | {_pct(correct, len(gs))} |")
    out += ["", "Construction failures and gold-query failures:", ""]
    for s in sorted(stats, key=lambda s: s.step_count):
        out.append(f"- step {s.step_count}: construction {s.construction_failures or '{}'}, duplicates "
                   f"{s.duplicates}, gold {s.gold_failures or '{}'}")
    out += ["", "## Outcomes per step count", "", "| Step count | " + " | ".join(o.value for o in Outcome) + " |",
            "|---|" + "---|" * len(Outcome)]
    for step in sorted(grades_by_step):
        c = Counter(g.outcome for g in grades_by_step[step])
        out.append(f"| {step} | " + " | ".join(str(c.get(o, 0)) for o in Outcome) + " |")
    out.append("")
    graded = [g for g in grades if g.task_id in by_task]
    by_clue: dict[str, list[GradeResult]] = defaultdict(list)
    by_meaning: dict[str, list[GradeResult]] = defaultdict(list)
    by_target: dict[str, list[GradeResult]] = defaultdict(list)
    for g in graded:
        t = by_task[g.task_id]
        for clue_type in sorted({c.clue_type.value for s in t.segments for c in s.clues}):
            by_clue[clue_type].append(g)
        by_meaning[t.answer_meaning.value].append(g)
        by_target[t.target_category.value].append(g)
    out += ["## Breakdowns (informative only; small n)", ""]
    out += _breakdown("Tasks containing a clue type", by_clue)
    out += _breakdown("Answer meaning", by_meaning)
    out += _breakdown("Task target category", by_target)
    errors = Counter(g.error_type or "unknown" for g in graded if g.outcome == Outcome.EXEC_ERROR)
    out += ["## Execution error types", "", *[f"- {k}: {v}" for k, v in errors.most_common()], ""]
    used = [calls_by_task[g.task_id] for g in graded if g.task_id in calls_by_task]
    cost = sum(c.cost_usd for c in used)
    comp = sorted(c.completion_tokens for c in used)
    out += ["## Cost and tokens", "",
            f"- calls: {len(used)}; total cost ${cost:.4f}",
            f"- completion tokens: median {comp[len(comp) // 2] if comp else 0}, max {comp[-1] if comp else 0}",
            ""]
    return "\n".join(out)
