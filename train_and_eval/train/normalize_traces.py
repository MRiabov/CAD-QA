"""Normalize the 275 teacher traces to gemma-native tool-call format for SFT.

Each trace becomes a pre-rendered conversation string:
  <|turn>system <|tool>declaration:...<tool|> <turn|>
  <|turn>user <prompt><turn|>
  <|turn>model <reasoning><|tool_call>call:<name>{args}<tool_call|><turn|>

Rendered via the model's own chat template with tools= (native declarations)
and tool_calls messages (native call rendering). Output: sft_texts.jsonl.
"""



from __future__ import annotations

import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # train_and_eval root

import argparse
import json
import re
from pathlib import Path

from transformers import AutoProcessor

from tool_calls import (
    FORMAT_TO_TOOL,
    _ARGS_MODELS,
    _decode_gold,
    AnswerFormat,
    ToolName,
)

TRACE_COLUMNS = ["row_id", "prompt", "trace", "hop", "tool_name", "answer_format", "gold", "compacted"]


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


def build_text(prompt: str, reasoning: str, tool: ToolName, args: dict, processor, tools) -> str:
    """Assistant turn = reasoning + literal native call tokens (no tool_calls key,
    so the template's plain-text path keeps them as-is without <|tool_response>)."""
    call = f"<|tool_call>call:{tool.value}{json.dumps(args, separators=(',', ':'))}<tool_call|>"
    msgs = [
        {"role": "user", "content": [{"type": "text", "text": prompt}]},
        {"role": "assistant", "content": f"{reasoning}\n{call}"},
    ]
    return processor.apply_chat_template(msgs, tools=tools, tokenize=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", type=Path, default=Path("sft_traces_final.jsonl"))
    ap.add_argument("--out", type=Path, default=Path("sft_texts.jsonl"))
    ap.add_argument("--max-len", type=int, default=64000)  # keep all 275 traces as-is
    args = ap.parse_args()

    traces = [json.loads(l) for l in args.traces.read_text().splitlines() if l.strip()]
    processor = AutoProcessor.from_pretrained("unsloth/gemma-4-E2B-it")

    # tool declarations: one per tool used in the traces
    tools_used = sorted({t["tool_name"] for t in traces})
    tools = []
    for name in tools_used:
        tool = ToolName(name)
        model = _ARGS_MODELS[tool]
        tools.append({"type": "function", "function": {
            "name": name,
            "description": f"Submit the answer for the {name} format.",
            "parameters": model.model_json_schema(),
        }})

    n = 0
    skipped = 0
    with args.out.open("w") as f:
        for t in traces:
            tool = ToolName(t["tool_name"])
            try:
                args_dict = _args_from_trace(t, tool)
            except Exception:
                skipped += 1
                continue
            # split reasoning from the final tool-call block: reasoning = text before the last JSON block
            import re
            m = re.search(r"\{.*\}", t["trace"], re.DOTALL)
            reasoning = t["trace"][: m.start()].rstrip() if m else t["trace"]
            text = build_text(t["prompt"], reasoning, tool, args_dict, processor, tools)
            if len(text) > args.max_len:
                print(f"OVERLEN {t[chr(114)+chr(111)+chr(119)+chr(95)+chr(105)+chr(100)][:40]} {len(text)}", flush=True)
                skipped += 1
                continue
            rec = {c: t[c] for c in TRACE_COLUMNS}
            rec["text"] = text
            f.write(json.dumps(rec) + "\n")
            n += 1
    print(f"normalized {n} traces (skipped {skipped}) -> {args.out}")
    print("sample:", traces[0]["row_id"][:40], "| text len:", len(traces[0]["trace"]))


if __name__ == "__main__":
    main()
