# 03b — Construct task definitions

**Parent:** [`03-task-generation.md`](../03-task-generation.md).

**Purpose:** construct persisted task definitions into the task quota plan: task
target, ordered task clues, task answer step, gold answer, validity record, and
canonical identity.

**Input/output contract:** [`io-contracts.md`](../io-contracts.md).

## Input / output

- Input: `CadGraph`, `TaskQuotaPlan`, and the current `DeficitLedger` on resume
  (empty on the first run).
- Output: `TaskDefinition` records and the updated `DeficitLedger`.

## Task definition

A `TaskDefinition` is the complete, answer-bearing construction record for one
task. It is not prompt text and not a loose task tuple. It is what `04` renders.

| Field | Meaning |
|---|---|
| `task_id` | `cadqatask:<sha256>` over the canonical task identity. It does not encode the gold answer. |
| `definition_sha256` | Hash of the canonical task content and the inputs that change it. Assignment is excluded. The provenance block is not hashed as a block, but the provenance inputs that change the content are covered. |
| `answer_sha256` | Hash of the answer and scoring fields, computed at construction and copied by `04`. It excludes `answer_evidence`. |
| `program_id`, `program_sha256` | CadQuery program identity. |
| `cadevolve_program_family_id` | Program family used for split isolation. |
| `split`, `subset` | Split and warmup/main label assigned by `03a`. |
| `graph_schema_version`, `definition_schema_version` | Versions needed to reproduce the definition. |
| `state_scope` | Which solid states the task may refer to. `final` in P0 (`DS-34`). |
| `target_category` | Task target category from `requirements/task-structure.md`. |
| `target_binding` | The concrete graph entity or measurement instance the task asks about. |
| `task_clues` | Ordered typed task clues. |
| `clue_operand_form_profile` | The ordered `(clue_type, clue_operand_form)` pair for every clue. Derived from `task_clues`. |
| `answer_meaning`, `task_answer_step` | What the answer is about and the step that produces it. |
| `answer_parameter` | The point for a position or a membership, the category for a topology change, null otherwise. |
| `native_answer_format`, `answer_format` | The meaning's native format and the format the prompt will request. |
| `gold_answer`, `answer_unit`, `tolerance`, `scoring_rule` | Answer data. `gold_answer` and `tolerance` are canonical text, matching the release columns. |
| `answer_schema_version` | Version of the answer representation: the answer formats, the canonical text rules, and the answer evidence shape. Hashed by `answer_sha256`. |
| `answer_evidence` | Measured or derived evidence as canonical JSON text: rule, references, the answer-equivalent set, and the point probe. `04` copies it into the release column. |
| `choice_pool` | The ordered, labeled options when multiple choice is planned: label, answer value, distinguishing graph facts, and the P2 error mode. Empty otherwise. |
| `task_clue_step_count`, `task_reasoning_step_count` | Step accounting. |
| `geometry_required` | Whether at least one task clue depends on the built shape. |
| `validity_record` | Typed check results and the answer-uniqueness result. |
| `provenance` | Constructor version, seed, and input versions. Assignment, not content. |

The definition must be sufficient to reproduce the task without re-running task
construction. `04` may render text, but it must not reorder or relabel the choice
pool, bind a new target, compute the answer, or decide validity.

## Graph input boundary

`03b` reads the CAD graph and the `TaskQuotaPlan`. Every task target, clue operand,
answer value, and piece of answer evidence must resolve to a graph entity, a
graph relation, or a measurement. A task definition that needs a missing graph element
is rejected; it is not softened or filled with program-text heuristics.

The graph observation that starts a chain is input. It is not a task reasoning
step. If a task clue states the observation, that clue is a step.

## Target binding

The task target is bound in one of two ways:

- directly, when the question names a task target category with exactly one instance
  in the program, such as the final solid state;
- by the ordered task clues, when the first clues narrow the possible answers to
  one target.

The binding must resolve to exactly one entity or scalar value. A task target
category whose binding is ambiguous is rejected. For a scalar target, the binding
is a measurement instance: the subject, the measurement, and its value. The
subject need not be unique, because the answer is that measurement value. A task
target and an answer measurement are different: the target is the entity or
value the task asks about; the answer meaning says what is reported about it.

