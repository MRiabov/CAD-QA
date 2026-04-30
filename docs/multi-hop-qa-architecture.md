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
- No LLM translator is used in the trusted path.
- Rows that fail candidate-breadth or uniqueness gates go to the failure
  manifest.

## Implementation Priorities

P0 implements profile geometry, workplane frames, profile application effects,
query resolution, and prompt rendering.

P1 adds selector face identity, same-face joins, sketch centers, path tangents,
nearest path points, and centroid relations.

P2 adds material/void-region geometry and stable topology adjacency where the
evidence is strong enough for release labels.
