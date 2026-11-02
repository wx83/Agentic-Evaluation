#!/usr/bin/env bash
# answer-format 对照试验:跑 P.SETS/formats 下全部题套(blind + clip30),结果写 results/formats/<agent>/<mode>/。
#   bash run_formats.sh gemini [wait_pid]     # 可选:等某个 PID 退出后再开始(串行避免 Gemini 限流 / GPU 抢占)
#   bash run_formats.sh qwen  [wait_pid]
# 环境变量:MODES="clip30" LEVELS="3 4" 只跑一部分(并行拆分用);NO_JUDGE=1 跳过 judge。
# gemini 跑完自动跑 judge_formats.py 判 open 简答的规则无结论行。
set -u
AGENT=$1; WAIT=${2:-}
SEED=${PYRAMID_SEED:-43}
cd "$(dirname "$0")"
if [ -n "$WAIT" ]; then while kill -0 "$WAIT" 2>/dev/null; do sleep 60; done; fi
if [ "$AGENT" = gemini ]; then
  PY=/home/weihanxu/miniconda3/envs/gemini/bin/python
  export GEMINI_API_KEY="$(cat ${GEMINI_KEY_FILE:-/home/weihanxu/.gemini_api_key})"
else
  PY=/home/weihanxu/miniconda3/envs/timechatcap/bin/python
fi
SETS=/mnt/work_new/weihanxu/output/pyramid_seed${SEED}/sets/formats
OUT=/mnt/work_new/weihanxu/output/pyramid_seed${SEED}/results/formats/$AGENT
for MODE in ${MODES:-blind clip30}; do
  for L in ${LEVELS:-1 2 3 4}; do
    mkdir -p "$OUT/$MODE"
    PYRAMID_SEED=$SEED $PY evaluate.py --agent "$AGENT" --mode "$MODE" \
      --questions "$SETS"/L${L}_yn.json "$SETS"/L${L}_ms.json "$SETS"/L${L}_open.json "$SETS"/L${L}_open_x.json \
      --out "$OUT/$MODE" 2>&1 | grep -E "^\s+\[$AGENT/|Traceback|Error"
  done
done
if [ "$AGENT" = gemini ] && [ -z "${NO_JUDGE:-}" ]; then PYRAMID_SEED=$SEED $PY judge_formats.py; fi
echo "run_formats $AGENT done $(date)"
