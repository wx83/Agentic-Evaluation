#!/bin/bash
# 剩余的 qwen 任务,GPU 串行。全部可续跑:中断重启会跳过已答的题。
set -u
export GEMINI_API_KEY='AQ.Ab8RN6K-mRMni3bTOwVZdKcW5AFDQfg4TyG9-07h3sdR49FelA'
QP=/home/weihanxu/miniconda3/envs/timechatcap/bin/python
cd "$(dirname "$0")"
echo "##### 1/4 seed42 clip30 shared_l1(L1 已完成,从 L2 续)#####"
$QP orchestrate.py --arm shared_l1 --mode clip30 --agents qwen --no-gate || echo "!!!!! seed42 clip30 中断"
echo "##### 2/4 seed42 memory 补 L4(此前被闸门截断)#####"
$QP orchestrate.py --arm shared_l1 --agents qwen --no-gate || echo "!!!!! seed42 memory 中断"
echo "##### 3/4 seed7 memory shared_l1 #####"
PYRAMID_SEED=7 $QP orchestrate.py --arm shared_l1 --agents qwen --no-gate || echo "!!!!! seed7 memory 中断"
echo "##### 4/4 seed7 clip30 shared_l1 #####"
PYRAMID_SEED=7 $QP orchestrate.py --arm shared_l1 --mode clip30 --agents qwen --no-gate || echo "!!!!! seed7 clip30 中断"
echo "##### qwen 全部任务结束 #####"
