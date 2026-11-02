#!/bin/bash
# 10-28 晚(用户定):gold 臂自己走阶梯(history_mode=gold 直接 run)。55 / 07 / 13 三并行;55 跑完接 39(起始档续 goldlive 55);07 跑完接 05。最后合并 + 打分。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
log() { echo "[$(date +%T)] $*"; }
one() { log "goldlive task $1"; ./run_smoke.sh $C/p2_hdepicE_1023t_g4_v16_goldlive__$1.json L1 L2 L3 L4; log "goldlive task $1 done"; }
( one 55; one 39 ) > /mnt/work_new/weihanxu/logs/pyramid2/run_v16_goldlive_a.log 2>&1 &
sleep 30; ( one 07; one 05 ) > /mnt/work_new/weihanxu/logs/pyramid2/run_v16_goldlive_b.log 2>&1 &
sleep 30; ( one 13 ) > /mnt/work_new/weihanxu/logs/pyramid2/run_v16_goldlive_c.log 2>&1 &
wait
$PY merge_runs.py p2_hdepicE_1023t_g4_v16_goldlive
for T in 55 39 07 13 05; do $PY pyramid_score.py $R/p2_hdepicE_1023t_g4_v16_goldlive__$T | head -n 1; done
log "V16_GOLDLIVE_DONE"
