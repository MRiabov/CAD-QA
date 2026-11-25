# Coverage fixtures

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
