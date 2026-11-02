#!/bin/bash
# 10-27(用户:也跑 Qwen)。Qwen 服务器单线程,顺序:等 v9 的 Qwen goldv 推送(QWEN_GOLDV_PUSHED)+ Gemini v12 pilot 完成(V12_PILOT_DONE)
#   → 停掉 run_v8_label.sh 剩下的 selfv 部分 → Qwen 重答 Gemini v12 同题(task 00/09,无 history)→ Qwen 自己跑 v12 阶梯 task 00(self + none replay)
#   → 合并 / 报告 → 补跑 v9 的 Qwen selfv 三波 → publish(与 run_v8_label.sh 相同)。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; LOG=/mnt/work_new/weihanxu/logs/pyramid2
until grep -qE "QWEN_GOLDV_PUSHED" $LOG/run_v8_label.log && grep -qE "V12_PILOT_DONE" $LOG/run_v12_pilot.log; do sleep 600; done
echo "[$(date +%T)] goldv pushed + gemini v12 done; stopping the label chain's selfv part"
pkill -f run_v8_label.sh; sleep 2; pkill -f "qwen_v8_selfv__" ; sleep 5
rep() { GEMINI_BACKEND=nv $PY cli.py replay --contract $C/$1.json --from-run $2; echo "[$(date +%T)] $1 done"; }
rep p2_hdepicE_1023t_qwen_v12ong4_none__00 p2_hdepicE_1023t_g4_v12_self__00 & rep p2_hdepicE_1023t_qwen_v12ong4_none__09 p2_hdepicE_1023t_g4_v12_self__09 & wait
echo "[$(date +%T)] QWEN_V12_ONG4_DONE"
./run_smoke.sh $C/p2_hdepicE_1023t_qwen_v12_self__00.json L1 L2 L3 L4
rep p2_hdepicE_1023t_qwen_v12_none__00 p2_hdepicE_1023t_qwen_v12_self__00
echo "[$(date +%T)] QWEN_V12_SELF_DONE"
$PY merge_runs.py p2_hdepicE_1023t_qwen_v12ong4_none; for arm in self none; do $PY merge_runs.py p2_hdepicE_1023t_qwen_v12_${arm}; done
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_v12=p2_hdepicE_1023t_g4_v12 qwen_v12=p2_hdepicE_1023t_qwen_v12 --extra qwen_v12_on_g4set=p2_hdepicE_1023t_qwen_v12ong4_none --out /mnt/work_new/weihanxu/experiments/daily_report/1027_v12_pilot.md
echo "[$(date +%T)] QWEN_V12_REPORTED"
# ---- 补跑 v9 Qwen selfv(与 run_v8_label.sh 相同)
rep9() { GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_qwen_v8_selfv__$1.json --from-run p2_hdepicE_1023t_qwen_v8_self__$1; echo "[$(date +%T)] qwen selfv task $1 done"; }
for K in 00 01 02 03; do rep9 $K & done; wait
for K in 04 05 06; do rep9 $K & done; wait
for K in 07 08 09; do rep9 $K & done; wait
echo "[$(date +%T)] QWEN_LABEL_DONE"
HIST="g4_v7=p2_hdepicE_1023t_g4_v7 g4_v6=p2_hdepicE_1023t_g4_v6 g4_v5=p2_hdepicE_1023t_g4_v5 qwen_v5=p2_hdepicE_1023t_qwen_v5 g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap g4_full=p2_hdepicE_1023t_g4_full qwen_full=p2_hdepicE_1023t_qwen_full"
AG="g4_v8=p2_hdepicE_1023t_g4_v8 qwen_v8=p2_hdepicE_1023t_qwen_v8"
for a in g4 qwen; do for arm in self gold none goldv selfv; do ls -d /mnt/work_new/weihanxu/output/pyramid_v2/runs/p2_hdepicE_1023t_${a}_v8_${arm}__* >/dev/null 2>&1 && $PY merge_runs.py p2_hdepicE_1023t_${a}_v8_${arm}; done; done
GEMINI_BACKEND=nv $PY daily_1023.py --agents $AG --out /mnt/work_new/weihanxu/experiments/daily_report/1025_v8_stair_10tasks.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023 && $PY build.py --agents $AG --history $HIST && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py; cd /mnt/work_new/weihanxu/agent/bench/pyramid2
echo "[$(date +%T)] LABEL_PUSHED"
