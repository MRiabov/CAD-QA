# Scratch experiment: can a frontier LLM model write CadQuery queries, by task reasoning step count?

**Status:** plan, 2026-10-22. This is a disposable experiment, not a dataset release. It answers
one question: does the kernel-query pivot (`docs/dataset/requirements/PRD.md`, KI1) have headroom?
It runs on real CADEvolve programs before any spec is rewritten.

**Spec alignment.** The experiment follows the dataset specs in `docs/dataset/`, in their
terminology (`requirements/terminology.md`), so its logic rests on reviewed contracts rather than
new inventions. Confidence differs by pipeline stage:

| Pipeline stage | Spec state | How this experiment uses it |
|---|---|---|
| `01` ETL (`01b`, `01d`) | mostly reviewed | Follows the selection and normalization rules on a small pool. |
| `02` extraction (`02a`, `02b`) | most reviewed | Follows the accepted AST subset, entity identity, topology, and canonicalization contracts for every fact a task uses. |
| `03b` task definitions | draft, not yet reviewed | Uses the typed task-clue schema, the narrowing and uniqueness rules, and step accounting. A deviation is listed under *Deviations* below, never silent. |
| `04` rendering | draft, not yet reviewed | Uses the rule that prompt copy lives in YAML and variants are chosen deterministically. |

## Question

Given the program text and a task, can `deepseek/deepseek-v4.1-flash-1017` write a CadQuery query
that, run after the program, returns the gold answer? How does accuracy change with the task
reasoning step count? The model is called through OpenRouter at $0.30 / $1.20 per million
input/output tokens.

## Scope

- **300 tasks** at task reasoning step counts **1, 3, 5, 7, 9**, 60 tasks per count. That gives a
  Wilson 95% CI of about ±12.5 percentage points per level.
- One model and one sample per task. The model gets no execution feedback: it makes one tool call
  and is graded on it.
- **Task generation is deterministic.** The same inputs, seed, and versions must give a
  byte-identical `tasks.jsonl`, and a test asserts this. The model's outputs are not deterministic;
  they are recorded instead.
- Out of scope: training, other models, release planning (`03a`), deficit handling (`03c`), and
  multiple-choice answers.

## Inputs and the existing extracted data

- The program pool comes from the 2026-10-19 regeneration (`runs/regen_1300_traced_20261019/`).
  Its `sources.parquet`, `traces_combined.parquet`, and `graph/graphs/*.parquet` are used only to
  pick programs. A program qualifies if its trace succeeded and its graph has final-state faces
  whose count matches the trace.
- That data came from the superseded generator (`dataset/SUPERSEDED.md`). A 2026-10-22 audit found
  it unfit as a source of task facts:

  | Fact | Old graphs |
  |---|---|
  | Final-state faces present | 776 of 1,259 CADEvolve-C graphs (750 with an exact face count) |
  | Graph faces matched one-to-one to kernel faces by bounding box | 787/787 (30-program kernel sample) |
  | `parallel_to` / `perpendicular_to` correct | 100%, but only planar faces carry them |
  | `adjacent_to` claims that are true | 765/784 (98%) |
  | Real adjacencies the graph contains | 765/1,706 (45%) |
  | Face area present / correct where present | 462/787 (59%) / 332/462 (72%) |
  | Face→edge relation | missing in all 1,300 graphs |
  | Face provenance (which operation created a face) | missing in all 1,300 graphs |

  With adjacency incomplete and areas wrong, narrowing and uniqueness checks computed from the
  graph would be wrong, and provenance clues would be impossible. So no task fact is read from the
  old graph.
- Every fact a task clue or gold answer depends on is recomputed with the CadQuery kernel, following
  the `02b` rules:
  - shape snapshots per solid state;
  - CAD topology entity IDs from the `entities.md` fingerprints, using the `canonicalization.md`
    hashing and 9-decimal rounding;
  - the topology records from `topology.md` (`face_has_edge`, `edge_has_vertex`,
    `face_adjacent_to_face`);
  - CAD feature solid state effect deltas.
- This is a minimal, spec-conformant slice of `02b`, kept inside the experiment. It is not the
  production `02` implementation, and it is not imported by `dataset/`.

## Program pool (`01b`/`01d` rules on a small pool)

1. Candidates: programs in the 1,300-program regeneration that are tier C (from `source_subtree`),
   whose trace succeeded, and whose old graph has final-state faces matching the trace face count.
   The final state is found by following `result = wpN` aliases.
2. Keep a program only if it passes the `02a` accepted subset (flat, one CadQuery call per
   assignment, no control flow, face/edge/vertex selectors only), checked with the Python AST.
   Rejected programs are recorded with the reason.
