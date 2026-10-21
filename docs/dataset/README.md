# CAD-QA dataset

**Status:** re-specified from first principles, 2026-10-21. The previous
dataset documentation is archived under
`docs/_archive/dataset-pre-rebuild-2026-10-21/` and is not a specification.

This directory defines what the CAD-QA dataset is for, what a user gets from
training and evaluating on it, and the concepts needed to describe a task.
The technical specification is not written yet.

## Why the product comes first

The previous dataset grew from a mixture of good ideas, inherited names, and
implementation-first decisions. The result was hard to explain to a user and
hard to check against its own claims. This rewrite starts with the user outcome:
what the dataset must let an LLM do, what a reviewer must be able to check, and
what the dataset must contain. The implementation is chosen after that.

The order is:

1. Define what the user gets and what the dataset must contain.
2. Agree on the words used to describe it.
3. Write the technical specification.
4. Build the smallest complete sample.
5. Produce the first dataset release.

Steps 1 and 2 are in this directory. The technical specification is not written
yet.

## Documents

| Document | What it defines |
|---|---|
| [`PRD.md`](PRD.md) | What the user gets, what the dataset must contain, quality promises, size, splits, deliverables, and priorities. |
| [`task-structure.md`](task-structure.md) | The dimensions of a task, P0/P1/P2 priorities for generation inputs, coverage and balance at every task reasoning step count, clue types, answer meanings, task reasoning step count rules, and uniqueness rules. |
| [`prompt-content.md`](prompt-content.md) | What the LLM model sees: program text, question, task clues, choices, and answer instruction. |
| [`release-dataset-structure.md`](release-dataset-structure.md) | Release artifacts, row counts, task-file and answer-data columns, and why one physical file is not enough. |
| [`graph-content.md`](graph-content.md) | The graph elements the tasks rely on: graph entities, relations, measurements, states, evidence, and P0/P1/P2 priorities. |
| [`terminology.md`](terminology.md) | Proposed terms, replacements for old terms, and naming decisions that still need owner approval. |
| [`decisions.md`](decisions.md) | Feature-wide dataset decisions in ADR format. |

## Relation to the project PRD

[`../PRD.md`](../PRD.md) remains the authority for the research questions,
hypotheses, and evaluation goals. This dataset PRD is subordinate to it: it
defines the dataset those goals need, and it does not change the goals.

## Archived material

The archive is history, not current requirements. It contains the old dataset
documentation, the old answer notes, the old decisions, and the old issue
register. Details that still change a requirement are carried into the new PRD;
everything else stays archived.
