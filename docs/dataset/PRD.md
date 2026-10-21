# PRD — CAD-QA dataset generator

**Status:** draft for owner review, 2026-10-21.

**Authority.** This PRD defines the replacement dataset generator. It replaces
all previous dataset-generation specifications. The previous pipeline docs,
answer-format record, decisions, and issue register are archived at
`docs/_archive/dataset-pre-rebuild-2026-10-21/` and are historical input only.
The project PRD (`docs/PRD.md`) remains authoritative for the research
questions, hypotheses, and evaluation contract. This PRD only defines the
instrument those goals need.

**Scope of this document.** This is a product requirements document, not a
technical specification. It defines what the generator is for, what a task is,
what tasks the dataset must contain, and what properties the result must have.
Architecture, data schema, language boundaries, algorithms, and migration
mechanics are deliberately deferred. The technical specification follows after
this PRD is agreed.

---

## 1. Purpose

Build a verifiable, deterministic dataset of questions about CadQuery programs,
suitable for training and evaluating a small LLM model that has no access to a
CAD kernel.

The dataset is the instrument for the project's research questions. It is not a
collection of prompts. Every question must be backed by a reproducible
computation over the program and its geometry, and the answer must be uniquely
determined by that computation.

The generator is successful when:

1. an immutable dataset release exists that an LLM model can be trained on and evaluated
   against;
2. every answer can be recomputed from the program and recorded facts without
   an LLM in the loop;
3. the release contains the task shapes, answer formats, and reasoning depths
   the project claims;
4. a reviewer can reconstruct any dataset entry from tracked manifests and
   hashes;
5. the generation loop is fast enough to iterate on a laptop.

---

## 2. Why the generator is being rebuilt

The previous generator produced a usable internal release but did not match its
own specification. The rebuild is not a refactor. The following properties are
non-negotiable in the replacement:

- tasks are compositions of a small set of typed operations, not hard-coded
  per-family code paths;
- all intended answer formats are first-class, not three formats plus
  aspirational branches;
- reasoning depth is computed from the actual selection procedure, not declared
  by a constant;
- a low-depth warmup tier exists and is separate from the benchmark release;
- the trusted core is fast, typed, and independently testable, and CadQuery is
  confined to an execution boundary;
- vocabulary describes the problem, not an implementation accident;
- rejected programs and questions are recorded, never silently dropped;
- the dataset release is reproducible from a manifest and finite inputs.

The old release remains immutable and tagged. It may be used for a first training
cycle while the replacement is built. It must not be extended or repaired.

---

## 3. Users and consumers

| User | What they need |
|---|---|
| Dataset owner | Define tasks, inspect samples, finalize releases, and understand why an entry exists. |
| Training pipeline | Public prompts, private gold answers, splits/pools, and a stable machine-readable contract. |
| Evaluation pipeline | Held-out entries, typed answers, chance metadata, and per-slice breakdowns. |
| Reviewer or replicator | A manifest, hashes, commands, and reproducible generation. |
| Future contributor or agent | One clear task definition and a small set of extension points. |

---

## 4. Product scope

### In scope

- curating and fingerprinting the CadQuery program corpus;
- executing programs and recording geometry, topology, CadQuery selector results, and
  operation effects;
- building a typed CAD fact graph per program;
- defining composable task templates;
- instantiating tasks, verifying answers, and preserving distractors;
- rendering public prompts and private answer keys;
- assembling, validating, splitting, and freezing dataset releases;
- exporting public/private rows, warmup slices, and training/evaluation views;
- reporting coverage, balance, failures, and reproducibility metadata.

### Out of scope

- LLM model training, fine-tuning, reinforcement learning, and inference;
- LLM-authored prompts, LLM judges, or any LLM in the trusted path;
- CAD generation, editing, or reconstruction;
- a public query language or user-facing question DSL;
- running CadQuery inside the evaluation harness;
- reproducing the previous generator's internal schema or module layout.

---

## 5. Provisional vocabulary

The previous vocabulary was difficult to reason about because it mixed domain
concepts with implementation details. The following terms are the proposed
replacement. They are provisional until the owner approves them for the
glossary. Code and later specs must use the approved terms, not synonyms.

