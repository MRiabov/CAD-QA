"""CLI: pool -> generate -> eval (staged) -> report.

    python -m experiments.old.cq_query_scratch.cli pool --target 80
    python -m experiments.old.cq_query_scratch.cli generate --step-counts 1 3 5 7 9 --quota 60
    python -m experiments.old.cq_query_scratch.cli eval --step-counts 3 [--limit 5]
    python -m experiments.old.cq_query_scratch.cli report
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from experiments.old.cq_query_scratch import generate, pool, report, run_eval
from experiments.old.cq_query_scratch.generate import StepCountStats
from experiments.old.cq_query_scratch.models import (
    EXPERIMENT_VERSION,
    SEED,
    GradeResult,
    Harness,
    ModelCall,
    ProgramFacts,
    Rejection,
    TaskDefinition,
)
from experiments.old.cq_query_scratch.render import prompts_sha256, render_task_text


def _main_checkout() -> Path:
    """Repo root, or the primary checkout when running from .worktrees/<name> (runs/ and .env live there)."""
    root = Path(__file__).resolve().parents[3]
    return root.parent.parent if root.parent.name == ".worktrees" else root


MAIN_CHECKOUT = _main_checkout()
MAIN_RUNS = MAIN_CHECKOUT / "runs"
log = logging.getLogger("cq_query_scratch")


def _write_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(r.model_dump_json() + "\n" for r in rows))


def _read_jsonl(path: Path, model):
    if not path.exists():
        return []
    return [model.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]


def _api_key(repo_root: Path) -> str:
    key = os.environ.get(run_eval.API_KEY_ENV)
    if key:
        return key
    for line in (repo_root / ".env").read_text().splitlines():
        if line.startswith(f"{run_eval.API_KEY_ENV}="):
            return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit(f"{run_eval.API_KEY_ENV} not found")


def cmd_pool(args) -> None:
    entries, facts, rejections = pool.build_pool(args.regen_dir, args.out, args.target)
    args.out.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist([e.model_dump() for e in entries]), args.out / "pool.parquet")
    _write_jsonl(args.out / "extraction" / "facts.jsonl", facts)
    _write_jsonl(args.out / "pool_rejections.jsonl", rejections)
    import cadquery
    import OCP

    manifest = {"experiment_version": EXPERIMENT_VERSION, "seed": SEED, "python": platform.python_version(),
                "cadquery": cadquery.__version__, "ocp": getattr(OCP, "__version__", "unknown"),
                "ruff": pool.ruff_version(), "pool_size": len(entries), "regen_dir": str(args.regen_dir)}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    log.info("pool: %d programs, %d rejections", len(entries), len(rejections))


def cmd_generate(args) -> None:
    facts = _read_jsonl(args.out / "extraction" / "facts.jsonl", ProgramFacts)
    facts_by_id = {f.program_id: f for f in facts}
    all_tasks: list[TaskDefinition] = []
    all_stats: list[StepCountStats] = []
    rejections: list[Rejection] = []
    for step in args.step_counts:
        stats = StepCountStats(step_count=step)
        built = generate.construct(facts, step, stats)
        accepted = generate.select_and_verify(built, facts_by_id, args.quota, stats, rejections)
        for t in accepted:
            t.prompt = render_task_text(t, facts_by_id[t.program_id])
        all_tasks += accepted
        all_stats.append(stats)
        log.info("step %d: %s", step, stats.model_dump_json())
    _write_jsonl(args.out / "tasks.jsonl", all_tasks)
    _write_jsonl(args.out / "failures.jsonl", rejections)
    (args.out / "generation_stats.json").write_text(
        json.dumps([s.model_dump() for s in all_stats], indent=2, sort_keys=True) + "\n")
    manifest_path = args.out / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["prompts_yaml_sha256"] = prompts_sha256()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def cmd_eval(args) -> None:
    facts = {f.program_id: f for f in _read_jsonl(args.out / "extraction" / "facts.jsonl", ProgramFacts)}
    tasks = [t for t in _read_jsonl(args.out / "tasks.jsonl", TaskDefinition)
             if t.task_reasoning_step_count in args.step_counts]
    if args.limit:
        tasks = tasks[: args.limit]
    harness = Harness(args.harness)
    out = args.out if harness == Harness.SINGLE_SHOT else args.out / f"{harness.value}_{run_eval.REASONING_EFFORT}"
    run_eval.run(tasks, facts, out, _api_key(MAIN_CHECKOUT), args.max_cost, harness)


def cmd_regrade_literal(args) -> None:
    tasks = {t.task_id: t for t in _read_jsonl(args.out / "tasks.jsonl", TaskDefinition)}
    calls = {c.task_id: c for c in _read_jsonl(args.out / "calls.jsonl", ModelCall) if c.submitted_code}
    grades = run_eval.regrade_literal(tasks, calls, _read_jsonl(args.out / "grades.jsonl", GradeResult))
    _write_jsonl(args.out / "grades.jsonl", grades)


def cmd_review(args) -> None:
    from experiments.old.cq_query_scratch.review import build_review

    facts = {f.program_id: f for f in _read_jsonl(args.out / "extraction" / "facts.jsonl", ProgramFacts)}
    page = build_review(_read_jsonl(args.out / "tasks.jsonl", TaskDefinition), facts,
                        _read_jsonl(args.out / "calls.jsonl", ModelCall),
                        _read_jsonl(args.out / "grades.jsonl", GradeResult))
    path = args.out / "review.html"
    path.write_text(page)
    print(f"file://{path.resolve()}")


def cmd_report(args) -> None:
    stats = [StepCountStats(**s) for s in json.loads((args.out / "generation_stats.json").read_text())]
    text = report.build_report(stats, _read_jsonl(args.out / "tasks.jsonl", TaskDefinition),
                               _read_jsonl(args.out / "grades.jsonl", GradeResult),
                               _read_jsonl(args.out / "calls.jsonl", ModelCall))
    (args.out / "report.md").write_text(text)
    print(text)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=MAIN_RUNS / "cq_query_scratch_20261022")
    p.add_argument("--regen-dir", type=Path, default=MAIN_RUNS / "regen_1300_traced_20261019")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("pool")
    sp.add_argument("--target", type=int, default=80)
    sg = sub.add_parser("generate")
    sg.add_argument("--step-counts", type=int, nargs="+", default=[1, 3, 5, 7, 9])
    sg.add_argument("--quota", type=int, default=60)
    se = sub.add_parser("eval")
    se.add_argument("--step-counts", type=int, nargs="+", required=True)
    se.add_argument("--limit", type=int, default=0)
    se.add_argument("--max-cost", type=float, default=5.0)
    se.add_argument("--harness", choices=[h.value for h in Harness], default=Harness.SINGLE_SHOT.value)
    sub.add_parser("report")
    sub.add_parser("regrade-literal")
    sub.add_parser("review")
    args = p.parse_args()
    match args.cmd:
        case "pool":
            cmd_pool(args)
        case "generate":
            cmd_generate(args)
        case "eval":
            cmd_eval(args)
        case "report":
            cmd_report(args)
        case "regrade-literal":
            cmd_regrade_literal(args)
        case "review":
            cmd_review(args)


if __name__ == "__main__":
    main()
