"""Typed models for the step-9 no-kernel evaluation.

Task and fact models are reused from the CadQuery-query scratch. Only the
answer-submission and grading records are new.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from experiments.old.cq_query_scratch.models import ProgramFacts, TaskDefinition, TurnRecord

Point3 = tuple[float, float, float]


class Step9Outcome(StrEnum):
    CORRECT = "correct"
    WRONG = "wrong"
    PARSE_ERROR = "parse_error"
    NO_TOOL_CALL = "no_tool_call"
    API_ERROR = "api_error"


class AnswerCall(BaseModel):
    task_id: str = Field(min_length=10, max_length=40)
    model: str = Field(min_length=1, max_length=160)
    harness: str = Field(default="no_tools", max_length=16)
    run_code_calls: int = Field(default=0, ge=0)
    provider: str = Field(default="", max_length=200)
    provider_base: str = Field(default="", max_length=200)
    system_prompt_sha256: str = Field(min_length=64, max_length=64)
    user_prompt_sha256: str = Field(min_length=64, max_length=64)
    reasoning: str = ""
    content: str = ""
    tool_calls: list[dict] = Field(default_factory=list)
    turns: list[TurnRecord] = Field(default_factory=list)
    submitted_answer: str | None = None
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    finish_reason: str | None = Field(default=None, max_length=64)
    cost_usd: float = Field(default=0.0, ge=0.0)
    latency_s: float = Field(default=0.0, ge=0.0)
    vendor: str = Field(default="", max_length=64)
    error: str | None = None


class AnswerGrade(BaseModel):
    task_id: str = Field(min_length=10, max_length=40)
    task_reasoning_step_count: int = Field(ge=1)
    outcome: Step9Outcome
    model_answer: str | None = None
    parsed_answer: float | int | list[float] | None = None
    gold_answer: float | int | Point3
    error_type: str | None = Field(default=None, max_length=120)
    message: str | None = Field(default=None, max_length=4000)


__all__ = [
    "AnswerCall",
    "AnswerGrade",
    "Point3",
    "ProgramFacts",
    "Step9Outcome",
    "TaskDefinition",
    "TurnRecord",
]
