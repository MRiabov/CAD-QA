# Scratch experiment: LLM-model accuracy on the re-specified CAD-QA dataset, by task reasoning step count

**Status:** plan, 2026-10-22. This is a disposable experiment, not a dataset release and not a
benchmark claim. It measures how well current LLM models answer tasks built to the re-specified
dataset in `docs/dataset/requirements/` before the production generator exists. Its main purpose is
to decide whether the new no-kernel task format has headroom, and which parts of the 03/04 pipeline
deserve implementation first.

**Spec alignment.** The experiment follows the re-specified dataset documentation and its
terminology (`requirements/terminology.md`). Confidence differs by pipeline stage:

| Pipeline stage | Spec state | How this experiment uses it |
|---|---|---|
| `01` ETL (`01b`, `01d`) | draft | Reuses the small program pool and normalized text already selected for `experiments/old/cq_query_scratch/` under the `01b`/`01d` rules. |
| `02` extraction (`02a`, `02b`, `02c`) | draft | Reuses the throwaway `02b` slice from the CadQuery-query scratch, then adds the few facts this experiment needs. No profiles or workplane frames. |
| `03` task definitions (`03a`, `03b`, `03c`) | draft | Uses the `03b` `TaskDefinition` shape, step accounting, and validity rules, with a local construction grammar because MC-08 is still missing. Extends the grammar to step counts 7 and 9 as an above-release probe. No quota allocation or deficit resolution. |
| `04` rendering | draft | Uses `prompt-content.md` and a `prompts.yaml` with separate `dataset` and `eval` namespaces. |
| `05` validation and release | draft | Not implemented. The experiment writes its own manifest and report, not release artifacts. |

**Relation to the CadQuery-query scratch.** The `cq-query-scratch-experiment.md` run tested the
kernel-query pivot (PRD KI1) by asking an LLM model to write a CadQuery query. Its partial recorded run
answered 176 of 198 graded tasks correctly with `deepseek/deepseek-v4.1-flash-1017`
(`runs/cq_query_scratch_20261022/`). That is high across the graded step counts. This experiment
asks the complementary question: how well do models answer the re-specified no-kernel dataset,
where the output is an answer rather than a query? It therefore also informs KI1: if models
already answer well without a kernel, the pivot has less justification; if they fail mainly on
measurement and arithmetic, the pivot gains support.

## Question

Given a CadQuery program and a task from the re-specified dataset, can current LLM models return
the exact answer with no access to CadQuery? How does accuracy change with the **task reasoning step
count** at levels 1, 3, 5, 7, and 9, and which task target categories, clue types, answer
formats, and answer meanings fail? Secondary questions:

- Does removing the NumPy compute tool hurt accuracy, or are failures about entity selection rather
  than arithmetic?
- Does full CadQuery access change the result? That is the realistic agent setting and the upper
  bound for the no-kernel claim.
- Does a text-only shortcut baseline answer a meaningful share of tasks? If it does, the dataset
  has a shortcut problem before it has an LLM model-capability result.
- Is the task construction unambiguous enough for a careful human, and does it survive a prompt
  leak audit?

## Scope

- **300 core tasks**, 60 at each task reasoning step count **1, 3, 5, 7, 9**. A Wilson 95% CI at
  `p = 0.5` is about ±12.6 percentage points per step count. Per-format and per-clue cells are
  smaller and descriptive only. Phase B2 may add up to 120 tasks at step counts 11 and 13 if the
  step-9 result is still saturated.
- **Why 7, 9, and possibly 11/13.** The first release covers step counts 1–5 and treats 6+ as P2.
  The CadQuery-query scratch showed the lower range is already easy for the teacher: the main run
  solved 60/60 at step count 1 and 60/60 at step count 3, and the partial step-5 slice was 18/18.
  Its agentic step-9 rerun scored 56/60 (93.3%). A 1–5-only experiment would therefore likely
  measure a ceiling rather than headroom. Step counts 7 and 9 are the first above-release probes.
  If step 9 is still at or above 80% for API models, Phase B2 extends to 11 and 13 to find the
  actual failure point; if the sampler cannot fill at least 30 tasks per extended level, the
  shortfall is recorded and the curve stops at 9.
- **One LLM model in the step-9 run**: `deepseek/deepseek-v4.1-flash-1017`. The wider panel (a second
  API model and small open models) is deferred until the step-9 protocol is immutable; it must not be
  mixed into the step-9 comparison.
- **One sample per task per model.** The primary `numpy` arm gives the LLM model `run_code` with NumPy
  and `math`, but no CadQuery. A secondary `no_tools` arm on a 120-task subset removes the compute
  tool to isolate pure reasoning. A tertiary `cadquery` arm gives the LLM model the CAD kernel through
  `run_code`; it is the realistic agent setting and the upper bound for the no-kernel claim.
- **Task generation is deterministic.** The same inputs, seed, and versions must produce a
  byte-identical `tasks.jsonl`. A test asserts this. LLM model outputs are not deterministic; they are
  recorded.
- **All tasks are evaluation-only.** Programs are assigned to an experiment `eval` group by
  hash; the same CADEvolve program families are reserved from any later training run in this
  project until the official split exists.
- Out of scope: training, SFT, transfer, release planning (`03a`/`03c`), the 10,000-task release,
  P1/P2 clue types, answer meanings, and answer formats, multiple samples, confidence calibration,
  and human baselines. Step counts 7, 9, and conditional 11/13 are a deliberate above-release
  probe, not a P2 input claim.

