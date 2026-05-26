# Harbor Export

CAD-QA can export public/private row artifacts as Harbor closed-book CAD
reasoning tasks. Harbor receives ordinary task directories; CAD-QA keeps the
graph/query/verifier machinery, public/private split policy, grading, SFT gates,
and release-readiness checks.

## Build A Smoke Dataset

Create a small development slice with the normal CAD-QA pipeline:

```bash
rtk uv run cadqa experiment smoke \
  --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl \
  --limit 10 \
  --out runs/experiment_smoke
```

For benchmark or training claims, use the release and training gates documented
in `README.md` and `docs/text_finetune_runbook.md`. Smoke artifacts are useful
for integration checks only.

## Export Public/Private Rows

If a dataset directory does not already contain `public.parquet` and
`private.parquet`, export them first:

```bash
rtk uv run cadqa dataset export-public-private data/cadqa_graph_release_smoke
```

Public rows must not include `gold_answer`, `query_program`, `candidate_trace`,
`clue_map`, or verifier-private fields. The Harbor materializer writes
`workspace/row_public.json` from `cad_qa.dataset.public.PUBLIC_FIELDS` only.

## Materialize Harbor Tasks

From explicit public/private files:

```bash
rtk uv run cadqa harbor materialize \
  --public data/cadqa_graph_release_smoke/public.parquet \
  --private data/cadqa_graph_release_smoke/private.parquet \
  --out runs/harbor_cadqa_smoke \
  --split test \
  --max-rows 8 \
  --fresh
```

From a CAD-QA dataset directory:

```bash
rtk uv run cadqa harbor materialize-dataset \
  data/cadqa_graph_release_smoke \
  --out runs/harbor_cadqa_smoke \
  --difficulty hard \
  --relation-family has_measurement \
  --fresh
```

Filters are available for `--split`, `--difficulty`, `--relation-family`,
`--measurement-scope`, and `--max-rows`.

Each task contains `instruction.md`, `task.toml`, `environment/Dockerfile`,
`workspace/prompt.txt`, `workspace/row_public.json`, `tests/test.sh`,
`tests/grade_cadqa.py`, and hidden verifier data under `expected/private.json`.
The agent must write exactly one of:

```json
{"answer": "...", "confidence": 0.75}
```

to `/app/answer.json`, or plain answer text to `/app/answer.txt`.

## Run With Harbor

Run one task or the full materialized directory:

```bash
harbor run -p runs/harbor_cadqa_smoke -a <agent> -m <model>
```

The verifier uses `cad_qa.evaluation.grade.grade_public_private` for the single
row, writes the full CAD-QA artifact to `/logs/verifier/cadqa_grade.json`, and
writes the scalar reward to `/logs/verifier/reward.txt`. Reward is `1` only for
a parsed exact match to the private `gold_answer`; wrong, missing, duplicate, or
invalid output receives `0`.

## Export SFT And ATIF Artifacts

Harbor SFT export reuses CAD-QA's default training-row filter and readiness
report:

```bash
rtk uv run cadqa harbor export-sft \
  --rows data/cadqa_graph_release_smoke/rows.parquet \
  --out runs/harbor_sft
```

To export graded response records for Harbor ATIF workflows:

```bash
rtk uv run cadqa harbor export-atif \
  --responses runs/model_responses.jsonl \
  --public data/cadqa_graph_release_smoke/public.parquet \
  --private data/cadqa_graph_release_smoke/private.parquet \
  --out runs/harbor_atif
```

## Oracle Warning

`cadqa evaluation tool-assisted-upper-bound` uses private verifier artifacts to
construct deterministic oracle responses. It is an analysis upper bound only,
not a normal Harbor model-facing tool environment.
