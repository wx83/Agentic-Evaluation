#!/bin/bash
# 10-27 晚(用户:scope planner 要给每个 skill 划考试范围;先改 Gemini 重跑):v13 = v12 - contact + scope 覆盖全部 skill + 只用本 task 的 cluster + 阶梯 scope 优先。
# Gemini 4 跑 task 00 / 09 四层 self,再 gold / none replay;合并 + 报告;Space 只放 g4_v13 并推送。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
one() { K=$1
  ./run_smoke.sh $C/p2_hdepicE_1023t_g4_v13_self__$K.json L1 L2 L3 L4
  for arm in gold none; do GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_g4_v13_${arm}__$K.json --from-run p2_hdepicE_1023t_g4_v13_self__$K; done
  echo "[$(date +%T)] g4 v13 task $K done"; }
one 00 & one 09 & wait
for arm in self gold none; do $PY merge_runs.py p2_hdepicE_1023t_g4_v13_${arm}; done
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_v13=p2_hdepicE_1023t_g4_v13 --out /mnt/work_new/weihanxu/experiments/daily_report/1027_v13_scope.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
printf '# 10-27 晚(用户:space 只放最新版本)。存在时 build.py 只放这里列的组\ng4_v13=p2_hdepicE_1023t_g4_v13\n' > latest_only.txt
GEMINI_BACKEND=nv $PY build.py && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] V13_DONE"
