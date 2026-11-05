#!/bin/bash
# 跑 v31(三个时空推理 L3 skill,只跑 L3):./run_v31.sh [task ...]   默认 61 62 13 55
#   L1 / L2 的 history 来自已带的 seed run(61/62 ← v30b,13/55 ← v28),脚本先把它们复制进本 run 目录。
#   需要:OPENROUTER_API_KEY(或 .secrets/openrouter_key 文件)、ffmpeg / ffprobe、hd-epic/video 下的源视频(setup_data.sh)。
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
export P2_REPO=$HERE; export P2_ROOT=${P2_ROOT:-$HERE/pyramid_v2}; export GEMINI_BACKEND=${GEMINI_BACKEND:-openrouter}
export HDEPIC_ROOT=${HDEPIC_ROOT:-$HERE/hd-epic}; export P2_POSE_DIR=${P2_POSE_DIR:-$HERE/output/_shared/pose}
C=$P2_ROOT/contracts; R=$P2_ROOT/runs; mkdir -p $R $P2_ROOT/logs
cd "$HERE/code/bench/pyramid2"
declare -A SEED=([61]=p2_hdepicE_1023t_g4_v30b_self__61 [62]=p2_hdepicE_1023t_g4_v30b_self__62 [13]=p2_hdepicE_1023t_g4_v28_self__13 [55]=p2_hdepicE_1023t_g4_v28_self__55)
for t in ${@:-61 62 13 55}; do
  CT=$C/p2_hdepicE_1023t_g4_v31_self__$t.json; RID=p2_hdepicE_1023t_g4_v31_self__$t; D=$R/$RID; mkdir -p $D
  for L in L1 L2; do [ -d $D/$L ] || { [ -d $R/${SEED[$t]}/$L ] && cp -r $R/${SEED[$t]}/$L $D/; }; done
  [ -d $D/L2 ] || echo "[warn] task $t: no L2 seed yet (v30b L2 for 61/62 is not in this bundle until v30b finishes); history will have L1 only"
  echo "[$(date +%T)] $RID: sg-dry (pools)"; python3 cli.py sg-dry --contract $CT > /dev/null && grep -A1 "object_location_at_event\|object_displacement_direction\|object_identity_continuity" $D/sg_dry.md | grep "###"
  echo "[$(date +%T)] $RID: run L3"
  for i in 1 2 3 4; do python3 cli.py run --contract $CT --levels L3 >> $D/nohup.log 2>&1 && break; echo "[$(date +%T)] exited $? - retry in 60 s" >> $D/nohup.log; sleep 60; done
  python3 pyramid_score.py $D | head -n 20
done
echo "[$(date +%T)] ALL DONE"
