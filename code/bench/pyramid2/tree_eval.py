#!/usr/bin/env python3
"""题树评测汇总(10-22):
  §1 pyramid 合理性:增益 G_L = acc(gold) − acc(none);必要性 = corrupt 翻转率 vs control 翻转率(每类边);传播 P(父错|子错) vs P(父错|子全对);层正确率单调;充分性 acc(gold@L4)
  §2 agent 对比(每个 self run):每层正确率、决策点正确率、task completed、脚手架效应 self − none、三次重答一致率
  §3 归因分布 + repair 成功率(diagnosis.json)
  §4 每决策点树状明细
  python3 tree_eval.py --agents flash=p2_egoplan_1022_tree_flash,pro=p2_egoplan_1022_tree_pro
输出 runs/<第一个 agent>/tree_eval.{json,md}。"""
import json, argparse, collections
from pathlib import Path
import p2config as P
from store import read_jsonl
import intervene as IV

LAYERS = ["L1", "L2", "L3", "L4"]


def load_arms(rid):
    d = P.RUNS / rid / "intervene"; out = {}
    for arm in ("gold", "none", "corrupt", "control"):
        fp = d / f"{arm}.jsonl"
        out[arm] = list(read_jsonl(fp)) if fp.exists() else []
    return out


def agree(r):
    v = r.get("votes") or [x.get("verdict") for x in (r.get("reps") or [])]
    v = [x for x in v if x]
    return (len(set(v)) == 1) if len(v) > 1 else None


def agent_stats(rid):
    _, contract, cands, rows = IV.load_run(rid)
    arms = load_arms(rid)
    by_layer = {L: [r for r in rows.values() if r["layer"] == L] for L in LAYERS}
    acc = {L: (sum(r["verdict"] == "correct" for r in v), len(v)) for L, v in by_layer.items()}
    roots = [r for r in rows.values() if r["layer"] == "L4"]
    tasks = collections.defaultdict(list)
    for r in roots: tasks[r.get("sample_id")].append(r["verdict"] == "correct")
    gold = {(x["node_id"]): x for x in arms["gold"]}; none = {(x["node_id"]): x for x in arms["none"]}
    # 增益按层(非叶节点)
    gain = {}
    for L in ("L2", "L3", "L4"):
        ids = [r["tree"]["node_id"] for r in by_layer[L] if IV.children_of(r, rows)]
        g = [gold[i]["verdict"] == "correct" for i in ids if i in gold]; n = [none[i]["verdict"] == "correct" for i in ids if i in none]; s = [rows[i]["verdict"] == "correct" for i in ids]
        gain[L] = {"n_nodes": len(ids), "self": (sum(s), len(s)), "gold": (sum(g), len(g)), "none": (sum(n), len(n)),
                   "gain_gold_minus_none": round(sum(g) / len(g) - sum(n) / len(n), 3) if g and n else None,
                   "scaffold_self_minus_none": round(sum(s) / len(s) - sum(n) / len(n), 3) if s and n else None}
    # 必要性:corrupt 翻转 = gold 对且 corrupt 错(按边的层对)
    nec = collections.defaultdict(lambda: {"edges": 0, "gold_correct": 0, "flipped": 0})
    for x in arms["corrupt"]:
        child = rows.get(x["edge"]); par = rows.get(x["node_id"])
        if not child or not par: continue
        key = f"{child['layer']}->{par['layer']}"; nec[key]["edges"] += 1
        g = gold.get(x["node_id"])
        if g and g["verdict"] == "correct":
            nec[key]["gold_correct"] += 1; nec[key]["flipped"] += (x["verdict"] == "wrong")
    for k, v in nec.items(): v["flip_rate_given_gold_correct"] = round(v["flipped"] / v["gold_correct"], 3) if v["gold_correct"] else None
    ctrl = {"n": 0, "gold_correct": 0, "flipped": 0}
    for x in arms["control"]:
        ctrl["n"] += 1; g = gold.get(x["node_id"])
        if g and g["verdict"] == "correct": ctrl["gold_correct"] += 1; ctrl["flipped"] += (x["verdict"] == "wrong")
    ctrl["flip_rate_given_gold_correct"] = round(ctrl["flipped"] / ctrl["gold_correct"], 3) if ctrl["gold_correct"] else None
    # 传播(self):P(父错 | ≥1 子错) vs P(父错 | 子全对)
    prop = {"child_wrong": [0, 0], "children_all_correct": [0, 0]}
    for r in rows.values():
        ch = IV.children_of(r, rows)
        if not ch: continue
        k = "child_wrong" if any(c["verdict"] == "wrong" for c in ch) else "children_all_correct"
        prop[k][1] += 1; prop[k][0] += (r["verdict"] == "wrong")
    prop_rates = {k: (round(v[0] / v[1], 3) if v[1] else None, v) for k, v in prop.items()}
    # 一致率
    ag = [agree(r) for r in rows.values()]; ag = [a for a in ag if a is not None]
    diag = json.loads((P.RUNS / rid / "diagnosis.json").read_text()) if (P.RUNS / rid / "diagnosis.json").exists() else None
    attr = collections.Counter(); rep_ok = [0, 0]
    if diag:
        for d in diag["decision_points"]:
            a = d["attribution"] or {}; attr[(a.get("kind"), a.get("layer"), a.get("skill"))] += 1
            for rp in d["repairs"]: rep_ok[1] += 1; rep_ok[0] += rp["root_fixed"]
    return {"run": rid, "solver_model": contract.get("solver_model"), "n_nodes": len(rows), "layer_acc": acc,
            "decision_points": (sum(r["verdict"] == "correct" for r in roots), len(roots)),
            "task_completed": (sum(all(v) for v in tasks.values()), len(tasks)), "gain": gain, "necessity": dict(nec), "control": ctrl,
            "propagation": prop_rates, "reps_agree_frac": round(sum(ag) / len(ag), 3) if ag else None,
            "attribution": {"|".join(str(x) for x in k): v for k, v in attr.items()}, "repair_success": rep_ok, "rows": rows, "arms": arms, "diag": diag}


