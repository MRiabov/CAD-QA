# Dataset requirements

**Status:** active, 2026-11-24. This document is the ownership contract for the
product requirements. It names which document owns which fact and how the three
content documents project onto each other. It does not repeat a fact an owner
already states. The document catalog is in [`../README.md`](../README.md).

## Three content layers

The dataset is one thing seen at three layers. The layers are not peer topics,
so a fact lives at exactly one layer and is projected into the others.

| Layer | Document | Owns |
|---|---|---|
| Graph | [`graph-content.md`](graph-content.md) | The CAD graph: graph entities, relations, measurements, evidence, states, and emission rules, including the closed value sets they use. |
| Task | [`task-structure.md`](task-structure.md) | The task: task target, task clue semantics, clue reduction form, answer meaning, answer format, task reasoning step count, uniqueness, coverage, and balance. |
| Prompt | [`prompt-content.md`](prompt-content.md) | The prompt: parts and order, wording of questions and task clues, choices, answer instruction, and what the prompt must not contain. |

The supporting documents are not a fourth layer.

| Document | Role |
|---|---|
| [`PRD.md`](PRD.md) | Product promise and quality requirements. Where the detail belongs to a layer, the PRD links to it. |
| [`terminology.md`](terminology.md) | The words. A term is defined here or in the glossary, not in a layer document. |
| [`decisions.md`](decisions.md) | Requirements decisions (`DS-REQ-*`). |
| [`release-dataset-contract.md`](release-dataset-contract.md) | The consumer contract for the release table. |
| [`shortcut-resistance.md`](shortcut-resistance.md) | The P1 R-5 construction gate: the answer dependency chain, the verdicts, the threshold, the storage cost, and what the check does not prove. |
| [`views/clue-list.md`](views/clue-list.md) | A derived view of the strings a task clue renders to. It owns no rule and no open question. |
| [`views/reference-forms.md`](views/reference-forms.md) | A derived view of the phrases that name a thing in a prompt. It owns no rule and no open question. |
| [`views/prompt-examples.md`](views/prompt-examples.md) | Eight complete prompts with their answers, for reading the rendered text end to end. It owns no rule and no open question. |
| [`views/capability-coverage.md`](views/capability-coverage.md) | A derived view of what each P0 capability can be asked about and which capabilities no task reads yet. It owns no rule and no open question. |
| [`views/shortcut-resistance.md`](views/shortcut-resistance.md) | A derived view of the shortcut-resistance check with worked examples. It owns no rule and no open question. |

The views are split by release scope: P0 first, then P1, then P2 where they have
content. A form that does not exist at a scope is marked `missing`.

The owner reviews the views, not the requirement tables. A new capability,
measurement, clue string, or reference form appears in a view in the same
change; a rule no view projects is unreviewed.

## The projection rule

A vocabulary is defined once, in the layer that contains it. The other layers
project it; they do not copy it.

- A graph value, such as a face surface kind or a measurement name, is defined in
  `graph-content.md`. `task-structure.md` says whether a task may use it and what
  an answer meaning reads from it. `prompt-content.md` says how it is worded.
- A task dimension, such as a clue type or an answer format, is defined in
  `task-structure.md`. `prompt-content.md` gives its wording and links back.
- A prompt part, such as the answer instruction, is defined in
  `prompt-content.md`. The release table stores the rendered prompt; it does not
  redefine the part.

When a layer needs another layer's value, it links to the owner and states the
projection. It does not reproduce the list. A closed vocabulary copied into
three layers drifts: one copy gains a value, one keeps a retired value, and the
renderer labels a value no graph row carries.

## Precedence

The layers are not equal when they disagree.

1. `graph-content.md`, `task-structure.md`, `prompt-content.md`, and
   `shortcut-resistance.md` are the requirements. They record what the dataset
   must be.
2. `clue-list.md`, `reference-forms.md`, and `views/shortcut-resistance.md` are
   derived from them. If one of them disagrees with a requirement, the
   requirement is right.
3. `implementation/` describes how the generator satisfies the requirements. An
   implementation doc that disagrees with a requirement is a defect to record,
   not newer truth to copy.
4. `generator/config/prompts.yaml` is data that implements a requirement. A copy
   that disagrees is an implementation defect.

A disagreement never moves a requirement down a level. If the requirement is
genuinely wrong, change it here, in the requirements, and then update the
implementation to follow it.

## Reading order

1. `PRD.md` for the product promise.
2. `graph-content.md` for what exists.
3. `task-structure.md` for what a task asks.
4. `prompt-content.md` for what the LLM model sees.
5. `release-dataset-contract.md` for what a release carries.
