#!/bin/bash
# 用 v30b 规则跑一个 task 的全四层(L1–L4):./run_full.sh <task>   task ∈ 61 62 63 h1 h2 h3 h4 h5
#   held-out(h1–h5)用这个先产出 L1 / L2,再 ./run_v31.sh hX。每个 task 按 OpenRouter 标价约 $25–40(缓存后实际约六成)。
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
export P2_REPO=$HERE; export P2_ROOT=${P2_ROOT:-$HERE/pyramid_v2}; export GEMINI_BACKEND=${GEMINI_BACKEND:-openrouter}
export HDEPIC_ROOT=${HDEPIC_ROOT:-$HERE/hd-epic}; export P2_POSE_DIR=${P2_POSE_DIR:-$HERE/output/_shared/pose}
C=$P2_ROOT/contracts; R=$P2_ROOT/runs; mkdir -p $R $P2_ROOT/logs
cd "$HERE/code/bench/pyramid2"
t=$1; CT=$C/p2_hdepicE_1023t_g4_v30b_self__$t.json; RID=p2_hdepicE_1023t_g4_v30b_self__$t; D=$R/$RID; mkdir -p $D
echo "[$(date +%T)] $RID: L1 L2 L3 L4 (resumable: rerun the same command to continue)"
for i in 1 2 3 4 5 6; do python3 cli.py run --contract $CT --levels L1 L2 L3 L4 >> $D/nohup.log 2>&1 && break; echo "[$(date +%T)] exited $? - retry in 60 s" >> $D/nohup.log; sleep 60; done
python3 pyramid_score.py $D | head -n 30; python3 diag_run.py $D
