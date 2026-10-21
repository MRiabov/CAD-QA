# Dataset decisions

**Status:** active, 2026-10-21.

Feature-wide decisions for the CAD-QA dataset, in ADR format
(`../docs-conventions.md`). Decisions scoped to one pipeline stage belong in
that pipeline stage's `Local decisions` section. The decision prefix is `DS-`.

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
  ordered task clues, the answer operation, the answer format, and the answer
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
- **Consequences:** The release needs a task reasoning step support table. The
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

- **Status:** accepted (2026-10-21).
- **Context:** A small LLM model needs a lower-step entry point, and evaluation
  must not see training programs.
- **Decision:** The warmup subset contains 500 to 1,000 tasks with one task
  reasoning step, drawn from the same programs and labeled inside the dataset.
  Training, validation, and test are split by CadQuery program at approximately
  70/15/15; the same program never appears in more than one part.
- **Consequences:** Warmup tasks may be used for training. The test part is never
  trained on, tuned on, or used to choose an LLM model.

## DS-10 — The next technical deliverable is a task enumeration contract

- **Status:** accepted direction (2026-10-21); details open.
- **Context:** The dimensions and balance rules do not define the set of tasks.
  "Enumerate all tasks" is ambiguous until the task identity, the valid-task
  universe, and the selection of the release are defined.
- **Decision:** The next specification defines: the task tuple and canonical
  identity; the valid-task universe versus the release subset; the validity
  oracle; exact task reasoning step count accounting; the typed clue predicate
  schema; the answer meaning to answer format map; support as existence in the universe; the
  release selection algorithm; and deterministic ordering, deduplication,
  serialization, and split assignment.
- **Consequences:** Implementation should not start from the current
  conceptual docs alone. `task-structure.md` and this file define the target;
  the enumeration contract defines the implementable space.

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
  longer defines or generates 0-step tasks. The warmup subset is still 500 to
  1,000 tasks at the target release size.

---

## DS-12 — No separate answer-key container

- **Status:** accepted (2026-10-21).
- **Context:** "Answer key" is an assessment-artifact term. It entered the PRD
  as a file-layout concept before the dataset data model existed, which implied a
  separate container that the product does not need.
- **Decision:** The dataset has tasks and their correct answers. The correct
  answer never appears in the task file. There is no separate answer-key object
  at the PRD level. The technical specification may
  choose how answer fields are stored.
- **Consequences:** Product and terminology text say "correct answer" or "gold
  answer," not "answer key." A human-readable answer listing, if needed, is a
  release artifact chosen by the technical specification, not a dataset concept.

---

## DS-13 — Do not use public/private for dataset parts

- **Status:** accepted (2026-10-21).
- **Context:** "Public" and "private" are access scopes. Using them for dataset
  columns conflates visibility with permission and makes the data model sound
  like an access-control model.
- **Decision:** Use **prompt** or **task file** for what the LLM model sees.
  Use **answer** or **answer data** for the gold answer and scoring material.
  Access control, if any, is a separate concern.
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

## Open questions

- **Q1.** Is the release a selected subset of the valid-task universe, or must
  it contain every valid task?
  - **Option A — release = universe.** Every valid task is released. Simple,
    but the size is uncontrolled and balance may be impossible.
  - **Option B — release ⊆ universe.** The universe is every valid task; the
    release is a deterministic selection that meets the size and balance
    targets.
  - **Option C — exhaustive for small programs, selected for large programs.**
    Keeps small programs complete but needs two rules.
  - **Recommendation:** B. Example: a program produces 120,000 valid tasks; the
    release takes 10,000 selected to meet the step-count and dimension quotas.
    "Required enumeration" means the required cells, not every tuple.

- **Q2.** Is a chain clue one task reasoning step or one step per relation? Is a
  clue that combines a relation and a property one condition or two?
  - **Option A — chain is one step; a compound sentence is one clue.** The
    current text allows “the face adjacent to X whose area is larger than X” as
    one clue.
  - **Option B — atomic predicates.** Each relation or property is one clue and
    one task reasoning step. The compound sentence becomes two clues; the chain
    becomes one clue per relation.
  - **Option C — hybrid.** Chains count per relation, but a relation plus a
    property in one sentence counts as one clue.
  - **Recommendation:** B. Example: “the face adjacent to X whose area is
    larger than X” is two steps; `A -> B -> C` is two steps. Split the public
    clues accordingly. This makes the step count auditable.

- **Q3.** Is the conditional release share computed from the valid-task universe,
  or allocated from the global targets before selection?
  - **Option A — universe share.** Compute each value's share in the universe
    among the values supported at that step count, then require the release to
    approximate it.
  - **Option B — allocate quotas from the global targets, then fill from the
    universe.** Choose the target mix first, allocate counts per step count and
    dimension, then select tasks that fill the quotas.
  - **Option C — select, compute, repair.** Select a draft release, measure it,
    and move tasks until the targets hold.
  - **Recommendation:** B. Example: at step count 2, supported answer meanings
    `A`, `B`, and `C` have target shares 20%, 30%, and 50%; allocate the step-2
    quota in those proportions, fill from the universe, and report a conflict if
    the universe cannot fill a cell. This avoids the circular definition.

- **Q4.** Which answer formats are valid for each answer meaning, and how are
  multiple-choice distractors selected deterministically?
  - **Option A — one answer format per answer meaning.** Simple, but identity
    would be limited to multiple choice.
  - **Option B — a compatibility table.** Each answer meaning lists its allowed
    answer formats.
  - **Option C — the generator chooses any format.** Flexible, but hard to
    audit.
  - **Recommendation:** B. Example mapping: identity -> multiple choice;
    volume, area, length, distance, angle -> number; count or rank -> integer; membership or validity -> yes or no;
    position -> 3D coordinate; extent -> bounding box; CadQuery workplane state
    -> structured object; material change -> number; topology change ->
    structured object. Distractors are real graph candidates from the same
    target category, unique, non-leaking, deterministically ordered; if fewer
    than five exist, reject the task.

- **Q5.** When is a task a duplicate of another task?
  - **Option A — canonical tuple.**
    `(program, target entity, clue sequence, answer operation, answer format)`.
  - **Option B — rendered prompt text.** Two tasks with the same prompt are
    duplicates.
  - **Option C — answer value.** Two tasks with the same answer are duplicates.
  - **Recommendation:** A, with canonical clue order. Example: the same target,
    clues, and answer but multiple choice vs number are two tasks. The same
    tuple rendered twice is one task. The same prompt text with two different
    answers is an ambiguity defect, not two tasks.
