# Prompt content

**Status:** draft, 2026-10-21. This document defines what the LLM model sees in
a CAD-QA prompt. It does not define how the prompt is rendered.

This document owns the prompt surface. The task dimensions it renders are
defined in [`task-structure.md`](task-structure.md); the graph values it words
are defined in [`graph-content.md`](graph-content.md). It links to both and does
not repeat their closed value sets.

## 1. Prompt parts

The prompt is delivered as the user message. It has a frame convention line and
up to four parts, in this order:

1. **Program text**: the complete CadQuery program, unchanged except for
   normalization.
2. **Question**: the interrogative sentence that asks what to answer.
3. **Task clues**: a numbered list of conditions the answer must satisfy, in
   reasoning order.
4. **Choices**: a short list of multiple-choice options, only when the answer
   format is multiple choice.

The question is only the interrogative sentence; the task that contains it is
defined in [`task-structure.md`](task-structure.md).

The prompt does not contain the answer or any hidden identifier.

The prompt contains only what the task needs. The system prompt, the answer
instruction, and the submission format are harness policy: a harness adds them
from the answer metadata (`answer_format` and `answer_meaning`), and they are not
part of the dataset prompt (`DS-REQ-24`). The dataset card carries the answer
conventions a consumer needs.

### 1.1 Frame conventions

Every prompt states the direction convention once, before the program text:

> Directions use the program frame: +x is right, +y is back, +z is up.

The convention is part of the fixed prompt prefix, not a per-task variant. It is
what makes a directional word in a task clue unambiguous: "top" is the face at
the maximum z, "front" is the face at the minimum y, and so on. The words name
the extremes of the axis-aligned bounding box of the solid state, never a part
name and never a sorted-by-area rank.

| Frame name | Word |
|---|---|
| `max_x` | right |
| `min_x` | left |
| `max_y` | back |
| `min_y` | front |
| `max_z` | top |
| `min_z` | bottom |

The graph stores the frame name; the prompt renders the word from this table.

## 2. Program text

The program text is shown as normal CadQuery code. It is not shortened,
rewritten, or explained by the prompt. The LLM model reads the program to
understand the construction.

The programs come from the CADEvolve dataset. The program text is the CADEvolve
code after normalization, exactly as supplied in the CADEvolve record. It is not
reformatted into the example style below.

The program text must be the same program that produced the answer. It must
not be replaced by a simplified description.

## 3. Question

The question is the interrogative sentence in the prompt. It always names the
task target category and asks what to answer. It does not contain a condition
and does not narrow the candidates.

Examples of a question:

- "What is the volume of the target solid state?"
- "What is the signed change in volume caused by the target operation?"
- "Which CadQuery workplane satisfies these conditions?"
- "What is the shortest distance between the task target and the face touching
  the bottom of the axis-aligned bounding box?"

The question is not a task clue. It tells the LLM model what task target
category the answer is about and what to answer.

A pair answer reads the reference a task clue binds. The question names that
reference. It may cite the clue by category — "an edge from clue 1" — only when
the clue names exactly one set of that category; the category then identifies
the reference. A clue that narrows one category and binds the same category
names two sets of it, so a category citation cannot say which set it means; the
question names the reference phrase instead, such as "the face touching the
bottom of the axis-aligned bounding box". The question does not restate the
clue's condition. "Shortest" or "nearest" makes the reading unambiguous when
the bound reference set holds several members. A pair answer with no bound
reference is not rendered.

## 4. Task clues

A task clue is one condition the answer must satisfy. Every task clue
corresponds to one task clue step. Task clues are numbered list items, not
prose paragraphs.

### 4.1 Task clue rules

1. One task clue states one condition. If a list item contains two conditions,
   split it into two task clues.
2. Task clues are ordered from broad to narrow. The order is the intended
   reasoning order. They are presented as a numbered list; the number is
   presentation, not a task reasoning step count. Every clue must also be
   necessary, so a later clue may not make an earlier one redundant
   (`task-structure.md` §2.2).
3. Each task clue must be checkable against the program and the shape it
   builds.
4. Each task clue must be understandable without internal terms.
5. A task clue must not name the answer.
6. A task clue must not say how many steps the task has.
7. A task clue must not use words such as `candidate`, `graph`, `node`,
   `relation`, `measurement scope`, or `selector result`. Say the thing in plain
   language.
8. A task clue must not say "first" or "last" unless the program has a clear
   order and the phrase is defined. Prefer "the operation that appears last in
   the program" or describe the operation by what it does.
9. A task clue must not repeat the program text. Refer to the entity the program
   builds, not to its variable name.
