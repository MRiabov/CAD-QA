# Task construction

**Parent:** [`../README.md`](../README.md).

**Status:** draft, 2026-11-20. Fills the construction gap `KI-DS-REQ-01`: `03b` defines
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

The state scope is `final` in P0 (`DS-REQ-08`). The set is not curated: it is
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
  (`DS-REQ-15`).
- `cover` is a bounded set-cover search. Applying a fact is a set intersection,
  so a greedy cover gives the shortest chain and a less greedy cover gives a
  longer one.
- The target step count is a search parameter. If the plan asks for four steps,
  the search looks for a three-clue cover plus the answer step.
- No cover at the target step count is a deficit for `03a`/`03c`, not a reason to
  accept a longer or shorter task.
- The search runs under the [cost budget](#cost-budget); exhausting it is a
  deficit, not a reason to search longer.

## Step 4 — chain order

Order the chosen clues by dependency first, then broad-to-narrow: the size of the
narrowed set, descending, with a stable hash as the tie-break (`TG-7`). This is
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
| answer uniqueness | every remaining candidate gives the same answer (`DS-REQ-15`) |
| choice pool | every P0 row of the multiple-choice check list (`TG-8`) |
| step count | the number of necessary clues plus the answer step matches the target |

A chain that fails a check is recorded with its reason. It is not repaired by
adding or dropping clues silently: a shorter valid task is a different task.

## Step 6 — acceptance

Construction proposes; the scheduler disposes. The quota scheduler accepts a
definition only when it fills an unfilled target and does not push any cell past
its maximum (`TG-2`). Overfill is rejected and recorded.

## Cost budget

The search is bounded by counts, not by `max_state_entities` alone. The constants
are implementation-scope constants like `max_state_entities`: they are measured
once from the selected pool, recorded with the distribution that produced them,
and read by construction rather than recomputed per run.

| Constant | Meaning | Provisional default |
|---|---|---|
| `max_construction_candidates` | Candidate witnesses examined per attempt. | 200 |
| `max_construction_facts` | Facts considered per candidate. | 64 |
| `max_cover_expansions` | Set intersections the cover search may evaluate per attempt. | 20,000 |
| `max_validity_rechecks` | Clue-removal rechecks the validity gates may run per chain. | 64 |

When a budget is exhausted the attempt stops and the batch records a
`construction_deficit` with detail `construction_budget` for the targets it could
not fill. It is not a failure row, and it is not retried inside the same plan
revision; `03c` may move the target to a family with a smaller candidate set,
raise the budget in a new revision, or accept the miss.

Every limit is a count, so the search stays deterministic. A wall-clock deadline
would make the accepted task set depend on machine load, which contradicts the
byte-identical rerun rule in `run-contract.md`. The constants are part of
`constructor_version`: changing one changes the definitions it can produce and
invalidates them.

The deficit ledger records attempt counts, not wall-clock milliseconds, for the
same reason: the ledger is an input to the plan identity, and timing would make a
rerun non-deterministic. The cost constants are measured offline, once per
implementation scope.

## Determinism

Construction is deterministic for a given graph, plan version, definition schema
version, and seed. Candidate order, fact order, tie-breaks, and the cover search
use stable hashes. The same inputs produce the same definitions, so `task_id`
and the release are reproducible.

## Worked example

The box-with-hole program in
[`golden/box-with-hole.json`](../../testing/golden/box-with-hole.json) is the
first golden record. The final solid has 15 edges, not 14: the cylindrical face
carries a periodic seam edge. The top face leaves five edges, and the
cylindrical face leaves the one edge shared with the top face, so the chain is
two relation clues plus the length answer. The clue operand form profile is
`[(relation, named), (relation, named)]`. The record format and comparison rules
are in [`golden/README.md`](../../testing/golden/README.md).
