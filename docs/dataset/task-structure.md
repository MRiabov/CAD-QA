# Task structure

**Status:** draft, 2026-10-21. This document defines how a CAD-QA task is
described. It replaces the flat task list in the PRD.

A **task** is one dataset instance: a CadQuery program, a task target, a set of
task clues, and one answer. A **question** is only the interrogative sentence in
the prompt; it is not the whole task.

## 1. Why a flat list is wrong

The previous list mixed several different things:

- "Direct fact" described task reasoning depth.
- "Give a coordinate" described an answer format.
- "Measure a distance" described a measurement.
- "Follow a chain" described a task reasoning pattern.
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
| Scalar fact | A measurement or count with no entity chosen as the answer. |

A task has exactly one task target category. If the answer is a measurement
taken from an entity, the entity is the task target and the measurement is the
answer. The task target category is not the answer format.

### 2.2 Task clue

A task clue is one public sentence in the prompt that states a condition the
answer must satisfy. A task clue is not a hint and not an example. It is a condition that
can be checked against the graph.

Every task clue has one of these forms:

| Task clue form | What it says |
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

### 2.4 Task reasoning pattern

The task reasoning pattern is how the task target is found.

| Pattern | What happens |
|---|---|
| Direct | The task target is named, and the task asks for a fact about it. |
| Locate | One or more task clues narrow the candidates to one task target. |
| Measure | The task target is located, then a measurement of it is reported. |
| Compare | Two targets are located, then compared. |
| Count | A set is located, then counted. |
| Rank | A set is located, then ordered and ranked. |
| Effect measurement | An operation is located, then its effect is measured. |
| Membership test | A solid state and a point are located, then tested. |
| CadQuery workplane description | A feature or sketch is located, then its CadQuery workplane is described. |
| Chain | The task target is reached through several relations in order. |

The task reasoning pattern is not the same as the answer format. A locate task
can return a variable name or a multiple-choice label. A measure task can return a
number, a coordinate, or a bounding box.

### 2.5 Task reasoning depth

Task reasoning depth is the number of task reasoning steps a task requires:

- **Task clue step**: applies one task clue and reduces the set of possible answers.
- **Task answer step**: produces the answer once the task target is identified.
- **Task reasoning step**: either a task clue step or a task answer step.

The depth is computed from the actual task solution sequence, not from a label.

| Pattern | Depth |
|---|---|
| Direct | 0 |
| Locate | Number of task clue steps. |
| Measure | Task clue steps plus 1 for the measurement. |
| Compare | Task clue steps plus 1 for the comparison. |
| Count | Task clue steps plus 1 for the count. |
| Rank | Task clue steps plus 1 for the ranking. |
| Effect measurement | Task clue steps plus 1 for the effect measurement. |
| Membership test | Task clue steps plus 1 for the test. |
| CadQuery workplane description | Task clue steps plus 1 for the CadQuery workplane description. |
| Chain | Number of relations followed, plus 1 for the final answer if it is computed. |

A task that names a task target and asks for its volume has depth 1, not depth
0, because the volume must still be measured. A task that names a task target
and asks which operation created it may have depth 1.

### 2.6 Geometry requirement

A step is **geometry-based** when it needs the shape the program builds:
measurements, topology, CadQuery selector results, or operation effects. A step
is **syntax-based** when it can be answered from the program text alone:
variable names, literal arguments, or operation order.

A benchmark task must have at least one geometry-based step. The share of
geometry steps is reported with the task.

## 3. Task families

A **task family** is a precise pattern with five parts:

1. a task target category;
2. an ordered list of task clue forms;
3. an answer format;
4. a depth rule;
5. a uniqueness rule.

The task family is the reusable task reasoning pattern; the task target, the task
clues, and the answer format are chosen when a task is built. This is why a task family is not a flat
label.

The canonical task families are:

| Family | Target | Clues | Answer | Depth |
|---|---|---|---|---|
| Direct | Any named entity | None | Any answer format | 0 |
| Locate | Any entity | Property, relation, comparison, aggregation, provenance, or chain | Variable name or multiple choice | Number of task clues |
| Measure | Any entity | Clues that locate it | Number, integer, coordinate, or bounding box | Clues plus 1 |
| Compare | Two entities | Clues that locate both | Yes or no, or one of the two | Clues plus 1 |
| Count | A set | Clues that define the set | Integer | Clues plus 1 |
| Rank | A set | Clues that define the set, plus an order | Integer or an entity | Clues plus 1 |
| Effect measurement | An operation | Clues that locate the operation | Number, integer, coordinate, or bounding box | Clues plus 1 |
| Membership test | A solid state and a point | Clues that locate both | Yes or no | Clues plus 1 |
| CadQuery workplane description | A feature or sketch | Clues that locate it | Structured object | Clues plus 1 |
| Chain | Any entity | An ordered sequence of relations | Variable name, multiple choice, or a measurement | Chain length plus 1 if computed |

## 4. Writing a family definition

A family definition must be precise enough that two people would build the same
tasks from it. It must state:

- the task target category;
- each task clue in order, with placeholders for sampled values;
- the answer format and the task answer step, if any;
- the depth rule;
- the uniqueness rule;
- the geometry requirement.

For example, a measure family is defined like this:

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

This is a definition, not an example. The named CadQuery workplane, the named
operation, and the area value are chosen when a task is built. A task
that does not satisfy the uniqueness rule is not generated.

## 5. Coverage

The dataset must cover:

- every task target category that the PRD claims;
- every task clue form;
- every answer format;
- every task reasoning pattern;
- every depth from 0 to 5;
- both syntax-based and geometry-based steps, with geometry required for
  benchmark tasks.

Coverage is reported by dimension, not by the old flat labels. A task
family that produces zero tasks is a gap, not a category.

## 6. What is not a task family

- An answer format alone, such as "coordinate task".
- A measurement alone, such as "volume task".
- A task target alone, such as "face task".
- A depth alone, such as "3-step task".

Those are properties of a task. A family must state the pattern that ties
them together.

## 7. Open questions

- **Q1.** Is "task family" the right term, or should this be "task
  pattern"?
- **Q2.** Is "task clue" the right public term, or should it be something
  else?
- **Q3.** Should a comparison task clue always name both entities, or may one
  entity be selected by an earlier task clue?
- **Q4.** Should "direct" be a family, or is every direct task just a
  measure with depth 1?
