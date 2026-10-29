#!/bin/bash
# Fill in every Qwen run that Gemini has but Qwen does not.
# Resumable: finished rows in each jsonl are skipped, error rows are retried.
#   setsid nohup ./run_qwen_backfill.sh > /mnt/work_new/weihanxu/logs/qwen_backfill.log 2>&1 &
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PY=/home/weihanxu/miniconda3/envs/timechatcap/bin/python
OUT=/mnt/work_new/weihanxu/output

run() {           # run <seed> <set-arm> <result-arm> <mode>
  local seed="$1" setarm="$2" resarm="$3" mode="$4" level
  for level in 1 2 3 4; do
    local q="$OUT/pyramid_seed${seed}/sets/${setarm}/pooled/L${level}.json"
    local o="$OUT/pyramid_seed${seed}/results/${resarm}/qwen/L${level}.jsonl"
    if [ ! -f "$q" ]; then echo "!! missing set $q" >&2; continue; fi
    echo "===== seed${seed} ${resarm} qwen L${level} (${mode}) · $(date '+%F %T')"
    PYRAMID_SEED="$seed" "$PY" "$HERE/evaluate.py" --agent qwen --mode "$mode" \
      --questions "$q" --out "$o" || echo "!! failed: seed${seed} ${resarm} L${level}" >&2
  done
}

# Cheap text-only passes first: these are what unlock Qwen's video gain.
run 43 pooled_clip30      pooled_clip30_blind     blind
run 44 pooled_clip30      pooled_clip30_blind     blind
run 43 pooled_clip30_cur  pooled_clip30_cur_blind blind
# Slow pass last: 200 clips through the 30B model, roughly 3-4 hours.
run 43 pooled_clip30_cur  pooled_clip30_cur       clip30

echo "===== qwen backfill finished · $(date '+%F %T')"
