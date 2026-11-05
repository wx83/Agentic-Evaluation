#!/bin/bash
# 跑 v31(三个时空推理 L3 skill,只跑 L3):./run_v31.sh [task ...]   task ∈ 61 62 13 55 h1 h2 h3 h4 h5(默认 61 62 13 55)
#   L1 / L2 的 history 来自 seed run:61/62/63 ← v30b,13/55 ← v28,h1–h5 ← 先用 ./run_full.sh hX 跑一次 v30b 全四层。
#   需要:OPENROUTER_API_KEY(或 .secrets/openrouter_key)、ffmpeg / ffprobe、hd-epic/video 下的源视频(setup_data.sh)。
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
export P2_REPO=$HERE; export P2_ROOT=${P2_ROOT:-$HERE/pyramid_v2}; export GEMINI_BACKEND=${GEMINI_BACKEND:-openrouter}
export HDEPIC_ROOT=${HDEPIC_ROOT:-$HERE/hd-epic}; export P2_POSE_DIR=${P2_POSE_DIR:-$HERE/output/_shared/pose}
C=$P2_ROOT/contracts; R=$P2_ROOT/runs; mkdir -p $R $P2_ROOT/logs
cd "$HERE/code/bench/pyramid2"
seed_of(){ case $1 in 13|55) echo p2_hdepicE_1023t_g4_v28_self__$1;; *) echo p2_hdepicE_1023t_g4_v30b_self__$1;; esac; }
for t in ${@:-61 62 13 55}; do
  CT=$C/p2_hdepicE_1023t_g4_v31_self__$t.json; RID=p2_hdepicE_1023t_g4_v31_self__$t; D=$R/$RID; SEED=$(seed_of $t); mkdir -p $D
  for L in L1 L2; do [ -d $D/$L ] || { [ -d $R/$SEED/$L ] && cp -r $R/$SEED/$L $D/; }; done
  [ -d $D/L2 ] || echo "[warn] $t: no L2 seed ($SEED/L2 missing) - run ./run_full.sh $t first; proceeding with L1 history only"
  echo "[$(date +%T)] $RID: sg-dry (pools, no API cost except the cached planner)"; python3 cli.py sg-dry --contract $CT > /dev/null && grep "^### object_location_at_event\|^### object_displacement_direction\|^### object_identity_continuity" $D/sg_dry.md
  echo "[$(date +%T)] $RID: run L3"
  for i in 1 2 3 4; do python3 cli.py run --contract $CT --levels L3 >> $D/nohup.log 2>&1 && break; echo "[$(date +%T)] exited $? - retry in 60 s" >> $D/nohup.log; sleep 60; done
  python3 pyramid_score.py $D | head -n 20; python3 diag_run.py $D
done
echo "[$(date +%T)] ALL DONE"
