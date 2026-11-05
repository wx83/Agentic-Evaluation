#!/bin/bash
# 下载 9 个源视频(约 11.7 GB):全部在私有 dataset WitneyWW/pyramid2-v31-1104 的 hd-epic/video/ 下。
# 若你是用 `hf download WitneyWW/pyramid2-v31-1104 --repo-type dataset --local-dir .` 整包下载的,视频已在本地,本脚本只做校验。
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
DL="hf download"; command -v hf >/dev/null 2>&1 || DL="huggingface-cli download"
$DL WitneyWW/pyramid2-v31-1104 --repo-type dataset --local-dir "$HERE" --include "hd-epic/video/*" || echo "[setup] 需要 WitneyWW/pyramid2-v31-1104 的访问权限(export HF_TOKEN=...)"
n=$(ls "$HERE"/hd-epic/video/*/*.mp4 2>/dev/null | wc -l); ls -la "$HERE"/hd-epic/video/*/; echo "[setup] $n / 9 videos present"
