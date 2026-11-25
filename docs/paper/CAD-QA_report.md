# CAD-QA: A Dataset Verifying Geometry Reasoning over Complex Procedural CAD Programs

Maksym Riabov · 25194372 · MSc Research Project · School of Computing, National College of Ireland
Supervisor: Syed Abidi

<!--
WORD BUDGET
- Hard maximum: 6,000 words. Target: 4,000–6,000 words, excluding references, tables, figure captions and appendices.
- Working split: Abstract 200–250 · Introduction 600–800 · Related Work 1,000–1,400 · Research Methodology 700–900 · Design Specification 800–1,000 · Implementation 500–700 · Evaluation 1,000–1,400 · Conclusion and Future Work 300–400.
- If a section overruns, cut repetition, not evidence. Re-check the split once the Evaluation numbers exist.

HOW TO USE THESE ANNOTATIONS
- Every section carries a comment block: what it must establish, which artifact or doc backs it, and what not to claim.
- These are notes, not prose. Delete a block once its section is written.
- Numbers and status words below are copied from docs/ on 2026-11-25. Re-check before quoting; status vocabulary is verified / exists / missing / planned / unverified.
- Keep one fact in one section. Cross-reference instead of repeating.
- The report structure follows the NCI MSc Research Project Report template; the content docs are docs/dataset/requirements/, docs/dataset/implementation/, docs/train-and-eval/ and docs/experiments/.
-->

## Abstract

LLMs are becoming quite strong in CAD, with yet open, training-ready datasets focus on reconstruction. No training-ready datasets focused on deep reasoning of LLMs on complex, messy shapes exists. We present a dataset allowing to train foundational capabilities of CAD-specific reasoning - 
<!--
ABSTRACT (write last, 200–250 words, no citations)
- Problem: LLMs are proposed as CAD assistants, yet they misread procedural geometry; one wrong selector destroys the part.
- Gap: existing CAD benchmarks test reconstruction or single-pass numeric lookup. BenchCAD Code QA (2,400 questions, 200 parts, last tested 2026-05) already covers single-pass comprehension. Do not claim that no open dataset exists.
- Difference: CAD-QA is multi-hop, distractor-rich, and covers the CAD ontology (faces, edges, vertices, profiles, workplanes, regions, operations) rather than numeric lookup only.
- What was built: a task schema, a CAD graph, a deterministic generator, a released Dataset card, and a no-kernel evaluation harness.
- How it is evaluated: immutable train/validation/test split; no-kernel primary harness (NumPy compute only); kernel access as an upper bound; fine-tuning ablation.
- Findings: report only what has actually run. Current evidence is one step-9 stress test on 60 tasks (60.0% no-kernel vs 88.3% with CadQuery, deepseek-v4.1-flash), not a release-level result.
- Contribution: the multi-hop instrument, the graph-derived supervision target, the generator method, and the evaluation protocol.
- Limitation: public CADEvolve programs; no-kernel setting is a deliberate constraint, not a claim that kernels are unavailable; transfer (H3) not yet measured.
-->

## 1. Introduction

<!--
INTRODUCTION: what the reader must believe by the end
- Background: LLMs are being pushed into CAD generation, editing and assistance (Text2CAD, CAD-Recode, CADBench, BenchCAD).
- Why it is hard: procedural CAD is a chain of boolean and topology-changing operations; the answer depends on the built shape, not on the text; a selector error is destructive to the whole part.
- Why it matters: CAD code is cheap to generate and expensive to verify; an assistant that cannot locate the right face or edge is unusable regardless of syntax correctness.
- Research problem: current models can produce plausible CadQuery, but cannot reliably reason about what the program builds.
- Research question (from docs/PRD.md): how can the raw capability of an LLM to comprehend CAD code be improved?
- Secondary questions: how should a dataset be constructed to improve reasoning over 3D code; does synthetic training transfer to other benchmarks; is the resulting reasoning concise?
- Objectives (docs/PRD.md): build the verifiable instrument; measure base models on it; fine-tune a small open model with graph-derived supervision; test transfer to an independent benchmark.
- Contributions: task schema and CAD graph; deterministic graph-derived generator; tiered 1–10 benchmark with a no-kernel setting; SFT recipe and evaluation protocol; negative results reported as findings.
- Scope: executable CadQuery programs from CADEvolve; P0 is no kernel, NumPy allowed; kernel access is an upper bound (P2), not the headline.
- Limitations to preview: BenchCAD already has Code QA, so the gap is depth not task shape; transfer is P1 and unproven; the release is built from public programs, so contamination must be audited.
- Outline: one sentence per later section.
- Do not claim "no open dataset": BenchCAD Code QA exists. Do not claim "statistically correct" before Evaluation supports it.
-->

