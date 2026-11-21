"""Call the model in parallel, execute submitted queries (throttled), grade, and log JSONL.

Every call is recorded with reasoning, visible content, and raw tool calls (calls.jsonl).
Runs resume by task_id: tasks already present in grades.jsonl are skipped.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from pydantic import BaseModel, Field

from experiments.old.cq_query_scratch.grading import answers_match, assigns_literal_answer, escape_attempt
from experiments.old.cq_query_scratch.kernel import run_queries
from experiments.old.cq_query_scratch.models import (
    GradeResult,
    Harness,
    ModelCall,
    Outcome,
    ProgramFacts,
    TaskDefinition,
    TurnRecord,
)
from experiments.old.cq_query_scratch.render import render_prompt

log = logging.getLogger(__name__)

API_BASE = "https://api-gateway.merge.dev/v1/openai"  # Merge Gateway, OpenAI-compatible chat completions
API_KEY_ENV = "MERGE_GATEWAY_API_KEY"
MODEL = "deepseek/deepseek-v4.1-flash-1017"
TEMPERATURE = 1.0  # model card recommendation
TOP_P = 0.95
VENDOR = "deepseek"  # Merge routes unpinned calls to any vendor (DeepInfra seen); "vendor" is enforced
REASONING_EFFORT = "high"  # Merge returns no reasoning unless an effort is set
MAX_TOKENS = 32000  # 3/27 OpenRouter step-3 calls hit 16k while still reasoning
API_WORKERS = int(os.environ.get("CQ_SCRATCH_API_WORKERS", "60"))
API_RETRIES = 3
REQUEST_TIMEOUT_S = 600
SUBMIT_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_query",
        "description": "Submit CadQuery Python code that assigns the answer to `answer`.",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python code run after the program."}},
            "required": ["code"],
        },
    },
}

RUN_TOOL = {
    "type": "function",
    "function": {
        "name": "run_query",
        "description": "Execute Python code after the program and return the value of `answer` or the error.",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python code run after the program."}},
            "required": ["code"],
        },
    },
}
AGENTIC_MAX_RUNS = 8
AGENTIC_MAX_TURNS = 12

_local = threading.local()
_write_lock = threading.Lock()


class ApiError(RuntimeError):
    pass


class ChatResponse(BaseModel):
    content: str = ""
    reasoning: str = ""
    tool_calls: list[dict] = Field(default_factory=list)
    finish_reason: str | None = None
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    vendor: str = Field(default="", max_length=64)


def _session(api_key: str) -> requests.Session:
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
        _local.session.headers.update({"Authorization": f"Bearer {api_key}"})
    return _local.session


def chat(api_key: str, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
    payload = {"model": MODEL, "messages": messages, "tools": tools or [SUBMIT_TOOL], "temperature": TEMPERATURE,
               "top_p": TOP_P, "max_tokens": MAX_TOKENS, "reasoning_effort": REASONING_EFFORT, "vendor": VENDOR}
    r = _session(api_key).post(f"{API_BASE}/chat/completions", json=payload, timeout=REQUEST_TIMEOUT_S)
    if r.status_code >= 400:
        raise ApiError(f"HTTP {r.status_code}: {r.text[:500]}")
    data = r.json()
    choice = data["choices"][0]
    msg = choice["message"]
    usage = data.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return ChatResponse(
        content=msg.get("content") or "",
        reasoning=msg.get("thinking") or msg.get("reasoning_content") or msg.get("reasoning") or "",
        tool_calls=msg.get("tool_calls") or [], finish_reason=choice.get("finish_reason"),
        prompt_tokens=usage.get("prompt_tokens") or 0, completion_tokens=usage.get("completion_tokens") or 0,
        reasoning_tokens=details.get("reasoning_tokens") or 0, cost_usd=usage.get("cost") or 0.0,
        vendor=r.headers.get("x-merge-vendor", ""))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _submitted_code(tool_calls: list[dict]) -> str | None:
    for tc in tool_calls:
        fn = tc.get("function", {})
        if fn.get("name") != "submit_query":
            continue
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            return None
        code = args.get("code")
        return code if isinstance(code, str) and code.strip() else None
    return None


def call_model(task: TaskDefinition, api_key: str) -> ModelCall:
    prompt = render_prompt(task)
    messages = [{"role": "system", "content": prompt.system}, {"role": "user", "content": prompt.user}]
    base = ModelCall(task_id=task.task_id, model=MODEL, provider=API_BASE, reasoning_effort=REASONING_EFFORT,
                     system_prompt_sha256=_sha(prompt.system), user_prompt_sha256=_sha(prompt.user))
    for attempt in range(API_RETRIES):
        t0 = time.monotonic()
        try:
            r = chat(api_key, messages)
        except (ApiError, requests.RequestException, KeyError, ValueError) as exc:
            base.error = f"{type(exc).__name__}: {exc}"[:2000]
            log.warning("api error on %s (attempt %d): %s", task.task_id, attempt + 1, base.error[:200])
            time.sleep(5 * (attempt + 1))
            continue
        return ModelCall(
            task_id=task.task_id, model=MODEL, provider=API_BASE, reasoning_effort=REASONING_EFFORT,
            system_prompt_sha256=base.system_prompt_sha256, user_prompt_sha256=base.user_prompt_sha256,
            reasoning=r.reasoning, content=r.content, tool_calls=r.tool_calls,
            submitted_code=_submitted_code(r.tool_calls), finish_reason=r.finish_reason,
            prompt_tokens=r.prompt_tokens, completion_tokens=r.completion_tokens,
            reasoning_tokens=r.reasoning_tokens, cost_usd=r.cost_usd, latency_s=round(time.monotonic() - t0, 3),
            vendor=r.vendor)
    return base


def _chat_with_retries(api_key: str, messages: list[dict], tools: list[dict], task_id: str) -> ChatResponse | str:
    """ChatResponse, or the last error string after API_RETRIES failures."""
    error = ""
    for attempt in range(API_RETRIES):
        try:
            return chat(api_key, messages, tools)
        except (ApiError, requests.RequestException, KeyError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"[:2000]
            log.warning("api error on %s (attempt %d): %s", task_id, attempt + 1, error[:200])
            time.sleep(5 * (attempt + 1))
    return error


def _tool_code(tc: dict) -> str | None:
    try:
        code = json.loads(tc.get("function", {}).get("arguments") or "{}").get("code")
    except json.JSONDecodeError:
        return None
    return code if isinstance(code, str) and code.strip() else None


def _run_tool_result(pf: ProgramFacts, code: str | None) -> tuple[str, bool]:
    """(text returned to the model, blocked by the escape guard)."""
    if code is None:
        return "error: missing or invalid `code` argument", False
    if (why := escape_attempt(code)) is not None:
        return f"refused: code may not access the environment ({why}); compute with CadQuery only", True
    r = run_queries(pf.program_text, [code], explore=True)[0]
    printed = f"\nstdout:\n{r.stdout}" if r.stdout else ""
    if r.timed_out:
        return "error: timed out", False
    if not r.ok:
        return f"error: {r.error_type}: {(r.message or '')[-1500:]}{printed}", False
    return f"answer = {r.repr_text}{printed}", False


def call_model_agentic(task: TaskDefinition, api_key: str, pf: ProgramFacts) -> ModelCall:
    """Multi-turn: run_query (executed, result returned) up to AGENTIC_MAX_RUNS times, then submit_query."""
    prompt = render_prompt(task, max_runs=AGENTIC_MAX_RUNS)
    messages = [{"role": "system", "content": prompt.system}, {"role": "user", "content": prompt.user}]
    call = ModelCall(task_id=task.task_id, model=MODEL, provider=API_BASE, harness=Harness.AGENTIC,
                     reasoning_effort=REASONING_EFFORT, system_prompt_sha256=_sha(prompt.system),
                     user_prompt_sha256=_sha(prompt.user))
    t0 = time.monotonic()
    for _ in range(AGENTIC_MAX_TURNS):
        r = _chat_with_retries(api_key, messages, [RUN_TOOL, SUBMIT_TOOL], task.task_id)
        if isinstance(r, str):
            call.error = r
            break
        turn = TurnRecord(reasoning=r.reasoning, content=r.content, tool_calls=r.tool_calls,
                          finish_reason=r.finish_reason, completion_tokens=r.completion_tokens,
                          reasoning_tokens=r.reasoning_tokens)
        call.turns.append(turn)
        call.prompt_tokens += r.prompt_tokens
        call.completion_tokens += r.completion_tokens
        call.reasoning_tokens += r.reasoning_tokens
        call.cost_usd += r.cost_usd
        call.vendor = r.vendor
        call.finish_reason = r.finish_reason
        if not r.tool_calls:
            break
        messages.append({"role": "assistant", "content": r.content or None, "tool_calls": r.tool_calls})
        for tc in r.tool_calls:
            name, code = tc.get("function", {}).get("name"), _tool_code(tc)
            match name:
                case "submit_query":
                    call.submitted_code = code
                    text = "submitted"
                case "run_query" if call.run_query_calls >= AGENTIC_MAX_RUNS:
                    text = "error: run_query limit reached; call submit_query now"
                case "run_query":
                    call.run_query_calls += 1
                    text, blocked = _run_tool_result(pf, code)
                    call.blocked_run_queries += int(blocked)
                case _:
                    text = f"error: unknown tool {name}"
            turn.tool_results.append(text)
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": text})
        if call.submitted_code is not None:
            break
    call.reasoning = "\n\n---\n\n".join(t.reasoning for t in call.turns)
    call.latency_s = round(time.monotonic() - t0, 3)
    return call


def grade(task: TaskDefinition, pf: ProgramFacts, call: ModelCall) -> GradeResult:
    def result(outcome: Outcome, **kw) -> GradeResult:
        return GradeResult(task_id=task.task_id, task_reasoning_step_count=task.task_reasoning_step_count,
                           outcome=outcome, gold_answer=task.gold_answer, **kw)

    if call.submitted_code is None:
        return result(Outcome.API_ERROR if call.error else Outcome.NO_TOOL_CALL, message=call.error)
    if (why := escape_attempt(call.submitted_code)) is not None:
        return result(Outcome.EXEC_ERROR, error_type="escape_refused", message=why)
    execution = run_queries(pf.program_text, [call.submitted_code])[0]
    if execution.timed_out:
        return result(Outcome.TIMEOUT)
    if not execution.ok:
        return result(Outcome.EXEC_ERROR, error_type=execution.error_type, message=execution.message)
    if assigns_literal_answer(call.submitted_code):
        return result(Outcome.LITERAL_ANSWER, model_answer=execution.answer)
    ok = answers_match(execution.answer, task.gold_answer, task.native_answer_format, task.tolerance_rel,
                       task.tolerance_abs)
    return result(Outcome.CORRECT if ok else Outcome.WRONG, model_answer=execution.answer)


def _append(path: Path, line: str) -> None:
    with _write_lock, path.open("a") as fh:
        fh.write(line + "\n")


def done_task_ids(grades_path: Path) -> set[str]:
    if not grades_path.exists():
        return set()
    # API failures are not results; they are retried on the next run.
    rows = [json.loads(line) for line in grades_path.read_text().splitlines() if line.strip()]
    return {r["task_id"] for r in rows if r["outcome"] != Outcome.API_ERROR}


def run(tasks: list[TaskDefinition], facts: dict[str, ProgramFacts], out_dir: Path, api_key: str,
        max_cost_usd: float, harness: Harness = Harness.SINGLE_SHOT) -> list[GradeResult]:
    out_dir.mkdir(parents=True, exist_ok=True)
    calls_path, grades_path = out_dir / "calls.jsonl", out_dir / "grades.jsonl"
    done = done_task_ids(grades_path)
    todo = [t for t in tasks if t.task_id not in done]
    log.info("eval: %d tasks (%d already graded)", len(todo), len(tasks) - len(todo))
    spent = 0.0
    results: list[GradeResult] = []

    def work(task: TaskDefinition) -> tuple[GradeResult, float]:
        match harness:
            case Harness.AGENTIC:
                call = call_model_agentic(task, api_key, facts[task.program_id])
            case _:
                call = call_model(task, api_key)
        _append(calls_path, call.model_dump_json())
        g = grade(task, facts[task.program_id], call)
        _append(grades_path, g.model_dump_json())
        return g, call.cost_usd

    with ThreadPoolExecutor(max_workers=API_WORKERS) as pool:
        futures = {pool.submit(work, t): t for t in todo}
        for fut in as_completed(futures):
            g, cost = fut.result()
            spent += cost
            results.append(g)
            log.info("%s step=%d %s ($%.4f total)", g.task_id, g.task_reasoning_step_count, g.outcome.value, spent)
            if spent > max_cost_usd:
                log.error("cost cap $%.2f exceeded; cancelling remaining calls", max_cost_usd)
                for f in futures:
                    f.cancel()
                break
    return results


def regrade_literal(tasks: dict[str, TaskDefinition], calls: dict[str, ModelCall],
                    grades: list[GradeResult]) -> list[GradeResult]:
    """Re-apply the current literal-answer rule to LITERAL_ANSWER rows using the stored executed answer."""
    out = []
    for g in grades:
        if g.outcome == Outcome.LITERAL_ANSWER and not assigns_literal_answer(calls[g.task_id].submitted_code):
            t = tasks[g.task_id]
            ok = answers_match(g.model_answer, t.gold_answer, t.native_answer_format, t.tolerance_rel,
                               t.tolerance_abs)
            g.outcome = Outcome.CORRECT if ok else Outcome.WRONG
        out.append(g)
    return out
