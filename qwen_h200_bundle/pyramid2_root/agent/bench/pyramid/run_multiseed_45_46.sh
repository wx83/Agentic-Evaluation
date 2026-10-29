#!/bin/bash
# seed45 + seed46: clip30 pyramid for gemini+qwen, then the blind control on the same sets.
# Resumable at every stage. The key is read from ~/.gemini_api_key so it never lands in argv or history.
#   setsid nohup ./run_multiseed_45_46.sh > /mnt/work_new/weihanxu/logs/multiseed_45_46.log 2>&1 &
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PY=/home/weihanxu/miniconda3/envs/timechatcap/bin/python
GEM_PY=/home/weihanxu/miniconda3/envs/gemini/bin/python
KEYFILE=/home/weihanxu/.gemini_api_key

GEMINI_API_KEY="$(cat "$KEYFILE" 2>/dev/null)"
if [ -z "$GEMINI_API_KEY" ]; then echo "no key in $KEYFILE; refusing to start" >&2; exit 2; fi
export GEMINI_API_KEY

run_clip30() {
  local seed="$1"
  echo "===== seed${seed}: program / clip30 / gemini+qwen · $(date '+%F %T')"
  PYRAMID_SEED="$seed" "$PY" "$HERE/orchestrate.py" \
    --arm pooled --mode clip30 --agents gemini,qwen --no-gate --select program
}

run_blind() {
  local seed="$1" root="/mnt/work_new/weihanxu/output/pyramid_seed${1}" level agent interp q out
  echo "===== seed${seed}: blind on the clip30 sets · $(date '+%F %T')"
  for level in 1 2 3 4; do
    q="$root/sets/pooled_clip30/pooled/L${level}.json"
    [ -f "$q" ] || { echo "!! missing $q" >&2; return 1; }
    for agent in gemini qwen; do
      [ "$agent" = gemini ] && interp="$GEM_PY" || interp="$PY"
      out="$root/results/pooled_clip30_blind/$agent/L${level}.jsonl"
      mkdir -p "$(dirname "$out")"
      # PYRAMID_SEED must match, or the rows get stamped with the default seed
      PYRAMID_SEED="$seed" "$interp" "$HERE/evaluate.py" --agent "$agent" \
        --questions "$q" --out "$out" --mode blind || echo "!! blind failed: seed${seed} ${agent} L${level}" >&2
    done
  done
}

for seed in 45 46; do
  if run_clip30 "$seed"; then
    run_blind "$seed" || echo "!! seed${seed} blind incomplete" >&2
  else
    echo "!! seed${seed} clip30 interrupted; continuing" >&2
  fi
done
echo "===== multi-seed 45/46 finished · $(date '+%F %T')"
