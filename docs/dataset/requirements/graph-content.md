# CAD graph content

**Status:** draft, 2026-10-21. This document defines what the CAD graph
must contain for a task to be answerable. It does not define storage or
code.

This document owns the graph vocabulary: the entity, relation, and measurement
categories, and the closed value sets they use. [`task-structure.md`](task-structure.md)
owns which of them a task may use and how an answer meaning reads them;
[`prompt-content.md`](prompt-content.md) owns the words. Neither document repeats
these tables.

## 1. Purpose

The graph is the answerable representation of a CadQuery program. Every task clue in a prompt
must be checkable against the graph. Every answer must be produced from the
graph.

If a task clue cannot be checked against the graph, the task is not generated.
If an answer cannot be produced from the graph, the task is not generated.

The graph is not a copy of the program text. It is the set of graph elements the
tasks need, derived from the program and from running it.

Priority follows the PRD. P0 graph inputs are required for the first release,
P1 inputs strengthen it, and P2 inputs are optional. Priority is implementation
order for the input; it is not a task label. A task that uses a later-priority
input belongs to a later release scope.

## 2. Graph entities

The graph contains these entity categories.

| Entity | What it represents | Identity | Priority |
|---|---|---|---|
| CadQuery program | The program under test. | One per task. | P0 |
| Operation | One modeling call in the program. | Visible variable name and position in the program. | P0 |
| Feature | The modeling feature an operation creates or changes. | The operation that creates it. | P0 |
| Solid state | The shape after one operation, and the final shape. | The operation that produced it. | P0 |
| Face | A face of a solid state. | Stable face identity when available; otherwise a stable description tied to a solid state. | P0 |
| Edge | An edge of a solid state. | Stable edge identity when available; otherwise a stable description. | P0 |
| Vertex | A vertex of a solid state. | Stable vertex identity when available; otherwise a stable description. | P0 |
| Edge endpoint | One end of an edge. | The edge and the end. | P1 |
| CadQuery profile | The two-dimensional shape a sketch draws. | The sketch operation that creates it. | P0 |
| CadQuery workplane | The frame a sketch or feature is built on. | The operation that creates or uses it. | P0 |
| Path | A curve used by a sweep or path operation. | The operation that creates it. | P1 |
| Path point | A point on a path. | The path and a stable point identity. | P1 |
| Path segment | A segment of a path. | The path and a stable segment identity. | P1 |
| Region | Material a feature adds or removes. | The feature and the sign of the change. | P0 |
| Point probe | A classified point near a solid state. | The solid state and a stable probe index. | P0 |
| CadQuery selector result | The entities a CadQuery selector actually selected. | The CadQuery selector expression and the solid state it ran on. | P1 |

A CadQuery workplane is a frame, not a shape: an origin, an x direction, and a
normal. The shape an operation produces is a solid state. The two are separate
entities even when one operation creates both.

Every entity belongs to exactly one CadQuery program. An entity without a
program is not part of a task.

Measurements are not entities. They are defined in section 4.

### 2.1 Face attributes

A face carries two categorical attributes beyond its identity:

| Attribute | Values | Meaning |
|---|---|---|
| Face surface kind | `plane`, `cylinder`, `cone`, `sphere`, `torus`, `bspline`, `other` | The geometric surface of the face. |
| Position | `min_x`, `max_x`, `min_y`, `max_y`, `min_z`, `max_z` | Every axis-aligned bounding-box extreme plane of the solid state that the face lies in. A face lies in the plane when all its points share that coordinate; a face that only spans the extreme, such as a side face that reaches the top, does not. |

A face also carries an **outward normal**: for a planar face, the unit direction
pointing out of the solid, in the program frame. It is a continuous direction,
stored as a vector. There is no orientation category and no closed set of axes: a
prompt that says "faces +z" and a prompt that says "30 degrees from +z" read the
same vector, and the wording is a choice at render time. A curved face has no
single normal and carries no value.

The position is a set, not a unique name. A face may touch several extremes, and
several faces may touch the same extreme; coplanar faces are the common case.

The graph stores labels and directions, not English. `04` renders the prompt
wording.

### 2.2 Point probes

A point probe is a point with a classification, produced where the shape is
available. It exists because a membership answer needs a point that the task
generator cannot classify without a kernel.

- One or two probes per solid state.
- The first probe is the state centroid, which is already measured.
- The second probe is a seeded point next to the state surface, on either side
  of it. It is not confined to the bounding box.
- A probe within the clear-case margin of a face surface is discarded. For a
  probe the margin is relative to the state, not to an entity: it is
  `100 × geometric_tolerance × d`, with `d` the bounding-box diagonal, because a
  point has no size of its own.
