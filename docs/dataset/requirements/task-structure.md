# Task structure

**Status:** draft, 2026-10-21. This document defines how a CAD-QA task is
described. It replaces the flat task list in the PRD.

This document owns the task vocabulary and the task-level reading of the graph.
The graph entity, relation, and measurement kinds are defined in
[`graph-content.md`](graph-content.md); this document does not repeat their
closed value sets. The prompt that renders a task is defined in
[`prompt-content.md`](prompt-content.md).

A **task** is one dataset instance: a CadQuery program, a task target, a set of
task clues, and one answer. A **question** is only the interrogative sentence in
the prompt; it is not the whole task.

## 1. Why a flat list is wrong

The previous list mixed several different things:

- "Direct lookup" described task reasoning step count.
- "Give a coordinate" described an answer format.
- "Measure a distance" described a measurement.
- "Follow a chain" described a chain of task clues.
- "Locate by property" described how the task target is found.

Those are not peers. Treating them as one list makes some tasks look
similar when they are not, and hides gaps.

A task is a combination of separate dimensions. Once the dimensions are
separate, every task can be described precisely, and the dataset can be
checked for real coverage instead of counting labels.

Each value below has a priority. P0 values are required for the first release,
P1 values strengthen it, and P2 values are optional. Priority is implementation
order for that input; it is not a task label. A task that uses a later-priority
value belongs to a later release scope, not to a different task category.

## 2. The dimensions of a task

### 2.1 Task target

The task target is the entity or value the task asks about.

| Task target category | What it is | Priority |
|---|---|---|
| CadQuery program | The program as a whole. | P1 |
| Operation | One modeling call in the program. | P0 |
| Feature | The modeling feature an operation creates or changes. | P0 |
| Solid state | The shape after an operation, including the final shape. | P0 |
| Face | A face of a solid state. | P0 |
| Edge | An edge of a solid state. | P0 |
| Vertex | A vertex of a solid state. | P0 |
| Edge endpoint | One end of an edge. | P1 |
| CadQuery profile | The two-dimensional shape a sketch draws. | P0 |
| CadQuery workplane | The frame a sketch or feature is built on. | P0 |
| Path | A curve used by a sweep or a path operation. | P1 |
| Path point | A point on a path. | P1 |
| Path segment | A segment of a path. | P1 |
| Region | The material a feature adds, or the material it removes. | P0 |
| CadQuery selector result | The entities a CadQuery selector actually selected. | P1 |
| Scalar value | A measurement instance whose value is the answer. The subject need not be unique. | P0 |

The `Priority` column is the priority of a category as a task target. It is not
the graph-input priority in [`graph-content.md`](graph-content.md) section 2: a
CadQuery program is a P0 graph input because every graph entity belongs to one,
and a P1 task target because a question about a whole program ships later.

A task has exactly one task target category. If the answer is a measurement
taken from an entity, the entity is the task target and the measurement is the
answer. The task target category is not the answer format.

In P0 a value answer records the entity as the target. The answer-equivalent set
may hold several entities that share that answer value (`DS-REQ-15`), and the kept
definition binds the first witness in stable candidate order (`DS-REQ-35`). The
scalar value row is defined but no P0 task uses it: a scalar target is deferred
until a question names a measurement whose subject is not an entity category.

A state that an earlier operation produced is not a candidate. The candidate set
is the entities of the target category in the bound state scope, and `DS-REQ-08`
fixes that scope: the final state in P0, one named intermediate state in P1, the
pair in P2. A task never chooses among the states the program passed through.

A scalar target is a measurement instance: a subject, a measurement, and a
value. The subject may be an entity or a solid state. The candidate set is
every instance of the declared measurement in the state scope. A task clue
narrows the instances by constraining the subject or the measurement value. The answer is
the measurement value, and instances that share it are answer-equivalent, so
the subject need not resolve to one entity.

A count is a stored measurement such as `face_count`, `edge_count`, or
`vertex_count` on a solid state. A count over an arbitrary set that is not a
stored measurement is not a scalar target in P0.

### 2.2 Task clue

A task clue is one numbered list item in the prompt that states a condition the
answer must satisfy. A task clue is not a hint and not an example. It is a condition that
can be checked against the graph.

