# Implementation Status

Date: 2026-05-24

The repository has been reset around the graph-first CAD-QA architecture.

The current surface is an active dataset-builder implementation, not a finished
fine-tuning-ready benchmark release. Core schema, graph, resolver, release,
evaluation, and SFT export mechanisms exist, and several release/training gates
are now implemented. The remaining risk is distribution quality: task-family
coverage, maximal parameterization, source-family spread, and semantic
shortcut-resistance still need substantial work.
The critical missing implementation is not more syntax-readable prompts; it is
release-grade CAD geometry task coverage for the rows models should actually
train on.
The next missing slice is value-bearing measurement prompts and multi-hop
equal-value distractor tasks: prompts should often expose concrete CAD
measurements such as area, volume, length, centroid coordinate, or distance,
then require additional geometry to disambiguate among equal or near-equal
candidates.
The newly identified quality gap is overfitting to hard-coded generator choices:
release-grade families must not permanently mean one axis, one view word, one
min/max direction, one exact value shape, one comparison, or one entity subtype
when those choices can be sampled and verified.

## Implemented In Current Surface

- Source JSONL loading and normalized source records.
- CADEvolve-oriented source manifests and audits for stable IDs, normalized
  source hashes, duplicate source IDs, source-ID/hash conflicts, duplicate
  normalized code, missing source paths, and protected source grouping
  coverage.
- Isolated CadQuery trace execution worker with timeout, worker-crash, parse,
  execution, missing-result, invalid-type, non-solid, volume, and bounding-box
  failure accounting.
- Trace snapshots for measurable top-level CadQuery assignments, final shape
  metrics, centroids, topology counts, and adjacent snapshot-derived
  volume/bbox/centroid/topology deltas when CadQuery is installed.
- Scalar trace-derived geometry measurements for resolver use, including bbox
  spans, bbox extrema, centroid coordinates, topology counts, centroid deltas,
  topology deltas, and bbox deltas.
- Trace CLI that writes `traces.jsonl` and `trace_report.json`.
- Optional graph build integration for trace JSONL, including snapshot-state
  measurements, feature application effect deltas, and exact
  kernel-measured material/void region relations where an assignment delta can
  be matched to a source feature.
- AST assignment and call-chain extraction.
- Bounded unrolling for simple `for` loops over literal iterables.
- Typed ontology graph records with nodes, relations, and measurements.
- Ontology graph relation and measurement insertion is idempotent for exact
  duplicate records, preventing repeated selector observations from inflating
  graph relation/measurement lists.
- Operation, feature, parameter, profile, workplane, path, path-point,
  path-segment, selector, solid, and measurement node families.
- Stable selector-derived face nodes and same-face joins.
- Kernel selector-result summaries for directly assigned `.faces(...)`
  workplanes, with selected counts, shape types, face bbox signatures,
  kernel-backed stable face IDs, and release-ready selected-face rows when
  private trace evidence is present.
- Kernel-selected face nodes include compiled face-center coordinates,
  face-center distance-to-origin measurements, and face-area measurements
  derived from selector-result bounding boxes.
- Kernel selector-result association for simple loop-variable `.faces(...)`
  calls when trace evidence can be matched by source line.
- Profile geometry for `.circle(...)`, `.rect(...)`, and
  `.polyline(...).close()`.
- Workplane frame extraction for default planes and explicit `cq.Plane(...)`.
- Sketch-center, path-tangent, nearest-path-point, material-region, and
  void-region evidence when conservatively derivable from source/profile data.
- Explicit path-point and path-segment geometry from visible spline points,
  including point coordinates, point distance to origin, segment vectors,
  segment midpoints, segment lengths, and midpoint distances.
- Conservative material/void region prism geometry from located profiles,
  including volume, bbox, extrusion axis, height, start/end centroids, and
  midpoint centroid.
- Kernel trace-backed material/void regions are separated from conservative
  source projections so release filtering does not quarantine exact snapshot
  region labels solely for using region geometry.
- Deterministic query IR with candidate-set trace, argmax/argmin, and
  reject-unless-unique policy.
- Initial geometry-backed query families for compiled feature volume, compiled
  feature centroid, compiled feature face count, positive kernel volume delta,
  removed kernel volume delta, bbox-bound movement, centroid-shift magnitude,
  upward centroid delta, and compiled face/edge-count deltas.
- Initial selector-result geometry query families for kernel-selected face
  identity, face bbox comparisons, and selected-count comparisons.
- Initial path-geometry query families for nearest path point to origin,
  highest path point, and longest path segment.
- Initial value-bearing measurement query families for tolerance-equal feature
  volumes, feature centroid heights, feature overall heights, selected-face
  areas, selected-edge lengths, and selected-edge midpoint distances. These
  rows expose rounded measurement values in the public prompt, keep equal-value
  candidates as distractors, and resolve with an additional geometric
  aggregation.
- Initial cross-feature value-bearing distance tasks: selected edges with equal
  measured length can be resolved by nearest midpoint distance to the solid
  centroid of a reference feature described by measured volume and centroid
  height.
- Release and SFT stop gates now require value-bearing measurement coverage and
  at least one cross-feature value-bearing row on applicable release-scale
  artifacts.
- YAML-backed prompt rendering from `prompt-templates.yaml`, with centralized
  domain-language clause templates, metric display labels, versioned query-shape
  template IDs, clause-to-clue maps, persisted candidate-count annotations,
  hidden-clause traceability validation, and row-level high-hop clue breadth
  audits.
