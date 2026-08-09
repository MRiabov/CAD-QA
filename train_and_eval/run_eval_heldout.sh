#!/bin/bash
cd /root/cadqa-bench
pkill -9 -f "eval_ben[c]h.py" 2>/dev/null
sleep 1
rm -f /root/cadqa-bench/eval_heldout.log /root/cadqa-bench/eval_heldout.jsonl
setsid nohup /root/cadqa-rl-venv/bin/python /root/cadqa-bench/eval_bench.py \
  --adapter /root/cadqa-sft-final \
  --exclude-traces /root/cadqa-bench/sft_traces.jsonl \
  --max-rows 24 --seed 3407 \
  --out /root/cadqa-bench/eval_heldout.jsonl > /root/cadqa-bench/eval_heldout.log 2>&1 < /dev/null &
echo "EVAL_PID $!"
