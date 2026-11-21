# Overnight Task: Graph-First CAD-QA Rewrite

Date: 2026-04-29

## Original Human Direction

The current codebase and documentation grew around a split that no longer
matches the desired benchmark:

- "CAD-QA Core"
- old `graph_query`
- separate "multi-hop" ideas

This split is now wrong. The codebase should revolve around one concept:

```text
typed CAD ontology graph + deterministic query/verifier + hop-counted prompts
```

The old "Core" task families are not a separate conceptual pipeline. They are
low-hop special cases of the same graph reasoning system:

- 0 hops: direct source/statistic lookup;
- 1 hop: resolve one entity and read one metric;
- 2 hops: resolve through one relation and read/compare a metric;
- 3+ hops: real multi-hop benchmark rows.

The overnight task is to rewrite the repository around this single idea.

No regrets. This codebase was implemented while the user was sleeping; another
agent can implement the new version today. Restarting is acceptable and desired
if it makes the project simpler.

## Non-Negotiable Outcome

By the end of the task, the repo should no longer contain a conceptual split
between "simple QA", "graph query", and "multi-hop". There should be one
graph-first architecture with low-hop and high-hop slices.

The target design is:

```text
CadQuery source
-> source normalization
-> trace/snapshot extraction
-> typed CAD ontology graph
-> deterministic query program
-> verifier-backed answer
-> rule-based public prompt renderer
-> public rows grouped by hop count and relation/metric families
```

## Scope

Do both parts:

1. Rewrite the documentation and planning artifacts.
2. Rewrite the codebase from scratch after the docs are aligned.

This is intentionally destructive. Do not preserve legacy modules just because
they currently pass tests. Preserve ideas only when they fit the new graph-first
architecture.

## 1. Documentation Rewrite

Rewrite all documentation to match the new architecture.

Be brutal. If a document is misleading, clear it and restart it. If the old
organization creates the wrong mental model, delete or replace it.

Required documentation direction:

- The project is one CAD ontology QA system, not multiple unrelated task
  pipelines.
- CAD-QA Core is a low-hop subset of graph reasoning.
- Multi-Hop CAD-QA is the high-hop, obfuscated, distractor-gated subset.
- Spatial distance, bounding-box region, selector, provenance, topology,
  profile, material-region, and validity questions are relation/metric families
  over the same graph.
- Prompt generation is rule-based templating from deterministic query programs,
  not an LLM translator pipeline.
- LLM calls, if any, are only optional external evaluation or wording
  experiments, not trusted generation or judging.

>- Multi-Hop CAD-QA is the high-hop, obfuscated, distractor-gated subset.
  explicit note: Let me define this better: see BrowseComp dataset, and see https://huggingface.co/papers/2507.02592

In addition, we have *already detailed well in experiments/old/multi_hop_qa_mock" In particular, /home/maksym/Work/proj/Problemologist/CAD-QA/experiments/old/multi_hop_qa_mock/preview/comprehensive_ontology_preview.md and the script that generated it defined more or less how I want the features to look like. I have also reviewed and corrected that experiment doc in a few places too.

### Documents To Rewrite Or Replace

At minimum inspect and update:

- `README.md`
- `epics-and-stories.md`
- `epics-and-stories.yaml`
- `specs/benchmark-family.md`
- `specs/benchmark-task-spec.md`
- `specs/schema.md`
- `specs/label_rules.md`
- `specs/generation_policy.md`
- `specs/dataset-spec.md`
- `specs/extracting-cadevolve-features.md`
- `specs/multi-hop-qa-task-spec.md`
- `docs/multi-hop-qa-architecture.md`
- any docs under `docs/` that still describe the old split

It is acceptable to replace long old documents with shorter new documents if
that improves coherence.

### Epics Rewrite

Update `epics-and-stories.yaml` aggressively.

Rules:

- Drop the old `graph_query` framing.
- Drop separate top-level epics that are really graph query variants.
- Fold spatial distance and bounding-box region work into the graph ontology
  relation/metric family plan.
