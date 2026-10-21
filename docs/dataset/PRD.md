# PRD — CAD-QA dataset

**Status:** draft for owner review, 2026-10-21.

**What this document is.** This is the product requirements document for the
CAD-QA dataset. It describes what a user gets from training and evaluating on
the dataset. It does not describe how the dataset is produced; that belongs in
the technical specification.

**Relation to the project PRD.** [`../PRD.md`](../PRD.md) remains the authority
for the research questions, hypotheses, and evaluation goals. This document
defines the dataset those goals need. It does not change the research goals.

**Supersedes.** All previous dataset-generation specifications. The old
dataset documentation, answer-shape notes, decisions, and issue register are
archived at `docs/_archive/dataset-pre-rebuild-2026-10-21/` and are history,
not requirements.

---

## 1. What the user gets

The user gets a training dataset and a separate evaluation benchmark for LLMs
that read CadQuery programs and reason about the three-dimensional shapes those
programs produce.

Training on the dataset should make an LLM model better at:

- reading a CadQuery program and predicting what shape it builds;
- finding the feature, face, edge, vertex, CadQuery profile, CadQuery workplane, path, or region a question asks about;
- answering quantitative questions about volume, area, length, distance,
  angle, bounding box, centroid, and counts;
- reasoning about relationships such as adjacent, contained, parallel,
  perpendicular, closer, farther, before, and after;
- reasoning about what an operation changed, including material added, material
  removed, volume change, and topology change;
- following several clues in order until only one answer remains;
- answering without access to CadQuery, OpenCascade, or any other CAD kernel
  (P0);
- as a P2 goal, answering with access to CadQuery as an upper-bound setting.

The user also gets:

- a held-out benchmark for comparing LLM models fairly;
- a labeled warmup subset of easier questions for teaching an LLM model the task
  shape before the hard questions;
- questions and answer keys in separate files;
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

---

## 2. Who it is for

| User | What they need |
|---|---|
| Researcher or trainer | A dataset that teaches CAD program comprehension and geometry reasoning, with a clear answer key. |
| Evaluator | A held-out benchmark with several difficulty levels and a fair way to compare models. |
| Reviewer | Questions a careful human can read and check, plus a documented answer key. |
| Dataset maintainer | A dataset that can be regenerated, extended with new question categories, and reviewed without redoing everything. |

---

## 3. What is in the dataset

The dataset contains:

- a curated collection of CadQuery programs;
- questions about those programs;
- one correct answer for each question;
- enough recorded evidence to show why the answer is correct;
- a separate answer key;
- training, validation, and test sets;
- a labeled warmup subset;
- a dataset card and evaluation material.

Each question shows the CadQuery program and asks for one answer. The answer
key is never part of the question file.

In this document, a CAD model means one CadQuery program. Two questions
share a CAD model when they come from the same program.

A question is built from clues: conditions the answer must satisfy. Clues are
written in plain language, and their variety is a requirement in its own right.

The structure of a question is defined in [`question-structure.md`](question-structure.md).
The content of the prompt is defined in [`prompt-content.md`](prompt-content.md).
The facts the questions rely on are defined in [`graph-content.md`](graph-content.md).
The proposed vocabulary is in [`terminology.md`](terminology.md).

---

## 4. Question structure

A question is not one of a flat list of labels. It is a combination of five
independent dimensions:

- the **target** the question asks about;
- the **clues** the answer must satisfy;
- the **answer shape** the LLM model must return;
- the **reasoning pattern** that finds the target;
- the **reasoning depth** the question requires.

The previous flat list mixed these dimensions. For example, "direct fact"
described depth, "give a coordinate" described an answer shape, and "measure a
distance" described a measurement. Those are not peers.

The full structure, including target categories, clue forms, reasoning patterns,
depth rules, and the precise definition of a question family, is in
[`question-structure.md`](question-structure.md).

The dataset must cover these reasoning patterns:

