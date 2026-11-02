#!/usr/bin/env python3
"""Compare methods A/B (and the old split S) per video -> out/compare_<date>.{md,csv}.  Usage: python -I compare.py <vid> ..."""
import json, glob, os, sys, statistics, collections, datetime, csv
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); A = "/mnt/data_new/hd-epic/annotations/data"; OLD = "/mnt/work_new/weihanxu/experiments/hdepic_goal_split/out"
R = "/mnt/work_new/weihanxu/benchmarks_1011/raw"
acts_df = pd.concat([pd.read_csv(f) for f in glob.glob(f"{A}/high-level/activities/*_recipe_timestamps.csv")])
for c in ("start_time", "end_time"): acts_df[c] = pd.to_numeric(acts_df[c], errors="coerce")
recipes = json.load(open(f"{A}/high-level/complete_recipes.json"))
def ref_sizes():
    e1 = [len(x["task_progress_metadata"]) + 1 for x in json.load(open(f"{R}/egoplan1/EgoPlan_validation.json")) if x.get("video_source") == "EpicKitchens"]
    e2 = [len(x["task_progress_metadata"]) + 1 for x in json.load(open(f"{R}/egoplan2/EgoPlan-Bench2.json"))]
    return e1, e2
def hist(sizes):
    b = collections.Counter("1-3" if s <= 3 else "4-8" if s <= 8 else "9-20" if s <= 20 else ">20" for s in sizes); n = len(sizes)
    return {k: f"{b[k]/n:.0%}" for k in ("1-3", "4-8", "9-20", ">20")}
def load(method, vid):
    if method == "S":  # old whole-video split
        m = json.load(open(f"{OLD}/{vid}/merged.json")); acts = json.load(open(f"{OLD}/{vid}/input_actions.json"))["actions"]
        t = {a["action_id"]: a for a in acts}
        goals = [{"goal_id": g["goal_id"], "description": g["description"], "action_ids": g["chronological_action_ids"]} for g in m["goals"] if g["chronological_action_ids"]]
        for g in goals:
            ids = sorted(g["action_ids"], key=lambda i: t[i]["start_s"]); g["n_actions"] = len(ids)
            g["n_interruptions_gt60s"] = sum(1 for k in range(len(ids) - 1) if t[ids[k + 1]]["start_s"] - t[ids[k]]["end_s"] > 60)
        un = [a["action_id"] for a in m["action_assignments"] if a["assignment_type"] in ("unrelated", "uncertain")]
        return goals, un, acts, m
    m = json.load(open(f"{HERE}/out/{method}/{vid}/merged.json")); acts = json.load(open(f"{HERE}/out/{method}/{vid}/input_actions.json"))["actions"]
    return m["goals"], m["unassigned_action_ids"], acts, m
def official_rows(vid, acts):
    rows = acts_df[acts_df.video_id == vid].dropna(subset=["start_time", "end_time"])
    st = []
    for rid, rv in recipes.items():
        for c in rv["captures"]:
            if vid not in c["videos"]: continue
            for sid, txt in rv["steps"].items():
                for x in c["step_times"].get(sid, []):
                    if x["video"] == vid: st.append((x["start"], x["end"], f"{sid}: {txt}"))
    act_of = {}; step_of = {}
    for a in acts:
        mid = (a["start_s"] + a["end_s"]) / 2
        r = rows[(rows.start_time <= mid) & (rows.end_time >= mid)]; act_of[a["action_id"]] = r.high_level_activity_label.iloc[0] if len(r) else None
        s = [l for s0, s1, l in st if s0 <= mid <= s1]; step_of[a["action_id"]] = s[0] if s else None
    return act_of, step_of, len(rows), len(st)
def purity(goals, lab):
    """mean over goals of share of its actions falling in its dominant official label (ignoring actions with no label); and inverse: per official label, number of goals holding >=20% of its actions."""
    p = []; inv = collections.defaultdict(collections.Counter)
    for g in goals:
        c = collections.Counter(lab[i] for i in g["action_ids"] if lab.get(i))
        if c: p.append(c.most_common(1)[0][1] / sum(c.values()))
        for l, n in c.items(): inv[l][g["goal_id"]] += n
    frag = [sum(1 for g, n in c.items() if n >= 0.2 * sum(c.values())) for l, c in inv.items()]
    return (statistics.mean(p) if p else None), (statistics.mean(frag) if frag else None)
