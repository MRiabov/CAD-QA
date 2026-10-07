# CAD-QA: A Benchmark Verifying Geometry Reasoning over Complex Procedural CAD Programs

**Maksym Riabov · 25194372 · Research in Computing · National College of Ireland**

## Abstract

Large language models (LLMs) are increasingly proposed and demanded as CAD
design assistants, yet their comprehension of procedural geometry remains
too often incorrect: they generate functioning and correct-looking
code that fails with invalid geometry such as overlaps between
parts or simply incorrect geometry. We construct a
question-answering dataset from CadQuery programs, where each question requires
comprehending a complex CAD model --- finding relationships between boolean
operations, faces, vertices and edges, computing their volume, span or
location. Questions range from simple lookups to challenging high reasoning hop
questions with rich distractors, requiring chains of complex and correct reasoning. 
We evaluate open-source LLMs in three harnesses --- without tools, with a NumPy shell, and with full CadQuery access --- measuring accuracy by hop count, task type, and tool setting.
Expected contribution: a benchmark exposing
the multi-hop geometry reasoning gap in current Large Language Models

**Keywords:** multi-hop reasoning, procedural CAD, CadQuery, verifiable evaluation, LLM benchmark

## 1. Introduction

LLMs are increasingly proposed and demanded as CAD designers and assistants
[zhang2026cadllmsurvey, khan2024text2cad]. Recent work targeted text-, image-
and mesh-to-CAD generation, and engineering documentation question answering
datasets, but LLMs still struggle with generation of useful, complex CAD models,
in particular with problems such as overlapping parts, impossible geometry (on top
of simple code correctness problems) [khan2024text2cad, doris2026cadbench] as
well as identifying the correct edge or face to select to build geometry upon; a
mistake in one selector is destructive to the whole part.

Furthermore, LLMs are too often struggling with generating and coding of CAD models with
anything beyond box geometry in part due to lack of datasets that would have other geometry primitives [elistratov2026cadevolve]; and even then, computing intersections between them requires
what appears to be an extraordinary amount of reasoning tokens compared to pure software/web app tasks. This is despite extensive mathematics
benchmarks for general 3D understanding. As such, the LLM approach is
presently infeasible even for simpler 3D modeling tasks.

To our knowledge, there isn't an open dataset which could reliably measure and allow improvement on
mathematical and spatial reasoning of models in domain of deriving and locating exact
parts, boolean operations (shapes), positions of objects, as well as truthful CAD code question answering beyond simple question.

The main research question is:
- How to improve the raw capabilities of LLMs on comprehending of CAD code?

The secondary research questions are:
- How to construct such a dataset that would improve models' reasoning on 3d code?
- Will scaling a synthetic training approach on such questions improve the actual reasoning on other datasets?
- Will reasoning be concise?

The main expected contributions are:

- A synthetic dataset and an open-source method of constructing the dataset to reliably drive mathematical reasoning on CAD models and CAD-specific ontology, such as vertices, faces, selectors
- The dataset can be reused for training of models for conciseness of reasoning on the tasks- as graphs are provided; one can train the LLM to follow the shortest/critical path necessary to achieve the result; aiding in evaluation of model on achieving correct intermediary steps faster.
- A dataset of progressively challenging and labeled tasks for 3D code & geometry reasoning aiding in curriculum learning.

The remainder of the document is structured as Literature review reviewing most relevant SOTA of the field, and our methodology and evaluation setting is explained in Section 3.

## 2. Literature Review

Presently, the relevant literature in the field of LLM and CAD modeling is split into three themes: reconstruction, geometry comprehension, general multi-hop reasoning benchmarks.

### 2.1 LLMs for CAD: Text-, Image- and Mesh reconstruction

The most prominent line of work in our field are Text2CAD, and Image2CAD, and Mesh2Cad tuned
reconstruction LLM models [rukhovich2025cadrecode]. This is useful for the field of science as it
provides a means of generating substantial SFT-training data. Works such as "Text2CAD" [khan2024text2cad]
generate CAD designs from text prompts; CADBench [doris2026cadbench] is a benchmark advancing
generation of CAD models; BenchCAD [zhang2026benchcad] is a fresh benchmark asking to generate and
edit CAD programs. `cadrille` [kolodiazhnyi2026cadrille], CADEvolve [elistratov2026cadevolve], and CADENA [kabisov2026cadena] benchmarks test reconstruction of CadQuery models from parts. However, none are asking to e.g.
find a relationship between the two geometrical primitives which (by our
preliminary tests) leads to the model emitting many more reasoning tokens than expected. 

