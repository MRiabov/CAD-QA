#!/bin/bash
cd /root/cadqa-bench
pkill -9 -f "eval_bench\.py" 2>/dev/null   # inside script: own cmdline is 'bash run_eval2.sh'
sleep 1
rm -f eval_heldout.log eval_heldout.jsonl
setsid nohup /root/cadqa-rl-venv/bin/python /root/cadqa-bench/eval_bench.py \
  --model /root/cadqa-sft-merged \
  --exclude-traces /root/cadqa-bench/sft_texts.jsonl \
  --max-rows 12 > /root/cadqa-bench/eval_heldout.log 2>&1 < /dev/null &
echo "EVAL_PID $!"
