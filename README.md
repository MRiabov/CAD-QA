# CAD-QA

CAD-QA is a graph-first benchmark pipeline for CadQuery program reasoning. The
project is organized around one concept:

```text
typed CAD ontology graph + deterministic query/verifier + hop-counted prompts
```

Low-hop rows and high-hop rows are slices of the same machinery. There is no
separate simple-QA pipeline and no separate graph-query task family.

## Architecture

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

The current implementation is intentionally small after the graph-first reset.
It supports:

- JSONL source loading;
- AST-backed assignment and call-chain extraction;
- bounded unrolling for simple `for` loops over literal iterables;
- feature, operation, parameter, profile, workplane, path, selector, solid, and
  measurement nodes;
- stable selector-derived face nodes and same-face joins;
- `before`, `after`, `input_to`, `parameter_of`, `uses_profile`, `used_by`,
  `located_on`, `has_measurement`, `selected_by`, `same_selected_face_as`,
  `has_path_tangent`, `nearest_point_on_path`, `adds_material_to`, and
  `removes_material_from` relations;
- profile geometry for `.circle(...)`, `.rect(...)`, and
  `.polyline(...).close()`;
- workplane frame extraction for default planes and explicit `cq.Plane(...)`
  calls;
- sketch-center, path-tangent, nearest-path-point, and conservative
  material/void-region measurements;
- deterministic query programs with candidate-set traces, argmax/argmin, and
  reject-unless-unique policy;
- rule-based prompt rendering from query clauses;
- dataset row materialization, quarantine tagging, smoke validation, and release
  validation.

This surface is suitable for smoke testing and controlled release-candidate
exports. It is not automatically a fine-tuning-ready benchmark surface:
release/SFT artifacts must pass the active geometry-first gates, and manual
preview review must confirm that task families are not collapsed onto
hard-coded generator choices such as one axis, one min/max direction, one value
shape, one comparison relation, or one entity type.

The benchmark-release target is the canonical public-release bar, not a nice
extra check. A public benchmark or real fine-tuning dataset must satisfy the
numeric tier in [`specs/dataset-spec.md`](specs/dataset-spec.md): at least
10,000 release rows, at least 10,000 default SFT rows, generated task families
in the 1%-10% band with at least 10 generated release families, at least 20
prompt templates with no template above 5%, at least 95%
geometry-hop-positive rows, at least 99% geometry-critical default SFT rows, 0%
syntax-only default SFT rows, value-bearing and cross-feature coverage targets,
parameter-balance targets, manual preview/test evidence, and a non-collapsed
multi-split release. Smoke and release-candidate artifacts are development
evidence only.

## Quick Start

Inspect source records:

```bash
uv run cadqa sources inspect --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl
```

Build ontology graphs:

```bash
uv run cadqa graph build \
  --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl \
  --limit 10 \
  --out runs/graph_smoke
```

Generate deterministic smoke queries:

```bash
uv run cadqa query smoke \
  --graph runs/graph_smoke/graphs.jsonl \
  --out runs/query_smoke
```

Materialize and validate public rows:

```bash
uv run cadqa dataset materialize \
  --queries runs/query_smoke/queries.jsonl \
  --out data/cadqa_graph_smoke

uv run cadqa dataset validate data/cadqa_graph_smoke

uv run cadqa dataset audit data/cadqa_graph_smoke

uv run cadqa dataset quarantine data/cadqa_graph_smoke

uv run cadqa dataset card data/cadqa_graph_smoke

uv run cadqa dataset export-public-private data/cadqa_graph_smoke

uv run cadqa dataset validate data/cadqa_graph_smoke --release

uv run cadqa dataset export-release \
  data/cadqa_graph_smoke \
  --out data/cadqa_graph_release_smoke
```

The release validation command is expected to report `valid: false` while smoke
rows still include conservative region projections or selector-surrogate
identities. Use `cadqa dataset quarantine` to inspect those rows before deciding
whether to upgrade, exclude, or keep them as training-only artifacts.
`cadqa dataset export-release` writes only `release_ready=true` rows.

For benchmark-release claims, validate the stricter tier explicitly:

```bash
uv run cadqa dataset release-report \
  data/cadqa_graph_release_smoke \
  --release-tier benchmark-release
```

The artifact is not benchmark-release ready unless that report has
`valid_for_release=true` and no blocking gates.

Run simple baselines, grade release-style model responses, and export SFT rows:

```bash
uv run cadqa evaluation baseline \
  --rows data/cadqa_graph_smoke/rows.jsonl \
  --out runs/baseline_smoke

uv run cadqa evaluation grade-private \
  --public data/cadqa_graph_release_smoke/public.jsonl \
  --private data/cadqa_graph_release_smoke/private.jsonl \
  --responses runs/model_responses.jsonl \
  --out runs/model_eval

uv run cadqa evaluation export-oracle-responses \
  --private data/cadqa_graph_release_smoke/private.jsonl \
  --out runs/model_eval/oracle_responses.jsonl

uv run cadqa evaluation export-requests \
  --rows data/cadqa_graph_smoke/rows.jsonl \
  --out runs/eval_requests/zero_shot_requests.jsonl \
  --mode zero-shot

uv run cadqa training export-sft \
  --rows data/cadqa_graph_smoke/rows.jsonl \
  --out runs/sft_smoke \
  --scaling-sizes 8 16 32

uv run cadqa dataset preview \
  data/cadqa_graph_smoke \
  --graphs runs/graph_smoke \
  --out runs/feature_preview.md \
  --family largest_compiled_volume_feature \
  --node-type feature \
  --sample-per-family 2 \
  --seed 17
```

