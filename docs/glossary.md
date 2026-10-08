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
- **Qualify every Domain term** with its domain (`CAD-QA`, `CAD`, `CadQuery`, or the owning
  concept). A bare common English noun (`source`, `snapshot`, `selector`) is opaque.
- **Keep qualifiers when composing.** A term built on a qualified term keeps its
  qualifier: a Measurement over a Shape snapshot is a **Shape snapshot measurement**, never
  a "Snapshot measurement" or "snapshot measurement".
- **Qualify everywhere.** Use the qualified term in docs; there are no short-form aliases.
  Code keeps the documented `In code:` identifiers.
- **Case.** A term is capitalized only in its glossary heading; in prose and definitions it
  is lowercase, like placis's "a website term includes **website**". Proper nouns and
  acronyms (CadQuery, CAD) keep their case.
- **Meaning, not implementation.** An entry says what the term means, and optionally why
  that word is used (`Distinct from:`, never-say). It never says how something works —
  that belongs in the specs. Names of types, tables, routes, or `In code:` identifiers may
  appear so code can match the term.
- **One concept, one word.** A term names one thing; a thing has one term.
- **Approval.** A definition is a proposal until the owner approves it. Definitions are
  added or changed with the owner's agreement, never autonomously.
- Don't-say words appear only in the *Don't say* table and in never-say listings. A docs
  sweep replaces don't-say usage with the Say term until the checkers are green.

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

### CadQuery program

One CadQuery program the benchmark draws from. `In code:` `SourceRecord`.

---

### CadQuery program operation trace

A CadQuery program decomposed into its operations, each with its Shape snapshot (and Shape
snapshot measurement), effect delta, and selector results. `In code:` `TraceRecord`.
`Distinct from:` **agent training trace**.

---

### Shape snapshot

The shape a CadQuery program has built after one assignment statement, captured while
tracing. `In code:` a trace record's `snapshots` entry.

### Shape snapshot measurement

A Measurement taken over a Shape snapshot: its volume, bounding box, centroid, or topology
counts. `Distinct from:` the Shape snapshot itself, which is the shape these measurements
describe. Measurement scope `snapshot_state`.

---

### CAD ontology graph

The typed graph of a CadQuery program.

---

### CAD ontology node

A typed entity in a CAD ontology graph (for example feature, workplane, profile, face,
edge, vertex, path, selector). `Distinct from:` code node.

---

### Relation

A typed edge between two CAD ontology nodes.

---

### Relation family

A group of relation types, used to categorize a CAD-QA dataset row.

---

### Measurement

A typed numeric or geometric fact about a CAD ontology node.

---

### CadQuery selector

A CadQuery expression that picks topology entities (for example `.faces(">Z")`).

---

### CadQuery workplane

The coordinate frame a CadQuery sketch or feature is built in.

---

### CadQuery profile

The 2D shape drawn on a CadQuery workplane (circle, rectangle, polyline).

---

### CAD feature

A modeling feature of a CadQuery program — an extrude, a cut, a fillet, and so on. A CAD
ontology node type.

---

### CAD feature-added region

The geometry a CAD feature adds. `In code:` `material_region`.

---

### CAD feature-removed region

The geometry a CAD feature removes. `In code:` `void_region`.

---

### CAD-QA dataset row

One question instance — a single record in the dataset file holding every field: the
public prompt plus the private verifier material (gold answer, Gold query program,
candidate-set trace, clue map).

#### Public CAD-QA dataset row column set

The answer-free columns of a CAD-QA dataset row: the prompt and metadata, with the gold
answer, Gold query program, candidate-set trace, and clue map withheld.

#### Private CAD-QA dataset row column set

The verifier columns of a CAD-QA dataset row: gold answer, Gold query program,
candidate-set trace, and clue map.

The two column sets are written as separate release artifacts (`public`, `private`) so the
answer never travels with the prompt.

---

### Gold query program

The hidden, deterministic program a CAD-QA dataset row is generated from, whose result is
the gold answer.

---

### Gold query predicate

One predicate of a Gold query program, mapped to exactly one public clue.
`In code:` `Clause`.

**Why "predicate".** A predicate is the part of a statement that says something about its
subject — describing a state or condition, and so being true or false of that subject
(grammar and logic agree here). For the clue *"the target face is adjacent to another
face"*, the subject is *the target face* and the predicate is *"is adjacent to another
face"*. A Gold query predicate is that part alone — the condition with the subject left
open — stored once and tested against every candidate: *"is adjacent to another face"*,
*"is made by an extrude operation"*, *"has more than three entities"*, *"has a surface area
of 12.5"*. The program is a short ordered list of these, and the public prompt states each
as one clue. `Distinct from:` the aggregation and tie-break steps, which rank the survivors
rather than test them.

---

### Answer candidate set

The set of CAD ontology nodes still possible as the gold answer as a Gold query program
resolves; each Gold query predicate narrows it, and it should end at one node.

### Answer candidate set trace

The record of how the answer candidate set narrows to the gold answer.
`In code:` `CandidateSetTrace`. `Distinct from:` **CadQuery program operation trace**, **agent training trace**.

---

### Gold answer

The verifier-backed correct answer for a CAD-QA dataset row.

---

### Reasoning hop count

The number of reasoning steps a CAD-QA dataset row requires. `In code:` `logical_hop_count`
on the row, `hop_count` on the Gold query program — one concept under two names, a
divergence to unify.

#### Syntactic reasoning hop count

Reasoning hops resolvable from the CadQuery program's structure alone, without geometry.

#### Geometry reasoning hop count

Reasoning hops that require geometry evidence. Syntactic + geometry = Reasoning hop count.

---

### Difficulty tier

