#!/usr/bin/env python3
"""11-01:必需性分类。对一个 self run 的 L3/L4 计分题,用同题的 none 臂(看 clip、不带 history)和 gold 臂(history = 参考答案)分类:
  依赖题 = none 错 且 gold 对;独立题 = none 对;坏题 = none 错 且 gold 错。再给 self / gold / none 的通过率与 self→gold 翻转。
用法:python3 necessity.py <prefix> <task> [<task> ...]   例:python3 necessity.py g4_v19 13 55 39"""
import json, os, sys
import p2config as P
R = P.ROOT / "runs"


def rows(run, L):
    p = R / run / L / "history.jsonl"
    return [json.loads(l) for l in open(p)] if p.exists() else []


def classify(prefix, task):
    out = {}
    for L in ("L3", "L4"):
        s = {h["candidate_id"]: h for h in rows(f"p2_hdepicE_1023t_{prefix}_self__{task}", L) if h.get("verdict") in ("correct", "wrong")}
        g = {h["candidate_id"]: h["verdict"] for h in rows(f"p2_hdepicE_1023t_{prefix}_gold__{task}", L) if h.get("verdict") in ("correct", "wrong")}
        n = {h["candidate_id"]: h["verdict"] for h in rows(f"p2_hdepicE_1023t_{prefix}_none__{task}", L) if h.get("verdict") in ("correct", "wrong")}
        items = []
        for cid, h in s.items():
            if cid not in g or cid not in n: continue
            cls = "independent" if n[cid] == "correct" else ("dependent" if g[cid] == "correct" else "bad")
            items.append({"cid": cid, "skill": h["capability_skill"], "tier": h["difficulty_level"], "self": h["verdict"], "gold": g[cid], "none": n[cid], "cls": cls, "q": (h.get("question") or "")[:110]})
        out[L] = items
    return out


def main():
    prefix, tasks = sys.argv[1], sys.argv[2:]
    tot = {L: {"dependent": 0, "independent": 0, "bad": 0, "n": 0} for L in ("L3", "L4")}
    for t in tasks:
        res = classify(prefix, t)
        for L, items in res.items():
            if not items: print(f"task {t} {L}: no overlapping items"); continue
            c = {k: sum(1 for x in items if x["cls"] == k) for k in ("dependent", "independent", "bad")}
            acc = {a: sum(1 for x in items if x[a] == "correct") for a in ("self", "gold", "none")}
            print(f"task {t} {L}: n={len(items)} 依赖 {c['dependent']} 独立 {c['independent']} 坏 {c['bad']} | 通过 self {acc['self']} gold {acc['gold']} none {acc['none']} | self✗→gold✓ {sum(1 for x in items if x['self']=='wrong' and x['gold']=='correct')}")
            for x in items:
                if x["cls"] == "dependent": print(f"    依赖题: {x['skill'][:22]} t{x['tier']} self={x['self']} | {x['q']}")
            for k in c: tot[L][k] += c[k]
            tot[L]["n"] += len(items)
    print("合计:", {L: v for L, v in tot.items()})


if __name__ == "__main__":
    main()
