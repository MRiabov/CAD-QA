# TinyLLM: small LLM models for agentic tasks on edge devices (2025)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations. Provenance: `[preprint]` (arXiv).

## Citation

Haque, M.A., Rahman, F., Gupta, K.D., Shujaee, K. and George, R. (2025) 'TinyLLM: Evaluation and
Optimization of Small Language Models for Agentic Tasks on Edge Devices', arXiv preprint
arXiv:2511.22138. Available at: `arxiv.org/abs/2511.22138`.

- Reference: `prior-art.md`, reference [18].

## What it is

An evaluation and optimization study of small LLM models for agentic function/tool calling on
edge devices, using the BFCL framework. It covers supervised fine-tuning, parameter-efficient
fine-tuning, RL optimization, DPO preference alignment, and hybrid methods across TinyAgent,
TinyLlama, Qwen, and xLAM.

## Findings

- Medium-sized LLM models (1–3B) clearly outperform ultra-compact ones (<1B), reaching up to
  65.74% overall and 55.62% multi-turn accuracy with hybrid optimization.
- xLAM-2-3B-fc-r leads its set; Qwen3-4B is close; multi-turn accuracy degrades sharply for the
  smallest LLM models.
- Combines several optimization strategies and reports per-category BFCL results.

## Why it matters for CAD-QA

Academic evidence for the useful size band: below ~1B the capability falls off, while 1–3B is
competitive on tool calling. Useful when deciding whether a very small base is worth trying, and
it confirms multi-turn/tool formatting as the hard part rather than single-call mapping.

## Related

- `2025-small-models-big-tasks-function-calling.md`
- `2025-berkeley-function-calling-leaderboard.md`
