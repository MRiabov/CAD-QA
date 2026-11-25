# Missing contracts

**Status:** ephemeral audit backlog, 2026-11-20; reopened 2026-11-25. This is
not a source of truth. Each entry names an absent contract. When the contract is
written into its owner doc, delete the entry. Open questions remain in
[`open-questions.md`](open-questions.md).

The **Product** sections are the decisions only the owner can make; they are
collected as questions at the top. The **Technical** sections are contracts a
coding agent can close from the decisions already recorded.

Each technical section opens with a work order, most unblocking first. The order
is dependency order, not importance: an entry can start once its prerequisite
lands, and the tests run alongside the milestone they cover.

There are 2 open entries: two P0 technical contracts. P1 and P2 are empty. They
were scheduled as `P0-W1` items and none is written into its owner doc yet.
`MC-63` and `MC-66` closed on 2026-11-25; `MC-64` and `MC-65` remain.

## Decisions needed from the owner

None.

## P0

### Product (P0)

None. `MC-63` closed by re-scoping R-5 to P1; see
[`requirements/shortcut-resistance.md`](../requirements/shortcut-resistance.md).

### Technical (P0)

Work order:

1. `MC-65` — a rejection has no disposition; `02a`/`02b`/`02c` write rejection
   rows from `P0-W3` on.
2. `MC-64` — the absence and residual review frames; the review gate in `P0-W6`
   consumes them.

#### MC-65 — A rejection has no disposition

The [`failure-record.md`](failure-record.md) row carries no
`by_design | corpus_defect | extractor_gap` column, and the reason sets in
[`extraction/validation.md`](pipeline/extraction/validation.md) do not supply
one. `CompletenessDisposition` in
[`graph-completeness.md`](pipeline/extraction/graph-completeness.md) is the
nearest pattern, but it classifies a missing graph row on an accepted graph, not
a rejected program, so an extractor gap is still indistinguishable from a
corpus limitation.

**Recommendation:** add a typed `disposition` column to the failure record, and
make each rejecting stage's closed reason set name the disposition its reasons
carry. `by_design` is a rejection the contract intends at the declared scope;
`corpus_defect` is invalid CadQuery program or a runtime result the contract
excludes; `extractor_gap` is a supported construct the extractor failed to
capture. `05` counts by disposition during reconciliation, and the Go
`FailureRecord` struct and its merge test follow the column.

#### MC-64 — The review gate has no absence or residual frame

