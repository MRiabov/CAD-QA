# Using CADEvolve Dataset Exports

CADEvolve exports provide the primary source programs for CAD-QA.

The graph-first loader expects a JSONL file with at least:

- `source_id`;
- `normalized_code` or `source_code`;
- optional source path and family metadata.

The smoke command path is:

```bash
uv run cadqa sources inspect --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl
uv run cadqa sources manifest --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl --out runs/source_manifest.json
uv run cadqa sources audit --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl --out runs/source_audit.json
uv run cadqa graph build --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl --limit 10 --out runs/graph_smoke
uv run cadqa query smoke --graph runs/graph_smoke/graphs.jsonl --out runs/query_smoke
uv run cadqa dataset materialize --queries runs/query_smoke/queries.jsonl --out data/cadqa_graph_smoke
uv run cadqa dataset validate data/cadqa_graph_smoke
```

Generated rows should be grouped by hop count, relation family, and measurement
scope. Release splits must keep related source variants together.
