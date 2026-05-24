# Useful Implementation Optimization

Optimize for a small graph-first core before broad task coverage.

## P0

1. Source JSONL loading and normalization.
2. AST call-chain extraction.
3. Ontology graph records.
4. Profile geometry for circle, rect, and polyline.
5. Workplane frame extraction.
6. Deterministic query resolution.
7. Rule-based prompt rendering.
8. Dataset row validation.

## P1

- selector face identity;
- same-face joins;
- sketch centers;
- path tangents;
- nearest path points;
- centroid and coordinate relations;
- group-safe splits.

The current graph-first implementation includes source-derived and
trace-backed selector face/edge nodes, same-face joins, sketch centers, path
tangents, nearest path points, centroid/coordinate relations, and group-safe
split machinery. Remaining work is not the existence of these mechanisms; it is
coverage, stable distribution across CadEvolve source families, and avoiding
hard-coded query-family choices.

## P2

- material-region and void-region geometry;
- stable face/edge/vertex adjacency;
- containment and intersection relations;
- validity/failure probes.

The current graph-first implementation includes conservative material/void
region projections and trace-backed kernel material/void region associations
where snapshot deltas can be matched to source features. Remaining work is
broader boolean-diff association, in-place mutation and chained-feature
coverage, and robust stable topology relations at release scale.

Avoid task-specific one-off generators. New capabilities should add nodes,
relations, measurements, clauses, parameterized query-family shapes, or prompt
templates to the shared graph/query system. Any variable choice that can be
sampled and verified should become a row parameter rather than a hard-coded
family name.
