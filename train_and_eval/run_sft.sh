#!/bin/bash
cd /root/cadqa-bench
rm -f sft.log
CADQA_SFT_TRACES=/root/cadqa-bench/sft_texts.jsonl \
CADQA_SFT_OUT=/root/cadqa-sft-final \
setsid nohup /root/cadqa-rl-venv/bin/python /root/cadqa-bench/sft_train.py > sft.log 2>&1 &
echo "sft pid $!"
sleep 5
pgrep -f "sft_trai[n].py" >/dev/null && echo ALIVE || echo DEAD
