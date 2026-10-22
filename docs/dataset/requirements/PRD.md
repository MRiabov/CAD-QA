# PRD — CAD-QA dataset

**Status:** draft for owner review, 2026-10-21.

**What this document is.** This is the product requirements document for the
CAD-QA dataset. It describes what a user gets from training and evaluating on
the dataset. It does not describe how the dataset is produced; that belongs in
the technical specification.

**Relation to the project PRD.** [`../../PRD.md`](../../PRD.md) remains the authority
for the research questions, hypotheses, and evaluation goals. This document
defines the dataset those goals need. It does not change the research goals.

**Supersedes.** All previous dataset-generation specifications. The old
dataset documentation, answer-format notes, decisions, and issue register are
archived at `docs/_archive/dataset-pre-rebuild-2026-10-21/` and are history,
not requirements.

---

## 1. What the user gets

The user gets a training dataset and a separate evaluation benchmark for LLMs
that read CadQuery programs and reason about the three-dimensional shapes those
programs produce.

Training on the dataset should make an LLM model better at:

- reading a CadQuery program and predicting what shape it builds;
- finding the feature, face, edge, vertex, CadQuery profile, CadQuery workplane, path, or region a task asks about;
- answering quantitative questions about volume, area, length, distance,
  angle, bounding box, centroid, and counts;
- reasoning about relationships such as adjacent, contained, parallel,
  perpendicular, closer, farther, before, and after;
- reasoning about what an operation changed, including material added, material
  removed, volume change, and topology change;
- following several task clues in order until only one answer remains;
- answering without access to CadQuery, OpenCascade, or any other CAD kernel
  (P0);
- as a P2 goal, answering with access to CadQuery as an upper-bound setting.

The user also gets:

- a held-out benchmark for comparing LLM models fairly;
- a labeled warmup subset of lower-step tasks for teaching an LLM model the
  task format before the higher-step tasks;
- training, validation, and test sets that do not overlap;
- a dataset card that explains what the dataset contains and what it does not;
- enough documentation to reproduce and review the dataset release.

### Priorities

The project uses three priorities:

| Priority | Meaning for the dataset |
|---|---|
| **P0** | Required for the thesis. Without it, the dataset cannot support the primary no-kernel training and evaluation claim. |
| **P1** | Important for the thesis. It strengthens the result or its credibility but does not block the first training cycle. |
| **P2** | Venue extra. It may never execute and must not delay P0 or P1 work. |

Requirements below are P0 unless the requirement ID is followed by a
priority.

Priority also applies to these generation inputs: task target categories,
clue types, answer meanings, answer formats, graph entities, relations, and
measurements. It records the order in which those inputs are implemented. It is
not a task label: a task is never P0, P1, or P2, and no release column records an
implementation priority. The authoritative tables are in
[`task-structure.md`](task-structure.md) and
[`graph-content.md`](graph-content.md).

The first benchmark dataset release implements the P0 requirements and input
values. Later releases add P1 and P2 values. Coverage and balance are checked
against the values implemented by that release; a value deferred to a later
implementation scope is not a gap in the current release.

---

## 2. Who it is for

| User | What they need |
|---|---|
| Researcher or trainer | A dataset that teaches CAD program comprehension and geometry reasoning, with clear correct answers. |
| Evaluator | A held-out benchmark with several task reasoning step counts and a fair way to compare models. |
| Reviewer | Tasks a careful human can read and check, plus documented correct answers. |
| Dataset maintainer | A dataset that can be regenerated, extended with new tasks, clue types, or answer meanings, and reviewed without redoing everything. |

---

## 3. What is in the dataset

The dataset contains:

- a curated collection of CadQuery programs from the CADEvolve dataset;
- tasks about those programs;
- one correct answer for each task;
- enough recorded answer evidence to show why the answer is correct;
- training, validation, and test sets;
- a labeled warmup subset;
- a dataset card and evaluation material.

