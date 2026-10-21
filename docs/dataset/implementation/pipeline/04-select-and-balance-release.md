# Pipeline stage 04 — Select and balance release

**Purpose:** select task definitions into a release that meets the size,
coverage, balance, split, and implementation-scope constraints before any prompt
text is rendered.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

Selection math: [`../selection-math.md`](../selection-math.md).

## Scope

- Select a deterministic release subset from the valid task definitions.
- Apply the task reasoning step count mix.
- Apply target category, clue type, answer meaning, and answer format coverage
  and balance.
- Assign training, validation, and test splits by CADEvolve program family, not
  by program.
- Apply the CAD model and correct-answer caps.
- Check the selected values against the task reasoning step support tables.
- Emit `SelectedTask` records: the task definition plus split, subset, and
  selection metadata.

## Why selection comes before prompt assembly

Selection needs the task definition, not the prompt. Rendering is pure cost for a
task that will not enter the release. It also introduces a second rejection point
after selection, which can break coverage targets.

All semantic validity is decided in `03`:

- the answer is unique and evidenced;
- the target is identified;
- every task clue narrows;
- a multiple-choice definition has at least five real choices in its choice
  pool.

`05` must not discover a new semantic reason to reject a selected definition.
P2 near-miss distractors are the exception described in `05` Q1.

## Open questions

- **Q1.** Is release selection implemented by enumerating and cutting, or by
  planning quotas and generating into them?
  - **Recommendation:** this is an implementation choice; the contract fixes
    deterministic output, not the strategy.

- **Q3.** Is the conditional release share computed from the valid-task set,
  or allocated from the global targets before selection?
  - **Recommendation:** Option B: allocate quotas from the global targets, then
    fill from the valid-task set.

## Not here

Prompt rendering, choice rendering, schema validation, leak checks, and export.
