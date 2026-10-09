# Research notes

**Status:** active, 2026-10-08. External papers, benchmarks, and study notes collected for
related work and citations.

These are secondary notes, not our results. One file per study, named `YYYY-<slug>.md`,
holding the citation, the method, the findings, and why the study matters for CAD-QA. The
project's own findings stay in their home docs (`../prior-art.md`, `../train-and-eval/`); this
folder links to them rather than restating them.

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
| [8] | `[preprint]` | Learning what to learn: Training-stage-specific data for SFT-then-RL | arXiv (2026) | `2026-learning-what-to-learn.md` | align data difficulty to the Training stage |
| [9] | `[workshop]` | Privileged on-policy self-distillation harms thinking LLM models | ICML 2026 FoGen workshop | `2026-privileged-on-policy-distillation.md` | copying teacher reasoning suppresses self-correction |
| [10] | `[preprint]` | GeoGramBench: geometric program reasoning in modern LLMs | arXiv (2025) | `2025-geogrambench-program-to-geometry.md` | program-to-geometry reasoning is a hard, unsolved capability |
| [11] | `[preprint]` | QueryCAD: grounded question answering for CAD models | arXiv (2024) | `2024-querycad-cad-question-answering.md` | grounding in executed code; failures are perceptual |
| [12] | `[peer-reviewed]` | NoReGeo: Non-Reasoning Geometry Benchmark | AAAI 2026 | `2026-noregeo-non-reasoning-geometry-benchmark.md` | native geometric understanding; fine-tuning alone does not confer it |
| [13] | `[peer-reviewed]` | Selecting an LLM model to fine-tune via a rectified scaling law | ICML 2024 (arXiv) | `2024-selecting-llm-to-finetune-rectified-scaling-law.md` | size/zero-shot/small-subset tuning do not predict full fine-tuning |
| [14] | `[preprint]` | Where to start? Intermediate models as base LLM models | arXiv (2022) | `2022-where-to-start-intermediate-models.md` | most base LLM models degrade; linear probing ranks them |
| [15] | `[preprint]` | Pre-training indicators and fine-tuning outcomes | arXiv (2025) | `2025-pretraining-indicators-finetuning-outcomes.md` | perplexity is misleading; proxy metrics cut prediction error |
| [16] | `[peer-reviewed]` | Small Models, Big Tasks: small LLM models for function calling | EASE 2025 (ACM) | `2025-small-models-big-tasks-function-calling.md` | fine-tuning works; output-format adherence is the weakness |
| [17] | `[peer-reviewed]` | Berkeley Function Calling Leaderboard (BFCL) | ICML 2025 | `2025-berkeley-function-calling-leaderboard.md` | the academic tool-calling benchmark |
| [18] | `[preprint]` | TinyLLM: small LLM models for agentic tasks on edge devices | arXiv (2025) | `2025-tinyllm-agentic-edge.md` | 1–3B is the useful range; <1B falls off |
| [19] | `[preprint]` | SFT vs RL for tool-calling agents, controlled across data/method/scale | arXiv (2026) | `2026-sft-vs-rl-tool-calling.md` | SFT+LoRA strongest; corpus choice matters as much as the method |
| [20] | `[preprint]` | GRPO adds no gain on mastered tasks; gains where reward is reachable by sampling | arXiv (2026) | `2026-grpo-null-web-agent.md` | why the recorded GRPO collapse happened; condition RL on reachability |
| [21] | `[preprint]` | Online difficulty filtering for reasoning-oriented RLVR | arXiv (2025) | `2025-online-difficulty-filtering-rlvr.md` | reward variance = learnability; keep the ~0.25–0.75 RL-eligible pass rate |
| [22] | `[preprint]` | Rollout pass-rate control for binary-reward RL | arXiv (2026) | `2026-rollout-pass-rate-control.md` | 50% pass rate maximizes signal; skewed groups are weak |
| [23] | `[preprint]` | DAPO: decoupled clip and dynamic sampling | arXiv (2025) | `2025-dapo-decoupled-clip-dynamic-sampling.md` | drop all-pass/all-fail groups; entropy and overlong shaping |
| [24] | `[preprint]` | Where the reward scorer fails: category-level audit of RLVR reward signals | arXiv (2026) | `2026-where-the-verifier-fails.md` | scorer self-agreement as low as 53.8%; audit before RL |
| [25] | `[preprint]` | Finetuning with sampling: SFT learns better than you think | arXiv (2026) | `2026-finetuning-with-sampling.md` | sampling SFT can beat on-policy RL on generalization and retention |
| [26] | `[peer-reviewed]` | BREAD: branched rollouts bridge SFT and RL | NeurIPS 2025 | `2025-bread-branched-rollouts.md` | SFT+RL fails when traces are too hard or rewards too sparse |
| [27] | `[workshop]` | Preventing process-reward hacking on verifiable rewards | AAMAS 2026 | `2026-prm-reward-hacking-aamas.md` | dense reward terms are hacked unless optimality-preserving |
| [28] | `[peer-reviewed]` | Detecting and suppressing reward hacking with gradient fingerprints | COLM 2026 | `2026-gradient-fingerprints-reward-hacking.md` | hacking is implicit; detect early, use counterfactuals |
| [29] | `[peer-reviewed]` | Contamination-free evaluation of multi-step function calling (FuncBenchGen) | ICLR 2026 | `2025-contamination-free-function-calling-eval.md` | tool-call benchmarks/corpora are contamination-prone; use train-disjoint eval |
| [30] | `[preprint]` | Scaling environments for LLM agents: a survey | arXiv (2025) | `2025-scaling-environments-llm-agents.md` | environments are the central object; RL needs verifiable interactive experience |
| [31] | `[preprint]` | RLVE: scaling RL with adaptive verifiable environments | arXiv (2025) | `2025-rlve-adaptive-verifiable-environments.md` | environment count, not data volume, drives generalizable reasoning |
| [32] | `[preprint]` | Warm-start then RL on synthesized terminal tasks | arXiv (2026) | `2026-endless-terminals-warm-start.md` | SFT is a readiness check; RL cold-start barely moves a small LLM model |
| [33] | `[preprint]` | BenchCAD: programmatic CAD benchmark and its Code QA overlap | arXiv (2026) | `2026-benchcad.md` | Code QA overlaps CAD-QA; generation tasks saturating, comprehension gap narrowing |
| — | `[vendor]` | liquid-finetune: evaluation, async eval, rollouts | GitHub README (2026) | `2026-liquid-finetune.md` | `evals:` + custom metrics; async eval without blocking training; vLLM rollouts |
| — | `[vendor]` | LFM2.5-DSpark: separate draft speculator for speculative decoding | Liquid AI blog / vLLM docs (2026) | `2026-lfm2.5-dspark.md` | no built-in MTP; spec decode is lossless and serving-only |