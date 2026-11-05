#!/usr/bin/env python3
"""11-02(用户:用 top-down 反查 bottom-up 为什么出不出依赖题)。
对每个 task:(1) 自上而下让 Gemini 列出「答 L4 决策点 / L3 关系题所必需的、发生在 clip 之前的事实」;(2) 把这些需要的事实与 bottom-up 已出的 L1/L2 题(事实)匹配,
统计覆盖率与缺口类型。用法:GEMINI_BACKEND=openrouter python3 topdown_check.py <v21 prefix> <task> [...]"""
import json, sys, glob, os
from collections import Counter
import p2config as P
from examiner import call, jparse
R = P.ROOT / "runs"; MODEL = "gcp/google/gemini-3.1-pro-preview"

NEED_SYS = """You design a benchmark on first-person cooking video. A recipe step (goal) is split into sub-goals. Upper-layer items are asked about a short clip
that shows ONLY the later part; everything earlier must come from the solver's memory of lower-layer facts.
For each target listed, write the MINIMAL set of facts (1-3) that a solver must know from BEFORE the clip to answer it, each fact a short declarative sentence
about a concrete object / action / location / state in this task. Tag each fact with "kind": "perception" (what/where at a moment), "event" (what was done, from where to where, with what),
or "relation" (how two events connect), and "sub_goal": the sub-goal index the fact comes from.
Return exactly one JSON object: {"targets": [{"target_id": "...", "needed_facts": [{"fact": "...", "kind": "...", "sub_goal": <int>}]}]}"""

MATCH_SYS = """You compare facts. For each NEEDED fact, find whether any AVAILABLE fact (a question with its reference answer, already asked about the same video) states the same information.
Classify each needed fact as one of:
  "covered"            an available fact states it (give its fact_id);
  "partial"            an available fact is about the same object/event but at the wrong granularity or missing the key detail (give fact_id and what is missing);
  "wrong_target"       available facts touch the same sub-goal but ask about other objects/moments; the needed fact was never asked;
  "no_item"            nothing about that sub-goal / event was asked at all.
Return exactly one JSON object: {"matches": [{"target_id": "...", "fact": "...", "status": "...", "fact_id": "...", "note": "..."}]}"""


def plan_of(task_sid):
    fs = sorted(glob.glob(str(P.DATA / "sg_cache" / f"{task_sid}.*.json")))
    d = json.load(open(fs[-1])); plan = d.get("plan", d)
    texts = {s["idx"]: s.get("text") for s in (d.get("input", {}).get("sub_goals") or [])}      # sub-goal 文字在 cache 的 input 里
    for s in plan["sub_goals"]: s.setdefault("text", texts.get(s["idx"], ""))
    plan.setdefault("goal", d.get("input", {}).get("goal"))
    if "events" not in plan:                      # 缓存里 event 挂在 sub_goals[].events 下;这里补一个扁平映射
        plan["events"] = {e["event_id"]: dict(e, sub_goal=sg["idx"]) for sg in plan["sub_goals"] for e in (sg.get("events") or []) if e.get("event_id")}
    return plan


def facts_of(run):
    facts = {}
    for f in glob.glob(f"{R}/{run}/contexts/L[34]_*.json"):
        for x in json.load(open(f)).get("lower_layer_facts") or []: facts[x["fact_id"]] = x
    return facts


def main():
    prefix, tasks = sys.argv[1], sys.argv[2:]
    tot = Counter()
    for t in tasks:
        run = f"p2_hdepicE_1023t_{prefix}_self__{t}"
        c = json.load(open(R / run / "run_contract.json")) if (R / run / "run_contract.json").exists() else json.load(open(P.ROOT / "contracts" / f"{run}.json"))
        plan = plan_of(c["task_sample_id"]); facts = facts_of(run)
        if not facts: print(f"task {t}: no lower_layer_facts in contexts yet"); continue
        sgs = plan["sub_goals"]; rels = plan.get("relations") or []; dps = plan.get("decision_points") or []
        targets = [{"target_id": f"L4_dp{d['idx']}", "kind": "L4 next sub-goal", "ask": f"After sub-goal {d['idx']-1} ends (clip = last 10 s before sub-goal {d['idx']} starts), which sub-goal comes next?", "clip_sub_goal": d["idx"] - 1} for d in dps if d.get("real", True)]
        for r in rels:
            targets.append({"target_id": f"L3_{r['rel_id']}", "kind": f"L3 {r['type']}", "ask": r.get("ask"), "clip_sub_goal": max(plan["events"][e]["sub_goal"] for e in r["events"] if e in plan["events"]) if any(e in plan["events"] for e in r["events"]) else None})
        user = json.dumps({"goal": plan["goal"], "sub_goals": [{"idx": s["idx"], "text": s.get("text") or s.get("sub_goal") or s.get("description") or ""} for s in sgs], "targets": targets}, ensure_ascii=False)
        text, _ = call(NEED_SYS, user, MODEL, max_tokens=8192, thinking="default", run_dir=None, role="topdown"); need = jparse(text)["targets"]
        avail = [{"fact_id": k, "layer": v["layer"], "skill": v["skill"], "sub_goal": v.get("sub_goal"), "question": v["question"], "reference_answer": v["reference_answer"]} for k, v in facts.items()]
        user2 = json.dumps({"needed": [{"target_id": n["target_id"], "facts": n["needed_facts"]} for n in need], "available": avail}, ensure_ascii=False)
        text2, _ = call(MATCH_SYS, user2, MODEL, max_tokens=16384, thinking="default", run_dir=None, role="topdown"); m = jparse(text2)["matches"]
        st = Counter(x["status"] for x in m); kinds = Counter((n_["kind"], x["status"]) for n in need for n_ in n["needed_facts"] for x in m if x["fact"] == n_["fact"])
        print(f"\n== task {t}: {len(targets)} 上层目标, 需要 {sum(len(n['needed_facts']) for n in need)} 条事实; bottom-up 已有 {len(avail)} 条; 匹配: {dict(st)}")
        print("   按需要的事实类型:", {f"{k[0]}/{k[1]}": v for k, v in sorted(kinds.items())})
        for x in m:
            if x["status"] != "covered": print(f"   [{x['status']:12s}] {x['target_id']:10s} {x['fact'][:90]}  {('<- ' + str(x.get('fact_id'))[-14:] + ' ' + str(x.get('note'))[:60]) if x.get('fact_id') else str(x.get('note'))[:70]}")
        tot.update(st)
        json.dump({"targets": targets, "needed": need, "matches": m}, open(R / run / "topdown_check.json", "w"), ensure_ascii=False, indent=1)
    print("\n合计:", dict(tot))


if __name__ == "__main__":
    main()
