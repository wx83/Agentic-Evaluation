#!/usr/bin/env python3
"""多模型 × 四条件探针对比(2026-10-11):同一题套(gemini-3.5-flash 出题),不同作答模型 / thinking 设置。

读取 <POUT>/results/modality_probe/<backend>/<agent_dir>/L<k>/{av,v_only,a_only,a_swap}.jsonl,
agent_dir ∈ {gemini, gemini@<model>, gemini@<model>+think}(见 pconfig.AGENT_DIR)。

  PYRAMID_SEED=1011 python3 model_compare.py --levels 1,2,3,4
  PYRAMID_SEED=43   python3 model_compare.py --levels 2
-> <POUT>/report/model_compare.md
"""
import argparse, json, collections
from pathlib import Path
import pconfig as P
import modality_probe as MP

LABEL = {"gemini": "gemini-3.5-flash(关 thinking)"}


def label(d):
    if d in LABEL:
        return LABEL[d]
    m = d.split("@", 1)[1]
    return m.replace("+think", "") + ("(开 thinking)" if d.endswith("+think") else "(关 thinking)")


def agent_dirs(backend):
    root = P.POUT / "results" / "modality_probe" / backend
    return sorted(p.name for p in root.iterdir() if p.is_dir() and p.name.startswith("gemini")) if root.exists() else []


def load(backend, d, level):
    R = {c: MP._rows(backend, c, level) for c in []}  # placeholder
    base = P.POUT / "results" / "modality_probe" / backend / d / f"L{level}"
    R = {}
    for c in MP.CONDS:
        f = base / f"{c}.jsonl"
        R[c] = {r["question_id"]: r for r in (json.loads(l) for l in f.open() if l.strip()) if not r.get("error")} if f.exists() else {}
    dm = base / "swap_map.json"
    return R, (json.loads(dm.read_text()) if dm.exists() else {})


def stats(R, donors):
    ids = list(R["av"])
    out = {"n": len(ids)}
    for c in MP.CONDS:
        common = [i for i in ids if i in R[c]]
        out[c] = (sum(bool(R[c][i]["correct"]) for i in common), len(common))
        if c != "av" and common:
            b = sum(R["av"][i]["correct"] and not R[c][i]["correct"] for i in common)
            cc = sum(R[c][i]["correct"] and not R["av"][i]["correct"] for i in common)
            out[c + "_p"] = MP._mcnemar(b, cc)
    avok = [i for i in ids if R["av"][i]["correct"] and i in R["v_only"] and i in R["a_only"]]
    nb = [i for i in avok if not R["v_only"][i]["correct"] and not R["a_only"][i]["correct"]]
    out["needs_both"] = (len(nb), len(avok)); out["nb_ids"] = nb
    n = aud = vis = 0
    for i in ids:
        r = R["a_swap"].get(i); d = donors.get(i)
        if not r or not d:
            continue
        opts = [o.split(". ", 1)[-1].strip().lower() for o in r["options"]]
        if d["donor_answer"].lower() not in opts:
            continue
        n += 1; pi = r.get("parsed_index")
        if pi == r["gold_index"]: vis += 1
        elif pi is not None and opts[pi] == d["donor_answer"].lower(): aud += 1
    out["follow"] = (aud, vis, n)
    lat = sorted(r["latency_sec"] for c in MP.CONDS for r in R[c].values() if r.get("latency_sec") is not None)
    out["lat_med"] = lat[len(lat) // 2] if lat else None
    return out


def pct(c, n):
    return f"{100 * c / n:.0f}% ({c}/{n})" if n else "—"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", default="1,2,3,4")
    ap.add_argument("--backend", default="nv")
    a = ap.parse_args()
    levels = [int(x) for x in a.levels.split(",")]
    dirs = agent_dirs(a.backend)
    L = [f"# 多模型对比(seed {P.SEED},后端 {a.backend},题套由 gemini-3.5-flash 出)", "",
         "同一道题四种输入:av 原 clip / v_only 静音 / a_only 黑屏留音 / a_swap 原画面+另一题音轨。括号「对/题数」,Δ 相对 av,p 为配对 McNemar。", ""]
    allrows = {}
    for lv in levels:
        L += [f"## L{lv}", "", "| 作答模型 | n | av | v_only | a_only | a_swap | needs-both(av 对里) | a_swap 跟声音 / 跟画面(donor 在选项) | 中位延迟 s |", "|---|---|---|---|---|---|---|---|---|"]
        for d in dirs:
            R, donors = load(a.backend, d, lv)
            if not R["av"]:
                continue
            s = stats(R, donors); allrows[(d, lv)] = s
            cells = [pct(*s["av"])]
            for c in ("v_only", "a_only", "a_swap"):
                k, n = s[c]; d_ = 100 * (k / n - s["av"][0] / s["av"][1]) if n else 0
                cells.append(f"{pct(k, n)} {d_:+.0f} pp p={s.get(c + '_p', 1):.2f}" if n else "—")
            aud, vis, n = s["follow"]
            L.append(f"| {label(d)} | {s['n']} | " + " | ".join(cells) + f" | {pct(*s['needs_both'])} | {pct(aud, n)} / {pct(vis, n)} | {s['lat_med']} |")
        L.append("")
    # 合计
    L += ["## 全部层合计", "", "| 作答模型 | n | av | v_only | a_only | a_swap | needs-both | 跟声音 / 跟画面 |", "|---|---|---|---|---|---|---|---|"]
    for d in dirs:
        ss = [allrows[(d, lv)] for lv in levels if (d, lv) in allrows]
        if not ss:
            continue
        tot = lambda key: (sum(s[key][0] for s in ss), sum(s[key][1] for s in ss))
        aud = sum(s["follow"][0] for s in ss); vis = sum(s["follow"][1] for s in ss); n = sum(s["follow"][2] for s in ss)
        L.append(f"| {label(d)} | {sum(s['n'] for s in ss)} | {pct(*tot('av'))} | {pct(*tot('v_only'))} | {pct(*tot('a_only'))} | {pct(*tot('a_swap'))} | {pct(*tot('needs_both'))} | {pct(aud, n)} / {pct(vis, n)} |")
    # 逐题:哪些题三个模型都要「同时看和听」
    L += ["", "## needs-both 题 id(按模型)", ""]
    for d in dirs:
        ids = [f"L{lv}:{i[-3:]}" for lv in levels if (d, lv) in allrows for i in allrows[(d, lv)]["nb_ids"]]
        L.append(f"- {label(d)}:{', '.join(ids) or '无'}")
    txt = "\n".join(L)
    P.REPORT.mkdir(parents=True, exist_ok=True)
    out = P.REPORT / "model_compare.md"; out.write_text(txt); print(txt); print(f"\n-> {out}")


if __name__ == "__main__":
    main()
