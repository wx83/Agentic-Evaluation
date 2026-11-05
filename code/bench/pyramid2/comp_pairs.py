#!/usr/bin/env python3
"""11-03 实验 A / B 汇总:python3 comp_pairs.py <prefix> <tasks...>   例 python3 comp_pairs.py p2_hdepicE_1023t_g4_v24c 55 13 39
实验 A:同 skill 内按 pair_key(task|skill|tier|format|窗长|选项数)配对 weak / strong 前置条件的组合题,报配对正确率差(strong − weak,百分点)、配对数、event 数、两侧准确率、不一致题对数;unpaired / unknown 单列。
实验 B:同一道固定题在 none / self / gold 三臂(replay)的多数票;报 self 错 gold 对、self 对 gold 错 的题数。盲测标记另列。"""
import sys, json, collections, itertools
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import p2config as P

prefix = sys.argv[1]; tasks = sys.argv[2:]
rows = {}      # (task, layer, candidate_id) -> {arm: row}
comp = {}      # candidate_id -> private.comp
for t in tasks:
    for arm in ("self", "none", "gold"):
        rd = P.RUNS / f"{prefix}_{arm}__{t}"
        for L in ("L2", "L3"):
            hp = rd / L / "history.jsonl"
            if not hp.exists(): continue
            for line in open(hp):
                h = json.loads(line)
                if h.get("verdict") not in ("correct", "wrong"): continue
                key = (t, L, h.get("candidate_id"))          # replay 行保留原 candidate_id
                rows.setdefault(key, {})[arm] = h
        cp = rd / "candidates.jsonl"
        if arm == "self" and cp.exists():
            for line in open(cp):
                c = json.loads(line); pri = (c.get("output") or {}).get("private") or {}
                if isinstance(pri, dict) and isinstance(pri.get("comp"), dict): comp[c["candidate_id"]] = pri["comp"]

print("== 实验 A:weak vs strong 前置条件(self 臂,组合题)")
by_skill = collections.defaultdict(lambda: collections.defaultdict(list))
unk = collections.Counter(); n_comp = 0
for (t, L, cid), arms in rows.items():
    h = arms.get("self")
    if not h or cid not in comp: continue
    c = comp[cid]; n_comp += 1
    stt = c["prereq"]["status"]
    if stt == "unknown": unk[h["capability_skill"]] += 1; continue
    by_skill[h["capability_skill"]][c["pair_key"]].append((stt, h["verdict"] == "correct", c["source_event"], t))
print(f"组合题(self)共 {n_comp};unknown 前置 {dict(unk)}")
for sk, groups in by_skill.items():
    pairs = []; unpaired = 0
    for pk, items in groups.items():
        w = [x for x in items if x[0] == "weak"]; s = [x for x in items if x[0] == "strong"]
        if w and s:
            for a, b in itertools.product(w, s): pairs.append((a, b))
        else: unpaired += len(items)
    if not pairs: print(f"  {sk}: 无可配对(unpaired {unpaired})"); continue
    acc_w = sum(1 for a, b in pairs if a[1]) / len(pairs); acc_s = sum(1 for a, b in pairs if b[1]) / len(pairs)
    disc = sum(1 for a, b in pairs if a[1] != b[1]); ev = len({a[2] for a, b in pairs} | {b[2] for a, b in pairs})
    print(f"  {sk}: pairs {len(pairs)}, events {ev}, acc weak {acc_w:.2f} strong {acc_s:.2f}, diff (strong−weak) {100*(acc_s-acc_w):+.0f} pp, discordant {disc}, unpaired {unpaired}")

print("\n== 实验 B:同题三臂(none / self / gold),组合题与非组合题分开")
for comp_only in (True, False):
    cnt = collections.Counter(); n = 0
    for (t, L, cid), arms in rows.items():
        if (cid in comp) != comp_only or not all(a in arms for a in ("none", "self", "gold")): continue
        n += 1; v = {a: arms[a]["verdict"] == "correct" for a in ("none", "self", "gold")}
        cnt["none✓"] += v["none"]; cnt["self✓"] += v["self"]; cnt["gold✓"] += v["gold"]
        cnt["self✗gold✓"] += (not v["self"]) and v["gold"]; cnt["self✓gold✗"] += v["self"] and not v["gold"]
        cnt["blind✓"] += bool(arms["self"].get("blind_guessable"))
    print(f"  {'组合题' if comp_only else '非组合题'}: n={n} " + ", ".join(f"{k} {v_}" for k, v_ in cnt.items()))
