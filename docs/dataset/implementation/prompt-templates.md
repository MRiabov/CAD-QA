# Prompt templates

**Status:** draft, 2026-11-20. This document defines `generator/config/prompts.yaml`
artifact and the schema that `04` render prompt and choices validates. It is the
contract for prompt authors, `04`, and the evaluation harness.

## 1. What the file is

`prompts.yaml` is the only place for LLM-facing copy. It holds the prompt shell,
question templates, clue templates, choice descriptions, answer instructions,
label tables, and evaluation-harness instructions. In the generator this document
specifies, Go and Python code select a template ID and fill typed placeholders;
they do not contain question, clue, choice, or answer-instruction strings.

The file has two namespaces:

- `dataset`: read by `04` render prompt and choices when it renders a
  `TaskDefinition` into a release row. `03b` construct task definitions does not
  read it: the definition carries typed facts, not sentences.
- `evaluation`: read by the evaluation harness. The dataset release does not read
  it. The dataset supplies no system prompt (`DS-REQ-24`); the evaluation harness may
  add its own copy from this namespace.

The file is answer-free. It contains no gold answer, answer value, hidden
identifier, variable name, or task reasoning step count. `05` validate and export
release checks the rendered prompt against the same rule.

The file is data, not code. A wording change edits this file and bumps its
`version`; it does not edit Go or Python.

The relevant decisions are `DS-REQ-05` (no variable names), `TG-7` (canonical clue
order and presentation order), and `DS-REQ-24` (the prompt is the user message), in
[`../requirements/decisions.md`](../requirements/decisions.md) and
[`pipeline/03-task-generation/decisions.md`](pipeline/03-task-generation/decisions.md).

The legacy root `prompt-templates.yaml` belonged to the pre-rebuild pipeline and
was deleted on 2026-11-24. It was not an alias for this file and is not part of
this contract.

## 2. File shape

A minimal file looks like this:

```yaml
schema_version: 2
version: cadqa_prompt_v10

namespaces:
  dataset:
    labels:
      target_category:
        face: "face"
    templates:
      dataset.question.volume:
        variants:
          - "What is the volume of the target {{target_label}}?"
        placeholders:
          target_label: label.target_category
  evaluation:
    labels: {}
    templates:
      evaluation.system.no_cadquery:
        variants:
          - "Do not use CadQuery or any other CAD library."
        placeholders: {}
```

The top-level mapping has exactly three keys:

| Key | Value | Rule |
|---|---|---|
| `schema_version` | integer | Bumped when the file's structure or placeholder forms change. |
| `version` | string | The prompt template version. Bumped when rendered copy changes. |
| `namespaces` | mapping | Exactly `dataset` and `evaluation`. |

Each namespace has exactly two keys:

| Key | Value | Rule |
|---|---|---|
| `labels` | mapping of label table name to a mapping of key to label | Display copy for `label.<table>` placeholders. `{}` when the namespace uses no labels. |
| `templates` | mapping of template ID to template | The templates for that namespace. |

Each template has exactly two keys:

| Key | Value | Rule |
|---|---|---|
| `variants` | non-empty list of strings | Wording variants. Every variant must use the same declared placeholders. |
| `placeholders` | mapping of placeholder name to placeholder form | `{}` when the template has no placeholders. Every placeholder is declared and typed. |

Unknown keys are rejected at every level. A misspelled `placeholder` or
`variant` key is a validation error, not a silently ignored field.

The file is UTF-8 YAML. Comments are allowed and are part of the file bytes, so
they change the file hash. Comments do not change the template version.

The in-memory `PromptTemplateSet` mirrors this shape: one entry per namespace,
label table, template, variant, and placeholder form. It is the `04` input model
named in [`pipeline/io-contracts.md`](pipeline/io-contracts.md).

## 3. Template IDs

A template ID is the key under `templates`. It has three parts:

```text
<namespace>.<group>.<name>
```

