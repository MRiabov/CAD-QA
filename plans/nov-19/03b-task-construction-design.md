# 03b task construction — working design

**Status:** plan, 2026-11-19. Working design for `03b`; not a specification.
It records the construction picture and the clue-stratification proposal from
the 2026-11-19 discussion so the construction grammar can be written next.

**Companion docs:** `plans/nov-19/dataset-kernel-known-issues.md` (KI-DS-01,
KI-DS-02, KI-DS-03), `docs/dataset/implementation/pipeline/03b-construct-task-definitions.md`,
and `docs/dataset/requirements/task-structure.md`.

## Purpose

`03b` currently defines `TaskDefinition` fields, the clue predicate schema,
validity predicates, step accounting, canonical identity, and attempt budgets.
It does not define the construction algorithm (KI-DS-01). This document fixes
the working picture:

- a task is a path through a possible-answer set, not a filled template;
- the clue chain is the primary object, and the target and answer are the leaf;
- clues are stratified by derivation depth, not by clue type alone;
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
at each step count a mix of clue strata, and at least one S3 clue in the
four-step bucket." The synthesizer is a personal shopper per program. It does
not enumerate the whole task space.

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

**`answer_unique(narrowed)` is not necessarily "one entity."** For a
measurement answer, two symmetric faces can both produce the same area; the
task is still answerable. The final set is a witness set, and the answer
evidence records it. Identity answers still require one entity.

## Clue stratification

"Stratify" is the right word. The unit is a **clue stratum** (plural: strata),
not a "difficulty level." `DS-05` retired the difficulty label, and the stratum
should not bring it back.

### Clue type is not a difficulty axis

A property clue can be shallow or deep; a relation clue can be shallow or deep.
The useful object is a **clue type × clue stratum matrix**:

| Clue type | S0 | S1 | S2 | S3 | S4 | S5 |
|---|---|---|---|---|---|---|
| Property | x | x |  | x | x | x |
| Relation |  |  | x | x | x | x |
| Comparison |  |  |  | x | x | x |
| Aggregation |  |  |  | x | x | x |
| Provenance | x |  | x | x | x | x |

The marks are illustrative; the support tables derive the real cells.

### The ladder

A clue's stratum is the number of **derivation steps** needed to evaluate it
against a possible answer, given the bindings available before the clue. One
derivation step is one of:

- read an attribute (face surface kind, curve kind, `is_closed`, operation kind);
- read a measurement (area, volume, length, count);
- traverse one graph relation to another entity;
- apply one aggregation over a set;
- apply one arithmetic or geometric derivation (difference, ratio, angle
  between normals, volume change);
- cross one solid-state boundary (before/after).

| Stratum | Name | What the clue needs | Example |
|---|---|---|---|
| **S0** | Attribute lookup | One attribute of the named entity | "The face is planar." "The edge is closed." |
| **S1** | Single measurement | One measurement of the named entity, compared to a literal | "The face area is greater than 50." |
| **S2** | Relation to a named entity | One relation traversal to another named entity | "The face is adjacent to the cylindrical face." |
| **S3** | Selection or aggregation | The operand is selected by an earlier clue, or aggregated over a set | "The face is adjacent to the face selected in step 1." "The largest face among the faces adjacent to the cylinder." |
| **S4** | Derived comparison | A measurement compared to another measurement that is itself selected or derived | "The face has a larger area than the face selected in step 1." "The angle between the two faces is less than 45°." |
| **S5** | Effect or counterfactual | A before/after state, material change, or topology change | "The operation removed more material than the previous operation." "The face existed before the operation and not after." |

The exact weights are a policy; the ordering is what matters. The stratum must
be computable from the typed clue and its bindings, not assigned by a human.

### The generation lever

Stratification is not only classification. It is how the generator populates
the ladder from the same graph facts. The same fact can be expressed at
different strata by changing the operand binding:

- **S2:** "The face is adjacent to the face created by `cutBlind`."
- **S3:** "The face is adjacent to the face selected in step 1."
- **S3:** "The face is adjacent to the largest face created by `cutBlind`."
- **S4:** "The face is adjacent to the face whose area is largest among the
  faces created by `cutBlind`."

