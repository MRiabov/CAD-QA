# Run contract

**Status:** draft, 2026-11-21. This document owns the run-level execution
contract: the run manifest, the run directory, incremental Parquet persistence,
completion markers, cache lookup, resume, the command-line interface, and exit
codes.

**Parent:** [`artifacts.md`](artifacts.md) owns artifact ownership, identity,
and format. [`pipeline/io-contracts.md`](pipeline/io-contracts.md) owns typed
pipeline stage I/O. This document owns how a run executes those artifacts.

**Related:** [`pipeline/extraction/graph-persistence.md`](pipeline/extraction/graph-persistence.md)
owns the `TolerancePolicy` shape; this document stores it in the run manifest.
[`failure-record.md`](failure-record.md) owns the failure row; this document owns
how the failure partition is written and resumed.

## 1. Principle: a run is incremental

A **run** is one durable execution of the dataset generator for one input
identity. A run directory is not a scratch directory that is deleted at the end;
it is the resumable state of the run.

- A **unit** is the smallest deterministic piece of work a pipeline stage
  produces. The unit is a CadQuery program for most pipeline stages and a task
  for `03b` construct task definitions and `04` render prompt and choices. Each
  pipeline stage doc names its unit.
- A **pass** is the scheduling group the orchestrator runs together. For a
  sharded pipeline stage (`01d`, `02a`–`02c`, `03b`, `04`) the pass is one
  shard. For the non-sharded stages the pass is a pipeline stage's natural
  batch: one metadata read for `01a`, one selection call for `01b`, one fetch
  batch for `01c`, one manifest for `01e`, one plan revision for `03a`, one
  control decision for `03c`, and one release for `05`. A pass processes its
  units one at a time in stable unit-key order; the unit stays the resume
  granularity.
- A **shard** is the deterministic set of units that share one Parquet part. A
  unit belongs to `sha256(pass_key) mod journal_shard_count`, so shard membership
  depends on the key and the run-level shard count, never on wall-clock time or
  on which units happen to finish together. The pass key is `raw_program_sha256`
  for `01d` and `program_sha256` for every other stage, so all tasks of one
  program land in one shard. The default `journal_shard_count` is 16, and a shard
  with no units is not written.
- A completed unit is not recomputed unless it is forced. A partially completed
  pipeline stage resumes from the units already committed.
- The durable state of a unit is its row in a **Parquet part**: the shard's rows,
  written to an immutable file. The part is the completion marker for the units
  whose rows it holds. There is no per-unit JSON checkpoint.
- A pipeline stage whose unit is as long as the flush interval uses one unit per
  part. `02b` execute CadQuery is that pipeline stage: a unit is 30 seconds and
  the default flush interval is 30 seconds.
- Unit independence: one unit's failure never fails its shard or the other units
  in it. The writer commits the units that succeeded and the failure partition
  records the rest.
- Bulk state is Parquet. JSON is limited to the run manifest, pipeline stage
  completion markers, the deficit ledger, and other small or rare control
  documents. `DS-39` measured the CAD graph as 163 MB in Parquet and 6.7 GB as
  JSON text, a 41x size ratio, and a 57x read-time difference on a 100-program
  shard. That measurement is why per-unit state is Parquet and why JSON is not
  used for progress.
- A run is deterministic: the same inputs, versions, and `journal_shard_count`
  produce byte-identical parts and the same `run_id`. A flush may write an
  incomplete shard; the complete shard replaces it, so the final part set is
  deterministic. The complete part is written in a pipeline stage's stable sort order
  (§4.1); an intermediate flush may be in completion order. A forced recompute
  that produces different bytes is a defect, not a new result.

The reason is cost. With 1,500 active programs, 30 seconds per execution, and
about 20,000 relations per program, an interrupted run without a resume rule
recomputes hours of work. Pipeline stage docs already promise retries and
cache hits; this document is the contract that makes those promises true.

## 2. Run identity and the run manifest

`run.json` is the run manifest. The orchestrator writes it once, before the
first pipeline stage, and never edits it. A changed declared input, component
version, or policy hash is a new run directory, not an edit.

`run_id` is `cadqarun:<sha256>` over the canonical JSON of the declared
identity fields: everything in the table except `run_id`, `run_number`, and
`execution_environment`. Canonical JSON is the serialization in `03b`
construct task definitions: sorted keys, no spaces, UTF-8, SHA-256 lowercase
hexadecimal. The execution environment is recorded for audit and enters the
`02b` unit identity, not `run_id`; a resume on a different machine reuses the
run directory and recomputes only the `02b` units whose environment changed.

