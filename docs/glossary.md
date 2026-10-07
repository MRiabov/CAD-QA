# Glossary

The **ubiquitous language** of CAD-QA. Read this before naming anything new.

> "By using the model-based language pervasively and not being satisfied until it flows, we
> approach a model that is complete and comprehensible, made up of simple elements that
> combine to express complex ideas." — Eric Evans, *Domain-Driven Design*

## Why

Bad names in a spec become table, field, route, and code names, and are hard to fix once
shipped. We name each concept once, here, and reuse the same word everywhere. If a doc
invents a new word, it is wrong — the word should already be here, or be added here first.

## The rule

- **Domain** terms are the project's own words for its concepts. Use them in docs, code,
  and conversation.
- **Enums** are closed sets of labels. They live together under Enums, not as their own
  terms.
- **Internal** terms are technical names for something that is not a Domain concept. Use
  them in technical docs and code only.
- **Meaning, not implementation.** An entry says what the term means, and optionally why
  that word is used (`Distinct from:`, never-say). It never says how something works —
  that belongs in the specs. Names of types, tables, routes, or `In code:` identifiers may
  appear so code can match the term.
- **One concept, one word.** A term names one thing; a thing has one term.
- **Approval.** A definition is a proposal until the owner approves it. Definitions are
  added or changed with the owner's agreement, never autonomously.
- Don't-say words appear only in the *Don't say* table and in never-say listings.

---

## Domain

### CAD-QA

The benchmark for reasoning over procedural CAD programs (CadQuery), and the fine-tuning
effort that uses it.

---

### CADEditQA

A possible extension of CAD-QA: predicting a constrained edit to a CAD program. Not
active; priority P2.

---

### source

One CadQuery program the benchmark draws from. `In code:` `SourceRecord`.

---

### CAD query trace

The execution record of a source. `Distinct from:` **training trace**.

---

### snapshot

The measured state of one assignment within a source.

---

### CADEvolve

The primary corpus of executable CadQuery programs the benchmark draws from.

---

### ontology graph

The typed graph of a source.

---

### ontology node

A typed entity in an ontology graph (for example source, feature, workplane, profile,
face, edge, vertex, path, selector). `Distinct from:` code node.

---

### relation

A typed edge between two ontology nodes.

---

### relation family

A group of relation types, used to categorize a dataset row.

---

### measurement

A typed numeric or geometric fact about an ontology node.

---

### selector

A CadQuery expression that picks topology entities (for example `.faces(">Z")`).

---

### workplane

The coordinate frame a sketch or feature is built in.

---

### profile

The 2D shape drawn on a workplane (circle, rectangle, polyline).

---

### material region / void region

The geometry a feature adds / removes.

---

### dataset row

One question instance: a public rendering plus its private verifier artifacts.

#### public row

The answer-free model input of a dataset row.

#### private row

The verifier side of a dataset row: gold answer, hidden query program, candidate trace,
clue map.

---

### query program

The hidden, deterministic program a dataset row is generated from.

---

### clause

One step of a query program, mapped to exactly one public clue.

---

### candidate trace

The record of how the candidate set narrows to the answer.
`Distinct from:` **CAD query trace**, **training trace**.

---

### gold answer

The verifier-backed correct answer for a dataset row.

---

### hop count

The number of reasoning steps a dataset row requires.

#### logical hop count

Hops in the question's reasoning.

#### static hop count

Hops derivable from source syntax alone.

#### geometry hop count

Hops requiring geometry evidence.

---

### difficulty bucket

A coarse difficulty label for a dataset row.

---

### verifier

The deterministic authority for whether a query resolves uniquely, and what its gold
answer is.

---

### quarantine

A dataset row that is not release-ready.

---

### training trace

A model-facing record of reasoning followed by a tool call, used as supervision.
`Distinct from:` **CAD query trace**, **candidate trace**.

---

### submit tool

The typed answer tools a model emits to answer (`submit_label`, `submit_number`, …).

---

### run_code

The sandboxed Python/NumPy compute tool available to the model.

---

### compact_trace

A tool that shortens reasoning while a training trace is produced.

---

## Enums

### answer format

The shape of an answer: `candidate_label`, `coordinate`, `text`, `number`, `integer`,
`boolean`, `bbox`, or `json`.

---

### measurement scope

Where a measurement comes from: `profile_intrinsic`, `feature_application_effect`,
`entity_geometry`, `snapshot_state`, or `relation_metric`. Used to avoid category errors.

---

### release tier

The readiness bar a dataset is validated against: `smoke`, `release-candidate`, or
`benchmark-release`.

---

### harness mode

Which compute tools a model gets during evaluation.

#### numpy

The primary harness: a Python shell with NumPy.

#### no_tools

Reasoning only; no compute.

#### cadquery

Full CadQuery kernel access; one correct call suffices.

---

## Internal

### dataset_generation

The code package that builds the benchmark. `In code:` `cad_qa/`.

---

### fine_tuning

The code package for training and evaluation. `In code:` `train_and_eval/`.

---

### rows artifact

The input/output contract between `dataset_generation` and `fine_tuning`.

---

### Harbor

The environment and runner used to evaluate cost-effective models on the benchmark.

---

## Don't say

A ratchet: entries are removed only when the term is engineered out of the docs and code.

| Don't say | Say | Why |
|---|---|---|
| "intent" (as a doc) | PRD | "intent" is the concept, not the artifact |
| "trace" (alone) | CAD query trace / training trace / candidate trace | overloaded across three concepts |
| "model" (alone) | base model / adapter / merged model | ambiguous between weights, adapter, and served endpoint |
| "node" (alone) | ontology node / code node | ambiguous between graph and code |
| "entity id" (in a public answer) | source variable | internal `entity_id` values must not leak into public answers |
| "the pipeline" / "the object" / "the value" | name the concept | unspecific placeholder |
| "first/last" (as family semantics) | the sampled parameter | a rendering choice, not a permanent meaning |

---

## Proposed additions

Terms the specs use that still need a definition; each is added only with owner approval.
task family · intended family · answer contract · answer spec · sampled parameters ·
evidence tier · prompt template · clue map · release-ready · split / split group ·
geometry-critical · geometry-hop-positive · shortcut resistance · stop gate · candidate
label · source variable · path point / path segment / edge endpoint · tool declaration ·
native tool-call format · curriculum · compaction · held-out row · tool-valid · baseline ·
grader · closed-book · harness (the runner, distinct from **harness mode**) · Harbor task ·
slice (rc10 / release10k / clean-100) · tool-assisted upper bound.
