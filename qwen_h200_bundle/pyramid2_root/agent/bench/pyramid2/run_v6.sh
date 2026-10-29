#!/bin/bash
# v6(10-24 22:50):L4 plan 题改阶段级(contract plan_mode=stages);只重跑 L4(决策点 + gap),L1–L3 用符号链接复用 v5 同臂的 run,scope 复用 v5 self。
# g4 task 07/09 并行立刻跑;qwen 等 run_v5.log 出现最终 V5_PUSHED(非 G4_V5_PUSHED)后再跑(Qwen 服务单实例)。Gemini 完成先 push 一次,全部完成再报告 + push。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
HIST="g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full"
prep() { AG=$1; K=$2
  for arm in self gold none; do d=$R/p2_hdepicE_1023t_${AG}_v6_${arm}__$K; mkdir -p $d
    for L in L1 L2 L3; do [ -e $d/$L ] || ln -s $R/p2_hdepicE_1023t_${AG}_v5_${arm}__$K/$L $d/$L; done
    [ -d $d/scope ] || cp -r $R/p2_hdepicE_1023t_${AG}_v5_self__$K/scope $d/scope
  done; }
one() { AG=$1; K=$2; prep $AG $K
  GEMINI_BACKEND=nv $PY cli.py run --contract $C/p2_hdepicE_1023t_${AG}_v6_self__$K.json --levels L4 || GEMINI_BACKEND=nv $PY cli.py run --contract $C/p2_hdepicE_1023t_${AG}_v6_self__$K.json --levels L4
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_${AG}_v6_${arm}__$K.json --from-run p2_hdepicE_1023t_${AG}_v6_self__$K --levels L4; done
  echo "[$(date +%T)] $AG v6 task $K done"; }
( one g4 07 & one g4 09 & wait
  for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_g4_v6_${arm}; done
  cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023 && $PY build.py --agents g4_v6=p2_hdepicE_1023t_g4_v6 qwen_v6=p2_hdepicE_1023t_qwen_v6 --history $HIST && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
  echo "[$(date +%T)] G4_V6_PUSHED" ) &
PG=$!
( until grep -qE "(^|[^_])V5_PUSHED" /mnt/work_new/weihanxu/logs/pyramid2/run_v5.log; do sleep 120; done
  echo "[$(date +%T)] qwen v5 finished; starting qwen v6"
  one qwen 07; one qwen 09
  for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_qwen_v6_${arm}; done
  echo "[$(date +%T)] QWEN_V6_DONE" ) &
PQ=$!
wait $PG $PQ
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_v6=p2_hdepicE_1023t_g4_v6 qwen_v6=p2_hdepicE_1023t_qwen_v6 --out /mnt/work_new/weihanxu/experiments/daily_report/1024_v6_tasks0709.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
$PY build.py --agents g4_v6=p2_hdepicE_1023t_g4_v6 qwen_v6=p2_hdepicE_1023t_qwen_v6 --history $HIST
HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] V6_PUSHED"
