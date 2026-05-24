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
- `failure_manifest.jsonl`: query-generation failures with resolver or
  candidate-trace reasons. Quarantined resolved rows are reported separately.
- `dataset_report.json`: counts by hop slice, relation family, measurement
  scope, and verifier status.
- `quarantine_report.json`: counts and examples for rows that resolve
  deterministically but are not release-ready because their evidence is
  conservative or surrogate-backed.
- `release_validation_report.json`: release-mode validation that rejects
  non-release-ready rows.
- `release_exclusions.json`: rows filtered out by release export, including
  release-validation failures, prompt-policy exclusions, duplicate prompts, and
  syntax-only calibration rows beyond the cap.
- `release_verifier_report.json` and `RELEASE_VERIFIER_REPORT.md`: aggregate
  stop-gate report for release exports, including validation, leakage,
  public/private parity when available, shortcut resistance, training
  readiness, prompt balance, answer entropy, value-bearing coverage, and
  geometry-hop coverage.
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

## Dataset Quality Gates

Schema-valid and release-ready are not sufficient for fine-tuning readiness.
Main benchmark and training exports must additionally pass geometry-first
quality gates:

- syntax-only calibration rows are excluded or capped;
- prompt-family quotas require every generated release task family to account
  for at least 1% and at most 10% of the exported rows;
- rows report nonzero geometry-derived evidence for main benchmark slices;
- value-bearing measurement rows and cross-feature value-bearing rows are
  represented above the configured release thresholds;
- parameterized families report coverage over sampled dimensions such as axis,
  sign, min/max direction, comparison relation, value bucket, aggregation
  metric, target type, and reference type;
- static shortcut baselines are reported separately from geometry reasoning
  baselines;
- release reports include template distribution, static-hop/geometry-hop
  distribution, and answer-entropy checks.

Some gates are already enforced by the release and SFT exporters. A dataset is
still not recommended for model training unless every active gate passes and
manual preview review confirms that the sampled prompts are not collapsed onto
hard-coded generator choices.

The 1%-10% prompt-family gate applies to task families present in the generated
export. Intended task families that produce zero rows need an explicit
intended-family manifest; without that manifest, absence must be caught during
manual release review and treated as unfinished coverage.

## Benchmark-Release Numeric Gates

The benchmark-release tier is the target standard for public benchmark claims and
real fine-tuning dataset creation. Smoke and release-candidate runs may use lower
thresholds for development, but they must be labeled as such and must not be
described as benchmark-release ready.

| Gate | Benchmark-release requirement |
| --- | --- |
| Release rows | At least 10,000 public/private release rows. |
| Default SFT rows | At least 10,000 rows after default geometry-critical filtering. |
| Generated task-family share | Every generated release family is between 1% and 10% of exported rows. |
| Zero-row intended families | 0 intended release families with zero rows, unless explicitly marked `review_only` or `calibration`. |
| Default SFT geometry-critical share | At least 99%. |
| Default SFT syntax-only calibration share | 0%. |
| Benchmark syntax-only calibration share | At most 2%, or emitted only in a separate calibration split/artifact. |
| Geometry-hop-positive share | At least 95% of benchmark-release rows have `geometry_hop_count > 0`. |
| Main BrowseComp hop share | At least 90% of benchmark-release rows have `logical_hop_count >= 3`. |
| Value-bearing measurement share | 15%-30% of benchmark-release rows. |
| Cross-feature value-bearing share | 5%-15% of benchmark-release rows. |
| Candidate breadth | Minimum 2 candidates before the final selector for high-hop rows; median pre-final breadth at least 4. |
| Prompt-template max share | No prompt template exceeds 5% of benchmark-release rows. |
| Unique answer count | At least 1,000 unique gold answers. |
| Answer entropy | At least 8 bits. |
| Parameter value max share | Within each parameterized family, no sampled parameter value exceeds 35%, unless marked geometry-limited. |
| Axis/direction coverage | Every supported sampled axis/direction value contributes at least 20% where applicable, unless marked geometry-limited. |
| Split quality | Multi-split benchmark releases must have train/validation/test splits, at least 3 protected groups per split, and no train-only collapse. |
| Manual preview | At least 20 sampled rows per changed release family, or all rows if fewer than 20 exist. |
| New-family tests | Each new release family has positive generation coverage, failure/quarantine coverage, and release-report accounting coverage. |

Current implementation gates now support an explicit `benchmark-release` tier for
the row-count, hop-coverage, geometry-critical, syntax-only, value-bearing,
cross-feature, prompt-template, answer-diversity, candidate-breadth, and split
coverage targets above. Benchmark-release release/SFT reports also enforce the
intended-family manifest: generated review-only/calibration/unknown families and
zero-row intended release families block the tier. They also serialize private
`query_program.sampled_parameters` and enforce an initial parameter-balance gate
over that metadata: target type, final selector, aggregation metric/axis,
extremum direction, clause metrics/axes, comparison operators, reference
metrics, and value buckets. Full synthesis-layer parameter bindings for
predicate sequence, reference anchor, rank, tie-break metric, and rendered
wording, plus machine-checked preview/test evidence gates, remain open
implementation work.

## Splits

Release splits must be group-safe by source family, generator, and
counterfactual group when such metadata exists. Smoke datasets may use a single
`rows.jsonl` file.

If available source metadata collapses all rows into one protected split group,
the artifact may still be useful as a fine-tuning-format export, but it is not a
multi-split benchmark release. This limitation must be reported explicitly.

## Quarantine Policy

Smoke rows may include conservative material/void region projections and
selector-surrogate face identities so the graph stack can be exercised end to
end. Release exports must either upgrade those rows to kernel-backed evidence or
exclude them. The release validator treats `release_ready=false` as an error.

## Answer Formats

Supported formats are `entity_id`, `integer`, `number`, `boolean`, `choice`,
`bbox`, and compact JSON objects.
