# 05/release checks — test contract

**Parent:** [`README.md`](../05-validate-and-export-release.md).

**Contract under test:**
[`../../05-validate-and-export-release/release-checks.md`](../../05-validate-and-export-release/release-checks.md),
with the policy in `generator/config/checks.yaml` and `generator/config/balance.yaml`.

## Tests

`test_05_check_outcomes` — the three fixture checks produce `pass`, `miss` with
disposition `reported`, and `not_applicable`, and the export proceeds. An
enforced miss blocks it, and the manifest is not written. The test reads the
outcome and disposition from the manifest, not from a log.

`test_05_known_miss` — an enforced miss listed in `known_misses` proceeds and the
manifest carries the accepted reason. The same release without the entry blocks
and names the check.

`test_05_unknown_check_field` — an unknown field, an unknown `arithmetic`, a
duplicate `id`, or a bound reference that does not resolve in `balance.yaml`
stops the export before any check runs, and no check report row is written.

`test_05_bound_conversion` — each arithmetic converts its bound to an integer
count with the documented rounding: `share_range` rounds the lower bound up and
the upper bound down, `relative_range` uses
`max(1, ceil(below * reference_share * denominator))`, and `share_target` uses
the target plus or minus the tolerance. The test recomputes the counts itself.

`test_05_coverage_rows` — a coverage row carries supported, observed, missing,
and unexpected values, and there is no whole-release coverage row for a
dimension.

`test_05_report_is_sorted` — the report rows are sorted by check name, scope,
and value, so two runs with different parallel schedules produce identical
manifest bytes.

`test_05_no_share_of_its_own` — changing a share in `balance.yaml` changes the
check outcome and the manifest policy hash; `05` has no hardcoded share.

**TDD pin:** pins the check-outcome vocabulary, known misses, policy validation,
bound conversion, and report ordering before `05` exists.

## What this does not prove

- That the release table is well formed. That is [`README.md`](../05-validate-and-export-release.md).
- That the plan is feasible. That is
  [`../03-task-generation/03a-allocate-task-quotas/README.md`](../03-task-generation/03a-allocate-task-quotas/README.md).
