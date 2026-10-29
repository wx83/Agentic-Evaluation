#!/bin/bash
# 10-25 14:30(用户定):v8 阶梯(预算 12)再跑剩下 7 个 task(00 01 03 04 07 08 09),页面展示全部 10 个。
# Gemini 分两波(4 + 3)并行,避免 Examiner 并发过多;Qwen 等 run_v8_extend.log 的 QWEN_V8_EXT_DONE 后同样分两波。每波后 gold/none replay,最后合并 / 报告 / 页面。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
HIST="g4_v7=p2_hdepicE_1023t_g4_v7 g4_v6=p2_hdepicE_1023t_g4_v6 g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full"
one() { AG=$1; K=$2
  /mnt/work_new/weihanxu/agent/bench/pyramid2/run_smoke.sh $C/p2_hdepicE_1023t_${AG}_v8_self__$K.json L1 L2 L3 L4
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_${AG}_v8_${arm}__$K.json --from-run p2_hdepicE_1023t_${AG}_v8_self__$K; done
  echo "[$(date +%T)] $AG v8 task $K done"; }
publish() { AG="g4_v8=p2_hdepicE_1023t_g4_v8 qwen_v8=p2_hdepicE_1023t_qwen_v8"
  for a in g4 qwen; do for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_${a}_v8_${arm}; done; done
  GEMINI_BACKEND=nv $PY daily_1023.py --agents $AG --out /mnt/work_new/weihanxu/experiments/daily_report/1025_v8_stair_10tasks.md
  cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023 && $PY build.py --agents $AG --history $HIST && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py; cd /mnt/work_new/weihanxu/agent/bench/pyramid2; }
( one g4 00 & one g4 07 & one g4 09 & one g4 04 & wait
  one g4 01 & one g4 03 & one g4 08 & wait
  publish; echo "[$(date +%T)] G4_V8_MORE_PUSHED" ) &
PG=$!
( until grep -qE "QWEN_V8_EXT_DONE" /mnt/work_new/weihanxu/logs/pyramid2/run_v8_extend.log; do sleep 600; done
  echo "[$(date +%T)] qwen v8 extension done; running 7 more tasks"
  one qwen 00 & one qwen 07 & one qwen 09 & one qwen 04 & wait
  one qwen 01 & one qwen 03 & one qwen 08 & wait
  echo "[$(date +%T)] QWEN_V8_MORE_DONE" ) &
PQ=$!
wait $PG $PQ
publish; echo "[$(date +%T)] V8_MORE_PUSHED"
