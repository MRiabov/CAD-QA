# CAD-QA Feature Provenance Dataset Notes

This note captures an exploratory direction for a dataset family distinct from
IntersectionQA/IntersectionEdit. The working name is CAD-QA: code, topology, and
point questions over CAD construction provenance.

The core task is feature attribution: given CadQuery code plus a final CAD
entity or 3D point, answer which construction feature or code step created,
modified, deleted, bounded, or otherwise contributed to it.

## Task Idea

Example question forms:

- Given CadQuery code and a highlighted face, which feature created this face?
- Given CadQuery code and a 3D point on the model, which feature contributed to
  the face/edge/vertex containing that point?
- Given a selected final vertex, which previous feature first generated it or
  last modified the adjacent topology?

The answer should not be a single vague label like "feature". It should use a
small provenance ontology:

- `created_by`: the feature generated this final entity.
- `modified_by`: the feature changed an existing entity into this final entity.
- `deleted_by`: the feature removed a prior entity.
- `inherited_from`: the entity survived unchanged from an earlier state.
- `bounded_by`: the entity is a boundary induced by multiple contributing
  features.

Single-choice provenance rows store all defensible contributing features and
answer with the earliest contributor in source execution order. Cleanup,
unification, topology merging, or kernel history loss is represented in
diagnostics; rows are filtered when no contributor set can be defended.

For example, after cutting a cylindrical hole through a box:

- The cylindrical wall face is `created_by` the cut/hole feature.
- The top planar face is `modified_by` the cut/hole and `inherited_from` the
  base box top face.
- The circular top edge is `bounded_by` the original top face and the hole
  cutter.
- Untouched side faces are `inherited_from` the base box.

## CadQuery/OCC Findings

CadQuery selected `Face` and `Vertex` objects do not carry feature provenance.
They wrap OpenCascade `TopoDS_Shape` objects, which preserve topology and
geometry but not the history of modeling operations that produced them.

OpenCascade builder objects such as `BRepAlgoAPI_Cut` can expose per-operation
history through `Modified`, `Generated`, and `IsDeleted`, but CadQuery's fluent
API usually creates those builders internally, extracts `op.Shape()`, and drops
the builder. Once only the final `TopoDS_Shape` remains, exact operation history
is not recoverable.

CadQuery `Workplane` objects do retain a parent chain of prior fluent states.
This chain can show intermediate snapshots such as:

```text
final result -> derived workplane -> selected face -> base solid -> initial plane
```

That is useful for state diffing, but it is not a complete feature log. The
chain does not reliably preserve method names, arguments, or OCC builder
history.

## CADEvolve Reconstructibility

CADEvolve should be the primary source corpus for CAD-QA. It is unusually
favorable for reconstruction because the released programs are executable
CadQuery and the local source cache is machine-generated, mostly
single-assignment code.

The CADEvolve paper describes three relevant tiers:

- `CADEvolve-G`: about 8k parametric generators.
- `CADEvolve-P`: executable programs sampled from those generators.
- `CADEvolve-C`: canonicalized, normalized, binarized scripts used for training.

For CAD-QA, `CADEvolve-P` and `CADEvolve-C` are the first targets because they
are executable program trees. `CADEvolve-G` is useful for generator-family
metadata, leakage-resistant splitting, and source-family analysis, but should
not be treated as the default executable object source unless the pipeline
explicitly supports generator invocation.

A full scan of the local `data/cadevolve_sources` tree found:

- 100,000 Python source files.
- 100,000 files assigning the final object through `result = ...`.
- 3,129,349 call assignments.
- 3,129,115 simple call assignments of the form `target = name.method(...)`.
- 233 calls on attribute bases.
- 33 subscript assignments such as `wp7.vals()[18]`.
- 16 direct context mutations such as `wp41.ctx.pendingWires = [...]`.

This means an operation graph is highly reconstructible. A typical source can
be parsed into steps like:

```json
{
  "step_id": "wp13",
  "base": "wp7",
  "op": "cut",
  "args": ["wp12"],
  "source_line": 13
}
```

This is enough to reconstruct code-step provenance and to rerun programs
statement-by-statement with instrumentation. It is not enough, by itself, to
recover exact final face/edge/vertex provenance without executing the program
and tracking topology through the modeling operations.

## Recommended Generation Pipeline

For CADEvolve-backed CAD-QA:

1. Parse each source file with Python AST into a variable and operation DAG.
2. Execute statements step-by-step in an isolated worker, matching the existing
   repository caution that CADEvolve programs are untrusted Python.
3. Record each step's method name, arguments, source line, input variables, and
   output variable.
4. Preserve pre/post CadQuery objects for topology diffing.
5. Wrap high-value OCC operations where possible to capture `Modified`,
   `Generated`, and `IsDeleted` histories before CadQuery discards builders.
6. Assign stable IDs to final faces, edges, and vertices.
7. Attach provenance records to each final entity.
8. Materialize QA rows from those entity-level provenance records.

Suggested provenance record shape:

```json
{
  "entity_id": "face_017",
  "entity_type": "face",
  "geometry_type": "CYLINDER",
  "created_by": ["wp13"],
  "modified_by": [],
  "inherited_from": [],
  "bounded_by": ["wp7", "wp12"],
  "source_steps": ["wp12", "wp13"]
}
```

For point-grounded CAD-QA, map the point to the nearest or containing topology
entity using explicit tolerances, then answer from the entity provenance.

## Dataset Split

Random train/test splits are not enough for CADEvolve-backed CAD-QA. Store and
use split metadata from source paths, generator IDs, operation signatures, and
topology signatures.

Recommended split families:

- random sanity split
- generator-family held-out
- source-subtree held-out
- operation-sequence held-out
- topology held-out
- transform or coordinate-frame held-out
- near-boundary hard split

When exact generator IDs are unavailable, fall back conservatively to source
subtree, source path prefix, normalized code hash, operation signature, object
ID, and counterfactual group ID.

## Caveats

Feature provenance is many-to-many. Fillets, chamfers, shelling, booleans,
patterns, cleanup, and face unification can split, merge, or replace topology.
The label schema must allow multiple contributing steps and relation types.

CADEvolve code-step features are not necessarily human CAD design intent. A
label like `wp13.cut(wp12)` is defensible. A label like "mounting hole" requires
extra grouping or semantic naming.

Arbitrary CadQuery code should not be assumed reconstructible to the same
degree as CADEvolve. The favorable finding above depends on the observed
machine-generated structure of the local CADEvolve source cache.
