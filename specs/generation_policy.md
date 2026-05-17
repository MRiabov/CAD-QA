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

## Difficulty

Difficulty is reported through logical hop count, static hop count, geometry
hop count, relation families, and measurement scopes. Hard rows should include
geometry-derived hops, not only source-order or literal-argument hops.
