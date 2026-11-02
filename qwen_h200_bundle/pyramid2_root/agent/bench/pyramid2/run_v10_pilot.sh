#!/bin/bash
# 10-27(用户定):L3 扩展四 skill(l3ext.py)pilot —— Gemini 4 跑 task 00 / 02 的 L1 L2 L3(self),gold / none 只 replay L3;合并 + 报告。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
one() { K=$1
  ./run_smoke.sh $C/p2_hdepicE_1023t_g4_v10_self__$K.json L1 L2 L3
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_g4_v10_${arm}__$K.json --from-run p2_hdepicE_1023t_g4_v10_self__$K --levels L3; done
  echo "[$(date +%T)] g4 v10 task $K done"; }
one 00 & one 02 & wait
for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_g4_v10_${arm}; done
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_v10=p2_hdepicE_1023t_g4_v10 --out /mnt/work_new/weihanxu/experiments/daily_report/1027_v10_l3ext_pilot.md
echo "[$(date +%T)] V10_PILOT_DONE"