| Term | Meaning |
|---|---|
| **CadQuery program** | One program from the corpus, written in CadQuery. |
| **Program execution record** | The facts captured by running one CadQuery program: shape states, operation effects, CadQuery selector results, and failures. |
| **CAD fact** | A typed, verifiable statement about a program or its geometry, such as an entity, a relation, a measurement, or a validity result. |
| **CAD fact graph** | The collection of CAD facts for one CadQuery program. |
| **Task template** | A parameterized pattern of reasoning steps that can produce many questions. |
| **Task shape** | The structural pattern of a task template, for example *filter then traverse then aggregate*. |
| **Question** | One concrete instance of a task template bound to a program, a target, and sampled parameters. |
| **Target** | The entity or value the question asks about. |
| **Selection step** | One composable operation in the hidden reasoning procedure. |
| **Hidden selection procedure** | The deterministic procedure that starts from all candidates and narrows them to the target. |
| **Clue** | One public statement corresponding to exactly one selection step. |
| **Gold answer** | The answer produced by executing the hidden selection procedure. |
| **Shortlist** | The public list of candidate labels when the answer is a label rather than a value. |
| **Witness** | The facts and steps that prove the gold answer is unique. |
| **Reasoning depth** | The number of inference steps a question requires, computed from the witness. |
| **Dataset entry** | One generated question with its public and private column sets. |
| **Dataset release** | An immutable, validated, versioned set of dataset entries. |
| **Warmup slice** | A separate low-depth set used for task-shape and format warmup; not part of the benchmark release. |
| **Leakage group** | The unit that must not cross train/validation/test boundaries. |
| **Evidence tier** | The strength of the origin of a fact: kernel-backed, exact analytic, or surrogate. |

The most important renames are:

| Previous term | Proposed term |
|---|---|
| `source` | CadQuery program |
| `trace` | program execution record |
| `ontology graph` | CAD fact graph |
| `query program` | hidden selection procedure |
| `clause` | selection step, or clue when public |
| `candidate trace` | witness |
| `task family` | task template |
| `hop count` | reasoning depth |
| dataset row | dataset entry |
| resolver | selection engine |
| `quarantine` | non-release-ready |
| release gate | quality requirement or release check |

A full glossary pass is a separate owner-approved step. This PRD uses the
proposed terms but does not edit `docs/glossary.md`.

---

## 6. The task definition

A question is defined by four things:

1. **Target**: the entity or value being asked about.
2. **Hidden selection procedure**: an ordered composition of selection steps
   that narrows candidates to the target or computes the target value.
3. **Gold answer**: the target projected into one answer format.
4. **Public clues**: one clue per selection step, rendered in plain language,
   plus the answer instruction.

### 6.1 Selection steps

Every task is built from the same small step vocabulary. A step consumes a
candidate set and produces a candidate set, a value, or a truth value.

| Step | What it does | Example |
|---|---|---|
| **Select** | Start from all CAD facts of one category. | All faces of the final solid. |
| **Filter** | Keep candidates that satisfy a typed predicate. | Faces whose area is greater than a sampled value. |
| **Traverse** | Move from candidates along one typed relation. | Faces adjacent to the selected face. |
| **Compare** | Keep candidates whose measure compares to a reference. | Edges longer than the selected edge. |
| **Aggregate** | Choose or compute over candidates by a measure. | The face with the largest area; the count of edges. |
| **Compute** | Derive a value from the current candidates. | Volume removed by the selected cut; bounding box. |
| **Answer** | Project the final result into an answer format. | A label, a number, a coordinate, a boolean, or a JSON object. |

A step may use syntax-derived facts, geometry-derived facts, or both. For a
main benchmark task, at least one step must depend on geometry, topology,
CadQuery selector results, or execution measurements.

### 6.2 Composition rules

Every task template must satisfy these rules:

1. Steps are typed: the output of one step must be valid input to the next.
2. The procedure must end with exactly one target, or with a value computed from
   a uniquely determined set.
