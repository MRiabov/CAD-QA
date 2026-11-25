# Capability coverage

**Status:** derived view, 2026-11-25. What each P0 graph capability can be asked
about, and which capabilities no P0 task reads yet. Every rule comes from
[`graph-content.md`](../graph-content.md) sections 2–4,
[`task-structure.md`](../task-structure.md) section 2.4,
[`prompt-content.md`](../prompt-content.md) section 4, and the two phrase views.
This view owns no rule: if it disagrees with a requirement, the requirement is
right, and an empty "read by" cell is a gap to settle in the requirement, not a
permission to skip the capability.

## How to read a row

A capability is read three ways:

- **answer** — an answer meaning reads it
  ([`task-structure.md`](../task-structure.md#241-answer-meaning-and-the-graph));
- **clue** — a clue string names or compares it ([`clue-list.md`](clue-list.md));
- **reference** — a phrase names the category
  ([`reference-forms.md`](reference-forms.md)).

A measurement with a `label.metric` row is also readable by the property and
comparison clues on a target of its subject: "The target face has an area
greater than 10". The table below names the answer meaning, which is the reader
the requirement fixes.

A capability with no reader is still required. The extraction contract declares
it as a [`MustExtractCapability`](../../implementation/pipeline/extraction/validation.md#the-must-extract-capability-set)
cell, and `extraction_capability_coverage` fails the release when no accepted
graph carries it. This view is the other half: whether a task can reach it once
the graph has it.

## P0 answer meanings

| Answer meaning | Reads | Categories |
|---|---|---|
| Identity | The task target binding. | every target category |
| Volume | `volume` | solid state, region |
| Area | `area` | face, CadQuery profile, region |
| Length | `length` | edge |
| Distance | `distance` | two entities, or an entity and a point |
| Angle | `angle` | two faces, two edges, a face and an axis |
| Count | `face_count`, `edge_count`, `vertex_count` | solid state, face |
| Membership | `is_inside` with a point or point probe | solid state |
| Position | `centroid` | face, edge, vertex, region, solid state |
| Extent | `bounding_box` | solid state, face, edge, region |
| Material change | `volume_change` | operation |
| Topology change | `topology_change` | operation |

## P0 measurements by subject

| Subject | Measurement | Answer meaning |
|---|---|---|
| solid state | `volume` | Volume |
| solid state | `bounding_box` | Extent |
| solid state | `centroid` | Position: the center of mass |
| solid state | `face_count`, `edge_count`, `vertex_count` | Count |
| face | `area` | Area |
| face | `bounding_box` | Extent |
| face | `centroid` | Position: the area centroid, and the comparison clue on a centroid coordinate |
| face | `edge_count`, `vertex_count` | Count |
| edge | `length` | Length |
| edge | `bounding_box` | Extent |
| edge | `centroid` | Position: the length centroid, the midpoint only for a straight edge |
| vertex | `centroid` | Position: the vertex point |
| CadQuery profile | `area` | Area |
| region | `volume` | Volume; target only |
| region | `area` | Area; target only |
| region | `bounding_box` | Extent; target only |
| region | `centroid` | Position: the center of mass; target only |
| point probe | `probe_point` | Membership: the point literal |
| point probe | `distance_to_face_surface` | none: the clear-case margin evidence |
| operation | `volume_change` | Material change |
| operation | `topology_change` | Topology change |
| pair | `distance` | Distance |
| pair | `angle` | Angle, and the angle clue |

P1 rows are not listed: `selected_count`, `workplane_frame`,
`bounding_box_change`, `perimeter`, and the path measurements.

`centroid` is the measure-weighted center; for a solid state or region the
volume centroid is the center of mass under uniform density. The center of the
bounding box is the midpoint of `bounding_box`, an exact derivation and a
different point; no answer meaning reads it, so a prompt that asks for a center
names which one. `distance` on a pair is the shortest distance between the two
entities' geometry, at their closest points, not the distance between their
centroids.

## P0 relations

| Relation | Read by |
|---|---|
| `before`, `after` | reference form: the `<method>` operation that appears last in the program |
| `creates` (operation to feature, operation to solid state) | provenance clue: created by the operation |
| `uses` (feature to CadQuery profile) | provenance clue: uses the CadQuery profile |
| `uses` (feature to CadQuery workplane) | no reader: a CadQuery workplane is not a clue discriminator |
| `derived_from` (CadQuery profile to CadQuery workplane) | no P0 reader; the frame is the P1 CadQuery workplane state |
| `has_face` | no clue: the target category and the count read the state |
| `has_edge`, `has_vertex` | containment clue |
| `adjacent_to` | relation clue: is adjacent to |
| `has_point_probe` | no clue: it supplies the membership point |
| `adds_material`, `removes_material` | no clue: Material change reads the operation's volume change |
| `part_of` | no reader |

## P0 categories

| Category | Target | Reference phrase | Reached by a clue |
|---|---|---|---|
| Face | yes | yes | yes |
| Edge | yes | yes | yes |
| Vertex | yes | none | yes, by containment or its own centroid |
| Solid state | yes | only "the target solid state" | no: there is one state to name |
| Operation | yes | yes | yes, by its effects only |
| CadQuery profile | yes | yes, except `other` | yes, by CadQuery profile kind and area |
| CadQuery workplane | yes | none | no |
| Region | yes | none | no |
| Feature | yes | none | no |
| CadQuery program | no | none | no |
| Point probe | no: it supplies the membership point | none | no |

## Gaps recorded here

- No reference phrase names a region, a feature, a CadQuery workplane, a vertex,
  or the operation that created a face or edge. A region, a feature, and a
  CadQuery workplane can only be a target; a vertex is reached by containment or by its
  own centroid.
- Vertex, CadQuery profile, CadQuery workplane, region, and feature are P0 and
  have no constructed task yet; the target questions are written, the
  construction is `03b` work.
- `distance_to_face_surface` is evidence, not an answer: membership reads its
  point, not its distance.
- `distance` on a pair is the closest-point distance (above), but the requirement
  does not declare which entity kinds it pairs and no pipeline stage produces the
  rows yet
  (`MC-67`). A pair-distance question cannot be built until both land.
- `derived_from`, `part_of`, `adds_material`, `removes_material`, and the
  CadQuery workplane `uses` have no clue. Material change reads the operation's volume
  change, so the region relations stay graph facts for now.
