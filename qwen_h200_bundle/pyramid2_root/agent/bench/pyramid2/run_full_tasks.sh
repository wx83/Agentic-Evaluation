#!/bin/bash
# 10-24:task 07 / 09 全四层(含 L4 gap)—— g4 两个 task 并行,qwen 串行;各自 self -> gold -> none;最后合并 + 报告 + 页面
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
one() { AG=$1; K=$2
  /mnt/work_new/weihanxu/agent/bench/pyramid2/run_smoke.sh $C/p2_hdepicE_1023t_${AG}_full_self__$K.json L1 L2 L3 L4
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_${AG}_full_${arm}__$K.json --from-run p2_hdepicE_1023t_${AG}_full_self__$K; done
  echo "[$(date +%T)] $AG task $K done"; }
( one g4 07 & one g4 09 & wait; echo "[$(date +%T)] G4_FULL_DONE" ) &
PG=$!
( one qwen 07; one qwen 09; echo "[$(date +%T)] QWEN_FULL_DONE" ) &
PQ=$!
wait $PG $PQ
for AG in g4 qwen; do for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_${AG}_full_${arm}; done; done
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full --out /mnt/work_new/weihanxu/experiments/daily_report/1024_full_tasks0709.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
$PY build.py --agents g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full --extra qwen_on_g4set=p2_hdepicE_1023t_qwen_on_g4set
HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] FULL_TASKS_PUSHED"
