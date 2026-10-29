#!/usr/bin/env bash
# EPIC-Sounds 纯声音三层 × 五种格式:blind + clip30。  bash run_epic_sounds.sh <gemini|qwen> [wait_pid]
set -u
AGENT=$1; WAIT=${2:-}
cd "$(dirname "$0")"
if [ -n "$WAIT" ]; then while kill -0 "$WAIT" 2>/dev/null; do sleep 60; done; fi
if [ "$AGENT" = gemini ]; then
  PY=/home/weihanxu/miniconda3/envs/gemini/bin/python
  export GEMINI_API_KEY="$(cat ${GEMINI_KEY_FILE:-/home/weihanxu/.gemini_api_key})"
else
  PY=/home/weihanxu/miniconda3/envs/timechatcap/bin/python
fi
ROOT=/mnt/work_new/weihanxu/output/epic_sounds
for MODE in blind clip30; do
  mkdir -p "$ROOT/results/$AGENT/$MODE"
  PYRAMID_SEED=43 $PY evaluate.py --agent "$AGENT" --mode "$MODE" --questions "$ROOT"/sets/L*_*.json \
    --out "$ROOT/results/$AGENT/$MODE" 2>&1 | grep -E "^\s+\[$AGENT/|题套=|Traceback|Error"
done
if [ "$AGENT" = gemini ]; then PYRAMID_SEED=43 $PY judge_formats.py --root "$ROOT/results"; fi
echo "run_epic_sounds $AGENT done $(date)"
