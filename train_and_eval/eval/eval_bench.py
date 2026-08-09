"""Benchmark the SFT gemma-4-E2B (merged bf16 checkpoint) on CAD-QA with native tool calls.

Loads the merged model via plain transformers (no unsloth patching), prompts with native
<|tool>declaration:...<tool|> blocks, and parses completions with processor.parse_response.

Three switchable harness modes (same grading, only the compute tools differ):
  no_tools — submit tools only (reasoning must be done internally),
  numpy    — submit tools + run_code python/numpy sandbox (DEFAULT),
  cadquery — submit + run_code + CadQuery execution (lands at the RL stage).
The run_code round-trip truncates generation at the first <tool_call|> close token
(verified single token id 49), executes the code server-side, injects the native
<|tool_response|> block, and continues — like the SFT v3 traces.
"""
from __future__ import annotations

import sys
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # train_and_eval root

import argparse
import json
import re
from pathlib import Path

import torch
from datasets import load_dataset
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoProcessor

from tool_calls import (
    HarnessMode,
    ToolName,
    _ARGS_MODELS,
    execute_code,
    format_to_tool,
    render_tool_response,
    tool_call_matches,
)

MAX_NEW = 4096
ROUND_MAX_NEW = 2048   # per round-trip round (generation is truncated at the tool call)
MAX_TOOL_ROUNDS = 10   # prompt -> up to 9 run_code execs -> submit (hop-5 chains need room)
BATCH = 8              # default batch (amortize weight reads); override with --batch
TOOL_CALL_CLOSE_ID = 49  # <tool_call|> single token (verified on gemma-4-E2B)


_SUBMIT_TOOLS = [
    {"type": "function", "function": {
        "name": name.value,
        "description": f"Submit the answer ({name.value}).",
        "parameters": _ARGS_MODELS[name].model_json_schema()}}
    for name in ToolName if name not in (ToolName.COMPACT_TRACE, ToolName.RUN_CODE)
]
_RUN_CODE_TOOLS = [{
    "type": "function", "function": {
        "name": ToolName.RUN_CODE.value,
        "description": "Execute python/numpy code (numpy preloaded as np) and return stdout or an error.",
        "parameters": _ARGS_MODELS[ToolName.RUN_CODE].model_json_schema()}}
]


def tools_for_mode(mode: HarnessMode) -> list[dict]:
    if mode == HarnessMode.NO_TOOLS:
        return _SUBMIT_TOOLS
    if mode == HarnessMode.CADQUERY:
        raise NotImplementedError("cadquery mode lands at the RL stage; use --mode no_tools|numpy")
    return _SUBMIT_TOOLS + _RUN_CODE_TOOLS


class ToolRound(BaseModel):
    name: str = Field(min_length=1)
    arguments: dict = Field(default_factory=dict)
    result: str | None = Field(default=None, description="Server-side run_code result, when executed.")


class EvalRow(BaseModel):
    row_id: str
    answer_format: str
    gold: str
    correct: bool
    tool_valid: bool
    tool_name: str | None
    completion_tokens: int = 0
    completion: str = ""          # raw decoded completion (debuggable trace)
    capped: bool = False          # True if a round hit ROUND_MAX_NEW without a tool call
    tool_call: str | None = None  # extracted native tool-call JSON (name + args), if any
    rounds: list[ToolRound] = Field(default_factory=list)  # every run_code round (A5)