- Keep separate epics only for real implementation layers, such as source
  ingestion, tracing, graph extraction, query resolution, row materialization,
  evaluation, and training.
- Mark every epic touched by the rewrite as `planned` or `work-in-progress` - the latter being in rarer cases of something you don't need to remove completely.
- It is fine to replace the entire file if that is clearer.

The preferred epic structure is roughly:

1. Project framing and graph-first spec.
2. Source ingestion and normalization.
3. Trace/snapshot execution.
4. CAD ontology graph extraction.
5. Query program and deterministic resolver.
6. Label and relation families.
7. Rule-based prompt rendering.
8. Dataset materialization, splits, and validation.
9. Baselines and evaluation.
10. Training/SFT artifacts.
11. Experiment orchestration and reports.

## 2. Codebase Rewrite

After rewriting the docs, delete the old implementation and restart the
codebase from scratch.

This includes tests.

The same rule applies as for docs: the old split makes the project harder to
reason about. A clean graph-first implementation is preferable to preserving a
working but conceptually wrong pipeline.

### Destructive Reset Instructions

Delete and recreate the implementation surface, including:

- `cad_qa/`
- `scripts/`
- `tests/`
- obsolete configs under `configs/`
- obsolete generated experiment helpers if they encode the old split

Do not delete:

- `.git/`
- `.agents/`
- source specs/docs that were just rewritten
- raw or useful dataset inputs under `data/` unless they are clearly generated
  stale outputs
- external adjacent source trees outside this repo

If in doubt, move old generated artifacts to a clearly named archive directory
or ignore them, but do not design the new code around them.

### New Code Architecture

Implement a small, coherent graph-first package.

Suggested package layout:

```text
cad_qa/
  __init__.py
  cli.py
  config.py
  io.py
  source.py
  trace.py
  ontology/
    __init__.py
    nodes.py
    relations.py
    extract.py
    profile_geometry.py
    workplane_frames.py
    material_regions.py
  query/
    __init__.py
    ir.py
    resolver.py
    candidates.py
    difficulty.py
  prompts/
    __init__.py
    templates.py
    render.py
    wording_gates.py
  dataset/
    __init__.py
    materialize.py
    validate.py
    split.py
  evaluation/
    __init__.py
    parse.py
    grade.py
    baselines.py
```

This layout is guidance, not a requirement. The real requirement is that the
code expresses one graph/query system and is worthy of being publishable, and would train CAD LLM agent models better, just like "WebSailor: Navigating Super-human Reasoning for Web Agent" trained better web search agents.

### Core Data Model

The new implementation should center on these concepts:

- `SourceRecord`
- `TraceRecord`
- `OntologyGraph`
- `Node`
- `Relation`
- `Measurement`
- `QueryProgram`
- `Clause`
- `CandidateSetTrace`
- `RenderedPrompt`
- `DatasetRow`

Every public row should be generated from a hidden query program. Low-hop rows
and high-hop rows use the same machinery.

### Node Families

Support the ontology vocabulary from the spec, starting small but in the right
shape:

```text
source
feature
operation
parameter
workplane
sketch
profile
solid
face
edge
vertex
axis
direction
point
centroid
centerline
path
material_region
void_region
selector
measurement
```

### Relation Families

Use one relation registry. Do not scatter task-specific relation logic across
unrelated prompt generators.

Important relation families:

```text
before
after
input_to
combines
created_by
modified_by
deleted_by
bounded_by
selected_by
located_on
uses_profile
used_by
parameter_of
has_measurement
has_normal
has_centroid
has_coordinate
distance_to
nearest_tangent_to
parallel_to
not_parallel_to
perpendicular_to
orthogonal_to
coaxial_with
adjacent_to
opposite_to
contained_in
intersects
adds_material_to
removes_material_from
```

### Measurement Scopes

Implement measurement scopes explicitly:

```text
profile_intrinsic
feature_application_effect
entity_geometry
snapshot_state
relation_metric
```

This avoids invalid labels like:

```text
profile.has_measurement(edge_count_delta)
```