- Each probe records the point, `inside` or `outside`, the distance to the nearest
  face surface, the classifier, and the margin it was tested against.
- The first and second probes carry opposite labels when both survive, so a
  state supports both membership answers. The sampler in
  `extraction/cadquery/algorithm/runtime.md#point-probes` states the draw.
- A state with no surviving probe supports no membership task. That is a deficit,
  not a guess.

A point probe is not a task target category in P0. It supplies the point literal
for a membership answer about the state it belongs to.

Persisted, a probe is a `point_probe` graph entity with a `has_point_probe`
relation from its solid state. Its point and distance are the `probe_point` and
`distance_to_face_surface` measurements; `is_inside` and `classifier` are attributes.
Storage and table names belong to the `02c` build CAD graph contract, not here.

## 3. Relations

Relations connect graph entities. The graph must contain at least the following
relation categories.

### 3.1 Program and provenance

| Relation | From | To | Meaning | Priority |
|---|---|---|---|---|
| before | Operation | Operation | The first operation appears before the second in the program. | P0 |
| after | Operation | Operation | The inverse of `before`. | P0 |
| creates | Operation | Feature | The operation creates the feature. | P0 |
| creates | Operation | Solid state | The operation produces the solid state. | P0 |
| uses | Feature | CadQuery profile | The feature uses the CadQuery profile. | P0 |
| uses | Feature | CadQuery workplane | The feature is built on the CadQuery workplane. | P0 |
| derived_from | CadQuery profile | CadQuery workplane | The CadQuery profile is drawn on the CadQuery workplane. | P0 |
| derived_from | Path point or segment | Path | The point or segment belongs to the path. | P1 |

These relations are read from the program text and the construction record, not
from the shape: the face a `cutBlind` call created is known from the operation,
and its area is a separate measurement. A clue that uses one of them needs the
program; it does not need the geometry.

### 3.2 Topology

| Relation | From | To | Meaning | Priority |
|---|---|---|---|---|
| has_face | Solid state | Face | The solid state contains the face. | P0 |
| has_edge | Face | Edge | The face contains the edge. | P0 |
| has_vertex | Edge | Vertex | The edge contains the vertex. | P0 |
| adjacent_to | Face | Face | The faces share an edge. | P0 |
| has_point_probe | Solid state | Point probe | The solid state owns the probe. | P0 |
| endpoint_of | Edge endpoint | Edge | The endpoint is one end of the edge. | P1 |
| same_as | Face or edge or vertex | Same category | Two records describe the same entity across two solid states. | P2 |

### 3.3 Space and shape

| Relation | From | To | Meaning | Priority |
|---|---|---|---|---|
| coplanar_with | Face | Face | The two faces lie in the same plane within tolerance. | P1 |
| coaxial_with | Edge or path segment | Edge or path segment | The two share an axis within tolerance. | P1 |

Parallelism and perpendicularity are not relations. The graph stores the `Angle`
measurement: parallel is 0 degrees, or 180 degrees for two faces whose outward
normals point opposite ways, and perpendicular is 90 degrees. "Parallel" and
"perpendicular" are render-time wording for those values. `coplanar_with` and
`coaxial_with` stay relations because neither reduces to one angle: coplanar is a
parallel pair at zero plane distance, and coaxial is two collinear axes.

Point membership is not a relation. It is computed by `is_inside` from a point
literal and a solid state; see `03b`. Entity containment stays with `has_face`,
`has_edge`, and `has_vertex`.

Pair intersection is not a relation. Within one solid state it is either trivial
or a duplicate of `adjacent_to`; between two bodies it would need a body entity,
which the graph does not represent. Multi-body programs are one compound state,
and tasks are about that compound as a whole.

### 3.4 Material change

| Relation | From | To | Meaning | Priority |
|---|---|---|---|---|
| adds_material | Feature | Region | The feature adds the region. | P0 |
| removes_material | Feature | Region | The feature removes the region. | P0 |
| part_of | Region | Feature | The region belongs to the feature. | P0 |

### 3.5 Selection

| Relation | From | To | Meaning | Priority |
|---|---|---|---|---|
| selected_by | Face, edge, or vertex | CadQuery selector result | The entity was selected by the CadQuery selector. | P1 |
| selected_from | CadQuery selector result | Solid state | The CadQuery selector ran on the solid state. | P1 |

Every relation has two endpoints. A relation with a missing endpoint is a graph
defect, not a graph element.

## 4. Measurements

Measurements are the numeric and geometric values a task can use. The graph
must support at least these.

