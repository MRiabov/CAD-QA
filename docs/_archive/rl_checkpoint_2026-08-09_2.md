# RL/SFT Progress — 2026-08-09 (checkpoint 2: format pivot + retrain)

Companion to `docs/rl_progress_2026-08-09.md`. Covers the tool-call-format pivot, the
native-format SFT retrain, the eval/speed blockers, and the open decision.

## The pivot: native gemma tool calling (the real bug)

- The first SFT trained the model to emit an **OpenAI-style JSON envelope**
  (`{"name": ..., "arguments": ...}` in a ```json fence). The base gemma-4-E2B is
  **natively trained** to emit `<|tool_call>call:<name>{args}<tool_call|>` with
  gemma's arg encoding (`<|"|>`-wrapped strings, unquoted keys) — verified by running
  the base weights: it emits the native format, never the envelope.
- The envelope-trained model therefore rambled (did its native thinking phase, never
  transitioned to a tool-call phase), invented tool names (`submit_coordinate_frame`),
  and rarely emitted a parseable call (eval: tool_valid 12-17%).
- **Native tool flow (verified end-to-end on the box):**
  - Prompts: `apply_chat_template(msgs, tools=[7 declarations])` → `<|tool>declaration:...<tool|>`.
  - Assistant: `tool_calls=[{"function": {"name", "arguments"}}]` → `<|tool_call>call:<name>{args}<tool_call|>`.
  - Parsing: `processor.parse_response(raw)` → tool_calls dict (works on the real native
    output, incl. gemma-style args). Gemma4 has a **legacy response_schema** (no
    `response_template`; `prefix=` unsupported).
- **MTP**: exists for Gemma 4 but as separate *inference-time drafter* checkpoints
  (speculative decoding, 1.4-2.2× faster) — NOT a training objective; the E2B safetensors
  repo has no MTP weights. Unsloth Studio enables it automatically.

## Dataset: 268 traces, all ≤4K tokens

- Original 275 traces: **40 were >4K tokens** (mostly 5-hop; compaction in the original
  sampling failed for them and fell back to the originals).
- Policy (user): remove >4K traces; the removed ones get agentic compaction with a
  **≥1K-token floor** (reject oracle-like 377-char summaries) + a ≤4K cap.
- Agentic compaction: deepseek compacts, and if the output is too short/long it is
  **reprompted with its previous output** as context (up to 4 iterations), 48 parallel
  workers. Result: 33 compacted to 1000-1735 tokens (good quality, real step-by-step CAD
  reasoning), 7 dropped. Final: **268 traces** `sft_traces_filtered3.jsonl`
  ({0:50, 1:49, 2:48, 3:74, 5:47}).
- Normalized to gemma-native text: `sft_texts.jsonl` (268, pre-rendered with native
  `<|tool_call>` tokens in the assistant turn; no `<|tool_response>` quirk).
- **Seq length**: measured rendered sequences: p50 2221, p90 4066, max 5822 tokens →
  **SEQ=6144** fits 100% (not 16K — user's point; 16K was RL-era headroom).

## SFT retrain (native format) — COMPLETE

- Config: 268 traces, seq 6144, **per_device_train_batch_size=4, grad_accum=1**
  (eff. batch 4), LoRA rank 32, lr 3e-4, 4 epochs, 268 steps, ~25 min.
- **`loss_type="nll"`** (the code fix): trl 1.9.2 defaults to `chunked_nll` which patches
  the lm-head and breaks on unsloth's functools.partial-wrapped forward
  (`AttributeError: 'partial' has no '__func__'`); disabling the patch made the loss path
  expect `num_valid_tokens` on the model output (second error). `loss_type="nll"` is the
  config-level fix — no reimplementation.
- Result: `SFT_DONE /root/cadqa-sft-final` (adapter + checkpoints). Merged full bf16
  model saved at `/root/cadqa-sft-merged` (10.2GB) for fast inference.

## Blockers (unresolved)

1. **Eval crashes**: `eval_bench.py` died twice. Bug: `parse_native_tool_call` references
   module-level `tokenizer` only defined in `main()`. Also `apply_chat_template` returns a
   bare Tensor for text-only (`.items()` crashes) — handled in the benchmark but the eval
   needs the same guard. **No clean eval number yet** for the new adapter.
2. **Decode speed ~13-19 tok/s** (user reports 50-150 tok/s achievable on this box):
   - unsloth path (bf16): 11 tok/s; `use_cache=True` makes it *worse* (3 tok/s).
   - plain transformers merged, sdpa: 19 tok/s; **FA2 unavailable** (flash-attn package
     missing); unsloth 4-bit test pending.
   - This makes the eval (12 rows × 4096) ~1h and any RL rollout phase impractical at
     scale. Suspected: missing flash-attn / unsloth fast kernels not engaging on this
     stack; yesterday's fast runs likely used 4-bit + unsloth fast kernels.
3. **deepseek teacher success low (23%)** — decomposed: **parsed-but-wrong dominates**
   (hop0: 233 wrong vs 25 format-fail). Not a format bug: temp 1.0 exploration tanks
   accuracy vs the ~60-70% achievable (greedy / lower temp). If re-sampling, use temp
   0.3-0.6.

## Open decision (user's)

- Questioning whether to continue hand-rolling (>24h, no presentable result). Options:
  **Unsloth Studio** (same stack, auto-configured, fast kernels incl. MTP, SFT+GRPO,
  tool-calling support) vs. one clean eval number from the current adapter (~30 min) to
  know where the recipe stands.

## Artifacts / state

- Box 47200188 (4080S) running; `/root/cadqa-sft-final` (adapter), `/root/cadqa-sft-merged`
  (full bf16), `/root/cadqa-bench/` (scripts: sft_train.py, eval_bench.py, normalize_traces.py,
  compact_agentic.py, teacher.py, tool_calls.py, rejection_sample.py).
- Local: `runs/gemma_bench/rl/` mirrors the scripts + data (sft_traces_final.jsonl 275,
  sft_traces_filtered3.jsonl 268, sft_texts.jsonl 268, sampling_log.jsonl).
- HF: `MRiabov/cadqa-rl-2000` v2_curriculum / v3_curriculum / sft_traces_v1.
- git: rl_progress_2026-08-09.md committed earlier; this doc pending commit.

## Operational pitfalls (recurring — track these)

- **pkill self-kill**: `pkill -f "pattern"` matches your own ssh/launch cmdline if it contains the
  pattern. Always bracket (`[e]val_bench`) AND/OR put pkill inside a launch script whose own
  cmdline doesn't contain the pattern (e.g. `bash run_eval2.sh`). Bitten ~6 times.
- **Gemma4Processor.apply_chat_template(tokenize=True, return_tensors="pt")** returns a bare
  `Tensor` for text-only (not a BatchFeature dict) — `inputs.items()` crashes. Guard:
  `if hasattr(inputs, "items") else {"input_ids": inputs.to("cuda")}`.
- **trl 1.9.2 SFTConfig**: `loss_type="nll"` (chunked_nll patches lm-head, breaks on unsloth's
  partial forward AND requires num_valid_tokens output). No `max_seq_length` (use `max_length`),
  no `push_to_hub_token`.
- **gemma-4-E2B tokens**: real eos is `<turn|>`, pad `<pad>`; unsloth defaults `<EOS_TOKEN>/<PAD_TOKEN>`
  are NOT in vocab → force via SFTConfig monkeypatch or explicit eos_token/pad_token.
- **fast_inference=False decode is ~13-19 tok/s** on 4080S for gemma-4-E2B across ALL paths
  (sdpa, unsloth 4-bit; FA2 unavailable). Not a config bug — stack-wide. llama.cpp/GGUF (or
  Studio's fast kernels) is the path to 50-150 tok/s.
- **deepseek-v4-flash**: reasoning in `message.reasoning` (content empty until thinking ends);
  temp 1.0 tanks success to ~23% (parsed-but-wrong dominates) vs ~60-70% at greedy/lower temp.