This is the lever that lets the generator hit a target stratum without
inventing new facts. The clue schema's `BindingRef` (target, earlier result,
named graph element, literal) is already close to what is needed. The missing
pieces are the stratum annotation and the aggregation/derived-measurement
support at the higher strata.

### Answer strata

Keep the answer step separate from the clue profile. The answer still has its
own complexity:

| Stratum | Name | Example |
|---|---|---|
| **A0** | Identity | Return the multiple-choice label. |
| **A1** | Single measurement | Volume, area, length, count. |
| **A2** | Derived measurement | Distance, angle, ratio, bounding box. |
| **A3** | Effect | Volume change, topology change, material change. |

### Task profile

A task is described by:

```text
step_count = number of clue steps + (answer step ? 1 : 0)
clue_stratum_profile = [clue 1 stratum, clue 2 stratum, ...]   # one per clue
max_clue_stratum = max(clue_stratum_profile)
answer_stratum = one of A0, A1, A2, A3
```

The step count remains the chain length. The clue profile is the per-clue
derivation depth. A four-step task of four S0 clues is not the same benchmark
item as a two-step task of two S4 clues.

This is the `DS-05` tension. `DS-05` says task reasoning step count is the only
measure. The proposal is to amend it: step count is the length measure; clue
stratum is the per-clue measure; neither is a task label. See `D10`.

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

Task shape: a four-step chain on the final solid, with clue strata
`[S2, S2, S4]` and answer stratum `A1`. The chain resolves to an edge; the
answer is its length, as a number.

Initial possible-answer set: all edges of the final solid — the box edges plus
the two circular edges of the hole.

Witness answer: the top circular edge of the hole.

| Step | Clue | Set after | Clue stratum |
|---|---|---|---|
| 1 | The edge is adjacent to a planar face. | Many edges | S2 |
| 2 | The edge is adjacent to the cylindrical face. | 2 circular edges | S2 |
| 3 | The edge has a larger z-coordinate than the other edge adjacent to the cylindrical face. | 1 edge | S4 |
| Answer | Return the length. | `12.57` | A1 |

Each clue narrows. Clue 3 is a comparison whose reference is the other circular
edge selected by clue 2. The chain is broad-to-narrow. The answer is `2πr`
rounded to 4 significant figures. The answer evidence points to the edge, the
measurement, and the rule.

If the hole were a through-hole, both circular edges would have the same
length. Then:

- **entity-unique** would require clue 3, making a four-step task;
- **answer-unique** would stop after clue 2, because both remaining edges give
  `12.57`, making a three-step task.

That is the first schema decision (`D1` below).

## Three uses of stratification

### 1. Generation and quotas

Add `clue_stratum` as a quota dimension. At each step count, require coverage
of the supported strata and balance them with the conditional release share.
The plan becomes "40 four-step tasks, at least one S2 and one S3 clue in each,"
not just "40 four-step tasks." This prevents the generator from hitting the
step-count mix with five trivial clues.

### 2. Coverage and balance

Check coverage over `(clue_type, clue_stratum)` cells, not clue type alone.
Otherwise a dataset can cover every clue type at S0 and claim coverage. A fifth
support table, `clue-stratum-by-step.json`, records which strata are
structurally supported at each step count and why not.

### 3. Evaluation and splits

Report accuracy by `(step_count, max_clue_stratum)`, not just by step count. An
LLM model that fails S3 selection is different from one that fails long chains
of S0 lookups. Stratify the test split so each cell has enough tasks to
measure; otherwise the per-stratum number is noise.

The warmup subset should be **one step and `max_clue_stratum <= 1`**, not just
one step. A one-step S3 aggregation is not warmup.

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
   available target categories, clue constructors, maximum clue stratum per
   constructor, measurement types, relation types, answer meanings, maximum
   step count, and entity counts.
3. `03b` is supply-driven by default.
4. `03a` and `03c` use the census for deficits. When a quota target is
   underfilled, query the census for capable programs and request supplemental
   programs through the existing slow loop.
5. A cell-level demand query is a last resort. It carries a `forced` flag and
   a naturalness check, and a miss is recorded rather than forced.