## Inputs and the existing extracted data

- **Program pool.** Reuse `runs/cq_query_scratch_20261022/pool.parquet`: 80 CADEvolve-C programs
  selected by the `01b`/`01d` rules, the approximate `02a` subset, and the old-graph final-face
  filter. The pool is not a random sample of the 1,300-program regeneration; it over-represents
  programs with at least 8 final-state faces in the flat accepted subset. Record this bias.
- **Program facts.** Reuse `runs/cq_query_scratch_20261022/extraction/facts.jsonl`. It holds one
  `ProgramFacts` record per program with:
  - final-state faces, edges, and vertices, with the `canonicalization.md` entity IDs;
  - every top-level solid state, with volume, area, centroid, face/edge/vertex counts, and
    before/after face fingerprints;
  - `has_edge`, `has_vertex`, and `adjacent_to` relations for the final state;
  - face normals, bounding boxes, edge directions, and vertex points.
- **The old graph is not used for task facts.** The 2026-10-22 audit in the CadQuery-query plan
  found face→edge relations missing, adjacency incomplete, and face areas wrong in 1,300 old
  graphs. The old artifacts select programs; the CadQuery kernel facts produce answers.
- **Facts added by this experiment.** The extraction slice is extended, still in Python and still
  outside `dataset/`:
  - **Region facts**: signed volume change and topology change for a solid state producing operation,
    from the stored before/after solid states.
  - **Angle facts**: angles between face normals and between straight-edge directions, derived
    from the stored normals and directions.
  - **Extent facts**: solid-state and entity bounding boxes, from the stored face and vertex
    coordinates.
  - **Membership facts**: whether a sampled vertex, edge centroid, or face centroid lies inside the
    final solid, measured once by the CadQuery kernel. Points within `1e-6` of the boundary are excluded.
- **Facts not added.** CadQuery profiles and CadQuery workplane frames need `02a`/`02b` work that
  the CadQuery-query slice does not have. They are omitted and reported as scope gaps, not guessed.
- **Why reuse.** Re-extracting 80 programs costs 1–2 hours of throttled CadQuery kernel work and risks the
  thermal problems recorded in the CadQuery-query plan. Reuse makes the experiment start in
  minutes. The cost is a narrower fact set and a pool selected for a different experiment; both
  are recorded as limitations.

## Program pool and evaluation families

1. Load the 80 programs from `pool.parquet`. Verify the file hash and the 80 program SHA-256
   values against `facts.jsonl`.
2. Keep the existing `01b` family IDs. Assign each family to `scratch_eval` or `scratch_reserve`
   by `sha256("cadqa-new-dataset-eval-20261022" || family_id)`: the first 60% of families by hash
   are `scratch_eval`, the rest are `scratch_reserve`. Only `scratch_eval` families produce tasks.
3. Keep programs whose final state has at least 8 faces and whose facts contain at least one
   before/after state pair. Record the rejected programs and reasons.
4. If a family produces fewer valid tasks than its share, promote the next `scratch_reserve`
   family into `scratch_eval` by hash order and record the promotion. No family appears in both
   groups.
5. Record the family assignment, program order, and split hash in `manifest.json`.

This is not the release 70/15/15 split. It exists so that a later training run does not contaminate
the only evaluation families this experiment uses. The release-shaped `split` field is `test` for
every task; `subset` is `warmup` at step count 1 and `main` at every other level. The
`scratch_eval`/`scratch_reserve` family group is recorded in `provenance`, not in `split`.

## Task definitions (`03b` schema, local construction grammar)

Each task is a `TaskDefinition` with the `03b` fields:

- `task_id`, `definition_sha256`;
- `program_id`, `program_sha256`, `cadevolve_program_family_id`;
- `split`, `subset`;
- `target_category`, `target_binding`;
- ordered `clues`, each a typed `TaskClue` with `clue_id`, `order`, `clue_type`, `subject`,
  `check`, and `result`;
- `answer_meaning`, `answer_step`;
- `native_answer_format`, `answer_format`;
- `gold_answer`, `unit`, `tolerance`, `scoring_rule`, `answer_evidence`;
- `choice_pool` for multiple choice;
- `clue_step_count`, `task_reasoning_step_count`;
- `validity`, `provenance`.

The experiment adds no `gold_query` field. The gold answer is a value, not a query. `provenance`
records the constructor ID, the sampled operands, the fact-file hash, and the template version.

### Step accounting

`task_reasoning_step_count` is the number of task clue steps plus one if the task needs a task
answer step:

| Step count | Measurement task | Identity task |
|---|---|---|
| 1 | 0 clue steps + answer step, target named by the question | 1 clue step, no answer step |
| 2 | 1 clue step + answer step | 2 clue steps, no answer step |
| 3 | 2 clue steps + answer step | 3 clue steps, no answer step |
| 4 | 3 clue steps + answer step | 4 clue steps, no answer step |
| 5 | 4 clue steps + answer step | 5 clue steps, no answer step |
| 7 | 6 clue steps + answer step | 7 clue steps, no answer step |
| 9 | 8 clue steps + answer step | 9 clue steps, no answer step |

If Phase B2 runs, step counts 11 and 13 follow the same formula: 10 and 12 clue steps plus the
answer step for measurement tasks, or 11 and 13 clue steps for identity tasks.