Every task clue has one of these clue types:

| Task clue type | What it says | Priority |
|---|---|---|
| Property | The task target has a measurement with a stated value or range, or a categorical feature with a stated value. | P0 |
| Relation | The task target stands in a named relation to another entity, or in a measured angle to one. | P0 |
| Comparison | The task target's measurement compares to a reference measurement. | P0 |
| Aggregation | The task target is the extreme or the rank of a set. | P1 |
| Provenance | The task target was created by an operation or uses a CadQuery profile. | P0 |

A property clue has one of two shapes:

- a **measurement** — a number with a unit, compared with a comparator: area,
  length, distance, angle, count, volume, volume change, topology change, a
  centroid coordinate, or perimeter (P1). A direction is measured as the angle
  between the outward normal and a program axis; it is not a categorical value;
- a **categorical feature** — a closed value compared for equality. Both
  categorical features apply to a face. Their values and meanings are defined in
  [`graph-content.md`](graph-content.md) section 2.1 and are not repeated here:
  the face surface kind, and the position as the bounding-box extremes the face
  touches. Position is set-valued, because several coplanar faces may touch one
  extreme. A direction is not a categorical feature; it is measured above.

A relation clue has one of two shapes:

- a **named relation** — a relation from [`graph-content.md`](graph-content.md)
  section 3, such as `adjacent_to` or `has_edge`;
- a **measured angle** — the `Angle` measurement between the target and a
  reference, with a comparator and a threshold. Parallel and perpendicular are
  renderings of 0 or 180 degrees and 90 degrees, not separate relations.

A measured-angle relation is one condition, not a relation combined with a
property.

A task clue narrows through geometry or through an earlier task clue. It does not
resolve its target by a pre-registered unique name whose result is independent of
the candidate set; that is a lookup, not a reasoning step. A computed selection,
such as the third from the left or the largest, may leave one entity because the
one is derived from the set.

A task clue with a reference is also described by its **clue reduction form**:
how the reference set is reduced from the entities of the graph. A clue with no
reference has no form; a property clue is one, because it is about the target
alone.

| Clue reduction form | Reference | Priority |
|---|---|---|
| `filtered` | The entities of a category that satisfy conditions. | P0 |
| `selected_in_earlier_clue` | The set an earlier task clue bound. | P0 |
| `aggregated` | A set reduced to one entity by an extreme or rank. | P1 |
| `cross_state` | The before/after solid state pair. | P2 |

All four reduce a set; none creates one. The reference is a set, not a single
entity. A relation or comparison is true when at least one member of the
reference set satisfies it; a clue states "every" only when it says so. The
reference does not add a task clue step; the clue stays one task clue.

Not every clue type can carry every reduction form. These combinations cannot
exist, so no task uses one:

| Combination | Why it cannot exist |
|---|---|
| property with any form | A property clue is about the target alone and has no reference. |
| aggregation with `aggregated` | That is an aggregation over an aggregate, and it is written as two clues. |
| `selected_in_earlier_clue` at task reasoning step count 1 | It needs an earlier task clue. |
| `cross_state` in P0 and P1 | It needs a second solid state, and P0 and P1 use the final state only (`DS-REQ-08`). |

A comparison task clue may filter both entities, or it may refer to a set bound
by an earlier task clue. If the reference set has several members, the clue is
read existentially unless it says "every remaining entity".

A task clue states one condition. A list item that combines a named relation
with a property is two task clues and is split into two list items; a
measured-angle relation is already one condition.

A chain is not a task clue type. It is a P2 implementation of an ordered
sequence of relation task clues: each relation is one task clue and one task
clue step.

A task clue narrows the set of possible answers: it leaves fewer candidates than
it found. A condition that does not narrow is not a task clue. The canonical term
for the condition is **task clue**.

Narrowing is local to the clue's position in the chain and does not make the clue
necessary. Every task clue must also be **necessary**: removing it and running the
remaining clues in order must leave at least two distinct answers, or change the
answer (`DS-REQ-34`). Distinct answers are compared with `same_answer` at the
task's precision (`DS-REQ-15`), so an answer-equivalent set is one answer and not
two. A clue that passes neither test is redundant: the task is shortened by
dropping it, never kept at its length to reach a task reasoning step count.
Removing a clue that a later clue refers to by `selected_in_earlier_clue` changes
that reference set, which is the case the "or change the answer" half covers.

