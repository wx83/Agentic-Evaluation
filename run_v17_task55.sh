#!/bin/bash
# Reproduce the v17 run on the bundled task (P09-20240622-154652, recipe step P09_R02_S07):
#   self arm  (Solver sees its own earlier answers as lower-layer history)
#   goldlive arm (Solver sees the reference answers as history)
# Both arms are run as independent staircases, then scored.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
export P2_REPO=$HERE
export P2_ROOT=${P2_ROOT:-$HERE/pyramid_v2}
export GEMINI_BACKEND=${GEMINI_BACKEND:-google}
export RUN_TAG=${RUN_TAG:-repro}
cd "$HERE/code/bench/pyramid2"
mkdir -p "$P2_ROOT/contracts" "$P2_ROOT/runs"
for ARM in self goldlive; do
  SRC=$P2_ROOT/contracts/p2_hdepicE_1023t_g4_v17_${ARM}__55.json
  RID=p2_v17_${ARM}__55_${RUN_TAG}
  python3 - "$SRC" "$P2_ROOT/contracts/$RID.json" "$RID" <<'PY'
import json, sys
c = json.load(open(sys.argv[1])); c["run_id"] = sys.argv[3]
json.dump(c, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
PY
  python3 cli.py preflight --contract "$P2_ROOT/contracts/$RID.json"
  ./run_smoke.sh "$P2_ROOT/contracts/$RID.json" L1 L2 L3 L4
  python3 cli.py report --run-id "$RID"
  python3 pyramid_score.py "$P2_ROOT/runs/$RID"
done
