#!/bin/bash
# 10-28(用户定):v16 gold 臂 = self run 跑完后逐题重放(history 换参考答案),task 55 → 39;然后合并 + 对比表。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
log() { echo "[$(date +%T)] $*"; }
for T in 55 39; do
  until grep -q "ALL DONE" $R/p2_hdepicE_1023t_qwen_v16_self__$T/nohup.log 2>/dev/null; do sleep 120; done
  log "qwen v16 task $T gold replay"
  for i in 1 2 3; do
    GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_qwen_v16_gold__$T.json --from-run p2_hdepicE_1023t_qwen_v16_self__$T 2>&1 | grep -v Warning | tail -n 3 && break
    log "replay $T exited with $? - retry in 60s"; sleep 60
  done
  GEMINI_BACKEND=nv $PY cli.py compare --self-run p2_hdepicE_1023t_qwen_v16_self__$T --gold-run p2_hdepicE_1023t_qwen_v16_gold__$T 2>&1 | grep -v Warning | head -n 12
done
$PY merge_runs.py p2_hdepicE_1023t_qwen_v16_gold
log "QWEN_V16_GOLD_DONE"
