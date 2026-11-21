# 04 render prompt and choices — answer-free release rows

> Authoritative: `../04-render-prompt-and-choices.md`
> Templates: `../../prompt-templates.md`
> Prompt content: `../../requirements/prompt-content.md`

READ:

- `TaskDefinition` from `03b`
- `NormalizedProgram` selected by the definition's `program_sha256`; do not re-normalize or reformat
- `RenderConfig` → validated `PromptTemplateSet` (template version, file hash) and release `RenderSeed`

## 1 — Validate the template set

TRANSFORM:

- validate `prompts.yaml` per the template sub-document: exactly the known top-level, namespace, and template keys; namespaces exactly `dataset` and `evaluation`; a template ID starts with its namespace; no duplicate ID; at least one non-empty string variant; every placeholder used, declared, and typed; every `label.<table>` table present; every required P0 dataset ID present
- the first line of `dataset.prompt_shell` is the frame convention from the prompt-content sub-document and is the same for every task
- the file is answer-free and contains no gold answer, hidden identifier, variable name, or step count
- a missing template ID or an invalid placeholder stops the render before any row is written; it is a release defect, not a task rejection
- never fall back to a hardcoded string

WRITE:

- (none)

## 2 — Render

TRANSFORM:

- `task_render_seed = derive(release_seed, task_id)`; deterministic and part of the `04` version
- `variant_index = hash(template_id, task_render_seed) mod len(variants)`
- select templates by part and definition field:
  - prompt layout: `dataset.prompt_shell`
  - question: `dataset.question.<answer_meaning>`
  - property clue: `dataset.clue.property.threshold` when the check has `threshold`, `dataset.clue.property.range` when it has `range`
  - relation clue: `dataset.clue.relation`; comparison clue: `dataset.clue.comparison`
  - provenance clue: `dataset.clue.provenance.operation | profile | workplane` by the check field
  - choice description: `dataset.choice.description`, once per choice
  - answer instruction: `dataset.answer_instruction.multiple_choice`, `.number.with_unit`, `.number.unitless`, `.integer`, `.boolean`, `.coordinate`, or `.bounding_box`
- render the question, the numbered clue list, the choice list, and the answer instruction first; fill `dataset.prompt_shell` in this order: frame line, program text, question, clue list, choice list, answer instruction
- render clues in canonical order in P0; P1 applies a seeded permutation that respects reference dependencies, and clue wording uses presentation positions
- the frame line is the fixed first line of `dataset.prompt_shell`; it is not a per-task variant
- multiple choice: render `choice_pool` in its recorded order with its recorded labels; never reorder, relabel, re-bind an entity, or recompute an answer
- the rendered choice block has one line per pool entry, in pool order, with pool labels; a mismatch stops the render before any row is written; never reorder, relabel, or drop an entry to make it fit
- collapse a run of three or more newlines to two, so an empty choice list leaves one blank line before the answer instruction
- the prompt is answer-free and uses no variable name; a multiple-choice label is not answer data, because every label appears in the list

WRITE:

- (none)

## 3 — Project the release row

TRANSFORM:

- copy definition fields unchanged, including `clue_operand_form_profile`, `answer_schema_version`, and `answer_unit`
- copy `gold_answer`, `tolerance`, and `answer_evidence` as typed values; never re-serialize or recompute an answer value
- copy `answer_sha256`; never recompute it
- copy the label and the answer value of every choice-pool entry into `choices`; the descriptions stay in the prompt and `distinguishing_facts` stay in the definition
- `choices` is empty for every answer format other than multiple choice
- derive `clue_types` from `clue_operand_form_profile`, in the same order
- `prompt_sha256 = SHA-256(prompt UTF-8 bytes)` after rendering
- one row per `task_id`; rendering does not reject a definition
- a projection that needs a field the definition lacks is a `03b` defect

WRITE:

- `ReleaseTable` `(release_id)` → one row per task, in the release contract column order: `task_id, split, subset, prompt, prompt_sha256, program_id, program_sha256, cadevolve_program_family_id, task_reasoning_step_count, target_category, clue_types, clue_operand_form_profile, answer_format, choices (label, candidate), answer_meaning, geometry_required, gold_answer, answer_unit, tolerance, scoring_rule, answer_schema_version, answer_sha256, answer_evidence`
