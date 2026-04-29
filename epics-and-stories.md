# Scrum Epics and Stories: CAD-QA Paper + Dataset Delivery

## Product goal

Deliver **CAD-QA**, a research paper and accompanying code-plus-label dataset for evaluating and training models on closed-book reasoning over executable CadQuery construction programs. CAD-QA focuses on what a single CAD script does: operation ordering, selector semantics, intermediate geometry, topology, point membership, feature provenance, and counterfactual CAD reasoning. The v0.1 MVP uses CADEvolve-backed single-script prompts and structured answers; CADEditQA repair tasks, multimodal variants, and broad natural-language explanations remain reserved extensions unless promoted by a later release.

Backlog note: this backlog is reconstructed from `specs/` and mirrors the sibling IntersectionQA document style. The YAML companion records the same planning structure in a compact machine-readable form.

---

# Epic 1: Research Scope and Paper Framing

## Goal

Freeze the CAD-QA research contribution, benchmark boundary, reviewer-facing claims, and paper narrative before implementation expands.

## Story 1.1 - Define benchmark thesis

**As a researcher**, I want a clear central thesis for CAD-QA so that the paper has a focused contribution.

**Acceptance criteria**

* A one-paragraph thesis statement exists.
* The thesis distinguishes CAD-QA from generic text-to-CAD generation.
* The thesis explains why closed-book CAD program reasoning is useful.
* The thesis separates diagnostic QA from later edit-prediction tasks.

**Output**

```markdown
CAD-QA tests whether language and code models can infer the geometry, topology, construction history, selector behavior, point membership, and feature provenance implied by executable CadQuery scripts without running a CAD kernel at evaluation time.
```

---

## Story 1.2 - Define task tiers

**As a dataset designer**, I want the task tiers frozen so that implementation can target stable labels and prompts.

**Acceptance criteria**

The paper defines:

* Tier A: static code comprehension.
* Tier B: symbolic geometry.
* Tier C: topology reasoning.
* Tier D: feature provenance.
* Tier E: counterfactual CAD reasoning.

**Output**

`specs/paper-spec.md` sections `Core Claim` and `Task Tiers`.

---

## Story 1.3 - Define evaluation regimes

**As a reviewer-facing researcher**, I want closed-book, tool-assisted, and optional multimodal settings separated so that claims are precise.

**Acceptance criteria**

The paper defines:

* Closed-book setting: model answers from code only, without CAD execution.
* Tool-assisted setting: model may execute CadQuery or use verifier tools.
* Trace-derived labels as official answers, not hidden prompt content.
* Optional render-backed setting as a separate extension.

**Output**

Section draft: `Evaluation Settings`.

---

## Story 1.4 - Define success metrics for the paper

**As the project owner**, I want clear criteria for when CAD-QA is paper-ready.

**Acceptance criteria**

Paper-ready means:

* Dataset pipeline can generate valid examples reproducibly from CADEvolve.
* All seven MVP task families are implemented.
* Protected split manifests pass leakage audits.
* Baseline and model evaluations cover closed-book and diagnostic settings.
* Paper draft includes method, dataset, experiments, limitations, and release notes.

---

# Epic 2: Dataset Source Ingestion

## Goal

Ingest CADEvolve CadQuery programs as the primary source and normalize them into source records with stable provenance. Synthetic examples are limited to golden tests, smoke tests, debugging, and label edge cases.

## Story 2.1 - Select initial CAD program sources

**As a dataset builder**, I want defensible source datasets so that CAD-QA has scale and provenance.

**Acceptance criteria**

* CADEvolve is the primary released-data source.
* `CADEvolve-P/` and `CADEvolve-C/` executable trees are preferred.
* `CADEvolve-G/` is treated as metadata/family context unless generator invocation is explicitly supported.
* Source license and archive metadata are recorded.
* Synthetic rows do not dominate public benchmark counts.

**Output**

`specs/using-cadevolve-dataset-export.md` and the source-policy sections in `specs/generation_policy.md`.

---

## Story 2.2 - Build source record loader

**As an engineer**, I want a common source loader so that raw CadQuery programs become auditable records.

**Acceptance criteria**

Loader returns records with:

```json
{
  "source": "cadevolve",
  "source_id": "...",
  "archive_member_path": "...",
  "source_subtree": "CADEvolve-P",
  "raw_code": "...",
  "normalized_code": "...",
  "hashes": {}
}
```

* Loader supports deterministic sampling by seed.
* Loader records skipped records and failure reasons.
* Loader stores source-family grouping keys for leakage-safe splits.

---

## Story 2.3 - Normalize CadQuery scripts

**As an engineer**, I want normalized scripts so that prompts, traces, and hashes are reproducible.

**Acceptance criteria**

* Imports are standardized or allowlisted.
* Final result assignment is detected or normalized.
* Code formatting is deterministic.
* Unsupported dynamic constructs are tagged instead of silently dropped.
* Normalized source hashes are stable.

---

## Story 2.4 - Validate source executability

**As a dataset builder**, I want to reject or quarantine programs that cannot produce valid CAD objects.

**Acceptance criteria**

For each candidate source:

