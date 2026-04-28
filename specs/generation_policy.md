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
- Public rows for:
  - `operation_count`
  - `selector_count`
  - `bbox_after_step`
  - `signed_volume_delta`
  - `topology_count_after_step`
  - `point_membership`
  - `feature_provenance_choice`

Do not start by building a large standalone synthetic CAD corpus. First build a
small trace-backed release candidate from CADEvolve plus a deterministic golden
fixture suite.

## 2. CADEvolve Source Policy

Use the downloaded `cadevolve.tar` archive as the canonical CADEvolve input and
provenance root. For local generation, materialize the configured executable
source subset into an extracted directory and load repeated runs from that
directory instead of treating the tar archive as the hot path.

Prefer executable CadQuery program trees:

- `CADEvolve-P/`
- `CADEvolve-C/`

Treat `CADEvolve-G/` as generator metadata, embeddings, and family context. Do
not treat it as the default executable source unless a later policy explicitly
supports generator invocation.

For every source record, store:

- `source: "cadevolve"`;
- deterministic `source_id`;
- archive member path exactly as seen in `cadevolve.tar`;
- normalized archive member path with any leading `./` removed;
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
5. Compute volume, bounding box, topology counts, and selector diagnostics for
   target states.
6. Assign stable entity IDs per snapshot.
7. Match topology across adjacent snapshots.
8. Capture OpenCascade operation history where practical before CadQuery drops
   builder objects.
9. Store failures and partial traces instead of silently skipping them.

## 5. Task Row Materialization

Derive many task rows from one trace, but do not recompute geometry while
materializing prompts. Candidate rows should be created from stored trace
metadata only.

High-value row sources:

- every supported operation for `operation_count`;
- selectors that appear in the source;
- operations with nonzero volume delta;
- operations that change bounding box dimensions;
- operations that change face/edge/vertex counts;
- points sampled deep inside, deep outside, on boundary, near boundary, inside
  removed cuts, and inside added features;
- final entities with stable provenance labels;
- counterfactual parameter variants with shared group IDs.

## 6. Point Sampling

Sample point questions from explicit strata:

```text
deep_inside
deep_outside
near_face
near_edge
near_vertex
on_boundary
inside_removed_cut
inside_added_feature
inside_fillet_region
```

Store nearest entity diagnostics and point classification confidence. Do not
mix ordinary inside/outside rows with ambiguous near-boundary rows unless the
task is explicitly boundary-aware.

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
multi_solid
kernel_sensitive
```

Difficulty should be derived from measurable source and trace metadata, not
manual impressions.

## 9. Class Balance Targets

Balance per task family, not globally. The MVP should avoid a release where
most rows are easy operation counts.

Suggested public row mix for a first release:

- 15-20% static code tasks;
- 15-20% selector/workplane tasks;
- 20-25% numeric geometry tasks;
- 15-20% topology tasks;
- 15-20% point membership tasks;
- 10-15% provenance tasks.

Exact proportions can change after failure rates and runtime costs are known.

## 10. Candidate Rejection Rules

Reject or quarantine rows when:

- source execution fails or times out;
- the final object is not a valid solid/compound under the selected policy;
- required intermediate snapshots are missing;
- labels contain non-finite numeric values;
- topology count is kernel-unstable across repeated runs;
- provenance confidence is below the task threshold;
- point classification is ambiguous but the task expects a crisp label;
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
