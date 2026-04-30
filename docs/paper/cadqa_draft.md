# CAD-QA: BrowseComp for CAD Program Reasoning

## Abstract

BrowseComp showed that short-answer questions can expose a large missing
capability in browsing agents: persistent reasoning through entangled,
hard-to-find evidence. CAD-QA targets the analogous gap for CAD agents. Given
an executable CadQuery script, a model must identify or compute a short,
verifier-backed answer by resolving a hidden typed CAD ontology graph. The
public prompt contains only the source program and rule-rendered clues; the
private label path contains source normalization, trace or snapshot evidence,
ontology nodes, relation families, measurement scopes, a deterministic query
program, candidate-set traces, and a verifier decision.

The benchmark unifies simple and hard CAD questions under one graph-first
design. Low-hop rows ask for direct statistics or one-relation measurements.
High-hop rows are BrowseComp-style CAD questions: obfuscated, distractor-rich
checklists that require resolving profiles, workplanes, selectors, paths,
material changes, topology, and metric comparisons before producing one
structured answer. Unlike web browsing benchmarks, CAD-QA does not rely on an
LLM judge in the trusted generation path; answers are produced and checked by a
deterministic resolver over CadQuery-derived evidence. Release-scale model
numbers remain `[RESULT: pending]`, but the intended claim is clear: CAD-QA is
a compact, verifiable benchmark and training source for the reasoning pattern
CAD agents need before they can reliably edit geometry.

## Introduction

CAD agents increasingly write plausible CadQuery programs, but plausible code
is not the same as geometric understanding. A useful CAD model must know which
profile a feature used, how a workplane frame projects local sketch coordinates
into world coordinates, which selected face received a cut, whether a path
tangent is parallel to an extrusion direction, and which operation introduced
or removed a region of material. These facts are rarely stated in one line of
source code. They emerge from a construction graph.

This paper frames CAD-QA as the CAD analogue of BrowseComp. BrowseComp asks
browsing agents to persist through sparse, entangled web evidence and return a
short answer. CAD-QA asks CAD agents to persist through sparse, entangled CAD
program evidence and return a short answer. The important difference is that
CAD-QA's evidence is not the open web; it is a typed ontology graph extracted
from source, execution traces, geometry snapshots, and verifier policy.

The central research question is:

> Given a CadQuery script, can a model reduce uncertainty over the implied CAD
> ontology graph and recover the unique verifier-backed answer without running
> a CAD kernel at evaluation time?

The benchmark should not be organized as separate low-hop diagnostics and
high-hop reasoning tracks. Those are difficulty slices of the same system. A
0-hop row may ask for a source statistic. A 1-hop row may resolve one entity
and read one measurement. A 2-hop row may traverse from a feature to a profile
or workplane before comparing a metric. A 3+ hop row becomes the real
BrowseComp-style CAD challenge: several individually broad clues jointly
identify one answer while distractors remain plausible.

## Contributions

CAD-QA makes four contributions.

1. A graph-first benchmark formulation for CAD program reasoning. Every row is
   generated from a hidden query program over a typed CAD ontology graph, so
   low-hop calibration rows and high-hop CAD BrowseComp rows share one
   architecture.
2. A deterministic data-generation path. Source normalization, AST extraction,
   optional CadQuery traces, ontology extraction, query resolution, prompt
   rendering, and validation are explicit artifacts rather than opaque LLM
   generation.
3. A relation and measurement vocabulary for CAD reasoning. The benchmark
   covers operation order, inputs, parameters, profiles, workplanes, selectors,
   topology, paths, centroids, distances, material additions, material
   removals, and scoped measurements such as profile geometry and feature
   application effects.
4. An evaluation and training target for CAD agents. Short structured answers
   support exact grading, invalid-output measurement, calibration analysis, and
   answer or reasoning SFT data in the same spirit that hard web-search tasks
   motivate post-training for browsing agents.

## Related Work

BrowseComp evaluates browsing agents with short-answer questions that are
challenging because the evidence is hard to find and entangled. CAD-QA imports
that benchmark shape but replaces web access with source-visible CAD evidence
and hidden verifier traces. The analogy is useful because both settings test
uncertainty reduction rather than fluent summarization.

WebSailor argues that strong deep-research agents need training data that
requires structured sampling, information obfuscation, and persistent
reasoning. CAD-QA uses the same high-level recipe for CAD: sample subgraphs
from an ontology, hide the target behind public clues, preserve enough
distractors for each individual clue, and require the full clue set to resolve
a unique answer.

