# Fine-tuning — training

**Status:** active, 2026-10-09. First of four fine-tuning/evaluation docs: this doc (training),
`data.md`, `system.md`, and `../evaluation/plan.md`.

**This doc owns — how we train the LLM model:** base LLM model and stack choice, cookbook-first
execution, capability preservation, the training stages and optimizer/recipe, hardware/budget and
serving/export, the surviving-code boundary (FT-D12), and training P0/P1/P2.

**The data doc** (`data.md`) owns datasets, mix ratios, contamination/licensing,
training order/curriculum, and the CAD-QA task dataset. **The system doc**
(`system.md`) owns the `TrainingExample` record, its converter, and the
ingest/normalize/quality/dedup/sample stages.

**The evaluation doc** (`../evaluation/plan.md`) owns the LLM harness and modes, the
tool-call contract, the scorer, the evaluation-dataset procedure, grading reconciliation, judge independence,
and baselines.

**Shared interfaces, single-sourced:**

- **Format contract** (Liquid `messages` SFT set and the native tool-call tokens) — owned here.
- **`TrainingExample` + converter** — owned by the system plan.
- **Evaluation-dataset procedure** — owned by the evaluation doc; dataset rows held by the data doc.
- **H1/H2** — owned here; the mixes they test are defined by the data doc.

**Presumed surviving code.** The Phase 3 rewrite is expected to delete most of `train_and_eval/`,
keeping only the rows loader, the typed tool/answer contract, and (probably) the grader (FT-D12).
This plan builds on exactly that surviving code — it does not assume the teacher,
agent-training-trace normalization, SFT, GRPO, evaluation, or vLLM code will be ported.
`tool_calls.py` itself is only partly reusable: its typed definitions/mapper/matcher survive; its
gemma-native rendering and parsing are re-authored.

**Related docs.** `system.md` (the staged post-training loop and the RL-readiness
gate);
`../../prior-art.md` (external evidence, refs [1]–[33]);
`../../PRD.md` (research contract); `decisions.md`
(FT-D* decisions); `../../../plans/oct-8/trust-audit.md` (Phase 0 gate).

---

## 0. For a first-time fine-tuner: the 30-second primer

Fine-tuning continues training a pretrained LLM model on new examples, with a **much smaller** learning
rate and a **much smaller** dataset than pretraining. Two facts drive the training recipe:

1. **You are not teaching the LLM model to think from zero.** A ~2.6B base LLM model already reasons
   and follows instructions to some degree. The recipe *steers* it toward our task shape (CAD-QA
   prompts + `submit_*` tools) and, optionally, a reasoning *style* — it does not build the
   capability.
2. **Everything you train on, the LLM model learns to imitate — including the format and even the
   question text.** If a training example includes the prompt and it is not masked, the LLM model also
   learns to *produce the prompt*, a known cause of over-generation. This is why completion-only loss is
   **verified, not assumed** (`pipeline/04-sft.md`).

The distinction that matters for training (versus evaluation): **SFT scores only to admit an agent training trace
to the dataset and trains by next-token imitation from fixed targets; RL would score as a reward
and train the LLM model on its own generations.** See the evaluation doc §1.

---

## 1. The core bet, stated plainly

`../../prior-art.md` records (refs [1]–[4]) that **base LLM model choice predicts little; the
recipe and the data predict most**, and that small LLM models can be driven to 90–98% on narrow
tool-calling tasks. CAD-QA's recorded "lots of effort, little gain"
(`../../development-context.md`) is therefore most likely a **recipe/data** problem, not a base
problem. So we invest in:

- **Format compliance** (teach the native tool-call format and the `submit_*` contract),
- **Reasoning style** (teach a short, correct hop-by-hop style),
- **Capability preservation** (do not trade general reasoning for CAD-QA format),
- **Evaluation hygiene** (prove the gain is real and is not format compliance alone).

Two predictions this architecture commits to and must test:

- **H1 (format):** a small, curated tool-format + CAD-QA-format mix raises tool-valid rate sharply
  using the cookbook recipe (LoRA, cookbook epochs, prompt-masked).
- **H2 (reasoning):** an external reasoning-distillation + agent training trace mix raises CAD-QA held-out
  accuracy *beyond* what format-only training achieves, without a regression on the general-capability
  evaluation dataset.
