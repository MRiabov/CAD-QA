# Overnight Task: Apr 28 to Apr 29

This document has two sections:

1. The original human prompt, lightly corrected for typos and clarity.
2. A suggested expansion for execution. This expansion is guidance only. If it
   conflicts with the original prompt, the original prompt wins.

## 1. Original Human Prompt

See a similar codebase at `../IntersectionQA`.

It has a concept of overnight tasks.

Write an overnight task today to:

1. Implement the codebase overnight.
2. Run an SFT experiment as per the "run experiment" skill.

The code is somewhat similar to IntersectionQA, which makes implementation
easier. The main difference is that CAD-QA has two topology phases:
preprocessing and the rest of the pipeline. The implementation should be similar
in spirit to IntersectionQA.

## 2. Suggested Expansion

This section is my suggested operational expansion. It is not a replacement for
the original prompt above.

### Precedence

- The original human prompt above is the source of truth.
- Follow CAD-QA specs before copying IntersectionQA behavior:
  - `specs/label_rules.md`
  - `specs/schema.md`
  - `specs/benchmark-task-spec.md`
  - `specs/generation_policy.md`
  - `specs/research-experiment-spec.md`
- Use IntersectionQA as an implementation reference, not as a semantic source of
  truth. CAD-QA is single-script CadQuery program reasoning, not two-object
  intersection reasoning.
- Keep public prompts closed-book. Evaluation and prompt formatting must not
  execute CadQuery or recompute labels.

### Files To Read First

- `/home/maksym/.codex/RTK.md`
- `README.md`
- `specs/benchmark-task-spec.md`
- `specs/schema.md`
- `specs/label_rules.md`
- `specs/generation_policy.md`
- `specs/using-cadevolve-dataset-export.md`
- `specs/research-experiment-spec.md`
- `epics-and-stories.md`
- `../IntersectionQA/AGENTS.md`
- `../IntersectionQA/overnight-task.md`
- `../IntersectionQA/.agents/skills/run-experiments/SKILL.md`
- `../IntersectionQA/.agents/skills/run-experiments/references/experiment-workflow.md`
- `../IntersectionQA/configs/overnight_experiment_suite.yaml`
- `../IntersectionQA/scripts/experiments/run_experiment_suite.py`
- `../IntersectionQA/scripts/training/text_sft_train_unsloth.py`

Use `rtk` for local shell commands. On a bootstrapped Vast/PyTorch GPU image,
use the image Python directly after bootstrap, following the run-experiments
skill.

### Known Starting State

- CAD-QA already has seed package modules under `cad_qa/` for config, source
  loading, AST operation graphs, optional tracing, materialization, validation,
  splitting, parsing, baselines, and export.
- The advertised console entry point `cadqa = cad_qa.cli:main` currently needs
  to be made real and tested.
- There are no committed tests in this snapshot. Add focused tests before
  trusting generated data.
- The current implementation is a vertical seed, not a complete release or
  training stack.
- A likely adjacent CADEvolve-style local source tree exists at:
  `/home/maksym/Work/proj/Problemologist/big-build123d-dataset/cadevolve-cq-translation/translated`
  and should be checked before downloading anything.
- Treat existing uncommitted/untracked files as user work. Do not revert them.

### Core Objective

By morning, leave CAD-QA in a state where a future agent or researcher can see:

- what code was implemented;
- which smoke and validation commands pass;
- what dataset candidate was built;
- what SFT experiment was run or why it was gated off;
- where artifacts, logs, metrics, and the exact next command live.

The preferred outcome is:

- a runnable CAD-QA CLI and script stack;
- a validated smoke dataset;
- a bounded CADEvolve-derived release candidate;
- baseline reports;
- one Qwen3.5 4B answer-only SFT canary, promoted to a longer run only if the
  canary is healthy.

### Implementation Priorities

1. Stabilize the local package.
   - Add `cad_qa/cli.py` matching README commands:
     `smoke`, `generate`, `trace`, `validate`, and `baseline`.
   - Make `uv run cadqa ...` work from a clean checkout.
   - Add tests for config loading, source loading, operation graph extraction,
     smoke export, row validation, parsing, baselines, and CLI smoke paths.
   - Run `rtk uv run python -m compileall -q cad_qa` and focused pytest before
     larger work.

