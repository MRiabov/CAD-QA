# Apr 28-29 CAD-QA Answer SFT

## Purpose

Implement the CAD-QA codebase far enough to produce validated public task rows,
baseline reports, answer-only SFT JSONL, and a restartable Qwen3.5 4B canary
manifest.

## Local Commands

```bash
rtk uv run python -m compileall -q cad_qa scripts tests
rtk uv run pytest -q
rtk uv run python -m scripts.experiments.run_experiment_suite configs/orchestration_smoke.yaml --resume
rtk uv run --extra cadquery cadqa generate --auto-source-dir --output-dir runs/cadevolve_trace_probe_t30/dataset --limit 3 --workers 1 --trace-timeout-seconds 30
rtk uv run --extra cadquery cadqa validate runs/cadevolve_trace_probe_t30/dataset
rtk uv run cadqa baseline runs/cadevolve_trace_probe_t30/dataset/jsonl/train.jsonl --output-dir runs/cadevolve_trace_probe_t30/baselines
rtk uv run python -m scripts.training.prepare_answer_sft_dataset --dataset-dir runs/cadevolve_trace_probe_t30/dataset --output-dir runs/cadevolve_trace_probe_t30/sft --max-train-rows 512 --max-eval-rows 128
rtk uv run python -m scripts.training.text_sft_smoke --sft-dir runs/cadevolve_trace_probe_t30/sft
rtk uv run python -m scripts.experiments.run_experiment_suite configs/overnight_experiment_suite.yaml --run answer_sft_canary --with-dependencies --dry-run
```

## Current Status

- Implementation: local CAD-QA package, CLI, scripts, configs, and tests are
  present. `epics-and-stories.yaml` has no remaining `planned` or
  `work-in-progress` implementation stories.
- Tests: `compileall` passes and `pytest -q` reports 38 passing tests.
- Dataset: current smoke generation produces 53 validated code-plus-label rows
  across the implemented task families.
- Local orchestration: `configs/orchestration_smoke.yaml` completed all runs and
  wrote dataset, validation, baseline, SFT JSONL, and SFT-format smoke
  artifacts under `runs/`.
- CadQuery: optional dependency install succeeded through
  `uv run --extra cadquery`, with CadQuery 2.7.0 and OCP 7.8.1.1 observed in
  trace metadata.
- CADEvolve probe: adjacent source directory detected at
  `/home/maksym/Work/proj/Problemologist/big-build123d-dataset/cadevolve-cq-translation/translated`.
  A 3-source trace-backed probe with a 30 second per-source timeout generated
  921 validated rows: 33 operation-count, 96 bbox, 62 signed-volume-delta, 665
  topology-count, 6 point-membership, and 59 conservative provenance rows. The
  failure manifest is empty. A 10 second probe had one timeout, so larger runs
  should use `--trace-timeout-seconds 30` or higher.
- SFT data: CADEvolve trace probe SFT prep wrote 512 train and 128 validation
  answer-only chat rows; format smoke passed.
- 10-source RC: `data/cadqa_cadevolve_rc_10` generated 1,419 validated public
  rows: 958 train, 298 validation, and 163 test-random rows. Five of ten
  sources timed out at 30 seconds and are recorded in `failure_manifest.jsonl`;
  static operation-count rows are still emitted for failed traces. Baselines are
  under `runs/cadqa_cadevolve_rc_10_baselines`, and answer-only SFT JSONL is
  under `runs/cadqa_cadevolve_rc_10_sft`.
- Training: real SFT is gated unless GPU dependencies, CUDA, and
  pricing/account state are confirmed. The `answer_sft_canary` manifest entry
  now launches through `uv run --extra training`; `answer_sft_canary_dry_run`
  remains available for local artifact checks.

## Apr 29 Vast RC Canary

Ran the first GPU answer-only SFT canary on Vast instance `35803130`
(`A100-SXM4-80GB`, listed price `$0.8411/hr`) using the 10-source RC dataset
already present on the instance at `data/cadqa_cadevolve_rc_10`.

Command:

```bash
cd /root/CAD-QA
uv run python -m scripts.experiments.run_experiment_suite \
  configs/rc_answer_sft_canary_vast.yaml \
  --run answer_sft_rc_canary \
  --with-dependencies \
  --resume
```

Local gates before launch:

```bash
rtk scripts/experiments/run_cadqa_experiment.sh preflight
rtk uv run python -m scripts.experiments.run_experiment_suite \
  configs/rc_answer_sft_canary_vast.yaml --run answer_sft_rc_canary --with-dependencies --dry-run
rtk uv run python -m scripts.dataset.dataset_stats \
  data/cadqa_cadevolve_rc_10 --output /tmp/cadqa_rc_dataset_stats.json
```

Stop-gate dependencies all completed on the instance:

- `runs/validate_rc_dataset`
- `runs/rc_heuristic_baselines`
- `runs/prepare_answer_sft_rc_canary`
- `runs/text_sft_rc_format_smoke`
- `runs/compare_rc_heuristic_experiments`
- `runs/check_rc_canary_stop_gates`

Training result:

- Model: `unsloth/Qwen3.5-4B`
- Train rows: 958 public `train` rows
- Eval rows staged: 128 public `validation` rows
- Steps: 20
- Adapter: `runs/answer_sft_rc_canary/adapter`
- Status: completed
- Runtime: 884.8166 seconds for trainer loop; manifest elapsed time
  928.958 seconds
- Final train loss: 1.1522146046161652
- Throughput: 0.181 samples/sec, 0.023 steps/sec
- Loss masking: `packed_assistant_tokens_only`
- `--pack-tokenized`, `--no-assistant-only-loss`

Monitoring notes:

- Live GPU was `NVIDIA A100-SXM4-80GB`, CUDA available.
- Training used only about 9.6 GB of 80 GB VRAM.
- Step time was about 43.7 seconds after the first step.
- GPU utilization sampled around 73-75% during steady training, with lower
  samples during monitoring. This is acceptable for a tiny canary artifact but
  too underutilized for a longer run.
- Warnings: Flash Attention 2 was unavailable and Unsloth used Xformers; Unsloth
  also warned about import order and a missing fast path. Fix the runtime/kernel
  path and raise per-device batch size before promoting to a longer run.

Artifacts:

- Remote run directory: `/root/CAD-QA/runs/answer_sft_rc_canary`
- Remote package: `/root/CAD-QA/runs/package_rc_canary_artifacts`
- HF bucket upload:
  `hf://buckets/MRiabov/cadqa-qwen3p5-4b-sft-artifacts/cadqa-overnight-2026-04-29/vast-35803130/rc-answer-sft-canary`
- Uploaded files: `cadqa_artifacts.tar.gz`, `artifact_manifest.json`
- The initial upload was mistakenly placed under the IntersectionQA artifact
  bucket. The files were copied server-side into the CAD-QA bucket above and
  removed from the IntersectionQA bucket path.

Decision: keep this as the first successful RC canary. Do not launch a longer
run until data transport is converted to HF dataset/bucket pull, the stale
remote `HF_TOKEN` is replaced, and the SFT config is tuned for materially higher
A100 utilization.

## Next Command

```bash
rtk uv run python -m scripts.experiments.run_experiment_suite \
  configs/rc_answer_sft_canary_vast.yaml --run answer_sft_rc_canary --with-dependencies --dry-run
```
