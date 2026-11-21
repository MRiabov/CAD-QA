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
  answer evidence. No LLM writes or judges an answer.
- **Consequences:** A guessed or approximate value is not answer evidence. A task
  whose answer cannot be produced with answer evidence is rejected.

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

## DS-10 — Task definitions and task quota planning are specified together

- **Status:** accepted (2026-10-21); delivered in `03a`–`03c`.
- **Context:** The dimensions and balance rules do not define the set of tasks.
  "Enumerate all tasks" is ambiguous until the task identity, the valid-task
  set, and the task quota plan are defined.
- **Decision:** The task-definition contract defines the task tuple and canonical
  identity, the valid-task set, the validity oracle, exact task reasoning step
  count accounting, the typed clue predicate schema, the answer meaning to
  answer format map, the task quota planning and sampling algorithm, deterministic
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
  CAD graph evidence (kernel identity or a geometric fingerprint) and rejects
  ambiguous matches.
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
  answer columns hold the gold answer, scoring fields, and answer evidence. A
  prompt-only view is derived when a consumer needs one. Parquet is canonical;
  JSONL is an optional export.
- **Consequences:** The minimum artifacts are `release.parquet`,
  `manifest.json`, `dataset-card.md`, `failures.parquet`, and `support/`. No separate answer
  table, program table, or answer evidence table is needed initially. The evaluation
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
  `implementation/pipeline/03-task-generation/03b-construct-task-definitions.md` until P2 is implemented.

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
  assembly, task enumeration, prompt and choice rendering, task quota planning,
  validation, and export are Go. The boundary is defined in
  `implementation/python-and-golang.md`; the declared libraries and toolchains
  are in `implementation/stacks.md`.
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
- **Consequences:** `03` does not read the task reasoning step support tables as
  data. `03a` calls the same derivation that writes them, so the plan and the QA
  projection cannot disagree; `05` reads the persisted tables. A supported value
  missing from the dataset is a coverage gap; a released value the table marks
  unsupported is a specification or generator defect. Dataset quantity remains a separate
  coverage question.

## DS-29 — Plan quotas before constructing task definitions

- **Status:** accepted (2026-10-21).
- **Context:** The valid-task set is combinatorial. Enumerating every task and
  selecting afterward wastes work and can exceed any practical budget.
- **Decision:** Plan task quotas first with independent quota targets, family
  profiles, split assignment, and attempt budgets. Construct and sample task
  definitions into that plan. Use `03c` to replan or expand the program data when quotas
  cannot be filled.
- **Consequences:** There is no separate post-construction release-selection
  pipeline stage. `03c` is a bounded loop back through supplemental `01b` selection,
  `01c`/`01d` delta processing, `02` graph building, and an updated plan.
  Deficits are recorded and either filled or accepted.

## DS-30 — Code and schema names mirror approved terms

- **Status:** accepted (2026-10-22).
- **Context:** The dataset generator is greenfield and docs-only. An implementation that
  invents a synonym for a glossary term creates a second vocabulary, and
  persisted names are expensive to change later. Extraction had inherited
  `Static*` and `Execution*` names from an earlier implementation choice.
- **Decision:** Every pipeline stage uses the approved glossary term, or its
  documented `In code:` identifier, for class, function, artifact, table, field,
  and hash names. Do not retain a synonym from an earlier implementation.
  Preserve the term's qualifiers and do not introduce a new short form. If an
  approved term changes, rename the affected names in the same change and bump
  the affected schema version when the artifact schema changes.
- **Consequences:** Extraction is the first application: `Static*`, `static_*`,
  and `Execution*` are retired, and extraction uses
  `CadQueryAstExtractionResult`, `Ast*`, `CadQueryRuntimeExtractionResult`,
  `CadQueryRuntimeExtractionSuccess`, `FailureTombstone`,
  `CadFeatureSolidStateEffectDelta`, `CadQuerySelectorResult`, `ast_*` and
  `runtime_*` tables, and the matching hash fields. Every later pipeline stage
  follows the same rule.

## DS-31 — A clue is one narrowing statement, described by clue type and clue operand form

- **Status:** accepted (2026-11-20).
- **Context:** An earlier draft described each clue by a derivation-depth ladder
  (`S0`–`S5`) and each answer by a four-level ladder (`A0`–`A3`). Both were
  invented partitions with no precedent in the prior-art survey. The ladder also
  implied that one clue could contain several task reasoning steps, which
  contradicts the rule that a clue is one narrowing statement. The word
  "stratum" was read as a frequency target, which is a different axis.
- **Decision:** A clue is one narrowing statement and one task clue step. It is
  described by its clue type — property, relation, comparison, aggregation, or
  provenance — and, when it has a reference, by the clue operand form of that
  reference: `named`, `selected`, `aggregated`, or `cross_state`. A clue with no
  reference has no clue operand form. The answer step is described by `answer_meaning`
  and has no separate ladder. Task reasoning step count stays the number of clues
  plus the answer step.