This preserves pipeline stage order, keeps task construction natural, and
confines the demand logic to the deficit path where it belongs.

## Open decisions

| ID | Decision | Options | Recommendation | Blocks |
|---|---|---|---|---|
| D1 | What is the uniqueness unit? | Entity-unique; answer-unique; hybrid | Hybrid: identity is entity-unique, measurement is answer-unique with a witness set | `TaskDefinition.target_binding`, `answer_evidence`, choice pool |
| D2 | Does the question name the solid state? | Question names it; first clue names it | Question names it; add `state_scope` to `TaskDefinition` | Question templates, possible-answer set |
| D3 | How is a clue evaluated when a measurement is missing? | Unknown means false; clue is invalid | Clue is applicable only when the predicate is total on the current set | Chain search, rejection reasons |
| D4 | What counts as a separation? | Any difference; answer tolerance; separate margin | One separation margin derived from the answer tolerance | Uniqueness, tie rejection, clue validity |
| D5 | How are clues ordered? | Search order; broad-to-narrow; dependency order | Topological order with a broad-to-narrow key: the size of the narrowed set, descending, then hash | Comparison references, prompt order |
| D6 | What is the minimum narrowing? | One possible answer; at least k | Each non-final clue leaves at least 2–3 possible answers | Task quality, step count |
| D7 | Where do multiple-choice choices come from? | Penultimate set; sibling measurements | Identity from the penultimate set; numeric only when at least 5 distinct values exist | Multiple-choice availability |
| D8 | How does the scheduler fill the plan? | Per-cell greedy; global selection | Greedy coverage-first: minimum, then target, then volume | Quota filling, deficits |
| D9 | How are strata weighted? | Equal; weighted by derivation depth | Equal first, then calibrate against LLM model results | Coverage and balance |
| D10 | Does `DS-05` change? | Keep step count as the only measure; add clue stratum | Add clue stratum as a second measure; neither is a task label | PRD section 6, R-9, benchmark reporting |
| D11 | What is the construction strategy? | Supply-driven; full demand-driven; supply-driven with capability-aware deficits | Supply-driven with capability-aware deficits | `01b`, `02c`, `03a`, `03b`, `03c` |

## Proposed document and schema changes

| Change | Owner |
|---|---|
| Add the S0–S5 ladder, the A0–A3 answer strata, and the clue type × clue stratum matrix | `requirements/task-structure.md`, or a new `requirements/clue-stratification.md` |
| Add `clue_stratum` to `TaskClue`; add `clue_stratum_profile`, `max_clue_stratum`, `answer_stratum`, and `state_scope` to `TaskDefinition`; add the derivation rule | `03b` |
| Add `clue_stratum` as a quota dimension; require coverage at each step count; balance with the conditional share | `03a` |
| Add `support/clue-stratum-by-step.json` | `05`, task-step support |
| Add `clue_strata` and `max_clue_stratum` to the release table | release contract, `04` |
| Check coverage and balance over `(clue_type, clue_stratum)` | `05` |
| Emit `ProgramCapabilityProfile` as a by-product of graph construction | `02c` |
| Use the census to allocate quota targets to capable families, not to pre-select the pool | `03a` |
| Add a `capability_deficit` reason and a supplemental-program request path | `03c` |
| Keep supply-driven construction as the default; add a cell-level demand query only as a fallback with a `forced` flag | `03b` |
| Add `DS-31`: step count is the chain length; clue stratum is the per-clue derivation depth; neither is a task label | `decisions.md` |
| State that every benchmark result names the step counts and clue strata it covers | PRD |

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
capability-aware deficit loop. The two decisions that still block the schema
are `D1` (uniqueness unit) and `D2` (state scope). Once they are settled, the
construction grammar can be written with the box-and-hole example as the first
golden record.

## References

- `docs/dataset/implementation/pipeline/03b-construct-task-definitions.md`
- `docs/dataset/requirements/task-structure.md`
- `docs/dataset/requirements/graph-content.md`
- `docs/dataset/implementation/task-step-support.md`
- `plans/nov-19/dataset-kernel-known-issues.md`