They build on datasets such as CADEvolve, DeepCAD [elistratov2026cadevolve, wu2021deepcad] which generate
geometry procedurally or via a LLM, which we build on too. 

### 2.2 Benchmarks for Geometry Comprehension

DesignQA [doris2025designqa] is a dataset evaluating LLMs on engineering documentation e.g. PDFs to check whether models comply with engineering rules and standards; it is similar
in spirit in that it measures comprehension of parts, although it does not demand
multi-hop reasoning from CAD itself. Furthermore, the benchmark is about visual
reasoning, while our benchmark comprehends code only (visual is deferred to
future work).
SiT-Bench [guo2026sitbench] and Real-3DQA [ma2026real3dqa] explicitly evaluate models' 3D comprehension abilities from text alone, without visuals. They are similar, but they do not evaluate or focus on CAD-specific geometry such as selectors, vertices, and boolean operations — only on text descriptions of scenes; nor are they working with code.

### 2.3 Verifiable Reasoning and Multi-Hop Benchmarks

Numerous verifiable reasoning/QA LLM benchmarks and datasets are present in
fields such as math, code, browsing [wei2025browsecomp, li2025websailor], but are absent from the yet-nascent field of CAD reasoning.

In the past, such synthetic benchmarks have allowed significant improvements and
served as a foundation for future work [wei2022cot]. With CAD geometrical reasoning being one
of the core requirements of correct modeling, this is arguably a critical
feature to address.

Remarkably, benchmarks in other fields aid curriculum learning by progressively labeling from simple to complex, which other works in the field of CAD modeling do not address the way
that we do.

CADTestBench [mallis2026cadtestbench] can be notably close to ours — it verifies generated
CAD models against executable tests (CADTests), rather than grading them by visual similarity. Our dataset is, however, generated to
answer more complex questions and to support offline evaluation of prompts. It
is also a relatively simple benchmark, requiring at most 2-3 hops of reasoning,
whereas we propose up to ten.

### 2.4 Research Niche

As such, we survey the field and find that existing benchmarks evaluate models' reconstruction abilities, simple comprehension or question answering, but rarely dig deeper on model mathematics capabilities or deriving complex relationships between CAD parts in code. Nor they evaluate - or provide means to measure the shortest required reasoning for solving the problem. The problems are also relatively "clean" - one-step tasks that don't require discerning real-world noise or larger problems. These are three problems that we aim to improve on.

## 3. Research Methods & Specifications

### 3.1 Research Method

We construct a graph from a CAD program in three passes: we parse the program
into an Abstract Syntax Tree (AST) to recover operations and dataflow, and CadQuery code manipulations, executing it to measure geometry. Below is a representative
example; the task is to compute the Z difference between the topmost vertex of
the final part and the topmost vertex of the cylinder.

Code sample:

```py
import cadquery as cq
wp1 = cq.Workplane("XY")
wp2 = wp1.circle(2)           # cylinder circle
wp3 = wp2.extrude(5)          # cylinder extrusion
wp4 = cq.Workplane(           # define a point to build from
    cq.Plane(origin=cq.Vector(0, 0, 10))
)
wp5 = wp4.rect(4, 3)          # make a rectangle
wp6 = wp5.extrude(2)          # extrude a box
result = wp3.union(wp6)       # combined solid
```

From this we derive a graph such as:

```text
wp2 -> wp3 ... wp3 -> result
wp4 -> wp5 -> wp6 ... wp6 -> result
```

The question is:

> Given the CadQuery script below, what is the Z difference between the topmost
> vertex of the final part and the topmost vertex of the cylinder? Answer with
> exactly one finite number.

Derivation:

```text
z(top_vertex(result)) - z(top_vertex(wp3)) == 12 - 5 == 7
As such the answer has to be: 7
```

Notably, unlike many other CAD benchmarks which use realtime execution, our benchmark is meant to be generated and trained on _offline_, as we can precompute labels, positions, volumes and other
numerics ahead of time. This simplifies execution and verification thanks to the tabular data model (and no need for setup of e.g. docker containers.)

We distinguish the following answer types:

- **Entity references** — a source code variable name or unique entity id (`wp3`,
  `feature:wp3`, `path:wp2:point:6`, `selector:sel_all_faces_all`) for
  "which feature/face/edge/path-point …" questions.
- **Coordinates** — a `(x, y, z)` tuple for vertex position questions.
- **Numbers** — one finite value (graded to a 4-significant-figure tolerance):
  volumes, deltas, distances, vertex-position differences (such as `7`
  in the example above).
