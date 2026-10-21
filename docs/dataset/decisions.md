# Dataset decisions

**Status:** active, 2026-10-21.

Feature-wide decisions for the CAD-QA dataset, in ADR format
(`../docs-conventions.md`). Decisions scoped to one pipeline stage belong in
that pipeline stage's `Local decisions` section. Open questions live in the
document that owns the uncertainty; this file records decisions. The decision
prefix is `DS-`.

---

## DS-01 — Rebuild the dataset from first principles

- **Status:** accepted (2026-10-21).
- **Context:** The previous generator and documentation mixed good ideas,
  inherited names, and implementation-first choices. The result was hard to
  explain to a user and hard to check against its own claims.
- **Decision:** Start from the user outcome and a product PRD, then define the
  vocabulary, then write the technical specification. Archive the old
  documentation at `docs/_archive/dataset-pre-rebuild-2026-10-21/`; mark the old
  generator superseded; freeze the old release; keep no compatibility layer.
- **Consequences:** The replacement dataset may use a new task-file and
  answer layout. The old release may support a first training cycle, but it
  is not extended or repaired.

## DS-02 — A task and a question are different

- **Status:** accepted (2026-10-21).
- **Context:** Earlier documentation used "question" both for the whole dataset
  instance and for the interrogative sentence inside the prompt.
- **Decision:** A **task** is one dataset instance: a CadQuery program, a task
  target, a set of task clues, and one answer. A **question** is only the
  interrogative sentence in the prompt. The prompt also contains the program
  text, the task clues, optional choices, and the answer instruction.
- **Consequences:** Dataset code and documentation use "task" for the instance.
  Prompt documentation uses "question" only for the sentence.

## DS-03 — Compose tasks; do not enumerate task families, task types, or task patterns

- **Status:** accepted (2026-10-21).
- **Context:** A flat list of task labels mixed the target, the task reasoning step count,
  the answer format, and the measurement. Enumerating every combination would be
  limiting and would force an engineer to write logic for each combination.
- **Decision:** A task is composed from separate dimensions: the task target, the
  ordered task clues, the task answer step, the answer format, and the answer
  meaning. The generator composes these dimensions from the CAD graph. There are
  no task families, task types, or task patterns.
- **Consequences:** Coverage and balance are reported by the dimensions, not by
  a flat label list. A new combination of dimensions does not require a new code
  path.

## DS-04 — Check coverage and balance at every task reasoning step count

- **Status:** accepted (2026-10-21).
- **Context:** Global balance can hide a value concentrated at one task
  reasoning step count. Absolute percentages for a single step count do not work
  when each step count supports a different set of values.
- **Decision:** Coverage is checked at every task reasoning step count: every
  value supported at that step count must appear. Balance is checked at every
  step count using a **conditional release share**: a supported value's share at
  a task reasoning step count is between half and twice its share among the
  values supported at that step count. A step count with zero or one supported
  value for a dimension is coverage-only.
- **Consequences:** The release needs the task reasoning step support tables. The
  technical specification must define how support and the conditional share are
  computed, and must report conflicts instead of dropping coverage. Target
  category stays coverage-only at each task reasoning step count, with a
  release-level cap.

## DS-05 — Task reasoning step count is the only measure

- **Status:** accepted (2026-10-21).
- **Context:** The previous step-count targets were mathematically inconsistent,
  and the earlier "difficulty level" label was ambiguous about what is counted.
- **Decision:** A **task reasoning step** is either a task clue step or a task
  answer step. **Task reasoning step count** is the number of task reasoning steps.
  The target mix is: 1 step 5%, 2 steps 15%, 3 steps 40%, 4 steps 25%, and 5
  steps 15%. At least 80% of the release needs three or more task reasoning
  steps. One-step tasks form the labeled warmup subset.
- **Consequences:** A 10,000-task release contains about 500 warmup tasks and
  8,000 tasks at three or more steps. Product text says "task reasoning step
  count," not "difficulty level" or "reasoning depth."

## DS-06 — Answer meaning and answer format are separate

- **Status:** accepted (2026-10-21).
- **Context:** "Coordinate" and "bounding box" appeared as both answer meanings
  and answer formats, which blurred what the answer is about and how it is
  returned.
- **Decision:** An **answer meaning** is the semantic content of the answer:
  identity, volume, area, length, distance, angle, count, rank, membership,
  position, extent, CadQuery workplane state, material change, topology change,
  or validity. An **answer format** is the syntax the LLM model returns:
  multiple choice, number, integer, yes or no, 3D coordinate, bounding box, or
  structured object.
