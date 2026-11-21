# 03b — Construct task definitions

**Parent:** [`../README.md`](../README.md).

**Purpose:** construct persisted task definitions into the task quota plan: task
target, ordered task clues, task answer step, gold answer, validity record, and
canonical identity.

**Input/output contract:** [`../../io-contracts.md`](../../io-contracts.md).

## Input / output

- Input: `CadGraph`, `TaskQuotaPlan`, and the current `DeficitLedger` on resume
  (empty on the first run).
- Output: `TaskDefinition` records and the updated `DeficitLedger`.

The records are Parquet shard parts. Resume reads the committed parts and skips a
`task_id` that is already present; a rejected `task_id` is in the failure
partition and is also skipped. The persistence and resume rules are in
[`../../../run-contract.md`](../../../run-contract.md#4-incremental-parquet-persistence).

## Task definition

A `TaskDefinition` is the complete, answer-bearing construction record for one
task. It is not prompt text and not a loose task tuple. It is what `04` renders.

| Field | Meaning |
|---|---|
| `task_id` | `cadqatask:<sha256>` over the canonical task identity. It does not encode the gold answer. |
| `definition_sha256` | Hash of the canonical task content and the inputs that change it. Assignment is excluded. The provenance block is not hashed as a block, but the provenance inputs that change the content are covered. |
| `answer_sha256` | Hash of the answer and scoring fields, computed at construction and copied by `04`. It excludes `answer_evidence`. |
| `program_id`, `program_sha256` | CadQuery program identity. |
| `cadevolve_program_family_id` | Program family used for split isolation. |
| `split`, `subset` | Split and warmup/main label assigned by `03a`. |
| `graph_schema_version`, `definition_schema_version` | Versions needed to reproduce the definition. |
| `state_scope` | Which solid states the task may refer to. `final` in P0 (`DS-REQ-08`). |
| `possible_answer_count` | The size of the initial possible-answer set for the target category in the state scope, before any task clue narrows it. |
| `target_category` | Task target category from `requirements/task-structure.md`. |
| `target_binding` | The concrete graph entity or measurement instance the task asks about. |
| `task_clues` | Ordered typed task clues. |
| `clue_operand_form_profile` | The ordered `(clue_type, clue_operand_form)` pair for every clue. Derived from `task_clues`. |
| `answer_meaning`, `task_answer_step` | What the answer is about and the step that produces it. |
| `answer_parameter` | The point for a position or a membership, the category for a topology change, null otherwise. |
| `native_answer_format`, `answer_format` | The meaning's native format and the format the prompt will request. |
| `gold_answer`, `answer_unit`, `tolerance`, `scoring_rule` | Answer data. `gold_answer` is an `AnswerValue` and `tolerance` is a `Tolerance`; both use canonical decimal text for numbers and match the release columns. |
| `answer_schema_version` | Version of the answer representation: the answer formats, the canonical text rules, and the answer evidence shape. Hashed by `answer_sha256`. |
| `answer_evidence` | Typed `AnswerEvidence`: rule, references, the answer-equivalent count and shared answer, and the point probe. The full set stays in the definition; `04` copies the count and shared answer into the release column. |
| `choice_pool` | The ordered, labeled options when multiple choice is planned: label, answer value, distinguishing graph facts, and the P2 error mode. Empty otherwise. |
| `task_clue_step_count`, `task_reasoning_step_count` | Step accounting. |
| `geometry_required` | Whether at least one task clue depends on the built shape. |
| `validity_record` | Typed check results and the answer-uniqueness result. |
| `provenance` | Constructor version, seed, and input versions. Assignment, not content. |

The definition must be sufficient to reproduce the task without re-running task
construction. `04` may render text, but it must not reorder or relabel the choice
pool, bind a new target, compute the answer, or decide validity.

## Documents

| Doc | Contract |
|---|---|
| [`a-construction.md`](a-construction.md) | Graph boundary, target binding, clue schema, validity, step accounting, attempt budget, and the search algorithm. |
| [`b-answer-semantics.md`](b-answer-semantics.md) | Answer step, format, multiple-choice pool, resolver, evidence, and equality. |
| [`c-definition-identity.md`](c-definition-identity.md) | Canonical order, serialization, the three hashes, and provenance. |

## Open questions

- **Q6** (P2). How are plausible, deterministic near-miss choices generated and
  validated?
  - **Recommendation:** start from the correct task solution and apply one
    controlled error: an adjacent entity, the wrong solid state, the wrong
    operation, a swapped comparison, a different measurement, or an off-by-one
    count. Validate against the graph, then add each near miss to the pool before
    the pool is ordered. For a multi-step task, a near miss should satisfy most
    task clues and fail at least one. Record its `error_mode`. P0 and P1 do not
    require this audit.

## Resolved questions

- **Q2.** *Resolved 2026-10-21.* Option B: atomic predicates. Each relation or
  property is one task clue and one task clue step. A list item that states a
  relation and a property is split into two task clues. A chain is not one task
  clue; it is a P2 ordered sequence of relation task clues, one step per
  relation. Task clues are rendered as numbered list items, not prose.

- **Q4.** *Resolved 2026-10-21.* Multiple choice is valid for every answer
  meaning; it is a presentation wrapper, not a separate answer meaning. The
  native answer format is recorded with the answer meaning; multiple choice may
  be used when enough choices can be generated.

- **Q5.** *Resolved 2026-10-21.* A task is a duplicate when its canonical task
  identity is identical. Answer format, multiple-choice choices, prompt wording,
  and answer instruction are excluded because multiple choice is a presentation
  wrapper.

## Not here

Task quota planning, data expansion, prompt rendering, choice rendering, and
export. The construction test contract is in
[`../testing/03b-construct-task-definitions.md`](../../testing/03b-construct-task-definitions.md), and the
golden record format is in [`../testing/golden/README.md`](../../testing/golden/README.md).