* Script runs only in an isolated worker.
* Execution has wall-clock timeout and structured failure reporting.
* Final object type is checked.
* Volume, bounding box, and topology are finite when required.
* Failure reason is stored.

---

## Story 2.5 - Implement CADEvolve materialization workflow

**As an operator**, I want repeatable local source materialization so repeated runs do not depend on the tar archive hot path.

**Acceptance criteria**

* Archive browsing supports metadata inspection.
* Configured executable subsets can be extracted deterministically.
* Extracted source manifests are recorded.
* Repeated generation reads from extracted source directories.

---

## Story 2.6 - Keep synthetic fixtures scoped

**As a maintainer**, I want synthetic examples reserved for verification rather than becoming the benchmark.

**Acceptance criteria**

Synthetic fixtures cover:

* box/extrude volume and topology;
* cut and hole cases;
* selector-heavy scripts;
* workplane-transform scripts;
* fillet or chamfer scripts;
* point boundary cases;
* provenance cases.

---

# Epic 3: Operation Graph and Trace Generation

## Goal

Convert normalized source programs into operation graphs, isolated execution traces, and reusable intermediate-state snapshots.

## Story 3.1 - Extract AST-backed operation graphs

**As an engineer**, I want operation graphs from Python AST rather than regex so task labels are source-structure aware.

**Acceptance criteria**

Operation nodes contain:

```json
{
  "feature_id": "wp13",
  "step_index": 13,
  "source_line": 42,
  "operation": "extrude",
  "args_repr": [],
  "input_features": [],
  "status": "ok"
}
```

* Fluent calls, assigned variables, attribute calls, and simple result finalization are supported.
* Unsupported dynamic constructs are represented explicitly.
* Operation graph hash is deterministic.

---

## Story 3.2 - Implement isolated trace execution

**As an engineer**, I want CadQuery execution isolated from the main process so untrusted source programs cannot affect generation.

**Acceptance criteria**

* Worker runs with timeout, memory limits, captured stdout/stderr, and restricted side effects.
* Python, CadQuery, OCP, and OpenCascade versions are recorded.
* Execution status is one of the documented status values.
* Partial failures produce failure manifests.

---

## Story 3.3 - Capture intermediate snapshots

**As a dataset builder**, I want geometry snapshots after supported feature steps so many task rows can reuse one trace.

**Acceptance criteria**

Each snapshot records:

* snapshot ID;
* feature ID and step index;
* shape status;
* volume;
* bounding box;
* topology counts;
* entity IDs where feasible;
* diagnostics.

---

## Story 3.4 - Generate selector result tables

**As a dataset builder**, I want selector labels from trace execution so selector tasks match CadQuery semantics.

**Acceptance criteria**

* Selector expressions are discovered from source.
* Target state and entity type are recorded.
* Raw and deduplicated selected entity IDs are stored.
* Selector count uses the dataset tolerance policy.
* Selector failures are represented as invalid rows or rejection reasons.

---

## Story 3.5 - Assign stable entity IDs

**As a provenance researcher**, I want stable face, edge, vertex, and solid identifiers so topology and provenance rows can be audited.

**Acceptance criteria**

* IDs are deterministic for a snapshot.
* IDs include entity type and canonical ordering.
* Matching diagnostics are stored.
* Kernel-sensitive cases are tagged.

---

## Story 3.6 - Match topology across adjacent snapshots

**As a researcher**, I want best-effort topology matching so provenance tasks can distinguish created, modified, inherited, deleted, and bounded entities.

**Acceptance criteria**

* Matching method and confidence are stored.
* OpenCascade builder history is preferred when available.
* Low-confidence cases are filtered or labeled ambiguous.
* Cleanup, fillet, shell, and merge cases are not forced into single labels.

---

# Epic 4: Geometry, Topology, and Provenance Labeling

## Goal

Compute official labels from precomputed trace metadata under explicit tolerance and ambiguity policies.

## Story 4.1 - Implement label policy object

**As an engineer**, I want thresholds versioned with every dataset release so labels are reproducible.

**Acceptance criteria**

Label policy stores:

* linear tolerance;
* angular tolerance;
* volume tolerance;
* bounding-box tolerance;
* point-boundary tolerance;
* selector deduplication tolerance.

---

## Story 4.2 - Compute operation count labels

**As a dataset builder**, I want operation counts from operation graphs, not text substrings.

**Acceptance criteria**

* CadQuery operation aliases are normalized.
* Comments, imports, function definitions, and dead text are excluded.
* Executed loop expansion is used only when trace support is available.
* Rows without defensible counts are excluded or marked invalid.

---

## Story 4.3 - Compute volume and bounding-box labels

**As a dataset builder**, I want numeric labels for intermediate and final states.

**Acceptance criteria**

* Signed volume delta is `volume_after - volume_before`.
* Bounding boxes are world-coordinate min/max triples.
* Numeric values are finite.
* Raw values and derived answers are stored separately.
* Evaluation tolerance comes from label rules or row-specific tolerance.

---

## Story 4.4 - Compute topology count labels

**As a dataset builder**, I want topology counts from target snapshots.

