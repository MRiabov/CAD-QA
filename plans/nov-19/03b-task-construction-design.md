# 03b task construction — working design

**Status:** plan, 2026-11-19. Working design for `03b`; not a specification.
It records the construction picture and the clue-form proposal from the
2026-11-19 discussion so the construction grammar can be written next.

**Canonical home:** `docs/dataset/implementation/pipeline/03-task-generation/`.
This plan is the working record; the module contract and its decisions are the
authority once written.

**Companion docs:** `plans/nov-19/dataset-kernel-known-issues.md` (KI-DS-01,
KI-DS-02, KI-DS-03),
`docs/dataset/implementation/pipeline/03-task-generation/03b-construct-task-definitions.md`,
and `docs/dataset/requirements/task-structure.md`.

## Purpose

`03b` currently defines `TaskDefinition` fields, the clue predicate schema,
validity predicates, step accounting, canonical identity, and attempt budgets.
It does not define the construction algorithm (KI-DS-01). This document fixes
the working picture:

- a task is a path through a possible-answer set, not a filled template;
- the clue chain is the primary object, and the target and answer are the leaf;
- a clue is one narrowing statement, described by its clue type and by how
  its reference resolves;
- task construction is a local search, while quota filling is a global
  scheduler.

## The working picture: a decision tree over possible answers

For one CadQuery program and one state scope, a target category defines a
finite **possible-answer set**:

```text
possible_answers = all possible answers for target_category in state_scope
```

A clue is a typed predicate: for each possible answer it returns true, false,
or unknown. Applying a clue keeps only the answers for which it returns true:

```text
narrowed = {answer in possible_answers | clue(answer) is true}
```

A task is a sequence of clues followed by an answer step:

```text
possible_answers
  --clue_1--> narrowed_1
  --clue_2--> narrowed_2
  ...
  --clue_last--> final_set
  --answer_step--> answer
```

The constraints are:

- every clue strictly shrinks the set:
  `len(narrowed_after) < len(narrowed_before)`;
- the final set is answer-unique: every remaining possible answer produces the
  same answer within tolerance;
- the answer step produces exactly one answer;
- the step count is the number of clues plus one when an answer step is
  needed.

This makes four properties fall out of one structure:

| Property | How it falls out |
|---|---|
| Task reasoning step count | The path length. |
| Clue order | The path order, constrained to broad-to-narrow and to dependency order. |
| Uniqueness | The final set has one answer value. |
| Multiple-choice choices | The set before the last clue, for an identity answer. |

The useful consequence: the engine does not need to enumerate tasks. It needs
to search for a path that ends in one answer.

## Pipeline shape

There are two different kinds of work:

```text
per program, parallel                         per dataset release, serial
──────────────────────                        ───────────────────────────
02c CadGraph
   │
   ▼
GraphIndex
   │
   ▼
TaskSynthesizer ──► valid TaskDefinition ──► QuotaScheduler ──► DeficitLedger
   │                     candidates              │
   │                                             ├── accept into plan
   ▼                                             └── record rejection
PossibleAnswerSet
ClueGenerator
ChainSearch
AnswerResolver
Validator
```

- The **TaskSynthesizer** is local. Given one graph and one quota target, it
  searches for valid tasks. It is pure, deterministic, and parallel per
  program.
- The **QuotaScheduler** is global. It decides which quota targets to fill,
  accepts or rejects task definitions, and updates the ledger. It is serial
  because it owns the release-level counts.

The task quota plan is a shopping list: "I need 40 four-step face-area tasks,
at each step count a mix of clue forms, and at least one `comparison` clue
with a `selected` reference in the four-step bucket." The synthesizer is a
personal shopper per program. It does not enumerate the whole task space.

This also explains why enumerate-and-cut is wrong: the plan is the constraint,
and the search is local.

## The core loop

For one quota target:

```text
possible_answers = possible_answers(graph, target_category, state_scope)

for each answer_entity in stable_order(possible_answers):
    distractors = possible_answers without answer_entity
    facts = true_facts(graph, answer_entity)   # predicates true of answer_entity
    chain = cover(distractors, facts, target_depth = step_count - answer_step)
    if chain is empty: continue

    narrowed = apply(chain, possible_answers)
    if not answer_unique(narrowed): continue

    answer = resolve(narrowed, answer_meaning)
    definition = build(answer_entity, chain, answer, narrowed)
    if valid(definition): yield definition
```

