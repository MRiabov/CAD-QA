# Harness

**Status:** `exists` — the local three-mode harness and the Harbor export and
runner are implemented; end-to-end verification is incomplete (per-component
tags under `## Current status`). 2026-10-07.

## Purpose

Run a model closed-book over CAD-QA rows and score exact structured answers,
under a switchable compute mode, both for the local fine-tuned small model and for
cost-effective external models through Harbor.

## Inputs / outputs

Inputs:

- **public row** — the answer-free model input. The canonical field set is
  `cad_qa.dataset.public.PUBLIC_FIELDS` (`cad_qa/dataset/public.py::PUBLIC_FIELDS`):
  `row_id`, `source_id`, `source_code`, `prompt`, `answer_format`, `split`, and
  public metadata (hop counts, difficulty bucket, relation families, measurement
  scopes, prompt version).
- **private row** — the verifier artifacts
  (`cad_qa/dataset/public.py::PRIVATE_FIELDS`): `gold_answer`,
  `query_program`, `candidate_trace`, `clue_map`, `verifier_status`, and the
  answer format. Never exposed to the model.
- **model** — a local checkpoint (the merged small model) for the local harness, or
  an OpenRouter model name for Harbor.
- **harness mode** — one of `numpy`, `no_tools`, `cadquery` (see below).
- **requests** — answer-free request records built by
  `cad_qa/evaluation/requests.py::zero_shot_requests` (and the few-shot variant).

Outputs:

- **local harness** — a per-row JSONL of `EvalRow` records
  (`train_and_eval/eval/eval_bench.py::EvalRow`): gold, parsed correctness,
  tool-validity, the raw completion, the reconstructed tool call, token count, and
  every `run_code` round.
- **Harbor** — the agent's `/app/answer.json` or `/app/answer.txt`, and a verifier
  artifact directory: `cadqa_grade.json` (reward, submission status, full metrics),
  `graded_responses.jsonl`, and `reward.txt`
  (`cad_qa/harbor.py::grade_harbor_answer_files`).

The evaluation harnesses consume the rows artifacts, but the canonical rows IO
contract is not yet written in the new doc tree (`dataset/pipeline/00-overview.md`
is a forward reference), so the field names above are the current source of truth
(see `## Open questions`).

## Requirement

For the evaluation contract to hold, the harness must (1) feed the model only
public information, (2) score answers with the same deterministic grader used to
build the gold labels, and (3) run the base model, the tuned model, and the
recorded baselines on the same rows so the comparison is meaningful. The primary
thesis claim depends specifically on the `numpy` mode and on a grader whose
correctness is established beyond the oracle identity.

## Harness modes

A **harness mode** is which compute tools the model gets. All three modes are
closed-book CAD reasoning: the model may not call CadQuery, OCP, OpenCascade, or
any other CAD kernel, and may not use the network. The mode changes only the
compute surface, not the task or the grading contract.

- **`numpy` (primary, P0).** Submit tools plus the sandboxed `run_code` tool: a
  Python interpreter with NumPy and `math` preloaded. The model reasons in text,
  calls `run_code` to compute exact values, receives the result as a tool response,
  and finally emits a `submit_*` tool call. This is the default mode in the local
  harness (`train_and_eval/eval/eval_bench.py::main`, `HarnessMode.NUMPY`).
- **`no_tools` (P2).** Submit tools only; all arithmetic is internal. A `run_code`
  call is not served and the row is finalized as a failed attempt
  (`train_and_eval/eval/eval_bench.py::main`).
- **`cadquery` (P2, unimplemented).** Submit tools, `run_code`, and CadQuery
  execution. The intent is that one correct CadQuery call suffices. It is not
  implemented: `train_and_eval/eval/eval_bench.py::tools_for_mode` raises
  `NotImplementedError`, and the docstring says it "lands at the RL stage". A
  deterministic per-row CadQuery solution synthesis is planned separately, in the
  `mode3/cadquery-solutions` worktree
  (`.worktrees/mode3-cadquery-solutions/docs/mode3-solution-synthesis-plan.md`).

The tool contract behind all modes is `train_and_eval/tool_calls.py`: a `ToolName`
per answer shape (`submit_label`, `submit_number`, `submit_bbox`, `submit_workplane`,
…), typed Pydantic arguments, and `tool_call_matches` which decides whether a parsed
tool call equals the gold answer. Numeric answers compare at `1e-3` relative
tolerance; `text` also tolerates float-formatting differences in a decomposed
`cq.Plane` string; everything else is exact after whitespace normalization.

