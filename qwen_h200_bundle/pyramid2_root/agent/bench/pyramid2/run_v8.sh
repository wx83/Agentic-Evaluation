#!/bin/bash
# v8(10-25 00:30,用户定):skill 内难度阶梯(2-down-1-up,每 skill ≤6 搜索 + 2 验证),Gemini 4 Solver ×3 重答,gemini-3.1-pro Examiner / scope / judge。
# 三个 task(02 P03 aubergine S02、05 P04 Peas Pulao S06、06 P06 Uttapam pan S03)并行;等 run_v7.log 出现 G4_V7_PUSHED(避免 5 路 Examiner 并发触发 429)后开跑。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
HIST="g4_v7=p2_hdepicE_1023t_g4_v7 g4_v6=p2_hdepicE_1023t_g4_v6 g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full"
until grep -qE "G4_V7_PUSHED" /mnt/work_new/weihanxu/logs/pyramid2/run_v7.log; do sleep 120; done
echo "[$(date +%T)] gemini v7 pushed; starting v8"
one() { K=$1
  /mnt/work_new/weihanxu/agent/bench/pyramid2/run_smoke.sh $C/p2_hdepicE_1023t_g4_v8_self__$K.json L1 L2 L3 L4
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_g4_v8_${arm}__$K.json --from-run p2_hdepicE_1023t_g4_v8_self__$K; done
  echo "[$(date +%T)] g4 v8 task $K done"; }
one 02 & one 05 & one 06 & wait
for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_g4_v8_${arm}; done
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_v8=p2_hdepicE_1023t_g4_v8 --out /mnt/work_new/weihanxu/experiments/daily_report/1025_v8_stair_tasks020506.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
$PY build.py --agents g4_v8=p2_hdepicE_1023t_g4_v8 --history $HIST
HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] V8_PUSHED"
