# Dataset implementation decisions

**Status:** active, 2026-11-21.

Implementation decisions that span pipeline stages of the dataset generator, in ADR format
([`../../docs-conventions.md`](../../docs-conventions.md)). A decision here shapes more
than one pipeline stage: the implementation language, artifact storage, the run model,
unit identity, sharding, concurrency, and process lifetime. Requirements-level decisions
are in [`../requirements/decisions.md`](../requirements/decisions.md); decisions scoped
to one pipeline stage or module are in that step doc's `## Local decisions` or module
`decisions.md`. The decision prefix is `DS-ADR-`.

The entries are grouped: project scope, language and storage, and the run model. The
grouping is editorial; the numbers are the citation keys and never change meaning.

---

## DS-ADR-01 — P0/P1/P2 are implementation order, not task labels

- **Status:** accepted (2026-10-21); corrected (2026-10-21).
- **Context:** Priorities on requirements and generation inputs were being
  converted into a task priority. That made the release table carry a label with
  no product meaning and made the same task change priority depending on which
  inputs happened to be used.
- **Decision:** P0/P1/P2 describe the order in which requirements and generation
  inputs are implemented. A task is never labelled P0, P1, or P2. A release is
  defined by the generator scope that produced it; later releases add tasks from
  later scopes. Coverage and balance are checked against the values implemented
  by that release. A value deferred to a later scope is not a gap in the current
  release. No release column records implementation priority.
- **Consequences:** The release table has no `task_priority` column. Six or more
  task reasoning steps and P2 inputs belong to later implementation scope, not
  to a task label. The first benchmark release implements the P0 scope; later
  releases add P1 and P2 values.

## DS-ADR-02 — Go is the default implementation language

- **Status:** accepted (2026-10-21).
- **Context:** The dataset generator is mostly file, graph, coverage, and export
  work. Python is required only where CadQuery/OCP or Python semantics are
  involved. Mixing languages without a boundary would duplicate models and make
  the generator harder to operate.
- **Decision:** Go is the default for all dataset implementation work. Python is
  allowed only for work that requires the Python runtime or a Python-only
  library: CadQuery/OCP execution, Python AST or tokenizer work, and canonical
  Python program normalization. The CLI, orchestration, manifests, graph
  assembly, task enumeration, prompt and choice rendering, task quota planning,
  validation, and export are Go. The boundary is defined in
  `implementation/python-and-golang.md`; the declared libraries and toolchains
  are in `implementation/stacks.md`.
- **Consequences:** The Go entry point invokes Python workers through typed,
  versioned artifacts. Go code does not import CadQuery or OCP. Python code does
  not own release state. New Python code outside the allowed list needs a
  decision.

## DS-ADR-03 — Bulk artifacts are columnar

- **Status:** accepted (2026-10-21).
- **Context:** Per-row JSON parsing and serialization dominated CPU time, and
  row-oriented JSON artifacts add IO. Most dataset artifacts have many rows with
  a stable schema.
- **Decision:** Parquet is the default for artifacts with many rows. Use typed
  nested structs and lists for schemas that are known. Do not store bulk
  artifacts as JSONL or as one JSON string per row. JSON is limited to small
  control documents and opaque versioned payloads that cannot be typed. JSONL
  is an optional inspection export, never part of a pipeline stage or release
  contract.
  Rejections use `failures.parquet`; the release table remains `release.parquet`.
- **Consequences:** Pipeline stages exchange columnar tables, not JSON rows.
  Large tables are partitioned by program family or release where useful. The release
  artifacts are `release.parquet`, `failures.parquet`, `manifest.json`,
  `dataset-card.md`, and `support/`. Schema versions are recorded in Parquet
  metadata and the manifest.

## DS-ADR-04 — The CAD graph is an immutable Parquet artifact, not a relational table

