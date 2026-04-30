# Text Finetune Runbook

Training exports now exist for the graph-first row schema:

- answer-only SFT rows from `data/cadqa_graph_smoke/rows.jsonl`;
- candidate-trace reasoning rows from hidden query programs;
- ablations by hop count, relation family, and measurement scope.

Build the smoke SFT artifacts:

```bash
rtk uv run cadqa training export-sft \
  --rows data/cadqa_graph_smoke/rows.jsonl \
  --out runs/sft_smoke \
  --scaling-sizes 8 16 32
```

The command writes:

- `answer_sft.jsonl`;
- `reasoning_sft.jsonl`;
- `ablations/*.jsonl` grouped by hop count and difficulty;
- `scaling/*.jsonl` grouped by requested size.

Do not use legacy `scripts.training.*` commands. They were removed during the
graph-first reset.
