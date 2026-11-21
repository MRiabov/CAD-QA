# Dataset implementation plan — 2026-11-21

**Status:** working plan, updated 2026-11-21 against commit `ef3ac58`.

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
| `P0-W6` | R-1–R-10, R-13, R-14, R-17–R-19 | Rendering, validation, and the release contracts: `04`, `05`, the grader, the review pack and its absence frames | A release built from the real pool, validated, with every miss recorded as a `known_miss` |
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

No code. Each item is a small edit to one owner document, scheduled here because
the code that would otherwise encode the wrong answer is `P0-W2` or `P0-W3` work.

| Item | Owner | Why it cannot wait |
|---|---|---|
| `DA-4` / `MC-53` — one answer-equivalence relation | `03b`, `DS-REQ-15`, `release-dataset-contract.md` | `03b` uniqueness and the grader must be the same predicate, or a task passes construction and fails scoring |
| `MC-22` / `DA-15` — `geometry_required` for one-step tasks | `03b`, `checks.yaml`, `task-structure.md` | Changes what `03a` plans and what `05`'s 95% check counts |
| `DA-7` — the R-5 shortcut-resistance proxy, or its re-scope | `03b`, `checks.yaml`, `prompt-content.md` | R-5 is P0 and no construction rule or check measures it |
| `DA-13` / `MC-44` — support-table derivation and fixtures | `task-step-support.md`, `testing/00-support-tables.md` | `03a` cannot run without the derivation; the fixtures are programs, so they are `P0-W3` work |
| `DA-5` — `release_id` inputs | `release-dataset-contract.md`, `artifacts.md` | The manifest writer in `P0-W2` should record the final field set |
| Review frames: absence and residual, ledgers scoped to a pipeline stage | `devtools/review-pack.md`, `05` | The merged pack samples release rows only; partial extraction loss and unknown unknowns have no review frame |
| Failure disposition: `by_design`, `corpus_defect`, `extractor_gap` | `failure-record.md`, `validation.md` | Every rejection is equally legitimate today, so an extractor gap is indistinguishable from a corpus limitation |
| Extraction capability coverage check | `checks.yaml`, `release-checks.md` | A must-extract capability with zero accepted graphs is a silent deficit, not a release failure |

The performance findings `PA-1`–`PA-14` are closed in `ef3ac58`: `EX-22` to
`DS-ADR-09` and the run-contract rewrite carry them. Their implementation is `P0-W2`,
`P0-W3`, and `P0-W4` work; the plan schedules that work, not the decision.

Already closed: `DA-1` by `run-contract.md`, and `DA-3`'s data path by the
review-pack ledger in `01578d8`; the renderer is `P0-W6` code, not a `P0-W1` gap.
The graph completeness contract and the extraction-graph oracle format are
written; their implementation and the verified oracle set are `P0-W3` work.

Deferred, and deliberately not closed in `P0-W1`:

| Item | Lands in | Reason |
|---|---|---|
| `DA-2` evaluation material and grader | `P0-W6` | It is a deliverable, not a generator input; the prompt-only view is `04`'s projection |
| `DA-6` per-split coverage and balance | `P0-W6` | The checks are `05` code and their bounds depend on what `03b` can construct |
| `DA-8` family-to-split registry | `P0-W6` writer, `P1-W3` reader | The writer must exist before the first release; only the second release reads it |
| `DA-9` license and attribution | `P1-W4` | Publication blocker, not a first-release blocker |
| `MC-49` external benchmark program set | `P1-W2` | R-16 is P1; `05` owns the overlap check and the manifest fields |
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
- Replace the freeform `dict` request and response in
  `cadqa_dataset_generator/cli.py` with typed per-pipeline-stage models as each
  pipeline stage lands. Do not design all pipeline stages' models up front.

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
  `failures.parquet`, `manifest.json`, the dataset card, and `support/`.
- `tools/manual-verification/render_task.py` renders the skeleton row: the final
  solid state, the prompt text, and the gold answer. It is the owner's first
  verification point and the same tool serves `P0-W4`.

**Pass condition.** `test_pipeline_end_to_end` from
`testing/00-end-to-end.md` is written from its contract and green on the fixture
pool; a second run with the same inputs executes no unit, writes no part, and
produces byte-identical `release.parquet`; `generator status` reports the
completion marker and part counts for each pipeline stage.

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
  and the fingerprint copy instead of a recompute (`DS-ADR-08`).
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
- The rejection contact sheet and the absence review: every rejected program gets
  an oracle render, its failure reason, and a disposition.
- The residual random sample: programs drawn uniformly from the pinned pool, sized
  by the `3/p` rule, run through the oracle differential.

**Pass condition.** The extraction validation and graph persistence tests pass
on a 100-program slice and then the full active pool; every program either has a
graph or one failure row and the counts reconcile; per-program wall clock, CPU,
and peak memory are recorded; the graph report is comparable to the pre-rebuild
measurements (677,937 CAD graph entities and 20,135,608 CAD graph relations for
1,000 programs); the completeness report has no unexplained missing, orphan, or
unclassified row, and every must-extract capability has a verified oracle.

