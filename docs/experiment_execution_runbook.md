# Experiment Execution Runbook

The active smoke workflow is graph-first:

```bash
rtk uv run cadqa sources from-cadevolve-tar --tar data/cadevolve.tar --out runs/cadevolve_sources.jsonl --path-prefix CADEvolve-P/ShapeNet-P --limit 100 --stratify-geometry-tags
rtk uv run cadqa sources inspect --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl
rtk uv run cadqa graph build --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl --limit 10 --out runs/graph_smoke
rtk uv run cadqa query smoke --graph runs/graph_smoke/graphs.jsonl --out runs/query_smoke
rtk uv run cadqa query synthesize --graph runs/graph_smoke/graphs.jsonl --out runs/query_synth --max-per-family 3
rtk uv run cadqa dataset materialize --queries runs/query_smoke/queries.jsonl --out data/cadqa_graph_smoke
rtk uv run cadqa dataset validate data/cadqa_graph_smoke
rtk uv run cadqa dataset audit data/cadqa_graph_smoke
rtk uv run cadqa dataset quarantine data/cadqa_graph_smoke
rtk uv run cadqa dataset card data/cadqa_graph_smoke
rtk uv run cadqa dataset validate data/cadqa_graph_smoke --release
rtk uv run cadqa dataset export-release data/cadqa_graph_smoke --out data/cadqa_graph_release_smoke
rtk uv run cadqa dataset preview data/cadqa_graph_smoke --graphs runs/graph_smoke --out runs/feature_preview.md --sample-per-family 1 --seed 17
rtk uv run cadqa evaluation baseline --rows data/cadqa_graph_smoke/rows.jsonl --out runs/baseline_smoke
rtk uv run cadqa training export-sft --rows data/cadqa_graph_smoke/rows.jsonl --out runs/sft_smoke
```

The first command is optional when a prepared `sources.jsonl` already exists.
Use it when starting from the local CADEvolve archive; it writes normalized
source JSONL plus manifest/report sidecars before the usual graph build.
Keep `--stratify-geometry-tags` on limited source exports so rare path,
selector, and void-bearing sources are not silently skipped by archive order.
Use `--complete-stratified-scan` only when the sidecar report needs full
archive-wide tag counts.

Use `cadqa query smoke` for small plumbing checks that still include calibration
and review rows. Use `cadqa query synthesize` for release-oriented graph-hop
generation: it emits only manifest release families by default, can emit
multiple deterministic viable variants per family, and is the path to use when
checking sampled-parameter coverage. Review `graph_report.json` for
`missing_release_support` before synthesizing a full dataset; zero support there
means the corresponding release families cannot be recovered by regeneration
without changing the selected sources.

The SFT command above now exports only geometry-critical rows by default and
excludes syntax-only calibration, noncritical, and quarantined rows. A real
training run still must use rows that pass the broader geometry-first dataset
quality gates: prompt-family and prompt-template balance must pass,
value-bearing and cross-feature coverage must pass, parameterized families must
show healthy sampled distributions, and geometry-derived clauses must be
necessary for the main answers. Use `--include-calibration` only for explicit
calibration exports.

For benchmark-release training or benchmark claims, the artifact must satisfy the
numeric benchmark-release tier in `specs/dataset-spec.md`, not only the current
smoke/release-candidate gates. Treat the benchmark-release report as the
canonical verdict: the artifact is benchmark-release ready only when
`valid_for_release=true`, every stop gate passes, and the matching default SFT
report also passes the benchmark-release tier. In particular, expect at least
10,000 release rows, at least 10,000 default SFT rows, 95%+
geometry-hop-positive rows, 99%+ geometry-critical default SFT rows, 0%
syntax-only default SFT rows, 15%-30% value-bearing rows, 5%-15% cross-feature
value-bearing rows, at least 10 generated release families with each family in
the 1%-10% band, at least 20 prompt templates with no template above 5%,
healthy parameter coverage, manual preview/test evidence, and non-collapsed
train/validation/test protected splits.

Pass `--release-tier benchmark-release` to `cadqa dataset release-report`,
`cadqa dataset export-release`, and `cadqa training export-sft` when validating a
benchmark-release candidate. The default tier remains `release-candidate` for
development runs.

Run `cadqa dataset preview` whenever a task family, graph node type, or
measurement extractor changes. Filter it with repeated `--family` and
`--node-type` flags to produce a small review artifact for the exact feature
under inspection. The preview includes prompts, query programs, candidate
traces, gold answers, and optional graph node/measurement samples.

To grade release-style model responses, provide JSONL records with `row_id` and
`answer`. Use the public rows as the model input and the private rows as the
answer key. Responses may also include numeric `confidence`; when present,
grading reports calibration metrics. The grader also reports response coverage,
missing responses, invalid outputs, duplicate response IDs, and extra response
IDs that do not match public rows.

```bash
rtk uv run cadqa evaluation grade-private \
  --public data/cadqa_graph_release_smoke/public.jsonl \
  --private data/cadqa_graph_release_smoke/private.jsonl \
  --responses runs/model_responses.jsonl \
  --out runs/model_eval
```

To sanity-check a public/private release key, export oracle-formatted responses
from `private.jsonl` and grade them through the same public/private path:

```bash
rtk uv run cadqa evaluation export-oracle-responses \
  --private data/cadqa_graph_release_smoke/private.jsonl \
  --out runs/model_eval/oracle_responses.jsonl

rtk uv run cadqa evaluation grade-private \
  --public data/cadqa_graph_release_smoke/public.jsonl \
  --private data/cadqa_graph_release_smoke/private.jsonl \
  --responses runs/model_eval/oracle_responses.jsonl \
  --out runs/model_eval/oracle_key_check
```

To export model requests:

```bash
rtk uv run cadqa evaluation export-requests \
  --rows data/cadqa_graph_smoke/rows.jsonl \
  --out runs/request_smoke/zero_shot_requests.jsonl \
  --mode zero-shot
```

The same workflow can be run as one smoke experiment:

```bash
rtk uv run cadqa experiment smoke \
  --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl \
  --limit 10 \
  --out runs/experiment_smoke
```

The smoke experiment writes full `dataset/` and filtered `release_dataset/`
trees, public/private row views, dataset cards, query failure report,
quarantine reports, smoke and release validation reports, leakage audits,
full-smoke and release-subset baseline outputs, full-smoke and release-subset
public/private oracle-grade sanity checks, full-smoke and release-subset
request exports, full-smoke and release-subset SFT artifacts,
`dataset/GENERATED_PREVIEW.md`, `run_summary.json`, `RUN_SUMMARY.md`, and an
artifact manifest. Package the run for sharing with:

```bash
rtk uv run cadqa experiment package \
  --run runs/experiment_smoke \
  --out runs/experiment_smoke.tar.gz

rtk uv run cadqa experiment paper-results \
  --run runs/experiment_smoke
```

GPU training and provider submission are planned follow-up layers. Rebuild them
against the graph-first `DatasetRow` schema rather than restoring the removed
legacy scripts.
