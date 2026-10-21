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
  answer-key layout. The old release may support a first training cycle, but it
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

## DS-05 — Task reasoning step count is the difficulty measure

- **Status:** accepted (2026-10-21).
- **Context:** The previous difficulty targets were mathematically inconsistent,
  and "difficulty level" is ambiguous about what is being counted.
- **Decision:** A **task reasoning step** is either a task clue step or a task
  answer step. **Task reasoning step count** is the number of task reasoning steps.
  The target mix is: 0–1 steps 5%, 2 steps 15%, 3 steps 40%, 4 steps 25%, and 5
  steps 15%. At least 80% of the release needs three or more task reasoning
  steps. Steps 0 and 1 form the labeled warmup subset.
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
  multiple choice, variable name, number, integer, yes or no, 3D coordinate,
  bounding box, or structured object.
- **Consequences:** A position is returned as a 3D coordinate; an extent is
  returned as a bounding box. The technical specification needs a compatibility
  table from answer meaning to valid answer formats.

## DS-07 — Answers come from CadQuery or an exact rule, never an LLM

- **Status:** accepted (2026-10-21).
- **Context:** The dataset must be objectively checkable, and an LLM in the
  trusted path would make the answer key unauditable.
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
- **Context:** A small LLM model needs an easier entry point, and evaluation
  must not see training programs.
- **Decision:** The warmup subset contains 500 to 1,000 tasks with 0 or 1 task
  reasoning steps, drawn from the same programs and labeled inside the dataset.
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

## Open questions

- **Q1.** Is the release a selected subset of the valid-task universe, or must it
  contain every valid task? The answer changes the selection algorithm and the
  meaning of "required enumeration."
- **Q2.** Is a chain clue one task reasoning step or one step per relation? Is a
  clue that combines a relation and a property one condition or two? These
  determine task reasoning step count.
- **Q3.** Is the conditional release share computed from the valid-task universe,
  or allocated from the global targets before selection? The current definition
  depends on the release, which is what selection produces.
- **Q4.** Which answer formats are valid for each answer meaning, and how are
  multiple-choice distractors selected deterministically?
- **Q5.** When is a task a duplicate of another task? The canonical task identity
  is not yet fixed.
- **Q6.** What defines a 0-step task? Two definitions conflict:
  - **Strict step count:** 0 steps means no task clue step and no task answer
    step; the answer is a named object or a value directly visible in the
    program. A property filter such as "which operation has a `faces()`
    CadQuery selector" is one task clue step, so it is 1 step.
  - **Syntax-only evidence:** 0 steps means any task answerable from Python
    syntax alone, including a filter over entities. That would make "which
    operation has a `faces()` CadQuery selector" 0 steps, but it classifies by
    evidence origin rather than by reasoning steps.

  "Which box has a length of 10" is 0 steps only if 10 is a literal argument
  read from the syntax; if the length is measured from geometry, it is a
  geometry step. The specification must choose. The current leaning is to keep
  the step count as the number of atomic task reasoning steps: syntax-only
  filters are 1-step syntax tasks, and 0-step is a direct named lookup.
