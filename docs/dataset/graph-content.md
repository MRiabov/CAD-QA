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

## 2. Graph entities

The graph contains these entity categories.

| Entity | What it represents | Identity |
|---|---|---|
| CadQuery program | The program under test. | One per task. |
| Operation | One modeling call in the program. | Visible variable name and position in the program. |
| Feature | The modeling feature an operation creates or changes. | The operation that creates it. |
| Solid state | The shape after one operation, and the final shape. | The operation that produced it. |
| Face | A face of a solid state. | Stable face identity when available; otherwise a stable description tied to a solid state. |
| Edge | An edge of a solid state. | Stable edge identity when available; otherwise a stable description. |
| Vertex | A vertex of a solid state. | Stable vertex identity when available; otherwise a stable description. |
| Edge endpoint | One end of an edge. | The edge and the end. |
| CadQuery profile | The two-dimensional shape a sketch draws. | The sketch operation that creates it. |
| CadQuery workplane | The frame a sketch or feature is built on. | The operation that creates or uses it. |
| Path | A curve used by a sweep or path operation. | The operation that creates it. |
| Path point | A point on a path. | The path and a stable point identity. |
| Path segment | A segment of a path. | The path and a stable segment identity. |
| Region | Material a feature adds or removes. | The feature and the sign of the change. |
| CadQuery selector result | The entities a CadQuery selector actually selected. | The CadQuery selector expression and the solid state it ran on. |
| Measurement | A numeric or geometric value about an entity or a pair of entities. | The measured entity or pair, and the measurement name. |

Every entity belongs to exactly one CadQuery program. An entity without a
program is not part of a task.

## 3. Relations

Relations connect graph entities. The graph must contain at least the following
relation categories.

### 3.1 Program and provenance

| Relation | From | To | Meaning |
|---|---|---|---|
| before | Operation | Operation | The first operation appears before the second in the program. |
| after | Operation | Operation | The inverse of `before`. |
| creates | Operation | Feature | The operation creates the feature. |
| creates | Operation | Solid state | The operation produces the solid state. |
| uses | Feature | CadQuery profile | The feature uses the CadQuery profile. |
| uses | Feature | CadQuery workplane | The feature is built on the CadQuery workplane. |
| derived_from | CadQuery profile | CadQuery workplane | The CadQuery profile is drawn on the CadQuery workplane. |
| derived_from | Path point or segment | Path | The point or segment belongs to the path. |

### 3.2 Topology

| Relation | From | To | Meaning |
|---|---|---|---|
| has_face | Solid state | Face | The solid state contains the face. |
| has_edge | Face | Edge | The face contains the edge. |
| has_vertex | Edge | Vertex | The edge contains the vertex. |
| adjacent_to | Face | Face | The faces share an edge. |
| endpoint_of | Edge endpoint | Edge | The endpoint is one end of the edge. |
| same_as | Face or edge or vertex | Same category | Two records describe the same entity across two solid states. |

### 3.3 Space and shape

| Relation | From | To | Meaning |
|---|---|---|---|
| parallel_to | Face, edge, or path segment | Face, edge, or path segment | The two are parallel within tolerance. |
| perpendicular_to | Face, edge, or path segment | Face, edge, or path segment | The two are perpendicular within tolerance. |
| coplanar_with | Face | Face | The two faces lie in the same plane within tolerance. |
| coaxial_with | Edge or path segment | Edge or path segment | The two share an axis within tolerance. |
| contains | Solid state or face | Point or entity | The first contains the second. |
| intersects | Entity | Entity | The two intersect. |
| distance_to | Entity | Entity | The shortest distance between the two. |

### 3.4 Material change

| Relation | From | To | Meaning |
|---|---|---|---|
| adds_material | Feature | Region | The feature adds the region. |
| removes_material | Feature | Region | The feature removes the region. |
| part_of | Region | Feature | The region belongs to the feature. |

### 3.5 Selection

| Relation | From | To | Meaning |
|---|---|---|---|
| selected_by | Face, edge, or vertex | CadQuery selector result | The entity was selected by the CadQuery selector. |
| selected_from | CadQuery selector result | Solid state | The CadQuery selector ran on the solid state. |

Every relation has two endpoints. A relation with a missing endpoint is a graph
defect, not a graph element.

## 4. Measurements

Measurements are the numeric and geometric values a task can use. The graph
must support at least these.

| Measurement | Applies to | Notes |
|---|---|---|
| Volume | Solid state, region | Positive for a shape; signed for an effect. |
| Area | Face, CadQuery profile, region | Face area and CadQuery profile area are different scopes. |
| Length | Edge, path segment | Straight or curve length. |
| Distance | Two entities, or an entity and a point | Shortest distance. |
| Angle | Two faces, two edges, or a path tangent | Degrees or radians, stated once. |
| Bounding box | Solid state, entity, region | Minimum and maximum corners in the program frame. |
| Centroid | Solid state, entity, region | Point in the program frame. |
| Count | Solid state, face, CadQuery selector result | Faces, edges, vertices, selected entities. |
| Validity | Solid state | Whether the shape is a valid solid or compound. |
| Volume change | Operation | Signed volume added or removed. |
| Bounding-box change | Operation | Change caused by the operation. |
| Topology change | Operation | Change in face, edge, or vertex counts. |
| CadQuery workplane frame | CadQuery workplane | Origin, x direction, and normal. |

