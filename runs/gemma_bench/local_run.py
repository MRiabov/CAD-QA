"""Local Gemma-4-E2B CAD-QA bench runner (Vast/Colab/local GPU).

Same harness logic as the Kaggle notebook, with local paths:
  - REQUESTS_DIR: dir containing rc10_zero_shot.jsonl / release10k_zero_shot.jsonl
  - OUT_DIR: where responses_h1_<slice>.jsonl / responses_h3_<slice>.jsonl are written

Env knobs: CADQA_MODEL_ID, CADQA_SLICES, CADQA_RUN_H1/H3, CADQA_SAMPLE_LIMIT,
CADQA_MAX_TURNS, CADQA_EXEC_TIMEOUT, CADQA_MAX_NEW_TOKENS, CADQA_TEMPERATURE,
CADQA_SEED.
"""

import contextlib
import io
import json
import os
import random
import re
import signal
from pathlib import Path

MODEL_ID = os.environ.get("CADQA_MODEL_ID", "google/gemma-4-E2B-it")
SLICES = os.environ.get("CADQA_SLICES", "both")
RUN_HARNESS1 = os.environ.get("CADQA_RUN_H1", "1") == "1"
RUN_HARNESS3 = os.environ.get("CADQA_RUN_H3", "1") == "1"
SAMPLE_LIMIT = int(os.environ.get("CADQA_SAMPLE_LIMIT", "0") or 0)
MAX_TURNS_H3 = int(os.environ.get("CADQA_MAX_TURNS", "4"))
EXEC_TIMEOUT_SECS = int(os.environ.get("CADQA_EXEC_TIMEOUT", "15"))
BATCH_SIZE = int(os.environ.get("CADQA_BATCH", "8"))
MAX_NEW_TOKENS = int(os.environ.get("CADQA_MAX_NEW_TOKENS", "16384"))
MAX_SEQ_LENGTH = int(os.environ.get("CADQA_MAX_SEQ", "32768"))
TEMPERATURE = float(os.environ.get("CADQA_TEMPERATURE", "0.2"))
SEED = int(os.environ.get("CADQA_SEED", "20260808"))
random.seed(SEED)

REQUESTS_DIR = Path(os.environ.get("CADQA_REQUESTS_DIR", "requests"))
OUT_DIR = Path(os.environ.get("CADQA_OUT_DIR", "out"))
OUT_DIR.mkdir(parents=True, exist_ok=True)


def find_requests() -> dict[str, list[dict]]:
    found: dict[str, list[dict]] = {}
    for p in sorted(REQUESTS_DIR.glob("*.jsonl")):
        rows = [json.loads(line) for line in open(p)]
        if not rows or "messages" not in rows[0] or "row_id" not in rows[0]:
            continue
        name = p.name
        for key in ("rc10", "release10k", "zero_shot"):
            if key in name:
                name = key
        found.setdefault(name, rows)
    return found


REQUESTS = find_requests()
print("found request files:", {k: len(v) for k, v in REQUESTS.items()}, flush=True)
if not REQUESTS:
    raise SystemExit(f"No request JSONL found under {REQUESTS_DIR}")


def slice_names() -> list[str]:
    if SLICES == "both":
        names = [k for k in ("rc10", "release10k") if k in REQUESTS]
        return names or list(REQUESTS)
    return [SLICES] if SLICES in REQUESTS else list(REQUESTS)


def selected_requests(name: str) -> list[dict]:
    rows = REQUESTS[name]
    if SAMPLE_LIMIT:
        rows = rows[:SAMPLE_LIMIT]
    return rows


# ---------------------------------------------------------------- model load
import torch  # noqa: E402


def _device():
    try:
        return model.get_input_embeddings().weight.device
    except Exception:  # noqa: BLE001
        return next(model.parameters()).device