Step 1 therefore has two legitimate forms: a direct measurement of a target the question names
(for example, the final solid state) and a one-clue identity answer. The 60 step-1 tasks include
both forms, but they are not split 50/50: multiple-choice identity tasks use the single-clue construction, and
the other five answer formats use a direct answer step. The sampler aims for at least 8 tasks per
format at step count 1 and records any shortfall. If the question identifies an entity by a condition
(for example, "the face created by the last operation"), that condition is written as a numbered
clue and counted as a clue step; it is not treated as a free observation.

### Construction grammar

The production construction grammar is missing (MC-08). The experiment uses this local grammar and
records it as a deviation, not as a proposed production grammar.

| Constructor | Step count | Target | Clues | Answer |
|---|---|---|---|---|
| `direct_measurement` | 1 | solid state, operation, feature, region, scalar value | none; the question names the target | volume, area, count, membership, position, extent, material change, topology change |
| `one_clue_identity` | 1 | face, edge, vertex | one property, relation, or provenance clue | identity, multiple choice |
| `entity_measure_chain` | 2–13 | face, edge, vertex, region | `step_count - 1` property, relation, comparison, or provenance clues | area, length, distance, angle, count, position |
| `entity_identity_chain` | 2–13 | face, edge, vertex | `step_count` property, relation, comparison, or provenance clues | identity, multiple choice |
| `membership_chain` | 2–13 | solid state, face, region | `step_count - 1` clues that fix a point or entity | membership, yes or no |
| `extent_chain` | 2–13 | solid state, face, region | `step_count - 1` clues that fix a target | extent, bounding box |
| `comparison_final` | 2–13 | face, edge, region | preceding clues plus one comparison against a named reference | measurement or identity |

Step counts 11 and 13 are conditional: the grammar is the same, but the sampler may not fill them
from 80 programs.

A direct target must be unambiguous without a condition. In practice, step-1 direct tasks use the
final solid state or a scalar of it; an operation, feature, or region is direct only when the
program has exactly one such instance. Otherwise the identification is a numbered clue and the task
has at least two steps.

A comparison clue may name both entities or refer to the single entity selected by an earlier clue
(`task-structure.md` Q1). A reference must resolve to exactly one entity; otherwise the task is
rejected. A clue list that needs an extreme to become unique is rejected in the P0-only set. In
the optional P1 slice, one aggregation clue may be the final clue; those tasks are labelled
`p1_aggregation` and reported separately.

### Scope of values

The experiment covers the P0 core that the reused facts can support. It does not claim release
coverage.

| Dimension | Covered by this experiment | Not covered, and why |
|---|---|---|
| Task target category | solid state, operation, feature (as the creating operation), face, edge, vertex, region, scalar value | CadQuery profile and CadQuery workplane are P0 but need new AST/runtime extraction; program, edge endpoint, path, path point, path segment, and CadQuery selector result are P1 |
| Clue type | property, relation, comparison, provenance | aggregation is P1; used only as a labelled final clue in at most 10% of tasks |
| Answer meaning | identity, volume, area, length, distance, angle, count, membership, position, extent, material change, topology change | rank and CadQuery workplane state are P1; validity is P2 |
| Answer format | multiple choice, number, integer, yes or no, 3D coordinate, bounding box | structured object is P1 |

Within each step count, the sampler aims for at least 8 tasks per answer format where the format
is structurally supported. This is a coverage-first sample, not the release balance rule. A cell
that cannot reach 8 is recorded as a shortfall.

### Clue meanings stated in the prompt

Every clue whose meaning depends on a tolerance or convention carries its definition in the prompt,
so an LLM model failure cannot come from guessing the experiment's convention. These are scratch
conventions; the re-specified docs do not define all of them yet.

| Clue or answer | Definition stated in the prompt |
|---|---|
| parallel / perpendicular | Angle between face normals or edge directions within 0.1° of 0° or 90°; planar faces and straight edges only. |
| same length / same area, larger / smaller | Relative tolerance `1e-3`. |
| adjacent faces | The faces share an edge. |
| created by an operation | A face of the shape after the operation whose geometry (centroid, area, normal, bounding box at `1e-6`) matches no face of the shape before it. A face that was only trimmed or split counts as created. |
| angle | The smaller angle between two face normals or two straight-edge directions, in degrees, from 0° to 180°. |
| distance | The shortest distance between two entities, or between a point and an entity. |
| membership | A point is inside the solid if the CadQuery kernel reports it inside at `1e-6`; points within `1e-6` of the boundary are excluded from the task. |
| extent | The axis-aligned bounding box in the program frame. |

### Validity

A definition is valid only when all of these hold:

- every clue is satisfied by the bound entities;
- every clue narrows the possible-answer set (`after < before`);
- the final possible-answer set contains exactly one entity or value;
- the answer step produces exactly one answer;
- the target binding is unambiguous;
- the family and split are present and match the assignment;
- the answer has answer evidence;
- for multiple choice, the choice pool has at least five real choices, the correct choice is
  present, all choices are unique, and all choices are in the same answer space;
- the canonical identity is unique;
- `geometry_required` is recorded;
- the gold answer can be recomputed from the stored facts by an independent function and matches;
- the prompt leak audit passes.

A definition that fails any check is written to `failures.jsonl` with its reason and does not
consume a slot.

### Geometry requirement

