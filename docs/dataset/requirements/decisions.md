# Dataset requirements decisions

**Status:** active, 2026-11-21.

Requirements-level decisions for the CAD-QA dataset, in ADR format
([`../../docs-conventions.md`](../../docs-conventions.md)). A decision here states a
property of the dataset or of the task unit, without reference to which pipeline stage
computes it. Implementation decisions that span pipeline stages are in
[`../implementation/decisions.md`](../implementation/decisions.md); decisions scoped to
one pipeline stage or module are in that step doc's `## Local decisions` or module `decisions.md`.
The decision prefix is `DS-REQ-`.

The entries are grouped: the charter, the task unit, the answer, coverage and balance,
the release, and the specification. The grouping is editorial; the numbers are the
citation keys and never change meaning.

---

## DS-REQ-01 — Rebuild the dataset from first principles

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

## DS-REQ-02 — A task and a question are different

- **Status:** accepted (2026-10-21).
- **Context:** Earlier documentation used "question" both for the whole dataset
  instance and for the interrogative sentence inside the prompt.
- **Decision:** A **task** is one dataset instance: a CadQuery program, a task
  target, a set of task clues, and one answer. A **question** is only the
  interrogative sentence in the prompt. The prompt also contains the program
  text, the task clues, optional choices, and the answer instruction.
- **Consequences:** Dataset code and documentation use "task" for the instance.
  Prompt documentation uses "question" only for the sentence.

## DS-REQ-03 — Compose tasks; do not enumerate task families, task types, or task patterns

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

## DS-REQ-04 — A clue is one narrowing statement, described by clue type and clue operand form

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

## DS-REQ-05 — Task text does not use variable names

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

## DS-REQ-06 — Question names the category; task clues are numbered

- **Status:** accepted (2026-10-21).
- **Context:** Prompt-content Q1 and Q2 were open. The question and the clue
  list need a fixed shape before prompt rendering can be specified.
- **Decision:** The question always names the task target category and the
  answer meaning. Task clues are a numbered list in reasoning order. The number
  is presentation, not a task reasoning step count.
- **Consequences:** The prompt renderer has one layout. The question does not
  narrow candidates; every task clue still maps to one task clue step.

---

## DS-REQ-07 — Comparison clues may name an entity or reuse one selected earlier

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

## DS-REQ-08 — Tasks refer to the final solid state in P0

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

## DS-REQ-09 — Cross-state `same_as` is P2

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

## DS-REQ-10 — Pair rows are state-scoped

- **Status:** accepted (2026-11-21).
- **Context:** The pair emission rule made pair rows linear in the entity count
  per named endpoint, but it applied to every solid state. `DS-REQ-08` binds a P0
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

## DS-REQ-11 — Drop 0-step tasks

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

## DS-REQ-12 — Answer meaning and answer format are separate

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

## DS-REQ-13 — Answers come from CadQuery or an exact rule, never an LLM

- **Status:** accepted (2026-10-21).
- **Context:** The dataset must be objectively checkable, and an LLM in the
  trusted path would make the correct answer unauditable.
- **Decision:** Every answer is produced by running the CadQuery program or by an
  exact derivation from the program and its geometry, and is recorded with
  answer evidence. No LLM writes or judges an answer.
- **Consequences:** A guessed or approximate value is not answer evidence. A task
  whose answer cannot be produced with answer evidence is rejected.

## DS-REQ-14 — Numeric answers use 4 significant figures

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

## DS-REQ-15 — Answer uniqueness compares an answer-equivalent set

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

## DS-REQ-16 — Task reasoning step count is the only measure

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

## DS-REQ-17 — Check coverage and balance at every task reasoning step count

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

## DS-REQ-18 — Clue operand form is a coverage dimension in P0

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

## DS-REQ-19 — Clue operand form is reported as a descriptive breakdown, not a difficulty axis

- **Status:** accepted (2026-11-20).
- **Context:** `DS-REQ-16` makes task reasoning step count the only measure of task
  difficulty, and `DS-REQ-18` makes clue operand form a P0 coverage dimension.
  Coverage alone does not show how the forms combine inside one task, and the
  per-task clue operand form profile is already part of the definition.
- **Decision:** Every task definition records `clue_operand_form_profile`, the
  ordered clue type and clue operand form of each clue. The release reports
  aggregate coverage per task reasoning step count, and the per-task clue
  operand form profile stays available. Clue operand form is descriptive; it is
  not a difficulty label, and `DS-REQ-16` is unchanged.
- **Consequences:** The release table carries `clue_operand_form_profile`, and `05`
  checks coverage per clue operand form. The recorded entry keeps the clue type, so a
  `(clue_type, clue_operand_form)` breakdown is derivable without a second support
  table. Benchmark results may name the step counts and clue operand forms they
  cover, without ranking tasks by clue operand form.

## DS-REQ-20 — A release dataset is one table

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

## DS-REQ-21 — No separate answer-key container

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

## DS-REQ-22 — Do not use public/private for dataset parts

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

## DS-REQ-23 — Answer columns are typed; the release carries a bounded evidence summary

- **Status:** accepted (2026-11-21).
- **Context:** The release stored `gold_answer_json`, `tolerance_json`, and
  `answer_evidence_json` as canonical JSON text, and `05` parsed them per row.
  `DS-ADR-03` bans per-row JSON on bulk paths, and `DS-ADR-04` measured JSON text at 41x
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

## DS-REQ-24 — The dataset prompt is the user message

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

## DS-REQ-25 — Plausible near-miss distractors are P2

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

## DS-REQ-26 — The thesis release ladder is 1–10; 6–10 is P1 and gated

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

## DS-REQ-27 — Warmup and splits

- **Status:** accepted (2026-10-21); corrected (2026-10-21).
- **Context:** A small LLM model needs a lower-step entry point, and evaluation
  must not see training programs.
- **Decision:** The warmup subset is the 1-step bucket: 5% of tasks, drawn from
  the same program pool and labeled inside the dataset.
  Training, validation, and test are split by CADEvolve program family at
  approximately 70/15/15; the same family never appears in more than one part.
- **Consequences:** Warmup tasks may be used for training. The test part is never
  trained on, tuned on, or used to choose an LLM model. `ETL-3` defines the
  program-family identity.

## DS-REQ-28 — Task definitions and task quota planning are specified together

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
