"""Agentic compaction: >4k-token traces compacted to [1000,4096] tokens.
If the compactor's output is too short/long, reprompt with the previous output
as context and ask it to fix the length. Up to MAX_IT iterations."""
import sys, json, re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, ".")
from teacher import TeacherClient
from tool_calls import ToolName, extract_tool_call
from transformers import AutoProcessor

client = TeacherClient(max_tokens=16384)
proc = AutoProcessor.from_pretrained("unsloth/gemma-4-E2B-it")
tok = proc.tokenizer

MIN_TOK, MAX_TOK = 1000, 4096
MAX_IT = 4

_INIT = (
    "You are compressing a solved CAD (CadQuery) reasoning trace.\n"
    "The question required {hop} logical reasoning hops. Produce a COMPLETE but condensed\n"
    "reasoning trace of {min_tok}-{max_tok} tokens: keep EVERY reasoning step (one per hop),\n"
    "all entity ids, numbers and key facts. Do NOT summarize to a few lines.\n"
    "End with exactly one JSON tool call:\n"
    '{{"name": "compact_trace", "arguments": {{"reasoning": "<compressed reasoning>"}}}}\n'
    "\n[original trace]\n{trace}\n"
)
_RETRY = (
    "Your previous compression was WRONG in length: it was {n} tokens, but the target is\n"
    "{min_tok}-{max_tok} tokens ({reason}). Rewrite it to hit the target: keep every reasoning\n"
    "step (one per logical hop), all entity ids, numbers and key facts. End with exactly one\n"
    "JSON tool call:\n"
    '{{"name": "compact_trace", "arguments": {{"reasoning": "<compressed reasoning>"}}}}\n'
    "\n[your previous output]\n{prev}\n"
)

def _iter(prompt, prev_reasoning, reason):
    if prev_reasoning is not None:
        prompt = _RETRY.format(n=len(tok.encode(prev_reasoning, add_special_tokens=False)),
                               min_tok=MIN_TOK, max_tok=MAX_TOK, reason=reason, prev=prev_reasoning)
    try:
        return client.complete(prompt)
    except Exception:
        return None

def compact(trace, hop):
    ans = re.search(r"\{.*\}", trace, re.DOTALL)
    answer_block = ans.group(0) if ans else None
    if answer_block is None:
        return None, 0
    prompt = _INIT.format(hop=hop, min_tok=MIN_TOK, max_tok=MAX_TOK, trace=trace)
    prev = None
    for it in range(MAX_IT):
        call = _iter(prompt, prev, "too short" if prev is not None and len(tok.encode(prev, add_special_tokens=False)) < MIN_TOK else "too long")
        if call is None:
            return None, 0
        parsed = extract_tool_call(call.text, ToolName.COMPACT_TRACE)
        if parsed is None or parsed[0] != ToolName.COMPACT_TRACE:
            prev = call.text[-2000:]
            continue
        reasoning = parsed[1].reasoning
        n = len(tok.encode(reasoning, add_special_tokens=False))
        print(f"  it{it} len {n}", flush=True)
        if MIN_TOK <= n <= MAX_TOK:
            return f"{reasoning.strip()}\n\n{answer_block}", n
        prev = reasoning
    return None, 0

traces = [json.loads(l) for l in open("sft_traces_final.jsonl")]
kept = [t for t in traces if len(tok.encode(t["trace"], add_special_tokens=False)) <= 4096]
long_ones = [t for t in traces if len(tok.encode(t["trace"], add_special_tokens=False)) > 4096]
print(f"kept {len(kept)}, long {len(long_ones)}", flush=True)

lock = threading.Lock()
out = list(kept)
n_ok = n_fail = 0
with ThreadPoolExecutor(max_workers=8) as pool:
    futs = {pool.submit(compact, t["trace"], t["hop"]): t for t in long_ones}
    for fut in as_completed(futs):
        t = futs[fut]
        new_trace, n = fut.result()
        if new_trace:
            t2 = dict(t); t2["trace"] = new_trace; t2["compacted"] = True; t2["trace_tokens"] = n
            with lock:
                out.append(t2); n_ok += 1
            print(f"OK {t['row_id'][:40]} -> {n} tokens", flush=True)
        else:
            with lock:
                n_fail += 1
            print(f"FAIL {t['row_id'][:40]}", flush=True)

with open("sft_traces_filtered3.jsonl", "w") as f:
    for r in out:
        f.write(json.dumps(r) + "\n")
print(f"final: {len(out)} (compacted {n_ok}, failed {n_fail})", flush=True)




import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # train_and_eval root
