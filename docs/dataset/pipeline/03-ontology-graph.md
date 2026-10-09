# 03 — CAD ontology graph

## Purpose

Extract a typed CAD ontology graph — nodes, relations, and measurements — from each
CadQuery program, enriched with kernel-backed evidence from a CadQuery program operation trace
when one is available.

## Inputs / outputs

- **Input:** **sources** artifact; optional **traces** artifact
  (`pipeline/00-overview.md`).
- **Output artifact:** **graphs** (`graphs.parquet`, or sharded under `graphs/`), matching
  the contract; each record is an `OntologyGraph` (`dataset/ontology/nodes.py::OntologyGraph`)
  with `graph_id`, `source` (the serialized `SourceRecord`), `nodes`, `relations`,
  `measurements`, `diagnostics`.
- **Sidecar output:** `graph_report.json` (`dataset/cli.py::_cmd_graph_build`).

## Requirement

The graph must be a faithful, auditable view of the CadQuery program plus whatever the
kernel measured. For the downstream geometry claim: a CadQuery program entity (feature,
CadQuery profile, CadQuery workplane, CadQuery selector, path, topology) must be reachable
as a typed CAD ontology node; geometry evidence must be attached as measurements with a
correct measurement scope; and release-family support must be measurable so sparse coverage
is visible before synthesis. Conservative (CadQuery-program-derived) region projections and
kernel-backed region evidence must be distinguishable.

## Current status

**exists.** Extraction is present and readable
(`dataset/ontology/extract.py::build_graph`, `dataset/ontology/nodes.py`,
`dataset/ontology/relations.py`, `dataset/cli.py::_cmd_graph_build`). AST-based extraction
runs without CadQuery; CadQuery program operation trace enrichment requires it. No graph
build was executed while writing this doc.

## Verification

```bash
rtk uv run cadqa graph build \
  --sources-jsonl runs/cadevolve_sources.parquet \
  --traces-jsonl runs/trace/traces.parquet \
  --out runs/graph
```

Inspect `runs/graph/graph_report.json` for `node_type_counts`, `relation_type_counts`,
`measurement_scope_counts`, `release_support_coverage`, and `missing_release_support`. The
focused tests are `tests/test_graph_first_pipeline.py::test_graph_build_report_exposes_type_coverage`,
`::test_graph_operation_properties_are_json_safe_for_function_arguments`,
`::test_graph_build_integrates_trace_feature_effects`, and
`::test_compiled_snapshot_topology_creates_kernel_face_edge_vertex_entities_without_selector_syntax`.

## Local decisions

### D1 — AST-first extraction, not execution

- **Status:** accepted.
- **Context:** Graph extraction must run on sources that fail to execute and must never run
  untrusted code.
- **Decision:** `dataset/ontology/extract.py::build_graph` parses the CadQuery program with
  `ast` and walks statements; expressions are evaluated only through a restricted evaluator
  (`dataset/ontology/extract.py::_safe_eval`, `::_compile_safe_function`).
- **Consequences:** The graph is a static-structure view even when no CadQuery program operation trace
  exists; execution-derived facts enter only through the optional `TraceRecord`.

### D2 — CadQuery program operation trace enrichment attaches to features by target and line

- **Status:** accepted.
- **Context:** Shape snapshots are keyed by assignment target and CadQuery program line;
  graph features are keyed by assignment target.
- **Decision:** The extractor indexes shape snapshots/effects/CadQuery selector results by
  target, CadQuery program line, and CadQuery selector text and operation, then
  attaches `snapshot_state`, `feature_application_effect`, and CadQuery selector-derived
  measurements to the matching feature
  (`dataset/ontology/extract.py::_attach_trace_snapshot_state`,
  `::_attach_trace_feature_effect`, `::_attach_profile_application_effect`).
- **Consequences:** A feature can carry compiled volume/bbox/centroid/topology and effect
  deltas; kernel entity signatures become face/edge/vertex evidence.

### D3 — Conservative region projections and kernel-backed regions are distinct

- **Status:** accepted.
- **Context:** A CadQuery-program-order projection of a cut/extrude (CadQuery profile area
  × distance) is an AABB guess, while a CadQuery program operation trace delta is
  kernel-backed.
- **Decision:** `dataset/ontology/material_regions.py::feature_effect_from_profile` produces
  conservative `has_material_region_geometry`/`has_void_region_geometry` evidence, while
  kernel-backed paths produce `has_kernel_material_region_geometry`/
  `has_kernel_void_region_geometry` (`dataset/ontology/extract.py::_add_kernel_region_projection`).
- **Consequences:** Materialization quarantines conservative region rows
  (`dataset/release/materialize.py::_evidence_policy`) rather than mislabelling them.

### D4 — Idempotent graph insertion and indexed lookup

- **Status:** accepted.
- **Context:** Compiled topology repeatedly produces identical relations/measurements, and
  topology-rich graphs need fast lookup.
- **Decision:** `OntologyGraph.add_node`/`add_relation`/`add_measurement` deduplicate by
  structural key, and lookups are served by lazily built, mutation-safe indexes
  (`dataset/ontology/nodes.py`).
- **Consequences:** Repeated CadQuery selector observations do not inflate the graph;
  caches are not serialized into graph artifacts.

### D5 — Graph artifacts can be sharded

- **Status:** accepted.
- **Context:** Large graph builds do not fit comfortably in one in-memory file.
- **Decision:** `dataset/cli.py::_write_graph_shards` writes `graphs/part-NNNNN.parquet`
  when `--shard-size` is set; `_load_graphs` reads either form.
- **Consequences:** Downstream stages accept a single artifact or a shard directory.

## Open questions

- **Q1.** `dataset/ontology/relations.py::RELATION_FAMILIES` and `MEASUREMENT_SCOPES` are the
  registry of allowed relation type and measurement scope values, but
  `assert_relation_type`/`assert_measurement_scope` are available and not obviously
  enforced on every insertion. Whether every emitted relation type and measurement scope is
  a member, and whether the registry is intended as a hard gate, is `[unknown]`.
- **Q2.** `release_support_coverage` in `graph_report.json` uses
  `dataset/cli.py::RELEASE_SUPPORT_REQUIREMENTS`; this is an early-warning signal, not a
  blocking gate. Whether synthesis reuses it to skip unsupported families is `[unknown]`.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- A per-graph provenance table mapping each measurement back to the exact shape snapshot /
  effect / CadQuery selector index that produced it, for a fully reproducible audit.
