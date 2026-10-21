# Dataset terminology

**Status:** proposal for owner approval, 2026-10-21. This document does not
edit `docs/glossary.md`. A term becomes canonical only after the owner approves
it.

## 1. Core terms

| Term | Meaning |
|---|---|
| **CadQuery program** | One program from the corpus, written in CadQuery. |
| **CAD model** | The shape a CadQuery program builds. In split rules, one CAD model means one CadQuery program. |
| **Question** | One task instance: a program, a target, a set of clues, and one answer. |
| **Question family** | A precise reasoning pattern that can produce many questions: a target category, an ordered list of clue forms, an answer shape, a depth rule, and a uniqueness rule. |
| **Target** | The entity or value the question asks about. |
| **Clue** | One public sentence in the prompt that states a condition the answer must satisfy. |
| **Disambiguator** | Informal word for the information in a clue that rules out candidates. The canonical public object is a clue. |
| **Narrowing step** | The hidden graph operation that applies one clue and reduces the set of possible answers. |
| **Computation step** | The hidden operation that produces the answer once the target is identified. |
| **Reasoning step** | A narrowing step or a computation step. |
| **Solution path** | The ordered list of narrowing and computation steps that leads from the question to the answer. |
| **Answer shape** | The form of the answer: multiple choice, variable name, number, integer, yes or no, 3D coordinate, bounding box, or structured object. |
| **Multiple-choice choices** | The short list of options shown for a multiple-choice answer. |
| **Answer instruction** | The part of the prompt that tells the LLM model which answer shape to return and in what syntax. |
| **Program text** | The CadQuery program shown in the prompt. |
| **Prompt** | Everything the LLM model sees for one question: program text, task statement, clues, optional choices, and answer instruction. |
| **Answer key** | The private record of the correct answer and the evidence for it. |
| **CAD fact graph** | The typed facts about one CadQuery program and the shape it builds. |
| **Graph entity** | One entity in the CAD fact graph, such as a face, edge, operation, or region. |
| **Relation** | A typed link between two graph entities. |
| **Measurement** | A numeric or geometric fact about a graph entity or a pair of entities. |
| **Evidence** | The record of how a measurement was obtained: measured by running CadQuery, or derived exactly from the program. |
| **State** | The shape before or after an operation, or the final shape. |
| **Warmup subset** | The labeled set of 0- and 1-step questions inside the dataset. It is useful for training, not a separate dataset. |
| **Curriculum** | The order in which questions are presented, from easier to harder. |
| **Dataset release** | An immutable, validated, versioned set of questions and answer keys. |

## 2. Replacements

| Old term | New term |
|---|---|
| `source` | CadQuery program |
| `execution record` | program execution record |
| `ontology graph` | CAD fact graph |
| `node` | graph entity |
| `clause` | clue |
| `candidate trace` | solution path |
| `task family` | question family |
| `hop count` | reasoning step count, or reasoning depth |
| `dataset row` | question, or dataset entry |
| `candidate` | multiple-choice choice (public), or possible answer (hidden) |
| `release` | dataset release |
| `quarantine` | non-release-ready |
| `selector` | CadQuery selector |
| `workplane` | CadQuery workplane |
| `profile` | CadQuery profile |
| `stage` | pipeline stage, or training stage |
| `gate` | quality requirement |
| `tracked` | recorded or documented |

## 3. Naming decisions needed

- **Q1.** Should the graph be called the **CAD fact graph**, the **CAD model
  graph**, or something else?
- **Q2.** Should the public condition be called a **clue** or a
  **disambiguator**? This document uses clue and treats disambiguator as
  informal.
- **Q3.** Should the reasoning pattern be called a **question family**, a
  **question pattern**, or a **question category**?
- **Q4.** Should "direct" be a question family, or is a direct question a
  measure family with a named target and one computation step?
- **Q5.** Is "narrowing step" clear, or should it be "graph step", "filter
  step", or "constraint step"?
- **Q6.** Should "multiple-choice choices" be shortened to "choices" after the
  first use?

## 4. Terms to avoid

These words caused ambiguity in the previous documentation:

- **`source`** for a CadQuery program;
- **`trace`** for anything other than a program execution record;
- **`node`** for a graph entity;
- **`clause`** for a clue or a narrowing step;
- **`candidate`** for both a hidden possible answer and a public choice;
- **`hop`** for a reasoning step;
- **`family`** without saying question family;
- **`release`** without saying dataset release;
- **`stage`** without saying pipeline stage or training stage;
- **`gate`** without naming the requirement.