Two details matter.

**`cover(distractors, facts, target_depth)` is a bounded set-cover search.**
Each fact has a precomputed set of possible answers it selects, so applying a
clue is a set intersection. A greedy cover gives the shortest chain; a less
greedy cover gives a longer chain. The target step count is therefore a search
parameter, not an outcome. If the plan asks for a four-step task, the search
looks for a three-clue cover plus the answer step. If no such cover exists, the
quota target is a deficit.

## Uniqueness

**`answer_unique(narrowed)` is not necessarily "one entity."** For a
measurement answer, two symmetric faces can both produce the same area; the
task is still answerable. The final set is then the
**`answer_equivalent_set`**: the entities still possible after the last clue,
which all produce the same answer within tolerance. The answer evidence
records the whole set, because a record that named one entity would claim the
prompt had identified it uniquely. An identity answer is the special case
where the set holds exactly one entity.

### Where uniqueness is checked

Uniqueness is one predicate, called from one place: task validity.

```text
answer_unique(narrowed) =
    every pair (a, b) in answer_equivalent_set satisfies equals(answer_meaning, a, b)
```

`equals` is supplied by the answer meaning, so there is no second code path and
no mode flag. The consequences are placed where they belong:

| Place | What it decides | Keyed on |
|---|---|---|
| Chain search | when to stop adding clues | the uniqueness predicate |
| Validity | accept or reject the task | the equality relation |
| Answer evidence | what to record | the whole `answer_equivalent_set` |
| Multiple-choice pool | how choices are built | the answer format |
| Separation | when two measurements differ | the `D4` margin |
| Release reporting | how much symmetry the corpus holds | the answer meaning |

Two consequences are easy to get wrong:

- **The search stops on `answer_unique`, never on `len(narrowed) == 1`.** Stopping
  at a singleton makes every task entity-unique by construction and silently
  removes the symmetric measurement tasks that the rule exists to keep.
- **The choice pool is keyed on the answer format, not on uniqueness.** An
  identity answer in multiple-choice format needs a singleton set, because a set
  of two cannot be expressed as one correct label. A numeric answer in
  multiple-choice format may keep a larger set.

### The equality relation

| Answer meaning | `equals(a, b)` | Priority |
|---|---|---|
| identity | `a` is `b` | P0 |
| volume, area, length, distance, angle | `abs(a - b) <= answer_tolerance` | P0 |
| count, rank | `a == b` | P0 |
| membership | same label: inside, outside, or on the boundary | P0 |
| validity | same boolean | P0 |
| position | same point within `answer_tolerance`, component by component | P1 |
| extent | same minimum and maximum corner within `answer_tolerance` | P1 |
| CadQuery workplane state | same origin and frame within `answer_tolerance` | P1 |
| material change | same added and removed volume within `answer_tolerance` | P1 |
| topology change | same face, edge, and vertex counts, and the same changed set | P1 |

`answer_tolerance` is the same constant that `D4` uses for the separation
margin. If the two diverge, a task can pass uniqueness and fail separation, or
the reverse.

`position`, `extent`, and the change meanings are P1 because their equality rule
needs a decision about component order and about which topology changes count as
the same. They are left undefined on purpose rather than guessed.

## Describing a clue

A clue is **one narrowing statement** and **one task clue step**. A task is a
chain of clues. The answer step is separate: it produces the answer, it does not
narrow.

"Stratified sampling" is reserved for dataset-level composition: splitting the
released tasks into subgroups and drawing from each in proportion to the target
population. It is not a property of one clue. The frequency target for a given
clue type is a **clue quota** or **clue share**, and it lives in `03a`.

### Two axes, one grammar

A clue has a subject, an optional reference, and a predicate:

```text
TaskClue = (clue_type, subject_binding, reference_binding | none, predicate)
```

- **`clue_type`** is what the clue asserts: property, relation, comparison,
  aggregation, or provenance. The five clue types are already defined in
  `requirements/task-structure.md`; this design does not add a sixth.
