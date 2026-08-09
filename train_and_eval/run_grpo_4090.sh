#!/bin/bash
cd /root/cadqa-bench
pkill -9 -f "grpo_trai[n].py" 2>/dev/null
sleep 1
rm -f grpo_4090.log
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  CADQA_RL_ROWS=2000 CADQA_RL_STEPS=500 CADQA_RL_GEN=2 CADQA_RL_BS=4 CADQA_RL_SEQ=16384 CADQA_RL_MAXCOMP=4096 CADQA_RL_OUT=/root/cadqa-rl-4090 \
  setsid nohup /root/cadqa-rl-venv/bin/python /root/cadqa-bench/grpo_train.py > grpo_4090.log 2>&1 &
echo "grpo-4090 pid $!"
sleep 5
pgrep -f "grpo_trai[n].py" >/dev/null && echo ALIVE || echo DEAD