3. Every public clue maps to exactly one selection step, and every step has
   exactly one public clue.
4. Every step before the final answer must preserve distractors, except in
   explicitly low-depth warmup tasks.
5. No step may hard-code an avoidable choice. Target category, relation, metric,
   comparison, direction, reference, and answer format are sampled parameters
   where the evidence allows.
6. The procedure must be executable from the recorded CAD facts alone.
7. The gold answer must be recomputable and must match the stored answer.
8. A template that cannot satisfy these rules on enough programs is invalid and
   must be reported, not patched with special cases.

### 6.3 Reasoning depth

Reasoning depth is the number of inference steps in the witness:

- `Select` and `Answer` are not inference steps.
- Each `Filter`, `Traverse`, `Compare`, `Aggregate`, and `Compute` is one
  inference step.
- Depth is computed from the procedure, never declared as metadata.
- **Static depth** counts steps that use only syntax-derived facts.
- **Geometry depth** counts steps that use geometry-derived facts.
- Total depth is static depth plus geometry depth.

The release target is depth 2 to 5. Depth 0 and 1 are warmup and calibration
tasks and are kept in the separate warmup slice. Depth 6 or more may be added
later if the evidence supports it and the release remains balanced.

A depth label alone is not a difficulty claim. Difficulty also depends on the
number of distractors, the density of the relation graph, and whether the
required facts are kernel-backed.

### 6.4 Sampled parameters

A task template declares which parts of the pattern vary. The generator samples
those parts from evidence; it must not bake an avoidable choice into the
template.

| Parameter | Examples |
|---|---|
| Target category | face, edge, feature, vertex, endpoint, region, solid. |
| Relation | adjacency, containment, incidence, parallelism, perpendicularity, distance, order, provenance. |
| Measurement | area, volume, length, angle, distance, centroid, bounding box, topology count, delta. |
| Comparison | greater, smaller, equal within tolerance, parallel, perpendicular, before, after. |
| Direction | minimum, maximum, ascending, descending, nearest, farthest. |
| Reference | another entity, a sampled value, a CadQuery workplane, a point, a path. |
| Threshold | exact value, tolerance bucket, quantile, or category boundary. |
| Answer format | one of the eight answer formats. |
| Shortlist size | five to seven presented candidates. |
| Wording variant | a reviewed phrasing variant for the same clue. |

A template that hard-codes any of these choices is not release-grade. It may
still be useful as a warmup or calibration template, or as a negative test.

---

## 7. Task requirements

Requirements are grouped by task semantics, answers, dataset composition, and
operations. Each requirement has an acceptance check. The technical
specification will turn these checks into executable tests.

### 7.1 Task semantics

