# 03a — Allocate task quotas to program families

**Parent:** [`../README.md`](../README.md).

**Purpose:** allocate task quotas and quota targets to CADEvolve program
families, assign splits, and set construction attempt budgets before task
definitions are generated.

**Input/output contract:** [`../../io-contracts.md`](../../io-contracts.md).

## Input / output

- Input: CAD graphs for the selected program pool, `ProgramMetadata` from `01a`
  and `ProgramSelection` from `01b`, the support-table derivation, the balance
  policy (`balance.yaml`), the current `DeficitLedger` (empty on the first plan),
  and `ProgramReassignmentRequest` records from `03c`.
- Output: `TaskQuotaPlan` and the derived task reasoning step support table at
  `support/support.parquet`.

The plan's `seed` is the run's `plan_seed`; the run manifest records it. A plan
revision is a new Parquet part keyed by `plan_version`, and resume reads the
current revision. See
[`../../../run-contract.md`](../../../run-contract.md#4-incremental-parquet-persistence).

## Documents

| Doc | Contract |
|---|---|
| [`a-support-derivation.md`](a-support-derivation.md) | The support-table derivation and the program capability census. |
| [`b-balance.md`](b-balance.md) | The balance policy and the conditional share. |
| [`c-quota-allocation.md`](c-quota-allocation.md) | The plan, quota targets, allocation equations, family assignment, and attempt budgets. |
| [`d-replan.md`](d-replan.md) | Residual replanning and the deficit details `03a` records. |

## Resolved questions

- **Q1.** *Resolved 2026-10-21.* Use quota planning, not enumerate-and-cut.
  Select and sample into a task quota plan.
- **Q3.** *Resolved 2026-10-21.* Allocate the conditional release share from the
  global quota shares before task construction, then fill from available data.

## Not here

Task definition validity, clue predicates, answer resolution, prompt rendering,
and dataset release validation.
