# CAD-QA

CAD-QA is a benchmark of questions about CadQuery programs. Each task shows a
CadQuery program, a target, a set of task clues, and one answer. In the P0
setting the LLM model answers without access to CadQuery, OpenCascade, or any
other CAD kernel: the program text is the evidence, and the answer is checked
against a known answer.

The dataset is a training dataset and a separate evaluation benchmark for LLMs
that read CadQuery programs and reason about the three-dimensional shapes those
programs produce. See
[`docs/dataset/requirements/PRD.md`](docs/dataset/requirements/PRD.md) for what
a user gets from it.

## Status

The pre-rebuild dataset generator (`dataset/`) and its training and evaluation
stack (`train_and_eval/`) were deleted on 2026-11-21. They produced a benchmark
that no longer matched the requirements, and their release validator rejected
their own rows. The tag `before-deleting-the-old-generator-and-harness`
preserves them in history.

The replacement is specified and scaffolded:

| Where | Holds |
|---|---|
| `docs/dataset/requirements/` | What the dataset is: PRD, terminology, task structure, prompt content, release contract. |
| `docs/dataset/implementation/` | How it is built: pipeline stage docs, IO contracts, release checks, file trees. |
| `docs/dataset/implementation/pipeline/streamlined/` | One executable "what to do" doc per pipeline stage. |
| `docs/dataset/implementation/pipeline/testing/` | One integration test contract per pipeline stage, plus fixtures and golden records. |
| `generator/` | Go module: CLI, run-contract flags and exit codes, shared Parquet/policy/worker code. |
| `generator/python/cadqa_dataset_generator/` | Python worker package: JSON worker protocol and one module per Python pipeline stage. |

The Go module and the Python worker package build and test. `generator run`
validates its flags and returns the run-contract exit codes; run orchestration
and every pipeline stage are still TODOs. The intended tree is in
[`docs/dataset/implementation/file-trees.md`](docs/dataset/implementation/file-trees.md).

### Bootstrap TODOs

- `internal/run`: run directory allocation, `run.json`, run lock, pipeline stage
  loop, `status`, and `list`.
- `internal/shared`: `parquet_writer.go`, `run_manifest.go`, `run_state.go`, and
  `cache_index.go`.
- Python pipeline stages: `01d`, `02a`, and `02b`.
- Go pipeline stages: `01a`, `01b`, `01c`, `01e`, `02c`, `03a`, `03b`, `03c`,
  `04`, `05`, and the end-to-end test.

`docs/train-and-eval/` still describes the deleted training stack. It is kept
for the rewrite and does not describe code that exists.

## Repository layout

```text
balance.yaml          Balance policy for task quotas
checks.yaml           Release check policy
prompts.yaml          Prompt copy
generator/            Go module: CLI, orchestrator, shared code, pipeline stage packages
generator/python/cadqa_dataset_generator/   Python worker package (skeleton; stages land one per pipeline stage)
docs/general-architecture/  Cross-cutting engineering contracts (CI/CD)
docs/dataset/         The dataset design: requirements, implementation, decisions
docs/train-and-eval/  Training and evaluation design (superseded, kept for the rewrite)
tests/                Document, contract, and golden-record tests
tools/                Repository checks
```

## Checks

```bash
cd generator && go test -count=1 ./...
uv run pytest -q
uv run rumdl check docs
uv run python tools/ci_cd/check_dont_say.py --ratchet tools/ci_cd/dont_say_baseline.txt \
  --names-ratchet tools/ci_cd/dont_say_names_baseline.txt
```

CI runs these incrementally: a `quality-and-plan` job always runs the Markdown
and Don't-say checks, then starts only the suites the change can reach. See
[`docs/general-architecture/ci-cd.md`](docs/general-architecture/ci-cd.md) for
the path mapping, the caches, and the runtime budget.

`go test -count=1` disables Go's test cache because the policy-loader tests read
the root `balance.yaml` and `checks.yaml` by path.