## P0-W4 — `03b` depth

Started roughly a week after `P0-W3`.

- The `TG-10` construction rules first: one attempt budget per (CADEvolve program
  family, task reasoning step count), one program pass per revision with the
  census from the plan, and count-based cover-search scope constants. These rules
  are what keep a 10,000-task release from becoming 10^5 cover searches.
- The clue-search milestone (`03b-M2`), then the full-vocabulary milestone
  (`03b-M3`): comparison, aggregation, provenance, multiple target categories,
  distance, angle, region. This is the P0 vocabulary; the P2 extras stay out.
- Golden records per task shape, and the property tests: every accepted task is
  answer-unique under `DA-4`'s predicate, every clue narrows, and every clue is
  true of all final possible answers.
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
  and its persisted tables, the split assignment, and the warmup label.
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
  the dataset card, and the answer-column review.
- The review-pack renderer and its sampled matrix, per
  [`devtools/review-pack.md`](../../docs/dataset/implementation/devtools/review-pack.md);
  `tools/manual-verification/render_task.py` and the ledger already exist from
  `P0-W2`.
- The review pack's absence and residual frames, and the release gate that
  requires every upstream stage ledger to be clean, so an open extraction gap
  blocks export even when the release rows look complete.
- The `extraction_capability_coverage` check: a must-extract capability with zero
  accepted graphs fails the release.
- The evaluation material and grader (`DA-2`), including the prompt-only view,
  answer parsing per format, and the tolerance semantics from `DA-4`.

**Pass condition.** A release built from the real pool with every P0 check green
or recorded as a `known_miss` with a reason; the grader scores a gold row and a
near-miss correctly; export blocks when a review-ledger cell is missing.

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
| R-5 no trivial shortcuts | `P0-W1`, `P0-W4`, `P0-W6` |
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
| `P0-W2` | The skeleton row: does the prompt read as a question, and is the answer defensible? This is the first point at which the wording pipeline can be judged. | `render_task.py` on the skeleton row, plus a `pass` or `defect` row in the review ledger | ~15 min |
| `P0-W2` | The box-with-hole extraction-graph oracle: do the nodes, incidence relations, and measurements match the program? Set `verified` and name the reviewer. | `oracles/extraction-graph/box-with-hole.json` | ~30 min |
| `P0-W3` | The rotated-box oracle and the first capability-cell oracles; the completeness report exceptions; the rejection contact sheet. This is the check that a supported capability did not silently disappear. | oracle records, completeness report, contact sheet | ~2–3 h |
| `P0-W4` | The quality gate before scale: 15–30 constructed definitions on real graphs, across clue types and answer meanings, plus the yield number. This is where ambiguous wording is cheapest to fix. | a `render_task.py` sample and the yield report | ~1–2 h |
| `P0-W5` | The deficit ledger: accept or reject each miss and each expansion round. `known_misses` is an owner decision. | deficit ledger and plan | ~30 min |
| `P0-W6` | The blocking review gate: every required sampling cell has a current `pass`; a `defect` blocks the export. Dataset card sign-off. | review pack and ledger | per the sampling matrix |
| `P0-W6` | The absence and residual frames: is each absence legitimate, and does the random pool sample contain an unexplained miss? | absence and residual ledgers | per the sampling policy |
| `P0-W7` | Release sign-off: manifest, dataset card, `known_misses`, `release_id`. | release directory | ~1 h |
| `P1-W1` | The PRD section 6.1 release gate per tier: 30 tasks reviewed, or every task. | review pack and ledger | per tier |

- `P0-W2` and `P0-W4` are cheap, and they are where wording defects are fixed
  while the prompt copy and the constructor are still moving. Do not defer
  wording review to `P0-W6`: a defect there costs a re-render, a new
  `prompt_sha256`, and a fresh review of that cell.
- The review ledger is written from `P0-W2` on, so no owner judgement is
  throwaway. `tools/manual-verification/render_task.py` and the ledger are the
  first-release fallback in
  [`devtools/review-pack.md`](../../docs/dataset/implementation/devtools/review-pack.md);
  the sampled pack with the full matrix lands in `P0-W6`.
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

The scaffold is nearly complete and green (`go test ./...` three packages,
`uv run pytest` 47 tests):

- `generator/main.go`, `generator/internal/run/run.go` — flags, pipeline stage selection,
  exit codes, usage;
- `generator/internal/shared/` — typed artifact tables, the failure record and
  its merge, the `balance.yaml` and `checks.yaml` loaders, the worker bridge;
- `cadqa_dataset_generator/cli.py` — the worker protocol and dispatch;
  `s01d`, `s02a`, `s02b` are stubs that raise `StageNotImplemented`;
- the test contracts for every pipeline stage, the golden record, `prompts.yaml`, and
  `tolerance.yaml`;
- the graph completeness contract, the extraction-graph oracle format and two
  `proposed` records, and the oracle builder.

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
