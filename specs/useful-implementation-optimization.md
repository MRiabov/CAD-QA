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

The current reset implements source-derived selector face nodes, same-face
joins, sketch centers, path tangents, nearest path points, and centroid
relations. Kernel-backed selector IDs and group-safe release splits remain open.

## P2

- material-region and void-region geometry;
- stable face/edge/vertex adjacency;
- containment and intersection relations;
- validity/failure probes.

The current reset implements conservative material/void region projections from
profile geometry and operation order. Robust boolean-diff region geometry
remains open.

Avoid task-specific generators. New capabilities should add nodes, relations,
measurements, clauses, or templates to the shared graph/query system.