CAD synthesis and reverse-engineering benchmarks usually evaluate whether a
model can generate code or reconstruct geometry. CAD-QA instead evaluates
diagnostic understanding of a given construction program: what entities exist,
how they relate, what measurements they have, and which operation caused a
geometric effect.

Geometry benchmarks over meshes, point clouds, images, or final solids often
discard the procedural history. CAD-QA keeps the program as the primary object,
because CAD editing depends on history, selectors, workplanes, feature
provenance, and parameter sensitivity.

Citation placeholders: `[CITE: BrowseComp]`, `[CITE: WebSailor]`,
`[CITE: CadQuery]`, `[CITE: CADEvolve]`, `[CITE: CAD synthesis]`,
`[CITE: geometric learning]`, `[CITE: CAD agents]`.

## Benchmark Design

CAD-QA rows are generated by a single pipeline:

```text
CadQuery source
-> source normalization
-> trace/snapshot extraction
-> typed CAD ontology graph
-> deterministic query program
-> verifier-backed answer
-> rule-based public prompt renderer
-> public row grouped by hop count and relation/metric families
```

The ontology contains nodes for sources, features, operations, parameters,
workplanes, sketches, profiles, solids, faces, edges, vertices, axes,
directions, points, centroids, centerlines, paths, selectors, measurements,
material regions, and void regions. Relations include temporal order,
`input_to`, `parameter_of`, `uses_profile`, `located_on`, `selected_by`,
`bounded_by`, `has_measurement`, `has_centroid`, `has_normal`, `distance_to`,
`parallel_to`, `perpendicular_to`, `coaxial_with`, `adjacent_to`,
`contained_in`, `intersects`, `adds_material_to`, and
`removes_material_from`.

Measurements are scoped to avoid category errors. A profile has intrinsic
measurements such as area, perimeter, centroid, local bounding box, edge count,
and vertex count. A feature application has effects such as signed volume
delta, topology delta, circular-edge delta, and bounding-box delta. Entity
geometry, snapshot state, and relation metrics are separate scopes.

This design turns earlier "core" tasks into low-hop graph rows:

| Hop slice | Example | Purpose |
| --- | --- | --- |
| 0-hop | Count `.extrude(...)` calls. | Source-statistic calibration. |
| 1-hop | Resolve one feature and read its signed volume delta. | Entity and metric grounding. |
| 2-hop | Resolve a feature, traverse to its profile, compare profile area. | Short relation reasoning. |
| 3+ hops | Combine profile, workplane, selector, path, material, and metric clues to identify one entity. | CAD BrowseComp. |

## CAD BrowseComp Rows

A release-quality high-hop row should be short-answer, verifier-backed, and
hard because of uncertainty, not because of vague wording. A public prompt is a
checklist of clues rendered from hidden clauses. Each clue must be understandable
from the visible script, but no single clue should collapse the candidate set
unless the row is intentionally low-hop. The full clue set must resolve one
answer under a reject-unless-unique policy.

Example prompt shape:

```text
Given the CadQuery script, identify the feature that satisfies all constraints:
- It creates a circular profile on one of the explicit `cq.Plane(...)`
  workplanes rather than on the default XY plane.
- Its workplane origin has a larger Z coordinate than at least five other
  repeated boss workplanes.
- The resulting extrusion is later added to the running object with `.union(...)`.
- The profile's feature-application effect has the largest circular-edge
  increase among the candidates that pass the previous clues.
Return exactly one feature ID.
```

The hidden query program for this row records the target entity type, answer
type, relation paths, metric filters, aggregation, candidate-set trace, hop
counts, failure reasons if any, and verifier status. Public wording is
rule-based. LLMs may be used for optional wording experiments or external
evaluation, but not for trusted generation or judging.

The local ontology preview already shows the intended clue vocabulary:
profiles from `.circle(...)`, `.rect(...)`, and `.polyline(...).close()`;
workplanes from `cq.Workplane(...)` and `cq.Plane(...)`; selectors from
`.faces(...)`; paths from `splineApprox(...)` and sweep inputs; material
regions from extrude/union and cut operations; and measurements from profile
geometry, bounding-box deltas, topology deltas, centroids, and distances.

## Dataset Construction

The primary source is CADEvolve-style executable CadQuery code. Synthetic
fixtures remain useful for golden tests, smoke tests, and didactic examples,
but release rows should be CADEvolve-derived and split by source family or
counterfactual group to reduce leakage.

For each source, the pipeline stores normalized code, source metadata, stable
hashes, and extraction diagnostics. Static extraction builds an operation graph
from assignments and call chains. Trace extraction, when enabled, executes the
source in an isolated worker and records snapshot-level measurements: volume,
bounding boxes, centers, topology counts, selector results, point membership,
and conservative provenance. Failures are not silently dropped; they are
written to a failure manifest and used to define benchmark coverage.

