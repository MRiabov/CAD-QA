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

The replacement is specified, not built:

| Where | Holds |
|---|---|
| `docs/dataset/requirements/` | What the dataset is: PRD, terminology, task structure, prompt content, release contract. |
| `docs/dataset/implementation/` | How it is built: pipeline stage docs, IO contracts, release checks, file trees. |
| `docs/dataset/implementation/pipeline/streamlined/` | One executable "what to do" doc per pipeline stage. |
| `docs/dataset/implementation/pipeline/testing/` | One integration test contract per pipeline stage, plus fixtures and golden records. |

`docs/train-and-eval/` still describes the deleted training stack. It is kept
for the rewrite and does not describe code that exists.

## Repository layout

```text
balance.yaml          Balance policy for task quotas
checks.yaml           Release check policy
prompts.yaml          Prompt copy
cadqa_dataset_generator/   Python worker package (skeleton; stages land one per pipeline stage)
docs/dataset/         The dataset design: requirements, implementation, decisions
docs/train-and-eval/  Training and evaluation design (superseded, kept for the rewrite)
tests/                Document, contract, and golden-record tests
tools/                Repository checks
```

The Go module and the pipeline stage packages land with the first implementation
change; their tree is in
[`docs/dataset/implementation/file-trees.md`](docs/dataset/implementation/file-trees.md).

## Checks

```bash
uv run pytest -q
uv run rumdl check docs
uv run python tools/check_dont_say.py --roots docs
```
