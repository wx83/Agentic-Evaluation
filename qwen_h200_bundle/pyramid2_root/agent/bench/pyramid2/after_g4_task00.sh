#!/bin/bash
# Gemini 4 task 00:self 完成后自动 gold / none replay → 合并 → 报告 → 页面推送
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
until grep -q "ALL DONE" $R/p2_hdepicE_1023t_g4_self__00/nohup.log 2>/dev/null; do sleep 30; done
echo "[$(date +%T)] self done"
for arm in gold none; do
  GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_g4_${arm}__00.json --from-run p2_hdepicE_1023t_g4_self__00
  echo "[$(date +%T)] $arm done"
done
$PY merge_runs.py p2_hdepicE_1023t_g4_self p2_hdepicE_1023t_g4_gold p2_hdepicE_1023t_g4_none
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4=p2_hdepicE_1023t_g4 --out /mnt/work_new/weihanxu/experiments/daily_report/1023_task00_g4.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
rm -rf site/media/*
$PY build.py --agents g4=p2_hdepicE_1023t_g4 --extra
HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] G4_TASK00_PUSHED"
