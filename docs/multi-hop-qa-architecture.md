# Multi-Hop CAD-QA Architecture Notes

This document is an exploratory architecture note for the BrowseComp-style
Multi-Hop CAD-QA track described in
[`specs/multi-hop-qa-task-spec.md`](../specs/multi-hop-qa-task-spec.md). It is
not an implementation contract. The goal is to make the generation pipeline
concrete enough to debate, prototype, and reject bad ideas early.

The core design thesis is:

```text
deterministic hidden query skeleton
+ graph-grounded answer-first sampling
+ LLM surface rendering
+ deterministic verifier
+ LLM judges and adversarial solvers
= natural-looking hard questions with auditable labels
```

The public benchmark should look like ordinary CAD questions over code. The
private dataset row should keep enough structure to regenerate the question,
validate the answer, measure difficulty, and explain why a row was accepted.

## Design Goals

- Generate genuine-looking, obfuscated multi-hop CAD questions.
- Keep every official answer deterministic and verifier-backed.
- Make questions hard to solve but easy to verify after a candidate answer is
  proposed.
- Avoid exposing a query DSL to benchmarked models.
- Avoid relying on LLMs for truth, uniqueness, or geometry labels.
- Use inexpensive LLMs where possible by limiting them to bounded generation,
  critique, and adversarial solving roles.
- Record enough hidden structure to support audits, regeneration, balancing,
  and difficulty analysis.

## Non-Goals

- Do not make a public formal query language.
- Do not ask an LLM to invent CAD facts.
- Do not accept rows whose uniqueness depends only on model judgment.
- Do not treat vague design intent as a label source.
- Do not optimize first for maximum linguistic diversity. Natural language
  diversity should come after label correctness and ambiguity control.

## Relevant Design Patterns

BrowseComp is useful as a design analogy because it starts from an answer and
builds an inverted question that is hard to discover but short and easy to
verify. For CAD-QA, the verifier is stronger than in open-web QA because the
answer can be checked against trace and graph labels.

SailorFog-style generation is useful because difficulty comes from graph
sampling, uncertainty, and distractors rather than from a fixed template list.
The CAD analogue should sample connected CAD subgraphs, then render their
constraints into natural language.

WebShaper is useful because it separates the formal reasoning structure from
surface question text. The CAD analogue should use hidden typed query programs,
not public DSL prompts.

## High-Level Pipeline

### 1. Trace And Graph Construction

Input:

- normalized CadQuery script;
- operation graph;
- trace snapshots;
- selector tables;
- topology counts and topology deltas;
- volume and bounding-box metrics;
- provenance records when available;
- spatial indexes when available.

Output:

- hidden CAD knowledge graph;
- node and relation family coverage metadata;
- label status for every metric or relation family.

The graph may be partial. Every candidate row must declare which graph
families it uses, and the row should be rejected when any required family is
missing, unstable, or below confidence thresholds.

### 2. Answer-First Target Sampling

Sample a target before generating the question. Candidate answer types:

- `feature_id`;
- `entity_id`;
- `integer`;
- `number`;
- `coordinate`;
- `axis_id`;
- `enum`;
- `json`;
- `invalid_or_ambiguous`.

For the initial release, prioritize `feature_id`, `number`, and `enum` because
they are easier to grade and audit.

Target sampling should be balanced by:

- operation family;
- answer type;
- graph relation family;
- constraint type;
- difficulty bucket;
- source group;
- trace label confidence.

### 3. Constraint Mining

For the sampled answer, mine true facts from the graph. Each fact becomes a
candidate hidden clause. Each clause must include:

```json
{
  "clause_id": "c03",
  "constraint_type": "metric",
  "target_entity_type": "feature",
  "predicate": "feature.measurements.bbox_delta == [0, 0, 0]",
  "public_text_seed": "It does not change the global bounding box.",
  "evidence_chain": ["feature --has_measurement--> bbox_delta"],
  "label_sources": ["trace.snapshots", "operation_node"],
  "stability_status": "ok"
}
```

