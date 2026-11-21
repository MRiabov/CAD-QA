# Dataset implementation plan — 2026-11-21

**Status:** working plan, updated 2026-11-21 against commit `ef3ac58`.

This document owns the order in which the replacement dataset generator is
built, and which contract gaps are closed at which milestone. It does not own
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

## The ordering decision

**A vertical walking skeleton first, then DAG-order depth, with `02` and `03b`
concurrent.**

Neither pure option is right, because the DAG has two independent risk poles and
strict DAG order serializes them:

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
every pipeline stage, then each track deepens in dependency order. `02` and `03b` run
concurrently because `03b`'s input contract (the graph tables and the runtime
schema) is already fixed, so it can be built against golden fixtures and graphs
from a handful of programs.

## Milestones

| Milestone | Goal | Pass condition |
|---|---|---|
| `M0` | Close the contracts that are cheap now and expensive after code exists | The owner docs named in [M0](#m0--contract-close-out) carry the new rules; no code |
| `M1` | Walking skeleton: one program → one release row | `test_pipeline_end_to_end` green on the fixture pool; a rerun is a no-op with byte-identical output |
| `M2` | `02` depth: extraction, execution, graph, census | Validation and persistence tests green on the real pool; failures reconcile; time and memory per program recorded |
| `M3` | `03b` depth: construction, clue search, full P0 vocabulary | Golden records match; property tests hold; yield per program measured on real graphs |
| `M4` | `03a`/`03c`: quotas, deficits, loops | A planned release over the real pool with reconciled counts and a deficit ledger |
| `M5` | `04`/`05` depth and the release-facing contracts | A release built from the real pool, validated, with every miss recorded as a `known_miss` |
| `M6` | First real release, then handoff | Tagged release revision and run manifest; the training and evaluation work in `docs/development-plan.md` Phase 2 onward can start |

`M2` and `M3` are the only concurrent pair. Start `M2` first and `M3` roughly a
week later, so `02c`'s schema is real before `03b` depends on it.

## Owner verification points

The owner is not in the loop for code, extraction correctness, or graph content;
the tests own those. The owner is in the loop for three judgements: whether a
task reads as a question a careful person can answer, whether the answer is the
right answer, and whether a miss is acceptable.

| Milestone | What the owner verifies | Artifact | Time |
|---|---|---|---|
| `M1` | The skeleton row: does the prompt read as a question, and is the answer defensible? This is the first point at which the wording pipeline can be judged. | `render_task.py` on the skeleton row, plus a `pass` or `defect` row in the review ledger | ~15 min |
| `M2` (optional) | Three to five program renders: is each highlighted entity the one a clue would name? This catches semantic drift in CAD graph entity binding that a test cannot see. | one program render per spot-checked program | ~30 min |
| `M3` | The quality gate before scale: 15–30 constructed definitions on real graphs, across clue types and answer meanings, plus the yield number. This is where ambiguous wording is cheapest to fix. | a `render_task.py` sample and the yield report | ~1–2 h |
| `M4` | The deficit ledger: accept or reject each miss and each expansion round. `known_misses` is an owner decision. | deficit ledger and plan | ~30 min |
| `M5` | The blocking review gate: every required sampling cell has a current `pass`; a `defect` blocks the export. Dataset card and license sign-off. | review pack and ledger | per the sampling matrix |
| `M6` | Release sign-off: manifest, dataset card, `known_misses`, `release_id`. | release directory | ~1 h |

- `M1` and `M3` are cheap, and they are where wording defects are fixed while
  the prompt copy and the constructor are still moving. Do not defer wording
  review to `M5`: a defect there costs a re-render, a new `prompt_sha256`, and a
  fresh review of that cell.
- The review ledger is written from `M1` on, so no owner judgement is throwaway.
  `tools/manual-verification/render_task.py` and the ledger are the first-release
  fallback in
  [`devtools/review-pack.md`](../../docs/dataset/implementation/devtools/review-pack.md);
  the sampled pack with the full matrix lands in `M5`.
- The 6–10 tiers add the PRD section 6.1 release gate: 30 tasks per tier, or
  every task.
- `M2` needs no owner review unless the spot check shows drift.

## M0 — contract close-out

No code. Each item is a small edit to one owner document, scheduled here because
the code that would otherwise encode the wrong answer is `M1` or `M2` work.

| Item | Owner | Why it cannot wait |
|---|---|---|
| `DA-4` / `MC-53` — one answer-equivalence relation | `03b`, `DS-32`, `release-dataset-contract.md` | `03b` uniqueness and the grader must be the same predicate, or a task passes construction and fails scoring |
| `MC-22` / `DA-15` — `geometry_required` for one-step tasks | `03b`, `checks.yaml`, `task-structure.md` | Changes what `03a` plans and what `05`'s 95% check counts |
| `DA-13` / `MC-44` — support-table derivation and fixtures | `task-step-support.md`, `testing/00-support-tables.md` | `03a` cannot run without the derivation; the fixtures are programs, so they are `M2` work |
| `DA-5` — `release_id` inputs | `release-dataset-contract.md`, `artifacts.md` | The manifest writer in `M1` should record the final field set |

The performance findings `PA-1`–`PA-14` are closed in `ef3ac58`: `DS-49` to
`DS-56` and the run-contract rewrite carry them. Their implementation is `M1`,
`M2`, and `M3` work; the plan schedules that work, not the decision.

Already closed: `DA-1` by `run-contract.md`, and `DA-3`'s data path by the
review-pack ledger in `01578d8`; the renderer is `M5` code, not an `M0` gap.

Deferred, and deliberately not closed in `M0`:

| Item | Milestone | Reason |
|---|---|---|
| `DA-2` evaluation material and grader | `M5` | It is a deliverable, not a generator input; the prompt-only view is `04`'s projection |
| `DA-6` per-split coverage and balance | `M5` | The checks are `05` code and their bounds depend on what `03b` can construct |
| `DA-7` R-5 shortcut resistance | `M5` | Needs the constructed task to measure; a rule written now would be a guess |
| `DA-8` family-to-split registry | `M5` | Written by `05`; only the second release reads it |
| `DA-9` license and attribution | `M5` | Publication blocker, not a code blocker |
| `MC-49` external benchmark program set | `M5` | `05` owns the overlap check and the manifest fields; the artifact is authored with the release |
| Construction cost constants | `M3` | `DS-51` sets the budget and cover-search rules; the provisional numbers need one measured pass over the pool |
| `02b` point-probe state scope | `M2` | `ef3ac58` records that P0 binds one solid state but `02b` still probes every state; resolve it with the `DS-52` rule |
| Release answer column review | `M5` | `ef3ac58` makes the answer columns typed consumer-facing Parquet; confirm them before the first published release |

The rule this table encodes: **if a decision does not unblock the next milestone,
defer it to the milestone that consumes it.** This is the mitigation from
`vocabulary-scope-risk.md` applied at project scale.

## M1 — walking skeleton

One program produces one release row through the production entry point. The
point is not the row; it is that every seam is exercised while it is still cheap
to change.

**Go.**

- Implement the run-contract code half that is documented but absent:
  `internal/shared/run_manifest.go`, `run_state.go` (lock, pipeline stage markers, part
  scan), `cache_index.go`, `parquet_writer.go`.
- The writer is the sharded part writer from `DS-50`: a unit belongs to
  `sha256(pass_key) mod journal_shard_count`, the default is 16, and
  `journal_shard_count` is part of `run_id`. `02b` stays one unit per part.
- A shard is a container, not a transaction (`DS-56`): a rejection, timeout, or
  crash is a failure row for that unit and the shard commits the rest; a shard
  with no successes writes no part.
- Implement `internal/run` `Run`, `Status`, and `List`, replacing the
  `ErrNotImplemented` returns.
- Unit identity follows `DS-50`: content, not assignment. A `03b` unit is keyed
  by the program and the graph identity, and the `03a` plan is not an input.
- Replace the freeform `dict` request and response in
  `cadqa_dataset_generator/cli.py` with typed per-pipeline-stage models as each
  pipeline stage lands. Do not design all pipeline stages' models up front.

**Pipeline stages.**

- `01a`–`01e` on a three-program fixture pool cut from
  `data/cadevolve_sources.parquet`.
- `02a`/`02b`/`02c` on the program in
  `docs/dataset/implementation/pipeline/testing/golden/box-with-hole.json`.
- `03a` emits a one-cell plan, typed from its own doc even though the allocation
  is trivial.
- `03b` is the plumbing milestone from
  `plans/nov-19/03b-task-construction-design.md`: final solid state target,
  volume answer, number format, one step, no clue search.
- `04` renders from `prompts.yaml`; `05` exports `release.parquet`,
  `failures.parquet`, `manifest.json`, the dataset card, and `support/`.
- `tools/manual-verification/render_task.py` renders the skeleton row: the final
  solid state, the prompt text, and the gold answer. It is the owner's first
  verification point and the same tool serves `M3`.

**Pass condition.** `test_pipeline_end_to_end` from
`testing/00-end-to-end.md` is written from its contract and green on the fixture
pool; a second run with the same inputs executes no unit, writes no part, and
produces byte-identical `release.parquet`; `generator status` reports the
completion marker and part counts for each pipeline stage.

**Why first.** Artifact identities, the Parquet schema across the Go/Python
boundary, the worker protocol, resume, and failure reconciliation are the
expensive things to change later. It also converts "the documents are the
deliverable" into a running binary.

## M2 — `02` depth

Started first of the two tracks.

- The coverage and rejection fixture set, which is also the support table's
  input.
- `02a`: the full allowlist, method signatures, shape derivation, and the
  CadQuery selector, CadQuery workplane, CadQuery profile, solid, and expression
  features.
- `02b`: the long-lived worker that preloads CadQuery/OCP and forks a child per
  program (`DS-49`), runtime capture, topology, states, point probes, tolerance
  handling, and failure tombstones. The child writes under `.tmp-` and the parent
  validates and renames; the 30-second limit starts at the child's ready signal.
- `02c`: graph construction and persistence, bindable-state pair emission and
  `implementation_scope` in the graph identity (`DS-52`), the capability census,
  and the fingerprint copy instead of a recompute (`DS-55`).
- Shard parts for `01d`, `02a`, and `02c`; `02b` stays one unit per part
  (`DS-50`).
- Resolve the `02b` point-probe scope: P0 binds one solid state per task, so
  decide whether probes follow the same rule before the graph is measured.

**Pass condition.** The extraction validation and graph persistence tests pass
on a 100-program slice and then the full active pool; every program either has a
graph or one failure row and the counts reconcile; per-program wall clock, CPU,
and peak memory are recorded; the graph report is comparable to the pre-rebuild
measurements (677,937 CAD graph entities and 20,135,608 CAD graph relations for
1,000 programs).

## M3 — `03b` depth

Started roughly a week after `M2`.

- The `DS-51` construction rules first: one attempt budget per (CADEvolve program
  family, task reasoning step count), one program pass per revision with the
  census from the plan, and count-based cover-search scope constants. These rules
  are what keep a 10,000-task release from becoming 10^5 cover searches.
- The clue-search milestone, then the full P0 vocabulary: comparison,
  aggregation, provenance, multiple target categories, distance, angle, region.
- Golden records per task shape, and the property tests: every accepted task is
  answer-unique under `DA-4`'s predicate, every clue narrows, and every clue is
  true of all final possible answers.
- The multiple-choice pool from the penultimate answer candidate set, under
  `MC-15`.

**Pass condition.** The golden records match; the property tests hold; the
provisional construction limits (200 candidates, 64 facts, 20,000 expansions,
64 rechecks) are measured and either confirmed or replaced; and **yield per
program is measured on 50–100 real graphs**. That number, not a schedule
estimate, decides whether 10,000 tasks are reachable, how much expansion `03c`
must do, and whether the vocabulary needs to shrink.

## M4 — `03a` and `03c`

- `03a`: quota allocation, the conditional share, the support-table derivation
  and its persisted tables, and the split assignment.
- `03c`: the seven deficit classes, the fast loop (`03a` → `03b`), the slow loop
  (`01b` → `01c` → `01d` → `02` → `03a` → `03b`), the three-round 20% stop rule,
  and the deficit ledger.

**Pass condition.** A planned release over the real pool with counts reconciled
at every pipeline stage, a deficit ledger, and one exercised slow-loop round.

## M5 — `04`, `05`, and the release contracts

- `04`: the full projection, choices, and the evaluation-namespace prompt.
- `05`: the release checks including per-split coverage and balance (`DA-6`),
  `release_id` (`DA-5`), the family-to-split registry (`DA-8`), the external
  benchmark program set and its overlap check (`MC-49`), the dataset card, and
  license attribution (`DA-9`). Confirm the typed answer columns before the first
  published release.
- The review-pack renderer and its sampled matrix, per
  [`devtools/review-pack.md`](../../docs/dataset/implementation/devtools/review-pack.md);
  `tools/manual-verification/render_task.py` and the ledger already exist from
  `M1`.
- The evaluation material and grader (`DA-2`), including the prompt-only view,
  answer parsing per format, and the tolerance semantics from `DA-4`.
- `DA-7`'s measurable shortcut-resistance proxy, or its explicit re-scope.

**Pass condition.** A release built from the real pool with every check green or
recorded as a `known_miss` with a reason; the grader scores a gold row and a
near-miss correctly; export blocks when a review-ledger cell is missing.

## M6 — first release

Tag the release revision, record the run manifest, and hand off to
`docs/development-plan.md` Phase 2. Everything after that is the existing
project plan, not this one.

## What is already done

The init milestone is nearly complete and green (`go test ./...` three packages,
`uv run pytest` 42 tests):

- `generator/main.go`, `generator/internal/run/run.go` — flags, pipeline stage selection,
  exit codes, usage;
- `generator/internal/shared/` — typed artifact tables, the failure record and
  its merge, the `balance.yaml` and `checks.yaml` loaders, the worker bridge;
- `cadqa_dataset_generator/cli.py` — the worker protocol and dispatch;
  `s01d`, `s02a`, `s02b` are stubs that raise `StageNotImplemented`;
- the test contracts for every pipeline stage, the golden record, `prompts.yaml`, and
  `tolerance.yaml`.

So `M1` is not "initialise everything"; it is the run-contract code half plus one
thin body per stage. Do not stub `03`–`05` beyond what `M1` needs: a stub package
that guesses its typed models is a second schema to maintain.

## What not to do

- **Do not harden `01` beyond the fixture pool before `M2`.** Its only consumer
  is `02`; rejection cases should be driven by real pool failures in `M2`.
- **Do not build `05`'s full check suite before `03b`.** The `superseded` bound
  logic exists because construction can make a bound impossible; the checks and
  the constructor are tuned together.
- **Do not fix `graph_schema_version` before `DS-52` is implemented.** A schema
  change after `M2` invalidates every graph and every `03b` unit.
- **Do not design all typed models in one pass.** The docs own the models; the
  code derives them one pipeline stage at a time.
- **Do not run the real pool before `M1`'s resume works.** A 12.5-hour execution
  pass without resume is a single-point failure.

## Milestone quality gates

These are the numbers that decide whether the plan still holds. Record each in
the run manifest or the milestone note.

| Quality gate | Milestone | Kills the plan if |
|---|---|---|
| Tasks per program on real graphs | `M3` | The yield cannot reach 10,000 tasks within the 20%/3-round expansion |
| Per-program execution wall clock and peak memory | `M2` | The full pool does not fit the available machine time |
| `03b` attempts per accepted task | `M3` | It exceeds the `DS-51` budget |
| Construction limits (candidates, facts, expansions, rechecks) | `M3` | The measured pass cannot fill the quota targets within them |
| Time from a program change to a new reviewable row | `M5` | It requires a full corpus rerun (`R-21`) |
| Import cost as a share of the execution budget | `M2` | It stays at 7–9% per program after `DS-49` |
