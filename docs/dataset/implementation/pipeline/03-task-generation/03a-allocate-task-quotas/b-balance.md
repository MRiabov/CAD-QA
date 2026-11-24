# Balance policy

**Parent:** [`README.md`](README.md).

## Balance policy

Every tunable quota and balance number is data in `generator/config/balance.yaml`.
`03a` reads that file; `05` validate and export release reads the same file when
checking the release. Neither holds balance numbers of its own.

| Key | Sets |
|---|---|
| `release.tasks_min`, `release.programs_min` | The release size floors. |
| `release.distinct_answer_min` | The distinct-correct-answer floor; read by `05` in P1. |
| `release.splits` | The split shares. |
| `release.share_tolerance` | The absolute share a release may drift from `release.splits` and `task_reasoning_step_share`; read by `05`. |
| `release.built_shape_min_share` | The minimum share of tasks with a built shape. |
| `release.three_or_more_step_min_share` | The floor on the share of tasks that need three or more task reasoning steps; read by `05`. |
| `release.cad_model_max_share` | The per-CAD-model task cap. |
| `release.correct_answer_max_share` | The per-answer task cap; read by `05` in P1. |
| `task_reasoning_step_share` | The task reasoning step mix. |
| `task_reasoning_step_share_p0_fallback` | The 1–5 mix used when the 6–10 release gate has not passed. |
| `expansion.rounds`, `expansion.growth_share_per_round` | The `03c` resolve deficits stop rule. |
| `construction.attempt_multiplier`, `construction.high_rejection_attempt_multiplier` | The construction attempt budgets. |
| `dimensions.<dimension>.min`, `.max` | The release-level plan minimum and maximum for one value. |
| `dimensions.<dimension>.values.<value>` | A per-value override of `min`, `max`, or `target`. |
| `dimensions.<dimension>.target` | A global share; `equal` is an equal share among the supported values. |
| `dimensions.clue_operand_form.severe` | The P0 severe-imbalance multiples. |

Load rules:

- Every key is required except `min`, `max`, `target`, and `values`. A missing
  `min` means no plan minimum, a missing `max` means no cap, and a missing
  `target` means an equal share among the supported values.
- An unknown key is an error at every level. A typo must not fall back to a
  default.
- `task_reasoning_step_share` covers every task reasoning step count in the
  thesis release and sums to 1 within `1e-9`. `task_reasoning_step_share_p0_fallback`
  covers 1–5 and sums to 1; it is the policy used when the 6–10 release gate has not
  passed. `release.splits` does the same.
- Every share is in `(0, 1]`, and `min <= max` when both are present.
- `version` is a positive integer, bumped when any number changes.

The file carries no priority field. The `# p0` and `# p1` comments are for the
owner and are not data. Coverage and scope come from the support-table
derivation, which takes the requirement marks as input; this file only says how
much of a supported value to plan.

No test compares the file to the requirement defaults. A release may depart from
them deliberately, and the departure is visible in the version and hash that the
manifest records. The defaults are the starting point, not a second copy.

## Conditional share

`conditional_share(task_reasoning_step_count, quota_dimension, dimension_value)`
is the dimension value's global share divided by the sum of the global shares of
values supported at that task reasoning step count. The global quota share is the
quota share target for that dimension value. When the target does not name a
share, use an equal share among implemented values in that quota dimension.
