#!/bin/bash
# Download the full evidence store + pre-cut clips (+ optionally the 49 HD-EPIC source videos) so that every task
# in pyramid_v2/contracts can be run, not only the bundled task 55.
#   ./setup_full_data.sh [--with-videos]       (public HF dataset WitneyWW/pyramid2-qwen-data-1028, ~2.8 GB; +11.7 GB with videos)
# Afterwards run everything with  P2_ROOT=$PWD/data_full/output/pyramid_v2  (run_task.sh honours $P2_ROOT).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd); DST=$HERE/data_full; REPO=WitneyWW/pyramid2-qwen-data-1028
DL="hf download"; command -v hf >/dev/null 2>&1 || DL="huggingface-cli download"
INC="--include output/pyramid_v2/data/* output/pyramid_v2/media/* output/_shared/* hd-epic/annotations/*"
[ "${1:-}" = "--with-videos" ] && INC="$INC hd-epic/video/*"
echo "[setup] downloading -> $DST"; $DL $REPO --repo-type dataset --local-dir "$DST" $INC
ROOT=$DST/output/pyramid_v2
echo "[setup] merging this repo's contracts / runs / sub-goal caches into $ROOT"
mkdir -p "$ROOT/contracts" "$ROOT/runs" "$ROOT/data/sg_cache" "$ROOT/logs"
cp -n "$HERE"/pyramid_v2/contracts/*.json "$ROOT/contracts/"; cp -rn "$HERE"/pyramid_v2/runs/* "$ROOT/runs/" 2>/dev/null || true
cp -n "$HERE"/pyramid_v2/data/sg_cache/*.json "$ROOT/data/sg_cache/"
for f in capability_map.json extension_registry.json skill_exclusions.json verification_policy.json; do [ -f "$ROOT/data/$f" ] || cp "$HERE/pyramid_v2/data/$f" "$ROOT/data/"; done
echo "[setup] rewriting the original machine's absolute paths inside the downloaded jsonl/json files"
MARK=$DST/.paths_rewritten_to
if [ "$(cat $MARK 2>/dev/null)" != "$DST" ]; then
  grep -rlIZ --include='*.json' --include='*.jsonl' -e '/mnt/work_new/weihanxu' -e '/mnt/data_new/hd-epic' "$ROOT/data" "$DST/output/_shared" \
    | xargs -0 -r sed -i -e "s|/mnt/data_new/hd-epic|$DST/hd-epic|g" -e "s|/mnt/work_new/weihanxu/output|$DST/output|g" -e "s|/mnt/work_new/weihanxu|$DST|g"
  echo "$DST" > $MARK
fi
cat <<MSG
[setup] done. Use:
  export P2_ROOT=$ROOT
  export P2_POSE_DIR=$DST/output/_shared/pose        # SLAM pose cache (only needed by egocentric_frame_transform, not in v16+)
  export HDEPIC_ANNOT_ROOT=$DST/hd-epic/annotations   # official annotations (gaze priming skill, not in v16+)
  export HDEPIC_ROOT=$DST/hd-epic
  ./run_task.sh g4_v16 13 self goldlive
Without --with-videos only the pre-cut clips are available; a contract that needs a new clip window (e.g. v18's 10 s L4 clips on a task
that was never run with v18) needs the source video of that participant.
MSG
