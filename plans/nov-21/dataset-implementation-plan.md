# Dataset implementation plan — 2026-11-21

**Status:** working plan, updated 2026-11-25 against commit `ca7ef60`.

This document owns the order in which the replacement dataset generator is
built, keyed by the requirement scope each work item implements. It does not own
any contract: every change it schedules is written into the owner document named
in the tables below. Each pipeline stage contract is owned by
[`docs/dataset/implementation/pipeline/`](../../docs/dataset/implementation/pipeline/00-end-to-end.md),
the file layout by
[`file-trees.md`](../../docs/dataset/implementation/file-trees.md), and the
execution rules by [`run-contract.md`](../../docs/dataset/implementation/run-contract.md).

It exists because three fragments implied three different orders:
`file-trees.md` §Bootstrap order is bottom-up per pipeline stage,
`plans/nov-19/03b-task-construction-design.md` §Milestones is depth-first inside
`03b` only, and `plans/nov-21/dataset-architecture-audit.md` §Recommended
pre-implementation order is about documents, not code.

## Scoping rule

`P0`, `P1`, and `P2` are the requirement scopes in
[`PRD.md` section 8](../../docs/dataset/requirements/PRD.md#8-size-and-mix-of-the-benchmark-dataset-release)
and [`DS-ADR-01`](../../docs/dataset/implementation/decisions.md#ds-adr-01--p0p1p2-are-implementation-order-not-task-labels):
implementation order for requirements and generation inputs. This plan is keyed
by them and by nothing else.

- `P0` is the first release: task reasoning steps 1–5, the P0 vocabulary, and
  the P0 checks. It ends with a release that meets the PRD's P0 targets or
  records each miss as a `known_miss`.
- `P1` starts only after that release exists. It adds the 6–10 tiers behind the
  PRD section 6.1 release gate, the transfer benchmark set, cumulative split
  preservation, the P1 balance bounds, and publication.
- `P2` may never execute.

Work items are numbered `P0-W1`–`P0-W7`, `P1-W1`–`P1-W4`, and `P2-W1`–`P2-W3`.
`W` is a work item and the number is dependency order within the scope. The
suffix is deliberately not `T` or `M`: `task` already means a CAD-QA dataset
task (`task_id`, `TaskDefinition`), and `M` is the `03b-M1`–`03b-M5` milestone
series inside `03b`.

The project schedule is a different axis: `Phase 0`–`Phase 6` in
[`docs/development-plan.md`](../../docs/development-plan.md) are the research
plan over months. `Phase 1` consumes the `P0` work list and then the `P1` work
list; the later phases consume the release. `Phase N` is a schedule phase and
`PN` is a requirement scope, so they are never the same number space.

## Ordering inside P0

**A vertical walking skeleton first, then DAG-order depth, with `02` and `03b`
concurrent.**

Neither a pure DAG order nor hardest-first is right, because the DAG has two
independent risk poles and strict DAG order serializes them:

| Risk | Where it lives | What it decides |
|---|---|---|
| Technical | `02a`/`02b`: CadQuery/OCP execution, entity identity, topology, tolerance | Whether the graph can be built at the stated cost and precision |
| Design | `03b`: construction, uniqueness, clue search, answer equality | Whether 10,000 unambiguous tasks exist at all |

DAG order answers the second question last, which is the project-scale version
of the failure recorded in
[`plans/nov-20/vocabulary-scope-risk.md`](../nov-20/vocabulary-scope-risk.md):
breadth-first work with no feedback signal. Hardest-first alone is also wrong:
`03b` cannot be debugged without a graph and a release row, and `02b` built
without a consumer produces graph fields nothing reads.

The DAG is still the right *filling-in* order: the skeleton is one pass through
every pipeline stage, then each track deepens in dependency order. `P0-W3` and
`P0-W4` run concurrently because `03b`'s input contract (the graph tables and the
runtime schema) is already fixed, so it can be built against golden fixtures and
graphs from a handful of programs. Start `P0-W3` first and `P0-W4` roughly a week
later, so `02c`'s schema is real before `03b` depends on it.

## P0 work list

| Work item | Requirements | Goal | Pass condition |
|---|---|---|---|
| `P0-W1` | — | Contract close-out: the decisions that must exist before code | The owner docs named in [P0-W1](#p0-w1--contract-close-out) carry the new rules; no code |
| `P0-W2` | R-18, R-19 | Walking skeleton: one program → one release row | `test_pipeline_end_to_end` green on the fixture pool; a rerun is a no-op with byte-identical output |
| `P0-W3` | R-1, R-4, R-19 | Extraction and execution depth: AST, CadQuery runtime, CAD graph, census, completeness, and the verified oracle set | Validation and persistence tests green on the real pool; failures reconcile; no unexplained missing or orphan row; every must-extract capability has a verified oracle; time and memory per program recorded |
| `P0-W4` | R-1–R-9, R-15 | Construction depth: clue search and the P0 vocabulary | Golden records match; property tests hold; yield per program measured on real graphs |
| `P0-W5` | R-7–R-10, R-13, R-15 | Quotas and deficits: `03a` and `03c` | A planned release over the real pool with reconciled counts and a deficit ledger |
| `P0-W6` | R-1–R-10, R-13, R-14, R-17–R-19 | Rendering, validation, and the release contracts: `04`, `05`, the grader, the dataset browser and the three dataset release review ledgers | A release built from the real pool, validated, with every miss recorded as a `known_miss` |
| `P0-W7` | R-14, R-17–R-19 | First real `P0` release | Tagged release revision and run manifest; `docs/development-plan.md` Phase 2 can start |

The five `03b` construction milestones in
[`plans/nov-19/03b-task-construction-design.md`](../nov-19/03b-task-construction-design.md#milestones)
are local to `03b` and are numbered `03b-M1`–`03b-M5`:

| `03b` milestone | Lands in |
|---|---|
| `03b-M1` plumbing | `P0-W2` |
| `03b-M2` clue search | `P0-W4` |
| `03b-M3` full vocabulary | `P0-W4` |
| `03b-M4` scheduler | `P0-W4` → `P0-W5` |
| `03b-M5` first release | `P0-W6` → `P0-W7` |

## P0-W1 — contract close-out

Nearly no code. Each item is a small edit to one owner document, scheduled here
because the code that would otherwise encode the wrong answer is `P0-W2` or
`P0-W3` work. The shared `FailureRecord` struct follows a contract change in
the same change, as `MC-65` did with its disposition column.

No item remains open. `DA-4`, `DA-15`, `DA-13`, and `DA-5` closed between
the audit and 2026-11-25 and are listed below; `DA-7` / `MC-63` closed by
re-scoping R-5 to P1, `MC-66` closed by the must-extract capability set,
`MC-65` closed by the failure disposition, `MC-64` closed by the dataset
release absence and geometry residual ledgers, and `MC-67` closed by the
pair-distance contract and its measured capture cost.

Closed since the audit's `P0-W1` table:

- `MC-66` — the must-extract capability set and its release check are written:
  `MustExtractCapability` in `extraction/validation.md` is the closed P0 cell
  set, and `extraction_capability_coverage` blocks the export when a declared
  cell has no accepted graph. The `P0-W3` pass condition can be evaluated.
- `MC-65` — `FailureDisposition` is the closed `by_design`, `corpus_defect`,
  `extractor_gap` set in `failure-record.md`; every rejecting pipeline stage's
  reason set names the disposition its reasons carry, `05` counts by disposition
  during reconciliation, and the Go `FailureRecord` struct and its merge test
  carry the column. The decision is `DS-ADR-17`.
- `MC-64` — the review gate has three ledgers: the dataset release task review
  ledger over the sampled matrix, an exhaustive dataset release absence ledger
  over every absent program, capability, or capacity, and a uniform dataset release
  geometry residual ledger of `min(pool_size, 300)` programs at `bound_p = 0.01`
  run through the CAD graph kernel-oracle differential. `05` derives the
  expected absence key set and blocks on a gap or an `extractor_gap`; the
  manifest records the three ledger hashes. The ledger schemas are in
  [`release-dataset-contract.md`](../../docs/dataset/requirements/release-dataset-contract.md#dataset-release-review-ledgers),
  the frontend is
  [`devtools/dataset-browser.md`](../../docs/dataset/implementation/devtools/dataset-browser.md),
  and the review gate is
  [`05` validate and export release](../../docs/dataset/implementation/pipeline/05-validate-and-export-release.md#review-gate).
- `DA-4` / `MC-53` — `DS-REQ-15` makes `same_answer` the construction comparison
  and the grader's comparison, and `b-answer-semantics.md` rechecks the
  answer-equivalent set against it.
- `MC-22` / `DA-15` — `geometry_required` is derived from the answer meaning and
  the clue type in `a-construction.md`; `release-checks.yaml` selects `value: true` in
  `built_shape_share_floor`, so the 95% floor is executable.
- `DA-7` / `MC-63` — R-5 is re-scoped to P1. `03b` runs the P1
  `shortcut_resistance` quality gate over the answer dependency chain; the
  requirement is [`requirements/shortcut-resistance.md`](../../docs/dataset/requirements/shortcut-resistance.md)
  and the implementation is `P1-W5`. The P0 release makes no R-5 claim.
- `DA-13` / `MC-44` — the support-table derivation is written in
  `task-step-support.md` and `testing/00-support-tables.md`. The coverage
  fixtures are programs, so they are `P0-W3` artifacts, not a missing contract.
- `DA-5` — the `release_id` inputs are the table in
  `release-dataset-contract.md` §7.1, so the `P0-W2` manifest writer records the
  final field set.
- `MC-50` — closed in `30c66b5`; pair emission is bounded per reference class
  (`DS-REQ-37`), which schedules `02c` and `03b` work in `P0-W3` and `P0-W4`.
- `MC-49` / `DS-ADR-16` — closed in `059e8fb`; the P0 exact-text overlap check
  belongs to `05` in `P0-W6`.
- `DS-ADR-15` — `982423e` makes run wall time a CadQuery-execution budget; the
  `P0-W3` measurement certifies it.

The performance findings `PA-1`–`PA-14` are closed in `ef3ac58`: `EX-22` to
`DS-ADR-09` and the run-contract rewrite carry them. Their implementation is `P0-W2`,
`P0-W3`, and `P0-W4` work; the plan schedules that work, not the decision.

Closed before the audit list was written: `DA-1` by `run-contract.md`, and
`DA-3`'s data path by the review ledger in `01578d8`; the browser scene and
approval are `P0-W6` code, not a `P0-W1` gap.
The graph completeness contract and the extraction-graph oracle format are
written; their implementation and the verified oracle set are `P0-W3` work.

Deferred, and deliberately not closed in `P0-W1`:

| Item | Lands in | Reason |
|---|---|---|
| `DA-2` evaluation material and grader | `P0-W6` | It is a deliverable, not a generator input; the prompt-only view is `04`'s projection |
| `DA-6` per-split coverage and balance | `P0-W6` | The checks are `05` code and their bounds depend on what `03b` can construct |
| `DA-8` family-to-split registry | `P0-W6` writer, `P1-W3` reader | The writer must exist before the first release; only the second release reads it |
| `DA-9` license and attribution | `P1-W4` | Publication blocker, not a first-release blocker |
| `MC-49` external benchmark program set (the artifact, not its contract) | `P1-W2` | R-16 is P1; `05` owns the P0 overlap check and the manifest fields |
| Construction cost constants | `P0-W4` | `TG-10` sets the budget and cover-search rules; the provisional numbers need one measured pass over the pool |
| `02b` point-probe state scope | `P0-W3` | `ef3ac58` records that P0 binds one solid state but `02b` still probes every state; resolve it with the `DS-REQ-10` rule |
| Release answer column review | `P0-W6` | `ef3ac58` makes the answer columns typed consumer-facing Parquet; confirm them before the first published release |

The rule this table encodes: **if a decision does not unblock the next work
item, defer it to the item that consumes it.** This is the mitigation from
`vocabulary-scope-risk.md` applied at project scale.

## P0-W2 — walking skeleton

One program produces one release row through the production entry point. The
point is not the row; it is that every seam is exercised while it is still cheap
to change.

**Go.**

- Implement the run-contract code half that is documented but absent:
  `internal/shared/run_manifest.go`, `run_state.go` (lock, pipeline stage markers, part
  scan), `cache_index.go`, `parquet_writer.go`.
- The writer is the sharded part writer from `DS-ADR-07`: a unit belongs to
  `sha256(pass_key) mod journal_shard_count`, the default is 16, and
  `journal_shard_count` is part of `run_id`. `02b` stays one unit per part.
- A shard is a container, not a transaction (`DS-ADR-09`): a rejection, timeout, or
  crash is a failure row for that unit and the shard commits the rest; a shard
  with no successes writes no part.
- Implement `internal/run` `Run`, `Status`, and `List`, replacing the
  `ErrNotImplemented` returns.
- Unit identity follows `DS-ADR-07`: content, not assignment. A `03b` unit is keyed
  by the program and the graph identity, and the `03a` plan is not an input.
- Replace the remaining freeform `dict` request and response in
  `generator/python/cadqa_dataset_generator/worker.py` with typed per-pipeline-stage models as
  each pipeline stage lands. Do not design all pipeline stages' models up front.

**Pipeline stages.**

- `01a`–`01e` on a three-program fixture pool cut from
  `data/cadevolve_sources.parquet`.
- `02a`/`02b`/`02c` on the program in
  `docs/dataset/implementation/pipeline/testing/golden/box-with-hole.json`.
- `02c` writes the `GraphCompletenessReport` for the box-with-hole program from
  [`extraction/graph-completeness.md`](../../docs/dataset/implementation/pipeline/extraction/graph-completeness.md);
  the expected set comes from the upstream extraction records and the contract
  rules, not from the graph. The oracle set calibrates those rules.
- Verify the two extraction-graph oracles (`box-with-hole`, `rotated-box`) from
  `proposed` to `verified`; the builder and the records are checked in under
  [`testing/oracles/extraction-graph/`](../../docs/dataset/implementation/pipeline/testing/oracles/extraction-graph/).
- `03a` emits a one-cell plan, typed from its own doc even though the allocation
  is trivial.
- `03b` lands the plumbing milestone (`03b-M1`) from
  `plans/nov-19/03b-task-construction-design.md`: final solid state target,
  volume answer, number format, one step, no clue search.
- `04` renders from `prompts.yaml`; `05` exports `release.parquet`,
  `failures.parquet`, `manifest.json`, and the dataset card. The support table
  and its `05` assertion belong to `P0-W5`; the W2 export does not require them.
- `tools/manual-verification/dataset_browser.py` opens the skeleton row: the final
  solid state, the prompt text, and the gold answer. It is the owner's first
  verification point and the same tool serves `P0-W4`. Its approval action
  appends the verdict to the dataset release task review ledger at the path the
  release contract defines; that is an edit to the existing browser, and the
  schema is the one `P0-W6`'s review queue consumes.

**Pass condition.** `test_pipeline_end_to_end` from
`testing/00-end-to-end.md` is written from its contract and green on the fixture
pool; a second run with the same inputs executes no unit, writes no part, and
produces byte-identical `release.parquet`; `generator status` reports the
completion marker and part counts for each pipeline stage.

**Scope, and what replaces it.** The skeleton is deliberately thin. Each thin
part has an owner later in the plan; a skeleton behaviour that is not in this
table is part of the contract and is not replaced later.

| Skeleton behaviour | Replaced by | Failure if left |
|---|---|---|
| `01` runs on a three-program fixture pool | `P0-W3` full pool | the fixture hides fetch, selection, and normalization failures |
| `03a` emits a one-cell plan | `P0-W5` quota allocation | the typed plan bakes in one cell and one program |
| `03b-M1`: final solid state, volume answer, number format, one step | `P0-W4` `03b-M2`/`M3` | the constructor grows a path that the `box-volume` oracle later disagrees with |
| `05` exports without the full check suite | `P0-W6` P0 checks and `known_misses` | the partial export becomes the release contract |
| One `GraphCompletenessReport`, for `box-with-hole` | `P0-W3` whole pool | the report shape is the acceptance gate, and it is untested on hard geometry |
| `02b` binds one solid state; the point-probe scope is unresolved | `P0-W3` `DS-REQ-10` rule | changing it later invalidates every graph and every `03b` unit |
| No family-to-split registry | `P0-W6` writer, `P1-W3` reader | the first release becomes the migration |
| No sampled review queue, only `dataset_browser` and the dataset release task review ledger | `P0-W6` three-ledger gate | the ledger schemas change after rows exist |
| No graph persistence tuning; one part per `02b` unit | contract, not a shortcut (`DS-ADR-07`/`DS-ADR-09`) | none; this one is not replaced |

**Contract conflict to settle before the first commit.** `P0-W2`'s `03b` scope
is `03b-M1` (one step, volume, no clue search), but `test_pipeline_end_to_end`
in [`testing/00-end-to-end.md`](../../docs/dataset/implementation/pipeline/testing/00-end-to-end.md)
asserts that the golden record's definition appears in the release, and
[`golden/box-with-hole.json`](../../docs/dataset/implementation/pipeline/testing/golden/box-with-hole.json)
is a three-step edge-length task. The test cannot be green on a one-step
constructor as written. Either the skeleton asserts a one-step `box-volume`
golden and `box-with-hole` moves to `P0-W4`, or the skeleton's single row is the
box-with-hole chain. The first keeps `03b-M1` honest and is the smaller scope;
the test doc owns the answer and must say which before `P0-W2` is marked green.

**Why first.** Artifact identities, the Parquet schema across the Go/Python
boundary, the worker protocol, resume, and failure reconciliation are the
expensive things to change later. It also converts "the documents are the
deliverable" into a running binary.

## P0-W3 — `02` depth

Started first of the two concurrent tracks.

- The coverage and rejection fixture set, which is also the support table's
  input.
- `02a`: the full allowlist, method signatures, shape derivation, and the
  CadQuery selector, CadQuery workplane, CadQuery profile, solid, and expression
  features.
- `02b`: the long-lived worker that preloads CadQuery/OCP and forks a child per
  program (`EX-22`), runtime capture, topology, states, point probes, tolerance
  handling, and failure tombstones. The child writes under `.tmp-` and the parent
  validates and renames; the 30-second limit starts at the child's ready signal.
- `02c`: graph construction and persistence, bindable-state pair emission and
  `implementation_scope` in the graph identity (`DS-REQ-10`), the capability census,
  the fingerprint copy instead of a recompute (`DS-ADR-08`), and the pair-emission
  bound per reference class (`DS-REQ-37`, `MC-50`): a dense class is emitted
  whole or not at all, and the bound is measured from the pool.
- `02b` also captures the dense pair distances with the specialized extrema
  classes, while CadQuery is warm, and `02c` copies them (`EX-25`); the measured
  cost is 38.5 ms at the median and 811 ms at the worst of 40 sampled programs,
  inside the `DS-ADR-15` budget.
- Shard parts for `01d`, `02a`, and `02c`; `02b` stays one unit per part
  (`DS-ADR-07`).
- Resolve the `02b` point-probe scope: P0 binds one solid state per task, so
  decide whether probes follow the same rule before the graph is measured.
- The completeness contract: the expected-relation table and the per-program
  `GraphCompletenessReport` with missing, orphan, and unclassified counts. The
  production check is projection-only; the kernel oracle stays a dev-mode
  calibration path, not a pipeline stage.
- The extraction-graph oracle set: one program per must-extract capability cell,
  plus the hard-geometry classes (rotated, tangent, thin wall, multi-solid, seam,
  spline). Each record is human-verified before it gates a release.
- The rejection contact sheet and the absence review: every absent program,
  capability, or capacity gets a row in the dataset release absence ledger; a program row also
  gets an oracle render, its failure reason, and a disposition.
- The residual random sample: `min(pool_size, 300)` programs at `bound_p = 0.01`,
  drawn uniformly from the pinned dataset release program pool and run through the kernel-oracle
  differential; `residual_sample.py` writes the ledger.

**Pass condition.** The extraction validation and graph persistence tests pass
on a 100-program slice and then the full active pool; every program either has a
graph or one failure row and the counts reconcile; per-program CadQuery-execution
wall clock is reported against the `DS-ADR-15` budget with import time separate,
and CPU and peak memory are recorded; the graph report is comparable to the pre-rebuild
measurements (677,937 CAD graph entities and 20,135,608 CAD graph relations for
1,000 programs); the completeness report has no unexplained missing, orphan, or
unclassified row, and every must-extract capability has a verified oracle.

## P0-W4 — `03b` depth

Started roughly a week after `P0-W3`.

**Input: the gold matrix is complete.** The owner approved the hand-authored set
on 2026-11-25, and it is recorded outside the oracle files: the eight P0 prompts
in [`prompt-examples.md`](../../docs/dataset/requirements/views/prompt-examples.md#p0)
(including the comparison and provenance clue types), every P0 reference form in
[`reference-forms.md`](../../docs/dataset/requirements/views/reference-forms.md#p0),
and the clue strings in
[`clue-list.md`](../../docs/dataset/requirements/views/clue-list.md#p0). Thirteen
cases also have an executable record under
[`oracles/task-construction/`](../../docs/dataset/implementation/pipeline/testing/oracles/task-construction/README.md),
with a gold query that runs without generator code; eleven are `verified` and two
returned to `proposed` after the copy change, as the oracle README records.
`03b` matches the records by answer, clue chain, and evidence, and treats an
approved worked example as the gold for a cell with no record. §9 of the oracle README counts records only; it
is reworded when `03b` lands so a missing record does not read as a missing
vocabulary cell.

- The `TG-10` construction rules first: one attempt budget per (CADEvolve program
  family, task reasoning step count), one program pass per revision with the
  census from the plan, and count-based cover-search scope constants. These rules
  are what keep a 10,000-task release from becoming 10^5 cover searches.
- The clue-search milestone (`03b-M2`), then the full-vocabulary milestone
  (`03b-M3`): comparison, provenance, multiple target categories, distance,
  angle, region. This is the P0 vocabulary; aggregation is P1 and the P2 extras
  stay out.
- Golden records per task shape, and the property tests: every accepted task is
  answer-unique under the `same_answer` predicate (`DS-REQ-15`), every clue
  narrows, and every clue is true of all final possible answers.
- The multiple-choice pool from the penultimate answer candidate set, under
  `MC-15`.
- `DA-7`'s R-5 proxy as a construction rule, if `P0-W1` defined one.

**Pass condition.** The golden records match; the property tests hold; the
provisional construction limits (200 candidates, 64 facts, 20,000 expansions,
64 rechecks) are measured and either confirmed or replaced; and **yield per
program is measured on 50–100 real graphs**. That number, not a schedule
estimate, decides whether 10,000 tasks are reachable, how much expansion `03c`
must do, and whether the P0 vocabulary needs to shrink.

## P0-W5 — `03a` and `03c`

- `03a`: quota allocation, the conditional share, the support-table derivation
  and its single run artifact (`support/support.parquet`, not a release copy),
  the split assignment, and the warmup label.
- `03c`: the seven deficit classes, the fast loop (`03a` → `03b`), the slow loop
  (`01b` → `01c` → `01d` → `02` → `03a` → `03b`), the three-round 20% stop rule,
  and the deficit ledger.

This is the scheduler milestone (`03b-M4`) from the `03b` design doc, where
`03b` meets `03a` and `03c`.

**Pass condition.** A planned release over the real pool with counts reconciled
at every pipeline stage, a deficit ledger, and one exercised slow-loop round.

## P0-W6 — `04`, `05`, and the release contracts

- `04`: the full projection, choices, and the evaluation-namespace prompt.
- `05`: the P0 release checks, including per-split coverage and balance
  (`DA-6`), `release_id` (`DA-5`), the family-to-split registry writer (`DA-8`),
  the P0 exact-text overlap check against the external benchmark program set
  (`MC-49`, `DS-ADR-16`), the dataset card, and the answer-column review.
- The dataset browser's review queue and its sampled matrix, per
  [`devtools/dataset-browser.md`](../../docs/dataset/implementation/devtools/dataset-browser.md);
  the browser and its ledger write already exist from `P0-W2`, and `P0-W6` adds
  the coverage-gap queue, the clue-coloured scene, and the `pending` rows.
- The dataset release absence and geometry residual ledgers, and the release gate
  that derives the expected absence key set and requires the dataset release
  geometry residual-defect sample to meet
  `min(pool_size, 300)` at `bound_p = 0.01`, so an open extraction gap blocks
  export even when the release rows look complete.
- The `extraction_capability_coverage` check: a must-extract capability with zero
  accepted graphs fails the release.
- The evaluation material and grader (`DA-2`), including the prompt-only view,
  answer parsing per format, and the tolerance semantics from `DA-4`.

**Pass condition.** A release built from the real pool with every P0 check green
or recorded as a `known_miss` with a reason; the grader scores a gold row and a
near-miss correctly; export blocks when a review-gate cell is missing.

## P0-W7 — first `P0` release

Tag the release revision, record the run manifest, and hand off to
`docs/development-plan.md` Phase 2. Everything after that is the existing
project plan, not this one.

## P1 work list

`P1` starts only when `P0-W7` exists. Each item names the requirement it adds.

| Work item | Requirements | Goal |
|---|---|---|
| `P1-W1` | R-9 (6–10) | 6–10 tiers behind the PRD section 6.1 release gate: a synthesis pilot, at least two real candidates, 30 reviewed tasks per tier or every task, and a test row per tier |
| `P1-W2` | R-16 | External benchmark program set and the transfer overlap check (`MC-49`) |
| `P1-W3` | R-11, R-12 | Cumulative releases (PRD section 10): honour the family-to-split registry, and add the P1 balance bounds (no CAD model above 1%, no clue type above 25%, answer-meaning shares, at least 1,000 distinct answers) |
| `P1-W4` | R-18 | License and attribution (`DA-9`), and the public dataset card and tagged revision |
| `P1-W5` | R-5 | `03b` R-5 quality gate: the standalone answer-dependency-chain function, the `shortcut_resistance` validity rule, and the P1 rejection count. Last P1 item; it may move to P2 if the graph parts are not retained or the threshold check is not worth its cost |

`P1-W1` reuses `P0-W4`'s constructor and `P0-W6`'s checks; it is a scope extension,
not a rewrite. A tier that fails its release gate is reported as not covered, and the
release claims the highest contiguous tier that passed.

## P2 work list

`P2` may never execute, and none of it may delay `P0` or `P1`.

| Work item | Requirements | Goal |
|---|---|---|
| `P2-W1` | R-3 | Near-miss multiple-choice distractors (`Q6` in `03b`) |
| `P2-W2` | — | Arbitrary Python control flow in P-tier programs (`02a` open question) |
| `P2-W3` | R-22 | Kernel-assisted evaluation upper bound (`cadquery` LLM harness) |

## P0 requirement coverage

Every P0 requirement has at least one work item. A requirement with no item is a
planning defect, not a scheduling choice.

| Requirement | Work items |
|---|---|
| R-1 answers are correct | `P0-W3`, `P0-W4`, `P0-W6` |
| R-2 exactly one correct answer | `P0-W4`, `P0-W6` |
| R-3 multiple choice is fair | `P0-W4`, `P0-W6` |
| R-4 at least 95% require the built shape | `P0-W1`, `P0-W3`, `P0-W4`, `P0-W6` |
| R-6 no answer leakage | `P0-W4`, `P0-W6` |
| R-7 answer-format coverage and balance | `P0-W4`, `P0-W5`, `P0-W6` |
| R-8 coverage of categories, clue types, forms, meanings | `P0-W4`, `P0-W5`, `P0-W6` |
| R-9 steps 1–5 | `P0-W4`, `P0-W5`, `P0-W6` |
| R-10 at least 1,000 CAD models | `P0-W5`, `P0-W6` |
| R-13 splits do not overlap | `P0-W5`, `P0-W6` |
| R-14 the test set is never trained on | `P0-W6`, `P0-W7` |
| R-15 the warmup subset is labeled | `P0-W4`, `P0-W5`, `P0-W6` |
| R-17 a careful human understands every task | `P0-W2`, `P0-W4`, `P0-W6`, `P0-W7` |
| R-18 the dataset is reproducible | `P0-W2`, `P0-W6`, `P0-W7` |
| R-19 nothing disappears silently | `P0-W2`, `P0-W3`, `P0-W4`, `P0-W5`, `P0-W6` |

## Owner verification points

The owner is not in the loop for code or mechanical checks; the tests own those.
The owner is in the loop for four judgements: whether the extraction checker is
trustworthy on the verified oracle set, whether a task reads as a question a
careful person can answer, whether the answer is the right answer, and whether a
miss is acceptable. The first judgement is new: the checker cannot certify
itself, so a human verifies the oracle set that calibrates it, not every program.
[`manual-verification-protocol.md`](manual-verification-protocol.md) turns these
points into passes and names the seams they do not cover.

| Work item | What the owner verifies | Artifact | Time |
|---|---|---|---|
| `P0-W2` | The skeleton row: does the prompt read as a question, and is the answer defensible? This is the first point at which the wording pipeline can be judged. | the dataset browser on the skeleton row, plus a `pass` or `defect` row in the dataset release task review ledger | ~15 min |
| `P0-W2` | The box-with-hole extraction-graph oracle: do the nodes, incidence relations, and measurements match the program? Set `verified` and name the reviewer. | `oracles/extraction-graph/box-with-hole.json` | ~30 min |
| `P0-W3` | The rotated-box oracle and the first capability-cell oracles; the completeness report exceptions. This is the check that a supported capability did not silently disappear. | oracle records and the completeness report | ~2–3 h |
| `P0-W4` | The quality gate before scale: 15–30 constructed definitions on real graphs, across clue types and answer meanings, plus the yield number. This is where ambiguous wording is cheapest to fix. | a dataset browser sample and the yield report | ~1–2 h |
| `P0-W5` | The deficit ledger: accept or reject each miss and each expansion round. `known_misses` is an owner decision. | deficit ledger and plan | ~30 min |
| `P0-W6` | The blocking review gate: every required sampling cell has a current `pass`; a `defect` blocks the export. Dataset card sign-off. | the dataset browser and the task review ledger | per the sampling matrix |
| `P0-W6` | The dataset release absence and geometry residual ledgers: does every absence account for an upstream subject, and does the random pool sample contain a mismatch? | dataset release absence and geometry residual ledgers | per the sampling policy |
| `P0-W7` | Release sign-off: manifest, dataset card, `known_misses`, `release_id`. | release directory | ~1 h |
| `P1-W1` | The PRD section 6.1 release gate per tier: 30 tasks reviewed, or every task. | the dataset browser and the task review ledger | per tier |

- `P0-W2` and `P0-W4` are cheap, and they are where wording defects are fixed
  while the prompt copy and the constructor are still moving. Do not defer
  wording review to `P0-W6`: a defect there costs a re-render, a new
  `prompt_sha256`, and a fresh review of that cell.
- The dataset release task review ledger is written from `P0-W2` on by the
  dataset browser's approval action, so no owner judgement is throwaway.
  `tools/manual-verification/dataset_browser.py` and the ledger are the one
  human review frontend in
  [`devtools/dataset-browser.md`](../../docs/dataset/implementation/devtools/dataset-browser.md);
  the coverage-gap queue with the full matrix lands in `P0-W6`.
- `P0-W3`'s oracle review is not a spot check of every program: it is the
  calibration set. A verified oracle the checker disagrees with is a checker
  defect; a `proposed` oracle nobody verified is not evidence.

## Related plans

| Document | Owns |
|---|---|
| [`docs/development-plan.md`](../../docs/development-plan.md) | Project phases 0–6, the schedule. `Phase 1` consumes the `P0` list, then the `P1` list. |
| This document | The `P0`/`P1`/`P2` work lists and where each contract gap lands. |
| [`plans/nov-19/03b-task-construction-design.md`](../nov-19/03b-task-construction-design.md) | The `03b` construction algorithm and `03b-M1`–`03b-M5`. |
| [`plans/nov-21/dataset-architecture-audit.md`](dataset-architecture-audit.md) | The `DA-*` findings this plan schedules. |
| [`plans/nov-21/performance-audit.md`](performance-audit.md) | The `PA-*` findings, closed in `ef3ac58`. |
| [`docs/dataset/implementation/missing-contracts.md`](../../docs/dataset/implementation/missing-contracts.md) | The live `MC-*` backlog. |
| [`docs/dataset/requirements/decisions.md`](../../docs/dataset/requirements/decisions.md) | The `DS-REQ-*` decisions every work item implements. |
| [`docs/dataset/implementation/decisions.md`](../../docs/dataset/implementation/decisions.md) | The `DS-ADR-*` decisions every work item implements. |

## What is already done

The scaffold is green (`(cd generator && go test -count=1 ./...)`, `uv run pytest`):

- `generator/main.go`, `generator/internal/run/run.go` — flags, pipeline stage selection,
  exit codes, usage;
- `generator/internal/shared/` — typed artifact tables, the failure record and
  its merge, the `balance.yaml` and `release-checks.yaml` loaders, the worker bridge, and
  the checked-in worker JSON Schema;
- `generator/python/cadqa_dataset_generator/worker.py` — the worker protocol and dispatch;
  `s01d`, `s02a`, `s02b` raise `PipelineStageNotImplemented`;
- the test contracts for every pipeline stage, the golden record, `prompts.yaml`, and
  `tolerance.yaml`;
- the graph completeness contract, the extraction-graph oracle format and two
  `proposed` records, the oracle builder, and the task-construction oracle set
  with its schema, runner, and verifier;
- `tools/manual-verification/dataset_browser.py` and the dataset browser frontend.

So `P0-W2` is not "initialise everything"; it is the run-contract code half plus
one thin body per stage. Do not stub `03`–`05` beyond what `P0-W2` needs: a stub
package that guesses its typed models is a second schema to maintain.

## What not to do

- **Do not harden `01` beyond the fixture pool before `P0-W3`.** Its only consumer
  is `02`; rejection cases should be driven by real pool failures in `P0-W3`.
- **Do not build `05`'s full check suite before `03b`.** The `superseded` bound
  logic exists because construction can make a bound impossible; the checks and
  the constructor are tuned together.
- **Do not fix `graph_schema_version` before `DS-REQ-10` is implemented.** A schema
  change after `P0-W3` invalidates every graph and every `03b` unit.
- **Do not design all typed models in one pass.** The docs own the models; the
  code derives them one pipeline stage at a time.
- **Do not run the real pool before `P0-W2`'s resume works.** A 12.5-hour execution
  pass without resume is a single-point failure.
- **Do not pull `P1` work into `P0`.** The 6–10 tiers, the transfer set, and the
  P1 balance bounds wait for the P0 release; only the family-to-split registry
  writer is early, because the first release would otherwise become the
  migration.
- **Do not read `missing-contracts.md` as the status of `P0-W1`.** It is
  explicitly ephemeral and tracks the entries someone remembered to file. The
  remaining open `P0-W1` items are `MC-64` and `MC-67`; the owner doc named in
  the `P0-W1` table is still the only evidence that the contract exists.

## Quality gates

These are the numbers that decide whether the plan still holds. Record each in
the run manifest or the work-item note.

| Quality gate | Work item | Kills the plan if |
|---|---|---|
| Tasks per program on real graphs | `P0-W4` | The yield cannot reach 10,000 tasks within the 20%/3-round expansion |
| Per-program execution wall clock and peak memory | `P0-W3` | The full pool does not fit the available machine time |
| `03b` attempts per accepted task | `P0-W4` | It exceeds the `TG-10` budget |
| Construction limits (candidates, facts, expansions, rechecks) | `P0-W4` | The measured pass cannot fill the quota targets within them |
| Verified extraction-graph oracles | `P0-W3` | A must-extract capability has no verified oracle, or a verified oracle fails |
| Completeness report on the 100-program slice | `P0-W3` | A missing, orphan, or unclassified row has no disposition |
| Rejection contact sheet coverage | `P0-W3` | A rejected program has no oracle render or no disposition |
| Time from a program change to a new reviewable row | `P0-W6` | It requires a full corpus rerun (`R-21`) |
| Import cost as a share of the execution budget | `P0-W3` | It stays at 7–9% per program after `EX-22` |
| P0 requirement coverage | `P0-W1` | A P0 requirement has no work item in the coverage table |
