# 03a/b balance — policy load and conditional share

> Authoritative: `../../../03-task-generation/03a-allocate-task-quotas/b-balance.md`
> Models: `../../models/03-task-generation.md`

## Load — balance policy

READ:

- `balance.yaml` → `release`, `task_reasoning_step_share`, `task_reasoning_step_share_p0_fallback`, `expansion`, `construction`, `dimensions`, `version`
- the support-table derivation → `supported_values`

TRANSFORM:

- read every required key at every level; an unknown key is an error, not a default
- `task_reasoning_step_share` and `release.splits` each sum to 1 within `1e-9`
- every share is in `(0, 1]`; `min <= max` when both are present; `version` is a positive integer
- a missing `min` means no minimum; a missing `max` means no cap; a missing `target` means an equal share among supported values
- `task_reasoning_step_share_p0_fallback` covers 1–5 and is used when the 6–10 release gate has not passed
- `03a` holds no balance number of its own
- `conditional_share(s, d, v) = global_share(v) / sum(global_share(x) for x in supported_values(s, d))`
- when a target does not name a share, use an equal share among the implemented values in that quota dimension

WRITE:

- (none)