That should instead be represented as:

```text
profile -> used_by -> feature
feature -> has_measurement(feature_application_effect.edge_count_delta)
```

## P0 Implementation Slices

Build P0 first. Do not start with material regions or advanced boolean diff.

Delivery expectation: **all P0 items are required**. If a P0 item is not
implemented, the final report must treat the overnight task as incomplete and
state the exact blocker.

### P0.1 Minimal Source And Operation Graph

Implement:

- JSONL source loading;
- normalized CadQuery source records;
- AST-backed assignment/call-chain extraction;
- feature/operation nodes;
- parameter nodes;
- static `before`, `after`, `input_to`, and `parameter_of` relations.

Acceptance:

- Can load at least 10 CADEvolve sources.
- Can emit a graph summary with nodes and relations.
- Unit tests cover simple assignments, chained calls, and parameter reuse.

### P0.2 Profile Geometry

Implement first-class profile extraction for:

- `.circle(radius)`;
- `.rect(width, height)`;
- `.polyline(points).close()`;
- bounded helper-returned point lists when safe.

Compute:

- area;
- perimeter;
- centroid;
- local bbox;
- edge count;
- vertex count;
- primitive segment counts.

Acceptance:

- Profiles become graph nodes.
- `feature -> uses_profile -> profile` and `profile -> used_by -> feature`
  projection paths exist.
- Tests cover circle, rect, and polyline.

### P0.3 Workplane Frames

Extract:

- workplane origin;
- normal;
- x/y axes when available;
- local-to-world transform;
- relation from profile to workplane.

Acceptance:

- Profile local coordinates can be projected to world coordinates.
- Workplane-normal clues can be evaluated.

### P0.4 Profile Application Effects

Attach operation/snapshot effects to features that used profiles:

- signed volume delta;
- bbox delta;
- topology delta;
- edge-count delta;
- circular-edge delta when available.

Acceptance:

- A query can ask for "the profile whose resulting cut creates the largest
  edge-count increase" through the feature application path.

### P0.5 Query Program And Resolver

Implement a deterministic query IR:

- target entity type;
- answer type;
- clauses;
- relation paths;
- metric filters;
- aggregations such as argmax/argmin;
- candidate-set trace;
- reject-unless-unique tie policy.

Acceptance:

- Same resolver handles 0-hop, 1-hop, 2-hop, and 3+ hop rows.
- Resolver records exact failure reasons.

### P0.6 Rule-Based Prompt Rendering

Implement checklist rendering from approved clauses:

- no LLM translator;
- versioned templates;
- clue map from public sentence to hidden clause;
- banned ontology-jargon gate;
- individual clue breadth gate;
- projection-path gate.

Acceptance:

- Public prompts are generated from query programs.
- Every public clue maps to a hidden clause.
- No clue can narrow candidates below the configured minimum unless the row is
  explicitly a low-hop calibration row.

## P1 Implementation Slices

P1 makes the dataset look like the intended benchmark.

Delivery expectation: **all P1 items are also required**. Do not treat P1 as a
nice-to-have bucket. The goal is not merely to rebuild low-hop rows; the goal is
to get enough non-feature graph relations working that the dataset resembles the
intended BrowseComp/WebSailor-style CAD reasoning benchmark.

- stable selector face IDs;
- same-face joins;
- non-top/side-face predicates;
- sketch centers and center-offset clues;
- path tangents for `splineApprox(...)` and sweep paths;
- nearest point on path;
- centroid and coordinate relations over solids/profiles.

Acceptance:

- Can generate questions involving profiles, workplanes, selected faces, and
  path tangents without relying on private IDs.

## P2 Implementation Slices

P2 depends on heavier geometry/provenance work.

Delivery expectation: implement the easy P2 items too. In practice this means:

- implement any P2 relation that can be done conservatively from existing
  snapshots, source geometry, or simple exact geometry checks;
- emit diagnostic/quarantine labels when evidence is useful but not yet
  release-grade;
- defer only the genuinely heavy pieces, such as robust boolean-diff material
  regions or fragile B-rep adjacency, and document the blocker precisely.

