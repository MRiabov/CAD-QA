# 06 — Materialize, validate, release

## Purpose

Turn resolved query programs into `DatasetRow`s, validate them, assign group-safe splits,
produce answer-free public and private views, and export the release-ready subset with a
blocking-gate report.

## Inputs / outputs

- **Input:** **queries** artifact plus the matching **graphs** sidecar
  (`pipeline/00-overview.md`).
- **Output artifacts (matching the contract):**
  - **rows** (`rows.parquet`) — `DatasetRow` fields (see `pipeline/00-overview.md`), plus
    `split`.
  - **public** / **private** (`public.parquet`, `private.parquet`) and
    `public_private_report.json`.
  - `split_manifest.json`, `dataset_report.json`, `validation_report.json`,
    `release_validation_report.json`, `leakage_audit.json`, `split_audit.json`,
    `quarantine_report.json`, `failure_report.json`, `failure_manifest.*`, `DATASET_CARD.md`,
    `GENERATED_PREVIEW.md`, `preview_evidence.json`.
  - a release export directory containing only `release_ready=true` rows with its own
    validation, leakage, non-release-readiness, preview, and Query verifier reports.

## Requirement

Every row must be resolved by the Query verifier and self-describing, and no private field
may leak into the public view. For the release claim: rows must satisfy schema and
public-answer contracts, record logical/static/geometry hop counts, carry evidence-tier
metadata and non-release-ready status, share a split only with their protected group, and
the release export must be empty of non-release-ready rows and carry a report whose
blocking gates all pass at the declared tier.

## Current status

**exists.** Materialization, validation, audit, non-release-ready handling, split,
public/private, preview, release export, and release reporting are present and readable
(`dataset/release/`, `dataset/cli.py::_cmd_dataset_materialize` and siblings). No dataset was
built while writing this doc.

## Verification

```bash
rtk uv run cadqa dataset materialize \
  --queries runs/query/queries.parquet --graphs runs/graph --out runs/dataset
rtk uv run cadqa dataset validate runs/dataset
rtk uv run cadqa dataset audit runs/dataset
rtk uv run cadqa dataset quarantine runs/dataset
rtk uv run cadqa dataset export-public-private runs/dataset
rtk uv run cadqa dataset validate runs/dataset --release
rtk uv run cadqa dataset export-release runs/dataset --out runs/release_dataset
rtk uv run cadqa dataset release-report runs/dataset --release-tier benchmark-release
```

The focused tests include `tests/test_graph_first_pipeline.py::test_validation_rejects_overwide_public_candidate_label_lists`,
`::test_validation_rejects_duplicated_gold_candidate_description`, and the smoke/integration
tests around `materialize`/`validate`. The one-command check is
`rtk uv run cadqa experiment smoke --sources-jsonl runs/cadevolve_sources.parquet --limit 10 --out runs/experiment_smoke`.

## Local decisions

### D1 — Row identity is `row:{query_id}`

- **Status:** accepted.
- **Context:** Row IDs must be globally unique and traceable to the producing query, and
  earlier CadQuery-program+family IDs collided.
- **Decision:** `dataset/release/materialize.py::materialize_row` sets
  `row_id = f"row:{query.query_id}"`.
- **Consequences:** Duplicate row IDs are a validation error; public/private parity uses the
  full query ID.

### D2 — Hop counts are derived, not asserted

- **Status:** accepted.
- **Context:** Difficulty must be auditable and not just a label.
- **Decision:** `logical_hop_count` is the query's `hop_count`; `static_hop_count` counts
  `property_equals` clauses and `before`/`after`/`input_to`/`parameter_of` relations; and
  `geometry_hop_count = hop_count - static_hop_count` (`materialize.py::materialize_row`).
- **Consequences:** Syntax-only rows have `geometry_hop_count == 0` and are calibration;
  geometry-critical gates read these fields.

### D3 — Evidence tier and non-release-ready status are computed per row

- **Status:** accepted.
- **Context:** Conservative region projections and CadQuery-selector surrogate identities
  are not release-grade.
- **Decision:** `dataset/release/materialize.py::_evidence_policy` returns an `evidence_tier`
  (`source_static_or_analytic`, `quarantine`, `unresolved`) and `quarantine_reasons`
  (`conservative_region_projection`, `selector_identity_surrogate`, `unresolved_verifier`);
  `release_ready = not quarantine_reasons`.
- **Consequences:** Quarantined rows stay in the full dataset for diagnostics and are
  excluded from release export (`dataset/release/quarantine.py`).

### D4 — Splits are assigned before public/private export

- **Status:** accepted.
- **Context:** Every row needs a split and the split must be group-safe.
- **Decision:** `dataset/cli.py::_cmd_dataset_materialize` calls
  `dataset/release/split.py::assign_splits` and writes split-sharded Parquet plus a
  `split_manifest.json`; `leakage_audit` and `split_audit` run against that manifest.
- **Consequences:** A CadQuery-program-only dataset collapses to `train` and is reported as
  single-split.

### D5 — Release export is a filtered tree with its own evidence

- **Status:** accepted.
- **Context:** Release numbers must be auditable against the broader generation surface.
- **Decision:** `dataset/release/release.py::export_release_dataset` filters to release-ready
  rows, then applies deterministic caps (syntax-only calibration, family/template/value
  shares, parameter diversity) and writes its own validation, leakage, non-release-readiness,
  preview, and Query verifier reports.
- **Consequences:** Every dropped row is recorded as an exclusion; the export carries its own
  blockers.

### D6 — The dataset release tier gates are the executable contract

- **Status:** accepted.
- **Context:** `specs/dataset-spec.md` fixes numeric release gates.
- **Decision:** `dataset/release/release_report.py::{SMOKE,RELEASE_CANDIDATE,BENCHMARK}_RELEASE_PROFILE`
  encode the thresholds; `release_gate_profile` selects one by name; the default is
  `release-candidate`.
- **Consequences:** Only `benchmark-release` requires ≥10,000 rows, ≥10% distinct CAD-model
  coverage, intended-family coverage, parameter balance, preview evidence, and family-test
  evidence.

## Open questions

- **Q1.** **Doc/code mismatch.** `specs/schema.md::DatasetRow` omits `source_path`, `source_hash`,
  `source_metadata`, `split_group`, `prompt_version`, `prompt_template_id`, and `clue_map`,
  all of which the code emits. The code is authoritative.
- **Q2.** **Re-resolution on materialize.** `dataset/cli.py::_cmd_dataset_materialize` reads each
  record's `query` and re-runs `resolve_query`, ignoring the `resolution` already stored in
  the query record. Materialization is therefore not a pure function of the query artifact;
  it recomputes from the graph. Whether that is intended (to pick up graph changes) or an
  oversight is `[unknown]`; the smoke experiment path instead calls `materialize_row`
  directly with the stored resolution.
- **Q3.** **Static-hop heuristic.** The `property_equals` + temporal-relation rule for
  `static_hop_count` is a heuristic; whether it matches the spec's intended static/geometry
  split for every family is `[unknown]`.
- **Q4.** **Boolean `answer_format`.** The schema lists `boolean`, but the materializer rejects the
  `json` format as unsupported (`dataset/release/validate.py::validate_rows`); boolean row
  coverage is not audited here.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- A release-export "capacity report" that, before capping, states the maximum rows each
  family could contribute under the tier's share band, so a small balanced export cannot
  hide coverage limited by the available CadQuery programs.
