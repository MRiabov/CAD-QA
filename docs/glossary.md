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
- **No bare single-letter symbol.** A quantity or an index of our own is never written as a
  bare letter — `k`, `T`, `r`, `N`, or similar. Name the quantity (`rollout count`,
  `rollout temperature`, `pass rate`, `sample size`); an `In code:` identifier keeps its
  documented name. Established external notation (`pass@k`, a LoRA rank) keeps its standard
  symbol.
- **Meaning, not implementation.** An entry says what the term means, and optionally why
  that word is used (`Distinct from:`, never-say). It never says how something works —
  that belongs in the specs. Names of types, tables, routes, or `In code:` identifiers may
  appear so code can match the term.
- **One concept, one word.** A term names one thing; a thing has one term.
- **Approval.** A definition is a proposal until the owner approves it. Definitions are
  added or changed with the owner's agreement, never autonomously.
- Don't-say words appear only in the *Don't say* table and in never-say listings. A docs
  sweep replaces don't-say usage with the Say term until the checkers are green.
- **Separate 3D model terms from software terms.** A 3D model term and a software or
  code term are different terms even when they share a word. Qualify the term with its
  domain, and do not use a 3D word as a metaphor for a software concept. For example,
  **depth** is a CAD measurement (`cut depth`, `hole depth`); the reasoning measure is
  **task reasoning step count**, never "reasoning depth."
- **Do not use permission words for dataset parts.** `public` and `private` are access
  scopes. For dataset content, say **prompt** or **task file** for what the LLM model
  sees, and **answer** or **answer data** for the gold answer and scoring material.
- **Task text stays domain-level.** Do not use variable names, internal IDs, or generator
  terms in questions, clues, choices, or answer instructions. Describe an entity by its
  geometry or its role in the construction. Code belongs in the program text.

| Shared word | 3D model term | Software, code, or reasoning term |
|---|---|---|
| depth | cut depth, hole depth | task reasoning step count |
| edge | CAD edge | graph edge |
| feature | CAD feature | software feature |
| path | CadQuery path | file path |
| profile | CadQuery profile | performance profile |
| vertex | CAD vertex | graph vertex |

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

### Shape snapshot

The shape a CadQuery program has built after one assignment statement, captured during
runtime extraction. `In code:` a runtime extraction result's `snapshots` entry.
`Distinct from:` **solid state**, the CAD graph entity that represents the same shape.

### Shape snapshot measurement

A Measurement taken over a Shape snapshot: its volume, bounding box, centroid, or topology
counts. `Distinct from:` the Shape snapshot itself, which is the shape these measurements
describe. Measurement scope `snapshot_state`.

---

### CAD graph

The typed graph of CAD graph entities, CAD graph relations, and CAD graph measurements for
one CadQuery program.

---

### CAD graph entity

A typed entity in a CAD graph (for example feature, workplane, profile, face, edge,
vertex, path, selector). `Distinct from:` code node. `node_id` and `nodes.parquet` are
code and schema names.

---

### CAD graph relation

A typed link between two CAD graph entities.

---

### CAD graph relation family

A group of CAD graph relation types, used to categorize a CAD-QA dataset row.

---

### CAD graph measurement

A typed numeric or geometric fact about a CAD graph entity or a pair of CAD graph
entities.

---

### CadQuery selector

A CadQuery expression that picks topology entities (for example `.faces(">Z")`).

---

### CadQuery selector result

The CAD topology entities selected by one CadQuery selector, with the selector and the
solid state it ran on. `Distinct from:` the CadQuery selector itself.

---

### CadQuery workplane

The coordinate frame a CadQuery sketch or feature is built in.

---

### CadQuery profile

The 2D shape drawn on a CadQuery workplane (circle, rectangle, polyline).

---

### CAD feature

A modeling feature of a CadQuery program — an extrude, a cut, a fillet, and so on. A CAD
graph entity type.

---

### CAD feature-added region

The geometry a CAD feature adds. `In code:` `material_region`.

---

### CAD feature-removed region

The geometry a CAD feature removes. `In code:` `void_region`.

---

### CAD feature effect delta

The measured before/after volume, bounding box, and topology change caused by a CAD
feature. `Distinct from:` the Measurement scope `feature_application_effect`, which names
where a Measurement belongs rather than the delta record.

---

### CAD topology entity

A face, edge, or vertex of a solid state.

---

### CAD-QA dataset row

