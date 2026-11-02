#!/usr/bin/env python3
"""10-23 HD-EPIC Method E pyramid 报告:每个 agent 的 self / gold / none 三臂 → 按层正确率、翻转、决策点 / task completed、追问诊断、audio 交叉。
用法:python3 daily_1023.py --agents g4=p2_hdepicE_1023_g4 qwen=p2_hdepicE_1023_qwen [--extra qwen_on_g4set=p2_hdepicE_1023_qwen_on_g4set] [--out 1023.md]
每个 agent 前缀对应 <prefix>_self / _gold / _none 三个 run(缺的臂跳过)。"""
import json, argparse, collections, datetime
from pathlib import Path
import p2config as P
from store import read_jsonl
import chain, trajectory_eval as TE

LAYERS = ["L1", "L2", "L3", "L4"]
AUDIO = {}
for d in Path("/mnt/work_new/weihanxu/experiments/hdepic_goal_gen/out/E").glob("*/audio_tags.json"):
    AUDIO.update(json.loads(d.read_text())["sub_goals"])


ISSUES_FILE = P.DATA / "item_issues.json"


def item_issues():
    """人工判定的问题题(candidate_id -> reason);不计入任何臂。"""
    return {x["candidate_id"]: x for x in json.loads(ISSUES_FILE.read_text())["items"]} if ISSUES_FILE.exists() else {}


def rows(rid, L, include_issues=False):
    p = P.RUNS / rid / L / "history.jsonl"
    bad = {} if include_issues else item_issues(); excl = P.excluded_skills()        # 10-27:contact 四个 skill 全局不计分
    return [h for h in read_jsonl(p) if h.get("verdict") in ("correct", "wrong") and h["candidate_id"] not in bad and h.get("capability_skill") not in excl] if p.exists() else []


def issues_md(prefix):
    bad = item_issues(); out = []
    for L in LAYERS:
        for h in rows(f"{prefix}_self", L, include_issues=True):
            if h["candidate_id"] in bad:
                out.append(f"| {L}-{h['turn']:03d} | {h['capability_skill']} | {h['sample_id']} | self {h['verdict']} | {bad[h['candidate_id']]['reason']} |")
    return ("| 题号 | skill | sample | 原判 | 原因 |\n|---|---|---|---|---|\n" + "\n".join(out)) if out else "无"


def exists(rid): return (P.RUNS / rid / "run_contract.json").exists()


def layer_table(prefix, arms):
    out = ["| layer | " + " | ".join(arms) + " | gold − self | none |", "|---|" + "---|" * (len(arms) + 2)]
    tot = {a: [0, 0] for a in arms}
    for L in LAYERS:
        cells = []; acc = {}
        for a in arms:
            rs = rows(f"{prefix}_{a}", L); n = len(rs); k = sum(h["verdict"] == "correct" for h in rs); tot[a][0] += k; tot[a][1] += n
            acc[a] = (k, n); cells.append(f"{k}/{n} ({k/n:.2f})" if n else "-")
        d = (acc.get("gold", (0, 0))[0] - acc.get("self", (0, 0))[0])
        out.append(f"| {L} | " + " | ".join(cells) + f" | {d:+d} | {acc.get('none', ('-',))[0]} |")
    out.append("| all | " + " | ".join(f"{tot[a][0]}/{tot[a][1]} ({tot[a][0]/tot[a][1]:.2f})" if tot[a][1] else "-" for a in arms) + " | | |")
    return "\n".join(out)


def flips(prefix, a, b):
    """self → arm 的逐题翻转(同 candidate):up = self 错 arm 对,down = self 对 arm 错。"""
    out = []
    for L in LAYERS:
        A = {h["candidate_id"]: h for h in rows(f"{prefix}_{a}", L)}; B = {h["candidate_id"]: h for h in rows(f"{prefix}_{b}", L)}
        up = sum(1 for c in A if c in B and A[c]["verdict"] == "wrong" and B[c]["verdict"] == "correct")
        dn = sum(1 for c in A if c in B and A[c]["verdict"] == "correct" and B[c]["verdict"] == "wrong")
        out.append(f"| {L} | {len(set(A) & set(B))} | +{up} | −{dn} |")
    return "\n".join(["| layer | 同题数 | self 错 → " + b + " 对 | self 对 → " + b + " 错 |", "|---|---|---|---|"] + out)


