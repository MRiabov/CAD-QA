# CAD-QA Generation Policy

Trusted generation is deterministic:

```text
source -> graph -> query -> verifier -> prompt -> row
```

LLMs are not trusted generators or judges. They may be used only for optional
wording experiments or external model evaluation.

## Candidate Breadth

High-hop CAD BrowseComp rows must keep distractors alive. Individual clues
should not identify a unique candidate unless the row is marked as low-hop
calibration. The full clue set must resolve uniquely.

## Geometry-First Requirement

The main training and benchmark rows must not be answerable from source syntax
alone. The public prompt may reference visible CadQuery constructs, but the
label should depend on geometry, topology, selector results, distances,
centroids, snapshot deltas, or other ontology evidence that comes from graph
extraction and, when needed, CadQuery execution.

Rows that can be solved by reading only assignment names, operation order,
literal arguments, or regex-like syntax are calibration rows, not main
fine-tuning rows. They must be capped or excluded from training exports by
default.

Release-quality high-hop rows should satisfy these shortcut-resistance gates:

- `geometry_hop_count` is nonzero;
- geometry-derived clauses are necessary for uniqueness;
- static-only baselines are measured and reported;
- prompt-family quotas prevent syntax-only templates from dominating the set.

## Axis and View Sampling

Release-grade spatial task families must not bake a single global axis or view
direction into the family definition. A family named or implemented as
"frontmost", "rightmost", "leftmost", "highest", "positive Z", or similar is
only acceptable when that word is a sampled rendering of an explicit
axis/direction parameter for the row. It is not acceptable for the generator to
produce a stable family such as `frontmost_longer_positive_z_kernel_edge`,
because that collapses the task distribution onto one coordinate convention.

Axis-dependent families should be written in axis-general form. For example,
the intended family shape is `longer_positive_edge_along_axis`: the query
chooses an axis and sign from the graph, filters candidates by that sampled
parameter, and renders the prompt with terminology appropriate to the sampled
view. The verifier must record the bound axis/direction, and release reports
should measure distribution across axes and signs so collapsed axis habits are
visible and gateable.

## Critical Training Subset

The highest-priority implementation work is the subset of rows that teaches
models CAD geometry, not source-code lookup. Do not treat broader prompt
coverage, request export, or SFT formatting as training readiness until this
subset is implemented and dominates the release set.

Critical rows should exercise at least these geometry-backed task families:

- final and intermediate solid measurements: volume, bbox, centroid, validity,
  face/edge/vertex counts;
- feature application effects: signed volume delta, bbox delta, topology delta,
  circular-edge delta, centroid movement;
- selector-result geometry: selected count, selected entity type, selected
  bboxes, stable face/edge signatures, repeated selector identity;
- material and void regions from kernel-backed operation deltas, not only
  source-order projections;
- profile-to-solid effects: which profile or workplane produced a measured
  downstream geometry change;
- path and sketch geometry: path tangents, nearest points, distances, centers,
  axes, and coordinate comparisons;
- spatial relations: distance, containment, intersection, adjacency, opposite
  faces, parallel/perpendicular/coaxial relations when evidence is stable.

Release and training reports should make the count of these critical geometry
rows prominent. A dataset with mostly syntax-only or static-argument rows is a
smoke dataset even if it is schema-valid.

## Rejection

Reject or quarantine rows when:

- the query has zero candidates;
- the query has multiple final candidates under reject-unless-unique policy;
- required relation families are unsupported;
- a label depends on unstable face/edge/vertex identity;
- material or void-region evidence is only an AABB guess;
- the public prompt cannot be traced to hidden clauses.
- a nominal training/benchmark row is solvable by syntax-only clues without
  geometry-derived evidence.
- a nominal spatial family hard-codes one global axis or view direction instead
  of sampling an explicit axis/direction parameter.

## Difficulty

Difficulty is reported through logical hop count, static hop count, geometry
hop count, relation families, and measurement scopes. Hard rows should include
geometry-derived hops, not only source-order or literal-argument hops.
