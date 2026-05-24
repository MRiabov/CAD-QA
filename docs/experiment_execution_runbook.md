# Experiment Execution Runbook

The active smoke workflow is graph-first:

```bash
rtk uv run cadqa sources inspect --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl
rtk uv run cadqa graph build --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl --limit 10 --out runs/graph_smoke
rtk uv run cadqa query smoke --graph runs/graph_smoke/graphs.jsonl --out runs/query_smoke
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

The SFT command above now exports only geometry-critical rows by default and
excludes syntax-only calibration, noncritical, and quarantined rows. A real
training run still must use rows that pass the broader geometry-first dataset
quality gates: prompt-family and prompt-template balance must pass,
value-bearing and cross-feature coverage must pass, parameterized families must
show healthy sampled distributions, and geometry-derived clauses must be
necessary for the main answers. Use `--include-calibration` only for explicit
calibration exports.

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
