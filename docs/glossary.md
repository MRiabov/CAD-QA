# Glossary

Canonical vocabulary for CAD-QA. **One concept, one word.** Every load-bearing term used in
the docs is defined here, or is on the Don't-say list. Add a term here before using it
elsewhere. `Distinct from:` marks a near-synonym that must not be confused with the term.

**Status:** seeded 2026-10-07. The Don't-say list is a partial seed; the full legacy-term
audit is pending (see `development-plan.md`).

## Project

- **CAD-QA** — the benchmark for reasoning over procedural CAD programs (CadQuery), and the
  fine-tuning effort that uses it.
- **CADEditQA** — a possible extension: constrained edit prediction over the same sources
  and verifier. Not active. Priority P2.

## Sources and tracing

- **source** (`SourceRecord`) — one normalized CadQuery program, identified by its archive
  path plus a hash of the normalized code.
- **CAD query trace** — the recorded execution of a source: snapshots and measurements
  produced by running CadQuery. `Distinct from:` **training trace**.
- **snapshot** — the measured state of one top-level assignment in a source (volume,
  bounding box, topology counts, centroid), produced by a CAD query trace.
- **CADEvolve** — the primary corpus of executable CadQuery programs the benchmark draws
  from.

## Ontology

- **ontology graph** — the typed graph extracted from a source: nodes, relations, and
  measurements.
- **ontology node** — a typed entity in the graph (source, feature, operation, parameter,
  workplane, profile, solid, face, edge, vertex, point, path, material region, void region,
  selector, measurement). `Distinct from:` **code node**.
- **relation** — a typed edge between ontology nodes (for example `selected_by`,
  `has_measurement`, `adds_material_to`).
- **relation family** — a group of relation types used to categorize a dataset row.
- **measurement** — a typed numeric or geometric fact attached to a node.
- **measurement scope** — where a measurement comes from, one of: `profile_intrinsic`,
  `feature_application_effect`, `entity_geometry`, `snapshot_state`, `relation_metric`.
  A measurement's scope prevents category errors (an edge-count delta is a feature effect,
  not a profile property).
- **selector** — a CadQuery selection expression (for example `.faces(">Z")`,
  `.edges("|X")`) that binds one or more topology entities.
- **workplane** — the coordinate frame a sketch or feature is built in, defined by an
  origin, a normal, and x/y axes.
- **profile** — the 2D shape drawn on a workplane (circle, rectangle, polyline) before it
  becomes a solid feature.
- **material region** / **void region** — the geometry a feature adds / removes,
  conservatively derived.

## Rows and labels

- **dataset row** — one question instance: a public rendering plus the private verifier
  artifacts. `Distinct from:` **candidate**.
- **public row** — the answer-free model input (source code, prompt, answer format, public
  metadata).
- **private row** — the gold answer, hidden query program, candidate trace, and clue map.
- **query program** — the deterministic hidden program a row is generated from: target
  entity type, answer type, ordered clauses, metric filters, optional aggregation, and a
  reject-unless-unique policy.
- **clause** — one step of a query program, mapped to exactly one public clue.
- **candidate trace** — the record of how candidates narrow across clauses, ending in the
  final candidate set.
- **gold answer** — the verifier-backed correct answer for a row.
- **answer format** — the shape of the answer: `candidate_label`, `coordinate`, `text`,
  `number`, `integer`, `boolean`, `bbox`, or `json`.
- **hop count** — the number of reasoning steps a row requires:
  - **logical hop count** — hops in the question's reasoning;
  - **static hop count** — hops derivable from source syntax alone;
  - **geometry hop count** — hops requiring geometry evidence.
- **difficulty bucket** — a coarse label derived from hop count.
- **verifier** — the deterministic component that decides whether a query resolves
  uniquely and what the gold answer is.
- **quarantine** — a row that resolves deterministically but is not release-ready (its
  evidence is conservative or surrogate-backed).
