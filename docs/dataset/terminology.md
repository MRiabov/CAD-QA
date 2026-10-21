# CAD-QA dataset terminology

**Status:** proposal for owner approval, 2026-10-21. This document does not
edit `docs/glossary.md`. A term becomes canonical only after the owner approves
it.

## 1. Core terms

| Term | Meaning |
|---|---|
| **Task** | One dataset instance: a CadQuery program, a task target, a set of task clues, and one answer. Use "dataset task" when it could be confused with an internal task. |
| **Question** | The interrogative sentence in the prompt. It is not the whole task. |
| **Clue type** | The category of condition a task clue states: property, relation, comparison, aggregation, provenance, or chain. |
| **Answer meaning** | What the answer is about, independent of how it is returned: identity, volume, area, length, distance, angle, count, rank, membership, coordinate, bounding box, CadQuery workplane state, material change, topology change, or validity. |
| **Task target** | The entity or value the task asks about. |
| **Task clue** | One public sentence in the prompt that states a condition the answer must satisfy. |
| **Task clue step** | The hidden graph operation that applies one task clue and reduces the set of possible answers. |
| **Task answer step** | The hidden operation that produces the answer once the task target is identified. |
| **Task reasoning step** | A task clue step or a task answer step. |
| **Task solution sequence** | The ordered task clue steps and task answer step that solve the task. |
| **Answer format** | The form of the answer: multiple choice, variable name, number, integer, yes or no, 3D coordinate, bounding box, or structured object. |
| **Multiple-choice choices** | The short list of options shown for a multiple-choice answer. |
| **Answer instruction** | The part of the prompt that tells the LLM model which answer format to return and in what syntax. |
| **Program text** | The CadQuery program shown in the prompt. |
| **Prompt** | Everything the LLM model sees for one task: program text, question, task clues, optional choices, and answer instruction. |
| **Answer key** | The private record of the correct answer and the evidence for it. |
| **CAD graph** | The graph of CAD entities, relations, and measurements for one CadQuery program and the shape it builds. |
| **CAD graph element** | One entity, relation, or measurement in the CAD graph. |
| **Graph entity** | One entity in the CAD graph, such as a face, edge, operation, or region. |
| **Relation** | A named link between two graph entities. |
| **Measurement** | A numeric or geometric value about a graph entity or a pair of entities. |
| **Evidence** | The record of how a measurement was obtained: measured by running CadQuery, or derived exactly from the program. |
| **Solid state** | The shape before or after an operation, or the final shape. |
| **Warmup subset** | The labeled set of 0- and 1-step tasks inside the dataset. It is useful for training, not a separate dataset. |
| **Curriculum** | The order in which tasks are presented, from easier to harder. |
| **Dataset release** | An immutable, validated, versioned set of tasks and answer keys. |

## 2. How terms compose

Terms are built from words the reader already knows. A term should be
understandable from its parts, not from a definition that introduces a new
magic word.

| Composed term | Parts | Meaning |
|---|---|---|
| Task target | task + target | The target of a task. |
| Task clue | task + clue | A clue in a task prompt. |
| Task clue step | task + clue + step | The hidden step that applies one task clue. |
| Task answer step | task + answer + step | The hidden step that produces the task answer. |
| Task reasoning step | task + reasoning + step | A task clue step or a task answer step. |
| Task solution sequence | task + solution + sequence | The ordered task clue steps and task answer step that solve the task. |
| Task reasoning depth | task + reasoning + depth | The number of task reasoning steps a task requires. |
| Clue type | clue + `type` | The category of condition a task clue states. |
| Answer meaning | answer + meaning | What the answer is about. |
| Answer format | answer + format | The form of the answer. |
| Answer instruction | answer + instruction | The prompt part that states the answer format. |
| Solid state | solid + state | The shape before or after an operation, or the final shape. |
| CAD graph | CAD + graph | The graph of CAD entities, relations, and measurements for a CadQuery program and its shape. |
| Warmup subset | warmup + subset | A labeled subset of easier tasks. |
| Dataset release | dataset + release | An immutable, validated dataset. |

Terms that were replaced because they were not composed from the domain:

| Avoided term | Why | Composed term |
|---|---|---|
| computation step | "computation" could mean anything in software. | task answer step |
| solution path | "path" is already a CAD concept. | task solution sequence |
| answer shape | "shape" is a CAD concept. | answer format |
| disambiguator | only means something after a definition. | task clue |
| narrowing step | "narrowing" is a metaphor. | task clue step |

## 3. Replacements

| Old term | New term |
|---|---|
| `source` | CadQuery program |
| `execution record` | program execution record |
| `ontology graph` | CAD graph |
| `node` | graph entity |
| `clause` | task clue |
| `candidate trace` | task solution sequence |
| `question` (the whole instance) | task |
| `question family` | removed; use clue type and answer meaning |
| `target` | task target |
| `clue` | task clue |
| `hop count` | task reasoning step count, or task reasoning depth |
| `dataset row` | task, or dataset entry |
| `candidate` | multiple-choice choice (public), or possible answer (hidden) |
| `release` | dataset release |
| `quarantine` | non-release-ready |
| `selector` | CadQuery selector |
| `workplane` | CadQuery workplane |
| `profile` | CadQuery profile |
| `stage` | pipeline stage, or training stage |
| `gate` | quality requirement |
| `tracked` | recorded or documented |

## 4. Naming decisions

- The public condition is a **task clue**.
- The step that applies a task clue is a **task clue step**.
- The step that produces the answer is a **task answer step**.
- The ordered steps that solve the task are the **task solution sequence**.
- The form of the answer is the **answer format**.
There are no task types, task families, or task patterns. The old generator used
hard-coded task families; the replacement chooses a task target and a task
solution sequence from the CAD graph. Coverage and balance are reported by
clue type, answer meaning, answer format, and task reasoning depth.

## 5. Terms to avoid

These words caused ambiguity in the previous documentation:

- **`source`** for a CadQuery program;
- **`trace`** for anything other than a program execution record;
- **`node`** for a graph entity;
- **`clause`** for a task clue or a task clue step;
- **`candidate`** for both a hidden possible answer and a public choice;
- **`hop`** for a task reasoning step;
- **`family`** for a group of tasks; use clue type and answer meaning;
- **`release`** without saying dataset release;
- **`stage`** without saying pipeline stage or training stage;
- **`gate`** without naming the requirement;
- **`question`** for the whole task rather than the interrogative sentence;
- **`type`** or **`pattern`** as a way to group tasks; use clue type and answer meaning.
