# Task structure

**Status:** draft, 2026-10-21. This document defines how a CAD-QA task is
described. It replaces the flat task list in the PRD.

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
| Scalar value | A measurement or count with no entity chosen as the answer. | P0 |

A task has exactly one task target category. If the answer is a measurement
taken from an entity, the entity is the task target and the measurement is the
answer. The task target category is not the answer format.

### 2.2 Task clue

A task clue is one numbered list item in the prompt that states a condition the
answer must satisfy. A task clue is not a hint and not an example. It is a condition that
can be checked against the graph.

Every task clue has one of these clue types:

| Task clue type | What it says | Priority |
|---|---|---|
| Property | The task target has a property or measurement with a stated value or range. | P0 |
| Relation | The task target stands in a named relation to another entity. | P0 |
| Comparison | The task target's measurement compares to a reference measurement. | P0 |
| Aggregation | The task target is the extreme, the rank, or the count of a set. | P1 |
| Provenance | The task target was created by an operation, uses a CadQuery profile, or sits on a CadQuery workplane. | P0 |

A comparison task clue may name both entities, or it may refer to one entity
selected by an earlier task clue. A reference must resolve to exactly one
entity. If earlier task clues leave several possible entities, the comparison
must say how it applies to them (for example, "larger than every remaining
entity") or the task is rejected. The reference does not add a task clue step;
the comparison is still one task clue.

A task clue states one condition. A list item that combines a relation with a
property is two task clues and is split into two list items.

A chain is not a task clue type. It is a P2 implementation of an ordered
sequence of relation task clues: each relation is one task clue and one task
clue step.

A task clue narrows the set of possible answers. The canonical term for the
condition is **task clue**.

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
| Volume | A volume or volume change. | P0 |
| Area | An area. | P0 |
| Length | A length. | P0 |
| Distance | A distance between two entities or a point and an entity. | P0 |
| Angle | An angle between faces, edges, or a path tangent. | P0 |
| Count | A number of entities. | P0 |
| Rank | A position in an ordered set. | P1 |
| Membership | Whether a point is inside, outside, or on a boundary. | P0 |
| Position | A point location in space. | P0 |
| Extent | A minimum and maximum corner. | P0 |
| CadQuery workplane state | The frame of a CadQuery workplane. | P1 |
| Material change | Material added or removed. | P0 |
| Topology change | A change in faces, edges, or vertices. | P0 |
| Validity | Whether a shape is valid. | P2 |

The answer meaning is not the answer format. A volume can be returned as a
number; a membership result can be returned as yes or no; an identity is
returned as a multiple-choice label; a position can be
returned as a 3D coordinate; an extent can be returned as a bounding box.

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
Task clue 1: the face is parallel to a named CadQuery workplane.
Task clue 2: the face is adjacent to the face created by a named operation.
Task clue 3: among the faces that satisfy task clues 1 and 2, the face with the
            largest area.
Answer: the area of the selected face, as a number.
Task reasoning step count: 4 (three task clue steps and one task answer step).
Uniqueness: exactly one face satisfies task clues 1 and 2, and the largest area is
            achieved by exactly one of them. Otherwise the task is rejected.
Geometry requirement: every task clue depends on the built shape, not only on
                    the program text.
```

This is a task description, not an example. The named CadQuery workplane, the
named operation, and the area value are chosen when a task is built. A task
that does not satisfy the uniqueness rule is not generated.

## 5. Coverage

Coverage is checked at each task reasoning step count and per release
implementation scope. The first release checks P0 values; later releases add P1
and P2 values. For each step count in the release, the dataset must contain:

- every task target category supported at that task reasoning step count;
- every task clue type supported at that task reasoning step count;
- every answer meaning supported at that task reasoning step count;
- every answer format supported at that task reasoning step count;

A **task reasoning step support table** records which values can occur at each
step count and why an unsupported value cannot occur there. The four tables are
derived from the task-definition rules; they are not authored as an independent
input. They are part of the release documentation and are versioned with the
generator. "Supported" is a property of the task structure, not of the current
generator: a value may be marked unsupported only when no valid task can express
it at that step count. Structural support is separate from implementation
priority. A value may be structurally supported but deferred to P1 or P2; that
is not a gap in the current release. A value that is structurally valid, in the
release implementation scope, and not implemented is a gap.

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

Answer format and answer meaning shares are over tasks. Clue type shares are
over task clues, because one task can contain several task clues.

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

## 8. Resolved questions

- **Q1.** *Resolved 2026-10-21: Option C.* A comparison task clue may name both
  entities or refer to an entity selected by an earlier task clue. Every
  referenced entity is either named in the program or already in the set of
  possible answers. A reference to an earlier selected entity must resolve to
  exactly one entity. If the earlier clue leaves several, the comparison must
  state an explicit aggregation, or the task is rejected. Prefer the reference
  form for multi-step tasks and the named form for a self-contained one-step
  task. This is the same composition pattern as BrowseComp: a later step can
  build on an earlier result without restating it.

  ```text
  The area of the face created by `cutBlind` is larger than the area of the
  face created by `box`.
  ```

  ```text
  1. The selected face is the face created by `cutBlind`.
  2. The task target is adjacent to the selected face and has a larger area
     than the selected face.
  ```