The `constraint_type` enum is defined in the task spec and should be used for
generation, balancing, validation, and diagnostics:

```text
temporal
metric
topological
selector
provenance
spatial
comparative
parameter
operation_semantics
relation
```

Useful mined constraints include:

- temporal: after the second box, before the final fillet, immediately after a
  cylindrical feature;
- metric: largest positive volume delta, zero bounding-box change, shortest
  centerline distance;
- topological: largest circular-edge increase, no face-count change,
  cylindrical-face count;
- selector: face selected by a side-face selector, entity selected by `">Z"`,
  selector result count;
- provenance: modifies a previously selected face, removes material from a
  region created by an earlier feature;
- spatial: adjacent to the deepest blind cut, coaxial with a hole, contained in
  a region;
- comparative: changed Y extent more than another feature, smaller volume
  delta among matching candidates;
- parameter: dimensions in a range, parameter reused from a prior feature,
  transformed offset;
- operation semantics: subtractive feature, transform-only operation,
  workplane-changing operation;
- relation: existence of a path or relation when no more specific type is
  dominant.

### 4. Distractor-Aware Clause Selection

A clause is useful only in relation to the candidate set it leaves behind.

For each clause, compute:

- candidate set after applying the clause alone;
- entropy or ambiguity reduction;
- whether it leaks the answer directly;
- whether it depends on stable labels;
- how many distractors remain;
- which distractor attributes overlap the answer.

Apply an atomic clue breadth gate before composing clauses:

- each individual public clue should leave at least a configured minimum number
  of candidates, initially `min_individual_candidate_count = 5`;
- temporal before/after anchors should also require at least a configured side
  range, initially `min_temporal_side_range = 5`, so prompts do not use anchors
  like "before feature #4" or "after feature #11" in a small feature set;
- immediately-before, immediately-after, final-step, rare-selector, and
  one-off provenance clues should be rejected as standalone clues unless the
  source has enough repeated structure for the clue to retain at least the
  minimum candidate count;
- the full clause set must still resolve to exactly one answer after all
  accepted broad clues are combined.

This gate will reject many interesting rare facts. That is intentional for the
hard track: a clue that selects only one or two entities is a disguised direct
reference, even when it sounds natural.

Apply a public wording gate after canonical clue compilation:

- public clues must be understandable from the shown CadQuery script alone by a
  small model that knows no CAD-QA ontology;
- internal terms such as `material_region`, `measurement`, `profile`,
  `accumulated body`, `provenance`, or `graph node` should not appear in public
  prompts unless immediately grounded in visible code such as `.extrude(...)`,
  `.union(...)`, `.faces(...)`, `.polyline(...)`, `.cutBlind(...)`,
  `.cutThruAll()`, or an explicit before/after measurement;
- if a clue refers to a derived concept, the wording should explain what the
  model can inspect in the code, for example "the object later added with
  `.union(...)`" rather than "the material region";
- candidate grouped prompts should be rejected when their clues mix
  incompatible target types, such as asking for one feature while combining
  face, vertex, profile, and parameter clues that do not share a resolvable
  target.

Then select a clause set that satisfies:

- individual clues are not all trivially identifying;
- partial clue sets leave plausible distractors;
- the full clue set resolves to exactly one answer;
- at least two thirds of counted hops are geometry/trace-derived for release
  rows;
- the public text can omit direct IDs without becoming ambiguous.

This step should be deterministic or mostly deterministic. The LLM should not
choose the accepted answer.

### 5. Hidden Query Program Assembly

The hidden query program is the canonical artifact. It should include:

```json
{
  "query_version": "cadqa_multihop_query_v1",
  "answer_type": "feature_id",
  "target_entity_type": "feature",
  "public_prompt_style": "constraint_checklist",
  "clauses": [],
  "candidate_set_trace": [],
  "distractors": [],
  "tie_break": "reject_unless_unique",
  "difficulty": {},
  "required_graph_families": []
}
```

