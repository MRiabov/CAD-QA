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