`geometry_required` is true when at least one clue or the answer depends on a measured fact that
cannot be read from the program text alone, for example a topology relation, a face count after a
boolean operation, or a created-face provenance. A direct final-volume task on a single primitive
may be `false`; the shortcut baseline measures exactly that case. The experiment reports the share
of `geometry_required` tasks and does not claim the release's 95% target. The release definition of
the flag for one-step no-clue tasks is still open (MC-22).

### Deterministic construction

- Constructors run in a fixed order, recorded in `provenance`.
- Candidate operands are sorted by the canonical entity order: category rank, then
  `fingerprint_json`, then `entity_id`.
- Every choice uses the first item in
  `sha256(seed || program_id || step_count || slot || constructor_id)` order. Python's `random` is
  not used.
- Duplicates are removed by the canonical `03b` identity. Up to 3 tasks per program per step count
  are accepted, then the next identity in hash order is tried.
- 60 accepted tasks at each core level (1, 3, 5, 7, 9), and at least 30 at each conditional
  extended level (11, 13). If a constructor cannot fill its share, the sampler moves to the next
  constructor and records the shortfall.

### Local resolutions of missing contracts

The re-specified docs still have missing contracts. This experiment resolves them locally and
marks each as a scratch convention:

- **MC-08 construction grammar.** The constructor table above is the local grammar.
- **MC-09 canonical serialization.** `definition_sha256` is SHA-256 over canonical JSON of the full
  definition, including the gold answer and answer evidence, with sorted keys, 9-decimal rounding
  for measurements, and no timestamps. `task_id` is
  `nds_` plus the first 16 hex characters of SHA-256 over
  `(program_sha256, target binding identity, canonical clue sequence, answer meaning)`.
- **MC-15 multiple-choice fairness.** Choices come from the real answer candidate set before the last
  clue, plus the correct entity. If fewer than five remain, the pool expands to an earlier clue
  state; if still fewer than five, the task is rejected. Choices are described by geometry or
  construction role, never by variable name or internal ID. The P2 near-miss audit is not done.
- **MC-22 geometry requirement.** The experiment records the flag per task and reports the share;
  it does not enforce the 95% release target.
- **MC-25 prompts schema.** The experiment defines a typed local schema for `prompts.yaml` and
  records its hash. It does not claim the production schema.

## Rendering (`04` rules)

- **Prompt copy.** All wording lives in `experiments/old/new_dataset_eval_scratch/prompts.yaml`, with
  separate `dataset` and `eval` namespaces, stable template IDs, and typed placeholders. A
  template variant is selected by `sha256(template_id || seed)`. The YAML hash is recorded in
  `manifest.json`.
- **Prompt layout.** Program text, question, numbered task clues, choices for multiple choice, and
  answer instruction, in that order (`prompt-content.md`).
- **Program text.** The normalized program text from `01d`, shown as code. It is not shortened,
  explained, or reformatted.
- **Question.** The interrogative sentence names the task target category and asks what to answer.
  It does not narrow the candidates. Examples: "What is the volume of the final solid state?",
  "Which face satisfies the task clues?"
- **Task clues.** One condition per numbered item, ordered from broad to narrow. No variable names,
  CadQuery selector strings such as `>Z`, or internal terms. An operation is named by what it does and by
  the line number in the rendered program: "the operation that removes material on line 14".
  Line numbers refer to the normalized program shown in the prompt, not to the original CADEvolve
  file.
- **Answer instruction (`dataset` namespace).** Matches the answer format: one number with unit and
  4 significant figures, one integer, one of `true`/`false`, one coordinate tuple, one bounding
  box, or one choice label.
- **Evaluation wrapper (`eval` namespace).** The local harness parses a final JSON tool call, so
  the eval prompt appends a short, identical paragraph:
  "End your reply with exactly one tool call `{"name": "submit_<format>", "arguments": {...}}`
  matching the schema below. Do not put the answer anywhere else." The wrapper never changes the
  task clues, choices, or answer format. Both the dataset prompt hash and the eval prompt
  hash are recorded.
- **Multiple choice.** Labels `A` to `G`, at least five choices, deterministic hash order. The
  correct choice's label is the gold answer. Choice descriptions use geometry or construction
  role, for example "the planar face with centroid `(10.0, 5.0, 2.0)`", never a variable name.
- **Leak audit.** The rendered question, clues, choices, and answer instruction are scanned for:
  - the gold answer as a string, and numeric answers within grading tolerance;
  - variable names from the program;
  - hidden entity IDs and evidence fields;
  - wording such as "correct", "answer", or "choose this".
  A task that fails the audit is rejected. A gold answer that appears only inside the program text
  is recorded as a `literal_leak` and removed from the LLM model run.

## Running the LLM models and grading

1. **LLM model.** The step-9 run uses `deepseek/deepseek-v4.1-flash-1017` through Merge Gateway.
   A second API model and the small open models are deferred until the step-9 protocol is immutable;
   they are not mixed into the step-9 comparison. Pin the exact model ID, provider, and price in
   `manifest.json` before the run.
2. **Call.** Use the repository's OpenAI-compatible client path (`train_and_eval/teacher.py` or the
   equivalent used by `run_eval.py` in the CadQuery-query scratch). Temperature 0, or 0.1 if the
   provider rejects 0; top-p 1.0. One sample per task. Record reasoning, visible content, raw tool
   calls, prompt and response hashes, tokens, cost, latency, provider, and finish reason. Resume by
   `(task_id, model_id)`.
