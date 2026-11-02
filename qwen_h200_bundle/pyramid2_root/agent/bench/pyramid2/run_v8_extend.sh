#!/bin/bash
# 10-25 14:10(用户定):阶梯搜索预算 6 → 12,就地续跑。只重开因 budget 停下的 skill(staircase.reopen_for_budget),保留已有轨迹;
# 续搜 → 重新验证 → gold/none 只补答新题(replay 跳过已答)。Gemini 立刻跑;Qwen 等 run_v8_qwen.log 出现 QWEN_V8_PUSHED(none 臂收尾)再跑。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
HIST="g4_v7=p2_hdepicE_1023t_g4_v7 g4_v6=p2_hdepicE_1023t_g4_v6 g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full"
one() { AG=$1; K=$2
  $PY staircase.py reopen 12 p2_hdepicE_1023t_${AG}_v8_self__$K
  /mnt/work_new/weihanxu/agent/bench/pyramid2/run_smoke.sh $C/p2_hdepicE_1023t_${AG}_v8_self__$K.json L1 L2 L3 L4
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_${AG}_v8_${arm}__$K.json --from-run p2_hdepicE_1023t_${AG}_v8_self__$K; done
  echo "[$(date +%T)] $AG v8 extend task $K done"; }
publish() { AG="g4_v8=p2_hdepicE_1023t_g4_v8 qwen_v8=p2_hdepicE_1023t_qwen_v8"
  GEMINI_BACKEND=nv $PY daily_1023.py --agents $AG --out /mnt/work_new/weihanxu/experiments/daily_report/1025_v8_stair_tasks020506.md
  cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023 && $PY build.py --agents $AG --history $HIST && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py; cd /mnt/work_new/weihanxu/agent/bench/pyramid2; }
( one g4 02 & one g4 05 & one g4 06 & wait
  for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_g4_v8_${arm}; done
  publish; echo "[$(date +%T)] G4_V8_EXT_PUSHED" ) &
PG=$!
( until grep -qE "QWEN_V8_PUSHED" /mnt/work_new/weihanxu/logs/pyramid2/run_v8_qwen.log; do sleep 300; done
  echo "[$(date +%T)] qwen v8 first pass pushed; extending"
  one qwen 02 & one qwen 05 & one qwen 06 & wait
  for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_qwen_v8_${arm}; done
  echo "[$(date +%T)] QWEN_V8_EXT_DONE" ) &
PQ=$!
wait $PG $PQ
publish; echo "[$(date +%T)] V8_EXT_PUSHED"
