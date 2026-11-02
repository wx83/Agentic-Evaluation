#!/bin/bash
# 用法: ./geo3d/run_all.sh <sample 选择...>   (默认 all) —— frames → DA3 → prompts → SAM3 → derive → eval
set -u
HOLI=/home/weihanxu/miniconda3/envs/holi/bin/python
SAMPY=/mnt/work_new/demo_dev/scenebind-interact-demo-v0/SAM/.conda/sam3/bin/python
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
SEL=${@:-all}
export HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
echo "[$(date +%H:%M:%S)] frames"; $HOLI -m geo3d.frames --samples $SEL
echo "[$(date +%H:%M:%S)] da3";    $HOLI -m geo3d.run_da3 --samples $SEL 2>&1 | grep -v "INFO\|Warning\|warn"
echo "[$(date +%H:%M:%S)] prompts"; $HOLI -m geo3d.prompts --samples $SEL
for d in $($HOLI -c "import sys; sys.path.insert(0,'.'); from geo3d import cfg; print(' '.join(str(cfg.clip_dir(s['sample_id'])) for s in cfg.samples('$SEL'.split())))"); do
  echo "[$(date +%H:%M:%S)] sam3 $(basename $d)"; $SAMPY geo3d/track_sam3.py $d 2>&1 | grep -E "^  '|DONE|Traceback|Error"
done
echo "[$(date +%H:%M:%S)] derive"; $HOLI -m geo3d.derive --samples $SEL 2>&1 | grep -v "Warning\|warn"
echo "[$(date +%H:%M:%S)] eval";   $HOLI -m geo3d.eval --samples $SEL 2>&1 | grep -v "Warning\|warn"
echo "[$(date +%H:%M:%S)] GEO3D ALL DONE"
