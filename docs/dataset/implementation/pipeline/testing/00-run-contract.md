# 00 run contract — execution and resume test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:** [`../../run-contract.md`](../../run-contract.md).

## Happy-path integration test (test-first, adversarial)

`test_run_contract_happy_path_adversarial` — runs the chain on a fixture pool,
interrupts it after a fixed number of units, resumes it, and asserts the run
state read back from the run directory.

**Given** a fixture pool of 12 CadQuery programs, their metadata, typed packets
for the `01c` fetch that replace the network, a temporary runs root, a fixed run
request, and a test-only execution counter. Each fixture program appends one
line to a counter file when the `02b` child process executes it. The counter is
real code, not a mock; it is how the test observes that a completed unit was not
recomputed.

**When** the test starts `generator run --runs-root <tmp>/runs` with
`--flush-interval 100ms` and sends `SIGINT` after five `02b` parts are visible.
The first run allocates `<tmp>/runs/run0001`.

**Then** assert the run directory:

- `run0001/run.json` exists, its `run_number` is 1, and its `run_id` recomputes
  from the canonical manifest body without the `run_id`, `run_number`, and
  `execution_environment` fields;
- `02b` has five committed parts under `parts/`, no `.tmp-` file is visible, and
  each part's metadata carries `cadqa.pipeline_stage`,
  `cadqa.unit_key`, `cadqa.artifact_identity_sha256`, `cadqa.schema_version`,
  `cadqa.generator_version`, and `cadqa.complete=true`;
- the `02b` pipeline stage marker is absent, and `generator status` reports `02b`
  partial with five of twelve units;
- the process exits 130.

**When** the test runs the same command again with the same runs root.

**Then** assert:

- the CLI reuses `run0001`; it does not allocate `run0002`;
- only the remaining seven programs execute; the counter has twelve lines in
  total, five from the first process and seven from the second;
- the `02b` pipeline stage marker appears with `part_count=12` and
  `row_count=12`;
- `03b`, `04`, and `05` run, and the release is written;
- a third run executes no unit, leaves the counter at twelve lines, writes no
  part, and produces byte-identical `release.parquet` and the same `release_id`.

`test_run_contract_run_directory_allocation` — a changed `release_seed` produces
a different `run_id` and allocates `<tmp>/runs/run0002`. `--new-run` with the
`run0001` request allocates `<tmp>/runs/run0003`, produces byte-identical
`release.parquet`, and keeps the same `release_id`. `generator list --runs-root
<tmp>/runs` prints `run0001`, `run0002`, and `run0003` in that order. A `run0004` directory without `run.json` is printed as
`invalid` and makes `list` exit 1; a `run0005` directory whose `run.json` has
`run_number=6` is also `invalid`; a `notes/` directory is ignored.
`--run-dir <tmp>/runs/notes` exits 2 because the basename is not `run<NNNN>`.
`--run-dir <tmp>/runs/run0002` with the `run0001` request exits 2 because
`run_id` differs. `--run-dir <tmp>/runs/run0001` resumes `run0001`.

`test_run_contract_flushes_during_a_pipeline_stage` — a fixture program sleeps
long enough to observe a part before that pipeline stage finishes. With
`--flush-interval 50ms`, a part appears while `02b` is still running, and the
compute loop starts the next program before the first flush returns. The test
asserts the part appears before the process exits and that the writer is a
separate goroutine or thread; it does not assert a wall-clock bound.

`test_run_contract_force` — `--force 02b` recomputes every `02b` unit, the parts
are byte-identical, and `03b`, `04`, and `05` are skipped because their
identities do not change. A doctored `02b` part makes the force abort with exit
1 and leaves the committed part in place. A corrupt `02b` part is replaced and
the force succeeds.

`test_run_contract_manifest_mismatch` — resuming `run0001` with `--run-dir` and
a changed `checks.yaml` changes `checks_policy_sha256`; the run exits 1 before
any pipeline stage, names the field, and writes no part. A changed
`release_seed` does the same. Without `--run-dir`, the same changed input
allocates a new run directory instead of resuming `run0001`.

`test_run_contract_partial_release` — a `05` failure leaves no `release.parquet`
in a visible release directory, the previous `release/current` symlink is
unchanged, and the failure partition names the reason.

`test_run_contract_lock` — a second process on the same run directory exits 1; a
lock with a dead PID on the same host is taken over; a lock from another host
exits 1 and names the host. Two concurrent runs with the same inputs allocate
one run directory; the loser exits 1 on the run lock and the winner continues.

`test_run_contract_exit_codes` — success is 0, a blocked run is 1, a usage error
is 2, and `SIGINT` is 130.

`test_run_contract_status` — `status` reports complete or partial per pipeline stage,
the unit counts, the failure counts, and the current `release_id`. It
reads the run directory while a run is active and takes no lock.

**TDD pin:** pins the run manifest, the per-unit Parquet part as the completion
marker, the 30-second flush rule, asynchronous persistence, the resume rule, the
force rule, the run lock, and the exit codes before the `internal/run` package
exists.

## Failure-mode tests

- `test_run_contract_corrupt_part` — a truncated part fails to parse; the run
  exits 1 and names the file; `--force <pipeline stage>` replaces it and resumes.
- `test_run_contract_stale_part` — a part with an old
  `cadqa.artifact_identity_sha256` is ignored, the unit is recomputed, and the
  stale part is removed after the new pipeline stage marker is written.
- `test_run_contract_marker_without_parts` — deleting a committed part after the
  pipeline stage marker exists makes the run exit 1 and name the part; the run
  does not silently recompute a complete pipeline stage.
- `test_run_contract_missing_prerequisite` — `--from 02b` without a complete
  `02a` exits 2 and names `02a`.
- `test_run_contract_cache_hit_is_byte_identical` — a new run directory with the
  same inputs reads the shared cache, writes the same part bytes, and executes
  no child process for a cache-hit unit.
- `test_run_contract_tolerance_policy` — a `tolerance.yaml` missing a unit, naming
  an unknown unit, giving an `absolute` entry no unit, giving a `relative` entry a
  unit, or giving an `exact` entry a value each exit 2 before any pipeline stage
  and name the entry. A valid policy is copied into `run.json` with
  `tolerance_policy_version` and `tolerance_policy_sha256`, and the hash is over
  the canonical policy object, not the file bytes.

## What this does not prove

- That the release is correct. That is
  [`05-validate-and-export-release.md`](05-validate-and-export-release.md).
- That a task is natural or well worded. That is the review gate.
- That the cache is faster. That is a benchmark, not a contract.
