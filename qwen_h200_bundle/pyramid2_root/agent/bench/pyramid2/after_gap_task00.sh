#!/bin/bash
# L4 gap filling pilot on task 00: g4 self -> g4 gold/none ; qwen self -> qwen gold/none ; merge+report+page push
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs
run_agent() {
  AG=$1
  GEMINI_BACKEND=nv $PY cli.py run --contract $C/p2_hdepicE_1023t_${AG}_gap_self__00.json --levels L4 || GEMINI_BACKEND=nv $PY cli.py run --contract $C/p2_hdepicE_1023t_${AG}_gap_self__00.json --levels L4
  echo "[$(date +%T)] $AG gap self done"
  for arm in gold none; do
    GEMINI_BACKEND=nv $PY cli.py replay --contract $C/p2_hdepicE_1023t_${AG}_gap_${arm}__00.json --from-run p2_hdepicE_1023t_${AG}_gap_self__00 --levels L4
    echo "[$(date +%T)] $AG gap $arm done"
  done
}
run_agent g4 &
P1=$!
run_agent qwen &
P2=$!
wait $P1 $P2
for AG in g4 qwen; do $PY merge_runs.py p2_hdepicE_1023t_${AG}_gap_self p2_hdepicE_1023t_${AG}_gap_gold p2_hdepicE_1023t_${AG}_gap_none; done
GEMINI_BACKEND=nv $PY daily_1023.py --agents g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap --out /mnt/work_new/weihanxu/experiments/daily_report/1024_gap_task00.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
$PY build.py --agents g4=p2_hdepicE_1023t_g4 qwen=p2_hdepicE_1023t_qwen g4_gap=p2_hdepicE_1023t_g4_gap qwen_gap=p2_hdepicE_1023t_qwen_gap --extra qwen_on_g4set=p2_hdepicE_1023t_qwen_on_g4set
HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py
echo "[$(date +%T)] GAP_TASK00_PUSHED"
