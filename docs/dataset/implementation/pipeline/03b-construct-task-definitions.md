# 03b — Construct task definitions

**Parent:** [`03-enumerate-tasks.md`](03-enumerate-tasks.md).

**Purpose:** construct persisted task definitions into the task quota plan: task
target, ordered task clues, answer step, gold answer, validity record, and
canonical identity.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Input / output

- Input: `CadGraph`, `TaskQuotaPlan`, and the current `DeficitLedger` on resume
  (empty on the first run).
- Output: `TaskDefinition` records and the updated `DeficitLedger`.

## Task definition

A `TaskDefinition` is the complete, answer-bearing construction record for one
task. It is not prompt text and not a loose task tuple. It is what `04` renders.

| Field | Meaning |
|---|---|
| `task_id` | Stable identity derived from the canonical task identity. It does not encode the gold answer. |
| `definition_sha256` | Hash of the canonical task definition, including the answer and answer evidence. |
| `program_id`, `program_sha256` | CadQuery program identity. |
| `cadevolve_program_family_id` | Program family used for split isolation. |
| `split`, `subset` | Split and warmup/main label assigned by `03a`. |
| `graph_schema_version`, `definition_schema_version` | Versions needed to reproduce the definition. |
| `target_category` | Task target category from `requirements/task-structure.md`. |
| `target_binding` | The concrete graph entity or scalar value the task asks about. |
| `clues` | Ordered typed task clues. |
| `answer_meaning`, `answer_step` | What the answer is about and the step that produces it. |
| `native_answer_format`, `answer_format` | The meaning's native format and the format the prompt will request. |
| `gold_answer`, `unit`, `tolerance`, `scoring_rule` | Answer data. |
| `answer_evidence` | Measured or derived answer evidence with rule and references. |
| `choice_pool` | Real answer-space candidates and their distinguishing graph facts, when multiple choice is planned. For P2, it includes validated near-miss choices. |
| `clue_step_count`, `task_reasoning_step_count` | Step accounting. |
| `validity` | Uniqueness, final possible-answer count, geometry requirement, and check results. |
| `provenance` | Constructor, sampled parameters, and input versions. |

The definition must be sufficient to reproduce the task without re-running task
construction. `04` may render text and order the choice pool, but it must not bind
a new target, compute the answer, or decide validity.

## Graph input boundary

`03b` reads the CAD graph and the `TaskQuotaPlan`. Every task target, clue operand,
answer value, and piece of answer evidence must resolve to a graph entity, a
graph relation, or a measurement. A task definition that needs a missing graph element
is rejected; it is not softened or filled with program-text heuristics.

The graph observation that starts a chain is input. It is not a task reasoning
step. If a task clue states the observation, that clue is a step.

## Target binding

The task target is bound in one of two ways:

- directly, when the question names a task target category with exactly one instance
  in the program, such as the final solid state;
- by the ordered task clues, when the first clues narrow the possible answers to
  one target.

The binding must resolve to exactly one entity or scalar value. A task target category
whose binding is ambiguous is rejected. A task target and an answer measurement
are different: the target is the entity or value the task asks about; the answer
meaning says what is reported about it.

## Task clue predicate schema

A task clue is one typed predicate. It is not a sentence template.

Every `TaskClue` has:

| Field | Meaning |
|---|---|
| `clue_id` | Stable within the task definition. |
| `order` | Position in the task solution sequence. |
| `clue_type` | Property, relation, comparison, aggregation, or provenance. |
| `subject` | Binding reference the clue constrains. |
| `check` | One typed check variant. |
| `result` | Before/after possible-answer counts, bound entities, and answer evidence. |

A `BindingRef` is one of:

- the task target;
- a result of an earlier task clue;
- a named graph element;
- a literal value.

The typed check variants are:

| Clue type | Check fields |
|---|---|
| Property | `measurement`, `comparator`, `threshold` or `range`. |
| Relation | `relation_type`, `object`. |
| Comparison | `measurement`, `comparator`, `reference`. |
| Aggregation | `scope`, `aggregation_kind`, `measurement`, `rank` or extreme. |
| Provenance | `operation_id`, `profile_id`, or `workplane_id`. |

Every task clue must narrow the possible answers: its `after` count is smaller
than its `before` count. A clue that does not narrow is not a task clue step and
the definition is rejected. A list item that states two conditions is two task
clues.

A comparison may name both entities or refer to one selected by an earlier task
clue. The reference must resolve to exactly one entity; otherwise the comparison
needs an explicit aggregation or the task is rejected.

## Answer step and answer format

The answer step produces the answer after the target is identified. It is absent
only when the answer is the target identity; otherwise it is one task reasoning
step.

