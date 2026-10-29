#!/bin/bash
# v7(10-24 23:55):答对也追问(followup_on_pass)+ v6 阶段级 plan 题;四层全部重跑。
# g4 task 07/09 并行立刻跑;qwen 等 run_v5.log 出现最终 V5_PUSHED 后跑(跳过 qwen v6)。Gemini 完成先 push,全部完成再报告 + push。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
HIST="g4_v6=p2_hdepicE_1023t_g4_v6 g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full"
one() { AG=$1; K=$2
  /mnt/work_new/weihanxu/agent/bench/pyramid2/run_smoke.sh $C/p2_hdepicE_1023t_${AG}_v7_self__$K.json L1 L2 L3 L4
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_${AG}_v7_${arm}__$K.json --from-run p2_hdepicE_1023t_${AG}_v7_self__$K; done
  echo "[$(date +%T)] $AG v7 task $K done"; }
( one g4 07 & one g4 09 & wait
  for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_g4_v7_${arm}; done
  cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023 && $PY build.py --agents g4_v7=p2_hdepicE_1023t_g4_v7 qwen_v7=p2_hdepicE_1023t_qwen_v7 --history $HIST && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
  echo "[$(date +%T)] G4_V7_PUSHED" ) &
PG=$!
( until grep -qE "(^|[^_])V5_PUSHED" /mnt/work_new/weihanxu/logs/pyramid2/run_v5.log; do sleep 120; done
  echo "[$(date +%T)] qwen v5 finished; starting qwen v7"
  one qwen 07; one qwen 09
  for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_qwen_v7_${arm}; done
  echo "[$(date +%T)] QWEN_V7_DONE" ) &
PQ=$!
wait $PG $PQ
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_v7=p2_hdepicE_1023t_g4_v7 qwen_v7=p2_hdepicE_1023t_qwen_v7 --out /mnt/work_new/weihanxu/experiments/daily_report/1024_v7_tasks0709.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
$PY build.py --agents g4_v7=p2_hdepicE_1023t_g4_v7 qwen_v7=p2_hdepicE_1023t_qwen_v7 --history $HIST
HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] V7_PUSHED"