- added material-region geometry;
- removed void-region geometry;
- region centroid/bbox/volume;
- region adjacency;
- region intersection and containment;
- stable face/edge/vertex adjacency and opposite-face relations.

Acceptance:

- Can generate material-region and void-region multi-hop rows with conservative
  evidence rather than AABB-only guesses.

## Dataset Rows

Every row should include:

- `row_id`;
- `source_id`;
- public source code;
- public prompt;
- answer format;
- gold answer;
- hidden query program;
- candidate-set trace;
- relation families used;
- measurement scopes used;
- logical hop count;
- static hop count;
- geometry hop count;
- difficulty bucket;
- verifier status.

Core rows are simply low-hop rows. Do not create a separate Core generation
pipeline.

## CLI Shape

Implement only a small CLI at first:

```bash
uv run cadqa sources inspect --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl
uv run cadqa graph build --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl --limit 10 --out runs/graph_smoke
uv run cadqa query smoke --graph runs/graph_smoke/graphs.jsonl --out runs/query_smoke
uv run cadqa dataset materialize --queries runs/query_smoke/queries.jsonl --out data/cadqa_graph_smoke
uv run cadqa dataset validate data/cadqa_graph_smoke
```

Keep commands boring and composable. Avoid many task-family-specific commands.

## Tests

Delete old tests and write new tests around the graph system.

Minimum test coverage:

- source loading;
- AST call-chain extraction;
- operation graph extraction;
- profile geometry for circle/rect/polyline;
- workplane frame extraction;
- relation registry;
- query resolver candidate filtering;
- argmax/argmin aggregation;
- reject-unless-unique policy;
- low-hop row materialization;
- multi-hop checklist rendering;
- row validation.

Run:

```bash
rtk uv run python -m compileall -q cad_qa
rtk uv run pytest -q
```

## Smoke Dataset

Build a tiny smoke dataset from existing CADEvolve source records:

```bash
rtk uv run cadqa graph build \
  --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl \
  --limit 10 \
  --out runs/graph_smoke

rtk uv run cadqa query smoke \
  --graph runs/graph_smoke/graphs.jsonl \
  --out runs/query_smoke

rtk uv run cadqa dataset materialize \
  --queries runs/query_smoke/queries.jsonl \
  --out data/cadqa_graph_smoke

rtk uv run cadqa dataset validate data/cadqa_graph_smoke
```

The smoke dataset should contain:

- 0-hop direct rows;
- 1-hop metric rows;
- 2-hop profile/workplane rows;
- at least a few 3+ hop checklist rows if the labels support them.

If 3+ hop rows are not ready, emit a failure manifest explaining which relation
families are missing.

## What To Avoid

Do not rebuild the old architecture:

- no separate old `graph_query` task family;
- no separate spatial-distance pipeline;
- no separate bounding-box-region pipeline;
- no hardcoded task family generators that bypass the query program;
- no LLM translator or LLM judge in the trusted generation path;
- no public DSL;
- no prompt text that cannot be traced to a hidden clause;
- no private ontology jargon in public clues unless grounded in visible code.

## Final Deliverables

Leave the repo with:

- rewritten docs;
- rewritten `epics-and-stories.yaml`;
- deleted/restarted implementation;
- new graph-first package skeleton;
- all P0 functionality implemented;
- all P1 functionality implemented;
- easy P2 functionality implemented or explicitly quarantined with blocker
  reasons;
- focused tests;
- passing compile/test smoke if feasible;
- a tiny graph smoke dataset or a documented blocker manifest;
- a concise final report listing:
  - files deleted;
  - files created;
  - commands run;
  - tests passing/failing;
  - exact next implementation slice.

## Acceptance Criteria

The task is successful if a future reader can no longer mistake this repo for a
collection of separate QA pipelines. The design and code should say one thing:

```text
CAD-QA is typed graph reasoning over executable CAD programs.
Low-hop rows are curriculum and calibration.
High-hop rows are the benchmark target.
```
