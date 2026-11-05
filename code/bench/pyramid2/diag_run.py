#!/usr/bin/env python3
"""11-04 晚(用户:改动要 general,不能只 tailor 几个 example):每个 run 的三项通用性诊断,换数据集时先看这三项有没有偏。
  ① 盲猜率:每 skill 盲测答对的比例(含作废与仅标记);四选一基线 25%,明显高于基线 = 选项 / 题面泄漏
  ② 字母分布:单选题参考答案落在 A/B/C/D 的分布(卡方对均匀),时间段题单列;四段长度是否一致
  ③ 余量分布:程序出题的几何 / 时间余量(sg.sc.knob / ed.margin / sa.margin / ch.margin / rs.margin)分位数,看档位是否覆盖 1–4
  另:Examiner 调用次数 / turn、校验拒绝次数、作废重出次数(token 浪费)
用法:python3 diag_run.py <run_dir> [<run_dir> ...]   (多个 run 合并统计)"""
import json, sys, re, math, collections, os
from pathlib import Path

LAY = ("L1", "L2", "L3", "L4")
_SPAN = re.compile(r"(\d+):(\d{2})\s*[-–]\s*(\d+):(\d{2})")


def rows(d, L):
    p = Path(d) / L / "history.jsonl"
    return [json.loads(l) for l in p.open()] if p.exists() else []


def chi_uniform(counts):
    n = sum(counts.values()); k = 4
    if n == 0: return None
    e = n / k; return round(sum((counts.get(x, 0) - e) ** 2 / e for x in "ABCD"), 1)


def main(dirs):
    blind = collections.defaultdict(lambda: [0, 0])            # skill -> [blind correct, n]
    letters = collections.defaultdict(collections.Counter)     # kind -> letter counts
    lens = collections.Counter(); margins = collections.defaultdict(list)
    waste = collections.Counter()
    for d in dirs:
        up = Path(d) / "usage.jsonl"
        if up.exists():
            for l in up.open():
                r = json.loads(l); waste["examiner_calls"] += r.get("role") == "examiner"
        lg = Path(d) / "run.log"
        if lg.exists():
            for l in lg.open(): waste["examiner_rejected"] += "examiner output rejected" in l
        for L in LAY:
            for r in rows(d, L):
                sk = r.get("capability_skill") or "?"; v = r.get("verdict"); waste["turns"] += 1
                if v == "guessable": waste["dropped_guessable"] += 1
                b = r.get("blind") or {}
                bc = (v == "guessable") or bool(r.get("blind_guessable")) or b.get("verdict") == "correct"
                if v in ("correct", "wrong", "guessable"):
                    blind[sk][1] += 1; blind[sk][0] += bc
                if r.get("format") == "single_choice" and v in ("correct", "wrong") and r.get("options"):
                    ref = str(r.get("reference") or "")[:1]
                    if ref in "ABCD":
                        sp = [_SPAN.search(o) for o in r["options"]]
                        kind = "time_span" if all(sp) else ("program_filled" if (r.get("sg") or {}).get("rel_id") else "examiner_written")
                        letters[f"{L} {kind}"][ref] += 1
                        if all(sp):
                            lens[len({(int(x.group(3)) * 60 + int(x.group(4)) - int(x.group(1)) * 60 - int(x.group(2))) for x in sp})] += 1
                sg = r.get("sg") or {}
                for key, path in (("spatial_change", ("sc", "knob")), ("ego", ("ed", "margin_deg")), ("ref_frame", ("rf", "margin")), ("spatial_audio", ("sa", "margin")), ("chain", ("ch", "margin_m")), ("rsn", ("rs", "margin_deg"))):
                    x = (sg.get(path[0]) or {}).get(path[1]) if isinstance(sg.get(path[0]), dict) else None
                    if isinstance(x, (int, float)): margins[key].append(abs(float(x)))
    print("== ① 盲猜率(盲测答对 / 题数;四选一基线 25%)")
    for sk, (c, n) in sorted(blind.items(), key=lambda x: -x[1][1]):
        flag = "  <-- 高于基线" if n >= 6 and c / n > 0.45 else ""
        print(f"  {sk:32s} {c:3d}/{n:3d} = {c / n:4.0%}{flag}")
    print("== ② 参考答案字母分布(卡方对均匀,df=3:>7.8 即 5% 水平显著不均)")
    for k, c in sorted(letters.items()):
        print(f"  {k:28s} " + " ".join(f"{x}={c.get(x, 0):3d}" for x in "ABCD") + f"  chi2={chi_uniform(c)}" + ("  <-- 不均" if (chi_uniform(c) or 0) > 7.8 else ""))
    if lens: print(f"  时间段题四段长度一致的题: {lens.get(1, 0)} / {sum(lens.values())}")
    print("== ③ 程序出题的余量分位数(档位应覆盖 1–4)")
    for k, v in margins.items():
        v = sorted(v); q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
        print(f"  {k:16s} n={len(v):3d} min={v[0]:.2f} q25={q(.25):.2f} med={q(.5):.2f} q75={q(.75):.2f} max={v[-1]:.2f}")
    t = waste["turns"] or 1
    print(f"== 浪费: turns {waste['turns']}, Examiner 调用 {waste['examiner_calls']} ({waste['examiner_calls'] / t:.2f}/turn), 校验拒绝 {waste['examiner_rejected']}, 盲猜作废 {waste['dropped_guessable']} ({waste['dropped_guessable'] / t:.0%} of turns)")


if __name__ == "__main__":
    main(sys.argv[1:])