3. **Two-turn submission.** If the first response has no parseable tool call, send one short
   reminder: "You did not submit. Submit exactly one tool call now." If the second response still
   has none, the outcome is `no_tool_call`. The reminder is a harness convention, not a task clue,
   and is recorded in `calls.jsonl`. This follows the CadQuery-query run, where one-shot calls
   produced 19 `no_tool_call` outcomes in 198 tasks.
4. **Harness extensions.** The existing `train_and_eval/tool_calls.py` covers `submit_number`,
   `submit_integer`, `submit_coordinate`, `submit_bbox`, and `submit_label`. This experiment adds:
   - `submit_choice` with a label matching `^[A-G]$`, for multiple choice;
   - `submit_boolean` with a boolean value, for yes or no.
   Both are small, typed additions. If adding a tool is undesirable, `submit_label` and
   `submit_text` can carry the same values, but the typed tools are preferred and are recorded as
   scratch harness changes.
5. **Primary arm: `numpy`.** Submit tools plus `run_code` with NumPy and `math`, no CadQuery,
   no network. Up to 8 compute turns, then one submit. This is the project's primary evaluation
   harness: the LLM model may compute, but it cannot build the shape or call the CAD kernel.
6. **Secondary arm: `no_tools`.** Submit tools only; all reasoning and arithmetic are internal.
   Run this on the same 120-task subset as a paired diagnostic. It isolates comprehension from
   tool use and shows whether the NumPy tool is doing the work.
7. **Tertiary arm: `cadquery`.** Submit tools plus `run_code`, which executes Python after the
   program in the same namespace with CadQuery available. The LLM model can inspect faces, edges,
   vertices, and measurements, then submit the answer. This is the realistic agent setting and the
   upper bound, not the P0 claim. Run it on the same 120-task subset as `no_tools`; the step-9
   run uses all 60 tasks.
8. **Grade** with the release scoring rules:
   - multiple choice, integer, yes or no: exact after whitespace and case normalization where the
     format allows it;
   - number, coordinate, bounding box: relative `1e-3` with absolute fallback `1e-6`, per
     component for coordinates and boxes;
   - structured object: not used.
   The grader reads only the submitted tool call. Invalid arguments, missing tools, and malformed
   JSON are failures, not exclusions.
9. **Outcomes:** `correct`, `wrong`, `no_tool_call`, `parse_error`, `invalid_tool_call`,
   `literal_answer`, `timeout`, `api_error`.
10. **Literal-answer check.** A submitted answer that is a bare constant or a program literal is
   flagged `literal_answer` but still graded. A task whose gold answer appears verbatim in the
   prompt is removed at generation time by the leak audit.
11. **Shortcut baseline.** A deterministic, no-LLM baseline runs on every constructed task and is
    reported separately:
    - `majority`: the most frequent gold answer per `(step_count, answer_format)`, with hash
      tie-breaking;
    - `program_text`: closed-form volume/area/length for a single primitive whose arguments are
      literals, a fixed `6` face count for a single box, the first or last candidate for identity,
      `true` for yes/no, and abstention elsewhere.
    Abstentions are reported, not counted as wrong. If the shortcut baseline exceeds 25% on a
    cell, that cell is flagged before any LLM model result is interpreted.
12. **Logging.** Every call writes one JSONL record. The record includes the internal reasoning,
    the visible output, and the tool calls, as required for later reconstruction. If a provider
    hides reasoning, the field is `null` and the provider is recorded.

## Report

- **Funnel:** programs loaded, families in `scratch_eval`, facts validated, definitions
  constructed, valid definitions, rejections by reason, accepted tasks, rendered prompts, leak
  audit failures, calls, parseable tool calls, executed submissions, correct answers.
- **Accuracy by task reasoning step count**, per model and pooled by LLM model class, with Wilson 95%
  CIs.
- **Paired model comparisons** on the same tasks: McNemar exact test and a paired bootstrap 95% CI
  for the risk difference. Compare the two API models, the two small models, and the
  best API model against the best small model.
- **Breakdowns** by task target category, clue type, answer format, and answer meaning. These are
  descriptive, with cell counts. Do not report a CI for a cell with fewer than 8 tasks.
- **`numpy` versus `no_tools`** on the 120-task subset, paired by task.
- **Shortcut baseline** accuracy and abstention rate, by step count and format.
- **Failure taxonomy**: wrong entity, wrong measurement, wrong frame or sign, wrong unit or
  precision, provenance/adjacency error, multiple-choice distractor, parse failure, literal
  shortcut, API failure.
- **Cost and tokens** per model, per correct answer, and per step count.
- **Five example tasks** with the prompt, gold answer, LLM model output, and grade: one correct, one
  wrong entity, one wrong measurement, one multiple-choice error, one parse failure.
- **Coverage table**: which P0 target categories, clue types, answer meanings, and answer formats
  were attempted, which were not, and why.

## Phased run and gates

| Phase | Tasks | LLM models | Purpose |
|---|---|---|---|
| 0. Smoke | 10, two per step count | `deepseek/deepseek-v4.1-flash-1017` | End-to-end plumbing, parsing, grading, report. |
| A. Calibration | 120, step counts 1 and 3 | one API model, one small model | Prompt wording, gold validity, leak audit, parse rate. |
| B. Main | 300, step counts 1, 3, 5, 7, 9 | two API models, two small models | Main accuracy curve. |
| B2. Extended ceiling | up to 120, step counts 11 and 13 | two API models, two small models | Run only if step 9 is ≥ 80% for API models and at least 30 tasks per level are constructible. |
| C. no_tools | 120, 24 per core step count | one API model, one small model | Paired diagnostic: whether removing the NumPy tool changes the result. |
| C2. CadQuery | 120, 24 per core step count | one API model, one small model | Realistic upper bound: full CadQuery access through `run_code`. |
| D. Optional | 300 | one additional frontier model | Only if Phase B is clean and budget remains. |

