#!/bin/bash
# 下载 v31 四个 task 的 HD-EPIC 源视频(P01 / P07 / P09 来自公开数据集 WitneyWW/pyramid2-qwen-data-1028;P08 已随本包一起上传)。
#   ./setup_data.sh            → hd-epic/video/<P>/<video>.mp4
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
DL="hf download"; command -v hf >/dev/null 2>&1 || DL="huggingface-cli download"
$DL WitneyWW/pyramid2-qwen-data-1028 --repo-type dataset --local-dir "$HERE" \
   --include "hd-epic/video/P01/P01-20240203-132119.mp4" "hd-epic/video/P07/P07-20240531-201703.mp4" "hd-epic/video/P09/P09-20240622-154652.mp4"
# P08 不在公开数据集里:从私有 dataset 下(需要有权限的 HF token:export HF_TOKEN=...)
$DL WitneyWW/pyramid2-v31-1104 --repo-type dataset --local-dir "$HERE" --include "hd-epic/video/P08/P08-20240614-125650.mp4" || echo "[setup] P08 视频需要 WitneyWW/pyramid2-v31-1104 的访问权限"
ls -la "$HERE"/hd-epic/video/*/
echo "[setup] done. 之后 export P2_REPO=$HERE 即可(HDEPIC_ROOT / P2_POSE_DIR / P2_ROOT 由 p2config 按 P2_REPO 推出)。"
