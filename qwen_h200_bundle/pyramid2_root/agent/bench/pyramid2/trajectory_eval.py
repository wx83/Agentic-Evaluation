#!/usr/bin/env python3
"""轨迹式 completability 评测(10-21,用户定义):
  GT 轨迹 = L1–L3 问过的题 + 正确答案 → 喂给 L4;L4 在每个决策点(中间截断 + 官方最终截断)答「下一步做什么」;
  task completed = 该样本所有决策点都答对。四条臂同一批题:self(下层答案 = Solver 自己的)/ gold(参考答案)/ none(无 history)/ blindgold(只看文字不看 clip)。
  python3 trajectory_eval.py --self p2_egoplan_1021_pilot_self --arms gold=p2_egoplan_1021_pilot_gold,none=...,blindgold=...
输出 runs/<self>/trajectory.json + trajectory.md。"""
import json, argparse, collections, os
from pathlib import Path
import p2config as P
from store import read_jsonl
import chain

LOWER = ["L1", "L2", "L3"]


def samples(self_rid=None):
    """按 self run 的 contract.dataset 选样本表(10-23:hdepic_e = Method E 样本,scenario 字段用 recipe 名)。"""
    ds = None
    if self_rid:
        cp = P.RUNS / self_rid / "run_contract.json"
        if cp.exists(): ds = json.loads(cp.read_text()).get("dataset")
    if ds == "hdepic_e":
        from adapters.hdepic_methode import load_samples as ls
        return {s["sample_id"]: dict(s, scenario=s.get("recipe_name")) for s in ls()}
    if ds == "aea_p":
        from adapters.aea_protocol import load_samples as ls
        return {s["sample_id"]: dict(s, scenario="AEA " + s["video_id"]) for s in ls()}
    os.environ.setdefault("EGOPLAN_SAMPLES", str(P.DATA / "egoplan_samples_pilot1021.json"))
    from adapters.egoplan import load_samples
    return {s["sample_id"]: s for s in load_samples()}


def scored(rid, L):
    p = P.RUNS / rid / L / "history.jsonl"
    ip = P.DATA / "item_issues.json"
    bad = {x["candidate_id"] for x in json.loads(ip.read_text())["items"]} if ip.exists() else set()
    excl = P.excluded_skills()                                   # 10-27:contact 四个 skill 全局不计分
    return [h for h in read_jsonl(p) if h.get("verdict") in ("correct", "wrong") and h["candidate_id"] not in bad and h.get("capability_skill") not in excl] if p.exists() else []


def short(s, n=160):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def decision_points(self_rid, arms, sid, s):
    """该样本的 L4 计分题(self run 出的),按 cutoff 排序;每臂取同 candidate 的重答结果。"""
    rows = sorted([h for h in scored(self_rid, "L4") if h.get("sample_id") == sid and h.get("capability_skill") == "goal_conditioned_planning"], key=lambda h: (h.get("media_refs") or [{}])[0].get("windows", [[0, 0]])[0][1])   # 10-24:gap 题不算决策点
    by_arm = {a: {h["candidate_id"]: h for h in scored(rid, "L4")} for a, rid in arms.items()}
    out = []
    for h in rows:
        cut = (h.get("media_refs") or [{}])[0].get("windows", [[None, None]])[0][1]
        official = cut is not None and abs(cut - s["t1"]) < 0.6
        ref_txt = chain.answer_text(h, "gold")
        d = {"turn": h["turn"], "candidate_id": h["candidate_id"], "phase": h.get("phase"), "cutoff": cut, "official": official,
             "format": h.get("format"), "question": short(h.get("question"), 220), "options": h.get("options"), "reference": ref_txt,
             "steps_done_by_cutoff": [k["idx"] for k in s["steps"] if k["t0"] <= (cut or 0) + 0.5], "arms": {}}
        d["arms"]["self"] = _arm_cell(h)
        for a in arms:
            r = by_arm[a].get(h["candidate_id"])
            d["arms"][a] = _arm_cell(r) if r else None
        out.append(d)
    return out


def _arm_cell(r):
    hu = r.get("history_used") or {}
    reps = r.get("reps") or []
    votes = [str(x.get("parsed") or "").strip().upper()[:1] for x in reps] if reps else None
    return {"verdict": r["verdict"], "correct": r["verdict"] == "correct", "answer": chain.answer_text(r, "self"),
            "reps": [x["verdict"] for x in reps] if reps else None, "votes": votes,
            "reps_agree": (len(set(v for v in votes if v)) == 1) if votes else None,
            "history_n": hu.get("n", 0), "history_excluded_after_cutoff": len(hu.get("excluded_after_cutoff") or []), "blind": bool(r.get("blind"))}