- **Consequences:** `clue_operand_form` belongs to the clue's reference binding,
  not to the clue, so the property clue type carries none. Coverage is checked per
  clue operand form for clues that carry a reference; the clue type stays in the
  per-task profile, so a pair breakdown is derivable. The support table is
  `clue-operand-form-by-step`. "Stratified sampling" stays reserved for
  dataset-level composition; the frequency target for a clue type is a clue quota
  or clue share.

## DS-32 — Answer uniqueness compares an answer-equivalent set

- **Status:** accepted (2026-11-20).
- **Context:** Entity uniqueness and answer uniqueness conflict. A measurement
  answer can have several entities that all produce the same number, which is
  answerable; an identity answer cannot, because two entities are two labels.
  Choosing one rule globally either rejects symmetric measurement tasks or admits
  ambiguous identity tasks.
- **Decision:** Answer uniqueness compares every entity in the answer-equivalent
  set using `same_answer`, a relation supplied by the answer meaning and the
  answer format. Identity answers compare entities; numeric answers compare
  canonical strings at the stated precision; label answers compare labels. The
  chain search terminates on answer uniqueness, never on a set size of one.
- **Consequences:** The answer-equivalent set is recorded in the answer evidence.
  `same_answer` is the comparison the release grader performs, so a task cannot
  pass build-time uniqueness and fail scoring. A comparison clue uses the same
  precision to decide whether a measured difference is real. An identity answer
  in multiple-choice format requires a singleton set. `position`, `extent`, and
  the change answer meanings need their own equality rule before they ship.

## DS-33 — Task generation is supply-driven with capability-aware deficits

- **Status:** accepted (2026-11-20).
- **Revised by:** `DS-43`; the census is derived from the graph, not emitted by
  `02c`.
- **Context:** A full demand-driven planner would specify a task cell up front and
  query a capability index for programs that can support it. The capability
  census needs the graph, but `01b` selects the program pool before `02` builds
  graphs, so the planner either reverses pipeline stage order or forces a larger
  execution pass. A capability in the pool is also not a constructed task.
- **Decision:** `03b` constructs tasks supply-driven by default, from the facts a
  graph actually has. The census is derived from the graph; `DS-43` supersedes
  the earlier sentence that had `02c` emit it as a by-product. `03a` and `03c` use
  that census only for deficits: when a
  quota target is underfilled, they query it for capable programs and request
  supplemental programs through the existing slow loop. A cell-level demand query
  is a last resort and carries a `forced` flag and a naturalness check.
- **Consequences:** `01b` stays metadata-based. `capability_deficit` becomes a
  deficit reason. Forced tasks are confined to the deficit path, where review can
  see them, and a miss is recorded rather than filled with an unnatural task.

## DS-34 — Tasks refer to the final solid state in P0

- **Status:** accepted (2026-11-20).
- **Context:** A CadQuery program produces a solid state after each solid state
  producing operation, and topology entities belong to one state. The
  same face can exist in several states with different measurements, so a task
  that does not bind a state has no well-defined possible-answer set and its
  answer can differ between snapshots.
- **Decision:** P0 tasks refer to the final solid state only. P1 adds one named
  intermediate state, identified by its producing operation. P2 adds before/after
  pairs for material-change and topology-change answers. The state is bound
  before the clue chain starts and is named in the user prompt; a clue never
  introduces it.
- **Consequences:** `TaskDefinition` carries `state_scope`, which is `final` in
  P0. The possible-answer set is defined per state scope. A clue that needs
  another state is rejected rather than resolved by convention. An effect answer
  that reads the bound operation's recorded delta needs no second state, so
  material-change and topology-change answers are P0. Only an answer that compares
  two states waits for P2.

## DS-35 — Canonical clue order is identity-bearing; prompt order is a permutation

- **Status:** accepted (2026-11-20).
- **Context:** Clues are conjunctive conditions on one target, so the prompt can
  present them in any order that respects references. The construction record
  needs a stable order, because identity, deduplication, the narrowing record,
  and the strict-narrowing check all depend on it. Treating the two as one order
  either freezes the prompt, which leaks that the last clue is the
  discriminator, or makes identity depend on rendering.
- **Decision:** The task definition stores a canonical clue order: dependency
  order first, then broad-to-narrow by the size of the narrowed set, descending,
  with a stable hash as the tie-break. Validity checks, the narrowing record, and
  `task_id` use this order. The prompt may render a permutation that respects
  reference dependencies. P0 renders the canonical order; P1 may render a seeded
  permutation recorded as the render seed.
