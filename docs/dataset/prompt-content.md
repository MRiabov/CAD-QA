# Prompt content

**Status:** draft, 2026-10-21. This document defines what the LLM model sees in
a CAD-QA prompt. It does not define how the prompt is rendered.

## 1. Prompt parts

A prompt has five parts, in this order:

1. **Program text**: the complete CadQuery program, unchanged except for
   normalization.
2. **Task statement**: one sentence that names the target category and says
   what the question is about.
3. **Clues**: an ordered list of conditions the answer must satisfy.
4. **Choices**: a short list of multiple-choice options, only when the answer
   shape is multiple choice.
5. **Answer instruction**: the required answer shape and an exact example of
   its syntax.

The prompt does not contain the answer, the answer key, or any hidden
identifier.

## 2. Program text

The program text is shown as normal CadQuery code. It is not shortened,
rewritten, or explained by the prompt. The LLM model reads the program to
understand the construction.

The program text must be the same program that produced the answer. It must
not be replaced by a simplified description.

## 3. Task statement

The task statement names the target category and the question in plain
language. It does not contain a condition and does not narrow the candidates.

Examples of a task statement:

- "The question is about a face of the final solid."
- "The question is about the operation that removed material to produce the
  hole."
- "The question is about the CadQuery workplane used by the selected sketch."

The task statement is not a clue. It only tells the LLM model what category of entity
the answer is about.

## 4. Clues

A clue is one condition the answer must satisfy. Every clue corresponds to one
narrowing step.

### 4.1 Clue rules

1. One clue states one condition. If a sentence contains two independent
   conditions, split it into two clues.
2. Clues are ordered from broad to narrow. The order is the intended reasoning
   order.
3. Each clue must be checkable against the program and the shape it builds.
4. Each clue must be understandable without internal terms.
5. A clue must not name the answer.
6. A clue must not say how many steps the question has.
7. A clue must not use words such as `candidate`, `graph`, `node`, `relation`,
   `measurement scope`, or `selector result`. Say the thing in plain language.
8. A clue must not say "first" or "last" unless the program has a clear order
   and the phrase is defined. Prefer "the operation that appears last in the
   program" or name the operation by its visible variable.
9. A clue must not repeat the program text. Refer to the visible variable or
   the entity the program builds.
10. If the question needs a measurement of the target, do not write the
    measurement as a clue. Put it in the answer instruction.

### 4.2 Clue forms

| Form | Wording pattern |
|---|---|
| Property | "The target has a <measurement> <comparison> <value>." |
| Relation | "The target is <relation> <other entity>." |
| Comparison | "The target's <measurement> is <comparison> the <measurement> of <reference>." |
| Aggregation | "Among the targets that satisfy the previous clues, choose the one with the <extreme> <measurement>." |
| Provenance | "The target was created by <operation>." or "The target uses <CadQuery profile>." |
| Chain | "The target is <relation> <entity A>, which is <relation> <entity B>." |

The placeholders are filled with real entities and measurements when a
question is built. A clue is never a template with placeholder text left in it.

## 5. Multiple-choice choices

When the answer shape is multiple choice:

- show at least five and at most seven choices;
- label the choices `A`, `B`, `C`, and so on;
- include the correct choice;
- draw every choice from the same target category;
- describe each choice by a visible program name or a distinguishing property,
  never by an internal identifier;
- make every description unique;
- do not let any description contain the answer or say that it is correct;
- use a deterministic order.

A choice is not padding. If there are not enough real candidates to fill the
minimum, the question is not generated.

## 6. Answer instruction

The answer instruction tells the LLM model exactly what to return. It must match
the answer shape.

| Answer shape | Instruction |
|---|---|
| Multiple choice | "Return exactly one label from the list above, for example `A`." |
| Variable name | "Return exactly one variable name from the program." |
| Number | "Return exactly one number. Use <unit>; round to <precision>." |
| Integer | "Return exactly one integer." |
| Yes or no | "Return exactly one of `true` or `false`." |
| 3D coordinate | "Return exactly one coordinate tuple `(x, y, z)` in <frame>; round to <precision>." |
| Bounding box | "Return exactly one bounding box as `{\"min\": [x, y, z], \"max\": [x, y, z]}` in <frame>; round to <precision>." |
| Structured object | "Return exactly one JSON object with fields <field list>." |

The answer instruction always states the frame and precision when they matter.
It never gives the answer, and it never explains how to find the target.

## 7. What the prompt must not contain

- The correct answer.
- The answer key or any hidden field.
- Internal identifiers.
- The number of reasoning steps.
- A hidden clue that is not in the clue list.
- A clue that is not in the hidden solution path.
- A description of the graph or the generator.
- A hint that identifies the correct multiple-choice choice.
- A named entity that does not appear in the program or cannot be identified
  from it.

## 8. Worked example

This example uses a real CadQuery program and a real question. It is not a
placeholder.

Program:

```python
import cadquery as cq

result = (
    cq.Workplane("XY")
    .box(10, 20, 5)
    .faces(">Z")
    .workplane()
    .circle(2)
    .cutBlind(-2)
)
```

Prompt:

````text
Given the CadQuery script below, answer the question by reasoning about the
CAD construction.

    import cadquery as cq

    result = (
        cq.Workplane("XY")
        .box(10, 20, 5)
        .faces(">Z")
        .workplane()
        .circle(2)
        .cutBlind(-2)
    )

The question is about the operation that removed material to produce the hole.

1. The target operation is the one that cut the cylindrical hole.
2. Report the volume of material that operation removed.

Return exactly one number.
````

Answer: `25.132741` (the volume of a cylinder of radius 2 and depth 2).

The task statement names the target category. The clue names the operation. The
answer instruction asks for the measurement. The prompt does not say "the
answer is 8 pi".

## 9. Review checklist

Before a prompt is accepted:

- every clue is one condition;
- every clue has a matching narrowing step;
- the clue order is the intended reasoning order;
- the answer instruction matches the answer shape;
- the prompt does not leak the answer;
- the prompt does not use internal terms;
- the prompt is readable by a careful human without the answer key;
- a real dataset row, not an invented example, is used for the review sample.

## 10. Open questions

- **Q1.** Should the task statement always name the target category, or may it
  be part of the first clue?
- **Q2.** Should clues be numbered, or presented as a paragraph?
- **Q3.** Should the answer instruction include the unit and precision for every
  numeric answer, or only when the unit is not obvious?
- **Q4.** Should multiple-choice descriptions use variable names, geometric
  descriptions, or both?