One task instance — a single record in the dataset file holding every field: the
prompt plus the answer data (gold answer, Gold query program, candidate-set trace,
clue map).

#### CAD-QA dataset row prompt column set

The columns the LLM model sees: the prompt and metadata, with the gold answer,
Gold query program, candidate-set trace, and clue map withheld.

#### CAD-QA dataset row answer column set

The columns used for scoring: gold answer, Gold query program, candidate-set
trace, and clue map.

The two column sets are written as separate release artifacts so the answer never
travels with the prompt.

---

### Gold query program

The hidden, deterministic program a CAD-QA dataset row is generated from, whose result is
the gold answer.

---

### Gold query predicate

One predicate of a Gold query program, mapped to exactly one task clue.
`In code:` `Clause`.

**Why "predicate".** A predicate is the part of a statement that says something about its
subject — describing a state or condition, and so being true or false of that subject
(grammar and logic agree here). For the clue *"the target face is adjacent to another
face"*, the subject is *the target face* and the predicate is *"is adjacent to another
face"*. A Gold query predicate is that part alone — the condition with the subject left
open — stored once and tested against every candidate: *"is adjacent to another face"*,
*"is made by an extrude operation"*, *"has more than three entities"*, *"has a surface area
of 12.5"*. The program is a short ordered list of these, and the prompt states each
as one clue. `Distinct from:` the aggregation and tie-break steps, which rank the survivors
rather than test them.

---

### Answer candidate set

The set of CAD graph entities still possible as the gold answer as a Gold query program
resolves; each Gold query predicate narrows it, and it should end at one node.

### Answer candidate set trace

The record of how the answer candidate set narrows to the gold answer.
`In code:` `CandidateSetTrace`. `Distinct from:` **CadQuery program runtime extraction result**, **agent training trace**.

---

### Gold answer

The verifier-backed correct answer for a CAD-QA dataset row.

---

### Reasoning hop count

The number of reasoning steps a CAD-QA dataset row requires. `In code:` `logical_hop_count`
on the row, `hop_count` on the Gold query program — one concept under two names, a
divergence to unify. `Distinct from:` **task reasoning step count**, the dataset
terminology's clearer name; the glossary will adopt it when that terminology is
merged. **depth** is a CAD measurement and is not used for this count.

#### Syntactic reasoning hop count

Reasoning hops resolvable from the CadQuery program's structure alone, without geometry.

#### Geometry reasoning hop count

Reasoning hops that require geometry evidence. Syntactic + geometry = Reasoning hop count.

---

### Difficulty tier

A coarse difficulty label for an older CAD-QA dataset row. `Distinct from:`
**task reasoning step count**, the measure the replacement dataset uses; the
replacement does not use a difficulty label or score.

---

### Rejection sampling

Keeping only the sampled completions the Query verifier accepts. One technique, two sources: **teacher
rejection sampling** keeps the **teacher's** accepted traces (distillation; pipeline step 02);
**RFT** keeps the **policy's** accepted traces (self-distillation). Name the source when ambiguous.

---

### RFT (rejection-sampling fine-tuning)

SFT on the **tuned policy's own** Query-verifier-correct completions — self-distillation (STaR-style).
Distinct from teacher distillation: `02-teacher-sampling` keeps the teacher's accepted traces. It
requires the policy to already produce accepted completions (`pass > 0`).

---

### RL-readiness gate

The post-SFT check that samples rollouts from the tuned policy and measures the per-prompt pass rate to
classify Reasoning-hop tiers (`mastered` / `learnable` / `unreachable`) and decide whether RL is
indicated. `In code:` to build; `train-and-eval/fine-tuning/pipeline/05-rl-readiness-gate.md`.
`Distinct from:` the Dataset release gate and the phase gates.

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
supervision. `Distinct from:` **CadQuery program runtime extraction result**, **answer candidate set trace**.

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

### External dataset

A dataset published outside CAD-QA and used as support data (tool format, reasoning style,
anti-forgetting replay, domain priming), never as the CAD-QA task itself. Registered with its
license and a pinned revision. `Distinct from:` **Mixed training dataset** (built from these) and
**Training stage** (a run that consumes the blend).

---

### Mixed training dataset

The materialized set of training rows for one run: **External dataset** sources blended at fixed
weights, defined as dataset role → weight. `Distinct from:` **External dataset** (a source, not a
blend) and **Training stage** (a run, not a dataset). `In code:` `mixed_dataset_<composition>`.

---

