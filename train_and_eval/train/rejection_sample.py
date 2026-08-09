"""Rejection sampling: teacher (deepseek-v4-flash) generates successful CAD-QA traces.

For each hop bucket, sample rows until the quota of *validated* tool calls is met.
A trace is kept only when the teacher's typed tool call matches the gold
(exact strings/ints, 1e-3 relative floats). Traces > MAX_TRACE_TOKENS are
compacted via compact_trace(reasoning) and the original answer call is spliced
server-side. Every call is logged for monitoring (validity, tokens, cost).
"""



from __future__ import annotations

import sys
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # train_and_eval root

import argparse
import json
import random
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from datasets import load_dataset
from pydantic import BaseModel, Field

from teacher import TeacherCall, TeacherClient, build_teacher_prompt
from tool_calls import (
    ToolName,
    TraceStep,
    TraceStepKind,
    execute_code,
    extract_tool_call,
    format_to_tool,
    tool_call_matches,
    tool_schema,
)

MAX_TRACE_TOKENS = 4000
COMPACT_BOUND_TOKENS = 3500
MAX_TOOL_ROUNDS = 3  # prompt -> up to 2 run_code execs -> submit
DEFAULT_QUOTAS = {"0": 50, "1": 50, "2": 50, "3": 75, "5": 50}

RUN_CODE_TOOLS = [tool_schema(ToolName.RUN_CODE)]

_ID_RE = re.compile(r"\b(?:wp\d+|workplane:\w+|face:\S+|kernel:\S+)\b")


class Trace(BaseModel):
    row_id: str = Field(min_length=1)
    hop: int = Field(ge=0)
    prompt: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    trace: str = Field(min_length=1)  # flattened text: reasoning + tool calls + results
    gold: str = Field(min_length=1)
    answer_format: str = Field(min_length=1)
    compacted: bool = Field(default=False)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    mode: str = Field(default="no_tools", pattern="^(no_tools|numpy)$")  # harness mode that produced this trace
    steps: list[TraceStep] = Field(default_factory=list)  # structured round-trip (SFT rendering)


class RoundLog(BaseModel):
    text: str = Field(default="")          # raw completion text of this round
    reasoning: str = Field(default="")     # provider reasoning of this round
    tool_call: str | None = Field(default=None)  # extracted tool-call envelope, if any
    result: str | None = Field(default=None)     # server-side tool result, if run_code


class AttemptLog(BaseModel):
    hop: int
    row_id: str
    ok: bool
    parsed: bool
    tool_valid: bool
    compacted: bool
    tokens: int
    cost: float
    error: str | None = None
    text: str = ""             # raw completion text (always recorded)
    reasoning: str = ""        # raw reasoning field, when the provider exposes it
    tool_call: str | None = None  # extracted tool-call JSON block (name + args), if any
    rounds: list[RoundLog] = Field(default_factory=list)  # every LLM call of the attempt (A5)


# --- compaction -------------------------------------------------------------

_COMPACT_PROMPT = (
    "You are compressing a solved CAD (CadQuery) reasoning trace.\n"
    "The question required {hop} logical reasoning hops. Compress the reasoning to "
    "at most {bound} tokens: keep exactly one concise reasoning step per logical hop, "
    "preserving all entity ids, numbers and key facts. Do NOT restate the question.\n"
    "End with exactly one JSON tool call:\n"
    '{{"name": "compact_trace", "arguments": {{"reasoning": "<compressed reasoning>"}}}}\n'
    "\n[original trace]\n{trace}\n"
)


def _key_facts(text: str) -> set[str]:
    return set(_ID_RE.findall(text))


