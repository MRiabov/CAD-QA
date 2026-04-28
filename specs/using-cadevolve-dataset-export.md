# Using CADEvolve Dataset

CADEvolve is a synthetic CAD dataset built around executable CadQuery programs.
For CAD-QA, CADEvolve is the primary source corpus for released benchmark
examples because it provides executable scripts at scale and enough source
regularity to reconstruct operation graphs and traces.

Synthetic primitives should be kept to golden fixtures, smoke tests, debugging
examples, and edge-case audits rather than used as a separate full corpus before
CADEvolve ingestion.

## Dataset at a Glance

- Format: WebDataset-style archive.
- Main executable trees: `CADEvolve-P/` and `CADEvolve-C/`.
- Generator/context tree: `CADEvolve-G/`.
- License metadata: expected `apache-2.0`; confirm from the local dataset card
  and release files used for the build.
- Paper: CADEvolve: Creating Realistic CAD via Program Evolution.

The paper describes a pipeline that evolves parametric generators and expands
them into a large set of CadQuery scripts paired with geometry artifacts. CAD-QA
should treat the executable CadQuery code as the primary input.

## Suggested Environment

For archive inspection:

- Python;
- `tarfile`;
- `datasets` or `huggingface_hub` if loading from Hugging Face.

For execution:

- `cadquery`;
- a working CadQuery/OCP/OpenCascade backend;
- isolated worker support;
- enough disk space for a bounded extracted source subset.

## Archive Layout

The archive root has three top-level trees:

- `CADEvolve-G/` for generator artifacts and embeddings;
- `CADEvolve-P/` for executable CadQuery programs;
- `CADEvolve-C/` for executable CadQuery programs.

Within those trees, expected subfolders include:

- `CADEvolve-G/parametric_generators.json`;
- `CADEvolve-G/embeddings/`;
- `CADEvolve-P/ABC-P/`;
- `CADEvolve-P/CADEvolve-P-core/`;
- `CADEvolve-P/ShapeNet-P/`;
- `CADEvolve-C/ABC-C/`;
- `CADEvolve-C/CADEvolve-C-core/`;
- `CADEvolve-C/ShapeNet-C/`.

Archive paths may include a leading `./`, so prefix filters should account for
both forms.

## Quirks and Handling Notes

- The `.py` files are arbitrary Python and must be treated as untrusted input.
- Many scripts assign the final object to `result`; some may use alternate
  variables.
- Some scripts are simple primitives, while others use advanced CadQuery
  features such as sweeps, lofts, multiple workplanes, helper functions, and
  selectors.
- `CADEvolve-G`, `CADEvolve-P`, and `CADEvolve-C` are different kinds of
  content, not interchangeable subsets of the same representation.
- Repeated local generation should use a deterministic extracted source
  directory, not the tar archive as the hot path.
- Do not extract the entire upstream archive by default. Extract a bounded
  configured subset or source shard for the intended run.

## Basic Workflow

### 1. Browse Metadata

Use the dataset page or local archive listing to inspect row counts, top-level
paths, and license metadata.

### 2. Materialize a Local Source Subset

Create a deterministic source directory preserving archive member paths. Record:

- source archive path;
- extraction command;
- extraction config;
- selected prefixes;
- file count;
- manifest hash.

The extracted directory is a local generation artifact. Public rows should
preserve archive provenance, not local cache paths.

### 3. Normalize Sources

For each selected `.py` file:

- read source text;
- normalize line endings;
- parse with Python AST;
- detect final result variable;
- build operation graph;
- compute raw and normalized hashes;
- assign source and group IDs.

### 4. Execute in Controlled Workers

Run each source in an isolated worker with timeouts. Capture:

- final result object status;
- intermediate snapshots;
- stdout/stderr;
- exception type and message;
- Python/CadQuery/OCP versions;
- worker resource limits.

### 5. Generate CAD-QA Rows

From successful traces, materialize structured rows for operation, selector,
volume, topology, point, and provenance tasks. Prompt generation should not
load CadQuery or execute code.

## What to Expect From the Code

CADEvolve code is favorable for CAD-QA because many files are machine-generated
and single-assignment. A typical operation can often be represented as:

```json
{
  "feature_id": "wp13",
  "base": "wp7",
  "operation": "cut",
  "args": ["wp12"],
  "source_line": 13
}
```

This makes operation graphs and trace-backed QA practical. It does not by
itself solve exact face/edge/vertex provenance; that still requires execution,
topology matching, and, where possible, OpenCascade operation history.

## Safety Notes

- Never import CADEvolve scripts in the main generation process.
- Disable or restrict filesystem writes, networking, and subprocesses in
  workers.
- Use explicit timeouts.
- Store failures in a manifest instead of dropping them silently.
- Avoid publishing local paths, downloaded archive paths, or cache directory
  paths in released rows.

## References

- `specs/dataset-spec.md`
- `docs/cad_qa_feature_provenance.md`
- `specs/generation_policy.md`
- `specs/schema.md`