## Task clue predicate schema

A task clue is one typed predicate. It is not a sentence template.

Every `TaskClue` has:

| Field | Meaning |
|---|---|
| `clue_id` | Stable within the task definition. |
| `order` | Position in the task solution sequence. |
| `clue_type` | Property, relation, comparison, aggregation, or provenance. |
| `subject` | Binding reference the clue constrains. |
| `check` | One typed check variant. |
| `result` | Before/after possible-answer counts, bound entities, and answer evidence. |

A `BindingRef` is one of:

- the task target;
- a result of an earlier task clue;
- a named graph element;
- a literal value.

When a clue has a reference binding other than the task target, the binding
carries `clue_operand_form` (`DS-31`):

| Clue operand form | Binding | Example |
|---|---|---|
| `named` | a named graph element | "adjacent to the cylindrical face" |
| `selected` | a result of an earlier task clue | "adjacent to the face selected in step 1" |
| `aggregated` | an extreme, rank, or count over a set | "adjacent to the largest face of the hole" |
| `cross_state` | a before/after solid state pair | P2 only |

A clue with no reference has no clue operand form. A property clue that refers to
another entity is two clues and is split into two list items.

The typed check variants are:

| Clue type | Check fields |
|---|---|
| Property | `measurement`, `comparator`, `threshold` or `range`. |
| Relation | `relation_type`, `object`. |
| Comparison | `measurement`, `comparator`, `reference`. |
| Aggregation | `scope`, `aggregation_kind`, `measurement`, `rank` or extreme. |
| Provenance | `operation_id`, `profile_id`, or `workplane_id`. |

Every task clue must narrow the possible answers: its `after` count is smaller
than its `before` count. A clue that does not narrow is not a task clue step and
the definition is rejected. A list item that states two conditions is two task
clues.

The definition also records `clue_operand_form_profile`, the ordered
`(clue_type, clue_operand_form)` pair for every clue. It is derived from
`task_clues` at construction and never authored separately. `05` validate and
export release checks that its clue types match `clue_types` and uses the forms
for clue operand form coverage.

A comparison may name both entities or refer to one selected by an earlier task
clue. The reference must resolve to exactly one entity; otherwise the comparison
needs an explicit aggregation or the task is rejected.

## Answer step and answer format

The answer step produces the answer after the target is identified. It is absent
only when the answer is the target identity; otherwise it is one task reasoning
step.

The answer meaning determines the native answer format:

| Answer meaning | Native answer format |
|---|---|
| Identity | Multiple choice. |
| Volume, area, length, distance, angle | Number. |
| Count, rank | Integer. |
| Membership, validity | Yes or no. |
| Position | 3D coordinate. |
| Extent | Bounding box. |
| CadQuery workplane state | Structured object. |
| Material change | Number for a volume effect; integer for a count effect. |
| Topology change | Integer for a count change. |

Multiple choice is a presentation wrapper valid for every answer meaning when
the definition carries enough real choices. The native format is still recorded.
A format that cannot express the meaning is not used; for example, identity is
not returned as a number and position is not returned as a scalar.

The choice pool is a construction output (`DS-36`). Identity answers draw options
from the penultimate answer candidate set; numeric answers draw them from the
distinct answers of that set. Fewer than five real options rejects the task.
`04` renders the pool in the recorded order.

The answer must be produced by CadQuery execution or by an exact derivation from
the program and its geometry, with answer evidence. A guessed or approximate
answer is not valid.

### Multiple-choice choices

A pool entry is typed:

| Field | Meaning |
|---|---|
| `label` | The position label, `A` to `G`. |
| `candidate` | The answer value, as canonical text in the same representation as `gold_answer`. |
| `distinguishing_facts` | The graph facts the choice description is rendered from. |
| `error_mode` | Why a P2 near-miss is wrong. Null in P0 and P1. |

`03b` orders the pool by a stable hash of `(task_id, candidate)` and assigns
labels from the fixed alphabet `A` to `G` in that order. The order and the labels
are therefore construction output: the correct answer is not always in the same
position, no render step chooses a position, and the pool is hashed with its
labels.

