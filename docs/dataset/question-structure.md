# Question structure

**Status:** draft, 2026-10-21. This document defines how a CAD-QA question is
described. It replaces the flat question list in the PRD.

## 1. Why a flat list is wrong

The previous list mixed several different things:

- "Direct fact" described reasoning depth.
- "Give a coordinate" described an answer shape.
- "Measure a distance" described a measurement.
- "Follow a chain" described a reasoning pattern.
- "Locate by property" described how the target is found.

Those are not peers. Treating them as one list makes some questions look
similar when they are not, and hides gaps.

A question is a combination of independent dimensions. Once the dimensions are
separate, every question can be described precisely, and the dataset can be
checked for real coverage instead of counting labels.

## 2. The dimensions of a question

### 2.1 Target

The target is the entity or value the question asks about.

| Target category | What it is |
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

A question has exactly one target category. If the answer is a measurement taken
from an entity, the entity is the target and the measurement is the answer. The
target category is not the answer shape.

### 2.2 Clue

A clue is one public sentence in the prompt that states a condition the answer
must satisfy. A clue is not a hint and not an example. It is a condition that
can be checked against the graph.

Every clue has one of these forms:

| Clue form | What it says |
|---|---|
| Property | The target has a property or measurement with a stated value or range. |
| Relation | The target stands in a named relation to another entity. |
| Comparison | The target's measurement compares to a reference measurement. |
| Aggregation | The target is the extreme, the rank, or the count of a set. |
| Provenance | The target was created by an operation, uses a CadQuery profile, or sits on a CadQuery workplane. |
| Chain | The target is reached through an ordered sequence of relations. |

A clue may combine a relation with a property, for example "the face adjacent
to the selected face whose area is larger than the selected face". It is still
one clue if it names one condition.

The information in a clue that rules out candidates is its **disambiguating
information**. "Disambiguator" is a useful word in conversation, but the
canonical term for the public object is **clue**.

A question may also need a **computation** after the target is identified, such
as reporting the volume of the selected solid state. A computation is not a
clue and is not written as one. It belongs in the answer instruction.

### 2.3 Answer shape

The answer shape is what the LLM model must return.

| Answer shape | What the LLM model returns |
|---|---|
| Multiple choice | One label from a short list of choices. |
| Variable name | One name that appears in the CadQuery program. |
| Number | One finite numeric value. |
| Integer | One whole number. |
| Yes or no | One boolean value. |
| 3D coordinate | One point. |
| Bounding box | One minimum corner and one maximum corner. |
| Structured object | One small object with named fields. |

The answer shape is independent of the target and the clue. A question about a
face can have a multiple-choice answer, a variable-name answer, a coordinate
answer, or a bounding-box answer.

### 2.4 Reasoning pattern

The reasoning pattern is how the target is found.

| Pattern | What happens |
|---|---|
| Direct | The target is named, and the question asks for a fact about it. |
| Locate | One or more clues narrow the candidates to one target. |
| Measure | The target is located, then a measurement of it is reported. |
| Compare | Two targets are located, then compared. |
| Count | A set is located, then counted. |
| Rank | A set is located, then ordered and ranked. |
| Effect | An operation is located, then its effect is measured. |
| Membership | A solid state and a point are located, then tested. |
| CadQuery workplane | A feature or sketch is located, then its CadQuery workplane is described. |
| Chain | The target is reached through several relations in order. |

The pattern is not the same as the answer shape. A locate question can return a
variable name or a multiple-choice label. A measure question can return a
number, a coordinate, or a bounding box.

### 2.5 Reasoning depth

Reasoning depth is the number of steps a question requires:

- **Narrowing step**: applies one clue and reduces the set of possible answers.
- **Computation step**: produces the answer once the target is identified.
- **Reasoning step**: either a narrowing step or a computation step.

The depth is computed from the actual solution path, not from a label.

| Pattern | Depth |
|---|---|
| Direct | 0 |
| Locate | Number of narrowing steps. |
| Measure | Narrowing steps plus 1 for the measurement. |
| Compare | Narrowing steps plus 1 for the comparison. |
| Count | Narrowing steps plus 1 for the count. |
| Rank | Narrowing steps plus 1 for the ranking. |
| Effect | Narrowing steps plus 1 for the effect measurement. |
| Membership | Narrowing steps plus 1 for the test. |
| CadQuery workplane | Narrowing steps plus 1 for the CadQuery workplane description. |
| Chain | Number of relations followed, plus 1 for the final answer if it is computed. |

