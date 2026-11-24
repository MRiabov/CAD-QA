# 03a allocate task quotas — adversarial integration test (TDD)

**Parent:** [`../../00-testing-strategy.md`](../../00-testing-strategy.md).

**Contract under test:**
[`../../../03-task-generation/03a-allocate-task-quotas/README.md`](../../../03-task-generation/03a-allocate-task-quotas/README.md),
with the balance policy in `generator/config/balance.yaml` and the census in
[`../../../03-task-generation/algorithm/program-capability-census.md`](../../../03-task-generation/algorithm/program-capability-census.md).

This folder mirrors the authoritative `03a` folder. The test contract for this pipeline stage is here; the
phase tests are the lettered sub-documents.

## Test inventory

| Doc | Test contract |
|---|---|
| [`a-support-derivation.md`](a-support-derivation.md) | Census derivation and reuse; support values. |
| [`b-balance.md`](b-balance.md) | Balance policy load rules and the conditional share. |
| [`c-quota-allocation.md`](c-quota-allocation.md) | Step quotas, quota targets, family task capacity, splits, attempt budgets, determinism. |
| [`d-replan.md`](d-replan.md) | Residual replan against an accepted ledger. |

The happy-path test is in [`c-quota-allocation.md`](c-quota-allocation.md); it
pins the whole plan through the persisted `TaskQuotaPlan` reader that `03b`
uses.

## What this does not prove

- That a task can be constructed. That is
  [`../03b-construct-task-definitions/README.md`](../03b-construct-task-definitions/README.md).
- That a deficit can be resolved. That is
  [`../03c-resolve-deficits.md`](../03c-resolve-deficits.md).
- That the release is balanced. That is
  [`../../05-validate-and-export-release.md`](../../05-validate-and-export-release.md).