- Dataset row materialization and validation.
- Deterministic group-safe smoke and release splits over protected source
  groups, including source family, generator, counterfactual group, explicit
  split group, and path-derived CADEvolve families when available.
- Leakage audit for source/split leaks, duplicate prompts, and query ID leaks.
- Baseline metrics for oracle, first-candidate, first-static-filter, majority,
  and null baselines with hop-slice, static-hop, geometry-hop, and difficulty
  breakdowns.
- Prediction-response grading with hop, difficulty, relation-family,
  measurement-scope, static-hop, geometry-hop, invalid-output, missing-response,
  duplicate/extra response, response-coverage, and optional
  confidence-calibration breakdowns.
- Closed-book model evaluation reports that pair answer-free request JSONL,
  public rows, private keys, and response JSONL while auditing hidden-field
  leaks, request coverage, duplicate requests, and public/private parity.
- Private-key grading for release-style public/private row exports.
- Oracle-response export and public/private key sanity grading for smoke and
  release artifacts.
- Tool-assisted upper-bound exports and grading from private verifier artifacts,
  including provenance-bearing responses and smoke/release experiment reports.
- Zero-shot and few-shot model request export.
- Answer-only, candidate-trace, ablation, and scaling SFT JSONL exports.
- One-command smoke experiment orchestration.
- Dataset card, query failure report, and run artifact manifest generation.
- Generated Markdown dataset previews for reviewing sampled prompts, query
  programs, candidate traces, gold answers, and ontology node/measurement
  samples after task-family or node-type changes.
- Dataset composition reports now include prompt-family counts and quality flags
  for syntax-only calibration rows and geometry-critical rows.
- Release verifier reports with row validation, release validation, group-safe
  split audit, leakage, public/private parity, verifier failure taxonomy,
  quarantine taxonomy, and stop-gate summaries.
- Compact machine-readable and Markdown run summaries.
- Local experiment artifact packaging with SHA-256 package summary.
- Per-row evidence tiering with quarantine reasons and release validation for
  conservative geometry or selector-surrogate labels.
- Release export command that filters smoke datasets down to rows that pass
  per-row release validation, including `release_ready=true`, quarantine, and
  geometry-first prompt-policy checks.
- Release export deterministically caps syntax-only calibration rows so
  calibration examples can remain reviewable without silently violating the
  aggregate release cap.
- One-command smoke experiments now emit both `dataset/` and filtered
  `release_dataset/` artifact trees.
- Baseline metrics are written for both the full smoke rows and the filtered
  release rows.
- Zero-shot/few-shot request exports and answer/reasoning SFT exports are
  written for both full smoke rows and filtered release rows.
- SFT export defaults now exclude syntax-only calibration, noncritical, and
  quarantined rows, and write the geometry-critical training subset unless
  calibration export is explicitly requested. SFT reports include a default
  training-readiness summary.
- SFT reports include input/training balance diagnostics and training stop
  gates for geometry-critical dominance, prompt-family balance,
  prompt-template balance, answer entropy, geometry-hop coverage, and
  syntax-only calibration share.
- Default SFT exports enforce applicable training stop gates and fail the CLI
  command when the default training subset is geometry-light, prompt-family
  collapsed, answer-collapsed, geometry-hop-light, or syntax-calibration-heavy.
  Explicit calibration exports remain allowed as review artifacts, and
  `--allow-failing-training-gates` is available for deliberate debugging.
- Release verifier reports include a `default_sft_geometry_critical_dominance`
  stop gate requiring the default exported training rows to be nonempty,
  geometry-critical above threshold, syntax-calibration-free, and
  quarantine-free.
- Release verifier reports include release-balance diagnostics and stop gates
  for prompt-family concentration, prompt-template concentration, answer
  entropy, geometry-hop coverage, and syntax-only calibration share; these
  gates are only applicable above the smoke-dataset size floor so small
  fixtures do not masquerade as release evidence.
- Public/private row views separate answer-free benchmark inputs from private
  gold answers, query programs, candidate traces, and clue maps.
- Public/private exports include row-ID parity and hidden-field leak audits.
- Smoke CLI for source inspection, graph build, query generation, dataset
  materialization, and validation.

## Latest Smoke Snapshot

Command:

```bash
rtk uv run cadqa experiment smoke \
  --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl \
  --limit 10 \
  --out runs/experiment_smoke \
  --scaling-sizes 8 16 32
```

Result reviewed on 2026-05-24:

- 10 graphs, 1,521 nodes, 2,773 relations, and 3,374 measurements.
- 57 resolved smoke rows: 10 hop-0, 6 hop-1, 13 hop-2, and 28 hop-3.
- The experiment writes a filtered `release_dataset/` with 27 rows after
  excluding 30 release-validation-invalid rows, including 25 prompt-policy
  rows and 14 quarantined rows. Some excluded rows overlap those categories.
- The filtered release tree has zero quarantined rows and passes row-level
  release validation, leakage, public/private parity, and no-quarantine gates.
  It still fails aggregate release gates on this tiny sample:
  `prompt_family_balance`, `geometry_hop_coverage`, and
  `syntax_only_calibration_cap`.
- Quarantine reasons in the full smoke rows: 8 conservative region projections
  and 6 selector-surrogate identities.
- Relation families covered in public rows include `located_on`,
  `has_material_region_geometry`, `has_void_region_geometry`,
  `has_path_tangent`, `same_selected_face_as`, `selected_by`,
  `point_on_path`, and `segment_on_path`.
