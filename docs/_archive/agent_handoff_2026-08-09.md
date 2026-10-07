# CAD-QA RL/SFT — Full Agent Handoff — 2026-08-09 ~11:45 IST

Comprehensive context for the next agent. Read the three prior docs too:
`docs/rl_state_2026-08-09_1140.md` (timestamped snapshot), `docs/rl_checkpoint_2026-08-09_2.md`
(second checkpoint + pitfalls), `docs/rl_progress_2026-08-09.md` (first checkpoint).

---

## 1. Project goal

Fine-tune `unsloth/gemma-4-E2B-it` (google gemma-4 "Everything-to-B", ~2.3B active / ~5.1B
total params, bf16 ≈ 10.3 GB) on CAD-QA (multi-hop CadQuery questions) so the model answers
better than the base. The pipeline that emerged:

1. **Teacher rejection sampling** (`deepseek/deepseek-v4-flash` via OpenRouter) → validated
   traces (reasoning + a typed tool-call answer).
2. **SFT** gemma-4-E2B on those traces in **gemma's native tool-calling format**.
3. (Future) GRPO RL on top — NOT done yet.

## 2. Current result (the win)

Native tool-call SFT on 268 traces → held-out eval:

| Eval (12 held-out rows, seed 3407, same setup) | acc | tool_valid |
|---|---|---|
| SFT, broken (non-native envelope) format | 16.7% | 16.7% |
| **SFT, native `<|tool_call>` format** | **50.0%** | **58.3%** |

- Per-row dump: `~/Documents/cadqa_eval_native_sft_12rows.json`.
- Base-model reference (different grading, rough): 30% (0-hop) / 14% (2-5 hop).
- Weak spot: free-text derivation rows (wp-id answers) — ~5/12 emit no tool call yet;
  candidate_label rows (options in prompt) are answered reliably (4/4).

## 3. Why the format was the bug (critical knowledge)