Each task shows the CadQuery program and asks for one answer. The correct
answer is never part of the prompt.

In this document, a CAD model means one CadQuery program. Two tasks
share a CAD model when they come from the same program.

A **task** is one dataset instance: a CadQuery program, a task target, a set of
task clues, and one answer. A **question** is only the interrogative sentence in
the prompt; it is not the whole task.

A task is built from task clues: conditions the answer must satisfy. Task clues are
written in plain language, and their variety is a requirement in its own right.

The structure of a task is defined in [`task-structure.md`](task-structure.md).
The content of the prompt is defined in [`prompt-content.md`](prompt-content.md).
The CAD graph the tasks rely on is defined in [`graph-content.md`](graph-content.md).
The proposed vocabulary is in [`terminology.md`](terminology.md).
The consumer contract for the release dataset is in
[`release-dataset-contract.md`](release-dataset-contract.md).

---

## 4. Task structure

A task is not one of a flat list of labels. It is a combination of five
separate dimensions:

- the **task target** the task asks about;
- the **task clues** the answer must satisfy;
- the **answer format** the LLM model must return;
- the **answer meaning** the answer is about;
- the **task reasoning step count** the task requires.

The previous flat list mixed these dimensions. For example, "direct lookup"
described a low task reasoning step count, "give a coordinate" described an answer format, and "measure a
distance" described a measurement. Those are not peers.

The full structure, including task target categories, task clue types, answer
meanings, answer formats, task reasoning step count rules, and the precise description of a task, is in
[`task-structure.md`](task-structure.md).

A task is described by its task target, task clues, answer format, answer
meaning, and task reasoning step count. The dataset does not use task families,
task types, or task patterns. Target category is a coverage dimension.
Clue type, answer meaning, and answer format are coverage and balance
dimensions. Task reasoning step count has a coverage and target-mix requirement.

Coverage and balance are checked at each task reasoning step count, not only over the
whole release. A value that appears only at one task reasoning step count does not
cover the other task reasoning step counts, and a global target may not be met
by concentrating a value at one task reasoning step count. Target category has no percentage target at
each task reasoning step count; it has coverage at each task reasoning step count and a release-level
diversity cap.

The dataset is not a list of predefined task types. Enumerating every
combination of clue type, answer meaning, and task reasoning step count would be limiting and would
force per-combination logic. The generator composes these dimensions instead.

New combinations of task target, task clues, answer format, and answer meaning
may be added if they follow the structure and meet the same quality rules.

---

## 5. Answer formats

The dataset must support all of the following answer formats at the priority shown.

| Answer format | What the user sees | Requirements | Priority |
|---|---|---|---|
| Multiple choice | A short list of choices, one of which is correct. | At least five choices, with seven as the goal, for every multiple-choice task; the correct answer is always present; choices are real candidates from the construction, not padding; descriptions do not repeat; no choice leaks the answer. | P0 |
| Number | A finite numeric value. | Unit, precision, and tolerance are stated; the default precision is 4 significant figures; the number is measured from the real geometry. | P0 |
| Integer | A whole number, usually a count or a rank. | Exact and non-negative where it is a count. | P0 |
| Yes or no | A boolean answer. | Exactly one of true or false is correct. | P0 |
| 3D coordinate | A point such as `(x, y, z)`. | Three finite numbers in a stated coordinate frame, with a stated tolerance; 4 significant figures per component by default. | P0 |
| Bounding box | A minimum and maximum corner. | Two three-dimensional points in a stated frame, with a stated tolerance; 4 significant figures per component by default. | P0 |
| Structured object | A small object with named fields, such as a CadQuery workplane state. | The fields are meaningful and documented; the answer is not an internal object dump. | P1 |

Numbers, coordinates, and bounding-box components are rounded to 4 significant
figures by default. A task may state a different precision only with a
documented reason.

