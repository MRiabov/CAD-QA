# Coverage fixtures

Programs that define what the support table means by "supported". See
[`../task-step-support.md`](../task-step-support.md) for the test contract.

A fixture is one CadQuery program and its `program_sha256`. It is chosen from the
pinned pool for a capability it exercises, and it is representative rather than
degenerate.

Each fixture covers at least one of:

- several solid states, for provenance and effect answers;
- a pair relation, for `distance` and `angle`;
- a CadQuery profile;
- a CadQuery workplane;
- a feature-added region.

The graphs are derived by `02a` extract CadQuery AST, `02b` execute CadQuery, and
`02c` build CAD graph, and written to a temporary directory. No Parquet is
committed here, and no cache is involved.
