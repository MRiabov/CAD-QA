# 02c build CAD graph — entities, relations, measurements

> Authoritative: `../02c-build-cad-graph.md`
> Construction: `../extraction/graph-construction.md`
> Persistence: `../extraction/graph-persistence.md`
> Models: `models/02c-build-cad-graph.md`

READ:

- `CadQueryAstExtractionResult` from `02a`
- `CadQueryRuntimeExtractionResult` from `02b`; a `FailureTombstone` never enters
- `NormalizedProgram` → `program_id, program_sha256`

TRANSFORM:

- reject the pair when extraction hashes do not match
- map extraction records to graph entities, relations, and measurements per the construction sub-document
- attach every point probe to its solid state; a probe with no state is a graph defect
- assign graph IDs deterministically from their documented components
- every task-facing target, clue operand, answer value, and answer evidence resolves to a graph element; a missing element rejects the pair
- attach CAD graph evidence to every relation and measurement: `measured` with the kernel call, or `derived` with the rule and its references; a relation or measurement with neither rejects the pair
- carry the tolerance and the reason on a relation whose tolerance is overridden
- use the tables, IDs, attributes, enums, and evidence fields in the persistence sub-document
- reject on a missing required reference, an unresolved relation or measurement endpoint, an unknown extraction schema version, a non-deterministic graph ID, or a solid state above `max_state_entities`
- reject the pair when an AST operation has no recording, a recording has no AST operation, a state ID does not match its producing operation, a CadQuery selector ID does not match the AST extraction result, a selected entity is missing from the state, a solid state producing operation has no effect, the final state differs from the last state in operation order, or an entity ID hash does not match its fingerprint fields
- emit one complete graph per program or reject the pair; never a partial graph
- do not construct tasks and do not render prompts

WRITE:

- `CadGraph` `(program_sha256, graph schema version, runtime_extraction_result_sha256)` → nodes, relations, measurements
- `nodes.parquet`, `relations.parquet`, `measurements.parquet`
- failure partition `02c_build_cad_graph`
