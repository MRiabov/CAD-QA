# High-Hop CAD-QA Task Specification

High-hop CAD-QA is the BrowseComp slice of the same graph-first benchmark, not
a separate pipeline.

Rows use 3+ logical hops and should combine broad clues over profiles,
workplanes, selectors, paths, topology, measurements, material regions, or void
regions. Each clue is individually readable from the public CadQuery source but
should preserve distractors. The complete clue set must resolve exactly one
answer through the hidden query program.

## Axis-Parameterized Spatial Families

Spatial task families must be axis-general. If a task uses an extremum,
directional coordinate, positive/negative side, or view word, the axis and sign
must be row parameters sampled by the generator and recorded in the private
query metadata. The family name should describe the relation independently of a
fixed coordinate convention, for example `longer_positive_edge_along_axis`.

Do not define release-grade families whose identity is tied to one global axis
or view, such as `frontmost_longer_positive_z_kernel_edge`. Words like
"frontmost", "rightmost", "leftmost", "highest", and "lowest" are prompt
rendering choices for a sampled view parameter, not permanent family semantics.

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