| Field | Format | Meaning |
|---|---|---|
| `run_id` | string `cadqarun:<sha256>` | Identity of the run. |
| `run_number` | integer | Local sequence number from the directory name. Not part of `run_id`. |
| `schema_version` | integer | Run manifest schema. |
| `generator_version` | string | Declared generator version. Not derived from git. |
| `implementation_scope` | enum `p0`, `p1`, `p2` | Dataset implementation scope. |
| `external_dataset` | struct | `uri`, `revision`, `schema_version` of the CADEvolve Parquet cache. |
| `selection` | struct | `SelectionPolicy` values, including `seed`, and `policy_sha256`. |
| `plan_seed` | integer | Deterministic seed for `03a` allocate task quotas. |
| `release_seed` | integer | `RenderConfig.release_seed` for `04` render prompt and choices. |
| `journal_shard_count` | integer | Number of journal shards. A unit belongs to `sha256(pass_key) mod journal_shard_count`. Part of `run_id`; changing it is a new run. |
| `external_benchmark` | struct, nullable | `id`, `revision`, and `program_set_sha256`. Required when `05` validate and export release runs; `MC-49` owns the program set. |
| `component_versions` | struct | `metadata_reader`, `selection`, `fetcher`, `normalization`, `external_dataset_manifest_schema`, `ast_extractor`, `runtime_extractor`, `canonicalization`, `graph_builder`, `planner`, `constructor`, `deficit_controller`, `renderer`, `exporter`, `graph_schema`, `task_definition_schema`, `release_schema`, `cadquery`, `ocp`, `python`, and `go`. |
| `execution_environment` | struct | The `02b` execute CadQuery environment record: `os_arch` (for example `linux/amd64`), `timeout_seconds`, `memory_limit_bytes`, `worker_preload` (boolean), and `worker_request_limit`. It never contains a hostname, PID, container ID, kernel version, CPU model, or timestamp. Recorded for audit; enters the `02b` unit identity, not `run_id`. |
| `tolerance_policy` | `TolerancePolicy` | The six entries defined in `graph-persistence.md`. |
| `tolerance_policy_version` | integer | Policy version. |
| `tolerance_policy_sha256` | string | Hash of the canonical `TolerancePolicy` object. |
| `policy_files` | struct | `balance`, `checks`, and `prompts`, each `{version, sha256}`, and `tolerance`, `{sha256}`. The hash is the file hash; the version is the file's declared version. The tolerance policy version is the top-level `tolerance_policy_version`. |

`execution_environment` names an environment *class*, not a machine. Two hosts
with the same `os_arch`, Python, CadQuery, and OCP versions, limits, and preload
setting produce the same record, so a resume on another host reuses every `02b`
unit. A host-specific value in the record would invalidate all executions on a
move; it is a contract violation, not a tuning choice.

`run.json` is the only JSON document the orchestrator writes before the first
pipeline stage. It is small and rare, which is the exception that keeps JSON
here. The external dataset manifest, the release `manifest.json`, the deficit
ledger, and pipeline stage completion markers are separate small control
documents; the release manifest is owned by `05` validate and export release and
the [release contract](../requirements/release-dataset-contract.md), and it is
not the run manifest.

On resume, the orchestrator recomputes `run_id` from the declared inputs and
compares it with the stored value. A mismatch exits 1 and names the first field
that differs. The orchestrator does not repair a manifest in place.

## 3. Run directory

New runs live under the runs root, `--runs-root` (default `runs/`), as
`<runs_root>/run<NNNN>/`, zero-padded to four digits: `run0001`, `run0002`, and
so on. The number is the run order, not the identity. `run.json` records it as
`run_number`; `run_id` does not depend on it.

Allocation scans the runs root for `run[0-9]{4}` directories, takes the highest
number, and creates the next with an exclusive `mkdir`; a race retries the next
number. A matching-name directory without `run.json` is occupied and reported
as invalid; it is never reused. A run past `run9999` exits 1 and names the runs
root.

Allocation is serialized by `<runs_root>/.allocation.lock`, held only for the
match scan, the `mkdir`, and the `run.json` write. A stale lock from a dead PID
is removed; a live lock exits 1 and the caller retries. The per-run `lock` in
section 10 is separate.

`generator run` without `--run-dir` computes `run_id` from the declared inputs
and reuses the lowest `run_number` with the same `run_id`; it allocates a new
directory only when no match exists. `--new-run` skips the match and allocates
a new directory. `--run-dir` resumes an existing directory; its basename must
match `run[0-9]{4}` and its `run.json` must match the current `run_id`.

A pre-existing `run25` must be renamed to `run0025` before the first run; the
CLI does not recognize the two-digit name.

`<run_dir>` below is `<runs_root>/run<NNNN>/`; `<runs_root>/cache/` sits beside
the run directories.

```text
<run_dir>/
  run.json
  lock
  01a-read-cadevolve-metadata/
    parts/program-metadata.parquet
    stage.json
  01b-select-program-pool/
    parts/program-selection-<delta_id>.parquet
    stage.json
  01c-fetch-program-pool/
    parts/part-<sequence>-<sha256>.parquet
    stage.json
  01d-normalize-programs/
    parts/shard-<nn>-<sha256>.parquet
    stage.json
  01e-write-external-dataset-manifest/
    external-dataset-manifest.json
    stage.json
  02a-extract-cadquery-ast/
    parts/shard-<nn>-<sha256>.parquet
    stage.json
  02b-execute-cadquery/
    parts/<program_sha256>/
      runtime_*.parquet
    failures/<program_sha256>.parquet
    stage.json
  02c-build-cad-graph/
    parts/shard-<nn>-<sha256>/
      nodes.parquet
      relations.parquet
      measurements.parquet
    stage.json
  03a-allocate-task-quotas/
    parts/task-quota-plan-<plan_version>.parquet
    stage.json
  03b-construct-task-definitions/
    parts/shard-<nn>-<sequence>-<sha256>.parquet
    failures/shard-<nn>-<sequence>-<sha256>.parquet
    deficit-ledger.json
    stage.json
  04-render-prompt-and-choices/
    parts/shard-<nn>-<sequence>-<sha256>.parquet
    stage.json
  05-validate-and-export-release/
    failures/part-<sequence>-<sha256>.parquet
    release/<release_id>/
      release.parquet
      failures.parquet
      manifest.json
      dataset-card.md
      support/
    current -> release/<release_id>
    stage.json
```

