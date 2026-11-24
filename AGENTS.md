# AGENTS.md

**Status:** active, 2026-11-21. Entry point for agents working in this
repository. It records only what an agent needs to start and to avoid breaking
the repository's contracts; every fact it names has its home in `docs/`.

## Read first

| Need | Document |
|---|---|
| How docs are written | [`docs/docs-conventions.md`](docs/docs-conventions.md) |
| Canonical reading order | [`docs/README.md`](docs/README.md) |
| Terms, and the Don't-say table | [`docs/glossary.md`](docs/glossary.md) |
| Toolchains and libraries | [`docs/dataset/implementation/stacks.md`](docs/dataset/implementation/stacks.md) |
| Which language owns which work | [`docs/dataset/implementation/python-and-golang.md`](docs/dataset/implementation/python-and-golang.md) |
| Run, CLI, and exit codes | [`docs/dataset/implementation/run-contract.md`](docs/dataset/implementation/run-contract.md) |
| Code layout | [`docs/dataset/implementation/file-trees.md`](docs/dataset/implementation/file-trees.md) |
| Developer tools | [`docs/dataset/implementation/devtools/README.md`](docs/dataset/implementation/devtools/README.md) |
| What to build next | [`plans/nov-21/dataset-implementation-plan.md`](plans/nov-21/dataset-implementation-plan.md) |

## Docs first (blocks implementation)

