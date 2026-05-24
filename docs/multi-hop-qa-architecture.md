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

## Axis-General Spatial Tasks

Main benchmark and default SFT rows must not encode a fixed global direction as
the semantic identity of a task family. Families such as
`frontmost_longer_positive_z_kernel_edge`,
`rightmost_shorter_positive_z_kernel_edge`, or any equivalent "always X/Y/Z"
variant are unacceptable as release-grade training families because they teach
models a narrow coordinate habit instead of CAD reasoning.

Axis-dependent tasks must be parameterized. The family identity should describe
the geometric relation while leaving the axis as a sampled query parameter. For
example, use a family shape like `longer_positive_edge_along_axis`, then sample
the axis and direction from supported candidate geometry. The hidden query
program may bind that parameter to X, Y, or Z for a specific row, but the
family/template itself must not permanently mean "positive Z" or "frontmost".

View words such as "frontmost", "backmost", "leftmost", "rightmost", "highest",
and "lowest" are allowed only as sampled renderings of an explicit axis/view
parameter. They must not be hard-coded into generator family names or fixed to
one global axis across a release. Release reports should expose axis/direction
coverage for these families and block or cap collapsed distributions.

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