- Full-smoke oracle baseline accuracy is 1.0; first-candidate baseline
  accuracy is 0.333.
- Filtered release oracle baseline accuracy is 1.0; first-candidate baseline
  accuracy is 0.667.
- Request exports: 57 full zero-shot requests, 57 full few-shot requests,
  27 release zero-shot requests, and 27 release few-shot requests.
- Public/private oracle key checks pass at 1.0 accuracy for both the 57-row
  smoke dataset and the 27-row filtered release dataset, with zero invalid
  outputs and zero missing, duplicate, or extra responses.
- SFT exports: 17 full answer/reasoning rows and 17 release answer/reasoning
  rows, plus hop/difficulty ablations and scaling subsets. These smoke-sized
  artifacts validate orchestration and format only; the release subset remains
  too small and aggregate-gate-skewed for training.
- Run summary artifacts: `runs/experiment_smoke_after_release_prefilter/run_summary.json`,
  `runs/experiment_smoke_after_release_prefilter/RUN_SUMMARY.md`, and
  `runs/experiment_smoke_after_release_prefilter/PAPER_RESULTS.md`.
- Public/private exports: 57 full public/private rows and 27 filtered release
  public/private rows; public/private parity and hidden-field audits pass.
- Packaged artifact: `runs/experiment_smoke_after_release_prefilter.tar.gz`
  with SHA-256
  `39a592a718e93a3b2f6371caba6a6743be7398637695d97d9365583f52435200`.
- Stories 11.1, 11.3, 11.4, and 11.5 are checked as implemented after manual
  review of the smoke graph/dataset reports, one-command orchestration,
  run-summary and paper-result artifacts, artifact manifest checksums, and
  packaged tarball.

## CadEvolve 50 Release-Candidate Snapshot

Result reviewed on 2026-05-24:

- Local CadEvolve source evidence is present at
  `data/cadqa_cadevolve_50/sources.jsonl`.
- The old checked-in `data/cadqa_cadevolve_50/traces.jsonl` should not be used
  as release evidence: it has 14 successful traces, 36 failed traces, no
  recorded CadQuery version, zero operation effects, and zero selector results.
- Fresh trace regeneration wrote
  `runs/release_cadevolve_50_20260524/trace_current/traces.jsonl` and
  `trace_report.json`: 46 of 50 programs executed successfully, producing 855
  snapshots, 809 operation effects, and 74 selector results. The 4 failures are
  trace-quality exclusions: 3 `non_solid_result` and 1
  `zero_or_negative_volume`.
- Fresh graph build wrote
  `runs/release_cadevolve_50_20260524/graph_current/graphs.jsonl`: 50 graphs,
  7,846 nodes, 21,718 relations, 54,265 measurements, and zero graph
  diagnostics.
- Query generation and materialization produced 470 rows across 31 prompt
  families. Of those, 386 are geometry-critical, 50 are syntax-only
  calibration, and 462 are row-level release-ready before release export.
- Filtered release export wrote
  `runs/release_cadevolve_50_20260524/release_dataset_current_capped/`: 407
  release rows, 41 release-validation exclusions, 41 prompt-policy exclusions,
  13 duplicate-prompt exclusions, and 9 syntax-only calibration rows excluded
  by the deterministic cap. All release verifier stop gates pass.
- The release verifier reports 26 prompt families, 26 prompt templates, largest
  family/template share 0.098, 99 unique answers, 5.894 answer-entropy bits,
  geometry-hop-positive share 0.902, and syntax-only calibration share 0.098.
- Default SFT export wrote
  `runs/release_cadevolve_50_20260524/release_sft_current_capped/`: 367
  answer-only rows and 367 candidate-trace reasoning rows, with scaling
  subsets of 32, 128, and 256 rows. Default training rows are 100%
  geometry-critical, syntax-calibration-free, and pass all training gates.
- Review preview:
  `runs/release_cadevolve_50_20260524/RELEASE_50_REVIEW_PREVIEW.md`. It samples
  one row per prompt family and includes graph node samples; reviewed families
  include compiled feature volume/face-count, positive and removed volume
  deltas, added and removed regions, centroid shifts, face/edge-count deltas,
  selector-result counts, selected-face area/distance, and kernel edge
  midpoint/endpoint/length spatial tasks.
- Important caveat: the leakage-safe split manifest currently assigns the 50
  sources to one protected train-only group because the available source
  metadata/path grouping collapses them together. This is acceptable for a
  fine-tuning dataset export, but not yet enough for a multi-split benchmark
  release.

## Generated Preview Review

Reviewed on 2026-05-17:

- `runs/verify_cadevolve_20260517/material_region_fix_preview.md`
- `runs/verify_cadevolve_20260517/void_region_loop_trace_preview.md`
- `runs/verify_cadevolve_20260517/solid_measurement_feature_preview.md`
- `runs/verify_cadevolve_20260517/feature_effect_delta_preview.md`
- `runs/verify_cadevolve_20260517/selector_geometry_preview.md`
- `runs/verify_cadevolve_20260517/path_geometry_preview.md`
- `runs/verify_cadevolve_20260517/selector_edge_trace_preview_v2.md`
- `runs/verify_cadevolve_20260517/edge_selector_spatial_preview.md`
- `runs/verify_cadevolve_20260517/edge_spatial_relation_preview.md`
- `runs/verify_cadevolve_20260517/edge_adjacency_relation_preview.md`
- `runs/verify_cadevolve_20260517/edge_endpoint_preview.md`
- `runs/verify_cadevolve_20260517/edge_intersection_relation_preview.md`
- `runs/verify_cadevolve_20260517/edge_endpoint_containment_preview.md`
- `runs/verify_cadevolve_20260517/edge_opposite_relation_preview.md`
- `runs/verify_cadevolve_20260517/edge_endpoint_distance_preview.md`
- `runs/verify_cadevolve_20260517/edge_midpoint_distance_preview.md`
- `runs/verify_cadevolve_20260517/edge_length_midpoint_preview.md`
- `runs/verify_cadevolve_20260517/edge_length_ordering_preview.md`
- `runs/verify_cadevolve_20260517/edge_same_length_ordering_preview.md`
- `runs/verify_cadevolve_20260517/edge_shorter_than_preview.md`
- `runs/verify_cadevolve_20260517/face_spatial_relation_preview.md`

Reviewed on 2026-05-24:

- `runs/verify_cadevolve_20260517/release_report_rc10_after_balance/RELEASE_VERIFIER_REPORT.md`
- `runs/verify_cadevolve_20260517/release_report_rc10_after_balance/release_verifier_report.json`
- `runs/verify_cadevolve_20260524/face_center_distance_preview.md`
- `runs/verify_cadevolve_20260524/release_report_rc10_after_face_center_distance/RELEASE_VERIFIER_REPORT.md`
- `runs/verify_cadevolve_20260524/face_geometry_preview.md`
- `runs/verify_cadevolve_20260524/release_report_rc10_after_face_geometry/RELEASE_VERIFIER_REPORT.md`
- `runs/verify_cadevolve_20260524/sft_rc10_after_face_geometry/sft_report.json`
- `runs/verify_cadevolve_20260524/release_export_rc10_after_split_audit/split_audit.json`
- `runs/verify_cadevolve_20260524/release_export_rc10_after_split_audit/RELEASE_VERIFIER_REPORT.md`
- `runs/verify_cadevolve_20260524/release_export_rc10_after_split_audit/SPLIT_AUDIT_PREVIEW.md`
- `runs/verify_cadevolve_20260524/release_export_rc10_after_split_audit/EPIC12_SELECTOR_PATH_PREVIEW.md`
- `runs/verify_cadevolve_20260524/release_export_rc10_after_prompt_template_ids/PROMPT_TEMPLATE_PREVIEW.md`
- `runs/verify_cadevolve_20260524/release_export_rc10_after_prompt_template_ids/release_verifier_report.json`
- `runs/verify_cadevolve_20260524/release_export_rc10_after_prompt_template_ids/MATERIAL_VOID_REGION_REVIEW.md`
- `runs/verify_cadevolve_20260524/release_export_rc10_after_template_balance_gate/release_verifier_report.json`

Conservatively checked as done:

- The preview generator itself works as a review artifact: it shows sampled
  prompts, hidden query programs, candidate traces, gold answers, and graph
  node samples with attached measurements.
- The reviewed traced CadEvolve-derived artifact contains 9 rows, of which 4
  are tagged geometry-critical and 1 is tagged syntax-only calibration.
- The SFT default export for that artifact keeps the 4 geometry-critical rows
  and excludes 5 calibration/noncritical/quarantined rows.
- The sampled geometry-critical families are backed by compiled/kernel-derived
  measurements rather than assignment-order-only syntax:
  `largest_compiled_volume_feature`, `largest_positive_volume_delta_feature`,
  `largest_face_count_delta_feature`, and `largest_added_region`.
- The graph contains scalar resolver-ready measurements for snapshot volume,
  bbox spans/extrema, centroid coordinates, topology counts,
  feature-application volume deltas, bbox deltas, centroid deltas, and topology
  deltas.
- The reviewed RC10 release export recomputes row-level split labels from the
  final release split manifest after release filtering. Its split audit reports
  no row/manifest mismatches and no protected-label split leaks.
- The reviewed epic-12 selector/path preview contains release-ready,
  geometry-critical selector-result face/edge, endpoint containment,
  path-point, and path-segment rows backed by kernel or compiled geometry
  measurements and relations.
- The reviewed prompt-template export backfills stable query-shape
  `prompt_template_id` values for existing rows and reports 27 template IDs in
  the RC10 release verifier, with sampled geometry families showing non-null
  template IDs in the generated Markdown preview.
- The reviewed template-balance export applies a release stop gate for
  prompt-template concentration. The RC10 release passes with 27 template IDs,
  largest-template share below the configured 0.35 cap, and no blocking gates.
- Kernel-measured material-region rows exist for additive `.extrude(...)` and
  `.sweep(...)` features in the reviewed trace artifact, including the first
  additive solid where no previous solid snapshot exists.
- The reviewed material/void-region RC10 preview contains release-ready,
  geometry-critical `largest_added_region` and `largest_removed_region` rows
  backed by `has_kernel_material_region_geometry` and
  `has_kernel_void_region_geometry`. Sampled region nodes have
  `conservative=false`, trace evidence, volume measurements, and signed volume
  deltas.
- Additive features are no longer misclassified as void regions when an
  adjacent trace snapshot delta is negative because the adjacent snapshot is an
  unrelated standalone solid.
- Simple `for` loops are traced body-statement by body-statement, so repeated
  CadEvolve cut operations on the same assignment target can be aligned with
  per-iteration kernel deltas.
