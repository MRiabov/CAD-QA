# High-Hop CAD-QA Task Specification

High-hop CAD-QA is the BrowseComp slice of the same graph-first benchmark, not
a separate pipeline.

Rows use 3+ logical hops and should combine broad clues over profiles,
workplanes, selectors, paths, topology, measurements, material regions, or void
regions. Each clue is individually readable from the public CadQuery source but
should preserve distractors. The complete clue set must resolve exactly one
answer through the hidden query program.

## Parameterized Task Families

Task families must be as parameterized as the graph evidence and verifier allow.
If a task uses an extremum, directional coordinate, positive/negative side,
measurement value, comparison relation, target subtype, or reference subtype,
that choice should be a row parameter sampled by the generator and recorded in
the private query metadata.

The family name should describe the relation independently of avoidable fixed
choices. Do not define release-grade families whose identity is tied to one
global axis, one min/max direction, one exact value shape, or one entity subtype
when those choices can be varied. Words like "frontmost", "rightmost",
"leftmost", "highest", and "lowest" are prompt rendering choices for sampled
view parameters, not permanent family semantics.

## Graph-Hop Narrowing

Task families that are rare or ambiguous under a direct global selector should
not be discarded. They should be expressed as graph-hop narrowing programs:

1. start from a broad entity type, such as selectors, faces, edges, vertices,
   features, material regions, or void regions;
2. narrow candidates with one or more sampled geometry-derived relations, such
   as shared height, coplanarity, shared axis, equal measurement bucket,
   containment, adjacency, or distance to a sampled reference entity;
3. apply a sampled final selector, such as min/max, nearest/farthest, or rank
   under a sampled metric;
4. require the candidate trace to show nontrivial distractors before the final
   selector and exactly one final answer.

For example, a selector-count task should not depend on the entire model having
a unique largest selector. It may ask for the selector among a graph-defined
subset, such as selectors associated with entities on the same plane or sharing
a sampled measurement bucket, then resolve by a sampled count/position/distance
criterion.

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
