# GeoGramBench: geometric program reasoning in modern LLMs (2025)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

Luo, S., Zhu, Z., Yuan, Y., Yang, Y., Shan, L. and Wu, Y. (2025) 'GeoGramBench: Benchmarking
the Geometric Program Reasoning in Modern LLMs', arXiv preprint arXiv:2505.17653. Available at:
`arxiv.org/abs/2505.17653`.

- Reference: `prior-art.md`, reference [10].

## What it is

A benchmark for the **Program-to-Geometry** task: translating procedural drawing code into
accurate spatial reasoning. 500 problems organized by geometric complexity, not by reasoning
step count, across three levels:

1. Primitive Recognition.
2. Local Relation Composition.
3. Global Abstract Integration.

## Findings

- 17 frontier LLM models evaluated. Even reasoning-oriented LLM models (for example o1) score
  below **50%** at the highest abstraction level.
- Accuracy falls as structural complexity rises; chain-of-thought did not help and, in the
  authors' analysis, showed a downward trend with complexity.
- Models parse local geometry but fail to synthesize globally consistent spatial structures —
  the authors call this the key research frontier.

## Staleness (2026-10-09)

The "below 50%" frontier figure is from May 2025. Frontier capability moved sharply since — BenchCAD
Vision2Code rose from about 0.3 to 0.95+ in roughly six months — so the gap is
`[stale — verify or drop]`: re-run the current frontier on the 500 problems before using
GeoGramBench as a transfer target (`../train-and-eval/evaluation/plan.md` §5.1).

## Why it matters for CAD-QA

The closest published analogue to CAD-QA's core capability. It is evidence that
program-driven spatial reasoning is a genuine weakness of current LLM models, so a 2–4B base is
fighting a capability ceiling on the hard slice — "little gain" may be the task, not the tuning.
It also argues the gold signal should reward *compositional* spatial integration, not single-step
recognition.

## Related

- `2026-noregeo-non-reasoning-geometry-benchmark.md`
- `2024-querycad-cad-question-answering.md`
