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
`tests/grade_cadqa.py`, `solution/solve.sh`, and hidden verifier data under
`expected/private.json`. The solution script is for Harbor oracle runs only; it
reads the private answer key and writes `/app/answer.json`.
The agent must write exactly one of:

```json
{"answer": "...", "confidence": 0.75}
```

to `/app/answer.json`, or plain answer text to `/app/answer.txt`.

The task allows local computation, including Python standard-library modules and
installed third-party packages such as NumPy. It remains closed-book CAD
reasoning: agents must not import or call CadQuery, `cq`, OCP, OpenCascade, or
any other CAD kernel, and must not make network requests.

## Run With Harbor

Run one task or the full materialized directory:

```bash
harbor run -c runs/harbor_cadqa_smoke/cadqa_harbor_job.json
```

The generated job config uses the `terminus-2` Harbor agent with model
`openrouter/deepseek/deepseek-v4-flash`. It also pins conservative run limits:
`max_input_tokens=32768`, `max_output_tokens=16384`, `max_tokens=16384` on each
LLM call, `max_turns=32`, one attempt, no trial retries, and one concurrent
trial. In Terminus-2, `max_turns` is the cap on agent interaction turns/tool-use
rounds; Harbor `max_retries` is only a job-level retry policy for failed trials.
For OpenRouter models with native low-cost cache hits, generated configs pin
provider routing in `llm_call_kwargs.extra_body.provider`: DeepSeek models route
only to the `deepseek` provider and Xiaomi Mimo models route only to the
`xiaomi` provider, with fallbacks disabled. This prevents OpenRouter from
load-balancing or failing over to other providers whose cached-token pricing and
cache locality can make repeated agent loops materially more expensive.
The materializer writes the same recommendation to `cadqa_harbor_manifest.json`
under `recommended_run`. Agent/model/token selection is a Harbor run
configuration, not part of the public task prompt or CAD-QA grading contract.
Use `--model openrouter/xiaomi/mimo-v2.5-pro` or another concrete OpenRouter
model on `cadqa harbor materialize` / `materialize-dataset` when generating a
non-default benchmark config; the native-provider pin is inferred from the model
prefix when supported.

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
