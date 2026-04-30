# High-Hop CAD-QA Task Specification

High-hop CAD-QA is the BrowseComp slice of the same graph-first benchmark, not
a separate pipeline.

Rows use 3+ logical hops and should combine broad clues over profiles,
workplanes, selectors, paths, topology, measurements, material regions, or void
regions. Each clue is individually readable from the public CadQuery source but
should preserve distractors. The complete clue set must resolve exactly one
answer through the hidden query program.

## Required Hidden Evidence

- typed ontology graph;
- query program;
- clause-to-clue map;
- candidate-set trace;
- relation families;
- measurement scopes;
- hop counts;
- verifier status.

## Priority Relation Families

P0:

- profile geometry;
- workplane frames;
- profile application effects;
- projection paths;
- measurement-scope-aware templates.

P1:

- stable selector face IDs;
- same-face joins;
- sketch centers;
- path tangents;
- nearest path points;
- centroid and coordinate relations.

P2:

- material-region and void-region geometry;
- adjacency and opposite relations;
- region intersection and containment.
