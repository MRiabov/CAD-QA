# CAD graph content

**Status:** draft, 2026-10-21. This document defines what the CAD graph
must contain for a task to be answerable. It does not define storage or
code.

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
| CadQuery selector result | The entities a CadQuery selector actually selected. | The CadQuery selector expression and the solid state it ran on. | P1 |
| Measurement | A numeric or geometric value about an entity or a pair of entities. | The measured entity or pair, and the measurement name. | P0 |

Every entity belongs to exactly one CadQuery program. An entity without a
program is not part of a task.

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

### 3.2 Topology

| Relation | From | To | Meaning | Priority |
|---|---|---|---|---|
| has_face | Solid state | Face | The solid state contains the face. | P0 |
| has_edge | Face | Edge | The face contains the edge. | P0 |
| has_vertex | Edge | Vertex | The edge contains the vertex. | P0 |
| adjacent_to | Face | Face | The faces share an edge. | P0 |
| endpoint_of | Edge endpoint | Edge | The endpoint is one end of the edge. | P1 |
| same_as | Face or edge or vertex | Same category | Two records describe the same entity across two solid states. | P2 |

### 3.3 Space and shape

| Relation | From | To | Meaning | Priority |
|---|---|---|---|---|
| parallel_to | Face, edge, or path segment | Face, edge, or path segment | The two are parallel within tolerance. | P0 |
| perpendicular_to | Face, edge, or path segment | Face, edge, or path segment | The two are perpendicular within tolerance. | P0 |
| coplanar_with | Face | Face | The two faces lie in the same plane within tolerance. | P1 |
| coaxial_with | Edge or path segment | Edge or path segment | The two share an axis within tolerance. | P1 |
| contains | Solid state or face | Point or entity | The first contains the second. | P0 |
| intersects | Entity | Entity | The two intersect. | P1 |
| distance_to | Face, edge, vertex, or solid state | Face, edge, vertex, or solid state | The shortest distance between the two. | P0 |

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
| Length | Edge, path segment | Straight or curve length. | P0 |
| Distance | Two endpoint entities, or one endpoint entity and a point | Shortest distance. | P0 |
| Angle | Two faces, two edges, or a path tangent | Degrees or radians, stated once. | P0 |
| Bounding box | Solid state, entity, region | Minimum and maximum corners in the program frame. | P0 |
| Centroid | Solid state, entity, region | Point in the program frame. | P0 |
| Count | Solid state, face, CadQuery selector result | Faces, edges, vertices, selected entities. | P0 |
| Validity | Solid state | Whether the shape is a valid solid or compound. | P2 |
| Volume change | Operation | Signed volume added or removed. | P0 |
| Bounding-box change | Operation | Change caused by the operation. | P1 |
| Topology change | Operation | Change in face, edge, or vertex counts. | P0 |
| CadQuery workplane frame | CadQuery workplane | Origin, x direction, and normal. | P1 |

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

### 4.1 Enumeration domain

A measurement kind is declared for a scope, not for every member of that scope.
Two domains exist.

**Per-entity measurements are total over their scope.** Every face has an area,
every edge has a length, every path segment has a length, every solid state has
a volume and a bounding box. A missing row for a per-entity measurement is a
graph defect, not a data condition.

**Pair measurements and pair relations have one named endpoint.** `distance_to`,
`angle`, `coplanar_with`, `coaxial_with`, `intersects`, and `contains` apply to
pairs, and a solid state can hold thousands of pairs. The domain is not the full
pair set.

A pair element exists only when at least one endpoint is a **named entity**: an
entity a clue can name directly, by face surface kind, by position, or by
the operation or feature that created it. "The cylindrical face", "the top face",
and "the face created by `cutBlind`" are named entities.

The other endpoint must be of an **endpoint entity kind** that the relation or
measurement declares in section 3 or section 4. `coplanar_with` declares faces,
`coaxial_with` declares edges and path segments, and `angle` declares faces or
edges. An endpoint entity kind is a per-relation declaration, not the global
entity category. The domain is then

```text
named endpoint × candidate endpoints of the declared endpoint entity kinds
```

which is linear in the entity count per named endpoint, not quadratic.

The rule follows the clue grammar, so the enumeration is not a separate
vocabulary:

- a `named` reference needs the pair to exist in the graph, because the clue
  names one endpoint and the search must know which candidates the pair selects;
- a `selected` or `aggregated` reference resolves both endpoints at search time,
  so the comparison is computed from the per-entity measurements and no pair
  row is needed;
- a `cross_state` reference needs the per-entity values in both states.

A named endpoint must resolve to exactly one entity in the solid state. It is
identified by face surface kind, by position, or by the operation or feature that
created it. Zero matches or several matches means the pair is not emitted, and a
task clue that needs it is invalid.

There is no cap on pairs per named endpoint: the domain is linear in the entity
count for each endpoint. A program whose solid state exceeds `max_state_entities`
is rejected at graph construction rather than truncated, so every accepted graph
carries its whole pair domain. `max_state_entities` is provisional at 500 and is
tuned against the program pool.

A pair outside the domain is not a missing measurement; it is not a candidate.

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
   outside the declared enumeration domain. A gap is the domain minus the
   rows, computed by the coverage check; the graph stores no missing-value
   record.
8. The graph can answer every task target category, clue type, and answer meaning the dataset claims to support at each task reasoning step count.
9. A task that needs a graph element outside the declared domain is rejected,
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

- **Q4.** *Resolved 2026-10-21.* Record a failure tombstone for a failed
  operation. Do not create measurements, answers, or tasks from the failed
  output. Use the tombstone for debugging and for cache hits when the same
  program, operation, and environment are seen again. The failure manifest
  counts it.
