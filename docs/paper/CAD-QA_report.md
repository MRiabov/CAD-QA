# Deep-3D-CAD-QA: A Dataset Verifying Geometry Reasoning over Complex Procedural CAD Programs

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

**Background:** LLMs are becoming notably strong in CAD reconstruction, with open, training-ready datasets focusing on reconstruction, engineering standard following and editing.

**Problem:** However, no training-ready datasets focused on deep reasoning of LLMs on complex, messy shapes exist.

**Objectives and contribution:** We present a large dataset that allows training foundational capabilities of LLMs in deep geometric reasoning, generated and validated through a CAD kernel, not requiring expensive expert validation.

**Methodology:** To aid in efficient training of LLMs on our dataset, we present a critical path that allows validated step-by-step solutions.

**Results, findings and remaining gap:** We show that frontier models are only 50–80% successful without tool assistance, showing headroom in geometrical reasoning.

**Availability:** We open-source the dataset at https://huggingface.co/MRiabov/

[to be revised]
<!--
ABSTRACT (write last, 200–250 words, no citations)
- Structured labels: Background, Problem, Objectives/contribution, Methodology, Results/findings/remaining gap, Availability.
- Keep the CA2 arc (winter/spring 2026): assistant → comprehension failure (invalid geometry, overlaps) → question-answering dataset from CadQuery programs → simple lookups to high-step questions with distractors → three harnesses → accuracy by task reasoning step, clue type, relation family and LLM harness mode → contribution. The 2026 evidence updates the middle of that arc; it does not replace it.
- Keep the CA2 breadth in the dataset sentence: relationships between boolean operations, faces, vertices and edges; volume, span or location. Do not shrink it to "numeric QA".
- The three harnesses are part of the identity: no_tools, NumPy shell, full CadQuery. Name all three even though the primary setting has no access to CadQuery.
- Problem: LLMs are proposed as CAD assistants, yet they misread procedural geometry; one wrong selector destroys the part.
- Gap: existing CAD benchmarks test reconstruction or single-pass numeric lookup. BenchCAD Code QA (2,400 questions, 200 parts, last tested 2026-05) already covers single-pass comprehension. Do not claim that no open dataset exists.
- Difference: CAD-QA is multi-hop, distractor-rich, and covers the CAD ontology (faces, edges, vertices, profiles, workplanes, regions, operations) rather than numeric lookup only.
- What was built: a task schema, a CAD graph, a deterministic generator, a released Dataset card, and a no-kernel evaluation harness.
- How it is evaluated: immutable train/validation/test split; no-kernel primary harness (NumPy compute only); kernel access as an upper bound; fine-tuning ablation.
- Findings: report only what has actually run. Current evidence is one step-9 stress test on 60 tasks (60.0% no-kernel vs 88.3% with CadQuery, deepseek-v4.1-flash), not a release-level result.
- Contribution: the multi-hop instrument, the graph-derived supervision target, the generator method, and the evaluation protocol.
- Limitation: public CADEvolve programs; no-kernel setting is a deliberate constraint, not a claim that kernels are unavailable; transfer (H3) not yet measured.
- Volume evidence (2026-11-25 scan): 199 arXiv abstracts match CAD for 2026-08-25 to 2026-11-25, against 109 in the same 93 days of 2025 (+82.6%) and 89 in 2024 (2.24×). The field is producing far faster than it is verifying; say "83% year on year", never "10×".
- Measurement evidence to cite as motivation, not as our result: DrawScore (2611.24681) shows IoU/Chamfer/F-score discount a local error as a power of its size, so a 0.9 mm bolt-hole shift leaves F-score at 100%; RealCAD (2608.30617) shows DeepCAD parameter accuracy can be earned from value priors; OpenCascade 8.0.1 validity checks accept B-reps with no realizable solid (2026-11-13 Zenodo preprint, DOI 10.5281/zenodo.24203268).
- Independent scores to quote as context, never as our baseline: CAD Bench V3 61.03 overall and 39.69 create-and-edit (2611.02659); CADWorld 17.5% vs 87.0% expert (2609.16251); EngiWorld 44.3/100 with 3.6% cross-application success (2609.37686).
- Do not put any of those numbers in the abstract as findings; they describe other instruments. Keep the abstract to our instrument, our split, our measured diagnostic.
-->