| ID | Requirement | Acceptance |
|---|---|---|
| **T-1** | Tasks are compositions of the step vocabulary. Adding a task shape or parameter combination must not require a new bespoke generation path. | A new valid task template can be added as data and produces questions without changing the core engine. |
| **T-2** | Every step is typed. Invalid compositions fail at template validation, not at row generation. | The template validator rejects a composition whose output category does not match the next step's input category. |
| **T-3** | Reasoning depth is computed from the witness, not declared. | Recomputing the witness reproduces the stored depth. |
| **T-4** | Main benchmark tasks are geometry-first: at least one step depends on geometry or execution evidence. | A syntax-only solver cannot determine the answer from names, literal arguments, or operation order. |
| **T-5** | The hidden procedure resolves exactly one target or value. Ties are rejected unless the template declares a deterministic tie-break that preserves uniqueness. | The selection engine returns one answer for every accepted question. |
| **T-6** | Intermediate steps preserve distractors. High-depth tasks keep at least two candidates before the final narrowing step. | Candidate counts are recorded per step and checked against the template's breadth policy. |
| **T-7** | Public clues are traceable. Each clue corresponds to one step, and each step has one clue. | Clue identifiers and step identifiers match exactly in both directions. |
| **T-8** | The task set covers the target categories the project claims: features, faces, edges, vertices, endpoints, CadQuery profiles, CadQuery workplanes, paths, regions, solids, and scalar facts. | Coverage report by target category, with explicit gaps. |
| **T-9** | The task set covers the relation categories the project claims: incidence, adjacency, containment, parallelism, perpendicularity, distance, order, provenance, and material/void relations. | Coverage report by relation category, with explicit gaps. |
| **T-10** | The task set covers the measurements the project claims: volume, area, length, angle, distance, centroid, bounding box, topology counts, and deltas. | Coverage report by measurement category and scope. |
| **T-11** | Feature-effect tasks are first-class: questions can ask for the volume, bounding box, topology, or centroid effect of an operation. | At least one feature-effect shape produces numeric answers, not only labels. |
| **T-12** | CadQuery selector and topology tasks are first-class: questions can depend on what a CadQuery selector actually selected. | CadQuery-selector-derived questions record the CadQuery selector result as evidence and cannot use surrogate identities. |
| **T-13** | A careful human can understand every rendered question without knowing the generator. | Human review of sampled prompts per template; ambiguous wording is a defect. |
| **T-14** | No public clue, shortlist, or prompt leaks the gold answer or private identifiers. | Leakage checks on prompt text, shortlist descriptions, and answer instructions. |
| **T-15** | Low-depth tasks exist for warmup and smoke runs, separate from the benchmark release. | A warmup slice contains depth 0 and 1 tasks across all answer formats. |
| **T-16** | A task template is viable only if it produces enough questions across enough CAD models to meet its release share. A non-viable template is reported, not silently omitted or patched. | Template viability report with generation counts and failure reasons. |
| **T-17** | Every public clue is rendered from a reviewed, versioned wording template. An unseen combination of step and wording fails validation instead of rendering ad hoc text. | Prompt-template coverage and review evidence per task template. |

### 7.2 Answers

| ID | Requirement | Acceptance |
|---|---|---|
| **A-1** | All eight answer formats are first-class: `candidate_label`, `coordinate`, `text`, `number`, `integer`, `boolean`, `bbox`, and `json`. | Each format appears in the warmup slice and in the release at or above its minimum share. |
| **A-2** | Identity answers use either a public program-visible name or a shortlist label. Internal CAD ontology identifiers are never public answers. | No public gold answer contains an internal identifier. |
| **A-3** | A `candidate_label` question shows a shortlist of real candidates from the same target set. The gold is always present, labels are unique, and descriptions do not collide. | Shortlist audit passes for every candidate-label entry. |
| **A-4** | For a benchmark release, a shortlist has at least five and at most seven candidates. | Shortlist size distribution satisfies the release requirement. |
| **A-5** | `number` answers are finite, unit-typed, rounded to a declared precision, and graded with a declared tolerance. | Numeric contract check per task template. |
| **A-6** | `integer` answers are exact non-negative counts or ranks with a declared range. | Integer contract check per task template. |
| **A-7** | `boolean` answers are true or false and have a typed submission tool. | Boolean tool round-trips through extraction and grading. |
| **A-8** | `coordinate` answers are three finite numbers with a declared frame and tolerance. | Coordinate contract check. |
| **A-9** | `bbox` answers are a minimum and maximum three-vector with a declared frame and tolerance. | Bounding-box contract check. |
| **A-10** | `json` answers have a template-specific schema with non-degenerate fields, such as a CadQuery workplane state. A JSON answer must not be a relabeled internal object dump. | JSON schema check and sampled human review. |
| **A-11** | `text` answers are program-visible variable names or program-visible entity names. They are unique in their program and do not require internal graph knowledge. | Text contract check. |
| **A-12** | Every answer format maps to one typed submission tool and one grading path. | Format/tool/grading parity test. |
| **A-13** | Candidate-label entries record the chance probability of a random correct guess. | Each entry carries enough metadata to compute chance-corrected accuracy. |

### 7.3 Dataset composition

These are release-level targets. Exact numbers belong in the technical
specification and the executable release rule set, but the PRD fixes the shape.

