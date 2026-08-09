#!/bin/bash
cd /root/cadqa-bench
pkill -9 -f "grpo_trai[n].py" 2>/dev/null
sleep 1
rm -f grpo_final.log
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  CADQA_RL_ROWS=$1 CADQA_RL_STEPS=$2 CADQA_RL_GEN=4 CADQA_RL_BS=1 CADQA_RL_SEQ=16384 CADQA_RL_MAXCOMP=4096 CADQA_RL_OUT=/root/cadqa-rl-final \
  setsid nohup /root/cadqa-rl-venv/bin/python /root/cadqa-bench/grpo_train.py > grpo_final.log 2>&1 &
echo "grpo-final pid $!"
sleep 5
pgrep -f "grpo_trai[n].py" >/dev/null && echo ALIVE || echo DEAD
