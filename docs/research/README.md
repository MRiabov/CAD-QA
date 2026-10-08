# Research notes

**Status:** active, 2026-10-08. External papers, benchmarks, and study notes collected for
related work and citations.

These are secondary notes, not our results. One file per study, named `YYYY-<slug>.md`,
holding the citation, the method, the findings, and why the study matters for CAD-QA. The
project's own findings stay in their home docs (`../prior-art.md`, `../evaluation/`,
`../fine-tuning/`); this folder links to them rather than restating them.

The `Ref` column matches the numbered references in `../prior-art.md`.

## Index

| Ref | Study | Venue | File | Relevance |
|---|---|---|---|---|
| [1] | distil labs: 12 small LLM models across 8 fine-tuning tasks | distil labs blog (2025) | `2025-distil-labs-12-small-models-fine-tuning.md` | base rank does not predict fine-tuned rank |
| [2] | distil labs: 15 small LLM models across 9 fine-tuning tasks | distil labs blog (2026) | `2026-distil-labs-15-small-models-fine-tuning.md` | Liquid LFM2 tops tunability; Qwen tops tuned |
| [3] | distil labs: base vs fine-tuned rank in mid-size MoE LLM models | distil labs blog (2026) | `2026-distil-labs-base-vs-tuned-moe.md` | worst base became most tunable and best tuned |
| [4] | distil labs: Qwen vs Llama vs Gemma vs Liquid for tool calling | distil labs learn (2026) | `2026-distil-labs-tool-calling-families.md` | family sets the start, training sets the finish |
| [5] | ert.as: Phi-4-Mini vs Gemma 4 vs Qwen3-4B for on-device tool calling | ert.as (2026) | `2026-ertas-on-device-tool-calling.md` | post-fine-tune parity; native function-call tokens |
| [6] | Small LLMs for agentic tool calling on OPT-350M | AAAI 2026 workshop (arXiv) | `2026-slm-agentic-tool-calling.md` | targeted single-epoch SFT beats much larger LLM models |
| [7] | RL squeezes, SFT expands | ICLR 2026 (arXiv) | `2026-rl-squeezes-sft-expands.md` | explains the SFT→RL order and RL collapse |
| [8] | Learning what to learn: stage-specific data for SFT-then-RL | arXiv (2026) | `2026-learning-what-to-learn.md` | align data difficulty to the stage |
| [9] | Privileged on-policy self-distillation harms thinking LLM models | ICML 2026 FoGen workshop | `2026-privileged-on-policy-distillation.md` | copying teacher reasoning suppresses self-correction |
| [10] | GeoGramBench: geometric program reasoning in modern LLMs | arXiv (2025) | `2025-geogrambench-program-to-geometry.md` | program-to-geometry reasoning is a hard, unsolved capability |
| [11] | QueryCAD: grounded question answering for CAD models | arXiv (2024) | `2024-querycad-cad-question-answering.md` | grounding in executed code; failures are perceptual |
| [12] | NoReGeo: Non-Reasoning Geometry Benchmark | AAAI 2026 | `2026-noregeo-non-reasoning-geometry-benchmark.md` | native geometric understanding; fine-tuning alone does not confer it |
