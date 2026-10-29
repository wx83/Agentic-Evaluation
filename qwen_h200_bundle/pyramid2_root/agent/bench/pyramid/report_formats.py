"""answer-format 对照试验的汇总:level × format × model × input 的准确率、chance-corrected、
同题配对 vs mc 的 McNemar、tf4 逐项准确率、open 的 rule / judge 占比。

    PYRAMID_SEED=43 python3 report_formats.py            # -> P.REPORT/formats.{json,md}

mc 一档直接读 pooled_clip30(clip30)与 pooled_clip30_blind(blind)里基题的已有结果。
"""
import collections, json, math
from pathlib import Path
import pconfig as P

SLOTS = ["yn", "mc", "ms", "open", "open_x"]
AGENTS = ["gemini", "qwen"]
MODES = ["clip30", "blind"]


def wilson(c, n, z=1.96):
    if not n:
        return (float("nan"), float("nan"))
    p = c / n
    d = 1 + z * z / n
    m = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (m - h, m + h)


def mcnemar(b, c):
    """精确二项检验(b = 只有 A 对,c = 只有 B 对)。"""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def load_rows(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.open() if l.strip()]


def mc_rows(agent, mode, base_ids):
    key = "pooled_clip30" + ("_blind" if mode == "blind" else "")
    out = {}
    for level, ids in base_ids.items():
        want = set(ids)
        for r in load_rows(P.RESULTS / key / agent / f"L{level}.jsonl"):
            if r["question_id"] in want and not r.get("error"):
                out[r["question_id"]] = {"correct": bool(r["correct"]), "fmt": "mc",
                                         "base_id": r["question_id"], "level": int(level),
                                         "subtype": r["subtype"], "score": float(bool(r["correct"])),
                                         "score_by": "rule"}
    return out


def fmt_rows(agent, mode, slot):
    out = {}
    for level in (1, 2, 3, 4):
        for r in load_rows(P.RESULTS / "formats" / agent / mode / f"L{level}_{slot}.jsonl"):
            if not r.get("error"):
                out[r["base_id"]] = dict(r, level=level)
    return out


def main():
    base_ids = json.loads((P.SETS / "formats" / "base_ids.json").read_text())
    rep = {"cells": [], "pairs": [], "tf4": [], "open_scoring": [], "parse_fail": []}
    lines = ["# answer-format 对照(seed %d,每层 %d 基题)\n" % (P.SEED, P.N_FORMAT_PER_LEVEL)]
    for agent in AGENTS:
        for mode in MODES:
            data = {"mc": mc_rows(agent, mode, base_ids)}
            for slot in ("yn", "ms", "open", "open_x"):
                data[slot] = fmt_rows(agent, mode, slot)
            if not any(data[s] for s in SLOTS if s != "mc"):
                continue
            lines.append(f"\n## {agent} × {mode}\n")
            lines.append("| level | " + " | ".join(SLOTS) + " |")
            lines.append("|---|" + "---|" * len(SLOTS))
            for level in (1, 2, 3, 4):
                cells = []
                for slot in SLOTS:
                    rs = [r for r in data[slot].values() if r["level"] == level]
                    # open 档里 open 与 tf4 混合:chance 按各自格式取,再按题数加权
                    n = len(rs)
                    c = sum(bool(r["correct"]) for r in rs if r.get("score_by") != "pending")
                    pend = sum(r.get("score_by") == "pending" for r in rs)
                    if not n:
                        cells.append("—"); continue
                    ch = sum(P.FMT_CHANCE[r.get("fmt", "mc")] for r in rs) / n
                    acc = c / max(1, n - pend)
                    cc = (acc - ch) / (1 - ch) if ch < 1 else float("nan")
                    lo, hi = wilson(c, n - pend)
                    rep["cells"].append({"agent": agent, "mode": mode, "level": level, "slot": slot,
                                         "n": n, "correct": c, "pending": pend, "acc": round(acc, 3),
                                         "chance": round(ch, 3), "chance_corrected": round(cc, 3),
                                         "wilson": [round(lo, 3), round(hi, 3)]})
                    cells.append(f"{acc:.0%} ({c}/{n - pend}, cc {cc:+.2f})" + (f" +{pend} 待判" if pend else ""))
                lines.append(f"| L{level} | " + " | ".join(cells) + " |")
            # 同题配对 vs mc
            lines.append("\n配对 vs mc(同一基题;b = 只有该格式对,c = 只有 mc 对;McNemar 精确):\n")
            for slot in ("yn", "ms", "open", "open_x"):
                both = [(r, data["mc"][bid]) for bid, r in data[slot].items()
                        if bid in data["mc"] and r.get("score_by") != "pending"]
                if not both:
                    continue
                b = sum(bool(r["correct"]) and not m["correct"] for r, m in both)
                c = sum(not r["correct"] and m["correct"] for r, m in both)
                p = mcnemar(b, c)
                rep["pairs"].append({"agent": agent, "mode": mode, "slot": slot, "n": len(both),
                                     "only_fmt": b, "only_mc": c, "p": round(p, 4)})
                lines.append(f"- {slot}: n={len(both)}, 只有 {slot} 对 {b}, 只有 mc 对 {c}, p={p:.3f}")
            # tf4 逐项
            tf = [r for s in ("open", "open_x") for r in data[s].values() if r.get("fmt", "").startswith("tf4")]
            if tf:
                per = sum((r.get("score_detail") or {}).get("per_item", 0) for r in tf) / (4 * len(tf))
                whole = sum(bool(r["correct"]) for r in tf) / len(tf)
                rep["tf4"].append({"agent": agent, "mode": mode, "n": len(tf), "per_item": round(per, 3),
                                   "whole": round(whole, 3)})
                lines.append(f"\ntf4(逐项 True/False,n={len(tf)}):逐项准确率 {per:.0%},整题全对 {whole:.0%}")
            # open 判分来源
            op = [r for s in ("open", "open_x") for r in data[s].values() if r.get("fmt", "").startswith("open")]
            if op:
                by = collections.Counter(r.get("score_by") for r in op)
                rep["open_scoring"].append({"agent": agent, "mode": mode, "n": len(op), **by})
                lines.append(f"open 判分来源(n={len(op)}):{dict(by)}")
            # 解析失败率
            pf = collections.Counter()
            for s in ("yn", "ms", "open", "open_x"):
                for r in data[s].values():
                    pf[r.get("fmt")] += r.get("parsed") is None
            tot = {s: len(data[s]) for s in ("yn", "ms", "open", "open_x")}
            rep["parse_fail"].append({"agent": agent, "mode": mode, "fail": dict(pf), "n": tot})
            lines.append(f"解析失败(parsed=None):{dict(pf)} / 题数 {tot}")
    P.REPORT.mkdir(parents=True, exist_ok=True)
    (P.REPORT / "formats.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    (P.REPORT / "formats.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
