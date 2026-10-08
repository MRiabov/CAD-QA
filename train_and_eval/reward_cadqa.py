"""CAD-QA GRPO reward function (trl>=0.28 style: completions + **kwargs with dataset columns).

Grades a completion against the gold answer using the dataset's exact-match parser,
mirroring the train_and_eval grading grade_public_private (per-format parsing + string equality).
Batch API: reward_cadqa(completions, gold_answer=[...], answer_format=[...], ...) -> list[float].
"""
import json
import re

def _strip_special(text: str) -> str:
    return re.sub(r"<\|?[a-z_]*\|?>", "", text).strip()

def _parse_answer(text: str, fmt: str):
    t = _strip_special(text)
    if fmt == "candidate_label":
        return t
    if fmt == "boolean":
        return t
    if fmt == "text":
        # entity ids appear inside reasoning; extract any token-ish id from the tail
        return t
    if fmt in ("number", "integer"):
        m = re.search(r"-?\d+(?:\.\d+)?", t)
        return m.group(0) if m else ""
    if fmt == "json":
        # extract first {...} block
        m = re.search(r"\{.*\}", t, re.DOTALL)
        return m.group(0) if m else ""
    if fmt == "coordinate":
        m = re.search(r"[-+]?\d*\.?\d+\s*,\s*[-+]?\d*\.?\d+", t)
        return m.group(0) if m else ""
    if fmt == "bbox":
        m = re.search(r"\[[^\]]*\]", t)
        return m.group(0) if m else ""
    return t

def _decode_gold(gold_raw: str):
    """HF dataset stores gold_answer as a JSON string of a JSON string; decode robustly."""
    g = gold_raw
    for _ in range(2):
        if not isinstance(g, str):
            break
        try:
            g = json.loads(g)
        except (json.JSONDecodeError, TypeError):
            break
    return g

def _reward_one(pred: str, gold: object, fmt: str) -> float:
    tool_reward = _tool_call_reward(pred, gold, fmt)
    if tool_reward is not None:
        return tool_reward
    if isinstance(gold, list):
        gold = [str(x) for x in gold]
        parsed = _parse_answer(pred, fmt)
        return 1.0 if parsed in gold else 0.0
    gold_str = str(gold)
    if fmt == "boolean":
        return 1.0 if _strip_special(pred).lower() == gold_str.lower() else 0.0
    if fmt == "text":
        # the id is embedded in a long agent training trace; substring presence wins
        return 1.0 if gold_str in _strip_special(pred) else 0.0
    if fmt == "number":
        try:
            return 1.0 if abs(float(_parse_answer(pred, fmt)) - float(gold_str)) < 1e-6 else 0.0
        except ValueError:
            return 0.0
    return 1.0 if _parse_answer(pred, fmt) == gold_str else 0.0


_NATIVE_CALL_RE = re.compile(r"<\|tool_call>call:(\w+)(\{.*?\})<tool_call\|>", re.DOTALL)


def _normalize_native_args(args_raw: str) -> str:
    """Turn gemma's native arg encoding into parseable JSON.

    gemma-4-E2B emits args like `{label:<|"|>A<|"|>}` (strings wrapped in
    `<|"|>`, keys unquoted); `processor.parse_response` decodes this in eval,
    but the reward has no processor, so normalize before json.loads.
    """
    s = args_raw.replace("<|\"|>", "\"")
    s = re.sub(r"([{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', s)
    return s


def _native_tool_call(text: str):
    """Parse the LAST native <|tool_call|> block without a processor.

    Returns (ToolName, typed-args) or None. Mirrors eval_bench's
    parse_native_tool_call but grades pure-JSON args directly; gemma's
    `<|"|>`-encoded strings are normalized before json.loads.
    """
    from tool_calls import _ARGS_MODELS, ToolName  # lazy: tool_calls imports reward_cadqa at module load

    blocks = list(_NATIVE_CALL_RE.finditer(text))
    if not blocks:
        return None
    block = blocks[-1]
    name_raw, args_raw = block.group(1), block.group(2)
    try:
        name = ToolName(name_raw)
        args = json.loads(_normalize_native_args(args_raw))
    except (ValueError, json.JSONDecodeError):
        return None
    model = _ARGS_MODELS.get(name)
    if model is None or not isinstance(args, dict):
        return None
    try:
        return name, model.model_validate(args)
    except Exception:  # noqa: BLE001 - malformed args -> no reward
        return None


def _tool_call_reward(pred: str, gold: object, fmt: str) -> float | None:
    """Grade a tool-call completion via the tool contract; None if not a tool call."""
    from tool_calls import extract_tool_call, format_to_tool, tool_call_matches  # lazy import (module cycle)

    try:
        expected = format_to_tool(fmt)
    except ValueError:
        return None
    parsed = _native_tool_call(pred) or extract_tool_call(pred, expected)
    if parsed is None:
        return None
    name, args = parsed
    return 1.0 if tool_call_matches(name, args, gold, fmt) else 0.0

def reward_cadqa(completions, **kwargs) -> list[float]:
    golds = kwargs.get("gold_answer")
    fmts = kwargs.get("answer_format")
    scores = []
    for i, comp in enumerate(completions):
        text = comp[0]["content"] if isinstance(comp, list) else comp["content"]
        gold = _decode_gold(golds[i]) if golds is not None else None
        fmt = fmts[i] if fmts is not None else "text"
        scores.append(_reward_one(text, gold, fmt))
    return scores