def load_model():
    global model, tokenizer
    try:
        from unsloth import FastModel

        model, tokenizer = FastModel.from_pretrained(
            model_name="unsloth/gemma-4-E2B-it",
            max_seq_length=MAX_SEQ_LENGTH,
            dtype=torch.bfloat16,
            load_in_4bit=True,
        )
        FastModel.for_inference(model)
    except Exception as exc:  # noqa: BLE001
        print("unsloth load failed:", type(exc).__name__, exc, flush=True)
        from transformers import AutoModelForMultimodalLM, AutoProcessor, BitsAndBytesConfig  # noqa: E402

        if torch.cuda.is_available():
            try:
                model = AutoModelForMultimodalLM.from_pretrained(
                    MODEL_ID,
                    dtype="auto",
                    device_map="auto",
                    quantization_config=BitsAndBytesConfig(load_in_4bit=True),
                )
                tokenizer = AutoProcessor.from_pretrained(MODEL_ID)
            except Exception as exc2:  # noqa: BLE001
                print("transformers 4-bit load failed:", type(exc2).__name__, exc2, flush=True)
                model = AutoModelForMultimodalLM.from_pretrained(MODEL_ID, dtype="auto", device_map="auto")
                tokenizer = AutoProcessor.from_pretrained(MODEL_ID)
        else:
            model = AutoModelForMultimodalLM.from_pretrained(MODEL_ID, dtype="auto", device_map="auto")
            tokenizer = AutoProcessor.from_pretrained(MODEL_ID)
    try:
        base_tok = tokenizer.tokenizer if hasattr(tokenizer, "tokenizer") else tokenizer
        base_tok.padding_side = "left"
        if base_tok.pad_token is None:
            base_tok.pad_token = base_tok.eos_token
    except Exception:  # noqa: BLE001
        pass
    return model, tokenizer


model, tokenizer = load_model()
print("loaded:", MODEL_ID, "| device:", _device(), flush=True)


# ------------------------------------------------------------------ helpers
def _normalize_messages(messages: list[dict]) -> list[dict]:
    """gemma-4 multimodal processor expects content as typed blocks."""
    out = []
    for message in messages:
        content = message["content"]
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        out.append({**message, "content": content})
    return out


def _strip_special(text: str) -> str:
    text = re.sub(r"<[^>]*turn[^>]*>", "", text)  # gemma-4 <turn|> separators
    try:
        base = tokenizer.tokenizer if hasattr(tokenizer, "tokenizer") else tokenizer
        specials = base.all_special_tokens
    except Exception:  # noqa: BLE001
        specials = []
    for tok in specials:
        text = text.replace(tok, "")
    return str(text).strip()


def generate(messages: list[dict], max_new_tokens: int = MAX_NEW_TOKENS, temperature: float = TEMPERATURE) -> str:
    inputs = tokenizer.apply_chat_template(
        _normalize_messages(messages), tokenize=True, return_dict=True, return_tensors="pt",
        add_generation_prompt=True, enable_thinking=False,
    ).to(_device())
    input_len = inputs["input_ids"].shape[-1]
    with torch.inference_mode():
        outputs = model.generate(
            **inputs, max_new_tokens=max_new_tokens, temperature=temperature,
            top_p=0.95, top_k=64, do_sample=True, use_cache=True,
        )
    response = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=False)
    try:
        parsed = tokenizer.parse_response(response, prefix=inputs["input_ids"])
        text = parsed.get("response") or parsed.get("text") or response
    except Exception:  # noqa: BLE001
        text = response
    text = re.sub(r"<[^>]*turn[^>]*>", "", text)
    return _strip_special(text)


def batch_generate(messages_list: list[list[dict]], max_new_tokens: int = MAX_NEW_TOKENS,
                   temperature: float = TEMPERATURE) -> list[str]:
    inputs = tokenizer.apply_chat_template(
        [_normalize_messages(m) for m in messages_list], tokenize=True, return_dict=True,
        return_tensors="pt", padding=True, add_generation_prompt=True, enable_thinking=False,
    )
    inputs = {k: v.to(_device()) for k, v in inputs.items()}
    real_lens = inputs["attention_mask"].sum(dim=1)
    with torch.inference_mode():
        outputs = model.generate(
            **inputs, max_new_tokens=max_new_tokens, temperature=temperature,
            top_p=0.95, top_k=64, do_sample=True, use_cache=True,
        )
    texts = []
    for i, prefix_len in enumerate(real_lens.tolist()):
        response = tokenizer.decode(outputs[i][prefix_len:], skip_special_tokens=False)
        try:
            parsed = tokenizer.parse_response(response, prefix=inputs["input_ids"][i][:prefix_len])
            text = parsed.get("response") or parsed.get("text") or response
        except Exception:  # noqa: BLE001
            text = response
        text = re.sub(r"<[^>]*turn[^>]*>", "", text)
        texts.append(_strip_special(text))
    return texts


FINAL_RE = re.compile(r"FINAL\s*ANSWER\s*:?\s*(.+)", re.IGNORECASE | re.DOTALL)


def extract_final(text: str) -> str | None:
    m = FINAL_RE.search(text)
    return m.group(1).strip() if m else None


def last_line(text: str) -> str:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else text.strip()


