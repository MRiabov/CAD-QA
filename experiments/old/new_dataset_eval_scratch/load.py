"""Load the step-9 tasks and facts produced by the CadQuery-query scratch."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from experiments.old.cq_query_scratch.models import ProgramFacts, TaskDefinition

log = logging.getLogger(__name__)


def main_checkout() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root.parent.parent if root.parent.name == ".worktrees" else root


MAIN_CHECKOUT = main_checkout()
RUN_DIR = MAIN_CHECKOUT / "runs" / "cq_query_scratch_20261022"
TASKS_PATH = RUN_DIR / "tasks.jsonl"
FACTS_PATH = RUN_DIR / "extraction" / "facts.jsonl"
STEP_COUNT = 9


def _read_jsonl(path: Path, model):
    if not path.exists():
        raise SystemExit(f"missing input: {path}")
    return [model.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]


def load_step9() -> tuple[list[TaskDefinition], dict[str, ProgramFacts]]:
    tasks = [t for t in _read_jsonl(TASKS_PATH, TaskDefinition)
             if t.task_reasoning_step_count == STEP_COUNT]
    facts = {f.program_id: f for f in _read_jsonl(FACTS_PATH, ProgramFacts)}
    missing = sorted({t.program_id for t in tasks if t.program_id not in facts})
    if missing:
        raise SystemExit(f"missing facts for {len(missing)} programs: {missing[:3]}")
    unverified = [t.task_id for t in tasks if not t.validity.gold_query_reproduces_answer]
    if unverified:
        log.warning("%d step-9 tasks lack a verified gold query; they are still used", len(unverified))
    log.info("loaded %d step-9 tasks from %d programs", len(tasks), len({t.program_id for t in tasks}))
    return tasks, facts


def write_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(r.model_dump_json() + "\n" for r in rows))


def read_jsonl(path: Path, model):
    return _read_jsonl(path, model)