All answers must be objectively checkable. An answer that requires an LLM to
judge is not allowed.
Multiple-choice choices are P0 when they are real, unique, and non-leaking. P2
adds examiner-style plausible near misses: each distractor should fail one task
clue or the answer step, and the release should record why. P0 and P1 do not
require the near-miss audit.

---

## 6. Task reasoning step count

Task reasoning step count is the number of task reasoning steps a task needs. It
is a count of the task solution sequence, not a score or a label.

- **1 step**: exactly one task clue step with an identity answer, or exactly one
  task answer step about a task target the question identifies directly (for
  example, the final solid state). This is the warmup subset and the curriculum
  entry point (P0).
- **2 to 5 steps**: the main benchmark range (P0). The LLM model must combine
  task clues about geometry, relationships, measurements, or operations.
- **6 or more steps**: optional future work (P2).

P2 inputs are deferred to later implementation; a task that uses one is part of a
later release, not a different task label.

The task reasoning step count comes from the task solution sequence defined in
[`task-structure.md`](task-structure.md), not from the number of sentences in
the prompt. A task that looks long but can be answered from a variable name or
an operation order does not have a high step count.

The first benchmark dataset release covers steps 1 through 5. Step 1 forms the
labeled warmup subset and is also useful training material. Steps 2 through 5
carry the main benchmark claim. Every benchmark result must name the task
reasoning step counts it covers, so a result that includes warmup tasks is not
mistaken for a result on steps 2 through 5 alone.

---

## 7. Product requirements

### 7.1 Correctness and fairness

| ID | Requirement | How the user can tell |
|---|---|---|
| **R-1** | Every answer is correct. | The answer is produced by running the CadQuery program or derived by an exact rule, and recorded with answer evidence. No LLM writes or judges the answer. |
| **R-2** | Every task has exactly one correct answer. | Ambiguous tasks and tasks with ties are rejected. |
| **R-3** | Multiple-choice tasks are fair. | The correct answer is present; there are enough choices that guessing does not look competitive; choices are real candidates from the construction; choices do not give the answer away. |
| **R-4** | At least 95% of benchmark tasks require reasoning about the actual shape. | At least one task clue depends on the geometry or topology the program builds, not only on the text of the program. |
| **R-5** | Trivial shortcuts do not win on shape-required tasks. | For a task that requires the built shape, an LLM model cannot answer by reading variable names, literal arguments, or operation order alone. |
| **R-6** | Answers are not leaked. | The prompt never contains the answer or hidden identifiers. |

### 7.2 Coverage and balance

Coverage and balance apply to the implementation scope of the release. The first
release covers P0 values; later releases add P1 and P2 values. A value deferred
to a later implementation scope is not a coverage gap in the current release.
"Supported" below means supported by the release's implementation scope.

| ID | Requirement | How the user can tell |
|---|---|---|
| **R-7** | The dataset balances answer formats at every task reasoning step count. | Every answer format in section 5 appears at every task reasoning step count where it is supported. No format is more than twice or less than half its share among the formats supported at that task reasoning step count. Over the release, each format is between 5% and 25% of tasks. |
| **R-8** | The dataset covers all target categories, clue types, and answer meanings. | Every target category, clue type, and answer meaning supported at a task reasoning step count appears at that task reasoning step count. A value that is valid, implemented by the release, and missing is a gap; the task reasoning step support tables record which values cannot occur at that step count and why. |
| **R-9** | The dataset covers the full task reasoning step count range. | Steps 1 through 5 all appear in the target mix in section 8, with steps 3 and 4 carrying most benchmark tasks. |
| **R-10** | The dataset is diverse. | It draws from at least one thousand distinct CAD models, and no single CAD model is above 1% of tasks. |
| **R-11** (P1) | The dataset has varied answers. | At least one thousand different correct answers appear, and no correct answer is above 1% of tasks. |
| **R-12** (P1) | The dataset is balanced at every task reasoning step count. | No clue type is above 25% of clues at a task reasoning step count or over the release, and no clue type is more than twice or less than half its share among the clue types supported at a task reasoning step count. Every answer meaning is between 1% and 10% over the release, and no answer meaning is more than twice or less than half its share among the meanings supported at a task reasoning step count. No target category is above 25% of the release. |

