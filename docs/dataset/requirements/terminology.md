# CAD-QA dataset terminology

**Status:** approved 2026-10-22. Extraction terms are mirrored in
`docs/glossary.md`.

**Scope:** a **domain term** may appear in the PRD. An **internal term** describes
how the generator computes coverage or balance and must not appear in the PRD.
If a product document needs an internal concept, use the domain term or describe
the user-visible outcome.

## 1. Core terms

| Term | Scope | Meaning |
|---|---|---|
| **Task** | Domain | One dataset instance: a CadQuery program, a task target, a set of task clues, and one answer. Use "dataset task" when it could be confused with an internal task. |
| **Task definition** | Internal | The persisted, answer-bearing construction record for one task: target binding, ordered clues, answer step, answer, validity record, and identity. It is not prompt text. |
| **Question** | Domain | The interrogative sentence in the prompt. It is not the whole task. |
| **Clue type** | Domain | The category of condition a task clue states: property, relation, comparison, aggregation, or provenance. A chain is a P2 sequence of relation clues, not a clue type. |
| **Answer meaning** | Domain | What the answer is about, independent of how it is returned: identity, volume, area, length, distance, angle, count, rank, membership, position, extent, CadQuery workplane state, material change, topology change, or validity. |
| **CADEvolve program family** | Domain | A stable program family used as the split unit: a CADEvolve generator family or a CADEvolve-predicted ABC/ShapeNet mesh family. P and C versions of one family share a family ID. |
| **Task reasoning step support table** | Domain | The release artifact that records which dimension values can occur at each task reasoning step count, and why an unsupported value cannot occur there. |
| **Task reasoning step count coverage** | Internal | Every value supported at a task reasoning step count appears at that count. |
| **Conditional release share** | Internal | A value's share among the values supported at a task reasoning step count, used as the comparison base for task reasoning step count balance. |
| **Task reasoning step count balance** | Internal | For clue type, answer meaning, and answer format, a supported value's share at a task reasoning step count is between half and twice its conditional release share. |
| **Task target** | Domain | The entity or value the task asks about. |
| **Task target category** | Domain | The category of the task target. It is a coverage dimension, not a percentage-balance dimension at each task reasoning step count. |
| **Task clue** | Domain | One numbered list item in the prompt that states a condition the answer must satisfy. |
| **Task clue step** | Domain | The hidden graph operation that applies one task clue and reduces the set of possible answers. |
| **Task answer step** | Domain | The hidden operation that produces the answer once the task target is identified. |
| **Task reasoning step** | Domain | A task clue step or a task answer step. |
| **Task reasoning step count** | Domain | The number of task reasoning steps a task requires. |
| **Task solution sequence** | Domain | The ordered task clue steps and task answer step that solve the task. |
| **Answer format** | Domain | The form of the answer: multiple choice, number, integer, yes or no, 3D coordinate, bounding box, or structured object. |
| **Multiple-choice choices** | Domain | The short list of options shown for a multiple-choice answer. |
| **Answer instruction** | Domain | The part of the prompt that tells the LLM model which answer format to return and in what syntax. |
| **Program text** | Domain | The CadQuery program shown in the prompt. |
| **Prompt** | Domain | Everything the LLM model sees for one task: program text, question, task clues, optional choices, and answer instruction. |
| **Gold answer** | Domain | The correct answer for one task. It is kept out of the prompt. |
| **Answer data** | Domain | The answer columns in the release dataset: gold answer, scoring fields, and answer evidence. |
| **CAD graph** | Domain | The typed graph of CAD graph entities, CAD graph relations, and CAD graph measurements for one CadQuery program and the shape it builds. |
| **CAD graph element** | Internal | One CAD graph entity, CAD graph relation, or CAD graph measurement. |
| **CAD graph entity** | Internal | One entity in the CAD graph, such as a face, edge, operation, or region. |
| **CAD graph relation** | Domain | A named link between two CAD graph entities. |
| **CAD graph measurement** | Domain | A numeric or geometric value about a CAD graph entity or a pair of CAD graph entities. |
| **CAD graph evidence** | Internal | The record of how a CAD graph element (CAD graph relation or CAD graph measurement) was obtained: measured by running CadQuery, or derived by an exact rule, with the rule and references. |
| **Answer evidence** | Domain | The record of how a task's gold answer was obtained: the referenced CAD graph evidence and the rule that produces the answer. |
| **Validity record** | Internal | The check results that establish a task definition's uniqueness, target binding, clue narrowing, and geometry requirement. It is not answer evidence. |
| **Failure tombstone** | Internal | A recorded failed program or operation, with the error and cache key, used for debugging and cache hits. It is not a graph entity and never supports an answer. |
| **CadQuery program AST extraction result** | Internal | The result of extracting a CadQuery program without running it: operations, CadQuery workplanes, CadQuery profiles, CadQuery paths, CadQuery selectors, and their relationships in the CadQuery program. |
| **CadQuery program runtime extraction result** | Internal | The result of executing a CadQuery program and extracting Shape snapshots, CAD feature solid state effect deltas, CadQuery selector results, and evidence. |
| **solid state producing operation** | Internal | A CadQuery program operation that can produce a solid state. |
| **CAD feature solid state effect delta** | Domain | The measured before/after volume, bounding box, and topology change caused by a CAD feature. Distinct from the Measurement scope `feature_application_effect`. |
| **CadQuery selector result** | Internal | The CAD topology entities selected by one CadQuery selector, with the CadQuery selector and the solid state it ran on. |
| **CadQuery accessor** | Internal | A CadQuery call that reads or converts existing values without creating geometry. |
| **CAD topology entity** | Domain | A face, edge, or vertex of a solid state. |
| **CAD topology entity ID** | Internal | The stable identity of a CAD topology entity within one solid state; `In code:` `entity_id`. |
| **AST rejection** | Internal | A rejected `02a` CadQuery program with no CadQuery program AST extraction result, distinct from a `02b` failure tombstone. |
| **Solid state** | Domain | The shape before or after an operation, or the final shape. |
| **Warmup subset** | Domain | The labeled set of 1-step tasks inside the dataset. It is useful for training, not a separate dataset. |
| **Curriculum** | Domain | The order in which tasks are presented, from lower to higher task reasoning step counts. |
| **Dataset release** | Domain | An immutable, validated, versioned set of tasks and correct answers. |
| **Release dataset** | Domain | The one release table for one implementation scope, with prompt and answer columns. Use it when distinguishing the release from external datasets and LLM reasoning-output datasets. |
| **Implementation priority** | Domain | P0/P1/P2 order for requirements and generation inputs. It is not a task property and never appears as a row label. |
| **Quota** | Internal | An allowed or required count at a stated scope. |
| **Task quota** | Internal | A quota counted in tasks. |
| **Task reasoning step quota** | Internal | The task quota for one task reasoning step count. |
| **Clue quota** | Internal | A quota counted in task clue occurrences. |
| **Quota dimension** | Internal | One independent way tasks are counted for coverage and balance: task target category, clue type, answer meaning, or answer format. |
| **Quota target** | Internal | A count target for one quota dimension value at one task reasoning step count: minimum, target count, and maximum. It is not a task. |
| **Task quota plan** | Internal | The plan for task quotas, family assignment, split assignment, and construction attempt budgets for one dataset release. |
| **Family task capacity** | Internal | The estimated maximum number of tasks a CADEvolve program family can supply. |
| **Split task target** | Internal | The planned number of tasks for one split. |
| **Construction attempt budget** | Internal | The number of task-definition construction attempts allocated to a quota target before accepted tasks are counted. |
| **Probe success rate** | Internal | The share of bounded-probe construction attempts that produced accepted task definitions. |

