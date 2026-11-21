"""Call LLM models on the step-9 no-kernel tasks and grade their submitted answers.

Two harnesses:
- ``no_tools``: submit only; all reasoning is internal.
- ``numpy``: submit plus a sandboxed ``run_code`` with NumPy and math, no CadQuery.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from pydantic import BaseModel, Field

from experiments.old.new_dataset_eval_scratch.grading import grade_answer
from experiments.old.new_dataset_eval_scratch.models import AnswerCall, AnswerGrade, Step9Outcome, TaskDefinition
from experiments.old.cq_query_scratch.grading import escape_attempt
from experiments.old.cq_query_scratch.kernel import run_queries
from experiments.old.cq_query_scratch.models import ProgramFacts, TurnRecord

log = logging.getLogger(__name__)

MERGE_BASE = "https://api-gateway.merge.dev/v1/openai"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash-1017"
DEFAULT_PROVIDER = "merge"
DEFAULT_HARNESS = "numpy"
TEMPERATURE = 0.0
TOP_P = 1.0
REASONING_EFFORT = "high"
MAX_TOKENS = int(os.environ.get("NDS_MAX_TOKENS", "32000"))
MAX_TURNS = int(os.environ.get("NDS_MAX_TURNS", "3"))
NUMPY_MAX_RUNS = int(os.environ.get("NDS_NUMPY_MAX_RUNS", "8"))
API_RETRIES = 3
REQUEST_TIMEOUT_S = 600
API_WORKERS = int(os.environ.get("NDS_API_WORKERS", "60"))
RUN_CODE_SANDBOX = Path(__file__).with_name("run_code_sandbox.py")
RUN_CODE_TIMEOUT_S = 10.0


def execute_code(code: str, timeout: float = RUN_CODE_TIMEOUT_S) -> str:
    """Run one snippet in the repository's NumPy-only sandbox; return stdout or the error."""
    try:
        proc = subprocess.run([sys.executable, "-I", "-B", str(RUN_CODE_SANDBOX)], input=code,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"Error: execution timed out after {timeout:.0f}s"
    if proc.returncode == 0:
        return (proc.stdout.strip() or "Ok (no output)")[:8000]
    return ("Error: " + (proc.stderr.strip() or f"exit code {proc.returncode}"))[-8000:]


def run_cadquery(facts: ProgramFacts, code: str) -> str:
    """Execute one snippet after the program with CadQuery; return repr(answer) and stdout."""
    if (why := escape_attempt(code)) is not None:
        return f"refused: code may not access the environment ({why}); compute with CadQuery only"
    result = run_queries(facts.program_text, [code], explore=True)[0]
    printed = f"\nstdout:\n{result.stdout}" if result.stdout else ""
    if result.timed_out:
        return "error: timed out"
    if not result.ok:
        return f"error: {result.error_type}: {(result.message or '')[-1500:]}{printed}"
    return f"answer = {result.repr_text}{printed}"

SUBMIT_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_answer",
        "description": "Submit the final answer as a string.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {"type": "string", "description": "The final answer only, in the requested format."}
            },
            "required": ["answer"],
        },
    },
}

RUN_CODE_TOOL = {
    "type": "function",
    "function": {
        "name": "run_code",
        "description": "Run Python with numpy as np and math preloaded. No CadQuery, files, or network. "
                       "Returns the last expression's value or an error.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code; the last expression is displayed."}
            },
            "required": ["code"],
        },
    },
}

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


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _session(api_key: str, provider: str) -> requests.Session:
    key = f"session_{provider}"
    if not hasattr(_local, key):
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
        if provider == "openrouter":
            session.headers.update({"HTTP-Referer": "https://github.com/MRiabov/CAD-QA", "X-Title": "CAD-QA step-9 eval"})
        setattr(_local, key, session)
    return getattr(_local, key)


def _provider_base(provider: str) -> str:
    match provider:
        case "merge":
            return MERGE_BASE
        case "openrouter":
            return OPENROUTER_BASE
    raise SystemExit(f"unknown provider {provider!r}; use merge or openrouter")


def _payload(model: str, messages: list[dict], provider: str, tools: list[dict], max_tokens: int = MAX_TOKENS,
             reasoning_effort: str = REASONING_EFFORT, tool_choice: dict | None = None) -> dict:
    payload = {
        "model": model.removeprefix("openrouter/"),
        "messages": messages,
        "tools": tools,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": max_tokens,
    }
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    if provider == "merge":
        payload["reasoning_effort"] = reasoning_effort
        if model.startswith("xiaomi/"):
            payload["vendor"] = "xiaomi"
        elif model.startswith("deepseek/"):
            payload["vendor"] = "deepseek"
    return payload


