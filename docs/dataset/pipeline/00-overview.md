# Dataset pipeline — overview

**Status:** active, 2026-10-07. This is the DAG and the stage IO contract for the
benchmark-generation pipeline. It is the single source for artifact and field names
between steps; the step docs restate behaviour but must match this contract.

Audience note: terms follow `docs/glossary.md`. Read that first if a term is unclear.

## What this pipeline builds

The pipeline turns normalized CadQuery source programs into verifiable QA rows. It is
the `dataset_generation` package (today `cad_qa/`), which is **frozen**: the docs describe
what it does, not what it should do (`plans/oct-7/restructure-docs.md`). Low-hop rows and
high-hop CAD BrowseComp rows are slices of the same machinery; there is no separate
simple-QA pipeline (`README.md`).

## DAG order

```text
A1 Source ingestion
      sources artifact
        |
        v
A2 CAD query trace (optional for low-hop rows; required for release-grade geometry)
      traces artifact
        |
        v
A3 Ontology graph  <---- (A2 traces, when present)
      graphs artifact
        |
        v
A4 Query synthesis + resolver
      queries artifact + failure_manifest artifact
        |
        v
A5 Prompt rendering  (a function invoked inside A6, not a standalone artifact)
      rendered prompt embedded in each row
        |
        v
A6 Materialize / validate / release
      rows artifact, public/private artifacts, release dataset
        |
        v
A7 Exports: Harbor, SFT, evaluation
```

A1–A4 have dedicated CLI stages; A5 is invoked by the materializer; A6 and A7 have their
own CLI stages. The one-command `cadqa experiment smoke` runs A3–A7 end to end for a small
slice (`cad_qa/experiment.py::run_smoke_experiment`).

## Stage IO contract

Each stage names its producer, its input artifact, and its output artifact. Artifact
formats default to Parquet with a JSONL fallback (`cad_qa/io.py::read_records`,
`cad_qa/io.py::write_records`, `cad_qa/io.py::record_artifact_path`).

