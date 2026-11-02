"""分片 -> summary.json + 终端矩阵。带 Wilson 置信区间。"""
import json, math, glob, os, collections, argparse
import config as C

TIERS = ["Easy", "Low", "Medium", "High"]
MODES = ["memory", "clip30", "long5m"]


def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0, c - h), 3), round(min(1, c + h), 3))


def _leak():
    """memory 文本直接含 gold 的比例——量化泄漏，说明该档是天花板而非理解。"""
    from timeline_index import TimelineIndex
    import memory as MEM
    d = json.loads((C.SHARED / "chains.json").read_text())
    ix = TimelineIndex(d["video_id"])
    hit = collections.Counter(); tot = collections.Counter()
    for c in d["chains"]:
        txt, _ = MEM.render(ix, c["clip_start"], c["clip_end"])
        for st in c["steps"]:
            tot[st["tier"]] += 1
            if MEM.contains_gold(txt, st["answer"]):
                hit[st["tier"]] += 1
    return {t: round(hit[t] / tot[t], 2) for t in TIERS if tot[t]}


def load(agent):
    out = {}
    for m in MODES:
        p = C.OUT / agent / f"chains_{m}.jsonl"
        if p.exists():
            rows = [json.loads(l) for l in p.open() if l.strip()]
            if rows: out[m] = rows
    return out


def summarize(agent):
    data = load(agent)
    if not data: return None
    s = {"agent": agent, "cells": {}}
    for m, rows in data.items():
        depths = [r["depth"] for r in rows]
        cell = {"n_chains": len(rows),
                "mean_depth": round(sum(depths) / len(depths), 2),
                "depth_hist": dict(sorted(collections.Counter(depths).items())),
                "by_tier": {}, "errors": 0}
        locs, tparse = [], 0
        for t in TIERS:
            turns = [x for r in rows for x in r["turns"] if x["tier"] == t]
            if not turns: continue
            k = sum(x["correct"] for x in turns); n = len(turns)
            # pass_rate：真实 history 下走到该层的（上游全对）
            reach = [x for r in rows for i, x in enumerate(r["turns"])
                     if x["tier"] == t and all(y["correct"] for y in r["turns"][:i])]
            cell["by_tier"][t] = {
                "accuracy": round(k / n, 3), "n": n, "ci95": wilson(k, n),
                "pass_rate": round(sum(x["correct"] for x in reach) / len(reach), 3) if reach else None,
                "n_reached": len(reach)}
        for r in rows:
            for x in r["turns"]:
                if x.get("error"): cell["errors"] += 1
                if x.get("localization_error_sec") is not None:
                    locs.append(x["localization_error_sec"])
                if x.get("parsed_time") is None: tparse += 1
        ntot = sum(len(r["turns"]) for r in rows)
        cell["time_parse_fail_rate"] = round(tparse / max(1, ntot), 3)
        if locs:
            locs_s = sorted(locs)
            cell["localization_error_sec"] = {
                "median": locs_s[len(locs_s) // 2],
                "mean": round(sum(locs) / len(locs), 1), "n": len(locs)}
        if m == "memory":
            cell["memory_contains_gold_frac"] = _leak()
            cell["note"] = "memory 档是检索天花板：gold 直接出现在文本里，不是感知测试"
        allk = sum(x["correct"] for r in rows for x in r["turns"])
        cell["accuracy_overall"] = round(allk / max(1, ntot), 3)
        s["cells"][m] = cell
    return s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--agents", nargs="*")
    a = ap.parse_args()
    agents = a.agents or [d.name for d in C.OUT.iterdir()
                          if d.is_dir() and d.name != "_shared"]
    allsum = {}
    for ag in sorted(agents):
        s = summarize(ag)
        if s: allsum[ag] = s
    (C.OUT / "summary.json").write_text(json.dumps(allsum, ensure_ascii=False, indent=1))

    print(f"{'agent':14s} {'档':8s} {'链':>3} {'mean_depth':>10} {'总正确率':>9} "
          f"{'Easy':>12} {'Low':>12} {'Medium':>12} {'High':>12}")
    print("-" * 104)
    for ag, s in allsum.items():
        for m, c in s["cells"].items():
            cells = []
            for t in TIERS:
                b = c["by_tier"].get(t)
                cells.append(f"{b['accuracy']:.2f}({b['n']})" if b else "  -  ")
            print(f"{ag:14s} {m:8s} {c['n_chains']:>3} {c['mean_depth']:>10.2f} "
                  f"{c['accuracy_overall']:>9.2f} " + " ".join(f"{x:>12s}" for x in cells))
    print(f"\n-> {C.OUT/'summary.json'}")


if __name__ == "__main__":
    main()