- **Status:** accepted (2026-11-20).
- **Context:** `DS-ADR-03` makes Parquet the default for many-row artifacts, and
  `implementation/pipeline/extraction/graph-persistence.md` defines the graph as
  three Parquet tables. The open question is whether the graph should instead
  live in a relational database, where foreign keys and joins are native. The
  access pattern answers it. The graph is written once per program and never
  mutated, it is read one program at a time, and the interesting queries are
  traversals over one program's edges rather than joins across programs. A
  relational store would therefore add a server, a DDL copy of the schema, and a
  second writer without removing the cost that dominates a read: hydrating rows
  into program objects. Measured on `runs/current_cadevolve1000_10k_regen_20260613`,
  1,000 programs produce 677,937 nodes, 20,135,608 relations, and 10,205,884
  measurements. The Parquet holding them is 163 MB; the same graph as JSON text
  is 6.7 GB, a 41× ratio driven by repeated relation keys. Reading the heaviest
  100-program shard through the current JSON-in-Parquet path takes 21.0 s wall
  and 5.8 GB peak RSS, almost all of it in `json.loads`; the same rows as three
  typed tables scan in 0.37 s at 562 MB, a 57× difference.
  `tools/bench_graph_columnar.py` reproduces both numbers.
- **Decision:** The CAD graph is stored only as the Parquet tables in
  `graph-persistence.md`. No relational database is the graph store, and Postgres
  is rejected for it. Referential integrity stays a builder invariant and a
  validation gate, not a database constraint. If a relational database is added,
  it owns control-plane state only: the run registry, manifests, tolerance
  policy, deficit ledger, failures, and job queue. This decision does not choose
  an analytics store. DuckDB over the Parquet files is the default for ad-hoc
  SQL because it adds no service. ClickHouse is not adopted, and would need its
  own decision backed by a measured scan workload.
- **Consequences:** `03` reads one program's graph by `program_id`, and the
  physical partition layout stays an artifact concern in `artifacts.md`. The
  graph artifact remains the single source of truth, so no schema is duplicated
  as DDL and the artifact has exactly one writer. A relational store cannot be
  introduced on the graph path without superseding this decision. The ClickHouse
  column type mapping in `graph-persistence.md` is a compatibility note for a
  hypothetical loader, not a deployment commitment.

## DS-ADR-05 — UUID columns are written by Go and never rewritten by Polars

- **Status:** accepted (2026-11-20), corrected (2026-11-20).
- **Context:** The graph artifact stores graph-local IDs as the native UUID
  logical type, and Python also reads these tables. The two Python readers behave
  differently. Polars has no UUID data type at all: `pola-rs/polars#7175` has been
  open since February 2023 and is labelled `needs decision` as of August 2026,
  and Polars 2.1.0 has no UUID type. Verified on Polars 1.41.0: a UUID column
  reads as `Binary`, and writing it back produces `optional binary` in the
  Parquet schema, so the write drops both the `FIXED_LEN_BYTE_ARRAY(16)` physical
  column type and the UUID logical type, with no error and no change to the values.
  PyArrow does not have this problem. `pq.read_table` returns
  `extension<arrow.uuid>` from a `parquet-go` file that carries no `ARROW:schema`
  metadata, so the Parquet logical type is sufficient. `pq.read_schema` dropped
  extension types on PyArrow 24.0.0 and earlier (`apache/arrow#48254`), which the
  project no longer runs: `pyproject.toml` requires `pyarrow>=25.0`, the release
  that fixed it.
- **Decision:** UUID columns are written by Go and read by Go. A Python stage
  reads them with PyArrow and gets `pa.uuid()`, from the schema or the table. No
  Python stage rewrites a graph table, and no Polars job is on the graph path.
- **Consequences:** `02b` may emit UUID columns from PyArrow and `02c` reads them
  unchanged. A Polars round-trip of a graph table is a defect even when the
  values are correct, because both the physical type and the logical type are
  lost. A test that compares values will not catch it; the check must compare the
  Parquet schema. The Polars limitation is upstream and tracked, not something
  the graph contract works around.

## DS-ADR-06 — A run is incremental and resumable per unit

- **Status:** accepted (2026-11-21).
- **Context:** `05` validate and export release said atomic directory replacement
  was the run-level execution contract, but no such document existed.
  `graph-persistence.md` required the tolerance policy to live in the run
  manifest, and `failure-record.md` said the run manifest records versions, but
  `artifacts.md` had no run-manifest row. `02b` execute CadQuery defined a cache
  key without a cache location, a lookup rule, or a resume rule. The cost is not
  theoretical: with 1,500 active programs, 30 seconds per execution, and about
  20,000 relations per program, an interrupted run without resume recomputes
  hours of work. The alternative was a per-unit JSON checkpoint, but `DS-ADR-04`
  measured JSON text at 41x the Parquet size and 57x the read time for the CAD
  graph. A JSON progress file per unit would repeat that mistake at a smaller
  scale.
