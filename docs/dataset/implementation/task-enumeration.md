# Task enumeration contract

**Status:** draft, 2026-10-21. This is the technical contract for turning the
task requirements into a release dataset. It does not define the consumer-facing
release layout; that is
[`../requirements/release-dataset-contract.md`](../requirements/release-dataset-contract.md).

## 1. Scope

This contract defines the task tuple and canonical identity, the valid-task
universe versus the release subset, the validity oracle, task reasoning step
accounting, the clue predicate schema, the answer meaning to answer format map,
release selection, deduplication, serialization, and split assignment.

The questions below are unresolved. They are implementation questions, not
product requirements.

## 2. Open questions

- **Q1.** Is the release selection implemented by enumerating and cutting, or
  by planning quotas and generating into them?
  - **Option A — enumerate and cut.** Generate the valid tasks, then select a
    release that meets coverage and balance. Simple, but may do unused work.
  - **Option B — quota plan.** Allocate counts per task reasoning step count and
    dimension, then generate into the quotas with deterministic randomness.
    Avoids unused work, but must detect when the valid-task universe cannot fill
    a cell.
  - **Option C — hybrid.** Enumerate small cells and plan large cells.
  - **Recommendation:** This is an implementation choice, not a product
    decision. The contract fixes the release constraints and reproducibility; it
    does not mandate either strategy.

- **Q2.** Is a chain clue one task reasoning step or one step per relation? Is a
  clue that combines a relation and a property one condition or two?
  - **Option A — chain is one step; a compound sentence is one clue.** The
    current text allows “the face adjacent to X whose area is larger than X” as
    one clue.
  - **Option B — atomic predicates.** Each relation or property is one clue and
    one task reasoning step. The compound sentence becomes two clues; the chain
    becomes one clue per relation.
  - **Option C — hybrid.** Chains count per relation, but a relation plus a
    property in one sentence counts as one clue.
  - **Recommendation:** B. Example: “the face adjacent to X whose area is
    larger than X” is two steps; `A -> B -> C` is two steps. Split the prompt
    task clues accordingly. This makes the step count auditable.

- **Q3.** Is the conditional release share computed from the valid-task universe,
  or allocated from the global targets before selection?
  - **Option A — universe share.** Compute each value's share in the universe
    among the values supported at that step count, then require the release to
    approximate it.
  - **Option B — allocate quotas from the global targets, then fill from the
    universe.** Choose the target mix first, allocate counts per step count and
    dimension, then select tasks that fill the quotas.
  - **Option C — select, compute, repair.** Select a draft release, measure it,
    and move tasks until the targets hold.
  - **Recommendation:** B. Example: at step count 2, supported answer meanings
    `A`, `B`, and `C` have target shares 20%, 30%, and 50%; allocate the step-2
    quota in those proportions, fill from the universe, and report a conflict if
    the universe cannot fill a cell. This avoids the circular definition.

- **Q5.** When is a task a duplicate of another task?
  - **Option A — canonical tuple.**
    `(program, target entity, clue sequence, task answer step, answer format)`.
  - **Option B — rendered prompt text.** Two tasks with the same prompt are
    duplicates.
  - **Option C — answer value.** Two tasks with the same answer are duplicates.
  - **Recommendation:** A, with canonical clue order. Example: the same target,
    clues, and answer but multiple choice vs number are two tasks. The same
    tuple rendered twice is one task. The same prompt text with two different
    answers is an ambiguity defect, not two tasks.

## 3. Resolved questions

- **Q4.** *Resolved 2026-10-21.* Multiple choice is valid for every answer
  meaning. It is a presentation wrapper: it changes the return syntax and the
  choices, not the answer meaning or the correct answer. The native formats
  remain: identity -> multiple choice; volume, area, length, distance, angle,
  material change -> number; count or rank -> integer; membership or validity
  -> yes or no; position -> 3D coordinate; extent -> bounding box;
  CadQuery workplane state -> structured object; topology change -> integer or
  structured object. Every answer meaning may also use multiple choice when enough choices
  can be generated.