- **H3 (transfer):** graph-derived CAD-QA supervision raises accuracy on **existing, credible**
  external benchmarks — **BenchCAD `qa_code`** (primary means, official split), with BenchCAD
  `edit_code` and a text-in text-to-CAD benchmark as end/defect corroboration — *beyond* the Base,
  format-only, and answer-only controls. This is the evidence that the dataset, not only the
  trained LLM model, is useful; without a gain on a credible external benchmark the improvement
  claim rests on an internal split and will not survive review. Suite, arms, and preconditions:
  `../evaluation/plan.md` §5.1 (D-E5).
- **H4 (means → end):** the pass rate an LLM model reaches on the CAD-QA task predicts its
  performance on the independent credible benchmark (FT-D15: the lever is the task environment +
  scorer, not the corpus). Tested as a dose-response at fixed recipe and matched compute, with the
  `preserve_general_math_and_code_reasoning` evaluation dataset as covariate and a non-CAD-QA counter-arm: `../evaluation/plan.md` §5.1 (D-E6).

**Priority.** H3 (headline), H4 (strong mechanism), H2 (core means), H1 (control). The paper presents
them in that order; the experiments run in the dependency order H1 → H4.

If H1 holds and H2 fails, the honest result is "format compliance, not reasoning" — a finding, not
a failure, and it must be reported as such (`../../PRD.md` definition of done, item 3). If H1
and H2 hold but H3 fails, the dataset improves its own split but does not transfer; that is a
recorded finding, and the dataset's usefulness then rests on the benchmark-validity package. The
mixes that test H1 and H2 are defined in the data doc.

---

## 2. Execution strategy: copy the Liquid cookbook first

The biggest risk is not the LLM model or the data — it is that the author has not built a fine-tuning
pipeline before. Mitigate by **copying a working cookbook end to end before changing anything**,
then swapping in CAD-QA data one variable at a time.

Each step below is a gate; do not start the next until the previous passes.

1. **Reproduce the Liquid SFT example verbatim.** Clone `liquid-finetune` (renamed from
   `leap-finetune` on 2026-10-08), `uv sync`, and run its SFT example
   (`job_configs/sft_example.yaml`) on `HuggingFaceTB/smoltalk` **unchanged**. Gate: training
   completes, an adapter is produced, and the standalone eval (`short_answer` metric, vLLM backend)
   writes `results.json`. This proves the toolchain, the GPU path, and the HF/Modal path before
   CAD-QA enters.
2. **Reproduce the Home Assistant loop.** Follow
   `docs.liquid.ai/examples/customize-models/home-assistant`: generate a small synthetic JSONL,
   convert it with the cookbook's `prepare_data.py` to the LFM2 text format, train LoRA for 5
   epochs on a Modal H100 (~$1.50), merge + export GGUF, and re-run its benchmark. The cookbook
   fine-tunes **LFM2.5-350M** as a cheap demo — this is a **pipeline smoke test, not our LLM model**.
   Gate: the benchmark accuracy moves. This proves the whole narrow-task loop
   data → train → merge → export → eval.
3. **Swap in our data (`mixed_dataset_general_and_easy_cadqa`).** Replace the cookbook dataset
   with our first-run rows (general tasks + low-hop `learn_the_cadqa_task`) in Liquid's `messages`
   format (built by the data doc), keep the cookbook config and hyperparameters, and run the
   evaluation doc's `emit_our_tool_call_format` evaluation dataset. Gate: H1.
4. **Only if H1 holds**, expand to `mixed_dataset_full_cadqa_training` and the progressive `learn_the_cadqa_task`.

Rules for the whole effort:

- **Do not write a trainer.** Use `liquid-finetune` configs (`TrainingConfig(extends="DEFAULT_SFT")`,
  `PeftConfig(extends="DEFAULT_LORA")`); override only `model_name` and the dataset path until a
  measured result says otherwise.
- **Do not invent a dataset format.** Consume Liquid's `messages` SFT set. The repo's
  `rows_loader` and `tool_calls` typed contract are the converter's input, not a parallel schema
  (the converter is owned by the data doc).
- **Do not hand-convert checkpoints.** Use the cookbook's merge + GGUF export
  (`finetune/export.py`, `--quant-type q8_0`).
- **Use Modal for the first runs** — it is Liquid's recommended serverless path and the Home
  Assistant run costs ~$1.50. Move to a rented **Vast.ai** 24 GB GPU once the loop is proven and
  hourly cost matters. (Modal + Vast are our only environments; the docs' SLURM/KubeRay backends do not
  apply.)