def lower_chain(self_rid, sid):
    out = []
    for L in LOWER:
        for h in scored(self_rid, L):
            if h.get("sample_id") != sid: continue
            we, how = chain._event_end(h, P.RUNS / self_rid)
            out.append({"layer": L, "turn": h["turn"], "phase": h.get("phase"), "skill": h["capability_skill"], "format": h.get("format"),
                        "question": short(h.get("question"), 220), "options": h.get("options"), "reference": chain.answer_text(h, "gold"),
                        "self_answer": chain.answer_text(h, "self"), "verdict": h["verdict"], "event_end": we, "scope_id": h.get("scope_id")})
    return out


def skill_verdicts(rid):
    out = {}
    for L in LOWER + ["L4"]:
        p = P.RUNS / rid / L / "summary.json"
        if not p.exists(): continue
        s = json.loads(p.read_text()); conf = (s.get("confirmation") or {}).get("results") or {}
        for sk, v in s.get("by_skill", {}).items():
            out[sk] = {"layer": L, "verdict": v.get("verdict"), "scored": v.get("scored"), "correct": v.get("correct"),
                       "confirmation": (conf.get(sk) or {}).get("result")}
    return out


def build(self_rid, arms):
    S = samples(self_rid)
    arm_names = ["self"] + list(arms)
    sids = sorted({h.get("sample_id") for L in LOWER + ["L4"] for h in scored(self_rid, L) if h.get("sample_id")})
    per = []
    sids.sort(key=lambda x: (str((S.get(x) or {}).get("scenario")), x))
    for sid in sids:
        s = S.get(sid)
        if s is None: continue
        ch = lower_chain(self_rid, sid); dps = decision_points(self_rid, arms, sid, s)
        rec = {"sample_id": sid, "scenario": s.get("scenario"), "goal": s["goal"], "n_steps": len(s["steps"]), "t0": s["t0"], "t1": s["t1"],
               "steps": [{"idx": k["idx"], "text": k["text"], "t0": k["t0"]} for k in s["steps"]], "next_action": s["next_action"]["text"],
               "lower_chain": ch, "lower_n": len(ch), "lower_self_correct": sum(x["verdict"] == "correct" for x in ch),
               "decision_points": dps, "n_decision_points": len(dps), "arms": {}}
        for a in arm_names:
            cells = [d["arms"].get(a) for d in dps]
            have = [c for c in cells if c]
            rec["arms"][a] = {"n": len(have), "correct": sum(c["correct"] for c in have),
                              "task_completed": bool(have) and len(have) == len(dps) and all(c["correct"] for c in have),
                              "final_official_correct": next((c["correct"] for d, c in zip(dps, cells) if d["official"] and c), None),
                              "pattern": "".join("✓" if c and c["correct"] else ("✗" if c else "·") for c in cells)}
        per.append(rec)
    agg = {}
    for a in arm_names:
        xs = [r["arms"][a] for r in per]
        n_dp = sum(x["n"] for x in xs); n_ok = sum(x["correct"] for x in xs)
        fin = [x["final_official_correct"] for x in xs if x["final_official_correct"] is not None]
        agree = [c["reps_agree"] for r in per for d in r["decision_points"] for c in [d["arms"].get(a)] if c and c["reps_agree"] is not None]
        agg[a] = {"samples": len(xs), "task_completed": sum(x["task_completed"] for x in xs), "decision_points": n_dp, "decision_correct": n_ok,
                  "decision_acc": round(n_ok / n_dp, 3) if n_dp else None, "final_official_correct": sum(fin), "final_official_n": len(fin),
                  "reps_agree_frac": round(sum(agree) / len(agree), 3) if agree else None}
    return {"self_run": self_rid, "arms": arms, "skill_verdicts": skill_verdicts(self_rid), "aggregate": agg, "samples": per}