Each directory is named after its pipeline stage doc stem. `parts/` holds the durable
Parquet parts; `failures/` holds the Parquet failure parts of a rejecting
pipeline stage. A part file name is for humans; the Parquet metadata is
authoritative.

`03c` resolve deficits is a controller, not a data writer. It has no directory
and no data artifact; its decisions are in `03b`'s deficit ledger. It re-enters
`01b`, `01c`, `01d`, `02a`, `02b`, `02c`, `03a`, or `03b` under the same resume
rules. A supplemental selection, a fetch delta, or a new plan revision is a new
part with its own identity; the previous parts remain valid for the units they
cover.

## 4. Incremental Parquet persistence

A pipeline stage writes its output as a sequence of immutable Parquet parts.
A part is a complete table fragment with that pipeline stage schema and the
rows of one or more units. A pipeline stage's logical table is the union of
its parts; readers apply that pipeline stage's stable sort order after reading
the union.

The external dataset manifest and the release directory are control and release
artifacts rather than Parquet parts. They follow the same temp-then-rename rule,
and the completion marker names them in `outputs`.

### 4.1 Write rule

A part is written to `<target>.tmp-<uuid>` in the target directory, fsynced,
renamed to `<target>`, and the parent directory is fsynced. A visible part is
complete. A `.tmp-` file is never read; startup removes it. For a multi-file part,
such as the three CAD graph tables or the release directory, write the files
under `<target>.tmp-<uuid>/` and rename the directory.

A part's Parquet key-value metadata carries:

| Key | Meaning |
|---|---|
| `cadqa.pipeline_stage` | Pipeline stage doc stem. |
| `cadqa.shard` | Shard number and count, for example `07-of-16`; absent for a one-unit part. |
| `cadqa.unit_key` | Unit key when the part holds one unit (`02b`); absent for a sharded part. |
| `cadqa.artifact_identity_sha256` | Hash of the sorted unit identities in the part. |
| `cadqa.schema_version` | Schema version of the part. |
| `cadqa.generator_version` | Declared generator version. |
| `cadqa.complete` | `true` when the part holds every row it was written for; `false` for an intermediate flush. For a rewritten shard that means every unit of the shard; for an append-only `03b` or `04` part it means every row of that revision segment. |

A shard is a container, not a transaction. Its rows carry the unit key
(`program_sha256` or `task_id`) and the unit's content identity, so a reader
recovers units without a side index. A rewritten shard is replaced on recompute:
write the new part, commit it, then remove the superseded part after the
completion marker names the new part set. A crash between the new part and the removal leaves a
stale part that the next run ignores by identity and removes.

A shard may be flushed before every unit in it is done. The rows present are
committed and complete for their units; `cadqa.complete` is `false` until the last
row the part was written for is present. A later revision of `03b` or `04`
appends a new part with a sequence suffix instead of rewriting an earlier part,
because accepted rows are immutable and a replan must not rewrite them. Resume
unions the parts and deduplicates by unit key, requiring the content identity to
agree. A shard is complete when every unit of it is present in the union of its
parts, not in any single part.

The complete part is written in a pipeline stage's stable sort order. An intermediate
flush may be in completion order, because the complete part replaces it. For an
append-only `03b` or `04` part, the sort order applies within the revision
segment; a reader sorts the union of the segments.

### 4.2 Flush rule

A pipeline stage flushes after each unit only when the unit is as long as the
flush interval and the unit is its own part; `02b` execute CadQuery is that
pipeline stage. Every other pipeline stage flushes at most every
`--flush-interval` or every `--flush-rows` rows, whichever comes first. A
sharded pipeline stage rewrites its shard part at that cadence; it never
rewrites a shard per unit. The default `--flush-interval` is 30 seconds and the
default `--flush-rows` is 10,000. A pipeline stage that holds rows for minutes
is a contract violation, not a performance tuning choice.