A question that names a target and asks for its volume has depth 1, not depth
0, because the volume must still be measured. A question that names a target
and asks which operation created it may have depth 1.

### 2.6 Geometry requirement

A step is **geometry-based** when it needs the shape the program builds:
measurements, topology, CadQuery selector results, or operation effects. A step
is **syntax-based** when it can be answered from the program text alone:
variable names, literal arguments, or operation order.

A benchmark question must have at least one geometry-based step. The share of
geometry steps is reported with the question.

## 3. Question families

A **question family** is a precise pattern with five parts:

1. a target category;
2. an ordered list of clue forms;
3. an answer shape;
4. a depth rule;
5. a uniqueness rule.

The family is the reasoning pattern; the target, the clues, and the answer
shape are chosen when a question is built. This is why a family is not a flat
label.

The canonical families are:

| Family | Target | Clues | Answer | Depth |
|---|---|---|---|---|
| Direct | Any named entity | None | Any answer shape | 0 |
| Locate | Any entity | Property, relation, comparison, aggregation, provenance, or chain | Variable name or multiple choice | Number of clues |
| Measure | Any entity | Clues that locate it | Number, integer, coordinate, or bounding box | Clues plus 1 |
| Compare | Two entities | Clues that locate both | Yes or no, or one of the two | Clues plus 1 |
| Count | A set | Clues that define the set | Integer | Clues plus 1 |
| Rank | A set | Clues that define the set, plus an order | Integer or an entity | Clues plus 1 |
| Effect | An operation | Clues that locate the operation | Number, integer, coordinate, or bounding box | Clues plus 1 |
| Membership | A solid state and a point | Clues that locate both | Yes or no | Clues plus 1 |
| CadQuery workplane | A feature or sketch | Clues that locate it | Structured object | Clues plus 1 |
| Chain | Any entity | An ordered sequence of relations | Variable name, multiple choice, or a measurement | Chain length plus 1 if computed |

## 4. Writing a family definition

A family definition must be precise enough that two people would build the same
questions from it. It must state:

- the target category;
- each clue in order, with placeholders for sampled values;
- the answer shape and the computation, if any;
- the depth rule;
- the uniqueness rule;
- the geometry requirement.

For example, a measure family is defined like this:

```text
Target: a face of the final solid state.
Clue 1: the face is parallel to a named CadQuery workplane.
Clue 2: the face is adjacent to the face created by a named operation.
Clue 3: among the faces that satisfy clues 1 and 2, the face with the largest
        area.
Answer: the area of the selected face, as a number.
Depth: 3 (two narrowing clues and one computation).
Uniqueness: exactly one face satisfies clues 1 and 2, and the largest area is
            achieved by exactly one of them. Otherwise the question is rejected.
Geometry: all three steps are geometry-based.
```

This is a definition, not an example. The named CadQuery workplane, the named
operation, and the area value are chosen when a question is built. A question
that does not satisfy the uniqueness rule is not generated.

## 5. Coverage

The dataset must cover:

- every target category that the PRD claims;
- every clue form;
- every answer shape;
- every reasoning pattern;
- every depth from 0 to 5;
- both syntax-based and geometry-based steps, with geometry required for
  benchmark questions.

Coverage is reported by dimension, not by the old flat labels. A question
family that produces zero questions is a gap, not a category.

## 6. What is not a question family

- An answer shape alone, such as "coordinate question".
- A measurement alone, such as "volume question".
- A target alone, such as "face question".
- A depth alone, such as "3-step question".

Those are properties of a question. A family must state the pattern that ties
them together.

## 7. Open questions

- **Q1.** Is "question family" the right term, or should this be "question
  pattern"?
- **Q2.** Is "clue" the right public term, or should the PRD use
  "disambiguator"?
- **Q3.** Should a comparison clue always name both entities, or may one entity
  be selected by an earlier clue?
- **Q4.** Should "direct" be a family, or is every direct question just a
  measure with depth 1?