10. If the answer is a measurement of the task target, do not write that
    measurement as a task clue. It is the answer; the answer conventions state
    it.
11. A clue states a number without a unit when the answer conventions supply
    one; an angle clue says degrees.

### 4.2 Task clue types

The clue types and their meanings are defined in
[`task-structure.md`](task-structure.md) section 2.2. This table gives the
wording for each clue type; it does not redefine them.

| Clue type | Wording pattern |
|---|---|
| Property, measurement | "The task target has a <measurement> <comparison> <value>." |
| Property, measurement range | "The task target has a <measurement> between <min> and <max>." |
| Property, direction | "The angle between the outward normal of the task target and <axis> is <comparison> <value> degrees." |
| Property, categorical feature | "The task target is <face surface kind>." / "The task target touches the <position> of the axis-aligned bounding box." |
| Relation, named | "The task target is <relation> <other entity>." |
| Relation, angle | "The angle between the task target and <reference> is <comparison> <value> degrees." |
| Comparison | "The <measurement> of the task target is <comparison> the <measurement> of <reference>." |
| Aggregation | "Among the remaining <categories>, choose the one with the <extreme> <measurement>." |
| Provenance | "The task target was created by <operation>." or "The task target uses <CadQuery profile>." |

A relation clue is a named relation or a measured angle. The measured-angle form
states the number; "parallel" and "perpendicular" are renderings of 0 or 180 and
90 degrees and are not separate relations.

A containment clue reads with the task target on the contained side: "The target
edge is an edge of a cylindrical face", or "The target vertex is an endpoint of
an edge whose length is greater than 10". The opposite direction, with the
container as the target, carries the same information and is a wording gap, not a
different clue: the relation is written "The task target is <relation> the
<other entity>", so its relation phrase is adjectival or prepositional
("adjacent to", "an edge of"). From the container side containment is a verb
("contains"), and that sentence has no frame yet.

A chain is a P2 sequence of relation clues: each relation is its own numbered
list item and one task clue step. The sequence rule is in `task-structure.md`.

The placeholders are filled with real entities and measurements when a task is
built. A task clue is never a template with placeholder text left in it.

A categorical feature clue states equality, not a comparison. Position is
set-valued: "touches the top of the axis-aligned bounding box" is true of every
face that lies in that extreme plane, however many there are. The phrase names the
bounding box every time; "the top" alone reads as a part name. A direction is not
a categorical feature: the outward normal is continuous, so the clue measures the
angle to the axis it names and states the number.

A clue does not name a specific entity as "the top face"; a reference names a set
by a condition ("a face facing +z", "a cylindrical face") or by an earlier clue
("the faces from clue 1"). A direction condition reads "facing <axis>" when the
angle is zero, and names the angle when it is not. A pair-angle relation names
the angle too; the renderer may use "parallel" or "perpendicular" when the angle
is 0, 180, or 90 degrees.

A reference may also state one measurement condition: "a face whose area is
greater than 10", or an angle: "a face whose outward normal is within 45 degrees
of +z". Exactly one condition is allowed, because a reference is one statement
and must be unambiguous on its own. A referenced entity that needs two
conditions, and so two steps of its own, is out of P0 scope; it is the multi-set
question in `task-structure.md` section 8.

A reference may also be an `aggregated` reduction of an earlier set of faces:
"the largest of the faces from clue 1" (P1). It is one reference, not a second
condition.

A threshold is the narrowing strength, not a tolerance around an exact match. For
the angle, one degree selects the faces that really face that axis, 45 degrees
selects a cone of them, and 90 degrees selects every planar face and is therefore
not a clue. A threshold sits between two candidate values, at least the
clear-case margin from each (`graph-content.md` section 4.2).

Every rendered noun phrase takes its determiner from what its description
selects in the program: `the` for exactly one element, `a` for a condition that
selects several, and the plural for a set bound by an earlier clue. No template
supplies an article.

An operation, CadQuery profile, or CadQuery workplane description takes `the`
only when it selects exactly one element of its category in the program. Two
`cutBlind` calls make `a cutBlind operation` correct and `the cutBlind operation`
ambiguous; two circles do the same to `the circular CadQuery profile`. Repeats
are common: several boxes, several holes, several cuts, several CadQuery profiles.