The SFT export command writes only geometry-critical rows by default and
excludes syntax-only calibration, noncritical, and quarantined rows. Do not
treat its output as a model-training dataset unless the input rows also pass
the broader geometry-first quality gates: generated prompt families must each
represent 1%-10% of the export, value-bearing and cross-feature coverage must
pass thresholds, parameterized families must have healthy sampled distributions,
and geometry-derived clauses must be necessary for the main benchmark answers.
Use `--include-calibration` only for explicit calibration exports.

Use `cadqa dataset preview` after adding or changing a task family, graph node
type, or measurement extractor. It writes a Markdown artifact containing
sample prompts, query programs, candidate traces, gold answers, and optional
graph node/measurement samples. The smoke experiment also writes
`dataset/GENERATED_PREVIEW.md` automatically.

Release and SFT reports accept `--release-tier smoke`,
`--release-tier release-candidate`, or `--release-tier benchmark-release`.
Use `benchmark-release` only when the artifact is meant to satisfy the numeric
benchmark tier; it intentionally blocks small smoke datasets and train-only split
collapses.

Run the full smoke workflow as one command:

```bash
uv run cadqa experiment smoke \
  --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl \
  --limit 10 \
  --out runs/experiment_smoke

uv run cadqa experiment package \
  --run runs/experiment_smoke \
  --out runs/experiment_smoke.tar.gz

uv run cadqa experiment paper-results \
  --run runs/experiment_smoke
```

The smoke experiment writes graph/query/dataset/baseline/SFT artifacts plus a
full smoke dataset, filtered `release_dataset/`, public/private row views,
dataset cards, query failure report, quarantine reports, leakage audits,
validation reports, full-smoke and release-subset baselines, full-smoke and
release-subset public/private oracle-grade sanity checks, full-smoke and
release-subset request exports, full-smoke and release-subset SFT exports, run
summary, generated paper-results snapshot, and artifact manifest.

Run tests:

```bash
rtk uv run python -m compileall -q dataset
rtk uv run pytest -q
```

## Row Contract

Every internal row is generated from a hidden query program and includes:

- `row_id`;
- `source_id`;
- public source code;
- public prompt;
- answer format and answer contract;
- gold answer;
- hidden query program;
- candidate-set trace;
- relation families used;
- measurement scopes used;
- logical, static, and geometry hop counts;
- difficulty bucket;
- verifier status.
- evidence tier;
- release readiness flag;
- quarantine reasons for rows backed by conservative projections or surrogate
  identities.

Release directories also include `public.jsonl` and `private.jsonl`.
`public.jsonl` is answer-free and contains model inputs plus public metadata.
`private.jsonl` contains gold answers, hidden query programs, candidate traces,
and clue maps for grading and audit. `public_private_report.json` records row
counts, field splits, row-ID parity, and hidden-field leak checks.

The answer contract is selected by the query family and must keep prompt
wording, resolver output, public recoverability, and grading in sync. Closed-book
public rows should prefer source-visible or computed answers such as source
variables, coordinates, numbers, booleans, integers, or exposed candidate
labels. Internal `entity_id` answers are reserved for debug/tool-assisted rows
unless the public prompt provides the exact candidate IDs.

Families may emit both selection-style rows and identification/location rows.
Selection rows expose a public candidate list capped at 7 displayed choices and
expect a label such as `A`.
Selector-expression selection rows are a special selection form: the public
candidate list contains plausible canonical CadQuery selector expressions such
as `base.edges(">Z")`, but the expected answer is still the candidate label.
The displayed choices are derived from the real measured selector candidates
used by the resolver; synthetic selector strings are not padded in as
distractors. These rows train selector syntax without requiring arbitrary-code
execution or accepting every semantically equivalent selector spelling.
Identification/location rows ask for the entity's public representation, such
as a coordinate tuple, endpoint pair, source variable, or scalar value. These
styles should be sampled with quotas; they should not be produced as duplicate
variants of every hidden query by default.

Prediction metrics include accuracy, response coverage, missing-response rate,
invalid-output rate, duplicate/extra response counters, optional confidence
calibration when responses include `confidence`, and breakdowns by difficulty,
hop count, relation family, and measurement scope.

## BrowseComp-Style CAD Reasoning

The hard CAD-QA rows should resemble BrowseComp in benchmark shape: short
verifiable answers, high uncertainty, distractor-rich clues, and persistent
reasoning over entangled evidence. CAD-QA differs from web browsing benchmarks
because the trusted evidence is a CadQuery-derived ontology graph and verifier,
not an LLM judge.

Main benchmark and fine-tuning rows must require geometry-derived evidence such
as profile geometry, workplane frames, selector results, path geometry, feature
effects, topology deltas, centroids, distances, material regions, or void
regions. Rows answerable from assignment names, operation order, literal
arguments, or source syntax alone are calibration rows and should not dominate
release or training exports.

Task families should be maximally parameterized. Axes, signs, min/max
direction, exact measurement values, comparison relations, aggregation metrics,
target entity type, reference entity type, and rendered view words should be
sampled row parameters whenever the verifier can support the variation. A
schema-valid dataset that repeatedly asks the same hard-coded spatial/value
pattern is still a weak training set. Release exports block generated task
families below 1% or above 10% of the row distribution.

The critical path is kernel/geometry-backed task coverage: volumes, bounding
boxes, centroids, topology counts and deltas, feature effects, selector-result
geometry, material/void region deltas, path distances, containment,
intersection, adjacency, and other stable spatial relations. Export plumbing is
not enough; these geometry families must dominate the rows used for model
training.

CadEvolve source groups matter. If a generated artifact collapses all sources
into one protected train-only group, it can still validate fine-tuning export
format and training mechanics, but it is not a multi-split benchmark release.

LLM calls are allowed only for optional external evaluation or wording
experiments. They are not part of trusted generation or grading.
