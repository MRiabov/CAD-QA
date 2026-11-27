# Developer tools

**Status:** draft, 2026-11-21. This directory documents developer tools that are
not pipeline stages: owner-run checks, renderers, benchmarks, and doc checkers.

A tool here is not part of the release and is not imported by the generator. A
tool whose output becomes load-bearing moves into the package and gets a test
contract; it does not stay here.

## What belongs here

- tools whose output a person reads or judges: 3D scenes, sampled slices,
  review ledgers;
- benchmarks and one-off measurements that support a decision;
- repository checkers that enforce a doc or code convention.

## What does not belong here

- pipeline stage behaviour and I/O contracts: [`../pipeline/`](../pipeline/);
- release artifacts and their columns:
  [`../../requirements/release-dataset-contract.md`](../../requirements/release-dataset-contract.md);
- requirements-level decisions: [`../../requirements/decisions.md`](../../requirements/decisions.md);
- implementation decisions that span pipeline stages: [`../decisions.md`](../decisions.md).

## Conventions

- One document per tool, named after the tool.
- A tool document states: purpose, status (`planned`, `missing`, or `available`),
  invocation, inputs, outputs and where they are written, the human step it
  supports, and what it does not prove.
- Code lives under `tools/ci_cd/` when CI or pre-commit invokes it, and under
  `tools/manual-verification/` when a person runs it by hand. Neither is imported
  by the generator.
- Output is written under `runs/manual_verification/<tool>/` or another
  gitignored path. No scene cache, sample, or ledger is committed.
- A tool builds against the contracts in `docs/`, never against the code being
  replaced.
- The tool prints the inputs it used next to the output path. A scene without
  the prompt it came from is not verifiable.
- A tool that runs CadQuery over many items executes them in one process and
  imports the kernel once. A cold `import cadquery` costs seconds and hundreds
  of megabytes ([measurement
  log](../../../../plans/nov-21/performance-audit.md#measurement-log)), while a
  hand-written oracle query's geometry costs a fraction of a second, so one
  process per item pays that import once per item for no gain. Keep items
  isolated by giving each a fresh namespace and catching its failure as a row,
  and enforce the per-item deadline from the parent. The trade-off is that a
  program that corrupts the interpreter can affect the items after it:
  acceptable for checked-in, reviewed test data, not for generated programs,
  which run in the `02b` worker.

## Manual verification

A manual verification script is a tool whose check needs human judgement: is the
highlighted entity the one the clue names, does this prompt read clearly, does
this answer match the geometry. An automated check cannot make that judgement.

- One file per check, named `<verb>_<object>.py`.
- Run it by hand: `uv run python tools/manual-verification/<name>.py --help`.
- Take the dataset path and a row selector as arguments; never hardcode a run.
- A script that becomes load-bearing moves into the package and gets a test.

The one human review frontend is the
[dataset browser](dataset-browser.md). It lists, filters, and opens release tasks
or gold oracles, orders the review queue by coverage gap, and records a release
row's verdict in the dataset release task review ledger. The absence and
geometry residual ledgers are derived and machine-checked; the browser shows them
read-only under its `Other` menu and never asks for a verdict on them.

## Tools

| Tool | What it does | Status |
|---|---|---|
| [`dataset-browser.md`](dataset-browser.md) | Lists, filters, and opens release tasks or gold oracles, orders the review queue by coverage gap, records a release row's verdict in the dataset release task review ledger, and shows the derived absence and residual ledgers read-only. | `available`; review queue and approval `planned` |
| `residual_sample.py` | Draws `min(pool_size, 300)` programs from the pinned dataset release program pool, runs the CAD graph kernel-oracle differential, and writes the dataset release geometry residual ledger. | `planned` |
| Don't-say checker | Enforces the glossary's Don't-say table and the identifier renames. | `available`; see [`../../../docs-conventions.md`](../../../docs-conventions.md) |
