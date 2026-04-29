# CAD-QA Generation Policy

This file defines dataset generation policy for CAD-QA. It specifies what
examples should be proposed, accepted, rejected, balanced, tagged, grouped, and
recorded before implementation starts. It is not a code architecture or module
layout.

CADEvolve is the primary source corpus for released CAD-QA examples. Synthetic
fixtures are allowed for golden tests, smoke tests, debugging, and label edge
cases, but should not become the main dataset source.

## 1. MVP Generation Scope

The first implementation target is deliberately narrow:

- Single CadQuery program rows only.
- Code-only closed-book prompts only.
- CADEvolve `CADEvolve-P` and `CADEvolve-C` scripts as primary sources.
- Minimal synthetic primitives for golden fixtures and local fallback.
- Stable public rows for:
  - `operation_count`
  - `selector_count`
  - `bbox_after_step`
  - `signed_volume_delta`
  - `topology_count_after_step`
  - `point_membership`
  - `feature_provenance_choice`

Do not start by building a large standalone synthetic CAD corpus. First build a
small trace-backed release candidate from CADEvolve plus a deterministic golden
fixture suite. Experimental candidate descriptors for `workplane_state`,
`coordinate_frame`, `graph_query`, `spatial_distance`, `bbox_region_query`, and
`validity_failure_prediction` may be generated from the same traces, but they
are gated before public release.

## 2. CADEvolve Source Policy

Do not redownload or duplicate CADEvolve by default. CAD-QA generation should
prefer an already available adjacent/local CADEvolve source tree, such as an
extracted source cache from a sibling repository, and read repeated runs from
that directory.

An upstream archive such as `cadevolve.tar` may be used to inspect metadata,
validate provenance, or materialize a missing bounded subset, but it is not a
required hot path and should not be copied into this repository. If both an
adjacent source tree and an archive are configured, the source tree is the
execution input and archive metadata is provenance/audit context.

Prefer executable CadQuery program trees:

- `CADEvolve-P/`
- `CADEvolve-C/`

Treat `CADEvolve-G/` as generator metadata, embeddings, and family context. Do
not treat it as the default executable source unless a later policy explicitly
supports generator invocation.

For every source record, store:

- `source: "cadevolve"`;
- deterministic `source_id`;
- archive member path exactly as seen upstream when available;
- normalized archive member path or source-relative path with any leading `./`
  removed;
- local source root identifier in private manifests only, not public rows;
- source subtree;
- generator or family ID if derivable;
- license metadata;
- raw source code hash;
- normalized source code hash;
- operation signature hash;
- source-family grouping keys for leakage-safe splits.

All CADEvolve programs are untrusted Python. They must execute only inside
isolated workers with timeouts and failure reporting.

## 3. Source Sampling Strategy

Initial sampling should prefer scripts that are highly reconstructible:

- assign final output through `result = ...`;
- use mostly single-assignment fluent CadQuery operations;
- have bounded file size;
- avoid dynamic imports, filesystem access, network access, and subprocesses;
- include at least one solid-producing operation;
- include a range of selectors, transforms, booleans, fillets, chamfers,
  shells, lofts, sweeps, and workplanes over time.

Sampling should stratify by:

- source subtree;
- operation count;
- operation signature;
- topology complexity;
- presence of booleans;
- presence of fillet/chamfer/shell;
- selector usage;
- workplane transformations;
- source family/generator ID.

## 4. Trace Generation

For each accepted source:

1. Parse the Python AST into a source operation graph.
2. Execute the script step-by-step in an isolated worker.
3. Record normalized operation nodes with source lines, arguments, inputs, and
   outputs.
4. Capture intermediate CadQuery objects where feasible.
5. Compute volume, bounding box, topology counts, selector diagnostics,
   workplane/frame state, and cheap adjacent-step deltas for target states.
6. Assign stable entity IDs per snapshot.
7. Match topology across adjacent snapshots.
8. Capture OpenCascade operation history where practical before CadQuery drops
   builder objects.
9. Build spatial references and indexes for stable points, axes, centerlines,
   entity bounding boxes, sampled material regions, and reusable candidate
   query pools.
10. Run optional validity probes for bounded operation or candidate-edit
    failure tasks.
11. Store failures and partial traces instead of silently skipping them.

## 5. Label-Led Task Materialization

Generation is driven by the labels the release needs, not by exhaustively
labeling everything a script could answer. The pipeline separates:

- **eager trace labels**: cheap, reusable facts already needed for the trace,
  such as operation nodes, snapshots, volume, bounding boxes, topology counts,
  workplane state, source selectors, and adjacent-step scalar deltas;
