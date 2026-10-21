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

## 2. The dimensions of a task

### 2.1 Task target

The task target is the entity or value the task asks about.

| Task target category | What it is |
|---|---|
| CadQuery program | The program as a whole. |
| Operation | One modeling call in the program. |
| Feature | The modeling feature an operation creates or changes. |
| Solid state | The shape after an operation, including the final shape. |
| Face | A face of a solid state. |
| Edge | An edge of a solid state. |
| Vertex | A vertex of a solid state. |
| Edge endpoint | One end of an edge. |
| CadQuery profile | The two-dimensional shape a sketch draws. |
| CadQuery workplane | The frame a sketch or feature is built on. |
| Path | A curve used by a sweep or a path operation. |
| Path point | A point on a path. |
| Path segment | A segment of a path. |
| Region | The material a feature adds, or the material it removes. |
| CadQuery selector result | The entities a CadQuery selector actually selected. |
| Scalar value | A measurement or count with no entity chosen as the answer. |

A task has exactly one task target category. If the answer is a measurement
taken from an entity, the entity is the task target and the measurement is the
answer. The task target category is not the answer format.

### 2.2 Task clue

A task clue is one sentence in the prompt that states a condition the
answer must satisfy. A task clue is not a hint and not an example. It is a condition that
can be checked against the graph.

Every task clue has one of these clue types:

| Task clue type | What it says |
|---|---|
| Property | The task target has a property or measurement with a stated value or range. |
| Relation | The task target stands in a named relation to another entity. |
| Comparison | The task target's measurement compares to a reference measurement. |
| Aggregation | The task target is the extreme, the rank, or the count of a set. |
| Provenance | The task target was created by an operation, uses a CadQuery profile, or sits on a CadQuery workplane. |
| Chain | The task target is reached through an ordered sequence of relations. |

A task clue may combine a relation with a property, for example "the face adjacent
to the selected face whose area is larger than the selected face". It is still
one task clue if it names one condition.

A task clue narrows the set of possible answers. The canonical term for the
condition is **task clue**.

A task may also need a **task answer step** after the task target is identified,
such as reporting the volume of the selected solid state. A task answer step is
not a task clue and is not written as one. It belongs in the answer instruction.

### 2.3 Answer format

The answer format is what the LLM model must return.

| Answer format | What the LLM model returns |
|---|---|
| Multiple choice | One label from a short list of choices. |
| Number | One finite numeric value. |
| Integer | One whole number. |
| Yes or no | One boolean value. |
| 3D coordinate | One point. |
| Bounding box | One minimum corner and one maximum corner. |
| Structured object | One small object with named fields. |

The answer format is independent of the task target and the task clue. A task about a
face can have a multiple-choice answer, a coordinate answer, or a
bounding-box answer.

### 2.4 Answer meaning

The answer meaning is what the answer is about, independent of how it is
returned. The answer format says "number" or "boolean"; the answer meaning says
"volume" or "membership".

| Answer meaning | What it describes |
|---|---|
| Identity | Which entity is the answer. |
| Volume | A volume or volume change. |
| Area | An area. |
| Length | A length. |
| Distance | A distance between two entities or a point and an entity. |
| Angle | An angle between faces, edges, or a path tangent. |
| Count | A number of entities. |
| Rank | A position in an ordered set. |
| Membership | Whether a point is inside, outside, or on a boundary. |
| Position | A point location in space. |
| Extent | A minimum and maximum corner. |
| CadQuery workplane state | The frame of a CadQuery workplane. |
| Material change | Material added or removed. |
| Topology change | A change in faces, edges, or vertices. |
| Validity | Whether a shape is valid. |

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
Depth: 4 (three task clue steps and one task answer step).
Uniqueness: exactly one face satisfies task clues 1 and 2, and the largest area is
            achieved by exactly one of them. Otherwise the task is rejected.
Geometry: all four steps are geometry-based.
```

This is a task description, not an example. The named CadQuery workplane, the
named operation, and the area value are chosen when a task is built. A task
that does not satisfy the uniqueness rule is not generated.

## 5. Coverage

Coverage is checked at each task reasoning step count. For each step count in
the release, the
dataset must contain:

- every task target category supported at that task reasoning step count;
- every task clue type supported at that task reasoning step count;
- every answer meaning supported at that task reasoning step count;
- every answer format supported at that task reasoning step count;
- both syntax-based and geometry-based steps where supported, with geometry
  required for benchmark tasks.

A **task reasoning step support table** records which values can occur at each
step count and why an unsupported value cannot occur there. It is part of the release documentation
and is versioned with the generator. "Supported" is a property of the task
structure, not of the current generator: a value may be marked unsupported only
when no valid task can express it at that step count. A value that is valid but
not implemented is a gap, not an unsupported value.

Coverage is reported at each task reasoning step count and per dimension. Global
coverage is the union of the task reasoning step count reports; it does not
replace them. A value that appears only at step count 5 does not cover step
count 2.

## 6. Balance

Balance is also checked at each task reasoning step count. The release-level
targets remain, but they may not be met by concentrating a value at one task
reasoning step count.

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

Target categories are not percentage-balanced at each task reasoning step count
because their availability differs by step count. The release-level 25% cap
prevents one target category from dominating the whole dataset.

Coverage and balance at each task reasoning step count can conflict, for example
when an answer format can express only a few answer meanings. A conflict is reported with the
affected values; it is not resolved by silently dropping coverage.

## 7. What a task is not

- An answer format alone, such as "coordinate task".
- A measurement alone, such as "volume task".
- A task target alone, such as "face task".
- A task reasoning step count alone, such as "3-step task".

Those are properties of a task. A task must state the task target, task clues,
answer format, answer meaning, and task reasoning step count that tie them together.

## 8. Open questions

- **Q1.** Should a comparison task clue always name both entities, or may one
  entity be selected by an earlier task clue?
  - **Option A — name both entities.**

    ```text
    The area of the face created by `cutBlind` is larger than the area of the
    face created by `box`.
    ```

  - **Option B — refer to the entity selected earlier.**

    ```text
    1. The selected face is the face created by `cutBlind`.
    2. The task target is adjacent to the selected face and has a larger area
       than the selected face.
    ```

  - **Option C — allow both.**
  - **Recommendation:** C, with a rule: every referenced entity is either named
    in the program or already in the candidate set. Prefer B for multi-step
    tasks; prefer A for a self-contained single-step task. Example: a two-clue
    task can say “the selected face” in clue 2 because clue 1 selected it. A
    one-clue task must name the reference face.