def fmt_pair(p): return f"{p[0]}/{p[1]}" + (f" ({p[0]/p[1]:.2f})" if p[1] else "")


def md(S):
    names = list(S)
    L = ["# 题树评测:pyramid 合理性 + agent 诊断", "",
         "题 = Examiner 按每个决策点的依赖树出(根 L4 ← L3 ← L2 ← L1,题目级依赖);作答自底向上,history 只含子节点的题 + 答案。"
         "self = agent 自己的答案;gold = 子节点参考答案;none = 无 history;corrupt = 只把一条边的子答案换错;control = gold 外加一条无关题的错答案。每题 ×3 取多数。", "",
         "## 1. pyramid 合理性", ""]
    L += ["### 1.1 增益与脚手架效应(非叶节点,按层)", "", "| agent | 层 | 节点数 | self | gold | none | gold − none | self − none |", "|---|---|---|---|---|---|---|---|"]
    for a in names:
        for Ly, g in S[a]["gain"].items():
            L.append(f"| {a} | {Ly} | {g['n_nodes']} | {fmt_pair(g['self'])} | {fmt_pair(g['gold'])} | {fmt_pair(g['none'])} | {g['gain_gold_minus_none']} | {g['scaffold_self_minus_none']} |")
    L += ["", "### 1.2 必要性:换错一条边的子答案,父节点(gold 下本来答对的)翻错的比例 vs control", "", "| agent | 边 | 边数 | gold 对 | 翻错 | 翻转率 |", "|---|---|---|---|---|---|"]
    for a in names:
        for k, v in sorted(S[a]["necessity"].items()):
            L.append(f"| {a} | {k} | {v['edges']} | {v['gold_correct']} | {v['flipped']} | {v['flip_rate_given_gold_correct']} |")
        c = S[a]["control"]; L.append(f"| {a} | **control(无关题错答案)** | {c['n']} | {c['gold_correct']} | {c['flipped']} | {c['flip_rate_given_gold_correct']} |")
    L += ["", "### 1.3 传播(self 臂)与层正确率", "", "| agent | P(父错 \\| ≥1 子错) | P(父错 \\| 子全对) | L1 | L2 | L3 | L4 | 三次重答一致率 |", "|---|---|---|---|---|---|---|---|"]
    for a in names:
        p = S[a]["propagation"]; acc = S[a]["layer_acc"]
        L.append(f"| {a} | {p['child_wrong'][0]} ({p['child_wrong'][1][0]}/{p['child_wrong'][1][1]}) | {p['children_all_correct'][0]} ({p['children_all_correct'][1][0]}/{p['children_all_correct'][1][1]}) | "
                 + " | ".join(fmt_pair(acc[Ly]) for Ly in LAYERS) + f" | {S[a]['reps_agree_frac']} |")
    L += ["", "## 2. agent 对比", "", "| agent | Solver | 节点数 | 决策点 对/总 | task completed | L4 gold(充分性) | L4 none | 脚手架效应 L4 |", "|---|---|---|---|---|---|---|---|"]
    for a in names:
        g4 = S[a]["gain"].get("L4", {})
        L.append(f"| {a} | {S[a]['solver_model']} | {S[a]['n_nodes']} | {fmt_pair(S[a]['decision_points'])} | {fmt_pair(S[a]['task_completed'])} | {fmt_pair(g4.get('gold', (0, 0)))} | {fmt_pair(g4.get('none', (0, 0)))} | {g4.get('scaffold_self_minus_none')} |")
    L += ["", "## 3. 归因(self 臂答错的决策点,按层从低到高做 repair)", "", "| agent | 归因 kind \\| layer \\| skill | 决策点数 |", "|---|---|---|"]
    for a in names:
        for k, v in sorted(S[a]["attribution"].items()): L.append(f"| {a} | {k} | {v} |")
        L.append(f"| {a} | repair 成功 / 尝试 | {S[a]['repair_success'][0]} / {S[a]['repair_success'][1]} |")
    L += ["", "## 4. 每决策点树状明细(节点:self / gold / none;corrupt 翻转的边标 ⚡)", ""]
    a0 = names[0]; rows = S[a0]["rows"]
    for a in names:
        rows_a = S[a]["rows"]; arms = S[a]["arms"]
        gold = {x["node_id"]: x for x in arms["gold"]}; none = {x["node_id"]: x for x in arms["none"]}
        flipped = {(x["node_id"], x["edge"]) for x in arms["corrupt"] if x["verdict"] == "wrong" and gold.get(x["node_id"], {}).get("verdict") == "correct"}
        diag = {d["root"]: d for d in (S[a]["diag"] or {}).get("decision_points", [])}
        L.append(f"### agent {a}"); L.append("")
        for root in sorted([r for r in rows_a.values() if r["layer"] == "L4"], key=lambda r: (r.get("sample_id"), r["tree"]["cutoff_step"])):
            d = diag.get(root["tree"]["node_id"], {}); at = d.get("attribution") or {}
            L.append(f"- **{root['tree']['node_id']}** `{str(root.get('sample_id'))[-12:]}` cutoff_step {root['tree']['cutoff_step']} · 归因 {at.get('kind')}{(' ' + str(at.get('layer')) + '/' + str(at.get('skill'))) if at.get('layer') else ''}")
            def walk(nid, depth, flip=False):
                r = rows_a[nid]; mk = lambda v: "✓" if v == "correct" else "✗"
                g = gold.get(nid); n = none.get(nid)
                L.append("  " * (depth + 1) + f"- {'⚡ ' if flip else ''}{nid} [{r['capability_skill']}] self {mk(r['verdict'])}" + (f" gold {mk(g['verdict'])}" if g else "") + (f" none {mk(n['verdict'])}" if n else "")
                         + f" · {IV.chain.answer_text(r, 'gold')[:50]} · Q: {(r.get('question') or '')[:90]}")
                for c in (r["tree"].get("depends_on") or []):
                    if c in rows_a: walk(c, depth + 1, flip=((nid, c) in flipped))
            walk(root["tree"]["node_id"], 0)
        L.append("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--agents", default="flash=p2_egoplan_1022_tree_flash,pro=p2_egoplan_1022_tree_pro"); a = ap.parse_args()
    S = {}
    for kv in a.agents.split(","):
        k, v = kv.split("="); S[k] = agent_stats(v) if (P.RUNS / v / "L4" / "history.jsonl").exists() else None
    S = {k: v for k, v in S.items() if v}
    first = list(S.values())[0]["run"]; out = P.RUNS / first
    slim = {k: {kk: vv for kk, vv in v.items() if kk not in ("rows", "arms", "diag")} for k, v in S.items()}
    (out / "tree_eval.json").write_text(json.dumps(slim, indent=1, ensure_ascii=False, default=str)); (out / "tree_eval.md").write_text(md(S))
    print(json.dumps(slim, indent=1, ensure_ascii=False, default=str)[:3000]); print("->", out / "tree_eval.md")


if __name__ == "__main__":
    main()
