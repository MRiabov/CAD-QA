# Test fixtures

Programs the tests run over. There are three sets, kept apart: a pipeline
fixture pool, coverage fixtures, and rejection fixtures.

## Pipeline fixture pool

**Status:** `missing` — `pipeline-pool.json` lands with the `P0-W2` test.

The end-to-end and stage tests read a committed copy of a few CADEvolve rows, not
the downloaded cache. `pipeline-pool.json` carries, per row, the `01a` metadata
fields, the program text `01c` would fetch, and the typed packet that replaces
the fetch. The test writes a three-row `cadevolve_sources.parquet` from the file
into a temporary directory and passes it as `--external-dataset`, so the
production Parquet reader is real and the 507 MB cache is not required.

The rows are copied from the pinned cache once, not invented: `source_id`,
`source_collection`, `path_family`, `source_feature_tags`, `generator_id`, and
`normalized_source_code_hash` keep the cache's values, and the program text is
the cache's normalized code. The file names the rows, so the pool is
deterministic. The fixture records the small-run `SelectionPolicy`
(`active_count`, `collection_minimum`, `usable_floor`) because the release
defaults cannot select three programs.

The fixture carries its own `cache_revision` and `cache_schema_version`, and the
test's manifest declares them, so `01a`'s revision check is exercised against a
real file rather than bypassed.

The pool is input for the end-to-end and stage seams. It is not a golden record
and not the coverage fixture set below.

## Coverage fixtures

Programs that define what the support table means by "supported". See
[`../00-support-tables.md`](../00-support-tables.md) for the test contract.

A fixture is one CadQuery program and its `program_sha256`. It is chosen from the
pinned pool for a capability it exercises, and it is representative rather than
degenerate.

Each fixture covers at least one of:

- several solid states, for provenance and effect answers;
- a pair measurement, for `distance` and `angle`;
- a CadQuery profile;
- a CadQuery workplane;
- a feature-added region.

The graphs are derived by `02a` extract CadQuery AST, `02b` execute CadQuery, and
`02c` build CAD graph, and written to a temporary directory. No Parquet is
committed here, and no cache is involved.

## Rejection fixtures

A rejection fixture is the opposite of a coverage fixture: a deliberately
degenerate program that must be rejected. The two sets are kept apart, so a
degenerate program cannot make a support-table cell look supported.

A rejection fixture records its expected failure reason. The tangent cut is
asserted in [`../02c-build-cad-graph.md`](../02c-build-cad-graph.md); the probe
filter is asserted in [`../02b-execute-cadquery.md`](../02b-execute-cadquery.md).

The rejection set starts with one program: a cut tangent to a face, for the
clear-case margin on a predicate. Probe rejection is a unit test on the filter,
not a program, because a well-formed solid keeps its centroid probe.