**Acceptance criteria**

Labels support:

* solids;
* faces;
* edges;
* vertices;
* wires;
* planar faces;
* cylindrical faces;
* circular edges;
* axis-parallel edges.

---

## Story 4.5 - Compute point membership labels

**As a dataset builder**, I want robust inside/outside/boundary labels for sampled points.

**Acceptance criteria**

* Point strata include deep inside, deep outside, near face, near edge, near vertex, on boundary, inside removed cuts, and inside added features.
* Ordinary inside/outside rows exclude ambiguous near-boundary cases.
* Boundary tasks may use `on_boundary`.
* Nearest entity diagnostics are stored.

---

## Story 4.6 - Compute feature provenance labels

**As a provenance researcher**, I want conservative provenance labels that do not overclaim many-to-many CAD histories.

**Acceptance criteria**

Allowed relations:

```text
created_by
modified_by
deleted_by
inherited_from
bounded_by
```

* Single-choice rows answer with the earliest contributing feature by source execution order.
* Multiple contributors are stored in diagnostics.
* Rows without a defensible contributor set are filtered.
* Confidence and matching method are stored.

---

## Story 4.7 - Validate label consistency

**As a release owner**, I want impossible or unstable labels rejected before export.

**Acceptance criteria**

* Non-finite numeric values are rejected.
* Missing required snapshots are rejected.
* Kernel-unstable topology labels are rejected or quarantined.
* Low-confidence provenance rows are filtered.
* Prompt text is checked for hidden labels and diagnostics.

---

# Epic 5: Prompt and Task Generation

## Goal

Materialize public task rows from trace metadata without recomputing CadQuery geometry during prompt formatting.

## Story 5.1 - Implement `operation_count` prompt generator

**As a benchmark user**, I want structured operation-count prompts with integer answers.

**Acceptance criteria**

* Prompt includes normalized source code and requested operation type.
* Answer is a non-negative integer.
* Parser rejects prose-only answers.
* Metrics use exact integer accuracy.

---

## Story 5.2 - Implement `selector_count` prompt generator

**As a benchmark user**, I want selector-count prompts that test CadQuery selector semantics.

**Acceptance criteria**

* Prompt names the target selector expression or feature.
* Prompt specifies entity type.
* Answer is a non-negative integer or explicit invalid value for invalid rows.
* Label comes from selector result tables.

---

## Story 5.3 - Implement `bbox_after_step` prompt generator

**As a benchmark user**, I want bounding-box prompts with machine-parseable answers.

**Acceptance criteria**

* Answer format is JSON with `min` and `max` triples.
* Unit is millimetres.
* Target step or feature is unambiguous.
* Numeric tolerance is stored with the row.

---

## Story 5.4 - Implement `signed_volume_delta` prompt generator

**As a benchmark user**, I want volume-delta prompts that distinguish added and removed material.

**Acceptance criteria**

* Prompt identifies target feature.
* Answer is a finite number in cubic millimetres.
* Positive, negative, and zero semantics are documented.
* Metrics use absolute and relative tolerance.

---

## Story 5.5 - Implement `topology_count_after_step` prompt generator

**As a benchmark user**, I want topology-count prompts over faces, edges, vertices, wires, and geometry-specific subsets.

**Acceptance criteria**

* Prompt identifies the target snapshot.
* Prompt identifies the requested topology key.
* Answer is a non-negative integer.
* Kernel and tolerance versions are recorded outside the prompt.

---

## Story 5.6 - Implement `point_membership` prompt generator

**As a benchmark user**, I want point classification prompts with a fixed enum answer.

**Acceptance criteria**

Allowed answers:

```text
inside
outside
on_boundary
ambiguous
```

* Prompt includes point coordinates and target state.
* Ordinary tasks filter ambiguous points unless explicitly boundary-aware.
* Metrics report near-boundary performance separately.

---

## Story 5.7 - Implement `feature_provenance_choice` prompt generator

**As a benchmark user**, I want provenance prompts that ask which feature created, removed, modified, inherited, or bounded material or topology.

**Acceptance criteria**

* Prompt provides candidate feature IDs.
* Answer is one candidate ID.
* Low-confidence labels are excluded.
* Diagnostics include contributor feature IDs, first-contributor rule, matching method, and provenance confidence.

---

## Story 5.8 - Reserve later task prompt generators

**As a maintainer**, I want reserved task types documented without mixing them into v0.1.

**Acceptance criteria**

Reserved tasks include:

* workplane state;
* coordinate frame;
* intermediate point membership;
* feature first-added or last-removed point;
* selector stability;
* counterfactual parameter;
* counterfactual operation removal;
* ambiguous question detection;
* natural-language explanation.

---

# Epic 6: Dataset Splits and Balancing

## Goal

Create leakage-resistant split manifests and task-family balance policies that make generalization claims defensible.

## Story 6.1 - Implement random split

**As an evaluator**, I want a random split for sanity checks and simple model comparisons.

**Acceptance criteria**

* Row IDs are assigned deterministically.
* Split assignment is reproducible from seed and manifest.
* Random split is not the primary evidence for generalization.

---