- **`clue_operand_form`** is how the clue's reference resolves. It is a property
  of `reference_binding`, and it is absent when the clue has no reference.

| Clue operand form | The reference is identified by | Example |
|---|---|---|
| `named` | its construction or geometry | "adjacent to the cylindrical face" |
| `selected` | an entity selected by an earlier clue | "adjacent to the face selected in step 1" |
| `aggregated` | an extreme, rank, or count over a set | "adjacent to the largest face of the hole" |
| `cross_state` | a before/after solid state | "created by the operation that removed the most material" |

The two axes answer different questions — what is asserted, and what it is
asserted about — so they are orthogonal wherever a reference exists. They are
not freely combinable, and the support grid says which cells are real:

| Clue type | `named` | `selected` | `aggregated` | `cross_state` |
|---|---|---|---|---|
| Property | no reference | redundant | two clues | two clues |
| Relation | canonical | canonical | needs aggregation | needs cross-state graph |
| Comparison | canonical | canonical | canonical | needs cross-state graph |
| Aggregation | canonical | canonical | degenerate | needs cross-state graph |
| Provenance | canonical | canonical | needs aggregation | canonical |

- **Property has no reference.** "The face is planar" constrains the candidate
  set directly. "The face selected in step 1 is planar" is redundant, because
  step 1 already selected it. "The largest face is planar" is aggregation plus
  property, which `requirements/task-structure.md` already splits into two
  clues. So the property row carries no operand form.
- **Aggregation with an `aggregated` reference is degenerate.** It is
  aggregation over an aggregate, and it is better written as two clues.

Of the twenty nominal cells, about fourteen are meaningful. The support table
declares the rest rather than letting the grid imply twenty equal buckets.

This also keeps the step count honest: one clue is one step regardless of how
many graph elements its evaluation reads. Resolving a reference, reading two
measurements, and comparing them is implementation cost inside one step, not
extra task reasoning steps.

### The generation lever

Clue form is not only a classification. It is how the generator populates the
grid from the same graph facts, by changing how the reference resolves:

- `relation` with a `named` reference: "the face is adjacent to the face
  created by `cutBlind`."
- `relation` with a `selected` reference: "the face is adjacent to the face
  selected in step 1."
- `relation` with an `aggregated` reference: "the face is adjacent to the
  largest face created by `cutBlind`."
- `comparison` with an `aggregated` reference: "the face has a larger area than
  every other face created by `cutBlind`."

The clue schema's `BindingRef` (target, earlier result, named graph element,
literal) is already close to what is needed. The missing pieces are the
`clue_operand_form` annotation and the aggregation and derived-measurement
support that the `aggregated` form needs.

### The answer is not a separate ladder

The answer step has its own complexity, but it is already modelled by
`answer_meaning` in `requirements/task-structure.md`: identity, volume, area,
length, distance, angle, count, rank, membership, position, extent,
CadQuery workplane state, material change, topology change, and validity.

An earlier draft added a four-level `A0`–`A3` answer ladder on top of that. It
duplicated `answer_meaning` and had no precedent in the prior-art survey, so it
is dropped. The task profile records `answer_meaning` directly.

### Task profile

A task is described by:

```text
step_count = number of clue steps + (answer step ? 1 : 0)
clue_form_profile = [(clue type, clue operand form), ...]   # one per clue
answer_meaning = one of the answer meanings
```

The step count remains the chain length. The clue form profile describes each
clue, and the operand form is absent for a clue with no reference. A four-step
task of four `property` clues is not the same benchmark item as a two-step task
of two `comparison` clues with `selected` references, even though neither
number is a difficulty label.

This is the `DS-05` tension. `DS-05` says task reasoning step count is the only
measure. The proposal is to amend it: step count is the length measure, clue
form is the per-clue measure, and neither is a task label. See `D10`.

## Worked example

Program:

```python
result = (
    cq.Workplane("XY")
    .box(10, 20, 5)
    .faces(">Z")
    .workplane()
    .circle(2)
    .cutBlind(-2)
)
```

