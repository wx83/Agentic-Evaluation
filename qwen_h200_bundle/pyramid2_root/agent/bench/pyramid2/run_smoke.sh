#!/bin/bash
# 用法: ./run_smoke.sh <contract.json> [levels...]   —— nohup 后台跑,崩了按同 run_id 续跑(最多 6 次)
set -u
C=$1; shift
LEVELS=${@:-L1 L2 L3 L4}
RID=$(python3 -c "import json,sys; print(json.load(open('$C'))['run_id'])")
RD=/mnt/work_new/weihanxu/output/pyramid_v2/runs/$RID
mkdir -p $RD
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
for i in 1 2 3 4 5 6; do
  echo "[$(date +%H:%M:%S)] attempt $i levels=$LEVELS" >> $RD/nohup.log
  GEMINI_BACKEND=nv python3 cli.py run --contract $C --levels $LEVELS >> $RD/nohup.log 2>&1 && break
  echo "[$(date +%H:%M:%S)] exited with $? — retry in 60s" >> $RD/nohup.log
  sleep 60
done
python3 cli.py report --run-id $RID > /dev/null 2>&1
echo "[$(date +%H:%M:%S)] ALL DONE" >> $RD/nohup.log
