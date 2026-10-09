# QueryCAD: grounded question answering for CAD models (2024)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

Kienle, C. et al. (2024) 'QueryCAD: Grounded Question Answering for CAD Models', arXiv preprint
arXiv:2409.08704. Available at: `arxiv.org/abs/2409.08704`. Project page:
`claudius-kienle.github.io/querycad`.

- Reference: `prior-art.md`, reference [11].

## What it is

A system and benchmark for extracting precise measurements from CAD models using natural-language
questions. A code-writing LLM model generates Python that calls a CAD-shaped API; part selection
is grounded by SegCAD, an open-vocabulary multi-view instance-segmentation network. The authors
also release a 111-question CAD question-answering benchmark.

## Findings

- On 111 questions, GPT-4o answered 44 correctly, 15 partially, and 52 incorrectly.
- Of the 67 non-correct cases, 52 were segmentation-mask errors (the wrong part was returned),
  14 were CAD-interface limitations, and only 1 was a reasoning/hallucination error.
- The prompt deliberately forces all metric conversion and reasoning into executed Python; the
  authors report this reduces hallucination, especially for smaller LLM models such as Llama
  3.1 8B.
- Larger LLM models (GPT-4o, Llama 3.1 405B) outperform smaller open LLM models on the same
  benchmark.

## Staleness (2026-10-09)

The GPT-4o 44/111 figure is from 2024, and the benchmark itself predates GeoGramBench. Frontier
capability moved sharply since — BenchCAD Vision2Code rose from about 0.3 to 0.95+ in roughly six
months — so any saturation statement here is `[stale — verify or drop]`: re-run the current frontier
before using QueryCAD as a transfer target (`plans/oct-8/evaluation-plan.md` §5.1).

## Why it matters for CAD-QA

The nearest published CAD question-answering prior art. Two lessons: grounding the LLM model in
executed code/measurements is what makes CAD QA tractable, and the dominant failure is
perception/grounding (part selection), not reasoning. That aligns with CAD-QA's `numpy` harness
and with NoReGeo's perception-vs-reasoning split, and it warns that small LLM models need the
grounded tool surface to compete.

## Related

- `2026-noregeo-non-reasoning-geometry-benchmark.md`
- `2025-geogrambench-program-to-geometry.md`