For a multiple-choice task, `gold_answer` is the label. A label is a position,
not an answer: the answer value is the `candidate` the label denotes, and
`answer_evidence` records it. `05` validate and export release counts the
candidate, not the label, when it counts distinct answers.

The pool checks run at construction, on the pool:

| Check | Holds when |
|---|---|
| Pool size | At least five entries and at most seven, because the alphabet ends at `G`. Seven is the goal. |
| Correct choice | `gold_answer` is one of the pool labels. |
| Answer space | Every `candidate` is a valid answer under `answer_format`: the same task target category for identity, the same unit and precision for a number, the same frame for a coordinate, and the documented fields for a structured answer. |
| Distinctness | No two entries hold the same answer under `same_answer`. |
| Real candidates | Every entry comes from the penultimate answer candidate set. None is padding. |
| Fact basis | Every entry's `distinguishing_facts` are geometric or construction facts from the graph, not free text. |
| Fact uniqueness | No two entries share the same `distinguishing_facts`. |
| Fact cleanliness | No fact is a variable name or an internal identifier, and no fact states the answer value. |
| Labels | Labels are contiguous from `A`, with no repeat. |
| P2 near-miss | Every near-miss fails at least one task clue or the answer step, and its `error_mode` is recorded. |

The first nine rows are P0. The P2 row is deferred.

`04` renders the descriptions and checks the rendered choice block: one line per
pool entry, in the pool's order, with the pool's labels; the description text
distinct across entries; and no description stating the answer value. A mismatch
is a defect in the template or the renderer, not a reason to reject the task.

`05` rechecks the released pool in the `choices` column: the entry count, the
labels, `same_answer` distinctness, that `gold_answer` is one of the labels, and
that the label's `candidate` is the answer in `answer_evidence`'s
answer-equivalent set. It does not recheck the construction facts, because the
release does not carry the graph.

### Answer resolver

The resolver turns the bound target and the penultimate answer candidate set into
the answer value and its evidence:

```text
resolve_answer(answer_meaning, bound_target, answer_parameter, penultimate_set)
  -> (answer_value, answer_evidence)
```

| Answer meaning | Answer value | Evidence |
|---|---|---|
| Identity | The entity the whole answer-equivalent set shares. | The set and the binding. |
| Volume | The volume of the bound solid state. | Kernel volume. |
| Area | The area of the bound face or profile. | Kernel area. |
| Length | The length of the bound edge or path segment. | Kernel length. |
| Distance | The shortest distance between the bound pair, or between the point and the entity. | Kernel distance. |
| Angle | The graph angle for the pair, with the convention in `graph-content.md`. | Graph measurement. |
| Count | The number of entities in the bound set. | Set size. |
| Membership | Inside or outside, from the point probe. | Probe classification. |
| Position | The declared point: face centroid, edge midpoint, vertex point, or solid state centroid. | Kernel point or graph centroid. |
| Extent | The minimum and maximum corner of the bounding box in the program frame. | Graph bounding box. |
| Material change | The signed volume or count the bound operation adds or removes. | Signed volume change or feature count. |
| Topology change | The signed change in the declared category. | Topology change. |

When the task is multiple choice, `gold_answer` is the pool label whose
`candidate` equals this answer value, not the answer value itself. The answer
value stays in `answer_evidence` and in `choice_pool`.

`answer_parameter` is null for every meaning that declares nothing. It carries
the point for a position or a membership and the category for a topology change.
A material change declares no parameter: its sign carries the direction, so a cut
answers a negative number.

The membership point is both the question parameter and the point the probe
classifies, bound once. `04` renders the question from `answer_parameter`, so it
does not parse the evidence to find the point.

P1 and P2 meanings get a row when their implementation scope is built. The
resolver never guesses: a missing target or a missing graph measurement rejects
the task rather than producing an approximate answer.

### Membership answers

A membership answer is computed by `is_inside(solid_state, point)`. The point comes
from a point probe in the graph (`graph-content.md` section 2.1); the task
definition copies its coordinates and its classification, so `03b` never needs a
kernel. The answer is inside or outside. A point within the geometric
clear-case margin of the face surface is not used, because "on the boundary" is a third case
that the binary answer cannot express. The classification is measured evidence
and records the point, the solid state hash, and the classifier.