- Direct
- Locate
- Measure
- Compare
- Count
- Rank
- Effect
- Membership
- CadQuery workplane
- Chain

The list is not a closed set of question labels. A question family is defined by
its pattern, target, clues, answer shape, depth, and uniqueness rule. New
families may be added if they follow the structure and meet the same quality rules.

---

## 5. Categories of answers

The dataset must support all of the following answer shapes.

| Answer shape | What the user sees | Requirements |
|---|---|---|
| Multiple choice | A short list of choices, one of which is correct. | At least five choices, with seven as the target, for the benchmark dataset release; the correct answer is always present; choices are real options drawn from the program, not padding; descriptions do not repeat; no choice leaks the answer. |
| Variable name | A name that appears in the CadQuery program. | The name is visible in the program and identifies one object. |
| Number | A finite numeric value. | Unit, precision, and tolerance are stated; the number is measured from the real geometry. |
| Integer | A whole number, usually a count or a rank. | Exact and non-negative where it is a count. |
| Yes or no | A boolean answer. | Exactly one of true or false is correct. |
| 3D coordinate | A point such as `(x, y, z)`. | Three finite numbers in a stated coordinate frame, with a stated tolerance. |
| Bounding box | A minimum and maximum corner. | Two three-dimensional points in a stated frame, with a stated tolerance. |
| Structured object | A small object with named fields, such as a CadQuery workplane state. | The fields are meaningful and documented; the answer is not an internal object dump. |

All answers must be objectively checkable. An answer that requires an LLM to
judge is not allowed.

---

## 6. Difficulty

Difficulty is described by how many reasoning steps a question needs.

- **0 to 1 steps**: a direct fact about a named object (0 steps), or one
  inference such as finding a feature by a property (1 step). This is the
  warmup subset and the curriculum entry point (P0).
- **2 to 5 steps**: the main benchmark range (P0). The LLM model must combine
  clues about geometry, relationships, measurements, and operations.
- **6 or more steps**: optional future work (P2).

A question's difficulty must come from the work it actually requires, not from
a label attached to it. A question that looks long but can be answered from a
variable name or an operation order is not a hard question.

The benchmark dataset release covers steps 0 through 5. Steps 0 and 1 form the
labeled warmup subset and are also useful training material. Steps 2 through 5
carry the main benchmark claim. Every benchmark result must name the reasoning
steps it covers, so a result that includes warmup questions is not mistaken for
a result on steps 2 through 5 alone.

---

## 7. Product requirements

### 7.1 Correctness and fairness

| ID | Requirement | How the user can tell |
|---|---|---|
| **R-1** | Every answer is correct. | The answer is produced by running the CadQuery program during dataset creation and measuring the real geometry. No LLM writes or judges the answer. |
| **R-2** | Every question has exactly one correct answer. | Ambiguous questions and questions with ties are rejected. |
| **R-3** | Multiple-choice questions are fair. | The correct answer is present; there are enough choices that guessing does not look competitive; choices are real options drawn from the program; choices do not give the answer away. |
| **R-4** | Benchmark questions require reasoning about the actual shape. | At least one clue depends on the geometry or topology the program builds, not only on the text of the program. |
| **R-5** | Trivial shortcuts do not win. | An LLM model cannot answer a benchmark question by reading variable names, literal arguments, or operation order alone. |
| **R-6** | Answers are not leaked. | The question file never contains the answer or hidden identifiers. |

### 7.2 Coverage and balance