def extract_code(text: str) -> str | None:
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL)
    if blocks:
        code = max(blocks, key=len).strip()
    else:
        m = re.search(r"import cadquery[\s\S]*", text)
        code = m.group(0).strip() if m else (text.strip() if ("\n" in text or "cq." in text) else None)
    if not code:
        return None
    code = re.sub(r"^\s*```(?:python|py)?\s*\n?", "", code)  # strip leading fence remnants
    code = re.sub(r"```\s*$", "", code)  # strip trailing fence
    return code.strip() or None


def _script_from_prompt(prompt: str) -> str | None:
    m = re.search(r"```python\n(.*?)```", prompt, re.DOTALL)
    return m.group(1).strip() if m else None


def run_cadquery(code: str, context_script: str | None = None, ns: dict | None = None) -> tuple[str, str | None]:
    buf = io.StringIO()
    error: str | None = None
    if ns is None:
        ns = {"__name__": "__main__", "__builtins__": __builtins__}

    def _timeout_handler(_sig, _frame):
        raise TimeoutError(f"cadquery exec timed out after {EXEC_TIMEOUT_SECS}s")

    old_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(EXEC_TIMEOUT_SECS)
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            if context_script:
                exec(context_script, ns)
            exec(code, ns)
    except BaseException as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
    return buf.getvalue().strip()[:3000], error


def load_done(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {json.loads(line)["row_id"] for line in open(path)}


def append_result(path: Path, rec: dict) -> None:
    with open(path, "a") as fh:
        fh.write(json.dumps(rec) + "\n")


SYSTEM_H1 = "You are an expert in CAD geometry reasoning. Answer with exactly the requested value and nothing else."

SYSTEM_H3 = (
    "You are a CAD geometry reasoning agent. A CadQuery script and a question about the resulting "
    "CAD model are given. The script has ALREADY been executed and all its objects (wp1, wp2, ..., "
    "result) are live in the Python environment, with CadQuery available (import cadquery as cq).\n"
    "To answer the question, write ONLY the additional Python statements that compute and print the "
    "answer using the existing variables - do NOT repeat the whole script.\n"
    "Rules:\n"
    "- Respond with ONLY a Python code block (```python ... ```) or a final answer.\n"
    "- Your code runs after the original script, so every variable from the script is available to you.\n"
    "- After the execution output is returned, either write corrected statements, or - when you are "
    "confident - answer with the exact value.\n"
    "- The final answer line must start with exactly \"FINAL ANSWER: \" followed by ONLY the required "
    "value (a number, coordinate tuple, entity id, label, or JSON), nothing else.\n"
    "- Do not call the network. Do not write files."
)


# ---------------------------------------------------------------- harnesses
def run_harness1(name: str) -> Path:
    rows = selected_requests(name)
    out = OUT_DIR / f"responses_h1_{name}.jsonl"
    done = load_done(out)
    print(f"[h1:{name}] {len(rows)} rows, {len(done)} already done -> {out.name}", flush=True)
    pending = [req for req in rows if req["row_id"] not in done]
    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]
        msgs = [[{"role": "system", "content": SYSTEM_H1},
                 {"role": "user", "content": req["messages"][-1]["content"]}] for req in batch]
        try:
            texts = batch_generate(msgs)
        except Exception as exc:  # noqa: BLE001
            print("  h1 batch generate error:", type(exc).__name__, exc, flush=True)
            texts = []
            for req in batch:
                try:
                    texts.append(generate([{"role": "system", "content": SYSTEM_H1},
                                           {"role": "user", "content": req["messages"][-1]["content"]}]))
                except Exception as exc2:  # noqa: BLE001
                    texts.append("")
                    print("  h1 generate error:", type(exc2).__name__, exc2, flush=True)
        for req, text in zip(batch, texts):
            answer = extract_final(text) or last_line(text)
            append_result(out, {"row_id": req["row_id"], "answer": answer, "confidence": None,
                                "harness": "h1", "metadata": {"slice": name, "raw": text[:500]}})
        if (start + len(batch)) % 10 == 0 or start + len(batch) >= len(pending):
            print(f"  h1[{name}] {len(done) + start + len(batch)}/{len(rows)}", flush=True)
    return out


