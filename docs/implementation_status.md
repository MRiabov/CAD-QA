# Implementation Status

Date: 2026-04-29

The repository has been reset around the graph-first CAD-QA architecture.

## Implemented In Current Surface

- Source JSONL loading and normalized source records.
- AST assignment and call-chain extraction.
- Bounded unrolling for simple `for` loops over literal iterables.
- Typed ontology graph records with nodes, relations, and measurements.
- Operation, feature, parameter, profile, workplane, path, selector, solid, and
  measurement node families.
- Stable selector-derived face nodes and same-face joins.
- Profile geometry for `.circle(...)`, `.rect(...)`, and
  `.polyline(...).close()`.
- Workplane frame extraction for default planes and explicit `cq.Plane(...)`.
- Sketch-center, path-tangent, nearest-path-point, material-region, and
  void-region evidence when conservatively derivable from source/profile data.
- Deterministic query IR with candidate-set trace, argmax/argmin, and
  reject-unless-unique policy.
- Rule-based prompt rendering with clause-to-clue maps.
- Dataset row materialization and validation.
- Deterministic group-safe smoke splits and split manifests.
- Leakage audit for source/split leaks, duplicate prompts, and query ID leaks.
- Baseline metrics for oracle, first-candidate, and null baselines.
- Prediction-response grading with hop, difficulty, relation-family,
  measurement-scope, static-hop, geometry-hop, invalid-output, missing-response,
  duplicate/extra response, response-coverage, and optional
  confidence-calibration breakdowns.
- Private-key grading for release-style public/private row exports.
- Oracle-response export and public/private key sanity grading for smoke and
  release artifacts.
- Zero-shot and few-shot model request export.
- Answer-only, candidate-trace, ablation, and scaling SFT JSONL exports.
- One-command smoke experiment orchestration.
- Dataset card, query failure report, and run artifact manifest generation.
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
  rows, plus hop/difficulty ablations and scaling subsets.
- Run summary artifacts: `runs/experiment_smoke/run_summary.json`,
  `runs/experiment_smoke/RUN_SUMMARY.md`, and
  `runs/experiment_smoke/PAPER_RESULTS.md`.
- Public/private exports: 45 full public/private rows and 31 release
  public/private rows; public/private parity and hidden-field audits pass.
- Packaged artifact: `runs/experiment_smoke.tar.gz` with SHA-256
  `16fefe2a511f75ddef0a0f2cddad88245a9a1c436498ced5893f316d142752f8`.

## Open Work

- Isolated CadQuery trace worker in the new package surface.
- Release-grade selector face identity backed by kernel selector results.
- Robust B-Rep adjacency and opposite-face relations.
- Material-region and void-region geometry beyond source/profile projections.
- Release-scale leakage audits beyond the smoke policy.
- Provider submission adapters and remote/GPU experiment orchestration.

## Quarantine Policy

Rows are release-grade only when the hidden query resolves uniquely from
supported evidence. Unsupported geometry relations, unstable topology IDs, and
AABB-only material-region guesses must be emitted as failure or quarantine
records rather than public benchmark labels.