When the description alone does not select one, it has two ways out. It stays
indefinite, which narrows to every element that any match produced ("created by a
cutBlind operation", "built from a circular CadQuery profile"). Or it selects one by a
condition the LLM model can read: a stated argument ("the cutBlind operation with
depth 2") or its place in the program ("the cutBlind operation that appears last
in the program"). A description that cannot
select one is not used: the LLM model cannot tell which entity the clue means, so
the clue is unanswerable even though the definition points at one entity.

A description of a CadQuery profile names the CadQuery profile kind: circular,
rectangular, elliptical, polygonal, or slot. Every other 2D boundary has the
CadQuery profile kind `other`, which has no noun, so a clue that would have to
name it is not built; the constructor measures it instead: area in P0, and
perimeter in P1.

A prompt does not describe a CadQuery workplane. A program builds on one named
CadQuery workplane in almost every case, so a phrase that names it selects the
whole program and narrows nothing; a face-derived or custom frame has no phrase at
all. A CadQuery workplane stays a graph entity and a P1 answer; whether it is a
task target category is open in `task-structure.md` section 8.

## 5. Multiple-choice choices

When the answer format is multiple choice, P0 and P1 require:

- at least five choices, with seven as the goal;
- labels `A`, `B`, `C`, and so on;
- the correct choice present;
- every choice a valid answer in the same answer space: same task target category
  for identity, same unit and precision for numbers, same frame for coordinates,
  and the documented fields for structured answers;
- for identity choices, describe each by a distinguishing geometric or
  construction property, never by a variable name or an internal identifier;
- every choice unique;
- no choice description saying that it is correct or explaining how to select
  it;
- every choice a real candidate from the construction, not padding;
- a deterministic order.

P2 adds examiner-style distractor quality:

- every distractor is a plausible near miss, not random padding;
- every distractor fails at least one task clue or the answer step;
- the generator records why each distractor is wrong.

A choice is not padding. For P0 and P1, if there are not enough real candidates
to fill the minimum, the task is not generated. For P2, if there are not enough
plausible distractors, the task is not generated.

## 6. Answer conventions are not prompt content

The dataset prompt does not state the answer format, an example of its syntax, or
how to submit an answer. Those are harness policy (`DS-REQ-24`): a harness builds
its answer instruction and submit tool from the row's `answer_format` and
`answer_meaning`. The release dataset card states the conventions a consumer needs —
units, precision, the angle and distance conventions, and the signed material
change ([`release-dataset-contract.md`](release-dataset-contract.md#8-dataset-card)).
The `answer_format` and `answer_meaning` columns are the machine-readable form;
CadQuery is unitless, so there is no per-row unit column.

## 7. What the prompt must not contain

- The correct answer, meaning the answer value. A multiple-choice label is not
  answer data: every label appears in the list.
- Any answer data or hidden field.
- Internal identifiers.
- The number of task reasoning steps.
- A hidden task clue that is not in the task clue list.
- A task clue that is not in the hidden task solution sequence.
- A description of the graph or the generator.
- A hint that identifies the correct multiple-choice choice.
- An entity reference that does not appear in the program or cannot be
  identified from it.

## 8. Worked example

This example uses a short CadQuery program and a realistic task shape. It is
illustrative; real program text comes from the CADEvolve dataset.

Program:

```python
import cadquery as cq

result = cq.Workplane("XY").cylinder(2, 2)
```

Prompt:

````text
Directions use the program frame: +x is right, +y is back, +z is up.

    import cadquery as cq

    result = cq.Workplane("XY").cylinder(2, 2)

What is the volume of the target solid state?
````

Answer: `25.13` (a cylinder of radius 2 and height 2 has volume 8π, rounded to 4
significant figures).

The question names the task target category and asks for the measurement. The
program has one solid state producing operation, so the question identifies the
final solid state directly and the task has no task clue. The harness adds the
answer instruction and submission format; the prompt does not say "the answer is
8 pi".

## 9. Review checklist

Before a prompt is accepted:

- the question is the interrogative sentence, not the whole task;
- every task clue is one condition;
- every task clue has a matching task clue step;
- the task clue order is the intended reasoning order;
- the prompt contains no answer instruction or submission syntax;
- the prompt does not leak the answer;
- the prompt does not use internal terms;
- the prompt is readable by a careful human without the answers;
- a task drawn from the dataset release, not the illustrative example above, is
  used for the review sample.

## 10. P2 near-miss implementation

The requirement for P2 near-miss choices is section 5. The generation and
validation mechanism is an implementation question in pipeline stage `03`,
tracked as Q6 in
[`../implementation/pipeline/03-task-generation/03b-construct-task-definitions/README.md`](../implementation/pipeline/03-task-generation.md).
A mechanism that cannot meet section 5 is an implementation defect; it does not
relax the requirement. P0 and P1 require real, unique, non-leaking choices.
