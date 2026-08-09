"""Rejection sampling: teacher (deepseek-v4-flash) generates successful CAD-QA traces.

For each hop bucket, sample rows until the quota of *validated* tool calls is met.
A trace is kept only when the teacher's typed tool call matches the gold
(exact strings/ints, 1e-3 relative floats). Traces > MAX_TRACE_TOKENS are
compacted via compact_trace(reasoning) and the original answer call is spliced
server-side. Every call is logged for monitoring (validity, tokens, cost).
"""



from __future__ import annotations

import sys, os as _os
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
    CompactTraceArgs,
    ToolName,
    extract_tool_call,
    format_to_tool,
    tool_call_matches,
)

MAX_TRACE_TOKENS = 4000
COMPACT_BOUND_TOKENS = 3500
DEFAULT_QUOTAS = {"0": 50, "1": 50, "2": 50, "3": 75, "5": 50}

_ID_RE = re.compile(r"\b(?:wp\d+|workplane:\w+|face:\S+|kernel:\S+)\b")


class Trace(BaseModel):
    row_id: str = Field(min_length=1)
    hop: int = Field(ge=0)
    prompt: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    trace: str = Field(min_length=1)  # reasoning + final tool call
    gold: str = Field(min_length=1)
    answer_format: str = Field(min_length=1)
    compacted: bool = Field(default=False)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)


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


def compact_trace(client: TeacherClient, trace: str, hop: int) -> tuple[str, bool]:
    """Compress reasoning; returns (compacted_trace_with_spliced_answer, ok).

    The answer tool call is extracted from the original and re-appended
    server-side (never re-derived by the compactor).
    """
    answer_call = _last_tool_call_block(trace)
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
    return f"{reasoning.strip()}\n\n{answer_call}", True


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
                 only_rows: set[str] | None = None, target_count: int | None = None) -> None:
        self.client = client
        self.quotas = {str(k): v for k, v in quotas.items()}
        self.only_rows = only_rows
        self.target_count = target_count
        self.attempts_per_row = attempts_per_row
        self.seed = seed
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
        call: TeacherCall | None = None
        for _ in range(self.attempts_per_row):
            with self.lock:
                if len(self.traces[hop]) >= quota:
                    return
            prompt = build_teacher_prompt(row["prompt"], tool, row["logical_hop_count"])
            parsed = False
            ok = False
            compacted = False
            error = None
            tool_call = None
            try:
                call: TeacherCall = self.client.complete(prompt)
                parsed_call = extract_tool_call(call.text, tool)
                parsed = parsed_call is not None
                if parsed:
                    name, args = parsed_call
                    tool_call = f'{{"name": "{name.value}", "arguments": {args.model_dump_json()}}}'
                    ok = tool_call_matches(name, args, row["gold_answer"], row["answer_format"])
                tokens = call.completion_tokens
                cost = call.cost_usd
                if ok:
                    trace_text = (call.reasoning + "\n\n" + call.text).strip() if call.reasoning else call.text
                    if call.completion_tokens > MAX_TRACE_TOKENS:
                        trace_text, compacted = compact_trace(self.client, trace_text, hop)
                    t = Trace(
                        row_id=row["row_id"], hop=hop, prompt=row["prompt"],
                        tool_name=tool.value, trace=trace_text,
                        gold=row["gold_answer"], answer_format=row["answer_format"],
                        compacted=compacted, prompt_tokens=call.prompt_tokens,
                        completion_tokens=call.completion_tokens,
                    )
                    with self.lock:
                        self.traces[hop].append(t)
                        if self.out_fh:
                            self.out_fh.write(t.model_dump_json() + "\n")
                            self.out_fh.flush()
                    self._log_attempt(AttemptLog(
                        hop=hop, row_id=row["row_id"], ok=True, parsed=True,
                        tool_valid=True, compacted=compacted, tokens=tokens, cost=cost,
                        text=call.text, reasoning=call.reasoning, tool_call=tool_call))
                    print(f"[sampler] hop={hop} OK row={row['row_id'][:40]} compacted={compacted}", flush=True)
                    return
            except Exception as e:  # noqa: BLE001 - teacher errors are logged, not fatal
                error = f"{type(e).__name__}: {str(e)[:100]}"
            self._log_attempt(AttemptLog(
                hop=hop, row_id=row["row_id"], ok=ok, parsed=parsed,
                tool_valid=parsed, compacted=compacted, tokens=0, cost=0.0, error=error,
                text=call.text if call else "", reasoning=call.reasoning if call else "",
                tool_call=tool_call))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("sft_traces.jsonl"))
    ap.add_argument("--log", type=Path, default=Path("sampling_log.jsonl"))
    ap.add_argument("--attempts-per-row", type=int, default=5)
    ap.add_argument("--seed", type=int, default=3407)
    ap.add_argument("--only-rows", type=Path, default=None, help="file with row_ids (one per line); sample only these rows")
    ap.add_argument("--target-count", type=int, default=None, help="quota per hop when --only-rows is used")
    args = ap.parse_args()

    client = TeacherClient(max_tokens=16384)
    print(f"balance: ${client.balance():.2f}")
    only_rows = {ln.strip() for ln in args.only_rows.read_text().splitlines() if ln.strip()} if args.only_rows else None
    sampler = Sampler(client, DEFAULT_QUOTAS, args.attempts_per_row, args.seed, log_path=args.log,
                      out_path=args.out, only_rows=only_rows, target_count=args.target_count)
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
