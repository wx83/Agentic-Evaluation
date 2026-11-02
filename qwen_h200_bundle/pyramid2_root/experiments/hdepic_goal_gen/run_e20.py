#!/usr/bin/env python3
"""Run Method E on the 20 audio-ranked HD-EPIC goals (av_goals_top20/top20_hd-epic.json). Usage: python -I run_e20.py <shard>/<n>"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import method_e
G = json.load(open("/mnt/work_new/weihanxu/experiments/av_goals_top20/top20_hd-epic.json"))["goals"]
pairs = [(g["recording"], g["goal_id"].split("@")[0]) for g in G]
seen = {}
for i, (v, rid) in enumerate(pairs):  # a recording with two recipes gets a second output dir <vid>__<rid>
    seen.setdefault(v, []).append(i)
def out_dir(v, rid): return f"{HERE}/out/E/{v}" if seen[v][0] == pairs.index((v, rid)) else f"{HERE}/out/E/{v}__{rid}"
k, n = (int(x) for x in sys.argv[1].split("/")) if len(sys.argv) > 1 else (0, 1)
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else len(pairs)   # only the first LIMIT goals of the ranking
for vid, rid in pairs[:LIMIT][k::n]:
    od = out_dir(vid, rid)
    if os.path.exists(f"{od}/merged.json"): print("skip", od); continue
    print("==", vid, rid, "->", od, flush=True); method_e.run(vid, rid, od)
