#!/bin/bash
# 10-28(用户定):qwen_v14 = g4_v14 配置,Qwen3-Omni 做 Examiner + scope planner + Solver,task 09;self 阶梯 → gold 重放 → 合并 / 打分 / 与 g4_v14 对比 / Space。
# 不含任何 pkill / kill:旧 Qwen 客户端(logs/pyramid2/qwen_paused_pids_1027.txt)保持 SIGSTOP;qwen_server 若已被别的 run 起着就共用(单线程,请求排队)。
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; QPY=/home/weihanxu/miniconda3/envs/timechatcap/bin/python
C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts; R=/mnt/work_new/weihanxu/output/pyramid_v2/runs; LOG=/mnt/work_new/weihanxu/logs/pyramid2; D=/mnt/work_new/weihanxu/experiments/daily_report
TID=P08-20240617-184909__P08_R07_S09; SELF=p2_hdepicE_1023t_qwen_v14_self__09; GOLD=p2_hdepicE_1023t_qwen_v14_gold__09
log() { echo "[$(date +%T)] $*"; }
up() { ss -ltn 2>/dev/null | grep -q "127.0.0.1:8799 "; }   # 服务器不答 GET,按监听端口判断
if ! up; then
  log "starting qwen_server on 8799"; nohup $QPY qwen_server.py --port 8799 >> $LOG/qwen_server.log 2>&1 &
  for i in $(seq 1 90); do up && break; sleep 10; done; up || { log "QWEN_SERVER_FAILED"; exit 1; }
fi
log "qwen_server up"
log "scope (Qwen) task 09"
GEMINI_BACKEND=nv $PY cli.py scope --contract $C/$SELF.json --task-id $TID --force 2>&1 | grep -v Warning | tail -n 3
grep -q '"status": "ok"' $R/$SELF/scope/$TID.json 2>/dev/null || { log "QWEN_SCOPE_FAILED"; exit 1; }
log "qwen v14 task 09 self"
./run_smoke.sh $C/$SELF.json L1 L2 L3 L4
log "qwen v14 task 09 gold replay"
GEMINI_BACKEND=nv $PY cli.py replay --contract $C/$GOLD.json --from-run $SELF 2>&1 | grep -v Warning | tail -n 3
$PY merge_runs.py p2_hdepicE_1023t_qwen_v14_self p2_hdepicE_1023t_qwen_v14_gold
$PY pyramid_score.py $R/$SELF | head -n 6
$PY compare_budget.py p2_hdepicE_1023t_g4_v14_self__09 $SELF $GOLD > $D/1028_qwen_v14_vs_g4_v14_t09.md
cd /mnt/work_new/weihanxu/hf_space_pyramid2_hdepic_e_1023
grep -q '^qwen_v14=' latest_only.txt || printf 'qwen_v14=p2_hdepicE_1023t_qwen_v14\n' >> latest_only.txt
GEMINI_BACKEND=nv $PY build.py 2>&1 | grep -v Warning | tail -n 2 && HF_TOKEN=$(cat /mnt/work_new/weihanxu/holi/.secrets/hf_token) $PY push.py 2>&1 | tail -n 1
log "QWEN_V14_DONE (task 09 self + gold)"