| ID | Requirement | Acceptance |
|---|---|---|
| **D-1** | A benchmark release contains at least 10,000 dataset entries. | Release count check. |
| **D-2** | A release draws from at least 1,000 distinct CAD model identities, not merely 1,000 program files. | CAD model coverage report keyed by CAD model identity. |
| **D-3** | Every answer format appears in the release. No format is a decorative branch with zero entries. | Format distribution check. |
| **D-4** | The release has at least 12 task templates and no template exceeds 10% of entries; every template contributes at least 1%. | Template distribution check. |
| **D-5** | The release covers reasoning depths 2 through 5 with no depth collapsed to zero. Depth 3 and 4 carry the headline slices. | Depth distribution check. |
| **D-6** | At least 95% of benchmark entries have geometry depth greater than zero, and at least 90% have total depth at least 3. | Geometry-depth and total-depth checks. |
| **D-7** | At least 15% and at most 30% of entries are value-bearing measurement tasks; at least 5% and at most 15% are cross-feature value-bearing tasks. | Value-bearing coverage checks. |
| **D-8** | Within a parameterized task template, no sampled parameter value exceeds 35% unless the template is explicitly marked geometry-limited. | Parameter-balance report. |
| **D-9** | The release has at least 1,000 unique gold answers and at least 8 bits of answer entropy. | Answer-diversity checks. |
| **D-10** | Candidate-label entries keep enough presented candidates that the chance floor is defensible. | Shortlist-size distribution and chance-floor report. |
| **D-11** | Every release entry records its evidence tier. Surrogate-backed entries are not release-ready. | Evidence-tier distribution and exclusion report. |
| **D-12** | The release is split into train, validation, and test; the training side is further split into SFT and RL pools. Evaluated entries are never trained on. | Split and pool manifests with disjointness checks. |
| **D-13** | Splits are group-safe by leakage group, and the leakage group is the CAD model, not the program file. | No CAD model crosses splits. |
| **D-14** | The release is contamination-checked against the external evaluation corpus used for transfer claims. | Overlap report by program hash and CAD model. |
| **D-15** | A separate warmup slice contains depth 0 and 1 tasks and is never included in benchmark-release metrics or claims. | Warmup manifest and exclusion check. |
| **D-16** | Every release entry has a complete provenance record: CadQuery program, execution record, task template, sampled parameters, witness, and hashes. | Provenance completeness check. |
| **D-17** | No intended release task template produces zero entries. | Template coverage report; zero-entry intended templates are release blockers. |
| **D-18** | No single prompt-wording template exceeds 5% of release entries, and the release has at least 20 distinct prompt-wording templates. | Prompt-template distribution check. |

### 7.4 Operations and quality

| ID | Requirement | Acceptance |
|---|---|---|
| **Q-1** | Generation is deterministic for a fixed corpus, generator version, and seed. | A replay produces the same release hash. |
| **Q-2** | Every accepted or rejected program and question is accounted for. There is no silent data loss. | Reconciliation report: input count equals accepted plus rejected plus skipped, with reasons. |
| **Q-3** | The trusted path contains no LLM. Generation and verification are deterministic. | Static check for network and LLM model clients in the trusted path. |
| **Q-4** | The generator is fast enough to iterate on a laptop. Program execution is cached and resumable; reruns do not re-execute unchanged programs; the deterministic core does not require CadQuery. | Pipeline-stage timing and memory report; a cached rerun of an unchanged corpus avoids re-execution. |
| **Q-5** | The core is typed and independently testable. The CadQuery boundary is small, explicit, and replaceable. | Core tests run without CadQuery installed; the execution adapter has its own contract tests. |
| **Q-6** | Adding a task template, a parameter dimension, or an answer-format adapter is a small, documented change with tests. | Extension guide and a worked example. |
| **Q-7** | Every release entry can be reconstructed from tracked manifests and hashes. | Reconstruction test from the manifest on a sample. |
| **Q-8** | A human review pass covers every changed task template and every new answer format before a release is finalized. | Review evidence stored with the release. |
| **Q-9** | The generator emits a stable public/private export that the training and evaluation pipeline can consume without re-deriving answers. | Downstream loader and grading smoke test. |
| **Q-10** | A small end-to-end run exercises every pipeline stage, every answer format, and depths 0 through 5. | E2E test with a small program corpus. |