- **Consequences:** A position is returned as a 3D coordinate; an extent is
  returned as a bounding box. The technical specification needs a compatibility
  table from answer meaning to valid answer formats.

## DS-07 — Answers come from CadQuery or an exact rule, never an LLM

- **Status:** accepted (2026-10-21).
- **Context:** The dataset must be objectively checkable, and an LLM in the
  trusted path would make the correct answer unauditable.
- **Decision:** Every answer is produced by running the CadQuery program or by an
  exact derivation from the program and its geometry, and is recorded with
  evidence. No LLM writes or judges an answer.
- **Consequences:** A guessed or approximate value is not evidence. A task whose
  answer cannot be produced with evidence is rejected.

## DS-08 — Domain terms may appear in the PRD; internal terms may not

- **Status:** accepted (2026-10-21).
- **Context:** The PRD must be product-facing, but coverage and balance logic
  needs internal vocabulary. Mixing the two leaks generator mechanics into the
  product contract.
- **Decision:** The terminology document marks each term as **domain** or
  **internal**. Domain terms may appear in the PRD. Internal terms must not;
  product text uses the domain term or describes the user-visible outcome.
  `task reasoning step`, `task reasoning step count`, `task clue step`, and `task
  answer step` are domain terms. `task reasoning step count coverage`,
  `task reasoning step count balance`, and `conditional release share` are
  internal terms.
- **Consequences:** The PRD uses task reasoning step count. Technical documents
  may use the internal terms. The terminology is still a proposal; it has not
  been merged into `docs/glossary.md`.

## DS-09 — Warmup and splits

- **Status:** accepted (2026-10-21); corrected (2026-10-21).
- **Context:** A small LLM model needs a lower-step entry point, and evaluation
  must not see training programs.
- **Decision:** The warmup subset is the 1-step bucket: 5% of tasks, drawn from
  the same program pool and labeled inside the dataset.
  Training, validation, and test are split by CADEvolve program family at
  approximately 70/15/15; the same family never appears in more than one part.
- **Consequences:** Warmup tasks may be used for training. The test part is never
  trained on, tuned on, or used to choose an LLM model. `DS-26` defines the
  program-family identity.

## DS-10 — Task definitions and release planning are specified together

- **Status:** accepted (2026-10-21); delivered in `03a`–`03c`.
- **Context:** The dimensions and balance rules do not define the set of tasks.
  "Enumerate all tasks" is ambiguous until the task identity, the valid-task
  set, and the release plan are defined.
- **Decision:** The task-definition contract defines the task tuple and canonical
  identity, the valid-task set, the validity oracle, exact task reasoning step
  count accounting, the typed clue predicate schema, the answer meaning to
  answer format map, the release planning and sampling algorithm, deterministic
  ordering, deduplication, serialization, and split assignment.
- **Consequences:** Implementation starts from the `03` contract.
  `requirements/task-structure.md` and this file define the target; `03a`
  defines planning and `03b` defines construction.

---

## DS-11 — Drop 0-step tasks

- **Status:** accepted (2026-10-21).
- **Context:** The previous docs allowed a task with no task clue step and no
  task answer step, so the lowest step count bucket was ambiguous and could be
  read as "no clue."
- **Decision:** Every task has at least one task reasoning step. The lowest step
  count in the release is 1. The warmup subset is the 1-step tasks. There is no
  0-step category.
- **Consequences:** The step-count target mix starts at 1 step (5%). The PRD no
  longer defines or generates 0-step tasks. The warmup subset is still the
  1-step bucket at 5% of the release.

---

## DS-12 — No separate answer-key container

- **Status:** accepted (2026-10-21).
- **Context:** "Answer key" is an assessment-artifact term. It entered the PRD
  as a file-layout concept before the dataset data model existed, which implied a
  separate container that the product does not need. The release still contains
  answers for training and scoring; the prompt does not.
- **Decision:** The release dataset has tasks and their correct answers. The
  prompt contains no answer. There is no separate answer-key object. The
  technical specification chooses how answer columns are represented.
- **Consequences:** Product and terminology text say "correct answer" or "gold
  answer," not "answer key." A human-readable answer listing, if needed, is a
  release artifact chosen by the technical specification, not a dataset concept.

---

## DS-13 — Do not use public/private for dataset parts