## 1. Introduction

### 1.1 Background and motivation

AI for CAD starts seeing a surge in industry in Q3 2026, with reconstruction capabilities being near-saturated on complex benchmarks [BenchCAD 1.0]. Foundational, large datasets, including recent ones in 2026 such as CADEvolve (Elistratov et al., 2026), CADENA (https://arxiv.org/abs/2608.00799), Zero-To-CAD focus on image- and Text-to-CAD reconstruction, training on which has mostly saturated the reconstruction benchmarks, however CAD editing is still consistently less than half successful [citation*S* required]. Existing datasets also measure QA answering on CAD, in particular answering about engineering standards following (engineering standard e.g. ISO) from CadQuery code [benchcad citation?], however, they are simple, rudimentary question answering, requiring only one lookup or knowledge of a particular standard and not deep geometrical reasoning. 

As such, the field is still lacking a dataset that would allow ready training on: verification of reasoning on more complex CAD reasoning beyond simple question answering pairs, as well as optimization of conciseness on reasoning in such tasks.

Our primary research question:

- How can we improve the raw capability of an LLM to comprehend the geometry resulting from CAD code?

Secondary:

- How can we increase the efficiency of geometrical reasoning of LLMs? [NOTE: I'm unsure this is a good RQ to state as I won't train a model]
[TODO. Ideas: 
efficiency - directly addressed by building a graph and allowing training on it]

<!--
- Research problem: current models can produce plausible CadQuery, but cannot reliably reason about what the program builds. Our step-9 diagnostic: 36/60 = 60.0% no-kernel vs 53/60 = 88.3% with CadQuery (deepseek-v4.1-flash); the seven kernel-assisted errors are entity-selection errors, not API errors.
- Research question (from docs/PRD.md): how can the raw capability of an LLM to comprehend CAD code be improved?
- Secondary questions: how should a dataset be constructed to improve reasoning over 3D code; does synthetic training transfer to other benchmarks; is the resulting reasoning concise?
-->

### 1.3 Objectives

Our objectives are:

- To create a dataset that allows higher correctness on deep, complex CAD reasoning tasks.
- To create a dataset that is easy to train efficient reasoning on.

<!--
- Objectives (docs/PRD.md): build the verifiable instrument; measure base models on it; fine-tune a small open model with graph-derived supervision; test transfer to an independent benchmark.
-->

### 1.4 Contributions

Our contributions are:
- A large dataset allowing training of models on question-answering pairs of deep and progressively complex CAD questions
- Critical path proof to the questions allowing easy and dense optimization of LLM trajectories on it, 
- Benchmarking SOTA models and showing where the current state of the art is still lacking.
<!--
- Keep CA2's three contributions, with one 2026 correction: dataset + open construction method over the CAD ontology; conciseness and critical-path supervision from the graph; labelled curriculum. "First open dataset" becomes "depth above BenchCAD"; the other two stand.
- Contributions: task schema and CAD graph; deterministic graph-derived generator; tiered 1–10 benchmark with a no-kernel setting; SFT recipe and evaluation protocol; negative results reported as findings.
-->

### 1.5 Limitations and assumptions

The limitations of our studies are in the transfer of our dataset to other benchmarks:

- We evaluate two LLMs only on approximately 750 trajectories each, spanning multiple levels and multiple clue types. Our results are statistically limited by budget.
- We do not train a model on the dataset, nor measure transfer of improvement to other benchmarks; primarily due to budget.
- We only train on one CAD engine. There are now numerous BREP kernels including open-source ones [brepbench], but we deem it sufficient as CadQuery is the widely adopted open-source CAD modelling application, being used in most major papers [Zero-to-CAD]. 

<!--
- Scope: executable CadQuery programs from CADEvolve; P0 is no kernel, NumPy allowed; kernel access is an upper bound (P2), not the headline.
- Limitations to preview: BenchCAD already has Code QA, so the gap is depth not task shape; transfer is P1 and unproven; the release is built from public programs, so contamination must be audited.
- Evaluation caveat worth one sentence: geometry scores are not a proxy for comprehension. DrawScore (2611.24681) shows a 0.9 mm hole shift leaves F-score at 100%; RealCAD (2608.30617) shows DeepCAD parameter accuracy can come from value priors. This is why the instrument grades exact answers against a rule-derived gold, not geometry similarity.
- Do not claim "no open dataset": BenchCAD Code QA exists. Do not claim "statistically correct" before Evaluation supports it.
-->

### 1.6 Structure of the report

We will structure our work as follows:
1. Related work will go over the recent contributions, in particular the state of the art in 3D applications and where they currently fall short, as well as foundational datasets.
2. Research methodology will go over the [.] 
3. Design specification will go over what the dataset is expected to be and the dataset validity procedures that are in place; it will also go over evaluation procedures.
4. Implementation will briefly describe the implementation structure of the dataset,
5. Evaluation will focus on evaluating the state of the art and showing deficiencies of existing models,
6. Conclusion and Future Work will show the future work.

<!--
- Outline: one sentence per later section.
-->

## 2. Related Work

LLMs in CAD have seen a surge in research and industry results in Q2 and Q3, producing 2x more literature than Q3 a year ago in the same field. In Q3, 19# papers were produced, with 45% focusing on generation, 20% on agent tool-use, ~20% focusing on application and ~9% on evaluation or foundational datasets. 




<!--
RELATED WORK: bullets only; write the prose from these
- Per reviewed paper: approach, method, results, one strength, one limitation; group minor papers by approach.
- Four streams: (1) CAD reconstruction and generation, (2) CAD comprehension benchmarks, (3) procedural CAD corpora and program evolution, (4) verifiable multi-hop reasoning and small-model fine-tuning.
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

Recent work has demonstrated major progress in CAD generation and reconstruction, partially driven by large synthetically generated datasets - both Zero-To-CAD and CADEvolve were released as million-scale datasets, where CADEvolve released a dataset of "deliberately as complex shapes as possible" which, in CADEvolve, was used to train a reconstruction model. A plurality of papers have focused on improving Text- and Image-to-CadQuery, saturating reconstruction benchmarks [CADENA, ConCAD], while editing is unsaturated; perhaps due to editing being more complex to scale data-wise.

<!--
- Text2CAD, CAD-Recode, cadrille, CADENA, CADBench, Text-to-CadQuery, CAD-Editor.
- 2026 additions to cite: CADFather (2610.09127, coordinated tool use), CADMAGEDDON (2611.22563, 27B Qwen3.8 reconstructing from meshes on one GPU, 0.999/0.993/0.933 IoU on 300-part subsets), VisCAD (2609.03811, 27B trained on ~1M executed CadQuery programs, 0.5540 vs 0.5496 for Gemini-3.1-Pro).
- Reward-side additions: ConCAD (2609.34494) adds a B-rep constraint-satisfaction rate as a dense reward (G-CSR 0.913; ablated 0.734 IoU as a reward vs 0.702 kernel-gated); PhyCAD (2611.09401) shows a flat GRPO sum lowers joint feasibility 21.76%→18.80% while validity rises to 98.4%, recovered by hierarchical grouping. Both are evidence that the field is fixing its objective, not its comprehension.
- What they do well: generate or reconstruct a program/mesh from text, images or point clouds; provide large SFT corpora.
- Limitation: they evaluate the produced shape or program, not an LLM model's understanding of an existing program.
- The metric critique belongs here as the bridge to our construct: DrawScore (2611.24681) proves IoU/Chamfer/F-score weight a local error as s^(k+q), so a 0.9 mm bolt-hole shift leaves F-score at 100%; RealCAD (2608.30617) shows DeepCAD parameter accuracy can be earned from value priors (+7.49/+14.73 pp without an mCD gain, with a higher invalid ratio). A high reconstruction score therefore says little about entity-level understanding.
- Do not conflate reconstruction accuracy with comprehension accuracy: different construct, different metric.
- If a reviewer challenges the word "valid", point to brep-bench (brepbench.org, first public 29 Oct 2026): 300+ cases across 15+ kernels, grading the exported STEP solid by volume, area, centroid and inertia at 1e-6, with a refusal ranked above a wrong answer. It is a community benchmark, not peer-reviewed, and it grades kernels rather than LLM models; it does not settle the metric question for generated B-reps.
- Naming caution: several 2026 papers reuse "CAD" in the title with different constructs (generation, reconstruction, editing, agentic authoring). State which construct each cited work measures.
-->

### 2.2 Geometry comprehension benchmark

Closest spiritually to our dataset are procedurally generated 2D and 3D geometry reasoning benchmarks such as SiT-Bench (Guo et al., 2026) and Real-3DQA (Ma et al., 2026), which explicitly evaluate models' 3D comprehension abilities from text alone, without visuals. They are similar in that they evaluate models on procedurally generated geometry, but they do not evaluate or focus on CAD-specific geometry such as selectors, vertices, and boolean operations — only on text descriptions of scenes.

### 2.3 CAD comprehension benchmarks

BenchCAD 1.0 has evaluated CAD generation across 4 benchmarks - Vision2Code, Code Edit, Vision QA, Code QA; so Code QA was already studied, however the dataset focuses on benchmarking simple question answering such as compliance to a standard (e.g. whether a thread size is compliant), whereas our dataset focuses on verification of correct geometrical reasoning, at scale and varying depth. BenchCAD 2.0/2.1 are reconstruction only (assemblies, PCB wiring) and add no comprehension task. QueryCAD is an earlier similar work evaluating capabilities of LLMs on answering factual questions based on CAD models, but without CadQuery; again, without depth.

MechReason is a benchmark evaluating multi-view and multi-hop reasoning of LLMs on mechanical engineering publications and papers; however it synthesizes QA pairs from papers and does not evaluate models on CAD programs, nor is it verifiable via a kernel.


<!--
- BenchCAD 1.0: 17,900 execution-verified CadQuery programs; Vision2Code, Code Edit, Vision QA, Code QA.
- Code QA: CadQuery program + numeric question -> number; 2,400 questions over 200 parts; symmetric-ratio metric; 0.80–0.84 total, Spatial Reasoning axis 0.537–0.731 against a 0.42 blind baseline. All Code QA rows are `tested: 2026-05`; quote as "as last measured in May 2026", not as a current gap.
- BenchCAD 2.1 (2026-10-19) is the reconstruction/agentic line: six tasks, 100 Core cases, 60 rounds / 500k tokens, scores not comparable with 2.0. It has no Code QA, so it does not refresh the comprehension numbers. Do not read newer Vision2Code tool scores as comprehension movement.
- BenchCAD 2.0/2.1 are reconstruction only (assemblies, PCB wiring) and add no comprehension task.
- CA2's BenchCAD row said "generation, edit, numeric QA, 1–2 hops". Keep the row but split it: 1.0 carries the single-fact numeric QA, 2.x carries reconstruction. Do not let the newer 2.x scores read as comprehension movement, and do not drop the row — it is the benchmark that forced the repositioning.
- Keep the catalogue assessment: every Code QA item is single-fact extraction with light arithmetic; the hardest are one-step counterfactuals; none requires resolving an intermediate entity before the final step, chaining two dependent resolutions, or choosing among distractors. This is the sentence the whole positioning rests on, and it is BenchCAD's own catalogue, not our opinion.
- QueryCAD and GeoGramBench: comprehension/program-to-geometry; their published gaps are stale and must be re-run before quoting.
- CADBench, Text2CAD-Bench, CAD-Editor: generation/edit and defect metrics (invalidity rate, exec%), useful as end/defect corroboration.
- New in the Aug–Nov 2026 window, cite as the independent-measurement layer: CAD Bench V3 (2611.02659; 100 FreeCAD tasks; best 61.03 overall, 50.87 create-from-text, 39.69 create-and-edit, 84.66 image-to-CAD), CADWorld (2609.16251; 200 GUI tasks, 17.5% vs 87.0% expert), EngiWorld (2609.37686; 1,301 tasks across 26 platforms, 44.3/100, 3.6% cross-application), RealCADBench (2609.03773; 1,770 industrial intents, executability 0.565–0.812, surface IoU 0.112–0.217).
- The asymmetry to state once: rendered-artifact and short-text benchmarks approach ceiling; persistent editable state, constraints and multi-tool work do not. Saturation is a property of the artifact scored, not of the field. Do not aggregate the numbers — different splits and metrics.
- MechReason (2609.16012) is the nearest multi-hop neighbour: multi-image mechanical reasoning, best 62.89%. Its input is images, not a program, so it corroborates the difficulty without occupying our task.
- CivilCADBench (2611.28853) and LED-BENCH are drawing comprehension: >90% on clean single-sheet reading, 52.65% on large-format cross-region questions, ~60% layer assignment. Cite only if the comparison is drawings vs code; do not use as a comprehension baseline.
- Limitation to state: these are single-pass lookups, visual questions, full authoring episodes, or GUI work; no multi-step clue chains, no distractor-rich selection over the CAD graph, no reasoning-step curriculum, no non-numeric answer contract.
- Do not say "CAD QA does not exist": the window scan finds one paper, not zero. Say "almost none, and none multi-step".
-->

### 2.4 QA datasets and verifiable reasoning 

Verifiable reasoning and evaluation by tool calling have become the de-facto standard for factual question-answering training, with the advantage of:

- Allowing stable training - no noisy LLM-as-a-judge is necessary, with verifiable reasoning being ubiquitous in physics, 3D and geometry datasets

<!--
- RLVR and verifier work: the verifier is the objective, so a noisy or divergent scorer is optimised; query-verifier audits report self-agreement as low as 53.8% and two configurations disagreeing on 49.9% of pairs.
- 2026 corroboration from CAD itself: PhyCAD (2611.09401) shows a flat multi-objective GRPO sum lets one criterion compensate for another — adding physics lowers joint feasibility 21.76%→18.80% while raising validity to 98.4% — and hierarchical advantage grouping recovers 39.5–58.1%. The general lesson is that heterogeneous criteria must not be summed into one scalar; the CAD-specific lesson is that a single "success rate" over geometric and physical checks hides the trade.
- Implication: one scorer, exact match, no LLM judge; gold answers computed offline. State the contrast with DrawScore (2611.24681), which needs no 3D ground truth because it scores projections; our gold is cheaper still and exact.
- Small-model evidence (docs/prior-art.md): base rank predicts little; the recipe and data predict most; tuned small models reach 90–98% on narrow tool-calling tasks; LFM2.5-350M beats a ~120B teacher in one study (61.4%→98.0% vs 97.03%). Cite as the reason a 1–3B model is a credible training target, not as evidence it will reason about geometry.
- Tool-calling and format compliance are separate from reasoning; an ablation must separate them. H1 is the format control; H2 is the reasoning claim.
- Multi-hop QA literature: the depth/gap framing, not a claim that CAD is just another multi-hop text task. The 2026 evidence for why it is not: BenchCAD's spatial axis (0.537–0.731) is the only public comprehension number that is unsaturated, and it is still single-fact.
- CADTestBench (Mallis et al., 2026) stays the closest test-verified neighbour from CA2: it grades generated CAD programs against executable CADTests rather than visual similarity, requires at most 2–3 steps, and does not support offline evaluation of a given program. Keep that comparison explicit; it is the one CA2 already made.
- Verifiability is the design constraint, not a convenience: a benchmark that needs a kernel, a GUI or an LLM judge to score cannot be a training target at our compute. This is the paragraph that justifies the no-kernel setting without claiming kernels are unavailable.
-->

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

<!--
METHODOLOGY: the scientific procedure, not the software
-->

Much like in software engineering, being proficient in one area, such as SQL queries, doesn't mean an agent is proficient in machine learning; nor does being proficient in Python make an agent proficient in Rust. Similarly, CAD requires understanding of numerous operations and relations, and underexposure to some will lead to knowledge gaps as highlighted by CADEvolve (an early 2026 paper) (Elistratov, 2026), where agents were not proficient in everything but modelling with boxes. As such, we construct a wide variety of tasks as well as compositions and report success rates on them separately.

### 3.1 Research design, variables and hypotheses

We construct the dataset across multiple axes:

- Tasks - what tasks in particular do models fail on?
- Depth - when task geometrical complexity is composed, what is the reasoning depth a model can solve reliably?
- Harnesses - given different tools available to the agent (no tools, NumPy, CadQuery), how does being able to verify, and with which tools, increase success rate?
- Models - we will evaluate a number of models to ensure fairness of evaluation. 

Our hypotheses are:
H1. There are limits beyond which models would show reasoning gaps; different per harness.


As other datasets already cover simple question-answering pairs (such as lookup radius of a hole), we deliberately abstain from questions not requiring deep geometrical reasoning, with at least 95% of our dataset containing geometry-focused questions.


<!--
- Design: instrument-building plus a controlled training experiment (design science + pre-registered analysis).
- Unit of analysis: one task = program + target + clues + one answer. One CAD model = one CadQuery program; one family may contain many programs.
- Hypotheses (docs/PRD.md): H2 reasoning supervision beats answer-only (P0 core); H3 transfer to BenchCAD qa_code (P1); H4 CAD-QA pass rate predicts transfer (P1 mechanism); H1 tool-format SFT raises tool-valid rate (P1 control).
- One instrument, several studies: benchmark validity, baseline measurement, fine-tuning ablation, external transfer.
- State H1–H4 with role and priority, and the decision each outcome forces.
- If H1 holds and H2 fails, the finding is "format compliance, not reasoning"; report it.
- If H3 is null, the dataset-usefulness claim weakens to an internal-split result; report it.
- Define "statistically supported": pooled 95% CI excludes zero and the same sign in at least 2 of 3 seeds.
-->

### 3.2 Dataset construction procedure

We use the CADEvolve dataset as it is the largest and most diverse dataset among the publicly available corpora. We normalize programs using AST and CadQuery post-processing to extract a graph of entities and dependencies between them, such as edges, vertices, faces, boolean operations and derive relations between them, such as distances, angles between them. The graph, with later post-processing, allows us to deterministically and verifiably generate questions such as in [figure 1]. We will expand on dataset construction in the design specification section.





<!--
- Instrument construction: CADEvolve -> normalized programs -> CAD graph -> task definitions -> rendered prompts -> validated release.
- Gold answers are computed by execution or exact derivation; no LLM writes or judges an answer.
- Source selection: CADEvolve metadata, family-safe selection, fetch, normalize (stages 01a–01e).
- Extraction: AST records what the program says; execution records what the shape is; neither side fills the other (stage 02).
- Task construction: quota plan, construct definitions, resolve deficits by replanning or expanding data (stage 03).
- Rendering and export: rule-rendered prompts and choices, then release validation (stages 04–05).
- Determinism: same inputs, versions and shard count produce byte-identical parts and the same run identity.
- Failure model: rejected programs and tasks become rows with reasons; counts must add up.
-->

### 3.3 Evaluation protocol

We evaluated models on completion of the tasks under varying tasks, depths and harnesses, reporting:

- Cost in tokens and quantity of tool calls spent per evaluation,
- Correctness

Over the combination of:
- Tasks (clues),
- Depth (number of narrowing steps required to derive an answer)
- Models
- Harnesses

### 3.4 Harnesses

To evaluate different CAD reasoning skills and the internal reasoning of models:

- without access to tools (the notable advantage of this is that stronger models can estimate correct solutions *without* doing a tool call),
- NumPy-only harness - the importance of this harness is twofold: being able to estimate complex CAD without a harness, such as in cases of "on-paper" feasibility analysis, as well as not being limited to CadQuery alone - for example not every CAD modelling assistant has shell access to a CAD kernel, but they may have access to a shell.
- CadQuery-enabled harness - CadQuery is the most ubiquitous CAD library, being popular in the largest recent CAD datasets - Zero-To-CAD, CADEvolve and others. 


<!--
- Evaluation arms: Base, Answer-only, CAD-QA reasoning, Format-only, General-only counter-arm; hold base, recipe, prompt set and loss-bearing token budget fixed.
- Primary endpoint: exact structured-answer accuracy on the immutable held-out test at a pre-registered tier.
- Harness modes: no_tools (P2 upper bound), numpy (P0 primary, no CadQuery), cadquery (P2 realistic upper bound; currently missing).
- Do not present the 50–70% planning estimate as a target; the base rate is measured first and the threshold set afterwards.
- Immutable split: approximately 70% SFT / 15% RL / 15% eval; eval is split into validation and test; the test portion is the thesis number.
- Group safety: no CADEvolve program family appears in more than one part; no external benchmark family appears in any training arm.
- Harness: model -> chat template -> tool declarations -> generation loop -> tool execution -> parser -> scorer.
- Answer contract: one submit tool per answer format; exact structured match; invalid output is a failure, not an exclusion.
- Metrics: accuracy; invalid-output rate; missing-response rate; accuracy by step, target category, clue type, answer meaning and harness mode; reasoning length; pass@1 with a CI; chance-corrected rate for bounded answer spaces.
- Baselines: cost-effective external models through the same harness; every number names its slice.
- Freshness: no external gap is quoted without a current re-run; record the benchmark's `tested` date next to every number.
-->

### 3.5 Statistical analysis

<!--
- Binary outcomes: McNemar exact two-sided on discordant rows, plus paired bootstrap (10,000 resamples) 95% CI.
- Multiplicity: Holm within the three H2 comparisons and separately within the three H3 comparisons.
- Chance correction: report raw and corrected rates, never only corrected; p_chance = 1/K for labels, 1/2 for boolean, 0 otherwise.
- Seeds: three per confirmatory training arm; report each seed and the mean; do not hide a sign flip.
- Power: compute MDE from the frozen split before the final test; declare anything below MDE exploratory.
- Freeze: endpoint, arms, revision hashes, tier, n, seeds, MDE, alpha and stopping rule are fixed before the final test; the test runs once.
- Do not select the best checkpoint or the best tier after seeing results.
-->

### 3.6 Ethics, licensing and reproducibility

<!--
- Public programs and public data; no human subjects; check each corpus licence and record it.
- Contamination: dedup CAD-QA programs against every transfer benchmark; exclude their families from every training arm.
- Reproducibility: tagged release, Dataset card, run manifest with versions and hashes, one command to regenerate.
- Logging: every LLM call, internal reasoning, visible output and tool call is recorded and reconstructable.
- Compute: small open models on a single GPU; report cost and hardware.
-->

## 4. Design Specification

In this section, we will describe how the dataset and evaluation procedures were built, focusing on the dataset.
<!--
DESIGN: what the instrument is, before how it was coded
- Keep requirements-level rules here; keep code paths in Implementation.
- Vocabulary must match docs/glossary.md and docs/dataset/requirements/terminology.md.
-->

### 4.1 Task model

A task is a single question-answering pair, defined by input geometry and the clues supplied to the model. Given a 3D model as a whole which may have 20,000 entities and relations, the model needs to narrow down to an entity or operation, for example finding the correct face among hundreds of entities.

The model narrows down by clues. For example, in a simple box-with-a-hole program [figure 1], we derive all entities and relations between them, and select clues as follows:

- Picked result entity: circular edge where the hole meets the top face,
- Picked property of the edge: length.

- Clue 1: the target edge is an edge of the face touching the top of the axis-aligned bounding box.
- Clue 2: the target edge is an edge of the cylindrical face.

The model thus needs to find all 15 edges of the final solid state, keep the five that are on the top face, and filter them into one that would be cylindrical. By design and verifiably, each clue in the dataset is necessary, so the LLM can never reach the answer while omitting any of the clues.

In total, we support the following types:

- Target categories: operation, feature, solid state, face, edge, vertex, CadQuery profile, CadQuery workplane, region, scalar value.
- Clue types: property, relation, comparison, provenance, aggregation.
- Answer formats: multiple choice, number, integer, boolean, 3D coordinate, bounding box; structured object.


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

### 4.5 Validity rules and quality gates

In order to validate the quality of our dataset, we enforce after-construction validation:

1. Every answer is correct,
2. There is exactly one answer, 
3. In multiple-choice questions, there are at least 5 answer options, with a mean of 7, so as to ensure fairness of the answer,
4. At least 95% of our dataset has geometrical questions as noted in [3.1](<CAD-QA_report#31-research-design-variables-and-hypotheses>)
5. There is no answer leakage in the question.
6. Human review: while tasks are sampled deterministically, we review a sample of questions that is as diverse as possible.

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
- Add from the 2026-11-25 scan, with author lists taken from the arXiv metadata: DrawScore (2611.24681), RealCAD (2608.30617), CAD Bench v3 (2611.02659), CADWorld (2609.16251), EngiWorld (2609.37686), RealCADBench (2609.03773), MechReason (2609.16012), CADFather (2610.09127), CADMAGEDDON (2611.22563), VisCAD (2609.03811), ConCAD (2609.34494), PhyCAD (2611.09401), Done Is Not Correct (2611.10063), Learn the Solid (2609.11573). All are 2026 preprints unless a venue appears; label them as preprints.
- Do not cite the Zenodo tolerant-B-rep preprint in the paper's reference list until its author list is confirmed; if the argument needs it, cite it in research-gap.md only.
- Do not cite a benchmark number without checking its current split and metric.
-->
