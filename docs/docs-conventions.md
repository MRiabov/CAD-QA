# CAD-QA documentation conventions

**Status:** active — initial version, 2026-10-07. Based on the plan
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
  general-architecture/
    README.md                   # router: cross-cutting engineering contracts
    ci-cd.md                    # CI triggers, quality-and-plan, suites, caches
  prior-art.md                  # mined open-source training/RL/data pipelines
  research/
    README.md                   # external study notes + citations
    YYYY-<slug>.md              # one file per external study
  research-scopes/
    cadedit/PRD.md              # only if CADEditQA is active (P2)
  dataset/
    README.md
    requirements/               # PRD, task structure, prompt, release, terminology
      views/                    # derived views for review: clue list, reference forms, prompt examples, capability coverage, shortcut resistance
      decisions.md              # requirements decisions (DS-REQ-*)
    implementation/
      decisions.md              # implementation decisions that span pipeline stages (DS-ADR-*)
    pipeline/
      00-overview.md            # DAG + stage IO contract
      NN[a-z]-<slug>.md         # 01-source-ingestion.md, 01a-…, 04c-…
      NN-<module>/              # module-sized step: 02 extraction, 03 task generation
        README.md               # entry point: input, output, process, status
        NNx-<slug>.md           # sub-step docs
        decisions.md            # module-local decisions (ADR format)
        algorithm/<slug>.md     # how each mechanism works
        features/<slug>.md      # per-item contract for each feature field
  train-and-eval/
    datasets.md                   # dataset → DatasetRole assignment
    fine-tuning/
      README.md
      training.md                 # base, stack, capability preservation, hardware
      data.md                     # dataset roles, mix recipe, order, governance
      system.md                   # post-training loop + data preparation
      testing.md                  # integration + end-to-end tests
      requirements.md
      decisions.md
      pipeline/
        00-overview.md
        NN[a-z]-<slug>.md
    evaluation/
      README.md
      plan.md                     # harness, scorer, evaluation datasets, H3/H4 transfer
      harness.md
      baselines.md
      decisions.md                # local decisions (ADR format)
  paper/
    CA2_Riabov_final.md          # written manuscript; parity-kept with the .tex
    CA2_Riabov_final.tex
    CA2Img-GanttChart-mermaid.png
docs/experiments/YYYY-MM-DD-<slug>.md   # dated experiment records
```

`_audit/` is a throwaway, owner-private working area (for example
`_audit/owner-audit-todo.md`). `_archive/` holds superseded docs kept as raw material.
Neither is part of the canonical tree; both are excluded from lint. `paper/` holds the
written manuscript (Markdown and LaTeX kept in parity); it is canonical output but is
exempt from the Markdown linter, because the manuscript is authored for the LaTeX
submission copy and linting would rewrite its prose out of parity. It uses the project's
domain terminology, so its prose follows the glossary. Literal code snippets, enum values
inside `\texttt{}`, and bibliographic titles may carry a `dont-say: allow` marker when a
term is unavoidable.

## Doc layers (roles)

Every doc has exactly one role, and every fact has exactly one home. Do not copy a fact
into two docs — link.

| Layer | Holds | Home |
|---|---|---|
| WHY / authoritative | rationale, decisions, constraints, known holes | `<feature>/decisions.md`, step-doc decision sections, `PRD.md` |
| WHAT / mechanics | how a step behaves, in words | `pipeline/NN-*.md` |
| CONTRACT / IO | artifact and field names between steps | `pipeline/00-overview.md` |
| STATUS | verification state | step-doc `Current status` |
| TERMS | canonical vocabulary | `glossary.md` |
| CONTEXT / external | external study notes and citations; secondary to the project docs | `research/` |

Docs restate behaviour deliberately (that is the point of the WHAT layer). They never copy
rationale — link the decision — and never redefine field names — match the IO contract.

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

A step that owns a module — a sub-pipeline with its own algorithms and per-item
contracts — is a folder instead of one file. The folder holds `README.md` for the
module contract, `NNx-*.md` for sub-steps, `algorithm/` for how each mechanism
works, `features/` for per-item field contracts, and `decisions.md` for decisions
scoped to the module. `pipeline/extraction/` and
`pipeline/03-task-generation/` are the current examples.

### `pipeline/00-overview.md`

- The DAG order; the IO contract between pipeline stages (single source of truth for artifact and field names); links
  to the step docs.

### `PRD.md`

- Intent; research questions; claims; deliverables; evaluation contract; scope; definition
  of done; non-goals.

### Decisions (`<feature>/decisions.md`)

- Record each decision at the **narrowest scope that owns it**, in this order:
  1. **Step-local** — in that step doc's `## Local decisions` (the file you are editing),
     e.g. `pipeline/02-trace-snapshot.md#local-decisions`.
  2. **Module-local** — in a module folder's `decisions.md`, for logic scoped to that
     module; e.g. `pipeline/03-task-generation/decisions.md#tg-1`.
  3. **Feature-wide** — in the feature's `decisions.md`, for logic that spans the
     feature's stages. A feature may have one file per layer:
     `dataset/requirements/decisions.md` (`DS-REQ-*`, what the dataset is) and
     `dataset/implementation/decisions.md` (`DS-ADR-*`, how the generator is built);
     `train-and-eval/fine-tuning/decisions.md` (`FT-D*`).
  4. **Cross-cutting/plan** — D1–D14 stay in the plan / `development-plan.md`.
