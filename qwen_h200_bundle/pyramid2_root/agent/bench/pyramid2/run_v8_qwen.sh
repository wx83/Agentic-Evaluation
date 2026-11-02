#!/bin/bash
# v8 Qwen3-Omni(10-25 02:30):同 g4_v8 的阶梯设计,三 task 02/05/06;Solver = 本地 qwen_server(8799,单线程 greedy,reps 1),Examiner/scope/judge = gemini-3.1-pro。
# 等 run_v5.log 出现最终 V5_PUSHED(Qwen v5 收尾)再跑;Qwen v7 已取消(v8 取代)。三 task 并行:Solver 请求在单线程服务上自然排队,Examiner 调用并行。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
HIST="g4_v7=p2_hdepicE_1023t_g4_v7 g4_v6=p2_hdepicE_1023t_g4_v6 g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full"
until grep -qE "(^|[^_])V5_PUSHED" /mnt/work_new/weihanxu/logs/pyramid2/run_v5.log; do sleep 120; done
echo "[$(date +%T)] qwen v5 finished; starting qwen v8"
one() { K=$1
  /mnt/work_new/weihanxu/agent/bench/pyramid2/run_smoke.sh $C/p2_hdepicE_1023t_qwen_v8_self__$K.json L1 L2 L3 L4
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_qwen_v8_${arm}__$K.json --from-run p2_hdepicE_1023t_qwen_v8_self__$K; done
  echo "[$(date +%T)] qwen v8 task $K done"; }
one 02 & one 05 & one 06 & wait
for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_qwen_v8_${arm}; done
# g4_v8 可能还没跑完:只在它的合并 run 存在时一起进报告 / 页面
AG="qwen_v8=p2_hdepicE_1023t_qwen_v8"; [ -f /mnt/work_new/weihanxu/output/pyramid_v2/runs/p2_hdepicE_1023t_g4_v8_self/run_contract.json ] && AG="g4_v8=p2_hdepicE_1023t_g4_v8 $AG"
GEMINI_BACKEND=nv $PY daily_1023.py --agents $AG --out /mnt/work_new/weihanxu/experiments/daily_report/1025_v8_stair_tasks020506.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
$PY build.py --agents $AG --history $HIST
HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] QWEN_V8_PUSHED"