def parse_native_tool_call(completion: str, expected: ToolName, processor) -> tuple[ToolName, object] | None:
    """Parse the LAST native <|tool_call|> block in the completion."""
    blocks = list(re.finditer(r"<\|tool_call>call:(\w+)\{.*?\}<tool_call\|>", completion, re.DOTALL))
    if not blocks:
        # fallback: bare args JSON after reasoning (old-style) -> still accept via expected tool
        m2 = re.search(r"\{.*\}", completion, re.DOTALL)
        if m2 is None:
            return None
        try:
            args = json.loads(m2.group(0))
            model = _ARGS_MODELS[expected]
            return (expected, model.model_validate(args) if isinstance(args, dict) else None)
        except Exception:
            return None
    block = blocks[-1].group(0)
    try:
        parsed = processor.parse_response(block)
    except Exception:
        return None
    if parsed is None or "tool_calls" not in parsed:
        return None
    fn = parsed["tool_calls"][0].get("function", {})
    try:
        name = ToolName(fn["name"])
    except ValueError:
        return None
    args = fn.get("arguments")
    try:
        args_model = _ARGS_MODELS[name].model_validate(args) if isinstance(args, dict) else None
    except Exception:
        args_model = None
    return (name, args_model) if args_model is not None else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=str, default="/root/cadqa-sft-merged")
    ap.add_argument("--out", type=Path, default=Path("eval_heldout.jsonl"))
    ap.add_argument("--exclude-traces", type=str, default="/root/cadqa-bench/sft_texts.jsonl")
    ap.add_argument("--max-rows", type=int, default=12)
    ap.add_argument("--seed", type=int, default=3407)
    ap.add_argument("--batch", type=int, default=BATCH, help="rows per generation batch (lower when modes share the GPU)")
    ap.add_argument("--mode", type=HarnessMode, default=HarnessMode.NUMPY,
                    choices=list(HarnessMode), help="harness mode: which compute tools the model gets")
    args = ap.parse_args()
    harness_mode = args.mode      # captured: the loop unpacks into `tool_args` so `args` (Namespace) is never shadowed
    batch_size = args.batch

    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.bfloat16, device_map="cuda", attn_implementation="sdpa")
    processor = AutoProcessor.from_pretrained(args.model)
    model.eval()
    tools = tools_for_mode(harness_mode)
    print(f"mode={harness_mode.value} tools={[t['function']['name'] for t in tools]}", flush=True)

    ds = load_dataset("MRiabov/cadqa-rl-2000", "v3_curriculum", split="train")
    rows = list(ds)
    if args.exclude_traces:
        excluded = {json.loads(line)["row_id"] for line in open(args.exclude_traces) if line.strip()}
        rows = [r for r in rows if r["row_id"] not in excluded]
    import random
    rng = random.Random(args.seed)
    rows = rng.sample(rows, min(args.max_rows, len(rows)))
    print(f"eval rows: {len(rows)} (held-out)", flush=True)

    results: list[EvalRow] = []
    eos = processor.tokenizer.eos_token_id
    pad = processor.tokenizer.pad_token_id or eos
    resp_cache: dict[str, str] = {}  # run_code snippet -> last result (dedupe identical executions)

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        msgs = [[{"role": "user", "content": [{"type": "text", "text": r["prompt"]}]}] for r in batch]
        inputs = processor.apply_chat_template(msgs, tools=tools, tokenize=True,
                                               add_generation_prompt=True, return_tensors="pt",
                                               padding=True)
        if hasattr(inputs, "items"):
            input_ids = inputs["input_ids"].to("cuda")
        else:
            input_ids = inputs.to("cuda")
        active = [True] * len(batch)
        segments: list[list[torch.Tensor]] = [[] for _ in batch]      # generated token segments
        row_rounds: list[list[ToolRound]] = [[] for _ in batch]
        finalized: list[EvalRow | None] = [None] * len(batch)

        for _ in range(MAX_TOOL_ROUNDS):
            active_idx = [j for j, a in enumerate(active) if a]
            if not active_idx:
                break
            max_len = max(input_ids[j].shape[0] for j in active_idx)
            padded = torch.full((len(active_idx), max_len), pad, dtype=torch.long, device="cuda")
            mask = torch.zeros((len(active_idx), max_len), dtype=torch.long, device="cuda")
            for k, j in enumerate(active_idx):
                n = input_ids[j].shape[0]
                padded[k, :n] = input_ids[j]
                mask[k, :n] = 1
            with torch.no_grad():
                out = model.generate(padded, attention_mask=mask, max_new_tokens=ROUND_MAX_NEW,
                                     do_sample=True, temperature=0.6, use_cache=True, pad_token_id=eos)
            for k, j in enumerate(active_idx):
                n = input_ids[j].shape[0]
                # out[k] is padded to the batch max on both sides: the row's real
                # output is input[:n] + generated tokens (which start at max_len).
                row_out = torch.cat([out[k][:n], out[k][max_len:]])
                gen = row_out[n:]
                close = (gen == TOOL_CALL_CLOSE_ID).nonzero(as_tuple=True)[0]
                if close.numel() == 0:
                    # no tool call this round: strip trailing output padding and finalize
                    while gen.numel() and int(gen[-1]) in (pad, eos):
                        gen = gen[:-1]
                    segments[j].append(gen)
                    finalized[j] = _finalize(batch[j], segments[j], row_rounds[j], processor, capped=True)
                    active[j] = False
                    continue
                call_end = int(close[0]) + 1
                call_segment = gen[:call_end]
                segments[j].append(call_segment)
                text = processor.tokenizer.decode(call_segment, skip_special_tokens=False)
                tool = format_to_tool(batch[j]["answer_format"])
                parsed = parse_native_tool_call(text, tool, processor)
                if parsed is None:
                    finalized[j] = _finalize(batch[j], segments[j], row_rounds[j], processor, capped=False)
                    active[j] = False
                    continue
                name, tool_args = parsed
                if name == ToolName.RUN_CODE and tool_args is not None:
                    code = tool_args.code  # type: ignore[attr-defined]
                    if harness_mode == HarnessMode.NO_TOOLS:
                        # no-tools mode: compute calls are not served — failed attempt
                        finalized[j] = _finalize(batch[j], segments[j], row_rounds[j], processor, capped=False)
                        active[j] = False
                        continue
                    result = resp_cache.get(code)
                    if result is None:
                        result = execute_code(code)
                        resp_cache[code] = result
                    row_rounds[j].append(ToolRound(name=name.value, arguments=tool_args.model_dump(), result=result))
                    resp_ids = processor.tokenizer.encode(
                        render_tool_response(ToolName.RUN_CODE, result), add_special_tokens=False)
                    input_ids[j] = torch.cat([row_out[:n + call_end],
                                              torch.tensor(resp_ids, dtype=torch.long, device="cuda")])
                    continue
                # answer tool: finalize
                row_rounds[j].append(ToolRound(name=name.value, arguments=tool_args.model_dump()))
                finalized[j] = _finalize(batch[j], segments[j], row_rounds[j], processor, capped=False,
                                         parsed=parsed)
                active[j] = False

        for j in range(len(batch)):
            if finalized[j] is None:
                finalized[j] = _finalize(batch[j], segments[j], row_rounds[j], processor, capped=False)
            results.append(finalized[j])
        done = min(i + batch_size, len(rows))
        print(f"[eval] {done}/{len(rows)} | acc so far {sum(x.correct for x in results)/done:.3f}", flush=True)

    with args.out.open("w") as f:
        for x in results:
            f.write(x.model_dump_json() + "\n")
    n = len(results)
    acc = sum(x.correct for x in results) / max(n, 1)
    val = sum(x.tool_valid for x in results) / max(n, 1)
    print(f"EVAL_DONE rows={n} acc={acc:.3f} tool_valid={val:.3f} -> {args.out}", flush=True)