def run_harness3(name: str) -> Path:
    rows = selected_requests(name)
    out = OUT_DIR / f"responses_h3_{name}.jsonl"
    done = load_done(out)
    print(f"[h3:{name}] {len(rows)} rows, {len(done)} already done -> {out.name}", flush=True)
    stats = {"exec_errors": 0, "turns_used": []}
    active: list[dict] = []
    for req in rows:
        if req["row_id"] in done:
            continue
        active.append({
            "row_id": req["row_id"],
            "messages": [{"role": "system", "content": SYSTEM_H3},
                         {"role": "user", "content": req["messages"][-1]["content"]}],
            "script": _script_from_prompt(req["messages"][-1]["content"]),
            "ns": {"__name__": "__main__", "__builtins__": __builtins__},
            "ran_script": False,
            "turns": 0,
            "exec_errors": 0,
            "turns_detail": [],
            "answer": None,
        })
    completed = 0
    while active:
        batch = active[:BATCH_SIZE]
        try:
            texts = batch_generate([s["messages"] for s in batch])
        except Exception as exc:  # noqa: BLE001
            print("  h3 batch generate error:", type(exc).__name__, exc, flush=True)
            texts = []
            for s in batch:
                try:
                    texts.append(generate(s["messages"]))
                except Exception as exc2:  # noqa: BLE001
                    texts.append("")
                    print("  h3 generate error:", type(exc2).__name__, exc2, flush=True)
        for s, text in zip(batch, texts):
            s["turns"] += 1
            s["messages"].append({"role": "assistant", "content": text})
            final = extract_final(text)
            if final is not None:
                s["answer"] = final
                continue
            code = extract_code(text)
            if code is None:
                s["turns_detail"].append({"turn": s["turns"], "kind": "no_code", "text": text[:200]})
                s["messages"].append({"role": "user", "content": (
                    "No executable Python code found and no final answer. Write a CadQuery script "
                    "(```python ... ```) that computes the answer, or reply with \"FINAL ANSWER: <value>\".")})
                continue
            output, error = run_cadquery(code, context_script=(s["script"] if not s["ran_script"] else None),
                                          ns=s["ns"])
            s["ran_script"] = True
            s["turns_detail"].append({"turn": s["turns"], "kind": "exec", "error": error,
                                      "code": code[:400], "output": (output or "")[:200]})
            if error:
                s["exec_errors"] += 1
                s["messages"].append({"role": "user", "content": f"Your script raised:\n{error}\n"
                                                                 "Fix the script, or reply with \"FINAL ANSWER: <value>\"."})
            else:
                s["messages"].append({"role": "user", "content": f"Execution output:\n{output}\n"
                                                                 "If this resolves the task, reply with \"FINAL ANSWER: <value>\"; "
                                                                 "otherwise write a corrected script."})
        remaining = []
        for s in active:
            if s["answer"] is None and s["turns"] < MAX_TURNS_H3:
                remaining.append(s)
                continue
            answer = s["answer"]
            if answer is None:
                answer = extract_final(s["messages"][-1]["content"]) or last_line(s["messages"][-1]["content"])
            stats["exec_errors"] += s["exec_errors"]
            stats["turns_used"].append(s["turns"])
            append_result(out, {"row_id": s["row_id"], "answer": answer, "confidence": None,
                                "harness": "h3", "metadata": {"slice": name, "turns": s["turns"],
                                                              "exec_errors": s["exec_errors"],
                                                              "turns_detail": s["turns_detail"]}})
            completed += 1
            if completed % 10 == 0:
                print(f"  h3[{name}] {completed}/{len(rows) - len(done)}", flush=True)
        active = remaining
    n = len(stats["turns_used"])
    print(f"  h3[{name}] stats: exec_error_rows={stats['exec_errors']}, "
          f"avg_turns={sum(stats['turns_used'])/n if n else 0:.1f}", flush=True)
    return out


def main() -> None:
    h1_files = {}
    h3_files = {}
    if RUN_HARNESS1:
        for name in slice_names():
            h1_files[name] = run_harness1(name)
    if RUN_HARNESS3:
        for name in slice_names():
            h3_files[name] = run_harness3(name)
    print("done:", {**{f"h1_{k}": str(v) for k, v in h1_files.items()},
                    **{f"h3_{k}": str(v) for k, v in h3_files.items()}}, flush=True)


# ------------------------------------------------------------------ smoke test
smoke = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Reply with exactly: 42"},
]
_inputs = tokenizer.apply_chat_template(
    _normalize_messages(smoke), tokenize=True, return_dict=True, return_tensors="pt",
    add_generation_prompt=True, enable_thinking=False,
).to(_device())
_ilen = _inputs["input_ids"].shape[-1]
_out = model.generate(**_inputs, max_new_tokens=16, do_sample=False, use_cache=True)
print("smoke reply:", repr(tokenizer.decode(_out[0][_ilen:], skip_special_tokens=True).strip()), flush=True)


if __name__ == "__main__":
    main()
