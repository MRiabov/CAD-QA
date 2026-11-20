# 03b construct task definitions — answer-bearing records

> Authoritative: `../03-task-generation/03b-construct-task-definitions.md`

READ:
- `CadGraph` from `02c`
- `TaskQuotaPlan` from `03a` → `quota_targets`, `construction_attempt_budgets`, `family_assignment`
- `DeficitLedger` on resume; empty on the first run

## 1 — Construct definitions

TRANSFORM:
- sample typed constructors from graph facts into each quota target; deterministic for the graph, plan version, definition-schema version, and seed; constructor order is fixed by `constructor_version`
- bind the target directly when the category has exactly one instance, otherwise by the ordered clues; the binding resolves to exactly one entity or one measurement instance
- build each clue as one typed predicate: `clue_id, order, clue_type, subject, check, result`; clue types are `property, relation, comparison, aggregation, provenance`
- a clue with a reference binding other than the task target carries `clue_operand_form`: `named, selected, aggregated, or cross_state`; a clue with no reference has no form
- a list item that states two conditions is two clues; a property clue that refers to another entity is two clues
- every clue narrows the possible answers: `after < before`; a clue that does not narrow rejects the definition
- derive `clue_operand_form_profile` as the ordered `(clue_type, clue_operand_form)` pair for every clue; never author it separately
- every target, clue operand, answer value, and answer evidence resolves to a graph entity, relation, or measurement; a missing element rejects the definition
- choose the answer step and native format from `answer_meaning`; identity → multiple choice; volume, area, length, distance, angle → number; count, rank → integer; membership, validity → yes or no; position → 3D coordinate; extent → bounding box; CadQuery workplane state → structured object; material change → number or integer; topology change → integer
- multiple choice draws real options from the penultimate answer candidate set; identity draws entity options, a numeric answer draws distinct answers; fewer than five real choices rejects the task
- `task_clue_step_count` = number of clues; `task_reasoning_step_count = task_clue_step_count + 1` when an answer step exists, otherwise `task_clue_step_count`; the minimum is 1
- construct one batch per plan revision from `construction_attempt_budgets`; accepted definitions are capped at the target; do not top up a target inside the revision

WRITE:
- (none)

## 2 — Resolve the answer

TRANSFORM:
- `resolve_answer(answer_meaning, bound_target, answer_parameter, penultimate_set)` → `gold_answer, answer_evidence`
- identity → the entity shared by the whole answer-equivalent set; evidence = the set and the binding
- volume → kernel volume of the bound solid state; area → kernel area of the bound face or profile; length → kernel length of the bound edge or path segment; distance → shortest kernel distance between the bound pair, or between the point and the entity; evidence = the kernel measurement
- angle → the graph angle for the pair; evidence = the graph measurement
- count → the size of the bound set
- membership → `is_inside(solid_state, point)` from the point probe; answer is inside or outside; a point within the clear-case margin is not used; evidence = the point, its classification, the solid state, and the classifier
- position → the declared point (face centroid, edge midpoint, vertex point, or state centroid)
- extent → minimum and maximum corner of the bounding box in the program frame
- material change → the signed volume or count the bound operation adds or removes; a cut answers a negative number
- topology change → the signed change in the declared category
- `answer_parameter` is null unless the meaning declares a point (position, membership) or a category (topology change); material change declares no parameter
- `same_answer`: count and rank exact integers; number, coordinate, and bounding box at canonical rounding, 4 significant figures by default; membership and validity label exact; structured object componentwise
- evidence is `evidence_kind (measured | derived), evidence_rule, evidence_refs, answer_equivalent_set, point_probe`; `answer_equivalent_set` holds one entry per remaining candidate, and every entry equals the gold answer under `same_answer`
- a missing target or a missing graph measurement rejects the task; never guess or approximate

WRITE:
- (none)

## 3 — Validate and identify

TRANSFORM:
- valid only when every clue is satisfied and narrows, every clue is necessary (removing it leaves at least two distinct answers or changes the answer), every predicate clears the clear-case margin, every candidate in the answer-equivalent set produces the same answer, a scalar target has one value across remaining instances, the answer step produces one gold answer, the binding is unambiguous, the family and split are present, the split matches `03a`, the subset matches the step count, the answer has evidence, multiple choice has at least five real choices, and `geometry_required` is recorded
- invalid → failure row with a reason; the definition does not consume quota and does not reach `04`
- canonical identity = `(program_sha256, target binding identity, canonical clue sequence, answer_meaning)`; for a scalar target the binding identity is the measurement name
- canonical clue sequence: dependency order first, then independent clues broad-to-narrow by narrowed-set size descending, tie-break by stable hash
- identical canonical identity → duplicate; keep one and record the duplicate
- `task_id = cadqatask:<sha256>` over the canonical task identity; the gold answer is not part of it

WRITE:
- (none)

## 4 — Serialize and persist

TRANSFORM:
- serialize one definition as canonical JSON: keys sorted by byte order, UTF-8, no byte-order mark, `,` and `:` with no surrounding space, no trailing newline, raw UTF-8 (no `\u` escapes), absent values as `null`, integers as JSON integers, every other number as canonical decimal text, UUIDs as lowercase hyphenated text, lists in recorded order
- reject a string containing U+2028 or U+2029
- `task_id` and `definition_sha256` are excluded from their own hash input
- `task_id` = canonical task identity; used for duplicate detection, the release key, and split isolation
- `definition_sha256` = canonical task content plus `program_sha256`, `graph_schema_version`, `runtime_extraction_sha256`, `constructor_version`, `definition_schema_version`, `construction_seed`; it excludes `plan_version`, `cadevolve_program_family_id`, `split`, and `subset`
- `answer_sha256` = `gold_answer`, `answer_unit`, `tolerance`, `scoring_rule`, `answer_schema_version`; it excludes `answer_evidence`
- the definition has no binary float fields
- record `provenance`: `runtime_extraction_sha256, constructor_version, construction_seed, plan_version, balance_policy_version`
- extra accepted definitions become reserve, not release rows
- an underfilled target is a deficit for `03c`; do not loop inside `03b`

WRITE:
- `TaskDefinition` Parquet `(task_id)` → `definition_sha256, answer_sha256, program_id, program_sha256, cadevolve_program_family_id, split, subset, graph_schema_version, definition_schema_version, state_scope, target_category, target_binding, task_clues, clue_operand_form_profile, answer_meaning, task_answer_step, answer_parameter, native_answer_format, answer_format, gold_answer, answer_unit, tolerance, scoring_rule, answer_schema_version, answer_evidence, choice_pool, task_clue_step_count, task_reasoning_step_count, geometry_required, validity_record, provenance`
- `DeficitLedger` `(plan_version, update sequence)` → accepted and rejected counts by quota target, family, step count, and rejection reason; `probe_deficit` and `construction_deficit` where known
- failure partition `03b_construct_task_definitions`
