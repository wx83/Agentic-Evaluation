#!/bin/bash
# 10-27 晚(用户:按 v13 harness 评测 AEA,先跑一个 task 的 self 臂)。
# 顺序:scope → mock 四层(0 invalid)→ 门:confirmed_<rec>.json 存在才继续(用户确认 SAM3 fixture 后)→ 重建 aea_p_spatial + scope --force → self run 四层 → report。
# 用法:setsid nohup ./run_aeaP_v13.sh > /mnt/work_new/weihanxu/logs/pyramid2/run_aeaP_v13.log 2>&1 < /dev/null &
set -u
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
PY=/home/weihanxu/miniconda3/bin/python3; C=/mnt/work_new/weihanxu/output/pyramid_v2/contracts
REC=loc2_script1_seq6_rec1; SID=${REC}__s1; SELF=p2_aeaP_1027_g4_v13_self__loc2; MOCK=p2_aeaP_1027_mock_v13__loc2
CONF=/mnt/work_new/weihanxu/experiments/aea_protocol/sam3_fixtures/confirmed_${REC}.json
log() { echo "[$(date +%T)] $*"; }
MOCKSCRIPT=$($PY -c "print(','.join(['C']*200))")
log "scope (provisional fixtures)"; GEMINI_BACKEND=nv $PY cli.py scope --contract $C/$SELF.json --task-id $SID 2>&1 | grep -v Warning | tail -5
log "mock run"; rm -rf /mnt/work_new/weihanxu/output/pyramid_v2/runs/$MOCK
GEMINI_BACKEND=nv $PY cli.py run --contract $C/$MOCK.json --levels L1 L2 L3 L4 --mock "$MOCKSCRIPT" > /mnt/work_new/weihanxu/output/pyramid_v2/runs/mock_aeaP_v13.log 2>&1
log "mock invalid/traceback lines: $(grep -c "item_invalid\|Traceback" /mnt/work_new/weihanxu/output/pyramid_v2/runs/mock_aeaP_v13.log)"
log "MOCK_DONE"
until [ -f "$CONF" ]; do log "WAIT_CONFIRMED ($CONF)"; sleep 600; done
log "confirmed list found -> rebuild aea_p_spatial + scope"
$PY build_data.py evidence --only aea_p_spatial 2>&1 | tail -1; $PY build_data.py policy 2>&1 | tail -1
GEMINI_BACKEND=nv $PY cli.py scope --contract $C/$SELF.json --task-id $SID --force 2>&1 | grep -v Warning | tail -3
log "self run"; ./run_smoke.sh $C/$SELF.json L1 L2 L3 L4
$PY cli.py report --run-id $SELF > /dev/null 2>&1
log "AEAP_V13_SELF_DONE"
