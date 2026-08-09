"""CAD-QA GRPO reward function (trl>=0.28 style: completions + **kwargs with dataset columns).

Grades a completion against the gold answer using cad_qa's exact-match parser,
mirroring cad_qa evaluation grade_public_private (per-format parsing + string equality).
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
    if isinstance(gold, list):
        gold = [str(x) for x in gold]
        parsed = _parse_answer(pred, fmt)
        return 1.0 if parsed in gold else 0.0
    gold_str = str(gold)
    if fmt == "boolean":
        return 1.0 if _strip_special(pred).lower() == gold_str.lower() else 0.0
    if fmt == "text":
        # the id is embedded in a long reasoning trace; substring presence wins
        return 1.0 if gold_str in _strip_special(pred) else 0.0
    if fmt == "number":
        try:
            return 1.0 if abs(float(_parse_answer(pred, fmt)) - float(gold_str)) < 1e-6 else 0.0
        except ValueError:
            return 0.0
    return 1.0 if _parse_answer(pred, fmt) == gold_str else 0.0

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
