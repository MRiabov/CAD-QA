# CAD-QA documentation conventions

**Status:** active — initial version, 2026-10-07. Source plan:
`plans/oct-7/restructure-docs.md`.

This is the contract for how CAD-QA docs are structured and written. It is the meta-doc:
every other doc follows it and, eventually, lint enforces it. Read it before adding or
editing a doc.

## Audience

Two readers, both primary:

- **The owner (human)** — must read a doc without pausing to ask what a term means. This is
  the readability bar.
- **Implementing agents** — read the docs to build and change the code, and write and
  update the docs themselves. They need the same precision.

One standard serves both: precise, in the project's ubiquitous language
(`glossary.md`). A doc that is complete but needs a follow-up question has failed. If a term
is ambiguous or a sentence overclaims, fix the doc.

## Doc tree

```text
docs/
  README.md                     # router: reading order + canonical references
  docs-conventions.md           # this file
  PRD.md                        # intent: questions, claims, deliverables, eval contract
  glossary.md                   # canonical terms + Don't-say (ratchet)
  development-context.md        # history + as-of snapshot (proven vs assumed)
  development-plan.md           # phased route to completion
  prior-art.md                  # mined open-source training/RL/data pipelines
  adr/
    NNNN-<slug>.md              # one decision per file; referenced as (ADR-0NNN)
  research-scopes/
    cadedit/PRD.md              # only if CADEditQA is active (P2)
  dataset/
    README.md
    requirements.md             # intended-vs-verified summary
    decisions.md                # local decisions (ADR format)
    pipeline/
      00-overview.md            # DAG + stage IO contract
      NN[a-z]-<slug>.md         # 01-source-ingestion.md, 01a-…, 04c-…
  fine-tuning/
    README.md
    requirements.md
    decisions.md
    pipeline/
      00-overview.md
      NN[a-z]-<slug>.md
  evaluation/
    README.md
    harness.md
    baselines.md
docs/experiments/YYYY-MM-DD-<slug>.md   # dated experiment records
```

`_audit/` is a throwaway, owner-private working area (for example
`_audit/owner-audit-todo.md`). `_archive/` holds superseded docs kept as raw material.
Neither is part of the canonical tree; both are excluded from lint.

## Doc layers (roles)

Every doc has exactly one role, and every fact has exactly one home. Do not copy a fact
into two docs — link.

| Layer | Holds | Home |
|---|---|---|
| WHY / authoritative | rationale, decisions, constraints, known holes | `adr/`, step-doc decision sections, `PRD.md` |
| WHAT / mechanics | how a step behaves, in words | `pipeline/NN-*.md` |
| CONTRACT / IO | artifact and field names between steps | `pipeline/00-overview.md` |
| STATUS | verification state | step-doc `Current status` |
| TERMS | canonical vocabulary | `glossary.md` |

Docs restate behaviour deliberately (that is the point of the WHAT layer). They never copy
rationale — link the ADR — and never redefine field names — match the IO contract.

## Required sections

### Pipeline step doc (`pipeline/NN-*.md` or `NNx-*.md`)

1. **Purpose** — one sentence.
2. **Inputs / outputs** — must match the `00-overview.md` IO contract exactly.
3. **Requirement** — what must be true for the downstream claim to hold.
4. **Current status** — one tag plus evidence.
5. **Verification** — the exact command that would make it `verified`.
6. **Local decisions** — decisions scoped to this step, in ADR format.
7. **Open questions**.
8. **Resolved questions** — moved here with resolution + date; never deleted.
9. **Extra deliverables - P2** (optional).

### `pipeline/00-overview.md`

- The DAG order; the stage IO contract (single source for artifact and field names); links
  to the step docs.

### `PRD.md`

- Intent; research questions; claims; deliverables; evaluation contract; scope; definition
  of done; non-goals.

### ADR (`adr/NNNN-<slug>.md`)