gemma-4-E2B is **natively trained** to emit:
`<|tool_call>call:<name>{args}<tool_call|>` with gemma's arg encoding (`<|"|>`-wrapped
strings, unquoted keys). Verified by running the base weights: it emits this, never an
OpenAI-style envelope. The first SFT taught the model a foreign envelope
(`{"name": ..., "arguments": ...}` in a ```json fence) → it rambled (did its native
thinking phase, never transitioned to the tool-call phase), invented tool names, and
rarely emitted a parseable call. Switching the training data to the native format is what
tripled held-out accuracy.

**Native tool flow (verified end-to-end on the box):**
- Prompts: `processor.apply_chat_template(msgs, tools=[<7 tool declarations>], ...)` →
  renders `<|tool>declaration:name{...}<tool|>` in a system turn.
- Assistant: message with `tool_calls=[{"type":"function","function":{"name","arguments"}}]`
  renders as `<|tool_call>call:<name>{args}<tool_call|>` (TRL does this for free).
- Parsing: `processor.parse_response(raw)` → `{'role':'assistant','tool_calls':[{'function':
  {'name','arguments'}}]}`. Gemma4 has a **legacy response_schema** (NOT a new-style
  response_template): `prefix=` is unsupported; a bare tool-call response parses, a
  reasoning-prefixed response comes back as plain content (so extract the
  `<|tool_call>...</tool_call|>` block first, then parse_response it).
- NOTE: the chat template IGNORES a `thinking` key in assistant messages — reasoning must
  be plain text in content (or use the `<|think|>`/`<|/think|>` tokens manually).

## 4. Dataset state

- **v3_curriculum** (HF `MRiabov/cadqa-rl-2000`, config `v3_curriculum`): 1,445 rows,
  hops {0:100, 1:342, 2:374, 3:291, 5:338} (no 4-hop), all 7 answer formats
  (bbox, candidate_label, coordinate, integer, json, number, text). Golds JSON-encoded
  strings; `logical_hop_count` column.
- **SFT set**: 268 traces (`sft_traces_filtered3.jsonl`, {0:50,1:49,2:48,3:74,5:47}),
  all ≤4K tokens. Built from the 275 original traces: the 40 >4K-token ones were
  agentic-compacted (deepseek, reprompted with previous output if too short/long, floor
  1000 tokens / cap 4096; 33 succeeded, 7 dropped). Reasonable quality (real step-by-step
  CAD reasoning, not oracle summaries).
- **sft_texts.jsonl**: the 268 traces pre-rendered to gemma-native text
  (`normalize_traces.py`). Seq lengths: p50 2221, p90 4066, max 5822 → **SEQ=6144** fits
  100%. This is what the SFT trains on (plain "text" column).
- HF: `sft_traces_v1` config (275 rows, the pre-format-fix set).

## 5. SFT recipe (what worked)

- `train_and_eval/train/sft_train.py` + `run_sft.sh` (on box: `/root/cadqa-bench/`).
- FastVisionModel.from_pretrained(load_in_4bit=False, fast_inference=False) → 16-bit LoRA
  rank 32, seq 6144, **per_device_train_batch_size=4, grad_accum=1** (eff. batch 4),
  lr 3e-4, 4 epochs (268 steps, ~25 min on 4080S).
- **`loss_type="nll"`** is REQUIRED: trl 1.9.2 defaults to `chunked_nll` which patches the
  lm-head and breaks on unsloth's `functools.partial`-wrapped forward (AttributeError:
  'partial' has no '__func__'); disabling the patch breaks the loss path (needs
  `num_valid_tokens` on output). `loss_type="nll"` fixes it — a config var, not a patch.
- Token quirks: gemma-4-E2B real eos=`<turn|>`, pad=`<pad>`; unsloth's `<EOS_TOKEN>`/
  `<PAD_TOKEN>` defaults are NOT in the vocab. Forced via SFTConfig monkeypatch
  (kwargs["eos_token"]="<turn|>", kwargs["pad_token"]="<pad>") in sft_train.py.
- Output: adapter `/root/cadqa-sft-final` + **merged full-bf16 model
  `/root/cadqa-sft-merged`** (10.2 GB; `PeftModel.from_pretrained` on the unsloth-patched
  base → `merge_and_unload()` → `save_pretrained`).

## 6. Eval (set up, paused — ready to run)

- `train_and_eval/eval/eval_bench.py` + `run_eval2.sh` (on box).
- Loads the **merged model** via plain transformers (`AutoModelForCausalLM`,
  attn_implementation="sdpa"), native tool declarations, `parse_response` parsing,
  **BATCH=8**, per-row raw completion + completion_tokens + capped flag logged.
- Usage on box: `bash /root/cadqa-bench/run_eval2.sh` → `eval_heldout.log/jsonl`.
  Arguments: `--model /root/cadqa-sft-merged --exclude-traces sft_texts.jsonl
  --max-rows 12`.
- Caveat: `processor.apply_chat_template(tokenize=True, return_tensors="pt")` returns a
  bare **Tensor** for text-only (not a dict) — guard with
  `hasattr(inputs, "items")` else `{"input_ids": inputs.to("cuda")}`.

## 7. Speed investigation (OPEN — not concluded)

Measured decode ~13-19 tok/s on the 4080S (launch-bound: GPU 17-32% util, CPU dispatch
dominates). All paths measured:

| Path | Result |
|---|---|
| transformers sdpa (merged bf16) | 19 tok/s |
| unsloth 4-bit | 15 tok/s |
| torch.compile (reduce-overhead) | 19 tok/s (no help) |
| FA2 | flash-attn package missing |
| **vLLM 0.26.0** (`/root/vllm-venv`) | engine init FAILS for base AND merged: vLLM's Gemma4 arch expects per-layer `k_norm` (QK-norm) weights; the unsloth checkpoint doesn't expose them |

**vLLM is likely a SERVING/config mismatch, not impossible** (do not declare dead):
- Check the checkpoint's actual weight names (safetensors index) for `k_norm` / how
  unsloth folds QK-norm; check the config's `qk_norm`/`attention_scale` flags vs vLLM's
  Gemma4 implementation.
- vLLM has weight-mapping override hooks; a mapping patch (or a config alignment) may fix
  the load. vLLM 0.26 requires transformers>=5.5.3, torch 2.11+ (installed in the
  isolated `/root/vllm-venv` — keep it isolated; the RL venv is the unsloth stack).
- If vLLM stays blocked: **llama.cpp/GGUF** (GGUF conversion of the merged model; unsloth
  MTP docs show gemma-4 at 50-150 tok/s there) or install flash-attn (uncertain 2-4×).
- vLLM batches natively (continuous batching) — the right tool for eval + RL rollouts.

## 8. Teacher / data pipeline knowledge

- `deepseek/deepseek-v4-flash` on OpenRouter: reasoning arrives in `message.reasoning`
  (content stays empty until thinking ends — an "empty completion" usually means the
  budget ran out mid-think, NOT a bug). Currently $0/M (balance $160+).
- Success rate at temp 1.0 was ~23% per attempt (parsed-but-wrong dominated → the model
  reasons wrong, not a format issue); ~60-70% achievable at temp 0.3-0.6. If re-sampling,
  use lower temperature.
- Teacher client: `train_and_eval/teacher.py` (handles `message.reasoning`, native
  `tool_calls` responses, per-call cost). Sampler: `train/rejection_sample.py`
  (per-hop quotas, incremental checkpoints). Compaction: `train/compact_agentic.py`.
- Typed tool contract: `train_and_eval/tool_calls.py` — 7 answer tools
  (submit_label/text/integer/number/coordinate/bbox/workplane) + compact_trace; exact
  strings/ints, 1e-3 relative floats; `parse_response`-style native parsing lives in the
  eval.

## 9. Box / environment state

- Vast instance **47200188**: RTX 4080S 32 GB, SSH `root@175.155.64.174 -p 19599` (key
  `~/.ssh/vastai_wireseghr`), ~$0.227/h, running.
- `/root/cadqa-rl-venv` — canonical Unsloth E2B-RL stack: unsloth git-main (2026.8.9),
  trl 1.9.2, transformers 5.14.1, torch 2.12.1+cu130, no vLLM. Build: `notebook_env.sh`.
- `/root/vllm-venv` — vllm 0.26.0 + transformers>=5.5.3 (for the speed test).
- `/root/cadqa-sft-final` (adapter), `/root/cadqa-sft-merged` (merged bf16).
- Box scripts in `/root/cadqa-bench/` (older copies; local `train_and_eval/` is the
  source of truth — sync before major changes). `.env` (OpenRouter key) is on the box.
- The old 5070 Ti box and the throwaway 2080 Ti are gone/stopped. The 2080 Ti instance
  (47213088) is stopped (can restart for CPU materialization).

## 10. Repo layout (all committed)

```
train_and_eval/
  tool_calls.py, teacher.py, reward_cadqa.py   # shared modules (imported via sys.path shim)
  train/    grpo_train.py, sft_train.py, rejection_sample.py, compact_agentic.py,
            normalize_traces.py, export_rl_data.py, gen_1hop_queries.py, run_sft.sh,
            run_grpo_*.sh, probe_4090.sh
  eval/     eval_bench.py, sanity_check.py, test_tool_calls.py, bench_vllm.py, run_eval2.sh,
            run_eval_heldout.sh, run_bench_vllm.sh, run_sanity.sh
  setup/    notebook_env.sh, setup_rl_venv.sh, rebuild_rl_venv.sh, 40xx_setup.sh,
            drop_vllm.sh, finalize_rl.sh
docs/       rl_state_2026-08-09_1140.md, rl_checkpoint_2026-08-09_2.md,
            rl_progress_2026-08-09.md, rl_checkpoint_2026-08-08.md
runs/gemma_bench/rl/   # data artifacts only (gitignored): sft_traces_*.jsonl, sampling_log.jsonl, etc.
```

Commit history (recent): `b00aceb` move-to-train_and_eval → `56aa127` organize →
`fe81699` straggler → `91c1da9` state snapshot.

## 11. Operational pitfalls (recurring — track these)

- **pkill self-kill**: `pkill -f "x"` matches your own ssh/launcher cmdline if it contains
  "x". Always bracket (`[e]val_bench`) AND/OR put pkill inside a launch script whose own
  cmdline is clean (`bash run_eval2.sh`). Bitten ~8 times.
- **Gemma4Processor returns a bare Tensor** from apply_chat_template(text-only) — guard
  `.items()`.
- **trl 1.9.2**: `loss_type="nll"`, `max_length` (not `max_seq_length`), no
  `push_to_hub_token`; eos/pad quirks (section 5).
- **Long-run job monitoring**: launch with `setsid nohup ... < /dev/null &`; use a
  background watcher that polls every ~4-5 min and writes to a file; do NOT sleep-poll in
  the foreground (tool has a 2-min cap).
- **setsid/nohup through the tool**: the tool wrapper may report
  "WaitDelay expired before I/O complete" — the process usually still runs; verify with
  `pgrep`.
- **Vast CLI**: use the JSON query via the API key at
  `~/.config/vastai/vast_api_key` (the CLI mangles quoted JSON); `vastai ssh-url <id>` for
  the direct endpoint; instances can be slow to provision (big image pulls).

## 12. Recommended next steps

1. **Decide if 50% is the SFT win** (recommend yes) — optionally scale the eval to the
   full 1,214 held-out rows at BATCH=8 for a tighter number.
2. **Fix the vLLM load** (k_norm/weight-mapping check) OR go llama.cpp/GGUF — unlocks fast
   rollouts for RL.
3. **RL on top** (GRPO, curriculum 0→1→2→3→5, tool-call reward using parse_response-style
   extraction) — the original project goal; the earlier GRPO attempt collapsed at the
   2-hop cliff (entropy death) and needs the 1-hop bridge + reward shaping (see
   `docs/rl_checkpoint_2026-08-08.md`).
4. Long-term: re-sample the teacher at temp 0.3-0.6 for higher-quality traces; consider
   MTP GGUF for deployment-speed inference (Gemma 4 MTP = inference-time drafter, not a
   training objective).

---

# ADDENDUM 2026-08-09 ~14:45 IST — current state + the compute-tool task

Everything above (sections 1-12) is still valid context. This addendum records what
changed after ~11:45 and defines the task for the next agent. Read the prior sections
first; this is the live state.

## A. What changed since the original handoff

### A1. Text-gold encoding fix (landed, `ea549b0`-era, parallel agent)
- `v3_curriculum` + `v2_curriculum` parquets re-uploaded to HF with normalized text golds:
  0 JSON-quoted (`"wp19"` → `wp19`) and 0 `_center`-suffixed (node-id leak `wp16_center` →
  `wp16`). Old versions recoverable; same config names/schema.
- Pipeline guard: `assert_text_golds_clean` raises at dataset load in
  `rejection_sample.py`, `eval_bench.py`, `grpo_train.py`, `sft_train.py`,
  `normalize_traces.py` — if you see it fire, the HF cache is stale (delete
  `~/.cache/huggingface/datasets/MRiabov___cadqa-rl-2000/`), do NOT remove the guard.
- The 22 previously-invalid center rows (exact row_ids, family
  `argmin/argmax_origin_z_workplane`, hop 1, text format):
  `docs/center_rows_invalid_gold_2026-08-09.md` (committed `a92479e`).

### A2. Targeted center-row re-sampling → merged pool 308 → HF `sft_traces_v2`
- `rejection_sample.py` gained `--only-rows <ids.txt> --target-count N` (committed).
- Ran on the 22 center rows: 33 validated traces (20 unique rows, hop-1, all
  `submit_text`, gold-matched against the FIXED golds).
- Merged pool `sft_traces_merged.jsonl`: **308 traces**, per-hop
  {0:50, 1:83, 2:50, 3:75, 5:50}, 251 unique row_ids (54 rows appear 2-3× — separate
  generations, all gold-validated). Pushed to HF as **`sft_traces_v2`** config
  (`train_and_eval/setup/publish_traces.py`, committed `9a6f11f`).
- Per-trace preview markdowns (row prompt + model output): **`docs/trace_previews/`**
  (308 files, tracked).

### A3. Post-fix eval + train/test distribution analysis
- Re-ran the 12-row held-out eval on the fixed dataset: **acc 41.7% (5/12),
  tool_valid 75% (9/12)** (was 50%/58.3% pre-fix — movement is ±1-2 rows of noise).
- **Train/test match analysis (do NOT skip this):**
  - Row overlap eval vs train pool: **0** (exclusion works).
  - Hop mix: eval flat {0:2,1:2,2:2,3:3,5:3} vs train {50,83,50,75,50} — eval slightly
    harder (over-weights hop-5, under-weights hop-1).
  - **Format mismatch — the critical finding.** deepseek per-format success
    (from `sampling_log.jsonl`, 1340 attempts): text 23%, candidate_label 42%,
    coordinate 23%, integer 35%, bbox 19%, **json 0% (0/113), number 0% (0/71)**.
    → The training pool has **ZERO json and ZERO number traces**; the eval sampled a
    `number` row (guaranteed fail, and it failed). The model cannot learn formats the
    teacher can never produce. **This is the task below.**

### A4. vLLM SOLVED (was "open" in section 7)
- vLLM 0.26.0 in `/root/vllm-venv` now **loads and serves the merged model at
  121-871 tok/s** (vs 19 tok/s transformers) with:
  1. Weight rename `model.language_model.*` → `language_model.model.*`
     (`train_and_eval/setup/convert_for_vllm.py`, committed `b062ca1`).
  2. Shared-layer `k_norm` duplication: layers 15-34 get `k_norm[layer % 15]` (gemma-4
     KV-sharing, `num_kv_shared_layers=20`, 35 layers → 15 unique).
  3. `VLLM_ATTENTION_BACKEND=TORCH_SDPA` (flashinfer can't compile: needed `curand.h`/
     `curand_kernel.h`, fixed by `apt-get install libcurand-dev-12-6` + symlink into
     `/usr/local/cuda/include/`).
- Converted checkpoint: `/root/cadqa-sft-merged-vllm3`. Benchmark script pattern:
  use `llm.chat(messages)` (NOT raw strings — raw prompts produce EOS-immediately,
  fake numbers).
- Use vLLM for all future batched evals/rollouts.

### A5. LLM-output recording rule (user standing instruction, committed `21cbf3b`)
- Every LLM call's outputs must be persisted — record **reasoning + output text +
  tool call** distinctly. Implemented: sampler `AttemptLog` (→ `sampling_log.jsonl`),
  eval `EvalRow.tool_call` (→ eval jsonl). Carry this into any new rollout logging.

### A6. Hygiene rule (user standing instruction)
- **No new python in `runs/`** (gitignored — data-loss risk). All code lives in
  tracked `train_and_eval/`; data/artifacts go to HF or tracked `docs/`.
- Durable storage done: traces → HF `sft_traces_v2`; previews → `docs/trace_previews/`.

### A7. SFT v2 (in flight at write time)
- Training **NOW**: 308 traces, seq 6144, bs 4, grad_accum 1, lr 3e-4, 4 epochs
  (~308 steps, ~9.5s/it → ~45-50 min total). Adapter out: `/root/cadqa-sft-v2`.
  Recipe identical to the 50% run (loss_type="nll", eos `<turn|>`, pad `<pad>`).
- Compute-bound (GPU 100%, ~280W) — bs 8 gains only ~10%; do NOT restart for speed.
- After it finishes: merge → eval with `run_eval2.sh` (12 rows) for the updated number.

## B. THE TASK — numpy compute tool in the harness

**Goal:** stop running the harness as pure internal reasoning. Add a sandboxed
python/numpy compute tool so the model can *compute* exact values (frames, volumes)
instead of deriving them mentally. This is expected to rescue the **json** (0/113) and
**number** (0/71) formats — the two with zero training traces — and improve bbox/text.

**User-approved scope:** **numpy/python sandbox NOW; cadquery execution at the RL
stage** (do not add cadquery to the sandbox yet — it would trivialize the task).

### Why (evidence)
- Harness today = 7 submit-only tools + compact_trace. **No compute tool.** Native
  format has no `<|tool_response|>` round-trip (normalize_traces.py comment says so
  deliberately). gemma-4-E2B is literally the E2B (code-execution) model — we're
  running it without its native capability.
- `submit_workplane` requires exact `origin/x_dir/normal` (6 floats, 1e-3 rel) from the
  script's frame chain — mechanical but exact; `submit_number` requires exact volume
  arithmetic. Neither is doable in-head reliably → teacher 0%.

### Design (concrete)
1. **`run_code(code: str) -> str`** tool in `train_and_eval/tool_calls.py` (new
   `ToolName.RUN_CODE`). Sandbox: subprocess python, numpy preloaded, strict timeout
   (~5-10 s), no network, no cadquery (per scope), capture stdout/stderr/exception.
   Server-side execution — the "result" is the tool response.
2. **Teacher harness** (`teacher.py`/`rejection_sample.py`): allow multi-turn
   reasoning: user prompt → assistant reasoning + `run_code` call → (server runs it) →
   tool result injected → assistant continues → `submit_*`. The trace captures the full
   loop. (OpenRouter supports tool-call round-trips; deepseek responds to tool results.)
3. **Native trace format** (`normalize_traces.py`): render the round-trip as
   `<|tool_call>call:run_code{...}<tool_call|>` + `<|tool_response|>...<tool_response|>`
   + subsequent reasoning + final submit. VERIFY the exact gemma-4 token spellings on
   the box with the base model before committing to a format (section 3 of this doc:
   the native flow is verified only for the one-shot case).
4. **Re-sample json + number** with the compute tool (targeted: v3 has 16 json + 16
   number rows; use `--only-rows` with the full json+number row_id list, generous
   attempts, maybe temp 0.3-0.6). Validate with existing `tool_call_matches`.
5. **SFT** on the enriched traces (recipe unchanged; seq cap 6144 still fits if the
   round-trip is bounded — re-measure seq lengths after re-rendering).
6. **Eval**: give the student the same `run_code` tool (native declarations + server
   execution in `eval_bench.py`), re-run the 12-row eval and report per-format.

### Files to touch (tracked only)
- `train_and_eval/tool_calls.py` (RUN_CODE schema, extraction, sandbox)
- `train_and_eval/teacher.py` (multi-turn tool loop)
- `train_and_eval/train/rejection_sample.py` (tool-result capture in trace)
- `train_and_eval/train/normalize_traces.py` (`<|tool_response|>` rendering)
- `train_and_eval/eval/eval_bench.py` (compute tool at inference)
- `train_and_eval/setup/publish_traces.py` (publish enriched pool as `sft_traces_v3`)

### Success criteria
- deepseek produces ≥1 validated json trace AND ≥1 validated number trace (both 0%
  today); per-format eval shows json/number > 0 with the tool enabled; no regression on
  the other formats; all LLM outputs recorded per A5.

### Guard rails / pitfalls (from sections 7-11 + A)
- `loss_type="nll"`, eos/pad quirks — unchanged recipe.
- Sandbox security: subprocess isolation, no network, timeout, no cadquery (RL stage).
- Record every run_code call + result (A5 rule).
- Sync box `/root/cadqa-bench/` from local `train_and_eval/` before running anything
  (box copies are stale); `.env` (OpenRouter key) lives on the box at
  `/root/cadqa-bench/.env`.
- If the gemma native tool-response format fights you, fall back to embedding the tool
  result as plain text in the assistant content (still a compute-capable trace), and
  note the deviation.
- Cost: deepseek is $0/M (balance $160); sandbox is free. Time: re-sampling json+number
  at 0%→20-40% teacher success will take 100-400 attempts (~1-3 h at 24 workers).

## C. Live state pointers (at write time)

- **git HEAD:** `21cbf3b` (recording rule); working tree clean except `.worktrees/`.
- **HF `MRiabov/cadqa-rl-2000` configs:** `v2_curriculum`, `v3_curriculum`,
  `sft_traces_v1` (275), `sft_traces_v2` (308).
- **Box 47200188** (4080S 32 GB): `/root/cadqa-bench/` (scripts+data), venvs
  `/root/cadqa-rl-venv` (unsloth stack) and `/root/vllm-venv` (vllm 0.26, working).
  Checkpoints: `/root/cadqa-sft-final` (adapter), `/root/cadqa-sft-merged` (bf16),
  `/root/cadqa-sft-merged-vllm3` (vLLM-ready), `/root/cadqa-sft-v2` (training NOW).
- **Eval inputs:** `sft_texts_v2.jsonl` (308, normalized), `eval_heldout.jsonl`
  (12 rows, 41.7%).
