# 07 — Exports: Harbor, SFT, evaluation

## Purpose

Export the dataset file / public / private artifacts to the downstream consumers: Harbor
tasks with no access to CadQuery, fine-tuning SFT data, evaluation request/grade
artifacts, and one-command smoke orchestration.

## Inputs / outputs

- **Input:** **dataset file**; **public**/**private** artifacts; or LLM model response JSONL
  (`pipeline/00-overview.md`).
- **Outputs:**
  - **Harbor:** task directories plus `cadqa_harbor_job.json`, `cadqa_harbor_manifest.json`,
    `tasks.jsonl` (`dataset/harbor.py::materialize_harbor_tasks`); an ATIF export
    (`train_and_eval/harbor.py::export_harbor_atif`).
  - **SFT:** `answer_sft.jsonl`, `reasoning_sft.jsonl`, `ablations/*.jsonl`,
    `scaling/*.jsonl`, `sft_report.json` (`dataset/release/sft.py`,
    `dataset/cli.py::_cmd_training_export_sft`).
  - **Evaluation:** request exports, oracle responses, graded metrics, reports for the
    no-access-to-CadQuery setting, tool-assisted upper bound (`train_and_eval/grading/`).
  - **Smoke experiment tree:** graph/query/dataset/release_dataset/baseline/requests/grade/
    tool-assisted/sft trees plus `run_summary.json`, `RUN_SUMMARY.md`, and
    `PAPER_RESULTS.md` (`train_and_eval/experiment.py::run_smoke_experiment`).

## Requirement

Exports must preserve the public/private boundary. Harbor tasks must give the agent no
access to CadQuery: the agent sees only the public prompt and may not import CadQuery or
OCP, and the grader scores `1` only for a parsed exact match to the private gold answer. The default SFT export must be
the geometry-critical subset, and its readiness report must not pass when the set is
geometry-light, prompt-family collapsed, answer-collapsed, geometry-hop-light, or
syntax-calibration-heavy.

## Current status

**exists.** Harbor, SFT, evaluation, and experiment orchestration are present and readable
(`dataset/harbor.py`, `dataset/release/sft.py`, `train_and_eval/grading/`,
`train_and_eval/experiment.py`, `dataset/cli.py`). No export was run while writing this doc.

## Verification

```bash
rtk uv run cadqa training export-sft \
  --rows runs/dataset/rows.parquet --out runs/sft

rtk uv run cadqa dataset export-public-private runs/release_dataset
rtk uv run cadqa harbor materialize \
  --public runs/release_dataset/public.parquet \
  --private runs/release_dataset/private.parquet \
  --out runs/harbor --split test --max-rows 8 --fresh

rtk uv run cadqa experiment smoke \
  --sources-jsonl runs/cadevolve_sources.parquet --limit 10 --out runs/experiment_smoke
```

The focused tests are `tests/test_graph_first_pipeline.py::test_sft_exports_coordinate_answers_as_prompt_tuple_text`
and the smoke/integration tests around `experiment`. Harbor execution itself
(`harbor run -c …/cadqa_harbor_job.json`) is an external dependency and is not run here.

## Local decisions

### D1 — Harbor gets ordinary task directories; CAD-QA keeps the Query verifier

- **Status:** accepted.
- **Context:** Harbor is the evaluation runner; CAD-QA owns graph construction, query
  synthesis, and the Query verifier, plus public/private policy (`docs/_archive/harbor.md`).
- **Decision:** `dataset/harbor.py::materialize_harbor_tasks` writes each task with
  `instruction.md`, `task.toml`, `environment/Dockerfile`, `workspace/prompt.txt`,
  `workspace/row_public.json`, `tests/…` Query verifier fixtures, and `solution/…` oracle
  files; the Query verifier calls `train_and_eval.grading.grade.grade_public_private`.
- **Consequences:** Reward is `1` only for a parsed exact match to the private gold answer;
  the agent may write `/app/answer.json` or `/app/answer.txt`.

### D2 — Public rows in Harbor come only from `PUBLIC_FIELDS`

- **Status:** accepted.
- **Context:** A task must not leak private Query verifier fields.
- **Decision:** the materializer writes `workspace/row_public.json` from
  `dataset/release/public.py::PUBLIC_FIELDS` only.
- **Consequences:** `gold_answer`, `query_program`, `candidate_trace`, and `clue_map` never
  reach the agent workspace.

### D3 — Default SFT is geometry-critical; calibration is opt-in

- **Status:** accepted (see DD-10).
- **Decision:** `dataset/release/sft.py::default_training_rows` keeps geometry-critical,
  non-calibration, non-quarantined rows; `--include-calibration` bypasses the filter and
  disables training gate enforcement.
- **Consequences:** The CLI raises a `RuntimeError` when applicable training gates fail,
  unless `--allow-failing-training-gates` is passed.

### D4 — Answer-only and reasoning SFT are separate exports

- **Status:** accepted.
- **Context:** The paper wants both direct-answer supervision and reasoning-length study.
- **Decision:** `answer_sft_rows` emits prompt→answer pairs; `reasoning_sft_rows` emits
  prompt→(answer candidate set trace step counts + answer) pairs (`dataset/release/sft.py`).
- **Consequences:** Both are written plus hop/difficulty ablations and size-based scaling
  subsets.

### D5 — The smoke experiment emits both full and filtered trees

- **Status:** accepted.
- **Context:** Release numbers must be auditable against the broader generation surface
  (`specs/dataset-spec.md`).
- **Decision:** `run_smoke_experiment` writes a full `dataset/` tree and a filtered
  `release_dataset/` tree, with baselines, requests, grades, tool-assisted runs, and SFT
  exports for both.
- **Consequences:** A single command produces the orchestratable evidence tree; the release
  tree passes its own Query verifier report.

## Open questions

- **The dataset file is the coupling.** The restructure plan intends `train_and_eval/` to
  consume only the rows I/O contract and answer contract. Whether consumer code today reads
  anything beyond `rows`/`public`/`private` is `[unknown]`; that boundary is not enforced by
  a test here.
- **`reasoning_sft` is not an agent training trace.** It summarizes candidate-set sizes, not
  LLM model reasoning. Whether it is useful supervision is a fine-tuning question, out of
  scope for this pipeline.
- **Harbor agent and LLM model config is run configuration, not part of the task contract**
  (`docs/_archive/harbor.md`); the default pin is `terminus-2` with
  `openrouter/deepseek/deepseek-v4-flash`.
- **LLM-output recording.** The dataset-generation path contains no LLM calls, so the
  "record every LLM call" rule applies to the fine-tuning/evaluation surface, not here.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- A Harbor task-count/coverage report sliced by hop, difficulty, relation family, and
  measurement scope, so a benchmark run's composition is visible before it executes.