def diag(prefix):
    """追问诊断:每层 skill verdict、追问题数、首答错后追问的结论、确认、scope 内 / 外。"""
    out = ["| layer | skill | scored | correct | verdict | follow-ups | confirmation | scope-out follow-ups |", "|---|---|---|---|---|---|---|---|"]
    for L in LAYERS:
        sp = P.RUNS / f"{prefix}_self" / L / "summary.json"
        if not sp.exists(): continue
        s = json.loads(sp.read_text()); conf = (s.get("confirmation") or {}).get("results") or {}
        rs = rows(f"{prefix}_self", L)
        for sk, v in (s.get("by_skill") or {}).items():
            if sk in P.excluded_skills(): continue                 # 10-27:contact 等全局排除的 skill 不列
            fu = [h for h in rs if h["capability_skill"] == sk and h.get("tests_hypothesis")]
            so = sum(1 for h in fu if h.get("scope_id") is None)
            c = conf.get(sk) or {}
            out.append(f"| {L} | {sk} | {v.get('scored')} | {v.get('correct')} | {v.get('verdict')} | {len(fu)} | {(str(c.get('correct')) + '/' + str(c.get('n')) + ' ' + str(c.get('result'))) if c else '-'} | {so} |")
    return "\n".join(out)


def audio_cross(prefix, arms):
    """决策点所在 sub-goal 的 audio 标签 × 正确率(L4 题,按 cutoff 落在哪个 sub-goal 起点)。"""
    S = TE.samples(f"{prefix}_self")
    tab = collections.defaultdict(lambda: collections.Counter())
    for a in arms:
        for h in rows(f"{prefix}_{a}", "L4"):
            s = S.get(h.get("sample_id"))
            if not s: continue
            cut = (h.get("media_refs") or [{}])[0].get("windows", [[None, None]])[0][1]
            st = next((k for k in s["steps"] if cut is not None and abs(k["t0"] - cut) < 0.6), None)
            lab = (st or {}).get("audio_label") or ("final" if st is None else "?")
            tab[(a, lab)]["n"] += 1; tab[(a, lab)]["ok"] += h["verdict"] == "correct"
    labs = sorted({k[1] for k in tab})
    out = ["| arm | " + " | ".join(labs) + " |", "|---|" + "---|" * len(labs)]
    for a in arms:
        out.append(f"| {a} | " + " | ".join(f"{tab[(a,l)]['ok']}/{tab[(a,l)]['n']}" if tab[(a, l)]["n"] else "-" for l in labs) + " |")
    return "\n".join(out)


def gap_section(prefix, arms):
    """10-24 L4 gap filling:按隐藏步数 / 难度 / 臂的正确率;选错时选中的干扰项类型;gap_steps 的 judge 分。"""
    out = []; C = {}
    for a in arms:
        p = P.RUNS / f"{prefix}_{a}" / "candidates.jsonl"
        if p.exists(): C[a] = {c["candidate_id"]: c for c in read_jsonl(p)}
    rs = {a: [h for h in rows(f"{prefix}_{a}", "L4") if h.get("capability_skill") == "plan_gap_filling"] for a in arms}
    if not rs.get("self"): return "(no gap items)"
    def key(h, c):
        g = ((c or {}).get("output") or {}).get("private", {}).get("gap") or {}
        return len(g.get("hidden_idx") or []), (h.get("format") or "")
    out.append("| 隐藏步数 | format | " + " | ".join(arms) + " |\n|---|---|" + "---|" * len(arms))
    byk = collections.defaultdict(lambda: {a: [0, 0] for a in arms})
    for a in arms:
        src = C.get(a) or C.get("self") or {}
        for h in rs[a]:
            k = key(h, src.get(h["candidate_id"]) or (C.get("self") or {}).get(h["candidate_id"])); byk[k][a][1] += 1; byk[k][a][0] += h["verdict"] == "correct"
    for k in sorted(byk): out.append(f"| {k[0]} | {k[1]} | " + " | ".join(f"{byk[k][a][0]}/{byk[k][a][1]}" for a in arms) + " |")
    # 选错时选中的干扰项类型
    out.append("\n选错时选中的干扰项类型(单选):\n\n| arm | order_violation | state_conflict | plausible_unobserved | skip | 未解析 |\n|---|---|---|---|---|---|")
    for a in arms:
        cnt = collections.Counter()
        for h in rs[a]:
            if h["verdict"] != "wrong" or h.get("format") != "single_choice": continue
            c = (C.get("self") or {}).get(h["candidate_id"]) or {}; dt = ((c.get("output") or {}).get("private", {}).get("gap") or {}).get("distractor_types") or {}
            cnt[dt.get(str(h.get("parsed") or "").strip().upper()[:1], "未解析")] += 1
        out.append(f"| {a} | " + " | ".join(str(cnt[t]) for t in ("order_violation", "state_conflict", "plausible_unobserved", "skip", "未解析")) + " |")
    return "\n".join(out)


