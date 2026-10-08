# Small Models, Big Tasks: small LLM models for function calling (2025)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations. Provenance: `[peer-reviewed]` (EASE 2025).

## Citation

Kavathekar, I., Donakanti, R., Kumaraguru, P. and Vaidhyanathan, K. (2025) 'Small Models, Big
Tasks: An Exploratory Empirical Study on Small Language Models for Function Calling',
*Proceedings of the 29th International Conference on Evaluation and Assessment in Software
Engineering (EASE 2025)*, AI Models and Data Evaluation track. doi: `10.1145/3756681.3757001`.
arXiv preprint arXiv:2504.19277. Available at: `arxiv.org/abs/2504.19277`.

- Reference: `prior-art.md`, reference [16].

## What it is

A peer-reviewed empirical study of small LLM models for generating function calls, across
domains, using zero-shot, few-shot, and fine-tuning, with and without prompt injection. It also
measures edge-device latency and memory, and releases the fine-tuned LLM models.

## Findings

- Small LLM models improve from zero-shot to few-shot and **perform best with fine-tuning**.
- Their main weakness is **adhering to the required output format** — the exact failure our
  submit-tool contract must guard against.
- The study reports edge latency/memory trade-offs and releases fine-tuned students for reuse.

## Why it matters for CAD-QA

Peer-reviewed support that small open LLM models can be made effective for tool calling by
fine-tuning, provided the format contract is enforced. It is the academic counterpart to the
vendor tool-calling benchmarks, and it flags output-format adherence (not raw capability) as the
recurring small-LLM-model failure.

## Related

- `2025-berkeley-function-calling-leaderboard.md`
- `2025-tinyllm-agentic-edge.md`