The query program is not public. It exists for:

- regeneration;
- validation;
- ambiguity detection;
- hop accounting;
- row audit;
- difficulty balancing;
- debugging model failures.

### 6. Natural-Language Rendering

Rendering should be LLM-assisted, but heavily constrained.

Inputs to the renderer:

- hidden clauses;
- allowed public facts;
- forbidden leaks;
- desired style;
- answer format;
- examples of acceptable phrasing;
- examples of unacceptable phrasing.

Renderer output:

```json
{
  "question": "Given the CadQuery script below, identify ...",
  "style": "constraint_checklist",
  "clue_map": [
    {"clause_id": "c01", "text_span": "..."},
    {"clause_id": "c02", "text_span": "..."}
  ],
  "notes": {
    "possible_leaks": [],
    "ambiguous_phrases": []
  }
}
```

Recommended prompt styles:

- `constraint_checklist`: safest MVP style;
- `single_paragraph`: more natural, higher ambiguity risk;
- `comparative_question`: useful for pairwise or ranked tasks;
- `chain_completion`: useful for relation-path tasks;
- `yes_no_relation`: useful for relation existence;
- `invalid_or_ambiguous`: optional calibration family.

The renderer may propose variants, but the verifier and judges decide which
variants survive.

### 7. Deterministic Re-Resolution

After rendering, re-resolve the hidden query program against the graph. Reject
if:

- answer is not unique;
- any clause cannot be evaluated;
- any required label source is unstable;
- tie-breaking is required but not explicitly allowed;
- answer changed after prompt rendering adjustments;
- prompt leaks a private ID or diagnostic field;
- public text references a concept not backed by the query program.

This stage should not depend on LLM judgment.

### 8. LLM Judge Stack

Use cheap LLM judges as rejection and ranking tools. They should not define
truth.

Potential judges:

- naturalness judge: does the question sound like a real CAD reasoning task?
- ambiguity judge: can the wording plausibly describe more than one answer?
- leakage judge: does the prompt expose the answer or hidden program too
  directly?
- CAD semantics judge: are CAD terms used correctly?
- clue alignment judge: does each public clue correspond to the intended
  hidden clause?
- difficulty judge: estimate whether the prompt requires multi-hop reasoning.
- answer-format judge: is the requested answer format clear and short?

Each judge should return structured output:

```json
{
  "pass": true,
  "score": 0.82,
  "failure_reason": null,
  "actionable_revision": null
}
```

Rows should require either unanimous pass from critical judges or a conservative
threshold. Critical judges are ambiguity, leakage, and clue alignment.

### 9. Adversarial Solver Filter

Run one or more inexpensive solver models on the public prompt only.

Use solver outputs to estimate:

- triviality: weak models solve too often;
- ambiguity: solvers produce multiple plausible answers;
- leakage: solvers identify the answer for the wrong reason;
- difficulty: pass rate across N attempts;
- answer-format clarity.

A useful acceptance shape:

- deterministic verifier says the answer is unique;
- weak solver pass rate is low for release-hard rows;
- stronger solver sometimes succeeds with coherent evidence;
- wrong solver answers mostly correspond to planned distractors.

If solvers invent many answers that are not in the planned candidate set, the
question wording may be too vague or the answer format may be underspecified.

### 10. Final Row Acceptance

Accept only when all gates pass:

1. Graph labels stable.
2. Hidden query resolves uniquely.
3. Candidate/distractor analysis satisfies target difficulty.
4. Public prompt has no forbidden leak.
5. Deterministic re-resolution passes.
6. Critical LLM judges pass.
7. Solver pass-rate band matches target bucket.
8. Public row validates under schema and grading policy.

Rejected candidates should be retained in an internal failure manifest with
machine-readable reasons. Failure manifests are useful for improving the
generator.

