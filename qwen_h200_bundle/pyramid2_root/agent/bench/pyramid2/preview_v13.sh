#!/bin/bash
# 10-27 19:20(用户:能不能先看到一些结果):v13 跑完前每小时把已有的 per-task run 合并、重建 Space(latest_only = g4_v13)并推送;V13_DONE 后停。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs; LOG=/mnt/work_new/weihanxu/logs/pyramid2/run_v13.log
while ! grep -q V13_DONE $LOG; do
  sleep 3600
  grep -q V13_DONE $LOG && break
  for arm in self gold none; do ls -d $R/p2_hdepicE_1023t_g4_v13_${arm}__* >/dev/null 2>&1 && $PY merge_runs.py p2_hdepicE_1023t_g4_v13_${arm}; done
  cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
  printf '# 10-27 晚(用户:space 只放最新版本)\ng4_v13=p2_hdepicE_1023t_g4_v13\n' > latest_only.txt
  GEMINI_BACKEND=nv $PY build.py && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py && echo "[$(date +%T)] preview pushed"
  cd /mnt/work_new/weihanxu/agent/bench/pyramid2
done
echo "[$(date +%T)] PREVIEW_STOPPED"