| Pipeline stage | Unit | Durable part | Flush trigger | Resume key |
|---|---|---|---|---|
| `01a` read CADEvolve metadata | cache read | `parts/program-metadata.parquet` | single write | Pipeline stage completion marker |
| `01b` select program pool | selection call | `parts/program-selection-<delta_id>.parquet` | single write per selection call | `delta_id` |
| `01c` fetch program pool | fetch batch | `parts/part-<sequence>-<sha256>.parquet` | per batch, at most 30 seconds | `program_id` rows |
| `01d` normalize programs | program | `parts/shard-<nn>-<sha256>.parquet`, many programs per file with a `raw_program_sha256` column | per shard, at most 30 seconds | `raw_program_sha256` rows |
| `01e` write external dataset manifest | manifest | `external-dataset-manifest.json` | single write | Pipeline stage completion marker |
| `02a` extract CadQuery AST | program | `parts/shard-<nn>-<sha256>.parquet`, many programs per file with a `program_sha256` column | per shard, at most 30 seconds | `program_sha256` rows |
| `02b` execute CadQuery | program | `parts/<program_sha256>/`, the runtime tables | per program | `program_sha256` |
| `02c` build CAD graph | program | `parts/shard-<nn>-<sha256>/`, many programs per shard with a `program_id` column | per shard, at most 30 seconds | `program_id` rows |
| `03a` allocate task quotas | plan revision | `parts/task-quota-plan-<plan_version>.parquet` | single write per revision | `plan_version` |
| `03b` construct task definitions | task | `parts/shard-<nn>-<sequence>-<sha256>.parquet` and `failures/shard-<nn>-<sequence>-<sha256>.parquet`, many task rows per file | per shard, at most 30 seconds | `task_id` rows |
| `03c` resolve deficits | control decision | no data artifact; `03b`'s deficit ledger | per decision | Plan version and accepted counts |
| `04` render prompt and choices | task | `parts/shard-<nn>-<sequence>-<sha256>.parquet`, many task rows per file | per shard, at most 30 seconds | `task_id` rows |
| `05` validate and export release | release | `release/<release_id>/` | single writer, staged directory | `release_id` |

`01d`, `02a`, `02c`, `03b`, and `04` write shard parts. `01d`, `02a`, and `02c`
rewrite the shard; `03b` and `04` append a part per revision. `02b` writes one
part per program because one execution is as long as the flush interval; a shard
would lose a whole execution on a crash. A crash in a sharded stage loses at most
the rows not yet flushed, which the flush interval already bounds. `01c` and `05`
keep their batch and release layouts.

A rejecting pipeline stage writes its failure rows to `failures/` with the same
flush rule. A failure row is a completed unit: resume does not retry it. The
failure partition is owned by [`failure-record.md`](failure-record.md).

### 4.3 Async writer

Each pipeline stage has one writer for its output directory. Compute workers put
completed units on a bounded queue; the writer owns the temp file, the fsync,
the rename, and the directory fsync. The queue is bounded at twice the pass
count. A producer waits only when the queue is full; that is the backpressure
rule, and it is the only place persistence blocks computation. Because a shard
has one pass owner (§4.5), the writer does not coordinate two producers for one
shard.

The writer commits at a pipeline stage's flush trigger (§4.2), not on every
unit. A one-unit-per-part pipeline stage (`02b`) commits at the unit boundary
because the unit is the part. It does not hold a transaction across units. On
`SIGINT`, the orchestrator stops scheduling new passes, lets each in-flight
unit finish up to the flush interval (30 seconds), or the unit's execution
timeout for `02b`, then kills any remaining child or worker. It closes the
queue, drains it, commits the last parts, writes the completion marker of a
pipeline stage only when every unit is done, releases the run lock, and exits
130. A
second `SIGINT` cancels the wait and exits 130 after committing what is already
queued. A crash loses only the units still in the
queue or in flight; the committed parts are valid.

The Go writer is a goroutine in `internal/shared/parquet_writer.go`. The Python
writer is a thread in `cadqa_dataset_generator/parquet_writer.py`. Both use the
same rule; the language boundary does not change it.

### 4.4 Unit independence

A shard is a container, not a transaction. One unit's failure never fails its
shard or the other units in it.

- A rejected unit writes a failure row and no success row. The writer continues
  with the remaining units and commits the shard.
- A unit that raises an exception or panics is recovered at the unit boundary and
  recorded as an `internal` failure. It does not unwind the shard.
- A unit that crashes a worker becomes a failure tombstone for that unit; the
  worker is replaced and the shard continues.
- A shard with no successful rows is not written. Its failure rows are the
  completion marker for its units.
- Resume reads success and failure parts together, so a failed unit is not
  retried and a successful unit is not recomputed because a sibling failed.
- A process-level failure, such as an OOM kill or `SIGKILL`, loses only the
  unflushed rows of the in-flight shards. Committed parts are valid and resume
  continues; it is not a unit failure and it does not fail the run.
- A corrupt shard is the only failure that spans units. It is an integrity error
  with a `--force` recovery, and its blast radius is that shard.

Unit independence is about a unit's data and execution. A defect in a
pipeline stage — an invalid template, a missing component, a writer that cannot
commit — is not a unit failure and stops that pipeline stage, because continuing
would write an incomplete artifact under a valid identity.

### 4.5 Concurrency

The orchestrator runs at most `--jobs` passes at a time. `--jobs` defaults to the
host's logical CPU count. A sharded pipeline stage is also capped by
`journal_shard_count`, because one pass owns one shard. `02b` execute CadQuery
adds a memory cap: the number of active passes is at most
`floor(available_memory / (memory_limit_bytes + worker_resident_bytes))`, where
`worker_resident_bytes` is measured once at startup by loading one preloaded
worker. That value is a scheduling input; it never enters
`execution_environment` or a unit identity.

