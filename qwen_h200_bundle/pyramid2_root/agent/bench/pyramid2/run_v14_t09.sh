#!/bin/bash
# 10-27 晚(用户定实验):v14 = v13 + 去掉验证题 + 起始档用上次边界;只跑 task 09,self 跑阶梯,gold 重放;合并、打分、Space 加 g4_v14 并推送。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
log() { echo "[$(date +%T)] $*"; }
log "v14 task 09 self"
./run_smoke.sh $C/p2_hdepicE_1023t_g4_v14_self__09.json L1 L2 L3 L4
log "v14 task 09 gold replay"
GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_g4_v14_gold__09.json --from-run p2_hdepicE_1023t_g4_v14_self__09 2>&1 | grep -v Warning | tail -n 3
$PY merge_runs.py p2_hdepicE_1023t_g4_v14_self p2_hdepicE_1023t_g4_v14_gold
$PY pyramid_score.py $R/p2_hdepicE_1023t_g4_v14_self__09 | head -n 6
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
printf '# 10-27 晚(用户:space 只放最新版本);v14 = 预算实验,与 v13 同 task 对比\ng4_v13=p2_hdepicE_1023t_g4_v13\ng4_v14=p2_hdepicE_1023t_g4_v14\n' > latest_only.txt
GEMINI_BACKEND=nv $PY build.py 2>&1 | grep -v Warning | tail -n 2 && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py 2>&1 | tail -n 1
log "V14_DONE (task 09 self + gold)"
