# Dataset requirements — intended vs verified

**Status:** active, 2026-10-07.

One row per pipeline stage: the requirement that must hold for the downstream benchmark
claim to be valid, the current status, and the command that would move the status to
`verified`. Status tags are defined in `../docs-conventions.md`: `verified` (a check ran
and passed), `exists` (code present, unchecked), `missing`, `stale`,
`[unverified — needs <env>]`, `[unknown]`.

**Verification note.** No stage below was executed while writing these docs. The
development environment has neither CadQuery nor pyarrow/polars installed
(`.venv/bin/python -c "import cadquery"` → `ModuleNotFoundError`), so most commands cannot
run without a fresh `uv sync`. `exists` therefore means "present and readable", not
"proven".

| Stage | Requirement | Status | Verification |
|---|---|---|---|
| A1 Source ingestion | CADEvolve programs are normalized into stable `SourceRecord`s with archive path + normalized-code hash IDs, path-family metadata, and protected/group metadata, and the source manifest/audit surfaces duplicate IDs, hash conflicts, and split-hygiene risks. | exists | `rtk uv run cadqa sources from-cadevolve-cache --cache data/cadevolve_sources.parquet --out runs/cadevolve_sources.parquet --limit 100 --stratify-geometry-tags && rtk uv run cadqa sources inspect --sources-jsonl runs/cadevolve_sources.parquet` |
| A2 Trace/snapshot | Each source executes in a bounded, isolated worker; measurable top-level assignments produce snapshots (volume, bbox, centroid, topology), adjacent assignments produce effect deltas, selector expressions produce selector results, and failures are classified rather than crashing the run. | [unverified — needs cadquery] | `rtk uv run cadqa trace run --sources-jsonl runs/cadevolve_sources.parquet --out runs/trace --timeout-seconds 10 --workers 4` |
| A3 Ontology graph | Each source becomes a typed `OntologyGraph` (nodes, relations, measurements, diagnostics); assignment snapshots/effects/selector results, when supplied, attach kernel-backed geometry and region evidence to the matching features. | exists | `rtk uv run cadqa graph build --sources-jsonl runs/cadevolve_sources.parquet --traces-jsonl runs/trace/traces.parquet --out runs/graph` |
| A4 Query synthesis + resolver | Query programs are generated deterministically from graph evidence; the resolver applies clauses and aggregation in order, rejects non-unique or empty candidate sets unless uniqueness is waived, records the candidate-set trace, and emits a verifier-backed gold answer in the declared answer format. | exists | `rtk uv run cadqa query synthesize --graph runs/graph/graphs.parquet --out runs/query --max-per-family 3` |
| A5 Prompt rendering | The public prompt is rendered by rule from `prompt-templates.yaml`; every public clue maps to a hidden clause or the aggregation step; candidate lists are bounded; banned public terms are absent; wording variants are selected from sampled parameters. | exists | `rtk uv run cadqa dataset preview runs/dataset/rows.parquet --out runs/preview.md --sample-per-family 2 --seed 17` |
| A6 Materialize / validate / release | Resolved queries become `DatasetRow`s with hop counts, relation families, measurement scopes, answer format, evidence tier, release readiness, and quarantine reasons; validation catches schema, uniqueness, clue-traceability, breadth, and public-answer-contract errors; group-safe splits are assigned; release export keeps only release-ready rows and reports blocking gates. | exists | `rtk uv run cadqa dataset materialize --queries runs/query/queries.parquet --out runs/dataset && rtk uv run cadqa dataset validate runs/dataset --release && rtk uv run cadqa dataset release-report runs/dataset --release-tier benchmark-release` |
| A7 Harbor / SFT / evaluation exports | Rows export to Harbor closed-book tasks, geometry-critical SFT JSONL, and evaluation request/grade artifacts; smoke orchestration runs all stages and writes run summaries and a paper-results snapshot. | exists | `rtk uv run cadqa training export-sft --rows runs/dataset/rows.parquet --out runs/sft && rtk uv run cadqa experiment smoke --sources-jsonl runs/cadevolve_sources.parquet --limit 10 --out runs/experiment_smoke` |

## Cross-stage requirements

These are not owned by a single stage but gate the release claim.

| Requirement | Home | Status | Verification |
|---|---|---|---|
| The trusted path contains no LLM: source, graph, query, verifier, and prompt rendering are deterministic. | `specs/generation_policy.md`, `README.md` | exists | inspect `cad_qa/` for model/network calls in the generation path; `rg -n "openrouter\|requests\|httpx\|openai" cad_qa` |
| Public release rows never expose private verifier fields (`gold_answer`, `query_program`, `candidate_trace`, `clue_map`, `verifier_status`). | `cad_qa/dataset/public.py::PUBLIC_FIELDS` | exists | `rtk uv run cadqa dataset export-public-private runs/dataset` and inspect `public_private_report.json` |
| A public benchmark or real fine-tuning claim is made only from the `benchmark-release` tier with `valid_for_release=true` and no blocking gates. | `specs/dataset-spec.md#release-tiers`, `cad_qa/dataset/release_report.py::BENCHMARK_RELEASE_PROFILE` | exists | `rtk uv run cadqa dataset release-report runs/release_dataset --release-tier benchmark-release` |

## Known gaps

- The current curriculum artifact (1,445 rows) does **not** pass the repo's own
  `benchmark-release` gates (scale, split-group coverage, parameter balance); this is
  recorded in `../development-context.md` and is a `[assumed]`-quality gap, not a stage
  failure.
- No 0-hop or 1-hop release families are synthesizable today: `synthesis.py` floors hop
  counts at 2. This blocks a clean 0→1→2→3 curriculum. See
  `pipeline/04-query-synthesis-resolver.md`.

## Extra deliverables - P2

- A single `rtk uv run cadqa experiment audit` command that runs one verification command
  per stage and writes a machine-readable pass/fail ledger into `docs/`.
