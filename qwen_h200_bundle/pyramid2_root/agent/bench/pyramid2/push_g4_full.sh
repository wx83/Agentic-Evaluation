#!/bin/bash
# Gemini 4 两个 task(07/09)全层 + replay 完成后先推一次页面(不等 Qwen);页面默认参数 = 最新 g4_full/qwen_full,历史折叠
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3
until grep -q "G4_FULL_DONE" /mnt/work_new/weihanxu/logs/pyramid2/run_full_tasks.log; do sleep 60; done
for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_g4_full_${arm}; done
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_full=p2_hdepicE_1023t_g4_full --out /mnt/work_new/weihanxu/experiments/daily_report/1024_full_tasks0709_g4.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
$PY build.py
HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] G4_FULL_PUSHED"