## Story 6.2 - Implement generator-held-out split

**As a researcher**, I want held-out CADEvolve generator or family groups to test cross-family generalization.

**Acceptance criteria**

* Generator/family IDs are stored when derivable.
* No protected generator group leaks across train and held-out splits.
* Missing generator metadata is handled explicitly.

---

## Story 6.3 - Implement source-subtree and source-family holdouts

**As a researcher**, I want source-level grouping so examples from the same source do not leak through derived rows.

**Acceptance criteria**

* `source_id`, normalized source hash, and source subtree are included in split manifests.
* All task rows from one trace stay in compatible splits.
* Counterfactual variants stay with their base source.

---

## Story 6.4 - Implement operation-held-out split

**As a researcher**, I want to test whether models generalize to unseen operation signatures.

**Acceptance criteria**

* Operation signature hash is stored.
* Held-out operation families can be specified by config.
* Split report lists excluded operation signatures and row counts.

---

## Story 6.5 - Implement topology-held-out split

**As a researcher**, I want to test generalization to unseen topology complexity and shape signatures.

**Acceptance criteria**

* Topology signature hash is stored.
* Split can hold out configured topology bins.
* Kernel-sensitive topology cases are reported separately.

---

## Story 6.6 - Implement near-boundary hard split

**As an evaluator**, I want near-boundary point and geometry cases isolated so headline metrics do not hide boundary failures.

**Acceptance criteria**

* Near-boundary sampling group IDs are stored.
* `test_near_boundary` rows are explicitly tagged.
* Performance is reported separately.

---

## Story 6.7 - Balance dataset classes

**As a dataset builder**, I want task families balanced so easy static rows do not dominate the release.

**Acceptance criteria**

Suggested public row mix:

* 15-20% static code tasks.
* 15-20% selector/workplane tasks.
* 20-25% numeric geometry tasks.
* 15-20% topology tasks.
* 15-20% point membership tasks.
* 10-15% provenance tasks.

---

# Epic 7: Baselines and Model Evaluation

## Goal

Measure shortcut baselines, closed-book model performance, training gains, and split-specific failures.

## Story 7.1 - Implement majority and random baselines

**As a reviewer**, I want trivial baselines so task distributions are interpretable.

**Acceptance criteria**

* Baselines are computed per task family.
* Row counts accompany every metric.
* Invalid-output rate is reported when relevant.

---

## Story 7.2 - Implement static operation-count baselines

**As a reviewer**, I want regex and static-parser baselines to separate static code tasks from geometry reasoning.

**Acceptance criteria**

* Regex baseline is documented as heuristic.
* AST/static baseline uses normalized operation graphs when available.
* Results are reported separately for static tasks.

---

## Story 7.3 - Implement selector and geometry heuristic baselines

**As a reviewer**, I want simple heuristics to reveal shortcut-solvable subsets.

**Acceptance criteria**

Baselines include:

* selector-name heuristic;
* primitive symbolic volume baseline for synthetic fixtures;
* AABB point-membership baseline.

---

## Story 7.4 - Evaluate closed-book LLMs

**As a researcher**, I want representative model evaluations with no CAD execution tools.

**Acceptance criteria**

* Prompts instruct models not to execute code.
* Parser grades only structured answers.
* Results are sliced by task type, split, `requires`, difficulty tags, and near-boundary rows.

---

## Story 7.5 - Evaluate few-shot prompting

**As a researcher**, I want few-shot results without leakage.

**Acceptance criteria**

* Examples come only from training split.
* Prompt template version is recorded.
* Few-shot results are compared with zero-shot results.

---

## Story 7.6 - Fine-tune answer-only models

**As a researcher**, I want a simple supervised training baseline over prompt-answer pairs.

**Acceptance criteria**

* 4B-8B model run is configured.
* Dataset version and split manifest hash are recorded.
* Ablations cover all tasks mixed, no static tasks, numeric-only, topology/selector-only, and provenance exclusions when data allows.

---

## Story 7.7 - Fine-tune with trace-grounded reasoning

**As a researcher**, I want to test whether trace-derived rationales improve hard CAD reasoning.

**Acceptance criteria**

* Rationales are grounded in trace metadata, not hallucinated.
* Rationale template version is recorded.
* Metrics compare format compliance and hard-task accuracy.

---

## Story 7.8 - Run data scaling experiments

**As a researcher**, I want learning curves across dataset sizes.

**Acceptance criteria**

Train at:

```text
1k
5k
15k
50k
full
```

* Task proportions are held fixed where possible.
* Learning curves are reported by task family and split.

---

## Story 7.9 - Evaluate tool-assisted upper bound

**As a reviewer**, I want a verifier-assisted setting separated from closed-book reasoning.

**Acceptance criteria**

* Tool-assisted results are never mixed with closed-book headline scores.
* Exact trace or CadQuery verification is described as an upper bound or alternate setting.
* Tool calls and failures are logged.

---

# Epic 8: Counterfactual and CADEditQA Extensions

## Goal

Extend CAD-QA from diagnostic reasoning to controlled counterfactual and edit-prediction tasks while reusing source records, traces, split groups, and verifier infrastructure.