---

## 8. Task catalog

This catalog is the rough shape of the tasks the generator must support. It is
not a closed list. New tasks are new compositions of the same steps. The
examples are illustrative, not literal prompt text.

| ID | Shape | Rough question | Typical answer formats | Depth |
|---|---|---|---|---|
| **C-1** | Select → Answer | What is the volume of the final solid? | `number` | 0 |
| **C-2** | Select → Filter → Answer | Which feature adds the most material? | `text`, `candidate_label` | 1 |
| **C-3** | Select → Traverse → Answer | Which CadQuery profile was used by the feature that created the final solid? | `text` | 1–2 |
| **C-4** | Select → Traverse → Filter → Answer | Which face of the final solid is parallel to the base plane and has the largest area? | `candidate_label`, `text` | 2 |
| **C-5** | Select → Filter → Aggregate → Answer | What is the rank of the selected edge among the edges of its face by length? | `integer` | 2 |
| **C-6** | Select → Filter → Count → Answer | How many faces of the final solid are parallel to the XY plane? | `integer` | 1–2 |
| **C-7** | Select → Compute → Answer | What is the volume removed by the cut that produced the hole? | `number` | 2 |
| **C-8** | Select + Select reference → Compare → Answer | Is the selected face larger than the face it shares an edge with? | `boolean` | 2 |
| **C-9** | Select + Select reference → Compute distance → Answer | What is the distance between the feature centroid and the nearest point on the path? | `number` | 3 |
| **C-10** | Select → Compute centroid → Answer | Give the centroid of the face that is adjacent to the top face. | `coordinate` | 1–2 |
| **C-11** | Select → Compute box → Answer | Give the bounding box of the solid after the final operation. | `bbox` | 1–2 |
| **C-12** | Select → Compute CadQuery workplane → Answer | Describe the CadQuery workplane of the sketch that produced the selected feature. | `json` | 2 |
| **C-13** | Select solid + point → Predicate → Answer | Is the point inside the final solid? | `boolean` | 1–2 |
| **C-14** | Select → Traverse → Traverse → Filter → Answer | Follow the face adjacency chain to the face created by the last cut. | `candidate_label`, `text` | 3–5 |
| **C-15** | Select → Traverse chain → Aggregate → Answer | Among the edges reachable through the selected faces, which is longest? | `candidate_label` | 4–5 |

### 8.1 Composability matrix

Every row is a task shape; every column is an answer format. A cell is
supported when the final target can be projected into that format without
changing the reasoning.

| Shape | label | text | number | integer | boolean | coordinate | bbox | json |
|---|---|---|---|---|---|---|---|---|
| Direct fact | — | — | yes | yes | yes | yes | yes | yes |
| Locate by filter | yes | yes | — | — | — | yes | yes | yes |
| One relation | yes | yes | yes | yes | yes | yes | yes | yes |
| Relation + filter | yes | yes | — | — | — | — | — | — |
| Aggregate or rank | yes | yes | yes | yes | yes | yes | yes | — |
| Compare | yes | yes | yes | yes | yes | yes | yes | — |
| Count | — | — | — | yes | — | — | — | — |
| Feature effect | yes | yes | yes | yes | yes | yes | yes | — |
| Distance | yes | yes | yes | — | yes | yes | — | — |
| Membership or validity | — | — | — | — | yes | — | — | — |
| CadQuery workplane state | — | — | — | — | — | — | — | yes |
| Multi-hop chain | yes | yes | yes | yes | yes | yes | yes | yes |

The matrix is a coverage requirement, not a promise that every cell is
instantiated in the first release. A cell that is not instantiated must be
reported as a known gap.

---

## 9. Dataset composition requirements

### 9.1 Benchmark release

The first replacement release must contain at least 10,000 entries and meet the
composition targets in section 7.3. The intended mix is:

| Dimension | Target |
|---|---|
| Reasoning depth | 2: 20–30%; 3: 30–40%; 4: 20–30%; 5: 10–20% |
| Answer format | every format at least 5%; no format above 25% |
| Task template | at least 12 templates; each 1–10% |
| Geometry depth | at least 95% of entries with geometry depth > 0 |
| Total depth | at least 90% of entries with depth at least 3 |
| Shortlist size | 5–7 candidates for `candidate_label` |
| Candidate breadth | at least 2 candidates before the final step; median at least 4 |
| Unique answers | at least 1,000 |
| Answer entropy | at least 8 bits |
| Distinct CAD model identities | at least 1,000 |
| Evidence | kernel-backed or exact analytic for release entries; no surrogates |

These are product targets. The technical specification will make them
executable and will define what happens when a target is infeasible.

### 9.2 Warmup slice

The warmup slice is a separate, non-release artifact. It exists because a small
LLM model needs an easy task-shape and format warmup, and because smoke runs need
cheap examples.

- 500 to 1,000 entries;
- depth 0 and 1 only;
- all eight answer formats;
- same public/private contract as the release;
- same provenance and verification rules;
- never counted in benchmark-release metrics or paper claims;
- group-disjoint from the release.

### 9.3 Splits and pools

The release is split by leakage group, where a leakage group is a CAD model, not
a program file and not a broad corpus provenance label.

- `sft_train`: entries that may enter an SFT mix;
- `rl_train`: entries held out from SFT for the RL-readiness gate and RL/RFT;
- `eval`: validation and test entries, never trained on.

The intended entry shares are approximately 70% `sft_train`, 15% `rl_train`, and
15% `eval`, with validation and test splitting the eval pool evenly. The exact
assignment algorithm belongs in the technical specification. The PRD requires
that no CAD model crosses splits and that the manifests report program, leakage-group,
and entry counts.

### 9.4 Corpus requirements

The corpus is the finite input to the generator. It must be:

- valid CadQuery that parses and executes within the execution budget;
- deduplicated by normalized code hash and by CAD model identity;
- grouped by CAD model so that variants of the same CAD model cannot cross splits;
- balanced enough to cover flat emitted programs and programs with control
  flow, functions, and math;
- licensed and provenance-recorded;
- stable under a content hash so a release can be reproduced.

The corpus manifest must report how many programs were considered, included,
duplicated, unsupported, timed out, or excluded, with reasons.

---

## 10. Quality attributes

### 10.1 Determinism and auditability

Given the same corpus, generator version, CadQuery/OCP version, and seed, the
generator must produce the same release hash. Every release must carry:

- the generator version and commit;
- the corpus manifest and content hashes;
- the CadQuery/OCP/Python versions;
- the task-template versions and sampled parameters;
- the selection seed;
- the command lines and pipeline-stage timings;
- the counts of accepted, rejected, and skipped programs and questions.

### 10.2 Performance and iteration

The previous generator was slow, repeatedly re-executed unchanged programs, and
could overheat a laptop. The replacement must make iteration cheap:

- tracing is cached by program content and environment version;
- a cached rerun of an unchanged corpus never re-executes;
- long stages are sharded and resumable;
- the deterministic core does not import CadQuery;
- the generator reports wall time and peak memory per pipeline stage;
- the default local workflow does not require re-executing the full corpus to
  change a task template or a prompt.

Exact timing budgets belong in the technical specification. The product
requirement is that a task-template change can be evaluated without paying the
full execution cost again.

### 10.3 Typed, testable core

The trusted core must be strongly typed, with explicit data records for facts,
steps, templates, questions, answers, and manifests. It must be testable
without CadQuery installed. CadQuery may appear only in the execution adapter
and in the tests that exercise that adapter.

This is a product requirement because the previous generator's untyped,
deeply coupled modules made it impossible to tell what a row depended on. The
choice of implementation language is deferred to the technical specification.

### 10.4 Extensibility

Adding a new task template or a new parameter dimension should be a data
change plus tests, not a new bespoke generator. Adding a new answer format
should require one typed value definition, one renderer, one submission tool, and
one grading path.

### 10.5 Failure accounting

Every program and every candidate question has one outcome: accepted, rejected
with a reason, or skipped with a reason. Failure reports are part of the
release, not a debugging afterthought. A release with unexplained missing entries
is invalid.