### 7.3 Splits and reuse

| ID | Requirement | How the user can tell |
|---|---|---|
| **R-13** | Training, validation, and test sets do not overlap. | The same CADEvolve program family — a CADEvolve generator family or a CADEvolve-predicted ABC/ShapeNet mesh family — never appears in both training and evaluation. |
| **R-14** | The test set is never trained on. | The dataset card names the test set and the training recipe excludes it. |
| **R-15** | The warmup subset is labeled, not excluded. | Warmup tasks are marked as tasks with one task reasoning step and may be used for training; every benchmark result names the task reasoning steps it covers. |
| **R-16** (P1) | Transfer results are not contaminated. | No program from the external benchmark used for transfer appears in training or evaluation. |

### 7.4 Usability and trust

| ID | Requirement | How the user can tell |
|---|---|---|
| **R-17** | A careful human can understand every task. | Sampled tasks covering every clue type, answer meaning, and answer format are reviewed before a dataset release; unclear wording is a defect. |
| **R-18** | The dataset can be reproduced. | The same programs and the same generator version produce the same dataset; the dataset card documents versions, settings, and how to regenerate it. |
| **R-19** | Nothing disappears silently. | Every rejected program or task is reported with a reason, and the counts add up. |
| **R-20** (P2) | The dataset can grow without breaking users. | New tasks, clue types, or answer meanings can be added without changing the release dataset layout or the evaluation interface. |
| **R-21** (P1) | The dataset is fast enough to iterate on. | A reviewer can change a task description and produce a new reviewable sample without re-running the entire corpus from scratch. |
| **R-22** (P2) | The dataset can support a kernel-assisted upper bound. | The same tasks can be evaluated with CadQuery access as an optional upper bound, without changing the primary no-kernel setting. |

---

## 8. Size and mix of the benchmark dataset release

The first benchmark dataset release implements the P0 requirements and must contain at least
ten thousand tasks and meet the following targets at their stated priorities.
Priority in this table is implementation order, not a task label.

| Property | Target | Priority |
|---|---|---|
| Tasks | At least 10,000 | P0 |
| Distinct CAD models | At least 1,000 | P0 |
| CAD model dominance | No CAD model above 1% of tasks | P1 |
| Target category coverage | Every supported category at every task reasoning step count | P0 |
| Target category dominance | No category above 25% of tasks | P1 |
| Answer format coverage | Every supported format at every task reasoning step count | P0 |
| Answer format balance | Each 5-25% over the release; mix at each task reasoning step count within the tolerance in `task-structure.md` | P0 |
| Clue type coverage | Every supported clue type at every task reasoning step count | P0 |
| Clue type balance | No clue type above 25% of clues at a task reasoning step count or over the release; mix at each task reasoning step count within the tolerance in `task-structure.md` | P1 |
| Answer meaning coverage | Every supported meaning at every task reasoning step count | P0 |
| Answer meaning balance | Each 1-10% over the release; mix at each task reasoning step count within the tolerance in `task-structure.md` | P1 |
| Task reasoning step count | Target mix: 1 step 5%, 2 15%, 3 40%, 4 25%, 5 15% | P0 |
| Tasks that require the built shape | At least 95% | P0 |
| Tasks needing at least three steps | At least 80% | P0 |
| Multiple-choice choices | At least five; aim for seven | P0 |
| Different correct answers | At least 1,000 | P1 |
| Answer dominance | No correct answer above 1% of tasks | P1 |
| Answer evidence | Available for every task | P0 |

The task reasoning step count mix is a target, not a hard quota. A miss is documented and accepted
by the owner; it is not hidden by changing the definition of a task reasoning step count.

These are product targets. The technical specification will define how they are
measured and what happens when a requirement cannot be met.

---

## 9. Warmup subset