- Repeated-target trace effects require a source-line match and are consumed in
  source-line order, preventing loop-body cut projections from being mislabeled
  when trace evidence is missing while still allowing exact repeated cut
  effects when trace evidence exists.
- In the reviewed 8-source CadEvolve cut slice, `largest_removed_region` rows
  are release-ready, geometry-critical rows backed by
  `has_kernel_void_region_geometry`.
- The reviewed 8-source CadEvolve cut slice contains 53 rows, 22
  geometry-critical rows, and 8 syntax-only calibration rows. Default SFT keeps
  19 rows and excludes 34 calibration/noncritical/quarantined rows.
- The reviewed 8-source solid-measurement slice contains 61 rows, including 30
  geometry-critical rows and 8 syntax-only calibration rows. Default SFT keeps
  27 rows and excludes 34 calibration/noncritical/quarantined rows.
- The reviewed solid-measurement preview demonstrates release-ready,
  geometry-critical rows for compiled volume plus bbox height, highest compiled
  centroid, largest compiled face count, and largest upward centroid delta.
- Story 12.1 is checked as implemented because the reviewed rows cover compiled
  solid volume, bbox, centroid, and topology-count measurements. This is not a
  statement that the full release is balanced or quota-complete.
- The reviewed feature-effect preview contains release-ready, geometry-critical
  rows for positive and removed kernel volume deltas, bbox minimum-Z movement,
  centroid-shift magnitude, upward centroid movement, face-count deltas, and
  edge-count deltas.
- The reviewed 8-source feature-effect slice contains 75 rows, including 44
  geometry-critical rows and 8 syntax-only calibration rows. Default SFT keeps
  41 rows and excludes 34 calibration/noncritical/quarantined rows.
- Story 12.2 is checked as implemented because the reviewed rows cover
  kernel-derived feature application effects for volume, bbox, topology, and
  centroid movement. This remains an initial subset, not a balanced release.
- The reviewed selector preview shows 3 release-ready, geometry-critical
  `selected_face` rows backed by `has_kernel_stable_face_id`. After source-line
  trace matching, all 16 selector nodes in the reviewed RC8 slice are
  kernel-backed, including simple loop-variable selectors.
- Selector tracing now evaluates selector subexpressions before executing the
  containing statement, so a `.faces(...)` or `.edges(...)` call inside a longer
  modeling chain is measured as the selector result rather than as the final
  assigned solid. A 10-source RC10 review slice captures 25 selector results,
  including 12 kernel-backed edge nodes from a real `.edges()` call; the
  preview labels no-argument selectors as `.edges()` rather than as the
  assignment variable name.
- The reviewed edge-selector spatial preview adds 1 release-ready,
  geometry-critical row backed by `has_kernel_stable_edge_id`. Its candidate
  trace starts from 12 kernel-selected edges from a real CadEvolve `.edges()`
  call, filters to X-spanning edges, filters to the negative-Y side, and then
  uses kernel-measured `bbox_max_z` to select the unique answer.
- The reviewed edge spatial-relation preview upgrades that row to require
  `perpendicular_to`, derived from kernel-selected edge bounding-box axes. The
  reviewed graph contains 36 `parallel_to` and 96 `perpendicular_to` relations
  on the 12 selected edge nodes, plus a release-ready row whose candidate trace
  preserves broad intermediate candidate sets before the final unique
  `bbox_max_z` aggregation.
- The reviewed edge adjacency preview further requires `adjacent_to`, derived
  only when two kernel-selected edge bounding boxes share an endpoint. The
  reviewed graph contains 48 `adjacent_to` relations on the same real
  CadEvolve `.edges()` source, and the single release-ready row is backed by
  `has_kernel_stable_edge_id`, `perpendicular_to`, and `adjacent_to`.
- The reviewed edge endpoint preview adds 8 deduplicated
  `edge_endpoint` nodes from the same compiled selector-result edge boxes,
  with 24 `endpoint_of` and 24 `has_endpoint` relations. It adds 1
  release-ready, geometry-critical row that filters compiled endpoint
  coordinates and selects the unique endpoint with the largest `coordinate_z`.
- The reviewed edge intersection preview adds `intersects` relations only
  when two kernel-selected edge boxes share a compiled endpoint. The reviewed
  graph contains 48 `intersects` relations on the same real CadEvolve
  `.edges()` source, and the single release-ready edge row is backed by
  `has_kernel_stable_edge_id`, `perpendicular_to`, `adjacent_to`, and
  `intersects`.
- The reviewed edge endpoint containment preview adds `contained_in` for
  compiled endpoint-to-edge membership from the same kernel-selected edge
  geometry. The reviewed graph contains 24 `contained_in` relations, and the
  release-ready endpoint row is backed by both `endpoint_of` and
  `contained_in` before coordinate filtering.
- The reviewed edge opposite preview adds `opposite_to` between
  kernel-selected edges only when they are parallel, same compiled length, and
  share no endpoint. The reviewed graph contains 36 `opposite_to` relations,
  and the release-ready edge row is backed by `has_kernel_stable_edge_id`,
  `perpendicular_to`, `adjacent_to`, `intersects`, and `opposite_to`.