This repository is documentation-first: a behaviour is written down before it
is implemented, and missing or ill-defined docs block the implementation rather
than being written up afterwards. The docs take precedence over the code: they
record what should exist, not what happens to be there
([`docs/docs-conventions.md`](docs/docs-conventions.md#writing-method)).

Every changeset starts in canonical `docs/`, not only in `plans/`:

- A new or changed pipeline stage or sub-step starts as its step doc, with its
  input and output in `pipeline/00-overview.md` and a `Verification` command
  that would make it `verified`.
- The doc mirror exists before the code: the same relative path under
  `pipeline/streamlined/` and `pipeline/testing/`, the test doc naming what must
  be verified.
- The decision the change rests on is recorded at its narrowest scope, and every
  new term is in `glossary.md`.

Implement only what those docs name. Do not invent a field, a pipeline stage, or
a test that no doc describes. If the doc is silent, raise the question with the
owner and settle it in the doc before writing code; silence is not a licence to
decide in code.

Because that contract is generally followed, the docs carry the answers and the
expected contract. Read the relevant docs before the code: the step doc, its
module `decisions.md`, the IO contract in `pipeline/00-overview.md`, and
`glossary.md` for the terms. Read code afterwards, to see where and how the doc
is implemented. Code that contradicts its doc is a defect to record, not newer
truth to imitate.

## Current state

The pre-rebuild generator (`dataset/`) and its training and evaluation stack
(`train_and_eval/`) were deleted from git on 2026-11-21. The tag
`before-deleting-the-old-generator-and-harness` preserves them in history. A
checkout that predates the deletion keeps only ignored `__pycache__` directories
on disk. Do not edit, import, or recreate those trees.

The replacement is:

- `generator/` — Go module `github.com/MRiabov/CAD-QA/generator`: CLI,
  orchestrator, shared code, and one package per Go pipeline stage.
- `generator/python/cadqa_dataset_generator/` — Python worker package: the JSON worker protocol
  and one module per Python pipeline stage.

`docs/train-and-eval/` describes the deleted training stack. Treat it as design
input for the rewrite, not as documentation of existing code. The
`.agents/skills/run-experiments` skill predates the rebuild and references
`scripts/` and `configs/` that do not exist; do not treat its paths as current.

## Build and check

Run from the repository root unless stated:

```bash
(cd generator && go test -count=1 ./...)
uv run pytest -q
uv run rumdl check docs
tools/ci_cd/file-length
tools/ci_cd/fanout
tools/ci_cd/check-doc-mirror
tools/ci_cd/dont-say --ratchet tools/ci_cd/dont_say_baseline.txt \
  --names-ratchet tools/ci_cd/dont_say_names_baseline.txt
uv run pre-commit run --all-files   # after `uv run pre-commit install`
```

`go test -count=1` disables the test cache because the policy-loader tests read
the root `balance.yaml` and `checks.yaml` by path. `tests/` holds the document,
contract, and golden-record tests; Go packages keep their tests beside the code.

The file-length gate warns above 800 lines and exits non-zero above 1,200; its
policy is in
[`docs/dataset/implementation/file-trees.md`](docs/dataset/implementation/file-trees.md#file-length).

The doc-mirror gate requires every pipeline stage/sub-step contract doc to have
the same relative path under `docs/dataset/implementation/pipeline/streamlined/`
and `docs/dataset/implementation/pipeline/testing/`.

The Don't-say ratchet only improves. A change that lowers the hit count must
lower `tools/ci_cd/dont_say_baseline.txt` in the same commit; never raise the
baseline to make a check pass.

## Language boundary

Go is the default. Python is allowed only for work that needs Python execution
semantics or a Python-only CAD library: `01d` normalize programs, `02a` extract
CadQuery AST, and `02b` execute CadQuery. Convenience is not a reason to choose
Python. New Python code needs a decision in `docs/dataset/implementation/decisions.md`.

Go and Python share no process memory. Bulk data crosses the boundary as typed
Parquet tables; small control documents may be JSON. Go code does not import
CadQuery or OCP. Python code does not own release state.

## Contracts that are easy to break

- **Parquet is typed.** A struct, list, or tagged union is a Parquet struct,
  list, or nullable group, never a JSON string (`DS-ADR-03`). A new JSON column
  needs a stated reason.
- **UUIDs use the Parquet UUID logical type.** Go writes `uuid.UUID` with
  `parquet-go`; PyArrow reads it as `pa.uuid()`. Polars never rewrites a graph
  table because it drops the logical type (`DS-ADR-05`).
- **Bulk state is Parquet; JSON is control only.** The run manifest, pipeline stage
  completion markers, and the deficit ledger are the JSON exceptions.
- **A rerun is deterministic.** The same inputs, versions, and
  `journal_shard_count` produce byte-identical parts and the same `run_id`. A
  forced recompute that produces different bytes is a defect.
- **Prompt text is data.** Every LLM-facing string lives in `prompts.yaml`.
  Code selects a template ID and fills typed placeholders; neither language
  hardcodes prompt copy. A template change bumps the prompt version and hash.
- **Failures are rows.** A rejected program or task becomes a failure record,
  not a log line and not an exception that aborts the run.

## Documentation rules

- Read `docs/docs-conventions.md` before adding or editing a doc.
- One fact has one home. Link the decision; do not copy the rationale.
- Decisions live at the narrowest scope: step doc, then module
  `decisions.md`, then the feature layer (`dataset/requirements/decisions.md`
  for `DS-REQ-*`, `dataset/implementation/decisions.md` for `DS-ADR-*`), then
  `docs/development-plan.md`. There is no central `docs/adr/`.
- Cite by anchor or `path::symbol`, never by line number.
- Mark unverified claims with a status tag (`exists`, `missing`, `stale`,
  `[unverified — needs <env>]`, `[unknown]`). A status moves up only when a
  check passes.
- `P0`, `P1`, and `P2` are implementation order, not task labels (`DS-ADR-01`). A
  task is never labelled with a priority, and no release column records one.

## Repository workflow

- Do repository work in a worktree under `.worktrees/<slug>`, never in the
  primary checkout. Branch from the local integration branch (`main`) while it
  is ahead of `origin/main`; otherwise from `origin/main`.
- Commit after each completed, self-contained step. Commit locally; do not push,
  open a pull request, or run CI unless the owner asks in that conversation.
- Do not rebase. Sync by merging `origin/main` into the branch and keep the
  merge commit.
- Work lands by squash-merge into local `main`; the owner decides when. The
  durable description goes in the squash-merge commit message, because branch
  commits are discarded.
- No artifact is committed. `data/`, `runs/`, `.worktrees/`, caches, and build
  output are gitignored; manual-verification tools write under
  `runs/manual_verification/<tool>/`.
- Report every non-text artifact (screenshot, render, PDF, log, archive) with
  its full absolute path.
