#!/bin/bash
# 10-28 02:55:task 39 续跑(55 已完成),然后合并 + 打分
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
echo "[$(date +%T)] v15 task 39 self (resume)"
./run_smoke.sh $C/p2_hdepicE_1023t_g4_v15_self__39.json L1 L2 L3 L4
$PY merge_runs.py p2_hdepicE_1023t_g4_v15_self
for T in 55 39; do $PY pyramid_score.py $R/p2_hdepicE_1023t_g4_v15_self__$T | head -n 8; done
echo "[$(date +%T)] V15_DONE (tasks 55 + 39 self)"
