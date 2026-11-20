# 03b construct task definitions — adversarial integration test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:**
[`../03-task-generation/03b-construct-task-definitions.md`](../03-task-generation/03b-construct-task-definitions.md),
with the search in
[`../03-task-generation/algorithm/construction.md`](../03-task-generation/algorithm/construction.md).

## Happy-path integration test (test-first, adversarial)

`test_03b_golden_record` — constructs a definition from
[`golden/box-with-hole.json`](golden/box-with-hole.json) with its pinned
construction input, and compares it per
[`golden/README.md`](golden/README.md).

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
coverage fixtures in [`fixtures/`](fixtures/),
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

`test_03b_multiple_choice_pool` — a multiple-choice definition carries a labeled
pool that passes every P0 row of the check list: five to seven entries, labels
contiguous from `A`, answer values distinct under `same_answer`, the correct
label present, and descriptions rendered from distinct facts. A pool of five that
repeats an answer value is rejected, not trimmed to four.

**TDD pin:** pins the golden record, the validity record's closed set, the
redundant-clue rejection, and the choice pool before `03b` exists.

## Failure-mode tests

- `test_03b_probe_deficit` — a state with no surviving point probe yields a
  `probe_deficit` and no membership task, and writes no failure row, because no
  definition was attempted.
- `test_03b_duplicate_definition` — a second definition with the same canonical
  identity is recorded as `definition_unique` and does not consume quota.
- `test_03b_answer_uniqueness` — an answer-equivalent set that disagrees under
  `same_answer` is rejected, and an identity answer with two entries is rejected
  (`DS-32`).
- `test_03b_definition_immutable` — a re-run with the same input versions
  produces a byte-identical definition and `definition_sha256`; a changed
  `plan_version` does not change either.
- `test_03b_target_ambiguity` — a target that resolves to two entities is
  rejected as `target_binding_unambiguous`.

## What this does not prove

- That the prompt renders. That is
  `04-render-prompt-and-choices.md`.
- That the release is balanced. That is
  `05-validate-and-export-release.md`.
- That a value is supported. That is [`00-support-tables.md`](00-support-tables.md).