### Answer evidence

`answer_evidence` is one typed record, persisted as canonical JSON text:

| Field | Meaning |
|---|---|
| `evidence_kind` | `measured` or `derived`, from `graph-content.md` section 4.3. |
| `evidence_rule` | The rule that produced the answer. |
| `evidence_refs` | The graph entity, relation, and measurement references the rule used. |
| `answer_equivalent_set` | The final possible-answer set: one entry per remaining candidate, with its subject and its answer. |
| `point_probe` | The point, its classification, the solid state reference, and the classifier. Null unless the answer is membership. |

`answer_equivalent_set` is stored so answer uniqueness can be rechecked from the
definition alone, without the graph. Every entry's answer must equal the answer
value under `same_answer`; an identity answer requires exactly one entry. An
entry's subject is a `node_id` for an entity target and the measurement name for
a scalar target.

### Answer equality

`same_answer(left_answer, right_answer)` is the comparison used for answer
uniqueness and for scoring
(`DS-32`). It is not a margin; it is canonical equality at the answer's stated
precision.

| Answer meaning | `same_answer(left_answer, right_answer)` |
|---|---|
| identity | the two answers are the same entity |
| volume, area, length, distance, angle | same canonical string at the stated precision |
| count, rank | same integer |
| membership | same label: inside, outside, or on the boundary |
| validity | same boolean |
| position | same point at the stated precision, component by component |
| extent | same minimum and maximum corner at the stated precision |
| CadQuery workplane state | same origin and frame at the stated precision |
| material change | same added and removed volume at the stated precision |
| topology change | same face, edge, and vertex counts, and the same changed set |

The precision comes from the answer format and the release scoring rule:

| Answer format | Precision |
|---|---|
| integer, count, rank | exact integer equality |
| number, coordinate, bounding box | canonical rounding, 4 significant figures by default |
| yes or no, membership, validity | label equality |
| structured object | componentwise under the same rules |

## Validity

A task definition is valid only when all of these hold:

- every task clue is satisfied by the bound entities;
- every task clue narrows the possible answers;
- every task clue is necessary: removing it leaves at least two distinct answers,
  or changes the answer;
- every predicate a task uses is decided by at least the clear-case margin;
- every candidate in the answer-equivalent set produces the same answer under
  `same_answer`; an identity answer requires a singleton set (`DS-32`);
