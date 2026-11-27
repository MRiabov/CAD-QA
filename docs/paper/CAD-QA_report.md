# Deep-3D-CAD-QA: A Dataset Verifying Geometry Reasoning over Complex Procedural CAD Programs

Maksym Riabov · 25194372 · MSc Research Project · School of Computing, National
College of Ireland Supervisor: Syed Abidi

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
- The report structure follows the NCI MSc Research Project Report template; the content docs are docs/dataset/requirements/, docs/dataset/implementation/ and docs/experiments/.
-->

## Abstract

LLMs are becoming notably strong in CAD reconstruction, with open,
training-ready datasets focusing on reconstruction, engineering standard
following and editing. However, no training-ready datasets focused on deep
reasoning of LLMs on complex, messy shapes exist. We present a large dataset
that allows training foundational capabilities of LLMs in deep geometric
reasoning, generated and validated through a CAD kernel, not requiring expensive
expert validation. To aid in efficient training of LLMs on our dataset, we
attach a minimum required reasoning steps that allows validated step-by-step
solutions. We show that frontier models are only 50–80% successful without tool
assistance, showing headroom in geometrical reasoning. We open-source the
dataset at https://huggingface.co/MRiabov/[...].

## 1. Introduction

AI for CAD starts seeing a surge in industry in Q3 2026, with reconstruction
capabilities being near-saturated on complex benchmarks [BenchCAD 1.0].
Foundational, large datasets, including recent ones in 2026 such as CADEvolve
(Elistratov et al., 2026), CADENA (https://arxiv.org/abs/2608.00799),
Zero-To-CAD focus on image- and Text-to-CAD reconstruction, training on which
has mostly saturated the reconstruction benchmarks, however CAD editing is still
consistently less than half successful [citation*S* required]. Existing datasets
also measure QA answering on CAD, in particular answering about engineering
standards following (engineering standard e.g. ISO) from CadQuery code [benchcad
citation?], however, they are simple, rudimentary question answering, requiring
only one lookup or knowledge of a particular standard and not deep geometrical
reasoning.

As such, the field is still lacking a dataset that would allow ready training
on: verification of reasoning on more complex CAD reasoning beyond simple
question answering pairs, as well as optimization of conciseness on reasoning in
such tasks.

Our primary research question:

- How can we improve the raw capability of an LLM to comprehend the geometry
  resulting from CAD code?

Secondary:

- How can we increase the efficiency of geometrical reasoning of LLMs? [NOTE:
  I'm unsure this is a good RQ to state as I won't train a model] [TODO. Ideas:
  efficiency - directly addressed by building a graph and allowing training on
  it]

Our objectives are:

- To create a dataset that allows higher correctness on deep, complex CAD
  reasoning tasks.
- To create a dataset that is easy to train efficient reasoning on.

Our contributions are:
- A large dataset allowing training of models on question-answering pairs of
  deep and progressively complex CAD questions
- Critical path proof to the questions allowing easy and dense optimization of
  LLM trajectories on it,
- Benchmarking SOTA models and showing where the current state of the art is
  still lacking.

The limitations of our studies are in the transfer of our dataset to other
benchmarks:

- We evaluate two LLMs only on approximately 750 trajectories each, spanning
  multiple levels and multiple clue types. Our results are statistically limited
  by budget.
- We do not train a model on the dataset, nor measure transfer of improvement to
  other benchmarks; primarily due to budget.
- We only train on one CAD engine. There are now numerous BREP kernels including
  open-source ones [brepbench], but we deem it sufficient as CadQuery is the
  widely adopted open-source CAD modelling application, being used in most major
  papers [Zero-to-CAD].

We will structure our work as follows:
1. Related work will go over the recent contributions, in particular the state
   of the art in 3D applications, reconstruction and shortcomings, as well as
   foundational datasets.
2. Research methodology will outline the structure of the dataset and evaluation
3. Design specification will go over what the dataset is expected to be and the
   dataset validity procedures that are in place; it will also go over
   evaluation procedures.
4. Implementation will briefly describe the implementation structure of the
   dataset,
5. Evaluation will focus on evaluating the state of the art and showing
   deficiencies of existing models,
6. Conclusion and Future Work will show the future work.

## 2. Related Work

LLMs in CAD have seen a surge in research and industry results in Q2 and Q3,
producing 2x more literature than Q3 a year ago in the same field. In Q3, 19#
papers were produced, with 45% focusing on generation, 20% on agent tool-use,
~20% focusing on application and ~9% on evaluation or foundational datasets.

<!--
RELATED WORK: bullets only; write the prose from these
- Per reviewed paper: approach, method, results, one strength, one limitation; group minor papers by approach.
- Four streams: (1) CAD reconstruction and generation, (2) CAD comprehension benchmarks, (3) procedural CAD corpora and program evolution, (4) verifiable multi-hop reasoning.
- Reuse the CA2 literature review as the skeleton (docs/paper/CA2_Riabov_final.md §2.1–2.4), then update it: BenchCAD invalidated the "no open dataset" claim, so the positioning changes from "first" to "deeper".
- 2026-11-25 update material: research_notes/CAD AI state of the art/ (six notes: llm_cad_generation, brep_and_geometry_learning, benchmarks_and_evaluation, downstream_engineering_tasks, industry_landscape, volume_venues_and_field_map) and reports/CAD AI state of the art.md. Every arXiv ID below was checked against the notes; do not add an ID that is not in them.
- Shape of the field, for one framing sentence: ~45% LLM/code-generation, ~20% agent and tool-use, ~16% geometry-native learning, ~20% applications, ~9% evaluation, ~5% surveys (overlapping rows). Growth is concentrated in agents (4.3×) and text-to-CAD (3.2×), not in the venues: NeurIPS 2026 accepted 4 CAD papers, CAD'26 27 total.
- The qualitative shift to name: the objective function moved from executability plus Chamfer/IoU to kernel-adjudicated rewards (ConCAD constraints, PhyCAD physics, DrawScore projection). That is progress in what is optimised, not in what is understood; say so explicitly.
- Carry CA2's Table 1 forward and update the rows: add Parametric CAD Bench v3 (agentic authoring, 61.03), CADWorld (GUI, 17.5% vs 87.0%), EngiWorld (3.6% cross-application), RealCADBench (industrial intents), MechReason (multi-image, 2–3 steps). Keep the columns work | task | input → output | grading | max reasoning steps | curriculum/critical path. The BenchCAD row becomes the load-bearing comparison: generation, edit and single-fact numeric QA, 1–2 steps.
- Terminology decision: CA2 says "hop"; the report and dataset docs say "task reasoning step count". Use the full term in prose and the table header, and define "hop" once if it is kept in the table for continuity with CA2.
- Template expectation: read around 50 papers, cite at least 15. Keep the Harvard style of CA2.
- Sources: docs/prior-art.md, docs/research/*.md, docs/experiments/*.md. Every citation must resolve to a DOI or proceedings page; URLs are footnotes, not references. New arXiv-only preprints are acceptable if labelled as such.
- End with the gap paragraph: no reviewed work asks multi-step, distractor-rich questions over a full CAD ontology with a rule-derived gold answer, a non-numeric answer contract and a no-kernel setting.
- Do not write "SOTA" as a claim about our instrument; use it only for the surveyed work.
-->

### 2.1 CAD generation and reconstruction

Recent work has demonstrated major progress in CAD generation and
reconstruction, partially driven by large synthetically generated datasets -
both Zero-To-CAD and CADEvolve were released as million-scale datasets, where
CADEvolve released a dataset of "deliberately as complex shapes as possible"
which, in CADEvolve, was used to train a reconstruction model. A plurality of
papers have focused on improving Text- and Image-to-CadQuery, saturating
reconstruction benchmarks [CADENA, ConCAD], while editing is unsaturated;
perhaps due to editing being more complex to scale data-wise.

### 2.2 Geometry comprehension benchmark

Closest spiritually to our dataset are procedurally generated 2D and 3D geometry
reasoning benchmarks such as SiT-Bench (Guo et al., 2026) and Real-3DQA (Ma et
al., 2026), which explicitly evaluate models' 3D comprehension abilities from
text alone, without visuals. They are similar in that they evaluate models on
procedurally generated geometry, but they do not evaluate or focus on
CAD-specific geometry such as selectors, vertices, and boolean operations — only
on text descriptions of scenes.

### 2.3 CAD comprehension benchmarks

BenchCAD 1.0 has evaluated CAD generation across 4 benchmarks - Vision2Code,
Code Edit, Vision QA, Code QA; so Code QA was already studied, however the
dataset focuses on benchmarking simple question answering such as compliance to
a standard (e.g. whether a thread size is compliant), whereas our dataset
focuses on verification of correct geometrical reasoning, at scale and varying
depth. BenchCAD 2.0/2.1 are reconstruction only (assemblies, PCB wiring) and add
no comprehension task. QueryCAD is an earlier similar work evaluating
capabilities of LLMs on answering factual questions based on CAD models, but
without CadQuery; again, without depth.

MechReason is a benchmark evaluating multi-view and multi-hop reasoning of LLMs
on mechanical engineering publications and papers; however it synthesizes QA
pairs from papers and does not evaluate models on CAD programs, nor is it
verifiable via a kernel.

### 2.4 QA datasets and verifiable reasoning 

Verifiable reasoning and evaluation by tool calling have become the de-facto
standard for factual question-answering training, with the advantage of:

- Allowing stable training - no noisy LLM-as-a-judge is necessary, with
  verifiable reasoning being ubiquitous in physics, 3D and geometry datasets,
- Allowing conciseness training - numerous studies such as
  [https://arxiv.org/html/2606.17687v1] focus on removing redundant reasoning
  and thus cost and latency by following the minimum required reasoning to
  achieve the objective.

### 2.5 Research gap and justification

<!--
- One paragraph: reviewed work either reconstructs a shape, answers a single-fact numeric question about a program, or evaluates generation quality.
- None combines: the full CAD graph (operations, solid states, faces, edges, vertices, CadQuery profiles, CadQuery workplanes, regions), multi-clue selection with distractors, a rule-derived gold answer, a non-numeric answer contract, a no-kernel setting, and a task reasoning step curriculum.
- Update the phrasing from CA2: the gap is depth above BenchCAD Code QA, not the existence of a comprehension task. The one-sentence version: "BenchCAD occupies the base task shape and does it well; CAD-QA occupies the depth above it, and the depth is where editing, agents and industrial use fail."
- Evidence that the depth matters, keep to one sentence each: instruction-guided editing succeeds ~37% and industrial edit prediction 29.0%; GUI work 17.5%; cross-application 3.6%. All three bottom out in entity and constraint resolution, which is comprehension.
- Keep CA2's three-part niche statement, not only the depth part: (1) reasoning depth beyond single-step tasks; (2) a measurable shortest required reasoning path, which is the conciseness contribution; (3) distractor-rich, non-clean problems rather than one-step textbook cases. The 2026 literature adds a fourth: an exact, non-geometric answer contract.
- Companion document: research-gap.md states the candidate gaps, the neighbour comparison, the falsification conditions and the claims to avoid. Do not duplicate its table here; summarise and point.
- This gap justifies the instrument; state it once and do not repeat it in later sections.
-->

## 3. Research Methodology

Much like in software engineering, being proficient in one area, such as SQL
queries, doesn't mean an agent is proficient in machine learning; nor does being
proficient in Python make an agent proficient in Rust. Similarly, CAD requires
understanding of numerous operations and relations, and underexposure to some
will lead to knowledge gaps as highlighted by CADEvolve (an early 2026 paper)
(Elistratov, 2026), where agents were not proficient in everything but modelling
with boxes. As such, we construct a wide variety of tasks as well as
compositions and report success rates on them separately.

### 3.1 Research design, variables and hypotheses

We construct the dataset across multiple axes:

- Tasks - what tasks in particular do models fail on?
- Depth - when task geometrical complexity is composed, what is the reasoning
  depth a model can solve reliably?
- Harnesses - given different tools available to the agent (no tools, NumPy,
  CadQuery), how does being able to verify, and with which tools, increase
  success rate?
- Models - we will evaluate a number of models to ensure fairness of evaluation.

Our hypotheses are: H1. There are limits beyond which models would show
reasoning gaps; different per harness.

As other datasets already cover simple question-answering pairs (such as lookup
radius of a hole), we deliberately abstain from questions not requiring deep
geometrical reasoning, with at least 95% of our dataset containing
geometry-focused questions.

### 3.2 Dataset construction procedure

We use the CADEvolve dataset as it is the largest and most diverse dataset among
the publicly available corpora. We normalize programs using AST and CadQuery
post-processing to extract a graph of entities and dependencies between them,
such as edges, vertices, faces, boolean operations and derive relations between
them, such as distances, angles between them. The graph, with later
post-processing, allows us to deterministically and verifiably generate
questions such as in Figure 1. We will expand on dataset construction in the
design specification section.

![**Figure 1.** A task generated from a box-with-hole program. The question and its two clues are on the left, the final solid on the right. The target circular edge (orange) is named by both clues: it is an edge of the top face (blue, clue 1) and an edge of the cylindrical face (green, clue 2). The answer, 12.57 mm, is computed by executing the program.](figures/task-example.png)

### 3.3 Evaluation protocol

We evaluated models on completion of the tasks under varying tasks, depths and
harnesses, reporting:

- Cost in tokens and quantity of tool calls spent per evaluation,
- Correctness

Over the combination of:
- Tasks (clues),
- Depth (number of narrowing steps required to derive an answer)
- Models
- Harnesses

### 3.4 Harnesses

To evaluate different CAD reasoning skills and the internal reasoning of models:

- without access to tools (the notable advantage of this is that stronger models
  can estimate correct solutions *without* doing a tool call),
- NumPy-only harness - the importance of this harness is twofold: being able to
  estimate complex CAD without a harness, such as in cases of "on-paper"
  feasibility analysis, as well as not being limited to CadQuery alone - for
  example not every CAD modelling assistant has shell access to a CAD kernel,
  but they may have access to a shell.
- CadQuery-enabled harness - CadQuery is the most ubiquitous CAD library, being
  popular in the largest recent CAD datasets - Zero-To-CAD, CADEvolve and
  others.

### 3.5 Statistical analysis

<!--
- Binary outcomes: McNemar exact two-sided on discordant rows, plus paired bootstrap (10,000 resamples) 95% CI.
- Multiplicity: Holm within the harness comparisons and separately within the model comparisons.
- Chance correction: report raw and corrected rates, never only corrected; p_chance = 1/K for labels, 1/2 for boolean, 0 otherwise.
- Samples: report the sample count per task and the mean; do not hide a sign flip.
- Power: compute MDE from the frozen split before the final test; declare anything below MDE exploratory.
- Freeze: endpoint, models, harness modes, revision hashes, tier, n, MDE, alpha and stopping rule are fixed before the final test; the test runs once.
- Do not select the best tier after seeing results.
-->

### 3.6 Ethics, licensing and reproducibility

<!--
- Public programs and public data; no human subjects; check each corpus licence and record it.
- Contamination: dedup CAD-QA programs against every benchmark we evaluate on; exclude their families from the release.
- Reproducibility: tagged release, Dataset card, run manifest with versions and hashes, one command to regenerate.
- Logging: every LLM call, internal reasoning, visible output and tool call is recorded and reconstructable.
- Compute: small open models on a single GPU; report cost and hardware.
-->

## 4. Design Specification

In this section, we will describe how the dataset and evaluation procedures were
built, focusing on the dataset.

### 4.1 Task model

A task is a single question-answering pair, defined by input geometry and the
clues supplied to the model. Given a 3D model as a whole which may have 20,000
entities and relations, the model needs to narrow down to an entity or
operation, for example finding the correct face among hundreds of entities.

The model narrows down by clues. For example, in a simple box-with-a-hole
program (Figure 1), we derive all entities and relations between them, and
select clues as follows:

- Picked result entity: circular edge where the hole meets the top face,
- Picked property of the edge: length.

- Clue 1: the target edge is an edge of the face touching the top of the
  axis-aligned bounding box.
- Clue 2: the target edge is an edge of the cylindrical face.

The model thus needs to find all 15 edges of the final solid state, keep the
five that are on the top face, and filter them into one that would be
cylindrical. By design and verifiably, each clue in the dataset is necessary, so
the LLM can never reach the answer while omitting any of the clues.

In total, we support the following types:

- Target categories: operation, feature, solid state, face, edge, vertex,
  CadQuery profile, CadQuery workplane, region, scalar value.
- Clue types: property, relation, comparison, provenance, aggregation.
- Answer formats: multiple choice, number, integer, boolean, 3D coordinate,
  bounding box; structured object.

### 4.5 Validity rules and quality gates

In order to validate the quality of our dataset, we enforce after-construction
validation:

1. Every answer is correct,
2. There is exactly one answer, 
3. In multiple-choice questions, there are at least 5 answer options, with a
   mean of 7, so as to ensure fairness of the answer,
4. At least 95% of our dataset has geometrical questions as noted in
   [3.1](<CAD-QA_report#31-research-design-variables-and-hypotheses>)
5. There is no answer leakage in the question.
6. Human review: while tasks are sampled deterministically, we review a sample
   of questions that is as diverse as possible.

## 5. Implementation

The code is split into two independent sections with separate documentation and
codebases - dataset generation and evaluation. Dataset generation is modelled as
Directed Acyclic Graph (DAG) data extraction and transformation pipeline. For
developer and reader convenience and interpretability, stages follow
alphanumeric naming: "02c Build CAD Graph", which we will omit in this paper.
Extensive documentation across stages is available.

For developer convenience and speed of dataset generation, we split the dataset
generation into two languages, Go and Python, with Go running most of the data
transforms (this is useful when running transforms over 2m entities in graph
involving substantial geometry computation and persistence), and a number of
python workers doing CadQuery and other processes dependent on Python.

The implementation follows this structure: 

1. Ingest and preprocess CadEvolve dataset
2. Extract the AST and CadQuery into graphs the task building and verification
   can later rely on
3. Generate the tasks (in intermediate representation) from the graph
4. Render the prompts from the representation and compose the final dataset.


### 5.1 Extraction

[I think this section is to be removed]
<!--
- `02a extract CadQuery AST` parses and validates an allowlisted CadQuery subset, assigns stable operation and entity IDs, rewrites the program for recording.
- `02b execute CadQuery` runs the instrumented program once in a child process, captures runtime values, classifies geometry, emits a failure tombstone on failure.
- `02c build CAD graph` joins AST and runtime by program_id and operation_id; no partial graph is persisted.
- Pins: CadQuery/OCP versions are part of the run manifest; a version change is a new run.
- Failure model: per-program fail-fast, recorded as a row; no exception aborts the run.
-->

### 5.2 Graph assembly
[I think this section is to be removed]

<!--
- Persist entities, relations and measurements as typed tables; derive deterministic UUIDv5 graph IDs.
- Point probes: centroid plus a seeded near-surface probe; opposite labels when both survive; clear-case margin discards ambiguous probes.
- Validation: must-extract capability set; release fails if no accepted graph carries a required capability.
- Determinism: stable ordering by program_sha256 and operation order; no random IDs.
-->

### 5.3 Task generation
[I think this section is to be removed]

<!--
- `03a allocate task quotas` builds family profiles, allocates quotas against the release targets, assigns split and attempt budgets; global allocation is serial.
- `03b construct task definitions` builds definitions per shard, resolves target binding, clue predicates and the gold answer, applies uniqueness, answer-equivalence, necessity, leakage and shortcut checks.
- `03c resolve deficits` reassigns programs or expands the corpus, bounded by budget; accepted misses are recorded.
- Construction is parallel per shard; accepted definitions merge in deterministic order.
-->

### 5.4 Prompt rendering, validation and export
[I think this section is to be removed]

<!--
- `04 render prompt and choices` turns typed task definitions into prompts and multiple-choice candidates; every LLM-facing string is data in generator/config/prompts.yaml, never hardcoded.
- A template change bumps the prompt version and hash; the prompt is the user message, no system prompt is shipped.
- `05 validate and export release` runs release checks (counts, coverage, balance, leakage, answer evidence, support tables) and writes release.parquet, manifest, Dataset card, failures, support.
- No partial release: a failed row fails the release build, not the published artifact.
-->

### 5.5 Evaluation harness
[I think this section is to be removed]

<!--
- Local tool-call harness: submit_* tools per answer format, run_code for NumPy mode, parser, exact-match scorer.
- Models are evaluated as released through the same harness; no fine-tuning and no adapter is trained.
- Scorer: one implementation for evaluation; the current three-scorer split is a recorded defect and must be reconciled before the thesis number.
- Sandbox: run_code is an accidental-misuse guard, not a security boundary; state that honestly.
- Status at writing: numpy and no_tools modes exist; cadquery mode is missing; no preserved NumPy run; three scorers disagree.
-->

## 6. Evaluation

<!--
EVALUATION: only results that exist at submission time
- Report the instrument result first (validity and composition), then the base-model results across harness modes.
- Every table names its split, tier, n, model and harness mode.
- Report negative and null results; do not hide them.
- Planned-but-unrun work belongs in Future Work, not here.
- Visuals: accuracy by step count; accuracy by answer meaning; accuracy by harness mode with CI.
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

### 6.3 Discussion

<!--
- Answer the research question directly: does the instrument expose a real gap, and how large is it.
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
- Implications: benchmark design, no-kernel evaluation, graph-derived supervision.
- Limitations: public-program bias, no-kernel constraint, release size, single-family or single-snapshot risks.
- Future work: the kernel-query pivot (generate the query, score by execution); reasoning conciseness from the critical path; CADEditQA; 6–10 tiers once the release gate passes; more models and samples; a larger public release.
- No new results, no new citations, no sweeping parameter-sweep promises.
-->

## References

<!--
REFERENCES
- Harvard or APA, per the NCI Library Referencing Guide; keep the CA2 list and extend it.
- At least 15 references in the paper; aim for the ~50 read.
- Every entry resolved to a DOI or proceedings page; URLs go in footnotes.
- Include: BenchCAD, Text2CAD, CAD-Recode, cadrille, CADENA, CADBench, Text2CAD-Bench, CAD-Editor, QueryCAD, GeoGramBench, DeepCAD, CADEvolve, the program-evolution dataset, plus the RLVR/verifier and tool-calling sources in docs/prior-art.md.
- Add from the 2026-11-25 scan, with author lists taken from the arXiv metadata: DrawScore (2611.24681), RealCAD (2608.30617), CAD Bench v3 (2611.02659), CADWorld (2609.16251), EngiWorld (2609.37686), RealCADBench (2609.03773), MechReason (2609.16012), CADFather (2610.09127), CADMAGEDDON (2611.22563), VisCAD (2609.03811), ConCAD (2609.34494), PhyCAD (2611.09401), Done Is Not Correct (2611.10063), Learn the Solid (2609.11573). All are 2026 preprints unless a venue appears; label them as preprints.
- Do not cite the Zenodo tolerant-B-rep preprint in the paper's reference list until its author list is confirmed; if the argument needs it, cite it in research-gap.md only.
- Do not cite a benchmark number without checking its current split and metric.
-->
