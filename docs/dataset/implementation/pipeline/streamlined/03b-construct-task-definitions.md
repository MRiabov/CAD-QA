# 03b construct task definitions — answer-bearing records

> Authoritative: `../03-task-generation/03b-construct-task-definitions.md`

READ:

- `CadGraph` from `02c`
- `TaskQuotaPlan` from `03a` → `quota_targets`, `construction_attempt_budgets`, `family_assignment`
- the program capability census, derived here from the graph: target categories, clue constructors, clue operand forms per clue type, measurements, answer meanings, and point probes
- `DeficitLedger` on resume; empty on the first run

## 1 — Construct definitions

TRANSFORM:

- for one quota target, `possible_answers` = all entities of the target category in `state_scope`; `state_scope = final` in P0; for a scalar target, the candidates are `(subject, value)` measurement instances of the declared measurement
- `facts(candidate)` = the true facts of the graph, each with the candidate set it selects; a fact exists only when the graph asserts it and its measurement is present, so an unsupported predicate is never attempted
- for each candidate as witness, `wrong` = the candidates whose answer differs under `same_answer`; `chain = cover(wrong, facts(witness), target_step_count = task_reasoning_step_count - task_answer_step)`; a bounded set-cover search, never an enumeration
- order the chain by dependency first, then narrowed-set size descending, tie-break by stable hash; this canonical order is identity-bearing and validity is checked against it
- no cover at the target step count writes one `no_cover` failure row and leaves the target as a deficit for `03a`/`03c`; never accept a longer or shorter task
- construction is deterministic for the graph, plan version, definition-schema version, and seed; candidate order, fact order, tie-breaks, and the cover search are fixed by `constructor_version`
- skip a clue operand form the census does not support before any construction attempt
- bind the target directly when the category has exactly one instance, otherwise by the ordered clues; the binding resolves to exactly one entity or one measurement instance
- build each clue as one typed predicate: `clue_id, order, clue_type, subject, check, result`; clue types are `property, relation, comparison, aggregation, provenance`
- check fields by clue type: property `measurement, comparator, threshold | range`; relation `relation_type, direction, object`; comparison `measurement, comparator, reference`; aggregation `scope, aggregation_kind, measurement, rank | extreme`; provenance `operation_id | profile_id | workplane_id`
- a clue with a reference binding other than the task target carries `clue_operand_form`: `named, selected, aggregated, or cross_state`; a clue with no reference has no form
- no task uses these combinations: property with any operand form; aggregation with `aggregated`; `selected` at step count 1; `cross_state` in P0 and P1
- a list item that states two conditions is two clues; a property clue that refers to another entity is two clues
- every clue narrows the possible answers: `after < before`; a clue that does not narrow rejects the definition
- derive `clue_operand_form_profile` as the ordered `(clue_type, clue_operand_form)` pair for every clue; never author it separately
- every target, clue operand, answer value, and answer evidence resolves to a graph entity, relation, or measurement; a missing element rejects the definition
- choose the answer step and native format from `answer_meaning`; identity → multiple choice; volume, area, length, distance, angle → number; count, rank → integer; membership, validity → yes or no; position → 3D coordinate; extent → bounding box; CadQuery workplane state → structured object; material change → number or integer; topology change → integer
- multiple choice is a presentation wrapper valid for every answer meaning; `native_answer_format` records the meaning's format and `answer_format` records the requested wrapper; the plan's `answer_format` target selects the wrapper, and a format that cannot express the meaning is not used
- multiple choice: the pool has 5-7 entries, ordered by a stable hash of `(task_id, candidate)` and labelled `A` to `G` in that order; each entry is `label, candidate, distinguishing_facts, error_mode`; every candidate comes from the penultimate answer candidate set and no two are equal under `same_answer`; identity uses entities, a numeric answer uses distinct answers; `gold_answer` is the label, and the answer value is the entry's `candidate`
- `choice_pool_valid` holds when the pool has 5-7 entries; `gold_answer` is one of the labels; every `candidate` is valid under `answer_format`; no two candidates are equal under `same_answer`; every candidate comes from the penultimate answer candidate set; every `distinguishing_facts` is a geometric or construction fact, unique across entries, and contains no variable name, internal identifier, or answer value; labels are contiguous from `A` with no repeat
- `possible_answer_count` = the size of `possible_answers` for the target category and `state_scope`, before any clue narrows it
- `task_clue_step_count` = number of clues; `task_reasoning_step_count = task_clue_step_count + 1` when an answer step exists, otherwise `task_clue_step_count`; the minimum is 1
- `subset = warmup` when `task_reasoning_step_count = 1`, else `main`; `subset_matches_step_count` rechecks it
- fill targets in the plan's priority order (coverage, then balance, then volume); within a tier, scarcest first, where scarcity is the number of active programs whose graph supports the target; accept a definition only when it fills an unfilled target and pushes no cell past its maximum; record an acceptance that would overfill
- construct one batch per plan revision from `construction_attempt_budgets`; accepted definitions are capped at the target; do not top up a target inside the revision