- The reviewed edge endpoint distance preview adds a typed global-origin node,
  `distance_to` relations from compiled edge endpoints to that origin, and
  `distance_to_origin` measurements. The RC10 preview contains one
  release-ready, geometry-critical endpoint row backed by `endpoint_of`,
  `contained_in`, and `distance_to`, with `entity_geometry` and
  `relation_metric` measurement scopes.
- The reviewed edge midpoint distance preview adds compiled midpoint
  coordinates and `midpoint_distance_to_origin` measurements to kernel-selected
  edges, plus `distance_to` relations from those edges to the global origin.
  On the real RC10 CadEvolve slice, the new release-ready row keeps all 12
  kernel-selected edge candidates through selector identity and distance
  evidence, narrows to 4 X-spanning edges, then 2 positive-Z midpoint edges,
  and resolves uniquely by `midpoint_y` aggregation.
- The reviewed edge length midpoint preview adds compiled `edge_length`
  measurements from kernel-selected edge endpoints and a resolver-side
  metric-ratio comparison for geometry relations like edge length versus
  midpoint distance. On the real RC10 CadEvolve slice, the new release-ready
  row keeps all 12 kernel-selected edge candidates through selector identity
  and length evidence, narrows to 4 positive-Z midpoint edges, then 2 edges
  whose compiled length is less than their compiled midpoint distance to the
  global origin, and resolves uniquely by `midpoint_x` aggregation.
- The reviewed edge length ordering preview adds `longer_than` and
  `shorter_than` relations between kernel-selected edges when their compiled
  bbox endpoint lengths differ. On the real RC10 CadEvolve slice, the new
  release-ready row keeps all 12 kernel-selected edge candidates through
  selector identity, narrows to 8 edges with a `longer_than` relation, then 2
  positive-Z midpoint edges, and resolves uniquely by `midpoint_y`
  aggregation.
- The reviewed edge same-length ordering preview adds `same_length_as`
  relations between kernel-selected edges with equal compiled endpoint
  lengths. On the real RC10 CadEvolve slice, the new release-ready row keeps
  all 12 kernel-selected edge candidates through selector identity and
  `same_length_as`, narrows to 8 edges with `longer_than`, then 2 positive-Z
  midpoint edges, and resolves uniquely by `midpoint_y` aggregation.
- The reviewed edge shorter-than preview demonstrates the complementary
  `shorter_than` length-ordering relation on the real RC10 CadEvolve slice.
  The new release-ready row keeps all 12 kernel-selected edge candidates
  through selector identity, narrows to 8 edges with `shorter_than`, then 2
  positive-Z midpoint edges, and resolves uniquely by `midpoint_x`
  aggregation.
- Face spatial extraction now derives face normal axes and conservative
  `parallel_to`, `perpendicular_to`, `adjacent_to`, `intersects`, and
  `opposite_to` relations from kernel-selected face bounding boxes. The
  reviewed face-spatial Markdown preview is a manual review fixture because
  the current RC10 CadEvolve slice does not contain a supported all-face
  selector row that demonstrates the new family. The fixture row is
  release-ready and geometry-critical, but this is not enough to close broader
  face-relation coverage for story 12.5.
- The reviewed path-geometry preview shows release-ready, geometry-critical
  rows for nearest visible spline path point to origin, highest visible spline
  path point, and longest visible spline path segment. The reviewed 8-source
  path slice contains 87 rows overall, including 61 geometry-critical rows and
  8 syntax-only calibration rows. Default SFT keeps 58 rows and excludes 29
  calibration/noncritical/quarantined rows.
- The reviewed path-geometry SFT report passes the default training geometry
  dominance gate: 58 of 58 default training rows are geometry-critical, with
  zero syntax-only and zero quarantined rows. The release verifier includes the
  `default_sft_geometry_critical_dominance` stop gate and passes that gate for
  this slice while still correctly blocking release on quarantined rows.
- Story 12.6 is checked as implemented because the SFT export and release
  verifier now enforce and report geometry-critical dominance for the default
  training surface.
- The reviewed RC10 CadEvolve release-balance report contains 134 rows and now
  applies stop gates for prompt-family balance, prompt-template balance,
  answer entropy, and geometry-hop coverage plus a cap for syntax-only
  calibration rows. The
  reviewed artifact passes those gates with 30 prompt families,
  largest-family share 0.075, 51 unique answers, answer entropy 5.30 bits,
  geometry-hop-positive share 0.925, and syntax-only calibration share 0.075.
- The same reviewed report still correctly fails release on
  `release_validation` and `no_quarantined_rows` because 3
  `selector_identity_surrogate` rows remain quarantined. Story 11.6 is checked
  as implemented for reporting and gating; this is not a claim that the dataset
  is release-ready.
- The reviewed face-geometry preview adds compiled face-center
  distance-to-origin and face-area measurements for kernel-selected faces. It
  demonstrates 2 release-ready, geometry-critical CadEvolve rows for
  `nearest_kernel_selected_face_center_to_origin` and 2 release-ready,
  geometry-critical CadEvolve rows for `largest_kernel_selected_face_area`.
  These rows start from two kernel-selected face candidates and resolve only
  through compiled `distance_to_origin` or `face_area` aggregation.
- The preview generator now reports total measurement counts and omitted
  measurement names for node samples when measurements are truncated, so newly
  added node measurements such as `face_center`, `distance_to_origin`, and
  `face_area` remain visible during manual review.
- The regenerated RC10 face-geometry graph drops from 10,543 to 10,456
  measurements after exact duplicate measurement insertion is made idempotent;
  the resolved row count and reviewed face-geometry rows remain unchanged.
