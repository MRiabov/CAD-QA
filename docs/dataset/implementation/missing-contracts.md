# Missing contracts

**Status:** ephemeral audit backlog, 2026-11-20. This is not a source of truth.
Each entry names an absent contract. When the contract is written into its owner
doc, delete the entry. Open questions remain in
[`open-questions.md`](open-questions.md).

The **Product** sections are the decisions only the owner can make; they are
collected as questions at the top. The **Technical** sections are contracts a
coding agent can close from the decisions already recorded.

Each technical section opens with a work order, most unblocking first. The order
is dependency order, not importance: an entry can start once its prerequisite
lands, and the tests run alongside the milestone they cover.

There are 8 open entries: 4 P0 technical and 4 P1 technical. No product
decision remains open, and P2 is empty.

## Decisions needed from the owner

None. Every open entry is a technical contract.

## P0

### Product (P0)

None.

### Technical (P0)

Work order:

1. `MC-11` — the rendering inputs; a prompt cannot be reproduced from the
   declared input without them.
2. `MC-15` — multiple-choice fairness; the choice check.
3. `MC-41` — the construction test contract; it locks the invariants the other
   entries introduce.
4. `MC-42` — the golden record; the first end-to-end comparison.

#### MC-11 — Rendering inputs

The `04` render prompt and choices input contract omits program text, render
seed, and template version. `04` render prompt and choices depends on them, but
`io-contracts.md` names only `TaskDefinition` and `PromptTemplateSet`, so
rendering cannot reproduce a prompt from the declared input alone.
`TaskDefinition` carries `program_id` and `program_sha256`, not the program text.

**Recommendation:** add the program text (or a `NormalizedProgram` reference),
the render seed, and the prompt template version to the `04` render prompt and
choices row of `io-contracts.md`; `04` render prompt and choices already owns
the rendering contract for `prompts.yaml`.

#### MC-15 — Multiple-choice fairness checks

P0 multiple-choice fairness checks are missing: the correct choice is present,
choices are distinct in the answer space, unit, frame, and precision match,
descriptions do not leak the answer, and labels are deterministic. A choice pool
of five entries can still be invalid. It absorbs `MC-24`.

**Recommendation:** write one check list in `03b` construct task definitions
when a task is built, and reuse it in `05` validate and export release when the
release is checked; pool size is necessary but not sufficient. Define the typed
`choice_pool` entry (candidate, distinguishing facts, and P2 error mode) at the
same time.

#### MC-41 — Construction test contract

The test contract for the construction invariants is missing: pair-emission
completeness, `is_inside` reproducibility from a probe, clear-case margin
rejection, and redundant-clue rejection. The invariants are written, but
`pipeline/testing/README.md` is a stub and nothing verifies them, so a
regression is invisible.

**Recommendation:** one test per invariant, plus a property test that every
accepted definition passes the validity list, plus one end-to-end test on the
golden record (after `MC-42` fixes its format).

#### MC-42 — Golden record format

The golden-record file format is not defined for the box-with-hole task.
`algorithm/construction.md` points at
`plans/nov-19/03b-task-construction-design.md` as the first golden record, but
that is a plan document, not a fixed data file. The first end-to-end test needs
a fixed record to compare against, and an untyped record drifts silently.

**Recommendation:** one versioned JSON file per golden task holding the program,
the expected canonical clue sequence, and the expected answer with its evidence;
the test compares the constructed definition field by field.

## P1

### Product (P1)

None.

### Technical (P1)

Work order:

1. `MC-18` — program-floor backfill; it keeps the floor after execution
   failures.
2. `MC-22` — geometry-required for 1-step tasks; it changes what the first
   release counts.
3. `MC-20` — duplicate normalized text; it can put the same `task_id` in two
   splits.
4. `MC-29` — run-level execution contract; retries and cache hits are promised
   without it.

#### MC-18 — Program floor backfill

Program-floor backfill after execution failures is undefined, including the
post-execution path when the 1,000-program floor is missed. `01c` fetch program
pool checks the floor before execution; execution failures can still drop the
usable count below 1,000. It absorbs `MC-19`. A 10k-task release can currently
ship with fewer than 1,000 usable programs.

**Recommendation:** one backfill loop triggered by the usable-program count:
promote reserve, graph it, replan; record the count in the deficit ledger so the
trigger is data, not a manual check.

#### MC-22 — Geometry-required for 1-step tasks

The geometry-required rule for 1-step no-clue tasks is wrong, and the 95%
aggregate check is missing. The current definition requires a task clue to
depend on the built shape, so every 1-step task with no clue is marked false
even when the answer needs geometry — including every 1-step membership task.

**Recommendation:** define `geometry_required` as "the answer cannot be computed
from the program text alone", which covers the answer step; a 1-step membership
task then counts as geometry-required and the 95% check applies to all tasks.
Restate R-4 the same way, or the check measures a different property from the
requirement.

#### MC-20 — Duplicate normalized text across collections

Duplicate normalized text across collections is unresolved. `01d` normalize
programs gives identical normalized bytes one `program_id` and says later stages
must not treat the records as distinct, but `01b` select program pool keeps both
rows with different families and no pipeline stage enforces the rule. `task_id`
is keyed on `program_sha256`, so the release can hold two rows with the same
`task_id` and different splits.

