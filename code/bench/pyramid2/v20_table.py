#!/usr/bin/env python3
"""11-02:v20 四臂表。self run 的 L3/L4 计分题(已通过必需性校验),与 gold / none / wrong 重放逐题对齐。
用法:python3 v20_table.py <prefix> <task> [<task> ...]"""
import json, sys
from collections import Counter
import p2config as P
R = P.ROOT / "runs"
ARMS = ("gold", "none", "wrong", "corrected", "wrongt")   # 11-02:v21 加 corrected / wrongt(定点)


def rows(run, L):
    p = R / run / L / "history.jsonl"
    return [json.loads(l) for l in open(p)] if p.exists() else []


def main():
    prefix, tasks = sys.argv[1], sys.argv[2:]
    tot = Counter()
    for t in tasks:
        for L in ("L3", "L4"):
            allr = rows(f"p2_hdepicE_1023t_{prefix}_self__{t}", L)
            drop = Counter(h.get("verdict") for h in allr if h.get("verdict") not in ("correct", "wrong"))
            s = {h["candidate_id"]: h for h in allr if h.get("verdict") in ("correct", "wrong")}
            arms = {a: {h["candidate_id"]: h["verdict"] for h in rows(f"p2_hdepicE_1023t_{prefix}_{a}__{t}", L) if h.get("verdict") in ("correct", "wrong")} for a in ARMS}
            print(f"task {t} {L}: 收录 {len(s)} 道(作废: " + ", ".join(f"{k} {v}" for k, v in drop.items()) + ")")
            if not s: continue
            ok = lambda a: sum(1 for c in s if arms[a].get(c) == "correct")
            print(f"   通过: self {sum(1 for h in s.values() if h['verdict']=='correct')}/{len(s)}  " + "  ".join(f"{a} {ok(a)}/{sum(1 for c in s if c in arms[a])}" for a in ARMS if arms[a]))
            flips = Counter()
            for c, h in s.items():
                sv = h["verdict"]
                if arms["gold"].get(c): flips["self✗→gold✓" if sv == "wrong" and arms["gold"][c] == "correct" else "self✓→gold✗" if sv == "correct" and arms["gold"][c] == "wrong" else "gold 同"] += 1
                if arms["wrong"].get(c): flips["self✓→wrong✗" if sv == "correct" and arms["wrong"][c] == "wrong" else "self✗→wrong✓" if sv == "wrong" and arms["wrong"][c] == "correct" else "wrong 同"] += 1
                if arms["none"].get(c): flips["self✓→none✗" if sv == "correct" and arms["none"][c] == "wrong" else "self✗→none✓" if sv == "wrong" and arms["none"][c] == "correct" else "none 同"] += 1
                for a in ("corrected", "wrongt"):
                    if arms[a].get(c): flips[f"self✗→{a}✓" if sv == "wrong" and arms[a][c] == "correct" else f"self✓→{a}✗" if sv == "correct" and arms[a][c] == "wrong" else f"{a} 同"] += 1
            print("   翻转:", dict(flips))
            for c, h in s.items():
                nec = h.get("necessity") or {}
                print(f"     {h['capability_skill'][:22]:22s} t{h['difficulty_level']} self={h['verdict'][:5]} " + " ".join(f"{a}={str(arms[a].get(c))[:5]}" for a in ARMS if arms[a]) + f" | req={len(nec.get('required_facts') or [])} | {h['question'][:70]}")
            tot[L] += len(s)
    print("收录合计:", dict(tot))


if __name__ == "__main__":
    main()