## Story 8.1 - Generate counterfactual groups

**As a researcher**, I want paired script variants to test sensitivity to relevant edits.

**Acceptance criteria**

Supported counterfactuals include:

* numeric parameter perturbation;
* operation removal;
* selector change;
* workplane offset change;
* fillet/chamfer radius change;
* extrusion height change;
* cut depth change.

* All variants share a counterfactual group ID.
* All variants stay in the same protected split.

---

## Story 8.2 - Define CADEditQA task boundary

**As a product owner**, I want edit tasks framed as a sibling family, not mixed into CAD-QA diagnostic labels.

**Acceptance criteria**

* CAD-QA remains diagnostic question answering.
* CADEditQA is constrained edit prediction.
* Both reuse shared source, trace, label, split, and verifier core.

---

## Story 8.3 - Implement `parameter_edit_direction`

**As a benchmark user**, I want a simple edit-direction task with discrete answers.

**Acceptance criteria**

Allowed answers:

```text
increase
decrease
unchanged
no_valid_edit
```

* Verifier checks target satisfaction.
* Ambiguous or insensitive edits are rejected or labeled `no_valid_edit`.

---

## Story 8.4 - Implement `feature_to_edit`

**As a benchmark user**, I want to choose which feature should be edited to satisfy a target property.

**Acceptance criteria**

* Prompt provides candidate feature IDs.
* Ground truth uses provenance and verifier-derived target satisfaction.
* Tie-breaking is deterministic.

---

## Story 8.5 - Implement selector and workplane repair slices

**As a benchmark user**, I want bounded repair tasks with candidate choices.

**Acceptance criteria**

* `selector_repair` chooses a replacement selector from candidates.
* `workplane_offset_repair` chooses a candidate offset or translation.
* Official scores use verifier checks, not natural-language judgment.

---

## Story 8.6 - Reserve numeric and multi-step edit tasks

**As a maintainer**, I want harder edit tasks documented but not included before supervised baselines are healthy.

**Acceptance criteria**

Reserved tasks include:

* numeric parameter value prediction;
* edit program synthesis under a restricted DSL;
* multi-step edit planning;
* provenance-guided edit selection;
* verifier-guided RL or rejection sampling.

---

# Epic 9: Rendering and Multimodal Extensions

## Goal

Support audit renders and optional multimodal variants without making geometry artifacts required for the default code-only dataset.

## Story 9.1 - Generate audit renders

**As a dataset auditor**, I want small render samples to inspect labels and failure cases.

**Acceptance criteria**

* Render artifacts live outside the default public JSONL.
* Render IDs and camera metadata are stored.
* Local cache paths are not required to read public rows.

---

## Story 9.2 - Generate orthographic views

**As a multimodal researcher**, I want deterministic views for optional visual QA.

**Acceptance criteria**

* Front, top, side, and isometric views can be generated.
* Camera metadata is recorded.
* Render generation is deterministic for a dataset version.

---

## Story 9.3 - Create multimodal prompt variant

**As a researcher**, I want an optional render-backed track to compare code-only and visual reasoning.

**Acceptance criteria**

* Multimodal rows are marked as a separate track.
* Default CAD-QA remains code-only.
* Metrics are not mixed with code-only headline results.

---

# Epic 10: Dataset Packaging and Release

## Goal

Package CAD-QA rows, metadata, manifests, validation reports, and optional artifacts in a reproducible release layout.

## Story 10.1 - Define final public row schema

**As a dataset consumer**, I want each JSONL row self-contained for training and evaluation.

**Acceptance criteria**

Public task rows include:

* stable row ID;
* dataset version;
* task type;
* source and trace IDs;
* target feature;
* split;
* prompt;
* answer type and structured answer;
* choices, unit, tolerance when applicable;
* `requires` and difficulty tags;
* labels, diagnostics, provenance, and hashes.

---

## Story 10.2 - Export JSONL and Parquet files

**As a dataset user**, I want conventional train/test files and optional columnar exports.

**Acceptance criteria**

Release layout includes:

```text
dataset/
  metadata.json
  split_manifest.json
  failure_manifest.jsonl
  jsonl/
    train.jsonl
    validation.jsonl
    test_random.jsonl
    test_generator_heldout.jsonl
    test_operation_heldout.jsonl
    test_topology_heldout.jsonl
    test_near_boundary.jsonl
  parquet/
  artifacts/
```

---

## Story 10.3 - Create dataset card

**As a release owner**, I want a dataset card that explains scope, provenance, limitations, and intended use.

**Acceptance criteria**

Dataset card includes:

* source provenance and license notes;
* task list;
* split definitions;
* label policy;
* known limitations;
* citation and release version.

---

## Story 10.4 - Create reproducibility scripts

**As a reviewer**, I want commands that regenerate or audit a release candidate.

**Acceptance criteria**

Scripts record:

* code commit;
* config hash;
* deterministic seed;
* source manifest;
* worker limits;
* retry policy;
* validation report paths.

---

## Story 10.5 - Add versioning

**As a maintainer**, I want dataset versions to reflect label-policy and schema changes.