A coarse difficulty label for a CAD-QA dataset row.

---

### Query verifier

The deterministic authority for whether a query resolves uniquely, and what its gold
answer is.

---

### Non-release-ready CAD-QA dataset row

A CAD-QA dataset row that resolves but cannot be released.

---

### Agent training trace

A record of reasoning followed by a tool call, produced to train an agent and used as
supervision. `Distinct from:` **CadQuery program operation trace**, **answer candidate set trace**.

---

### Submit tool

The typed answer tools an LLM model emits to answer (`submit_label`, `submit_number`, …).

---

### run_code

The sandboxed Python/NumPy compute tool available to the LLM model.

---

### compact_trace

A tool that shortens reasoning while an agent training trace is produced.

---

## Enums

### Answer format

The shape of an answer: `candidate_label`, `coordinate`, `text`, `number`, `integer`,
`boolean`, `bbox`, or `json`.

---

### Measurement scope

Where a Measurement comes from: `profile_intrinsic`, `feature_application_effect`,
`entity_geometry`, `snapshot_state`, or `relation_metric`. Used to avoid category errors.

---

### Dataset release tier

The readiness bar a dataset is validated against: `smoke`, `release-candidate`, or
`benchmark-release`.

---

### LLM harness mode

Which compute tools an LLM model gets during evaluation.

#### numpy LLM harness

The primary harness: a Python shell with NumPy.

#### no_tools LLM harness

Reasoning only; no compute.

#### cadquery LLM harness

Full CadQuery kernel access; one correct call suffices.

---

## Internal

### dataset_generation

The code package that builds the benchmark. `In code:` `dataset/`.

---

### train_and_eval

The code package for training and evaluation.

---

### Dataset file

The file holding the CAD-QA dataset rows (`rows.parquet` or `rows.jsonl`); the
input/output contract between `dataset_generation` and `train_and_eval`.

---

### Harbor

The environment and runner used to evaluate cost-effective LLM models on the benchmark.

---

## Don't say

A ratchet: entries are removed only when the term is engineered out of the docs and code.
A docs sweep replaces each don't-say usage with its Say term until the checkers are green.
A `(home)` annotation allows the token under that tree (`dataset`, `train_and_eval`, `tools`,
…), for identifiers documented as `In code:`; the checker's `ALLOWLIST` exempts
cross-cutting phrases. Enforced by `tools/check_dont_say.py`.

| Don't say | Say | Why |
|---|---|---|
| source | CadQuery program | bare noun; "source" of what? |
| release tier (dataset, train_and_eval, tools) | Dataset release tier | garbled; which release? |
| snapshot | Shape snapshot | opaque |
| CADEvolve | (name the corpus in prose) | proper noun, not a term |
| ontology graph (dataset) | CAD ontology graph | unqualified |
| ontology (bare) | CAD ontology | generic/overloaded |
| selector (bare) | CadQuery selector | CadQuery-specific |
| workplane (bare) | CadQuery workplane | CadQuery-specific |
| profile (bare) | CadQuery profile | generic |
| material region (dataset) / void region (dataset) | CAD feature-added region / CAD feature-removed region | unclear |
| dataset row (dataset) | CAD-QA dataset row | which dataset? |
| public row / private row | Public CAD-QA dataset row column set / Private CAD-QA dataset row column set | not separate rows; column sets of one row |
| query program (dataset, tools) | Gold query program | conflated with a general query |
| clause | Gold query predicate | wrong; not a logic clause |
| candidate set (dataset, train_and_eval, tools) | answer candidate set | unqualified |
| candidate trace (dataset, tools) | answer candidate set trace | candidate to what? |
| hop count (dataset, train_and_eval) | Reasoning hop count | unqualified |
| difficulty bucket (dataset, train_and_eval, tools) | Difficulty tier | "bucket" imprecise |
| harness mode (dataset, train_and_eval, tools) | LLM harness mode | unqualified |
| verifier (bare) | Query verifier | unqualified |
| quarantine | Non-release-ready CAD-QA dataset row | imprecise |
| rows artifact | Dataset file | "artifact" is vague; it is the dataset file |
| harness row | CAD-QA dataset row | same record after decoding; not a new concept |
| "intent" (as a doc) | PRD | "intent" is the concept, not the artifact |
| trace (bare) | CadQuery program operation trace / agent training trace / answer candidate set trace | overloaded across concepts |
| model (bare) | CAD model / LLM model / base LLM model / LLM adapter / merged LLM model | geometry vs language model vs weights/adapter/served endpoint |
| node (bare) | CAD ontology node / code node | ambiguous between graph and code |
| kind / kinds | predicate kind | raw noun; name the kind of what |
| type / types | CAD ontology node type / relation type / answer format / measurement scope / LLM harness mode | raw noun; name the type of what |
| entity id (in a public answer) (dataset, tools) | source variable | internal `entity_id` values must not leak into public answers |
| "the pipeline" / "the object" / "the value" | name the concept | unspecific placeholder |
| first/last (as family semantics) | the sampled parameter | a rendering choice, not a permanent meaning |

---

## Proposed additions

Terms the specs use that still need a definition; each is added only with owner approval.
task family · intended family · answer contract · answer spec · sampled parameters ·
evidence tier · prompt template · clue map · release-ready · split / split group ·
geometry-critical · geometry-hop-positive · shortcut resistance · stop gate · candidate
label · source variable · path point / path segment / edge endpoint · tool declaration ·
native tool-call format · curriculum · compaction · held-out row · tool-valid · baseline ·
grader · closed-book · harness (the runner, distinct from **LLM harness mode**) · Harbor task ·
slice (rc10 / release10k / clean-100) · tool-assisted upper bound.