def _finalize(row: dict, segments: list[torch.Tensor], rounds: list[ToolRound],
              processor, capped: bool, parsed: tuple[ToolName, object] | None = None) -> EvalRow:
    """Grade one row from its accumulated generation segments (native tool-call parse)."""
    comp_ids = torch.cat(segments) if segments else torch.empty(0, dtype=torch.long)
    comp = processor.tokenizer.decode(comp_ids, skip_special_tokens=True)
    n_tok = int(comp_ids.shape[0])
    tool = format_to_tool(row["answer_format"])
    if parsed is None:
        parsed = parse_native_tool_call(comp, tool, processor)
    tool_valid = parsed is not None and parsed[1] is not None
    tool_call_json = None
    if parsed is not None and parsed[1] is not None:
        tool_call_json = f'{{"name": "{parsed[0].value}", "arguments": {parsed[1].model_dump_json()}}}'
    correct = tool_valid and tool_call_matches(parsed[0], parsed[1], row["gold_answer"], row["answer_format"])
    return EvalRow(
        row_id=row["row_id"], answer_format=row["answer_format"], gold=row["gold_answer"],
        correct=correct, tool_valid=tool_valid,
        tool_name=parsed[0].value if parsed else None,
        completion_tokens=n_tok, capped=capped,
        completion=comp, tool_call=tool_call_json,
        rounds=rounds,
    )


if __name__ == "__main__":
    main()