## Architecture Components

### Graph Builder

Owns graph construction from trace artifacts. It should produce a normalized
private graph with node IDs, relation IDs, label source pointers, and stability
flags.

### Candidate Target Sampler

Owns answer-first selection. It should know quotas and avoid repeatedly
sampling the cheapest or most common answer types.

### Constraint Miner

Owns clause discovery. It should expose candidate clauses with their predicate,
constraint type, evidence chain, candidate-set effect, and label dependencies.

### Clause Set Searcher

Owns distractor-aware selection of clause combinations. This is the heart of
the generator. It should optimize for uniqueness, difficulty, and clue
diversity while rejecting brittle or leaky combinations.

### Prompt Renderer

Owns LLM-assisted wording. It should be stateless and reproducible given a
seed, model, prompt version, and hidden query program.

### Verifier

Owns deterministic query resolution. It should support exact failure reasons:

- `empty_candidate_set`;
- `ambiguous_candidate_set`;
- `missing_label_family`;
- `unstable_label`;
- `unsupported_predicate`;
- `tie_break_required`;
- `prompt_leak_detected`;
- `render_alignment_failed`.

### Judge Orchestrator

Owns LLM judge calls, structured parsing, retry policy, and cost controls.

### Solver Harness

Owns adversarial and calibration solver runs. It should record raw responses,
parsed answers, correctness, confidence when available, and error taxonomy.

### Row Materializer

Owns final public row creation and private label payloads.

## Difficulty Accounting

Difficulty should be computed, not guessed. Suggested fields:

```json
{
  "constraint_type_counts": {
    "temporal": 1,
    "metric": 2,
    "selector": 1
  },
  "static_hops": 2,
  "geometry_trace_hops": 5,
  "shortest_evidence_hops": 6,
  "distractor_count": 4,
  "min_clauses_for_uniqueness": 4,
  "full_clause_candidate_count": 1,
  "nearest_distractor_margin": 0.12,
  "weak_solver_pass_at_1": 0.0,
  "strong_solver_pass_at_3": 0.33
}
```

Difficulty buckets should combine graph structure and empirical solver
behavior. Solver pass rates should never override deterministic correctness,
but they are useful for release balancing.

## Obfuscation Strategy

Obfuscation should be a controlled transform over valid clauses, not free-form
rewriting.

Useful transforms:

- feature ID to operation description;
- exact step index to ordinal or relative order;
- exact parameter to comparison or safe range;
- entity ID to selector result;
- face ID to orientation or adjacency relation;
- operation name to material effect;
- direct metric value to argmax or threshold;
- source-line reference to construction-history clue.

Bad transforms:

- vague adjectives without thresholds;
- hidden world knowledge;
- ambiguous coordinate frames;
- design-intent language;
- references to visual salience not present in labels;
- phrases that imply topology/provenance precision the trace does not support.

## Suggested MVP

The first prototype should stay narrow.

Scope:

- answer types: `feature_id`, `number`, `enum`;
- prompt style: `constraint_checklist`;
- graph substrate: current feature-level graph plus trace metrics;
- constraint types: `temporal`, `metric`, `topological`, `selector`,
  `comparative`, `operation_semantics`;
- generation: deterministic clause mining plus LLM rendering;
- validation: deterministic resolver plus ambiguity/leakage/alignment judges;
- solver filter: one cheap weak model and one stronger model, small N.

MVP output:

- internal JSONL of hidden query programs;
- public JSONL rows;
- rejection manifest;
- difficulty report;
- judge report;
- solver calibration report;
- small manual audit sample.

MVP non-scope:

- broad B-rep face/edge relation graph;
- full provenance over material regions;
- paragraph-style prompts;
- Level 5 extreme rows;
- public invalid/ambiguous family.

## Experiments To Run

### Template vs LLM Rendering

Compare:

- fixed checklist templates;
- unusual Jinja templates with synonym slots;
- LLM-rendered checklist;
- LLM-rendered paragraph.

