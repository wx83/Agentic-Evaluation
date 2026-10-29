#!/bin/bash
# 两张 H200:每张卡起一个服务器(单线程),端口 8799 / 8800。日志在 logs/。
# 用法:./start_servers.sh [N_GPU=2] [BASE_PORT=8799]
set -u
cd "$(dirname "$0")"
N=${1:-2}; BASE=${2:-8799}; PY=${PY:-python}; mkdir -p logs
export QWEN_PATH=${QWEN_PATH:-$PWD/model/Qwen3-Omni-30B-A3B-Instruct}
for i in $(seq 0 $((N-1))); do
  PORT=$((BASE+i))
  CUDA_VISIBLE_DEVICES=$i nohup $PY qwen_server.py --port $PORT --host 0.0.0.0 > logs/qwen_server_$PORT.log 2>&1 &
  echo "gpu $i -> port $PORT (pid $!)"
done
echo "等 2–3 分钟模型加载完(logs/qwen_server_<port>.log 出现 'listening');然后 python smoke_test.py --url http://127.0.0.1:$BASE"