- **Decision:** A run is one durable directory with a `run.json` manifest that
  records `run_id`, generator and component versions, policy file hashes, and
  the run-level `TolerancePolicy`. New runs are allocated as
  `<runs_root>/run<NNNN>`, zero-padded to four digits; the number is local and
  excluded from `run_id`. A rerun with the same `run_id` reuses the lowest
  matching directory unless `--new-run` is given. Each pipeline stage commits
  immutable Parquet parts as units complete; the part is the unit's completion
  marker, and resume reads the committed parts and skips completed units. A unit
  is flushed when it completes, or at most every 30 seconds, asynchronously
  through one writer per pipeline stage; a sharded stage flushes its shard at
  the interval or `--flush-rows`, not per unit (`DS-ADR-10`). A completed unit is
  not recomputed unless it is forced. A forced recompute must be byte-identical;
  a difference
  is a defect. Bulk state is Parquet; JSON is limited to the run manifest,
  pipeline stage completion markers, the deficit ledger, and other small or rare
  control documents. The contract also owns the shared cache, the run lock, the
  command-line interface, the exit codes, and partial-run cleanup.
- **Consequences:** A partial run is readable and resumable; a crash loses only
  the units still in the writer queue. A changed input, component version, or
  policy is a new run directory, not an edit. A corrupt part is an integrity
  error with an explicit `--force` recovery, not a silent recompute. Downstream
  identity includes the upstream part hashes, so a changed program invalidates
  only that program's downstream units. The run manifest and pipeline stage completion
  markers are artifacts in `artifacts.md`; the full contract is
  `implementation/run-contract.md`.

## DS-ADR-07 — Unit identity is content; the plan is a work list

- **Status:** accepted (2026-11-21).
- **Context:** `run-contract.md` put the `03a` plan part hash in every `03b` unit
  identity and the `03b` part hash in every `04` unit identity. A plan revision
  therefore changed every identity, while `03a`/`03b` promised that accepted
  definitions survive a replan and `03b` skipped their `task_id`s. The two rules
  contradicted each other: one rebuilt all 10,000 definitions and prompts on
  every fast-loop replan, the other appended rows under a stale identity. The
  same mistake appeared at smaller scale in `01c`/`01d`, where a batch part hash
  named a per-program identity, and in one-row Parquet parts for cheap
  per-program units.
- **Decision:** A unit identity covers the inputs that determine its rows.
  Scheduling inputs — plan targets, plan version, deficit ledger, family
  assignment — are not identity. For `03b` and `04` the unit is a task and
  identity is row-level; a later revision appends a part
  (`<program_sha256>-<sequence>.parquet`) and resume deduplicates by `task_id`
  with a matching content hash. `01d` is keyed by `raw_program_sha256`, `02a` by
  `program_sha256`, and neither by a batch part hash. `01d` and `02a` batch many
  programs per part because a unit is milliseconds; `02b` and `02c` keep one part
  per program because a unit is an execution.
- **Consequences:** A replan changes the work list and nothing else, so the fast
  loop is actually cheap. An appended row never rewrites an accepted one. A
  changed graph invalidates that program's downstream units, not every unit of
  `03b`. A batched part can lose at most a batch of cheap work on a crash. The
  cost is a sequence suffix in the part name and a row-level dedupe step on
  resume.

## DS-ADR-08 — The run journal is fixed shards, not one file per unit or per stage

- **Status:** accepted (2026-11-21).
- **Context:** The run contract wrote one Parquet part per unit. For 1,500
  programs that is 1,500 files per program stage and 4,500 files for the
  three-table graph, about 9,000 files per run, each with footer and page
  overhead. The graph is 163 KB per program, so a per-program part is mostly
  metadata. One file per stage is not an option either: Parquet is immutable, a
  run is 12.5 hours of execution, and rewriting a 245 MB graph file on every
  flush is O(n²). Batching by flush time is also wrong: the part boundaries would
  depend on machine speed, which contradicts the byte-identical rerun rule.