def chat(api_key: str, model: str, provider: str, messages: list[dict], tools: list[dict], *,
         max_tokens: int = MAX_TOKENS, reasoning_effort: str = REASONING_EFFORT,
         tool_choice: dict | None = None) -> ChatResponse:
    base = _provider_base(provider)
    r = _session(api_key, provider).post(
        f"{base}/chat/completions",
        json=_payload(model, messages, provider, tools, max_tokens, reasoning_effort, tool_choice),
        timeout=REQUEST_TIMEOUT_S)
    if r.status_code >= 400:
        raise ApiError(f"HTTP {r.status_code}: {r.text[:800]}")
    data = r.json()
    choice = data["choices"][0]
    msg = choice["message"]
    usage = data.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return ChatResponse(
        content=msg.get("content") or "",
        reasoning=msg.get("thinking") or msg.get("reasoning_content") or msg.get("reasoning") or "",
        tool_calls=msg.get("tool_calls") or [],
        finish_reason=choice.get("finish_reason"),
        prompt_tokens=usage.get("prompt_tokens") or 0,
        completion_tokens=usage.get("completion_tokens") or 0,
        reasoning_tokens=details.get("reasoning_tokens") or 0,
        cost_usd=float(usage.get("cost") or 0.0),
        vendor=r.headers.get("x-merge-vendor", ""),
    )


def _submitted_answer(tool_calls: list[dict]) -> str | None:
    for tc in tool_calls:
        fn = tc.get("function", {})
        if fn.get("name") != "submit_answer":
            continue
        raw = fn.get("arguments")
        if isinstance(raw, str):
            try:
                args = json.loads(raw)
            except json.JSONDecodeError:
                return raw.strip() or None
        elif isinstance(raw, dict):
            args = raw
        else:
            return None
        answer = args.get("answer") if isinstance(args, dict) else args
        match answer:
            case str():
                return answer.strip() or None
            case int() | float():
                return str(answer)
            case list():
                return json.dumps(answer)
            case None:
                return None
            case _:
                return str(answer)
    return None


def _run_code(tc: dict, harness: str, facts: ProgramFacts | None) -> str:
    try:
        args = json.loads(tc.get("function", {}).get("arguments") or "{}")
    except json.JSONDecodeError:
        return "error: invalid JSON arguments for run_code"
    code = args.get("code") if isinstance(args, dict) else None
    if not isinstance(code, str) or not code.strip():
        return "error: run_code needs a non-empty `code` string"
    if harness == "cadquery":
        if facts is None:
            return "error: CadQuery harness has no program facts"
        return run_cadquery(facts, code)
    return execute_code(code)


def _chat_with_retries(api_key: str, model: str, provider: str, messages: list[dict], tools: list[dict],
                       task_id: str, *, max_tokens: int = MAX_TOKENS,
                       reasoning_effort: str = REASONING_EFFORT,
                       tool_choice: dict | None = None) -> ChatResponse | str:
    error = ""
    for attempt in range(API_RETRIES):
        try:
            return chat(api_key, model, provider, messages, tools, max_tokens=max_tokens,
                        reasoning_effort=reasoning_effort, tool_choice=tool_choice)
        except (ApiError, requests.RequestException, KeyError, ValueError, IndexError) as exc:
            error = f"{type(exc).__name__}: {exc}"[:2000]
            log.warning("api error on %s (attempt %d): %s", task_id, attempt + 1, error[:200])
            time.sleep(5 * (attempt + 1))
    return error


def call_model(task: TaskDefinition, system: str, user: str, api_key: str, model: str, provider: str,
               harness: str = DEFAULT_HARNESS, facts: ProgramFacts | None = None) -> AnswerCall:
    call = AnswerCall(task_id=task.task_id, model=model, provider=provider, harness=harness,
                      provider_base=_provider_base(provider), system_prompt_sha256=_sha(system),
                      user_prompt_sha256=_sha(user))
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    tools = [RUN_CODE_TOOL, SUBMIT_TOOL] if harness in ("numpy", "cadquery") else [SUBMIT_TOOL]
    max_turns = NUMPY_MAX_RUNS + 2 if harness in ("numpy", "cadquery") else MAX_TURNS
    t0 = time.monotonic()
    for turn_index in range(max_turns):
        final_turn = turn_index == max_turns - 1
        r = _chat_with_retries(
            api_key, model, provider, messages, tools, task.task_id,
            max_tokens=4000 if final_turn else MAX_TOKENS,
            reasoning_effort="low" if final_turn else REASONING_EFFORT,
            tool_choice={"type": "function", "function": {"name": "submit_answer"}} if final_turn else None,
        )
        if isinstance(r, str):
            call.error = r
            break
        call.turns.append(TurnRecord(reasoning=r.reasoning, content=r.content, tool_calls=r.tool_calls,
                                     finish_reason=r.finish_reason, completion_tokens=r.completion_tokens,
                                     reasoning_tokens=r.reasoning_tokens))
        call.prompt_tokens += r.prompt_tokens
        call.completion_tokens += r.completion_tokens
        call.reasoning_tokens += r.reasoning_tokens
        call.cost_usd += r.cost_usd
        call.vendor = r.vendor
        call.finish_reason = r.finish_reason
        call.tool_calls.extend(r.tool_calls)
        answer = _submitted_answer(r.tool_calls)
        if answer is not None:
            call.submitted_answer = answer
            break
        if not r.tool_calls:
            if turn_index + 1 >= max_turns:
                break
            messages.append({"role": "assistant", "content": r.content or None})
            messages.append({"role": "user", "content": (
                "Submit your best answer now. Call `submit_answer` once with only the final answer.")})
            continue
        messages.append({"role": "assistant", "content": r.content or None, "tool_calls": r.tool_calls})
        for tc in r.tool_calls:
            name = tc.get("function", {}).get("name")
            if name == "run_code" and harness in ("numpy", "cadquery"):
                if call.run_code_calls >= NUMPY_MAX_RUNS:
                    text = "error: run_code limit reached; call submit_answer now"
                else:
                    call.run_code_calls += 1
                    text = _run_code(tc, harness, facts)
            else:
                text = f"error: unknown tool {name}; call submit_answer" if name != "submit_answer" else "submitted"
            call.turns[-1].tool_results.append(text)
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": text})
        if turn_index + 1 >= max_turns:
            break
        messages.append({"role": "user", "content": (
            "Continue if you need `run_code`, then call `submit_answer` once. "
            "Do not continue reasoning after you have enough information.")})
    call.reasoning = "\n\n---\n\n".join(t.reasoning for t in call.turns)
    call.content = "\n\n---\n\n".join(t.content for t in call.turns)
    call.latency_s = round(time.monotonic() - t0, 3)
    return call


