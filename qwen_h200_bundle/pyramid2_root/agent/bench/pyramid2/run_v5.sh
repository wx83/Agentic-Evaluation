#!/bin/bash
# v5(10-24 18:30):g4 task 07/09 并行;qwen 先续完 v4 task 07 的 gold/none replay,再跑 v5 task 07、09;最后合并 + 报告 + 页面(最新 = v5,历史折叠)
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
one() { AG=$1; K=$2
  /mnt/work_new/weihanxu/agent/bench/pyramid2/run_smoke.sh $C/p2_hdepicE_1023t_${AG}_v5_self__$K.json L1 L2 L3 L4
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_${AG}_v5_${arm}__$K.json --from-run p2_hdepicE_1023t_${AG}_v5_self__$K; done
  echo "[$(date +%T)] $AG v5 task $K done"; }
( one g4 07 & one g4 09 & wait
  for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_g4_v5_${arm}; done
  cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023 && $PY build.py --agents g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 --history g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
  echo "[$(date +%T)] G4_V5_PUSHED" ) &
PG=$!
( for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_qwen_full_${arm}__07.json --from-run p2_hdepicE_1023t_qwen_full_self__07; done
  echo "[$(date +%T)] qwen v4 task 07 replays done"
  one qwen 07; one qwen 09; echo "[$(date +%T)] QWEN_V5_DONE" ) &
PQ=$!
wait $PG $PQ
for AG in g4 qwen; do for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_${AG}_v5_${arm}; done; done
for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_qwen_full_${arm}; done
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 --out /mnt/work_new/weihanxu/experiments/daily_report/1024_v5_tasks0709.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
$PY build.py --agents g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 --history g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full
HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] V5_PUSHED"
