#!/bin/bash
# 10-28 晚(用户:Gemini 4 用 v16 再跑 3 个 task,self + gold):task 07 / 13 / 05 三个 self 并行,各自跑完立刻 gold 重放 + compare;最后合并、打分、链路页 + 主 Space。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
log() { echo "[$(date +%T)] $*"; }
one() {
  T=$1
  log "v16 task $T self"
  ./run_smoke.sh $C/p2_hdepicE_1023t_g4_v16_self__$T.json L1 L2 L3 L4
  log "v16 task $T gold replay"
  for i in 1 2 3; do
    GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_g4_v16_gold__$T.json --from-run p2_hdepicE_1023t_g4_v16_self__$T 2>&1 | grep -v Warning | tail -n 2 && break
    log "replay $T failed - retry in 60s"; sleep 60
  done
  GEMINI_BACKEND=nv $PY cli.py compare --self-run p2_hdepicE_1023t_g4_v16_self__$T --gold-run p2_hdepicE_1023t_g4_v16_gold__$T 2>&1 | grep -v Warning | head -n 8
  log "v16 task $T done"
}
for T in 07 13 05; do one $T > /mnt/work_new/weihanxu/logs/pyramid2/run_v16_t$T.log 2>&1 & sleep 30; done
wait
$PY merge_runs.py p2_hdepicE_1023t_g4_v16_self p2_hdepicE_1023t_g4_v16_gold
for T in 55 39 07 13 05; do $PY pyramid_score.py $R/p2_hdepicE_1023t_g4_v16_self__$T | head -n 1; done
cd /mnt/work_new/weihanxu/hf_space_pyramid2_v16_chain_1028 && $PY build.py 2>&1 | grep -v Warning | tail -n 1 && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py 2>&1 | tail -n 1
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023 && (grep -q '^g4_v16=' latest_only.txt || printf 'g4_v16=p2_hdepicE_1023t_g4_v16\n' >> latest_only.txt) && GEMINI_BACKEND=nv $PY build.py 2>&1 | grep -v Warning | tail -n 1 && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py 2>&1 | tail -n 1
log "V16_X3_DONE (tasks 07 13 05 self + gold)"
