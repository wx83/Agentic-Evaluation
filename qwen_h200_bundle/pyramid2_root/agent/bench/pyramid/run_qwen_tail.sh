#!/bin/bash
# 收尾:等当前 qwen 链结束,补跑 seed42 clip30 的 L4(此前因题套尚未生成而跳过),
# 然后对全部结果做一次统一重评(解析器修好后)。
set -u
export GEMINI_API_KEY='AQ.Ab8RN6K-mRMni3bTOwVZdKcW5AFDQfg4TyG9-07h3sdR49FelA'
QP=/home/weihanxu/miniconda3/envs/timechatcap/bin/python
cd "$(dirname "$0")"
echo "##### 等待当前 qwen 链结束 #####"
until ! pgrep -f "run_qwen_rest.sh" >/dev/null; do sleep 60; done
echo "##### 补跑 seed42 clip30 shared_l1 L4 #####"
$QP orchestrate.py --arm shared_l1 --mode clip30 --agents qwen --no-gate || echo "!!!!! 中断"
echo "##### 统一重评 #####"
python3 rescore.py '/mnt/work_new/weihanxu/output/pyramid/results/*/*/L*.jsonl'
PYRAMID_SEED=7 python3 rescore.py '/mnt/work_new/weihanxu/output/pyramid_seed7/results/*/*/L*.jsonl'
echo "##### 全部收尾完成 #####"