- **Consequences:** The render seed and the presentation order belong to
  provenance, not to `task_id`. Clue wording uses presentation positions ("the
  face from clue 2"), never canonical positions. Strict narrowing is checked in
  canonical order only, so a permuted prompt may contain a clue that does not
  narrow at its position; the conjunction is unchanged. The multiple-choice pool
  stays the canonical penultimate set, so after a shuffle the choices are no
  longer "what the prompt's last clue discriminated between".

## DS-36 — Multiple-choice options come from the penultimate answer candidate set

- **Status:** accepted (2026-11-20).
- **Context:** `prompt-content.md` fixes the count (at least five, seven as the
  goal), the labels, uniqueness, leakage, and ordering. It does not say which
  candidates become options, so a renderer could draw from anywhere in the graph,
  including entities the last clue already excluded.
- **Decision:** Identity answers draw options from the penultimate answer
  candidate set, the entities the last clue discriminated between. Numeric answers
  draw options from the distinct answers of that set, so the options are
  comparable numbers. If fewer than five real options exist, the task is
  rejected; options are never padded.
- **Consequences:** The choice pool is a construction output, not a rendering
  choice: `03b` orders it and assigns its labels, so a multiple-choice task's
  `gold_answer` is a label before the definition is hashed. `04` renders that
  order and must not reorder, relabel, re-bind, or extend it. A task whose
  penultimate set is smaller than five is a deficit, not a padded task.

## DS-37 — Clue operand form is a coverage dimension in P0

- **Status:** accepted (2026-11-20).
- **Context:** Coverage requires a supported value to appear at all; balance
  requires its share at a task reasoning step count to stay within half to twice
  the conditional release share. Clue operand forms are unevenly available:
  `selected` needs an earlier clue, `cross_state` waits for P2, a property clue
  has no operand form, and an aggregation with an `aggregated` reference is two
  clues. A balance range at a step count where a form cannot exist would be
  vacuous or would force invalid tasks.
- **Decision:** In P0, clue operand form is a coverage dimension: every supported
  form appears at each step count where the support table says it is supported.
  Balance over clue operand form is P1, once the support grid is dense enough for
  a proportional target.
- **Consequences:** `03a` adds clue operand form as a coverage dimension with a
  minimum and no balance range in P0. The `clue-operand-form-by-step` support table
  decides which forms are required at each step count. A missing form at a step
  count is a coverage gap, not a balance problem. Coverage-only is a concession,
  not a good property: it guarantees that each form appears, not that the forms
  are usefully mixed, so a P0 release can concentrate one clue operand form. P1
  balance is the correction, and until it exists the clue operand form distribution is
  reported but not enforced. Severe imbalance promotes the balance target into P0
  for that release: the P1 balance check is computed and reported without
  blocking, and a form below a quarter or above four times its conditional share
  is severe. The release is then rebalanced or the miss is recorded with its
  reason. The quarter and four-times bounds are provisional.

## DS-38 — Clue operand form is reported as a descriptive breakdown, not a difficulty axis

- **Status:** accepted (2026-11-20).
- **Context:** `DS-05` makes task reasoning step count the only measure of task
  difficulty, and `DS-37` makes clue operand form a P0 coverage dimension.
  Coverage alone does not show how the forms combine inside one task, and the
  per-task clue operand form profile is already part of the definition.
- **Decision:** Every task definition records `clue_operand_form_profile`, the
  ordered clue type and clue operand form of each clue. The release reports
  aggregate coverage per task reasoning step count, and the per-task clue
  operand form profile stays available. Clue operand form is descriptive; it is
  not a difficulty label, and `DS-05` is unchanged.
- **Consequences:** The release table carries `clue_operand_form_profile`, and `05`
  checks coverage per clue operand form. The recorded entry keeps the clue type, so a
  `(clue_type, clue_operand_form)` breakdown is derivable without a second support
  table. Benchmark results may name the step counts and clue operand forms they
  cover, without ranking tasks by clue operand form.

## DS-39 — The CAD graph is an immutable Parquet artifact, not a relational table

- **Status:** accepted (2026-11-20).
- **Context:** `DS-23` makes Parquet the default for many-row artifacts, and
  `implementation/pipeline/extraction/graph-persistence.md` defines the graph as
  three Parquet tables. The open question is whether the graph should instead
  live in a relational database, where foreign keys and joins are native. The
  access pattern answers it. The graph is written once per program and never
  mutated, it is read one program at a time, and the interesting queries are
  traversals over one program's edges rather than joins across programs. A
  relational store would therefore add a server, a DDL copy of the schema, and a
  second writer without removing the cost that dominates a read: hydrating rows
  into program objects. Measured on `runs/current_cadevolve1000_10k_regen_20260613`,
  1,000 programs produce 677,937 nodes, 20,135,608 relations, and 10,205,884
  measurements. The Parquet holding them is 163 MB; the same graph as JSON text
  is 6.7 GB, a 41× ratio driven by repeated relation keys. Reading the heaviest
  100-program shard through the current JSON-in-Parquet path takes 21.0 s wall
  and 5.8 GB peak RSS, almost all of it in `json.loads`; the same rows as three
  typed tables scan in 0.37 s at 562 MB, a 57× difference.
  `tools/bench_graph_columnar.py` reproduces both numbers.
- **Decision:** The CAD graph is stored only as the Parquet tables in
  `graph-persistence.md`. No relational database is the graph store, and Postgres
  is rejected for it. Referential integrity stays a builder invariant and a
  validation gate, not a database constraint. If a relational database is added,
  it owns control-plane state only: the run registry, manifests, tolerance
  policy, deficit ledger, failures, and job queue. This decision does not choose
  an analytics store. DuckDB over the Parquet files is the default for ad-hoc
  SQL because it adds no service. ClickHouse is not adopted, and would need its
  own decision backed by a measured scan workload.
- **Consequences:** `03` reads one program's graph by `program_id`, and the
  physical partition layout stays an artifact concern in `artifacts.md`. The
  graph artifact remains the single source of truth, so no schema is duplicated
  as DDL and the artifact has exactly one writer. A relational store cannot be
  introduced on the graph path without superseding this decision. The ClickHouse
  column type mapping in `graph-persistence.md` is a compatibility note for a
  hypothetical loader, not a deployment commitment.

## DS-40 — Go reads and writes Parquet with parquet-go

- **Status:** accepted (2026-11-20).
- **Context:** `DS-22` makes Go the default implementation language, and
  `graph-persistence.md` requires graph-local IDs to be the native Parquet UUID
  logical type, read and written directly. `02c` writes the three graph tables in
  Go and `03` reads them in Go, so the Parquet library decides whether that
  requirement is cheap or a trap. Two pure-Go libraries are viable. In
  `apache/arrow-go`, `parquet/pqarrow/schema.go` maps the Parquet UUID logical
  column type to the `arrow.uuid` extension only when that extension is registered, and
  otherwise falls back to `FixedSizeBinary(16)`; on write it maps
  `FIXED_SIZE_BINARY` to `FIXED_LEN_BYTE_ARRAY` with no logical type. The
  extension type exists in `arrow/extensions`, but nothing registers it, so the
  annotation is lost silently. `parquet-go` maps `uuid.UUID` from
  `github.com/google/uuid` to the UUID logical type with no tag and no
  registration. Both were measured on the 6.39M-relation table: materializing
  every row costs 4.96 s and 2.16 GB, streaming in batches and keeping one
  program costs 3.27 s and 218 MB.
- **Decision:** Go reads and writes Parquet with
  `github.com/parquet-go/parquet-go`, and carries graph-local IDs as `uuid.UUID`
  from `github.com/google/uuid`. `arrow-go` is not adopted. It returns only if a
  measured need for Arrow compute appears, and then the UUID extension must be
  registered and every UUID field typed as that extension. The
  standard-library `uuid` added in Go 1.27 is not a substitute: `parquet-go`
  maps only `github.com/google/uuid.UUID` to the Parquet UUID logical type, and
  the standard package has no name-based (v5) constructor for the deterministic
  `failure_id` in `failure-record.md`.
- **Consequences:** The Go schema is a struct with `parquet` tags, where `dict`,
  `optional`, `zstd`, and `list` express the encoding requirements in
  `graph-persistence.md`. Graph tables are read by streaming through
  `parquet.GenericReader` in batches; `parquet.ReadFile` materializes the whole
  table and is not used on them. A schema mismatch is an error at the boundary,
  which is where `graph_schema_version` is enforced.

## DS-41 — UUID columns are written by Go and never rewritten by Polars

- **Status:** accepted (2026-11-20), corrected (2026-11-20).
- **Context:** The graph artifact stores graph-local IDs as the native UUID
  logical type, and Python also reads these tables. The two Python readers behave
  differently. Polars has no UUID data type at all: `pola-rs/polars#7175` has been
  open since February 2023 and is labelled `needs decision` as of August 2026,
  and Polars 2.1.0 has no UUID type. Verified on Polars 1.41.0: a UUID column
  reads as `Binary`, and writing it back produces `optional binary` in the
  Parquet schema, so the write drops both the `FIXED_LEN_BYTE_ARRAY(16)` physical
  column type and the UUID logical type, with no error and no change to the values.
  PyArrow does not have this problem. `pq.read_table` returns
  `extension<arrow.uuid>` from a `parquet-go` file that carries no `ARROW:schema`
  metadata, so the Parquet logical type is sufficient. `pq.read_schema` dropped
  extension types on PyArrow 24.0.0 and earlier (`apache/arrow#48254`), which the
  project no longer runs: `pyproject.toml` requires `pyarrow>=25.0`, the release
  that fixed it.
- **Decision:** UUID columns are written by Go and read by Go. A Python stage
  reads them with PyArrow and gets `pa.uuid()`, from the schema or the table. No
  Python stage rewrites a graph table, and no Polars job is on the graph path.
- **Consequences:** `02b` may emit UUID columns from PyArrow and `02c` reads them
  unchanged. A Polars round-trip of a graph table is a defect even when the
  values are correct, because both the physical type and the logical type are
  lost. A test that compares values will not catch it; the check must compare the
  Parquet schema. The Polars limitation is upstream and tracked, not something
  the graph contract works around.

## DS-42 — The dataset prompt is the user message

- **Status:** accepted (2026-11-20).
- **Context:** The prompt could be delivered as a system prompt. Many training
  stacks strip or special-case the system role, and a dataset that ships its task
  as a system prompt trains an LLM model to treat a CAD-QA question as a standing
  instruction rather than a request. The dataset also should not own harness
  policy: retry rules, tool access, and answer extraction belong to whoever runs
  the LLM model.
- **Decision:** The release `prompt` column is the user message. The dataset
  supplies no system prompt. A harness may add its own, and the dataset card says
  that the dataset does not.
- **Consequences:** Training blindly on the prompt column uses the normal
  user-turn shape. A harness that adds a system prompt does not change the release
  row, so `prompt_sha256` still identifies the dataset content. The frame
  convention and the answer instruction stay inside the user message, because they
  are task context, not harness policy.

## DS-43 — The capability census is derived, not emitted

- **Status:** accepted (2026-11-20).
- **Context:** `DS-33` said `02c` emits a capability census as a by-product of
  graph construction. That implied an artifact, and left open whether it was a
  fourth graph table or a sidecar. The census is a pure function of the graph, so
  a stored copy can only be stale or redundant. The graph tables are per-entity
  and the census is per-program, so it also has no existing row to extend.
- **Decision:** The census is a typed function of the graph, derived on demand. It
  is not an artifact and has no schema version of its own. `03a` derives it for
  all active programs and stores the union per family in
  `TaskQuotaPlan.family_profiles`; `03b` derives it for the program it is
  constructing; `03c` reads `family_profiles`.
- **Consequences:** One fewer artifact, schema, and staleness rule, and no change
  to `io-contracts.md` or `artifacts.md`. The cost is one pass per graph batch plus a
  pass over the programs a slow-loop round adds. A replan derives nothing, because
  the graph batch has not changed and `family_profiles` is already in the plan.

## DS-44 — A run is incremental and resumable per unit

- **Status:** accepted (2026-11-21).
- **Context:** `05` validate and export release said atomic directory replacement
  was the run-level execution contract, but no such document existed.
  `graph-persistence.md` required the tolerance policy to live in the run
  manifest, and `failure-record.md` said the run manifest records versions, but
  `artifacts.md` had no run-manifest row. `02b` execute CadQuery defined a cache
  key without a cache location, a lookup rule, or a resume rule. The cost is not
  theoretical: with 1,500 active programs, 30 seconds per execution, and about
  20,000 relations per program, an interrupted run without resume recomputes
  hours of work. The alternative was a per-unit JSON checkpoint, but `DS-39`
  measured JSON text at 41x the Parquet size and 57x the read time for the CAD
  graph. A JSON progress file per unit would repeat that mistake at a smaller
  scale.
- **Decision:** A run is one durable directory with a `run.json` manifest that
  records `run_id`, generator and component versions, policy file hashes, and
  the run-level `TolerancePolicy`. New runs are allocated as
  `<runs_root>/run<NNNN>`, zero-padded to four digits; the number is local and
  excluded from `run_id`. A rerun with the same `run_id` reuses the lowest
  matching directory unless `--new-run` is given. Each pipeline stage commits
  immutable Parquet parts as units complete; the part is the unit's completion
  marker, and resume reads the committed parts and skips completed units. A unit
  is flushed when it completes, or at most every 30 seconds, asynchronously
  through one writer per pipeline stage. A completed unit is not recomputed
  unless it is forced. A forced recompute must be byte-identical; a difference
  is a defect. Bulk state is Parquet; JSON is limited to the run manifest,
  pipeline stage completion markers, the deficit ledger, and other small or rare
  control documents. The contract also owns the shared cache, the run lock, the
  command-line interface, the exit codes, and partial-run cleanup.
- **Consequences:** A partial run is readable and resumable; a crash loses only
  the units still in the writer queue. A changed input, component version, or
  policy is a new run directory, not an edit. A corrupt part is an integrity
  error with an explicit `--force` recovery, not a silent recompute. Downstream
  identity includes the upstream part hashes, so a changed program invalidates
  only that program's downstream units. The run manifest and pipeline stage completion
  markers are artifacts in `artifacts.md`; the full contract is
  `implementation/run-contract.md`.

## DS-45 — The thesis release ladder is 1–10; 6–10 is P1 and gated

- **Status:** accepted (2026-11-21).
- **Context:** The pre-rebuild ladder was `{2,3,4,5}` because synthesis floored at
  2. The paper promises up to ten hops, and the owner wants the thesis release
  to reach ten. The dataset PRD already makes 1-step the warmup and drops
  0-step. A flat P2 for 6–10 would make the paper's 1–10 claim false.
- **Decision:** The thesis release targets task reasoning step counts 1 through
  10. Steps 1–5 are P0. Steps 6–10 are P1, not P2: they are part of the thesis
  release only when a synthesis pilot and a manual review pass the 6–10 release gate in
  `requirements/PRD.md` section 6.1. If the release gate fails, the release is 1–5 and
  every result names that range; the paper must not claim 1–10. There is no
  0-step task.
- **Consequences:** `balance.yaml` carries a 1–10 mix with a 6–10 tail and a
  P0-only fallback mix. The training docs' floor at hop 2 and the `{2,3,4,5}`
  references are superseded. The test split must report per-tier counts at
  6–10. The 6–10 cells are small, so per-tier significance is reported only
  when the cell is large enough; otherwise the paper reports the pooled 6–10
  slice. The general review gate (R-17) covers every tier 1–10; the 6–10
  sample is at least 30 tasks per tier, or every task if fewer.

## DS-46 — Go reads YAML policy files with gopkg.in/yaml.v3

- **Status:** accepted (2026-11-21).
- **Context:** `balance.yaml`, `checks.yaml`, and `tolerance.yaml` are YAML and
  are read by Go pipeline stages. Go has no standard-library YAML decoder, and
  `python-and-golang.md` requires a decision before adding a Go dependency.
- **Decision:** Go reads and validates YAML policy files with
  `gopkg.in/yaml.v3`. It is the only YAML library in the Go module. A loader
  rejects unknown fields, then validates the typed policy.
- **Consequences:** A policy file with an unknown key is a load error, not a
  silently ignored setting. Python keeps `PyYAML` for `prompts.yaml`; the two
  languages do not share a YAML loader.

## DS-47 — Go uses the standard CLI and a strict lint stack

- **Status:** accepted (2026-11-20; renumbered 2026-11-21 when `main` claimed
  `DS-44` and `DS-45`).
- **Context:** `DS-22` makes Go the default and `stacks.md` declares its
  libraries. The generator has one command with one subcommand per pipeline stage
  and a few global flags; it does not need generated shell completion or a nested
  command tree. YAML decoding is decided separately in `DS-46`, which `main`
  accepted with the first Go package, so this decision does not restate it. The
  owner prefers the strictest linters that are fast and can rewrite files, as
  `ruff` and `rumdl` do for Python and Markdown.
- **Decision:** The Go module is `github.com/MRiabov/CAD-QA/generator` on Go
  1.27.4, the latest stable release. The CLI uses the standard `flag` package with
  one `flag.FlagSet` per pipeline stage and no third-party CLI framework.
  Formatting is `gofumpt` and `goimports`; linting and static analysis are
  `golangci-lint`, configured with `staticcheck`, `govet`, `errcheck`, `revive`,
  `gocritic`, `errorlint`, `nilerr`, `exhaustive`, `prealloc`, `unparam`,
  `unused`, `ineffassign`, `misspell`, `forbidigo`, and `depguard`.
- **Consequences:** A CLI framework returns only if nested subcommands or
  generated completion become a real requirement. `go vet` runs through
  `golangci-lint`, so a separate vet invocation is optional; `go test` also runs
  the `stdversion` vet check on Go 1.27, so a standard-library symbol newer than
  the `go` directive fails both gates. Tool versions are pinned with `go.mod`
  `tool` directives. The Go hooks are declared in
  `stacks.md` but not yet wired in `.pre-commit-config.yaml`; that is a recorded
  gap, not a decision.

## DS-48 — Python type checking uses Pyrefly

- **Status:** accepted (2026-11-20; renumbered 2026-11-21 when `main` claimed
  `DS-44` and `DS-45`).
- **Context:** `pyproject.toml` declared mypy, but no mypy configuration or hook
  existed, and the owner prefers the fast Rust type checkers. `ty` is still beta
  and uses `0.0.x` versioning; `pyrefly` is stable at 1.x, understands Pydantic,
  and ships an official pre-commit hook. Pyrefly recommends `preset = "strict"`
  for most projects. `preset = "all"` enables every error kind, including new and
  low-signal checks, and is an audit mode rather than a default; on the old tree
  it reports 7,750 findings against 379 under `strict`. The old tree is
  superseded, but that is not a reason to adopt an unrecommended preset.
- **Decision:** Python type checking uses `pyrefly` with `preset = "strict"` and
  `python-version = "3.12"` in `pyproject.toml`. Mypy is removed from the dev
  dependencies. The pre-commit hook is installed on the manual stage until the
  old tree is removed; removing its `stages` line promotes it to a blocking
  hook.
- **Consequences:** `uv run pyrefly check` is the static-check command. New
  Python code is checked against the strict preset when the hook runs, but a
  finding does not block a commit until the manual stage is promoted.
  `preset = "all"` remains available as a one-off audit, not the project setting.
  `ty` returns if Pyrefly's diagnostics or performance become a measured
  problem.

## DS-49 — CadQuery execution amortizes the library import

- **Status:** accepted (2026-11-21).
- **Context:** `runtime.md` required a fresh child Python process per program, and
  the worker protocol started a Python process per request. Measured on the
  reference host, `import cadquery` costs 2.1–2.8 s and 451 MiB of resident
  memory. At 1,500 active programs that is 50–70 minutes of CPU spent before any
  geometry is evaluated, 7–9% of every 30-second execution budget, and a resident
  set that caps `--jobs` on a memory-limited host. Process isolation is the
  requirement; a fresh interpreter is not.
- **Decision:** `02b` execute CadQuery runs in a long-lived worker that imports
  CadQuery and OCP once, and forks a fresh child process per program. The child
  is a fresh address space, so no CadQuery or OCP state crosses programs. The
  30-second limit starts at the child's ready signal, not at process creation.
  The Go orchestrator runs a bounded worker pool per pipeline stage, not one
  process per request. `execution_environment` records only the environment class
  (`os_arch`, limits, preload setting, worker request limit), never host identity.
- **Consequences:** `02b` pays the import once per worker instead of once per
  program. A worker is replaced after a crash or after its request limit, so a
  leak is bounded. A cross-machine resume is a cache hit when the environment
  class matches. The import cost and the preloaded resident set are measured once
  per implementation scope and recorded with the run, not recomputed per program.

## DS-50 — Unit identity is content; the plan is a work list

- **Status:** accepted (2026-11-21).
- **Context:** `run-contract.md` put the `03a` plan part hash in every `03b` unit
  identity and the `03b` part hash in every `04` unit identity. A plan revision
  therefore changed every identity, while `03a`/`03b` promised that accepted
  definitions survive a replan and `03b` skipped their `task_id`s. The two rules
  contradicted each other: one rebuilt all 10,000 definitions and prompts on
  every fast-loop replan, the other appended rows under a stale identity. The
  same mistake appeared at smaller scale in `01c`/`01d`, where a batch part hash
  named a per-program identity, and in one-row Parquet parts for cheap
  per-program units.
- **Decision:** A unit identity covers the inputs that determine its rows.
  Scheduling inputs — plan targets, plan version, deficit ledger, family
  assignment — are not identity. For `03b` and `04` the unit is a task and
  identity is row-level; a later revision appends a part
  (`<program_sha256>-<sequence>.parquet`) and resume deduplicates by `task_id`
  with a matching content hash. `01d` is keyed by `raw_program_sha256`, `02a` by
  `program_sha256`, and neither by a batch part hash. `01d` and `02a` batch many
  programs per part because a unit is milliseconds; `02b` and `02c` keep one part
  per program because a unit is an execution.
- **Consequences:** A replan changes the work list and nothing else, so the fast
  loop is actually cheap. An appended row never rewrites an accepted one. A
  changed graph invalidates that program's downstream units, not every unit of
  `03b`. A batched part can lose at most a batch of cheap work on a crash. The
  cost is a sequence suffix in the part name and a row-level dedupe step on
  resume.

## DS-51 — One construction pass per program, budgeted per family and step

- **Status:** accepted (2026-11-21).
- **Context:** `03a` budgeted `ceil(target_count * 1.5)` construction attempts for
  every quota target, while one accepted definition fills several targets. The
  budgets therefore summed to roughly 1.2–1.5 × 10^5 attempts for a 10^4-task
  release. `03-task-generation.md` also made construction parallel per quota
  target, which invites a graph re-read per target, and `03a` and `03b` each
  derived the capability census. The cover search had no bound beyond
  `max_state_entities`, which bounds one input, not the search.
- **Decision:** Construction is one pass per program and plan revision: load the
  graph and census once and fill every target assigned to the program at that
  step count. The attempt budget is per `(family, task reasoning step count)` and
  is `ceil(family_task_reasoning_step_quota * construction_attempt_multiplier)`;
  one acceptance decrements every target it fills. The plan carries the
  per-program census (`program_census`) and `03b` reads it. The cover search runs
  under count-based scope constants (`max_construction_candidates`,
  `max_construction_facts`, `max_cover_expansions`, `max_validity_rechecks`), and
  exhaustion is a `construction_deficit` with detail `construction_budget`. The
  constants are part of `constructor_version`.
- **Consequences:** A 10,000-task release budgets on the order of 20,000–30,000
  attempts instead of 1.2 × 10^5. Each program graph is read once per revision.
  The census is derived once per graph version. The search has a deterministic
  bound, so a pathological graph becomes a recorded deficit rather than an
  unbounded run. A budget change is a new `constructor_version`, so it cannot
  silently change an accepted definition.

## DS-52 — Pair rows are state-scoped

- **Status:** accepted (2026-11-21).
- **Context:** The pair emission rule made pair rows linear in the entity count
  per named endpoint, but it applied to every solid state. `DS-34` binds a P0
  task to the final state and a P1 task to one named intermediate state, so pair
  rows for the other states were written, sorted, hashed, read by `03`, and never
  used. In the measured 1,000-program artifact, 82% of 20.1M relations were
  pairwise comparisons and there were 2,310 solid states, so the unused share is
  large.
- **Decision:** Pair relations and pair measurements are emitted only for the
  solid states the release implementation scope can bind: the final state in P0,
  the final and one named intermediate state in P1, and both states of a declared
  pair in P2. Per-entity measurements, containment relations, and effect
  measurements stay total over every state.
- **Consequences:** The dominant relation mass drops by roughly the number of
  unbindable states per program, and `02c` writes and `03` reads less.
  `implementation_scope` enters the `02c` identity so a cached graph cannot be
  reused across scopes with a different row set. A P1 or P2 release that binds
  more states emits more pair rows; that is a scope change, not a schema change.

## DS-53 — Answer columns are typed; the release carries a bounded evidence summary

- **Status:** accepted (2026-11-21).
- **Context:** The release stored `gold_answer_json`, `tolerance_json`, and
  `answer_evidence_json` as canonical JSON text, and `05` parsed them per row.
  `DS-23` bans per-row JSON on bulk paths, and `DS-39` measured JSON text at 41x
  the Parquet size and 57x the read time. `answer_evidence` also carried the full
  answer-equivalent set, which can hold one entry per candidate (up to
  `max_state_entities`), so "small enough to keep with the task" was an
  assumption, not a bound.
- **Decision:** The answer columns are typed Parquet structs: `AnswerValue` (a
  tagged union with canonical decimal text for numbers), `Tolerance`, and
  `AnswerEvidence`. The release carries the answer-equivalent count and the
  shared answer, not the full set; the full set stays in the task definition.
  `structured` is the only JSON text, for the CadQuery workplane-state answer, and
  `answer_schema_version` versions its shape.
- **Consequences:** `05` validates typed fields instead of parsing JSON, and a
  release row cannot grow with the candidate count. `04` copies typed values and
  never serializes an answer. The canonical text for numbers is unchanged, so Go
  and Python still agree byte for byte. A consumer that read the old JSON columns
  is unaffected because no release has been published.

## DS-54 — 02b emits the extraction hashes; 02c copies them

- **Status:** accepted (2026-11-21).
- **Context:** `graph-persistence.md` let `02c` recompute `fingerprint_sha256`
  from the canonical entity table and `runtime_extraction_result_sha256` over the
  whole runtime result. `02b` had already derived both: `entity_id` is a hash of
  the fingerprint, and the success result carries
  `runtime_extraction_result_sha256`. Recomputing put a second implementation of
  the same canonical hash in Go, and the contract made a mismatch a graph
  rejection.
- **Decision:** `02b` emits `fingerprint_sha256` with `entity_id` and carries
  `runtime_extraction_result_sha256`; `02c` copies both. `02c` recomputes them
  only under `--force`, where a mismatch rejects the graph.
- **Consequences:** The normal path has one implementation of each hash, in the
  process that has the kernel values. A determinism bug is caught by the force
  check rather than by two implementations that can drift.

## DS-55 — The run journal is fixed shards, not one file per unit or per stage

- **Status:** accepted (2026-11-21).
- **Context:** The run contract wrote one Parquet part per unit. For 1,500
  programs that is 1,500 files per program stage and 4,500 files for the
  three-table graph, about 9,000 files per run, each with footer and page
  overhead. The graph is 163 KB per program, so a per-program part is mostly
  metadata. One file per stage is not an option either: Parquet is immutable, a
  run is 12.5 hours of execution, and rewriting a 245 MB graph file on every
  flush is O(n²). Batching by flush time is also wrong: the part boundaries would
  depend on machine speed, which contradicts the byte-identical rerun rule.
- **Decision:** A part is a fixed shard: a unit belongs to
  `sha256(pass_key) mod journal_shard_count` (default 16), so membership is a
  function of the key and the run-level count. A shard is written as an
  incomplete part at the flush interval and replaced by the complete shard. `02b`
  keeps one unit per part because a unit is 30 seconds. `01d`, `02a`, `02c`,
  `03b`, and `04` shard. A shard's rows carry the unit key and content identity,
  and downstream identity uses the unit identity, never the shard hash.
- **Consequences:** A 1,500-program run writes about 16 parts per stage instead of
  1,500, and the graph writes 16 directories instead of 4,500 files. A crash
  loses at most the unflushed rows of a shard; `02b` still loses at most one
  execution. A shard rewrite on recompute is 16 MB for the graph, not 245 MB. The
  shard count is part of `run_id`, so a different layout is a new run.

## DS-56 — A unit failure never fails its shard

- **Status:** accepted (2026-11-21).
- **Context:** Sharding introduced a container that holds many units. If the
  writer treated the shard as a transaction, one rejected program or task would
  discard the successful units in the shard, and a single bad program could block
  a hundred others. The failure record already makes a rejection data, but the
  persistence rule did not say what happens to the siblings.
- **Decision:** A shard is a container, not a transaction. A rejected unit writes
  a failure row and no success row; the writer continues and commits the shard. A
  unit that crashes a worker becomes a failure tombstone; the worker is replaced.
  A shard with no successful rows is not written, and its failure rows are the
  completion marker. Resume reads success and failure parts together, so a failed
  unit is not retried and a successful sibling is not recomputed. A corrupt shard
  is the only failure that spans units, and its blast radius is that shard.
- **Consequences:** One program cannot fail its shard, its batch, or the run. The
  failure partition is the only per-unit negative state, and it is already the
  R-19 record. A corrupt shard is an integrity error with `--force` recovery, not
  a data condition.