| Pipeline stage | Pass | Concurrency |
|---|---|---|
| `01a` read CADEvolve metadata | metadata read | one pass; row-group reads inside the pass use up to `--jobs` workers |
| `01b` select program pool | selection call | one pass (global reduction) |
| `01c` fetch program pool | fetch batch | up to `--jobs` in-flight fetches |
| `01d` normalize programs | shard | up to `min(--jobs, journal_shard_count)` passes |
| `01e` write external dataset manifest | manifest | one pass (single writer) |
| `02a`–`02c` execute CadQuery and build graph | shard | up to `min(--jobs, journal_shard_count)` passes; `02b` adds the memory cap |
| `03a` allocate task quotas | plan revision | one pass (global allocation); family profiles may run per family |
| `03b` construct task definitions | shard | up to `min(--jobs, journal_shard_count)` passes |
| `03c` resolve deficits | control decision | one pass (serial controller) |
| `04` render prompt and choices | shard | up to `min(--jobs, journal_shard_count)` passes |
| `05` validate and export release | release | validation checks use up to `--jobs`; the release write is one pass |

A pass processes its units one at a time in stable unit-key order. A sharded
pass processes the units of its shard and does not move to another shard. The
intra-pass parallel axis named in the table (`01a` row groups, `01c` range reads,
`03a` family profiles, `05` validation checks) shares the same `--jobs` bound; it
does not multiply it.

For `01d` through `02c`, a pass processes one program at a time. Pipeline stage
`02` runs `02a`, then `02b`, then `02c` for that program before it starts the
next program in the shard (`DS-58`). `03b` processes one program and plan
revision at a time
and emits the task rows of that program. `04` processes one program at a time
and emits the task rows of that program.

A shard has one pass owner at a time. The owner produces the shard's rows, and
the writer is the only committer. `02b` has one child in flight per active shard;
the memory cap is per active pass, so the number of concurrent children is the
number of active shards.

## 5. Pipeline stage completion marker

`stage.json` is one small JSON document per pipeline stage that writes an artifact. It is
written after the writer drains and every unit is committed as a success part or
a failure part. It is never edited; a recompute writes a new marker atomically.
`03c` resolve deficits is a controller and has no marker; its decisions are in
the deficit ledger.

| Field | Format | Meaning |
|---|---|---|
| `pipeline_stage` | string | Pipeline stage doc stem. |
| `stage_identity_sha256` | string | Hash of its identity inputs. |
| `parts_sha256` | string | Hash of the sorted `(part_name, part_sha256)` pairs. `part_sha256` is the file hash, or the hash of the sorted `(file_name, file_sha256)` pairs for a multi-file part. |
| `part_count` | integer | Number of committed success parts. |
| `row_count` | integer | Total rows across the success parts. |
| `failure_parts_sha256` | string, nullable | Hash of the sorted failure part pairs; null when it rejects nothing. |
| `failure_count` | integer | Total failure rows. |
| `outputs` | struct | Pipeline stage-specific outputs, such as `release_id` or `external_dataset_manifest_sha256`. |
| `complete` | boolean | Always `true`. A marker is only written when that pipeline stage is complete. |

A pipeline stage is complete when its marker exists, its
`stage_identity_sha256` matches the current identity, and the recomputed
`parts_sha256` matches the directory. Otherwise that pipeline stage is partial
and resume reads its parts.

The marker is JSON because it is one file per pipeline stage that writes an artifact. It is
not per-unit state; a per-unit JSON checkpoint would repeat the mistake that
`DS-39` measured.

## 6. Pipeline stage identity

`stage_identity_sha256` is SHA-256 over the canonical JSON of
`{pipeline_stage, schema_version, input_hashes, component_versions,
policy_hashes}`.