- **Reference cookbooks:** `github.com/Liquid4All/cookbook`,
  `github.com/Liquid4All/liquid-finetune`, `docs.liquid.ai/lfm/fine-tuning/*` (LEAP Finetune,
  Datasets, TRL, Unsloth), the Home Assistant example, and the Unsloth LFM2.5 tutorial
  (`unsloth.ai/docs/models/tutorials/lfm2.5`).

---

## 3. Capability preservation — "don't screw the LLM model up"

The evidence is blunt: **LoRA does not reliably prevent catastrophic forgetting**, so we design for
it.

| Mechanism | Decision | Why |
|---|---|---|
| **LoRA on a bf16 base, not full FT** | P0 default | matches Liquid's recipe (§5.4); full FT of 2.6B needs ~40GB and is unnecessary at this data scale |
| **Cookbook LoRA hyperparameters** | P0 start | TRL/Liquid example: `r=16`, `lora_alpha=32`, `lora_dropout=0.05`, `target_modules=[q,k,v,o]_proj`; Unsloth adds the MLP projections (`gate/up/down_proj`) and reports better quality on small models — try both |
| **QLoRA only as a fallback** | fallback | needed only to fit <16GB; the Unsloth cookbook uses it (`load_in_4bit=True`), but Liquid's own recipe is LoRA-bf16 and LFM ships bf16 |
| **Completion-only loss** | P0 | fixes the B3 flat-`text` defect; implement it the **cookbook way** — train on the `messages` format and *verify* the loss is completion-only, rather than hand-rolling a masking path |
| **Epochs = the cookbook's, not ours** | P0 | TRL/Liquid example uses 3; the Home Assistant recipe uses 5 on a narrow 350M task; TeichAI used 1 at 4B. Start from the cookbook default, then let the evaluation dataset move it |
| **Cookbook learning rates** | P0 | LoRA `2e-4`, full FT `2e-5`, DPO `5e-7` (TRL/Liquid examples); `bf16=True` |
| **General-task mix (50–70%)** | P0 | xLAM precedent; the diverse general mix anchors prior ability (FT-D18). The general-task rows are a data-doc concern |
| **Gradient checkpointing + grad accumulation** | P0 | fits memory; the cookbook uses `gradient_accumulation_steps=4`, Unsloth uses its optimized checkpointing |
| **Evaluate the datasets before/after each run** | P0 | measure forgetting, do not assume it away; the procedure is the evaluation doc's |
| **KB/activation regularization (EWC, LaLoRA)** | P2 | more moving parts than a first run warrants |
| **Null-Basis LoRA (NB-LoRA)** | P2 | constrained LoRA that preserves RL-acquired reasoning (`arXiv:2609.25618`); only if the evaluation datasets show real loss |
| **Replay buffer / LwF distillation loss** | P2 | stronger forgetting control once the baseline recipe is measured |

**Do-not-do list:** no full fine-tuning at this size; no epoch/LR/rank value we picked ourselves
while the cookbook default is untested; no training on the unmasked flat `text`; no mixing the evaluation
dataset into training; no "Claude-style" reasoning copy at high weight without a filtered set and an
evaluation dataset.

---

## 4. Training stages and contract

Stack-neutral at the contract level (works for `liquid-finetune`, TRL, or Unsloth). The **contract**
is the important artifact here. Pipeline stages 1–5 are owned by the system plan
(`system.md` §7); the evaluation doc owns pipeline stage 9.

```text
[data registry] -> [ingest] -> [normalize] -> [quality gate] -> [dedup/contamination]
      -> [sample/mix] -> [convert to Liquid messages] -> [manifest] -> [train] -> [eval]
       \___________ system plan __________/          \_____ this doc _____/   \_ eval doc _/
```

**The on-disk training artifact is a Liquid `messages` SFT set** — the `messages` schema the cookbook
and `liquid-finetune` validate. `messages` is a **schema, not a container**: the cookbook ships JSONL,
but Parquet loads through HF `datasets` and is preferred (DD-06) — confirm `liquid-finetune` accepts a
Parquet path (open question).

6. **Convert (do not hand-render).** Emit Liquid's `messages` SFT set and let the cookbook /
   `liquid-finetune` apply the chat template and tokenization. The native tool-call spelling is
   base-specific and must be re-derived, never reused (FT-D3; the format churn in
   `../../development-context.md`). For LFM2.5: ChatML-like template (`<|startoftext|>`,
   `<|im_start|>`+role, `<|im_end|>`), tool calls in `<|tool_call_start|>`/`<|tool_call_end|>`, and
   **Pythonic calls by default** — so the `submit_*` answer tools must either be accepted as
   Pythonic or forced to JSON with "Output function calls as JSON" in the system prompt. This
   replaces the hand-rolled render+mask step: completion-only loss is a cookbook/trainer concern to
   **verify**, not a bespoke pipeline to build. See §5.4.