A necessary clue needs a wrong answer that survives every other clue; otherwise
removing the clue already leaves one answer. In a chain whose references are
conditions, each clue step therefore consumes one distinct wrong answer. A
candidate set with `m` distinct answers supports at most `m - 1` clue steps, and
`m` task reasoning steps when the answer is a value. A later clue that refers to
an earlier clue's set is the exception: removing the clue changes that set, and
the "or change the answer" half applies.

In P0 that set is the task target, and a task has one. A later scope may let a
clue narrow a set that is not the target: the clue already records the set it
narrowed and how far it narrowed it, and the prompt already has a phrase for the
set a clue left ("the faces from clue 2"), so that scope adds a binding rather
than a new clue contract.

A task may also need a **task answer step** after the task target is identified,
such as reporting the volume of the selected solid state. A task answer step is
not a task clue and is not written as one. It belongs in the answer instruction.

### 2.3 Answer format

The answer format is what the LLM model must return.

| Answer format | What the LLM model returns | Priority |
|---|---|---|
| Multiple choice | One label from a short list of choices. | P0 |
| Number | One finite numeric value. | P0 |
| Integer | One whole number. | P0 |
| Yes or no | One boolean value. | P0 |
| 3D coordinate | One point. | P0 |
| Bounding box | One minimum corner and one maximum corner. | P0 |
| Structured object | One small object with named fields. | P1 |

The answer format is independent of the task target and the task clue. A task about a
face can have a multiple-choice answer, a coordinate answer, or a
bounding-box answer.

### 2.4 Answer meaning

The answer meaning is what the answer is about, independent of how it is
returned. The answer format says "number" or "boolean"; the answer meaning says
"volume" or "membership".

| Answer meaning | What it describes | Priority |
|---|---|---|
| Identity | Which entity is the answer. | P0 |
| Volume | The volume of a shape. | P0 |
| Area | An area. | P0 |
| Length | A length. | P0 |
| Distance | A distance between two entities or a point and an entity. | P0 |
| Angle | An angle between two faces, two edges, a path tangent, or a planar face and a program axis. Two faces use outward normals, two edges the acute angle between the lines. | P0 |
| Count | A number of entities. | P0 |
| Rank | A position in an ordered set. | P1 |
| Membership | Whether a point is inside the solid state. Points within tolerance of a face surface are not used. | P0 |
| Position | A point location in space, declared by the question: a face centroid, an edge midpoint, a vertex point, or a solid state centroid. | P0 |
| Extent | A minimum and maximum corner. | P0 |
| CadQuery workplane state | The frame of a CadQuery workplane. | P1 |
| Material change | Material added or removed, as a signed volume or count. A cut answers negative. | P0 |
| Topology change | A change in face, edge, or vertex counts. The question declares the category; the answer is the signed delta for that category. | P0 |
| Validity | Whether a shape is valid. | P2 |

Position, membership, and topology change declare a parameter in the question:
the point for a position or a membership, and the category for a topology change.
The parameter is part of the task definition and the answer evidence, not a
convention the resolver picks. A material change declares no parameter; its sign
carries the direction.

The answer meaning is not the answer format. A volume can be returned as a
number; a membership result can be returned as yes or no; an identity is
returned as a multiple-choice label; a position can be
returned as a 3D coordinate; an extent can be returned as a bounding box.

#### 2.4.1 Answer meaning and the graph

An answer meaning is not a graph measurement; it is the task-level reading of
one. The graph element that supplies each meaning is fixed here so the two
vocabularies cannot drift. The measurement definitions are in
[`graph-content.md`](graph-content.md) section 4.

