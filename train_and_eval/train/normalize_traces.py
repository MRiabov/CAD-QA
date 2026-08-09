"""Normalize the 275 teacher traces to gemma-native tool-call format for SFT.

Each trace becomes a pre-rendered conversation string:
  <|turn>system <|tool>declaration:...<tool|> <turn|>
  <|turn>user <prompt><turn|>
  <|turn>model <reasoning><|tool_call>call:<name>{args}<tool_call|><turn|>

Rendered via the model's own chat template with tools= (native declarations)
and tool_calls messages (native call rendering). Output: sft_texts.jsonl.
"""



from __future__ import annotations

import sys
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # train_and_eval root

import argparse
import json
import re
from pathlib import Path

from transformers import AutoProcessor

from tool_calls import (
    _ARGS_MODELS,
    ToolName,
    TraceStep,
    render_call_tokens,
    render_trace_steps,
)

TRACE_COLUMNS = ["row_id", "prompt", "trace", "hop", "tool_name", "answer_format", "gold", "compacted", "mode"]

_TOOL_DESCRIPTIONS: dict[ToolName, str] = {
    ToolName.RUN_CODE: "Execute python with numpy (np) and math preloaded; the last expression's value is returned automatically (notebook-style).",
}


def _last_valid_json(text: str) -> dict | None:
    """Parse the last JSON object in text, tolerating trailing/leading junk."""
    import json as _json
    decoder = _json.JSONDecoder()
    for i in reversed([m.start() for m in re.finditer(r"\{", text)]):
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except _json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _args_from_trace(t: dict, tool: ToolName) -> dict:
    """Extract the typed args from the trace's final tool call (any envelope form)."""
    data = _last_valid_json(t["trace"])
    if data is None:
        raise ValueError(f"no JSON block in trace {t['row_id']}")
    if isinstance(data, dict) and "arguments" in data:
        return data["arguments"]
    return data


def build_text(prompt: str, content: str, processor, tools) -> str:
    """Assistant turn = full trace content (reasoning + literal native call/response
    tokens). No tool_calls key, so the template's plain-text path keeps the
    literal <|tool_call|>/<|tool_response|> tokens as-is."""
    msgs = [
        {"role": "user", "content": [{"type": "text", "text": prompt}]},
        {"role": "assistant", "content": content},
    ]
    return processor.apply_chat_template(msgs, tools=tools, tokenize=False)


def _assistant_content(t: dict, tool: ToolName) -> str | None:
    """Render the trace's assistant turn (native tokens). None if unrenderable.

    Structured steps (multi-turn run_code round-trips) render via
    render_trace_steps; legacy text traces split reasoning from the final
    tool call and render it as one native call.
    """
    steps = [TraceStep.model_validate(s) for s in t.get("steps") or []]
    if steps:
        return render_trace_steps(steps)
    try:
        args_dict = _args_from_trace(t, tool)
    except Exception:
        return None
    m = re.search(r"\{.*\}", t["trace"], re.DOTALL)
    reasoning = t["trace"][: m.start()].rstrip() if m else t["trace"]
    return f"{reasoning}\n{render_call_tokens(tool, args_dict)}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", type=Path, default=Path("sft_traces_final.jsonl"))
    ap.add_argument("--out", type=Path, default=Path("sft_texts.jsonl"))
    ap.add_argument("--max-len", type=int, default=64000)  # keep all 275 traces as-is
    args = ap.parse_args()

    traces = [json.loads(line) for line in args.traces.read_text().splitlines() if line.strip()]
    processor = AutoProcessor.from_pretrained("unsloth/gemma-4-E2B-it")

    # tool declarations: the answer tool + ALWAYS run_code (declared but unused in
    # plain-reasoning traces teaches the student to skip it when not needed)
    tools_used = sorted({t["tool_name"] for t in traces})
    tools = []
    for name in sorted(set(tools_used) | {ToolName.RUN_CODE.value}):
        tool = ToolName(name)
        model = _ARGS_MODELS[tool]
        description = _TOOL_DESCRIPTIONS.get(tool, f"Submit the answer for the {name} format.")
        tools.append({"type": "function", "function": {
            "name": name,
            "description": description,
            "parameters": model.model_json_schema(),
        }})

    n = 0
    skipped = 0
    seq_lens: list[int] = []
    with args.out.open("w") as f:
        for t in traces:
            tool = ToolName(t["tool_name"])
            content = _assistant_content(t, tool)
            if content is None:
                skipped += 1
                continue
            text = build_text(t["prompt"], content, processor, tools)
            if len(text) > args.max_len:
                print(f"OVERLEN {t['row_id'][:40]} {len(text)}", flush=True)
                skipped += 1
                continue
            seq_lens.append(len(processor.tokenizer.encode(text, add_special_tokens=False)))
            rec = {c: t[c] for c in TRACE_COLUMNS}
            rec["text"] = text
            f.write(json.dumps(rec) + "\n")
            n += 1
    if seq_lens:
        import statistics
        print(f"normalized {n} traces (skipped {skipped}) -> {args.out}")
        print(f"seq tokens: p50 {statistics.median(seq_lens):.0f} p90 "
              f"{sorted(seq_lens)[int(len(seq_lens)*0.9)-1]} max {max(seq_lens)} | "
              f"over-6144: {sum(1 for x in seq_lens if x > 6144)} | over-8192: {sum(1 for x in seq_lens if x > 8192)}")


if __name__ == "__main__":
    main()
