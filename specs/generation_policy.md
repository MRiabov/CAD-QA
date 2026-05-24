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

## Maximal Parameter Sampling

Release-grade task families must not bake avoidable constants or fixed choices
into the family definition. A family should encode the reasoning pattern; the
generator should sample the variable parts of that pattern from supported graph
evidence.

Parameters include, but are not limited to:

- target entity type: feature, face, edge, vertex, endpoint, material region,
  void region, path point, or path segment;
- reference entity type and reference-selection strategy;
- axis, sign, coordinate component, and rendered view word;
- extremum direction such as minimum or maximum;
- comparison relation such as shorter/longer, smaller/larger, nearer/farther,
  equal/tolerance-equal, before/after, inside/outside, or
  parallel/perpendicular;
- exact public measurement values and tolerance buckets;
- aggregation metric and tie-break metric.

Hard-coded families such as `frontmost_longer_positive_z_kernel_edge` are not
release-grade because they collapse several variable choices into permanent
family semantics. The intended shape is a parameterized family whose private
query metadata records the sampled entity type, axis, sign, comparison,
aggregation, and measurement values for the row. Release reports should measure
coverage across these parameter dimensions so collapsed distributions are
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
- a nominal task family hard-codes avoidable constants or fixed choices instead
  of sampling explicit row parameters.

## Difficulty

Difficulty is reported through logical hop count, static hop count, geometry
hop count, relation families, and measurement scopes. Hard rows should include
geometry-derived hops, not only source-order or literal-argument hops.