| Answer meaning | Graph element | Declared parameter |
|---|---|---|
| Identity | The task target binding. | none |
| Volume | `Volume` of a solid state or region. | none |
| Area | `Area` of a face, CadQuery profile, or region. | none |
| Length | `Length` of an edge or path segment. | none |
| Distance | `Distance` between two entities or an entity and a point. | none |
| Angle | `Angle`. | none |
| Count | `Count`, or a stored count such as `face_count`. | the counted entity kind |
| Rank | Derived by the task: the ordinal of the target in a reference set ordered by one measurement and direction. It is not a stored measurement. | the ordering measurement and direction |
| Membership | The `is_inside` predicate on a solid state. | the point or point probe |
| Position | `Centroid` of the task target entity or solid state. | face centroid, edge midpoint, vertex point, or solid state centroid |
| Extent | `Bounding box`. | none |
| CadQuery workplane state | `CadQuery workplane frame`. | none |
| Material change | `Volume change`. | none; the sign carries add or remove |
| Topology change | `Topology change`. | face, edge, or vertex |
| Validity | `Validity`. | none |

Two rows are not yet fully supported. `Rank` orders a reference set, but the
ordering measurement and the direction words are an open question in section 8.
`Position` on an edge reads the edge centroid, which is the midpoint only for a
straight edge; a Position answer that needs the midpoint of a curved edge is not
generated until the graph stores that midpoint.

### 2.5 Task reasoning step count

Task reasoning step count is the number of task reasoning steps a task requires:

- **Task clue step**: applies one task clue and reduces the set of possible answers.
- **Task answer step**: produces the answer once the task target is identified.
- **Task reasoning step**: either a task clue step or a task answer step.

The step count is the number of task clue steps plus one if the task needs a task
answer step. For example:

- A task that names the target and asks for its volume has one task answer
  step, so step count 1.
- A task with two task clues and a count answer has two task clue steps and one
  task answer step, so step count 3.

The step count is computed from the actual task solution sequence, not from a
label. The lowest step count in the release is 1; there are no 0-step tasks.

The thesis release targets step counts 1 through 10. Steps 1 through 5 are P0;
steps 6 through 10 are P1 and enter the release only when the 6–10 release gate in the
dataset PRD section 6.1 passes. If the release gate fails, the release is 1 through 5
and every result names that range.

## 3. There are no task types or task patterns

The dataset is not organized into task families, task types, or task patterns.
There is no fixed set of question shapes to instantiate. A task is produced by
choosing a task target, a set of task clues, and an answer format from the CAD
graph.

Enumerating every combination of target, clue type, answer meaning, answer
format, and task reasoning step count would be limiting and useless: it would ask an engineer to
write logic for each possible combination. The generator composes these
dimensions instead.

The task's properties are recorded for different reasons:

| Property | Role |
|---|---|
| Task target category | Coverage and release diversity |
| Task clue type | Coverage and balance |
| Clue reduction form | Coverage in P0; balance target in P1 |
| Answer meaning | Coverage and balance |
| Answer format | Coverage and balance |
| Task reasoning step count | Coverage and mix across task reasoning step counts |
| Uniqueness rule | Quality |
| Geometry requirement | Quality |

Those properties do not create separate generation paths. A new combination of
properties does not require a new code path.

Coverage and balance are checked **at each task reasoning step count**, not only
over the whole release. A global target may not be met by concentrating a value
at one task reasoning step count. The technical specification records a **task
reasoning step support table** that states which values can occur at each step
count.

## 4. Describing a task

A task description must be precise enough that two people would build the same
task from it. It must state:

- the task target category;
- each task clue in order, with placeholders for sampled values;
- the answer format;
- the answer meaning;
- the task answer step, if any;
- the task reasoning step count;
- the uniqueness rule;
- the geometry requirement.

For example, a measure task is described like this:

```text
Task target: a face of the final solid state.
Task clue 1: the target face is adjacent to a face facing +z.
Task clue 2: the angle between the target face and a face facing +x is 90 degrees.
Task clue 3: among the faces that satisfy task clues 1 and 2, the largest.
Answer: the area of the target face, as a number.
Task reasoning step count: 4 (three task clue steps and one task answer step).
Uniqueness: the three task clues leave exactly one face, and the largest area is
            achieved by exactly one of them. Otherwise the task is rejected.
Geometry requirement: at least one task reasoning step (a task clue step or the
                    task answer step) depends on the built shape, not only on
                    the program text.
```