7. **Manifest.** One JSON per run: External dataset revisions, row counts, role weights, seed, exact command,
   template hash, git SHA, checksums (Phase 0 TA-E3).
8. **Train.** Run `liquid-finetune` with the cookbook config and defaults (`DEFAULT_SFT`,
   `DEFAULT_LORA`), overriding only `model_name` and the dataset path until a measured result says otherwise.
   Not a hand-rolled trainer.

---

## 5. Hardware, budget, and the Liquid stack

### 5.1 Sizing (VRAM)

| Method | 2.6B LLM model | Notes |
|---|---|---|
| LoRA (bf16 base) | ~10–14 GB | **Liquid's default and our default** (§5.4); 24 GB comfortable |
| QLoRA (4-bit NF4) | ~6–8 GB | fallback only, to fit a ≤16 GB card at moderate sequence length |
| Full FT | ~40 GB | **not** needed |

Add headroom for activation at the CAD-QA agent training trace length (SFT was `SEQ=6144`,
`pipeline/04-sft.md`) and for longer external reasoning
traces. Use gradient checkpointing and gradient accumulation rather than a bigger card.

### 5.2 Recommendation

- **First runs: Modal** (serverless), following the cookbook; ~$1.50 per Home Assistant-scale run.
- **Primary self-managed:** a single **24 GB card (RTX 4090)** on a spot/on-demand Vast.ai instance
  running **LoRA on the bf16 base**; ~$0.35–0.60/hr.
- **Floor:** a **16 GB RTX 4080S** is sufficient for **QLoRA** at capped sequence length. Note:
  `../../development-context.md` calls it "RTX 4080S 32 GB"; an RTX 4080S has **16 GB**, so
  that figure is wrong and should be corrected as a finding.
- **Headroom (P2):** A100 40 GB for long-context external data.
- Serving/eval bytes are the evaluation doc's concern (vLLM needs its own allocation).
- **Keep the GPU busy (FT-D21).** Use `liquid-finetune`'s `async_eval` (`sidecar`/`reserved`, vLLM) so
  evaluation does not block training, and vLLM rollouts (`colocate`/`server`) so one engine serves
  rollouts and eval. See `../../research/2026-liquid-finetune.md`.

### 5.3 Cost estimate

The dominant cost is **teacher API calls for `learn_the_cadqa_task`** (the data doc's out-of-scope piece, but
it sets the budget). The external mix's ingest/filter/dedup is CPU-only; a LoRA run over ~20–50k
examples is hours on a 4090. Budget GPU by the hour and stop on the evaluation gate.

### 5.4 What Liquid ships (checked 2026-10-08)

Sources: `docs.liquid.ai/examples/customize-models/home-assistant`, `docs.liquid.ai/lfm/key-concepts/{tool-use,chat-template,text-generation-and-prompting}`,
`docs.liquid.ai/lfm/fine-tuning/*`, and the LFM2 LLM model table.

**Recommended stack: LEAP Finetune (`liquid-finetune`)**

- The docs name LEAP Finetune (repo `Liquid4All/liquid-finetune`, formerly `leap-finetune`) as
  Liquid's recommended training stack; it builds on TRL and wraps dataset validation, config
  defaults, evals, distributed launch, checkpointing, and HF/GGUF export.
- Config-first:

  ```python
  JobConfig(project_name, model_name="LFM2.5-1.2B-Instruct", training_type="sft",
      dataset=DatasetConfig(path=..., type="sft", limit=..., test_size=0.1),
      training_config=TrainingConfig(extends="DEFAULT_SFT", num_train_epochs=3, learning_rate=2e-5),
      peft_config=PeftConfig(extends="DEFAULT_LORA", use_peft=True))
  ```

  Run via `run_config(job)` or `liquid-finetune job_configs/sft_example.yaml`.
- Launch: **Modal** (managed, recommended first) or **local CUDA on a rented Vast.ai box** (SSH in
  and run `liquid-finetune` with the instance Python). We have Modal + Vast only; the SLURM and
  KubeRay backends the docs list do not apply.