### Internal and domain pairs

| Internal term | Domain term |
|---|---|
| Task reasoning step count coverage | Coverage at every task reasoning step count |
| Task reasoning step count balance | Balance at every task reasoning step count |

`Conditional release share` is a calculation detail for the technical
specification and has no domain equivalent.

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
| Task reasoning step count | task reasoning + step count | The number of task reasoning steps a task requires. |
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
| `execution record` | CadQuery program runtime extraction result |
| `CadQuery program operation trace` | CadQuery program runtime extraction result |
| `operation trace` | CadQuery program runtime extraction result |
| `execution result` | CadQuery program runtime extraction result |
| `static CadQuery model` | CadQuery program AST extraction result |
| `static model` | CadQuery program AST extraction result |
| `static schema` | AST extraction schema |
| `static rejection` | AST rejection |
| `static failure` | AST rejection |
| `state-producing operation` | solid state producing operation |
| `operation effect` | CAD feature solid state effect delta |
| `CAD feature effect delta` | CAD feature solid state effect delta |
| `entity fingerprint` | CAD topology entity ID |
| `CAD ontology graph` | CAD graph |
| `CAD ontology node` | CAD graph entity |
| `ontology graph` | CAD graph |
| `ontology node` | CAD graph entity |
| `CAD graph edge` | CAD graph relation |
| `graph node` | CAD graph entity |
| `graph edge` | CAD graph relation |
| `node` | CAD graph entity |
| `clause` | task clue |
| `candidate trace` | task solution sequence |
| `question` (the whole instance) | task |
| `question family` | removed; use clue type and answer meaning |
| `target` | task target |
| `clue` | task clue |
| `hop count` | task reasoning step count |
| `dataset row` | task, or dataset entry |
| `candidate` | multiple-choice choice, or possible answer (hidden) |
| `release` | dataset release |
| `quarantine` | non-release-ready |
| `selector` | CadQuery selector |
| `workplane` | CadQuery workplane |
| `profile` | CadQuery profile |
| `stage` | pipeline stage, or training stage |
| `gate` | quality requirement |
| `tracked` | recorded or documented |

