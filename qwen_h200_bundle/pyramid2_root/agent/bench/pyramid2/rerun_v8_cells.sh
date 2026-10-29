#!/bin/bash
# 10-25 03:50:重跑 Gemini v8 里 Examiner 失败的格子(goal 词卡食材名 / aubergine≠eggplant 已修):task 05 的 L3+L4(L4 依赖 L3 history),task 02 的 L4;
# 三臂对应层目录删掉重来,再合并 / 报告 / push(页面 latest = g4_v8;qwen_v8 合并后由 run_v8_qwen.sh 再推一次)。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
HIST="g4_v7=p2_hdepicE_1023t_g4_v7 g4_v6=p2_hdepicE_1023t_g4_v6 g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full"
cell() { K=$1; shift; LV="$@"
  for arm in self gold none; do for L in $LV; do rm -rf $R/p2_hdepicE_1023t_g4_v8_${arm}__$K/$L; done; done
  /mnt/work_new/weihanxu/agent/bench/pyramid2/run_smoke.sh $C/p2_hdepicE_1023t_g4_v8_self__$K.json $LV
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_g4_v8_${arm}__$K.json --from-run p2_hdepicE_1023t_g4_v8_self__$K --levels $LV; done
  echo "[$(date +%T)] rerun task $K levels $LV done"; }
cell 05 L3 L4 & cell 02 L4 & wait
for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_g4_v8_${arm}; done
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_v8=p2_hdepicE_1023t_g4_v8 --out /mnt/work_new/weihanxu/experiments/daily_report/1025_v8_stair_tasks020506.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
$PY build.py --agents g4_v8=p2_hdepicE_1023t_g4_v8 --history $HIST
HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] V8_CELLS_PUSHED"