The `run_code` execution path is `train_and_eval/tool_calls.py::execute_code`,
which spawns `train_and_eval/run_code_sandbox.py` as an isolated interpreter
(`python -I -B`). The sandbox blocks a set of module imports (including `os`,
`subprocess`, `socket`, and `cadquery`), removes file-I/O and code-execution
builtins, strips NumPy file-IO, and enforces a timeout. Its own docstring states
the threat model explicitly: it is an accidental-misuse guard for
model-generated snippets, **not** a security boundary, because a plain Python
subprocess can still be escaped.

## Harbor

Harbor is the environment and runner used to evaluate cost-effective external
models (`glossary.md`). CAD-QA keeps the graph/query/verifier, the public/private
split, and the grading; Harbor supplies the shell environment and the coding agent.
The mechanics are documented in `docs/_archive/harbor.md`; this section records the
contract.

**How a model is run.** `cad_qa/harbor.py::materialize_harbor_tasks` writes one
Harbor task directory per selected public/private row: `instruction.md`
(the rule-rendered prompt plus the closed-book rules), `task.toml` (metadata,
agent and verifier timeouts), `environment/Dockerfile` (`python:3.11-slim` with
NumPy, pyarrow, PyYAML), `workspace/row_public.json`, `tests/grade_cadqa.py`, the
hidden `expected/private.json`, and a `solution/solve.sh` oracle that writes the
private gold answer. The materializer also writes `cadqa_harbor_job.json` and
`cadqa_harbor_manifest.json`. A run is launched with
`harbor run -c <job config>` (`docs/_archive/harbor.md`). The default job runs the
`terminus-2` agent with the model `openrouter/deepseek/deepseek-v4-flash` in a
local Docker environment, with `daytona` as an alternative. The generated config
pins each OpenRouter model to its native provider (for example `xiaomi` for
Xiaomi Mimo), disables fallbacks, and caps turns and tokens
(`cad_qa/harbor.py::_job_config`).

**How answers are submitted.** The agent must write exactly one of:
`/app/answer.json` containing `{"answer": "...", "confidence": optional_number}`,
or `/app/answer.txt` containing only the answer text. Writing both, or neither,
is a submission error. `cad_qa/harbor.py::_load_submission` classifies the
submission as `ok`, `missing`, `duplicate`, or `invalid`.

**How grading works (public/private).** The verifier script
(`cad_qa/harbor.py::_grade_script`) loads the task's public and private rows,
turns the submission into a single response record, and calls
`cad_qa/evaluation/grade.py::grade_public_private`. That function merges the
answer-free public row with the private gold key by `row_id`, parses the answer
by `answer_format` (`cad_qa/evaluation/parse.py::parse_answer`), and applies exact
match. The verifier writes the scalar reward (1 only for a correct, non-invalid,
parsed answer; 0 otherwise) to `reward.txt` and the full artifact to
`cadqa_grade.json`. The same functions produce accuracy, missing-response rate,
invalid-output rate, by-hop and by-difficulty breakdowns, and optional
confidence-calibration metrics. Harbor's `tests/grade_cadqa.py` is a copy of the
repository grader's parse and grade modules, so the container does not import the
dataset-generation package.

