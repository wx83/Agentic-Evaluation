#!/bin/bash
# 10-28 v15(用户定,sub-goal 结构版,见 sg.py 头注释):task 55 → task 39,只跑 self 臂(Examiner gemini-3.1-pro,Solver Gemini 4 ×3)。跑完合并 + 打分;Space 页另做。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
log() { echo "[$(date +%T)] $*"; }
for T in 55 39; do
  log "v15 task $T self"
  ./run_smoke.sh $C/p2_hdepicE_1023t_g4_v15_self__$T.json L1 L2 L3 L4
done
$PY merge_runs.py p2_hdepicE_1023t_g4_v15_self
for T in 55 39; do $PY pyramid_score.py $R/p2_hdepicE_1023t_g4_v15_self__$T | head -n 8; done
log "V15_DONE (tasks 55 + 39 self)"
