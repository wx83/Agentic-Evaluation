#!/usr/bin/env python3
"""Method E (EgoPlan-Bench2 style): official recipe step = summary segment; Gemini extracts goals + action sequences inside each segment and excludes
unrelated actions; narrations outside every official step go into chronological 'no-step' windows. Usage: python -I method_e.py <vid> ..."""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import common
A = "/mnt/data_new/hd-epic/annotations/data"; rec = json.load(open(f"{A}/high-level/complete_recipes.json"))
SYS = """You extract task goals from one segment of an egocentric kitchen video, in the way EgoPlan-Bench2 built goals from Ego4D segment summaries.

You receive a SUMMARY of the segment (an official recipe step written by the dataset annotators, or a note that the segment is not covered by any recipe step) and the official timestamped action narrations inside the segment. The narrations of one recipe step may be non-contiguous because the person interleaves tasks.

Extract:
1. overall_goal: what this segment accomplishes, in your own short imperative phrase (do not just copy the summary).
2. goals: the subgoals, each a short imperative phrase for one clear purpose, each with its action_ids in chronological order. Prefer 4 to 20 actions per goal; do not make single-action goals and do not merge different purposes to reach a count.
3. unrelated_action_ids: actions in this segment that do not serve the summary's purpose (e.g. phone use, unrelated tidying while waiting). Do not force them into a goal.

Rules: use only the given narrations; never invent actions, ingredients or steps; refer to actions only by action_id; NEVER write times, durations or frame numbers in any output field. Every input action_id must appear exactly once, in a goal or in unrelated_action_ids. Return only JSON."""
USR = """Video ID: {VID}
Recipe: {RECIPE}
Segment {SEG}
Summary: {SUMMARY}

Actions in this segment ({N}):
{ACTIONS}

Return JSON: {{"overall_goal": "...", "goals": [{{"goal_id": "e1", "description": "...", "action_ids": ["..."], "rationale": "<one sentence, no times>"}}], "unrelated_action_ids": ["..."]}}"""
def segments(vid, acts, recipe_id=None):
    spans = []; recipe = None
    for rid, rv in rec.items():
        if recipe_id and rid != recipe_id: continue
        for c in rv["captures"]:
            if vid not in c["videos"]: continue
            recipe = f'{rv["name"]} ({rid})'
            for kind in ("step_times", "prep_times"):
                for sid, lst in c.get(kind, {}).items():
                    for x in lst:
                        if x["video"] == vid: spans.append((x["start"], x["end"], sid, rv["steps"].get(sid, sid)))
    by_step = collections.OrderedDict(); covered = set()
    for a in acts:
        mid = (a["start_s"] + a["end_s"]) / 2
        hit = sorted({(sid, txt) for s0, s1, sid, txt in spans if s0 <= mid <= s1})
        if hit:
            sid, txt = hit[0]; by_step.setdefault(sid, {"summary": f"Recipe step {sid.split('_')[-1]}: {txt}", "ids": []})["ids"].append(a["action_id"]); covered.add(a["action_id"])
    segs = [{"seg_id": sid, "kind": "step", **v} for sid, v in by_step.items()]
    return segs, covered, recipe
