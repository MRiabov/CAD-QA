# Towards contamination-free evaluation of multi-step function calling (2025)

**Status:** external study note, not our result. Added 2026-10-08 to support the contamination
caveat on the SFT-vs-RL tool-calling study [19].

## Citation

'Towards Reliable Benchmarking: A Contamination Free, Controllable Evaluation Framework for
Multi-step LLM Function Calling' (2025), arXiv:2509.26553; ICLR 2026.
Available at: `arxiv.org/html/2509.26553v2`. (Author list not captured at survey time.)

- Reference: `prior-art.md`, reference [29].
- Provenance: `[peer-reviewed]`.

## What it is

FuncBenchGen: a contamination-free, difficulty-controllable framework that models multi-step
function calling as a DAG-traversal task, generating synthetic tool-use problems with configurable
graph size, dependency depth, and distractor functions.

## Findings

- Existing tool-calling benchmarks (API-Bank, BFCLv4, ToolBench) are **vulnerable to data
  contamination** — their question/answer pairs can be leaked in pretraining or via test-time web
  search — so scores on them are unreliable.
- Synthetic, generated tasks avoid leakage and give fine-grained difficulty control.
- Applied to seven LLM models, it exposes failure modes of reasoning models under long call chains
  and connected distractor functions.

## Why it matters for CAD-QA

- It confirms, at `[peer-reviewed]` level, that tool-calling **benchmark and corpus contamination
  is a recognized problem** — exactly the concern raised about [19], where the Qwen3 base likely
  saw the public training corpora (`xLAM`, `ToolACE`, `Glaive`).
- Design principle for our canaries: a **train-disjoint, ideally generated** evaluation set is what
  makes a tool-format number interpretable; reusing a public corpus the base may have seen does not.
- CAD-QA's own task evaluation (internal) is naturally contamination-free; the risk is the external
  format canary (`tool_valid`), which should use disjoint sources or our own `submit_*` rows.

## Related

- `2026-sft-vs-rl-tool-calling.md`
- `2025-berkeley-function-calling-leaderboard.md`
