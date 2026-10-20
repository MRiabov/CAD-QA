# Answer formats — intended set, implementation status, and history

**Status:** active, 2026-10-20. This is the canonical record of the answer-format
gap in the dataset-generation pipeline. Read it before changing answer formats or
wondering why a release contains only three formats.

## Intended set

`../glossary.md` and `specs/dataset-spec.md` define eight public answer formats.

| Format | Answer shape | Example | Typed tool |
|---|---|---|---|
| `candidate_label` | one label from a public shortlist of at most 7 | `D` | `submit_label` |
| `coordinate` | one 3D coordinate tuple | `(112, 0, 0)` | `submit_coordinate` |
| `text` | one source variable name | `wp13` | `submit_text` |
| `number` | one finite number | `2415.226715` | `submit_number` |
| `integer` | one non-negative integer | `7` | `submit_integer` |
| `boolean` | `true` or `false` | `true` | none |
| `bbox` | axis-aligned bounding box | `{"min": [...], "max": [...]}` | `submit_bbox` |
| `json` | compact structured object, including a CadQuery workplane state | `{"feature_id": ..., "origin": ...}` | `submit_workplane` |

`entity_id` is internal and is not a public answer format. `text` is one variable
name from the CadQuery program, not free-form prose; see
`../experiments/2026-10-19-cadqa-regen-1300.md` for why that distinction matters.

## Current implementation status

The generation pipeline is `dataset/`. The release used by the 2026-10-19
regeneration is `runs/regen_1300_traced_20261019/release_10k`.

| Format | Full pool | Release | Status |
|---|---:|---:|---|
| `candidate_label` | 122,287 | 4,300 | generated and released |
| `coordinate` | 55,352 | 3,569 | generated and released |
| `text` | 39,048 | 2,131 | generated and released |
| `number` | 2,092 | 0 | one family exists; every row fails the prompt policy |
| `integer` | 0 | 0 | no family |
| `boolean` | 0 | 0 | no family, and no typed tool |
| `bbox` | 0 | 0 | no family, and no gold-formatting branch |
| `json` | 0 | 0 | no family; validation rejects the format |

The `number` family is `parameterized_void_region_volume`. It selects the target
with a literal `operation_target = wp10` predicate, and the geometry-first prompt
policy rejects that as `literal_property_clause`. The numeric answer itself is
fine; the target selection is the problem.

## History

### Legacy generation, before 2026-04-30

The legacy `cad_qa/materialize.py` generated these task families:

- `bbox_after_step` (`answer_type="bbox"`);
- `topology_count_after_step` (`answer_type="integer"`);
- `workplane_state` (`answer_type="json"`);
- `point_membership` (`answer_type="enum"`: `inside`, `outside`, `on_boundary`);
- `coordinate_frame` (`answer_type="enum"`);
- `operation_count`, `selector_count`, and `signed_volume_delta`.

The rc10 export in `runs/gemma_bench/kaggle/dataset/rc10_zero_shot.jsonl` is the
evidence: it contains `bbox` (17 rows), `integer` (17), `json` (16), `number`
(16), `candidate_label` (17), and `text` (17). It contains no `boolean` rows and
no `coordinate` rows.

`point_membership` was an enum, not a boolean. The paper and the current glossary
describe point membership as boolean; the legacy code never emitted a boolean
answer.

### The graph-first reset cut the legacy families, 2026-04-30

Commit `a0187dd` (“Pruning and re-doing”, 2026-04-30) deleted
`cad_qa/materialize.py` (1,179 lines), `cad_qa/schema.py`, `cad_qa/graph_query.py`,
and the legacy dataset scripts. It introduced the graph-first CAD ontology,
resolver, materializer, and validator.

That rewrite did not port `bbox_after_step`, `topology_count_after_step`,
`workplane_state`, or `point_membership`. The commit message gives no rationale;
the replacement pipeline simply started from a smaller family set.

`bbox` and `integer` were therefore collateral of the reset. They were not
rejected as bad formats.

### Synthesis rebuilt a subset, 2026-05-24 and 2026-06-14

Commit `1e2b25a` (“Add parameterized query synthesis slice”, 2026-05-24) added
the first graph-first synthesis families. Commit `3165e9a` (“Add query answer
contracts”, 2026-06-14) added `AnswerSpec` helpers for `number`, `boolean`,
`integer`, `coordinate`, and `text`.

The helpers made the formats representable, but no synthesis family used
`integer`, `boolean`, `bbox`, or `json`. The graph-first families used
`candidate_label`, `coordinate`, and `text`; one later family used `number`.

### `json` was explicitly rejected, 2026-08-09

Commit `754bbbe` (“dataset: drop degenerate json (workplane_state) rows from
v3_curriculum + reject the format in validation”, 2026-08-09) removed the last
16 `cadqa_workplane_state_*` rows from `v3_curriculum` (1,445 to 1,429).

The golds were degenerate: `{base: "cq", coordinate_frame: <repr>}`. The json
baseline scored 0/113. The commit also added a validator guard that rejects
`answer_format="json"` so the format cannot be re-emitted.

`json` was therefore cut in the reset and then deliberately banned because the
surviving rows were unlearnable, not because the format is inherently bad.

### Regeneration, 2026-10-19

The regenerated release contains `candidate_label` (4,300), `coordinate` (3,569),
and `text` (2,131). It contains no `number`, `integer`, `boolean`, `bbox`, or
`json` rows. See `../experiments/2026-10-19-cadqa-regen-1300.md` for the full
release gates and the bounded-pool decision.

## Why each format is missing

| Format | Why it is missing |
|---|---|
| `integer` | Collateral of the graph-first reset; never reimplemented |
| `bbox` | Collateral of the graph-first reset; never reimplemented |
| `json` | Cut in the reset, then explicitly rejected because the remaining golds were degenerate |
| `boolean` | Never implemented end-to-end; the legacy point-membership task was an enum, and the typed tool contract has no boolean tool |
| `number` | One family exists, but it selects the target by a literal operation name and fails the geometry-first prompt policy |

## What restoring each format requires

| Format | Required work |
|---|---|
| `integer` | Add a count family that selects the target by geometry, an `AnswerSpec` with `mode="integer"`, a gold-answer branch, and `submit_integer` coverage |
| `bbox` | Add an AABB-after-feature family, a `format_gold_answer` branch for `bbox`, and `submit_bbox` coverage |
| `json` | Add a CadQuery workplane-state family with non-degenerate gold fields, a `format_gold_answer` branch, `submit_workplane` coverage, and replace the unconditional `json` rejection |
| `boolean` | Decide the actual boolean task (point membership is currently an enum), add `SubmitBooleanArgs`, `AnswerFormat.BOOLEAN`, tool mapping, extraction, and grading; or remove `boolean` from the intended set |
| `number` | Redesign `parameterized_void_region_volume` to select the target by a geometry predicate instead of a literal operation name |

## References

- `../glossary.md` — answer-format enum.
- `specs/dataset-spec.md` — answer-format policy.
- `train_and_eval/tool_calls.py` — typed tool contract and format-to-tool map.
- `dataset/query/answers.py` — `AnswerSpec`, synthesis format mapping, gold formatting.
- `dataset/prompts/wording_gates.py` — geometry-first prompt policy.
- Commit `a0187dd` — graph-first reset.
- Commit `1e2b25a` — first graph-first synthesis slice.
- Commit `3165e9a` — answer-contract helpers.
- Commit `754bbbe` — explicit `json` rejection.
