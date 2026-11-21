"""Render the no-kernel step-9 prompt from the existing cq-query task text."""

from __future__ import annotations

import hashlib
import re
import string
from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from experiments.old.cq_query_scratch.models import ProgramFacts, TaskDefinition
from experiments.old.cq_query_scratch.render import render_task_text

PROMPTS_PATH = Path(__file__).with_name("prompts.yaml")


class RenderedPrompt(BaseModel):
    system: str = Field(min_length=1)
    user: str = Field(min_length=1)


@cache
def prompts() -> dict:
    return yaml.safe_load(PROMPTS_PATH.read_text())


def prompts_sha256() -> str:
    return hashlib.sha256(PROMPTS_PATH.read_bytes()).hexdigest()


def fill(template: str, **values: object) -> str:
    fields = {f for _, f, _, _ in string.Formatter().parse(template) if f}
    if fields != set(values):
        raise ValueError(f"placeholder mismatch: template {sorted(fields)} vs values {sorted(values)}")
    return template.format(**values)


def sanitize_task_text(text: str) -> str:
    """Remove variable names from task clues; the program text keeps them."""
    text = re.sub(r"\s*\(assigned to `[^`]+`\)", "", text)
    text = re.sub(r"\s+assigned to `[^`]+`", "", text)
    text = text.replace("the single solid `result.val()`", "the single solid the program returns")
    text = text.replace("`result.val()`", "the program's final shape")
    return text


def render_prompt(task: TaskDefinition, facts: ProgramFacts, harness: str = "no_tools",
                  max_runs: int = 8) -> RenderedPrompt:
    e = prompts()["eval"]
    dataset = sanitize_task_text(render_task_text(task, facts)).rstrip("\n")
    answer_type = e["answer_types"][task.native_answer_format.value]
    if harness == "numpy":
        instruction = fill(e["instruction_run_code"], answer_type=answer_type, max_runs=max_runs).rstrip("\n")
    elif harness == "cadquery":
        instruction = fill(e["instruction_cadquery"], answer_type=answer_type, max_runs=max_runs).rstrip("\n")
    else:
        instruction = fill(e["instruction"], answer_type=answer_type).rstrip("\n")
    return RenderedPrompt(system=e["system"].rstrip("\n"), user=f"{dataset}\n\n{instruction}")