- **Status:** accepted (2026-10-21).
- **Context:** "Public" and "private" are access scopes. Using them for dataset
  columns conflates visibility with permission and makes the data model sound
  like an access-control model.
- **Decision:** Use **prompt** for what the LLM model sees. Use **answer
  columns** or **answer data** for the gold answer and scoring material. Access
  control, if any, is a separate concern.
- **Consequences:** Dataset docs do not use "public" or "private" for dataset
  parts. The glossary marks the old column-set names as legacy.

---

## DS-14 — Numeric answers use 4 significant figures

- **Status:** accepted (2026-10-21).
- **Context:** The worked example printed `25.132741`, which implies eight
  significant figures and an unnecessarily tight grader.
- **Decision:** Numeric answers are rounded to 4 significant figures by default.
  Coordinates and bounding-box components use the same default. A task may state
  a different precision only with a documented reason.
- **Consequences:** The worked example answer is `25.13`. The answer data stores
  the rounded value; grading uses half a unit in the last stated place unless
  the task states another tolerance.

---

## DS-15 — Task text does not use variable names

- **Status:** accepted (2026-10-21).
- **Context:** Variable names are code-level identifiers. A BrowseComp-style
  task states the domain problem, not the implementation's internal names.
- **Decision:** Questions, task clues, multiple-choice descriptions, and answer
  instructions do not name variables. They describe an entity by its geometry or
  its role in the construction. The program text is the only place variable
  names appear. The answer format "variable name" is removed; identity answers
  use multiple choice.
- **Consequences:** Multiple-choice descriptions are geometric or construction
  descriptions. An LLM model cannot answer by matching a variable name; it must
  identify the entity from the construction. Internal graph identities may still
  use variable names.

---

## DS-16 — Question names the category; task clues are numbered

- **Status:** accepted (2026-10-21).
- **Context:** Prompt-content Q1 and Q2 were open. The question and the clue
  list need a fixed shape before prompt rendering can be specified.
- **Decision:** The question always names the task target category and the
  answer meaning. Task clues are a numbered list in reasoning order. The number
  is presentation, not a task reasoning step count.
- **Consequences:** The prompt renderer has one layout. The question does not
  narrow candidates; every task clue still maps to one task clue step.

---

## DS-17 — Comparison clues may name an entity or reuse one selected earlier

- **Status:** accepted (2026-10-21).
- **Context:** `requirements/task-structure.md` Q1 asked whether a comparison task clue must
  name both entities. BrowseComp-style composition lets a later step use a
  result from an earlier step, and the dataset needs the same freedom without
  ambiguous references.
- **Decision:** A comparison task clue may name both entities or refer to one
  entity selected by an earlier task clue. Every reference is either named in
  the program or selected earlier. A reference must resolve to exactly one
  entity; if earlier clues leave several, the clue needs an explicit aggregation
  or the task is rejected. The reference does not add a task reasoning step.
- **Consequences:** A task is evaluated over one CAD graph per program. The
  per-task evaluation carries the current set of possible answers and bindings
  for entities selected by earlier clues. It does not need one graph per clue or
  one graph per solid state; earlier and later solid states and their
  relationships already live in the same graph.

---

## DS-18 — P0/P1/P2 are implementation order, not task labels

- **Status:** accepted (2026-10-21); corrected (2026-10-21).
- **Context:** Priorities on requirements and generation inputs were being
  converted into a task priority. That made the release table carry a label with
  no product meaning and made the same task change priority depending on which
  inputs happened to be used.
- **Decision:** P0/P1/P2 describe the order in which requirements and generation
  inputs are implemented. A task is never labelled P0, P1, or P2. A release is
  defined by the generator scope that produced it; later releases add tasks from
  later scopes. Coverage and balance are checked against the values implemented
  by that release. A value deferred to a later scope is not a gap in the current
  release. No release column records implementation priority.
- **Consequences:** The release table has no `task_priority` column. Six or more
  task reasoning steps and P2 inputs belong to later implementation scope, not
  to a task label. The first benchmark release implements the P0 scope; later
  releases add P1 and P2 values.

## DS-19 — Cross-state `same_as` is P2

- **Status:** accepted (2026-10-21).
- **Context:** Cross-state topology identity is ambiguous: kernel IDs change,
  faces can split or merge, and geometric fingerprints can collide. P0 does not
  need persistence to compare before and after states, count topology changes,
  or reason about material change.
- **Decision:** P0 and P1 use independent topology per solid state (Option C).
  `same_as` is P2 only, for explicit persistence tasks. When used, it records
  evidence (kernel identity or a geometric fingerprint) and rejects ambiguous
  matches.
