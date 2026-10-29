#!/bin/bash
# 10-27 19:25(用户:先跑一个 task,而且只跑 self):task 09 self 跑完(run_smoke 的 ALL DONE)→ 合并 → Space(latest_only = g4_v13)推送。task 00 停在 L1 第 5 题左右,状态保留,可用同一 contract 续跑。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
until grep -q "ALL DONE" $R/p2_hdepicE_1023t_g4_v13_self__09/nohup.log 2>/dev/null; do sleep 120; done
echo "[$(date +%T)] g4 v13 task 09 self done"
mkdir -p $R/_hold; mv $R/p2_hdepicE_1023t_g4_v13_self__00 $R/_hold/ 2>/dev/null     # 合并只放 task 09;task 00 半截结果暂存 _hold
$PY merge_runs.py p2_hdepicE_1023t_g4_v13_self
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
printf '# 10-27 晚(用户:space 只放最新版本)\ng4_v13=p2_hdepicE_1023t_g4_v13\n' > latest_only.txt
GEMINI_BACKEND=nv $PY build.py && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] V13_DONE (task 09 self only)"