Every measurement has:

- an entity or a pair of entities;
- a name;
- a unit or a stated frame;
- a precision or tolerance;
- a record of how it was obtained.

The record of how it was obtained is the **evidence**. Evidence is either
**measured** by running CadQuery, or **derived** from the program text and
geometry by an exact rule. A guessed or approximate value is not evidence and
cannot support a benchmark answer.

## 5. States and timing

A program builds a shape over time. The graph must keep the solid states the tasks
need.

- the solid state before an operation;
- the solid state after an operation;
- the final solid state;
- the CadQuery selector result at the point where the CadQuery selector runs.

A task about an effect must refer to the solid state before and the solid state
after the operation. A task about the final shape must refer to the final solid
state. A face in an earlier solid state and a face in a later solid state are not
the same entity unless the graph records that they are the same.

## 6. Graph quality rules

1. Every entity has a program and a visible origin: a variable name, an
   operation, or a CadQuery selector expression.
2. Every relation has two endpoints.
3. Every measurement has an entity or pair, a name, and evidence.
4. No entity is duplicated under two identities unless the graph records a
   `same_as` relation.
5. No graph element is orphaned.
6. Every graph element used by a task clue or answer is present.
7. Every graph element that cannot be measured is recorded as missing, not guessed.
8. The graph can answer every task target category, clue type, and answer meaning the dataset claims to support at each task reasoning step count.
9. A task that needs a missing graph element is rejected, not softened.

## 7. What the graph is not

- It is not a full dump of every OpenCascade object.
- It is not a replacement for the program text.
- It is not a general-purpose knowledge graph.
- It is not a place to store guessed measurements.
- It is not a database of every possible task; it is the graph elements the
  tasks need.

## 8. Coverage check

For every task reasoning step count, and every task target category, clue type, and
answer meaning supported at that task reasoning step count in `task-structure.md`, the graph must
answer these checks:

- Which task target entities can the task use?
- Which task clue types does the task need?
- Which relations does each task clue need?
- Which measurements does the answer need?
- Which solid states does the task need?
- Which of those graph elements are measured, and which are derived?

A task is not supported if any required graph element is missing. The coverage
report lists the missing graph elements by task reasoning step count, task target
category, clue type, and answer meaning.

## 9. Open questions

- **Q1.** How stable are face, edge, and vertex identities across two
  operations, and when should the graph use `same_as`?
  - **Option A — kernel stable identities.** Use the kernel's stable IDs when
    available.
  - **Option B — geometric fingerprints.** Match by centroid, area, normal, and
    adjacency within tolerance.
  - **Option C — recompute per operation, no identity.** Treat each solid
    state's topology as independent.
  - **Recommendation:** A with B as a fallback, recording `same_as` when the
    match is confident. Example: a face keeps its area and normal after a
    fillet but gets a new kernel ID; the fingerprint matches, so the graph
    records `same_as`. If the match is ambiguous, reject tasks that need that
    identity.

- **Q2.** Should CadQuery selector results be stored as entities, as a relation,
  or both?
  - **Option A — entity only.** A CadQuery selector-result entity, with no membership
    edges.
  - **Option B — relation only.** `selected_by` edges from entities, with no
    result-set entity.
  - **Option C — both.** A CadQuery selector-result entity for counts and aggregation,
    plus `selected_by` edges for membership.
  - **Recommendation:** C. Example: `.faces(">Z")` produces one CadQuery selector-result
    entity, a `selected_from` edge to the solid state, and `selected_by` edges to
    the selected faces. Counts read the CadQuery selector-result entity; “which face was selected” reads
    the edges.

- **Q3.** Which measurements can be derived exactly from the program text, and
  which must always be measured by CadQuery?
  - **Option A — measure everything.** Simple, but loses exact syntax evidence.
  - **Option B — derive everything possible from syntax.** Fast, but wrong when
    later operations change the geometry.
  - **Option C — derive only exact syntax values; measure geometry.** Use exact
    rules for literals, operation counts, and selector membership; measure
    volumes, areas, distances, and topology after operations.
  - **Recommendation:** C, with the evidence recording which path was used.
    Example: `.box(10, 20, 5)` gives a volume of 1000 only if no later
    operation changes it; a fillet volume is measured. A derived value must
    carry the rule that produced it.

- **Q4.** How should the graph represent a shape that cannot be measured, such
  as a failed operation?
  - **Option A — omit the program.** No record, no explanation.
  - **Option B — record a failed state and reject its tasks.** Keep the error
    and the program identity.
  - **Option C — keep a partial graph with missing measurements.**
  - **Recommendation:** B. Example: a `cutBlind` raises; the graph records a
    failed solid state with the error, no task is generated, and the failure
    manifest counts it. Do not guess the missing value or drop the program
    silently.