**Acceptance criteria**

* Dataset version appears in every row.
* Threshold changes require a new dataset version or relabel audit.
* Schema migrations are documented.

---

# Epic 11: Paper Experiments

## Goal

Run the analysis needed to support the CAD-QA paper claims with transparent task mix, split mix, and failure reporting.

## Story 11.1 - Run dataset characterization

**As a reviewer**, I want to understand what the dataset contains.

**Acceptance criteria**

Report:

* row counts by task type and split;
* source counts by CADEvolve subtree;
* operation count distribution;
* topology distribution;
* selector expression distribution;
* volume delta distribution;
* point sampling strata;
* provenance relation counts;
* rejection reasons.

---

## Story 11.2 - Run baseline comparison table

**As a paper reader**, I want baselines in one clear table.

**Acceptance criteria**

Table includes:

* majority/random;
* regex/static parser;
* selector heuristic;
* primitive symbolic volume;
* AABB point membership;
* closed-book LLMs;
* SFT variants when available.

---

## Story 11.3 - Run task-family comparison

**As a researcher**, I want to know which task families are learnable and which remain hard.

**Acceptance criteria**

Report accuracy and invalid-output rate for:

* operation count;
* selector count;
* bounding box;
* signed volume delta;
* topology count;
* point membership;
* feature provenance.

---

## Story 11.4 - Run split-generalization analysis

**As a researcher**, I want held-out splits to drive the main claims.

**Acceptance criteria**

Report:

* random split;
* generator-held-out;
* source-subtree-held-out;
* operation-held-out;
* topology-held-out;
* near-boundary;
* counterfactual-held-out group when available.

---

## Story 11.5 - Run prompting and training ablations

**As a researcher**, I want to know which prompt and training choices matter.

**Acceptance criteria**

Compare:

* minimal prompt;
* answer schema prompt;
* task-definition prompt;
* selector-reminder prompt;
* few-shot prompt;
* answer-only SFT;
* reasoning SFT.

---

## Story 11.6 - Analyze failure cases

**As a paper author**, I want a failure taxonomy that explains model weaknesses.

**Acceptance criteria**

Taxonomy includes:

* CadQuery syntax misunderstanding;
* selector semantics error;
* workplane/local-global frame error;
* arithmetic error;
* boolean operation sign error;
* topology count error;
* boundary tolerance error;
* provenance over-attribution;
* invalid answer format;
* shortcut reliance.

---

# Epic 12: Paper Writing

## Goal

Write a paper that presents CAD-QA as a controlled, trace-derived CAD program reasoning benchmark.

## Story 12.1 - Draft abstract

**As a paper author**, I want an abstract that states the benchmark, task families, source, and headline findings.

**Acceptance criteria**

* Abstract says CAD-QA is code-only by default.
* Abstract identifies CADEvolve source programs.
* Abstract mentions trace-derived labels and structured evaluation.

---

## Story 12.2 - Draft introduction

**As a paper author**, I want an introduction that motivates CAD program reasoning beyond code generation.

**Acceptance criteria**

* Introduces construction history, selectors, topology, point membership, and provenance.
* Explains why exact CAD execution is not the only desired model behavior.
* States contributions.

---

## Story 12.3 - Draft related work

**As a paper author**, I want related work covering text-to-CAD, program execution, CAD agents, geometric reasoning, and dataset supervision.

**Acceptance criteria**

* Distinguishes CAD-QA from IntersectionQA-style assembly relation tasks.
* Distinguishes diagnostic QA from edit prediction.

---

## Story 12.4 - Draft dataset construction section

**As a paper author**, I want the pipeline clearly described.

**Acceptance criteria**

Section covers:

* CADEvolve ingestion;
* normalization;
* operation graph extraction;
* isolated trace execution;
* snapshots;
* label policies;
* task materialization.

---

## Story 12.5 - Draft task section

**As a paper author**, I want all task families and answer formats specified.

**Acceptance criteria**

* Each MVP task has an example prompt and answer.
* Later task families are described as reserved.
* Parser and metric behavior is explicit.

---

## Story 12.6 - Draft experiments section

**As a paper author**, I want results reported with task mix and split mix.

**Acceptance criteria**

* Baselines and model results are separated.
* Training ablations include dataset versions.
* Closed-book and tool-assisted settings are separated.

---

## Story 12.7 - Draft discussion and limitations

**As a paper author**, I want limitations to preempt reviewer concerns.

**Acceptance criteria**

Discuss:

* kernel sensitivity;
* provenance ambiguity;
* synthetic fixture limits;
* shortcut baselines;
* CADEvolve source bias;
* lack of default geometry artifacts.

---

## Story 12.8 - Draft conclusion

**As a paper author**, I want a concise conclusion that points toward verified CAD editing.

**Acceptance criteria**

* Restates CAD-QA contribution.
* Summarizes strongest result.
* Frames CADEditQA as future or companion work.

---

# Epic 13: Repository and Engineering Infrastructure

## Goal

Build the shared core needed to generate, validate, evaluate, and audit CAD-QA releases.

## Story 13.1 - Create repository structure

**As an engineer**, I want standard package, config, script, test, and artifact directories.

