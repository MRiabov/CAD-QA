# Step-9 evaluation: no-kernel versus CadQuery harness

Date: 2026-10-22 · Status: completed for one LLM model. The `numpy` primary arm and the
multi-LLM-model panel are not run.

## Purpose

Measure how well a current model answers the re-specified dataset's step-9 tasks under
two realistic settings:

- **no-kernel**: the LLM model sees the program and task, reasons internally, and submits a
  value. This is the P0 setting (no CadQuery).
- **CadQuery**: the LLM model may run Python after the program with CadQuery available, inspect
  the shape, and then submit the answer. This is the realistic agent setting and the upper
  bound for the no-kernel claim.

The tasks are the 60 step-9 tasks produced by the CadQuery-query scratch. They are
above-release tasks and use aggregation clues heavily, so this is a stress test, not a
release-level estimate.

## Setup

- LLM model: `deepseek/deepseek-v4.1-flash-1017` through Merge Gateway.
- Tasks: 60 at task reasoning step count 9, from
  `runs/cq_query_scratch_20261022/tasks.jsonl`; programs and facts from
  `runs/cq_query_scratch_20261022/extraction/facts.jsonl`.
- Prompts: the CadQuery-query task text re-rendered for a direct answer
  (`experiments/old/new_dataset_eval_scratch/prompts.yaml`), with variable names removed from
  task clues. The program text is unchanged.
- Answer formats: 33 number, 15 3D coordinate, 12 integer.
- Answer meanings: 22 distance, 15 position, 12 count, 6 length, 5 area.
- Task targets: 25 edge, 12 face, 12 scalar value, 11 vertex.
- Temperature 0, top-p 1.0. One sample per task. Cost is reported by Merge.
- **no-kernel:** one 64k-token turn; no tools except `submit_answer`.
- **CadQuery:** `submit_answer` plus `run_code`, which executes Python after the program
  in the same namespace with CadQuery; up to 8 compute calls, then a forced submit turn.
- Grading: numeric answers at `1e-3` relative with `1e-6` absolute fallback; integer exact;
  coordinates per component. A missing submission is `no_tool_call`, not a wrong answer.

## Results

| Arm | Correct | Accuracy | Wrong | No submission | Cost |
|---|---|---|---|---|---|
| no-kernel, 64k | 36/60 | 60.0% | 3 | 21 | $1.46 |
| CadQuery | 53/60 | **88.3%** | 7 | 0 | $0.29 |

CadQuery access adds **28.3 percentage points** and removes the submission failures. The
no-kernel arm also hit the 64k output limit on 21 tasks; those are budget failures, not
wrong answers.

### CadQuery accuracy by dimension

| Dimension | Value | Tasks | Correct | Accuracy |
|---|---|---|---|---|
| Task target | edge | 25 | 22 | 88.0% |
| Task target | face | 12 | 9 | 75.0% |
| Task target | scalar value | 12 | 11 | 91.7% |
| Task target | vertex | 11 | 11 | 100.0% |
| Answer meaning | area | 5 | 4 | 80.0% |
| Answer meaning | count | 12 | 11 | 91.7% |
| Answer meaning | distance | 22 | 20 | 90.9% |
| Answer meaning | length | 6 | 4 | 66.7% |
| Answer meaning | position | 15 | 14 | 93.3% |
| Answer format | 3D coordinate | 15 | 14 | 93.3% |
| Answer format | integer | 12 | 11 | 91.7% |
| Answer format | number | 33 | 28 | 84.8% |

The weakest cells are **face** targets (75%), **length** answers (66.7%), and tasks
containing **provenance** clues (78.3%). Count, position, and vertex tasks are at or near
90–100%.

### no-kernel accuracy by dimension

The no-kernel arm is much weaker on scalar-value and count tasks: scalar value 33.3%,
count 33.3%, face 66.7%, edge 68.0%, vertex 63.6%. The 21 non-submissions are concentrated
in count, face-area, and position tasks.

### Literal matches

Nine number tasks have a gold value that appears as a numeric literal in the prompt. The
CadQuery arm scored 7/9 on them and 46/51 (90.2%) on the 51 tasks without a literal match,
so the literal matches do not explain the result. Integer counts are not flagged because
small integers appear throughout the programs.

## CadQuery failures

Seven tasks were wrong:

| Task | Target | Meaning | LLM model answer | Gold |
|---|---|---|---|---|
| `cqt_8f456e38bde46971` | face | distance | 119.1426 | 165.6766 |
| `cqt_71970c36c940c47d` | edge | length | 194.0 | 200.0 |
| `cqt_a4519cf8fb5e15b5` | face | area | 1023.0 | 12.0 |
| `cqt_821fed67fea44318` | scalar value | count | 3 | 2 |
| `cqt_edd0e5aa3dca7fe4` | edge | length | 13.5 | 20.0744 |
| `cqt_fe39c658482d3dbe` | edge | distance | 24.0 | 100.0 |
| `cqt_b0f776c2aa454873` | face | position | (-100.0, 0.0, 0.0) | (0.0, -12.27, 0.5) |

The failures are entity-selection and interpretation errors, not CadQuery API errors. The
LLM model could execute the kernel and still picked the wrong face, edge, or reference.

## Interpretation

- **The query-task result does not transfer to the no-kernel answer task.** The CadQuery-query
  scratch solved 56/60 step-9 tasks (93.3%) with an agentic kernel loop. The no-kernel answer
  task solved 36/60 (60.0%) and failed to submit 21 tasks within 64k output tokens.
- **Kernel access recovers most of the gap.** The CadQuery arm reaches 88.3%, close to the
  query-task result. The remaining 7 failures are comprehension/entity-selection errors.
- **Step 9 is not "basically solved" without a kernel.** It is close to solved with a kernel.
  This supports the view that the no-kernel setting measures something real, and that a
  kernel-assisted setting is a useful realistic upper bound.

## Limitations

- One LLM model and one sample per task. The per-cell counts are small.
- The 60 step-9 tasks are above the first-release range and use P1 aggregation clues. They
  are a stress test, not release composition.
- The `numpy` primary arm was not run; the no-kernel arm is the stricter diagnostic.
- The no-kernel arm hit the 64k output limit on 21 tasks. A larger output budget or a
  different reasoning budget could change that arm, but it would not change the CadQuery
  result.
- The CadQuery harness uses process isolation, not a security sandbox. It is acceptable for
  a hosted model in a scratch run.
- Nine number tasks have a numeric literal equal to the gold value in the prompt. They are
  reported separately.
- The CadQuery arm's `run_code` calls are throttled to four concurrent kernel children;
  wall-clock time is not a benchmark.

## Artifacts

- CadQuery: `runs/new_dataset_step9_eval_64k_20261022/deepseek__deepseek-v4.1-flash-1017__cadquery/`
- no-kernel: `runs/new_dataset_step9_eval_64k_20261022/deepseek__deepseek-v4.1-flash-1017/`
- Review page: `runs/new_dataset_step9_eval_64k_20261022/review.html`
- Code: `experiments/old/new_dataset_eval_scratch/`
- Plan: `plans/oct-22/new-dataset-eval-scratch-experiment.md`

## Next steps

1. Run the `numpy` primary arm on the same 60 tasks.
2. Add one or two more LLM models to the panel.
3. If step 9 is the release ceiling, run the same protocol at step counts 1, 3, 5, and 7
   to locate the no-kernel failure curve.
