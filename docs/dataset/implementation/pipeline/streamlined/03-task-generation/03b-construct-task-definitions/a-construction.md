# 03b/a construction — binding, clues, validity, sampling

> Authoritative: `../../../03-task-generation/03b-construct-task-definitions/a-construction.md`
> Models: `../../models/03-task-generation.md`

## 1 — Possible answers, facts, and the cover

READ:

- `CadGraph` from `02c` → nodes, relations, measurements, point probes
- one `QuotaTarget` from `TaskQuotaPlan` → `task_reasoning_step_count`, `quota_dimension`, `dimension_value`, `minimum`, `quota_target_count`, `maximum`, `priority`
- `ProgramCapabilityCensus` from `TaskQuotaPlan.program_census` for the program

TRANSFORM:

- for one quota target, `possible_answers` = all entities of the target category in `state_scope`; `state_scope = final` in P0; for a scalar target, the candidates are `(subject, value)` measurement instances of the declared measurement
- `facts(candidate)` = the true facts of the graph, each with the candidate set it selects; a fact exists only when the graph asserts it and its measurement is present, so an unsupported predicate is never attempted
- for each candidate as witness, `wrong` = the candidates whose answer differs under `same_answer`; `chain = cover(wrong, facts(witness), target_step_count = task_reasoning_step_count - task_answer_step)`; a bounded set-cover search, never an enumeration
- order the chain by dependency first, then narrowed-set size descending, tie-break by stable hash; this canonical order is identity-bearing and validity is checked against it
- no cover at the target step count writes one `no_cover` failure row and leaves the target as a deficit for `03a`/`03c`; never accept a longer or shorter task
- construction is deterministic for the graph, plan version, definition-schema version, and seed; candidate order, fact order, tie-breaks, and the cover search are fixed by `constructor_version`
- skip a clue operand form the census does not support before any construction attempt
- the search is bounded by `max_construction_candidates`, `max_construction_facts`, `max_cover_expansions`, and `max_validity_rechecks`; exhausting a budget records `construction_deficit` with detail `construction_budget`, not a failure row
- every limit is a count; no wall-clock deadline

WRITE:

- (none)

## 2 — Target binding and clue schema

TRANSFORM:

- bind the target directly when the category has exactly one instance, otherwise by the ordered clues; the binding resolves to exactly one entity or one measurement instance
- a scalar target binds a measurement instance: subject, measurement, value; the subject need not be unique
- build each clue as one typed predicate: `clue_id, order, clue_type, subject, check, result`; clue types are `property, relation, comparison, aggregation, provenance`
- check fields by clue type: property `measurement, comparator, threshold | range`; relation `relation_type, direction, object`; comparison `measurement, comparator, reference`; aggregation `scope, aggregation_kind, measurement, rank | extreme`; provenance `operation_id | profile_id | workplane_id`
- a clue with a reference binding other than the task target carries `clue_operand_form`: `named, selected, aggregated, or cross_state`; a clue with no reference has no form
- no task uses these combinations: property with any operand form; aggregation with `aggregated`; `selected` at step count 1; `cross_state` in P0 and P1
- a list item that states two conditions is two clues; a property clue that refers to another entity is two clues
- every clue narrows the possible answers: `after < before`; a clue that does not narrow rejects the definition
- derive `clue_operand_form_profile` as the ordered `(clue_type, clue_operand_form)` pair for every clue; never author it separately
- every target, clue operand, answer value, and answer evidence resolves to a graph entity, relation, or measurement; a missing element rejects the definition
- `possible_answer_count` = the size of `possible_answers` for the target category and `state_scope`, before any clue narrows it
- `task_clue_step_count` = number of clues; `task_reasoning_step_count = task_clue_step_count + 1` when an answer step exists, otherwise `task_clue_step_count`; the minimum is 1
- `subset = warmup` when `task_reasoning_step_count = 1`, else `main`; `subset_matches_step_count` rechecks it

WRITE:

- (none)

## 3 — Validity gates

TRANSFORM:

- valid only when these named checks pass: `clue_satisfied, clue_narrows, clue_necessary` (removing any clue leaves at least two distinct answers or changes the answer), `predicate_margin, answer_equivalence` (every candidate agrees under `same_answer`; identity is a singleton), `scalar_target_agrees` (every remaining instance has the same value), `single_gold_answer, target_binding_unambiguous, family_and_split_present, split_matches_assignment, subset_matches_step_count, answer_evidence_present, choice_pool_valid, geometry_required_recorded, definition_unique`; P2 adds `near_miss_valid`
- `geometry_required` is recorded as its own field, not a checks entry
- `validity_record` = `checks` (one entry per named check: name, outcome, detail), `answer_equivalent_size` (entries in `answer_equivalent_set`), and `same_answer_holds` (whether every entry's answer equals the answer value)
- an accepted definition's `validity_record.checks` carries every named check except `geometry_required_recorded`, each with outcome `pass`; a missing check is a defect
- an invalid definition writes a failure row naming the failed check, or `no_cover` when the cover search found no chain; the definition does not consume quota and does not reach `04`
- a state without a surviving probe is a `probe_deficit` in the deficit ledger, not a failure row
- the failure reason set is closed: a check name from this section, `no_cover`, or `internal`

WRITE:

- (none)

## 4 — Sample into the plan

TRANSFORM:

- fill targets in the plan's priority order (coverage, then balance, then volume); within a tier, scarcest first, where scarcity is the number of active programs whose graph supports the target
- accept a definition only when it fills an unfilled target and pushes no cell past its maximum; record an acceptance that would overfill
- construct one batch per plan revision from `construction_attempt_budgets`; accepted definitions are capped at the target; do not top up a target inside the revision
- a batch is one program pass at one task reasoning step count: the graph and census are loaded once and every target assigned to the program at that step count is filled from the same pass
- on resume, reconcile accepted counts from the committed `TaskDefinition` parts, then construct only the remaining target count
- a `task_id` already present in the parts or the failure partition is skipped when its `definition_sha256` agrees; a disagreement is an integrity error
- extra accepted definitions become reserve; they are not release rows
- an underfilled target is a deficit for `03c`; do not loop inside `03b`

WRITE:

- (none)
