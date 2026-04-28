# CAD-QA: A Trace-Derived Benchmark for CAD Program Reasoning

## Abstract

Language models increasingly generate CAD scripts, yet they often fail to
mentally execute the geometry implied by those scripts. CAD-QA is a
code-only benchmark for closed-book reasoning over executable CadQuery
construction programs. The benchmark asks models to answer structured questions
about operation order, selector semantics, bounding boxes, signed volume
changes, topology counts, point membership, and conservative feature
provenance. Rows are derived from normalized source programs, static operation
graphs, isolated CadQuery traces when available, split-safe manifests, and
deterministic answer parsers. In the current implementation, smoke and
release-candidate probes validate the generation, schema, leakage audit, and
baseline pipeline; release-scale model numbers remain `[RESULT: pending]`.
CAD-QA is intended to measure whether models internalize CAD program semantics
without calling a CAD kernel at evaluation time.

## Introduction

CAD assistance requires more than producing plausible code. A useful design
model must understand how operations compose, how selectors bind to topology,
how workplanes and coordinate frames evolve, and how edits affect downstream
geometry. These requirements expose a gap between syntactic code fluency and
geometric reasoning: a model can write a CadQuery script that looks reasonable
while still misunderstanding which face is selected, whether a point is inside
the final solid, or how many topology entities remain after a cut.

CAD-QA frames this gap as controlled CAD program reasoning. Given one CadQuery
script, the model answers a structured question without running CadQuery. This
setting isolates the model's internal understanding of the construction history
and generated geometry. Tool-using CAD agents remain important, but closed-book
reasoning is a distinct capability: it supports planning, debugging,
explanation, and training-time supervision when a kernel is unavailable,
expensive, or intentionally withheld.

The benchmark design follows three constraints. First, source rows should come
from executable CAD programs rather than isolated trivia. Second, labels should
be trace-derived or statically derived with explicit label policy, so that
evaluation is reproducible. Third, public evaluation should use structured
answers and deterministic parsers rather than natural-language judgment.

## Related Work

CAD-QA is positioned between code reasoning, CAD program synthesis, geometric
learning, and tool-use evaluation.

Program reasoning benchmarks test whether models can infer the behavior of
code without executing it. CAD-QA shares that goal but adds geometric and
topological state that is not visible in ordinary text traces.

CAD synthesis systems evaluate whether generated code or geometry matches a
target. CAD-QA instead evaluates diagnostic understanding of a given program:
operation counts, intermediate states, selector results, topology, point
membership, and provenance.

Geometry and shape benchmarks often operate on meshes, point clouds, images,
or final solids. CAD-QA keeps the construction program as the primary object so
questions can target history, edit locality, and feature semantics.

Tool-use benchmarks measure whether a model can call an external solver. CAD-QA
defaults to a closed-book setting and treats tool-assisted evaluation as a
separate upper-bound regime.

Citation placeholders: `[CITE: code reasoning]`, `[CITE: CAD synthesis]`,
`[CITE: CADEvolve]`, `[CITE: geometric learning]`, `[CITE: tool use]`.

## Dataset Construction

The pipeline ingests CADEvolve-style CadQuery programs and synthetic smoke
fixtures. Synthetic rows are reserved for golden validation and edge cases; the
intended release rows are CADEvolve-derived. Each source record stores a source
identifier, normalized code, source grouping metadata when available, and
stable hashes.

The generator extracts an AST-backed operation graph from each script. When
CadQuery execution is enabled, an isolated worker executes the source with a
timeout and records scalar snapshots after supported steps. Snapshots include
bounding boxes, volume, center, topology counts, optional selector count
tables, sampled point membership queries, conservative provenance records, and
best-effort per-snapshot entity identifiers. Failures are kept in
`failure_manifest.jsonl` rather than silently dropped.

Public rows are materialized from the source and trace records, assigned to
group-safe splits, validated against the public schema, and exported as JSONL
with optional Parquet. Split manifests and leakage audits are release
artifacts. Manual audit samples, failure taxonomy reports, reproducibility
reports, and dataset cards are generated from the same export directory.

Release statistics should be filled from the release artifact:
`[TABLE: dataset row counts by split and task]`,
`[TABLE: trace failures by category]`,
`[RESULT: source count]`, `[RESULT: public row count]`.

## Task Families

CAD-QA currently implements these public task families:

| Task family | Answer type | Signal |
| --- | --- | --- |
| `operation_count` | integer | Static CadQuery syntax and construction ordering. |
| `selector_count` | integer | Selector semantics when selector traces exist. |
| `bbox_after_step` | bbox JSON | Intermediate geometric state. |
| `signed_volume_delta` | number | Additive and subtractive operation effects. |
| `topology_count_after_step` | integer | Face, edge, vertex, and solid counts. |
| `point_membership` | enum | Inside, outside, boundary, or ambiguous classification. |
| `feature_provenance_choice` | choice | Conservative source feature attribution. |

The answer contract is intentionally structured. Integers must parse as
non-negative integers, numeric answers use finite values with task-specific
tolerances, bounding boxes use JSON with `min` and `max` vectors, and choices
must match the row choices unless the label policy marks provenance as
ambiguous or merged.

Counterfactual source generation is implemented for grouped numeric parameter
variants, but verified counterfactual public labels are not yet part of the
benchmark release. CADEditQA tasks are planned as sibling edit-verification
tasks over the same shared sources and traces.

## Experiments

The evaluation protocol reports exact structured-answer accuracy and invalid
output rate. Results must be broken down by split and task family. Baselines
include majority, random, static operation-count, regex operation-count,
selector heuristic, and oracle systems. Closed-book LLM requests can be
exported in zero-shot and few-shot forms; answer-only SFT data can be prepared
from the same dataset export.

Current local artifacts include smoke validation, release-candidate generation
probes, baseline metrics, SFT data preparation, and experiment comparison
tables. Full model results are gated on release-scale generation, GPU
availability, provider/runtime setup, and final audit completion.

Required final tables:

- `[TABLE: headline baseline and model comparison]`
- `[TABLE: per-task accuracy and invalid output rate]`
- `[TABLE: per-split generalization]`
- `[TABLE: failure-case taxonomy]`
- `[TABLE: ablations for zero-shot, few-shot, and SFT when available]`

## Discussion And Limitations

CAD-QA's central benefit is controlled supervision over CAD program semantics.
The benchmark separates static code comprehension from geometry and topology
reasoning, exposes invalid answer formats, and keeps label policy visible.
Because public rows are code-plus-label, evaluation does not require shipping
OpenCascade artifacts or asking every benchmark user to run CadQuery.

The current implementation still has important limits. Feature provenance is
conservative rather than exact OpenCascade builder-history provenance.
Adjacent topology matching is best-effort and intentionally bounded for large
snapshots. Selector coverage depends on selectors appearing in traced source
programs. Kernel-sensitive labels require environment metadata and release
audits. Counterfactual public labels and CADEditQA verifier rows remain open.

The paper should not claim solved CAD reasoning. It should claim a reproducible
benchmark and pipeline for measuring specific CAD reasoning abilities, with
transparent failures and room for tool-assisted upper bounds.

## Conclusion

CAD-QA turns executable CadQuery programs into structured questions about CAD
construction history, geometry, topology, selectors, point membership, and
provenance. The benchmark is designed for closed-book evaluation, deterministic
parsing, split hygiene, and trace-derived labels. The current repository
implements the pipeline needed to generate, validate, audit, and compare
baseline results. Final paper claims should be filled only after release-scale
generation, audits, and model evaluations are complete.
