# Implementation Status

Date: 2026-05-17

The repository has been reset around the graph-first CAD-QA architecture.

The current surface is a smoke-test implementation, not a fine-tuning-ready
benchmark release. Core schema, graph, resolver, release, evaluation, and SFT
export mechanisms exist, but geometry-first dataset quality gates, template
diversity quotas, and syntax-shortcut rejection are still open work.
The critical missing implementation is not more syntax-readable prompts; it is
release-grade CAD geometry task coverage for the rows models should actually
train on.

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
- Operation, feature, parameter, profile, workplane, path, path-point,
  path-segment, selector, solid, and measurement node families.
- Stable selector-derived face nodes and same-face joins.
- Kernel selector-result summaries for directly assigned `.faces(...)`
  workplanes, with selected counts, shape types, face bbox signatures,
  kernel-backed stable face IDs, and release-ready selected-face rows when
  private trace evidence is present.
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
- Rule-based prompt rendering with clause-to-clue maps, persisted
  candidate-count annotations, hidden-clause traceability validation, and
  row-level high-hop clue breadth audits.
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
- Release verifier reports with row validation, release validation, leakage,
  public/private parity, verifier failure taxonomy, quarantine taxonomy, and
  stop-gate summaries.
- Compact machine-readable and Markdown run summaries.
- Local experiment artifact packaging with SHA-256 package summary.
- Per-row evidence tiering with quarantine reasons and release validation for
  conservative geometry or selector-surrogate labels.
- Release export command that filters smoke datasets down to
  `release_ready=true` rows.
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
- Release verifier reports include a `default_sft_geometry_critical_dominance`
  stop gate requiring the default exported training rows to be nonempty,
  geometry-critical above threshold, syntax-calibration-free, and
  quarantine-free.
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

Result on 2026-04-29:

- 10 graphs, 1,215 nodes, 2,486 relations, and 1,387 measurements.
- 45 resolved smoke rows: 10 hop-0, 6 hop-1, 13 hop-2, and 16 hop-3.
- 31 rows are release-ready under current evidence policy; 14 are quarantined
  smoke rows.
- The experiment writes a filtered `release_dataset/` with 31 valid release
  rows and zero quarantined rows.
- Quarantine reasons: 8 conservative region projections and 6
  selector-surrogate identities.
- Relation families covered in public rows: `located_on`,
  `has_material_region_geometry`, `has_void_region_geometry`,
  `has_path_tangent`, `same_selected_face_as`, and `selected_by`.
- Smoke validation passed and leakage audit passed. Release validation
  intentionally rejects non-release-ready rows until conservative region
  projections and selector-surrogate identities are upgraded or excluded.
- Full-smoke oracle baseline accuracy is 1.0; first-candidate baseline accuracy
  is 0.356.
- Filtered release oracle baseline accuracy is 1.0; first-candidate baseline
  accuracy is 0.516.
- Request exports: 45 full zero-shot requests, 6 full few-shot test requests,
  31 release zero-shot requests, and 5 release few-shot test requests.
- Public/private oracle key checks pass at 1.0 accuracy for both the 45-row
  smoke dataset and the 31-row release dataset, with zero invalid outputs and
  zero missing, duplicate, or extra responses.
- SFT exports: 45 full answer/reasoning rows and 31 release answer/reasoning
  rows, plus hop/difficulty ablations and scaling subsets. These artifacts
  validate export format only; they should not be treated as useful training
  data until geometry-first quality gates and prompt-family quotas pass.
- Run summary artifacts: `runs/experiment_smoke/run_summary.json`,
  `runs/experiment_smoke/RUN_SUMMARY.md`, and
  `runs/experiment_smoke/PAPER_RESULTS.md`.
- Public/private exports: 45 full public/private rows and 31 release
  public/private rows; public/private parity and hidden-field audits pass.
- Packaged artifact: `runs/experiment_smoke.tar.gz` with SHA-256
  `16fefe2a511f75ddef0a0f2cddad88245a9a1c436498ced5893f316d142752f8`.

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
- Kernel-measured material-region rows exist for additive `.extrude(...)` and
  `.sweep(...)` features in the reviewed trace artifact, including the first
  additive solid where no previous solid snapshot exists.
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

Still not checked as done:

- Solid measurement task coverage is still only an initial release-ready
  subset: it has volume/bbox/centroid/topology-count rows, but not broad
  variants, quotas, or answer-entropy guarantees.
- Feature-application effect coverage is still an initial release-ready subset:
  volume, bbox, topology, and centroid movement are demonstrated, but broader
  variants, quotas, and answer-entropy guarantees remain incomplete.
- Selector-result geometry remains partial: selected-count query support exists
  and is unit-tested, but the reviewed RC8 CadEvolve slice has selected count
  `1` for every kernel selector, so it does not yet demonstrate real
  selected-count training rows or enough bbox/signature variants to close
  story 12.3. The later RC10 review slice demonstrates kernel-backed edge
  nodes and 1 release-ready edge-selector spatial row, but this is not broad
  enough to close story 12.3.
- Path/distance coverage is partial: path-point and path-segment distance rows
  are demonstrated, and one kernel-edge perpendicularity/adjacency row plus
  one kernel-edge endpoint containment/distance row plus one kernel-edge
  midpoint distance row plus one kernel-edge length/midpoint row are
  demonstrated, along with one kernel-edge length-ordering row and one
  kernel-edge same-length ordering row plus one shorter-than length-ordering
  row. A
  face-spatial fixture demonstrates opposite, adjacent, intersecting, and
  perpendicular face relations, but a real CadEvolve slice has not yet
  demonstrated those face rows. Broader containment, broader intersection,
  opposite-face coverage on real CadEvolve data, broader opposite-relation,
  broader adjacency, broader parallel/perpendicular, and coaxial
  spatial-relation rows remain open, so story 12.5 is work-in-progress rather
  than implemented.
- The preview does not establish prompt-family balance, answer entropy, or
  syntax shortcut resistance. Those remain open release blockers even though
  the default SFT geometry-critical dominance gate is now implemented.
- Opposite-face on real CadEvolve data, broader containment, broader
  intersection, broader adjacency, and broader stable spatial-relation question
  families are not demonstrated by this preview.

## Open Work

- Highest priority: implement geometry-backed training rows for volume, bbox,
  centroid, topology counts/deltas, selector-result geometry, material/void
  region deltas, feature application effects, path distances, containment,
  intersection, adjacency, and stable spatial relations.
- Geometry-first release gates that reject or cap rows answerable from source
  syntax, assignment names, operation order, or literal arguments alone.
- Prompt-family, answer-entropy, and static-hop/geometry-hop quality reports
  that block release and training exports when the dataset collapses to a few
  shortcut templates.
- Training-export defaults that exclude syntax-only calibration rows unless an
  explicit calibration export is requested.
- Broader kernel snapshot association for chained features, in-place mutation
  patterns, non-assignment feature effects, and more complex chained selector
  expressions beyond the current pre-execution `.faces(...)`/`.edges(...)`
  subexpression tracing.
- Robust B-Rep adjacency and opposite-face relations.
- Material-region and void-region geometry beyond source/profile projections.
- Provider submission adapters and remote/GPU experiment orchestration.

## Quarantine Policy

Rows are release-grade only when the hidden query resolves uniquely from
supported evidence. Unsupported geometry relations, unstable topology IDs, and
AABB-only material-region guesses must be emitted as failure or quarantine
records rather than public benchmark labels.