- **Consequences:** P0 and P1 implementation refers to an entity in a named
  solid state and does not depend on cross-state identity. P2 persistence work
  may use `same_as`. No second graph is needed; the relation lives in the same
  graph.

---

## DS-20 — A release dataset is one table

- **Status:** accepted (2026-10-21).
- **Context:** Earlier drafts split the task and answer into two tables to keep
  the answer out of the LLM-facing artifact. That conflated the prompt, which
  is what the LLM model sees, with the release artifact. The release must
  contain answers for training and scoring; the evaluator selects columns.
- **Decision:** A release dataset is one `release.parquet` table, one row per
  task, with prompt and answer columns. The prompt column is answer-free. The
  answer columns hold the gold answer, scoring fields, and evidence. A
  prompt-only view is derived when a consumer needs one. Parquet is canonical;
  JSONL is an optional export.
- **Consequences:** The minimum artifacts are `release.parquet`,
  `manifest.json`, `dataset-card.md`, `failures.parquet`, and `support/`. No separate answer
  table, program table, or evidence table is needed initially. The evaluation
  harness must pass only `prompt` to the LLM model. The structure is defined in
  `requirements/release-dataset-contract.md`.

## DS-21 — Plausible near-miss distractors are P2

- **Status:** accepted (2026-10-21).
- **Context:** Multiple-choice choices must be real, unique, and non-leaking for
  P0 and P1. Examiner-style plausible near misses improve difficulty and audit,
  but they add an error-mode catalog, validation, and review work that is not
  needed for the thesis.
- **Decision:** P0 and P1 require real candidates. P2 requires every distractor
  to be a plausible near miss that fails at least one task clue or the answer
  step, with a recorded error mode. If enough plausible distractors cannot be
  generated, the task is rejected.
- **Consequences:** P0 and P1 can ship without the near-miss audit. P2 adds the
  error-mode catalog, choice audit, and review. The open question is Q6 in
  `implementation/pipeline/03b-construct-task-definitions.md` until P2 is implemented.

## DS-22 — Go is the default implementation language

- **Status:** accepted (2026-10-21).
- **Context:** The dataset generator is mostly file, graph, coverage, and export
  work. Python is required only where CadQuery/OCP or Python semantics are
  involved. Mixing languages without a boundary would duplicate models and make
  the generator harder to operate.
- **Decision:** Go is the default for all dataset implementation work. Python is
  allowed only for work that requires the Python runtime or a Python-only
  library: CadQuery/OCP execution, Python AST or tokenizer work, and canonical
  Python program normalization. The CLI, orchestration, manifests, graph
  assembly, task enumeration, prompt and choice rendering, release planning,
  validation, and export are Go. The boundary is defined in
  `implementation/python-and-golang.md`.
- **Consequences:** The Go entry point invokes Python workers through typed,
  versioned artifacts. Go code does not import CadQuery or OCP. Python code does
  not own release state. New Python code outside the allowed list needs a
  decision.

## DS-23 — Bulk artifacts are columnar

- **Status:** accepted (2026-10-21).
- **Context:** Per-row JSON parsing and serialization dominated CPU time, and
  row-oriented JSON artifacts add IO. Most dataset artifacts have many rows with
  a stable schema.
- **Decision:** Parquet is the default for artifacts with many rows. Use typed
  nested structs and lists for schemas that are known. Do not store bulk
  artifacts as JSONL or as one JSON string per row. JSON is limited to small
  control documents and opaque versioned payloads that cannot be typed. JSONL
  is an optional inspection export, never part of a pipeline stage or release
  contract.
  Rejections use `failures.parquet`; the release table remains `release.parquet`.
- **Consequences:** Pipeline stages exchange columnar tables, not JSON rows.
  Large tables are partitioned by program family or release where useful. The release
  artifacts are `release.parquet`, `failures.parquet`, `manifest.json`,
  `dataset-card.md`, and `support/`. Schema versions are recorded in Parquet
  metadata and the manifest.

## DS-24 — Start from the prepared CADEvolve Parquet cache

- **Status:** accepted (2026-10-21).
- **Context:** The raw CADEvolve release is a 4.7 GB tar archive. A prepared
  Parquet cache is published at `MRiabov/cadevolve-parquet`, contains the same
  program records in typed columns, and is about 508 MB. Archive extraction and
  row parsing are avoidable work.
