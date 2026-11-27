# 04 render prompt and choices — adversarial integration test (TDD)

**Parent:** [`00-testing-strategy.md`](00-testing-strategy.md).

**Contract under test:** [`../04-render-prompt-and-choices.md`](../04-render-prompt-and-choices.md),
with the column mapping in
[`../../../requirements/release-dataset-contract.md`](../../../requirements/release-dataset-contract.md)
section 4 and the template schema in [`../../prompt-templates.md`](../../prompt-templates.md).

## Happy-path integration test (test-first, adversarial)

`test_04_render_happy_path_adversarial` — renders the golden definition over the
golden program with the fixture `prompts.yaml`, and asserts the release row read
back through the reader `05` validate and export release uses.

**Given** the golden record's definition, its normalized program, and a
`RenderConfig` with a fixed release seed and a template set whose variants,
labels, and placeholders are all declared.

**When** `04` renders.

**Then** assert the release row:

- `prompt` starts with the frame convention line, then the program text verbatim
  inside a fenced block, then the question, then the two clues in canonical
  order and numbered;
- `12.57`, the gold answer, does not appear anywhere in `prompt`;
- `prompt_sha256` equals the SHA-256 the test recomputes over the `prompt` UTF-8
  bytes, with no trailing newline added;
- `choices` is empty, because the answer format is a number;
- `clue_types` is the clue type sequence of `clue_reduction_form_profile`, so the
  two columns cannot disagree;
- `gold_answer`, `tolerance`, `answer_evidence`, and `answer_sha256` equal the
  definition's typed values byte for byte after canonical encoding. The fixture
  writes its tolerance with a number form a serializer would change, so a
  re-serialization fails here;
- `answer_schema_version` is copied unchanged;
- every column the release contract marks required is present, and no column is
  invented.

`test_04_multiple_choice_pool` — a five-entry pool renders five choice lines in
the pool's recorded order with its labels `A` to `E`, the `choices` column holds
one `{label, candidate}` per entry in the same order, and `gold_answer.label` is
the correct label. The gold label appears exactly once in `prompt`, in its own
choice line, and nothing marks it as correct. A pool that is reordered, relabelled,
or trimmed fails.

`test_04_seed_selects_a_variant` — a template with two variants renders the same
variant for the same release seed and `task_id`, and a changed release seed
selects a different variant for at least one of twenty tasks. The test asserts the
selected text, not an internal index.

`test_04_parallel_merge` — rendering the same definitions in parallel produces a
table byte-identical to the sequential render, merged by `task_id`.

`test_04_newline_collapse` — a task with an empty choice list leaves exactly one
blank line at the end of the prompt, and a rendered part containing three
newlines collapses to two.

**TDD pin:** pins the prompt layout order, the answer-free prompt, the
`prompt_sha256` bytes, the copied answer text, the choice block, the seed-selected
variant, and the newline rule before `04` exists.

## Failure-mode tests

- `test_04_missing_template` — a template set without `dataset.question.length`
  stops the render before any row is written and names the template ID.
- `test_04_placeholder_declaration` — a placeholder used but not declared, one
  declared but not used, and one declared with no form each stop the render and
  name the file, the template, and the placeholder.
- `test_04_definition_field_missing` — a definition missing a field the template
  needs stops the render and reports a `03b` defect. It does not drop the task,
  because rendering must not reject a definition.
- `test_04_namespace_isolation` — a change to an `evaluation` template changes no
  prompt, because the dataset release reads the `dataset` namespace only.
- `test_04_no_partial_release` — a failure on the last of ten tasks leaves no
  release table at all, not nine rows.

## What this does not prove

- That the definition is valid. That is
  [`03b-construct-task-definitions.md`](03-task-generation/03b-construct-task-definitions/README.md).
- That the release passes its checks. That is
  `05-validate-and-export-release.md`.
- That the wording is good. That is the review gate.