- **release tier** — the readiness bar: `smoke`, `release-candidate`, or
  `benchmark-release`. Only `benchmark-release` supports public benchmark or real
  fine-tuning claims.

## Fine-tuning

- **training trace** — a model-facing record of reasoning followed by a tool call, used as
  supervision. `Distinct from:` **CAD query trace** and **candidate trace**.
- **teacher** — the model that produces training traces (currently
  `deepseek/deepseek-v4-flash` via OpenRouter).
- **rejection sampling** — generating many teacher attempts and keeping only those the
  verifier accepts.
- **tool call** — the model's structured output selecting one typed tool with arguments.
- **submit tool** — one of the typed answer tools (`submit_label`, `submit_number`, …) used
  to emit the final answer.
- **run_code** — the sandboxed Python/NumPy compute tool available to the model.
- **compact_trace** — a tool the teacher uses to shorten its own reasoning.
- **SFT** (supervised fine-tuning) — training on input/output pairs (here, prompts and
  training traces).
- **GRPO** — a reinforcement-learning method that scores groups of sampled completions
  against a reward.
- **reward** — the verifier-derived score for a completion, from exact answer match.
- **LoRA** / **QLoRA** — parameter-efficient fine-tuning; QLoRA quantizes the frozen base.
- **base model** — the untuned pretrained model.
- **adapter** — the trained LoRA weights, applied on top of the base model.
- **merged model** — the base model with the adapter merged into its weights.
  `Distinct from:` **base model**, **adapter**.
- **entropy collapse** — the failure where the policy's output distribution becomes
  near-deterministic and exploration stops.

## Evaluation and serving

- **harness mode** — which compute tools the model gets during evaluation:
  - **`numpy`** — the primary harness: a Python shell with NumPy;
  - **`no_tools`** — reasoning only, no compute;
  - **`cadquery`** — full CadQuery kernel access (one correct call suffices).
- **Harbor** — the environment and runner used to evaluate cost-effective models on the
  benchmark.
- **vLLM** — the high-throughput inference engine used for batched evaluation and rollouts.

## Infrastructure

- **dataset_generation** — the code package that builds the benchmark (today `cad_qa/`).
  Frozen: documented, not refactored.
- **fine_tuning** — the code package for training and evaluation (today `train_and_eval/`).
  Being revised.
- **rows artifact** — the input/output contract between `dataset_generation` and
  `fine_tuning`.

## Pending additions

Terms used by the pipeline docs but not yet defined here (from the 2026-10-07 drafting
audit). Define each before treating the glossary as complete:

task family · intended family · answer contract (suffix) · answer spec · sampled
parameters · evidence tier · prompt template · clue map · release-ready · split / split
group / protected group · geometry-critical · geometry-hop-positive · shortcut resistance ·
stop gate · candidate label · source variable · path point / path segment / edge endpoint ·
tool declaration / tool schema · native tool-call format · curriculum / hop curriculum ·
compaction · reasoning phase · held-out row · tool-valid · baseline · grader / exact match ·
closed-book · harness (the runner, distinct from harness mode) · Harbor task · terminus-2
agent · slice (rc10 / release10k / clean-100) · tool-assisted upper bound.

## Don't-say

Seeded; the full legacy-term audit is pending. Entries are a ratchet: they may be removed
only when the term is engineered out of the docs and code.

| Don't say | Say | Why |
|---|---|---|
| "intent" (as a doc) | PRD | renamed; "intent" is the concept, not the artifact |
| "trace" (alone) | CAD query trace / training trace / candidate trace | overloaded across three concepts |
| "model" (alone) | base model / adapter / merged model | ambiguous between weights, adapter, and served endpoint |
| "node" (alone) | ontology node / code node | ambiguous between graph and code |
| "entity id" (in a public answer) | source variable | internal `entity_id` values must not leak into public answers |
| "the pipeline" / "the object" / "the value" | name the concept | unspecific placeholder |
| "first/last" (as family semantics) | the sampled parameter | a rendering choice, not a permanent meaning |
