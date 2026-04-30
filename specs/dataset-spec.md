# CAD-QA Dataset Specification

The dataset is code-plus-label internally, but release artifacts separate the
public benchmark surface from private verifier artifacts. Public rows contain
normalized CadQuery source code, a rule-rendered prompt, answer format, and
public metadata. Private rows contain gold answers, hidden query programs,
candidate traces, and clue maps.

## Artifacts

- `sources.jsonl`: `SourceRecord` entries.
- `graphs.jsonl`: `OntologyGraph` entries.
- `queries.jsonl`: resolved query records and rendered prompts.
- `rows.jsonl`: internal construction and audit rows containing both public
  model input fields and private verifier fields.
- `public.jsonl`: answer-free public benchmark rows for model input.
- `private.jsonl`: private answer key and verifier artifacts for grading and
  audit.
- `public_private_report.json`: field split, row-count, row-ID parity, and
  hidden-field leak report for public/private views.
- `failure_manifest.jsonl`: rejected or quarantined queries with reasons.
- `dataset_report.json`: counts by hop slice, relation family, measurement
  scope, and verifier status.
- `quarantine_report.json`: counts and examples for rows that resolve
  deterministically but are not release-ready because their evidence is
  conservative or surrogate-backed.
- `release_validation_report.json`: release-mode validation that rejects
  non-release-ready rows.
- release export directories: filtered datasets containing only
  `release_ready=true` rows, with their own validation report, leakage audit,
  quarantine report, and dataset card.
- smoke experiment directories: full `dataset/` artifacts and filtered
  `release_dataset/` artifacts are emitted together so release numbers are
  always auditable against the broader smoke generation surface.
- experiment request and SFT directories: full-smoke and release-filtered
  zero-shot/few-shot requests, answer SFT rows, reasoning SFT rows, ablations,
  and scaling subsets are emitted side by side.
- experiment grade directories: oracle-formatted responses derived from
  `private.jsonl`, public/private graded responses, and prediction metrics for
  key-alignment sanity checks.
- run summaries: `run_summary.json`, `RUN_SUMMARY.md`, and
  `PAPER_RESULTS.md` capture headline counts, validation state, leakage state,
  quarantine reasons, request/SFT counts, paper-table-ready composition, and
  baseline numbers for quick release review.

## Splits

Release splits must be group-safe by source family, generator, and
counterfactual group when such metadata exists. Smoke datasets may use a single
`rows.jsonl` file.

## Quarantine Policy

Smoke rows may include conservative material/void region projections and
selector-surrogate face identities so the graph stack can be exercised end to
end. Release exports must either upgrade those rows to kernel-backed evidence or
exclude them. The release validator treats `release_ready=false` as an error.

## Answer Formats

Supported formats are `entity_id`, `integer`, `number`, `boolean`, `choice`,
`bbox`, and compact JSON objects.