- **Decision:** `01a` reads metadata from `cadevolve_sources.parquet` from
  `MRiabov/cadevolve-parquet`; `01b` selects the program pool; `01c` fetches only
  the selected rows; `01d` applies our own normalization version and program
  hash. The cache commit and conversion version are recorded in the external
  dataset manifest. The tar archive and JSONL are not primary inputs; they are
  provenance checks only.
- **Consequences:** No archive extraction in the normal path. The cache schema
  is part of the external input contract. A cache change is a new external
  dataset version, not an in-place update. Program identity remains ours.

## DS-25 — CADEvolve P and C are separate program populations

- **Status:** accepted (2026-10-21).
- **Context:** CADEvolve-3L is a three-tier corpus. G contains parametric
  generators, P contains executable programs with arbitrary code style, and C
  contains canonicalized, centered, scaled, and binarized programs used for
  training. P and C have no program-hash overlap.
- **Decision:** The dataset treats P and C as separate program populations.
  P0 and P1 use C only; P2 adds P. `01b` never deduplicates P against C or
  assumes one is a duplicate. G is not ingested. The program pool records the
  tier mix.
- **Consequences:** Prompt style and geometry scale depend on the tier. C is
  canonical and normalized; P preserves arbitrary style and original pose/scale.
  Counts from P and C are not additive as if they were the same programs.

## DS-26 — Split by CADEvolve program family

- **Status:** accepted (2026-10-21).
- **Context:** Splitting by CadQuery program is not enough. Different programs
  sampled from one CADEvolve generator share a code template and parameter
  family; P and C versions of one mesh or generator are also related. A
  program-level split can put near-duplicates in both training and evaluation.
- **Decision:** Split by `cadevolve_program_family_id`. For CADEvolve core, the
  family is the generator family taken from the path. For CADEvolve-predicted
  ABC/ShapeNet, the family is the mesh family. P and C versions of one family
  share an ID. Assign train, validation, and test at the family level; every
  task inherits the family split. The release table records
  `cadevolve_program_family_id`.
- **Consequences:** Split isolation is stricter than program isolation. Split
  sizes are balanced by family size, not program count. Unmatched P/C families
  become their own families. The cache's `generator_id` column is not the
  generator identity; derive the family from the CADEvolve `path_family` cache
  column.

## DS-27 — P2 adds P for scale variation

- **Status:** accepted (2026-10-21).
- **Context:** C canonicalization scales the longest bounding-box side to 200
  units, so C programs do not vary in absolute scale. P preserves the original
  pose and scale and uses arbitrary code style.
- **Decision:** P0 and P1 use C only. P2 adds P. P and C versions of one
  generator or mesh family share a program family ID, so P2 cannot split
  them across train and test.
- **Consequences:** P0/P1 keep canonical prompts and simpler normalization. P2
  gains absolute scale variation and arbitrary code style. The CADEvolve program
  family mapping must cover both tiers before P2 is built.

## DS-28 — `03` writes task definitions; task reasoning step support tables are a QA projection

- **Status:** accepted (2026-10-21).
- **Context:** The task reasoning step support tables had become a hand-authored
  generator input and crowded out the actual task-definition contract. That
  inverted the source of truth: a value is feasible because the task rules can
  construct it, not because a support row allows it.
- **Decision:** `03` defines task definitions and emits persisted
  `TaskDefinition` records. The task reasoning step support tables are derived
  from those rules as a separate QA baseline. They are not a pipeline stage and
  not a generator input; `03a` plans, `03b` constructs, `04` renders, and
  `03a`/`05` use the tables to check the release.
- **Consequences:** `03` does not read the task reasoning step support tables. A feasible value
  missing from the dataset is a coverage gap; a released value marked infeasible
  is a specification or generator defect. Dataset quantity remains a separate
  coverage question.

## DS-29 — Plan quotas before constructing task definitions

- **Status:** accepted (2026-10-21).
- **Context:** The valid-task set is combinatorial. Enumerating every task and
  selecting afterward wastes work and can exceed any practical budget.
- **Decision:** Plan the release first with marginal quota cells, family
  profiles, split assignment, and attempt budgets. Construct and sample task
  definitions into that plan. Use `03c` to replan or expand the program data when quotas
  cannot be filled.
- **Consequences:** There is no separate post-construction release-selection
  pipeline stage. `03c` is a bounded loop back through supplemental `01b` selection,
  `01c`/`01d` delta processing, `02` graph building, and an updated plan.
  Deficits are recorded and either filled or accepted.
