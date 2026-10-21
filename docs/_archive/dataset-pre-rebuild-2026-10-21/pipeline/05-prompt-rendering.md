# 05 — Prompt rendering

## Purpose

Render the public, answer-free prompt from a hidden Gold query program and a CadQuery
program, using approved YAML templates, and record which clue maps to which hidden
Gold query predicate.

## Inputs / outputs

- **Input:** `source_code` plus a `QueryProgram` (`pipeline/00-overview.md`); optionally the
  `OntologyGraph` to derive candidate lines.
- **Output (embedded, not a separate artifact):** a `RenderedPrompt`
  (`dataset/prompts/render.py::RenderedPrompt`) with `prompt`, `prompt_version`,
  `prompt_template_id`, `clue_map`, and `warnings`. Materialization embeds these into the
  row (`dataset/release/materialize.py::materialize_row`).

## Requirement

Prompts must be deterministic, answer-free, and faithful to the hidden query. Every public
clue must map to exactly one hidden Gold query predicate (or the aggregation/tie-break
step), high-hop prompts must not collapse distractors, private CAD ontology jargon must
not leak, and candidate choices must be bounded and include the gold target. Wording is
selected from approved
templates, not invented per row.

## Current status

**exists.** The renderer, templates, and wording gates are present and readable
(`dataset/prompts/render.py::render_prompt`,
`dataset/prompts/templates.py::checklist_prompt`,
`dataset/prompts/wording_gates.py`, root `prompt-templates.yaml`). No prompt render was
inspected while writing this doc.

## Verification

```bash
rtk uv run cadqa dataset preview runs/dataset/rows.parquet \
  --graphs runs/graph \
  --out runs/preview.md \
  --family parameterized_kernel_face_extreme \
  --sample-per-family 2 \
  --seed 17
```

Inspect `runs/preview.md` for prompt wording, Gold query predicate→clue maps, and candidate
lists. The focused tests are
`tests/test_graph_first_pipeline.py::test_prompt_templates_yaml_controls_generated_prompt_wording`,
`::test_prompt_template_variants_are_selected_from_sampled_parameters`,
`::test_render_prompt_hides_selector_set_and_count_boilerplate`, and
`::test_candidate_label_answers_bound_public_label_lists`.

## Local decisions

### D1 — Templates live in versioned YAML at the repo root

- **Status:** accepted.
- **Context:** Prompt wording is a dataset contract and must be reviewable and versioned.
- **Decision:** `dataset/prompts/templates.py::PROMPT_TEMPLATE_PATH` resolves to
  `<repo>/prompt-templates.yaml`; `PROMPT_VERSION` and `CHECKLIST_TEMPLATE_ID` are read from
  it and recorded on every row's `clue_map`.
- **Consequences:** Editing wording changes `prompt_version`; a missing required key raises
  at load (`prompt_template_registry`).

### D2 — Gold query predicate traceability is a validation contract

- **Status:** accepted.
- **Context:** A public clue that cannot be traced to a hidden Gold query predicate is a
  leak or a lie.
- **Decision:** `render_prompt` emits a `clue_map` whose entries carry `clause_id`,
  `clue_template_id`, and clue text; `dataset/prompts/wording_gates.py::clue_map_traceability_errors`
  checks the map against the query's Gold query predicate IDs plus
  `aggregation`/`tie_break_aggregation`.
- **Consequences:** Missing or unknown clue/Gold query predicate mappings are validation
  errors
  (`dataset/release/validate.py::validate_rows`).

### D3 — CadQuery selector set/count boilerplate is hidden from the public prompt

- **Status:** accepted.
- **Context:** Some clauses exist to make the graph query well-formed but expose no
  recoverable public information.
- **Decision:** `dataset/prompts/render.py::SKIPPED_PUBLIC_CLAUSE_IDS` filters those clauses
  before rendering.
- **Consequences:** The rendered prompt is shorter; the hidden query still contains them.

### D4 — Private CAD ontology terms are banned from public prompts

- **Status:** accepted.
- **Context:** `specs/benchmark-task-spec.md#prompt-requirements` requires visible CadQuery
  constructs rather than private CAD ontology jargon.
- **Decision:** `dataset/prompts/wording_gates.py::BANNED_PUBLIC_TERMS` flags terms such as
  `ontology`, `material_region`, `void_region`, and `measurement scope`; `render_prompt`
  records them as warnings and validation rejects them.
- **Consequences:** Prompt wording must ground concepts in constructs visible in the
  CadQuery program.

### D5 — Wording variants are sampled from private parameters

- **Status:** accepted.
- **Context:** A family must not permanently mean one view word or one phrasing.
- **Decision:** Template entries may be lists; the renderer selects a variant by the row's
  sampled `prompt_wording_variant` and records the rendered variant ID
  (`dataset/prompts/templates.py::_template_id_with_variant`).
- **Consequences:** Rendered wording is a sampled parameter reported for balance.

## Open questions

- **Q1.** **Human clarity of rendered prompts.** The templates in `prompt-templates.yaml` were
  LLM-authored and the owner, as a reader, cannot always tell what a rendered question is
  asking. Rewriting to unambiguous wording (then re-rendering and re-checking) is a
  precondition for freezing the benchmark; an ambiguous question cannot fairly judge an
  answer. See `development-context.md` Gaps and risks 8 and `_audit/owner-audit-todo.md` (E5).
- **Q2.** **Coupling to a root-level file.** `prompt-templates.yaml` sits at the repo root while its
  loader is inside `dataset/prompts/`; the path is computed with
  `parents[2]`. This is a packaging coupling worth documenting, not a bug found here.
- **Q3.** **Coverage of Gold query predicate templates.**
  `dataset/prompts/templates.py::clause_prompt` raises `KeyError` when a Gold query
  predicate has no template. Whether every Gold query predicate kind emitted by every
  synthesis family has a template is `[unknown]` without running synthesis + materialize
  across the full family set; preview/selfcheck evidence is the intended check.

## Resolved questions

None yet.

## Extra deliverables - P2

- A prompt-wording diff report that compares rendered prompts across wording variants per
  family for manual review.