**Acceptance criteria**

Repository includes:

```text
src/
tests/
configs/
scripts/
specs/
docs/
outputs/
```

* Generated outputs are ignored unless intentionally tracked.
* Specs remain the source of truth for task and schema behavior.

---

## Story 13.2 - Add configuration system

**As an operator**, I want all generation and evaluation settings config-driven.

**Acceptance criteria**

Config records:

* source paths;
* task mix;
* split policy;
* label policy;
* seeds;
* worker limits;
* output paths.

---

## Story 13.3 - Add logging and failure tracking

**As an engineer**, I want structured logs and failure manifests so long runs can be debugged.

**Acceptance criteria**

* Every skipped source has a reason.
* Worker failures include stdout/stderr snippets where safe.
* Release reports summarize rejection rates.

---

## Story 13.4 - Add caches for expensive artifacts

**As an engineer**, I want expensive trace, geometry, selector, topology, and provenance artifacts cached separately.

**Acceptance criteria**

* Cache keys include source hash, operation graph hash, execution environment, label policy, and config hash.
* Prompt materialization does not load CadQuery.
* Cache writes are deterministic and safe under parallel workers.

---

## Story 13.5 - Add sharded resumable generation

**As an operator**, I want long generation jobs to resume after worker or machine failures.

**Acceptance criteria**

* Per-worker shard files are merged deterministically.
* Row IDs do not depend on worker completion order.
* Resume skips completed valid shards.

---

## Story 13.6 - Add unit and golden tests

**As a maintainer**, I want fixture-backed tests for labels, prompts, and validation.

**Acceptance criteria**

Tests cover:

* operation graph extraction;
* source normalization;
* volume and bbox labels;
* topology counts;
* selector counts;
* point membership;
* provenance ambiguity;
* schema validation.

---

## Story 13.7 - Add smoke dataset generation

**As an engineer**, I want a fast smoke build that exercises the whole pipeline.

**Acceptance criteria**

* Smoke build includes every MVP task family.
* Smoke build uses at least one CADEvolve-derived source when configured.
* Validation runs in CI or local pre-release checks.

---

# Epic 14: Quality Assurance and Review

## Goal

Audit labels, splits, reproducibility, schema, leakage, and release readiness before public claims.

## Story 14.1 - Manual audit sample

**As a release owner**, I want a manual sample of rows inspected before release.

**Acceptance criteria**

* Sample covers every MVP task family.
* Includes easy, hard, invalid, and near-boundary cases.
* Audit notes are retained with release artifacts.

---

## Story 14.2 - Reproducibility audit

**As a reviewer**, I want evidence that repeated generation from the same inputs is stable.

**Acceptance criteria**

* Two independent runs are compared when feasible.
* Differences are explained or rejected.
* Config, environment, source manifest, and label policy are included in hashes.

---

## Story 14.3 - Leakage audit

**As a reviewer**, I want split manifests checked for protected-group leakage.

**Acceptance criteria**

No leakage across protected splits for:

* source ID;
* generator ID;
* source subtree;
* normalized source hash;
* operation signature hash;
* topology signature hash;
* counterfactual group ID;
* point sampling group ID.

---

## Story 14.4 - Reviewer-readiness checklist

**As the project owner**, I want a single checklist proving release readiness.

**Acceptance criteria**

Checklist covers:

* dataset build;
* reproducibility;
* schema and export;
* label quality;
* leakage;
* evaluation;
* release notes.

**Output**

`specs/reviewer-readiness-checklist.md`.

---

# Suggested Milestones

## Milestone 1 - Specification freeze

Done when:

* benchmark task spec is frozen;
* label rules are frozen;
* schema spec is frozen;
* generation policy is frozen;
* CADEvolve handling is frozen;
* reviewer checklist exists.

## Milestone 2 - Source and trace prototype

Done when:

* CADEvolve subset loads deterministically;
* source normalization works;
* operation graphs are extracted;
* isolated execution records final shape metadata;
* trace records include environment and failure status.

## Milestone 3 - MVP scalar task prototype

Done when:

* `operation_count` rows are generated;
* `bbox_after_step` rows are generated;
* `signed_volume_delta` rows are generated;
* schema validation passes;
* smoke export is reproducible.

## Milestone 4 - Selector, topology, and point tasks

Done when:

* selector result tables are generated;
* topology snapshots are stable enough for labels;
* point membership sampling and classification work;
* near-boundary rows are tagged;
* protected splits exist.

## Milestone 5 - Provenance and counterfactuals

Done when:

* entity IDs and topology matching are available;
* conservative provenance rows are emitted;
* low-confidence rows are filtered;
* counterfactual groups are generated and split-safe.

## Milestone 6 - Baseline evaluation

Done when:

* majority/random baselines run;
* static parser and regex baselines run;
* selector and AABB heuristics run;
* closed-book zero-shot evaluation runs;
* baseline report includes task and split slices.

## Milestone 7 - Training experiments

Done when:

* answer-only SFT runs;
* reasoning-SFT candidate runs;
* data scaling results exist;
* training artifacts and command lines are archived.

