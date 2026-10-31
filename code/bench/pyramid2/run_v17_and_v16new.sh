#!/bin/bash
# 10-29 13:20(用户定):v17(event 遍历)task 55/39/05 self→goldlive 三条线;v16 新 task 16/24/29/44/54 self→goldlive 两条线;5 条线并行。
set -u
HERE=$(cd "$(dirname "$0")" && pwd); cd "$HERE"
export P2_REPO=${P2_REPO:-$(cd "$HERE/../../.." && pwd)}; export P2_ROOT=${P2_ROOT:-$P2_REPO/pyramid_v2}
PY=python3; C=$P2_ROOT/contracts; R=$P2_ROOT/runs; LG=$P2_ROOT/logs; mkdir -p $LG
log() { echo "[$(date +%T)] $*"; }
one() { log "run $1"; ./run_smoke.sh $C/$1.json L1 L2 L3 L4; log "done $1"; }
( one p2_hdepicE_1023t_g4_v17_self__55; one p2_hdepicE_1023t_g4_v17_goldlive__55 ) > $LG/lane_v17_55.log 2>&1 &
sleep 20; ( one p2_hdepicE_1023t_g4_v17_self__39; one p2_hdepicE_1023t_g4_v17_goldlive__39 ) > $LG/lane_v17_39.log 2>&1 &
sleep 20; ( one p2_hdepicE_1023t_g4_v17_self__05; one p2_hdepicE_1023t_g4_v17_goldlive__05 ) > $LG/lane_v17_05.log 2>&1 &
sleep 20; ( for T in 16 24 54; do one p2_hdepicE_1023t_g4_v16_self__$T; one p2_hdepicE_1023t_g4_v16_goldlive__$T; done ) > $LG/lane_v16_d.log 2>&1 &
sleep 20; ( for T in 29 44; do one p2_hdepicE_1023t_g4_v16_self__$T; one p2_hdepicE_1023t_g4_v16_goldlive__$T; done ) > $LG/lane_v16_e.log 2>&1 &
wait
$PY merge_runs.py p2_hdepicE_1023t_g4_v17_self p2_hdepicE_1023t_g4_v17_goldlive
for r in v17_self__55 v17_goldlive__55 v17_self__39 v17_goldlive__39 v17_self__05 v17_goldlive__05 v16_self__16 v16_goldlive__16 v16_self__24 v16_goldlive__24 v16_self__29 v16_goldlive__29 v16_self__44 v16_goldlive__44 v16_self__54 v16_goldlive__54; do $PY pyramid_score.py $R/p2_hdepicE_1023t_g4_$r | head -n 1; done
log "V17_V16NEW_DONE"