## 4. Naming decisions

- **CadQuery program AST extraction result** is the `02a` output; **CadQuery program runtime extraction result** is the `02b` success output.
- A **Shape snapshot** is the runtime capture; a **solid state** is the CAD graph entity. Do not write bare `state`.
- Use **CAD graph entity** in prose; `node_id` and `nodes.parquet` are code and schema names.
- **CAD feature solid state effect delta** is the delta record; `feature_application_effect` is a Measurement scope.
- The prompt condition is a **task clue**.
- Task text and choice descriptions use geometry or construction role, never
  variable names. The program text is the only place variable names appear.
- The step that applies a task clue is a **task clue step**.
- The step that produces the answer is a **task answer step**.
- The ordered steps that solve the task are the **task solution sequence**.
- The form of the answer is the **answer format**.
- Target category is a **coverage** dimension. Clue type, answer meaning, and
  answer format are **coverage and balance** dimensions. Task reasoning step
  count uses the target mix.

There are no task types, task families, or task patterns. The old generator used
hard-coded task families; the replacement chooses a task target and a task
solution sequence from the CAD graph.

Coverage and balance are checked at each task reasoning step count. Target
category has coverage at each task reasoning step count and a release-level cap.
Clue type, answer meaning, and answer format are balanced at each task reasoning
step count and over the release, using the conditional release share. A value
may not be concentrated at one task reasoning step count.

## 5. Terms to avoid

These words caused ambiguity in the previous documentation:

- **`source`** for a CadQuery program;
- **`trace`** for anything other than a program execution record;
- **`node`** for a graph entity;
- **`clause`** for a task clue or a task clue step;
- **`candidate`** for both a hidden possible answer and a multiple-choice choice;
- **`hop`** for a task reasoning step;
- **`family`** for a group of tasks; use clue type and answer meaning;
- **`release`** without saying dataset release;
- **`stage`** without saying pipeline stage or training stage;
- **`gate`** without naming the requirement;
- **`question`** for the whole task rather than the interrogative sentence;
- **`type`** or **`pattern`** as a way to group tasks; use clue type and answer meaning;
- **`reasoning depth`** for task reasoning step count; **depth** is also a CAD
  measurement;
- **`evidence`** without a qualifier; use **CAD graph evidence** for a graph
  element and **answer evidence** for a task answer.

In product text, do not use internal terms:

- **`task reasoning step count coverage`** or **`task reasoning step count
  balance`**; say coverage or balance at every task reasoning step count;
- **`reasoning depth`**; say task reasoning step count;
- **`answer key`** for the correct answers; the dataset has tasks and their
  correct answers, with no separate answer-key object;
- **`variable name`** in task text or choices; describe the entity by its geometry
  or construction role.
- **`conditional release share`**; it is a technical calculation detail;
- **`CAD graph element`** or **`graph entity`**; say CAD graph when the product
  needs the concept.

## 6. 3D model terms and software terms

A 3D model term and a software or code term are different terms even when they
share a word. Qualify the term with its domain; do not use a 3D word as a
metaphor for a software concept.

| Shared word | 3D model term | Software, code, or reasoning term |
|---|---|---|
| `depth` | cut depth, hole depth | task reasoning step count |
| `edge` | CAD edge | CAD graph relation |
| `feature` | CAD feature | software feature |
| `path` | CadQuery path | file path |
| `profile` | CadQuery profile | performance profile |
| `vertex` | CAD vertex | graph vertex |

The reasoning measure is **task reasoning step count**, never "reasoning depth,"
because **depth** is already a CAD measurement.