def grade(task: TaskDefinition, call: AnswerCall) -> AnswerGrade:
    if call.submitted_answer is None:
        outcome = Step9Outcome.API_ERROR if call.error else Step9Outcome.NO_TOOL_CALL
        return AnswerGrade(task_id=task.task_id, task_reasoning_step_count=task.task_reasoning_step_count,
                           outcome=outcome, gold_answer=task.gold_answer, message=call.error)
    ok, parsed, error_type = grade_answer(task, call.submitted_answer)
    if error_type:
        return AnswerGrade(task_id=task.task_id, task_reasoning_step_count=task.task_reasoning_step_count,
                           outcome=Step9Outcome.PARSE_ERROR, model_answer=call.submitted_answer,
                           gold_answer=task.gold_answer, error_type=error_type)
    return AnswerGrade(task_id=task.task_id, task_reasoning_step_count=task.task_reasoning_step_count,
                       outcome=Step9Outcome.CORRECT if ok else Step9Outcome.WRONG,
                       model_answer=call.submitted_answer, parsed_answer=parsed, gold_answer=task.gold_answer)


def _append(path: Path, line: str) -> None:
    with _write_lock, path.open("a") as fh:
        fh.write(line + "\n")


def _done_task_ids(grades_path: Path) -> set[str]:
    if not grades_path.exists():
        return set()
    rows = [json.loads(line) for line in grades_path.read_text().splitlines() if line.strip()]
    return {r["task_id"] for r in rows if r["outcome"] != Step9Outcome.API_ERROR.value}


def run(tasks: list[TaskDefinition], prompts: dict[str, dict], facts: dict[str, ProgramFacts] | None,
        out_dir: Path, api_key: str, model: str, provider: str, harness: str, max_cost_usd: float,
        limit: int = 0) -> list[AnswerGrade]:
    out_dir.mkdir(parents=True, exist_ok=True)
    calls_path, grades_path = out_dir / "calls.jsonl", out_dir / "grades.jsonl"
    done = _done_task_ids(grades_path)
    todo = [t for t in tasks if t.task_id not in done]
    if limit:
        todo = todo[:limit]
    log.info("eval: %d tasks (%d already graded, %d todo), harness=%s", len(tasks), len(tasks) - len(todo),
             len(todo), harness)
    spent = 0.0
    results: list[AnswerGrade] = []
    lock = threading.Lock()

    def work(task: TaskDefinition) -> tuple[AnswerGrade, float]:
        row = prompts[task.task_id]
        facts_for_task = facts[task.program_id] if facts is not None else None
        call = call_model(task, row["system"], row[f"user_{harness}"], api_key, model, provider, harness,
                          facts_for_task)
        _append(calls_path, call.model_dump_json())
        g = grade(task, call)
        _append(grades_path, g.model_dump_json())
        return g, call.cost_usd

    with ThreadPoolExecutor(max_workers=API_WORKERS) as pool:
        futures = {pool.submit(work, t): t for t in todo}
        for fut in as_completed(futures):
            g, cost = fut.result()
            with lock:
                spent += cost
                results.append(g)
            log.info("%s %s ($%.4f total)", g.task_id, g.outcome.value, spent)
            if spent > max_cost_usd:
                log.error("cost cap $%.2f exceeded; cancelling remaining calls", max_cost_usd)
                for f in futures:
                    f.cancel()
                break
    return results


def api_key_for(provider: str, repo_root: Path) -> str:
    env_name = "MERGE_GATEWAY_API_KEY" if provider == "merge" else "OPENROUTER_API_KEY"
    key = os.environ.get(env_name)
    if key:
        return key
    env_path = repo_root / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith(f"{env_name}="):
            return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit(f"{env_name} not found")