| ID | Requirement | How the user can tell |
|---|---|---|
| **R-7** | The dataset covers all answer shapes. | Every answer shape in section 5 appears in the benchmark dataset release, including the warmup subset. |
| **R-8** (P1) | The dataset covers all question categories in section 4. | Every category in section 4 appears in the benchmark dataset release, and no category dominates. |
| **R-9** | The dataset covers the full difficulty range. | Steps 0 through 5 all appear, with steps 3 and 4 carrying the headline slices. |
| **R-10** | The dataset is diverse. | It draws from at least one thousand distinct CAD models, and no single CAD model or question category dominates. |
| **R-11** (P1) | The dataset has varied answers. | At least one thousand different correct answers appear, and no answer is repeated so often that guessing wins. |
| **R-12** (P1) | The dataset is balanced across question categories. | No question category is below one percent or above ten percent of the benchmark dataset release. |
| **R-23** (P1) | The clues inside questions are diverse. | No single clue pattern, such as "largest area" or "parallel to Z", dominates the benchmark dataset release; clue variety is reported beside question variety. |

### 7.3 Splits and reuse

| ID | Requirement | How the user can tell |
|---|---|---|
| **R-13** | Training, validation, and test sets do not overlap. | The same CAD model (the same CadQuery program) never appears in both training and evaluation. |
| **R-14** | The test set is never trained on. | The dataset card names the test set and the training recipe excludes it. |
| **R-15** | The warmup subset is labeled, not excluded. | Warmup questions are marked as steps 0–1 and may be used for training; every benchmark result names the reasoning steps it covers. |
| **R-16** (P1) | Transfer results are not contaminated. | No program from the external benchmark used for transfer appears in training or evaluation. |

### 7.4 Usability and trust

| ID | Requirement | How the user can tell |
|---|---|---|
| **R-17** | A careful human can understand every question. | Sampled questions from every category are reviewed before a dataset release; unclear wording is a defect. |
| **R-18** | The dataset can be reproduced. | The same programs and the same generator version produce the same dataset; the dataset card documents versions, settings, and how to regenerate it. |
| **R-19** | Nothing disappears silently. | Every rejected program or question is reported with a reason, and the counts add up. |
| **R-20** (P2) | The dataset can grow without breaking users. | New question categories can be added without changing the question file, the answer key, or the evaluation interface. |
| **R-21** (P1) | The dataset is fast enough to iterate on. | A reviewer can change a question category and produce a new reviewable sample without re-running the entire corpus from scratch. |
| **R-22** (P2) | The dataset can support a kernel-assisted upper bound. | The same questions can be evaluated with CadQuery access as an optional upper bound, without changing the primary no-kernel setting. |

---

## 8. Size and mix of the benchmark dataset release

The first benchmark dataset release must contain at least ten thousand
questions and meet the following targets.

| Property | Target | Priority |
|---|---|---|
| Questions | At least 10,000 | P0 |
| Distinct CAD models | At least 1,000 | P0 |
| Answer shapes | Every shape in section 5; each at least 5% and none above 25% | P0 |
| Question categories | All categories in section 4; each between 1% and 10% | P1 |
| Clue variety | No single clue pattern dominates | P1 |
| Difficulty | Steps 0–1: at least 5%; steps 2–5 cover the remainder, with 3 and 4 carrying the headline slices | P0 |
| Geometry-based questions | At least 95% | P0 |
| Questions needing at least three steps | At least 90% | P0 |
| Multiple-choice choices | At least five; target seven | P0 |
| Different correct answers | At least 1,000 | P1 |
| Evidence for the answer | Available for every question | P0 |

Within steps 2–5, aim for roughly 2: 20–30%, 3: 30–40%, 4: 20–30%, and 5:
10–20%.

These are product targets. The technical specification will define how they are
measured and what happens when a target cannot be met.

---

## 9. Warmup subset

A small LLM model needs an easy introduction before the hard questions. The
dataset therefore labels its easiest questions as the warmup subset. The warmup
subset is P0 for the first training cycle.

- 500 to 1,000 questions, drawn from the same CadQuery programs and the same
  dataset as the benchmark;
- 0 or 1 reasoning steps;
- all answer shapes;
- the same question and answer-key format as the benchmark;
- the same correctness and fairness rules;
- may be used for training, especially to teach an LLM model that knows little
  about CadQuery reasoning;