- **candidate descriptors**: lightweight references to possible questions,
  such as "classify a point from stratum X at snapshot Y" or "evaluate selector
  S at snapshot Y";
- **scheduled labels**: candidate descriptors selected by the sampler and then
  labeled;
- **public rows**: scheduled labels rendered into prompts and answers.

Do not brute-force expensive geometry labels just to build a large private
pool. Expensive selectors, point classifications, boolean/material-region
queries, validity probes, and counterfactual traces are evaluated only after
the scheduler requests them.

High-value descriptor sources:

- every supported operation type and operation prefix for `operation_count`;
- selector probes from both source selectors and generated common CadQuery
  selectors;
- every geometry-producing step for `signed_volume_delta`, including zero-delta
  steps;
- every valid intermediate snapshot for `bbox_after_step` and
  `topology_count_after_step`;
- point descriptors at intermediate and final states from object AABBs,
  expanded AABB shells, boundaries, removed regions, added regions, and stable
  entity neighborhoods;
- point/entity provenance descriptors for `created_by`, `deleted_by`,
  `modified_by`, `inherited_from`, and `bounded_by`;
- workplane and coordinate-frame states before and after workplane-changing
  operations;
- graph-query descriptors over operation, topology, provenance, parameter,
  selector, and measured-attribute graphs;
- counterfactual parameter, selector, workplane, and operation variants with
  shared group IDs.

Later complex row sources:

- graph-query templates over operation, topology, provenance, parameter, and
  measured-attribute graphs;
- stable point, axis, and centerline references for distance questions;
- bounding-box region queries over topology entities and conservative material
  change evidence;
- validity probes and bounded threshold searches for operation failure-mode
  questions.

Descriptor counts, scheduled-label counts, label-failure counts, and
exported-row counts are separate statistics. Generation reports must record all
four where available so imbalance is visible without requiring all possible
geometry labels to be computed.

### 5.1 Per-script Label Scheduler

Every generation run must define a sampler configuration with at least:

- `max_rows_per_source`;
- `max_rows_per_source_task_type`;
- target task-family weights;
- per-family strata and minimum quotas;
- RNG seed;
- duplicate prompt/label suppression policy;
- split-group policy.

Scheduling proceeds in this order:

1. compute eager trace labels once;
2. build lightweight candidate descriptors from trace metadata and configured
   descriptor generators;
3. attach task type, answer type, difficulty tags, operation family, source
   step, estimated cost, and sampling stratum to each descriptor;
4. run a round-robin or weighted round-robin scheduler across task families and
   strata;
5. label only the selected descriptors, stopping when per-source and global
   quotas are satisfied;
6. reject invalid, ambiguous, unstable, duplicate, or over-budget scheduled
   labels according to task contracts;
7. backfill from the next descriptor in the same stratum or neighboring strata
   when a scheduled label fails;
8. write a private sampling manifest that explains descriptor counts,
   scheduled-label counts, label failures, and exported rows by task type and
   stratum.

The sampler must prevent broad task families from crowding out narrow ones.
For example, `operation_count` and `bbox_after_step` may have many cheap rows,
but they should not consume the per-source budget before `point_membership`,
`graph_query`, `selector_count`, `signed_volume_delta`, and provenance strata
have been considered.

### 5.2 Label Cost Classes

Use the cheapest defensible label source for each task:

- **free from AST**: operation counts, operation order, source-line references,
  and many graph descriptors over operation nodes;
- **free from eager snapshots**: signed volume deltas, bounding boxes, topology
  counts, and scalar before/after deltas;
- **cheap scheduled probes**: selected point classifications and selected
  generated selector counts;
- **expensive scheduled probes**: boolean/material-region evidence, validity
  sweeps, counterfactual traces, and kernel-sensitive provenance checks.

Only the first two classes should be computed broadly. The last two are sampled
before labeling.

## 6. Point Sampling

Point membership is a large descriptor family, not a rare special case. For
each accepted snapshot, generate lightweight point-sampling descriptors from
explicit strata:

```text
deep_inside
deep_outside
aabb_uniform_inside
expanded_aabb_outside
near_boundary_inside
near_boundary_outside
on_boundary
inside_removed_cut
inside_added_feature
inside_fillet_region
```

Sampling may use the final object, every intermediate object, or a configured
subset of snapshots. Random points drawn uniformly from the object AABB or a
slightly expanded AABB are valid descriptors, but the kernel classifier should
run only for descriptors selected by the scheduler. The exported dataset should
be stratified so it does not collapse into easy outside points.

