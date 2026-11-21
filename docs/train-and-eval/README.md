# Training and evaluation

**Status:** superseded, 2026-11-21. The code this tree describes was deleted with
the pre-rebuild generator. The tag
`before-deleting-the-old-generator-and-harness` preserves it in history.

These documents are kept because the stack is being rewritten and the reasoning
in them is still the starting point:

- [`datasets.md`](datasets.md) — how a dataset release reaches training and
  evaluation.
- [`fine-tuning/`](fine-tuning/) — the fine-tuning plan and its decisions.
- [`evaluation/`](evaluation/) — the evaluation plan and harness.

Read them as a record of a design, not as a description of code that exists.
Where they name a module under `train_and_eval/` or `dataset/`, that module is
gone. The current dataset contract is in
[`../dataset/requirements/`](../dataset/requirements/).