- **Integers** — exact non-negative counts: operations, faces, edges, vertices.
- **Booleans** — `true`/`false` for correctness/validity and point-membership answers (is the point in a volume/on a face?).
- **Enums and candidate choices** — one token from a fixed vocabulary or the
  presented candidates: coordinate frames (`XY`, `YZ`, `XZ`, …), point
  membership (`inside`, `outside`, `on_boundary`, `ambiguous`), or labels `A`, `B`, … (including selector expressions) when a target is not readily nameable.
- **Structured JSON** — axis-aligned bounding boxes (`{"min": […], "max": […]}`)
  and workplane-state snapshots.

We extract this ontology:

- Nodes: sources, features, operations, parameters, workplanes, sketches, profiles, solids, faces, edges, vertices, axes, directions, points, centroids, centerlines, paths, selectors, measurements, material/void regions.
- Relations:
  - Temporal/dataflow: `before`, `after`, `input_to`, `combines`.
  - Parent/child node relationship: `created_by`, `modified_by`, `deleted_by`, `adds_material_to`, `removes_material_from`.
  - Construction: `uses_profile`, `used_by`, `parameter_of`, `selected_by`, `located_on`, `bounded_by`.
  - Measurement: `has_measurement`, `has_centroid`, `has_coordinate`, `has_normal`.
  - Geometry: `distance_to`, `nearest_tangent_to`, `parallel_to`, `not_parallel_to`, `perpendicular_to`, `orthogonal_to`, `coaxial_with`, `adjacent_to`, `opposite_to`, `contained_in`, `intersects`.
- Measurement scopes (prevent category errors):
  - `profile_intrinsic` — area, perimeter, centroid, local bounding box, edge/vertex counts.
  - `feature_application_effect` — signed volume delta, topology delta, circular-edge delta, bounding-box delta.
  - `entity_geometry`, `snapshot_state`, `relation_metric`.

When multiple objects are resolved (e.g., 8 vertices at the same Z height (a flat face parallel to the XY plane)), we further add classifiers like "select the 2nd highest on Y and lowest on X axes" to make the object unique (and further challenging to reason about).

The goal is to create an exhaustive ontology extraction from which a set of truly complex reasoning questions can be derived.

We classify complexity by the number of reasoning hops:

- 0 hops: direct code source or mathematical lookup ("what's the length of `box1`?": 10).
- 1 hop: resolve one entity and read or calculate one metric ("A sphere has a center rightmost to some box with parameters (1,2,3). What is the label of the sphere operation?": `sphere1`)
- 2 hops: traverse one relation and read or compare a metric. (as above, but with added reasoning hops)
- 3~10 hops: BrowseComp [wei2025browsecomp]-style rows where obfuscated, distractor-rich questions and code require a successful answer to identify and calculate a number of variables.

### 3.2 Measuring complexity

Constrained by token costs, we avoid using frontier models, and instead benchmark our dataset on cost-effective (10-100x cheaper) models such as `deepseek-v4-flash`, `xiaomi-mimo-v2.5`, `NVidia NemoTron` super and other models for evaluation. We target at most 30% pass rate by these models; with task families being equally distributed in solve rates. 

### 3.3 Improving models and proving learning

We will fine-tune LLM models using SFT & RL frameworks; in particular similar to how CADEvolve trained the models for better reconstruction, we will train models on more successful CAD mathematics using first SFT and then RL [deepseek2025r1], first using rejection sampling [shao2024deepseekmath], as well as in-place reasoning trace editing for conciseness; later we will post-train the model via frameworks like TRL or Unsloth on achieving better results on the task. We will show a graph that with training, the model's solve rate improves. 

After proving that the environment works and is correct through the API, we will post-train a small model following CADEvolve whose authors have post-trained only a small — a 2 billion parameter - model to
do CAD reconstruction. E.g. a model like Gemma4-E2B or Qwen3.5-2B will be used
owing to us attempting to save on compute expenses. If base models of this size
can solve these tasks with 10% success rates, this would be a good baseline. Our goal is to
improve their pass rates from 10% to 50-70%. RL is an expensive process, and as
such, and in our position, it is infeasible to train larger
models.

It could be that world modeling as done in InCoder-32B/InCoder-32B-Thinking
[yang2026incoder] will be used instead of SFT pipelines as it
has a higher potential to teach the model more correct answers.

### 3.4 Model harness and modes

To evaluate baseline and then improve on capability of models - at triple of the compute cost - we propose to use three harnesses for the model:

- No tools (reasoning only, where the model has to compute mathematics internally),
- A Python shell with NumPy (where the model has NumPy as a means to calculate the 3D model),
- A Python shell with CadQuery which will allow arbitrary CAD operations
to be executed, and the model is expected to use CadQuery to answer its question;
a single successful tool call will suffice - provided the model can get it right. 

