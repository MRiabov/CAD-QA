# Task construction

**Parent:** [`README.md`](README.md).

**Status:** draft, 2026-11-20. This document defines the construction contract
and the search that satisfies it.

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

The binding must resolve to exactly one entity or scalar value. A task target
category whose binding is ambiguous is rejected. For a scalar target, the binding
is a measurement instance: the subject, the measurement, and its value. The
subject need not be unique, because the answer is that measurement value. A task
target and an answer measurement are different: the target is the entity or
value the task asks about; the answer meaning says what is reported about it.

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

When a clue has a reference binding other than the task target, the binding
carries `clue_operand_form` (`DS-REQ-04`):

| Clue operand form | Binding | Example |
|---|---|---|
| `named` | a named graph element | "adjacent to the cylindrical face" |
| `selected` | a result of an earlier task clue | "adjacent to the face selected in step 1" |
| `aggregated` | an extreme, rank, or count over a set | "adjacent to the largest face of the hole" |
| `cross_state` | a before/after solid state pair | P2 only |

A clue with no reference has no clue operand form. A property clue that refers to
another entity is two clues and is split into two list items.

Four rules make a clue type and clue operand form combination impossible, so no
task uses one:

| Combination | Why it cannot exist |
|---|---|
| property with any operand form | A property clue constrains the candidate set directly and has no reference, so it has no operand form. |
| aggregation with `aggregated` | It is aggregation over an aggregate; it is written as two clues. |
| `selected` at task reasoning step count 1 | A `selected` reference needs an earlier task clue. |
| `cross_state` in P0 and P1 | It needs a second solid state, and P0 and P1 use the final state only (`DS-REQ-08`). |

The first two are grammar rules and hold for every program. The last two follow
from the task reasoning step count and the state scope. The support table
observes which forms the constructor produced, so a combination that cannot exist
simply has no supported value.

The typed check variants are:

| Clue type | Check fields |
|---|---|
| Property | `measurement`, `comparator`, `threshold` or `range`. |
| Relation | `relation_type`, `direction` (`object_to_subject` or `subject_to_object`), `object`. |
| Comparison | `measurement`, `comparator`, `reference`. |
| Aggregation | `scope`, `aggregation_kind`, `measurement`, `rank` or extreme. |
| Provenance | `operation_id`, `profile_id`, or `workplane_id`. |

Every task clue must narrow the possible answers: its `after` count is smaller
than its `before` count. A clue that does not narrow is not a task clue step and
the definition is rejected. A list item that states two conditions is two task
clues.

The definition also records `clue_operand_form_profile`, the ordered
`(clue_type, clue_operand_form)` pair for every clue. It is derived from
`task_clues` at construction and never authored separately. `05` validate and
export release checks that its clue types match `clue_types` and uses the forms
for clue operand form coverage.

A comparison may name both entities or refer to one selected by an earlier task
clue. The reference must resolve to exactly one entity; otherwise the comparison
needs an explicit aggregation or the task is rejected.

## Validity

A task definition is valid only when every rule in this table holds. The check
name is stable: it is the name the validity record carries.

