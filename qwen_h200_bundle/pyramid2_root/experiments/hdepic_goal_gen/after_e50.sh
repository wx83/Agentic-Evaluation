#!/bin/bash
# Method E ×50 入库(10-25 用户定):等 3 个 shard 跑完 → audio_tags → 样本 = 原 10 个 + 50 个目标 step(sub-goal ≥ 3)→ 重建 hdepic_e 的 media / evidence(增量,其它数据集不动)
set -u
H=/mnt/work_new/weihanxu/experiments/hdepic_goal_gen; L=/mnt/work_new/weihanxu/logs/method_e50; PY=/home/weihanxu/miniconda3/bin/python3
until [ $(grep -l SHARD_DONE $L/shard0.log $L/shard1.log $L/shard2.log 2>/dev/null | wc -l) -ge 3 ]; do sleep 300; done
echo "[$(date +%T)] shards done; failures: $(grep -c FAILED $L/shard*.log | tr '\n' ' ')"
cd $H
NEW=$($PY - <<'PYEOF'
import json, os
d=json.load(open("out/picks/e50_steps.json")); first={}
for p in d["pairs"]: first.setdefault(p["video"], p["recipe"])
dirs=[f"out/E/{p['video']}" if first[p['video']]==p['recipe'] else f"out/E/{p['video']}__{p['recipe']}" for p in d["pairs"]]
print(" ".join(x for x in dirs if os.path.exists(f"{x}/merged.json")))
PYEOF
)
echo "[$(date +%T)] E dirs with merged.json: $(echo $NEW | wc -w) / 40"
$PY -I audio_tags.py $NEW 2>&1 | tail -n 3
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
$PY - <<'PYEOF'
import json, random, collections
from adapters import hdepic_methode as HM
targets={f"{s['video']}__{s['step']}" for s in json.load(open("/mnt/work_new/weihanxu/experiments/hdepic_goal_gen/out/picks/e50_steps.json"))["steps"]}
old=HM.load_samples(); old_ids={s["sample_id"] for s in old}
cands=HM.candidate_steps(min_sub=3)
by_vid=collections.defaultdict(list)
for c in cands: by_vid[c["video_id"]].append(c)
new=[]
for c in cands:
    if c["sample_id"] in targets and c["sample_id"] not in old_ids:
        ch,gold=HM._choices(c, by_vid[c["video_id"]], random.Random(f"1023|{c['sample_id']}"))
        c=dict(c); c["next_action"]={"text": HM.COMPLETE, "choices": ch, "gold_letter": gold}; new.append(c)
miss=sorted(targets-{c["sample_id"] for c in cands})
doc=json.loads(HM.SAMPLES.read_text()); doc["samples"]=old+new; doc["rule"]=doc.get("rule","")+" | 10-25: + 50 dense unseen steps (out/picks/e50_steps.json), sub-goals >= 3"
HM.SAMPLES.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
print(f"samples: {len(old)} old + {len(new)} new = {len(old)+len(new)}; targets without >=3 sub-goals or missing: {len(miss)} {miss[:8]}")
print("sub-goals per new sample:", sorted(len(c["steps"]) for c in new))
PYEOF
GEMINI_BACKEND=nv $PY build_data.py media --only hdepic_e 2>&1 | tail -n 2
GEMINI_BACKEND=nv $PY build_data.py evidence --only hdepic_e 2>&1 | tail -n 4
$PY - <<'PYEOF'
from store import Store
S=Store(); segs=[r for r in S.evidence.values() if r["kind"]=="task_segment" and r["provenance"].get("dataset")=="hdepic_e" and r.get("event_id")]
print("hdepic_e task_segments in store:", len(segs))
PYEOF
echo "[$(date +%T)] E50_DONE"