- **Decision:** A part is a fixed shard: a unit belongs to
  `sha256(pass_key) mod journal_shard_count` (default 16), so membership is a
  function of the key and the run-level count. A shard is written as an
  incomplete part at the flush interval and replaced by the complete shard. `02b`
  keeps one unit per part because a unit is 30 seconds. `01d`, `02a`, `02c`,
  `03b`, and `04` shard. A shard's rows carry the unit key and content identity,
  and downstream identity uses the unit identity, never the shard hash.
- **Consequences:** A 1,500-program run writes about 16 parts per stage instead of
  1,500, and the graph writes 16 directories instead of 4,500 files. A crash
  loses at most the unflushed rows of a shard; `02b` still loses at most one
  execution. A shard rewrite on recompute is 16 MB for the graph, not 245 MB. The
  shard count is part of `run_id`, so a different layout is a new run.

## DS-ADR-09 — A unit failure never fails its shard

- **Status:** accepted (2026-11-21).
- **Context:** Sharding introduced a container that holds many units. If the
  writer treated the shard as a transaction, one rejected program or task would
  discard the successful units in the shard, and a single bad program could block
  a hundred others. The failure record already makes a rejection data, but the
  persistence rule did not say what happens to the siblings.
- **Decision:** A shard is a container, not a transaction. A rejected unit writes
  a failure row and no success row; the writer continues and commits the shard. A
  unit that crashes a worker becomes a failure tombstone; the worker is replaced.
  A shard with no successful rows is not written, and its failure rows are the
  completion marker. Resume reads success and failure parts together, so a failed
  unit is not retried and a successful sibling is not recomputed. A corrupt shard
  is the only failure that spans units, and its blast radius is that shard.
- **Consequences:** One program cannot fail its shard, its batch, or the run. The
  failure partition is the only per-unit negative state, and it is already the
  R-19 record. A corrupt shard is an integrity error with `--force` recovery, not
  a data condition.

## DS-ADR-10 — Concurrency is a bound per pipeline stage, not one global worker count

- **Status:** accepted (2026-11-21).
- **Context:** Concurrency rules were spread across `python-and-golang.md`,
  `run-contract.md#43-async-writer`, and `EX-22`/`DS-ADR-08`/`DS-ADR-09`. `--jobs`
  defaulted to `02b`'s memory formula and applied it to every pipeline stage, so
  a memory-limited host throttled cheap CPU pipeline stages to the number of
  CadQuery children it could hold. `run-contract.md#43-async-writer` also said
  the writer flushes on the unit boundary, while
  `run-contract.md#42-flush-rule` and `DS-ADR-08` flush a sharded part at the
  interval; per-unit flushes would rewrite a 16 MB shard for every program and
  reintroduce the cost `DS-ADR-08` removed. The pass was a program, but the shard
  is the persistence container, and the two were not tied together.
- **Decision:** A pass is the scheduling group; for a sharded pipeline stage
  (`01d`, `02a`–`02c`, `03b`, `04`) it is one shard. The orchestrator runs at
  most `--jobs` passes, `--jobs` defaults to the host's logical CPU count, a
  sharded pipeline stage is also capped by `journal_shard_count`, and `02b`
  adds the memory cap. The writer commits at a pipeline stage's flush trigger:
  a one-unit-per-part pipeline stage (`02b`) at the unit boundary, a sharded
  pipeline stage at `--flush-interval` or `--flush-rows`, never per unit. A
  complete part is written in a pipeline stage's stable sort order; an
  intermediate flush may be in completion order. Cache writes are hardlinks
  when possible, otherwise copies off the writer's critical path. `SIGINT`
  waits for in-flight units up to their timeout (`DS-ADR-12`).
- **Consequences:** Cheap pipeline stages no longer inherit `02b`'s memory cap.
  The shard count is both a persistence and a concurrency knob; raising it for
  more concurrency changes `run_id`. One pass owner per shard removes
  cross-worker write coordination. The per-unit flush is limited to `02b`, so
  a sharded pipeline stage does not reintroduce the O(n²) shard rewrite. The
  complete-shard sort keeps byte-identical final parts; an intermediate part
  may differ, which the contract already allows because the complete part
  replaces it.

## DS-ADR-11 — Pipeline stage 02 fuses 02a, 02b, and 02c per program within a shard