| Check | Rule |
|---|---|
| `clue_satisfied` | Every task clue is satisfied by the bound entities. |
| `clue_narrows` | Every task clue narrows the possible answers. |
| `clue_necessary` | Removing any task clue leaves at least two distinct answers, or changes the answer. |
| `predicate_margin` | Every predicate a task uses is decided by at least the clear-case margin. |
| `answer_equivalence` | Every candidate in the answer-equivalent set produces the same answer under `same_answer`; an identity answer requires a singleton set (`DS-REQ-15`). |
| `scalar_target_agrees` | For a scalar target, every remaining instance has the same value. |
| `single_gold_answer` | The answer step produces exactly one gold answer. |
| `target_binding_unambiguous` | The target binding resolves to exactly one entity or measurement instance. |
| `family_and_split_present` | The program family and split are present. |
| `split_matches_assignment` | The split matches the family assignment from `03a`. |
| `subset_matches_step_count` | The subset is consistent with the task reasoning step count. |
| `answer_evidence_present` | The answer has answer evidence. |
| `choice_pool_valid` | For multiple choice, the choice pool passes every P0 row of the [multiple-choice check list](b-answer-semantics.md#multiple-choice-choices). |
| `near_miss_valid` | For P2 multiple choice, every near-miss fails a task clue or the answer step, and its `error_mode` is recorded. |
| `definition_unique` | The task definition is unique under canonical identity. |
| `geometry_required_recorded` | `geometry_required` is recorded: at least one task clue depends on the built shape. |

An invalid definition is recorded as a failure naming the failed check and is not
passed to `04`. A task with an ambiguous target, an answer-equivalent set that disagrees
under `same_answer`, or an unverifiable answer is invalid.

### Validity record

`validity_record` is typed, not prose:

| Field | Meaning |
|---|---|
| `checks` | One entry per validity rule in the table above: the check name, the outcome, and a detail string. |
| `answer_equivalent_size` | The number of entries in `answer_equivalent_set`. |
| `same_answer_holds` | Whether every entry's answer equals the answer value. |

An accepted definition carries every check name except
`geometry_required_recorded`, each with outcome `pass`. A missing check is a
defect: it means the constructor did not run the rule.
`geometry_required_recorded` is a rule but not a `checks` entry, because
`geometry_required` is its own field and `04` copies it to the release row.

### Failure reasons

`03b` owns the closed reason set the failure record uses:

| Reason | Meaning |
|---|---|
| A check name from the table above. | The definition failed that rule. A duplicate is `definition_unique`. |
| `no_cover` | The cover search found no chain at the target task reasoning step count. |
| `internal` | The constructor raised an unexpected exception or panic. |

A state without a surviving probe is not a failure row. No definition was
attempted, so the state is a `probe_deficit` in the deficit ledger instead.

## Task reasoning step accounting

`task_reasoning_step_count` is:

```text
task_clue_step_count + 1 if the task needs an answer step, otherwise task_clue_step_count
```

The lowest step count is 1. There are no 0-step tasks. The graph observation is
not counted; the number of prompt sentences is not counted.

Example:

```text
observation -> clue A -> clue B -> clue C
```

- If `C` is the target identity: 3 steps.
- If the task asks for a measurement of `C`: 4 steps.

A clue that can be removed without losing answer uniqueness is redundant, so the
achievable step count is the number of necessary clues plus the answer step. A
quota target above that count is a deficit, not a reason to keep a redundant clue.

## Construction attempt budget

Use the plan's `construction_attempt_budgets`. Each entry is one batch for a
family and task reasoning step count; `03a` computes it from the remaining step
quota. On resume, reconcile the `DeficitLedger` accepted counts
from the committed `TaskDefinition` parts, then construct only the remaining
target count. A `task_id` already present in the parts or the failure partition
is skipped when its `definition_sha256` agrees; a disagreement is an integrity
error. A later revision appends a new shard part instead of rewriting an accepted
one, and the plan version is not part of the row identity. Accepted definitions are not regenerated or revalidated while the
input versions are unchanged. It does not top up a quota target incrementally
within the same plan revision.

A batch is one program pass at one task reasoning step count: the graph and
census are loaded once and every target assigned to the program at that step count
is filled from the same pass.
Passes are parallel across programs. Extra accepted definitions become reserve;
they are not dataset release rows. Track accepted and rejected counts per quota
target, family, step count, and rejection reason. A high rejection rate is a
constructor or validity signal; it is not automatically a reason to expand the
program pool.

An underfilled quota target is a deficit for `03c` after the batch, not a reason
to loop inside `03b`. A batch that exhausts its cost budget records
`construction_deficit` with detail `construction_budget`.

## Relationship to task reasoning step support

The **task reasoning step support tables** are a separate derived QA baseline.
They are computed from the rules in this document and are not an input to `03b`.
They are used to check release coverage in
[`../../../task-step-support.md`](../../../task-step-support.md).

## Deficits

A quota target that cannot be filled is recorded in the deficit ledger. `03c`
decides whether to sample more from existing graphs, use unused or reserve
programs, request supplemental `01b` selection, or accept the miss.

`03b` records the class when it knows it: `probe_deficit` when the bound state has
no surviving point probe, and `construction_deficit` when the batch is
underfilled. A search that exhausts its cost budget records `construction_deficit`
with detail `construction_budget`. Deficits that `03a` reports carry an allocation
detail instead, and `03c` classifies them.

## Construction algorithm

The search below finds a definition that satisfies the contract above.

### Purpose

Given one CAD graph and one quota target, find task definitions that satisfy the
validity contract in
[`README.md`](README.md).
Construction is a local search over one graph. It never enumerates the task space.

### Input

- one `CadGraph` from `02c`;
- one quota target from the `TaskQuotaPlan`, with its task reasoning step count,
  target category, clue type, clue operand form, answer meaning, and answer
  format;
- the program capability census from
  [`program-capability-census.md`](../algorithm/program-capability-census.md).

### Step 1 — possible-answer set

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

### Step 2 — facts and extensions

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

### Step 3 — cover search

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

### Step 4 — chain order

Order the chosen clues by dependency first, then broad-to-narrow: the size of the
narrowed set, descending, with a stable hash as the tie-break (`TG-7`). This is
the canonical order. It is identity-bearing, and validity is checked against it.
A presentation permutation is a later rendering step.

### Step 5 — validity gates

A chain that covers the wrong-answer candidates is still rejected unless it
passes the validity contract above. A chain that fails a check is recorded with
its reason. It is not repaired by adding or dropping clues silently: a shorter
valid task is a different task.

### Step 6 — acceptance

Construction proposes; the scheduler disposes. The quota scheduler accepts a
definition only when it fills an unfilled target and does not push any cell past
its maximum (`TG-2`). Overfill is rejected and recorded.

### Cost budget

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

### Determinism

Construction is deterministic for a given graph, plan version, definition schema
version, and seed. Candidate order, fact order, tie-breaks, and the cover search
use stable hashes. The same inputs produce the same definitions, so `task_id`
and the release are reproducible.

### Worked example

The box-with-hole program in
[`golden/box-with-hole.json`](../../testing/golden/box-with-hole.json) is the
first golden record. The final solid has 15 edges, not 14: the cylindrical face
carries a periodic seam edge. The top face leaves five edges, and the
cylindrical face leaves the one edge shared with the top face, so the chain is
two relation clues plus the length answer. The clue operand form profile is
`[(relation, named), (relation, named)]`. The record format and comparison rules
are in [`golden/README.md`](../../testing/golden/README.md).