A small LLM model needs a lower-step introduction before the higher-step tasks.
The dataset therefore labels its lowest-step tasks as the warmup subset. The warmup
subset is P0 for the first training cycle.

- 5% of tasks, drawn from the same CadQuery programs and the same dataset as the
  benchmark;
- one task reasoning step;
- all P0 answer formats;
- the same prompt and answer format as the benchmark;
- the same correctness and fairness rules;
- may be used for training, especially to teach an LLM model that knows little
  about CadQuery reasoning;
- may be included in a benchmark run, but every benchmark result must name the
  task reasoning step counts it covers.

The dataset is designed for curriculum learning: lower task reasoning step
counts first, higher counts later.

---

## 10. Training, validation, and test

Each implementation milestone produces a dataset release. Later releases are
cumulative: when a later release includes a task from an earlier release, its
split assignment is preserved. A task is never labelled by the milestone that
introduced it.

- **Training**: tasks an LLM model may learn from;
- **Validation**: tasks used to tune training decisions;
- **Test**: tasks used only for the final result.

The same CADEvolve program family must not appear in more than one part. A CADEvolve
program family is a CADEvolve generator family or a CADEvolve-predicted
ABC/ShapeNet mesh family; P and C versions of the same family share a family ID. The
test part must never be used for training, tuning, or choosing an LLM model.

The no-overlap rule is P0. The intended proportions are approximately 70%
training, 15% validation, and 15% test (P1). The exact proportions may change if
the available CAD models make them impractical, but the no-overlap rule may not
change.

---

## 11. Deliverables

| Deliverable | What the user receives | Priority |
|---|---|---|
| Training dataset | Tasks and correct answers for training. | P0 |
| Validation dataset | Tasks and correct answers for tuning. | P0 |
| Test dataset | Held-out tasks and correct answers for the final result. | P0 |
| Warmup subset | Labeled 1-step tasks for warmup. | P0 |
| Task reasoning step support tables | Which target categories, clue types, answer meanings, and answer formats are supported at each task reasoning step count and implementation scope, and why not. | P0 |
| Dataset card | A plain description of what the dataset contains, how it was made, what it is for, and what it is not for. | P0 |
| Evaluation material | The correct answers and instructions needed to score an LLM model. | P0 |
| Documentation | How to reproduce the dataset release and how to review it. | P1 |

---

## 12. Definition of done

The dataset is done when:

1. a small sample produces every target category, clue type, answer meaning,
   and answer format supported in the P0 implementation scope at every task reasoning step
   count where that value is structurally supported;
2. the first benchmark dataset release of at least ten thousand tasks meets the
   coverage and balance targets at every task reasoning step count in section 8,
   or every miss is documented and accepted by the owner;
3. the task reasoning step support tables are published and reviewed;
4. a labeled warmup subset exists;
5. training, validation, and test sets do not share a CAD model;
6. a reviewer can read sampled tasks covering every task reasoning step count,
   target category, clue type, answer meaning, and answer format supported in the
   released dataset and understand them without asking what they mean;
7. the answers can be checked without an LLM in the loop;
8. the dataset release can be regenerated and the result matches what is
   documented;
9. the dataset card states clearly what the dataset is and is not suitable for;
10. an LLM model can be trained on the training set and evaluated on the test
    set without touching the answers.

---

## 13. Non-goals

- Training or evaluating an LLM model. This document stops at the dataset.
- A user-facing question language.
- A dataset written or judged by an LLM.
- CAD generation or editing.
- Making CadQuery or a CAD kernel the primary evaluation setting. A
  kernel-assisted upper bound is a P2 goal.
- A general three-dimensional reasoning benchmark.
- A replacement for an independent transfer benchmark.
- Preserving the previous dataset's internal names or file layout.

---

## 14. Legacy and migration

- The previous dataset release is tagged
  `before-throwing-out-the-existing-dataset-generator` and is fixed.
- The previous dataset generator is marked superseded by
  `dataset/SUPERSEDED.md`.