- `<namespace>` is `dataset` or `evaluation`.
- `<group>` is the prompt part: `prompt_shell`, `question`, `clue`, `choice`,
  `answer_instruction`, `system`, or `submission`.
- `<name>` is a stable lower-case name, with dots for a sub-case.

The ID must start with the namespace that contains it. For example,
`dataset.question.volume` is valid under `namespaces.dataset.templates`, and
`evaluation.question.volume` is not.

The ID is stable. A rename is a new template ID and bumps `version`. The ID is
recorded in the release provenance; a variant is recorded as `id` when the
template has one variant and `id.variant_<n>` when a later variant is selected.
The variant index starts at 0.

The required P0 IDs are the selection table in section 6 and the P0 question IDs
below it. A missing required ID is a validation error, so a partial file cannot
ship.

## 4. Placeholders

A placeholder is written `{{name}}`. A single `{` or `}` is literal text. The
double-brace form keeps JSON examples in answer instructions readable: the
rendered prompt has single braces, and the template does not escape them.

Every placeholder used in a variant must be declared in `placeholders`, and every
declared placeholder must be used in every variant. The validator rejects:

- a placeholder used in a variant but not declared (missing declaration);
- a placeholder declared but not used in a variant (extra declaration);
- a placeholder declared with no form or an unknown form (untyped);
- a placeholder used in one variant but not another (inconsistent variant);
- a malformed `{{` or `}}`.

The placeholder forms are:

| Form | Value the renderer passes | Renderer rule |
|---|---|---|
| `text` | already-rendered text | Inserted as-is. The inserted text is answer-free and uses no variable name. |
| `label.<table>` | a key into the named label table | The renderer looks up the key in that table and inserts the label. A missing key is a task defect. |
| `number` | a finite number | Formatted at the task's stated precision. |
| `integer` | an integer | Formatted as a decimal integer. |
| `boolean` | a boolean | Rendered as `true` or `false`. |
| `coordinate` | three finite numbers, each with its recorded canonical decimal text | Rendered as `(x, y, z)` in the program frame. A probe point is inserted from its recorded text and is never re-rounded, so the prompt shows the point the kernel classified. |
| `reference` | a binding reference plus its clue reduction form | Rendered as a bare noun phrase such as `target face`, `cylindrical face`, or `faces from clue 2`. |
| `list` | an ordered list of rendered strings | One item per line, with no added marker. |
| `numbered_list` | an ordered list of rendered strings | One item per line, prefixed `1.`, `2.`, and so on. |
| `code` | program text | Inserted verbatim. The template supplies the fenced block and language tag. |

The renderer validates the passed entry against the declared form before it
formats the template. A `number` placeholder cannot receive a string; a
`label.metric` placeholder cannot receive a key from another table. This is what
makes the placeholders typed: the template names the placeholder form, and the
renderer refuses an entry that does not fit.

`text` is for a description or a sentence that another part of `04` has already
rendered. `label.<table>` is for a closed display table. A choice description, an
operation description, and a CadQuery profile description are `text`; a metric
name, a relation name, a comparator, a unit, and a target category are
`label.<table>`.

A `text` placeholder that names an entity is a full noun phrase with its
determiner, for example `the box operation` or `the circular CadQuery profile`.
`03b` supplies the prompt-safe description; `04` does not invent one.

The determiner follows what the description selects. It is definite only when the
description selects exactly one element of that category in the program, as one
`box` call makes `the box operation` unique. A description that can select
several is indefinite, as two `cutBlind` calls make `a cutBlind operation`; a
description that selects several and must mean all of them is plural.

A `reference` value is a full noun phrase with the determiner the rule chose, so
a template never adds an article before `{{subject}}` or `{{reference}}`. The
renderer builds it from the `BindingRef` and the clue reduction form (`filtered`,
`selected_in_earlier_clue`, `aggregated`, or `cross_state`). It chooses `the`
when the condition selects exactly one element of the category in the program, and
`a` when it selects several; a set bound by an earlier clue is plural. A clue
sentence begins with its subject, so the renderer capitalizes the first character
of the rendered sentence. The allowed forms are:

- `target <category>` for the task target;
- `<face surface kind> <category>`, such as `cylindrical face`;
- `<category> facing <axis>`, such as `face facing +z`, for a face whose outward
  normal is along that axis;
- `<category> whose outward normal is <comparator> <value> degrees of <axis>`,
  such as `face whose outward normal is within 45 degrees of +z`;
- `<category> whose <metric> is <comparator> <value>`, such as
  `face whose area is greater than 10`;
- `<category> touching the <position> of the axis-aligned bounding box`, such as
  `face touching the top of the axis-aligned bounding box`;
- `<categories> from clue N` for an earlier clue's result;
- `the <extreme> of the faces from clue N`, such as
  `the largest of the faces from clue 1`, for an `aggregated` face reference
  (P1).

A filtered reference is a set, and its article follows the set size: `the` for
one element ("the cylindrical face" when the program has one), `a` for several
("a face facing +z" when several do). A set bound by an earlier clue is plural
("the faces from clue 1"). It uses the presentation position,
not the canonical position, for that plural (`TG-7`). A reference never uses a
position as a proper noun ("the top face"); the touching form above is the
condition. The template never builds a reference from a graph identifier.

## 5. Label tables

A label table is a mapping from a stable key to a non-empty display string. The
key is the graph, task, or display value the renderer uses to choose the label;
the string is the copy the LLM model reads. The table is data in `prompts.yaml`,
not a Go or Python map.

The P0 label tables are:

| Table | Key examples | Used by |
|---|---|---|
| `target_category` | `face`, `edge`, `solid_state`, `operation` | `label.target_category` |
| `metric` | `volume`, `face_area`, `distance`, `face_count`, `centroid_x` | `label.metric` |
| `comparator` | `gt`, `ge`, `lt`, `le`, `eq` | `label.comparator` |
| `relation` | `adjacent_to`, `has_edge`, `has_vertex` | `label.relation` |
| `unit` | `mm`, `mm2`, `mm3`, `deg` | `label.unit` |
| `position_parameter` | `face_centroid`, `edge_midpoint`, `vertex_point`, `solid_state_centroid` | `label.position_parameter` |
| `counted_entity` | `face`, `edge`, `vertex`, `selected_entity` | `label.counted_entity` |
| `frame` | `program_frame` | `label.frame` |
| `face_surface_kind` | `plane`, `cylinder`, `cone` | `label.face_surface_kind` |
| `axis` | `+x`, `-x`, `+y`, `-y`, `+z`, `-z` | `label.axis` |
| `frame_position` | `min_x`…`max_z` | `label.frame_position` |
| `choice_label` | `A`, `B`, `C` | `label.choice_label` |

A label table is not a vocabulary of allowed graph values. The CAD graph owns
that vocabulary. The table is the display layer: a value with no row is a
validation error at render time, so a new measurement or relation cannot
silently fall back to an underscore-replaced identifier.

The label tables are a closed set. Schema version 2 added
`face_surface_kind`, `axis`, and `frame_position`, and `prompts.yaml` declares
them. One value has no label on purpose: `face_surface_kind` has no `other`,
because the face surface kind has no adjective, and a task that would name an
`other` face is a render-time task defect. A new table is a schema change: bump
`schema_version` and `version`, and add the renderer support.

## 6. Templates and selection

`04` selects a template by the part it is rendering and by a task-definition
field. The selection is deterministic; it does not use an LLM.

