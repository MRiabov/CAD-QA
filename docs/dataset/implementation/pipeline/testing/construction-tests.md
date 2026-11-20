# Construction test contract

**Parent:** [`README.md`](README.md).

**Contracts under test:**
[`03b` construct task definitions](../03-task-generation/03b-construct-task-definitions.md),
[task construction](../03-task-generation/algorithm/construction.md), the pair and
probe rules in [`graph-content.md`](../../../requirements/graph-content.md), and
their derivation in
[`graph-construction.md`](../extraction/graph-construction.md).

**Status:** draft, 2026-11-20. Closes `MC-41`.

## What is proven

A constructor can accept an invalid task in two ways: it can fail to run a
validity rule, or it can run the rule and still accept a task that breaks it. The
first is caught by the validity record, the second only by an independent
evaluation of the same rule.

Three tiers keep the cost proportional to what each one proves.

| Tier | Proves | Needs CadQuery | Runs |
|---|---|---|---|
| Definition | Every accepted definition satisfies the rules the definition alone decides. | no | every commit |
| Graph | The graph input is complete, and the rules that read the graph hold. | yes | the generation job |
| End-to-end | The golden record is what the constructor produces. | yes | the generation job |

The definition tier is cheap and runs everywhere. It cannot check a rule that
reads the graph, so the graph tier carries those. Neither tier proves that an
answer is correct in the world; that is the kernel, and the answer evidence
records it.

## Where the tests live

| Tier | Suite | Language |
|---|---|---|
| Definition | `03b` construct task definitions | Go |
| Graph, point probe and `is_inside` | `02b` execute CadQuery | Python, needs CadQuery |
| Graph, pair emission | `02c` build CAD graph | Go, consumes the `02b` output |
| End-to-end | the generation job, with `02a` to `02c` as subprocesses | Go |

A test sits next to the rule it proves. A definition rule is not re-tested in
`02c`, and a pair rule is not re-tested in `03b`.

## The validity record is the list

`03b` names every validity rule, and an accepted definition carries one `checks`
entry per rule, except `geometry_required_recorded`, with outcome `pass`. The
definition tier asserts two things for every accepted definition:

1. `validity_record.checks` carries every named rule except
   `geometry_required_recorded`, each with outcome `pass`;
2. an independent evaluation of every rule the definition decides agrees with the
   record.

The second assertion is the point. A constructor that skips `clue_narrows` and
records a pass fails the first. A constructor that records a pass for a clue whose
`after` count equals its `before` count fails the second.

### Rules the definition decides

| Check | Read from |
|---|---|
| `clue_narrows` | Each clue's `narrows.before` and `narrows.after`. |
| `answer_equivalence` | `answer_evidence.answer_equivalent_set` under `same_answer`. |
| `single_gold_answer` | `gold_answer` and the presence of the answer step. |
| `family_and_split_present` | `cadevolve_program_family_id` and `split`. |
| `split_matches_assignment` | `split` against the plan's family assignment. |
| `subset_matches_step_count` | `subset` against `task_reasoning_step_count`. |
| `answer_evidence_present` | `answer_evidence`. |
| `choice_pool_valid` | `choice_pool`: size, labels, distinctness, the correct label, and the answer space. |
| `definition_unique` | `task_id` over the accepted set. |
| `geometry_required_recorded` | `geometry_required` against the clues. |

### Rules the graph decides

| Check | Read from |
|---|---|
| `clue_satisfied` | Each clue's check against the graph entity it binds. |
| `clue_necessary` | Removing a clue and recomputing the answers of the remaining candidates. |
| `predicate_margin` | Each predicate's margin against the clear-case margin. |
| `scalar_target_agrees` | Every remaining measurement instance. |
| `target_binding_unambiguous` | The binding resolves to one entity or one measurement instance. |
| `choice_pool_valid`, real candidates | Each entry against the penultimate answer candidate set. |

`choice_pool_valid` appears in both tables because the rule spans them: the pool's
shape is in the definition, and whether an entry is a real candidate is in the
graph.

`near_miss_valid` is P2 and deferred with the P2 scope. It joins the definition
tier when near-miss generation lands.

## Pair emission completeness

