# Pipeline stage 04 — Render prompt and choices

**Purpose:** turn a task definition into the exact model-facing prompt
and, for multiple choice, the rendered choice set.

**Input/output contract:** [`io-contracts.md`](io-contracts.md).

## Scope

- Render the prompt from program text, question, task clues, choices, and answer
  instruction.
- Prefix the prompt with the frame convention from `prompt-content.md` section
  1.1. It is fixed, not a per-task variant.
- Keep the prompt answer-free.
- Render task clues in the definition's canonical order in P0. A seeded
  permutation that respects reference dependencies is P1; it is recorded as the
  render seed, and clue wording uses presentation positions.
- For multiple choice, order and label the definition's choice pool. Do
  not re-bind entities or recompute answers.
- For P2 multiple choice, render the validated near-miss choice pool produced by
  `03`.
- Emit dataset release rows with the prompt and answer columns.

## Release projection

`04` owns the `TaskDefinition` to release-table projection. The column mapping is
in the
[release contract](../../requirements/release-dataset-contract.md), one row per
column, so it is written once.

- Copy the definition fields unchanged, including `clue_operand_form_profile`,
  which `05` validate and export release reads for clue operand form coverage.
- Copy the answer text. `gold_answer`, `tolerance`, and `answer_evidence` are
  already canonical text from `03b` construct task definitions, and `04` never
  re-serializes an answer value.
- Compute `prompt_sha256` over the `prompt` UTF-8 bytes after rendering.
- Derive `clue_types` from `clue_operand_form_profile`, so the two columns cannot
  disagree.
- Copy `answer_sha256`. Do not recompute it: it covers a fixed set of answer
  fields in a canonical form, and a second implementation would make a mismatch
  ambiguous between a changed answer column and two serializers that drifted.

Rendering may not invent a value. A projection that needs a field the definition
does not carry is a `03b` construct task definitions defect, not a rendering
decision.

## Prompt copy comes from YAML

LLM-facing wording is data, not Go code. Pipeline stage `04` renders from the
root `prompts.yaml`; it does not contain hardcoded question, clue, choice, or
answer-instruction strings. The file's schema, template IDs, placeholder forms,
label tables, and validation rules are in
[`../prompt-templates.md`](../prompt-templates.md).

- `04` reads the `dataset` namespace. The evaluation harness reads the
  `evaluation` namespace; the dataset release does not.
- Templates cover the question, each clue type, choice descriptions, and the
  answer instruction.
- Each template has a stable ID and typed placeholders. `04` validates the file
  before rendering. A missing, extra, or untyped placeholder is a release
  defect, not a task rejection.
- Template variants are selected deterministically from the template ID and
  render seed, not by an LLM.
- The template version and `prompts.yaml` hash are recorded with the release so
  the rendered prompt is reproducible.
- The YAML is answer-free. It must not contain gold answers, hidden identifiers,
  or generated answer data.
- P2 near-miss choice copy uses the same template mechanism.
- The frame convention is the first line of `dataset.prompt_shell` and matches
  `prompt-content.md` section 1.1. It is fixed, not a per-task variant.
- The renderer collapses a run of three or more newlines to two, so an empty
  `choices` list leaves one blank line before the answer instruction.

Evaluation prompts outside the dataset follow the same rule: they live in
`prompts.yaml`, not in Python strings. Dataset and evaluation templates use
separate namespaces in that file.

The prompt template set is an input to `04`; `io-contracts.md` names it
`PromptTemplateSet`. A missing template ID or an invalid placeholder stops the
render before any release row is written. `04` renders the question, clues,
choices, and answer instruction first, then fills `dataset.prompt_shell` with
those rendered parts.

## Language and parallelism

- **Go:** prompt and choice rendering.
- Rendering is parallel per task; a task definition is immutable and rendering
  has no shared mutable state.
- The release table has one deterministic writer. Parallel output is merged by
  `task_id`.

## No rejection

Rendering must not reject a task definition. Choice availability, choice
validity, target ambiguity, answer evidence, and uniqueness are decided in `03`.
Task quota planning is decided in `03a`. A rejection here is a defect in an earlier
pipeline stage. A missing template ID or an invalid placeholder is a defect in
`prompts.yaml`, not a reason to reject a task; `04` stops before writing the
release.

## Not here

Gold-answer correctness and task validity (`03b`), task quota planning (`03a`), and
release export (`05`).