def compact_trace(client: TeacherClient, trace: str, hop: int,
                  steps: list[TraceStep] | None = None) -> tuple[str, bool]:
    """Compress reasoning; returns (compacted_trace_with_spliced_answer, ok).

    The tool round-trips (run_code calls + server results) and the answer call
    are spliced back VERBATIM — only the reasoning prose is compressed, so
    exact computed values are never re-derived or mangled. Traces without
    steps fall back to the legacy single-answer-call splice.
    """
    tool_blocks = _tool_blocks_verbatim(steps) if steps else []
    answer_call = tool_blocks[-1] if tool_blocks else _last_tool_call_block(trace)
    if answer_call is None:
        return trace, False
    prompt = _COMPACT_PROMPT.format(hop=hop, bound=COMPACT_BOUND_TOKENS, trace=trace)
    try:
        call = client.complete(prompt)
    except Exception:
        return trace, False
    parsed = extract_tool_call(call.text, ToolName.COMPACT_TRACE)
    if parsed is None or parsed[0] != ToolName.COMPACT_TRACE:
        return trace, False
    reasoning = parsed[1].reasoning  # type: ignore[attr-defined]
    if not reasoning.strip() or call.completion_tokens > COMPACT_BOUND_TOKENS:
        return trace, False
    # light faithfulness: key ids from the original must survive (if any existed)
    orig_facts = _key_facts(trace)
    if orig_facts and not (_key_facts(reasoning) & orig_facts):
        return trace, False
    if tool_blocks:
        return f"{reasoning.strip()}\n\n" + "\n\n".join(tool_blocks), True
    return f"{reasoning.strip()}\n\n{answer_call}", True


def _tool_blocks_verbatim(steps: list[TraceStep]) -> list[str]:
    """Render tool steps exactly as they appeared (envelopes + raw results)."""
    blocks: list[str] = []
    for s in steps:
        if s.kind == TraceStepKind.TOOL_CALL and s.name is not None:
            blocks.append(json.dumps({"name": s.name.value, "arguments": s.arguments or {}}))
        elif s.kind == TraceStepKind.TOOL_RESULT:
            blocks.append(s.text)
    return blocks


def _last_tool_call_block(text: str) -> str | None:
    parsed = extract_tool_call(text, ToolName.SUBMIT_LABEL)  # expected unused for block extraction
    if parsed is None:
        return None
    # re-extract the raw JSON block to splice verbatim
    import re as _re
    m = _re.search(r"\{.*\}", text, _re.DOTALL)
    return m.group(0) if m else None


# --- sampling ---------------------------------------------------------------

