# High-Hop CAD-QA Architecture

High-hop CAD-QA is the CAD BrowseComp slice of the graph-first system.

The generator samples a target entity or measurement from an `OntologyGraph`,
chooses a set of relation and metric clauses, verifies that each clause leaves
enough distractors, verifies that the full query resolves uniquely, and renders
a public checklist prompt from templates.

## Architecture

```text
OntologyGraph
-> QueryProgram
-> candidate-set trace
-> reject-unless-unique verifier
-> RenderedPrompt
-> DatasetRow
```

## Prompt Rules

- Every clue maps to a hidden clause.
- Public clues mention visible CadQuery constructs instead of private ontology
  jargon.
- Main benchmark clues should require geometry-derived ontology evidence. Clues
  answerable by assignment names, operation order, literal arguments, or source
  syntax alone are calibration-only and must be quota-limited outside smoke
  tests.
- Main benchmark clues should include value-bearing geometry constraints when
  the measured value is stable enough to expose publicly. For example, prefer
  "the target face has a surface area of 12.5" over "the target face has a
  measured surface area" when that value is part of the intended reasoning.
  Public values must be rounded or tolerance-bucketed consistently with the
  verifier so floating-point noise cannot change the gold answer.
- No LLM translator is used in the trusted path.
- Rows that fail candidate-breadth or uniqueness gates go to the failure
  manifest.

## Graph-Hop Candidate Narrowing

Generators must not treat a sparse direct extremum as evidence that a task is
unusable. If a family such as "largest selected-edge count" or "largest selector
result" rarely has a unique global answer, the generator should build a
multi-hop query that first narrows candidates through geometry-derived graph
relations, then applies a sampled final selector inside that subset.

Valid narrowing clauses include shared height or coordinate bucket, coplanarity,
axis/coaxial relation, equal measurement bucket, containment, adjacency,
membership in a sampled selector result, distance to a sampled vertex/reference
feature, or another stable relation in the ontology graph. The narrowed set must
still contain distractors before the final selector. The final selector should
also be parameterized: axis, min/max direction, rank where supported, metric,
target type, and reference anchor should vary by row.

Example shape:

```text
target candidates
-> candidates sharing a sampled geometric relation with a reference entity
-> candidates satisfying a sampled spatial/value constraint
-> nth/min/max/nearest/farthest selector under a sampled metric
-> unique answer
```

This is how sparse selector-count, face-count, edge-count, and similar tasks
should become useful training rows: by asking for a resolvable entity within a
geometry-defined subset, not by relying on a single global aggregation over the
entire model.

### Query Synthesis Architecture

Graph-hop narrowing should be implemented as a query-synthesis layer over the
`OntologyGraph`, not as more one-off hard-coded smoke queries.

```text
OntologyGraph
-> intended family spec
-> broad target candidates
-> predicate catalog
-> bounded clause-chain search
-> final selector sampler
-> QueryProgram
-> existing resolver/verifier/rendering path
```

The synthesis layer should add these components:

- `cad_qa/query/family_specs.yaml`: intended release task families, target
  entity types, allowed narrowing predicates, allowed final selectors,
  release/calibration status, and minimum/maximum hop counts.
- `cad_qa/query/predicate_catalog.py`: reusable geometry-derived predicates that
  can be instantiated from graph evidence. Initial predicates should cover
  shared coordinate buckets, coplanarity, axis/coaxial relation,
  equal/tolerance-equal measurement buckets, containment, adjacency, selector
  membership, and distance to a sampled vertex/feature/entity.
- `cad_qa/query/synthesis.py`: deterministic bounded search that composes
  predicate instances into candidate-narrowing clause chains.
- Query metadata fields for sampled parameters: target type, reference type,
  reference anchor, narrowing predicate sequence, measurement bucket policy,
  axis, sign, extremum direction, rank when supported, aggregation metric, and
  tie-break metric.

### Synthesis Algorithm

For each intended family and source graph:

1. Collect broad candidates by target type and required evidence. For example,
   selectors with kernel-backed selected-edge counts, faces with measured area,
   edges with stable IDs and centroids, or features with compiled volumes.
2. Instantiate predicate candidates from graph evidence. Each predicate instance
   must have a deterministic public rendering and a hidden verifier clause.
3. Search clause chains with a small deterministic beam. Keep only chains whose
   intermediate candidate sets remain nontrivial and whose clauses add
   geometry-derived evidence.
4. Sample a final selector from the family spec: min/max, nearest/farthest, nth
   rank where supported, count extremum, coordinate extremum, distance extremum,
   or measurement extremum.
5. Resolve the composed `QueryProgram`. Accept the row only if the candidate
   trace shows meaningful distractors before the final selector and exactly one
   final answer.
6. Score accepted rows by geometry-hop count, candidate breadth, rarity of the
   sampled parameter combination, prompt-family balance, and answer diversity.
   The exporter may downsample overrepresented rows, but it must not silently
   ignore underrepresented intended families.

The search must be bounded. A practical starting point is depth 1-3 narrowing
clauses, a fixed predicate-instance cap per predicate family, and a small beam
ordered by candidate breadth and parameter-balance need. This avoids a Cartesian
explosion while still finding local subsets that global direct extrema miss.

