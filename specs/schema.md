# CAD-QA Schema

The schema is intentionally small and graph-first. Internal `DatasetRow`
records contain both public model-input fields and private verifier fields;
release exports split them into `public.jsonl` and `private.jsonl`.

## SourceRecord

- `source_id`: stable ID.
- `source_code`: normalized CadQuery code.
- `source_path`: optional original path.
- `source_hash`: normalized source hash.
- `metadata`: source-family and provenance metadata.

## TraceRecord

- `source_id`;
- `execution_status`;
- `snapshots`;
- `operation_effects`;
- `environment`;
- `failure_reason`.

Trace records are optional for low-hop static rows but required for
release-grade geometry, topology, selector, material, and validity rows.

## OntologyGraph

- `graph_id`;
- `source`;
- `nodes`;
- `relations`;
- `measurements`;
- `diagnostics`.

Nodes have `id`, `type`, `label`, `source_ref`, and `properties`.
Relations have `source_id`, `target_id`, `type`, `properties`, and
`evidence`.
Measurements have `entity_id`, `scope`, `name`, `value`, `unit`, and
`evidence`.

## QueryProgram

- `query_id`;
- `target_type`;
- `answer_type`;
- `clauses`;
- `aggregation`;
- `aggregation_metric`;
- `tie_break_aggregation`;
- `tie_break_metric`;
- `hop_count`;
- `difficulty`;
- `reject_unless_unique`.
- `sampled_parameters`: private normalized metadata used for release balance
  gates, including target type, final selector, aggregation metric/axis,
  extremum direction, tie-break metric/axis/direction, clause metrics/axes,
  comparison operators, reference metrics, and value buckets where applicable.

## DatasetRow

- `row_id`;
- `source_id`;
- `source_code`;
- `prompt`;
- `answer_format`;
- `gold_answer`;
- `query_program`;
- `candidate_trace`;
- `relation_families`;
- `measurement_scopes`;
- `logical_hop_count`;
- `static_hop_count`;
- `geometry_hop_count`;
- `difficulty_bucket`;
- `verifier_status`;
- `evidence_tier`;
- `release_ready`;
- `quarantine_reasons`.

`release_ready=false` rows may be useful for smoke experiments, diagnostics, or
training ablations, but they must not be exported as final benchmark labels.
Current quarantine reasons include conservative material/void region
projections and selector-derived face identities when they are not backed by
kernel trace evidence. Kernel-backed material/void deltas and directly traced
selector results may be release-ready when the verifier resolves them uniquely.