| Rendered part | Template ID | Selection rule |
|---|---|---|
| Prompt layout | `dataset.prompt_shell` | Always. |
| Question | `dataset.question.<answer_meaning>` | `answer_meaning` from the definition. |
| Property clue, threshold | `dataset.clue.property.threshold` | `clue_type=property`, check has `threshold`. |
| Property clue, range | `dataset.clue.property.range` | `clue_type=property`, check has `range`. |
| Property clue, face surface kind | `dataset.clue.property.face_surface_kind` | `clue_type=property`, check is a categorical feature `face_surface_kind`. |
| Property clue, direction | `dataset.clue.property.direction` | `clue_type=property`, check is an `angle` measurement against a program axis. |
| Property clue, position | `dataset.clue.property.position` | `clue_type=property`, check is a categorical feature `position`. |
| Relation clue, angle | `dataset.clue.relation.angle` | `clue_type=relation`, check is an `angle` measurement. |
| Relation clue, named | `dataset.clue.relation` | `clue_type=relation`, check is a named relation. |
| Comparison clue | `dataset.clue.comparison` | `clue_type=comparison`. |
| Provenance clue, operation | `dataset.clue.provenance.operation` | `clue_type=provenance`, check has `operation_id`. |
| Provenance clue, CadQuery profile | `dataset.clue.provenance.profile` | `clue_type=provenance`, check has `profile_id`. |
| Choice description | `dataset.choice.description` | `answer_format=multiple_choice`; once per choice. |
| Answer instruction, multiple choice | `dataset.answer_instruction.multiple_choice` | `answer_format=multiple_choice`. |
| Answer instruction, number with a unit | `dataset.answer_instruction.number.with_unit` | `answer_format=number` and `answer_unit` is not null. |
| Answer instruction, number without a unit | `dataset.answer_instruction.number.unitless` | `answer_format=number` and `answer_unit` is null. |
| Answer instruction, integer | `dataset.answer_instruction.integer` | `answer_format=integer`. |
| Answer instruction, yes or no | `dataset.answer_instruction.boolean` | `answer_format=boolean`. |
| Answer instruction, 3D coordinate | `dataset.answer_instruction.coordinate` | `answer_format=coordinate`. |
| Answer instruction, bounding box | `dataset.answer_instruction.bounding_box` | `answer_format=bounding_box`. |
| Evaluation system prompt | `evaluation.system.no_cadquery` | The evaluation harness, when it adds a system prompt. |
| Evaluation submission instruction | `evaluation.submission.answer` | The evaluation harness, when it asks for a submission. |

The P0 question IDs are `identity`, `volume`, `area`, `length`, `distance`,
`angle`, `count`, `membership`, `position`, `extent`, `material_change`, and
`topology_change`. A later-priority answer meaning adds its question ID when its
scope ships; it does not reuse another meaning's template.

The three property templates above (face surface kind, direction, position) and
the three label tables they use are schema version 2, and `prompts.yaml` ships
them. The pair-angle relation template `dataset.clue.relation.angle` is added
with `cadqa_prompt_v10`; it uses `label.comparator` and `reference`, so the
schema does not change. The P1 aggregation
clue templates (`dataset.clue.aggregation.extreme` and
`dataset.clue.aggregation.rank`) and the P2 validity question
(`dataset.question.validity`) are added when their scope ships. A count is an
answer meaning, not a clue, while `task-structure.md` section 8 leaves that
question open; it gets a clue template only if the question resolves in its
favour. The schema does not change; only the template set and `version` do.

The prompt shell is the only template that contains `code`, `list`, and
`numbered_list` placeholders for the whole prompt. It places the frame convention,
the program text, the question, the numbered clue list, the choice list, and the
answer instruction in that order. The frame convention is the first line and
matches `prompt-content.md` section 1.1. The shell has one variant in P0; a
layout change is a version change, not a seed-selected wording variant.

The `target_label` value is the prompt-safe description of the bound subject. For
a scalar target it is the subject's category, not the enum key `scalar_value`;
the release `target_category` remains `scalar_value`.

## 7. Variants

