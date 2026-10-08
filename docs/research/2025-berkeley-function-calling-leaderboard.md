# Berkeley Function Calling Leaderboard (BFCL) (2025)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations. Provenance: `[peer-reviewed]` (ICML 2025).

## Citation

Patil, S.G., Mao, H., Ji, C.C.-J., Yan, F., Suresh, V., Stoica, I. and Gonzalez, J.E. (2025)
'The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation of Large
Language Models', *Proceedings of the 42nd International Conference on Machine Learning (ICML)*.
Leaderboard and data: `gorilla.cs.berkeley.edu/leaderboard`.

- Reference: `prior-art.md`, reference [17].

## What it is

The reference benchmark for function/tool calling. BFCL scores an LLM model's ability to call
functions accurately, and has grown from v1 (AST-match evaluation) through v2 (enterprise,
live data), v3 (multi-turn and multi-step), to v4 (holistic agentic evaluation including web
search). It executes the calls and includes relevance detection (withholding a call when no
function fits).

## Findings / scope

- Multiple categories: simple, multiple, parallel, parallel-multiple, multi-turn, relevance
  detection; scored by AST correctness and executability, plus cost and latency.
- It is the benchmark the vendor tool-calling blog posts use, so it gives their numbers a
  shared, auditable basis.

## Why it matters for CAD-QA

A peer-reviewed benchmark to cite when we evaluate tool calling, and a reason to treat vendor
tool-calling numbers as indicative rather than authoritative — the underlying suite is public and
we can run it ourselves.

## Related

- `2025-small-models-big-tasks-function-calling.md`
- `2025-tinyllm-agentic-edge.md`
