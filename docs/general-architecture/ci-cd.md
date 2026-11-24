# CI/CD contract

**Status:** active — initial version, 2026-11-21. The workflow in
`.github/workflows/ci.yml` exists; it has not run on GitHub yet (`exists`, not
`verified`).

## Purpose

This is the contract for what continuous integration runs, when it runs, and
what it deliberately does not run. The aim is fast, incremental feedback: one
cheap job always runs and decides which test suites the change can reach. CI
never runs a suite the diff cannot reach; the full suite is a local command, run
when the owner needs it.

CAD-QA has no deployable service. "CD" here means the checks that keep a change
safe to keep; there is no deployment step. LLM training and GPU evaluation are
experiments, not CI jobs.

## Triggers

| Event | What runs |
|---|---|
| Pull request | The quality job, then the suites the plan selects. |
| Push to `main` | The same, for the merge diff. |

There is no scheduled or manual full run. The full suite is the local command
in "Local parity"; CI stays incremental.

A push to a feature branch does not trigger CI. Open a pull request.

The concurrency group is keyed on the pull request number or the ref, with
`cancel-in-progress: true`, so a newer push supersedes an older run.

## The quality-and-plan job

`quality-and-plan` always runs. It owns the checks that read the tree rather
than the changed lines, and it computes the plan.

1. **Markdown.** `rumdl check docs plans` against `.rumdl.toml`.
2. **Don't-say terms.** Two ratchets, prose and declared names, over
   `docs`, `plans`, `contracts`, `generator`, `tests`, and `tools`. The check
   runs `tools/dont-say-go` through the Go toolchain, so the job installs Go
   before it runs.
3. **Doc mirror.** `tools/ci_cd/check_doc_mirror.py` requires the same relative
   path under `streamlined/` and `testing/` for every pipeline stage and sub-step
   contract doc.