- Prefix a decision ID by its scope (`DS-REQ`, `DS-ADR`, `TG`, `EX`, `STK`, `ETL`,
  `TERM`, `FT-D`). An ID is unique within its scope and is the citation key; it
  never changes meaning. Feature-level IDs are zero-padded (`DS-REQ-01`), local
  IDs are not (`TG-4`).
- Format: `Status` / `Context` / `Decision` / `Consequences`. There is no central
  `docs/adr/` folder.
- Decisions are forward-looking: record decisions made, not archaeology.

## Naming

- File names are lowercase and hyphenated. Pipeline steps are `NN[a-z]-<slug>.md`
  (`01-source-ingestion.md`, `01a-…`, `04c-…`).
- Headings are part of the interface. Rename them deliberately; anchors are referenced
  elsewhere.
- Code package directories use underscores (`cadqa_dataset_generator`) because
  they are Python imports. Hyphens are for docs only (`docs/train-and-eval/`).

## Prompt text

All LLM-facing prompt text is data, not code. Put it in `generator/config/prompts.yaml`.
The file's schema is in
[`dataset/implementation/prompt-templates.md`](dataset/implementation/prompt-templates.md).

- The dataset and evaluation harnesses use separate namespaces in that file.
- Code selects template IDs and fills typed placeholders. Go and Python do not
  hardcode question, clue, choice, system, or evaluation instruction strings.
- A template change bumps the prompt version. The rendered prompt hash and the
  `prompts.yaml` hash are recorded in the relevant artifact or run manifest.
- Prompt templates are answer-free; they never contain gold answers or hidden
  identifiers.

## References

Never cite line numbers — they drift. Cite in this order of preference:

- code: `path::symbol`
- another doc: a heading/anchor, e.g. `train-and-eval/fine-tuning/pipeline/04-sft.md#requirement`
- a decision: `<feature>/decisions.md#<anchor>`, or the step's local decision number
- an artifact: its path or revision hash

## Terminology discipline

- **One concept, one word.** A term names one thing; a thing has one term. Split
  collisions; pick one of synonyms.
- **Precise and scoped.** No unspecific placeholders where a named concept exists — name
  the concept.
- **No overclaiming.** Describe verified behaviour, or mark it. Never assert behaviour a
  check has not confirmed.
- **No conflation.** Do not reuse a term for a related-but-different concept; name the
  distinction.
- **Defined or banned.** Every load-bearing term is in `glossary.md`; every bad term is on
  its Don't-say list and fails lint.
- **No bare single-letter symbol.** A quantity or an index is named, never a bare `k`, `T`,
  `r`, or `N`; established external notation is exempt (`glossary.md`, "The rule").
- **A term that needs a follow-up question is a defect.**

## Status tags

Mark unverified or uncertain claims explicitly:

`verified` (a check ran and passed) · `exists` (present, unchecked) · `missing` ·
`stale` · `[unverified — needs <env>]` · `[unknown]`.

A status only moves up when a check passes.

## Open and resolved questions

Docs that carry uncertainty have `## Open questions` and, once settled,
`## Resolved questions`. Label each item **`Q1`, `Q2`, …** in document order (a bullet begins
`- **Q1.** …`). Resolving moves the item to `## Resolved questions`, keeping its label and adding
the resolution + date; it is never deleted. Reference an item by its label, not by line number.

## Priority

- **P0** — thesis critical path (blocking).
- **P1** — thesis important (should-have).
- **P2** — good-venue publication extras (optional, may never execute).

P2 work is collected in a trailing `## Extra deliverables - P2` block, never treated as a
P0/P1 commitment.

## Writing method

- **Describe logic and decisions**, in domain terms — not code. Code churns; by the end
  only the logic and the decisions matter.
- **Citations.** Cite the strongest independent reference first; prefer peer-reviewed and lab
  research to an interested party. The sourcing standards and provenance tags live in
  `research/README.md#sourcing-standards`.