The unit identity, `artifact_identity_sha256`, is the same composition with the
unit key and the upstream part hashes for that unit. The `02b` execute CadQuery
cache key is its unit identity; its composition is in
[`pipeline/extraction/cadquery/algorithm/runtime.md`](pipeline/extraction/cadquery/algorithm/runtime.md#cadquery-program-runtime-extraction-result-identity)
and is not repeated here.

### Content identity and assignment

A unit identity covers the inputs that determine the rows the unit produces. It
does not cover the scheduling inputs that decide *which* units a revision works
on. The plan's targets, the plan version, the deficit ledger, and the family
assignment decide the work list; they are not content. Hashing them into a unit
identity makes a replan invalidate every accepted row, which is the cost `03c`
exists to avoid.

For `03b` and `04`, the unit is one task and the identity is row-level:

- `03b`: `(program_sha256, graph_identity_sha256, task_definition_schema,
  constructor, construction_seed, quota_target_key)`. `quota_target_key` names
  the target the batch was filling; the same task reached through another target
  is the same row and is deduplicated by `task_id`.
- `04`: `(definition_sha256, prompt template version, prompts.yaml hash,
  release_seed, release_schema, renderer)`.

The `03a` plan part hash is not an input to either. A replan changes the work
list and leaves every accepted row valid. Shard membership is not an identity
input: a shard's hash changes when a sibling unit changes, so downstream identity
uses the unit's content identity, never the shard file hash.

| Pipeline stage | Identity inputs |
|---|---|
| `01a` | External dataset revision, cache schema version, `metadata_reader` version. |
| `01b` | `01a` part hash, canonical `SelectionPolicy` hash (including `seed`), `selection` version. |
| `01c` | `01b` selection part hash, external dataset revision, `fetcher` version. |
| `01d` | `raw_program_sha256` of the fetched text, `normalization` version. |
| `01e` | `01a` part hash, `01c` pool part hash, `01d` shard hashes, `external_dataset_manifest_schema` version. |
| `02a` | `program_sha256`, `ast_extractor` version, `canonicalization` version. |
| `02b` | The cache key in `runtime.md`: program hash, AST extraction result hash, extractor, AST extraction, runtime, and canonicalization versions, Python, CadQuery, and OCP versions, timeout, memory limit, and execution environment identifier. |
| `02c` | `ast_extraction_result_sha256`, `runtime_extraction_result_sha256`, `graph_schema` version, `graph_builder` version, tolerance policy hash, `implementation_scope`. The tuple is stored as the program's `graph_identity_sha256`. |
| `03a` | `02c` pipeline stage parts hash, `01a` metadata part hash, `01b` selection part hash, support table versions and hashes, balance policy hash, current `DeficitLedger` hash, parent plan hash, `plan_seed`, `planner` version. |
| `03b` | `program_sha256`, `graph_identity_sha256`, `task_definition_schema` version, `constructor` version, `construction_seed`, `quota_target_key`. The `03a` plan part hash is a work-list input, not identity. |
| `04` | `definition_sha256`, prompt template version, `prompts.yaml` hash, `release_seed`, `release_schema` version, `renderer` version. |
| `05` | `04` pipeline stage parts hash, `01d`, `02a`, `02b`, `02c`, and `03b` failure parts hashes, `01e` external dataset manifest hash, support table versions and hashes, prompt template version, `prompts.yaml` hash, balance policy hash, checks policy hash, external benchmark hash, `release_schema` version, `exporter` version. |

A changed input for one program invalidates that program's downstream per-program
units, not every unit of a per-program pipeline stage. A global pipeline stage
such as `05` validate and export release is recomputed as a whole. A changed
policy or component version invalidates every unit that names it. A changed
run-level input changes `run_id` and requires a new run directory.

## 7. Resume

The resume rule is:

1. Acquire the run lock.
2. Remove `*.tmp-*` files and `.tmp-*` directories under the run directory.
3. Read `run.json`; recompute `run_id`; exit 1 on a mismatch.
4. For each selected pipeline stage in dependency order:
   1. Compute `stage_identity_sha256`.
   2. If `stage.json` exists, matches the identity, and the recomputed
      `parts_sha256` matches, skip that pipeline stage unless it is forced.
   3. Otherwise read every committed part through the reader the next pipeline stage
      uses, and collect the completed unit keys from the success parts and
      the failure parts. A sharded part contributes one key per row of its unit
      key column; a one-unit part contributes its unit key. A part is complete
      when `cadqa.complete` is true; a partial part is read and completed.
   4. For each unit in its work list, skip it when its key is present and its
      content identity agrees: the unit's `artifact_identity_sha256` for a
      one-unit part, or the row's content identity for a sharded part. Otherwise
      compute it and enqueue its rows for the writer.
   5. Drain the writer and write `stage.json`.
5. Release the lock and print the summary.

A unit whose identity does not match the current identity is stale and is
recomputed. A shard is rewritten when any of its units is recomputed. For a
row-level unit (`03b`, `04`), staleness is per row: a `task_id` whose stored
content hash disagrees with the current computation is an integrity error, not a
silent rewrite, because accepted content is immutable. A part that fails to
parse, or whose metadata is missing, is an integrity error:
the run exits 1, names the file, and leaves the recovery to
`--force <pipeline stage>`. A corrupt part is replaced; a valid part is compared
byte for byte.

Each pipeline stage doc defines its work list; the table in section 4.2 names
the unit and the resume key.

Resume reads its own committed Parquet parts. It does not read
a side index, a JSON progress file, or an in-memory checkpoint.

## 8. Cache

The run directory is the primary cache: a rerun in the same directory resumes.
A shared cache is optional and is enabled by default at `<runs_root>/cache`;
`--no-cache` disables it.

- A cache entry is a directory `<cache_dir>/<pipeline_stage>/<artifact_identity_sha256>/`
  holding the same part files as the run. The directory name is the index; the
  Parquet metadata inside each file is the identity check. There is no JSON
  index.
- Lookup order is the run part, then the cache. A cache hit copies or hardlinks
  the files into the run directory and is logged. A hit must be byte-identical
  to a fresh computation; the test asserts it.
- A part is written to the cache after its run part is committed. A cache write
  is a hardlink when the cache and run directory are on the same filesystem;
  otherwise it is a copy performed off the writer's critical path. A cache write
  failure is a warning, not a run failure.
- A cache entry is immutable. A corrupt entry is removed and recomputed; the
  warning names the entry.
- The cache is not part of `run_id` or `release_id`. It is an optimization, and
  a cache miss is not a failure.
- A sharded stage caches at shard granularity. The key is the part's
  `artifact_identity_sha256`: the unit identity for a one-unit part, the sorted
  shard identity for a sharded part. A hit requires the same complete shard
  composition; a partial shard is not cached until it is complete.

`02b` execute CadQuery caches a failure tombstone like a success result; a
tombstone is a result for the same cache key.

## 9. Command-line interface

There is one binary, `generator`, built from `generator/main.go`. It calls the
`internal/run` package. The pre-rebuild `cadqa` console script was deleted with
the old generator.

```text
generator run [--run-dir <runs_root>/run<NNNN>] [flags]
generator status --run-dir <runs_root>/run<NNNN>
generator list [--runs-root <path>]
```

### 9.1 `run`

| Flag | Required | Default | Meaning |
|---|---|---|---|
| `--runs-root` | no | `runs/` | Root for new runs and for `list`. |
| `--run-dir` | no | — | Resume an existing run. Basename `run<NNNN>`; omit to reuse or allocate. |
| `--new-run` | no | false | Allocate a new run directory even when a `run_id` match exists. Incompatible with `--run-dir`. |
| `--external-dataset` | yes | — | CADEvolve Parquet cache path or URI. |
| `--external-dataset-revision` | yes | — | Expected upstream revision. |
| `--selection-policy` | yes | — | Selection policy file, including the seed. |
| `--plan-seed` | yes | — | Deterministic task quota plan seed. |
| `--release-seed` | yes | — | `RenderConfig.release_seed`. |
| `--scope` | no | `p0` | `p0`, `p1`, or `p2`. |
| `--balance` | no | `balance.yaml` | Balance policy file. |
| `--checks` | no | `checks.yaml` | Check policy file. |
| `--prompts` | no | `prompts.yaml` | Prompt template file. |
| `--tolerance-policy` | no | `tolerance.yaml` | Tolerance policy file. |
| `--external-benchmark` | conditional | — | Pinned external benchmark program set. Required when `--to` includes `05`. |
| `--external-benchmark-id` | conditional | — | Benchmark name. Required with `--external-benchmark`. |
| `--external-benchmark-revision` | conditional | — | Benchmark revision. Required with `--external-benchmark`. |
| `--from` | no | first incomplete | First pipeline stage doc stem. |
| `--to` | no | last | Last pipeline stage doc stem. |
| `--force` | no | none | Comma-separated pipeline stage stems or `all`. |
| `--jobs` | no | `NumCPU` | Maximum concurrent passes. A sharded stage is also capped by `journal_shard_count`. `02b` execute CadQuery adds the cap `floor(available_memory / (memory_limit_bytes + worker_resident_bytes))`; `worker_resident_bytes` is measured once at startup by loading one preloaded worker and is a scheduling input, never enters `execution_environment` or a unit identity. |
| `--flush-interval` | no | `30s` | Maximum interval between Parquet commits. |
| `--flush-rows` | no | `10000` | Maximum rows between Parquet commits. |
| `--shard-count` | no | `16` | Journal shards. A unit belongs to `sha256(pass_key) mod shard_count`. A sharded stage runs at most one pass per shard, so this is also its concurrency ceiling. Recorded in `run.json` as `journal_shard_count`; part of `run_id`. |
| `--cache-dir` | no | `<runs_root>/cache` | Shared cache directory. |
| `--no-cache` | no | false | Disable the shared cache. |
| `--log-level` | no | `info` | `debug`, `info`, `warn`, or `error`. |

With no `--run-dir`, `run` computes `run_id` and reuses the lowest matching
`run<NNNN>`; if none exists, it allocates the next number. `--new-run` skips
the reuse. `--run-dir` requires an existing directory whose basename matches
`run[0-9]{4}` and whose `run.json` matches the current `run_id`; a missing
directory or a `run_id` mismatch exits 2; a `run_number` mismatch exits 1 as an
integrity error. `--new-run` with `--run-dir` exits 2. A new run is never
created at an arbitrary path.

Pipeline stage selection is a contiguous range of the linear pass. A pipeline stage
before `--from` must already be complete; otherwise the command exits 2 and
names the missing prerequisite. `--force` is the only way to recompute a
complete pipeline stage. A forced unit that produces different bytes aborts the
force with exit 1 and leaves the committed part in place.

`03c` resolve deficits is a controller inside `03`; it is not selected by
`--from` or `--to`. The orchestrator runs it after `03b` and re-enters the
stages it names under the same resume rules.

`--selection-policy` is a YAML or JSON file that deserializes to
`SelectionPolicy` as defined in
[`01b` select program pool](pipeline/01b-select-program-pool.md#selection-policy);
an unknown field is a usage error. The manifest records the effective values
and the canonical hash.

### 9.2 `status`

`status` reads the run directory and prints the `run_id`, each pipeline stage's
complete or partial state, the unit counts from the part key columns, the failure
counts, and the current `release_id`. It takes no lock and is safe while a run is
active.

### 9.3 `list`

`list` scans the runs root for `run<NNNN>/run.json`, sorts by `run_number`, and
prints one line per run: run number, `run_id`, scope, external dataset revision,
status (`partial`, `complete`, or `invalid`), and release id. A matching-name
directory without `run.json` is printed as `invalid` and makes the command
exit 1. A `run_number` that disagrees with the directory name is also
`invalid`. A directory that does not match the name is ignored. `list` takes no
lock.

### 9.4 Exit codes

| Code | Meaning |
|---|---|
| 0 | Every selected pipeline stage is complete. Rejections are data and do not change the exit code. |
| 1 | Run blocked: manifest mismatch, `run_number` mismatch, missing or corrupt part, lock held, integrity error, forced recompute differs, or a blocking release check. |
| 2 | Usage error: unknown pipeline stage, invalid flag, missing required input, `--from` after `--to`, a missing prerequisite, a `--run-dir` path that is missing or has a different `run_id`, or `--new-run` with `--run-dir`. |
| 130 | Interrupted by `SIGINT`. Partial state is resumable. |

### 9.5 Logging

The binary logs with `log/slog` as JSON to standard error. It emits one line per
pipeline stage start, skip, and finish; per unit start, skip, finish, and
rejection; per flush; per cache hit and miss; and a final summary. Fields are
`run_id`, `pipeline_stage`, `shard`, `unit_key`, `event`, `duration_ms`, and
`row_count`.
There is no per-row log. The log is not an artifact.

## 10. Run lock and partial-run cleanup

Allocation treats any `run<NNNN>` directory as occupied, including one without
`run.json`; it never reuses a number. `run_number` must equal the number in the
directory name; a mismatch is an integrity error.

`lock` is a small JSON document with `run_id`, `pid`, `host`, and `started_at`.
It is created with an exclusive create. On startup:

- same host and the PID is alive: exit 1, the run is active;
- same host and the PID is dead: remove the stale lock and take it;
- different host: exit 1 and name the host. A lock from another host is removed
  only by the operator.

The lock is removed on a clean exit, on `SIGINT`, and on a blocked run. A crash
leaves a stale lock that the same host detects.

Startup removes `*.tmp-*` files and `.tmp-*` directories under the run directory.
It never removes a committed part, a failure part, or a pipeline stage marker.
A committed part without a marker is valid partial progress; a marker without
its parts is an integrity error.

`--force <pipeline stage>` recomputes every unit of that pipeline stage. It
writes the replacement parts to temp paths and compares each with the committed
part: an identical part is kept, a different part aborts the force with exit 1
and leaves the committed part in place, and a corrupt part is replaced. A
row-level stage compares its rows by `task_id` and content hash. The
pipeline stage marker is rewritten after the force. A forced pipeline stage's
failure partition is replaced, because the previous attempt's rejections no
longer describe the current output. Force is a repair and determinism check, not
a way to pick up a changed input, component version, or policy; those change
`run_id` and require a new run directory.

`05` validate and export release writes into `release/.tmp-<release_id>/` and
renames the directory to `release/<release_id>/`. `release/current` is replaced
by an atomic symlink rename. A failed `05` leaves the previous `current` and no
visible `release.parquet` in a new release directory.

## 11. Tolerance policy

The run manifest carries the `TolerancePolicy` defined in
[`pipeline/extraction/graph-persistence.md`](pipeline/extraction/graph-persistence.md#tolerance):
`millimetre`, `square_millimetre`, `cubic_millimetre`, `degree`, `radian`, and
`unitless`. The policy is read from the root `tolerance.yaml`, validated, and
copied into the manifest with `tolerance_policy_version` and
`tolerance_policy_sha256`.

`tolerance_policy_sha256` is over the canonical policy object, not the file
bytes. `policy_files.tolerance.sha256` is the file hash. A change to any entry is
a new policy version, a new `tolerance_policy_sha256`, and a new graph artifact
identity. A measurement `tolerance` of null inherits the policy entry for its
unit; a non-null value overrides it. Answer-scoring tolerance is separate and
belongs to the task definition and the release `tolerance` field.

The file has this shape:

```yaml
version: 1
policy:
  millimetre: {kind: relative, value: 1.0e-6}
  square_millimetre: {kind: relative, value: 1.0e-6}
  cubic_millimetre: {kind: relative, value: 1.0e-6}
  degree: {kind: absolute, value: 1.0e-4}
  radian: {kind: absolute, value: 1.0e-6}
  unitless: {kind: exact}
```

Validation rules:

- exactly the six units, no unknown unit and no missing unit;
- `Tolerance.kind` is `exact`, `absolute`, or `relative`;
- `exact` has null `value` and null `unit`;
- `absolute` has a non-negative `value` and the entry's unit, which is never
  `unitless`;
- `relative` has a non-negative fraction and null `unit`;
- the `unitless` entry is `exact` by default; a non-exact `unitless` entry is
  valid but is recorded in the manifest.

## 12. What is not here

- Artifact ownership, identity summary, and format: [`artifacts.md`](artifacts.md).
- Typed pipeline stage I/O: [`pipeline/io-contracts.md`](pipeline/io-contracts.md).
- Release columns and the release manifest:
  [`../requirements/release-dataset-contract.md`](../requirements/release-dataset-contract.md).
- The `TolerancePolicy` shape:
  [`pipeline/extraction/graph-persistence.md`](pipeline/extraction/graph-persistence.md#tolerance).
- The failure row and its merge:
  [`failure-record.md`](failure-record.md).
- Pipeline stage algorithms: pipeline stage docs.