**Recommendation:** keep both selection rows for collection accounting, but
graph and construct once per `program_id` and use the survivor's family, which
is the rule `01b` select program pool already applies within a collection. State
which stage enforces it (`03a` allocate task quotas at graph selection or `03b`
construct task definitions at construction).

#### MC-29 — Run-level execution contract

Run-level execution contracts are missing: the run manifest artifact, completion
markers, cache lookup, atomic writes, and resume semantics. The run-level graph
tolerance policy content is specified in `graph-persistence.md`, but the run
manifest that hosts it is not an artifact in `artifacts.md`. Retries and cache
hits are promised without the surrounding contract.

**Recommendation:** put the run contract in `artifacts.md`: one run manifest
with the tolerance policy and its hash, one completion marker per artifact,
write to a temporary path then rename, and a cache key of input hash plus every
version that affects the output. State the resume rule: skip an artifact only
when its completion marker and identity match.

## Closed or merged in the 2026-11-20 pass

- `MC-26` — release contract section 7 is a field table with `release_id`,
  `generator_version`, `upstream_dataset_version`, and the external-manifest hash;
  `release_id` is `cadqarel:<sha256>` over the canonical release rows in `task_id`
  order. Section 8 is the dataset card outline, including the answer conventions.
  `05` owns both and writes the card from the manifest.
- `MC-12` — `04` render prompt and choices owns the projection, and the release
  contract carries one `Carries` row per column. Answer text is copied, never
  re-serialized; `clue_types` comes from `clue_operand_form_profile`;
  `prompt_sha256` is over the `prompt` UTF-8 bytes; `answer_sha256` is copied and
  not recomputed. `answer_schema_version` is now a `TaskDefinition` field, which
  `answer_sha256` already hashed.
- `MC-25` — `prompts.yaml` and its schema are written in `prompt-templates.md`;
  `tests/test_prompt_templates.py` validates the file. The file carries template
  IDs, typed placeholders, label tables, and dataset and evaluation namespaces;
  `04` rejects a missing, extra, or untyped placeholder.
- `MC-13` — `05-validate-and-export-release/release-checks.md` lists one check
  per requirement statement, with its scope, bound, and first-release
  disposition.
  A miss blocks export until the owner accepts it into `known_misses`; a bound
  that coverage makes impossible is `superseded` rather than a miss. The
  conditional release share is one implementation, called by `03a` and `05`.
- `MC-38` — the release table carries `clue_operand_form_profile`, and
  `support/` carries five tables including `clue-operand-form-by-step.json`.
  `04` copies it from the definition, and `05` reads it for clue operand form
  coverage.
- `MC-46` — dissolved. The census is a typed function of the graph, not an
  artifact: `03a` derives it and stores the union per family in
  `family_profiles`, `03b` derives it per program, and `03c` reads the plan.
  `DS-43` supersedes the sentence in `DS-33` that says `02c` emits the census.
- `MC-44` — feasibility is the constructor's output over a committed coverage
  fixture set, not an abstraction of the grammar. The fixture set and the checked-in
  expected table are in `task-step-support.md`, and the structural and witness
  tiers are in `pipeline/testing/task-step-support.md`. Fixtures are programs, so
  no Parquet enters the repository.
- `MC-14` — `failure-record.md` owns the row schema, the dedupe key, the merge,
  the order, the reconciliation rule, and the aggregation. The record is one
  partition per rejecting pipeline stage, merged by `05`.
- `MC-40` — `DeficitClass` is a closed set of seven classes in `03c` resolve
  deficits, `03a` records the allocation detail instead of a class, and the
  census decides between a capability and a capacity deficit. A probe deficit
  stays local to its state; a pair that is not emitted is not a class.
- `MC-37` — the definition fields are written: `state_scope`,
  `clue_operand_form_profile`, `answer_parameter`, and `geometry_required` are
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
  tables as data; it calls the derivation that writes them, and `DS-28` now says
  so. The plan and the QA projection cannot disagree.
- `MC-31` — the slow loop in `03c` resolve deficits includes `01d` normalize
  programs; the flow line in `00` end to end was the defect and is fixed.
- `MC-17` — reserve rows are fetched but not normalized or graphed; promotion is
  the slow loop, in `01c`, `01d`, and `03c`.
- `MC-23` — the stop rule is three rounds with a 20% growth cap and an
  `AcceptedMiss`, in `03c`.
- `MC-45` — the P1 balance row is an equal share among supported forms, in
  `task-structure.md`.
- `MC-27` — Q1 is retired for PRD Q7, and the benchmark is pinned in the
  manifest, in `05`.
- `MC-28` — the owner reviews a P0 sample behind a blocking gate, in `05`.
- `MC-47` — the scalar target is a measurement instance, with the candidate set,
  binding, and identity written in `task-structure.md`, `construction.md`, and
  `03b`.
- `MC-35` — the relation row now carries `tolerance` and CAD graph evidence,
  both excluded from `relation_id`, in `graph-persistence.md`.
- `MC-43` — the named-endpoint derivation, the pair rows, and the state-size
  rejection are written in `graph-construction.md`.
- `MC-08` — the resolver table is written in `03b` construct task definitions,
  with the angle, position, material-change, and topology-change conventions.
  The dataset card now has to state them for consumers.
- `MC-39` — clue operand form is coverage-only in P0, with one clue occurrence
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
