# 03a/b balance — test contract

**Parent:** [`README.md`](README.md).

**Contract under test:**
[`../../../03-task-generation/03a-allocate-task-quotas/b-balance.md`](../../../03-task-generation/03a-allocate-task-quotas/b-balance.md).

## Tests

`test_03a_unknown_policy_key` — a misspelled key in the policy fixture fails the
plan and names the key; it does not fall back to a default.

`test_03a_policy_drives_the_plan` — changing one number in the policy fixture
changes the plan, and changing the policy version changes the plan version and
the recorded policy hash. No test compares the fixture to the shipped defaults.

`test_03a_conditional_share_is_renormalized` — a value supported at a step count
gets its global share divided by the sum of the supported values' shares at that
step count; a value not supported at that step count contributes nothing. The
test computes the share itself.

`test_03a_policy_invariants` — a share outside `(0, 1]`, a step-share sum that
misses 1 by more than `1e-9`, a split sum that misses 1, or `min > max` fails
the plan and names the offending key.

**TDD pin:** pins unknown-key rejection, policy-driven output, and the
conditional share before `03a` exists.
