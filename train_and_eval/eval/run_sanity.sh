#!/bin/bash
cd /root/cadqa-bench
pkill -9 -f "sanity_chec[k]\.py" 2>/dev/null
sleep 1
rm -f sanity_out.txt
/root/cadqa-rl-venv/bin/python sanity_check.py > sanity_out.txt 2>&1
echo "SANITY_EXIT=$?"