**Gates for Phases A–C and B2.**

- 100% of accepted definitions have a recomputed gold answer that matches, and 100% pass the leak
  audit. A single gold mismatch stops the phase.
- For each API model, at least 95% of calls return a parseable tool call after the two-turn
  protocol; for each small model, at least 80%. Below those rates, inspect the prompt and tool
  schema before treating the failures as LLM model errors.
- A manual read of 10 prompts per step count finds them unambiguous, answer-free, and correctly
  ordered. The reviewer records each prompt as `ok` or with a defect.
- All failures are triaged as LLM model error, harness bug, or definition/prompt bug. No harness or
  definition/prompt bug may remain unfixed. The phase is rerun after a fix.
- At Phase A, API LLM model accuracy is at least 70% at step count 1 and at least 50% at step
  count 3. If it is lower, audit the wording, answer instruction, and tool schema before Phase B.
  These thresholds are sanity checks, not success criteria.
- Phase B2 runs only when step-9 API LLM model accuracy is at least 80% and the sampler constructs at
  least 30 tasks at each of step counts 11 and 13. Otherwise record the shortfall and stop at 9.
- Stop if an LLM model's invalid-output rate exceeds 20% or if the cost cap is reached.

## Cost and time

- **LLM model calls.** The primary `numpy` arm costs 300 tasks × 4 LLM models = 1,200 calls in Phase B,
  plus 240 in Phase A. The `no_tools` diagnostic adds 480 calls on the 120-task subset, and the
  CadQuery upper bound adds another 480. Phase B2 adds up to 480 calls if it runs (120 tasks ×
  4 LLM models). At roughly 3,000 input and 1,500 output
  tokens per call, the cheap panel costs about $6–9, or about $30–45 for a panel that includes a
  current frontier model. The hard cap is **$60** for the whole experiment; do not start Phase B2
  or Phase D after $45. Check the provider balance before each phase and record actual cost per
  call.
- **CadQuery kernel work.** Reusing the extraction is minutes. If `facts.jsonl` is missing or a hash
  mismatch forces re-extraction, run 80 programs throttled, as in the CadQuery-query plan:
  `nice -n 19`, `OMP_NUM_THREADS=1`, at most 2 child processes, a 1–2 s pause between programs,
  and no loading of all graph shards at once. That takes about 1–2 hours.
- **Task construction and rendering.** CPU-only and fast: under 10 minutes for the 300 core tasks
  (up to 420 with Phase B2) plus rejections.
- **Wall clock.** Phase B with 60 parallel calls is about 30–60 minutes. Phase C is about 1–2
  hours because of the compute turns. Phase D is another 30–60 minutes.
- **Monitoring.** Long runs are checked every 3–5 minutes, not continuously.

## Code (`experiments/old/new_dataset_eval_scratch/`)

Start from the archived CadQuery-query scratch package
(`experiments/old/cq_query_scratch/`): copy `kernel.py`, `kernel_child.py`, `pool.py`, `models.py`, and the call
logging pattern into the new package as a starting point. Do not import across branches at runtime.

| Module | Responsibility | Lines (estimate) |
|---|---|---|
| `pool.py` | Load the existing pool, validate hashes, assign `scratch_eval`/`scratch_reserve` families, apply the small-pool checks. | ~110 |
| `facts.py` | Load `ProgramFacts`, derive region, angle, extent, and membership facts, validate the fact hash. | ~260 |
| `definitions.py` | `TaskDefinition`, `TaskClue`, constructors, validity, canonical identity, deterministic sampling. | ~450 |
| `choices.py` | Multiple-choice candidate pool, descriptions, labels, fairness checks. | ~150 |
| `render.py` (+ `prompts.yaml`, ~120 lines) | Render the dataset prompt and the eval wrapper from YAML. | ~180 |
| `shortcut.py` | Majority and program-text baselines. | ~120 |
| `run_eval.py` | LLM model calls, `no_tools` and `numpy` arms, two-turn submission, resume, call logging. | ~320 |
| `grading.py` | Tool-call parsing, scoring rules, outcomes, literal check, leak audit. | ~200 |
| `report.py` | Funnel, accuracy, Wilson CIs, paired comparisons, breakdowns, examples. | ~180 |
| `review.py` | Static HTML review page with task, program, gold, prompts, LLM model outputs, and tool calls. | ~200 |
| `tests/test_new_dataset_eval_scratch.py` | End-to-end test. | ~220 |

Total: about **2.2k lines**. Most bug risk is in `definitions.py`, `choices.py`, and `render.py`,
which the Phase A gates are designed to catch.

Code rules:

- Pydantic models with `Field()` constraints; `StrEnum` for every fixed vocabulary, spelled as in
  the re-specified docs.
- Keep each module under 800 lines.
- Use stdlib `logging`; the repository has no structlog.
- Reuse `train_and_eval.tool_calls` for parsing and matching; extend it with the two typed tools.
- Do not modify `dataset/` or write release artifacts.

