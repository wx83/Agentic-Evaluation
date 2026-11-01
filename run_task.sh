#!/bin/bash
# Run one task of one benchmark version with one or more arms.
#   ./run_task.sh <prefix> <task> <arm> [<arm> ...]
#   prefix = contract family, e.g. g4_v16 | g4_v16qa | g4_v17 | g4_v18 | qwen_v17 | qwen_v18b   (contracts/p2_hdepicE_1023t_<prefix>_<arm>__<task>.json)
#   task   = two-digit HD-EPIC Method-E task index (55, 39, 05, 13, ...; the bundled data covers 55 only, see README §2/§4)
#   arms   = self | goldlive            -> full L1-L4 run with its own staircase (cli.py run, resumable)
#            gold | blindnone | blindgl | blind -> replay of the matching self / goldlive run (same items, different history / no clip)
# Examples:  ./run_task.sh g4_v16 55 self goldlive blindnone blindgl
#            ./run_task.sh g4_v18 55 self gold          (gold = corrected arm, replays L3 L4 of the self run)
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
export P2_REPO=$HERE
export P2_ROOT=${P2_ROOT:-$HERE/pyramid_v2}
export GEMINI_BACKEND=${GEMINI_BACKEND:-google}
PFX=$1; T=$2; shift 2
C=$P2_ROOT/contracts; R=$P2_ROOT/runs
cd "$HERE/code/bench/pyramid2"
log() { echo "[$(date +%T)] $*"; }
for ARM in "$@"; do
  CT=$C/p2_hdepicE_1023t_${PFX}_${ARM}__${T}.json
  [ -f "$CT" ] || { echo "no contract $CT"; exit 1; }
  RID=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['run_id'])" "$CT")
  case $ARM in
    self|goldlive)
      log "$RID: full run L1-L4"; python3 cli.py preflight --contract "$CT"
      ./run_smoke.sh "$CT" L1 L2 L3 L4
      python3 cli.py report --run-id "$RID" || true
      python3 pyramid_score.py "$R/$RID" | head -n 1 ;;
    gold)                       # corrected arm: same items as self, lower-layer history = reference answers
      SRC=p2_hdepicE_1023t_${PFX}_self__${T}; LV=${REPLAY_LEVELS:-L1 L2 L3 L4}
      log "$RID: replay $LV from $SRC"; python3 cli.py replay --contract "$CT" --from-run "$SRC" --levels $LV ;;
    blindnone|blind)            # blind baseline of the self run: no clip, no history
      SRC=p2_hdepicE_1023t_${PFX}_self__${T}
      log "$RID: blind replay from $SRC"; python3 cli.py replay --contract "$CT" --from-run "$SRC" ;;
    blindgl)                    # blind baseline of the goldlive run
      SRC=p2_hdepicE_1023t_${PFX}_goldlive__${T}
      log "$RID: blind replay from $SRC"; python3 cli.py replay --contract "$CT" --from-run "$SRC" ;;
    *) echo "unknown arm $ARM"; exit 1 ;;
  esac
done
log "done"
