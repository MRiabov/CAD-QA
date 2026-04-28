# Useful Implementation Optimization Notes

This document records implementation choices that should make CAD-QA easier to
build, optimize, debug, and release. The expensive work is source execution,
intermediate-state capture, topology traversal, selector evaluation, point
classification, provenance matching, meshing, and rendering.

## Core Release Decision

The default dataset format should be code-plus-label, not geometry-plus-label.

Store in public rows:

- normalized CadQuery code;
- prompt;
- structured answer;
- target feature, selector, entity, or point;
- raw labels such as volume, bounding box, topology counts, point
  classification, and provenance relation;
- diagnostics such as label status, confidence, kernel status, and failure
  reason;
- provenance such as source ID, generator ID, operation signature,
  counterfactual group ID, config hash, code hash, and dataset version.

Do not store by default:

- STEP files;
- STL/OBJ/glTF meshes;
- B-Rep dumps;
- rendered images;
- serialized CadQuery/OpenCASCADE objects;
- local cache paths.

Allowed exceptions are small audit bundles, optional render bundles, local
generation caches, and failure reproducers outside the main public JSONL export.

## Pipeline Shape

Separate the system into five stages:

1. Source ingestion and normalization.
2. Operation graph extraction.
3. Isolated trace execution and geometry snapshot capture.
4. Task materialization.
5. Export and validation.

Recommended flow:

```text
CADEvolve source programs
  -> normalized source records
  -> operation graphs
  -> isolated execution traces
  -> snapshot geometry/topology/provenance metadata
  -> task rows and prompts
  -> split-safe JSONL/Parquet exports
```

The expensive CadQuery/OpenCASCADE work should happen only in stage 3. Stages 4
and 5 should consume precomputed metadata and avoid loading CadQuery.

## Record Granularity

Use one source record per normalized script, one trace record per successful
execution environment/configuration, one snapshot per supported feature step,
and many task rows per trace.

This prevents recomputing geometry for every prompt and allows future task
families to reuse the same raw labels.

## Caching Strategy

Cache these artifacts separately:

- normalized source records;
- operation graphs;
- isolated execution traces;
- per-snapshot scalar geometry labels;
- topology/entity ID maps;
- selector result tables;
- point classification tables;
- provenance match tables;
- rendered/debug artifacts.

Cache keys should include source hash, operation graph hash, execution
environment, label policy, and generator config.

## Offline Worker Model

CADEvolve scripts are untrusted Python. Run them in isolated workers with:

- wall-clock timeout;
- memory limit;
- disabled or restricted filesystem writes;
- disabled network;
- captured stdout/stderr;
- deterministic environment variables;
- structured failure reporting.

The main process should never import arbitrary source scripts directly.

## Operation Graph Extraction

The operation graph should be AST-based, not regex-based. It should support:

- simple fluent assignments;
- attribute calls;
- calls on prior variables;
- `result = ...` finalization;
- bounded static loops when trace execution can expand them;
- fallback `unsupported` nodes for dynamic constructs.

Store source lines and enough argument representation to make prompts auditable.

## Geometry Labeling Rules

Measure volumes, bounding boxes, and topology from precomputed snapshots. Do not
ask task materialization code to call CadQuery methods. Selector tasks should
use selector result tables generated during trace execution.

Topology matching should be best-effort but explicit. Store matching method and
confidence so provenance labels can be filtered instead of overclaimed.

## Broad Phase Before Expensive Work

Use cheap static filters before execution:

- file size limits;
- import allowlist;
- AST complexity limits;
- obvious missing CadQuery usage;
- known unsupported dynamic constructs.

After execution, use cheap geometry diagnostics before expensive provenance
matching:

- valid final solid;
- finite volume;
- bounded bounding box;
- nonempty topology;
- operation count within configured limits.

## Counterfactual Groups

Generate counterfactuals only after the base trace is valid. Small parameter
edits should preserve the same `counterfactual_group_id`, and all variants must
stay in the same split.

Counterfactual generation should prefer one changed factor at a time so labels
and explanations remain auditable.

## Parallelism

Parallelize at source/trace granularity. Avoid parallel writes to the same
cache file. Use append-only JSONL or per-worker shard files followed by a
deterministic merge.

The heavy geometry worker pool should be bounded separately from prompt/export
workers to avoid exhausting memory through OpenCascade objects.

## Determinism

Record all random seeds and sort all merges deterministically. Public row IDs
should not depend on worker completion order.

Stable IDs should be derived from content and canonical ordering:

- source ID from normalized source path/hash;
- feature ID from source variable or canonical step order;
- trace ID from source ID plus environment/config hash;
- row ID from task type plus trace/target fields.

## Rendering

Rendering is optional and belongs in audit or multimodal artifact bundles. It
should not be required to train or evaluate the default code-only CAD-QA tasks.

When rendering is used, store render IDs and camera metadata, not local paths.

## Validation Before Export

Before publishing a dataset build:

- validate schema;
- validate prompt/answer parseability;
- audit leakage groups;
- rerun a deterministic sample of labels;
- inspect failure manifests;
- inspect a small rendered sample;
- compare two independent runs when feasible.

## Implementation Order

1. Synthetic golden fixtures and schema validation.
2. CADEvolve source extraction and source records.
3. AST operation graph extraction.
4. Isolated execution producing final shape metadata.
5. Intermediate snapshot capture.
6. Scalar task rows: operation count, bbox, volume delta.
7. Selector and topology task rows.
8. Point membership task rows.
9. Provenance task rows.
10. Counterfactual and edit task rows.

## Anti-Patterns To Avoid

- Running CadQuery while formatting prompts.
- Treating topology counts as stable without storing kernel versions.
- Releasing rows that require local cache paths.
- Overfitting the schema to one prompt style.
- Treating feature provenance as single-label when the geometry is many-to-many.
- Using comments or source variable names that leak answers in public prompts.
