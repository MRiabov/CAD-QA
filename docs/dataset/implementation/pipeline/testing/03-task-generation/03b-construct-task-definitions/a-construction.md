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
- every clue's order, clue type, operand form, subject, check, and narrowing
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
evaluation of every rule the definition decides agrees with the record.

Two failures are distinguished. A constructor that skips `clue_narrows` fails the
first assertion. A constructor that records a pass for a clue whose `after` count
equals its `before` count fails the second.

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