def plan_section(prefix, arms):
    """10-24 v6 plan_mode=stages:L4 plan 题按阶段判;每臂 correct / 平均 coverage / 顺序对 / 有矛盾 的题数,再逐题列三项。"""
    rs = {a: [h for h in rows(f"{prefix}_{a}", "L4") if h.get("format") == "plan"] for a in arms}
    if not rs.get("self"): return "(no plan items)"
    out = ["| arm | plan 题 | correct | 平均 coverage | 顺序对 | 有矛盾 | 有超范围行(不扣) | 无 plan_eval(旧判法) |", "|---|---|---|---|---|---|---|---|"]
    for a in arms:
        pe = [h for h in rs[a] if h.get("plan_eval")]
        cov = [h["plan_eval"]["n_covered"] / h["plan_eval"]["n_stages"] for h in pe if h["plan_eval"].get("n_stages")]
        mc = f"{sum(cov) / len(cov):.2f}" if cov else "-"
        out.append(f"| {a} | {len(rs[a])} | {sum(h['verdict'] == 'correct' for h in rs[a])} | {mc} | {sum(bool(h['plan_eval'].get('order_ok')) for h in pe)}/{len(pe)} | {sum(bool(h['plan_eval'].get('contradictions')) for h in pe)} | {sum(bool(h['plan_eval'].get('beyond_horizon')) for h in pe)} | {len(rs[a]) - len(pe)} |")
    by = {a: {h["candidate_id"]: h for h in rs[a]} for a in arms}
    out.append("\n| 题 | sample | cutoff | " + " | ".join(f"{a}:coverage / 顺序 / 矛盾数 → 判定" for a in arms) + " |\n|---|---|---|" + "---|" * len(arms))
    for cid, h in by["self"].items():
        cut = (h.get("media_refs") or [{}])[0].get("windows", [[None, None]])[0][1]
        cells = []
        for a in arms:
            r = by[a].get(cid); pe = (r or {}).get("plan_eval")
            cells.append(f"{pe['n_covered']}/{pe['n_stages']} {'✓' if pe.get('order_ok') else '✗'} {len(pe.get('contradictions') or [])} → {r['verdict']}" if pe else (r["verdict"] if r else "-"))
        out.append(f"| L4-{h['turn']:03d} | {str(h.get('sample_id')).split('__')[-1]} | {cut} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def stair_section(prefix, arms):
    """10-25 v8 阶梯:每层每 skill 的边界档位(self 臂搜索得到)+ 每档正确率(三臂在同一批题上)。"""
    out = []
    for L in LAYERS:
        sp = P.RUNS / f"{prefix}_self" / L / "summary.json"
        if not sp.exists(): continue
        s = json.loads(sp.read_text()); stair = s.get("stair") or {}
        # 合并 run 的 summary(merge_runs.py 生成)没有 stair:先看各 per-task run 有没有
        has_task_stair = any((p_ / L / "summary.json").exists() and (json.loads((p_ / L / "summary.json").read_text()).get("stair") or {}) for p_ in P.RUNS.glob(f"{prefix}_self__*"))
        if not stair and not has_task_stair: continue
        rs = {a: rows(f"{prefix}_{a}", L) for a in arms}
        out.append(f"\n**{L}**\n\n| skill | task | 边界 | 停止原因 | 搜索题 | 验证(预期→实际) | " + " | ".join(f"{a} 每档 对/总(1·2·3·4)" for a in arms) + " |\n|---|---|---|---|---|---|" + "---|" * len(arms))
        # merged run:summary 的 stair 是最后一个 task 的;按 task_run 分别从 history 重算每档正确率,边界从各 task 的 summary 读
        by_task = collections.defaultdict(dict)
        for p_ in sorted(P.RUNS.glob(f"{prefix}_self__*")):
            sp2 = p_ / L / "summary.json"
            if sp2.exists():
                for sk, v in (json.loads(sp2.read_text()).get("stair") or {}).items(): by_task[p_.name][sk] = v
        if not by_task: by_task[f"{prefix}_self"] = stair
        for trun, d in sorted(by_task.items()):
            for sk, v in d.items():
                if sk in P.excluded_skills(): continue             # 10-27:全局排除的 skill 不列
                ver = v.get("verify") or []
                vtxt = "; ".join(f"L{x['level']} {x['expect'][:1]}→{(x.get('verdict') or '-')[:1]}" for x in ver) or "-"
                cells = []
                for a in arms:
                    acc = collections.defaultdict(lambda: [0, 0])
                    for h in rs[a]:
                        if h.get("capability_skill") != sk or h.get("difficulty_level") is None: continue
                        if len(by_task) > 1 and h.get("task_run") not in (trun, trun.replace("_self", f"_{a}")): continue
                        acc[h["difficulty_level"]][1] += 1; acc[h["difficulty_level"]][0] += h["verdict"] == "correct"
                    cells.append(" · ".join(f"{acc[k][0]}/{acc[k][1]}" if acc[k][1] else "-" for k in (1, 2, 3, 4)))
                b = v.get("boundary"); btxt = "-" if b is None else (f"{b}" + (" (unconverged)" if v.get("unconverged") else "") + (" ✓" if v.get("boundary_confirmed") else " ✗" if v.get("boundary_confirmed") is False else ""))
                out.append(f"| {sk} | {trun.split('__')[-1]} | {btxt} | {v.get('stop')} | {v.get('n_search')}{' (' + str(v.get('n_reused_events')) + ' 复用 event)' if v.get('n_reused_events') else ''} | {vtxt} | " + " | ".join(cells) + " |")
    return "\n".join(out) if out else "(no staircase runs)"


ARMS_ALL = ("self", "gold", "none", "selfv", "goldv")   # selfv / goldv(10-26):history 抬头标明「自己的未核实回答」/「已核实答案」


def usage(prefix):
    c = collections.Counter()
    for arm in ARMS_ALL:
        p = P.RUNS / f"{prefix}_{arm}" / "usage.jsonl"
        if not p.exists(): continue
        for u in read_jsonl(p):
            c[(arm, u.get("role"))] += 1
    return ", ".join(f"{k[0]}/{k[1]}: {v}" for k, v in sorted(c.items()))


def build(agents, extra, out):
    aea = all("aeaP" in p for p in agents.values())          # 10-27 晚:AEA protocol clip 的 run(goal / 步骤 = Gemini 候选,caption 自动,全部 needs_verification)
    L = [("# 2026-10-27 pyramid2 v13 × AEA protocol clip(goal / 步骤 = Gemini 候选;narration = legacy 自动 caption;声音 = legacy;fixture 3D = SAM3 + 官方 MPS;位姿 / 视线 = 官方 MPS;全部 needs_verification)\n" if aea else
          f"# 2026-10-23 pyramid × HD-EPIC Method E(10 example;goal = 官方 recipe step,plan = Gemini sub-goal)\n"),
         f"生成时间 {datetime.datetime.now():%Y-%m-%d %H:%M} · 脚本 `pyramid2/daily_1023.py`。**provisional**:plan 层(sub-goal)与 L1–L3 参考答案是模型写的,未人工核验;L4 中间点参考 = 下一个 sub-goal,最终点 = \"step complete\"。",
         "self = Solver 带下层基础题 + 自己的回答;gold = 同一批题重答,下层答案换参考答案;none = 无 history。Examiner / scope planner 固定 gemini-3.1-pro。\n"]
    for name, prefix in agents.items():
        arms = [a for a in ARMS_ALL if exists(f"{prefix}_{a}")]
        L.append(f"## {name}(runs `{prefix}_*`;Solver {json.loads((P.RUNS / f'{prefix}_self' / 'run_contract.json').read_text()).get('solver_model')})\n")
        L.append("### 按层正确率\n" + layer_table(prefix, arms) + "\n")
        if "gold" in arms: L.append("### self → gold 逐题翻转\n" + flips(prefix, "self", "gold") + "\n")
        if "none" in arms: L.append("### self → none 逐题翻转\n" + flips(prefix, "self", "none") + "\n")
        if "goldv" in arms or "selfv" in arms:
            import label_eval as LE
            L.append("### history 标注实验(v9,10-26 用户定:selfv = 抬头说明「你自己之前的未核实回答」;goldv = 抬头说明「已核实正确的答案」;原 self / gold 抬头中性)\n" + LE.section(prefix, arms) + "\n")
        try:
            T = TE.build(f"{prefix}_self", {a: f"{prefix}_{a}" for a in arms if a != "self"})
            (P.RUNS / f"{prefix}_self" / "trajectory.json").write_text(json.dumps(T, indent=1, ensure_ascii=False))
            (P.RUNS / f"{prefix}_self" / "trajectory.md").write_text(TE.md(T))
            L.append("### 决策点与 task completed(每个样本 = 一个官方 step;completed = 全部截断点答对)\n")
            L.append("| arm | task completed | 决策点 对/总 | 最终点(step complete)对/总 |\n|---|---|---|---|")
            for a, g in T["aggregate"].items():
                L.append(f"| {a} | {g['task_completed']} / {g['samples']} | {g['decision_correct']} / {g['decision_points']} | {g['final_official_correct']} / {g['final_official_n']} |")
            L.append("\n| sample | goal | 决策点 | " + " | ".join(T["aggregate"]) + " |\n|---|---|---|" + "---|" * len(T["aggregate"]))
            for r in T["samples"]:
                L.append(f"| {r['sample_id']} | {r['goal'][:50]} | {r['n_decision_points']} | " + " | ".join(r["arms"][a]["pattern"] for a in T["aggregate"]) + " |")
            L.append("")
        except Exception as ex:
            L.append(f"(trajectory eval failed: {type(ex).__name__}: {str(ex)[:160]})\n")
        L.append("### 排除的问题题(item_issue,不计入以上各表)\n" + issues_md(prefix) + "\n")
        L.append("### adaptive 诊断(self 臂)\n" + diag(prefix) + "\n")
        L.append("### 决策点所在 sub-goal 的 audio 标签 × L4 正确\n" + audio_cross(prefix, arms) + "\n")
        L.append("### L4 gap filling(头尾两段 clip,挖掉中间 sub-goal)\n" + gap_section(prefix, arms) + "\n")
        L.append("### L4 plan 题(v6 阶段级 judge:coverage / order / contradiction,全过才 correct)\n" + plan_section(prefix, arms) + "\n")
        L.append("### 难度阶梯(v8:每 skill 2-down-1-up 搜边界;档 = 题型 + 窗长 + 程序量;边界 = 反转点均值,✓ = 上下一档验证都符合预期)\n" + stair_section(prefix, arms) + "\n")
        L.append(f"Gemini / Qwen 调用数:{usage(prefix)}\n")
    for name, rid in (extra or {}).items():
        if not exists(rid): continue
        L.append(f"## 对照 run `{rid}`({name})\n")
        src = json.loads((P.RUNS / rid / "run_contract.json").read_text()).get("replay_of") or ""
        for Lr in LAYERS:
            rs = rows(rid, Lr); n = len(rs); k = sum(h["verdict"] == "correct" for h in rs)
            L.append(f"- {Lr}: {k}/{n}")
        L.append("")
    Path(out).write_text("\n".join(L)); print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--agents", nargs="+", required=True); ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--out", default="/mnt/work_new/weihanxu/experiments/daily_report/1023.md"); a = ap.parse_args()
    build(dict(x.split("=", 1) for x in a.agents), dict(x.split("=", 1) for x in a.extra), a.out)
