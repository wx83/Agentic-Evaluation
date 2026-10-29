#!/bin/bash
# 剩余的 gemini 任务:seed7 clip30 三臂 × 四层,不设闸门。只吃 API。
set -u
export GEMINI_API_KEY='AQ.Ab8RN6K-mRMni3bTOwVZdKcW5AFDQfg4TyG9-07h3sdR49FelA'
export PYRAMID_SEED=7
GEM=/home/weihanxu/miniconda3/envs/gemini/bin/python
cd "$(dirname "$0")"
for ARM in shared_l1 per_agent pooled; do
  echo "##### seed7 clip30 / $ARM #####"
  # 额度或网络抖动不该中断整条链:失败就记下继续,续跑会补齐
  $GEM orchestrate.py --arm $ARM --mode clip30 --agents gemini --no-gate || \
    echo "!!!!! $ARM 中断(见上方错误),继续下一臂"
done
echo "##### gemini 全部任务结束 #####"
