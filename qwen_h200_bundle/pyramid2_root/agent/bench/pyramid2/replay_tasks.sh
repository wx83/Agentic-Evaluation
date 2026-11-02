#!/bin/bash
# 用法: replay_tasks.sh <agent g4|qwen> <arm gold|none|on_g4set>  —— 对 10 个 task 逐个 replay
AG=$1; ARM=$2; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; cd /mnt/work_new/weihanxu/agent/bench/pyramid2
for i in $(seq -w 0 9); do
  if [ "$ARM" = "on_g4set" ]; then SRC=p2_hdepicE_1023t_g4_self__0$i; CT=$C/p2_hdepicE_1023t_qwen_on_g4set__0$i.json; EXTRA=--propagate; else SRC=p2_hdepicE_1023t_${AG}_self__0$i; CT=$C/p2_hdepicE_1023t_${AG}_${ARM}__0$i.json; EXTRA=; fi
  GEMINI_BACKEND=nv /home/weihanxu/miniconda3/bin/python3 cli.py replay --contract $CT --from-run $SRC $EXTRA
done
echo REPLAY_DONE_${AG}_${ARM}
