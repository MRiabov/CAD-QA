# CAD-QA dataset

**Status:** re-specified from first principles, 2026-10-21. The previous
dataset documentation is archived under
`docs/_archive/dataset-pre-rebuild-2026-10-21/` and is not a specification.

This directory defines what the CAD-QA dataset is for and what a user gets from
training and evaluating on it. Start with [`PRD.md`](PRD.md). The technical
specification is not written yet.

## Why the product comes first

The previous dataset grew from a mixture of good ideas, inherited names, and
implementation-first decisions. The result was hard to explain to a user and
hard to check against its own claims. This rewrite starts with the user outcome:
what the dataset must let an LLM model do, what a reviewer must be able to check, and
what the dataset must contain. The implementation is chosen after that.

The order is:

1. Define what the user gets and what the dataset must contain.
2. Agree on the words used to describe it.
3. Write the technical specification.
4. Build the smallest complete sample.
5. Produce the first dataset release.

Only step 1 is in this directory today.

## Relation to the project PRD

[`../PRD.md`](../PRD.md) remains the authority for the research questions,
hypotheses, and evaluation goals. This dataset PRD is subordinate to it: it
defines the dataset those goals need, and it does not change the goals.

## Archived material

The archive is history, not current requirements. It contains the old dataset
documentation, the old answer notes, the old decisions, and the old issue
register. Facts that still change a requirement are carried into the new PRD;
everything else stays archived.
