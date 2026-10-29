#!/usr/bin/env bash
# L4 注视预判题 probe(seed43):blind + clip30。  bash run_gaze_probe.sh <gemini|qwen> [wait_pid ...]
set -u
AGENT=$1; shift
cd "$(dirname "$0")"
for W in "$@"; do while kill -0 "$W" 2>/dev/null; do sleep 60; done; done
if [ "$AGENT" = gemini ]; then PY=/home/weihanxu/miniconda3/envs/gemini/bin/python; export GEMINI_API_KEY="$(cat ${GEMINI_KEY_FILE:-/home/weihanxu/.gemini_api_key})"
else PY=/home/weihanxu/miniconda3/envs/timechatcap/bin/python; fi
R=/mnt/work_new/weihanxu/output/pyramid_seed43
for MODE in blind clip30; do
  mkdir -p "$R/results/gaze_probe/$AGENT/$MODE"
  PYRAMID_SEED=43 $PY evaluate.py --agent "$AGENT" --mode "$MODE" --questions "$R"/sets/gaze_probe/high_gaze_destination.json "$R"/sets/gaze_probe/high_gaze_pickup.json \
    --out "$R/results/gaze_probe/$AGENT/$MODE" 2>&1 | grep -E "^\s+\[$AGENT/|题套=|Traceback|Error"
done
echo "run_gaze_probe $AGENT done $(date)"
