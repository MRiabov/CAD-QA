# External transfer evaluation — H3 (stub)

Date: 2026-10-09 · Status: planned (not run)

## Purpose

Test whether graph-derived CAD-QA supervision transfers to existing, credible external benchmarks
(H3). Means target: BenchCAD `qa_code`. End/defect: BenchCAD `edit_code`, `Text2CAD-Bench`. Owned
with `../train-and-eval/evaluation/plan.md` §5.1 (D-E5).

## Hypothesis

H3: training on `learn_the_cadqa_task` raises BenchCAD `qa_code` accuracy beyond the Base, format-only, and
answer-only controls, without a regression on the `preserve_general_math_and_code_reasoning` evaluation
dataset.

H4 (means → end): the CAD-QA pass rate predicts the external score (dose-response), at fixed recipe
and matched compute, with the `preserve_general_math_and_code_reasoning` evaluation dataset as covariate.

## Targets

- **Means (P0) — BenchCAD `qa_code`:** official full split and metric.
- **End (P1) — BenchCAD `edit_code` T4/T5; `Text2CAD-Bench` (arXiv:2605.18430):** text → CadQuery.
- **Defect (P1) — `Text2CAD-Bench` Invalidity Rate; BenchCAD `exec%`.**
- **Not targets:** Vision2Code, Vision QA, BenchCAD 2.0 assembly/PCB; `CADBench`, `cadrille`,
  `CAD-Recode` (need a multimodal LLM model); `MechReason`, `CADWorld` (wrong modality).

## Rules

- Official full split and official metric; no subset-shopping.
- Freshness: re-run the current frontier before quoting `GeoGramBench` or `QueryCAD` gaps.

## Arms

Hold base and recipe fixed; vary only training data.

| Arm | Training data | Isolates |
|---|---|---|
| Base | none | floor; pretraining-contamination proxy |
| Format-only | `emit_our_tool_call_format` + the general tasks | H1 format compliance |
| Answer-only | CAD-QA answers, no reasoning | supervision format vs reasoning content |
| CAD-QA reasoning | `learn_the_cadqa_task` | H2 capability |
| Full primary (optional) | the full Mixed training dataset | external reasoning support |

## Preconditions

- Reachability pilot: the base LLM model must be low-but-nonzero on the subset (zero yields no
  signal; high means saturated).
- Format-adaptation control: BenchCAD wants a JSON array of numbers; report invalid-output rate.
- Contamination audit: exclude every BenchCAD family from every training arm; dedup CAD-QA programs
  against BenchCAD.
- Freeze the subset, seed, and scorer before running.

## Commands / artifacts

- (fill in) subset manifest; arm configs; run manifests; scored results; the evaluator command.

## Results

(pending)

## Notes

Peer-review gate: no gain on a credible external benchmark means the "dataset improves models"
claim rests on an internal split and does not stand.