- The same graph drops from 3,339 to 3,321 relations after exact duplicate
  relation insertion is made idempotent; a duplicate scan over the regenerated
  RC10 graph reports zero exact duplicate relations.
- The reviewed RC10 face-geometry SFT export writes 109 default training rows
  from 138 input rows, excludes all 10 syntax-only calibration rows plus
  noncritical/quarantined rows, and reports passing training stop gates for
  geometry-critical dominance, prompt-family balance, prompt-template balance,
  answer entropy, geometry-hop coverage, and syntax-only calibration share.
  The default export now enforces applicable training gates and would fail on
  a large collapsed training export unless `--allow-failing-training-gates` is
  provided.
- Story 10.4 is checked as implemented because the default SFT export excludes
  syntax-only calibration/noncritical/quarantined rows and enforces applicable
  training balance gates. This does not close broader row/template-level
  shortcut resistance.
- The reviewed filtered RC10 release SFT export writes 106 answer-only rows
  and 106 candidate-trace reasoning rows from 116 release rows; the 10
  syntax-only calibration rows are excluded from default training. It writes
  ablation exports by difficulty and hop count plus scaling exports for 8, 16,
  and 32 row subsets, and all training gates pass. Stories 10.1, 10.2, and
  10.3 are checked as implemented for answer-only, reasoning, ablation, and
  scaling SFT artifacts.
- The shortcut-resistance report is now first-class in dataset reports,
  dataset cards, and the `dataset shortcut-report` CLI. The reviewed RC10
  CadEvolve-derived report contains 138 rows across 32 prompt families,
  geometry-hop-positive share 0.928, geometry-critical share 0.790, and
  syntax-only calibration share 0.072. It flags `first_operation` as the only
  zero-geometry-hop and syntax-only family, and separately flags five low
  geometry-critical families: `cad_browsecomp_profile`, `first_operation`,
  `highest_workplane`, `latest_repeated_selector`, and
  `profile_on_workplane`. Story 9.7 is checked as implemented for reporting;
  this is not a row/template-level blocking gate.
- The release verifier now uses the shortcut-resistance report as a release
  stop gate: any low geometry-critical prompt family blocks release unless
  that family is explicitly syntax-only calibration and remains under the
  separate syntax-only calibration cap. The reviewed RC10 report now fails
  `geometry_critical_prompt_family_coverage` in addition to
  `release_validation` and `no_quarantined_rows`, which is the desired
  conservative behavior while non-training prompt families remain in the
  source dataset. Story 8.8 is checked as implemented for release blocking
  gates.
- Release export now treats the release verifier as authoritative: artifacts
  are written, but the default `dataset export-release` command exits nonzero
  when verifier stop gates fail. The explicit
  `--allow-failing-release-gates` flag remains available for review artifacts.
  Release export now pre-filters rows that fail per-row release validation, so
  prompt-policy-invalid rows are excluded before verifier gates run. The
  reviewed RC10 export filters out 22 prompt-policy-invalid rows, including 3
  already-quarantined rows, and writes 116 release-valid rows with zero
  blocking verifier gates. Story 8.7 is checked as implemented for
  release-ready filtering plus gate enforcement.
- Release-scale verifier and quarantine reporting is checked as implemented:
  the reviewed RC10 release verifier reports row validation, release
  validation, quarantine, leakage, public/private, prompt-family balance,
  prompt-template balance, answer entropy, geometry-hop coverage,
  syntax-only calibration share, geometry-critical family coverage, and
  row-level prompt-policy gates. Story 11.2 is checked as implemented.
- Individual clue-breadth gating is checked as implemented: high-hop resolver
  clauses can fail with `clue_too_narrow`, and row validation audits clue
  maps against candidate-count traces. Story 7.4 is checked as implemented.
- Geometry-first prompt policy is now row-level in validation. Release
  validation raises `geometry_first_prompt_policy` errors for non-calibration
  rows that are not geometry-critical and for literal property clauses that
  expose source-syntax selectors or values; syntax-only calibration rows remain
  warnings and are controlled by the separate calibration cap. The reviewed
  RC10 release-validation report has 22 prompt-policy errors: 19
  non-geometry-critical prompt errors across `highest_workplane`,
  `profile_on_workplane`, `cad_browsecomp_profile`, and
  `latest_repeated_selector`, plus 3 literal property-clause errors on
  `selected_face`. It also reports 10 syntax-only calibration warnings. Story
  7.5 is checked as implemented for the explicit geometry-first policy gate;
  the raw dataset still contains blocked rows, while the filtered release
  export removes them.

Checked as implemented with remaining scale caveats:

- In this document, "implemented" means that the mechanism exists and has been
  demonstrated in reviewed artifacts. It does not mean the family is balanced,
  fully parameterized, or sufficient for a headline benchmark/training release.
- Solid measurement, feature-application effect, selector-result geometry,
  path/distance, material/void-region, and stable spatial-relation rows are
  implemented and demonstrated in reviewed smoke/RC10 artifacts, but larger
  releases still need better distribution across CadEvolve source families.
- The release verifier establishes prompt-family balance, prompt-template
  balance, answer entropy, geometry-hop coverage, syntax-only calibration,
  geometry-critical family coverage, and row-level geometry-first prompt-policy
  gates for release-scale artifacts. Future prompt families may still need
  additional semantic shortcut rules as new source patterns appear.
