#!/bin/bash
# 10-26(用户定):history 标注实验。selfv = 抬头说明「你自己之前的未核实回答」;goldv = 抬头说明「已核实正确的答案」。
# 都是对 v8 self run 同一批题的 replay(只换 history 文字),10 个 task。Gemini 两波(5+5)并行;Qwen 等 run_v8_more.log 的 V8_MORE_PUSHED(none 臂跑完、服务器空出)后 goldv 先、selfv 后。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
HIST="g4_v7=p2_hdepicE_1023t_g4_v7 g4_v6=p2_hdepicE_1023t_g4_v6 g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full"
AG="g4_v8=p2_hdepicE_1023t_g4_v8 qwen_v8=p2_hdepicE_1023t_qwen_v8"
rep() { GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_$1_v8_$2__$3.json --from-run p2_hdepicE_1023t_$1_v8_self__$3; echo "[$(date +%T)] $1 $2 task $3 done"; }
publish() {
  for a in g4 qwen; do for arm in self gold none goldv selfv; do ls -d /mnt/work_new/weihanxu/output/pyramid_v2/runs/p2_hdepicE_1023t_${a}_v8_${arm}__* >/dev/null 2>&1 && $PY merge_runs.py p2_hdepicE_1023t_${a}_v8_${arm}; done; done
  GEMINI_BACKEND=nv $PY daily_1023.py --agents $AG --out /mnt/work_new/weihanxu/experiments/daily_report/1025_v8_stair_10tasks.md
  cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023 && $PY build.py --agents $AG --history $HIST && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py; cd /mnt/work_new/weihanxu/agent/bench/pyramid2; }
( for K in 00 01 02 03 04; do (rep g4 goldv $K; rep g4 selfv $K) & done; wait
  for K in 05 06 07 08 09; do (rep g4 goldv $K; rep g4 selfv $K) & done; wait
  echo "[$(date +%T)] G4_LABEL_DONE" ) &
PG=$!
( until grep -qE "(^|[^_])V8_MORE_PUSHED" /mnt/work_new/weihanxu/logs/pyramid2/run_v8_more.log; do sleep 600; done
  echo "[$(date +%T)] qwen none arm finished; starting qwen goldv"
  for K in 00 01 02 03; do rep qwen goldv $K & done; wait
  for K in 04 05 06; do rep qwen goldv $K & done; wait
  for K in 07 08 09; do rep qwen goldv $K & done; wait
  echo "[$(date +%T)] QWEN_LABEL_GOLDV_DONE"; publish; echo "[$(date +%T)] QWEN_GOLDV_PUSHED"
  for K in 00 01 02 03; do rep qwen selfv $K & done; wait
  for K in 04 05 06; do rep qwen selfv $K & done; wait
  for K in 07 08 09; do rep qwen selfv $K & done; wait
  echo "[$(date +%T)] QWEN_LABEL_DONE" ) &
PQ=$!
wait $PG; publish; echo "[$(date +%T)] G4_LABEL_PUSHED"
wait $PQ; publish; echo "[$(date +%T)] LABEL_PUSHED"
