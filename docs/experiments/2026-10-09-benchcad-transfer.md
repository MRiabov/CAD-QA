# BenchCAD transfer evaluation — H3 (stub)

Date: 2026-10-09 · Status: planned (not run)

## Purpose

Test whether graph-derived CAD-QA supervision transfers to an independent, credible CAD benchmark
(H3). Primary target: BenchCAD `qa_code`. Secondary: BenchCAD `edit_code` T4/T5. Owned with
`../../plans/oct-8/evaluation-plan.md` §5.1 (D-E5).

## Hypothesis

H3: training on `cadqa_hop` raises BenchCAD `qa_code` accuracy beyond the Base, format-only, and
answer-only controls, without a general-canary regression.

## Targets

- **Primary — BenchCAD `qa_code`:** CadQuery program + numeric question → number; family-disjoint
  subset; read on the Spatial Reasoning axis.
- **Secondary — BenchCAD `edit_code` T4/T5:** instruction + program → edited program.
- **Not targets:** Vision2Code, Vision QA, BenchCAD 2.0 assembly/PCB (image/drawing-in, generation,
  agentic).

## Arms

Hold base and recipe fixed; vary only training data.

| Arm | Training data | Isolates |
|---|---|---|
| Base | none | floor; pretraining-contamination proxy |
| Format-only | `format_tool` + `rehearsal` | H1 format compliance |
| Answer-only | CAD-QA answers, no reasoning | supervision format vs reasoning content |
| CAD-QA reasoning | `cadqa_hop` | H2 capability |
| Mix-full (optional) | full primary mix | external reasoning support |

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
