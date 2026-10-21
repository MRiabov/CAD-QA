# Dataset generator

**Status:** rebuilt from first principles, 2026-10-21. The previous generator,
its pipeline docs, and its issue register are archived under
`docs/_archive/dataset-pre-rebuild-2026-10-21/` and are not a specification.

This directory defines the replacement dataset generator. Start with
[`PRD.md`](PRD.md). Technical specifications — architecture, data schema,
language boundaries, algorithms, and migration mechanics — are deliberately not
written yet.

## Why there is only a PRD

The previous generator was built from a mixture of good ideas, inherited
vocabulary, and code-first decisions. That produced a pipeline whose task
families were hard-coded, whose terminology often described implementation
accidents, and whose quality gates did not match the data. Re-specifying the
product first prevents the replacement from repeating that pattern.

The order is:

1. Re-define what the generator is for and what tasks the dataset must contain.
2. Establish the vocabulary the implementation will use.
3. Write the technical specification.
4. Build the smallest complete slice.
5. Scale to a release.

Only step 1 is in this directory today.

## Relation to the project PRD

[`../PRD.md`](../PRD.md) remains authoritative for the research questions,
hypotheses, and the evaluation contract. This PRD is subordinate to it: it
defines the instrument the project PRD needs, and it does not change the
research goals.

## Archived material

The archive is input material, not current truth. It contains the old pipeline
docs, the old answer-format record, the old decisions, and the known-major-issues
register. Useful historical facts are carried into the new PRD where they change
a requirement; everything else stays archived.
