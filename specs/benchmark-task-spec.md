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

## Geometry-First Benchmark Policy

CAD-QA's benchmark and fine-tuning value comes from geometry-derived reasoning,
not from syntactic lookup. Rows whose answer is inferable from assignment names,
operation order, literal arguments, or simple source-code pattern matching are
allowed only as low-hop calibration and parser checks.

Main release rows should require evidence that is produced by the CAD ontology
and, where appropriate, CadQuery execution: profile geometry, workplane frames,
selector results, path geometry, feature effects, topology deltas, centroids,
distances, material regions, void regions, containment, or adjacency. A row's
metadata must make this auditable through `static_hop_count`,
`geometry_hop_count`, relation families, measurement scopes, and candidate
traces.

Training exports must either exclude syntax-only calibration rows by default or
enforce a small quota for them.

The critical benchmark subset is CAD geometry itself. Release readiness must
prioritize rows about compiled or ontology-derived geometry: solid volume and
bbox, centroids, topology counts and deltas, selector-result geometry,
material/void region deltas, profile application effects, path distances,
containment/intersection/adjacency, and other stable spatial relations. These
rows should be the main training surface; syntax-readable rows are supporting
calibration only.

Spatial benchmark rows must avoid fixed-axis overfitting. A task family must
not permanently mean "frontmost", "rightmost", "leftmost", "highest", or
"positive Z". Those words are allowed only when they render a sampled
axis/direction parameter for a particular row. The durable family identity must
be axis-general, for example `longer_positive_edge_along_axis`, with the bound
axis and sign recorded privately for verification and reporting.

## Prompt Requirements

Prompts are rendered from approved templates. Every public clue maps to a
hidden clause. Public wording should mention visible CadQuery constructs such
as `.circle(...)`, `.rect(...)`, `.polyline(...)`, `.faces(...)`,
`.workplane(...)`, `.sweep(...)`, `.union(...)`, or `.cutBlind(...)` rather
than private ontology jargon.

LLMs are not part of trusted generation or grading.
