#!/bin/bash
# Reproducible, resumable multi-seed queue for the finalized clip30 pyramid.
# Usage: GEMINI_API_KEY=... ./run_multiseed_44_46.sh [pid-to-wait-for]
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PY=/home/weihanxu/miniconda3/envs/timechatcap/bin/python
GEM_PY=/home/weihanxu/miniconda3/envs/gemini/bin/python
QWEN_PY=/home/weihanxu/miniconda3/envs/timechatcap/bin/python
WAIT_PID="${1:-}"

if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "GEMINI_API_KEY is not set; refusing to start." >&2
  exit 2
fi

if [ -n "$WAIT_PID" ]; then
  echo "Waiting for active seed44 orchestrator PID $WAIT_PID ..."
  while kill -0 "$WAIT_PID" 2>/dev/null; do
    sleep 30
  done
fi

run_clip30() {
  local seed="$1"
  echo "===== seed${seed}: program / clip30 / gemini+qwen ====="
  PYRAMID_SEED="$seed" "$PY" "$HERE/orchestrate.py" \
    --arm pooled --mode clip30 --agents gemini,qwen --no-gate --select program
}

run_blind() {
  local seed="$1"
  local root="/mnt/work_new/weihanxu/output/pyramid_seed${seed}"
  local level agent interp questions out
  echo "===== seed${seed}: blind on the exact clip30 question sets ====="
  for level in 1 2 3 4; do
    questions="$root/sets/pooled_clip30/pooled/L${level}.json"
    if [ ! -f "$questions" ]; then
      echo "Missing $questions; blind seed${seed} is incomplete." >&2
      return 1
    fi
    for agent in gemini qwen; do
      if [ "$agent" = gemini ]; then
        interp="$GEM_PY"
      else
        interp="$QWEN_PY"
      fi
      out="$root/results/pooled_clip30_blind/$agent/L${level}.jsonl"
      mkdir -p "$(dirname "$out")"
      "$interp" "$HERE/evaluate.py" --agent "$agent" \
        --questions "$questions" --out "$out" --mode blind
    done
  done
}

# Every stage is resumable. Re-running seed44 first fills anything left by an
# interrupted foreground process without changing completed JSONL rows.
for seed in 44 45 46; do
  if run_clip30 "$seed"; then
    run_blind "$seed" || echo "!!!!! seed${seed} blind interrupted" >&2
  else
    echo "!!!!! seed${seed} clip30 interrupted; continuing to next seed" >&2
  fi
done

echo "===== multi-seed queue finished ====="