def cost(method, vid):
    if method == "S": f = f"{OLD}/gemini_calls.jsonl"; role = None
    else: f = f"{HERE}/out/gemini_calls.jsonl"; role = f"hdepic_goal_gen_{method}"
    rows = [json.loads(l) for l in open(f)] if os.path.exists(f) else []
    rows = [r for r in rows if r.get("video") == vid and (role is None or r.get("role") == role) and "error" not in r]
    return {"calls": len(rows), "in_tok": sum(r.get("prompt_tokens") or 0 for r in rows), "out_tok": sum(r.get("output_tokens") or 0 for r in rows), "think_tok": sum(r.get("thoughts_tokens") or 0 for r in rows), "wall_min": round(sum(r.get("latency_s") or 0 for r in rows) / 60, 1)}
def main(vids):
    e1, e2 = ref_sizes(); out = []; md = [f"# HD-EPIC goal generation: method comparison ({datetime.date.today()})\n",
        f"Reference granularity: EgoPlan-Bench EPIC goals median {statistics.median(e1)} actions, hist {hist(e1)}; EgoPlan-Bench2 median {statistics.median(e2)}, hist {hist(e2)}.\n",
        "S = previous whole-video split (user prompt, 2 passes); A = EgoPlan-style hierarchy per 120-action window; B = few-shot with 12 official EgoPlan exemplars per window.\n"]
    for vid in vids:
        md.append(f"\n## {vid}\n\n| method | goals | actions/goal min/med/max | size hist | % goals 4-20 | assigned % | unassigned | goals w/ >60s gap | purity vs activity rows | goals per activity row | purity vs recipe steps | goals per step | calls | in/out/think tok | wall min |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for meth in ("S", "A", "B"):
            try: goals, un, acts, m = load(meth, vid)
            except FileNotFoundError: continue
            act_of, step_of, nrows, nsteps = official_rows(vid, acts)
            sizes = [g["n_actions"] for g in goals]; assigned = {i for g in goals for i in g["action_ids"]}
            pa, fa = purity(goals, act_of); ps, fs = purity(goals, step_of); c = cost(meth, vid)
            # time-leak sanity for A/B: goal span == min/max of its actions (times are attached by code, so this checks the merge)
            t = {a["action_id"]: a for a in acts}; leak = sum(1 for g in goals if meth != "S" and (g["start_s"] != t[g["action_ids"][0]]["start_s"] or g["end_s"] != max(t[i]["end_s"] for i in g["action_ids"])))
            row = {"video": vid, "method": meth, "goals": len(goals), "min": min(sizes), "med": statistics.median(sizes), "max": max(sizes), **{f"h_{k}": v for k, v in hist(sizes).items()},
                   "pct_4_20": round(100 * sum(4 <= s <= 20 for s in sizes) / len(sizes)), "assigned_pct": round(100 * len(assigned) / len(acts)), "unassigned": len(un), "goals_gap60": sum(1 for g in goals if g["n_interruptions_gt60s"]),
                   "purity_activity": None if pa is None else round(pa, 2), "goals_per_activity": None if fa is None else round(fa, 1), "purity_step": None if ps is None else round(ps, 2), "goals_per_step": None if fs is None else round(fs, 1),
                   "official_activity_rows": nrows, "official_steps": nsteps, "time_span_mismatch": leak, **c}
            out.append(row)
            md.append(f"| {meth} | {row['goals']} | {row['min']}/{row['med']}/{row['max']} | {hist(sizes)} | {row['pct_4_20']}% | {row['assigned_pct']}% | {row['unassigned']} | {row['goals_gap60']} | {row['purity_activity']} | {row['goals_per_activity']} | {row['purity_step']} | {row['goals_per_step']} | {c['calls']} | {c['in_tok']//1000}k/{c['out_tok']//1000}k/{c['think_tok']//1000}k | {c['wall_min']} |")
        md.append(f"\nOfficial references: {nrows} activity rows, {nsteps} recipe step spans.\n")
        for meth in ("A", "B"):
            try: goals, un, acts, m = load(meth, vid)
            except FileNotFoundError: continue
            md.append(f"\n<details><summary>{meth}: goal list</summary>\n\n| goal | actions | span (s, from official times) | gaps>60s | description |\n|---|---|---|---|---|")
            for g in goals: md.append(f"| {g['goal_id']} | {g['n_actions']} | {g['start_s']:.0f}-{g['end_s']:.0f} | {g['n_interruptions_gt60s']} | {g['description']} |")
            md.append("\n</details>\n")
    d = datetime.date.today().strftime("%m%d")
    open(f"{HERE}/out/compare_{d}.md", "w").write("\n".join(md))
    with open(f"{HERE}/out/compare_{d}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    print("\n".join(md))
if __name__ == "__main__": main(sys.argv[1:])
