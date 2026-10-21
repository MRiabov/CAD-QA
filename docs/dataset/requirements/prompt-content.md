# Prompt content

**Status:** draft, 2026-10-21. This document defines what the LLM model sees in
a CAD-QA prompt. It does not define how the prompt is rendered.

## 1. Prompt parts

A prompt has up to five parts, in this order:

1. **Program text**: the complete CadQuery program, unchanged except for
   normalization.
2. **Question**: the interrogative sentence that asks what to answer.
3. **Task clues**: a numbered list of conditions the answer must satisfy, in
   reasoning order.
4. **Choices**: a short list of multiple-choice options, only when the answer
   format is multiple choice.
5. **Answer instruction**: the required answer format and an exact example of
   its syntax.

The question is only the interrogative sentence. It is not the whole task. The
task is the program, the task target, the task clues, and the answer.

The prompt does not contain the answer or any hidden identifier.

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

- "What is the volume of the final solid?"
- "What is the volume of material removed by an operation?"
- "What is the CadQuery workplane used by an operation?"

The question is not a task clue. It tells the LLM model what task target
category the answer is about and what to answer.

## 4. Task clues

A task clue is one condition the answer must satisfy. Every task clue
corresponds to one task clue step.

### 4.1 Task clue rules

1. One task clue states one condition. If a sentence contains two independent
   conditions, split it into two task clues.
2. Task clues are ordered from broad to narrow. The order is the intended
   reasoning order. They are presented as a numbered list; the number is
   presentation, not a task reasoning step count.
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
    measurement as a task clue. Put it in the answer instruction.

### 4.2 Task clue types

| Clue type | Wording pattern |
|---|---|
| Property | "The task target has a <measurement> <comparison> <value>." |
| Relation | "The task target is <relation> <other entity>." |
| Comparison | "The task target's <measurement> is <comparison> the <measurement> of <reference>." |
| Aggregation | "Among the task targets that satisfy the previous task clues, choose the one with the <extreme> <measurement>." |
| Provenance | "The task target was created by <operation>." or "The task target uses <CadQuery profile>." |
| Chain | "The task target is <relation> <entity A>, which is <relation> <entity B>." |

The placeholders are filled with real entities and measurements when a task is
built. A task clue is never a template with placeholder text left in it.

## 5. Multiple-choice choices

When the answer format is multiple choice:

- show at least five choices, with seven as the goal;
- label the choices `A`, `B`, `C`, and so on;
- include the correct choice;
- draw every choice from the same task target category;
- describe each choice by a distinguishing geometric or construction property,
  never by a variable name or an internal identifier;
- make every description unique;
- do not let any description contain the answer or say that it is correct;
- make every distractor a plausible near miss, not random padding;
- ensure every distractor fails at least one task clue or the answer step;
- use a deterministic order.

A choice is not padding. If there are not enough plausible choices to fill the
minimum, the task is not generated.

## 6. Answer instruction

The answer instruction tells the LLM model exactly what to return. It must match
the answer format.

| Answer format | Instruction |
|---|---|
| Multiple choice | "Return exactly one label from the list above, for example `A`." |
| Number | "Return exactly one number. Use <unit>; round to 4 significant figures." |
| Integer | "Return exactly one integer." |
| Yes or no | "Return exactly one of `true` or `false`." |
| 3D coordinate | "Return exactly one coordinate tuple `(x, y, z)` in <frame>; round each value to 4 significant figures." |
| Bounding box | "Return exactly one bounding box as `{\"min\": [x, y, z], \"max\": [x, y, z]}` in <frame>; round each value to 4 significant figures." |
| Structured object | "Return exactly one JSON object with fields <field list>." |

The answer instruction always states the frame when it matters. The default
numeric precision is 4 significant figures.
It never gives the answer, and it never explains how to find the task target.

## 7. What the prompt must not contain

- The correct answer.
- Any answer data or hidden field.
- Internal identifiers.
- The number of task reasoning steps.
- A hidden task clue that is not in the task clue list.
- A task clue that is not in the hidden task solution sequence.
- A description of the graph or the generator.
- A hint that identifies the correct multiple-choice choice.
- A named entity that does not appear in the program or cannot be identified
  from it.

## 8. Worked example

This example uses a short CadQuery program and a realistic task shape. It is
illustrative; real program text comes from the CADEvolve dataset.

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

What is the volume of material removed by an operation?

1. The operation cut the cylindrical hole.

Return exactly one number, rounded to 4 significant figures.
````

Answer: `25.13` (the volume of a cylinder of radius 2 and cut depth 2, rounded to 4 significant figures).

The question names the task target category and asks for the measurement. The
task clue names the operation. The answer instruction asks for the number. The
prompt does not say "the answer is 8 pi".

## 9. Review checklist

Before a prompt is accepted:

- the question is the interrogative sentence, not the whole task;
- every task clue is one condition;
- every task clue has a matching task clue step;
- the task clue order is the intended reasoning order;
- the answer instruction matches the answer format;
- the prompt does not leak the answer;
- the prompt does not use internal terms;
- the prompt is readable by a careful human without the answers;
- a task drawn from the dataset release, not the illustrative example above, is
  used for the review sample.

## 10. Open questions

- **Q1.** How are plausible, deterministic distractors generated and validated?
  - **Option A — fixed candidate order.** Take the first N candidates by a
    stable identifier. Simple, but the choices may be clustered and easy to
    eliminate.
  - **Option B — hash order.** Order candidates by a stable hash and take the
    first N. Deterministic, but still no guarantee that the choices are
    distinguishable.
  - **Option C — near-miss perturbation, then deterministic order.** Start from
    the correct task solution and apply one controlled error: use an adjacent
    entity, the wrong solid state, the wrong operation, a swapped comparison, a
    different measurement, or an off-by-one count. Validate the result against
    the same graph, then order the choices by a stable hash.
  - **Recommendation:** C. For a multi-step task, a distractor should satisfy
    most task clues and fail at least one. For a one-step task, use a
    same-category neighbor. “80% correct” is a useful heuristic, not a literal
    threshold. The generator must be able to state why each distractor is wrong.
    If enough plausible distractors cannot be generated, reject the task.
