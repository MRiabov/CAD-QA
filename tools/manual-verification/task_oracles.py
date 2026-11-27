"""Load checked-in gold task oracles as dataset-browser rows.

A gold record has no rendered prompt and no split, so the row records its input
as ``gold``/``oracle`` and keeps the record itself for the detail panel. The
browser only reads records; the reviewer changes a record through the procedure
in the oracle README, not through the API.
"""

from __future__ import annotations

from pathlib import Path

from task_oracle_runner import load_oracles
from task_oracle_schema import (
    Answer,
    BoundingBox,
    Point3D,
    TaskOracle,
    ValueKind,
    render_answer_value,
)
from task_release import DiagnosticEntry, TaskRow

GOLD_SPLIT = "gold"
GOLD_SUBSET = "oracle"


def _display_value(answer: Answer) -> str:
    """Render a point or box as coordinates; otherwise use the canonical text."""

    match answer.value_kind:
        case ValueKind.POINT:
            point = Point3D.model_validate(answer.value)
            return f"({point.x}, {point.y}, {point.z})"
        case ValueKind.BOUNDING_BOX:
            box = BoundingBox.model_validate(answer.value)
            return (
                f"({box.min.x}, {box.min.y}, {box.min.z})–"
                f"({box.max.x}, {box.max.y}, {box.max.z})"
            )
        case _:
            return render_answer_value(answer.value_kind, answer.value)


def _answer_text(oracle: TaskOracle) -> str:
    value = _display_value(oracle.answer)
    unit_name = oracle.answer.unit.value
    unit = "" if unit_name == "unitless" else unit_name.replace("_", " ")
    return f"{value} {unit}".strip()


def _preview(oracle: TaskOracle) -> str:
    return oracle.task.question


def _gold_query_line(oracle: TaskOracle) -> str:
    check = oracle.verification.gold_query
    parts = [check.status.value]
    if check.stdout is not None:
        parts.append(check.stdout)
    if check.checked_at is not None:
        parts.append(f"({check.checked_at})")
    return " ".join(parts)


def _diagnostics(oracle: TaskOracle) -> tuple[DiagnosticEntry, ...]:
    return (
        DiagnosticEntry(label="record", value=oracle.slug),
        DiagnosticEntry(label="verification", value=oracle.verification.status.value),
        DiagnosticEntry(label="gold query", value=_gold_query_line(oracle)),
        DiagnosticEntry(
            label="target category", value=oracle.task.target_category.value
        ),
        DiagnosticEntry(
            label="possible answers", value=str(oracle.task.possible_answer_count)
        ),
        DiagnosticEntry(
            label="task reasoning steps",
            value=str(oracle.task.task_reasoning_step_count),
        ),
        DiagnosticEntry(
            label="answer format",
            value=f"{oracle.task.answer_format.value} ({oracle.task.answer_meaning.value})",
        ),
        DiagnosticEntry(label="scoring rule", value=oracle.answer.scoring_rule.value),
        DiagnosticEntry(
            label="clue types",
            value=", ".join(clue.value for clue in oracle.covers.clue_types) or "none",
        ),
    )


def oracle_row(oracle: TaskOracle) -> TaskRow:
    """One browser row from one gold record."""

    return TaskRow(
        task_id=oracle.slug,
        split=GOLD_SPLIT,
        subset=GOLD_SUBSET,
        target_category=oracle.task.target_category.value,
        answer_format=oracle.task.answer_format.value,
        answer_meaning=oracle.task.answer_meaning.value,
        answer=_answer_text(oracle),
        preview=_preview(oracle),
        task_reasoning_step_count=oracle.task.task_reasoning_step_count,
        program_id=oracle.program.program_id,
        program_sha256=oracle.program.program_sha256,
        program=oracle.program.text,
        prompt=None,
        choices=[],
        diagnostics=list(_diagnostics(oracle)),
        oracle=oracle,
    )


def load_oracle_rows(directory: Path) -> list[TaskRow]:
    """Read every ``*.json`` record in the gold-oracle directory."""

    if not directory.is_dir():
        raise SystemExit(f"oracle directory does not exist: {directory}")
    rows = [oracle_row(oracle) for _, oracle in load_oracles(directory)]
    if not rows:
        raise SystemExit(f"{directory} has no oracle records")
    return rows
