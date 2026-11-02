#!/usr/bin/env python3
"""Group the fine goals (steps) of method A/B into outcome-level top goals. Usage: python -I group.py <A|B> <vid> ... -> out/<m>/<vid>/top_goals.json"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import common
SYS = """You organise the steps of one egocentric kitchen video into top-level goals.
A top-level goal is a complete outcome the person is working towards, such as preparing one dish or component ("Bake the fish cakes", "Cook couscous", "Roast vegetables in the air fryer"), or a self-contained chore ("Wash up and tidy the kitchen", "Log the ingredients' nutrition in the phone app").
Each step you receive is already a short plan (a few actions) with its official time range. Assign every step to exactly one top-level goal. Steps of one goal are often interleaved with steps of another; keep them in the same goal regardless of gaps. Use 2 to 8 top-level goals; do not split one dish into several goals and do not merge different dishes. Name goals as imperative outcomes, grounded only in the step descriptions (no invented recipe names or ingredients). Never write times in any field; refer to steps by step_id only. Return only JSON."""
USR = """Video ID: {VID}
Existing coarse label for the whole video (hint only, may mix several goals): {LABEL}

Steps (step_id | official time range | description | number of actions):
{STEPS}

Return JSON: {{"top_goals": [{{"goal_id": "T1", "description": "...", "step_ids": ["..."], "rationale": "<one sentence, no times>"}}]}}
Every step_id must appear exactly once."""
def run(m, vid):
    p = f"{HERE}/out/{m}/{vid}/merged.json"; M = json.load(open(p)); out = f"{HERE}/out/{m}/{vid}/top_goals.json"
    steps = "\n".join(f'{g["goal_id"]} | {g["start_s"]:.0f}-{g["end_s"]:.0f}s | {g["description"]} | {g["n_actions"]}' for g in M["goals"])
    ids = [g["goal_id"] for g in M["goals"]]
    for attempt in range(3):
        r = common.call(SYS, USR.format(VID=vid, LABEL=M["existing_label"] or "null", STEPS=steps), f"top_goals{'' if not attempt else attempt}", vid, f"hdepic_goal_gen_top_{m}")
        used = [s for t in r["top_goals"] for s in t["step_ids"]]; errs = [s for s in used if s not in ids] + [s for s in ids if used.count(s) != 1]
        if not errs and not any(common.TIME_RE.search(t["description"]) for t in r["top_goals"]): break
        print("  retry:", errs[:5], flush=True)
    G = {g["goal_id"]: g for g in M["goals"]}
    for t in r["top_goals"]:
        ss = [G[s] for s in t["step_ids"]]; ss.sort(key=lambda g: g["start_s"])
        t["step_ids"] = [g["goal_id"] for g in ss]; t["start_s"] = ss[0]["start_s"]; t["end_s"] = max(g["end_s"] for g in ss); t["n_steps"] = len(ss); t["n_actions"] = sum(g["n_actions"] for g in ss)
    r["top_goals"].sort(key=lambda t: t["start_s"]); r["time_source"] = "copied from steps -> official narrations by code"; r["errors"] = errs
    json.dump(r, open(out, "w"), indent=1, ensure_ascii=False)
    print(m, vid, [(t["description"], t["n_steps"], f"{t['start_s']:.0f}-{t['end_s']:.0f}") for t in r["top_goals"]], flush=True)
if __name__ == "__main__":
    for v in sys.argv[2:]: run(sys.argv[1].upper(), v)
