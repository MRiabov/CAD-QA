# Research notes

**Status:** active, 2026-10-08. External papers, benchmarks, and study notes collected for
related work and citations.

These are secondary notes, not our results. One file per study, named `YYYY-<slug>.md`,
holding the citation, the method, the findings, and why the study matters for CAD-QA. The
project's own findings stay in their home docs (`../prior-art.md`, `../train-and-eval/`,
`../fine-tuning/`); this folder links to them rather than restating them.

## Sourcing standards

Prefer independent research to an interested party. A claim should rest on the strongest
independent reference available, and a reference with a commercial interest in the claim is
treated as weaker evidence and must not be the sole support for a load-bearing claim.

Every reference carries one provenance tag:

| Tag | Meaning |
|---|---|
| `[peer-reviewed]` | published at a peer-reviewed venue |
| `[preprint]` | arXiv or OpenReview without peer review |
| `[workshop]` | workshop paper (lighter review) |
| `[vendor]` | commercial party with an interest in the claim |

Rules: cite the strongest independent reference first; tag every reference; if only a
`[vendor]` reference supports a claim, say so and corroborate with a `[peer-reviewed]` or
`[preprint]` reference where one exists.

The `Ref` column matches the numbered references in `../prior-art.md`.

## Index

| Ref | Provenance | Study | Venue | File | Relevance |
|---|---|---|---|---|---|
| [1] | `[vendor]` | distil labs: 12 small LLM models across 8 fine-tuning tasks | distil labs blog (2025) | `2025-distil-labs-12-small-models-fine-tuning.md` | base rank does not predict fine-tuned rank |
| [2] | `[vendor]` | distil labs: 15 small LLM models across 9 fine-tuning tasks | distil labs blog (2026) | `2026-distil-labs-15-small-models-fine-tuning.md` | Liquid LFM2 tops tunability; Qwen tops tuned |
| [3] | `[vendor]` | distil labs: base vs fine-tuned rank in mid-size MoE LLM models | distil labs blog (2026) | `2026-distil-labs-base-vs-tuned-moe.md` | worst base became most tunable and best tuned |
| [4] | `[vendor]` | distil labs: Qwen vs Llama vs Gemma vs Liquid for tool calling | distil labs learn (2026) | `2026-distil-labs-tool-calling-families.md` | family sets the start, training sets the finish |
| [5] | `[vendor]` | ert.as: Phi-4-Mini vs Gemma 4 vs Qwen3-4B for on-device tool calling | ert.as (2026) | `2026-ertas-on-device-tool-calling.md` | post-fine-tune parity; native function-call tokens |
| [6] | `[workshop]` | Small LLMs for agentic tool calling on OPT-350M | AAAI 2026 workshop (arXiv) | `2026-slm-agentic-tool-calling.md` | targeted single-epoch SFT beats much larger LLM models |
| [7] | `[peer-reviewed]` | RL squeezes, SFT expands | ICLR 2026 (arXiv) | `2026-rl-squeezes-sft-expands.md` | explains the SFT→RL order and RL collapse |
| [8] | `[preprint]` | Learning what to learn: stage-specific data for SFT-then-RL | arXiv (2026) | `2026-learning-what-to-learn.md` | align data difficulty to the stage |
| [9] | `[workshop]` | Privileged on-policy self-distillation harms thinking LLM models | ICML 2026 FoGen workshop | `2026-privileged-on-policy-distillation.md` | copying teacher reasoning suppresses self-correction |
| [10] | `[preprint]` | GeoGramBench: geometric program reasoning in modern LLMs | arXiv (2025) | `2025-geogrambench-program-to-geometry.md` | program-to-geometry reasoning is a hard, unsolved capability |
| [11] | `[preprint]` | QueryCAD: grounded question answering for CAD models | arXiv (2024) | `2024-querycad-cad-question-answering.md` | grounding in executed code; failures are perceptual |
| [12] | `[peer-reviewed]` | NoReGeo: Non-Reasoning Geometry Benchmark | AAAI 2026 | `2026-noregeo-non-reasoning-geometry-benchmark.md` | native geometric understanding; fine-tuning alone does not confer it |
| [13] | `[peer-reviewed]` | Selecting an LLM model to fine-tune via a rectified scaling law | ICML 2024 (arXiv) | `2024-selecting-llm-to-finetune-rectified-scaling-law.md` | size/zero-shot/small-subset tuning do not predict full fine-tuning |
| [14] | `[preprint]` | Where to start? Intermediate models as base LLM models | arXiv (2022) | `2022-where-to-start-intermediate-models.md` | most base LLM models degrade; linear probing ranks them |
| [15] | `[preprint]` | Pre-training indicators and fine-tuning outcomes | arXiv (2025) | `2025-pretraining-indicators-finetuning-outcomes.md` | perplexity is misleading; proxy metrics cut prediction error |
| [16] | `[peer-reviewed]` | Small Models, Big Tasks: small LLM models for function calling | EASE 2025 (ACM) | `2025-small-models-big-tasks-function-calling.md` | fine-tuning works; output-format adherence is the weakness |
| [17] | `[peer-reviewed]` | Berkeley Function Calling Leaderboard (BFCL) | ICML 2025 | `2025-berkeley-function-calling-leaderboard.md` | the academic tool-calling benchmark |
| [18] | `[preprint]` | TinyLLM: small LLM models for agentic tasks on edge devices | arXiv (2025) | `2025-tinyllm-agentic-edge.md` | 1–3B is the useful band; <1B falls off |
