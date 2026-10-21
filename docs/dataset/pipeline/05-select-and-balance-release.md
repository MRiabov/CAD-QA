# Pipeline stage 05 — Select and balance release

**Purpose:** select tasks into a release that meets the size, coverage, balance,
split, and priority constraints.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Scope

- Apply the P0/P1/P2 priority slice.
- Select a deterministic release subset.
- Apply task reasoning step count mix.
- Apply answer format, clue type, answer meaning, and target category coverage
  and balance.
- Assign training, validation, and test splits by program.
- Apply the CAD model and correct-answer caps.

## Open questions

- **Q1.** Is release selection implemented by enumerating and cutting, or by
  planning quotas and generating into them?
  - **Recommendation:** this is an implementation choice; the contract fixes
    deterministic output, not the strategy.

- **Q3.** Is the conditional release share computed from the valid-task
  universe, or allocated from the global targets before selection?
  - **Recommendation:** Option B: allocate quotas from the global targets, then
    fill from the universe.

## Not here

Schema validation, leak checks, and export.