def md(T):
    arms = ["self"] + list(T["arms"])
    L = [f"# 轨迹式 completability:`{T['self_run']}`", "",
         "定义:L1–L3 问过的题 + 答案作为 history 喂给 L4;L4 在每个决策点(中间截断 = 某步起点,参考 = 截断后第一条记录步骤;官方最终截断 = 官方 4 选 1)答「下一步」;**task completed = 该样本所有决策点都答对**。"
         "history 只含「问到的事件结束 ≤ 本题 cutoff」的下层题。self = 下层答案是 Solver 自己的;gold = 参考答案(用户定义的 GT 轨迹);none = 无 history;blindgold = 参考答案但不看 clip。L4 replay 臂每题重答 3 次取多数。", "",
         "## 1. 汇总(每臂)", "", "| 臂 | task completed / 样本 | 决策点 对 / 总 | 决策点正确率 | 最终官方题 对 / n | L4 三次重答一致率 |", "|---|---|---|---|---|---|"]
    for a in arms:
        g = T["aggregate"][a]
        L.append(f"| {a} | {g['task_completed']} / {g['samples']} | {g['decision_correct']} / {g['decision_points']} | {g['decision_acc']} | {g['final_official_correct']} / {g['final_official_n']} | {g['reps_agree_frac'] if g['reps_agree_frac'] is not None else '-'} |")
    L += ["", "## 2. 每个样本:下层题链 → 决策点 → 各臂结果", "",
          "| 样本 | scenario | 步数 | 下层题 self 对/总 | 决策点数 | " + " | ".join(f"{a}(✓✗ 按时间)" for a in arms) + " | " + " | ".join(f"{a} completed" for a in arms) + " |",
          "|---|---|---|---|---|" + "---|" * (2 * len(arms))]
    for r in T["samples"]:
        L.append(f"| `{r['sample_id'][-14:]}` | {r['scenario']} | {r['n_steps']} | {r['lower_self_correct']}/{r['lower_n']} | {r['n_decision_points']} | "
                 + " | ".join(r["arms"][a]["pattern"] for a in arms) + " | " + " | ".join("**是**" if r["arms"][a]["task_completed"] else "否" for a in arms) + " |")
    L += ["", "## 3. 「过程能否判断 task 可完成」:下层诊断 vs 轨迹结果", "",
          "run 级 skill 诊断结论(L1–L3 跨 5 条样本):", "", "| layer | skill | 结论 | 对/scored | confirmation |", "|---|---|---|---|---|"]
    for sk, v in T["skill_verdicts"].items():
        if v["layer"] == "L4": continue
        L.append(f"| {v['layer']} | {sk} | **{v['verdict']}** | {v['correct']}/{v['scored']} | {v['confirmation'] or '-'} |")
    L += ["", "样本级:下层题 self 正确率(预测器)对 gold 臂 / self 臂 task completed(目标):", "", "| 样本 | 下层 self 正确率 | gold completed | self completed | none completed | blindgold completed |", "|---|---|---|---|---|---|"]
    for r in T["samples"]:
        acc = f"{r['lower_self_correct']}/{r['lower_n']}"
        g = lambda a: ("是" if r["arms"].get(a, {}).get("task_completed") else "否") if a in r["arms"] else "-"
        L.append(f"| `{r['sample_id'][-14:]}` | {acc} | {g('gold')} | {g('self')} | {g('none')} | {g('blindgold')} |")
    L += ["", "## 4. 逐样本明细", ""]
    for r in T["samples"]:
        L += [f"### `{r['sample_id']}` · {r['scenario']} · goal「{r['goal']}」· {r['n_steps']} 步 · {r['t0']:.1f}–{r['t1']:.1f}s · 官方下一步「{r['next_action']}」", "",
              "步骤:" + "; ".join(f"{k['idx']}.{k['text']}({k['t0']:.1f}s)" for k in r["steps"]), "",
              "**下层题链(self run 问过的,按层 / 轮)**", "", "| 层 | 轮 | skill | 题面 | 参考答案 | self 答 | 对错 | 事件结束 s |", "|---|---|---|---|---|---|---|---|"]
        for x in r["lower_chain"]:
            L.append(f"| {x['layer']} | {x['turn']} | {x['skill']} | {x['question'].replace('|', '/')} | {short(x['reference'], 60).replace('|', '/')} | {short(x['self_answer'], 60).replace('|', '/')} | {'✓' if x['verdict'] == 'correct' else '✗'} | {x['event_end'] if x['event_end'] is None else round(x['event_end'], 1)} |")
        L += ["", "**决策点(L4)**", "", "| cutoff s | 官方? | 已完成步骤 | 参考(下一步) | " + " | ".join(f"{a} 答(对错;history n/剔除)" for a in arms) + " |", "|---|---|---|---|" + "---|" * len(arms)]
        for d in r["decision_points"]:
            cells = []
            for a in arms:
                c = d["arms"].get(a)
                if not c: cells.append("-"); continue
                v = f"{'✓' if c['correct'] else '✗'} {short(c['answer'], 40).replace('|', '/')}"
                if c["votes"]: v += f" 票{''.join(x or '?' for x in c['votes'])}"
                v += f" (h{c['history_n']}/{c['history_excluded_after_cutoff']})"
                cells.append(v)
            L.append(f"| {d['cutoff']:.1f} | {'官方' if d['official'] else '中间'} | {d['steps_done_by_cutoff'][-1] if d['steps_done_by_cutoff'] else 0} | {short(d['reference'], 50).replace('|', '/')} | " + " | ".join(cells) + " |")
        L.append("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--self", dest="self_rid", default="p2_egoplan_1021_pilot_self")
    ap.add_argument("--arms", default="gold=p2_egoplan_1021_pilot_gold,none=p2_egoplan_1021_pilot_none,blindgold=p2_egoplan_1021_pilot_blindgold")
    a = ap.parse_args()
    arms = {}
    for kv in a.arms.split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            if (P.RUNS / v / "L4" / "history.jsonl").exists(): arms[k] = v
    T = build(a.self_rid, arms)
    out = P.RUNS / a.self_rid
    (out / "trajectory.json").write_text(json.dumps(T, indent=1, ensure_ascii=False))
    (out / "trajectory.md").write_text(md(T))
    print(json.dumps(T["aggregate"], indent=1, ensure_ascii=False)); print("->", out / "trajectory.md")


if __name__ == "__main__":
    main()