class Sampler:
    def __init__(self, client: TeacherClient, quotas: dict[str, int], attempts_per_row: int, seed: int,
                 log_path: Path | None = None, out_path: Path | None = None,
                 only_rows: set[str] | None = None, target_count: int | None = None,
                 compute_tool: bool = True) -> None:
        self.client = client
        self.quotas = {str(k): v for k, v in quotas.items()}
        self.only_rows = only_rows
        self.target_count = target_count
        self.attempts_per_row = attempts_per_row
        self.seed = seed
        self.compute_tool = compute_tool
        self.lock = threading.Lock()
        self.attempts: list[AttemptLog] = []
        self.traces: dict[int, list[Trace]] = {int(k): [] for k in quotas}
        self.row_cycles: dict[int, list[dict[str, Any]]] = {}
        self.log_fh = log_path.open("a") if log_path else None
        self.out_fh = out_path.open("a") if out_path else None
        if self.out_fh and out_path.exists():
            # resume: count existing successful traces per hop
            for line in out_path.read_text().splitlines():
                if not line.strip():
                    continue
                t = Trace.model_validate_json(line)
                self.traces.setdefault(t.hop, []).append(t)

    def _log_attempt(self, a: AttemptLog) -> None:
        with self.lock:
            self.attempts.append(a)
            if self.log_fh:
                self.log_fh.write(a.model_dump_json() + "\n")
                self.log_fh.flush()

    def run(self) -> list[Trace]:
        ds = load_dataset("MRiabov/cadqa-rl-2000", "v3_curriculum", split="train")
        rows_by_hop: dict[int, list[dict[str, Any]]] = {}
        for r in ds:
            if self.only_rows is not None and r["row_id"] not in self.only_rows:
                continue
            h = int(r["logical_hop_count"])
            if str(h) in self.quotas:
                rows_by_hop.setdefault(h, []).append(dict(r))
        if self.only_rows is not None and self.target_count is not None:
            self.quotas = {str(h): self.target_count for h in rows_by_hop}
            self.traces = {h: self.traces.get(h, []) for h in rows_by_hop}
        for h, rows in rows_by_hop.items():
            rng = random.Random(self.seed + h)
            rng.shuffle(rows)
            self.row_cycles[h] = rows

        jobs = []
        total_needed = sum(int(q) for q in self.quotas.values())
        hop_list = sorted(self.quotas, key=int)
        with ThreadPoolExecutor(max_workers=24) as pool:
            for i in range(total_needed * self.attempts_per_row * 2 + 32):
                jobs.append(pool.submit(self._sample_row, int(hop_list[i % len(hop_list)])))
            for fut in as_completed(jobs):
                fut.result()
                if all(len(self.traces[int(h)]) >= q for h, q in self.quotas.items()):
                    break
        out = [t for h in sorted(self.traces) for t in self.traces[h]]
        return out

    def _sample_row(self, hop: int) -> None:
        quota = self.quotas[str(hop)]
        with self.lock:
            if len(self.traces[hop]) >= quota:
                return
            cycle = self.row_cycles[hop]
            if not cycle:
                return
            row = cycle.pop(0)
            cycle.append(row)
        tool = format_to_tool(row["answer_format"])
        for _ in range(self.attempts_per_row):
            with self.lock:
                if len(self.traces[hop]) >= quota:
                    return
            attempt = self._attempt_row(row, hop, tool)
            self._log_attempt(attempt)
            if attempt.ok:
                return

    def _attempt_row(self, row: dict[str, Any], hop: int, tool: ToolName) -> AttemptLog:
        """One sampling attempt: multi-turn teacher loop (reasoning + run_code -> submit).

        Every round's LLM output is recorded (A5). The trace captures the full
        loop as structured steps (text / tool_call / tool_result) plus a
        flattened text; the run_code round-trip is executed server-side.
        `compute_tool=False` runs the no-tools mode (reasoning only).
        """
        prompt = build_teacher_prompt(row["prompt"], tool, row["logical_hop_count"],
                                      compute_tool=self.compute_tool)
        messages: list[dict] = [{"role": "user", "content": prompt}]
        tools = RUN_CODE_TOOLS if self.compute_tool else None
        steps: list[TraceStep] = []
        round_logs: list[RoundLog] = []
        text_parts: list[str] = []
        tokens_total = 0
        cost_total = 0.0
        prompt_tokens_total = 0
        submitted: tuple[ToolName, BaseModel] | None = None
        last_call: TeacherCall | None = None
        error: str | None = None
        for _ in range(MAX_TOOL_ROUNDS):
            try:
                last_call = self.client.complete_messages(messages, tools=tools)
            except Exception as e:  # noqa: BLE001 - teacher errors are logged, not fatal
                error = f"{type(e).__name__}: {str(e)[:100]}"
                break
            tokens_total += last_call.completion_tokens
            cost_total += last_call.cost_usd
            prompt_tokens_total += last_call.prompt_tokens
            round_log = RoundLog(text=last_call.text, reasoning=last_call.reasoning)
            parsed_call = extract_tool_call(last_call.text, tool)
            if parsed_call is None or (not self.compute_tool and parsed_call[0] == ToolName.RUN_CODE):
                # no tool call (or compute call in no-tools mode): keep the prose and fail this attempt
                prose = f"{last_call.reasoning}\n\n{last_call.text}".strip()
                if prose:
                    steps.append(TraceStep(kind=TraceStepKind.TEXT, text=prose))
                    text_parts.append(prose)
                round_logs.append(round_log)
                break
            name, args = parsed_call
            round_log.tool_call = f'{{"name": "{name.value}", "arguments": {args.model_dump_json()}}}'
            if last_call.reasoning.strip():
                steps.append(TraceStep(kind=TraceStepKind.TEXT, text=last_call.reasoning))
                text_parts.append(last_call.reasoning)
            steps.append(TraceStep(kind=TraceStepKind.TOOL_CALL, name=name, arguments=args.model_dump()))
            text_parts.append(json.dumps({"name": name.value, "arguments": args.model_dump()}, ensure_ascii=False))
            round_logs.append(round_log)
            if name == ToolName.RUN_CODE:
                result = execute_code(args.code)  # type: ignore[attr-defined]
                round_log.result = result
                steps.append(TraceStep(kind=TraceStepKind.TOOL_RESULT, name=name, text=result))
                text_parts.append(result)
                # continue the conversation for the next round
                if last_call.tool_calls:
                    messages.append({"role": "assistant", "tool_calls": last_call.tool_calls})
                    tool_id = last_call.tool_calls[0].get("id")
                    if tool_id:
                        messages.append({"role": "tool", "tool_call_id": tool_id, "content": result})
                    else:
                        messages.append({"role": "user", "content": f"run_code result: {result}"})
                else:
                    messages.append({"role": "assistant", "content": last_call.text})
                    messages.append({"role": "user", "content": f"run_code result: {result}"})
                continue
            submitted = (name, args)
            break

        parsed = submitted is not None
        ok = False
        compacted = False
        if submitted is not None:
            name, args = submitted
            ok = tool_call_matches(name, args, row["gold_answer"], row["answer_format"])
        if ok:
            trace_text = "\n\n".join(p for p in text_parts if p.strip())
            if tokens_total > MAX_TRACE_TOKENS:
                trace_text, compacted = compact_trace(self.client, trace_text, hop, steps=steps)
            t = Trace(
                row_id=row["row_id"], hop=hop, prompt=row["prompt"],
                tool_name=tool.value, trace=trace_text,
                gold=row["gold_answer"], answer_format=row["answer_format"],
                compacted=compacted, prompt_tokens=prompt_tokens_total,
                completion_tokens=tokens_total,
                mode="numpy" if self.compute_tool else "no_tools",
                steps=steps if not compacted else [],
            )
            with self.lock:
                self.traces[hop].append(t)
                if self.out_fh:
                    self.out_fh.write(t.model_dump_json() + "\n")
                    self.out_fh.flush()
            print(f"[sampler] hop={hop} OK row={row['row_id'][:40]} compacted={compacted} rounds={len(round_logs)}", flush=True)
        return AttemptLog(
            hop=hop, row_id=row["row_id"], ok=ok, parsed=parsed,
            tool_valid=ok or parsed, compacted=compacted, tokens=tokens_total, cost=cost_total,
            error=error,
            text=last_call.text if last_call else "", reasoning=last_call.reasoning if last_call else "",
            tool_call=round_logs[-1].tool_call if round_logs else None,
            rounds=round_logs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("sft_traces.jsonl"))
    ap.add_argument("--log", type=Path, default=Path("sampling_log.jsonl"))
    ap.add_argument("--attempts-per-row", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=1.0,
                    help="teacher sampling temperature (re-sampling runs: use 0.3-0.6 for higher success)")
    ap.add_argument("--seed", type=int, default=3407)
    ap.add_argument("--only-rows", type=Path, default=None, help="file with row_ids (one per line); sample only these rows")
    ap.add_argument("--target-count", type=int, default=None, help="quota per hop when --only-rows is used")
    ap.add_argument("--no-compute-tool", action="store_true",
                    help="no-tools mode: teacher gets no run_code compute tool (reasoning only)")
    args = ap.parse_args()

    client = TeacherClient(max_tokens=16384, temperature=args.temperature)
    print(f"balance: ${client.balance():.2f}")
    only_rows = {ln.strip() for ln in args.only_rows.read_text().splitlines() if ln.strip()} if args.only_rows else None
    sampler = Sampler(client, DEFAULT_QUOTAS, args.attempts_per_row, args.seed, log_path=args.log,
                      out_path=args.out, only_rows=only_rows, target_count=args.target_count,
                      compute_tool=not args.no_compute_tool)
    traces = sampler.run()

    from collections import Counter
    per_hop = Counter(t.hop for t in traces)
    compacted = Counter(t.compacted for t in traces)
    print(f"traces: {len(traces)} | per-hop: {dict(sorted(per_hop.items()))} | compacted: {compacted[True]}")
    total_calls = len(sampler.attempts)
    ok_calls = sum(1 for a in sampler.attempts if a.ok)
    print(f"calls: {total_calls} | success: {ok_calls} ({ok_calls/max(total_calls,1):.1%})")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