Public/private hygiene is audited in the same layer:
`cad_qa/evaluation/closed_book.py::closed_book_request_audit` fails when a request
leaks a hidden field (`gold_answer`, `query_program`, `candidate_trace`,
`clue_map`, `verifier_status`), when request coverage is incomplete, or when the
request's answer format disagrees with the public row; `closed_book.py` also calls
`cad_qa.dataset.public.public_private_audit` for the row-level split check.
`cad_qa/evaluation/tool_assisted.py::run_tool_assisted_upper_bound` builds
deterministic responses from private verifier artifacts. It is an analysis upper
bound only and is not a model-facing tool environment (`docs/_archive/harbor.md`, "Oracle
Warning").

The local harness and Harbor are two different execution surfaces. The local
harness speaks the native `<|tool_call|>` protocol and grades with
`tool_calls.py::tool_call_matches`; Harbor runs an external coding agent that
writes answer files and grades with `grade_public_private`. Both share the
public/private row contract and the exact-answer principle, but they do not share
a grader implementation.

## Current status

- **Primary `numpy` mode:** `exists`. Implemented and runnable. The local small-model
  runs (handoff, 2026-08-09) used this harness; no `numpy`-mode run is preserved in-repo
  as an experiment record (`[unverified — needs GPU]`).
- **`no_tools` mode:** `exists`. Implemented. The 2026-08-08 bench's h1 slice is a
  different (closed-book, no-tools) runner, not this harness; treat it as an analogue
  only.
- **`cadquery` mode:** `missing`. `tools_for_mode` raises `NotImplementedError`.
- **Harbor export and grading:** `exists`. Materialization, job config, submission
  loading, and per-row grading are implemented (`cad_qa/harbor.py`).
- **Oracle grading path:** `verified`. The oracle baseline reproduces the gold
  answer exactly (accuracy 1.0) on the recorded slices
  (`runs/baseline_smoke/baseline_metrics.json`,
  `runs/cadqa_cadevolve_rc_10_baselines/baseline_metrics.json`).
- **Harbor end-to-end:** `[unverified — needs <env>]`. The recorded big-model
  Harbor numbers are not reproducible from this repository: no live GPU or
  Daytona/Docker run artifacts for them were found in-repo (see `baselines.md`).

## Verification

- Run the local harness on the merged small model, `numpy` mode:
  `python train_and_eval/eval/eval_bench.py --model <merged-checkpoint> --mode numpy --max-rows <n> --out <file>`.
- Run the local harness in `no_tools` and `numpy` modes concurrently:
  `bash train_and_eval/eval/run_eval_modes.sh` (a remote-run script that assumes
  the training-box layout; `cadquery` is reserved for the RL stage).
- Materialize and run Harbor:
  `uv run cadqa harbor materialize --public <public.parquet> --private <private.parquet> --out <dir> --fresh`,
  then `harbor run -c <dir>/cadqa_harbor_job.json`.
- Verify the grader without a model: grade the oracle submission
  (`harbor` `solution/solve.sh` writes `/app/answer.json` from the private key) and
  confirm `reward.txt` is `1`.
- These commands would promote Harbor end-to-end from `[unverified — needs <env>]`
  to `verified` once a run is executed and its artifacts are preserved.

## Local decisions

**D-E1. `numpy` is the primary harness; `no_tools` and `cadquery` are P2.**
Rationale: the dataset's value is geometry reasoning without a CAD kernel, and the
thesis needs one primary, comparable score. Consequence: `numpy` is the mode that
gates claims; the other two are upper-bound studies and are collected under
`## Extra deliverables - P2`.

**D-E2. The local harness and Harbor are separate surfaces sharing the row
contract, not one harness with two backends.** Rationale: the local model speaks
native tool calls, while Harbor runs a general coding agent that writes files; the
two answer protocols differ. Consequence: grading is not literally shared; a
change to one grader must be mirrored deliberately and is an audit item.

**D-E3. The `run_code` sandbox is an accidental-misuse guard, not a security
boundary.** Rationale: a plain Python subprocess cannot isolate a determined
attacker, and the training box cannot provide namespaces. Consequence: `run_code`
must not be exposed to untrusted input; sandbox isolation remains `[unverified]`.

**D-E4. Harbor reward is a scalar 0/1 exact match; diagnostics live in the
artifact.** Rationale: the agent loop consumes a reward, while analysis needs the
full breakdown. Consequence: `reward.txt` is the interface to Harbor; all richer
metrics must be read from `cadqa_grade.json`.

## Open questions

- Does the recorded big-model Harbor run preserve raw trajectories anywhere? Not
  found in-repo; needed to re-verify the 65/63/59 rc10 clean-100 numbers.
- Where does the rows IO contract live once `dataset/pipeline/00-overview.md`
  exists, and will it rename any public/private field used here?
- Should the local harness import the Harbor grader (or the reverse) so the two
  exact-match paths cannot drift? Currently they are independent implementations.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

### `no_tools` baseline matrix
Run the tuned model and cost-effective models in `no_tools` mode and report it as a
strict-reasoning upper bound alongside the primary `numpy` score.

### `cadquery` mode and one-shot solve rate
Implement the CadQuery compute tool and the deterministic per-row gold CadQuery
solutions (the `mode3` worktree plan), then report the fraction of rows solved by a
single correct tool call. This measures CAD-code production and conciseness.

### Verifier parity
Add a test that runs the same submissions through the local `tool_call_matches`
path and the Harbor `grade_public_private` path and asserts identical verdicts on a
shared fixture.
