# 05/release checks — coverage and balance arithmetic

> Authoritative: `../../05-validate-and-export-release/release-checks.md`
> Models: `../models/05-validate-and-export-release.md`

## 1 — Share references and check selection

READ:

- `checks.yaml` → the ordered check list, each check's `id`, `arithmetic`, `scope`, `dimension`, `value`, `minimum_value`, bounds, disposition, and `known_misses`
- `balance.yaml` → `dimensions`, `release.splits`, `release.share_tolerance`
- the support-table derivation → `supported_values`
- `ReleaseTable` → observed counts

TRANSFORM:

- validate `checks.yaml` before any check runs: known fields, known `arithmetic`, unique `id`, and every bound reference resolves in `balance.yaml`
- `reference_share(scope, dimension, value) = policy_share(value) / sum(policy_share(x) for x in supported_values(scope, dimension))`; scope is a task reasoning step count or `release`
- `05` holds no share of its own
- run exactly the checks in the file; a check not in the file is not run, and a report row whose check is not in the file is a defect
- coverage rows carry supported, observed, missing, and unexpected values; there is no whole-release coverage row for a dimension
- outcome is `pass | miss | superseded | not_applicable | deferred`; disposition is `enforced | reported | deferred`
- an `enforced` miss blocks the export until the owner accepts it and it is recorded in `known_misses`; a `reported` miss never blocks; a `deferred` row measures nothing
- a `superseded` row is recorded and does not block; it is not a known miss
- emit at least one row per listed check; a report that omits a check is a rejection
- sort every report row by check name, scope, and value before writing the manifest, so the hash does not depend on the parallel schedule

WRITE:

- (none)

## 2 — Bound conversion

TRANSFORM:

- `coverage`: the observed value set equals the supported value set
- `count_floor`: the observed count is at least the bound
- `share_range`: `minimum_count = ceil(minimum_share * denominator)`, `maximum_count = floor(maximum_share * denominator)`
- `share_range` selects the measured value: `value` selects one value, `minimum_value` selects that value and every larger value, neither emits one row per value; at most one is set
- `relative_range`: `minimum_count = max(1, ceil(below * reference_share * denominator))`, `maximum_count = floor(above * reference_share * denominator)`
- `share_target`: `minimum_count = ceil((target - tolerance) * denominator)`, `maximum_count = floor((target + tolerance) * denominator)`
- `set_equal`: the observed value set equals the declared set
- the denominator is the task count, or the clue occurrence count for a clue-scoped check
- a lower bound rounds up and an upper bound rounds down, so an accepted count is inside the range in shares too

WRITE:

- (none)

## 3 — Report

TRANSFORM:

- one report row per check and scope value: `check_id, arithmetic, scope, dimension, value, observed, minimum_count, maximum_count, outcome, disposition, detail`
- `known_misses` names the accepted enforced misses, with their reason
- a report that disagrees with `release.parquet` is a defect, not a second opinion

WRITE:

- (none)
