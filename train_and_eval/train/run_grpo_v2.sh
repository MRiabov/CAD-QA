#!/bin/bash
cd /root/cadqa-bench
pkill -9 -f "grpo_trai[n].py" 2>/dev/null
sleep 1
rm -f grpo_test.log
CADQA_RL_ROWS=8 CADQA_RL_STEPS=2 CADQA_RL_GEN=2 CADQA_RL_BS=1 CADQA_RL_OUT=/root/cadqa-rl-test \
  nohup /root/cadqa-rl-venv/bin/python /root/cadqa-bench/grpo_train.py > grpo_test.log 2>&1 &
echo "grpo-test pid $!"
sleep 5
pgrep -f "grpo_trai[n].py" >/dev/null && echo ALIVE || echo DEAD