The ledger in [`devtools/review-pack.md`](devtools/review-pack.md) samples
release rows and is keyed `(task_id, definition_sha256, prompt_sha256)`, one
verdict per rendered task. There is no frame for "was each absent program or
capability legitimately absent", no uniform draw from the pinned pool at the
`3/p` size, and no ledger scoped to an upstream pipeline stage; `05` checks only
the sampling matrix. `rejection_contact_sheet.py` and `residual_sample.py` are
planned in [`file-trees.md`](file-trees.md#tools-and-manual-verification) and
write no ledger cell.

**Recommendation:** add two ledgers to `review-pack.md`. The absence ledger has
one row per absent program or capability, keyed by the upstream pipeline stage
and the subject identity, with a disposition and the evidence that supports it.
The residual ledger has one row per program drawn uniformly from the pinned
pool, with the sample size the `3/p` rule sets and the oracle-differential
result. `05`'s review gate requires the absence ledger to account for every
upstream stage deficit and the residual sample to meet its size, and the
manifest records both hashes.

## P1

### Product (P1)

None.

### Technical (P1)

None. `MC-22` closed in the 2026-11-25 geometry-required pass and `MC-49`
closed in the 2026-11-25 benchmark-program-set pass.

## Closed in the 2026-11-25 extraction-capability-coverage pass

- `MC-66` — the must-extract capability set is `MustExtractCapability` in
  [`extraction/validation.md`](pipeline/extraction/validation.md#the-must-extract-capability-set):
  the closed P0 set of entity, relation, and measurement cells, taken from the P0
  marks of the completeness tables and never from the census. A cell is covered
  when at least one accepted program's `GraphCompletenessReport` carries it with
  `actual_count > 0`, and the report row identity is the cell identity.
  `extraction_capability_coverage` is an enforced release-scope `set_equal` check
  in [`release-checks.yaml`](../../../generator/config/release-checks.yaml) over the declared set
  and the realized declared cells; a miss blocks the export
  ([`release-checks.md`](pipeline/05-validate-and-export-release/release-checks.md#extraction-capability-coverage)).
  The census and `capability_deficit` stay a quota-planning tool. The decision is
  `EX-24`, and the support-table derivation now says that
  `no_valid_construction` does not distinguish a grammar limit from a capability
  no fixture graph carries.

## Closed in the 2026-11-25 benchmark-program-set pass

- `MC-49` — the external benchmark program set is an artifact in
  [`artifacts.md`](artifacts.md), written by the release author and identified by
  benchmark name, revision, split, normalization version, and file hash. Its
  typed declaration is `ExternalBenchmarkProgramSet` in
  [`05` validate and export release](pipeline/streamlined/models/05-validate-and-export-release.md#externalbenchmarkprogramset-parquet).
  `05` validates it against the run manifest's `external_benchmark` and blocks
  the P0 exact-text overlap; the P1 same-CAD-model comparison is a graph-reading
  audit over the same set. The release manifest records the identity, revision,
  split, and hash as validation provenance excluded from `release_id`. The
  decision is `DS-ADR-16`.

## Closed in the 2026-11-25 shortcut-resistance pass

- `MC-63` — R-5 is re-scoped to P1 and measured by a `03b` quality gate, not a
  release check. `shortcut_resistance` resolves the answer dependency chain from
  the CAD graph, records the operation count and topology flag, and rejects a
  shape-required definition whose chain is below `dependency_operation_min` with
  no topology dependency. An unresolved chain is `unknown` and also rejects. The
  quality gate stores no chain, adds no `TaskDefinition` or release column, and does not
  build a symbolic CAD engine. The P0 release makes no R-5 claim; the Phase 2
  baseline measures the LLM-model consequence. `P1-W5` owns the implementation; the
  requirement is [`requirements/shortcut-resistance.md`](../requirements/shortcut-resistance.md)
  and the worked examples are
  [`requirements/views/shortcut-resistance.md`](../requirements/views/shortcut-resistance.md).

## Closed in the 2026-11-25 geometry-required pass

- `MC-22` — `geometry_required` is "at least one task reasoning step (a task
  clue step or the task answer step) depends on the built shape". The clue-only
  definition was false for a 0-clue 1-step task, contradicting the accepted
  `box-volume` and `box-membership-inside` records. `R-4` is restated the same
  way. `03b` derives the flag from `answer_meaning` and `clue_type`: an answer
  step reads the built shape for every meaning except `Identity` and
  `CadQuery workplane state`, and a clue step reads it for every clue type
  except `provenance`.
  `geometry_required_recorded` checks the stored flag against that derivation.
  The 95% floor is executable: `built_shape_share_floor` selects `value: true`,
  and the policy schema now defines `value` and `minimum_value`; the sibling
  `steps_three_or_more_share` selects `minimum_value: 3`. `box-volume` stays true
  under this dependency rule; shortcut resistance is R-5 and is measured by the
  baseline report, not by this field.

## Closed in the 2026-11-25 pair-emission pass

- `MC-50` — a reference is a set, and pair emission emits every member of a
  reference class up to one bound. `DS-REQ-37` states the rule:
  `graph-content.md` §4.1 splits pair kinds into sparse (every true pair, no
  reference restriction) and dense (each reference class within
  `max_anchor_class_size`), emits a class whole or not at all, and records the
  constant as a reference-vocabulary bound measured from the pool, provisionally
  8. `named entity` is retired in favour of **reference class**. `BindingRef`
  carries the set expression — category, the one condition the phrase names, the
  reduction form, the aggregation, and the state scope — and not a resolved
  entity, so a definition's identity does not depend on the graph's entities. The
  same pass marks `DS-ADR-04`'s graph size figures stale, requires dictionary
  encoding on the endpoint columns, fixes the pair-row sort order, and records
  the per-program assembly representation as `DS-ADR-14`.

## Closed in the 2026-11-21 run-contract pass

- `MC-29` — the run-level execution contract is
  [`run-contract.md`](run-contract.md). A run is one durable directory with a
  `run.json` manifest: `run_id`, generator and component versions, policy file
  hashes, and the run-level `TolerancePolicy`. New runs are allocated as
  `<runs_root>/run<NNNN>`; the number is local and excluded from `run_id`, and
  `generator list` reads the manifests in order. Each pipeline stage commits
  immutable Parquet parts as units complete; the part is the unit's completion
  marker, and resume reads the committed parts and skips completed units. Bulk
  state is Parquet; JSON is limited to the run manifest, pipeline stage
  completion markers, the deficit ledger, and other small or rare control
  documents. A unit is flushed when it completes, or at most every 30 seconds,
  asynchronously through one writer per pipeline stage. The contract also defines
  the shared cache, the run lock, the command-line interface, the exit codes, and
  partial-run cleanup. The run manifest and pipeline stage completion markers
  are rows in [`artifacts.md`](artifacts.md); the contract is its own document
  because it is larger than the artifact table, and `artifacts.md` keeps the
  ownership and format rows.

## Closed in the 2026-11-20 streamlined pass

- `MC-20` — `03a` allocate task quotas counts one program per `program_id`. When
  two selection rows share a `program_id`, the row with the lexicographically
  smallest `source_id` is used and its family is the program's family; the other
  row is excluded from the plan and the conflict is recorded. `01b` still keeps
  both rows for collection accounting, and one `program_id` now produces one
  family and one set of `task_id` values.
- `MC-18` — the post-execution program floor is data. `03a` records a
  `capacity_deficit` with detail `program_floor_short` when
  `usable_program_count` is below `policy.usable_floor`; `03c` promotes reserve
  programs through the slow loop, and an exhausted reserve records an
  `AcceptedMiss` that the `programs_min` check turns into a blocked export.

## Closed or merged in the 2026-11-20 pass

- `MC-41` — the construction test contract is
  `pipeline/testing/03-task-generation/03b-construct-task-definitions/README.md`: a definition tier that re-evaluates
  every validity rule the definition decides, a graph tier for pair emission,
  point probes, and the clear-case margin, and an end-to-end tier that constructs
  the golden record and compares its counts against the graph. `03b` now names
  every validity rule and owns its failure reason set, so a skipped rule is a
  visible defect rather than an absent check. Rejection fixtures are kept apart
  from coverage fixtures, so a degenerate program cannot make a support-table
  cell look supported.
- `MC-15` — multiple choice is checked against a named list of nine P0 rules and
  one P2 rule. `choice_pool` is typed and labeled at construction, so a label is
  a position and `gold_answer` is a label before the definition is hashed. The
  release table carries a `choices` column of label and answer value, so `05`
  rechecks the pool without parsing the prompt, and a label counts by the answer
  value it denotes. It absorbs `MC-24`.
- `MC-42` — the golden record is a versioned JSON file per task, defined in
  `pipeline/testing/golden/README.md` with the program, construction input,
  task description, canonical clue sequence, answer, and evidence. The first
  record is `pipeline/testing/golden/box-with-hole.json`; the `03b` Go test
  validates the format (`missing` until the constructor lands). The box-with-hole
  chain is three steps, not the plan's four: the BRep seam edge changes the
  counts, and the plan's comparison is redundant.
- `MC-11` — `04` takes `NormalizedProgram` and `RenderConfig` (the validated
  `PromptTemplateSet` plus the release `RenderSeed`). The task render seed is
  derived from the release seed and `task_id`, and the manifest records the
  release seed with the template version and file hash.
- `MC-26` — release contract section 7 is a field table with `release_id`,
  `generator_version`, `upstream_dataset_version`, the external-manifest hash,
  and the benchmark identity fields; `release_id` is `cadqarel:<sha256>` over the
  release inputs, with `release_table_sha256` kept separately for byte integrity.
  Section 8 is the dataset card
  outline, including the answer conventions. `05` owns both and writes the card
  from the manifest. The benchmark program set the fields name is `MC-49`.
- `MC-12` — `04` render prompt and choices owns the projection, and the release
  contract carries one `Carries` row per column. Answer text is copied, never
  re-serialized; `clue_types` comes from `clue_reduction_form_profile`;
  `prompt_sha256` is over the `prompt` UTF-8 bytes; `answer_sha256` is copied and
  not recomputed. `answer_schema_version` is now a `TaskDefinition` field, which
  `answer_sha256` already hashed.
- `MC-25` — `prompts.yaml` and its schema are written in `prompt-templates.md`;
  the Go `04` loader test validates the file (`missing` until `04` lands, and
  there is no Python prompt-template contract). The file carries template
  IDs, typed placeholders, label tables, and dataset and evaluation namespaces;
  `04` rejects a missing, extra, or untyped placeholder.
- `MC-13` — `05-validate-and-export-release/release-checks.md` lists one check
  per requirement statement, with its scope, bound, and first-release
  disposition.
  A miss blocks export until the owner accepts it into `known_misses`; a bound
  that coverage makes impossible is `superseded` rather than a miss. The
  conditional release share is one implementation, called by `03a` and `05`.
- `MC-38` — the release table carries `clue_reduction_form_profile`, and
  `support/` carries five tables including `clue-reduction-form-by-step.json`.
  `04` copies it from the definition, and `05` reads it for clue reduction form
  coverage.
- `MC-46` — dissolved. The census is a typed function of the graph, not an
  artifact: `03a` derives it and stores the union per family in
  `family_profiles`, `03b` derives it per program, and `03c` reads the plan.
  `TG-9` supersedes the sentence in `TG-6` that says `02c` emits the census.
- `MC-44` — feasibility is the constructor's output over a committed coverage
  fixture set, not an abstraction of the grammar. The contract is written in
  `task-step-support.md`, and the structural and witness tiers are in
  `pipeline/testing/00-support-tables.md`. Fixtures are programs, so no Parquet
  enters the repository. The fixture programs and `support-table.json` are
  implementation artifacts and do not exist yet.
- `MC-14` — `failure-record.md` owns the row schema, the dedupe key, the merge,
  the order, the reconciliation rule, and the aggregation. The record is one
  partition per rejecting pipeline stage, merged by `05`.
- `MC-40` — `DeficitClass` is a closed set of seven classes in `03c` resolve
  deficits, `03a` records the allocation detail instead of a class, and the
  census decides between a capability and a capacity deficit. A probe deficit
  stays local to its state; a pair that is not emitted is not a class.
- `MC-37` — the definition fields are written: `state_scope`,
  `clue_reduction_form_profile`, `answer_parameter`, and `geometry_required` are
  fields; `answer_evidence` carries `answer_equivalent_set` and `point_probe`;
  `validity_record` is typed.
- `MC-09` — canonical JSON, three hash inputs, and the provenance block are
  written in `03b`, with `TG-3` recording why assignment is excluded from
  `definition_sha256`.
- `MC-16` — dissolved. The implementation-scope filter is the support-table
  derivation: it takes `implementation_scope` from the requirement marks, so a
  value above the release scope has no row and is neither planned nor accepted.
  `03a` calls the same derivation, and `05` reads the persisted tables. No
  separate scope file or filter exists.
- `MC-48` — resolved in favour of the derivation. `03a` does not read the
  tables as data; it calls the derivation that writes them, and `TG-4` now says
  so. The plan and the QA projection cannot disagree.
- `MC-31` — the slow loop in `03c` resolve deficits includes `01d` normalize
  programs; the flow line in `00` end to end was the defect and is fixed.
- `MC-17` — reserve rows are fetched but not normalized or graphed; promotion is
  the slow loop, in `01c`, `01d`, and `03c`.
- `MC-23` — the stop rule is three rounds with a 20% growth cap and an
  `AcceptedMiss`, in `03c`.
- `MC-45` — the P1 balance row is an equal share among supported forms, in
  `task-structure.md`.
- `MC-27` — the benchmark is pinned in the manifest, in `05`, and the transfer
  comparison is PRD Q7. The entry's Q1 reference was a misnumbering; no Q1 was
  retired.
- `MC-28` — the owner reviews a P0 sample behind a blocking gate, in `05`.
- `MC-47` — a scalar target is defined as a measurement instance but is deferred;
  a measurement of an entity records the entity as the target, in
  `task-structure.md` and `03b`.
- `MC-35` — the relation row now carries `tolerance` and CAD graph evidence,
  both excluded from `relation_id`, in `graph-persistence.md`.
- `MC-43` — the named-endpoint derivation, the pair rows, and the state-size
  rejection are written in `graph-construction.md`.
- `MC-08` — the resolver table is written in `03b` construct task definitions,
  with the angle, position, material-change, and topology-change conventions.
  The dataset card now has to state them for consumers.
- `MC-39` — clue reduction form is coverage-only in P0, with one clue occurrence
  per supported form per step count and no share; `03a` allocate task quotas now
  says so.
- `MC-36` — the state entity limit is a scope constant measured once per
  implementation scope, and the rule is written in `graph-content.md` section
  4.1. The first number is produced when the P0 pool is selected, which is plan
  work rather than a missing contract.
- `MC-32` — the external manifest has no link field; the repo-wide link check
  passes.
- `MC-34` — the implementation README now lists the test contract folder and the
  streamlined folder.
- `MC-19` — merged into `MC-18`; both named the same backfill path.
- `MC-24` — merged into `MC-15`; both named multiple-choice fairness.
- `MC-10` — merged into `MC-09`; identity and provenance are one reproducibility
  contract.