- may be included in a benchmark run, but every benchmark result must name the
  number of reasoning steps it covers.

The dataset is designed for curriculum learning: easy questions first, harder
questions later.

---

## 10. Training, validation, and test

The benchmark dataset release is divided into three parts:

- **Training**: questions an LLM model may learn from;
- **Validation**: questions used to tune training decisions;
- **Test**: questions used only for the final result.

The same CAD model (the same CadQuery program) must not appear in more than
one part. The test part must never be used for training, tuning, or choosing an
LLM model.

The no-overlap rule is P0. The intended proportions are approximately 70%
training, 15% validation, and 15% test (P1). The exact proportions may change if
the available CAD models make them impractical, but the no-overlap rule may not
change.

---

## 11. Deliverables

| Deliverable | What the user receives | Priority |
|---|---|---|
| Training dataset | Questions and answer keys for training. | P0 |
| Validation dataset | Questions and answer keys for tuning. | P0 |
| Test dataset | Held-out questions and answer keys for the final result. | P0 |
| Warmup subset | Labeled easy questions for teaching the task shape. | P0 |
| Dataset card | A plain description of what the dataset contains, how it was made, what it is for, and what it is not for. | P0 |
| Evaluation material | The answer keys and instructions needed to score an LLM model. | P0 |
| Documentation | How to reproduce the dataset release and how to review it. | P1 |

---

## 12. Definition of done

The dataset is done when:

1. a small sample produces every question category and every answer shape;
2. a benchmark dataset release of at least ten thousand questions meets the
   targets in section 8, or every miss is documented and accepted by the owner;
3. a labeled warmup subset exists;
4. training, validation, and test sets do not share a CAD model;
5. a reviewer can read sampled questions from every category and understand
   them without asking what they mean;
6. the answers can be checked without an LLM in the loop;
7. the dataset release can be regenerated and the result matches what is
   documented;
8. the dataset card states clearly what the dataset is and is not suitable for;
9. an LLM model can be trained on the training set and evaluated on the test set
   without touching the answer key.

---

## 13. Non-goals

- Training or evaluating an LLM model. This document stops at the dataset.
- A public question language.
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
- The replacement dataset may use a new question file and answer-key layout.
  Training and evaluation code moves to the new layout; no compatibility file is
  kept.

---

## 15. Open questions

- **Q7** (P1). When checking that the dataset does not overlap the independent
  benchmark used to test transfer (BenchCAD `qa_code` and `edit_code`), how
  exact must the check be: identical CadQuery program text, the same CAD model,
  or only the same category of question? Proposed default: identical CadQuery
  program and the same CAD model where it can be identified.

## 16. Resolved questions

- **Q1** (P0). *Resolved 2026-10-21.* The first benchmark dataset release targets
  ten thousand questions. Scale is not a constraint if generation is efficient.
- **Q2** (P0). *Resolved 2026-10-21.* At least five choices; seven is the target.
- **Q3** (P0). *Resolved 2026-10-21.* The same CAD model means the same CadQuery
  program. Questions that come from the same program stay in one part of
  the split.
- **Q4** (P1). *Resolved 2026-10-21.* Zero- and one-step questions appear in the
  dataset release. They form the labeled warmup subset and are also useful
  training material.
- **Q5** (P1). *Resolved 2026-10-21.* Yes. Every answer shape must reach five
  percent; a balanced and diverse dataset is the default.
- **Q6** (P1). *Resolved 2026-10-21.* All question categories in section 4.
  Clue variety is a separate requirement (R-23), because the conditions inside
  questions should be as varied as the question categories.
- **Q8** (P1). *Resolved 2026-10-21.* The same CadQuery programs. The warmup
  subset is a label for easier questions, not a separate generation path. The
  dataset is designed for curriculum learning.
- **Q9** (P0). *Resolved 2026-10-21.* No backward compatibility. Training and
  evaluation code moves to the new dataset layout; no compatibility file is
  kept.