Task shape: a four-step chain on the final solid, clue forms
`[(relation, named), (relation, named), (comparison, selected)]`, answer
meaning length. The chain resolves to an edge; the answer is its length, as
a number.

Initial possible-answer set: all edges of the final solid — the box edges plus
the two circular edges of the hole.

Bound answer entity: the top circular edge of the hole.

| Step | Clue | Set after | Clue type | Clue operand form |
|---|---|---|---|---|
| 1 | The edge is adjacent to the top face of the box. | 5 edges | Relation | `named` |
| 2 | The edge is adjacent to the cylindrical face. | 2 circular edges | Relation | `named` |
| 3 | The edge has a larger z-coordinate than the other edge adjacent to the cylindrical face. | 1 edge | Comparison | `selected` |
| Answer | Return the length. | `12.57` | none | answer meaning: length |

Each clue narrows. Clue 3 is a comparison whose reference is the other circular
edge left by clue 2, so its operand form is `selected`, not `named`. The chain
is broad-to-narrow. The answer is `2πr` rounded to 4 significant figures. The
answer evidence points to the edge, the measurement, and the rule.

If the hole were a through-hole, both circular edges would have the same
length. Then:

- **entity-unique** would require clue 3, making a four-step task;
- **answer-unique** would stop after clue 2, because both remaining edges give
  `12.57`, so the `answer_equivalent_set` holds both of them and the task has
  three steps.

That is the first schema decision (`D1` below).

## Three uses of the clue profile

### 1. Generation and quotas

Add `clue_operand_form` as a quota dimension. At each step count, require
coverage of the supported clue forms and balance them with the conditional
release share. The plan becomes "40 four-step tasks, at least one with a
`comparison` clue whose reference is `selected`," not just "40 four-step
tasks." This prevents the generator from hitting the step-count mix with four
`property` clues.

### 2. Coverage and balance

Check coverage over `(clue_type, clue_operand_form)` cells for clues that carry
a reference, not clue type alone. Otherwise a dataset can cover every clue type
at `named` references and claim coverage. A support table,
`clue-form-by-step.json`, records which clue forms are structurally supported at
each step count and why not. It also records the two known non-cells: the
property row has no operand form, and `aggregation` with an `aggregated`
reference is degenerate.

### 3. Evaluation and splits

Report accuracy by `(step_count, clue_operand_form)` and by
`(step_count, clue_type)`, not just by step count. An LLM model that fails
`selected` references is different from one that fails long chains of `named`
relations. Stratify the test split so each reported cell has enough tasks to
measure; otherwise the per-cell number is noise.

The warmup subset should be one step with only `named` references, not just one
step. A one-step `aggregated` clue is not warmup.

## Construction strategy: supply-driven, capability-aware deficits

The default construction strategy is **supply-driven**. `03b` iterates
programs and builds natural clue chains from what each graph actually has. The
clue chain is still the primary object and the target and answer are the leaf,
but the selection is local: the program supplies the facts, and the chain grows
from them.

A full demand-driven planner was considered and rejected. It would have
specified a task cell up front, queried a capability index for programs that
can support it, and synthesized into the cell. The reasons to reject it:

- the capability census needs the graph, but `01b` selects the pool before
  `02` builds graphs; a pre-selection census reverses pipeline stage order or
  forces a larger execution pass;
- a capability in the pool is not a constructed task, so the guarantee is
  necessary but not sufficient;
- a pool-level guarantee crowds the 1,500-program budget with tag reservations
  and can conflict with the two-programs-per-family cap;
- the fallback concentrates forced, unnatural tasks in the rarest cells,
  exactly where review is hardest.

What remains is a **capability-aware deficit loop**:

1. `01b` stays metadata-based.
2. `02c` emits a `ProgramCapabilityProfile` as a by-product of the graph:
   available target categories, clue constructors, supported clue operand
   forms per clue type, measurement kinds, relation kinds, answer meanings,
   maximum step count, and entity counts.
3. `03b` is supply-driven by default.
4. `03a` and `03c` use the census for deficits. When a quota target is
   underfilled, query the census for capable programs and request supplemental
   programs through the existing slow loop.
5. A cell-level demand query is a last resort. It carries a `forced` flag and
   a naturalness check, and a miss is recorded rather than forced.