4. **Directory fanout.** `tools/ci_cd/check_fanout.py` requires every tracked
   directory to have at most 10 immediate subdirectories; the repository root
   has 15. The rule and its exception list are in
   [`file-trees.md`](../dataset/implementation/file-trees.md#directory-fanout).
5. **Test ownership.** `tools/ci_cd/check_test_ownership.py` admits a Python
   test only under `generator/python/tests/`, `tests/ci_cd/`, or
   `tests/manual_verification/`, and a Go test only beside a non-test `.go`
   file. The rule is in
   [`python-and-golang.md#tests`](../dataset/implementation/python-and-golang.md#tests).
6. **Plan.** `tools/ci_cd/ci_plan.py` reads the diff and writes the `go` and `python`
   outputs.

The job does not install the project environment. `rumdl` runs through `uvx`,
the Don't-say check runs through the Go toolchain, and the remaining Python
checks run through `uv run --isolated --no-project --with 'pydantic>=2.14'`, so
the job installs a few megabytes of tools instead of the project environment.

The job is a dependency of both suites. A red Markdown, Don't-say, doc-mirror,
or test-ownership check stops the suites before they spend runner minutes; that
is deliberate.

## The plan

`tools/ci_cd/ci_plan.py` classifies the changed paths into the test suites they can
reach. The script is the executable plan; the table explains the intent.

| Changed path | Go | Python | Why |
|---|---|---|---|
| `generator/python/**` | yes | yes | Python worker; the Go bridge test starts it, and `generator/python/tests/` covers the worker. |
| `generator/**` | yes | no | Go module. |
| `contracts/**` | yes | yes | Worker contract documents; the Python validator and the generated Go types both read them. |
| `tests/**` | no | yes | Root tests: the CI/CD gates. |
| `tools/**` | no | yes | Python CI gates and devtools, and their tests. |
| `docs/dataset/implementation/pipeline/testing/**` | yes | no | Oracle and golden records are read by Go stage tests. |
| `docs/**`, `plans/**`, `specs/**`, `experiments/**`, `.agents/**` | no | no | The quality job still runs the docs checks. |
| Root Markdown files, `.gitignore`, `.rumdl.toml`, `.pre-commit-config.yaml` | no | no | The quality job still runs. |
| `generator/config/**` | yes | no | Generator policy and prompt inputs; the Go loaders and their tests read them. |
| `pyproject.toml`, `uv.lock`, `.python-version` | yes | yes | Both environments. |
| `.github/workflows/**` | yes | yes | The CI definition. |
| Unknown, empty, or unreadable diff | yes | yes | Fail open. |

Every row also runs the quality job; the two columns are the test suites only.

The classification fails open. A path no rule claims, an empty diff, or a diff
that cannot be read wakes every suite. Skipping a suite that should have run is
the expensive mistake; running one that need not have is the cheap one. A new
top-level path therefore costs a full run until the table learns about it.

The classifier is tested in `tests/ci_cd/test_ci_plan.py`, including the unknown-path
and empty-diff cases. That is the part a glob filter cannot express: an
unmatched path would silently skip every suite.

## Test suites

Path scoping lives in job-level `if:` conditions, never in workflow-level
`paths:`. A job skipped by a job-level `if:` reports `skipped`, which GitHub
counts as successful for required checks. A workflow that never starts leaves
its checks pending, which would block a pull request that legitimately does not
need that suite.

### Go

```bash
cd generator
test -z "$(gofmt -l .)"
go vet ./...
go test -count=1 ./...
```

`-count=1` is deliberate. The policy tests read `balance.yaml`, `checks.yaml`,
and `tolerance.yaml` from `generator/config/`, and Go's test cache does not
track those reads. The build cache still works.

The Go job installs the `worker-bridge` dependency group, not the full
environment. `generator/internal/shared/python_worker_test.go` starts
`cadqa_dataset_generator.worker` as a child process, and that worker imports only
`orjson` and `pydantic`. The group is 8 MB; the full environment is 2.3 GB.

### Python

```bash
uv sync --frozen --no-default-groups --group test
uv run --frozen --no-sync pytest -q
```

`--frozen` makes the lockfile authoritative; CI never re-resolves. The explicit
sync followed by `--no-sync` separates the install from the test, so a slow run
is attributable.

CI installs the base dependencies and the `test` group, not the local `dev`
group. The `dev` group carries mypy, ruff, pre-commit, and the experiment
drivers (`hf`, `vastai`, `kaggle`); the suite needs pytest and the worker's
runtime, nothing else. The result is about 359 MB; the full `dev` environment is
about 644 MB, and the kernel extra takes it to about 2.3 GB.

The CAD kernel is the `cadquery` extra, not a base dependency. The current
tests do not import it, and CI does not install it. Only pipeline stage `02b`
imports it. When the `02b` integration test lands, the `pipeline` suite installs
`--extra cadquery`; the current suite stays the lean `contract` suite.

The base dependencies still include pyarrow and polars (about 335 MB of the
359 MB) because the Python worker's pipeline stages read and write Parquet. That
is the worker's runtime, not a test-only convenience.

The uv cache makes the install about 1 s warm; only a lockfile change pays the
cold download.

### One suite per language

Do not split unit and integration tests yet. The suites take 1-2 s; a split
would add a second checkout, toolchain setup, and cache restore to save at most
a second of test time.

Split a suite when one of these is true:

- its warm wall clock exceeds about 2 minutes;
- part of it needs a resource the rest does not (CadQuery or OCP, network, a
  large fixture, a service, a GPU);
- part of it is flaky and would block the fast feedback loop;
- the split lets the fast part install a materially smaller environment.

Then split by requirement, not by the word "unit": a `contract` suite with no
CadQuery and no fixtures, and a `pipeline` suite with the real kernel, Parquet,
and the end-to-end test. The `pipeline` suite adds `--extra cadquery`; the
`contract` suite stays on the base environment. The testing strategy already
makes the `pipeline` suite the real one. The split will be forced by
pipeline stage `02b`, not chosen for symmetry.

Mechanisms when the split lands: Go build tags on integration test files
(`//go:build integration`) or `testing.Short()`; pytest markers with
`--strict-markers` and `-m "not pipeline"`. Do not move files into new
directories just to name the split.

## Caching

`astral-sh/setup-uv` caches the uv cache directory. The key hashes the files
matched by `cache-dependency-glob`; a changed lockfile or Python version
produces a new key.

| Job | `cache-dependency-glob` | `cache-suffix` |
|---|---|---|
| `quality-and-plan` | `pyproject.toml`, `uv.lock`, `.python-version`, `.pre-commit-config.yaml`, `.rumdl.toml`, `.github/workflows/ci.yml` | `quality` |
| `go` | `uv.lock`, `.python-version` | `worker-bridge` |
| `python` | `uv.lock`, `.python-version` | `tests` |

The suffix is the per-job cache prefix. Two jobs that install different
dependency sets from the same lockfile must not share a key: the GitHub cache is
immutable, and the second save of an existing key fails with HTTP 409. The
suffix prevents that race.

`cache-python: true` also caches the managed Python 3.12 installation.
`.python-version` is the one home for that version.

The cache is branch-scoped: a pull request restores from the base branch but
writes its own entry. The caches here are small enough that no cache-warm
workflow is part of this contract.

`actions/setup-go` caches the module cache and the build cache, keyed on
`generator/go.sum`. A cold build cache compiles the Parquet dependency tree
(about 22 s locally); a warm one runs the suite in about 1 s.

Not cached: `runs/`, `data/`, other gitignored runtime state, test results, and
the `.venv`. The uv cache is the shared layer.

## Runtime budget

Measured locally on 2026-11-21. CI numbers are `[unverified — needs a GitHub
run]`.

| Job | Warm | Cold | Target |
|---|---|---|---|
| `quality-and-plan` | about 2 s of checks | tools only | under 60 s |
| `go` | 1.2 s | 21.7 s (empty build cache) | under 90 s |
| `python` | 1.6 s | install dominates; `[estimated]` 15-45 s | under 90 s |

A job that exceeds its target by 2x is a signal to split it or move the slow
part to a local run. Do not add coverage upload, a version matrix, or a service
container without a decision in this document.

## Required checks

Require `quality-and-plan`, `go`, and `python` in branch protection. A suite
that the plan skips reports `skipped`, which GitHub counts as successful, so a
documentation-only pull request is not blocked by a Go check that did not run.

There is no aggregator job. The three job names are the checks. If only the
quality job is required, a Go or Python failure would not block a merge, so
require all three.

## Local parity

```bash
uv run pytest -q
cd generator && go test -count=1 ./...
uv run rumdl check docs plans
uv run python -m tools.ci_cd.check_fanout
uv run python -m tools.ci_cd.check_test_ownership
uv run python tools/ci_cd/check_dont_say.py \
  --ratchet tools/ci_cd/dont_say_baseline.txt \
  --names-ratchet tools/ci_cd/dont_say_names_baseline.txt
uv run python -m tools.ci_cd.ci_plan --base origin/main --head HEAD
```

The pre-commit hooks cover the Markdown and Don't-say checks. The last command
shows the plan for a local branch without running the suites. CI is a second
opinion, not the first.

## Placement

This document lives at `docs/general-architecture/ci-cd.md`, matching the other
repositories. CI is cross-cutting: it applies to every feature and owns no
single feature's pipeline stage. The folder is the home for engineering
contracts of that shape; a release process or a local-environment document
would join it rather than sit at the top level.

## Decisions

### CI-D1 — One quality-and-plan job gates conditional suites

**Status:** accepted, 2026-11-21.

**Context.** Three path-filtered workflows would duplicate the path lists and
leave required checks pending when a workflow does not start. The owner's other
repositories use one always-on quality job that also decides what to run.

**Decision.** One `ci.yml`. `quality-and-plan` always runs and owns the fast
checks; `go` and `python` depend on it and use job-level `if:` conditions.

**Consequences.** One place computes the plan, and a red quality check stops the
suites instead of running alongside them. The quality job pays a checkout and a
tool install on every change, including a Go-only change; that is a few seconds
of checks plus setup, and it buys the single status and the plan.

### CI-D2 — The plan is a typed script that fails open

**Status:** accepted, 2026-11-21.

**Context.** `dorny/paths-filter` is declarative, but a path that matches no
filter silently selects no suite. A new top-level directory would then pass CI
without either suite running.

**Decision.** `tools/ci_cd/ci_plan.py` classifies paths with a typed `JobPlan` and a
`match` table. An unknown path, an empty diff, or an unreadable diff returns the
all-true plan.

**Consequences.** The classifier is unit-tested and the fail-open rule is
explicit. A new top-level path costs a full run until the table learns about it.
The mapping is code rather than YAML, so it is reviewed like code.

### CI-D3 — The Go job installs only the worker-bridge group

**Status:** accepted, 2026-11-21.

**Context.** The Go bridge test starts the Python worker. The worker imports
`orjson` and `pydantic`; the kernel extra adds CadQuery, OCP, and vtk (about
1.9 GB, 2.3 GB with the rest of the environment).

**Decision.** `pyproject.toml` declares a `worker-bridge` dependency group with
the worker's import surface. The Go job runs
`uv sync --frozen --only-group worker-bridge`.

**Consequences.** The Go job installs 8 MB instead of 2.3 GB. The group is a
second declaration of two dependencies; if the worker grows an import, the Go
job fails and the group is updated. That failure is the intended signal, not a
surprise.

### CI-D4 — CadQuery is an extra, not a base dependency

**Status:** accepted, 2026-11-21.

**Context.** `cadquery` was listed both in the base dependencies and in the
`cadquery` extra. Its dependency tree (vtk, casadi, OCP, scipy, matplotlib) is
about 1.9 GB, and only pipeline stage `02b` imports it.

**Decision.** Keep the kernel in the `cadquery` extra and remove it from the
base dependencies. The default install is the worker, the CLI, and the tests;
the full generator uses `uv sync --extra cadquery`.

**Consequences.** The CI environment drops from 2.3 GB to about 359 MB; the
default `dev` environment is about 644 MB. A pipeline stage that needs the
kernel must install the extra; pipeline stage `02b` does so in the `pipeline`
suite. The language-boundary doc already scopes the kernel to `02b`, so this
makes the package match the documented boundary.

### CI-D5 — No unit/integration split yet

**Status:** accepted, 2026-11-21.

**Context.** The testing strategy requires integration tests with the real
kernel. The current suites are contract tests and run in seconds.

**Decision.** Keep one suite per language until a split criterion in "One suite
per language" is met.

**Consequences.** The suite names stay simple. The split is a future decision
with explicit triggers, not a guess made now.

### CI-D6 — Pin the runner image

**Status:** accepted, 2026-11-21.

**Context.** `ubuntu-latest` moved between 24.04 and 26.04 during 2026, which
changed the installed toolchains between runs.

**Decision.** All jobs use `ubuntu-24.04`.

**Consequences.** A runner upgrade is a deliberate change with a visible diff.
Revisit when 26.04 is validated.

## Open questions

- **Q2.** Should the Go suite add `-race` now? The run orchestrator will be
  concurrent; the current code is not. (Current: no, add it when `internal/run`
  starts goroutines.)
- **Q3.** Python lint is not wired. `ruff check` fails on one tracked file
  (`generator/python/cadqa_dataset_generator/worker.py`, TRY004) and
  `ruff format --check` wants three files; `mypy` fails on the gitignored
  `runs/` tree and on the `tools/ci_cd/check_dont_say.py` module name. Wire it
  into the quality job after the tree is clean.
- **Q4.** Should `README.md` and the other root Markdown files be linted?
  `rumdl`'s include is `docs/` and `plans/` only.
- **Q5.** Workflow lint is not wired.
  `uvx --from actionlint-py actionlint .github/workflows/ci.yml` passes today;
  add it to the quality job when the workflow grows.

## Resolved questions

- **Q1.** Should the scheduled full run be weekly, or is a full run on every
  push to `main` cheap enough? (Current: weekly.)
  **Resolved 2026-11-21:** no scheduled or manual full run. CI runs on pull
  requests and pushes to `main` only, and stays incremental; the owner runs the
  full suite locally when needed.