WRITE:

- (none)

## 2 — Resolve the answer

TRANSFORM:

- `resolve_answer(answer_meaning, bound_target, answer_parameter, penultimate_set)` → `answer_value, answer_evidence`
- identity → the entity shared by the whole answer-equivalent set; evidence = the set and the binding
- volume → kernel volume of the bound solid state; area → kernel area of the bound face or profile; length → kernel length of the bound edge or path segment; distance → shortest kernel distance between the bound pair, or between the point and the entity; evidence = the kernel measurement
- angle → the graph angle for the pair; evidence = the graph measurement
- count → the size of the bound set
- membership → `is_inside(solid_state, point)` from the point probe; answer is inside or outside; a point within the clear-case margin is not used; evidence = the point, its classification, the solid state, and the classifier; `answer_parameter` is that same probe point, bound once, and `04` renders the question from it
- material change → the signed volume or count the bound operation adds or removes; a cut answers a negative number; `answer_parameter` is null
- position → the declared point (face centroid, edge midpoint, vertex point, or state centroid)
- extent → minimum and maximum corner of the bounding box in the program frame
- topology change → the signed change in the declared category
- when the task is multiple choice, `gold_answer` is the pool label whose `candidate` equals `answer_value`; the answer value stays in `answer_evidence` and `choice_pool`
- `answer_parameter` is null unless the meaning declares a point (position, membership) or a category (topology change); material change declares no parameter
- `same_answer`: identity is the same entity; count and rank exact integers; number, coordinate, and bounding box at canonical rounding, 4 significant figures by default; membership and validity label exact; material change the same added and removed volume at the stated precision; topology change the same face, edge, and vertex counts and the same changed set; structured object componentwise
- evidence is `evidence_kind (measured | derived), evidence_rule, evidence_refs, answer_equivalent_set, point_probe`; `answer_equivalent_set` holds one entry per remaining candidate as `{subject, answer}`, and every entry equals the answer value under `same_answer`
- an entry's `subject` is a graph entity for an entity target and the measurement name for a scalar target; `04` renders the question and `05` the review pack from it
- a missing target or a missing graph measurement rejects the task; never guess or approximate

WRITE:

- (none)

## 3 — Validate and identify

TRANSFORM:

- valid only when these named checks pass: `clue_satisfied, clue_narrows, clue_necessary` (removing any clue leaves at least two distinct answers or changes the answer), `predicate_margin, answer_equivalence` (every candidate agrees under `same_answer`; identity is a singleton), `scalar_target_agrees` (every remaining instance has the same value), `single_gold_answer, target_binding_unambiguous, family_and_split_present, split_matches_assignment, subset_matches_step_count, answer_evidence_present, choice_pool_valid, geometry_required_recorded, definition_unique`; P2 adds `near_miss_valid`
- `geometry_required` is recorded as its own field, not a checks entry
- `validity_record` = `checks` (one entry per named check: name, outcome, detail), `answer_equivalent_size` (entries in `answer_equivalent_set`), and `same_answer_holds` (whether every entry's answer equals the answer value)
- an accepted definition's `validity_record.checks` carries every named check except `geometry_required_recorded`, each with outcome `pass`; a missing check is a defect
- an invalid definition writes a failure row naming the failed check, or `no_cover` when the cover search found no chain; the definition does not consume quota and does not reach `04`
- a state without a surviving probe is a `probe_deficit` in the deficit ledger, not a failure row
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
- `answer_sha256` = `gold_answer`, `answer_unit`, `tolerance`, `scoring_rule`, `answer_schema_version`; for multiple choice it also covers the `candidate` of the entry whose label is `gold_answer`; it excludes `answer_evidence`
- `choice_pool` is hashed in construction order, labels included; `04` renders that order and never writes a new one back
- the definition has no binary float fields
- record `provenance`: `runtime_extraction_sha256, constructor_version, construction_seed, plan_version, balance_policy_version`
- extra accepted definitions become reserve, not release rows
- an underfilled target is a deficit for `03c`; do not loop inside `03b`

WRITE:

- `TaskDefinition` Parquet `(task_id)` → `definition_sha256, answer_sha256, program_id, program_sha256, cadevolve_program_family_id, split, subset, graph_schema_version, definition_schema_version, state_scope, possible_answer_count, target_category, target_binding, task_clues, clue_operand_form_profile, answer_meaning, task_answer_step, answer_parameter, native_answer_format, answer_format, gold_answer, answer_unit, tolerance, scoring_rule, answer_schema_version, answer_evidence, choice_pool, task_clue_step_count, task_reasoning_step_count, geometry_required, validity_record, provenance`
- `choice_pool` is empty for every non-multiple-choice task
- `DeficitLedger` `(plan_version, update sequence)` → accepted and rejected counts by quota target, family, step count, and rejection reason; `probe_deficit` and `construction_deficit` where known
- failure partition `03b_construct_task_definitions`