- Prompt-family balance now blocks generated release/SFT task families outside
  the 1%-10% distribution band. This catches both dominant task families and
  sparse present families, but intended families that produce zero rows still
  need an explicit intended-family manifest to become machine-gated.
  Rechecking the current CadEvolve-50 release artifact with this stricter gate
  blocks release on `prompt_family_balance`: 18 present task families are below
  the 1% floor and no present family is above the 10% cap.
- Value-bearing measurement and tolerance-equal distractor rows are implemented
  for feature volume, centroid height, centroid X/Y coordinate, overall height,
  selected-face area, selected-face center Z, selected-edge length,
  selected-edge midpoint distance, endpoint Z, added-material region volume,
  and selected-edge distance to a geometry-described reference feature. The
  reviewed CadEvolve-50 check on 2026-05-24 generated 602 raw rows, 543
  release-valid rows, and 494 default SFT rows, with release and SFT
  value-bearing gates passing. Reports now surface the rounding/tolerance
  policy used by these tasks: six decimal places and an absolute match
  tolerance of 1e-6.
- Opposite-face rows on broad real CadEvolve data, broader containment,
  broader intersection, broader adjacency, and broader stable spatial-relation
  distributions remain scale/coverage work rather than unchecked core
  implementation stories.

## Open Work

- Replace hard-coded query families with maximally parameterized families.
  Current generator names such as `frontmost_longer_positive_z_kernel_edge`,
  `frontmost_same_length_longer_positive_z_kernel_edge`, and
  `rightmost_shorter_positive_z_kernel_edge` expose the immediate axis/view
  problem, but the rule is broader: axes, signs, min/max direction, comparison
  relation, exact values, target/reference entity type, and subtype choices
  should be sampled per row whenever the verifier supports the variation.
- Rewrite sparse direct selector/count/extremum families as graph-hop narrowing
  programs instead of treating them as unusable when the whole model lacks a
  unique global largest/smallest candidate. These rows should use sampled
  geometry-derived relations such as shared height, plane, axis, equal
  measurement bucket, containment, adjacency, or distance to a sampled reference
  entity to define a nontrivial candidate subset before the final selector.
- Add release/SFT reporting and gates for parameter balance. Any family that
  collapses onto one global axis, view word, extremum direction, comparison,
  value shape, or entity type should be capped, blocked, or treated as
  review-only until the sampled distribution is healthy.
- Add an intended-family manifest so planned release task families that generate
  zero rows block release instead of relying on manual review.
- Complete benchmark-release gating. Explicit release-tier verifier profiles now
  exist for `smoke`, `release-candidate`, and `benchmark-release`, and the
  benchmark-release profile enforces row counts, default SFT row counts,
  geometry-hop coverage, default SFT geometry-critical dominance, syntax-only
  caps, value-bearing and cross-feature coverage bands, prompt-template share,
  unique-answer count, answer entropy, candidate breadth, and non-collapsed split
  group coverage. Remaining benchmark-release gates are sampled parameter
  balance, intended-family zero-row coverage from a manifest, and machine-checked
  preview/test evidence for changed release families.
  Rechecking the current CadEvolve-50 release artifact with
  `--release-tier benchmark-release` blocks release on row count, split group
  coverage, default SFT row count, prompt-family balance, prompt-template
  balance, answer entropy, geometry-hop coverage, main BrowseComp hop coverage,
  syntax-only calibration cap, cross-feature value-bearing coverage, and
  candidate breadth.
- Broaden value-bearing and tolerance-equal coverage beyond the implemented
  core to radius/diameter/angle once those measurements are extracted broadly,
  additional face/endpoint/material/void coordinate combinations, and larger
  real CadEvolve distributions. Removed-region equal-volume mining is
  implemented and unit-tested, but produced no rows in the reviewed CadEvolve-50
  sample.
- Broaden cross-feature value-bearing tasks beyond the implemented selected-edge
  midpoint to reference-feature centroid family. Additional target/reference
  combinations should include faces, endpoints, material/void regions, and
  feature-to-feature distances where public clues describe geometry rather than
  source names.
- Broaden the current geometry-backed training rows across more CadEvolve
  source families and larger generated releases: volume, bbox, centroid,
  topology counts/deltas, selector-result geometry, material/void region
  deltas, feature application effects, path distances, containment,
  intersection, adjacency, and stable spatial relations are implemented in the
  reviewed smoke/RC10 surfaces, but still need scale and distribution work.
- Replace or stop generating rows currently excluded by geometry-first release
  filtering: noncritical workplane/profile/selector prompts, literal
  selector-property prompts, and syntax-only calibration rows beyond the cap.
- Extend prompt-policy checks when new source-syntax shortcut patterns appear
  outside the current geometry-critical, literal-property, and calibration
  gates.
- Broader kernel snapshot association for chained features, in-place mutation
  patterns, non-assignment feature effects, and more complex chained selector
  expressions beyond the current pre-execution `.faces(...)`/`.edges(...)`
  subexpression tracing.
- Robust B-Rep adjacency and opposite-face relations.
- Broader material-region and void-region geometry association for source
  patterns not covered by current trace snapshots/effects and conservative
  profile projections.
- Provider submission adapters and remote/GPU experiment orchestration.

## Quarantine Policy

Rows are release-grade only when the hidden query resolves uniquely from
supported evidence. Unsupported geometry relations, unstable topology IDs, and
AABB-only material-region guesses must be emitted as failure or quarantine
records rather than public benchmark labels.
