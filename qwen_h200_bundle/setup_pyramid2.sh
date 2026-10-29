#!/bin/bash
# 在新机器(tillicum)上把 pyramid2 装好:下载数据(private HF dataset)→ 把原机器写死的绝对路径换成本地路径。可重复运行。
# 用法:HF_TOKEN=... ./setup_pyramid2.sh [--with-videos]
#   --with-videos:再下载 49 个 HD-EPIC 原视频(68 GB),只有跑新 task / 新 clip 窗口才需要;已切好的 clip 已在数据里。
set -eu
cd "$(dirname "$0")"
ROOT=$PWD/pyramid2_root
REPO=WitneyWW/pyramid2-qwen-data-1028
DL="hf download"; command -v hf >/dev/null || DL="huggingface-cli download"

echo "[setup] downloading data -> $ROOT"
EXCL="--exclude hd-epic/video/*"; [ "${1:-}" = "--with-videos" ] && EXCL=""
$DL $REPO --repo-type dataset --local-dir "$ROOT" $EXCL

# 原机器路径 -> 本地路径(只改文本文件;用标记文件记录改到哪个 ROOT,重复运行时只改新下载的)
MARK=$ROOT/.paths_rewritten_to
if [ "$(cat $MARK 2>/dev/null)" != "$ROOT" ] || [ "${1:-}" = "--with-videos" ]; then
  echo "[setup] rewriting hard-coded paths"
  grep -rlIZ --include='*.py' --include='*.sh' --include='*.json' --include='*.jsonl' --include='*.md' \
       -e '/mnt/work_new/weihanxu' -e '/mnt/data_new/hd-epic' -e '/home/weihanxu/miniconda3' "$ROOT" \
  | xargs -0 -r sed -i \
      -e "s|/mnt/data_new/hd-epic|$ROOT/hd-epic|g" \
      -e "s|/mnt/work_new/weihanxu|$ROOT|g" \
      -e "s|/home/weihanxu/miniconda3/envs/timechatcap/bin/python|python3|g" \
      -e "s|/home/weihanxu/miniconda3/bin/python3|python3|g"
  echo "$ROOT" > $MARK
fi
mkdir -p "$ROOT/logs/pyramid2"
echo "[setup] done. 下一步见 README 第 8 节。"
