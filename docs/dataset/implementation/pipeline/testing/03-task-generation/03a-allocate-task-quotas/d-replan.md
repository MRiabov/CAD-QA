# 03a/d replan — test contract

**Parent:** [`README.md`](README.md).

**Contract under test:**
[`../../../03-task-generation/03a-allocate-task-quotas/d-replan.md`](../../../03-task-generation/03a-allocate-task-quotas/d-replan.md).

## Tests

`test_03a_replan_keeps_accepted_work` — a replan from a ledger with 40 accepted
identity tasks produces a new plan whose identity target is unchanged, whose
remaining target is `max(0, new - accepted)`, and whose budget is computed from
the remaining count. `parent_plan_version` names the previous version, every new
absolute target is at least the accepted count, and a family with accepted tasks
keeps its split.

`test_03a_replan_rejects_a_shrinking_target` — a `ProgramReassignmentRequest`
whose new absolute target is below the accepted count is rejected, the current
plan version is kept, and the previous plan and accepted definitions are
unchanged.

`test_03a_replan_does_not_fetch` — the fast loop writes no program request, no
fetch, no normalize, and no execute call; only the plan part and the deficit
ledger change.

**TDD pin:** pins the remaining-amount equations, the immutability rule, and the
no-fetch rule before `03a` exists.

## What this does not prove

- That the deficit controller picks the right loop. That is
  [`../03c-resolve-deficits.md`](../03c-resolve-deficits.md).
