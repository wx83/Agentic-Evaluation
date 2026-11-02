#!/usr/bin/env python3
"""10-27 晚(用户定实验):同一 task 上 v13(起始档 2 + 2 道验证题)与 v14(起始档 = 上次边界、无验证题)逐 skill 对比:题数、起始档、边界、skill 分;
再给 v14 self → gold 逐题翻转。用法:python3 compare_budget.py <run_a> <run_b> [gold_run_of_b] > md"""
import json, re, sys, collections
from pathlib import Path
import p2config as P, pyramid_score as PS
LAYERS = ["L1", "L2", "L3", "L4"]


def load(run):
    d = P.RUNS / run; out = {}
    reasons = PS._stop_reasons(d)
    for L in LAYERS:
        sp = d / L / "state.json"
        if not sp.exists(): continue
        rows = [json.loads(l) for l in open(d / L / "history.jsonl")] if (d / L / "history.jsonl").exists() else []
        for sk, v in (json.loads(sp.read_text()).get("stair") or {}).items():
            if not isinstance(v, dict) or sk in P.excluded_skills(): continue
            mine = [r for r in rows if r.get("capability_skill") == sk and r.get("verdict") in ("correct", "wrong")]
            tr = v.get("trace") or []
            out[sk] = {"layer": L, "n": len(mine), "n_search": sum(1 for r in mine if r.get("stair_phase") == "search"),
                       "n_invalid": sum(1 for r in rows if r.get("capability_skill") == sk and r.get("verdict") == "item_invalid"),
                       "start": tr[0]["level"] if tr else None, "boundary": v.get("boundary"), "stop": reasons.get(sk, ""),
                       "score": PS.skill_score(int(L[1]), v.get("boundary")), "correct": sum(1 for r in mine if r["verdict"] == "correct")}
    return out


def main(a, b, gold=None):
    A, B = load(a), load(b)
    print(f"# 预算实验:{a}(A)vs {b}(B)\n")
    print("| 层 | skill | A 题数(搜+验) | B 题数 | B 起始档 | A 边界 | B 边界 | 差 | A 分 | B 分 | A 停止 | B 停止 |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    tot = collections.Counter(); diffs = []
    for sk in sorted(set(A) | set(B), key=lambda k: ((A.get(k) or B.get(k))["layer"], k)):
        x, y = A.get(sk, {}), B.get(sk, {})
        d = None if x.get("boundary") is None or y.get("boundary") is None else round(y["boundary"] - x["boundary"], 2)
        if d is not None: diffs.append(abs(d))
        tot["A"] += x.get("n", 0); tot["B"] += y.get("n", 0)
        f = lambda v: "-" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))
        print(f"| {(x or y)['layer']} | {sk} | {x.get('n','-')} ({x.get('n_search','-')}+{(x.get('n',0)-x.get('n_search',0)) if x else '-'}) | {y.get('n','-')} | {y.get('start','-')} | {f(x.get('boundary'))} | {f(y.get('boundary'))} | {f(d)} | {f(x.get('score'))} | {f(y.get('score'))} | {x.get('stop','')} | {y.get('stop','')} |")
    sa, sb = PS.score_run(P.RUNS / a), PS.score_run(P.RUNS / b)
    print(f"\n题数:A {tot['A']} → B {tot['B']}({(tot['B']-tot['A'])/max(tot['A'],1):+.0%});边界绝对差均值 {sum(diffs)/max(len(diffs),1):.2f}(n={len(diffs)}),差 ≤ 0.5 的 skill {sum(1 for d in diffs if d <= 0.5)}/{len(diffs)}。")
    print(f"pyramid 分:A {sa['pyramid']:.2f}(高度 {sa['height']})→ B {sb['pyramid']:.2f}(高度 {sb['height']});层分 A " + " / ".join(f"{L} {('-' if not sa['layers'].get(L) else f'{sa[chr(108)+chr(97)+chr(121)+chr(101)+chr(114)+chr(115)][L][chr(115)+chr(99)+chr(111)+chr(114)+chr(101)]:.2f}')}" for L in LAYERS) + ";B " + " / ".join(f"{L} {('-' if not sb['layers'].get(L) else f'{sb[chr(108)+chr(97)+chr(121)+chr(101)+chr(114)+chr(115)][L][chr(115)+chr(99)+chr(111)+chr(114)+chr(101)]:.2f}')}" for L in LAYERS))
    if gold and (P.RUNS / gold / "L1" / "history.jsonl").exists():
        print(f"\n## {b} self → gold 逐题翻转\n\n| 层 | 同题数 | self 对 | gold 对 | self 错→gold 对 | self 对→gold 错 |\n|---|---|---|---|---|---|")
        for L in LAYERS:
            s = {r["candidate_id"]: r for r in map(json.loads, open(P.RUNS / b / L / "history.jsonl")) if r.get("verdict") in ("correct", "wrong")} if (P.RUNS / b / L / "history.jsonl").exists() else {}
            g = {r["candidate_id"]: r for r in map(json.loads, open(P.RUNS / gold / L / "history.jsonl")) if r.get("verdict") in ("correct", "wrong")} if (P.RUNS / gold / L / "history.jsonl").exists() else {}
            both = [k for k in s if k in g]
            print(f"| {L} | {len(both)} | {sum(1 for k in both if s[k]['verdict']=='correct')} | {sum(1 for k in both if g[k]['verdict']=='correct')} | {sum(1 for k in both if s[k]['verdict']=='wrong' and g[k]['verdict']=='correct')} | {sum(1 for k in both if s[k]['verdict']=='correct' and g[k]['verdict']=='wrong')} |")


if __name__ == "__main__":
    main(*sys.argv[1:4])