A template has one or more variants. Variants are alternate wording for the same
template ID and the same placeholders. `04` selects one variant
deterministically from the template ID and the task render seed, for example
`variant_index = hash(template_id, task_render_seed) mod len(variants)`. The task
render seed is derived from the release render seed and `task_id`. The exact
hash belongs to `04`; the contract is that the same task and release seed always
select the same variant.

Every variant must use exactly the declared placeholders. A variant that drops a
placeholder is rejected even if another variant uses it: the release must not
depend on which variant the seed picks.

A template with one variant may still use the list form. The file has one shape
for every template, so a later wording variant is a data addition, not a schema
change.

Variants are answer-free and use no variable name. They do not contain a task
reasoning step count, a hidden identifier, or a hint that identifies a
multiple-choice choice.

## 8. Validation

`04` validates the file before it renders any task. The validation rejects:

- a missing or unknown top-level key, namespace key, or template key;
- a `schema_version` that is not a positive integer;
- an empty `version`;
- a namespace other than `dataset` or `evaluation`;
- a template ID that does not start with its namespace;
- a duplicate template ID;
- a template with no variants, or a variant that is empty or not a string;
- a placeholder used in a variant but not declared;
- a placeholder declared but not used in a variant;
- a placeholder with no form, or a form outside the closed set;
- a `label.<table>` form whose table is absent from the namespace;
- a label table with an empty key or an empty label;
- a missing required P0 or evaluation template ID.

A malformed file is a release defect, not a task defect. `04` stops before it
writes a release row and names the file, the template ID, and the placeholder.
It does not fall back to a hardcoded string.

`05` validate and export release rechecks the rendered prompt: it is answer-free,
it contains no hidden identifier, and the manifest records the prompt template
version and `prompts.yaml` hash. A mismatch blocks the export.

## 9. Versioning and the release

`version` is the prompt template version. Bump it when rendered copy changes: a
variant is added or edited, a label changes, a template is added or removed, or
the selection rule changes which template a task uses. A comment-only edit does
not bump `version`.

`schema_version` is the file structure version. Bump it when a required key, a
placeholder form, a label table, or a namespace rule changes. A schema change
also bumps `version`, because the renderer changes.

The release manifest records `version` and the SHA-256 of the file bytes. The
file hash identifies the exact artifact; the version identifies the copy
semantics. A release row's `prompt_sha256` identifies the rendered prompt. The
three values together make a prompt reproducible.

## 10. Evaluation namespace

The evaluation namespace follows the same schema, validation, and answer-free
rule. It is not part of the dataset release. The dataset supplies no system
prompt (`DS-REQ-24`); the evaluation harness may add one from
`evaluation.system.no_cadquery`, and it may add a submission instruction from
`evaluation.submission.answer`.

The evaluation harness owns the evaluation copy. A change to an evaluation
template bumps `version` but does not change a dataset release row, because the
dataset namespace and the rendered prompt are unchanged. The manifest's file hash
changes, so the artifact still names the exact copy that produced the release.

## 11. Adding or changing a template

To add a P0 template:

1. Add the template under the namespace's `templates` mapping. Use the next
   stable ID in the group.
2. Declare every placeholder with a form. Use `label.<table>` for closed display
   copy and `text` for a rendered description.
3. Add a row to the selection table in section 6 if the template covers a new
   task-definition value.
4. Add the required ID to the validator's required list if the template is part
   of the P0 contract.
5. Bump `version`.
6. Run the Go prompt-template loader test and the docs checks. That test is
   `missing` until `04` lands; there is no Python prompt validator.

To change wording, edit an existing variant or add a new one; do not add a new
template ID for the same prompt part. To change the prompt layout, edit
`dataset.prompt_shell`; do not hardcode the change in `04`.

## 12. What is not here

- Task construction and answer resolution: `03b` construct task definitions.
- Release validation and export: `05` validate and export release.
- The release consumer contract: `../requirements/release-dataset-contract.md`.
- The prompt content requirements: `../requirements/prompt-content.md`.
