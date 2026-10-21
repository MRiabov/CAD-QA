# CAD-QA dataset

**Status:** re-specified from first principles, 2026-10-21. The previous
dataset documentation is archived under
`docs/_archive/dataset-pre-rebuild-2026-10-21/` and is not a specification.

This directory defines what the CAD-QA dataset is for, what a user gets from
training and evaluating on it, and the concepts needed to describe a task.
The product requirements are in `requirements/`. Technical structure is in
`implementation/`.

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

Steps 1 and 2 are in `requirements/`. Step 3 starts in `implementation/`.

## Documents

### Requirements

| Document | What it defines |
|---|---|
| [`requirements/PRD.md`](requirements/PRD.md) | What the user gets, what the dataset must contain, quality promises, size, splits, deliverables, and priorities. |
| [`requirements/task-structure.md`](requirements/task-structure.md) | The dimensions of a task, P0/P1/P2 priorities for generation inputs, coverage and balance at every task reasoning step count, clue types, answer meanings, task reasoning step count rules, and uniqueness rules. |
| [`requirements/prompt-content.md`](requirements/prompt-content.md) | What the LLM model sees: program text, question, task clues, choices, and answer instruction. |
| [`requirements/graph-content.md`](requirements/graph-content.md) | The graph elements the tasks rely on: graph entities, relations, measurements, states, evidence, and P0/P1/P2 priorities. |
| [`requirements/terminology.md`](requirements/terminology.md) | Proposed terms, replacements for old terms, and naming decisions that still need owner approval. |

### Implementation

| Document | What it defines |
|---|---|
| [`implementation/release-dataset-structure.md`](implementation/release-dataset-structure.md) | Release artifacts, row counts, release table columns, and why one table is enough. |

### Feature-wide

| Document | What it defines |
|---|---|
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
