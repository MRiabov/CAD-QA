# 06 — harness modes

## Purpose

Evaluate a trained LLM model on CAD-QA under a selectable **LLM harness mode** that controls which
compute tools the LLM model gets, grading every mode the same way.

## Inputs / outputs

- **In:** a **merged LLM model** directory, the `decoded CAD-QA dataset rows` set (from 01, either a
  local dataset file via `--rows` or HF `v3_curriculum`), and the **LLM harness mode**
  (`--mode no_tools | numpy | cadquery`).
- **Out `eval result`:** JSONL `EvalRow` records
  ([00-overview.md](00-overview.md#eval-result)); the script prints overall accuracy and
  tool-valid rate.
- **Launchers:** `train_and_eval/eval/run_eval2.sh` (12 rows, `numpy`),
  `train_and_eval/eval/run_eval_modes.sh` (`no_tools` and `numpy` in parallel, same seed),
  `train_and_eval/eval/run_sanity.sh` (a fast reward smoke via `sanity_check.py`).

## Requirement

The mode must not change grading — only the available compute tools. A correct final answer
must be accepted identically in every mode; `run_code` must execute the LLM model's code
server-side and feed the result back in the LLM model's native format.

## Current status

`[unverified — needs GPU + merged model]` for the end-to-end loop (no GPU in this audit).
The `run_code` compute tool and its sandbox pass their offline checks in
`train_and_eval/eval/test_tool_calls.py` (extraction, validation, notebook auto-display,
exception, forbidden imports, timeout, no file write). **`cadquery` mode is not
implemented** — `tools_for_mode` raises `NotImplementedError`.

## Verification

```bash
# compute tool + sandbox (offline)
rtk uv run pytest train_and_eval/eval/test_tool_calls.py -k "run_code or execute_code" -q

# full eval (needs GPU + merged model)
bash train_and_eval/eval/run_eval_modes.sh /root/cadqa-sft-merged /root/cadqa-bench/sft_texts.jsonl 12 4
# or single-mode
rtk uv run python train_and_eval/eval/eval_bench.py \
  --model /root/cadqa-sft-merged --max-rows 12 --mode numpy --out eval_heldout.jsonl
```

## Local decisions

### FT-06-D1 — Three modes, one grading path

- **Status:** accepted (2026-08).
- **Context:** `numpy` is the primary harness (no access to CadQuery, plus compute);
  `no_tools` is the pure-reasoning bound; `cadquery` is the full-kernel upper bound.
- **Decision:** `HarnessMode` (`train_and_eval/tool_calls.py::HarnessMode`) selects the tool
  set; `tools_for_mode` returns submit-only for `no_tools` and submit + `run_code` for
  `numpy`; grading always goes through `tool_call_matches`.
- **Consequences:** `no_tools` treats a `run_code` call as a failed attempt
  (`eval_bench.py::main`), not as a served tool. `cadquery` is reserved for the RL stage and
  is not implemented.

### FT-06-D2 — `run_code` round-trip in the native format

- **Status:** accepted (2026-08).
- **Context:** the LLM model emits `<|tool_call>call:run_code{...}<tool_call|>`; the harness must
  execute and return a `<|tool_response|>` block, then continue generation.
- **Decision:** generation is truncated at the first `<tool_call|>` close token (single token
  id `TOOL_CALL_CLOSE_ID = 49`), the code is executed via `execute_code`, and
  `render_tool_response` is appended before continuing (`train_and_eval/eval/eval_bench.py`).
  Identical code snippets are deduped via `resp_cache`.
- **Consequences:** the loop depends on the hardcoded close-token id; see open questions.

### FT-06-D3 — Sandbox is an accidental-misuse guard, not a security boundary

- **Status:** accepted (2026-08).
- **Context:** LLM model-generated code runs in the training pipeline.
- **Decision:** `run_code_sandbox.py` blocks a fixed deny-list of imports, restricts builtins
  (no `open`/`eval`/`exec`/`compile`), strips numpy file-IO, runs under `python -I -B`, and is
  bounded by a timeout. The module docstring states explicitly that a determined attacker can
  still escape a plain subprocess.
- **Consequences:** `run_code` must not be exposed to untrusted input. The isolation claim
  remains `[unverified]`.

### FT-06-D4 — Guard the bare-Tensor `apply_chat_template` return

- **Status:** accepted (2026-08).
- **Context:** `Gemma4Processor.apply_chat_template(tokenize=True, ...)` returns a bare
  `Tensor` for text-only input, not a `dict`; `.items()` crashes.
- **Decision:** guard with `hasattr(inputs, "items")` else treat the returned tensor as `input_ids`
  (`train_and_eval/eval/eval_bench.py::main`).
- **Consequences:** recorded as a recurring pitfall in `docs/_archive/agent_handoff_2026-08-09.md`.

## Open questions

- **`cadquery` mode is unimplemented.** `tools_for_mode` raises `NotImplementedError`; no
  CadQuery execution path exists. The PRD lists it as a P2 upper bound.
- **Sandbox isolation is unproven.** The threat considered is accidental misuse; there is no
  namespace/seccomp isolation, and the sandbox tests assert blocks that a determined actor
  could bypass. Whether "no network / no files / timeout" is sufficient for the claim is
  `[unknown]`.
- **`TOOL_CALL_CLOSE_ID = 49` is a hardcoded single token** "verified on gemma-4-E2B". Any
  tokenizer change silently breaks the loop. `[unknown]` if it is asserted anywhere.
- **Grader divergence from the reward.** Eval grades with `tool_call_matches`; GRPO grades
  with `reward_cadqa` (which has its own fallback parser). The two must agree for eval to
  measure what training optimized. See [05-grpo.md](05-grpo.md#open-questions).
- **Stale launcher.** `train_and_eval/eval/run_eval_heldout.sh` passes `--adapter`, which
  `eval_bench.py` does not accept (it takes `--model`); the script is stale.
- **No per-format / per-hop report.** The script prints only overall accuracy and
  tool-valid; the PRD's metrics (accuracy by hop, format, relation family, measurement scope)
  are not produced here.
- **`MAX_NEW` is defined and unused**; only `ROUND_MAX_NEW` is applied.
- **Held-out sampling.** Rows are drawn by `rng.sample` after excluding agent training trace
  `row_id`s; the exclusion list defaults to a box path (`sft_texts.jsonl`). `[unknown]` if a
  frozen held-out split is enforced independently of the agent training trace set.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- Implement `cadquery` mode and report `no_tools` / `numpy` / `cadquery` side by side.
- Kernel-isolated sandbox (namespaces/seccomp) for a defensible isolation claim.
- Per-format and per-hop metrics output.
