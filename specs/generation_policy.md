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

## Rejection

Reject or quarantine rows when:

- the query has zero candidates;
- the query has multiple final candidates under reject-unless-unique policy;
- required relation families are unsupported;
- a label depends on unstable face/edge/vertex identity;
- material or void-region evidence is only an AABB guess;
- the public prompt cannot be traced to hidden clauses.

## Difficulty

Difficulty is reported through logical hop count, static hop count, geometry
hop count, relation families, and measurement scopes. Hard rows should include
geometry-derived hops, not only source-order or literal-argument hops.
