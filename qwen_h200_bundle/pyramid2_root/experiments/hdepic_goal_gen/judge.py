#!/usr/bin/env python3
"""Blind pairwise Gemini judge of A vs B groupings on consecutive 60-action segments. Usage: python -I judge.py <vid> ... -> out/judge/<vid>.json"""
import json, os, sys, random, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import common
SEG = 60
SYS = """You are an expert annotator of egocentric kitchen videos evaluating two candidate groupings of the SAME timestamped action narrations into task goals.
A good goal is a plan a person follows to reach ONE identifiable outcome (as in the EgoPlan benchmark: "Clean and put away pan and spatula"), typically 4-20 actions, with boundaries at natural outcome changes; its description names the outcome, not a phase ("cooking") and not a single action.
Judge only from the narrations given. Do not reward longer or shorter goals per se. Return only JSON."""
USR = """Segment of video {VID} (official narrations with official times):
{ACTS}

Grouping X:
{X}

Grouping Y:
{Y}

Compare on: (1) granularity (goals are outcome-sized plans, not phases or single actions), (2) boundary correctness (goal starts/ends where the outcome changes; interrupted goals correctly resumed), (3) description quality (names the outcome, faithful to narrations, no invention), (4) overall which grouping you would rather hand to a human annotator to verify.
Return JSON: {{"granularity": "X|Y|tie", "boundaries": "X|Y|tie", "descriptions": "X|Y|tie", "overall": "X|Y|tie", "rationale": "<=2 sentences, no times"}}"""
def grouping(goals, seg_ids, t):
    s = set(seg_ids); out = []
    for g in sorted(goals, key=lambda g: min((t[i]["start_s"] for i in g["action_ids"] if i in s), default=1e9)):
        ids = sorted((i for i in g["action_ids"] if i in s), key=lambda i: t[i]["start_s"])
        if ids: out.append(f'- {g["description"]}  [{len(ids)} of {len(g["action_ids"])} actions in this segment: ' + ", ".join(i.split("-")[-1] for i in ids) + "]")
    return "\n".join(out) or "(no goals)"
def run(vid, m1="A", m2="B"):
    A = json.load(open(f"{HERE}/out/{m1}/{vid}/merged.json")); B = json.load(open(f"{HERE}/out/{m2}/{vid}/merged.json")); acts = json.load(open(f"{HERE}/out/{m1}/{vid}/input_actions.json"))["actions"]
    t = {a["action_id"]: a for a in acts}; os.makedirs(f"{HERE}/out/judge", exist_ok=True); p = f"{HERE}/out/judge/{vid}.json" if (m1, m2) == ("A", "B") else f"{HERE}/out/judge/{m1}{m2}_{vid}.json"
    res = json.load(open(p)) if os.path.exists(p) else []; done = {r["seg"] for r in res}; rng = random.Random(vid)
    for k in range(0, len(acts), SEG):
        if k // SEG in done: continue
        seg = acts[k:k + SEG]; ids = [a["action_id"] for a in seg]; flip = rng.random() < 0.5
        X, Y = (B, A) if flip else (A, B)
        prompt = USR.format(VID=vid, ACTS="\n".join(f'{a["action_id"].split("-")[-1]} [{a["start_s"]:.1f}-{a["end_s"]:.1f}s] {a["narration"]}' for a in seg), X=grouping(X["goals"], ids, t), Y=grouping(Y["goals"], ids, t))
        r = common.call(SYS, prompt, f"judge{m1}{m2}_seg{k // SEG:02d}", vid, "hdepic_goal_gen_judge")
        m = {"X": X["method"], "Y": Y["method"], "tie": "tie"}
        m = {"X": m1 if X is A else m2, "Y": m2 if Y is B else m1, "tie": "tie"}
        res.append({"seg": k // SEG, "first_action": ids[0], "x_is": m["X"], **{c: m.get(r.get(c), "?") for c in ("granularity", "boundaries", "descriptions", "overall")}, "rationale": r.get("rationale")})
        json.dump(res, open(p, "w"), indent=1, ensure_ascii=False); print(f"  seg {k // SEG}: overall {res[-1]['overall']}", flush=True)
    print(vid, {c: dict(collections.Counter(r[c] for r in res)) for c in ("granularity", "boundaries", "descriptions", "overall")})
if __name__ == "__main__":
    args = sys.argv[1:]; pair = args[0] if len(args[0]) == 2 and args[0].isalpha() and args[0].isupper() else None
    for v in (args[1:] if pair else args): run(v, *(pair if pair else "AB"))
