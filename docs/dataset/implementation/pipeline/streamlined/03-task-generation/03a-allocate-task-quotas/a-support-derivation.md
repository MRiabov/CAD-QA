# 03a/a support derivation — census, profiles, supported values

> Authoritative: `../../../03-task-generation/03a-allocate-task-quotas/a-support-derivation.md`
> Census: `../../../03-task-generation/algorithm/program-capability-census.md`
> Support tables: `../../../../task-step-support.md`
> Models: `../../models/03-task-generation.md`

## Derive — census and supported values

READ:

- `CadGraph` per active program from `02c` → `cadquery_program` attributes `program_sha256`, `graph_identity_sha256`, plus nodes, relations, measurements, point probes
- `ProgramMetadata` from `01a` → `source_id`, `source_collection`, `path_family`, `source_feature_tags`
- `ProgramSelection` from `01b` → `rows[].tier`, `rows[].cadevolve_program_family_id`, `SelectionPolicy`
- `implementation_scope` → the release scope the support derivation filters by

TRANSFORM:

- derive the program capability census from each active graph: available target categories, clue constructors, clue reduction forms, measurements, answer meanings, point probes, `max_task_reasoning_step_count`, and `entity_counts`
- store the per-program census in `TaskQuotaPlan.program_census`, keyed by `program_sha256` and `graph_identity_sha256`
- store per family the union of member capabilities, summed entity counts, `states_with_point_probe`, `max_task_reasoning_step_count`, split status, `family_task_capacity`, and `family_probe_success_rate`
- a fast-loop replan reuses `family_profiles` and `program_census`; a slow-loop round derives the census only for the added programs
- `03b` reads the program's `program_census` entry; it re-derives only when the entry is absent or its `graph_identity_sha256` differs
- `03c` reads `family_profiles`, never `program_census`
- `supported_values(s, d)` is the support-table derivation's output, filtered by `implementation_scope`; `03a` calls the derivation in-process and does not read the support tables as data
- a value above the release scope has no supported row
- an in-scope value keeps its row even when no accepted graph realizes its capability; the census and `family_profiles` record what the graphs offer and are not the release gate for the missing capability
- a capability is present only when the graph asserts the relation or measurement and its evidence is present
- pair elements exist only for the pairs the pair emission rule allows

WRITE:

- (none; the census and profiles are fields of `TaskQuotaPlan`)
