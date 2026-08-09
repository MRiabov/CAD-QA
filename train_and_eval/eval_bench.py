"""Benchmark the SFT gemma-4-E2B (merged bf16 checkpoint) on CAD-QA with native tool calls.

Loads the merged model via plain transformers (no unsloth patching), prompts with native
<|tool>declaration:...<tool|> blocks, and parses completions with processor.parse_response.
Batched generation for throughput.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import torch
from datasets import load_dataset
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoProcessor

from tool_calls import (
    ToolName,
    _ARGS_MODELS,
    format_to_tool,
    tool_call_matches,
)

MAX_NEW = 4096
BATCH = 8  # batch harder: amortize weight reads across rows (aggregate tok/s scales ~batch)

_TOOLS = [
    {"type": "function", "function": {
        "name": name.value,
        "description": f"Submit the answer ({name.value}).",
        "parameters": _ARGS_MODELS[name].model_json_schema()}}
    for name in ToolName if name != ToolName.COMPACT_TRACE
]


class EvalRow(BaseModel):
    row_id: str
    answer_format: str
    gold: str
    correct: bool
    tool_valid: bool
    tool_name: str | None
    completion_tokens: int = 0
    completion: str = ""          # raw decoded completion (debuggable trace)
    capped: bool = False          # True if generation hit MAX_NEW


def parse_native_tool_call(completion: str, expected: ToolName, processor) -> tuple[ToolName, object] | None:
    m = re.search(r"<\||tool_call>call:(\w+)\{.*?\}<tool_call\|>", completion, re.DOTALL)
    if m is None:
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
    block = m.group(0)
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
    args = ap.parse_args()

    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.bfloat16, device_map="cuda", attn_implementation="sdpa")
    processor = AutoProcessor.from_pretrained(args.model)
    model.eval()

    ds = load_dataset("MRiabov/cadqa-rl-2000", "v3_curriculum", split="train")
    rows = list(ds)
    if args.exclude_traces:
        excluded = {json.loads(l)["row_id"] for l in open(args.exclude_traces) if l.strip()}
        rows = [r for r in rows if r["row_id"] not in excluded]
    import random
    rng = random.Random(args.seed)
    rows = rng.sample(rows, min(args.max_rows, len(rows)))
    print(f"eval rows: {len(rows)} (held-out)", flush=True)

    results: list[EvalRow] = []
    eos = processor.tokenizer.eos_token_id
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        msgs = [[{"role": "user", "content": [{"type": "text", "text": r["prompt"]}]}] for r in batch]
        inputs = processor.apply_chat_template(msgs, tools=_TOOLS, tokenize=True,
                                               add_generation_prompt=True, return_tensors="pt",
                                               padding=True)
        if hasattr(inputs, "items"):
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        else:
            inputs = {"input_ids": inputs.to("cuda")}
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=MAX_NEW, do_sample=True, temperature=0.6,
                                 use_cache=True, pad_token_id=eos)
        for j, r in enumerate(batch):
            raw = out[j][inputs["input_ids"][j].shape[0]:]
            comp = processor.tokenizer.decode(raw, skip_special_tokens=True)
            n_tok = int(raw.shape[0])
            tool = format_to_tool(r["answer_format"])
            parsed = parse_native_tool_call(comp, tool, processor)
            tool_valid = parsed is not None and parsed[1] is not None
            correct = tool_valid and tool_call_matches(parsed[0], parsed[1], r["gold_answer"], r["answer_format"])
            results.append(EvalRow(
                row_id=r["row_id"], answer_format=r["answer_format"], gold=r["gold_answer"],
                correct=correct, tool_valid=tool_valid,
                tool_name=parsed[0].value if parsed else None,
                completion_tokens=n_tok, capped=n_tok >= MAX_NEW,
                completion=comp,
            ))
        done = min(i + BATCH, len(rows))
        print(f"[eval] {done}/{len(rows)} | acc so far {sum(x.correct for x in results)/done:.3f}", flush=True)

    with args.out.open("w") as f:
        for x in results:
            f.write(x.model_dump_json() + "\n")
    n = len(results)
    acc = sum(x.correct for x in results) / max(n, 1)
    val = sum(x.tool_valid for x in results) / max(n, 1)
    print(f"EVAL_DONE rows={n} acc={acc:.3f} tool_valid={val:.3f} -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