| Measurement | Applies to | Notes | Priority |
|---|---|---|---|
| Volume | Solid state, region | Positive for a shape; signed for an effect. | P0 |
| Area | Face, CadQuery profile, region | Face area and CadQuery profile area are different scopes. | P0 |
| Perimeter | CadQuery profile | The length of the closed boundary. It describes a CadQuery profile of any outline, including one whose outline has no noun. | P1 |
| Length | Edge, path segment | Straight or curve length. | P0 |
| Distance | Two entities of the declared endpoint kinds, or one endpoint entity and a point | The shortest distance between the two entities' geometry, which is the distance between their closest points, or from the point to the nearest point of the entity. 0 when they touch or intersect. Not the distance between centroids. The endpoint kinds are declared in section 4.1. | P0 |
| Angle | Two planar faces, two edges, a path tangent, or a planar face and a program axis | Two faces: between outward normals, 0–180°. Two edges: acute angle between the lines, 0–90°. A face and an axis: between the outward normal and the directed axis, 0–180°, because +z and -z are different labels. Path tangent: between consecutive tangents, 0–180° (P1). Degrees. | P0 |
| Outward normal | Planar face | The unit direction that points out of the solid, in the program frame. A direction, not a category and not a number. | P0 |
| Bounding box | Solid state, face, edge, region | The axis-aligned minimum and maximum corners in the program frame. A point has no extent to report, so a vertex has none. | P0 |
| Centroid | Solid state, face, edge, vertex, region | The measure-weighted center of the entity: the volume centroid of a solid state or region, which is its center of mass under uniform density; the area centroid of a face; the length centroid of an edge; and the point itself for a vertex. Not the center of the bounding box. | P0 |
| Centroid coordinate | Solid state, entity, region | The X, Y, or Z component of the centroid in the program frame. | P0 |
| Probe point | Point probe | The probe point in the program frame. | P0 |
| Distance to a face surface | Point probe | Distance from the probe point to the nearest face surface. | P0 |
| Count | Solid state, face, CadQuery selector result | Faces, edges, vertices, selected entities. | P0 |
| Validity | Solid state | Whether the shape is a valid solid or compound. | P2 |
| Volume change | Operation | Signed volume added or removed. | P0 |
| Bounding-box change | Operation | Change caused by the operation. | P1 |
| Topology change | Operation | Signed change in face, edge, or vertex counts; the task declares the category. | P0 |
| CadQuery workplane frame | CadQuery workplane | Origin, x direction, and normal. | P1 |

A pair angle between two faces or two edges is the measurement a pair-angle clue
or an angle answer reads. "Parallel" and "perpendicular" are renderings of 0 or
180 and 90 degrees, not separate measurements.

The center of a bounding box is the midpoint of its minimum and maximum corners.
It is an exact derivation from `Bounding box`, so it is not stored as a
measurement of its own, and it is a different point from `Centroid`. A prompt
that asks for a center names which one: the center of mass or the center of the
bounding box.

Every measurement has:

- an entity or a pair of entities;
- a name;
- a unit or a stated frame;
- a precision or tolerance;
- a record of how it was obtained.

The record of how it was obtained is the **CAD graph evidence**. CAD graph
evidence is either **measured** by running CadQuery, or **derived** from the
program text and geometry by an exact rule. A guessed or approximate value is not
CAD graph evidence and cannot support a benchmark answer.

### 4.1 Emission rules

A measurement kind is declared for a scope, not for every member of that scope.
Two rules decide what is emitted.

**Per-entity measurements are total over their scope.** Every face has an area,
every edge has a length, every path segment has a length, every solid state has
a volume and a bounding box. A missing row for a per-entity measurement is a
graph defect, not a data condition.

**Pair kinds are sparse or dense.** `distance`, `angle` between two entities,
`coplanar_with`, and `coaxial_with` apply to pairs. A pair row relates two
entities; each side is an **endpoint**. What bounds the rows depends on the pair kind.

A **sparse pair kind** holds for some pairs only: `adjacent_to`, and the P1
`coplanar_with` and `coaxial_with`. Its rows are bounded by the topology and by
the coplanar and coaxial groups, not by the entity product, so every true pair is
emitted and no reference restriction applies.

A **dense pair kind** holds for every pair of its declared endpoint kinds:
`distance`, and `angle` between two planar faces. Its rows are the product of the
sets on its two sides, so it is emitted over a **reference class** under the
bound below. The emitted pairs are not the full pair set.

