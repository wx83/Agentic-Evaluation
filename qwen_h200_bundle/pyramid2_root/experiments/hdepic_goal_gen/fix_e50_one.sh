#!/bin/bash
# 补跑 Method E 失败的那一对(P09-20240622-150155 P09_R02,模型引用了不存在的 action_id),再把它的 2 个目标 step 加进样本并增量重建 evidence
set -u
H=/mnt/work_new/weihanxu/experiments/hdepic_goal_gen; PY=/home/weihanxu/miniconda3/bin/python3
cd $H && $PY -I - <<'PYEOF'
import sys, os; sys.path.insert(0, "."); import method_e
od="out/E/P09-20240622-150155"; method_e.run("P09-20240622-150155", "P09_R02", od); print("merged:", os.path.exists(f"{od}/merged.json"))
PYEOF
$PY -I audio_tags.py out/E/P09-20240622-150155 | tail -n 1
cd /mnt/work_new/weihanxu/agent/bench/pyramid2 && $PY - <<'PYEOF'
import json, random, collections
from adapters import hdepic_methode as HM
targets={f"{s['video']}__{s['step']}" for s in json.load(open("/mnt/work_new/weihanxu/experiments/hdepic_goal_gen/out/picks/e50_steps.json"))["steps"]}
old=HM.load_samples(); old_ids={s["sample_id"] for s in old}
cands=HM.candidate_steps(min_sub=3); by_vid=collections.defaultdict(list)
for c in cands: by_vid[c["video_id"]].append(c)
new=[]
for c in cands:
    if c["sample_id"] in targets and c["sample_id"] not in old_ids:
        ch,gold=HM._choices(c, by_vid[c["video_id"]], random.Random(f"1023|{c['sample_id']}")); c=dict(c); c["next_action"]={"text": HM.COMPLETE, "choices": ch, "gold_letter": gold}; new.append(c)
doc=json.loads(HM.SAMPLES.read_text()); doc["samples"]=old+new; HM.SAMPLES.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
print(f"samples now {len(old)+len(new)} (+{len(new)}: {[c['sample_id'] for c in new]})")
PYEOF
GEMINI_BACKEND=nv $PY build_data.py media --only hdepic_e 2>&1 | tail -n 1
GEMINI_BACKEND=nv $PY build_data.py evidence --only hdepic_e 2>&1 | grep -E "task_segment|task_step"
echo "[$(date +%T)] E50_FIX_DONE"