3. Apply the `01b` rules:
   - dedupe by `normalized_source_code_hash` within each collection, keeping the smallest
     `source_id`;
   - cap programs at two per `cadevolve_program_family_id`, derived from `path_family` as `01b`
     defines;
   - order by `sha256(seed || source_id)` with seed `cadqa-cq-scratch-20261022`.
4. Normalize with `01d` (`ast.unparse`, pinned `ruff format`, one trailing newline). The program
   text in the prompt is the normalized text.
5. Take the first **80 programs** in hash order with at least 8 faces in the final solid state,
   trying to cover all three C collections. Record any collection shortfall.

## Task definitions (`03b` schema)

Each task is a `TaskDefinition` with these fields:

- `target_category`;
- `target_binding`;
- ordered `clues`, each a typed `TaskClue` with `clue_type`, `subject`, `check`, and `result`;
- `answer_meaning`, `answer_step`, `native_answer_format`;
- `gold_answer`, `tolerance`, `answer_evidence`;
- `clue_step_count`, `task_reasoning_step_count`;
- `validity`, `provenance`.

It also carries one experiment-only field, `gold_query`: the CadQuery code the definition compiles
to.

**Step accounting** (`task-structure.md` §2.5):
`task_reasoning_step_count = clue_step_count + 1` when there is an answer step. So:

| Step count | Clue steps | Example |
|---|---|---|
| 1 | 0, answer step only | "the volume of the final solid state" |
| 3 | 2 | |
| 5 | 4 | |
| 7 | 6 | |
| 9 | 8 | |

The comparison reference rule in task-structure Q1 applies: a reference to an earlier result does
not add a step.

**Scope of values.** Only P0 inputs that compile to CadQuery are used:

| Dimension | Values |
|---|---|
| Task target category | face, edge, vertex, solid state, operation (via its solid state), scalar value |
| Clue type: property | surface or curve kind; orientation relative to a named workplane axis; measurement threshold |
| Clue type: relation | `has_edge`, `has_vertex`, `adjacent_to`, `parallel_to`, `perpendicular_to` |
| Clue type: comparison | measurement against a reference |
| Clue type: provenance | created by the operation on line N (definition below) |
| Clue type: aggregation (P1) | extreme, used only as the final clue |
| Answer meaning | volume, area, length, distance, count, position, material change, topology change |
| Answer format | number, integer, 3D coordinate (no multiple choice in the scratch run) |