- `Status` / `Context` / `Decision` / `Consequences`. One decision per file. Referenced
  inline as `(ADR-0NNN)`. ADRs are forward-looking: record decisions made, not
  archaeology.

### `decisions.md`

- Local decisions for a unit, in the same format as an ADR.

## Naming

- File names are lowercase and hyphenated. Pipeline steps are `NN[a-z]-<slug>.md`
  (`01-source-ingestion.md`, `01a-…`, `04c-…`).
- Headings are part of the interface. Rename them deliberately; anchors are referenced
  elsewhere.
- Code package directories use underscores (`dataset_generation`, `fine_tuning`) because
  they are Python imports. Hyphens are for docs only (`docs/fine-tuning/`).

## References

Never cite line numbers — they drift. Cite in this order of preference:

- code: `path::symbol`
- another doc: a heading/anchor, e.g. `fine-tuning/pipeline/04-sft.md#requirement`
- a decision: `(ADR-0NNN)`, or the step's decision number
- an artifact: its path or revision hash

## Terminology discipline

- **One concept, one word.** A term names one thing; a thing has one term. Split
  collisions; pick one of synonyms.
- **Precise and scoped.** No unspecific placeholders ("the object", "the pipeline") where
  a named concept exists.
- **No overclaiming.** Describe verified behaviour, or mark it. Never assert behaviour a
  check has not confirmed.
- **No conflation.** Do not reuse a term for a related-but-different concept; name the
  distinction.
- **Defined or banned.** Every load-bearing term is in `glossary.md`; every bad term is on
  its Don't-say list and fails lint.
- **A term that needs a follow-up question is a defect.**

## Status tags

Mark unverified or uncertain claims explicitly:

`verified` (a check ran and passed) · `exists` (present, unchecked) · `missing` ·
`stale` · `[unverified — needs <env>]` · `[unknown]`.

A status only moves up when a check passes.

## Open and resolved questions

Docs that carry uncertainty have `## Open questions` and, once settled,
`## Resolved questions`. Resolving moves the item (resolution + date); it is never
deleted.

## Priority

- **P0** — thesis critical path (blocking).
- **P1** — thesis important (should-have).
- **P2** — good-venue publication extras (optional, may never execute).

P2 work is collected in a trailing `## Extra deliverables - P2` block, never treated as a
P0/P1 commitment.

## Writing method

- **Describe logic and decisions**, in domain terms — not code. Code churns; by the end
  only the logic and the decisions matter.
- **Verification is separate.** The heavy checks (oracle grading, parity, sandbox) are the
  audit, not the writing pass.
- **Conflicts are findings.** A doc/code disagreement is recorded and one side is fixed.

## Lint, format, ratchets

- **Don't-say checker: implemented and enforced.** `tools/check_dont_say.py` reads the
  `## Don't say` table from `glossary.md` and fails on banned terms across docs and code.
  A `(home)` annotation exempts a tree, `ALLOWLIST` exempts cross-cutting phrases, and the
  `dont-say: allow` / `dont-say: home` markers exempt a line/file. Code matches
  identifier-shaped tokens only. Run `uv run python tools/check_dont_say.py`.
- **Ratchets only improve.** `tools/dont_say_baseline.txt` holds the accepted count; the
  checker fails if hits rise, or fall without the baseline being lowered. Enforced by
  `tests/test_dont_say_ratchet.py` (the test gate). The sweep is tracked in
  `_audit/dont-say-worklist.md`.
- **Not implemented yet:** the Markdown formatter (`rumdl`, fallback `mdformat`), the
  docs-structure / ADR / decisions linters, and a pre-commit/CI wiring. See
  `development-plan.md`.

## Experiment records

Dated files under `docs/experiments/`. Each records: purpose, hypothesis, dataset and
splits, config and exact commands, hardware, outcomes, failures, and artifact paths.
Performance is one section, not the whole record.
