# CAD-QA Reviewer-Readiness Checklist

Use this checklist before sharing a dataset build, paper draft, or review
artifact. Every item should have a passing command, generated artifact path, or
recorded exception.

## Dataset Build

- Generate the intended dataset from the checked-in config and record the exact
  command.
- Confirm CADEvolve source provenance is preserved through archive member paths,
  not local cache paths.
- Confirm synthetic fixtures are used only for golden, smoke, debug, fallback,
  or edge-case rows.
- Confirm public rows exist for the intended task set.
- Confirm row counts by task, split, source subtree, and difficulty tag.
- Confirm failure manifests include all rejected sources and trace failures.

## Reproducibility

- Run the full test suite when tests exist:

```bash
rtk uv run pytest -q
```

- Compile Python modules when package code exists:

```bash
rtk uv run python -m compileall -q .
```

- Compare two independently generated dataset directories when the audit script
  exists.
- Confirm dataset metadata records Python, CadQuery, OCP, OpenCascade, config
  hash, code commit, and label policy.
- Confirm local-only cache paths and downloaded archive paths are not included
  in release artifacts.

## Schema And Export

- Validate every JSONL row against the schema.
- Confirm row IDs are unique.
- Confirm answer types match task types.
- Confirm numeric answers are finite.
- Confirm prompt hashes are stable.
- Confirm Parquet release files, if produced, match JSONL row counts.
- Confirm public rows can be loaded without CadQuery installed.

## Label Quality

- Check operation graph extraction success rates.
- Check isolated execution success rates.
- Check trace snapshot success rates.
- Inspect topology/kernel failure categories.
- Manually inspect a sample covering:
  - box/extrude;
  - hole/cut;
  - selector expressions;
  - workplane transforms;
  - fillet/chamfer;
  - near-boundary points;
  - provenance relations.
- Recompute labels for a deterministic sample and compare against exported
  labels.

## Leakage

- Run split leakage audit for:
  - `source_id`;
  - `generator_id`;
  - source subtree;
  - normalized source hash;
  - operation signature;
  - topology signature;
  - counterfactual group;
  - point sampling group.
- Confirm all counterfactual variants stay in the same split.
- Confirm held-out test splits match their advertised isolation rule.

## Evaluation

- Run majority/random baselines.
- Run static operation-count baseline.
- Run selector heuristic baseline.
- Run numeric and topology validation metrics.
- Evaluate at least one closed-book LLM prediction file.
- Confirm invalid output rate is reported.
- Confirm per-task and per-split metrics are reported, not only a single
  headline number.

## Release Notes

- Document dataset version.
- Document task families included and excluded.
- Document CADEvolve source version and license.
- Document label policy and known kernel sensitivities.
- Document known limitations of feature provenance.
- Include citation text and intended use.
- Include a clear statement that public task evaluation does not require CAD
  execution.
