# CAD-QA Paper Specification

This document captures the research narrative for making CAD-QA the
BrowseComp-style benchmark for CAD program reasoning. The implementation specs
must align with this frame: one typed CAD ontology graph, one deterministic
query/verifier path, and public rows grouped by hop count and relation/metric
families.

## 1. Core Claim

CAD-QA is the BrowseComp of CAD. BrowseComp tests whether browsing agents can
persist through entangled, hard-to-find evidence and return a short verifiable
answer. CAD-QA tests whether CAD agents can persist through entangled CadQuery
program evidence and return a short verifier-backed answer without running a
CAD kernel at evaluation time.

The central question is:

> Given a CadQuery script, can a model reduce uncertainty over the implied CAD
> ontology graph and recover the unique verifier-backed answer?

Low-hop diagnostics, graph-specific rows, and high-hop checklist rows are
hop-count and difficulty slices of the same system:

- 0 hops: direct source or statistic lookup;
- 1 hop: resolve one entity and read one metric;
- 2 hops: traverse one relation and read or compare a metric;
- 3+ hops: BrowseComp-style CAD rows with obfuscated, distractor-rich clues.

## 2. Paper Positioning

The paper should argue that CAD agents need a benchmark for uncertainty
reduction over program-derived geometry, not merely final-shape similarity or
code fluency. The benchmark measures whether models understand:

| Capability | Why it matters |
| --- | --- |
| Operation order | Determines construction history and edit locality. |
| Selector semantics | CadQuery modeling heavily depends on selector binding. |
| Workplane frames | Many CAD bugs are coordinate-frame mistakes. |
| Profile geometry | Sketches are the source of many downstream solids and cuts. |
| Volume, bounding boxes, and centroids | Basic quantitative geometry reasoning. |
| Topology counts and deltas | Faces, edges, vertices, holes, and loops affect manufacturability. |
| Paths and tangents | Sweep and trajectory features require non-local geometric reasoning. |
| Material and void regions | Editing requires knowing what was added or removed. |
| Feature provenance | Explanations and edits need operation-to-geometry attribution. |
| Validity and failure modes | Useful agents must anticipate invalid operations. |

The strongest eventual claim is that trace-derived CAD-QA training improves CAD
editing, debugging, and planning because it supervises the reasoning path from
source code to geometric effect.

## 3. Unified Graph-First Pipeline

The canonical pipeline is:

```text
CadQuery source
-> source normalization
-> trace/snapshot extraction
-> typed CAD ontology graph
-> deterministic query program
-> verifier-backed answer
-> rule-based public prompt renderer
-> public rows grouped by hop count and relation/metric families
```

The paper should emphasize that public prompts are not LLM-translated
questions. They are rule-rendered from hidden query programs. Every clue maps
to a hidden clause, and every row carries a candidate-set trace plus a
reject-unless-unique verifier decision.

LLM calls, if any, are optional external evaluation or wording experiments.
They are not trusted generation or grading.

## 4. CAD Ontology Vocabulary

The benchmark should start small but use the right ontology shape from the
beginning.

Node families:

- `source`;
- `feature`;
- `operation`;
- `parameter`;
- `workplane`;
- `sketch`;
- `profile`;
- `solid`;
- `face`;
- `edge`;
- `vertex`;
- `axis`;
- `direction`;
- `point`;
- `centroid`;
- `centerline`;
- `path`;
- `material_region`;
- `void_region`;
- `selector`;
- `measurement`.

Relation families:

- temporal and dataflow: `before`, `after`, `input_to`, `combines`;
- provenance: `created_by`, `modified_by`, `deleted_by`, `adds_material_to`,
  `removes_material_from`;
- construction links: `uses_profile`, `used_by`, `parameter_of`,
  `selected_by`, `located_on`, `bounded_by`;
- measurements: `has_measurement`, `has_centroid`, `has_coordinate`,
  `has_normal`;
- geometry relations: `distance_to`, `nearest_tangent_to`, `parallel_to`,
  `not_parallel_to`, `perpendicular_to`, `orthogonal_to`, `coaxial_with`,
  `adjacent_to`, `opposite_to`, `contained_in`, `intersects`.

Measurement scopes:

- `profile_intrinsic`;
- `feature_application_effect`;
- `entity_geometry`;
- `snapshot_state`;
- `relation_metric`.

The paper should explain these scopes because they prevent misleading labels.
For example, edge-count delta is not intrinsic to a profile; it is an effect of
the feature that used the profile.

## 5. CAD BrowseComp Row Criteria

A high-hop row is release-quality only if it satisfies all of these:

- The answer is short and typed: entity ID, integer, choice, boolean, finite
  numeric value, bounding box, or compact structured record.
- The hidden query resolves uniquely under deterministic policy.
- Each public clue maps to one hidden clause.
- Individual clues preserve enough distractors unless the row is a low-hop
  calibration item.
- The row uses visible CadQuery wording rather than private ontology jargon.
- The row records logical hop count, static hop count, geometry hop count,
  relation families, measurement scopes, candidate-set trace, and verifier
  status.
- Main benchmark and fine-tuning rows require geometry-derived evidence. Rows
  solved by assignment names, operation order, literal arguments, or simple
  syntax patterns are calibration rows and must be capped or excluded from
  default training exports.
