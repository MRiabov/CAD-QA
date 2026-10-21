# Task structure

**Status:** draft, 2026-10-21. This document defines how a CAD-QA task is
described. It replaces the flat task list in the PRD.

A **task** is one dataset instance: a CadQuery program, a task target, a set of
task clues, and one answer. A **question** is only the interrogative sentence in
the prompt; it is not the whole task.

## 1. Why a flat list is wrong

The previous list mixed several different things:

- "Direct lookup" described task reasoning depth.
- "Give a coordinate" described an answer format.
- "Measure a distance" described a measurement.
- "Follow a chain" described a chain of task clues.
- "Locate by property" described how the task target is found.

Those are not peers. Treating them as one list makes some tasks look
similar when they are not, and hides gaps.

A task is a combination of independent dimensions. Once the dimensions are
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

A task clue is one public sentence in the prompt that states a condition the
answer must satisfy. A task clue is not a hint and not an example. It is a condition that
can be checked against the graph.

Every task clue has one of these forms:

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
public object is **task clue**.

A task may also need a **task answer step** after the task target is identified,
such as reporting the volume of the selected solid state. A task answer step is
not a task clue and is not written as one. It belongs in the answer instruction.

### 2.3 Answer format

The answer format is what the LLM model must return.

| Answer format | What the LLM model returns |
|---|---|
| Multiple choice | One label from a short list of choices. |
| Variable name | One name that appears in the CadQuery program. |
| Number | One finite numeric value. |
| Integer | One whole number. |
| Yes or no | One boolean value. |
| 3D coordinate | One point. |
| Bounding box | One minimum corner and one maximum corner. |
| Structured object | One small object with named fields. |

The answer format is independent of the task target and the task clue. A task about a
face can have a multiple-choice answer, a variable-name answer, a coordinate
answer, or a bounding-box answer.

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
| Coordinate | A point. |
| Bounding box | A minimum and maximum corner. |
| CadQuery workplane state | The frame of a CadQuery workplane. |
| Material change | Material added or removed. |
| Topology change | A change in faces, edges, or vertices. |
| Validity | Whether a shape is valid. |

The answer meaning is not the answer format. A volume can be returned as a
number; a membership result can be returned as yes or no; an identity can be
returned as a variable name or a multiple-choice label.

### 2.5 Task reasoning depth

Task reasoning depth is the number of task reasoning steps a task requires:

- **Task clue step**: applies one task clue and reduces the set of possible answers.
- **Task answer step**: produces the answer once the task target is identified.
- **Task reasoning step**: either a task clue step or a task answer step.

The depth is the number of task clue steps plus one if the task needs a task
answer step. For example:

- A task that names the target and asks for its volume has one task answer
  step, so depth 1.
- A task with two task clues and a count answer has two task clue steps and one
  task answer step, so depth 3.

The depth is computed from the actual task solution sequence, not from a label.

## 3. There are no task types or task patterns

The dataset is not organized into task families, task types, or task patterns.
There is no fixed set of question shapes to instantiate. A task is produced by
choosing a task target, a set of task clues, and an answer format from the CAD
graph.

Enumerating every combination of target, clue type, answer meaning, answer
format, and depth would be limiting and useless: it would ask an engineer to
write logic for each possible combination. The generator composes these
dimensions instead.

The task's properties are recorded for coverage and balance:

- task target category;
- task clue types;
- answer meaning;
- answer format;
- task reasoning depth;
- uniqueness rule;
- geometry requirement.

Those properties do not create separate generation paths. A new combination of
properties does not require a new code path.

## 4. Describing a task

A task description must be precise enough that two people would build the same
task from it. It must state:

- the task target category;
- each task clue in order, with placeholders for sampled values;
- the answer format;
- the answer meaning;
- the task answer step, if any;
- the task reasoning depth;
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
Depth: 3 (two task clue steps and one task answer step).
Uniqueness: exactly one face satisfies task clues 1 and 2, and the largest area is
            achieved by exactly one of them. Otherwise the task is rejected.
Geometry: all three steps are geometry-based.
```

This is a task description, not an example. The named CadQuery workplane, the
named operation, and the area value are chosen when a task is built. A task
that does not satisfy the uniqueness rule is not generated.

## 5. Coverage

The dataset must cover:

- every task target category that the PRD claims;
- every task clue type;
- every answer meaning;
- every answer format;
- every task reasoning depth from 0 to 5;
- both syntax-based and geometry-based steps, with geometry required for
  benchmark tasks.

Coverage is reported by dimension, not by old flat labels. A dimension value
that produces zero tasks is a gap.

## 6. What a task is not

- An answer format alone, such as "coordinate task".
- A measurement alone, such as "volume task".
- A task target alone, such as "face task".
- A task reasoning depth alone, such as "3-step task".

Those are properties of a task. A task must state the task target, task clues,
answer format, and task reasoning depth that tie them together.

## 7. Open questions

- **Q1.** Should a comparison task clue always name both entities, or may one
  entity be selected by an earlier task clue?
- **Q2.** Should a task that reports a property of a named task target count as
  depth 0, or as one task answer step?