## 2. Related Work

<!--
RELATED WORK: bullets only; write the prose from these
- Four streams: (1) CAD reconstruction and generation, (2) CAD comprehension benchmarks, (3) procedural CAD corpora and program evolution, (4) verifiable multi-hop reasoning and small-model fine-tuning.
- Reuse the CA2 literature review as the skeleton (docs/paper/CA2_Riabov_final.md §2.1–2.4), then update it: BenchCAD invalidated the "no open dataset" claim, so the positioning changes from "first" to "deeper".
- Template expectation: read around 50 papers, cite at least 15. Keep the Harvard style of CA2.
- Sources: docs/prior-art.md, docs/research/*.md, docs/experiments/*.md. Every citation must resolve to a DOI or proceedings page; URLs are footnotes, not references.
- End with the gap paragraph: no reviewed work asks multi-hop, distractor-rich questions over a full CAD ontology with a rule-derived gold answer and a no-kernel setting.
-->

### 2.1 CAD generation and reconstruction

<!--
- Text2CAD, CAD-Recode, cadrille, CADENA, CADBench, Text-to-CadQuery, CAD-Editor.
- What they do well: generate or reconstruct a program/mesh from text, images or point clouds; provide large SFT corpora.
- Limitation: they evaluate the produced shape or program, not the model's understanding of an existing program.
- Do not conflate reconstruction accuracy with comprehension accuracy: different construct, different metric.
-->

### 2.2 CAD comprehension benchmarks

<!--
- BenchCAD 1.0: 17,900 execution-verified CadQuery programs; Vision2Code, Code Edit, Vision QA, Code QA.
- Code QA: CadQuery program + numeric question -> number; 2,400 questions over 200 parts; symmetric-ratio metric; 0.80–0.84 total, Spatial Reasoning axis 0.537–0.731 against a 0.42 blind baseline. All Code QA rows are `tested: 2026-05`; quote as "as last measured in May 2026", not as a current gap.
- BenchCAD 2.1 (2026-10-19) is the reconstruction/agentic line: six tasks, 100 Core cases, 60 rounds / 500k tokens, scores not comparable with 2.0. It has no Code QA, so it does not refresh the comprehension numbers. Do not read newer Vision2Code tool scores as comprehension movement.
- BenchCAD 2.0/2.1 are reconstruction only (assemblies, PCB wiring) and add no comprehension task.
- QueryCAD and GeoGramBench: comprehension/program-to-geometry; their published gaps are stale and must be re-run before quoting.
- CADBench, Text2CAD-Bench, CAD-Editor: generation/edit and defect metrics (invalidity rate, exec%), useful as end/defect corroboration.
- Limitation to state: these are single-pass lookups or generation; no multi-hop clue chains, no distractor-rich selection over the ontology, no reasoning-hop curriculum.
-->

### 2.3 Procedural CAD corpora

<!--
- DeepCAD and the program-evolution dataset provide procedural CAD programs at scale.
- CADEvolve is the source corpus here: program families and predicted ABC/ShapeNet mesh families give a group-safe split unit.
- Why procedural programs are the right substrate: gold answers can be computed by executing the program and reading the built shape; no human annotation is needed.
- Limitation: program quality varies; execution failures and degenerate shapes are expected and must be recorded as rows, not exceptions.
-->

### 2.4 Verifiable reasoning and small-model fine-tuning

<!--
- RLVR and verifier work: the verifier is the objective, so a noisy or divergent scorer is optimised; query-verifier audits report self-agreement as low as 53.8% and two configurations disagreeing on 49.9% of pairs.
- Implication: one scorer, exact match, no LLM judge; gold answers computed offline.
- Small-model evidence (docs/prior-art.md): base rank predicts little; the recipe and data predict most; tuned small models reach 90–98% on narrow tool-calling tasks; LFM2.5-350M beats a ~120B teacher in one study.
- Tool-calling and format compliance are separate from reasoning; an ablation must separate them.
- Multi-hop QA literature: the depth/gap framing, not a claim that CAD is just another multi-hop text task.
-->

### 2.5 Research gap

<!--
- One paragraph: reviewed work either reconstructs, answers single-pass numeric lookups, or evaluates generation quality.
- None combines: full CAD ontology, multi-clue selection with distractors, rule-derived gold answers, a no-kernel setting, and a reasoning-hop curriculum.
- This gap justifies the instrument; state it once and do not repeat it in later sections.
-->

## 3. Research Methodology

<!--
METHODOLOGY: the scientific procedure, not the software
- Design: instrument-building plus a controlled training experiment (design science + pre-registered analysis).
- Unit of analysis: one task = program + target + clues + one answer. One CAD model = one CadQuery program; one family may contain many programs.
- Instrument construction: CADEvolve -> normalized programs -> CAD graph -> task definitions -> rendered prompts -> validated release.
- Gold answers are computed by execution or exact derivation; no LLM writes or judges an answer.
- Hypotheses (docs/PRD.md): H2 reasoning supervision beats answer-only (P0 core); H3 transfer to BenchCAD qa_code (P1); H4 CAD-QA pass rate predicts transfer (P1 mechanism); H1 tool-format SFT raises tool-valid rate (P1 control).
- Evaluation arms: Base, Answer-only, CAD-QA reasoning, Format-only, General-only counter-arm; hold base, recipe, prompt set and loss-bearing token budget fixed.
- Primary endpoint: exact structured-answer accuracy on the immutable held-out test at a pre-registered tier.
- Harness modes: no_tools (P2 upper bound), numpy (P0 primary, no CadQuery), cadquery (P2 realistic upper bound; currently missing).
- Do not present the 50–70% planning estimate as a target; the base rate is measured first and the threshold set afterwards.
-->

### 3.1 Research design and hypotheses

<!--
- One instrument, several studies: benchmark validity, baseline measurement, fine-tuning ablation, external transfer.
- State H1–H4 with role and priority, and the decision each outcome forces.
- If H1 holds and H2 fails, the finding is "format compliance, not reasoning"; report it.
- If H3 is null, the dataset-usefulness claim weakens to an internal-split result; report it.
- Define "statistically supported": pooled 95% CI excludes zero and the same sign in at least 2 of 3 seeds.
-->

### 3.2 Dataset construction procedure

<!--
- Source selection: CADEvolve metadata, family-safe selection, fetch, normalize (stages 01a–01e).
- Extraction: AST records what the program says; execution records what the shape is; neither side fills the other (stage 02).
- Task construction: quota plan, construct definitions, resolve deficits by replanning or expanding data (stage 03).
- Rendering and export: rule-rendered prompts and choices, then release validation (stages 04–05).
- Determinism: same inputs, versions and shard count produce byte-identical parts and the same run identity.
- Failure model: rejected programs and tasks become rows with reasons; counts must add up.
-->

### 3.3 Evaluation protocol

<!--
- Immutable split: approximately 70% SFT / 15% RL / 15% eval; eval is split into validation and test; the test portion is the thesis number.
- Group safety: no CADEvolve program family appears in more than one part; no external benchmark family appears in any training arm.
- Harness: model -> chat template -> tool declarations -> generation loop -> tool execution -> parser -> scorer.
- Answer contract: one submit tool per answer format; exact structured match; invalid output is a failure, not an exclusion.
- Metrics: accuracy; invalid-output rate; missing-response rate; accuracy by step, target category, clue type, answer meaning and harness mode; reasoning length; pass@1 with a CI; chance-corrected rate for bounded answer spaces.
- Baselines: cost-effective external models through the same harness; every number names its slice.
- Freshness: no external gap is quoted without a current re-run; record the benchmark's `tested` date next to every number.
-->

### 3.4 Statistical analysis

<!--
- Binary outcomes: McNemar exact two-sided on discordant rows, plus paired bootstrap (10,000 resamples) 95% CI.
- Multiplicity: Holm within the three H2 comparisons and separately within the three H3 comparisons.
- Chance correction: report raw and corrected rates, never only corrected; p_chance = 1/K for labels, 1/2 for boolean, 0 otherwise.
- Seeds: three per confirmatory training arm; report each seed and the mean; do not hide a sign flip.
- Power: compute MDE from the frozen split before the final test; declare anything below MDE exploratory.
- Freeze: endpoint, arms, revision hashes, tier, n, seeds, MDE, alpha and stopping rule are fixed before the final test; the test runs once.
- Do not select the best checkpoint or the best tier after seeing results.
-->

### 3.5 Ethics, licensing and reproducibility

<!--
- Public programs and public data; no human subjects; check each corpus licence and record it.
- Contamination: dedup CAD-QA programs against every transfer benchmark; exclude their families from every training arm.
- Reproducibility: tagged release, Dataset card, run manifest with versions and hashes, one command to regenerate.
- Logging: every LLM call, internal reasoning, visible output and tool call is recorded and reconstructable.
- Compute: small open models on a single GPU; report cost and hardware.
-->

## 4. Design Specification

<!--
DESIGN: what the instrument is, before how it was coded
- One figure here: the pipeline from CADEvolve to release artifacts.
- One worked task example: program, rendered prompt, gold answer, answer evidence.
- Keep requirements-level rules here; keep code paths in Implementation.
- Vocabulary must match docs/glossary.md and docs/dataset/requirements/terminology.md.
-->

### 4.1 Task model

<!--
- A task has five independent dimensions: target, clues, answer format, answer meaning, reasoning step count.
- There are no task types or task patterns; the generator composes dimensions.
- Target categories (P0): operation, feature, solid state, face, edge, vertex, CadQuery profile, CadQuery workplane, region, scalar value.
- Clue types: property, relation, comparison, provenance (P0); aggregation (P1).
- Clue reduction forms: filtered, selected_in_earlier_clue (P0); aggregated (P1); cross_state (P2).
- Answer formats: multiple choice, number, integer, boolean, 3D coordinate, bounding box (P0); structured object (P1).
- Answer meanings: identity, volume, area, length, distance, angle, count, membership, position, extent, material change, topology change.
- Step counts: 1 warmup, 2–5 main (P0), 6–10 hard (P1, gated by a release gate).
- Target mix: 1 step 5%, 2 10%, 3 30%, 4 25%, 5 15%, 6 7%, 7 4%, 8 2%, 9 1%, 10 1%.
- Every clue must narrow and be necessary; necessary clues consume distinct wrong answers; a candidate set with m distinct answers supports at most m−1 clue steps.
- One task has exactly one correct answer; answer-equivalent entities at the stated precision count as one answer.
-->

### 4.2 CAD graph

<!--
- Entities: program, operation, feature, solid state, face, edge, vertex, CadQuery profile, CadQuery workplane, region, point probe (P0); path and selector result (P1).
- Relations: before/after, creates, uses, derived_from, has_face/has_edge/has_vertex, adjacent_to, adds_material/removes_material/part_of (P0).
- Face attributes: surface kind (plane, cylinder, cone, sphere, torus, bspline, other), bounding-box position extremes, outward normal.
- Measurements: volume, area, length, distance, angle, counts, centroid, bounding box, volume change, topology change; units, precision and tolerance are explicit.
- Parallel and perpendicular are angle values at render time, not stored relations.
- Point probes supply membership points; one or two per state, opposite labels when both survive; no probe means no membership task, a recorded deficit.
- States: P0 uses the final state; one named intermediate state is P1; the before/after pair is P2.
- Graph quality rules: every entity belongs to one program; every relation has two endpoints; missing provenance is a miss, not a pass.
-->

### 4.3 Generator architecture

<!--
- Five stages with typed artifacts: 01 external ETL, 02 extraction and graph, 03 task generation, 04 render, 05 validate and export.
- 03 splits into 03a quota allocation, 03b construction, 03c deficit resolution; 03c is a bounded loop back, not a terminal step.
- Incremental run: immutable Parquet parts, resumable, manifest-pinned inputs and policy hashes; a changed input is a new run directory.
- No full enumeration: quotas are sampled with deterministic ordering, deduplication and backfill.
- Language boundary: Go owns orchestration, graph assembly, task generation, rendering, release state; Python only normalizes programs, extracts the AST and executes CadQuery.
- Bulk data is typed Parquet; JSON is control only (manifest, completion markers, deficit ledger).
- UUIDs are stable: UUIDv5 from program-scoped IDs in extraction, UUID logical type in Parquet.
-->

### 4.4 Release contract

<!--
- Artifacts: release.parquet, manifest.json, dataset-card.md, failures.parquet, support/ with five step-support tables.
- One row per task; the prompt column is the only LLM-facing column; gold answer columns never enter the prompt.
- Answer value, tolerance and evidence are typed structs (tagged union), not JSON strings.
- Target size: at least 10,000 tasks and at least 1,000 distinct programs (P0); no program above 1% of tasks (P1).
- Warmup is 5% of tasks and is included in the count; at least 80% of tasks need three or more steps; at least 95% require the built shape.
- Splits: 70/15/15 target, group-safe, frozen in split_manifest.json; later releases preserve earlier split assignments.
- Support tables state which dimension values can occur at each step count and why not.
- The Dataset card states what the dataset is and is not suitable for, plus the answer conventions and precision.
-->

### 4.5 Validity rules and quality gates

<!--
- R-1 every answer is correct; R-2 exactly one answer; R-3 multiple-choice fairness (at least five, aim seven, real candidates, no leak); R-4 at least 95% shape-required; R-5 shortcut resistance (P1); R-6 no answer leakage.
- Coverage and balance: every supported value at every step count; formats 5–25% over the release; no clue type above 25%; each answer meaning 1–10% (P1 bounds).
- Shortcut gate: dependency operation minimum provisionally 3; a topology-changing chain passes even when the answer is closed-form (deliberate conservatism); unknown fails closed.
- The gate is a floor, not a proof: the baseline measures whether a model can still shortcut.
- Human review: sampled tasks covering every dimension value, up to step 10, before release; unclear wording is a defect.
- Reproducibility: same inputs and versions give the same dataset; every rejection is reported with a reason.
-->

## 5. Implementation

<!--
IMPLEMENTATION: only the final stage; no code listings, no user manual
- Name the outputs: generator CLI, Parquet artifacts, release directory, harness, trained adapter.
- Name tools and languages: Go module, Python worker, CadQuery/OCP, PyArrow/Parquet, uv, pytest, Liquid fine-tuning stack, HuggingFace/PyTorch.
- State what exists and what does not; do not present planned work as done.
- One table of artifact -> status (exists / verified / missing) is enough.
-->

### 5.1 Extraction

<!--
- 02a parses and validates an allowlisted CadQuery subset, assigns stable operation and entity IDs, rewrites the program for recording.
- 02b executes the instrumented program once in a child process, captures runtime values, classifies geometry, emits a failure tombstone on failure.
- 02c joins AST and runtime by program_id and operation_id; no partial graph is persisted.
- Pins: CadQuery/OCP versions are part of the run manifest; a version change is a new run.
- Failure model: per-program fail-fast, recorded as a row; no exception aborts the run.
-->

### 5.2 Graph assembly

<!--
- Persist entities, relations and measurements as typed tables; derive deterministic UUIDv5 graph IDs.
- Point probes: centroid plus a seeded near-surface probe; opposite labels when both survive; clear-case margin discards ambiguous probes.
- Validation: must-extract capability set; release fails if no accepted graph carries a required capability.
- Determinism: stable ordering by program_sha256 and operation order; no random IDs.
-->

### 5.3 Task generation

<!--
- 03a builds family profiles, allocates quotas against the release targets, assigns split and attempt budgets; global allocation is serial.
- 03b constructs definitions per shard, resolves target binding, clue predicates and the gold answer, applies uniqueness, answer-equivalence, necessity, leakage and shortcut checks.
- 03c handles deficits by reassigning programs or expanding the corpus, bounded by budget; accepted misses are recorded.
- Construction is parallel per shard; accepted definitions merge in deterministic order.
-->

### 5.4 Prompt rendering, validation and export

<!--
- 04 renders prompts and multiple-choice candidates from typed task definitions; every LLM-facing string is data in generator/config/prompts.yaml, never hardcoded.
- A template change bumps the prompt version and hash; the prompt is the user message, no system prompt is shipped.
- 05 runs release checks (counts, coverage, balance, leakage, answer evidence, support tables) and writes release.parquet, manifest, Dataset card, failures, support.
- No partial release: a failed row fails the release build, not the published artifact.
-->

### 5.5 Training and evaluation harness

<!--
- Local tool-call harness, shared by training and evaluation: submit_* tools per answer format, run_code for NumPy mode, parser, exact-match scorer.
- Base model: a small open LFM2.5 checkpoint (1.2B/2.6B class); LoRA SFT through the Liquid cookbook; teacher traces from deepseek-v4.1-flash.
- Training data mix: tool format, CAD-QA reasoning traces, general math/code preservation; two phases with an advancement gate.
- Scorer: one implementation for evaluation, rejection sampling and any reward; the current three-scorer split is a recorded defect and must be reconciled before the thesis number.
- Sandbox: run_code is an accidental-misuse guard, not a security boundary; state that honestly.
- Status at writing: numpy and no_tools modes exist; cadquery mode is missing; no preserved NumPy run; three scorers disagree; transfer not run.
-->

## 6. Evaluation

<!--
EVALUATION: only results that exist at submission time
- Report the instrument result first (validity and composition), then baseline, then the training ablation, then transfer.
- Every table names its split, tier, n, model and harness mode.
- Report negative and null results; do not hide them.
- Planned-but-unrun work belongs in Future Work, not here.
- Visuals: accuracy by step count; accuracy by answer meaning; ablation risk difference with CI; transfer point estimate with CI.
-->

### 6.1 Experiment 1: instrument validity

<!--
- What is checked: release counts, coverage and balance against the targets, uniqueness, leakage audit, answer evidence, reproducibility hash.
- Report the actual release size and the known misses; the ~10,000-row release is a contingency, the first run is ~1–2k rows, and the 1,445-row release is superseded.
- Human review: sampled tasks per dimension value; inter-rater or owner review; list the defects found and fixed.
- Shortcut audit: distribution of dependency-chain lengths and rejection counts (P1).
- Do not claim validity from the oracle path alone: the oracle proves the gold encoding is accepted, not that a wrong answer is rejected. A near-miss fixture is required.
-->

### 6.2 Experiment 2: no-kernel baseline and kernel upper bound

<!--
- Current evidence is a step-9 stress test, not a release estimate: 60 tasks, deepseek-v4.1-flash, temperature 0, one sample.
- Result: no-kernel 36/60 = 60.0% (3 wrong, 21 no submission, $1.46) vs CadQuery 53/60 = 88.3% (7 wrong, $0.29).
- Kernel access adds 28.3 percentage points; the 21 no-submissions are 64k output-budget failures, not wrong answers.
- Weak cells with kernel: face targets 75%, length 66.7%, provenance-clue tasks 78.3%; count/position/vertex near 90–100%.
- Literal matches: 9 number tasks have the gold value as a literal; 7/9 correct with kernel vs 46/51 without, so literals do not explain the result.
- Caveats: one model, one sample, above-release P1 aggregation clues, NumPy primary arm not run, process isolation not a security sandbox.
- Do not call this the thesis result; it is a diagnostic that the no-kernel setting measures something real.
-->

### 6.3 Experiment 3: fine-tuning ablation (H1, H2)

<!--
- Primary comparison: CAD-QA reasoning vs Answer-only, same task rows, general mix, prompt set and loss-bearing token budget; paired by row.
- Secondary: vs Base and vs Format-only (a bundle, not a reasoning isolation); Holm within the family.
- Endpoint: exact-answer accuracy on the pre-registered hard tier; paired risk difference in percentage points with 95% CI.
- Report all three seeds separately and the mean; a claim needs the pooled CI to exclude zero and the same sign in at least 2 of 3.
- Report invalid-output rate and tool-valid rate (H1) separately; do not fold format compliance into the reasoning claim.
- Include a general math/code monitor as a covariate; a drop above the review threshold is a specialization tradeoff, not a failed run.
- Status: fill only after the runs exist. If unrun at submission, move to Future Work and say so.
-->

### 6.4 Experiment 4: external transfer (H3, H4)

<!--
- Target: BenchCAD qa_code, official full split and official metric; report percentage-point difference with a paired CI. edit_code and Text2CAD-Bench corroborate.
- Preconditions: reachability pilot (base low but nonzero), format-adaptation control, contamination audit, frozen subset and scorer. The pilot doubles as the Code QA freshness check: run a current model on the official split before quoting the 2026-05 gap.
- No subset-shopping; spatial-axis and family breakdowns are diagnostics only.
- H4: dose-response of CAD-QA pass rate vs external score at fixed recipe and matched compute, with a general-only counter-arm.
- A null transfer is a finding: the dataset would improve only its own split.
- Status: planned, not run. Do not fabricate a number.
-->

### 6.5 Discussion

<!--
- Answer the research question directly: does the instrument expose a real gap, and does graph-derived supervision close it.
- Interpret by step count, target category and answer meaning, not only by aggregate accuracy.
- Compare with BenchCAD Code QA: same task shape, different depth; explain why a high single-pass score does not imply multi-hop success.
- Threats: contamination, saturation, small per-cell n, one model, scorer disagreement, kernel-version drift, prompt-template sensitivity.
- Be honest about design weaknesses and what would change the conclusion.
- Tie back to the literature: what this result adds, and what it cannot support.
-->

## 7. Conclusion and Future Work

<!--
CONCLUSION (300–400 words)
- Restate the question, the instrument and the work done; state how far each objective was met, including partial and failed ones.
- Key findings: only measured ones; name the tier and split.
- Implications: benchmark design, no-kernel evaluation, graph-derived supervision, small-model training.
- Limitations: public-program bias, no-kernel constraint, transfer unproven, release size, single-family or single-snapshot risks.
- Future work: the kernel-query pivot (generate the query, score by execution); RL on harder tiers after the readiness gate; reasoning conciseness from the critical path; CADEditQA; 6–10 tiers once the release gate passes; more models and seeds; a larger public release.
- No new results, no new citations, no sweeping parameter-sweep promises.
-->

## References

<!--
REFERENCES
- Harvard or APA, per the NCI Library Referencing Guide; keep the CA2 list and extend it.
- At least 15 references in the paper; aim for the ~50 read.
- Every entry resolved to a DOI or proceedings page; URLs go in footnotes.
- Include: BenchCAD, Text2CAD, CAD-Recode, cadrille, CADENA, CADBench, Text2CAD-Bench, CAD-Editor, QueryCAD, GeoGramBench, DeepCAD, CADEvolve, the program-evolution dataset, plus the fine-tuning, RLVR/verifier and tool-calling sources in docs/prior-art.md.
- Do not cite a benchmark number without checking its current split and metric.
-->
