#!/bin/bash
# Qwen task 00:gold / none replay + 重答 Gemini 4 题集 → 合并 → 报告 → 页面(两个 agent)推送;等 Gemini 链先推完再推
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
for arm in gold none; do
  GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_qwen_${arm}__00.json --from-run p2_hdepicE_1023t_qwen_self__00
  echo "[$(date +%T)] qwen $arm done"
done
GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_qwen_on_g4set__00.json --from-run p2_hdepicE_1023t_g4_self__00 --propagate
echo "[$(date +%T)] qwen on_g4set done"
until grep -q "G4_TASK00_PUSHED" /mnt/work_new/weihanxu/logs/pyramid2/after_g4_task00.log; do sleep 30; done
$PY merge_runs.py p2_hdepicE_1023t_qwen_self p2_hdepicE_1023t_qwen_gold p2_hdepicE_1023t_qwen_none p2_hdepicE_1023t_qwen_on_g4set
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen --extra qwen_on_g4set=p2_hdepicE_1023t_qwen_on_g4set --out /mnt/work_new/weihanxu/experiments/daily_report/1023_task00.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
$PY build.py --agents g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen --extra qwen_on_g4set=p2_hdepicE_1023t_qwen_on_g4set
HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] QWEN_TASK00_PUSHED"