2. Build the CAD-QA data pipeline in the same spirit as IntersectionQA.
   - Keep reusable logic in package modules and scripts thin.
   - Add `scripts/dataset/`, `scripts/evaluation/`, `scripts/training/`,
     `scripts/experiments/`, and `scripts/devops/` only as needed.
   - Reuse IntersectionQA orchestration patterns where practical:
     manifest-driven runs, run directories, explicit artifact contracts, and
     dated experiment docs.
   - Do not copy IntersectionQA task semantics.

3. Implement topology as two phases.
   - Phase A: trace/preprocess topology once. Extract per-snapshot topology
     counts and geometry classifications under the recorded CadQuery/OCP
     environment.
   - Phase B: materialize prompts, labels, metrics, and SFT rows only from
     stored topology records.
   - Do not recompute topology inside prompt formatting, baseline evaluation,
     SFT preparation, or prediction grading.

4. Complete MVP task-row support as far as possible.
   - Required v0.1 families:
     `operation_count`, `selector_count`, `bbox_after_step`,
     `signed_volume_delta`, `topology_count_after_step`, `point_membership`,
     and `feature_provenance_choice`.
   - If exact provenance is not reliable overnight, implement conservative
     provenance rows only when confidence is defensible and document the gap.
   - Do not block the first SFT canary on provenance if the other task families
     produce validated rows.

5. Make CADEvolve generation usable.
   - Prefer an adjacent extracted source tree over redownloading.
   - Preserve source-relative paths and avoid public local path leaks.
   - Execute untrusted CadQuery scripts only in isolated workers with timeouts.
   - Record failures in a manifest instead of silently dropping them.
   - Add row-count, failure-reason, split, and task-balance reports.

6. Add release-style validation and baselines.
   - Validate every public row against executable schema checks.
   - Report row counts by task, split, source subtree, `requires`, and
     difficulty tag.
   - Add majority, random, static operation-count, regex operation-count,
     selector heuristic, and simple numeric/topology baselines where feasible.
   - Preserve baseline predictions and metrics JSON.

7. Prepare SFT data.
   - Use public `train` rows only for optimizer updates.
   - Use public `validation` and held-out splits only for evaluation.
   - Build answer-only chat rows from public prompt and canonical answer.
   - Preserve row IDs, task types, split, prompt hash, and answer in the SFT
     dataset.
   - Keep answer formatting aligned with the parser policies in
     `cad_qa.parse`.

### Local Preflight

Run these before renting or restarting GPU:

```bash
rtk uv run python -m compileall -q cad_qa
rtk uv run pytest -q
rtk uv run cadqa smoke --output-dir data/cadqa_smoke
rtk uv run cadqa validate data/cadqa_smoke
rtk uv run cadqa baseline data/cadqa_smoke/jsonl/train.jsonl
```

After the CADEvolve source path is confirmed:

```bash
rtk uv run cadqa generate \
  --source-dir /home/maksym/Work/proj/Problemologist/big-build123d-dataset/cadevolve-cq-translation/translated \
  --output-dir data/cadqa_cadevolve_rc_500 \
  --limit 500

rtk uv run cadqa validate data/cadqa_cadevolve_rc_500
rtk uv run cadqa baseline data/cadqa_cadevolve_rc_500/jsonl/train.jsonl
```

If these commands do not exist yet, implement them before moving to training.

### Experiment Stack To Port Or Implement

CAD-QA does not yet have the full IntersectionQA experiment stack. Implement the
minimal restartable path needed for tonight:

- `configs/overnight_experiment_suite.yaml`
- `configs/orchestration_smoke.yaml`
- `scripts/experiments/run_experiment_suite.py`
- `scripts/experiments/monitor_experiment_run.py`
- `scripts/training/prepare_answer_sft_dataset.py`
- `scripts/training/text_sft_smoke.py`
- `scripts/training/text_sft_train_unsloth.py`
- `scripts/training/evaluate_text_model.py`
- `docs/experiment_execution_runbook.md`
- `docs/text_finetune_runbook.md`
- `docs/experiments/apr-28-29-qwen3p5-4b-cadqa-answer-sft.md`

Use the IntersectionQA files as references, but adapt:

- package names from `intersectionqa` to `cad_qa`;
- row schema and parser behavior to CAD-QA;
- dataset grouping to `source_id`, `trace_id`, source subtree, operation,
  topology, and near-boundary tags;