- **Status:** accepted (2026-11-21).
- **Context:** `pipeline/02-execute-cadquery-and-build-graph.md` said "each
  program runs `02a → 02b → 02c` in order; different programs run in parallel",
  while `run-contract.md` gave each sub-step its own directory, `stage.json`,
  and CLI stem, which reads as three global barriers. The reader could not tell
  whether pipeline stage 02 was one fused pipeline or three sequential
  pipeline stages, and the concurrency answer differs.
- **Decision:** Pipeline stage 02 is one fused pipeline. A shard pass processes
  its programs one at a time in stable `program_sha256` order; each program
  runs `02a`, then `02b`, then `02c`, before the next program starts. The
  per-sub-step directories, parts, and `stage.json` markers remain for resume:
  a sub-step marker is written when every shard has finished that sub-step, and
  a default resume skips `02a` for a program whose `02a` is complete. `02b`
  forks one child at a time per active shard.
- **Consequences:** A program's text, AST, and runtime result stay hot across
  the three sub-steps. The number of concurrent `02b` children is the number
  of active shards, not the number of programs. The tail is the slowest shard,
  not the slowest program; with many programs per shard the difference is
  small. A shard's sub-step outputs have one producer, so the writer needs no
  cross-worker merge for the shard.

## DS-ADR-12 — SIGINT drains in-flight units before exit

- **Status:** accepted (2026-11-21).
- **Context:** `run-contract.md#43-async-writer` said "stops scheduling new
  units, drains the queue", but a producer could push after the drain, and the
  text did not say whether an in-flight child or worker was waited for or
  killed. That is a lost-work or hung-process ambiguity.
- **Decision:** On `SIGINT`, the orchestrator stops scheduling new passes, lets
  each in-flight unit finish up to the flush interval (30 seconds), or the
  unit's execution timeout for `02b`, then kills any remaining child or worker.
  It closes the queue, drains it, commits the last parts, writes that
  pipeline stage's completion marker only when every unit is done, releases
  the run lock, and exits 130. A second `SIGINT` cancels the wait and exits 130 after
  committing what is already queued.
- **Consequences:** Ctrl-C can take up to 30 seconds but loses no completed
  work. A second Ctrl-C is immediate. A crash still loses only the units in the
  queue or in flight; the committed parts are valid.

## DS-ADR-13 — The worker protocol is a checked-in JSON Schema with generated Go structs

- **Status:** accepted (2026-11-21).
- **Context:** The Go orchestrator and the Python worker exchange small JSON
  control documents over standard input and standard output. Before this
  decision, each side hand-wrote the envelope, and the per-pipeline-stage
  payloads were free-form dicts; nothing checked that the two definitions
  agreed. The boundary is not HTTP, so an OpenAPI document would describe a
  transport the worker does not use.
- **Decision:** The JSON Schema files under `contracts/worker/v1/` are the
  language-neutral contract for the worker protocol. Pydantic classes in
  `cadqa_dataset_generator/contracts.py` are the executable authoring form, and
  `tools/contracts/export_worker_schemas.py` exports the schemas
  deterministically. Go structs are generated from the schema by
  `go-jsonschema`, pinned in `generator/internal/shared/generate.go`, and
  checked in. The envelope stays hand-written on both sides; the
  per-pipeline-stage payloads are generated. `WORKER_PROTOCOL_VERSION` in
  Python and `WorkerProtocolVersion` in Go are checked on the ready document,
  every response, and `--list-stages`. `tools/ci_cd/check-worker-contracts`
  runs in pre-commit when the contract files change; it exports with `--check`,
  regenerates the Go structs, and fails on a diff. A breaking wire change is a
  new `contracts/worker/v2/` directory and a protocol version bump; additive
  fields stay in `v1`.
- **Consequences:** One definition per document, so a change that is not
  exported or regenerated fails a check instead of drifting silently. Go structs
  are generated, not hand-maintained, while Python keeps Pydantic validation.
  The contract is JSON, not Parquet; bulk data remains Parquet (`DS-ADR-03`). No
  OpenAPI or HTTP dependency is added. A new pipeline stage contract is a schema
  file, an exporter entry, a Go generation line, and a fixture; models are still
  derived one pipeline stage at a time.