Metrics:

- verifier pass rate;
- judge ambiguity rate;
- weak solver pass rate;
- human naturalness rating;
- manual audit defect rate.

### Clause Count Sweep

Generate rows with 2, 3, 4, 5, and 6 clauses.

Measure:

- uniqueness rate;
- prompt length;
- solver pass rate;
- ambiguity judge failure rate;
- manual readability.

### Constraint Mix Sweep

Hold clause count fixed and vary constraint type mixes.

Example mixes:

- temporal + metric + comparative;
- temporal + selector + topology;
- operation semantics + metric + topology;
- selector + provenance + spatial.

Measure which mixes produce the best hard-but-natural questions.

### Judge Ablation

Run with and without each judge:

- ambiguity;
- leakage;
- clue alignment;
- CAD semantics;
- naturalness.

Measure downstream manual audit failures. Keep only judges that catch real
defects at acceptable false-positive rates.

### Solver-Based Difficulty Calibration

For a candidate batch, run repeated attempts from cheap and stronger solvers.

Use pass-rate distributions to tune:

- release difficulty thresholds;
- minimum distractor count;
- minimum clauses for uniqueness;
- acceptable prompt styles.

## Main Risks

### LLM Surface Text Changes Semantics

The renderer may subtly convert an exact predicate into a vague or stronger
claim.

Mitigation:

- require `clue_map`;
- use clue alignment judge;
- keep checklist style for MVP;
- reject when public text introduces unsupported concepts.

### Deterministic Graph Is Too Thin

Current graph coverage may not support enough genuine multi-hop diversity.

Mitigation:

- start with feature-level metric/temporal/topology/selector rows;
- record required graph families;
- report limitations clearly;
- add richer face/edge/provenance graph support incrementally.

### Questions Become Template-Looking

Checklist prompts may feel mechanical.

Mitigation:

- accept this for MVP;
- use multiple checklist variants;
- add paragraph rendering only after validation is robust.

### Judges Are Noisy

Cheap LLM judges can reject good rows or miss subtle defects.

Mitigation:

- treat judges as filters, not sources of truth;
- require deterministic verifier first;
- calibrate against manual audits;
- keep raw judge rationales in internal artifacts.

### Solver Pass Rate Is Misleading

A solver might fail due to formatting or succeed through leakage.

Mitigation:

- parse solver rationale when available;
- compare wrong answers against planned distractors;
- use pass rates as a balancing signal, not a correctness signal.

### Over-Obfuscation Creates Ambiguity

Hard questions can become under-specified.

Mitigation:

- compute full candidate set after every transform;
- keep ambiguity margin diagnostics;
- reject vague public text;
- add more precise clauses rather than looser wording.

## Open Questions

- Should `comparative` be a primary constraint type or an operator layered over
  metric/topological/spatial constraints?
- Should the hidden query program store executable predicates, structured
  predicate objects, or both?
- How much paragraph-style naturalness is worth the added ambiguity risk?
- What pass-rate band should define release-hard rows?
- Should solver traces be stored as training data, or only as generation
  diagnostics?
- Should invalid/ambiguous rows be part of the benchmark or only an internal
  quality-control tool?
- What is the minimum graph substrate needed before calling this BrowseComp-like
  rather than advanced `graph_query`?

## Recommended Next Step

Implement a small generator spike that never calls an LLM at first:

1. Sample answer-first feature targets from current typed graphs.
2. Mine deterministic `temporal`, `metric`, `topological`, and
   `operation_semantics` clauses.
3. Search for clause sets that uniquely identify the answer with distractors.
4. Render rigid checklist prompts.
5. Produce a rejection manifest and difficulty report.

Only after this deterministic spine produces credible hidden query programs
should LLM rendering and LLM judges be added. This keeps the expensive and noisy
parts downstream of the thing that matters most: graph-grounded uniqueness.
