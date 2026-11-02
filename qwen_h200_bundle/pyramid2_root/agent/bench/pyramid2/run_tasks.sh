#!/bin/bash
# 用法: run_tasks.sh <agent g4|qwen> <shard k> <n shards>  —— 顺序跑该 shard 的 per-task self run
AG=$1; K=$2; N=$3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
for i in $(seq 0 9); do
  [ $((i % N)) -ne $K ] && continue
  /mnt/work_new/weihanxu/agent/bench/pyramid2/run_smoke.sh $C/p2_hdepicE_1023t_${AG}_self__$(printf %02d $i).json L1 L2 L3 L4
done
echo TASKS_DONE_${AG}_${K}