- metrics to numeric tolerance, exact integer accuracy, enum accuracy, bbox
  tolerance, and invalid-output rate.

### SFT Experiment Plan

Goal: run one answer-only SFT experiment, not a broad sweep.

Default model:

```text
unsloth/Qwen3.5-4B
```

Canary first:

- 128-512 train rows;
- 32-128 eval rows;
- 20-50 optimizer steps;
- same row IDs and task mix preserved across reruns when possible;
- `max_seq_length` large enough for CAD-QA prompts without heavy truncation;
- frequent eval on parse-valid rate, exact/tolerance accuracy, invalid-output
  rate, and task-sliced accuracy.

Promote only if:

- loss is finite;
- no repeated OOM;
- completions are parse-valid at a reasonable rate;
- outputs do not collapse to a common label;
- held-out quality is not obviously worse than majority/static baselines;
- prompt/target truncation is measured and acceptable.

Suggested local manifest checks:

```bash
rtk uv run python -m scripts.experiments.run_experiment_suite \
  configs/overnight_experiment_suite.yaml --list

rtk uv run python -m scripts.experiments.run_experiment_suite \
  configs/overnight_experiment_suite.yaml --run answer_sft_canary --with-dependencies --dry-run
```

Suggested GPU command shape after bootstrap:

```bash
cd /root/CAD-QA
python -m scripts.experiments.run_experiment_suite \
  configs/overnight_experiment_suite.yaml \
  --run answer_sft_canary \
  --with-dependencies
```

If the canary is healthy, run the longer answer-only SFT entry from the same
manifest. Do not start reasoning-SFT or RL tonight unless answer-only SFT is
healthy, artifacts are preserved, and there is enough remaining budget and time.

### GPU And Run-Experiment Rules

Follow the run-experiments skill from IntersectionQA:

- Use manifest-driven, restartable runs instead of one-off training commands.
- Run cheap local validation before renting GPU.
- Use public `train` only for optimizer updates.
- Keep validation/test rows out of training.
- Select the cheapest suitable A100 80GB or H100-class instance after checking
  live price, VRAM, disk, and reliability.
- Bootstrap the instance with a script; do not spend GPU time debugging a
  half-installed environment if a known PyTorch image path is available.
- Launch long jobs in `tmux` or `nohup`.
- Monitor the first optimizer steps, GPU utilization, memory, disk, loss,
  invalid-output rate, and checkpoint writes.
- Preserve artifacts before teardown.
- Do not write secrets or credentials into repo files.

No explicit spend limit was provided in the prompt. Record live pricing and
estimated cost before launching any non-canary run. If pricing or account state
is unclear, stop after local artifacts and leave the exact GPU launch command.

### Stop Rules

- If package compile or focused tests fail, fix implementation first.
- If CLI smoke generation fails, do not run SFT.
- If dataset validation fails, do not train.
- If leakage or split grouping is unknown, do not train.
- If generated rows are dominated by one task or one answer, fix sampling or
  explicitly label the SFT as a tiny diagnostic.
- If CadQuery execution is too unstable, run static-only smoke and document the
  blocker instead of pretending it is the full benchmark.
- If GPU canary OOMs, reduce sequence length, batch size, or row cap before
  changing model size.
- If parse-valid rate remains poor after a short canary, fix answer formatting
  and parser alignment before extending.
- If artifacts cannot be saved, uploaded, or mirrored, stop before teardown and
  preserve local logs/checkpoints.

### Artifact Contract

For every meaningful implementation or experiment run, preserve:

- exact command;
- git status and dirty diff note;
- config and manifest JSON/YAML;
- source manifest hash;
- dataset metadata and split manifest;
- validation report;
- failure manifest;
- baseline metrics and predictions;
- SFT dataset report;
- prompt/target token length and truncation stats;
- train and eval metrics JSONL;
- sampled completions;
- checkpoints/adapters;
- hardware and runtime stack;
- upload paths and checksums when available.

### Morning Handoff

Before stopping for the morning, leave:

- execution log;
- researcher summary;
- implementation summary;
- commands that passed and failed;
- dataset path and validation status;
- SFT run status and best metrics;
- current GPU/session status;
- artifact paths and upload status;
- exact next command.

### Execution Log

Fill this in while running.

### Researcher Summary

Fill this in before morning handoff.
