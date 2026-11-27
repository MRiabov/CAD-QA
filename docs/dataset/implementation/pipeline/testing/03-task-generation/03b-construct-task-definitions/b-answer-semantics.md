# 03b/b answer semantics — test contract

**Parent:** [`README.md`](README.md).

**Contract under test:**
[`../../../03-task-generation/03b-construct-task-definitions/b-answer-semantics.md`](../../../03-task-generation/03b-construct-task-definitions/b-answer-semantics.md).

## Tests

`test_03b_multiple_choice_pool` — a multiple-choice definition carries a labeled
pool that passes every P0 row of the check list: five to seven entries, labels
contiguous from `A`, answer values distinct under `same_answer`, the correct
label present, and descriptions rendered from distinct facts. A pool of five
that repeats an answer value is rejected, not trimmed to four.

`test_03b_answer_uniqueness` — an answer-equivalent set that disagrees under
`same_answer` is rejected, and an identity answer with two entries is rejected
(`DS-REQ-15`).

`test_03b_membership_uses_the_probe` — a membership task's `answer_parameter` is
the probe point, the answer is the probe classification, and the evidence
carries the point, the solid state, the distance to the nearest face, the
classifier, and the margin. A point inside the clear-case margin is not used.

`test_03b_same_answer_precision` — a number answer at 4 significant figures
compares equal only at that precision; a coordinate compares componentwise; a
material change compares the signed volume, so a cut answers a negative number.

`test_03b_distance_reads_the_clue_reference` — a distance task whose clue binds a
three-face reference set resolves to the smallest stored `distance` between the
bound target and any member of that set, and its evidence names the target, the
nearest member, and the measurement row. A distance task whose definition has no
bound reference set is rejected with that reason, not resolved to zero. A
reference set holding one member supplies that member. The distance comes from
the graph, so the resolver never calls the kernel.

**TDD pin:** pins the choice pool, answer uniqueness, membership evidence,
`same_answer`, and the pair-answer reference reading before `03b` exists.

## What this does not prove

- That the chain covers the wrong answers. That is
  [`a-construction.md`](a-construction.md).
