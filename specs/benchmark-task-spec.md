# CAD-QA Task Specification

## Definition

A CAD-QA task row is an internal construction record: a public rendering plus
the private verifier artifacts from a hidden `QueryProgram` over an
`OntologyGraph`. Release exports split this into answer-free public model-input
rows and private grading/audit rows.

Required internal row fields:

- `row_id`;
- `source_id`;
- `source_code`;
- `prompt`;
- `answer_format`;
- `gold_answer`;
- `query_program`;
- `candidate_trace`;
- `relation_families`;
- `measurement_scopes`;
- `logical_hop_count`;
- `static_hop_count`;
- `geometry_hop_count`;
- `difficulty_bucket`;
- `verifier_status`.

## Hop Slices

| Slice | Meaning | Release role |
| --- | --- | --- |
| 0 | Source/statistic lookup. | Calibration and parser checks. |
| 1 | Resolve one entity and read one metric. | Low-hop training. |
| 2 | Traverse one relation and read/compare a metric. | Bridge reasoning. |
| 3+ | Compose several broad clues under distractors. | CAD BrowseComp benchmark. |

## Query Requirements

Every row must be generated from a deterministic query program. A query program
defines:

- target entity type;
- answer type;
- ordered clauses;
- relation paths;
- metric filters;
- optional aggregation such as `argmax` or `argmin`;
- candidate-set trace;
- reject-unless-unique policy.

## Prompt Requirements

Prompts are rendered from approved templates. Every public clue maps to a
hidden clause. Public wording should mention visible CadQuery constructs such
as `.circle(...)`, `.rect(...)`, `.polyline(...)`, `.faces(...)`,
`.workplane(...)`, `.sweep(...)`, `.union(...)`, or `.cutBlind(...)` rather
than private ontology jargon.

LLMs are not part of trusted generation or grading.