### Selector-Count Example

The direct family `largest_kernel_edge_selector_count` is weak when the whole
model rarely has a unique largest selector. The synthesized family should instead
look like:

```text
target: selector operations with kernel-backed selected-edge counts
narrowing:
  - selected edges share a sampled plane/height/axis bucket, or
  - selected result geometry is near/far from a sampled feature/vertex, or
  - selected entities share a sampled measurement bucket or containment relation
final selector:
  - largest/smallest selected-edge count, or
  - nth by selected-edge count with deterministic tie-break, or
  - nearest/farthest selector result centroid to a sampled reference
```

Rendered prompt shape:

```text
Identify the selector among the candidates whose selected edges lie on the same
sampled geometric condition as the reference entity. Among that subset, choose
the selector with the sampled count/distance/coordinate criterion.
```

The exact public wording should come from `prompt-templates.yaml`; the hidden
query program carries the actual sampled plane/axis/value bucket/reference
bindings. This keeps the row deterministic while preventing the family from
overfitting to one axis, one extremum, or one global aggregation.

### Acceptance Gates

A synthesized graph-hop narrowing family is release-ready only when:

- each generated row records the sampled narrowing predicates and final selector
  parameters in private metadata;
- candidate traces show at least two candidates before the final selector unless
  the row is explicitly low-hop calibration;
- intermediate narrowing clauses preserve distractors and are not solvable by
  syntax-only source lookup;
- final uniqueness comes from the composed graph query, not from a hand-coded
  target ID or assignment name;
- release reports expose coverage for narrowing predicate families, reference
  anchor types, axes, directions, ranks, final selector metrics, and target
  entity types;
- intended families that generate zero accepted rows are visible in an
  intended-family manifest and block release until moved to review-only status or
  supplied with enough valid rows.

For benchmark-release artifacts, these gates are evaluated under the
`benchmark-release` profile from `specs/dataset-spec.md`. A synthesized family
is not considered complete merely because it can produce one reviewed row: it
must also contribute to the benchmark-release distribution, sampled-parameter
coverage, preview evidence, family-test evidence, and default SFT gates without
collapsing onto one avoidable constant or starving other intended release
families.

## Maximally Parameterized Tasks

Main benchmark and default SFT rows must not encode avoidable constants or
fixed choices as the semantic identity of a task family. A family should
describe the invariant reasoning structure; everything that can vary while
preserving that structure should be a sampled row parameter.

This applies beyond axes. Axes, signs, min/max aggregation direction, exact
measurement values, comparison operators, entity types, reference-object
choices, and target subtypes such as feature, face, edge, vertex, endpoint, or
region should be parameterized whenever the graph and verifier can support the
variation. For example, avoid a permanent family like
`frontmost_longer_positive_z_kernel_edge`; prefer an axis/entity/ordering
general family whose row parameters bind the target type, axis, sign,
comparison relation, and aggregation direction.

Prompt view words such as "frontmost", "backmost", "leftmost", "rightmost",
"highest", and "lowest" are allowed only as sampled renderings of explicit
parameters. Exact public measurements such as area, length, volume, or distance
should likewise come from sampled verified values, not from hand-coded family
templates. Release reports should expose parameter coverage and block or cap
collapsed distributions where a nominally general family always chooses the
same axis, extremum, value shape, comparison, or entity type.

## Value-Bearing Multi-Hop Tasks

The dataset should contain a well-represented slice of tasks where public clues
name measured CAD quantities, not just the existence of a measurement. These
rows may be low-hop when a value uniquely identifies the answer, but they are
still important training examples because they force the model to ground
language in concrete geometry.

Value-bearing rows must be balanced with higher-hop variants. The generator
should mine repeated or tolerance-equal measurements and use those equal-value
sets as distractors. Examples:

- Multiple edges with the same length, such as the twelve equal edges of a box.
- Faces or regions with matching area, volume, centroid coordinate, radius, or
  span.
- Feature parameters or derived measurements that are numerically equal within
  a configured tolerance.

The intended multi-hop shape is:

1. Identify a reference entity by geometry, not by source syntax.
2. Use one of its measured values as a shared constraint.
3. Resolve among the equal-value candidates using another geometric relation or
   measurement.

Example task family: identify a line/edge on a box feature whose midpoint or
centroid is closest to the center of a sphere-like feature, where the box and
sphere are themselves described through geometry-based clues rather than direct
source names. This requires cross-feature grounding, equal-value distractors,
and a final distance comparison.

Release datasets should report coverage for value-bearing measurement prompts,
tolerance-equal distractor prompts, and cross-feature measurement prompts. These
families should be represented in the default SFT export, not left as rare
review-only examples.

## Implementation Priorities

P0 implements profile geometry, workplane frames, profile application effects,
query resolution, and prompt rendering.

P1 adds selector face identity, same-face joins, sketch centers, path tangents,
nearest path points, and centroid relations.

P2 adds material/void-region geometry and stable topology adjacency where the
evidence is strong enough for release labels.

P3 adds value-bearing prompt templates, tolerance-equal measurement mining, and
cross-feature measurement tasks with enough release/SFT coverage to train on
them.
