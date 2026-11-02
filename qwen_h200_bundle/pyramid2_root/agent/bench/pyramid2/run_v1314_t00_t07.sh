#!/bin/bash
# 10-28(用户定):v13 与 v14 各补跑 task 00、07,只 self,四个 run 同时跑;完成后合并、打分、逐 task 对比、建站推送。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs; D=/mnt/work_new/weihanxu/experiments/daily_report
log() { echo "[$(date +%T)] $*"; }
log "launch 4 runs"
for ver in v13 v14; do for k in 00 07; do
  ./run_smoke.sh $C/p2_hdepicE_1023t_g4_${ver}_self__$k.json L1 L2 L3 L4 &
  sleep 20
done; done
wait
log "4 runs finished"
$PY merge_runs.py p2_hdepicE_1023t_g4_v13_self p2_hdepicE_1023t_g4_v14_self
for ver in v13 v14; do for k in 00 07; do $PY pyramid_score.py $R/p2_hdepicE_1023t_g4_${ver}_self__$k | head -n 1; done; done
for k in 00 07; do $PY compare_budget.py p2_hdepicE_1023t_g4_v13_self__$k p2_hdepicE_1023t_g4_v14_self__$k > $D/1028_budget_v13_vs_v14_t$k.md; done
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
grep -q '^g4_v14=' latest_only.txt || printf 'g4_v14=p2_hdepicE_1023t_g4_v14\n' >> latest_only.txt
GEMINI_BACKEND=nv $PY build.py 2>&1 | grep -v Warning | tail -n 2 && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py 2>&1 | tail -n 1
log "V1314_T00T07_DONE"
