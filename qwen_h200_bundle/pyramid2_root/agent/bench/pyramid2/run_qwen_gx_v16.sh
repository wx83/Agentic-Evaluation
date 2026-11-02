#!/bin/bash
# 10-28(tillicum):qwen_gx_v16 = g4_v16 配置,Examiner / scope / judge = Gemini,Solver = Qwen3-Omni(qwen_server 8799)。
# 每个 task:self 阶梯 → gold 重放 → compare;最后合并 + 打分。用法:./run_qwen_gx_v16.sh [task ...](默认 55 39 07 13 05)
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
TASKS=${@:-55 39 07 13 05}
log() { echo "[$(date +%T)] $*"; }
for T in $TASKS; do
  log "qwen_gx v16 task $T self"
  ./run_smoke.sh $C/p2_hdepicE_1023t_qwen_gx_v16_self__$T.json L1 L2 L3 L4
  log "qwen_gx v16 task $T gold replay"
  for i in 1 2 3; do
    GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_qwen_gx_v16_gold__$T.json --from-run p2_hdepicE_1023t_qwen_gx_v16_self__$T 2>&1 | grep -v Warning | tail -n 3 && break
    log "replay $T failed - retry in 60s"; sleep 60
  done
  GEMINI_BACKEND=nv $PY cli.py compare --self-run p2_hdepicE_1023t_qwen_gx_v16_self__$T --gold-run p2_hdepicE_1023t_qwen_gx_v16_gold__$T 2>&1 | grep -v Warning | head -n 8
done
$PY merge_runs.py p2_hdepicE_1023t_qwen_gx_v16_self p2_hdepicE_1023t_qwen_gx_v16_gold
for T in $TASKS; do $PY pyramid_score.py $R/p2_hdepicE_1023t_qwen_gx_v16_self__$T | head -n 1; done
log "QWEN_GX_V16_DONE ($TASKS)"
