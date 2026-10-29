#!/bin/bash
# 10-27(用户定):v12 = v11 + egocentric_frame_transform / gaze_primed_next_pickup / object_grounding。等 v11 pilot 跑完后 Gemini 4 跑 task 00 / 09 四层 self + gold / none replay;合并 + 报告。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
until grep -qE "V11_PILOT_DONE" /mnt/work_new/weihanxu/logs/pyramid2/run_v11_pilot.log; do sleep 300; done
one() { K=$1
  ./run_smoke.sh $C/p2_hdepicE_1023t_g4_v12_self__$K.json L1 L2 L3 L4
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_g4_v12_${arm}__$K.json --from-run p2_hdepicE_1023t_g4_v12_self__$K; done
  echo "[$(date +%T)] g4 v12 task $K done"; }
one 00 & one 09 & wait
for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_g4_v12_${arm}; done
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_v12=p2_hdepicE_1023t_g4_v12 --out /mnt/work_new/weihanxu/experiments/daily_report/1027_v12_pilot.md
echo "[$(date +%T)] V12_PILOT_DONE"
