"""Release-table types and CadQuery execution for the task browser.

The browser reads the documented release columns, extracts the program from the
prompt's Python fence, and executes it to tessellate the final solid state. The
row type the browser indexes is shared with the gold-oracle input in
``task_oracles.py``; a gold record has no prompt, so its ``prompt`` is null and
its ``oracle`` is the record. This module imports CadQuery lazily, so the typed
models and the HTTP API load without the CAD kernel.

This is a manual-verification devtool. The generator never imports it.
"""

from __future__ import annotations

import re
import traceback
from enum import StrEnum
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field
from task_oracle_schema import TaskOracle

PYTHON_FENCE = re.compile(r"```python\n(?P<code>.*?)\n```", re.DOTALL)
FENCE = re.compile(r"```python\n.*?\n```", re.DOTALL)


class Split(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class Subset(StrEnum):
    WARMUP = "warmup"
    MAIN = "main"


class AnswerValueKind(StrEnum):
    LABEL = "label"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    POINT = "point"
    BOUNDING_BOX = "bounding_box"
    STRUCTURED = "structured"


class Point3D(BaseModel):
    """A point in the program frame, as canonical decimal text."""

    model_config = ConfigDict(extra="ignore")

    x: str
    y: str
    z: str


class BoundingBox(BaseModel):
    """An axis-aligned box in the program frame."""

    model_config = ConfigDict(extra="ignore")

    min: Point3D
    max: Point3D


class AnswerValue(BaseModel):
    """The release answer, a tagged union; exactly one value is set."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    answer_kind: AnswerValueKind = Field(alias="kind")
    label: str | None = None
    number_text: str | None = None
    integer: int | None = None
    boolean: bool | None = None
    point: Point3D | None = None
    bounding_box: BoundingBox | None = None
    structured: str | None = None


class Tolerance(BaseModel):
    """How close an answer must be to the gold answer."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    tolerance_kind: str = Field(alias="kind")
    value_text: str | None = None
    unit: str | None = None


class Choice(BaseModel):
    """One multiple-choice option."""

    model_config = ConfigDict(extra="ignore")

    label: str
    candidate: str


class ClueOperandForm(BaseModel):
    """One clue's clue type and clue operand form."""

    model_config = ConfigDict(extra="ignore")

    clue_type: str
    clue_operand_form: str | None = None


class ReleaseRow(BaseModel):
    """The release columns this tool reads."""

    model_config = ConfigDict(extra="ignore")

    task_id: str = Field(min_length=1)
    split: Split
    subset: Subset
    prompt: str = Field(min_length=1)
    prompt_sha256: str = Field(min_length=64, max_length=64)
    program_id: str = Field(min_length=1)
    program_sha256: str = Field(min_length=64, max_length=64)
    cadevolve_program_family_id: str = Field(min_length=1)
    task_reasoning_step_count: int = Field(ge=0)
    target_category: str = Field(min_length=1)
    clue_types: list[str] = Field(default_factory=list)
    clue_operand_form_profile: list[ClueOperandForm] = Field(default_factory=list)
    answer_format: str = Field(min_length=1)
    answer_meaning: str = Field(min_length=1)
    geometry_required: bool
    gold_answer: AnswerValue
    answer_unit: str | None = None
    tolerance: Tolerance | None = None
    scoring_rule: str = Field(min_length=1)
    answer_sha256: str = Field(min_length=64, max_length=64)
    choices: list[Choice] = Field(default_factory=list)


class DiagnosticEntry(BaseModel):
    """One label and value row of the task detail panel."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=500)


class TaskRow(BaseModel):
    """One task the browser shows, from a release table or a gold record.

    The program is already extracted, so the index does not care which input a
    row came from. A release row carries the prompt; a gold row carries the
    record and has no prompt.
    """

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    split: str = Field(min_length=1)
    subset: str = Field(min_length=1)
    target_category: str = Field(min_length=1)
    answer_format: str = Field(min_length=1)
    answer_meaning: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    preview: str = Field(min_length=1)
    task_reasoning_step_count: int = Field(ge=0)
    program_id: str = Field(min_length=1)
    program_sha256: str = Field(min_length=64, max_length=64)
    program: str = Field(min_length=1)
    prompt: str | None = Field(default=None)
    choices: list[Choice] = Field(default_factory=list)
    diagnostics: list[DiagnosticEntry] = Field(default_factory=list)
    oracle: TaskOracle | None = Field(default=None)


class TaskSummary(BaseModel):
    """One row of the task list."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    split: str = Field(min_length=1)
    subset: str = Field(min_length=1)
    target_category: str = Field(min_length=1)
    answer_meaning: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    task_reasoning_step_count: int = Field(ge=0)
    program_id: str = Field(min_length=1)
    preview: str = Field(min_length=1, max_length=240)


class TaskDetail(BaseModel):
    """Everything the detail panel shows for one task."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    split: str = Field(min_length=1)
    subset: str = Field(min_length=1)
    target_category: str = Field(min_length=1)
    answer_format: str = Field(min_length=1)
    answer_meaning: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    prompt: str | None = Field(default=None)
    program: str = Field(min_length=1)
    choices: list[Choice] = Field(default_factory=list)
    diagnostics: list[DiagnosticEntry] = Field(default_factory=list)
    oracle: TaskOracle | None = Field(default=None)


class Facets(BaseModel):
    """The filter values the browser offers."""

    model_config = ConfigDict(extra="forbid")

    task_count: int = Field(ge=0)
    input_kind: str = Field(default="release", min_length=1)
    splits: list[str] = Field(default_factory=list)
    subsets: list[str] = Field(default_factory=list)
    target_categories: list[str] = Field(default_factory=list)
    answer_meanings: list[str] = Field(default_factory=list)


class TaskPage(BaseModel):
    """One page of the task list."""

    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    tasks: list[TaskSummary] = Field(default_factory=list)


def release_table_path(release: Path) -> Path:
    """Resolve a release directory, ``current`` symlink, or parquet file."""

    if release.is_dir():
        candidate = release / "release.parquet"
        if not candidate.exists():
            raise SystemExit(f"{release} has no release.parquet")
        return candidate
    if release.name == "current":
        return release_table_path(release.resolve())
    if release.exists():
        return release
    raise SystemExit(f"release path does not exist: {release}")


def load_rows(table_path: Path) -> list[ReleaseRow]:
    """Read release rows and validate the columns this tool reads."""

    table = pq.read_table(table_path)
    rows = [ReleaseRow.model_validate(record) for record in table.to_pylist()]
    if not rows:
        raise SystemExit(f"{table_path} has no release rows")
    return rows


def program_text(prompt: str) -> str:
    """Extract the Python fence from the rendered prompt."""

    match = PYTHON_FENCE.search(prompt)
    if match is None:
        raise ValueError("the prompt has no ```python fence to execute")
    return match.group("code").rstrip() + "\n"


def execute_program(text: str) -> Any:
    """Execute a CadQuery program and return its final Workplane or Shape."""

    import cadquery as cq

    namespace: dict[str, Any] = {"__name__": "__task_browser__"}
    try:
        exec(compile(text, "<release-program>", "exec"), namespace)  # noqa: S102 - reviewed input
    except Exception as error:
        traceback.print_exc()
        raise RuntimeError(f"program execution failed: {error}") from error

    def first_shape(candidate: Any) -> Any | None:
        if isinstance(candidate, cq.Workplane):
            return candidate.val()
        if isinstance(candidate, cq.Shape):
            return candidate
        return None

    result = first_shape(namespace.get("result"))
    if result is not None:
        return result
    if isinstance(namespace.get("result"), (list, tuple)):
        for item in namespace["result"]:
            shape = first_shape(item)
            if shape is not None:
                return shape
    for value in reversed(list(namespace.values())):
        shape = first_shape(value)
        if shape is not None:
            return shape
    raise RuntimeError("program defined no Workplane or Shape to render")


def answer_display(row: ReleaseRow) -> str:
    """Render the gold answer as the reviewer should read it."""

    answer = row.gold_answer
    match answer.answer_kind:
        case AnswerValueKind.NUMBER:
            return str(answer.number_text)
        case AnswerValueKind.LABEL:
            return str(answer.label)
        case AnswerValueKind.INTEGER:
            return str(answer.integer)
        case AnswerValueKind.BOOLEAN:
            return str(answer.boolean)
        case AnswerValueKind.POINT:
            return str(answer.point)
        case AnswerValueKind.BOUNDING_BOX:
            return str(answer.bounding_box)
        case AnswerValueKind.STRUCTURED:
            return str(answer.structured)
    raise ValueError(f"unsupported answer kind: {answer.answer_kind}")


def tolerance_display(row: ReleaseRow) -> str:
    """Render the answer tolerance in one line."""

    tolerance = row.tolerance
    if tolerance is None:
        return "exact"
    unit = tolerance.unit or row.answer_unit or ""
    return f"{tolerance.tolerance_kind} {tolerance.value_text or ''} {unit}".strip()


def answer_text(row: ReleaseRow) -> str:
    """The gold answer as one line, with its unit."""

    return f"{answer_display(row)} {row.answer_unit or ''}".strip()


def prompt_preview(prompt: str, limit: int = 180) -> str:
    """The question after the program fence, collapsed to one line."""

    match = FENCE.search(prompt)
    body = prompt[match.end() :] if match is not None else prompt
    paragraphs = [part.strip() for part in body.split("\n\n") if part.strip()]
    text = " ".join(paragraphs[0].split()) if paragraphs else " ".join(prompt.split())
    if not text:
        text = " ".join(prompt.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def diagnostics(row: ReleaseRow) -> tuple[DiagnosticEntry, ...]:
    """The label and value rows the detail panel hides under Diagnostics."""

    slug = row.task_id.removeprefix("cadqatask:")
    short_slug = slug if len(slug) <= 12 else f"{slug[:12]}…"
    return (
        DiagnosticEntry(label="task", value=f"Task {short_slug}"),
        DiagnosticEntry(label="task_id", value=row.task_id),
        DiagnosticEntry(label="target category", value=row.target_category),
        DiagnosticEntry(
            label="task reasoning steps", value=str(row.task_reasoning_step_count)
        ),
        DiagnosticEntry(
            label="answer format", value=f"{row.answer_format} ({row.answer_meaning})"
        ),
        DiagnosticEntry(label="tolerance", value=tolerance_display(row)),
        DiagnosticEntry(label="scoring rule", value=row.scoring_rule),
        DiagnosticEntry(label="clue types", value=", ".join(row.clue_types) or "none"),
    )


def load_release_rows(table_path: Path) -> list[TaskRow]:
    """Read a release table as browser rows."""

    return [to_task_row(row) for row in load_rows(table_path)]


def to_task_row(row: ReleaseRow) -> TaskRow:
    """Extract the program and the detail payload from a release row."""

    return TaskRow(
        task_id=row.task_id,
        split=row.split.value,
        subset=row.subset.value,
        target_category=row.target_category,
        answer_format=row.answer_format,
        answer_meaning=row.answer_meaning,
        answer=answer_text(row),
        preview=prompt_preview(row.prompt),
        task_reasoning_step_count=row.task_reasoning_step_count,
        program_id=row.program_id,
        program_sha256=row.program_sha256,
        program=program_text(row.prompt),
        prompt=row.prompt,
        choices=row.choices,
        diagnostics=list(diagnostics(row)),
    )


def summary(row: TaskRow) -> TaskSummary:
    """One list row for the browser."""

    return TaskSummary(
        task_id=row.task_id,
        split=row.split,
        subset=row.subset,
        target_category=row.target_category,
        answer_meaning=row.answer_meaning,
        answer=row.answer,
        task_reasoning_step_count=row.task_reasoning_step_count,
        program_id=row.program_id,
        preview=row.preview,
    )


def detail(row: TaskRow) -> TaskDetail:
    """The detail payload for one task."""

    return TaskDetail(
        task_id=row.task_id,
        split=row.split,
        subset=row.subset,
        target_category=row.target_category,
        answer_format=row.answer_format,
        answer_meaning=row.answer_meaning,
        answer=row.answer,
        prompt=row.prompt,
        program=row.program,
        choices=row.choices,
        diagnostics=row.diagnostics,
        oracle=row.oracle,
    )
