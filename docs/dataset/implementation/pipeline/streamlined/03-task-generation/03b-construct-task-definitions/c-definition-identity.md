# 03b/c definition identity — canonical form, hashes, persistence

> Authoritative: `../../../03-task-generation/03b-construct-task-definitions/c-definition-identity.md`
> Models: `../../models/03-task-generation.md`

## 1 — Canonical identity

TRANSFORM:

- canonical identity = `(program_sha256, target binding identity, canonical clue sequence, answer_meaning)`; for a scalar target the binding identity is the measurement name
- canonical clue sequence: dependency order first, then independent clues broad-to-narrow by narrowed-set size descending, tie-break by stable hash
- identical canonical identity → duplicate; keep one and record the duplicate
- prompt identity = `(program_sha256, target category, canonical clue sequence, answer_meaning, answer_format, choice_pool)`; keep one definition per identity; a group that disagrees on the gold answer is `prompt_ambiguous` and none is accepted (`DS-REQ-35`)
- `task_id = cadqatask:<sha256>` over the canonical task identity; the gold answer is not part of it
- answer format, choice pool, and prompt wording are not part of `task_id`; the harness answer instruction is not definition content

WRITE:

- (none)

## 2 — Canonical serialization

TRANSFORM:

- serialize one definition as canonical JSON: keys sorted by byte order, UTF-8, no byte-order mark, `,` and `:` with no surrounding space, no trailing newline, raw UTF-8 (no `\u` escapes), absent values as `null`, integers as JSON integers, every other number as canonical decimal text, UUIDs as lowercase hyphenated text, lists in recorded order
- reject a string containing U+2028 or U+2029
- `task_id` and `definition_sha256` are excluded from their own hash input
- the definition has no binary float fields
- `choice_pool` is hashed in construction order, labels included

WRITE:

- (none)

## 3 — The three hashes

TRANSFORM:

- `task_id` = canonical task identity; used for duplicate detection, the release key, and split isolation
- `definition_sha256` = canonical task content plus `program_sha256`, `graph_schema_version`, `runtime_extraction_sha256`, `constructor_version`, `definition_schema_version`, `construction_seed`; it excludes `plan_version`, `cadevolve_program_family_id`, `split`, and `subset`
- `definition_sha256` covers `state_scope`, `possible_answer_count`, `target_binding`, `task_clues`, `clue_reduction_form_profile`, `answer_meaning`, `answer_parameter`, `gold_answer`, `answer_unit`, `tolerance`, `scoring_rule`, `answer_evidence`, and `choice_pool`
- `answer_sha256` = `gold_answer`, `answer_unit`, `tolerance`, `scoring_rule`, `answer_schema_version`; for multiple choice it also covers the `candidate` of the entry whose label is `gold_answer`; it excludes `answer_evidence`
- `04` copies `answer_sha256`; it never recomputes it

WRITE:

- (none)

## 4 — Provenance and persistence

TRANSFORM:

- record `provenance`: `runtime_extraction_sha256, graph_identity_sha256, constructor_version, construction_seed, plan_version, balance_policy_version`
- rendering provenance — render seed, template version, and `prompts.yaml` hash — belongs to `04`, not to the definition
- extra accepted definitions become reserve, not release rows
- an underfilled target is a deficit for `03c`; do not loop inside `03b`

WRITE:

- `TaskDefinition` Parquet `(task_id)` → `definition_sha256, answer_sha256, program_id, program_sha256, cadevolve_program_family_id, split, subset, graph_schema_version, definition_schema_version, state_scope, possible_answer_count, target_category, target_binding, task_clues, clue_reduction_form_profile, answer_meaning, task_answer_step, answer_parameter, native_answer_format, answer_format, gold_answer, answer_unit, tolerance, scoring_rule, answer_schema_version, answer_evidence, choice_pool, task_clue_step_count, task_reasoning_step_count, geometry_required, validity_record, provenance`
- `DeficitLedger` `(plan_version, update sequence)` → accepted and rejected counts by quota target, family, step count, and rejection reason; a `DeficitClass` value (`probe_deficit`, `construction_deficit`) where known
- failure partition `03b_construct_task_definitions`