`angle` declares faces and edges as endpoint entity kinds. `distance` declares
the same two: two faces, or a face and an edge. A reference class is always a
face class, so the emitted `distance` rows are face–face and face–edge pairs;
an edge–edge pair would need an edge reference class, which P0 does not have
([`02c` Q1](../implementation/pipeline/02c-build-cad-graph.md#open-questions)).
The point side a distance answer may name is a task parameter, not a graph
entity, so no stored row has one; the reference form that would name it is
recorded as missing in
[`views/reference-forms.md`](views/reference-forms.md#a-point).

**Pair emission is state-scoped.** Pair rows are emitted only for the solid
states a task can bind in the release implementation scope: the final state in
P0; the final state and the one named intermediate state in P1; both states of a
declared pair in P2 (`DS-REQ-08`). Per-entity measurements, containment relations,
and effect measurements stay total over every state, because the topology-change
answers read them. A pair row for a state the scope cannot bind is not emitted;
it is not a missing measurement.

A **reference class** is the set of entities a `filtered` clue reference names:
all faces of one face surface kind, all faces lying in one bounding-box extreme
plane, or all faces one operation created. A reference phrase names one condition
(`DS-REQ-31`), so a class is drawn by one attribute, and the class is derived
from the face attributes of section 2.1 rather than chosen. The operation class
is a graph label: the clue grammar has no reference phrase for a face created by
an operation ([`reference-forms.md`](views/reference-forms.md#a-face) section A
face). A class may hold no entity, one, or several; a task clue reads it
existentially (`DS-REQ-29`). The other reduction forms produce their set without
a class, and need no pair row.

The other endpoint must be of an **endpoint entity kind** that the relation or
measurement declares in section 3 or section 4. `coplanar_with` declares faces,
`coaxial_with` declares edges and path segments, and `angle` declares faces or
edges. An endpoint entity kind is a per-relation declaration, not the global
entity category.

The emitted pairs for one dense kind in one solid state are then

```text
reference class × candidate endpoints of the declared endpoint entity kind
```

for each class whose member count is at most `max_anchor_class_size`. The count
is bounded by that constant times the candidate count, and the constant is what
keeps it there.

The rule follows the clue grammar, so the enumeration is not a separate
vocabulary:

- a `filtered` reference needs the pair rows, because the clue names a class and
  the search must know which candidates those rows select;
- a `selected_in_earlier_clue` or `aggregated` reference resolves both endpoints at search time,
  so the comparison is computed from the per-entity measurements and no pair
  row is needed;
- a `cross_state` reference needs the per-entity values in both states.

A class is emitted whole or not at all. Truncating a class would make a clue's
truth depend on which members were dropped, because an absent pair row is
indistinguishable from a pair that does not hold. A class over the bound emits no
rows of a dense kind; the omission is a graph data condition, not a defect, and a
task clue that needs it is rejected with that reason.

`max_anchor_class_size` is provisional at 8. Both it and `max_state_entities` are
implementation-scope constants. Each is measured once, offline, from the selected
program pool when an implementation scope starts, and recorded with the
distribution that produced it. Graph construction and planning read the recorded
numbers and never recompute them, so a limit is not a per-run cost and a run stays
reproducible. `max_anchor_class_size` bounds the reference vocabulary — the widest
class one reference phrase may still name — not storage; its value comes from the
observed size distribution of the reference classes in the pool, not from a byte
budget. `max_state_entities` is provisional at 500 and rejects the program at
graph construction rather than truncating it, so every accepted graph carries all
of its emitted pairs. Both constants are revised deliberately when the graph
content grows, for example when P1 adds relations and states.

A pair that is not emitted is not a missing measurement; it is not a candidate.

### 4.2 Tolerance

Geometric tolerance classifies a predicate. It is relative to the entity size, and
the default is `1e-6`.

- It absorbs kernel noise, which is around `1e-9` relative for the geometry this
  dataset builds, so a zero angle between exact-parallel faces passes.
- A relation or pair measurement may override it. The override is recorded on the
  row with the tolerance and the reason.
- It is not the answer precision. A numeric answer is scored at the stated
  precision, four significant figures by default, which is roughly `1e-4`
  relative.

**Clear-case margin.** A predicate used by a task must be decided by at least
`100 × geometric_tolerance`, default `1e-4` relative. Below that the task is
rejected. The margin rarely binds here, because program dimensions are coarse and
near-parallel geometry is rare; it exists to catch numerically degenerate
programs, such as a cut tangent to a face.

### 4.3 Measured and derived evidence

Every relation and measurement records whether it was measured or derived, and
what produced it.

| Element | Evidence |
|---|---|
| `before`, `after`, `creates`, `uses`, `derived_from` | derived from the extraction records |
| `has_face`, `has_edge`, `has_vertex` | derived from the topology records |
| `adjacent_to` | derived from the topology records |
| `coplanar_with`, `coaxial_with`, `angle` | derived from geometry, with the tolerance from section 4.2 |
| `distance` | measured by the kernel |
| `adds_material`, `removes_material`, `part_of` | derived from the feature and region records |
| `is_inside` | measured by the kernel, from the solid state and a point literal |

A derived element names the exact rule and its references. A measured element
names the kernel call. A value with neither is not CAD graph evidence.

## 5. States and timing

A program builds a shape over time. The graph must keep the solid states the tasks
need.

- the solid state before an operation;
- the solid state after an operation;
- the final solid state;
- the CadQuery selector result at the point where the CadQuery selector runs.

A task about an effect must refer to the solid state before and the solid state
after the operation. A task about the final shape must refer to the final solid
state. Entities in different solid states are distinct. The P2 `same_as`
relation may record persistence; earlier releases must not depend on cross-state
identity.

A failed operation does not produce a measurable solid state. The graph records
a **failure tombstone** instead: program identity, operation, error,
environment, and a cache key. The tombstone supports debugging and cache hits.
It is not a graph entity, it never supports an answer, and every task that
depends on the failed output is rejected.

## 6. Graph quality rules

1. Every entity has a program and a visible origin: a variable name, an
   operation, or a CadQuery selector expression.
2. Every relation has two endpoints.
3. Every measurement has an entity or pair, a name, and CAD graph evidence.
4. No entity is duplicated within one solid state. Entities in different solid
   states are distinct; only the P2 `same_as` relation may link them.
5. No graph element is orphaned.
6. Every graph element used by a task clue or answer is present.
7. A graph element is either present with a measured or derived value, or
   outside the emission rules. A gap is what the emission rules require minus
   the rows present, computed by the coverage check; the graph stores no
   missing-value record.
8. The graph can answer every task target category, clue type, and answer meaning the dataset claims to support at each task reasoning step count.
9. A task that needs a graph element outside the emission rules is rejected,
   not softened.

## 7. What the graph is not

- It is not a full dump of every OpenCascade object.
- It is not a replacement for the program text.
- It is not a general-purpose knowledge graph.
- It is not a place to store guessed measurements.
- It is not a database of every possible task; it is the graph elements the
  tasks need.

The graph is an index, not a copy of the geometry. It is complete for the
task vocabulary — every entity, relation, and measurement a supported clue type
or answer meaning can reference — and incomplete for the geometry itself, which
stays in the kernel. Values are measured or derived once, at graph build time,
and stored immutably in the artifact. A task is reproduced from the artifact,
not by re-running the kernel.

## 8. Coverage check

For every task reasoning step count, every release implementation scope, and every
task target category, clue type, and answer meaning supported at that task
reasoning step count in `task-structure.md`, the graph must answer these checks:

- Which task target entities can the task use?
- Which task clue types does the task need?
- Which relations does each task clue need?
- Which measurements does the answer need?
- Which solid states does the task need?
- Which of those graph elements are measured, and which are derived?

A task is not supported if any required graph element is missing. The coverage
report lists the missing graph elements by task reasoning step count, task target
category, clue type, and answer meaning.

## 9. Implementation questions

The graph implementation questions are in
[`../implementation/pipeline/02c-build-cad-graph.md`](../implementation/pipeline/02c-build-cad-graph.md).
They are questions about how to satisfy this document, not a second requirement;
where an answer and this document disagree, this document is right.
Q1 and Q4 are resolved below.

## 10. Resolved questions

- **Q1.** *Resolved 2026-10-21.* P0 and P1 implementation use independent topology per solid
  state (Option C). A face, edge, or vertex in one solid state is not the same
  entity as one in another solid state. `same_as` is P2 only, for explicit
  persistence tasks. When P2 persistence uses it, record the CAD graph evidence (kernel
  identity or a geometric fingerprint) and reject ambiguous matches. Example: a
  face keeps its area and normal after a fillet but gets a new kernel ID; a
  confident fingerprint may support a P2 `same_as` link. P0 and P1 work that
  needs cross-state identity is not generated.

- **Q5.** *Resolved 2026-11-24.* Keep a solid state per solid-producing
  operation. An effect is a difference between the state before an operation and
  the state after it, and attribution compares consecutive states, so both are
  needed and both are stored. Dropping the snapshots would save storage, not
  reasoning, and would remove the P1 intermediate state.

- **Q4.** *Resolved 2026-10-21.* Record a failure tombstone for a failed
  operation. Do not create measurements, answers, or tasks from the failed
  output. Use the tombstone for debugging and for cache hits when the same
  program, operation, and environment are seen again. The failure manifest
  counts it.
