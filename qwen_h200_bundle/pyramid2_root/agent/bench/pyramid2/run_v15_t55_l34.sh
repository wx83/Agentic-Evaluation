#!/bin/bash
# 10-28 12:40:task 55 的 L3、L4 用派生关系重跑(旧 L3/L4 归档 _aborted/v15_55_l34_first),然后 gold 重放 L3 L4,合并打分
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
echo "[$(date +%T)] v15 task 55 self L3 L4 rerun"
./run_smoke.sh $C/p2_hdepicE_1023t_g4_v15_self__55.json L3 L4
echo "[$(date +%T)] v15 task 55 gold replay L3 L4"
GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_g4_v15_gold__55.json --from-run p2_hdepicE_1023t_g4_v15_self__55 --levels L3 L4 2>&1 | grep -v Warning | tail -n 3
GEMINI_BACKEND=nv $PY cli.py compare --self-run p2_hdepicE_1023t_g4_v15_self__55 --gold-run p2_hdepicE_1023t_g4_v15_gold__55 2>&1 | grep -v Warning | head -n 12
$PY merge_runs.py p2_hdepicE_1023t_g4_v15_self p2_hdepicE_1023t_g4_v15_gold
$PY pyramid_score.py $R/p2_hdepicE_1023t_g4_v15_self__55 | head -n 20
echo "[$(date +%T)] V15_T55_L34_DONE"
