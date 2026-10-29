#!/usr/bin/env python3
"""history 标注实验(10-26 用户定)的评测:selfv / goldv 臂(history 抬头标明「自己的未核实回答」/「已核实答案」)与原 self / gold / none 臂比。
核心问题:把下层答案改对(gold)在原来的中性抬头下几乎不翻转上层题;标明「已核实」后模型会不会用上这些事实?
按「本题 history 里有没有 self 答错、且和本题共用证据事件的下层行」分桶(只有这些题 gold 能改到相关事实),逐臂数答错。
用法:python3 label_eval.py p2_hdepicE_1023t_g4_v8 [arms...]"""
import json, sys, collections
from pathlib import Path
import p2config as P
from store import read_jsonl
LAYERS = ["L1", "L2", "L3", "L4"]
ARMS = ("self", "gold", "goldv", "selfv", "none")


def _win(row):
    return [w for m in (row.get("media_refs") or []) for w in (m.get("windows") or [])]


def _overlap(a, b):
    return any(x[0] < y[1] and y[0] < x[1] for x in a for y in b)


def _ev(cands, row):
    c = cands.get(row.get("candidate_id")) or {}
    return set(((c.get("output") or {}).get("private") or {}).get("evidence_refs") or [])


def collect(prefix, arms):
    """每道上层计分题一条:{task, layer, skill, cid, bucket, verdicts{arm}};bucket ∈ ev_wrong / rel_wrong / other_wrong / no_wrong / no_hist。"""
    out = []
    for sd in sorted(P.RUNS.glob(f"{prefix}_self__*")):
        task = sd.name.split("__")[-1]
        cands = {c["candidate_id"]: c for c in read_jsonl(sd / "candidates.jsonl")} if (sd / "candidates.jsonl").exists() else {}
        self_rows = {}
        for L in LAYERS:
            if (sd / L / "history.jsonl").exists():
                for h in read_jsonl(sd / L / "history.jsonl"): self_rows[(L, h["turn"])] = h
        for L in LAYERS:
            per = {}
            for a in arms:
                p = P.RUNS / f"{prefix}_{a}__{task}" / L / "history.jsonl"
                if p.exists(): per[a] = {h["candidate_id"]: h for h in read_jsonl(p) if h.get("verdict") in ("correct", "wrong") and not h.get("item_issue") and h.get("capability_skill") not in P.excluded_skills()}
            if "self" not in per: continue
            for cid, s in per["self"].items():
                ref = per.get("gold", {}).get(cid) or per.get("goldv", {}).get(cid)
                hu = ((ref or {}).get("history_used") or {}); turns = hu.get("turns") or []
                cw, ce = _win(s), _ev(cands, s)
                n_wrong = n_rel_wrong = n_ev_wrong = 0
                for (hl, ht) in turns:
                    h = self_rows.get((hl, ht))
                    if not h or h.get("verdict") != "wrong": continue
                    n_wrong += 1; n_rel_wrong += _overlap(_win(h), cw); n_ev_wrong += bool(_ev(cands, h) & ce)
                bucket = "no_hist" if not turns else ("ev_wrong" if n_ev_wrong else ("rel_wrong" if n_rel_wrong else ("other_wrong" if n_wrong else "no_wrong")))
                out.append({"task": task, "layer": L, "skill": s["capability_skill"], "cid": cid, "bucket": bucket, "n_hist": len(turns), "n_wrong": n_wrong,
                            "verdicts": {a: per[a][cid]["verdict"] for a in per if cid in per[a]}})
    return out


BUCKET_ZH = {"ev_wrong": "history 有 self 答错且共用证据事件的行", "rel_wrong": "有 self 答错且 clip 窗口重叠的行", "other_wrong": "有 self 答错但不相关的行", "no_wrong": "history 全对(gold 与 self 内容相同)", "no_hist": "无 history"}


def section(prefix, arms):
    arms = [a for a in ARMS if a in arms]
    items = collect(prefix, arms)
    if not items: return "(no runs)"
    out = []
    # 1) 同题集正确率
    out.append("| layer | 同题数 | " + " | ".join(f"{a} 对" for a in arms) + " |\n|---|---|" + "---|" * len(arms))
    tot = collections.Counter(); n_tot = 0
    for L in LAYERS:
        rs = [r for r in items if r["layer"] == L and all(a in r["verdicts"] for a in arms)]
        if not rs: continue
        c = {a: sum(r["verdicts"][a] == "correct" for r in rs) for a in arms}
        for a in arms: tot[a] += c[a]
        n_tot += len(rs)
        out.append(f"| {L} | {len(rs)} | " + " | ".join(f"{c[a]} ({c[a] / len(rs):.0%})" for a in arms) + " |")
    out.append(f"| all | {n_tot} | " + " | ".join(f"{tot[a]} ({tot[a] / max(1, n_tot):.0%})" for a in arms) + " |")
    # 2) 翻转
    pairs = [p for p in (("gold", "goldv"), ("self", "goldv"), ("self", "selfv"), ("none", "goldv")) if p[0] in arms and p[1] in arms]
    if pairs:
        out.append("\n逐题翻转(同题):\n\n| layer | " + " | ".join(f"{a}✗→{b}✓ / {a}✓→{b}✗" for a, b in pairs) + " |\n|---|" + "---|" * len(pairs))
        for L in LAYERS:
            rs = [r for r in items if r["layer"] == L]
            cells = []
            for a, b in pairs:
                up = sum(1 for r in rs if r["verdicts"].get(a) == "wrong" and r["verdicts"].get(b) == "correct")
                dn = sum(1 for r in rs if r["verdicts"].get(a) == "correct" and r["verdicts"].get(b) == "wrong")
                n = sum(1 for r in rs if a in r["verdicts"] and b in r["verdicts"])
                cells.append(f"+{up} / −{dn} (n={n})")
            if any(r for r in rs): out.append(f"| {L} | " + " | ".join(cells) + " |")
    # 3) 相关性分桶(L2–L4)
    out.append("\n按「history 里有没有可被 gold 改对的相关行」分桶(L2–L4 合计;每格 = 该臂答错数 / 题数):\n")
    out.append("| 桶 | 题数 | " + " | ".join(f"{a} 错" for a in arms) + " |\n|---|---|" + "---|" * len(arms))
    for b in ("ev_wrong", "rel_wrong", "other_wrong", "no_wrong", "no_hist"):
        rs = [r for r in items if r["bucket"] == b and r["layer"] != "L1"]
        if not rs: continue
        out.append(f"| {BUCKET_ZH[b]} | {len(rs)} | " + " | ".join(f"{sum(r['verdicts'].get(a) == 'wrong' for r in rs)} / {sum(a in r['verdicts'] for r in rs)}" for a in arms) + " |")
    out.append("\n同一桶按层:\n\n| layer | 桶 | 题数 | " + " | ".join(f"{a} 错" for a in arms) + " |\n|---|---|---|" + "---|" * len(arms))
    for L in ("L2", "L3", "L4"):
        for b in ("ev_wrong", "rel_wrong", "other_wrong", "no_wrong"):
            rs = [r for r in items if r["bucket"] == b and r["layer"] == L]
            if rs: out.append(f"| {L} | {b} | {len(rs)} | " + " | ".join(f"{sum(r['verdicts'].get(a) == 'wrong' for r in rs)} / {sum(a in r['verdicts'] for r in rs)}" for a in arms) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    pre = sys.argv[1]; arms = sys.argv[2:] or [a for a in ARMS if list(P.RUNS.glob(f"{pre}_{a}__*"))]
    print(section(pre, arms))
