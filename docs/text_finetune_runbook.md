# Text Finetune Runbook

Training exports now exist for the graph-first row schema:

- answer-only SFT rows from `data/cadqa_graph_smoke/rows.jsonl`;
- candidate-trace reasoning rows from hidden query programs;
- ablations by hop count, relation family, and measurement scope.

These exports currently prove that the row schema can be converted to SFT
JSONL. They are not automatically suitable for model training. Before running a
real fine-tune, use a dataset that has passed geometry-first quality gates:
syntax-only calibration rows must be excluded or capped, prompt families must
each represent 1%-10% of the export, value-bearing and cross-feature coverage
must pass thresholds, parameterized families must have healthy sampled
distributions, and the main rows must require geometry-derived evidence rather
than assignment-name, operation-order, or literal-argument lookup.

For benchmark-release fine-tuning, use the numeric tier in
`specs/dataset-spec.md`: at least 10,000 default SFT rows, at least 99%
geometry-critical default SFT rows, 0% syntax-only default SFT rows,
value-bearing rows in the 15%-30% band, cross-feature value-bearing rows in the
5%-15% band, generated task families in the 1%-10% band, and healthy sampled
parameter distributions. Current smoke/release-candidate gates are not enough for
that claim.

Use `--release-tier benchmark-release` to apply the benchmark numeric profile to
SFT reports. The default tier is `release-candidate`, so benchmark claims should
always pass the stricter tier explicitly.

Build the smoke SFT artifacts:

```bash
rtk uv run cadqa training export-sft \
  --rows data/cadqa_graph_smoke/rows.jsonl \
  --out runs/sft_smoke \
  --scaling-sizes 8 16 32
```

By default, `export-sft` writes only the geometry-critical training subset and
excludes syntax-only calibration, noncritical, and quarantined rows. Use
`--include-calibration` only when intentionally exporting calibration data for
audits or ablations.

The command writes:

- `answer_sft.jsonl`;
- `reasoning_sft.jsonl`;
- `ablations/*.jsonl` grouped by hop count and difficulty;
- `scaling/*.jsonl` grouped by requested size.

Do not use legacy `scripts.training.*` commands. They were removed during the
graph-first reset.