## Milestone 8 - Paper draft

Done when:

* dataset construction section is drafted;
* task section is drafted;
* experiments section is drafted;
* discussion, limitations, and release notes are drafted.

## Milestone 9 - Release candidate

Done when:

* full release build passes validation;
* leakage audit passes;
* reproducibility audit passes or explains differences;
* dataset card and metadata are complete;
* reviewer-readiness checklist is complete.

---

# Suggested Sprint Plan

## Sprint 1 - Scope and source smoke prototype

Focus:

* freeze CAD-QA v0.1 task list;
* inspect CADEvolve archive layout;
* materialize a small executable subset;
* create golden fixtures.

Deliverables:

* source manifest;
* smoke source records;
* fixture suite outline.

## Sprint 2 - Operation graph and final-shape execution

Focus:

* AST operation extraction;
* isolated worker execution;
* final volume, bbox, and topology capture;
* failure manifests.

Deliverables:

* trace record prototype;
* execution status report.

## Sprint 3 - Intermediate snapshots and scalar rows

Focus:

* snapshot capture;
* operation count prompts;
* bbox prompts;
* volume-delta prompts;
* schema validation.

Deliverables:

* first JSONL smoke dataset;
* validation report.

## Sprint 4 - Selector, topology, and point tasks

Focus:

* selector result tables;
* topology count rows;
* point sampling and classification;
* near-boundary split.

Deliverables:

* expanded MVP task smoke dataset;
* task-sliced metrics harness.

## Sprint 5 - Provenance and counterfactuals

Focus:

* stable entity IDs;
* topology matching;
* conservative provenance prompts;
* counterfactual group materialization.

Deliverables:

* provenance candidate dataset;
* counterfactual leakage audit.

## Sprint 6 - Splits and packaging

Focus:

* generator/source/operation/topology splits;
* metadata and split manifests;
* JSONL/Parquet export;
* dataset card.

Deliverables:

* release-candidate export layout;
* validation report.

## Sprint 7 - Baselines

Focus:

* majority/random baselines;
* regex/static baselines;
* selector heuristic;
* AABB point baseline;
* closed-book LLM harness.

Deliverables:

* baseline comparison table;
* task/split report.

## Sprint 8 - Training experiments

Focus:

* answer-only SFT;
* reasoning-SFT;
* data scaling;
* generalization by split.

Deliverables:

* training runs;
* artifact manifest;
* ablation report.

## Sprint 9 - Paper writing

Focus:

* abstract and introduction;
* dataset and task sections;
* experiments;
* failure analysis;
* limitations.

Deliverables:

* complete paper draft;
* figures and tables.

## Sprint 10 - Release and review

Focus:

* full validation;
* manual audit sample;
* reproducibility audit;
* leakage audit;
* reviewer-readiness checklist.

Deliverables:

* public release candidate;
* dataset card;
* paper-ready report.

---

# MVP Scope

## MVP dataset

The MVP dataset includes:

* CADEvolve-backed single-script code-only rows.
* Normalized source records.
* Operation graphs.
* Isolated execution traces.
* Intermediate snapshots where supported.
* Public task rows for:
  * `operation_count`;
  * `selector_count`;
  * `bbox_after_step`;
  * `signed_volume_delta`;
  * `topology_count_after_step`;
  * `point_membership`;
  * `feature_provenance_choice`.
* Split manifests and leakage audits.
* Dataset metadata and failure manifests.

## MVP baselines

The MVP reports:

* random and majority baselines;
* regex/static operation-count baselines;
* selector-name heuristic;
* primitive symbolic volume baseline for fixtures;
* AABB point-membership baseline;
* closed-book zero-shot and few-shot LLM results;
* answer-only SFT if compute allows.

## MVP paper claim

The MVP paper claim is:

> CAD-QA provides trace-derived, structured supervision and evaluation for closed-book reasoning about executable CAD construction programs, revealing model weaknesses in selectors, topology, point membership, feature provenance, and counterfactual sensitivity that are not captured by final-shape or text-to-CAD benchmarks.

---

# Backlog Priority

## P0 - Required for paper viability

* Research scope and task definitions.
* CADEvolve source ingestion.
* Source normalization.
* Operation graph extraction.
* Isolated trace execution.
* Snapshot labels for operation count, bbox, volume, topology, selectors, point membership, and conservative provenance.
* Public row schema and validation.
* Leakage-safe splits.
* Dataset export.
* Baseline evaluation.
* Paper dataset, task, experiment, limitation, and release sections.

## P1 - Strongly recommended

* Counterfactual groups.
* Reasoning-SFT over trace-grounded rationales.
* Data scaling experiments.
* Detailed failure taxonomy.
* Audit renders.
* CADEditQA first repair slices.

## P2 - Nice to have

* Multimodal prompt variants.
* Tool-assisted execution setting.
* Full Parquet release package.
* Extended symbolic baselines.
* Candidate edit ranking.

## P3 - Future work

* Unrestricted CAD code repair.
* Multi-step edit planning.
* Broad natural-language explanations as official labels.
* Verifier-guided RL as a primary result.
* Geometry-artifact default releases.