def run(vid, recipe_id=None, out_dir=None):
    acts, label = common.load_actions(vid); out = out_dir or f"{HERE}/out/E/{vid}"; os.makedirs(out, exist_ok=True)
    json.dump({"video_id": vid, "existing_label": label, "source": "HD_EPIC_Narrations.pkl (official)", "actions": acts}, open(f"{out}/input_actions.json", "w"), indent=1)
    T = {a["action_id"]: a for a in acts}; segs, covered, recipe = segments(vid, acts, recipe_id)
    goals = []; unrelated_pool = []; log = []
    def do(seg):
        p = f"{out}/{seg['seg_id']}.json"; ids = seg["ids"]
        if not os.path.exists(p):
            for attempt in range(3):
                r = common.call(SYS, USR.format(VID=vid, RECIPE=recipe or label or "unknown", SEG=seg["seg_id"], SUMMARY=seg["summary"], N=len(ids), ACTIONS="\n".join(common.fmt_action(T[i]) for i in ids)), f"E_{seg['seg_id']}{'' if not attempt else f'_r{attempt}'}", vid, "hdepic_goal_gen_E")
                r.setdefault("unassigned_action_ids", r.pop("unrelated_action_ids", [])); errs, warns = common.validate_window(r, ids, set()); r["_validation"] = {"errors": errs, "warnings": warns}
                if not errs: break
                print(f"  {seg['seg_id']}: {len(errs)} errors, retry: {errs[:2]}", flush=True)
            json.dump(r, open(p, "w"), indent=1, ensure_ascii=False)
        r = json.load(open(p)); log.append({"segment": seg["seg_id"], "n": len(ids), **r.get("_validation", {})})
        for g in r.get("goals", []):
            ids_ok = [i for i in g["action_ids"] if i in T]                   # 10-25:模型偶尔引用不存在的 action_id(P09 R02 KeyError '1048'),丢弃并记录
            if len(ids_ok) != len(g["action_ids"]): print(f"  {seg['seg_id']}: dropped {len(g['action_ids']) - len(ids_ok)} unknown action_ids in goal {g.get('goal_id')}", flush=True)
            if not ids_ok: continue
            goals.append({"goal_id": f"E_g{len(goals) + 1}", "description": g["description"], "action_ids": ids_ok, "segment": seg["seg_id"], "segment_summary": seg["summary"], "segment_overall_goal": r.get("overall_goal"), "model_goal_id": g.get("goal_id")})
        print(f"  {seg['seg_id']} ({seg['kind']}, {len(ids)} narr): {len(r.get('goals', []))} goals, {len(r.get('unassigned_action_ids', []))} unrelated | {r.get('overall_goal')}", flush=True)
        return [i for i in r.get("unassigned_action_ids", []) if i in T]          # 10-25:同样丢弃不存在的 id
    for seg in segs: unrelated_pool += do(seg)
    # no-step windows: everything not covered by a recipe step + what step segments rejected, chronological, 120 per window
    rest = sorted([a["action_id"] for a in acts if a["action_id"] not in covered] + unrelated_pool, key=lambda i: T[i]["start_s"])
    for k in range(0, len(rest), 120):
        ids = rest[k:k + 120]
        unrelated_pool2 = do({"seg_id": f"nostep_{k // 120:02d}", "kind": "nostep", "summary": "Not covered by any official recipe step (typically cleaning, weighing/logging ingredients, waiting, serving, or unrelated activity). Group these into goals by purpose; leave truly purposeless actions unrelated.", "ids": ids})
    common.attach_times(goals, acts)
    for g in goals: g["size_ok_4_20"] = 4 <= g["n_actions"] <= 20
    assigned = {i for g in goals for i in g["action_ids"]}; un = [a["action_id"] for a in acts if a["action_id"] not in assigned]
    json.dump({"video_id": vid, "method": "E", "model": common.MODEL, "existing_label": label, "recipe": recipe, "goals": goals, "unassigned_action_ids": un, "window_validation": log, "verification_status": "candidate (provisional, not verified)"}, open(f"{out}/merged.json", "w"), indent=1, ensure_ascii=False)
    sizes = [g["n_actions"] for g in goals]
    print(f"  {vid} E: {len(goals)} goals from {len(segs)} step segments + {(len(rest) + 119) // 120} no-step windows; sizes min/med/max {min(sizes)}/{sorted(sizes)[len(sizes)//2]}/{max(sizes)}; in 4-20 {sum(g['size_ok_4_20'] for g in goals)}; unassigned {len(un)}", flush=True)
if __name__ == "__main__":
    for v in sys.argv[1:]: run(v)
