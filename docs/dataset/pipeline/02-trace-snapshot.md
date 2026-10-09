# 02 — CadQuery program operation trace / Shape snapshot

## Purpose

Execute a normalized CadQuery program in a bounded, isolated worker and record kernel-backed
measurements — Shape snapshots, effect deltas, and CadQuery selector results — that later
become geometry evidence in the CAD ontology graph.

## Inputs / outputs

- **Input:** **sources** artifact (`pipeline/00-overview.md`).
- **Output artifact:** **traces** (`traces.parquet` preferred), matching the contract; each
  record is a `TraceRecord` (`dataset/trace.py::TraceRecord`) with `source_id`,
  `execution_status`, `snapshots`, `operation_effects`, `selector_results`, `environment`,
  `failure_reason`.
- **Sidecar output:** `trace_report.json` (`dataset/trace.py::trace_report`).

## Requirement

Execution must be safe and bounded: a CadQuery program cannot hang or crash the run, and
every non-result must be classified. For the geometry claim, a CadQuery program operation trace
must produce a usable Shape snapshot set (possibly partial) or a classified failure. Shape
snapshots must carry
volume, bounding box, centroid, and topology counts; adjacent measurable assignments must
produce signed effect deltas; CadQuery selector subexpressions must produce selected
counts, a label for each selected shape, and bbox signatures. A CadQuery program that
times out after producing measurable solids must
be preserved as `execution_status=partial` rather than discarded.

## Current status

**[unverified — needs cadquery].** The code is present and readable
(`dataset/trace.py::trace_sources_bounded`, `::trace_source`, `::measure_shape`,
`::_execute_source_trace`, CLI `dataset/cli.py::_cmd_trace_run`), but execution requires the
CadQuery kernel, which is **not installed** in the current environment (import fails). No
CadQuery program operation trace was produced while writing this doc.

## Verification

```bash
rtk uv run cadqa trace run \
  --sources-jsonl runs/cadevolve_sources.parquet \
  --out runs/trace \
  --timeout-seconds 10 \
  --workers 4
```

Because the environment lacks CadQuery, the first command is:

```bash
rtk uv sync --extra cadquery
```

The focused tests are `tests/test_graph_first_pipeline.py::test_trace_worker_executes_cadquery_source_or_reports_unavailable`,
`::test_trace_sources_bounded_preserves_order_and_reports_timeouts`,
`::test_partial_timeout_trace_contributes_snapshot_topology_to_graph`, and
`::test_trace_measures_selector_subexpression_not_final_chained_solid`.

## Local decisions

### D1 — Isolate each CadQuery program in a worker process with a timeout

- **Status:** accepted.
- **Context:** A CAD program can hang, recurse, or crash the interpreter; an in-process
  CadQuery program operation trace would take the whole run down.
- **Decision:** `dataset/trace.py::trace_source` runs isolated by default
  (`_trace_source_isolated`), and `trace_sources_bounded` manages a pool of worker processes
  with a per-CadQuery-program `timeout_seconds`, terminating and killing over-time workers
  (`dataset/trace.py::_stop_process`).
- **Consequences:** Slow or hostile CadQuery programs become `failed`/`partial` records;
  results keep input order.

### D2 — A timeout after measurable solids is `partial`, not `failed`

- **Status:** accepted.
- **Context:** Some upstream CadQuery programs build several solids before hitting an expensive tail
  operation.
- **Decision:** Workers publish bounded progress (`partial` results) while executing; a
  timed-out worker whose latest result has snapshots becomes `execution_status=partial`
  with `failure_reason=timeout` (`dataset/trace.py::_record_from_timed_out_worker`,
  `::_trace_record_from_worker_result`).
- **Consequences:** Partial geometry is usable downstream; `trace_report` separates
  `partial_count` and `usable_count`.

### D3 — Measure per top-level assignment, not just the final result

- **Status:** accepted.
- **Context:** Feature effects and provenance need the difference between successive
  assignments, not only the final solid.
- **Decision:** `dataset/trace.py::_execute_source_trace` compiles and executes each
  statement, snapshots each measurable assigned value, and emits `operation_effects` when a
  Shape snapshot's base target had a prior Shape snapshot (`::_snapshot_delta_effect`).
- **Consequences:** Graph extraction can attach Shape snapshot state and feature-application-effect
  measurements per feature.

### D4 — Bound topology entity signatures

- **Status:** accepted.
- **Context:** A complex solid can have many faces/edges/vertices; serializing all of them
  would bloat traces.
- **Decision:** `MAX_SNAPSHOT_TOPOLOGY_ENTITIES_PER_KIND = 128`
  (`dataset/trace.py`) bounds signatures to 128 entities per topology entity category.
- **Consequences:** Entity signatures are a sample, not a complete enumeration; graph
  evidence derived from them is bounded accordingly.

### D5 — Partial unrolling for simple `for` loops

- **Status:** accepted.
- **Context:** The upstream corpus uses loops to place repeated features.
- **Decision:** Loops without `break`/`continue` over literal iterables are unrolled
  statement-by-statement (`dataset/trace.py::_can_trace_unroll_for`,
  `::execute_statement`); unsupported loops fall back to a plain capture.
- **Consequences:** Repeated features get distinct snapshots; unbounded or data-dependent
  loops are not unrolled.

## Open questions

- **Q1.** **Untyped CadQuery program operation trace internals.**
  `dataset/trace.py::TraceRecord` stores `snapshots`, `operation_effects`, and
  `selector_results` as `list[dict[str, Any]]`, so what the record holds is only
  discoverable from the producer code. Typed records would document the contract the record
  is meant to express.
- **Q2.** **Doc/code mismatch.** `specs/schema.md::TraceRecord` lists only `source_id`,
  `execution_status`, `snapshots`, `operation_effects`, `environment`, `failure_reason`,
  while `dataset/trace.py::TraceRecord` also carries `selector_results`. The code is
  authoritative; the spec is stale.
- **Q3.** **Skipped loop bodies.** The extractor (`extract.py`) and the tracer use different
  unrolling rules (extractor caps iterations at 64, tracer unrolls any non-break loop).
  Cross-pipeline-stage consistency for complex loops is `[unknown]`.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- Optional per-CadQuery-program wall-clock and memory accounting persisted into
  `trace_report.json` for capacity planning on large release builds.
