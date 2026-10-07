# 05 — GRPO

## Purpose

Post-train the **base model** with GRPO on the **rows artifact**, scoring sampled
completions against the **gold answer** with an exact-match **reward**.

## Inputs / outputs

- **In:** `harness row` (from 01) — either HF `v2_curriculum` (default, `CADQA_RL_ROWS`
  rows) or a local rows artifact via `CADQA_RL_DATA`
  (`train_and_eval/train/grpo_train.py`). Each row contributes `prompt` as chat messages,
  `gold_answer`, `answer_format`, `row_id`.
- **Out:** an RL LoRA adapter at `CADQA_RL_OUT` (saved by `model.save_pretrained`).
- **Config knobs (env):** `CADQA_RL_ROWS` (512), `CADQA_RL_STEPS` (60), `CADQA_RL_GEN` (2),
  `CADQA_RL_BS` (1), `CADQA_RL_OUT`, `CADQA_RL_LOSS` (`bnpo`), `CADQA_RL_SEQ` (16384),
  `CADQA_RL_MAXCOMP` (8192), `CADQA_RL_HOP_SHARES`, `CADQA_RL_DATA`.

## Requirement

The reward must be a faithful verifier-derived score and the policy must not collapse: if
the reward accepts wrong answers, or the policy's entropy dies, the RL phase does not
produce a better model and no RL claim is admissible. Provenance: every reward and rollout
must be reconstructable.

## Current status

`[unverified — needs GPU + unsloth/trl]`. Reward grading is unit-verified
(`train_and_eval/eval/test_tool_calls.py::test_reward_tool_call_native`,
`test_reward_envelope_and_fallback`); the GRPO training loop was not run in this audit.
Historically the first GRPO run **collapsed** at the 2-hop cliff
(`docs/_archive/rl_checkpoint_2026-08-08.md`): 0-hop reward reached 1.0 but entropy ≈ 0 and
completions shrank to 2 tokens; the hop-2 stage then had reward 0 and
`frac_reward_zero_std=1`.

## Verification

```bash
# reward grading (offline)
rtk uv run pytest train_and_eval/eval/test_tool_calls.py -k reward -q

# smoke: 1 step on the box
bash train_and_eval/train/run_grpo_test.sh          # 8 rows, 1 step
# or targeted
CADQA_RL_ROWS=16 CADQA_RL_STEPS=2 CADQA_RL_OUT=/tmp/rl rtk uv run python train_and_eval/train/grpo_train.py
```

A collapse check (entropy, `mean_len`, `frac_reward_zero_std`, reward per hop) is not
automated; `[unknown]` whether it should be a gate.

## Local decisions

### FT-05-D1 — 16-bit LoRA with Unsloth inference, no vLLM in the loop

- **Status:** accepted (2026-08).
- **Context:** vLLM could not load gemma-4 at the time of the run; the official Unsloth E2B
  RL notebook is the reference.
- **Decision:** `FastVisionModel.from_pretrained(load_in_4bit=False, fast_inference=False)`,
  LoRA rank 32 / alpha 64, `loss_type` default `bnpo`
  (`train_and_eval/train/grpo_train.py`).
- **Consequences:** rollouts are slow (the speed investigation is recorded in
  `docs/_archive/rl_state_2026-08-09_1140.md`).

### FT-05-D2 — Exact-match reward, tool-call aware

- **Status:** accepted (2026-08).
- **Context:** the reward must mirror the verifier, not a model.
- **Decision:** `reward_cadqa` first tries the typed tool call
  (`_tool_call_reward` → `tool_call_matches`); if the completion is not a tool call it falls
  back to a per-format parser (`_reward_one`). Batch API:
  `reward_cadqa(completions, **kwargs)` reading `gold_answer` and `answer_format`.
- **Consequences:** a completion can still score via the fallback; the fallback is looser
  than the tool matcher (see open questions).

### FT-05-D3 — Hop-ascending curriculum

- **Status:** accepted (2026-08).
- **Context:** difficulty spans hop count; a 0→…→5 ladder was intended to avoid the cliff.
- **Decision:** rows are bucketed by `logical_hop_count`, shuffled within a bucket, and
  allocated steps by `HOP_SHARES` (default `{"0":0.25,"2":0.10,"3":0.15,"4":0.25,"5":0.25}`
  in the code); the dataset order is fixed and trainer shuffling is off.
- **Consequences:** the schedule encodes a hop distribution that differs from the teacher's
  quota set and from v3; see open questions.

### FT-05-D4 — Truncated completions are masked from the loss

- **Status:** accepted (2026-08).
- **Decision:** `mask_truncated_completions=True`, `max_completion_length=8192`.
- **Consequences:** a completion that never emits a tool call inside the budget contributes
  no reward signal.

## Open questions

- **Entropy collapse history.** The first run died at 2-hop (entropy ≈ 1e-5). Mitigations
  named in `docs/_archive/rl_checkpoint_2026-08-08.md` (reward shaping/partial credit, entropy term,
  higher KL, the 1-hop bridge) were not all landed. Whether the current config avoids it is
  unverified.
- **Reward is sparse and unshaped.** Binary exact match with no partial credit is the
  recorded cause of shortcut learning; no shaping exists in the code.
- **Curriculum mismatch.** `HOP_SHARES` omits hop `1` and includes hop `4`; the v3 dataset
  has `{0,1,2,3,5}` and the handoff describes a "0→1→2→3→5 ladder". The code's default is
  v2 (`{0,2,3,4,5}`). One of code or intent must change.
- **GRPO does not start from the SFT adapter.** `grpo_train.py` loads
  `unsloth/gemma-4-E2B-it`, not the SFT checkpoint; "SFT then GRPO" is not implemented.
- **Grader divergence.** The reward source says it "mirrors cad_qa evaluation
  grade_public_private", but the parser is self-contained (`reward_cadqa._parse_answer`).
  The eval grader uses the typed matcher (`eval_bench.py` → `tool_call_matches`), so eval and
  reward can disagree, especially via the `text` substring fallback
  (`_reward_one`: `gold_str in pred`) and number tolerance (`1e-6` absolute in the reward vs
  `1e-3` relative in `tool_call_matches`).
- **`boolean` format.** `reward_cadqa._parse_answer`/`_reward_one` handle `boolean`, but the
  typed contract (`train_and_eval/tool_calls.py::AnswerFormat`) has no `boolean`; a boolean
  row cannot map to a submit tool.
- **No checkpoints saved.** `save_strategy="no"` in `grpo_train.py`; a collapsed run
  preserves nothing mid-training (noted in `docs/_archive/rl_checkpoint_2026-08-08.md`).
- **Runbook signature is stale.** `docs/_archive/rl_runbook.md` documents
  `reward_cadqa(gold_answer, answer_format, completion)`, which is not the implemented batch
  API.
- **Default dataset is v2.** The default GRPO config trains on v2 (`v2_curriculum`), while
  the teacher and eval default to v3. See
  [00-overview.md](00-overview.md#open-questions).

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- Shaped reward (format/structure partial credit) and an entropy/length monitor with a stop
  gate.
- On-policy SFT-then-GRPO with checkpoints every N steps.