`has_edge` and `has_vertex` are used only as one step inside a longer chain (for example, "the
longest edge of the face adjacent to …"), never as a whole task.

**Exact clue meanings.** Every clue whose meaning depends on a tolerance or a convention carries
its definition in the prompt, so a model failure cannot come from guessing our convention:

| Clue | Definition stated in the prompt |
|---|---|
| parallel / perpendicular | Angle between normals (faces) or directions (edges) within 0.1° of 0° / 90°; planar faces and straight edges only. |
| same length / same area, larger / smaller | Relative tolerance 1e-3. |
| adjacent faces | The faces share an edge. |
| created by the operation on line N | A face of the shape after line N whose geometry (centroid, area, normal, bounding box at 1e-6) matches no face of the shape before line N. A face that was only trimmed or split counts as created, because its geometry changed. |

**Provenance is expected to be the hardest clue type.** CadQuery 2.7 has no public selector for
"faces made by this operation". OpenCascade's `Modified()`/`Generated()` history is used only
internally (`occ_impl/assembly.py`, `occ_impl/shapes.py`), and the CADEvolve programs discard the
builder. So the model must compare the before and after shapes by geometry itself. Gold provenance
uses the same geometric rule at extraction time. build123d's `Select.LAST`/`Select.NEW`
(recalled from memory, not checked here) would make this clue nearly a one-liner. That difference is
worth reporting if a build123d variant is ever run.

**Validity** follows `03b`:

- every clue narrows the set of possible answers (`after < before`);
- the final possible-answer set has exactly one entity;
- the answer step produces exactly one answer;
- at least one clue depends on the built shape (`geometry_required`).

The experiment adds one rule: the `gold_query`, executed in a fresh child process, must reproduce
`gold_answer`. A definition that fails any check is written to `failures.jsonl` with its reason.

**Deterministic construction.**

- Constructors run in a fixed order.
- Candidate operands are ordered by the canonical entity order (category rank, then
  `fingerprint_json`, then `entity_id`).
- Every sampling choice takes the first item in `sha256(seed || program_id || step_count || slot)`
  order. Python's `random` module is not used.
- Duplicates are removed by the `03b` canonical identity, and up to 60 tasks are accepted per step
  count in identity-hash order, with at most 3 per program per step count.

## Rendering (`04` rules)

- **Prompt copy.** All wording lives in `experiments/cq_query_scratch/prompts.yaml`, with
  separate `dataset` and `eval` namespaces, stable template IDs, and typed placeholders. Template
  variants are chosen by `sha256(template_id || seed)`. The YAML hash is recorded in the run
  manifest.
- **Prompt layout.** The prompt contains the normalized program text, one question, the task clues
  as a numbered list (one condition per item), and the answer instruction.
- **Clue wording.** Clues name operations as the specs do (`` the face created by `cutBlind` on
  line 12 ``). They never contain CadQuery selector strings such as `>Z` or `%CIRCLE`, so the task
  is not string translation. Each clue that needs one is followed by its definition from the table
  above.
- **Answer instruction (`eval` namespace).** Call `submit_query(code: str)` once. The code runs
  after the program in the same namespace and must assign the answer to `answer`. A fixed CadQuery
  cheat sheet (selector grammar, `.vals()`, `Area()`, `Length()`, `Center()`, `distance`) is part of
  the eval template, identical for any model that is evaluated later.

## Running the model and grading

1. **Call.** Reuse `train_and_eval/teacher.py::TeacherClient` with
   `model="deepseek/deepseek-v4.1-flash-1017"`, temperature 1.0 and top-p 0.95 (model card), and a
   native `tools=[submit_query]`. Check `balance()` before each stage. Write one `calls.jsonl`
   record per call, holding the reasoning, the visible content, the raw tool calls, tokens, cost and
   latency. Resume by `task_id`.
2. **Execute.** Run `program + query` in a child process with the `02b` limits (30 s, 2 GiB). As in
   `02b`, this is process isolation, not a security sandbox; that is acceptable for a scratch run
   with a hosted model.
3. **Grade** with the definition's `tolerance` and scoring rule: 1e-3 relative / 1e-6 absolute for
   numbers, exact for integers, per component for coordinates. Flag `literal_answer` when an AST
   check finds `answer` assigned a bare constant.
4. **Outcomes:** `no_tool_call`, `exec_error`, `timeout`, `literal_answer`, `wrong`, `correct`.

## Report (per task reasoning step count)

- **Funnel:**
  - definitions constructed;
  - valid definitions, with rejections by reason;
  - definitions accepted;
  - calls that returned a tool call;
  - queries that executed;
  - correct answers.
- Accuracy with a Wilson 95% CI.
- Breakdowns by clue type, answer meaning, and target category. These are informative only; with
  60 tasks per level they are too small to support claims.
- Reasoning tokens, cost, and `exec_error` subtypes: hallucinated API, selector syntax, other.

## Staged run (difficulty gates)

| Stage | Tasks | Purpose |
|---|---|---|
| 0. Smoke | 5 at step count 1 | End-to-end plumbing; about $0.01 |
| A | 60 at step count 3 | First real level |
| B | 60 at step count 5 | |
| C | 60 at step count 7 | |
| D | 60 at step count 1, 60 at step count 9 | Ends of the curve |

**Gate for stages A–C.** A level passes only when all of these hold:

- 60/60 definitions are valid and the gold queries reproduce the gold answers;
- at least 95% of calls return a parseable tool call;
- every failed task is triaged as a model error, a harness bug, or a definition/prompt bug, and no
  harness or definition/prompt bugs remain (they are fixed and the level is rerun);
- a manual read of 10 prompts finds them unambiguous;
- model accuracy is **at least 50%** (an assumption; adjust after stage A).

If accuracy is below 50%, stop and check whether the failures come from prompt ambiguity or real
difficulty before moving to a higher step count.

## Cost and time

- Model calls: about 300 × (~3k input + ~4k output tokens) ≈ $2, with a hard stop at $5.
- Kernel work is CPU-only: the `02b`-slice extraction for 80 programs plus about 600 query
  executions.
- **Thermal limits.** The laptop overheated during the first full audit run. All kernel work runs
  throttled:
  - `nice -n 19`, `OMP_NUM_THREADS=1`;
  - at most 2 child processes at a time;
  - a 1–2 s pause between programs;
  - no loading of all graph shards at once.

  At this rate the work takes roughly 1–2 hours, and it runs in the background.
- Monitor long runs every 3–5 minutes.

## Code (`experiments/cq_query_scratch/`)

| Module | Responsibility |
|---|---|
| Module | Responsibility | Lines (estimate) |
|---|---|---|
| `pool.py` | Program pool: `01b`/`01d` rules, the `02a` subset check, old-graph final-face filter. | ~120 |
| `extract.py` | The `02b`/`02c` slice: states, entities, face→edge, adjacency, parallel/perpendicular, provenance, effects, canonical IDs. | ~250 |
| `definitions.py` | `TaskDefinition`, `TaskClue`, and the constructors. | ~350 |
| `compile_query.py` | Clue and answer step → CadQuery. | ~200 |
| `render.py` (+ `prompts.yaml`, ~60 lines) | Rendering from `prompts.yaml`. | ~80 |
| `run_eval.py` | Model calls, execution, grading. | ~200 |
| `report.py` | Funnel and accuracy report. | ~100 |
| `tests/test_cq_query_scratch.py` | E2E test. | ~150 |

Total: about **1.4–1.9k lines**. Most of the bug risk sits in `definitions.py` and
`compile_query.py`, which the stage gates are designed to catch.

Code rules:

- Use Pydantic models with `Field()` constraints.
- Use StrEnums for clue type, answer meaning, answer format, target category, and outcome, with
  values spelled as in the specs.
- Use stdlib `logging`; the repo has no structlog.
- Keep each module under 800 lines.

**E2E test** (`tests/test_cq_query_scratch.py`). Use a small flat CADEvolve-C-style fixture and real
CadQuery, with only the LLM mocked. The test covers:

- the pool checks;
- the extraction IDs matching the `canonicalization.md` formulas;
- constructing tasks at step counts 1, 3 and 5;
- a non-narrowing clue being rejected;
- a gold query grading `correct`;
- a constant answer grading `literal_answer`;
- **two generation runs giving byte-identical `tasks.jsonl`**;
- the report funnel counts.

## Outputs

- Data (gitignored): `runs/cq_query_scratch_20261022/` holding:
  - `pool.parquet`;
  - `extraction/`;
  - `tasks.jsonl` and `failures.jsonl`;
  - `calls.jsonl` and `grades.jsonl`;
  - `report.md`;
  - `manifest.json`, recording the seed, versions, and the `prompts.yaml` hash.
- Record: `docs/experiments/2026-10-22-cq-query-scratch.md`, containing:
  - the funnel and accuracy tables;
  - the failure taxonomy;
  - cost;
  - five example tasks with model outputs;
  - the headroom verdict.

## Deviations from the specs (deliberate)

- **A throwaway Python slice of `02c`, not the Go implementation.** Tasks need five relations
  (`has_edge`, `adjacent_to`, `parallel_to`, `perpendicular_to`, `creates`) and the `02b`
  measurements. They are computed in Python by the `graph-construction.md` rules, without UUIDv5
  graph IDs or graph Parquet persistence. This is a partial `02c`, written for the experiment and
  deleted or replaced when the real Go `02c` exists.
- **Old graph artifacts select programs only.** They are not used for task facts; the audit numbers
  are under *Inputs* above.
- **Small pool.** 80 programs instead of the `01b` 1,500. The tag reservations and collection
  minima are recorded, not enforced.
- **No release planning or splits.** `03a` and `03c` are skipped, and the 60-per-level quota is
  fixed.
- **`gold_query` is an extra `TaskDefinition` field.** It does not exist in `03b` yet. If the pivot
  goes ahead, it becomes a spec change.
- **No multiple choice.** The scratch run uses native answer formats only.

## Expected results (guesses, recorded before the run)

| Step count | Guessed accuracy |
|---|---|
| 1 | 90–98% |
| 3 | 80–90% |
| 5 | 70–85% |
| 7 | 60–80% |
| 9 | 50–75% |

- Expected failure types:
  - wrong CadQuery API calls (10–20% before cheat-sheet tuning, independent of step count);
  - adjacency and provenance clues, which have no direct CadQuery selector;
  - definition and wording bugs found in stage A.
- The base 2–4B model is expected to score far lower; that is measured in the follow-up spike, not
  here.

## Decision this informs

- **Accuracy stays high (≥ 90%) up to step count 9:** writing queries is not the bottleneck. The
  pivot needs harder grounding, or it becomes a dataset-only paper.
- **Accuracy falls steadily with step count:** there is headroom, and step count is a valid
  difficulty measure. Proceed to the spike in
  `~/.claude/plans/product-thesis-decision-and-a-rustling-snowflake.md`: the base small model and
  more frontier models.
- **Accuracy is low already at step count 3:** audit the clue wording and the cheat sheet before
  drawing conclusions.

## Known limitations

- One model and one sample.
- Rule-rendered clues read stiffly.
- There is no perturbation (test-suite) grading, so a coincidentally correct value passes; the
  constant-answer check only catches the cheapest cheat.
- Restricting programs to CADEvolve-C under the `02a` subset excludes the P-tier programs with
  loops.