The answer meaning determines the native answer format:

| Answer meaning | Native answer format |
|---|---|
| Identity | Multiple choice. |
| Volume, area, length, distance, angle | Number. |
| Count, rank | Integer. |
| Membership, validity | Yes or no. |
| Position | 3D coordinate. |
| Extent | Bounding box. |
| CadQuery workplane state | Structured object. |
| Material change | Number for a volume effect; integer for a count effect. |
| Topology change | Integer for a count change. |

Multiple choice is a presentation wrapper valid for every answer meaning when
the definition carries enough real choices. The native format is still recorded.
A format that cannot express the meaning is not used; for example, identity is
not returned as a number and position is not returned as a scalar.

The answer must be produced by CadQuery execution or by an exact derivation from
the program and its geometry, with answer evidence. A guessed or approximate
answer is not valid.

## Validity

A task definition is valid only when all of these hold:

- every task clue is satisfied by the bound entities;
- every task clue narrows the possible answers;
- the final possible-answer set contains exactly one answer;
- the answer step produces exactly one answer;
- the target binding is unambiguous;
- the program family and split are present;
- the split matches the family assignment from `03a`;
- the subset is consistent with the task reasoning step count;
- the answer has answer evidence;
- for multiple choice, the choice pool has at least five real choices;
- for P2 multiple choice, every near-miss choice fails a task clue or the answer
  step, and its error mode is recorded;
- the task definition is unique under canonical identity;
- `geometry_required` is recorded: at least one task clue depends on the built
  shape.

An invalid definition is recorded as a failure with a reason and is not passed to
`04`. A task with a tie, an ambiguous target, or an unverifiable answer is
invalid.

## Task reasoning step accounting

`task_reasoning_step_count` is:

```text
clue_step_count + 1 if the task needs an answer step, otherwise clue_step_count
```

The lowest step count is 1. There are no 0-step tasks. The graph observation is
not counted; the number of prompt sentences is not counted.

Example:

```text
observation -> clue A -> clue B -> clue C
```

- If `C` is the target identity: 3 steps.
- If the task asks for a measurement of `C`: 4 steps.

## Enumeration and identity

`03b` constructs task definitions from the graph into the task quota plan using typed
constructors. Construction is deterministic for a given graph, plan version,
definition-schema version, and seed. Constructor order is stable and recorded in
provenance. A quota target that cannot be filled becomes a deficit for `03c`.

Canonical task identity is:

```text
(program_sha256, target binding identity, canonical task clue sequence, answer meaning)
```

The canonical task clue sequence preserves dependency order and sorts independent
clues deterministically. The gold answer, answer format, choices, prompt wording,
and answer instruction are not part of `task_id`; they are part of the definition
or a later presentation step.

Definitions with identical canonical identity are duplicates. `03b` keeps one
and records the duplicate. Invalid definitions go to the failure record and do
not consume quota.

## Construction attempt budget

Use the plan's `construction_attempt_budgets`. `03a` computes each from the
remaining target count. On resume, use the accepted count in the `DeficitLedger`
and construct only the remaining target count. Accepted definitions are not
regenerated or revalidated while the input versions are unchanged. It does not top up a quota target incrementally within
the same plan revision.

The batch is one iteration and is parallelizable. Extra accepted definitions
become reserve; they are not dataset release rows. Track accepted and rejected counts per quota target, family, and rejection reason. A high rejection rate is a constructor or validity signal; it
is not automatically a reason to expand the program pool.

An underfilled quota target is a deficit for `03c` after the batch, not a reason to loop
inside `03b`.

## Relationship to task reasoning step support

The **task reasoning step support tables** are a separate derived QA baseline.
They are computed from the rules in this document and are not an input to `03b`.
They are used to check release coverage in
[`../task-step-support.md`](../task-step-support.md).

## Open questions

- **Q6** (P2). How are plausible, deterministic near-miss choices generated and
  validated?
  - **Recommendation:** start from the correct task solution and apply one
    controlled error: an adjacent entity, the wrong solid state, the wrong
    operation, a swapped comparison, a different measurement, or an off-by-one
    count. Validate against the graph, then order the choices by a stable hash.
    For a multi-step task, a near miss should satisfy most task clues and fail at
    least one. Record the error mode. P0 and P1 do not require this audit.

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

## Deficits

A quota target that cannot be filled is recorded in the deficit ledger. `03c`
decides whether to sample more from existing graphs, use unused or reserve
programs, request supplemental `01b` selection, or accept the miss.

## Not here

Task quota planning, data expansion, prompt rendering, choice rendering, and
export.