This preserves pipeline stage order, keeps task construction natural, and
confines the demand logic to the deficit path where it belongs.

## Open decisions

Each decision is written so it can be answered on its own. The recommendation is
a default, not a ruling, and the ID is stable so other documents can refer to it.

Accepted decisions move to `docs/dataset/decisions.md` and are marked here with
their record ID. The clue-form model is `DS-31`, answer uniqueness is `DS-32`,
the construction strategy is `DS-33`, and state scope is `DS-34`.

### 1. `D1` — What is the equality relation for answer uniqueness?

Accepted as `DS-32`.

Options: entity identity for every answer meaning, or an equality relation
chosen per answer meaning. Recommendation: per answer meaning, as the table in
"The equality relation" above defines. Identity answers use entity identity, so
a singleton falls out of the general rule rather than being a separate mode.
Numeric answers use `answer_tolerance`; label answers compare labels.

Blocks: `TaskDefinition.answer_evidence`, the `answer_equivalent_set` field, the
validity predicate in `03b`, and the separation margin in `D4`.

### 2. `D2` — Which solid states can a task refer to?

Accepted as `DS-34`.

Options: the final state only, the final state plus one named intermediate
state, or a before/after pair. Recommendation: the final state only in P0. A
named intermediate state arrives in P1, and before/after pairs arrive in P2 with
the change answer meanings.

The state is bound before the clue chain starts and is named in the prompt
preamble. A clue cannot introduce it: the possible-answer set must exist before
the first clue is applied, and a scoping clue would spend a task reasoning step
on something that does not narrow.

Blocks: `TaskDefinition.state_scope`, question templates, and the
possible-answer set.

### 3. `D3` — How is a clue evaluated when a measurement is missing?

Withdrawn 2026-11-20.

The question assumed a template-driven search, where a clue sentence is
generated first and evaluated afterwards. The construction design enumerates
facts from the graph, and each fact carries the extension it selects, so an
unsupported predicate is never attempted and there is no inapplicable clue to
evaluate. What remains is graph completeness, which is a graph-contract rule
rather than a clue-evaluation rule: a per-entity measurement is total over its
scope, and a pair element exists only inside the declared enumeration domain.

Tracked as `MC-36` and in `requirements/graph-content.md` section 4.1.

### 4. `D4` — What counts as a separation?

Options: any difference, the answer tolerance, or a separate margin.
Recommendation: one separation margin derived from the answer tolerance. Two
answers that differ by less than the tolerance are not separated, and the clue
that would rely on the difference is rejected.

Blocks: uniqueness, tie rejection, and clue validity.

### 5. `D5` — How are clues ordered?

Options: search order, broad-to-narrow, or dependency order. Recommendation:
topological order, then a broad-to-narrow key — the size of the narrowed set,
descending, with a stable hash as the tie-break. Dependency order must come
first, because a clue that refers to an earlier selection cannot precede it.

Blocks: comparison references and prompt order.

### 6. `D6` — What is the minimum narrowing?

Options: each clue may leave one possible answer, or each clue must leave at
least `k`. Recommendation: each non-final clue leaves at least two or three
possible answers. A clue that jumps straight to one answer makes the rest of the
chain decorative.

Blocks: task quality and step count.

### 7. `D7` — Where do multiple-choice choices come from?

Options: the penultimate possible-answer set, or sibling measurements of the
answer entity. Recommendation: identity answers draw their choices from the
penultimate set, because those are the entities the last clue discriminated
between. An identity answer in multiple-choice format also needs a singleton
final set, since a set of two cannot be expressed as one correct label. Numeric
answers use sibling measurements only when at least five distinct values exist;
otherwise the choices are too easy to guess.

Blocks: multiple-choice availability.

### 8. `D8` — How does the scheduler fill the plan?

Options: per-cell greedy, or global selection across cells. Recommendation:
greedy coverage-first — fill the minimum, then the target, then the volume. This
matches the priority order already stated in `03a` and keeps the scheduler
explainable.

Blocks: quota filling and deficits.

### 9. `D9` — How are clue forms weighted?