- Alternatives also shipped: **TRL** (LoRA `r=16`, `lora_alpha=32`, `lora_dropout=0.05`,
  `target_modules=[q,k,v,o]`, `lr=2e-4`, `num_train_epochs=3`, `bf16=True`; full FT `lr=2e-5`; DPO
  `lr=5e-7`, `beta=0.1`) and **Unsloth** (QLoRA `load_in_4bit=True`, `r=16`, includes the MLP
  projections, `use_gradient_checkpointing="unsloth"`).
- Cookbook: `github.com/Liquid4All/cookbook`; the Home Assistant example is the end-to-end template
  (synthetic data → `prepare_data.py` → train → merge/export GGUF → benchmark).

#### Training and precision

- **Plain LoRA, not QLoRA.** The recipe uses LoRA on the base LLM model; it runs **5 epochs on a Modal
  H100** (~$1.50 for the 350M recipe), then **merges the adapter** and converts to GGUF
  (`--quant-type q8_0`).
- **Quantization is an export/serving step, not a training step.**
- **LFM2/LFM2.5 checkpoints ship in `bfloat16`.** No fp4/fp8 default; quantized variants (GGUF
  `Q4_0`/`Q4_K_M`/`Q8_0`, MLX 8-bit, and the Aug-2026 **QAD Q4_0** ~97% of BF16) are separate
  artifacts. Fine-tune the **bf16** checkpoint; do not fine-tune a QAD Q4_0 checkpoint.
- **No MTP/draft training.** LFM2.5 has **no built-in MTP head**; Liquid's separate ~300M
  **DSpark** draft is a serving artifact, and `liquid-finetune`/LEAP does not train it (FT-D22).
  Speculative decoding is lossless and serving-only — it never enters training, the merge, or a
  reported number. Do not add an MTP objective or fit a speculator at this scale.

#### Tool use and chat template (the format contract this doc owns)

- **ChatML-like template**: `<|startoftext|>` … `<|im_start|>` + role + newline … `<|im_end|>`,
  roles `system`/`user`/`assistant`/`tool`; defined in each LLM model's `chat_template.jinja`.
- **Tool calls**: LFM2.5 wraps calls in `<|tool_call_start|>`/`<|tool_call_end|>`; LFM2 also wraps
  tool definitions in `<|tool_list_start|>`/`<|tool_list_end|>` and results in
  `<|tool_response_start|>`/`<|tool_response_end|>`.
- **Calls are Pythonic by default**; JSON requires "Output function calls as JSON" in the system
  prompt. Tools are declared as JSON in the system prompt (recommended) or via
  `.apply_chat_template(tools=...)`.
- **Why this matters:** the provider ships the tool-call format, chat template, prompt settings
  (e.g. LFM2.5-1.2B-Instruct `temperature=0.1`, `top_k=50`, `repetition_penalty=1.05`), and a
  dataset validator. Adopting LFM inherits the format contract instead of hand-rolling it — the
  exact axis where the Aug-2026 gemma work burned effort
  (`../../development-context.md` "Tool-call and answer-submission format churn"). The
  tradeoff is the FT-D11 lock-in: the `submit_*` rendering is authored for these tokens and is not
  portable.

---

## 6. Surviving code boundary (FT-D12)

Phase 3 is expected to delete most of `train_and_eval/`, keeping:

- `rows_loader.py` (loaders), and
- the typed tool/answer contract in `tool_calls.py` (typed definitions, answer-format→tool mapper,
  `tool_call_matches`); its gemma-native rendering/parsing is re-authored, and
- `grading/` (evaluation contract) is a **keep candidate**, owned by the evaluation doc, to be
  reconciled with `tool_call_matches` (TA-A3).

Still unconfirmed: `run_code_sandbox.py` + `eval/`, and the CLI/orchestrator (`cli.py`,
`experiment.py`, `harbor.py`). Deletion is destructive and is done on a branch with the audit as
justification; `dataset/` stays immutable (DD-01). Detail: FT-D12 in
`decisions.md`.

---

## 7. P0 / P1 / P2 (training)