Store nearest entity diagnostics, source snapshot, coordinate frame, sampling
method, RNG seed, adaptive boundary margin, exported point precision, and point
classification confidence. Do not emit `ambiguous` point-membership rows.
Near-boundary inside/outside rows must be sampled at an adaptive margin, by
default 1% of the snapshot max AABB side length, so the rounded exported point
has a crisp classifier label.

## 7. Counterfactual Groups

Counterfactual variants are valuable but must share a group ID so splits cannot
leak variants across train and test.

Supported counterfactuals:

- numeric parameter perturbation;
- operation removal;
- selector change;
- workplane offset change;
- fillet/chamfer radius change;
- extrusion height change;
- cut depth change.

Every counterfactual group must store the base source ID, changed field, old
value, new value, and regenerated trace status.

## 8. Difficulty Tags

Recommended tags:

```text
static_code
symbolic_arithmetic
workplane_tracking
selector_semantics
boolean_cut
fillet_or_chamfer
shell
loft_or_sweep
topology_count
point_membership
near_boundary
feature_provenance
counterfactual
graph_query
multi_hop
spatial_distance
bbox_region_query
validity_failure
multi_solid
kernel_sensitive
```

Difficulty should be derived from measurable source and trace metadata, not
manual impressions.

## 9. Class Balance Targets

Balance per task family and per source. The MVP should avoid a release where
most rows are easy operation counts or where each source contributes only the
first few cheap descriptors discovered by the generator.

Suggested public row mix for a first release:

- 15-20% static code tasks;
- 15-20% selector/workplane tasks;
- 20-25% numeric geometry tasks;
- 15-20% topology tasks;
- 15-20% point membership tasks;
- 10-15% provenance tasks.

Exact proportions can change after failure rates and runtime costs are known.
For every release, publish descriptor counts, scheduled-label counts,
label-failure counts, and exported-row counts by task type, source subtree,
operation family, and difficulty stratum. A low exported count is acceptable
only when the descriptor set is truly small, scheduler quotas exclude it, or
the scheduled labels fail stability checks.

## 10. Candidate Rejection Rules

Reject or quarantine rows when:

- source execution fails or times out;
- the final object is not a valid solid/compound under the selected policy;
- required intermediate snapshots are missing;
- labels contain non-finite numeric values;
- topology count is kernel-unstable across repeated runs;
- provenance confidence is below the task threshold;
- point classification is not one of the crisp labels allowed by the task;
- a graph query has ambiguous references, empty candidates, or unstable
  tie-breaking;
- a point, axis, centerline, or bounding-box spatial reference cannot be
  resolved with the required confidence;
- a region query relies only on bounding-box false positives where exact
  geometry evidence is required;
- a validity probe or threshold search is kernel-unstable, timeout-sensitive,
  or non-monotonic under the declared search contract;
- the prompt leaks the answer through diagnostics or comments.

## 11. Smoke Dataset Requirements

A smoke dataset must include at least:

- one box/extrude-only script;
- one cut/hole script;
- one selector-heavy script;
- one workplane-transform script;
- one fillet or chamfer script;
- one topology-changing boolean script;
- one point-membership boundary case;
- one provenance case with `created_by`, `modified_by`, `inherited_from`, and
  `bounded_by`.

Later smoke suites for complex task families should add:

- one graph-like query with an ordinal feature reference;
- one point-to-point distance query;
- one hole/cylinder centerline distance query;
- one bounding-box region query over vertices or affected features;
- one stable invalid-operation or failure-mode query.

## 12. Determinism and Reproducibility

Generation must record:

- dataset version;
- code commit;
- config hash;
- deterministic seed;
- Python, CadQuery, OCP, and OpenCascade versions;
- label policy;
- source manifest;
- source extraction manifest;
- worker limits;
- retry policy.

Repeated generation from the same inputs should produce identical public rows
or a reproducibility audit explaining any differences.

## 13. Anti-Patterns

- Treating free-form natural language as the only answer.
- Recomputing geometry separately for every task prompt.
- Releasing rows without source-family or counterfactual group IDs.
- Using AABB heuristics as official labels.
- Forcing single-feature provenance labels for fillet, shell, cleanup, or merge
  cases that are genuinely many-to-many.
- Letting synthetic primitives dominate the benchmark.
- Treating graph-like questions as free-form natural language without storing
  the query IR and resolved references.
- Treating bounding-box region overlap as exact material evidence without
  conservative confirmation.
- Publishing failure-mode labels that are not stable across repeated isolated
  probes.
- Exporting every possible row from a script instead of scheduling a balanced
  subset of descriptors.
- Treating only selectors that appear in the source as selector-count
  descriptors when generated common selectors can be evaluated from the same
  trace.
- Sampling point membership only from uniform AABB points without balancing
  inside, outside, boundary, added-region, and removed-region cases.