### Training stage

One run in the training schedule; it consumes a **Mixed training dataset** and has an
advancement gate. Qualify it — a bare "stage" means a pipeline stage. `In code:`
`training_stage_<nn>_<purpose>`, never bare `stage_<...>`.

---

## Enums

### Answer format

The shape of an answer: `candidate_label`, `coordinate`, `text`, `number`, `integer`,
`boolean`, `bbox`, or `json`.

---

### Measurement scope

The provenance category of a Measurement — the aspect of the CAD program the fact describes.
Each Measurement has exactly one:

- `profile_intrinsic` — a property of the profile itself: area, perimeter, local bbox, counts.
- `feature_application_effect` — the delta a CAD feature causes: volume, bbox, topology.
- `entity_geometry` — a node's coordinates, normals, axes, bbox.
- `snapshot_state` — a Shape snapshot's volume, bbox, topology, validity.
- `relation_metric` — a Relation's distance, angle, containment, intersection.

`Distinct from:` the Measurement itself — this names the category, not the value. It keeps
categories from being conflated (an effect delta is `feature_application_effect`, never
`profile_intrinsic`), so attach an effect Measurement to the feature that caused it, not to the
profile it used. A CAD-QA dataset row carries the **set** of scopes its Measurements use.
`In code:` `measurement_scopes` (the per-row set; one Measurement's `scope`).

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

### Dataset role

The purpose a dataset serves: what a training dataset teaches, or how an evaluation dataset's
score is read. `In code:` `DatasetRole`. Training dataset roles: `emit_our_tool_call_format`,
`run_the_tool_call_loop`, `preserve_general_math_and_code_reasoning`,
`expose_general_python_code`, `expose_cadquery_programs`, `learn_the_cadqa_task`. Evaluation
dataset roles are not yet named.

---

### Data pool

The three-way split of eligible CAD-QA rows: `sft_train` (the only rows that enter an SFT mix),
`rl_train` (the RL-readiness gate and RL/RFT pool, held out from SFT), and `eval`
(validation+test; never trained on). `In code:` `DataPool`. The assignment is owned by
`train-and-eval/fine-tuning/data.md` §5 and recorded in `split_manifest.json`.

---

## Internal

### CadQuery program AST extraction result

The result of extracting a CadQuery program without running it: its operations, CadQuery
workplanes, CadQuery profiles, CadQuery paths, CadQuery selectors, and their relationships in the CadQuery program. `In code:` `StaticCadQueryModel`. `Distinct from:` **CadQuery program runtime
extraction result**.

---

### CadQuery program runtime extraction result

The result of executing a CadQuery program and extracting each operation's Shape snapshots,
CAD feature effect deltas, CadQuery selector results, and evidence. `In code:`
`ExecutionResult`. `Distinct from:` **CadQuery program AST extraction result**, **agent
training trace**, **answer candidate set trace**.

---

### CadQuery program AST extraction

The extraction of a CadQuery program without running it. Its output is a **CadQuery program
AST extraction result**.

---

### CadQuery program runtime extraction

The extraction of a CadQuery program by running it. Its output is a **CadQuery program
runtime extraction result** or a **failure tombstone**.

---

### solid state producing operation

A CadQuery program operation that can produce a **solid state**.

---

### CadQuery accessor

A CadQuery call that reads or converts existing values without creating geometry.

---

### AST rejection

A rejected `02a` CadQuery program: program identity, reason, location, and cache key, with
no CadQuery program AST extraction result. `Distinct from:` **failure tombstone**.

---

### CAD topology entity ID

The stable identity of a CAD topology entity within one solid state. `In code:` `entity_id`.

---

### CAD graph element

A CAD graph entity, CAD graph relation, or CAD graph measurement.

---

### failure tombstone

The failed `02b` result: program identity, terminal operation, error category, environment,
and cache key. It is not a CAD graph entity and supports no answer. `Distinct from:`
**CadQuery program runtime extraction result**.

---

### dataset_generation

The code package that builds the benchmark. `In code:` `dataset/`.

---

### train_and_eval

The code package for training and evaluation.

---

### Dataset file

The file holding the CAD-QA dataset rows (`rows.parquet`); the
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
| universe | valid-task set, or the named set | metaphor; name the set instead |
| source corpus | External dataset | unqualified; it is a dataset published outside CAD-QA |
| mix-format | Mixed training dataset | a blend, not a dataset; name it `mixed_dataset_<composition>` |
| mix-full | Mixed training dataset | a blend, not a dataset; name it `mixed_dataset_<composition>` |
| format_tool | emit_our_tool_call_format | old garbled Dataset role name |
| agent_trace | run_the_tool_call_loop | old garbled Dataset role name |
| reasoning_distill | preserve_general_math_and_code_reasoning | old name; it is general, not CAD, reasoning |
| rehearsal | the general tasks | there is no dedicated replay role; the general-task mix anchors prior ability |
| domain_code | expose_general_python_code | "domain" misleads; it is general Python |
| domain_3d | expose_cadquery_programs | "domain"/"prime" jargon |
| cadqa_hop | learn_the_cadqa_task | old garbled Dataset role name |
| eval_canary | evaluation dataset role | old name; evaluation roles are not yet named |
| imitate_general_reasoning_style | preserve_general_math_and_code_reasoning | earlier name; a preservation role, not style imitation |
| release tier (dataset, train_and_eval, tools) | Dataset release tier | garbled; which release? |
| snapshot | Shape snapshot | opaque |
| ontology graph (dataset) | CAD graph | unqualified |
| ontology (bare) | CAD graph | generic/overloaded |
| selector (bare) | CadQuery selector | CadQuery-specific |
| workplane (bare) | CadQuery workplane | CadQuery-specific |
| profile (bare) | CadQuery profile | generic |
| material region (dataset) / void region (dataset) | CAD feature-added region / CAD feature-removed region | unclear |
| dataset row (dataset) | CAD-QA dataset row | which dataset? |
| public row / private row | CAD-QA dataset row prompt column set / CAD-QA dataset row answer column set | permission words; not separate rows |
| query program (dataset, train_and_eval, tools) | Gold query program | conflated with a general query |
| clause | Gold query predicate | wrong; not a logic clause |
| candidate set (dataset, train_and_eval, tools) | answer candidate set | unqualified |
| candidate trace (dataset, train_and_eval, tools) | answer candidate set trace | candidate to what? |
| hop count (dataset, train_and_eval) | Reasoning hop count | unqualified |
| difficulty bucket (dataset, train_and_eval, tools) | Difficulty tier | "bucket" imprecise |
| harness mode (dataset, train_and_eval, tools) | LLM harness mode | unqualified |
| closed-book | no_tools LLM harness / no access to CadQuery | overloaded: "no compute tools" vs "no access to CadQuery" |
| open-book | having access to CadQuery | bare antonym; name the access |
| verifier (bare) | Query verifier | unqualified |
| quarantine | Non-release-ready CAD-QA dataset row | imprecise |
| frozen | immutable | imprecise metaphor; name the state |
| rows artifact | Dataset file | "artifact" is vague; it is the dataset file |
| harness row | CAD-QA dataset row | same record after decoding; not a new concept |
| "intent" (as a doc) | PRD | "intent" is the concept, not the artifact |
| trace (bare) | CadQuery program runtime extraction result / agent training trace / answer candidate set trace | overloaded across concepts |
| model (bare) | CAD model / LLM model / base LLM model / LLM adapter / merged LLM model | geometry vs language model vs weights/adapter/served endpoint |
| node (bare) | CAD graph entity / code node | ambiguous between graph and code |
| stage (bare) | Training stage / pipeline stage | which stage? qualify it |
| surface (bare) | scope / interface | imprecise metaphor; name the scope or interface |
| RL-readiness gate | RL-readiness gate | "sampling of what?" |
| RL-readiness gate | RL-readiness gate | ambiguous |
| gate (bare) | RL-readiness gate / release gate / phase gate / quality gate / review gate / coverage gate / regression gate / stop gate / forgetting gate / format gate / evaluation gate / test gate / advancement gate / blocking gate / freeze gate / smoke gate / trust-audit gate | name which gate |
| band | RL-eligible pass rate / range | imprecise; name the RL-eligible pass rate, or the range |
| kind (bare) / kinds (bare) | predicate kind | raw noun; qualify it |
| type (bare) / types (bare) | CAD graph entity type / CAD graph relation type / clue type / answer format / measurement scope / LLM harness mode | raw noun; qualify it |
| entity id (in an answer) (dataset, train_and_eval, tools) | source variable | internal `entity_id` values must not leak into answers |
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
grader · harness (the runner, distinct from **LLM harness mode**) · Harbor task ·
slice (rc10 / release10k / clean-100) · tool-assisted upper bound.
