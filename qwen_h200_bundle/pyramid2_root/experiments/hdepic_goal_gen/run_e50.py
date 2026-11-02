#!/usr/bin/env python3
"""Run Method E on the 40 (video, recipe) pairs behind the 50 dense unseen steps (out/picks/e50_steps.json). Usage: python -I run_e50.py <shard>/<n>"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import method_e
pairs = [(p["video"], p["recipe"]) for p in json.load(open(f"{HERE}/out/picks/e50_steps.json"))["pairs"]]
first = {}
for v, r in pairs: first.setdefault(v, r)
def out_dir(v, r): return f"{HERE}/out/E/{v}" if first[v] == r else f"{HERE}/out/E/{v}__{r}"
k, n = (int(x) for x in sys.argv[1].split("/")) if len(sys.argv) > 1 else (0, 1)
for vid, rid in pairs[k::n]:
    od = out_dir(vid, rid)
    if os.path.exists(f"{od}/merged.json"): print("skip", od, flush=True); continue
    print("==", vid, rid, "->", od, flush=True)
    try: method_e.run(vid, rid, od)
    except Exception as e: print("FAILED", vid, rid, repr(e)[:300], flush=True)
print("SHARD_DONE", k, n, flush=True)
