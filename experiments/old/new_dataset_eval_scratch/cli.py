"""CLI for the step-9 no-kernel evaluation.

    python -m experiments.old.new_dataset_eval_scratch.cli prepare
    python -m experiments.old.new_dataset_eval_scratch.cli eval --model deepseek/deepseek-v4.1-flash-1017
    python -m experiments.old.new_dataset_eval_scratch.cli eval --model xiaomi/mimo-v2.5-pro --provider openrouter
    python -m experiments.old.new_dataset_eval_scratch.cli report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from experiments.old.new_dataset_eval_scratch import run_eval
from experiments.old.new_dataset_eval_scratch.leak import audit_prompt
from experiments.old.new_dataset_eval_scratch.load import MAIN_CHECKOUT, STEP_COUNT, load_step9
from experiments.old.new_dataset_eval_scratch.models import AnswerCall, AnswerGrade, TaskDefinition
from experiments.old.new_dataset_eval_scratch.render import prompts_sha256, render_prompt
from experiments.old.new_dataset_eval_scratch.report import build_report, read_report_inputs
from experiments.old.new_dataset_eval_scratch.review import build_review

log = logging.getLogger("new_dataset_step9_eval")
DEFAULT_OUT = MAIN_CHECKOUT / "runs" / "new_dataset_step9_eval_20261022"
SEED = "cadqa-new-dataset-step9-20261022"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def _read_jsonl(path: Path, model):
    return [model.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]


def cmd_prepare(args) -> None:
    tasks, facts = load_step9()
    prompt_rows = []
    leaks: dict[str, str] = {}
    for task in tasks:
        base = render_prompt(task, facts[task.program_id], "no_tools")
        numpy = render_prompt(task, facts[task.program_id], "numpy")
        cadquery = render_prompt(task, facts[task.program_id], "cadquery")
        task.prompt = base.user
        prompt_rows.append({
            "task_id": task.task_id,
            "system": base.system,
            "user_no_tools": base.user,
            "user_numpy": numpy.user,
            "user_cadquery": cadquery.user,
            "system_sha256": _sha(base.system),
            "user_no_tools_sha256": _sha(base.user),
            "user_numpy_sha256": _sha(numpy.user),
            "user_cadquery_sha256": _sha(cadquery.user),
        })
        if (reason := audit_prompt(task, base.user)) is not None:
            leaks[task.task_id] = reason
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "tasks.jsonl").write_text("".join(t.model_dump_json() + "\n" for t in tasks))
    _write_jsonl(out / "prompts.jsonl", prompt_rows)
    (out / "leak_audit.json").write_text(json.dumps(leaks, indent=2, sort_keys=True) + "\n")
    manifest = {
        "seed": SEED,
        "step_count": STEP_COUNT,
        "task_count": len(tasks),
        "program_count": len({t.program_id for t in tasks}),
        "prompts_yaml_sha256": prompts_sha256(),
        "source_tasks": str(MAIN_CHECKOUT / "runs" / "cq_query_scratch_20261022" / "tasks.jsonl"),
        "source_facts": str(MAIN_CHECKOUT / "runs" / "cq_query_scratch_20261022" / "extraction" / "facts.jsonl"),
        "target_categories": sorted({t.target_category.value for t in tasks}),
        "answer_meanings": sorted({t.answer_meaning.value for t in tasks}),
        "answer_formats": sorted({t.native_answer_format.value for t in tasks}),
        "literal_leak_count": len(leaks),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    log.info("prepared %d step-9 prompts in %s", len(tasks), out)


def cmd_eval(args) -> None:
    tasks_path = args.out / "tasks.jsonl"
    prompts_path = args.out / "prompts.jsonl"
    tasks = _read_jsonl(tasks_path, TaskDefinition)
    prompts = {row["task_id"]: row for row in
               (json.loads(line) for line in prompts_path.read_text().splitlines() if line.strip())}
    facts = load_step9()[1] if args.harness == "cadquery" else None
    slug = args.model.replace("/", "__").removeprefix("openrouter__") + f"__{args.harness}"
    run_dir = args.out / slug
    api_key = run_eval.api_key_for(args.provider, MAIN_CHECKOUT)
    run_eval.run(tasks, prompts, facts, run_dir, api_key, args.model, args.provider, args.harness,
                 args.max_cost, args.limit)
    metadata = {
        "model": args.model,
        "provider": args.provider,
        "harness": args.harness,
        "temperature": run_eval.TEMPERATURE,
        "top_p": run_eval.TOP_P,
        "max_tokens": run_eval.MAX_TOKENS,
        "reasoning_effort": run_eval.REASONING_EFFORT,
        "workers": run_eval.API_WORKERS,
        "limit": args.limit,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompts_yaml_sha256": prompts_sha256(),
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    _write_report(args.out, run_dir)
    log.info("evaluated %s in %s", args.model, run_dir)


def _write_report(tasks_root: Path, run_dir: Path) -> None:
    tasks, grades, calls = read_report_inputs(tasks_root / "tasks.jsonl", run_dir)
    leak_path = tasks_root / "leak_audit.json"
    leaks = json.loads(leak_path.read_text()) if leak_path.exists() else {}
    report = build_report(tasks, grades, calls, leaks)
    (run_dir / "report.md").write_text(report)
    print(report)


def cmd_report(args) -> None:
    runs = [args.run] if args.run else sorted(p for p in args.out.iterdir() if (p / "grades.jsonl").exists())
    for run_dir in runs:
        _write_report(args.out, run_dir)


def cmd_review(args) -> None:
    if args.run:
        runs = args.run
    else:
        runs = sorted(p for p in args.out.iterdir()
                      if (p / "grades.jsonl").exists() and "deepseek-v4.1-flash-1017" in p.name)
    page = build_review(args.out, runs)
    path = args.out / "review.html"
    path.write_text(page)
    print(f"file://{path.resolve()}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    se = sub.add_parser("eval")
    se.add_argument("--model", default=run_eval.DEFAULT_MODEL)
    se.add_argument("--provider", choices=["merge", "openrouter"], default=run_eval.DEFAULT_PROVIDER)
    se.add_argument("--harness", choices=["no_tools", "numpy", "cadquery"], default=run_eval.DEFAULT_HARNESS)
    se.add_argument("--limit", type=int, default=0)
    se.add_argument("--max-cost", type=float, default=5.0)
    sr = sub.add_parser("report")
    sr.add_argument("--run", type=Path, default=None)
    sv = sub.add_parser("review")
    sv.add_argument("--run", type=Path, nargs="*", default=None)
    args = p.parse_args()
    match args.cmd:
        case "prepare":
            cmd_prepare(args)
        case "eval":
            cmd_eval(args)
        case "report":
            cmd_report(args)
        case "review":
            cmd_review(args)


if __name__ == "__main__":
    main()
