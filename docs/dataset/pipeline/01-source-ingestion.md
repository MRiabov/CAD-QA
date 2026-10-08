# 01 — CadQuery program ingestion

## Purpose

Turn the raw upstream CadQuery program corpus (or a generic JSONL) into normalized,
stable `SourceRecord`s that every later stage consumes.

## Inputs / outputs

- **Input:** an upstream CadQuery program corpus tar archive, an extracted corpus
  directory, a cached CadQuery program Parquet table, or a generic JSONL of
  CadQuery-program-like rows.
- **Output artifact:** **sources** (`sources.parquet` preferred, `sources.jsonl`
  accepted), matching `pipeline/00-overview.md`; each record is a `SourceRecord`
  (`cad_qa/source.py::SourceRecord`) with `source_id`, `source_code`, `source_path`,
  `source_hash`, `metadata`.
- **Sidecar outputs:** CadQuery program manifest (`sources.manifest.json`) and
  audit (`sources.audit.json`) when the corresponding CLI commands are used.

## Requirement

CadQuery program identity must be stable and reproducible, and split-hygiene metadata must survive
ingestion. Concretely: `source_id` is derived from archive path plus a normalized-code hash,
`source_hash` is a SHA-256 of the normalized code, and protected split-group metadata
(`split_group`, `counterfactual_group`, `source_family`, `family_id`, `template_id`) plus a
path-derived `path_family` are carried so later leakage audits and group-safe splits are
possible. The audit must surface duplicate IDs, CadQuery program ID/hash conflicts, duplicate
normalized code, missing paths, and ungrouped sources rather than hiding them.

## Current status

**exists.** The ingestion code, upstream corpus tar/directory/cache paths, manifest, and audit
are present and readable (`cad_qa/source.py`,
`cad_qa/cli.py::_cmd_sources_from_cadevolve_cache`,
`cad_qa/cli.py::_cmd_sources_manifest`, `cad_qa/cli.py::_cmd_sources_audit`). No ingestion
command was executed while writing this doc.

## Verification

```bash
rtk uv run cadqa sources cache-cadevolve-dir \
  --root data/cadevolve_extracted \
  --out data/cadevolve_sources.parquet
rtk uv run cadqa sources from-cadevolve-cache \
  --cache data/cadevolve_sources.parquet \
  --out runs/cadevolve_sources.parquet \
  --limit 100 --stratify-geometry-tags
rtk uv run cadqa sources inspect --sources-jsonl runs/cadevolve_sources.parquet
rtk uv run cadqa sources audit --sources-jsonl runs/cadevolve_sources.parquet --out runs/sources_audit.json
```

The focused tests are `tests/test_graph_first_pipeline.py::test_source_loading`,
`::test_cadevolve_tar_import_writes_source_jsonl`, and `::test_cadevolve_source_manifest_and_audit_cli`.

## Local decisions

### D1 — Normalize CadQuery program text before hashing

- **Status:** accepted.
- **Context:** Corpus files can differ in line endings and trailing whitespace, which
  would produce unstable IDs across reimports.
- **Decision:** `cad_qa/source.py::normalize_source_text` normalizes line endings and strips
  trailing whitespace, then appends a single trailing newline; the hash is taken over that
  normalized text (`cad_qa/source.py::source_record_from_mapping`).
- **Consequences:** Same logical program → same `source_hash` and `source_id`.

### D2 — Keep generic JSONL ingestion, not just the upstream corpus

- **Status:** accepted.
- **Context:** CadQuery programs may also come from synthetic fixtures and other corpora.
- **Decision:** `cad_qa/source.py::source_record_from_mapping` accepts
  `normalized_code`/`source_code`/`raw_code` and derives a CadQuery program ID when one is
  absent; the corpus-specific paths are separate functions.
- **Consequences:** The same downstream stages consume either origin.

### D3 — Geometry-tag stratification preserves rare families

- **Status:** accepted.
- **Context:** A limited export taken in archive order can silently skip rare path,
  CadQuery selector, and void-bearing CadQuery programs (`README.md`).
- **Decision:** `--stratify-geometry-tags` with `--min-per-geometry-tag` selects examples
  of `GEOMETRY_SOURCE_FEATURE_TAGS` before archive-order fill
  (`cad_qa/source.py::_select_stratified_source_rows`).
- **Consequences:** Rare geometry-bearing sources survive limited slices; counts are
  reported in `selected_geometry_feature_tag_counts`.

## Open questions

- Whether `_looks_like_cadquery_source` (requires `cadquery` or `cq.` in the text) drops
  valid CadQuery-free-but-CAD programs is `[unknown]`; the corpus is a set of upstream
  CadQuery programs, where the heuristic is intended to hold.
- The `metadata` bag is free-form (`dict[str, Any]`); there is no schema lock on which
  provenance keys are guaranteed. Downstream code treats protected keys as optional and
  falls back to `path_family`.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- A content-addressed CadQuery program store keyed by `source_hash` so re-ingestion is a
  no-op and provenance is queryable without rescanning archives.