- The previous documentation is archived under
  `docs/_archive/dataset-pre-rebuild-2026-10-21/`.
- The previous dataset release may be used for a first training cycle while the
  replacement is built. It must not be extended or repaired.
- The replacement dataset may use a new task and answer layout.
  Training and evaluation code moves to the new layout; no compatibility file is
  kept.

---

## 15. Resolved questions

- **Q1** (P0). *Resolved 2026-10-21.* The first benchmark dataset release targets
  ten thousand tasks. Scale is not a constraint if generation is efficient.
- **Q2** (P0). *Resolved 2026-10-21.* At least five choices; seven is the goal.
- **Q3** (P0). *Resolved 2026-10-21.* The same CAD model means the same CadQuery
  program. Tasks that come from the same program stay in one part of
  the split.
- **Q4** (P1). *Resolved 2026-10-21.* One-step tasks appear in the dataset
  release. They form the labeled warmup subset and are also useful training
  material.
- **Q5** (P1). *Resolved 2026-10-21.* Yes. Every answer format must reach five
  percent; a balanced and diverse dataset is the default.
- **Q6** (P1). *Resolved 2026-10-21.* Coverage is at each task reasoning step
  count for target categories, clue types, answer meanings, and answer formats.
  Balance is at each task reasoning step count and over the release for
  clue types, answer meanings, and answer formats. Target category is coverage-only
  at each task reasoning step count, with a release cap. Task reasoning step
  count uses the target mix in section 8.
- **Q7** (P0/P1). *Resolved 2026-10-21.* P0 uses Option A: compare normalized
  CadQuery program text. This is a hash/text check and does not run CadQuery or
  parse an AST. P1 uses Option B: normalize variable names and formatting with
  an AST, hash the result, and run CadQuery to compare the shape only for
  candidates that survive the cheap check or for a final audit. The shape check
  is not a P0 requirement.
- **Q8** (P1). *Resolved 2026-10-21.* The same CadQuery programs. The warmup
  subset is a label for easier tasks, not a separate generation path. The
  dataset is designed for curriculum learning.
- **Q9** (P0). *Resolved 2026-10-21.* No backward compatibility. Training and
  evaluation code moves to the new dataset layout; no compatibility file is
  kept.
- **Q10** (P1). *Resolved 2026-10-21.* Warmup is the 1-step bucket: 5% of the
  release, with no absolute cap. A larger release gets a proportionally larger
  warmup.
- **Q11** (P1). *Resolved 2026-10-21.* Use percentage caps: no CAD model above
  1% of tasks, and no correct answer above 1% of tasks.

---

## 16. Known issues

- **KI1** (P0). *Open, 2026-10-22.* **Why not run the CAD kernel?** The P0
  setting answers geometry questions about a CadQuery program without access to
  CadQuery. A reviewer will ask why: in practice CadQuery is usually available,
  free, and deterministic, so a kernel call gives the exact answer.
  - *Counter-argument.* A kernel call is not free for an LLM agent. It costs a
    tool round trip, sandbox latency, and extra context. Many questions are
    obvious from the program text, and reasoning about them directly is cheaper
    than executing it.
  - *Partial answer.* Writing CadQuery selectors and answering factual geometry
    questions (the distance from A to B; which component is heaviest) is useful
    work in its own right. Measuring how well an LLM model does it without a
    kernel also sets a baseline for future work.
  - *Why the P0 harness is `numpy`.* When the project began, the available LLM
    models did not know CadQuery, so NumPy seemed the easier tool for them.
    Fine-tuning removes that reason. A fine-tuned LLM model that writes a short
    CadQuery query is cheaper and easier to grade than one that rebuilds the
    geometry in NumPy.
  - *Not resolved.* The project is considering a pivot to a kernel-query task:
    given a question, generate the CadQuery query whose execution produces the
    answer, scored by execution. That task removes this objection but changes the
    P0 setting and the non-goals in section 13.