| Stage | Producer | Input | Output artifact | Key fields |
|---|---|---|---|---|
| A1 Source ingestion | `cad_qa/source.py` | CADEvolve tar, extracted directory, cached source Parquet, or generic JSONL | **sources** (`sources.parquet`) | `source_id`, `source_code`, `source_path`, `source_hash`, `metadata` (`SourceRecord`) |
| A2 Trace/snapshot | `cad_qa/trace.py` | sources | **traces** (`traces.parquet`) | `source_id`, `execution_status`, `snapshots`, `operation_effects`, `selector_results`, `environment`, `failure_reason` (`TraceRecord`) |
| A3 Ontology graph | `cad_qa/ontology/extract.py::build_graph` | sources; optional traces | **graphs** (`graphs.parquet`) | `graph_id`, `source`, `nodes`, `relations`, `measurements`, `diagnostics` (`OntologyGraph`) |
| A4 Query synthesis + resolver | `cad_qa/query/synthesis.py::synthesize_graph_hop_queries`, `cad_qa/query/resolver.py::{smoke_queries, resolve_query}` | graphs | **queries** (`queries.parquet`) + **failure_manifest** (`failure_manifest.parquet`) | per record: `graph_id`, `query` (`QueryProgram`), `resolution` (`QueryResolution`) |
| A5 Prompt rendering | `cad_qa/prompts/render.py::render_prompt` | source code + `QueryProgram` (+ graph) | rendered prompt embedded in the row | `prompt`, `prompt_version`, `prompt_template_id`, `clue_map`, `warnings` |
| A6 Materialize/validate/release | `cad_qa/dataset/` | queries (+ graphs sidecar) | **rows** (`rows.parquet`), **public**/**private**, dataset + release reports | `DatasetRow` fields (below) |
| A7 Exports | `cad_qa/harbor.py`, `cad_qa/dataset/sft.py`, `cad_qa/evaluation/`, `cad_qa/experiment.py` | rows, public/private, responses | Harbor task dirs, SFT JSONL, evaluation reports, smoke experiment tree | see step doc 07 |

### Nested field names

**`OntologyGraph`** (`cad_qa/ontology/nodes.py`):
`Node{id, type, label, source_ref, properties}`,
`Relation{source_id, target_id, type, properties, evidence}`,
`Measurement{entity_id, scope, name, value, unit, evidence}`.

**`QueryProgram`** (`cad_qa/query/ir.py`): `query_id`, `target_type`, `answer_type`,
`answer_spec` (`AnswerSpec`), `clauses` (`Clause`), `aggregation`, `aggregation_metric`,
`aggregation_rank`, `tie_break_aggregation`, `tie_break_metric`, `hop_count`,
`difficulty`, `reject_unless_unique`, `min_individual_clause_candidates`,
`sampled_parameters`.

**`Clause`** (`cad_qa/query/ir.py`): `id`, `kind`, `relation`, `target_type`, `metric`,
`reference_metric`, `operator`, `value`, `text`.

**`QueryResolution`** (`cad_qa/query/ir.py`): `query_program`, `gold_answer`,
`candidate_trace` (`CandidateSetTrace`), `relation_families`, `measurement_scopes`,
`verifier_status`.

**`CandidateSetTrace`** (`cad_qa/query/ir.py`): `query_id`, `steps`, `final_candidates`,
`status`, `failure_reason`.

**`DatasetRow`** (`cad_qa/dataset/materialize.py`): `row_id`, `source_id`, `source_path`,
`source_hash`, `source_metadata`, `split_group`, `source_code`, `prompt`, `answer_format`,
`gold_answer`, `query_program`, `candidate_trace`, `relation_families`,
`measurement_scopes`, `logical_hop_count`, `static_hop_count`, `geometry_hop_count`,
`difficulty_bucket`, `verifier_status`, `prompt_version`, `prompt_template_id`,
`clue_map`, `evidence_tier`, `release_ready`, `quarantine_reasons`. The CLI adds `split`
(`cad_qa/cli.py::_cmd_dataset_materialize`).

**Public / private column sets** (`cad_qa/dataset/public.py`):
`PUBLIC_FIELDS` and `PRIVATE_FIELDS` are the release boundary. `public` is answer-free
model input; `private` carries `gold_answer`, `query_program`, `candidate_trace`,
`clue_map`, `verifier_status`.

## Stage-to-CLI map

| Stage | CLI |
|---|---|
| A1 | `cadqa sources inspect` / `manifest` / `audit` / `from-cadevolve-tar` / `cache-cadevolve-tar` / `cache-cadevolve-dir` / `from-cadevolve-cache` |
| A2 | `cadqa trace run` |
| A3 | `cadqa graph build` |
| A4 | `cadqa query smoke`, `cadqa query synthesize` |
| A6 | `cadqa dataset materialize` / `validate` / `audit` / `quarantine` / `card` / `export-public-private` / `export-release` / `release-report` / `shortcut-report` / `preview` / `synthesis-selfcheck` |
| A7 | `cadqa training export-sft`, `cadqa harbor materialize` / `materialize-dataset` / `export-sft` / `export-atif`, `cadqa evaluation …`, `cadqa experiment smoke` / `package` / `paper-results` |

## Step docs

- `01-source-ingestion.md` — A1
- `02-trace-snapshot.md` — A2
- `03-ontology-graph.md` — A3
- `04-query-synthesis-resolver.md` — A4
- `05-prompt-rendering.md` — A5
- `06-materialize-validate-release.md` — A6
- `07-exports-harbor-sft.md` — A7

## Open questions

- **Doc/code schema drift.** `specs/schema.md::TraceRecord` omits `selector_results`,
  while `cad_qa/trace.py::TraceRecord` carries it. `specs/schema.md::DatasetRow` omits
  `source_path`, `source_hash`, `source_metadata`, `split_group`, `prompt_version`,
  `prompt_template_id`, and `clue_map`. The code is authoritative here; `specs/` is being
  superseded (`plans/oct-7/restructure-docs.md`).
- Whether a terse, runnable WHAT layer per pipeline is needed in addition to these step
  docs is open (D14 in the restructure plan).

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- A machine-checked IO-contract test that fails when a stage's serialized field set
  diverges from this table.