**End-to-end test.** Use a small flat CADEvolve-C-style fixture and real CadQuery, with only the
LLM calls mocked. The test covers:

- the pool and family split checks;
- the fact hash and canonical entity IDs from `canonicalization.md`;
- task construction at step counts 1, 3, 5, 7, and 9;
- each answer format, including a five-choice multiple-choice task;
- a non-narrowing clue being rejected;
- an ambiguous target being rejected;
- a multiple-choice pool with fewer than five real choices being rejected;
- a gold mismatch being rejected;
- a prompt whose question, clues, or choices contain the gold answer or a variable name being
  rejected (variable names in the program text are allowed);
- a valid gold answer grading `correct`, a wrong answer grading `wrong`, and a bare constant
  grading `literal_answer`;
- the `numpy` arm with a mocked `run_code`;
- the shortcut baseline returning the expected values;
- two generation runs giving byte-identical `tasks.jsonl`;
- the report funnel counts.

## Outputs

- Data (gitignored): `runs/new_dataset_eval_scratch_20261022/` holding:
  - `pool.parquet`;
  - `facts.jsonl` (or a pointer to the reused facts);
  - `tasks.jsonl` and `failures.jsonl`;
  - `prompts.parquet`;
  - `calls.jsonl` and `grades.jsonl`;
  - `shortcut_grades.jsonl`;
  - `leak_audit.json`;
  - `report.md`;
  - `review.html`, the static input-and-output review page;
  - `manifest.json`, recording the seed, versions (Python, CadQuery, OCP, ruff), fact and pool
    hashes, `prompts.yaml` hash, template version, LLM model IDs and prices, split hash, task counts,
    and actual cost.
- Record: `docs/experiments/2026-10-22-new-dataset-llm-eval-scratch.md`, containing:
  - the funnel and accuracy tables;
  - the failure taxonomy;
  - cost;
  - five example tasks with LLM model outputs;
  - the headroom verdict;
  - feedback for the re-specified docs: which clue types, formats, and answer meanings were
    ambiguous, and which local resolutions should become production contracts.
- No dataset release artifacts. The experiment does not write to `dataset/` and does not claim
  release coverage or balance.

## Deviations from the specs (deliberate)

- **A throwaway Python slice of `01`/`02`/`03`/`04`, not the Go pipeline.** It reuses the
  CadQuery-query extraction and adds only the facts this experiment needs. It is not the production
  generator and is not imported by `dataset/`.
- **Small pool.** 80 programs and 300 core tasks (up to 420 with Phase B2) instead of the
  10,000-task release. No `03a` quota allocation, no `03c` deficit resolution, and no release
  balance.
- **Balanced step-count sample.** 60 tasks at each of 1, 3, 5, 7, and 9 instead of the release
  mix 5/15/40/25/15. The experiment estimates accuracy at each level, not release composition.
- **Above-release step counts 7, 9, and conditional 11/13.** The first release covers 1–5 and
  treats 6+ as P2. The scratch extends the constructors to 7 and 9, and conditionally to 11 and 13,
  to test whether the query-task step-9 saturation survives the answer format. These tasks are
  labelled `above_release_step` and reported separately; they do not claim release support.
- **Warmup share.** Step count 1 is 60 of 300 tasks (20%), not the release 5%. Step-1 tasks still
  carry `subset = warmup`; the larger share gives the warmup cell an estimate.
- **Evaluation-only family split.** The 60/40 `scratch_eval`/`scratch_reserve` split is not the
  release 70/15/15 split. It exists to keep the evaluation families out of later training.
- **Inherited old-graph pool filter.** The 80 programs were selected with the old-graph final-face
  check from the CadQuery-query scratch. The re-specified `01b` does not use that check. It is a
  pool heuristic inherited for comparability, not a new selection rule.
- **Omitted P0 target categories.** CadQuery profile and CadQuery workplane are P0 but need
  extraction this slice does not have. They are reported as gaps, not approximated.
- **Local construction grammar.** The production grammar is missing (MC-08). The constructor table
  is a scratch convention and may be replaced by the production grammar.
- **Local canonical hashes.** `definition_sha256` and `task_id` use the scratch convention in
  *Local resolutions of missing contracts*, not the undefined production serialization.
- **P1 aggregation.** Aggregation is used only as a labelled final clue in at most 10% of tasks.
  Those tasks are reported separately and do not count toward the P0 result.
- **Multiple choice is not near-miss-audited.** Choices are real, unique, and non-leaking, as P0
  requires. The P2 near-miss audit is not done.
- **The eval wrapper and tool-call protocol are harness conventions.** The dataset prompt is
  rendered per `04`; the eval prompt adds one identical submission paragraph. The dataset itself
  does not require a tool call.
- **Two typed harness extensions.** `submit_choice` and `submit_boolean` are added for P0 answer
  formats the current harness does not cover.
- **No release validation.** The experiment does not enforce the 95% geometry-required target,
  the answer-format mix, or the clue/meaning balance. It reports what it constructs.

## Expected results (guesses, recorded before the run)

| Task reasoning step count | API LLM model accuracy | Small LLM model accuracy |
|---|---|---|
| 1 | 85–98% | 30–50% |
| 3 | 75–92% | 20–40% |
| 5 | 60–85% | 12–30% |
| 7 | 45–75% | 6–18% |
| 9 | 30–60% | 3–10% |
| 11 (conditional) | 20–45% | 2–8% |
| 13 (conditional) | 12–35% | 1–5% |

