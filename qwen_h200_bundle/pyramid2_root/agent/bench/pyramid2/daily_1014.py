#!/usr/bin/env python3
"""experiments/daily_report/1014.md §12:EgoPlan run(self 臂)+ gold replay 的结果自动拼表,追加 / 替换到计划文件末尾。
  python3 daily_1014.py [--self p2_egoplan_1014_self] [--gold p2_egoplan_1014_gold]"""
import json, argparse, collections, re
from pathlib import Path
import p2config as P
from store import read_jsonl
import p2report, chain

OUT = Path("/mnt/work_new/weihanxu/experiments/daily_report/1014.md")
MARK = "\n## 12. 结果"


def layer_summaries(run_id):
    return {L: (json.loads((P.RUNS / run_id / L / "summary.json").read_text()) if (P.RUNS / run_id / L / "summary.json").exists() else None) for L in ("L1", "L2", "L3", "L4")}


def overview(run_id):
    out = ["| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | 无效 / 要求核验 | confirmation(skill: 结果 对/题) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for L, s in layer_summaries(run_id).items():
        if s is None:
            out.append(f"| {L} | (未跑完) | | | | | | | | |"); continue
        bv = s["by_verdict"]; conf = (s.get("confirmation") or {}).get("results") or {}
        cs = "; ".join(f"{k}: {v['result'].replace('confirmed_', '')} {v['correct']}/{v['n']}" for k, v in conf.items() if v.get("result")) or "-"
        out.append(f"| {L} | {s['stop_reason']} | {s['turns']} | {s['scored']} | {s['correct']} | {s['raw_acc']} | {s['cluster_dedup_acc']} | {s['followup_items']} | {bv.get('item_invalid', 0)} / {bv.get('evidence_unresolved', 0)} | {cs} |")
    return out


def skills(run_id):
    out = ["| layer | skill | 诊断结论 | scored | 对 | cluster 数 | 首答对 | 支持的假设 | confirmation |", "|---|---|---|---|---|---|---|---|---|"]
    for L, s in layer_summaries(run_id).items():
        if s is None: continue
        conf = (s.get("confirmation") or {}).get("results") or {}
        for sk, v in s["by_skill"].items():
            c = conf.get(sk)
            cs = f"{c['result'].replace('confirmed_', '')} {c['correct']}/{c['n']}" if c and c.get("result") else "-"
            out.append(f"| {L} | {sk} | **{v['verdict']}** | {v.get('scored', '')} | {v.get('correct', '')} | {v.get('clusters', '')} | {v.get('cluster_first_correct', '')} | {', '.join(v.get('supported_hypotheses', [])) or '-'} | {cs} |")
        for sk, why in (s.get("not_evaluated") or {}).items():
            out.append(f"| {L} | {sk} | NOT_EVALUATED | | | | | | {why[:80]} |")
    return out


def followups(run_id):
    out = ["| layer | 题型 | 策略 | 追问结果(假设 → verdict) |", "|---|---|---|---|"]
    for L in ("L1", "L2", "L3", "L4"):
        rows = [h for h in read_jsonl(P.RUNS / run_id / L / "history.jsonl") if h["phase"] == "DIAGNOSIS"]
        if not rows: continue
        fm = dict(collections.Counter(h["format"] for h in rows if h["format"])); st = dict(collections.Counter(h["strategy"] for h in rows if h["strategy"]))
        fu = collections.Counter(f"{(h['tests_hypothesis'] or '').split(':')[2] if h.get('tests_hypothesis') else ''}→{h['verdict']}" for h in rows if h.get("tests_hypothesis"))
        out.append(f"| {L} | {fm} | {st} | {dict(fu) or '-'} |")
    return out


def scope_example(run_id, n=1):
    out = []
    d = P.RUNS / run_id / "scope"
    for f in sorted(d.glob("*.json"))[:n]:
        r = json.loads(f.read_text()); sc = r.get("scope") or {}
        out += [f"样本 `{r['task_id']}`,goal「{sc.get('goal')}」,phases {[(p['name'], p['step_idx']) for p in sc.get('phases', [])]};model `{r.get('model')}`,status {r.get('status')}", "",
                "| layer | skill | event_refs | target | ask | avoid |", "|---|---|---|---|---|---|"]
        for L, by in sc.get("layers", {}).items():
            for sk, ents in by.items():
                for e in ents:
                    out.append(f"| {L} | {sk} | {e['event_refs']} | {str(e.get('target') or '').replace('|', '/')[:60]} | {str(e.get('ask') or '').replace('|', '/')[:120]} | {str(e.get('avoid') or '').replace('|', '/')[:80]} |")
        out.append("")
    stat = collections.Counter()
    for f in d.glob("*.json"):
        r = json.loads(f.read_text()); stat[r.get("status")] += 1
    out.append(f"scope 状态:{dict(stat)}(共 {sum(stat.values())} 份)")
    return out


def item_examples(run_id, per_layer=2):
    out = []
    for L in ("L1", "L2", "L3", "L4"):
        rows = [h for h in read_jsonl(P.RUNS / run_id / L / "history.jsonl") if h["verdict"] in ("correct", "wrong")][:per_layer]
        for h in rows:
            hu = h.get("history_used") or {}
            out += [f"**{L} t{h['turn']} · {h['capability_skill']} · {h['format']} · sample `{h.get('sample_id')}` · scope_id {h.get('scope_id')} · history n={hu.get('n', 0)}(可用 {hu.get('depth_available', 0)},剔除 {len(hu.get('excluded') or [])})· {h['verdict']}**", "",
                    "```", (h.get("solver_prompt") or "")[:1800].rstrip(), "```", "",
                    f"参考答案:`{str(h.get('reference'))[:200]}` · Solver:`{str(h.get('parsed'))[:120]}`", ""]
    return out


def usage(run_ids):
    out = ["| run | role | calls | errors | tok_in | tok_out | tok_think |", "|---|---|---|---|---|---|---|"]
    tot = collections.Counter()
    for rid in run_ids:
        if not (P.RUNS / rid).exists(): continue
        for k, d in sorted(p2report.usage_summary(P.RUNS / rid).items()):
            out.append(f"| {rid} | {k} | {d['calls']} | {d['errors']} | {d['tok_in']:,} | {d['tok_out']:,} | {d['tok_think']:,} |")
            for kk in ("calls", "tok_in", "tok_out", "tok_think"): tot[kk] += d[kk]
    out.append(f"| **合计** | | {tot['calls']} | | {tot['tok_in']:,} | {tot['tok_out']:,} | {tot['tok_think']:,} |")
    return out


def goal_leak_check(run_id):
    """所有计分题的 solver_prompt 里 goal 原句是否出现(应为 0)。"""
    n = bad = 0
    for L in ("L1", "L2", "L3", "L4"):
        for h in read_jsonl(P.RUNS / run_id / L / "history.jsonl"):
            if h["verdict"] not in ("correct", "wrong") or not h.get("sample_id"): continue
            n += 1
            goal = next((s["goal"] for s in json.loads((P.DATA / "egoplan_samples.json").read_text())["samples"] if s["sample_id"] == h["sample_id"]), "")
            if goal and goal.lower() in (h.get("solver_prompt") or "").lower(): bad += 1
    return n, bad


def build(self_run, gold_run):
    import time
    L = [MARK.strip(), "", f"生成时间 {time.strftime('%Y-%m-%d %H:%M')} · self run `{self_run}` · gold replay `{gold_run}` · 脚本 `pyramid2/daily_1014.py`。",
         "**结果为 provisional**:L1–L3 的 gold 是 Examiner 的 proposed_reference_answer(未人工核验),L4 的官方 4 选 1 是 dataset_gt;Solver 看不到 goal,L4 比官方 EgoPlan 协议难,不与官方分数直接比。", ""]
    L += ["### 12.1 self 臂每层概览", ""] + overview(self_run) + ["", "### 12.2 每层 × skill 诊断结论(self)", ""] + skills(self_run)
    L += ["", "### 12.3 追问策略分布(self)", ""] + followups(self_run)
    if (P.RUNS / gold_run / "L1").exists() or (P.RUNS / gold_run / "L4").exists():
        L += ["", "### 12.4 self vs gold history(同一批题成对比较)", ""] + chain.compare(self_run, gold_run, write=True).split("\n", 2)[2].splitlines()
    else:
        L += ["", "### 12.4 self vs gold history", "", "(gold replay 未跑)"]
    n, bad = goal_leak_check(self_run)
    L += ["", f"### 12.5 goal 泄漏检查:{n} 道计分题的 Solver prompt 里 goal 原句命中 {bad} 次", ""]
    L += ["### 12.6 scope planner 样例", ""] + scope_example(self_run)
    L += ["", "### 12.7 题目样例(每层前两道计分题,含 Solver 实际看到的 prompt)", ""] + item_examples(self_run)
    L += ["### 12.8 Gemini 用量", ""] + usage([self_run, gold_run])
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--self", dest="self_run", default="p2_egoplan_1014_self"); ap.add_argument("--gold", dest="gold_run", default="p2_egoplan_1014_gold")
    a = ap.parse_args()
    sec = build(a.self_run, a.gold_run)
    txt = OUT.read_text()
    i = txt.find(MARK)
    k = txt.find("\n## 13.")
    tail = txt[k:] if k >= 0 else ""                       # §13 起的人工观察段落保留
    head = txt[:i] if i >= 0 else (txt[:k] if k >= 0 else txt)
    txt = head.rstrip("\n") + "\n\n" + sec + tail
    OUT.write_text(txt)
    print(f"wrote §12 to {OUT} ({len(sec)} chars)")


if __name__ == "__main__":
    main()