---

## 11. Deliverables

| Deliverable | Definition |
|---|---|
| Corpus manifest | The fingerprint, provenance, deduplication, and grouping record for the CadQuery program corpus. |
| Execution cache | Program execution records keyed by program hash and environment version, with failures included. |
| CAD fact graphs | Typed facts for every accepted program. |
| Task templates | Versioned, parameterized, composable task definitions with validation rules. |
| Question set | Generated, verified questions with witnesses and sampled parameters. |
| Dataset release | Immutable entries with public/private column sets, splits, pools, manifests, and reports. |
| Warmup slice | Separate depth 0/1 entries for task-shape and format warmup. |
| Exports | Public/private entries, SFT views, evaluation requests, and the training/evaluation loader contract. |
| Reports | Coverage, balance, failures, evidence tiers, shortlist audit, leakage, split audit, and reproducibility manifest. |
| Tests | Unit tests for the typed core, adapter tests for CadQuery, property tests for composition rules, and one end-to-end run. |
| Docs | This PRD, the approved glossary delta, and the technical specification. |

---

## 12. Definition of done

The replacement generator is done when:

1. a small end-to-end run produces every answer format and depths 0 through 5;
2. a 10,000-entry benchmark release meets the composition targets in section
   9.1, or every miss is recorded and explicitly accepted by the owner;
3. a separate warmup slice exists and is excluded from release claims;
4. the release is deterministic on replay and reconstructible from its
   manifest;
5. the training and evaluation pipeline can load the public/private export and
   grade a sample without re-deriving answers;
6. a human review of sampled prompts per task template finds no unclear or
   leaking questions;
7. the cached iteration loop is fast enough that changing a task template does
   not require retracing the corpus;
8. the old release remains immutable and the old generator is marked superseded.

---

## 13. Non-goals

- An LLM-model quality result. This PRD stops at the dataset; training and evaluation
  are separate.
- A public question language.
- An LLM-generated or LLM-judged dataset.
- Kernel access during evaluation.
- CAD generation or editing.
- Backward compatibility with the previous generator's internal schema. The
  public/private export may change, but downstream consumers must be migrated in
  the same effort.
- Preserving old task names, old family names, or old field names for their own
  sake.

---

## 14. Legacy and migration

- The old release is tagged
  `before-throwing-out-the-existing-dataset-generator` and is immutable.
- The old package is marked superseded by `dataset/SUPERSEDED.md`.
- The old documentation is archived under
  `docs/_archive/dataset-pre-rebuild-2026-10-21/`.
- The replacement must export a stable public/private view. The training and
  evaluation pipeline is migrated after the replacement can produce that view,
  not before.
- Old code may be read for algorithmic lessons, especially execution and
  CadQuery selector measurement, but it must not be copied wholesale into the
  replacement. Any reused logic gets a fresh contract and tests.

---

## 15. Open questions

- **Q1.** Is the benchmark-release target 10,000 entries, or should the first
  replacement release be smaller and the 10,000 target be a later scale-up?
- **Q2.** Is the minimum shortlist size five, or should it be seven for a lower
  chance floor?
- **Q3.** What exactly identifies a CAD model for leakage grouping: the base
  file stem, the path family, the normalized geometry, or a combination?
- **Q4.** Should depth 0 and 1 appear in the benchmark release at all, or only
  in the warmup slice? This PRD proposes warmup only.
- **Q5.** Should every answer format be required at a 5% share, or should the
  mix follow the task shapes and only require non-zero coverage?
- **Q6.** How many task templates should the first release target: 12, 20, or a
  smaller set with more parameter variation?
- **Q7.** Which external corpus must the contamination check cover for the
  transfer claim, and at what granularity?
- **Q8.** Should the warmup slice be generated from the same corpus and task
  engine, or from a separate small syntax/representation corpus?
- **Q9.** Does the training pipeline require a compatibility export in the old
  dataset-entry schema, or can it migrate to the new public/private schema immediately?
- **Q10.** Which of the proposed terms in section 5 are approved, and which
  need different names before they enter the glossary?