- **Step 1 is a sanity check.** If API LLM model accuracy is below 70% at step count 1, the
  prompt, answer instruction, or tool schema is more likely wrong than the LLM model.
- **Step 9 is the headroom check.** If API LLM model accuracy stays at or above 80% at step count 9,
  the answer task saturates like the query task did, and Phase B2 is the only way to find the
  failure point. If it falls below 50%, the new format has headroom even though the query task did
  not.
- **Multiple choice should make identity tasks the easiest cell.** The experiment does not run a
  free-form identity control, so the size of the effect is a guess, not a measurement.
- **Expected failure types:**
  - provenance and adjacency clues, which have no direct selector or visual cue;
  - coordinate and bounding-box answers, from frame and sign errors;
  - exact counts and topology changes after boolean operations;
  - material-change signs (added versus removed);
  - multiple-choice descriptions that are too close to each other;
  - parse and tool-call failures, especially for small models;
  - literal shortcuts on single primitives.
- **no_tools arm.** It should lose 5–15 percentage points on arithmetic-heavy measurement tasks
  relative to the primary `numpy` arm, and should not fix wrong entity selection.
- **CadQuery arm.** It should be the highest-scoring arm. If it is close to `numpy`, the tasks are
  about comprehension and entity selection, not arithmetic. If it is much higher, kernel access is
  doing real work and the no-kernel setting is measuring a genuine gap.
- **Shortcut baseline.** Expected 5–15%, mostly on step-1 volume or count tasks with literal
  arguments. Above 25% on a cell is a dataset defect signal.
- **Pool bias.** The 80-program pool was selected for the CadQuery-query experiment, so accuracy
  may be higher than on a random CADEvolve-C sample of the same size.

## Decision this informs

- **High accuracy at step count 9 (≥ 80% for API models):** run Phase B2. If step counts 11 and
  13 are also at or above 80%, the re-specified dataset is too easy for API models on this clue
  vocabulary, even beyond the first release. The project needs harder clue types, a different
  difficulty axis, or a different claim; training a small model is still useful, but the benchmark
  needs a harder slice.
- **A steady fall with step count and API LLM model accuracy below 50% at step count 9:**
  there is headroom. Proceed with the production generator and the training plan, and use the
  per-clue/per-format failures to prioritize constructors.
- **Step-9 accuracy between 50% and 80%:** there is partial headroom. Proceed with the production
  generator and report the curve; run Phase B2 only if the failures are LLM model errors rather than
  prompt or definition bugs.
- **Step counts 1–5 are already at or above 90% for API models:** the first-release range is
  saturated even if step count 9 falls. The release needs harder tasks inside 1–5, or a different
  target claim; a high step-9 score alone does not fix the first release.
- **Low accuracy at step count 1:** fix prompt wording, answer format, and tool submission before
  scaling. Do not interpret the curve.
- **Large NumPy gain:** keep `numpy` as the primary evaluation harness and implement the compute
  tool in the production evaluation path.
- **CadQuery arm far above `numpy`:** the realistic agent setting has substantial headroom over the
  no-kernel setting. Report the gap, and treat the CadQuery score as an upper bound rather than a
  replacement for the P0 number.
- **Small NumPy gain and mostly entity-selection failures:** the no-kernel reasoning claim is
  about comprehension, not arithmetic; the CadQuery-query pivot would not remove the main failure.
- **High shortcut-baseline accuracy:** fix the task construction (more geometry-required clues,
  fewer literal-answer tasks) before measuring models.
- **Spec feedback:** the Phase A review and the failure taxonomy tell the dataset owners which
  clue definitions, answer formats, and missing contracts (MC-08, MC-09, MC-15, MC-22, MC-25) block a
  10,000-task release.

## Known limitations

- One sample per task and one LLM model. The per-step CIs are wide, and per-format and
  per-clue cells are descriptive only.
- The 80-program pool was selected for the CadQuery-query experiment, not for this one. It
  over-represents flat, multi-face CADEvolve-C programs and may not generalize to the full
  1,300-program regeneration, which includes programs outside the flat accepted subset.
- The gold facts and the task construction share the same extraction. An extraction bug propagates
  to both. The independent gold recomputation catches construction and scoring bugs, not
  extraction bugs.
- CadQuery profile and CadQuery workplane target categories are P0 but absent. The accuracy curve
  is therefore not a release-level estimate.
- The task construction grammar is local. A different grammar could produce different difficulty.
- Step counts 7, 9, and conditional 11/13 are outside the first release. Their constructors are
  an extension of the local grammar, and their accuracy curve is not a release-level estimate.
- Rule-rendered clues read stiffly. A human review of 10 prompts per step count is not a
  substitute for the release review of every clue type and answer format.
- There is no perturbation grading. A coincidentally correct value passes; the literal-answer
  check only catches the cheapest shortcut.
- The multiple-choice choices are real candidates but are not near-miss-audited. A LLM model may
  succeed by elimination rather than by following the clues.
- The LLM model panel is fixed in time. Provider routing, quantization, and model versions can change
  between runs; the manifest records what was used.
- The experiment is evaluation-only. It says nothing about whether fine-tuning on the new dataset
  improves a small model, which is the project's P0 claim.
- The CadQuery arm is a realistic upper bound, not a P0 result. It uses process isolation, not a
  security sandbox, and it changes the task by giving the LLM model the shape.