The contract is [`graph-content.md` section 4.1](../../../requirements/graph-content.md#41-emission-rules):
for one solid state the emitted pairs are

```text
named endpoint × candidate endpoints of the declared endpoint entity kinds
```

and every accepted graph carries all of them. The named-endpoint derivation and
the row rules are in `graph-construction.md`.

The test builds a fixture graph, then for every pair relation and pair
measurement:

1. derive the named endpoints of the state and the candidate endpoints of the
   declared entity category;
2. compute the expected pair set as their cross product, drop a pair whose two
   endpoints are the same entity, and reduce to unordered pairs;
3. compare with the emitted rows as a set, with the endpoints in canonical id
   order.

A missing pair fails. So does an extra pair, and the extra pair is the more
dangerous one: it is a predicate the graph does not support, and a clue built from
it would be a fact about nothing.

Two edge cases are asserted separately. A name that resolves to zero entities
emits no pair, and so does a name that resolves to several. The test names a
face surface kind the program does not have, and a position name two faces share.
Both names exist only as a lookup, so neither creates a pair row.

## `is_inside` reproducibility

The contract is [`graph-content.md` section 2.1](../../../requirements/graph-content.md#21-point-probes)
and `03b`'s membership section. A point probe records the point, the
classification, the distance to the nearest face, and the classifier. `03b` copies the point and the classification into the
definition, so it never needs a kernel.

The test recomputes `is_inside(state, point)` for every probe and compares the
classification, and recomputes the distance within kernel noise. It also asserts
the probe count: one or two per solid state, and the first probe is the state
centroid.

A definition that carries a point no probe emitted, or a classification the
kernel does not reproduce, fails. This is the only rule that calls the kernel
directly, which is why it belongs to `02b` and not to `03b`.

## Clear-case margin rejection

The contract is [`graph-content.md` section 4.2](../../../requirements/graph-content.md#42-tolerance):
a predicate must be decided by at least `100 × geometric_tolerance`, default
`1e-4` relative, and a probe within that margin of a face surface is discarded.

Two assertions.

**A predicate below the margin rejects the task.** The fixture is a **rejection
fixture**: a deliberately degenerate program, such as a cut tangent to a face. A
coverage fixture is representative and defines the support table; a rejection
fixture is degenerate and must be rejected. The two sets are kept apart, so a
degenerate program cannot make a support-table cell look supported. A rejection
fixture records its expected failure reason, and the test asserts that reason, so
a rejection cannot silently become an acceptance or a different rejection.

**A probe within the margin is discarded.** This is a unit test on the probe
filter and the deficit path, with constructed probe rows, not a program. A
well-formed solid keeps its centroid probe, because the centroid is far from every
face, so no realistic program reaches zero probes. The test feeds the filter a
probe below the margin and asserts it is dropped, then feeds a state with no
surviving probe and asserts the constructor records a `probe_deficit` rather than
a guessed answer.

## Redundant clue rejection

The contract is `clue_narrows` and `clue_necessary`, and construction step 5. Two
assertions on the golden record's program:

1. **A clue that does not narrow is rejected.** Append the plan's third clue for
   the box with a hole, a comparison of the two circular edges' lengths. After the
   second clue one edge remains, so `before` and `after` are both 1 and the
   definition fails `clue_narrows`. The test asserts that the failure names
   `clue_narrows`, not a generic rejection.
2. **A step count above the program's necessary clues is a deficit, not a padded
   task.** Ask the same program for a four-step length task. Construction yields
   no accepted definition and one `no_cover` deficit.

The second assertion is what stops the failure that produced the plan's four-step
example: a search that keeps adding clues until the count matches.

## End-to-end: the golden record

The test constructs a definition from
[`golden/box-with-hole.json`](golden/box-with-hole.json) with its pinned
construction input, and compares it per
[`golden-records.md` section 6](golden-records.md#6-comparison):

- the task description fields;
- every clue's order, clue type, operand form, subject, check, and narrowing
  counts;
- the answer fields, including `choices`;
- the resolved entity for each descriptor, not an entity identifier.

It also compares the counts against the graph: `possible_answer_count` is the
number of target-category entities in the final state, and each clue's `before`
and `after` are the graph's counts. That is the part the record format test cannot
prove.

[`tests/test_golden_records.py`](../../../../../tests/test_golden_records.py)
proves the record is well-formed. This test proves the constructor agrees with it.
A failure is a regression until the review establishes a contract change; the
record is not edited to match the constructor.

## What this does not prove

- That the release is balanced. That is the check policy in
  [`../05-validate-and-export-release/release-checks.md`](../05-validate-and-export-release/release-checks.md).
- That a value is supported. That is the support table's witness tier in
  [`task-step-support.md`](task-step-support.md).
- That a task is natural or well worded. That is the review gate.
- That the answer is correct in the world. The test checks that the evidence is
  reproduced, not that the geometry is right; the kernel measured it once, and
  the answer evidence records which call.
