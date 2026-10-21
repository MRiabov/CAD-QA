# CAD-QA dataset

**Status:** re-specified from first principles, 2026-10-21. The previous
dataset documentation is archived under
`docs/_archive/dataset-pre-rebuild-2026-10-21/` and is not a specification.

This directory defines what the CAD-QA dataset is for, what a user gets from
training and evaluating on it, and the concepts needed to describe a task.
The product requirements and consumer contract are in `requirements/`. The
implementation docs, including the generation pipeline, are in `implementation/`.

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

Steps 1 and 2 are in `requirements/`. Step 3 starts in `implementation/pipeline/`.

## Documents

### Requirements

| Document | What it defines |
|---|---|
| [`requirements/PRD.md`](requirements/PRD.md) | What the user gets, what the dataset must contain, quality promises, size, splits, deliverables, and priorities. |
| [`requirements/task-structure.md`](requirements/task-structure.md) | The dimensions of a task, P0/P1/P2 implementation order for generation inputs, coverage and balance at every task reasoning step count, clue types, answer meanings, task reasoning step count rules, and uniqueness rules. |
| [`requirements/prompt-content.md`](requirements/prompt-content.md) | What the LLM model sees: program text, question, task clues, choices, and answer instruction. |
| [`requirements/graph-content.md`](requirements/graph-content.md) | The graph elements the tasks rely on: graph entities, relations, measurements, states, evidence, and P0/P1/P2 implementation order. |
| [`requirements/terminology.md`](requirements/terminology.md) | Proposed terms, replacements for old terms, and naming decisions that still need owner approval. |
| [`requirements/release-dataset-contract.md`](requirements/release-dataset-contract.md) | Consumer contract: release artifacts, row counts, release table columns, and why one table is enough. |

### Implementation

Implementation docs state how the generator satisfies the requirements. They are
not product requirements.

| Document | What it defines |
|---|---|
| [`implementation/README.md`](implementation/README.md) | Scope of implementation docs and where to start. |
| [`implementation/artifacts.md`](implementation/artifacts.md) | Who writes and reads each dataset artifact, and how artifacts are versioned. |
| [`implementation/planning-math.md`](implementation/planning-math.md) | Priority, coverage, balance, split, and release-cap math. |
| [`implementation/task-step-support.md`](implementation/task-step-support.md) | Derived task reasoning step support tables used to check coverage, not generator inputs. |
| [`implementation/python-and-golang.md`](implementation/python-and-golang.md) | The Python and Go language boundary for the dataset generator. |

#### Pipeline

| Document | What it defines |
|---|---|
| [`implementation/pipeline/00-end-to-end.md`](implementation/pipeline/00-end-to-end.md) | Why the dataset pipeline exists, pipeline stage order, and data flow. |
| [`implementation/pipeline/io-contracts.md`](implementation/pipeline/io-contracts.md) | Authoritative typed I/O between pipeline stages. |
| [`implementation/pipeline/01-external-dataset-etl.md`](implementation/pipeline/01-external-dataset-etl.md) | CADEvolve Parquet cache → normalized programs and manifest. |
| [`implementation/pipeline/02-execute-cadquery-and-build-graph.md`](implementation/pipeline/02-execute-cadquery-and-build-graph.md) | Static extraction and CadQuery execution → CAD graph. |
| [`implementation/pipeline/03-enumerate-tasks.md`](implementation/pipeline/03-enumerate-tasks.md) | Release planning, task definitions, deficit resolution, step counts, identity, and gold answers. |
| [`implementation/pipeline/04-render-prompt-and-choices.md`](implementation/pipeline/04-render-prompt-and-choices.md) | Prompt rendering and multiple-choice choices. |
| [`implementation/pipeline/05-validate-and-export-release.md`](implementation/pipeline/05-validate-and-export-release.md) | Validation, export, manifest, and dataset card. |

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