Ontology extraction then creates typed nodes and relations. The P0 release
target is profile geometry, workplane frames, profile-to-feature application
effects, deterministic query resolution, and rule-based prompt rendering. P1
adds selector face IDs, same-face joins, sketch centers, path tangents, nearest
path points, and centroid/coordinate relations. P2 adds conservative material
and void-region geometry, adjacency, containment, and intersection where the
evidence is release-grade.

Every internal construction row should include:

- `row_id`;
- `source_id`;
- public source code;
- public prompt;
- answer format;
- gold answer;
- hidden query program;
- candidate-set trace;
- relation families used;
- measurement scopes used;
- logical, static, and geometry hop counts;
- difficulty bucket;
- verifier status.

Release artifacts split those fields into answer-free `public.jsonl` rows for
model input and `private.jsonl` rows for grading, hidden query programs,
candidate traces, clue maps, and audit.

Release statistics should be filled from the release artifact:
`[TABLE: row counts by hop slice, relation family, and split]`,
`[TABLE: verifier failures and quarantine reasons]`,
`[RESULT: source count]`, `[RESULT: public row count]`.

## Evaluation

The main setting is closed-book CAD reasoning: the model receives the source
and prompt but cannot call CadQuery. This isolates whether the model has
internalized enough CAD semantics to reduce uncertainty from the visible
program. A tool-assisted setting can be reported as an upper bound, but it is
not the primary benchmark.

Scoring uses deterministic parsers whenever possible. Entity IDs, integers,
choices, booleans, finite numeric values, bounding boxes, and short structured
records are parsed into typed answers and compared against verifier labels with
task-specific tolerances. Invalid output rate is a first-class metric.
Missing-response rate is reported separately from parser failures, and response
files are audited for duplicate or extra row IDs. Confidence can be requested to
report calibration, matching BrowseComp's emphasis on short-answer accuracy and
uncertainty.

Baselines should include:

- random and majority baselines by answer type;
- static syntax and regex baselines;
- symbolic primitive-geometry baselines;
- selector-name and operation-order heuristics;
- AABB-only baselines for region, distance, and point queries;
- graph resolver oracle;
- closed-book LLM zero-shot and few-shot;
- answer-only SFT;
- reasoning or trace-distillation SFT when hidden query traces are available.

Required final tables:

- `[TABLE: headline model comparison by hop slice]`;
- `[TABLE: accuracy, invalid output rate, and calibration]`;
- `[TABLE: relation-family breakdown]`;
- `[TABLE: static-hop versus geometry-hop breakdown]`;
- `[TABLE: shortcut baseline gap]`;
- `[TABLE: SFT and reasoning-trace ablations]`.

## Training Signal

CAD-QA is not only an evaluation set. The same hidden query programs and
candidate-set traces can train CAD agents to perform uncertainty reduction over
program-derived geometry. Answer-only SFT teaches final labels; trace SFT can
teach candidate filtering, relation traversal, metric comparison, and
reject-unless-unique behavior. The research hypothesis is that this training
will improve downstream CAD editing, debugging, and planning more than generic
CAD-code finetuning, because it supervises the reasoning path that links source
edits to geometric consequences.

## Limitations

CAD-QA should not claim solved CAD reasoning. It measures a precise capability:
short-answer reasoning over executable CadQuery programs and verifier-derived
ontology evidence. Some labels are kernel-sensitive and must carry CadQuery,
OCP, and OpenCascade version metadata. Feature provenance is conservative
unless exact builder-history evidence is available. B-Rep adjacency and
opposite-face relations require careful stability policy. Material and
void-region labels should be quarantined when the evidence is only an AABB
guess. Counterfactual edit labels require separate verification before they
become public benchmark rows.

The benchmark also intentionally sidesteps long-form design assistance. A
model that scores well on CAD-QA may still fail to design a useful part. The
claim is narrower and more useful: CAD-QA tests whether a model can recover
hard, entangled facts about a CAD program's implied geometry.

## Conclusion

CAD-QA should be the BrowseComp of CAD: compact public prompts, short
verifiable answers, high uncertainty, and a benchmark shape that exposes a core
missing capability in agents. Its CAD-specific contribution is the hidden
typed ontology graph and deterministic verifier path. Low-hop rows calibrate
source and metric grounding; high-hop rows test the reasoning pattern needed to
resolve profiles, workplanes, selectors, topology, paths, and material effects
under distractors. Final claims should be filled only after release-scale graph
generation, validation, audits, and model evaluations are complete.
