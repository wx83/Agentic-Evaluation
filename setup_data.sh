#!/bin/bash
# 下载源视频:P01 / P07 / P09(…154652)/ P02(…120927)来自公开数据集 WitneyWW/pyramid2-qwen-data-1028;
# P08 ×3、P09 ×2 公开集没有,随本包放在私有 dataset WitneyWW/pyramid2-v31-1104 的 hd-epic/video/(从 HF 下载本包时已一起拿到)。
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
DL="hf download"; command -v hf >/dev/null 2>&1 || DL="huggingface-cli download"
$DL WitneyWW/pyramid2-qwen-data-1028 --repo-type dataset --local-dir "$HERE" \
   --include "hd-epic/video/P01/P01-20240203-132119.mp4" "hd-epic/video/P07/P07-20240531-201703.mp4" "hd-epic/video/P09/P09-20240622-154652.mp4" "hd-epic/video/P02/P02-20240211-120927.mp4"
for v in P08/P08-20240614-125650 P08/P08-20240618-163547 P08/P08-20240617-130401 P09/P09-20240622-162302 P09/P09-20240621-093545; do
  [ -f "$HERE/hd-epic/video/$v.mp4" ] || $DL WitneyWW/pyramid2-v31-1104 --repo-type dataset --local-dir "$HERE" --include "hd-epic/video/$v.mp4" || echo "[setup] $v 需要 WitneyWW/pyramid2-v31-1104 的访问权限(export HF_TOKEN=...)"
done
ls -la "$HERE"/hd-epic/video/*/ ; echo "[setup] done"
