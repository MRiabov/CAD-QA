# NoReGeo: Non-Reasoning Geometry Benchmark (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

```bibtex
@inproceedings{abdullaeva2026noregeo,
  title     = {NoReGeo: Non-Reasoning Geometry Benchmark},
  author    = {Abdullaeva, Irina and Vasiliuk, Anton and Goncharova, Elizaveta and
               Rahmatullaev, Temurbek and Ivan, Zagorulko and Kurkin, Maxim and
               Kuznetsov, Andrey},
  booktitle = {Proceedings of the AAAI Conference on Artificial Intelligence},
  volume    = {40},
  number    = {23},
  pages     = {18901--18909},
  year      = {2026},
  doi       = {10.1609/aaai.v40i23.38960}
}
```

- Venue: AAAI-26, Technical Track on Knowledge Representation and Reasoning.
- Identifiers: `doi.org/10.1609/aaai.v40i23.38960`; `arxiv.org/abs/2601.10254` (15 Jan 2026).
- Code: `github.com/FusionBrainLab/NoReGeo`.
- Affiliations: FusionBrain Lab, Innopolis University, HSE University, Lomonosov Moscow State
  University, Central University, Applied AI Institute (Moscow).

## What it is

NoReGeo tests whether LLM models and VLMs have *native* geometric understanding — the ability
to read spatial relations and geometric properties directly, without chain-of-thought or
algebra. It is the deliberate complement of reasoning-heavy geometry benchmarks: it asks for
single-step, school-level judgements (midpoints, area comparisons, collinearity, symmetry,
basic coordinates, circle properties) that a human answers by intuition.

## Method

- 2,500 problems across 25 categories, grouped into three task classes: classification
  (multiple choice), numeric (a value), and unstable (under-specified).
- Every problem is supplied in three formats: text only, text plus a dotted image (points
  only), and text plus a full image (points and connecting lines), so text-only LLM models
  and VLMs can be compared under one output contract.
- Direct-answer only: structured JSON output enforced by constrained decoding (Outlines and
  xgrammar), served with vLLM, with no chain-of-thought.
- 45+ frontier and open-source LLM models and VLMs evaluated; humans score ~74.5% on the same
  multiple-choice tasks.

## Findings

- Best proprietary LLM model ~65%; best open-source VLM ~55% (Phi3.5-Vision); all below the
  ~74.5% human level.
- Fine-tuning alone does **not** confer geometric competence.
- A frozen vision encoder plus a simple linear probe solves the tasks almost perfectly:
  geometric features exist in visual embeddings but current LLM architectures and training
  regimes do not access them.
- Full visual context strongly boosts VLMs versus text-only or dotted images; math-specialised
  text-only LLM models degrade instruction-following and misformat structured output.
- High variance across categories.

## Why it matters for CAD-QA

- Direct evidence that geometric understanding is a distinct, weak capability, and that it is
  not created by ordinary fine-tuning — relevant to CAD-QA's difficulty and to the
  "fine-tuning without gain" question.
- It sharpens the boundary with GeoGramBench: GeoGramBench tests program-to-geometry
  *reasoning*; NoReGeo strips reasoning away and tests perception. CAD-QA sits mostly on the
  reasoning side, so NoReGeo is a caution rather than a direct ceiling: if a capability is
  absent, supervised imitation is unlikely to install it.
- Its linear-probe result (frozen encoder) is a reminder that a representation may contain the
  signal while the policy does not use it — an argument for representation-aware methods over
  pure output imitation.

## Related

- GeoGramBench: program-to-geometry reasoning (`arxiv.org/abs/2505.17653`).
- QueryCAD: grounded question answering over CAD models.
- The small-LLM-model fine-tuning evidence in `../prior-art.md`.