Options: equal weight, weight by operand form, or calibrate against LLM
evaluation results. Recommendation: equal weight first, then calibrate against
LLM evaluation results. Weighting by operand form before there is measurement
data would encode a guess about difficulty that `DS-05` deliberately removed.

Blocks: coverage and balance.

### 10. `D10` — Does `DS-05` change?

Options: keep task reasoning step count as the only measure, or add clue form as
a per-clue measure. Recommendation: keep step count as the length measure and
add clue form as a per-clue measure. Neither is a task label; a task is
described by its clue form profile, not named by a grade.

Blocks: PRD section 6, R-9, and benchmark reporting.

### 11. `D11` — What is the construction strategy?

Accepted as `DS-33`.

Options: supply-driven, full demand-driven, or supply-driven with
capability-aware deficits. Recommendation: supply-driven with capability-aware
deficits. The reasons are recorded in the construction strategy section above.

Blocks: `01b`, `02c`, `03a`, `03b`, and `03c`.

## Proposed document and schema changes

| Change | Owner |
|---|---|
| Add the clue grammar and the clue form grid to `requirements/task-structure.md` and `requirements/terminology.md` | `requirements/task-structure.md`, `requirements/terminology.md` |
| Add `clue_operand_form` to `TaskClue`; add `clue_form_profile` and `state_scope` to `TaskDefinition`; add `answer_equivalent_set` to the answer evidence; define `answer_unique` over that set with an equality relation per answer meaning; record `answer_meaning` instead of an answer ladder | `03b` |
| Require a singleton `answer_equivalent_set` for an identity answer in multiple-choice format | `04` |
| Add `clue_operand_form` as a quota dimension; require coverage at each step count; balance with the conditional share | `03a` |
| Add `support/clue-form-by-step.json` | `05`, task-step support |
| Add `clue_form_profile` to the release table | release contract, `04` |
| Check coverage and balance over `(clue_type, clue_operand_form)` for reference-bearing clues | `05` |
| Emit `ProgramCapabilityProfile` as a by-product of graph construction | `02c` |
| Use the census to allocate quota targets to capable families, not to pre-select the pool | `03a` |
| Add a `capability_deficit` reason and a supplemental-program request path | `03c` |
| Keep supply-driven construction as the default; add a cell-level demand query only as a fallback with a `forced` flag | `03b` |
| Add `DS-31`: step count is the chain length; clue operand form describes how a clue's reference resolves; neither is a task label | `decisions.md` |
| State that every benchmark result names the step counts and clue forms it covers | PRD |

## Build phases

**Phase 0 — vertical slice.** One program, final solid state, target = solid
state, answer = volume, format = number, one step. This proves graph → possible
answers → answer resolver → `TaskDefinition` → render → release row. No clue
search yet.

**Phase 1 — the first real search.** Target = face, answer = area, two to three
steps. Property and relation clues only. Build the narrowing record, the
uniqueness check, and the multiple-choice pool from the penultimate set.

**Phase 2 — the full clue vocabulary.** Comparison, aggregation, provenance;
multiple target categories; distance, angle, region, CadQuery profile (after
KI-DS-02).
This is where the graph must supply the primitives.

**Phase 3 — the scheduler.** Quota-aware construction, coverage and balance,
multiple-choice availability, deficits. This is where `03b` meets `03a` and
`03c`.

**Phase 4 — P2.** Near-miss choices, six or more steps, arbitrary control flow.

Each phase gets a golden narrowing record, a property test (every accepted task
is answer-unique, every clue narrows, every clue is true of all final possible
answers), a replay test, and one end-to-end test.

## Next

The construction strategy is settled (`D11`): supply-driven with a
capability-aware deficit loop. The two schema blockers are settled as well:
`D1` (the equality relation for answer uniqueness) and `D2` (state scope). The
remaining open decisions are `D4` to `D10`, and the construction grammar can
be written with the box-and-hole example as the first golden record.

## References

- `docs/dataset/implementation/pipeline/03-task-generation/03b-construct-task-definitions.md`
- `docs/dataset/requirements/task-structure.md`
- `docs/dataset/requirements/graph-content.md`
- `docs/dataset/implementation/task-step-support.md`
- `plans/nov-19/dataset-kernel-known-issues.md`
