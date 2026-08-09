#!/bin/bash
cd /root/cadqa-bench
pkill -9 -f "bench_vllm\.py" 2>/dev/null
sleep 1
rm -f bench_vllm.log
HF_HUB_OFFLINE=1 nohup /root/cadqa-rl-venv/bin/python /root/cadqa-bench/bench_vllm.py > bench_vllm.log 2>&1 &
echo "bench_vllm pid $!"