- The row is rejected or quarantined when labels depend on unsupported topology,
  unstable face identity, or AABB-only material-region guesses.

Target difficulty:

| Slice | Intended use |
| --- | --- |
| 0-1 hops | Calibration, curriculum, parser checks, low-hop training. |
| 2 hops | Short relation reasoning and bridge rows. |
| 3-5 hops | Main benchmark rows for early release. |
| 6-8 hops | Hard CAD BrowseComp rows once P1 relations are stable. |
| 9-10 hops | Aspirational rows for expert/tool-assisted comparison. |

The hard rows should emphasize geometry-derived hops over static-code hops.
Static operation order and literal argument lookup are useful, but the
benchmark's identity comes from selector resolution, workplane frames, profile
geometry, topology deltas, paths, centroids, distances, and material effects.
Release reports must include prompt-family quotas and syntax-only shortcut
baselines so a schema-valid dataset cannot be mistaken for a useful CAD
reasoning dataset.

## 6. Example Paper Questions

Use examples like these in the paper:

- Which `.circle(5)` profile is drawn on the explicit plane whose origin has
  the largest Z value, is later extruded, and then contributes the largest
  circular-edge increase among the repeated unioned bosses?
- Which rectangular cut uses the selector that appears on both sides of the
  box, is centered at `-zpos`, and leaves the outer bounding box unchanged?
- Which sweep path point is nearest to the workplane origin of the boss whose
  extrusion is added immediately after the first union that changes the solid
  centroid upward?
- Which feature removed the void region whose centroid lies closest to the
  side-face selector reused by the final blind cut?

These examples should be presented as illustrative until the corresponding
relations are implemented and verifier-backed.

## 7. Dataset Artifact Strategy

The internal construction rows are code-plus-label. Release artifacts split the
benchmark surface from verifier data.

Public model-input rows should include:

- normalized source code;
- prompt;
- answer format;
- public relation-family, measurement-scope, hop-count, split, hash,
  evidence-tier, and release-readiness metadata.

Private verifier rows should include:

- gold answer;
- hidden query program;
- candidate-set trace;
- verifier status;
- private clue map and audit fields.

Rows with failure or quarantine reasons should remain available for smoke
diagnostics and training ablations, but final release benchmark rows must be
`release_ready=true`.

It should not require STEP, mesh, render, or OpenCascade object artifacts for
default training and evaluation. Optional artifacts may support audit,
visualization, or multimodal extensions.

CADEvolve is the practical primary source because it provides executable
CadQuery programs at scale. Synthetic fixtures remain necessary for tests,
smoke datasets, and exact didactic examples, but they should not dominate the
released benchmark.

## 8. Evaluation And Baselines

Report:

- exact structured-answer accuracy;
- invalid output rate;
- missing-response rate;
- duplicate and extra response counts;
- calibration when confidence is requested;
- accuracy by hop slice;
- accuracy by relation family;
- accuracy by measurement scope;
- static-hop versus geometry-hop breakdown;
- split generalization;
- failure taxonomy.

Baselines:

- random and majority;
- regex/static syntax;
- selector-name heuristic;
- operation-order heuristic;
- symbolic primitive geometry;
- AABB-only point, distance, and region baselines;
- graph resolver oracle;
- closed-book LLM zero-shot;
- closed-book LLM few-shot;
- answer-only SFT;
- reasoning or trace-distillation SFT.

The paper must separate closed-book CAD reasoning from tool-assisted CAD
execution. Tool-assisted results are useful upper bounds, not the main score.

## 9. Reviewer Risks

Likely critiques and responses:

- "Why not just run CadQuery?" The benchmark measures whether models
  internalize CAD program semantics for reasoning and training. Tool use is a
  separate upper-bound setting.
- "This is not BrowseComp because there is no web." Correct: it is BrowseComp
  by benchmark shape, not by domain. It uses short verifiable answers,
  entangled evidence, high uncertainty, and distractor-rich resolution over a
  CAD ontology graph.
- "Feature provenance is not exact." Distinguish exact builder history,
  topology-matched provenance, conservative source attribution, and ambiguous
  merged cases.
- "Topology is kernel-sensitive." Store CadQuery, OCP, and OpenCascade versions
  and include release audits.
- "Models can exploit shortcuts." Report shortcut baselines and group-safe
  splits by source family, generator, operation pattern, and counterfactual
  group.
- "Synthetic data may not transfer." Use CADEvolve as the main source and
  reserve synthetic rows for tests and audits.

## 10. Minimal First Paper

The first credible paper should include:

- the graph-first CAD BrowseComp thesis;
- CADEvolve-backed source ingestion;
- deterministic ontology/query/verifier artifacts;
- low-hop calibration and 3+ hop high-uncertainty rows;
- profile geometry, workplane frames, selector/path/material relation slices
  according to implemented coverage;
- structured answers with deterministic parsing;
- split hygiene and leakage audits;
- baseline and SFT experiments;
- an error taxonomy showing where models fail to reduce CAD uncertainty.

Final quantitative claims should be filled only after release-scale graph
generation, validation, audits, and model evaluations are complete.