- for a scalar target, every remaining instance has the same value;
- the answer step produces exactly one gold answer;
- the target binding is unambiguous;
- the program family and split are present;
- the split matches the family assignment from `03a`;
- the subset is consistent with the task reasoning step count;
- the answer has answer evidence;
- for multiple choice, the choice pool passes every P0 row of the
  [multiple-choice check list](#multiple-choice-choices);
- for P2 multiple choice, every near-miss choice fails a task clue or the answer
  step, and its `error_mode` is recorded;
- the task definition is unique under canonical identity;
- `geometry_required` is recorded: at least one task clue depends on the built
  shape.

An invalid definition is recorded as a failure with a reason and is not passed to
`04`. A task with an ambiguous target, an answer-equivalent set that disagrees
under `same_answer`, or an unverifiable answer is invalid.

### Validity record

`validity_record` is typed, not prose:

| Field | Meaning |
|---|---|
| `checks` | One entry per validity rule below: the check name, the outcome, and a detail string. |
| `answer_equivalent_size` | The number of entries in `answer_equivalent_set`. |
| `same_answer_holds` | Whether every entry's answer equals the answer value. |

The check name is a closed set, one name per rule. `geometry_required` is its own
field rather than a check entry, because `04` copies it to the release row.

## Task reasoning step accounting

`task_reasoning_step_count` is:

```text
task_clue_step_count + 1 if the task needs an answer step, otherwise task_clue_step_count
```

The lowest step count is 1. There are no 0-step tasks. The graph observation is
not counted; the number of prompt sentences is not counted.

Example:

```text
observation -> clue A -> clue B -> clue C
```

- If `C` is the target identity: 3 steps.
- If the task asks for a measurement of `C`: 4 steps.

A clue that can be removed without losing answer uniqueness is redundant, so the
achievable step count is the number of necessary clues plus the answer step. A
quota target above that count is a deficit, not a reason to keep a redundant clue.

## Enumeration and identity

`03b` constructs task definitions from the graph into the task quota plan using typed
constructors. Construction is supply-driven: it builds from the facts the graph
has and samples them into the quota targets (`DS-33`). A cell-level demand query
is a deficit-path last resort, not the default. Construction is deterministic for
a given graph, plan version, definition-schema version, and seed. Constructor
order is stable and fixed by `constructor_version`. A quota target that cannot be filled becomes a deficit for `03c`.

Canonical task identity is:

```text
(program_sha256, target binding identity, canonical task clue sequence, answer meaning)
```

For a scalar target, the target binding identity is the measurement name. The
subject is not part of it, because several subjects can share that measurement
value.

The canonical task clue sequence preserves dependency order first, then orders
independent clues broad-to-narrow by the size of the narrowed set, descending,
with a stable hash as the tie-break (`DS-35`). The gold answer, answer format,
choices, prompt wording, and answer instruction are not part of `task_id`; they
are part of the definition or a later presentation step.

Validity checks and the narrowing record use the canonical sequence. A later
presentation step may render a permutation that respects reference dependencies;
the permutation does not change `task_id`, and clue wording uses presentation
positions.

Definitions with identical canonical identity are duplicates. `03b` keeps one
and records the duplicate. Invalid definitions go to the failure record and do
not consume quota.

### Canonical serialization

One definition serializes to one canonical JSON object. Its bytes are the hash
input, so every rule below is part of the contract:

- keys sorted by byte order, so the field table can be reordered without changing
  a hash;
- UTF-8 bytes, no byte-order mark, `,` and `:` with no surrounding space, no
  trailing newline;
- non-ASCII characters written as raw UTF-8, not as `\u` escapes. Go disables
  HTML escaping, which would otherwise write `<`, `>`, and `&` as `\u003c`,
  `\u003e`, and `\u0026`;
- a string containing U+2028 or U+2029 is rejected at construction, because Go
  and Python escape those two characters differently;
- absent values written as `null`, never omitted;
- integers written as JSON integers; every other number written as canonical
  decimal text, never as a JSON number;
- UUIDs as lowercase hyphenated text;
- lists keep their recorded order, and the clue list is the canonical clue
  sequence.

`task_id` and `definition_sha256` are excluded from their own hash input.

The definition has no binary float fields. The answer precision rule already
produces canonical decimal text, and the release stores the same text in
`gold_answer_json`, `tolerance_json`, and `answer_evidence_json`. Clue
thresholds, ranges, points, and choice answers reuse it. The hash therefore
never formats a float, which is what makes it reproducible across languages:
Go and Python disagree on `1e17` (`100000000000000000` against `1e+17`), on the
exponent's leading zero (`1e-9` against `1e-09`), and on negative zero.

The rule is scoped to the task definition. Graph tables keep native float
columns: they are measured once, read in bulk, and never hashed.

Python serializes with `orjson` and sorted keys; Go uses `encoding/json` with
HTML escaping disabled. Because the definition has no float fields, the library
choice does not change the bytes: only strings, integers, and structure reach
the hash.

### Three hashes

| Hash | Input | Used for |
|---|---|---|
| `task_id` | the canonical task identity | duplicate detection, release key, split-isolation check |
| `definition_sha256` | the canonical task content | accepted-definition immutability, duplicate content, reproduction check |
| `answer_sha256` | the answer and scoring fields | release answer column integrity |

`definition_sha256` covers `state_scope`, `target_binding`, `task_clues`,
`clue_operand_form_profile`, `answer_meaning`, `answer_parameter`,
`gold_answer`, `answer_unit`, `tolerance`, `scoring_rule`, `answer_evidence`,
and `choice_pool` in construction order. It also covers the inputs that change
that content: `program_sha256`, `graph_schema_version`,
`runtime_extraction_sha256`, `constructor_version`, `definition_schema_version`,
and `construction_seed`.

It does not cover `plan_version`, `cadevolve_program_family_id`, `split`, or
`subset`. Those are assignment: `03a` re-enters with a new plan version without
changing an accepted definition, so hashing them would invalidate every accepted
definition on every replan (`TG-3`).

`answer_sha256` covers `gold_answer`, `answer_unit`, `tolerance`,
`scoring_rule`, and `answer_schema_version`. For a multiple-choice task it also
covers the `candidate` of the entry whose label is `gold_answer`, because a label
is a position and does not identify the answer on its own. It excludes
`answer_evidence`, because evidence is audit data and a change to its
representation must not change the answer identity. `04` copies the hash; it does
not recompute it.

`choice_pool` is hashed in construction order, labels included. `04` renders that
order and must not write a new one back.

### Provenance

`provenance` records the inputs the hash depends on, so a mismatch names the input
that moved:

| Field | Meaning |
|---|---|
| `runtime_extraction_sha256` | The CadQuery program runtime extraction result the graph was built from. |
| `constructor_version` | The typed constructor set that produced the definition. |
| `construction_seed` | The seed the constructor sampled with. |
| `plan_version` | The `TaskQuotaPlan` that assigned the quota target. |
| `balance_policy_version` | The balance policy the plan was computed from. |

Rendering provenance — render seed, template version, and `prompts.yaml` hash —
belongs to `04` render prompt and choices, not to the definition (`DS-35`). `05`
validate and export release records those values in the manifest. The template
schema is in [`../../prompt-templates.md`](../../prompt-templates.md).

## Construction attempt budget

Use the plan's `construction_attempt_budgets`. `03a` computes each from the
remaining target count. On resume, use the accepted count in the `DeficitLedger`
and construct only the remaining target count. Accepted definitions are not
regenerated or revalidated while the input versions are unchanged. It does not top up a quota target incrementally within
the same plan revision.

The batch is one iteration and is parallelizable. Extra accepted definitions
become reserve; they are not dataset release rows. Track accepted and rejected counts per quota target, family, and rejection reason. A high rejection rate is a constructor or validity signal; it
is not automatically a reason to expand the program pool.

An underfilled quota target is a deficit for `03c` after the batch, not a reason to loop
inside `03b`.

## Relationship to task reasoning step support

The **task reasoning step support tables** are a separate derived QA baseline.
They are computed from the rules in this document and are not an input to `03b`.
They are used to check release coverage in
[`../task-step-support.md`](../../task-step-support.md).

## Open questions

- **Q6** (P2). How are plausible, deterministic near-miss choices generated and
  validated?
  - **Recommendation:** start from the correct task solution and apply one
    controlled error: an adjacent entity, the wrong solid state, the wrong
    operation, a swapped comparison, a different measurement, or an off-by-one
    count. Validate against the graph, then add each near miss to the pool before
    the pool is ordered. For a multi-step task, a near miss should satisfy most
    task clues and fail at least one. Record its `error_mode`. P0 and P1 do not
    require this audit.

## Resolved questions

- **Q2.** *Resolved 2026-10-21.* Option B: atomic predicates. Each relation or
  property is one task clue and one task clue step. A list item that states a
  relation and a property is split into two task clues. A chain is not one task
  clue; it is a P2 ordered sequence of relation task clues, one step per
  relation. Task clues are rendered as numbered list items, not prose.

- **Q4.** *Resolved 2026-10-21.* Multiple choice is valid for every answer
  meaning; it is a presentation wrapper, not a separate answer meaning. The
  native answer format is recorded with the answer meaning; multiple choice may
  be used when enough choices can be generated.

- **Q5.** *Resolved 2026-10-21.* A task is a duplicate when its canonical task
  identity is identical. Answer format, multiple-choice choices, prompt wording,
  and answer instruction are excluded because multiple choice is a presentation
  wrapper.

## Deficits

A quota target that cannot be filled is recorded in the deficit ledger. `03c`
decides whether to sample more from existing graphs, use unused or reserve
programs, request supplemental `01b` selection, or accept the miss.

`03b` records the class when it knows it: `probe_deficit` when the bound state has
no surviving point probe, and `construction_deficit` when the batch is
underfilled. Deficits that `03a` reports carry an allocation detail instead, and
`03c` classifies them.

## Not here

Task quota planning, data expansion, prompt rendering, choice rendering, and
export. The construction test contract and the golden record are in
[`../testing/golden-records.md`](../testing/golden-records.md).
