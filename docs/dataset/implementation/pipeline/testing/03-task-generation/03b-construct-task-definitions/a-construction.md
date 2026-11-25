# 03b/a construction — test contract

**Parent:** [`README.md`](README.md).

**Contract under test:**
[`../../../03-task-generation/03b-construct-task-definitions/a-construction.md`](../../../03-task-generation/03b-construct-task-definitions/a-construction.md).

## Happy-path integration test (test-first, adversarial)

`test_03b_golden_record` — constructs a definition from
[`../../golden/box-with-hole.json`](../../golden/box-with-hole.json) with its
pinned construction input, and compares it per
[`../../golden/README.md`](../../golden/README.md).

**Given** the box-with-hole graph and the pinned `constructor_version`,
`construction_seed`, and schema versions from the record.

**When** `03b` constructs the three-step length task.

**Then** compare:

- the task description fields: target category, state scope,
  `possible_answer_count`, task reasoning step count, answer meaning, native
  answer format, answer format, and `geometry_required`;
- every clue's order, clue type, reduction form, subject, check, and narrowing
  counts;
- the answer fields, including `choices`, `gold_answer`, `answer_unit`,
  `tolerance`, `scoring_rule`, and `answer_evidence`;
- each entity descriptor by resolving it against the graph and comparing the
  resolved entity, never an entity identifier.

Also assert the counts against the graph: `possible_answer_count` is the number
of target-category entities in the final state, and each clue's `before` and
`after` are the graph counts. That is the part the record format test cannot
prove.

`test_03b_validity_record_is_complete` — for every accepted definition over the
coverage fixtures in [`../../fixtures/`](../../fixtures/),
`validity_record.checks` carries every named rule except
`geometry_required_recorded`, each with outcome `pass`, and an independent
evaluation of every rule the definition decides agrees with the record. In a P1
run the set also includes `shortcut_resistance`; a P0 run has no such entry.

Two failures are distinguished. A constructor that skips `clue_narrows` fails the
first assertion. A constructor that records a pass for a clue whose `after` count
equals its `before` count fails the second.

`test_03b_geometry_required` — `geometry_required` is recomputed from the
solution sequence and the stored value equals the recomputed value. The
0-clue 1-step volume and membership records
([`box-volume.json`](../../oracles/task-construction/box-volume.json),
[`box-membership-inside.json`](../../oracles/task-construction/box-membership-inside.json))
are true; a task whose only clues are provenance and whose answer is an identity
is false. A stored value that disagrees fails `geometry_required_recorded`.

`test_03b_shortcut_resistance` — P1 only. The constructor calls the standalone
`evaluate_shortcut_resistance` and records one validity check:

- a one-operation box volume fails `shortcut_resistance` and writes a failure
  row; the definition is not persisted;
- a three-operation chain passes, and its detail carries the operation count and
  the topology flag;
- a face count after a cut passes through the topology dependency;
- a task with `geometry_required = false` records `not_applicable`;
- a subject whose graph provenance cannot resolve records `unknown`, and the
  definition is rejected.

The test recomputes the dependency count from the fixture graph and asserts the
validity detail. It also asserts that no dependency chain or operation-id list is
stored. A P0 run records no `shortcut_resistance` entry.

`test_03b_redundant_clue_rejected` — two assertions on the same program:

1. Append the plan's third clue for the box with a hole, a comparison of the two
   circular edges' lengths. After the second clue one edge remains, so `before`
   and `after` are both 1 and the definition fails `clue_narrows`. The failure
   names that check, not a generic rejection.
2. Ask for a four-step length task. Construction yields no accepted definition,
   one `no_cover` failure row, and a deficit for the unfilled target. It does not
   add a clue to reach the count.

**TDD pin:** pins the golden record, the validity record's closed set, the
redundant-clue rejection, and the no-cover deficit before `03b` exists.

`test_03b_clue_capability` — one parametric test over the clue kinds. For every
set-narrowing kind, a witness graph where the clue leaves at least two candidates.
For every computed selection, a witness where the input set has at least two
candidates and the selection leaves one. A global identity name has no witness and
is rejected. The witness fixtures are a work item; the test names the capability
each one must provide.

`test_03b_answer_group` — the box face-area program has two 100 mm² faces. A clue
chain that leaves both produces one accepted definition whose
`answer_equivalent_set` holds both faces with distinct subjects, and whose
`target_binding` is one face. The other witness with the same canonical clue
sequence is a `prompt_unique` duplicate and is not accepted; it writes no failure
row. A witness with a different clue sequence is a separate definition.

`test_03b_prompt_ambiguous` — two definitions with the same prompt identity but
different gold answers are rejected as `prompt_ambiguous`, write no accepted row,
and leave the target as a deficit.

`test_03b_necessary_clue_bound` — a candidate set with `m` distinct answers
accepts at most `m - 1` clue steps. A quota target that asks for `m` clue steps
produces no accepted definition, and the rejection is `no_cover` or a census
exclusion, never a redundant clue.

`test_03b_answer_projection_once` — a counting graph reader asserts that one pass
reads each candidate's answer once per answer meaning, not once per witness or
comparison. The count is at most candidates times meanings, independent of the
number of witnesses.

## Failure-mode tests

- `test_03b_probe_deficit` — a state with no surviving point probe yields a
  `probe_deficit` and no membership task, and writes no failure row, because no
  definition was attempted.
- `test_03b_target_ambiguity` — a target that resolves to two entities is
  rejected as `target_binding_unambiguous`.
- `test_03b_construction_budget_exhausted` — a search that hits a cost constant
  records `construction_deficit` with detail `construction_budget`, writes no
  failure row, and does not retry inside the same plan revision.

## What this does not prove

- That the answer value is right. That is [`b-answer-semantics.md`](b-answer-semantics.md).
- That the definition is unique. That is
  [`c-definition-identity.md`](c-definition-identity.md).
