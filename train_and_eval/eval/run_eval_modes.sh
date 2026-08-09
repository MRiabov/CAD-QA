#!/bin/bash
# Run the no-tools and numpy harness modes IN PARALLEL on the same model and
# held-out rows (same seed), separate outputs — the modes are evaluated
# concurrently, not sequentially. cadquery mode is reserved for the RL stage.
# Usage: bash run_eval_modes.sh [model] [exclude-traces] [max-rows] [batch]
cd /root/cadqa-bench
EVAL=/root/cadqa-bench/train_and_eval/eval/eval_bench.py
MODEL=${1:-/root/cadqa-sft-merged}
EXCLUDE=${2:-/root/cadqa-bench/sft_texts.jsonl}
MAX_ROWS=${3:-12}
BATCH=${4:-4}   # two bf16 models share one GPU -> smaller batch per process
rm -f eval_heldout_notools.jsonl eval_heldout_numpy.jsonl eval_mode_nt.log eval_mode_np.log
setsid nohup /root/cadqa-rl-venv/bin/python "$EVAL" \
  --model "$MODEL" --exclude-traces "$EXCLUDE" --max-rows "$MAX_ROWS" --batch "$BATCH" \
  --mode no_tools --out eval_heldout_notools.jsonl > eval_mode_nt.log 2>&1 &
P1=$!
setsid nohup /root/cadqa-rl-venv/bin/python "$EVAL" \
  --model "$MODEL" --exclude-traces "$EXCLUDE" --max-rows "$MAX_ROWS" --batch "$BATCH" \
  --mode numpy --out eval_heldout_numpy.jsonl > eval_mode_np.log 2>&1 &
P2=$!
echo "no_tools pid $P1 | numpy pid $P2"
sleep 5
pgrep -f "eval_ben[c]h.py" >/dev/null && echo ALIVE || echo DEAD
