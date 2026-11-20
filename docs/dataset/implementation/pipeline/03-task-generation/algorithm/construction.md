# Task construction

**Parent:** [`../README.md`](../README.md).

**Status:** draft, 2026-11-20. Fills the construction gap `KI-DS-01`: `03b` defines
what a valid task is, and this document defines how one is found.

## Purpose

Given one CAD graph and one quota target, find task definitions that satisfy the
validity contract in
[`../03b-construct-task-definitions.md`](../03b-construct-task-definitions.md).
Construction is a local search over one graph. It never enumerates the task space.

## Input

- one `CadGraph` from `02c`;
- one quota target from the `TaskQuotaPlan`, with its task reasoning step count,
  target category, clue type, clue operand form, answer meaning, and answer
  format;
- the program capability census from
  [`program-capability-census.md`](program-capability-census.md).

## Step 1 — possible-answer set

```text
possible_answers = all entities of the target category in the state scope
```

The state scope is `final` in P0 (`DS-34`). The set is not curated: it is
whatever the graph holds for that category and state. Breadth is a property of
the graph, not a construction choice.

For a scalar target, the candidates are measurement instances:

```text
possible_answers = all (subject, value) instances of the declared measurement
                   in the state scope
```

The subject may be an entity or a solid state. The rest of the search is
unchanged: facts constrain the subject, and `same_answer` compares values.

## Step 2 — facts and extensions

For one candidate, ask the graph what is true of it:

```text
facts = true_facts(graph, candidate)
```

Each fact carries the set of candidates it selects, its **extension**. A fact
exists only when the graph asserts it and its measurement is present, so an
unsupported predicate is never attempted.

```text
fact: "adjacent to the cylindrical face"
extension: {top circular edge, bottom circular edge}
```

Facts are the only origin of clues. A clue sentence is rendered from a fact; it
is never generated first and checked afterwards.

## Step 3 — cover search

For each candidate as the witness answer:

```text
wrong = {
    other in possible_answers
    if not same_answer(answer(other), answer(witness))
}
chain = cover(wrong, facts(witness), target_step_count = task_reasoning_step_count - task_answer_step_count)
```

- The cover target is the **wrong-answer candidates**, not every other candidate.
  Candidates that remain and give the same answer are the answer-equivalent set
  (`DS-32`).
- `cover` is a bounded set-cover search. Applying a fact is a set intersection,
  so a greedy cover gives the shortest chain and a less greedy cover gives a
  longer one.
- The target step count is a search parameter. If the plan asks for four steps,
  the search looks for a three-clue cover plus the answer step.
- No cover at the target step count is a deficit for `03a`/`03c`, not a reason to
  accept a longer or shorter task.

## Step 4 — chain order

Order the chosen clues by dependency first, then broad-to-narrow: the size of the
narrowed set, descending, with a stable hash as the tie-break (`DS-35`). This is
the canonical order. It is identity-bearing, and validity is checked against it.
A presentation permutation is a later rendering step.

## Step 5 — validity gates

A chain that covers the wrong-answer candidates is still rejected unless it
passes the validity contract in `03b`. The checks that construction can fail on
its own:

| Check | Rule |
|---|---|
| narrowing | every clue reduces the answer candidate set |
| necessity | removing any clue leaves at least two distinct answers (`TG-1`) |
| answer uniqueness | every remaining candidate gives the same answer (`DS-32`) |
| choice pool | at least five real options for multiple choice (`DS-36`) |
| step count | the number of necessary clues plus the answer step matches the target |

A chain that fails a check is recorded with its reason. It is not repaired by
adding or dropping clues silently: a shorter valid task is a different task.

## Step 6 — acceptance

Construction proposes; the scheduler disposes. The quota scheduler accepts a
definition only when it fills an unfilled target and does not push any cell past
its maximum (`TG-2`). Overfill is rejected and recorded.

## Determinism

Construction is deterministic for a given graph, plan version, definition schema
version, and seed. Candidate order, fact order, tie-breaks, and the cover search
use stable hashes. The same inputs produce the same definitions, so `task_id`
and the release are reproducible.

## Worked example

The box-with-hole program in
[`plans/nov-19/03b-task-construction-design.md`](../../../../../../plans/nov-19/03b-task-construction-design.md)
is the first golden record: five edges narrow to two circular edges, then to the
top one, with clue operand form profile `[(relation, named), (relation, named),
(comparison, selected)]` and answer meaning length.