| Item | Tier | Rationale |
|---|---|---|
| Reproduce the Liquid SFT example verbatim (`smoltalk`, Modal) end to end | **P0** | proves the toolchain/GPU/HF path before CAD-QA data; de-risks a first-time pipeline author (§2) |
| Reproduce the Home Assistant loop (synthetic data → train → merge → export → benchmark) | **P0** | proves the full narrow-task loop the cookbook provides |
| Completion-only loss verified on the `messages` format | **P0** | fixes the B3 flat-`text` defect the cookbook way, without hand-rolling masking |
| Re-author the `[answer contract]` / `submit_*` rendering for LFM2.5 native tool tokens | **P0** | base-specific; the exact Aug-2026 failure mode (`../../development-context.md`) |
| Cookbook LoRA recipe (`r=16`, `alpha=32`, `lr=2e-4`, cookbook epochs) on bf16 | **P0** | baseline that does not forget; matches Liquid (§5.4) |
| Merge + GGUF export scripted from the cookbook | **P0** | the current repo has no merge step (FT-D10/TA-D2) |
| DPO / GRPO second training stage | **P2** | FT-D8 ordering, superseded by FT-D13: run GRPO only after the Training stage 2 pass@k gate shows a reachable tier (`system.md`) |
| NB-LoRA / EWC / replay-buffer forgetting control | **P2** | only if the evaluation datasets show real regression |
| Multi-base sweep (Qwen3.5-2B, LFM2.5-2.6B, Llama-3.2-3B) | **P2** | hold recipe fixed; adopting another base leaves the cookbook |

---

## 8. Decisions still to make (training)

1. **Base LLM model.** Cookbook-first means **LFM2.5** — 2.6B as primary, 1.2B for the cheap
   evaluation run. The `../../prior-art.md` shortlist (Qwen3.5-2B, Llama-3.2-3B, Phi-4-mini, Gemma 4 E2B/E4B) is
   deferred to the P2 multi-base sweep.
2. **Fine-tuning stack.** FT-D11 proposes `liquid-finetune` + LFM2.5, and Liquid's docs name LEAP
   Finetune the recommended stack. Recommendation: **adopt `liquid-finetune` and its cookbook
   configs**; the converter stays format-compatible so a stack swap remains possible.
3. **Answer-submission format.** Author the `submit_*` envelope in LFM2.5's native tokens
   (`<|tool_call_start|>`/`<|tool_call_end|>`, Pythonic vs JSON). The gemma `<|tool_call>` rendering
   does not transfer; treat this as P0 (§7).
4. **Modal vs Vast.** Recommendation: Modal for the cookbook reproduction and first runs, then
   a rented **Vast.ai** 24 GB GPU once the loop is proven. (No SLURM/Kubernetes access.)

---

## 9. Open questions (training)

- **Q1.** Does LEAP Finetune / TRL mask the prompt by default for `messages` SFT, or must
  `assistant_only_loss` (or equivalent) be set? Verify on the smoltalk reproduction before trusting
  any CAD-QA number.
- **Q2.** Does the LFM2.5 chat template + LEAP pass a custom `submit_*` tool list through unchanged, and do
  we accept Pythonic calls or force JSON via the system prompt? `[unknown]`.
- **Q3.** LoRA-bf16 is the default (§5.4); does QLoRA change the outcome on the evaluation dataset at this scale? The repo
  `pipeline/04-sft.md` records a code/narrative conflict (4-bit vs 16-bit) from the gemma runs; settle it
  with a measured A/B on the evaluation dataset.
- **Q4.** The §5.4 config snippet sets `learning_rate=2e-5` (the full-FT rate from §3) on a
  `DEFAULT_LORA` run, while the §3 table gives the LoRA rate as `2e-4`. Does `DEFAULT_LORA` override
  the snippet's rate, or is the snippet wrong? `[unknown]`
- **Q5.** H2 (§1) expects an external reasoning-distillation mix to raise CAD-QA accuracy, while FT-D15
  and `system.md` §0 call external general data *support*, not the lever (the task environment + scorer
  is). Reconcile: is the reasoning third a support/anchoring term or a lever for H2? `[open]`

---

## 10. Immediate next step (training)

1. **Run the Liquid SFT example verbatim** (`job_configs/sft_example.yaml` on `smoltalk`, on Modal)
   and its standalone eval. Nothing else starts until this passes.
2. **Reproduce the Home Assistant loop** (350M cookbook demo, synthetic data → train →
   merge/export GGUF → benchmark). This proves the data→train→export→eval path we will actually use.
3. Confirm the FT-D12 boundary (what else survives besides the loader, the typed tool contract, and
   the grader — the last owned by the evaluation doc).
4. Once the data doc delivers the `mixed_dataset_general_and_easy_cadqa` JSONL, run the `emit_our_tool_call_format` evaluation dataset (evaluation doc).