The advantages of the three environments are as follows:

- To generalize the reasoning to three environments: the no tools mode requires more thinking and following through the objective and own noise to solve the problem correctly.
- NumPy environment requires understanding of 3D environment and modeling its geometry successfully without access to CAD; which is useful for generalizing to closed CAD environments such as SolidWorks or Autodesk Inventor, more commonly used in industry.
- CadQuery environment allows the model to answer in one shot by only constructing a correct CAD operation. The research question is again, conciseness, but also measuring the model ability to produce correct CAD code and reasoning on achieving it. 

We will use Harbor coding environments with TerminalBench-equivalent environments (with access to only a Linux shell and file writing; the answers are submitted as files).

### 3.5 Ethical Considerations of the Research

The dataset and evaluation are exclusively synthetic and postprocessed from public secondary data — no human subjects, personal data, or human evaluation is involved; the advantage of the dataset is that it may enable models to reason faster on particular CAD data.
No risks are expected.

### 3.6 Project Plan

1. Dataset construction (2 weeks active + 2 weeks of debugging ad hoc)
2. Preparation of SFT and RL environments & setting training infrastructure — 3-4 days
3. Training and monitoring of progress.
4. Construction of evaluation environments (1-2 days — set up a Harbor environment)
5. Presentation of results (1-3 days)

![Project Plan for Research Work](CA2Img-GanttChart-mermaid.png)

## References

See `CA2References.bib` (bibliography compiled with BibTeX/`plainnat`). CORE rankings are stated where available; otherwise the citation count is quoted (Google Scholar where accessible, otherwise Semantic Scholar / Crossref / OpenAlex, which undercount Google Scholar). Counts as of August 2026.

- zhang2026cadllmsurvey — Systematic survey of LLMs for CAD (ACM Computing Surveys, 2026; no CORE rank, journal rankings discontinued 2022; ~4 citations, Crossref)
- khan2024text2cad — Text2CAD (NeurIPS 2024, CORE A*; ~116 citations, Semantic Scholar)
- doris2026cadbench — CADBench (arXiv preprint, 2026; no CORE rank; new, ~0 citations)
- doris2025designqa — DesignQA (ASME JCISE, 2025; no CORE rank; ~34 citations, Crossref)
- guo2026sitbench — SiT-Bench: Can LLMs See Without Pixels? Benchmarking Spatial Intelligence from Textual Descriptions (arXiv preprint, 2026; no CORE rank; 3 citations, Google Scholar)
- ma2026real3dqa — Real-3DQA: Do 3D Large Language Models Really Understand 3D Spatial Relationships? (ICLR 2026; arXiv preprint, 2026; not in CORE database; 6 citations, Google Scholar)
- zhang2026benchcad — BenchCAD (arXiv preprint, 2026; no CORE rank; new, ~0 citations)
- wei2025browsecomp — BrowseComp (arXiv preprint, 2025; no CORE rank; 530 citations, Google Scholar)
- deepseek2025r1 — DeepSeek-R1 (Nature, 2025; no CORE rank; ~918 citations, Crossref)
- shao2024deepseekmath — DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models (arXiv preprint, 2024; no CORE rank; 7557 citations, Google Scholar)
- wu2021deepcad — DeepCAD (ICCV 2021, CORE A*; ~362 citations, Semantic Scholar)
- elistratov2026cadevolve — CADEvolve (arXiv preprint, 2026; no CORE rank; 3 citations, Google Scholar)
- kolodiazhnyi2026cadrille — cadrille: Multi-modal CAD Reconstruction with Reinforcement Learning (ICLR 2026, Oral; arXiv preprint, 2025; not in CORE database; ~1 citation, OpenAlex)
- rukhovich2025cadrecode — CAD-Recode (ICCV 2025, CORE A*; ~66 citations, Semantic Scholar)
- kabisov2026cadena — CADENA: Stepwise CAD Reverse Engineering (arXiv preprint, 2026; no CORE rank; new, ~0 citations)
- wei2022cot — Chain-of-thought prompting (NeurIPS 2022, CORE A*)
- li2025websailor — WebSailor (arXiv preprint, 2025; no CORE rank; 43 citations, Google Scholar)
- yang2026incoder — InCoder-32B-Thinking: Industrial Code World Model for Thinking (arXiv preprint, 2026; no CORE rank; 1 citation, Google Scholar)
- mallis2026cadtestbench — CADTestBench (arXiv preprint, 2026; no CORE rank; 1 citation, Google Scholar)