This is a task description, not an example. The directions, the face
descriptions, and the area value are chosen when a task is built. A task that
does not satisfy the uniqueness rule is not generated.

## 5. Coverage

Coverage is checked at each task reasoning step count and per release
implementation scope. The first release checks P0 values; later releases add P1
and P2 values. For each step count in the release, the dataset must contain:

- every task target category supported at that task reasoning step count;
- every task clue type supported at that task reasoning step count;
- every clue reduction form supported at that task reasoning step count, for task
  clues that carry a reference;
- every answer meaning supported at that task reasoning step count;
- every answer format supported at that task reasoning step count;

A **task reasoning step support table** records which values the constructor
produced at least one valid definition for at each step count, and a reason when
it produced none. The five tables are derived from the constructor over the
coverage fixture set; they are not authored as an independent input, and they are
not a description of what the task grammar permits. They are part of the release
documentation and are versioned with the generator.

Support is an observation. A value the constructor can produce but no fixture
shows is not required by a release, and that is the cost of having one
implementation instead of a second description of the grammar. The fixture set
follows the vocabulary: a new value adds a fixture, or a row that names the
missing capability.

Support is separate from implementation priority. A value deferred to P1 or P2
has no row in the P0 table, and that is not a gap in the current release. A value
in the release implementation scope that a fixture supports and the release omits
is a gap.

Coverage is reported at each task reasoning step count and per dimension. Global
coverage is the union of the task reasoning step count reports; it does not
replace them. A value that appears only at step count 5 does not cover step
count 2.

## 6. Balance

Balance is also checked at each task reasoning step count and per release
implementation scope. The release-level targets remain, but they may not be met
by concentrating a value at one task reasoning step count. A release balances
only the values it implements.

| Dimension | Coverage at each task reasoning step count | Balance at each task reasoning step count | Release balance |
|---|---|---|---|
| Task target category | Every supported category appears. | None; coverage only. | No category above 25% of tasks. |
| Answer format | Every supported format appears. | Between half and twice its conditional release share. | Each format 5-25% of tasks. |
| Answer meaning | Every supported meaning appears. | Between half and twice its conditional release share. | Each meaning 1-10% of tasks. |
| Clue type | Every supported clue type appears. | Between half and twice its conditional release share. | No clue type above 25% of task clues. |
| Clue reduction form | Every supported form appears. | Between half and twice its conditional release share. | Equal share among the supported forms. |

Answer format and answer meaning shares are over tasks. Clue type shares are
over task clues, because one task can contain several task clues.

The numbers in this table are the defaults. The release instance is the root
`balance.yaml`, which records the policy that produced a release.

Clue reduction form is coverage-only in P0. Its P1 balance target is an equal share
among the supported forms, and the row is in the table above. Coverage-only is a
concession, not a good property: coverage guarantees that each supported form
appears, not that the forms are usefully mixed, so a release can concentrate one
form and still pass.

The balance check for clue reduction form is still computed in P0 and reported
without blocking. If a supported form falls below a quarter or above four times
its conditional release share, the imbalance is severe and balancing is promoted
into P0 for that release: the release is rebalanced, or the miss is recorded with
its reason. The quarter and four-times bounds are provisional and tuned with the
first release.

The **conditional release share** of a value at a task reasoning step count is
its share among the values supported at that step count, not its share of the
whole release. This makes the check possible when a step count supports only
some values. For example, if `identity` is 5% of the release and is supported at
step count 1, it may not become more than 10% of step count 1 tasks.

Absolute release percentages are not used for one task reasoning step count
because support sets differ. If step count 1 supports only two answer formats,
requiring every format to be 5-25% of step count 1 tasks would make the targets
impossible to satisfy. The conditional share compares like with like.

A step count with zero or one supported value for a dimension is coverage-only
for that dimension; there is no mix to balance. If half of a value's conditional
release share is less than one task, one task satisfies the lower bound.

Task target categories are not percentage-balanced at each task reasoning step count
because their availability differs by step count. The release-level 25% cap
prevents one task target category from dominating the whole dataset.