- **Verification is separate.** The heavy checks (oracle grading, parity, sandbox) are the
  audit, not the writing pass.
- **Conflicts are findings.** A doc/code disagreement is recorded and one side is fixed.

## Lint, format, ratchets

- **Don't-say checker: a script, not a test.** `tools/ci_cd/dont-say` reads the `## Don't say`
  table from `glossary.md` and fails on banned terms across docs, code, and JSON contracts
  (Markdown, LaTeX, Python, Go, JSON). It scans the whole repository (about a second), so it
  runs as a pre-commit hook and never from pytest: a test would make every test run pay for
  the scan.
  A `(home)` annotation exempts a tree, `ALLOWLIST` exempts cross-cutting phrases, and the
  `dont-say: allow` marker exempts one line. A fenced block is skipped whole; a fence closes
  only with a delimiter of the same character and at least the same length, so a `python`
  block quoted inside a longer `text` block is never read as prose. A comment line in the
  first ten lines that begins `dont-say: allow-file` exempts the whole file; use it only for
  historical records and verbatim external text. Two trees are skipped whole because they are
  written in the vocabulary of their sources rather than the project's: `research/` (external
  study notes) and `paper/` (the manuscript draft).
  In Python and Go, comments and docstrings are matched as prose, and every declared name is matched as a name: class, function, method, parameter, variable,
  field, declared type, constant, file, and folder. JSON checks `description` and `title` as
  prose, and property, definition, enum, and const values as names; schema vocabulary is not
  a CAD-QA name. Run `tools/ci_cd/dont-say`, or
  `tools/ci_cd/dont-say --ratchet tools/ci_cd/dont_say_baseline.txt
  --names-ratchet tools/ci_cd/dont_say_names_baseline.txt` to enforce both ratchets.
- **Name matching.** A name matches when the rule's words appear as consecutive segments, so
  `query_program`, `QueryProgram`, and `query-program` all match `query program`. A bare term
  is allowed when a preceding segment qualifies it (`clue_type`); a leading verb does not
  qualify it (`get_type` is a hit). Go syntax comes from `tools/dont-say-go`, which uses
  `go/parser`; the checker never guesses at Go comments or literals. The plan that rejected
  a hand-written Go lexer is `plans/nov-21/dont-say-naming-check.md`.
- **Clean code: P2.** The checker enforces the name ratchet now; the naming sweep itself is
  tracked in `development-plan.md` Phase 6 and is visibility only, not P0/P1.
- **Two ratchets.** `dont_say_baseline.txt` counts prose hits and
  `dont_say_names_baseline.txt` counts declared-name hits. The checker fails if either count
  rises, or if it falls without the baseline being lowered in the same commit. The
  `dont-say` pre-commit hook enforces both. Dated plans and audits are historical records and
  carry `dont-say: allow-file`; they are not rewritten. `docs/train-and-eval/` is stale design
  input for the deleted training stack, so its hits stay in the baseline until the rewrite
  replaces it; they are not live debt. The sweep is tracked in `_audit/dont-say-worklist.md`.
- **Markdown formatter: `rumdl`.** `.rumdl.toml` is the committed config (GFM flavor;
  `MD013` line length and `MD033` inline HTML off, matching the docs' style; scoped to
  `docs/` and `plans/`). Run `uv run rumdl check` to report, or
  `uv run rumdl fmt` to fix. Wired into pre-commit (`.pre-commit-config.yaml`); enable it
  once with `uv run pre-commit install`.
- **Doc mirror: a script, not a test.** `tools/ci_cd/check-doc-mirror` requires
  every pipeline stage/sub-step contract doc to have the same relative path under
  `streamlined/` and `testing/`. `decisions.md`, `algorithm/`, and `extraction/`
  are exempt; `streamlined/models/`, `testing/00-*.md`, and the test-data folders
  are allowed additions. It runs in the CI quality job and as a pre-commit hook.
- **Python and Go hooks.** `ruff format` and `ruff check --fix` are wired.
  `pyrefly` is wired on the manual stage until the old Python tree is removed. The Go
  hooks (`gofumpt`, `goimports`, `golangci-lint`) are declared as TODOs in
  [`dataset/implementation/stacks.md`](dataset/implementation/stacks.md#pre-commit);
  `generator/` exists, but the hooks are not wired yet.
- **Not implemented yet:** the docs-structure / decisions linters. CI is defined in
  [`general-architecture/ci-cd.md`](general-architecture/ci-cd.md).

## Experiment records

Dated files under `docs/experiments/`. Each records: purpose, hypothesis, dataset and
splits, config and exact commands, hardware, outcomes, failures, and artifact paths.
Performance is one section, not the whole record.
