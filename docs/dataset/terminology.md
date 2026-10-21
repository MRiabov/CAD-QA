# CAD-QA dataset terminology

**Status:** proposal for owner approval, 2026-10-21. This document does not
edit `docs/glossary.md`. A term becomes canonical only after the owner approves
it.

**Scope:** a **domain term** may appear in the PRD. An **internal term** describes
how the generator represents or computes something and must not appear in the
PRD. If a product document needs an internal concept, use the domain term or
describe the user-visible outcome.

## 1. Core terms

| Term | Scope | Meaning |
|---|---|---|
| **Task** | Domain | One dataset instance: a CadQuery program, a task target, a set of task clues, and one answer. Use "dataset task" when it could be confused with an internal task. |
| **Question** | Domain | The interrogative sentence in the prompt. It is not the whole task. |
| **Difficulty step** | Domain | One step of reasoning a task requires. The PRD uses this; the technical specification derives it from the task solution sequence. |
| **Difficulty level** | Domain | One of the step-count groups used to describe difficulty: 0, 1, 2, 3, 4, 5. |
| **Difficulty coverage plan** | Domain | The published table that states which target categories, clue types, answer meanings, and answer formats are available at each difficulty level, and why a value is not available. |
| **Clue type** | Domain | The category of condition a task clue states: property, relation, comparison, aggregation, provenance, or chain. |
| **Answer meaning** | Domain | What the answer is about, independent of how it is returned: identity, volume, area, length, distance, angle, count, rank, membership, position, extent, CadQuery workplane state, material change, topology change, or validity. |
| **Task target** | Domain | The entity or value the task asks about. |
| **Task target category** | Domain | The category of the task target. It is a coverage dimension, not a percentage-balance dimension at each difficulty level. |
| **Task clue** | Domain | One public sentence in the prompt that states a condition the answer must satisfy. |
| **Task reasoning step** | Internal | A task clue step or a task answer step. Public documents say difficulty step. |
| **Task reasoning depth** | Internal | The number of task reasoning steps; computed from the task solution sequence. Public documents say difficulty. |
| **Task clue step** | Internal | The hidden graph operation that applies one task clue and reduces the set of possible answers. |
| **Task answer step** | Internal | The hidden operation that produces the answer once the task target is identified. |
| **Task solution sequence** | Internal | The ordered task clue steps and task answer step that solve the task. |
| **Depth support table** | Internal | The generator-side table that records which dimension values can occur at each task reasoning depth, and why not. The public form is the difficulty coverage plan. |
| **Per-depth coverage** | Internal | Every value supported at a task reasoning depth appears at that depth. Public documents say coverage at every difficulty level. |
| **Conditional release share** | Internal | A value's share among the values supported at a depth, used as the comparison base for per-depth balance. |
| **Per-depth balance** | Internal | For clue type, answer meaning, and answer format, a supported value's share at a depth is between half and twice its conditional release share. Public documents say balance at every difficulty level. |
| **Answer format** | Domain | The form of the answer: multiple choice, variable name, number, integer, yes or no, 3D coordinate, bounding box, or structured object. |
| **Multiple-choice choices** | Domain | The short list of options shown for a multiple-choice answer. |
| **Answer instruction** | Domain | The part of the prompt that tells the LLM model which answer format to return and in what syntax. |
| **Program text** | Domain | The CadQuery program shown in the prompt. |
| **Prompt** | Domain | Everything the LLM model sees for one task: program text, question, task clues, optional choices, and answer instruction. |
| **Answer key** | Domain | The private record of the correct answer and the evidence for it. |
| **CAD graph** | Domain | The graph of CAD entities, relations, and measurements for one CadQuery program and the shape it builds. |
| **CAD graph element** | Internal | One entity, relation, or measurement in the CAD graph. |
| **Graph entity** | Internal | One entity in the CAD graph, such as a face, edge, operation, or region. |
| **Relation** | Domain | A named link between two graph entities. |
| **Measurement** | Domain | A numeric or geometric value about a graph entity or a pair of entities. |
| **Evidence** | Domain | The record of how a measurement was obtained: measured by running CadQuery, or derived exactly from the program. |
| **Solid state** | Domain | The shape before or after an operation, or the final shape. |
| **Warmup subset** | Domain | The labeled set of 0- and 1-step tasks inside the dataset. It is useful for training, not a separate dataset. |
| **Curriculum** | Domain | The order in which tasks are presented, from easier to harder. |
| **Dataset release** | Domain | An immutable, validated, versioned set of tasks and answer keys. |

### Internal and domain pairs

| Internal term | Domain term |
|---|---|
| Task reasoning step | Difficulty step |
| Task reasoning depth | Difficulty |
| Depth support table | Difficulty coverage plan |
| Per-depth coverage | Coverage at every difficulty level |
| Per-depth balance | Balance at every difficulty level |

A domain term may appear in the PRD. An internal term must not. If a product
document needs an internal concept, use the domain term or describe the
user-visible outcome.

## 2. How terms compose

Terms are built from words the reader already knows. A term should be
understandable from its parts, not from a definition that introduces a new
magic word.

| Composed term | Parts | Meaning |
|---|---|---|
| Task target | task + target | The target of a task. |
| Task target category | task target + category | The category of the task target. |
| Task clue | task + clue | A clue in a task prompt. |
| Task clue step | task + clue + step | The hidden step that applies one task clue. |
| Task answer step | task + answer + step | The hidden step that produces the task answer. |
| Task reasoning step | task + reasoning + step | A task clue step or a task answer step. |
| Task solution sequence | task + solution + sequence | The ordered task clue steps and task answer step that solve the task. |
| Task reasoning depth | task + reasoning + depth | The number of task reasoning steps a task requires. |
| Difficulty step | difficulty + step | One step of reasoning a task requires. |
| Difficulty level | difficulty + level | A step-count group used to describe difficulty. |
| Difficulty coverage plan | difficulty + coverage + plan | The published support table by difficulty level. |
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
- Target category is a **coverage** dimension. Clue type, answer meaning, and
  answer format are **coverage and balance** dimensions. Difficulty uses the
  target mix.
- The PRD uses **difficulty**, **difficulty step**, **difficulty level**, and
  **difficulty coverage plan**. Technical documents may use **task reasoning
  depth**, **task reasoning step**, and **depth support table** for the same
  concepts. Internal terms do not appear in the PRD.

There are no task types, task families, or task patterns. The old generator used
hard-coded task families; the replacement chooses a task target and a task
solution sequence from the CAD graph.

Coverage and balance are checked per task reasoning depth. Target category has
per-depth coverage and a release-level cap. Clue type, answer meaning, and
answer format are balanced per depth and over the release, using the conditional
release share. A value may not be concentrated at one depth. In public text,
say "at every difficulty level."

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

In product text, use the domain term:

- **`depth`** for difficulty level;
- **`depth support table`** for difficulty coverage plan;
- **`task reasoning depth`** for difficulty;
- **`task reasoning step`** for difficulty step.