Coverage and balance at each task reasoning step count can conflict, for example
when an answer format can express only a few answer meanings. A conflict is reported with the
affected values; it is not resolved by silently dropping coverage.

## 7. What a task is not

- An answer format alone, such as "coordinate task".
- A measurement alone, such as "volume task".
- A task target alone, such as "face task".
- A task reasoning step count alone, such as "task with a task reasoning step count of 3".

Those are properties of a task. A task must state the task target, task clues,
answer format, answer meaning, and task reasoning step count that tie them together.

## 8. Open questions

- **Is a count a clue?** A count removes no candidate on its own, so it may be an
  answer meaning rather than a clue. Until the question is resolved, a count is
  an answer step and not a task clue, and `clue-list.md` has no count row.
- **Which direction words may a rank clue use?** A rank needs a stated order.
  The ordering measurement and the direction words are not yet defined. Until
  they are, a P1 rank task is not generated.
- **May a provenance clue point at a second set?** A provenance clue names one
  operation or one CadQuery profile. Whether it may name a reference set is open.
- **May a task narrow more than one set?** Today a task has one target, and every
  clue narrows it, so a reference is either a single condition or an earlier state
  of that target. The previous generator built tasks with two narrowed sets, the
  target candidates and a reference entity, joined by a distance or a rank:
  `parameterized_<target>_reference_<reference kind>_distance` and
  `..._spatial_relation_chain_extreme` in
  [`../../_archive/implementation_status.md`](../../_archive/implementation_status.md).
  One step narrowed one set to fewer candidates; the join was a later step that
  referenced both. Restoring it needs a step that binds a set, a later step that
  references it, and a reducer relative to it. The shape to prefer is a wrapper
  around a step, so a multi-step reference does not reopen every clue contract.
  Deferred: P1 or P2, undecided. Until it is decided, no task binds a second set,
  and a reference states one condition (`prompt-content.md` section 4.2).
- **Is `cadquery_workplane` a task target category in the first release?** As a
  target it supports an identity answer, which is a multiple-choice label, or the
  `CadQuery workplane state` answer at P1: an origin, an x direction, and a
  normal that the program already states. Neither one reads the built shape, so
  the task is close to reading comprehension and counts against `R-4`. A frame
  derived from a face could carry a shape condition, but no phrase names one, and
  a named frame is the program's frame in almost every case, so naming it selects
  everything.

  The fair answers are about the frame: where its origin lies, how its normal is
  oriented, and how far it sits from another frame. None is expressible today.
  `CadQuery workplane state` carries the origin and the normal but is P1 and has
  no question template. `Position` has no CadQuery workplane origin parameter.
  `Angle`
  covers two faces, two edges, a path tangent, or a planar face and a program
  axis, and no CadQuery workplane scope, so an orientation reads as nothing: the
  normal is a direction, and no answer meaning states a direction.

  Every one of those reads the frame the program declares rather than the built
  shape, unless the frame is derived from a face.

  Until the question is resolved, the row keeps its P0 priority and no task uses
  it.

## 9. Resolved questions

- **Q1.** *Resolved 2026-10-21: Option C.* A comparison task clue may name both
  entities or refer to a set bound by an earlier task clue. Every reference set
  is either filtered from the graph or already bound by an earlier clue. A
  reference is a set; the clue holds when at least one member of it satisfies
  the comparison, and it states "every" only when it says so. Prefer a reference
  to an earlier clue for multi-step tasks and a filtered reference for a
  self-contained one-step task. This is the same composition pattern as
  BrowseComp: a later step can build on an earlier result without restating it.

  ```text
  The area of a face facing +z is larger than the area of a face facing -z.
  ```

  ```text
  1. The target face is a face facing +z.
  2. The area of the target face is larger than the area of every other face
     from clue 1.
  ```

- **Q2.** *Resolved 2026-11-25: record the entity.* A task that measures an
  entity records the entity as the target. The answer-equivalent set may hold
  several equal-answer entities, and the kept definition binds the first witness
  in stable candidate order (`DS-REQ-35`). A scalar target is defined but
  deferred; no P0 task uses it. This keeps the prompt label on the entity
  category and avoids a target kind that changes the release schema.
