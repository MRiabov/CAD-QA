# Old experiments

**Status:** archive, 2026-11-21. Historical experiment code kept so the runs can
be re-read and re-run when a new dataset regeneration has to be compared against
an older one. Nothing here is imported by the pipeline, run by CI, or
maintained; a fix belongs in a new experiment, not here.

The code reads its inputs and writes its outputs under `runs/`, which is
gitignored. A checkout without those directories can read the code and the
dated records under `docs/experiments/`, but cannot re-run it.

| Folder | Question it asked | Record | Input run |
|---|---|---|---|
| `multi_hop_qa_mock/` | What the full ontology clue vocabulary looks like, and which non-feature entities and relations are frequent enough to prioritize. | Its own `README.md` and `preview/`. | none; deterministic, non-LLM |
| `cq_query_scratch/` | Can a model write a CadQuery query that returns the gold answer, by task reasoning step count? | [`docs/experiments/2026-10-22-cq-query-scratch.md`](../../docs/experiments/2026-10-22-cq-query-scratch.md) | `runs/cq_query_scratch_20261022/` |
| `new_dataset_eval_scratch/` | Does the re-specified no-kernel answer task have headroom, and how does CadQuery access change it? | [`docs/experiments/2026-10-22-new-dataset-step9-eval.md`](../../docs/experiments/2026-10-22-new-dataset-step9-eval.md) | `runs/new_dataset_step9_eval_64k_20261022/` |

Plans: [`plans/oct-22/cq-query-scratch-experiment.md`](../../plans/oct-22/cq-query-scratch-experiment.md)
and [`plans/oct-22/new-dataset-eval-scratch-experiment.md`](../../plans/oct-22/new-dataset-eval-scratch-experiment.md).

## Running it

The packages are `experiments.old.<name>`; imports were rewritten when they moved
here, so a module path in an older log or plan still names the pre-move location.

```bash
uv run python -m experiments.old.cq_query_scratch.cli report
uv run python -m experiments.old.new_dataset_eval_scratch.cli report
```

`new_dataset_eval_scratch` carries its own `run_code_sandbox.py` so the
CadQuery arm does not depend on the deleted `train_and_eval/` tree.

The CadQuery-query end-to-end test needs the kernel extra and is not collected by
the default suite (`testpaths` is `tests`):

```bash
uv run --extra cadquery pytest experiments/old/cq_query_scratch/test_cq_query_scratch.py
```

## What is deliberately not here

- The `runs/` outputs: they are large, gitignored, and regenerable.
- The deleted `train_and_eval/` and `dataset/` trees; the tag
  `before-deleting-the-old-generator-and-harness` preserves them.
