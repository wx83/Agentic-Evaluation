"""Shared pieces for HD-EPIC goal generation at EgoPlan granularity (methods A and B).
Gemini only groups official action_ids; all times in outputs are copied from the official input by this code."""
import json, os, re, sys, time, datetime, collections
import pandas as pd
sys.path.insert(0, "/mnt/work_new/weihanxu/gemini"); import nv_gemini as NV
from google.genai import types
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "gcp/google/gemini-3.1-pro-preview"
A = "/mnt/data_new/hd-epic/annotations/data"
USAGE = f"{HERE}/out/gemini_calls.jsonl"
WIN, CTX = 120, 20          # actions per window, previous-tail context actions
_nar = None; _rec = None
def narrations():
    global _nar, _rec
    if _nar is None:
        _nar = pd.read_pickle(f"{A}/narrations-and-action-segments/HD_EPIC_Narrations.pkl"); _rec = json.load(open(f"{A}/high-level/complete_recipes.json"))
    return _nar, _rec
def load_actions(vid):
    nar, rec = narrations(); nv = nar[nar.video_id == vid].sort_values(["start_timestamp", "end_timestamp"])
    acts = [{"action_id": r.unique_narration_id, "start_s": round(float(r.start_timestamp), 2), "end_s": round(float(r.end_timestamp), 2), "narration": r.narration.strip(),
             "verbs": list(r.verbs), "nouns": list(r.nouns)} for r in nv.itertuples()]
    labels = [f"{rv['name']} ({rid})" for rid, rv in rec.items() for c in rv["captures"] if vid in c["videos"]]
    return acts, ("; ".join(labels) or None)
def fmt_action(a, ctx=False):
    s = f'{a["action_id"]} [{a["start_s"]:.2f}-{a["end_s"]:.2f}s] {a["narration"]}'
    return ("(context only, already handled) " + s) if ctx else s
def windows(acts):
    """Sequential windows of WIN actions; each carries the previous CTX actions as read-only context."""
    out = []
    for k in range(0, len(acts), WIN):
        out.append({"idx": k // WIN, "context": acts[max(0, k - CTX):k], "assign": acts[k:k + WIN]})
    return out
def call(system, prompt, tag, vid, role):
    cl = NV.client(timeout_ms=900_000)
    for attempt in range(4):
        t = time.time()
        try:
            txt = []; u = None; fin = None
            for ch in cl.models.generate_content_stream(model=MODEL, contents=prompt, config=types.GenerateContentConfig(system_instruction=system, temperature=0.0, max_output_tokens=65535, response_mime_type="application/json")):
                if ch.text: txt.append(ch.text)
                if ch.usage_metadata: u = ch.usage_metadata
                if ch.candidates and ch.candidates[0].finish_reason: fin = ch.candidates[0].finish_reason
            raw = "".join(txt)
            with open(USAGE, "a") as f: f.write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "role": role, "video": vid, "tag": tag, "model": MODEL, "key_id": NV.key_id(), "latency_s": round(time.time() - t, 1),
                "prompt_tokens": getattr(u, "prompt_token_count", None), "output_tokens": getattr(u, "candidates_token_count", None), "thoughts_tokens": getattr(u, "thoughts_token_count", None), "finish": str(fin)}) + "\n")
            return json.loads(raw)
        except Exception as e:
            with open(USAGE, "a") as f: f.write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "role": role, "video": vid, "tag": tag, "model": MODEL, "error": str(e)[:300]}) + "\n")
            print(f"  {tag} attempt {attempt+1} failed: {str(e)[:160]}", flush=True); time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"{tag} failed")
TIME_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:s|sec|seconds?|min|minutes?)\b|\b\d{1,2}:\d{2}\b")
def validate_window(resp, assign_ids, known_goal_ids):
    """Return (errors, warnings). Hard errors -> retry the window."""
    errs, warns = [], []; want = set(assign_ids); seen = collections.Counter()
    for g in resp.get("goals", []):
        for k in ("goal_id", "description", "action_ids"):
            if k not in g: errs.append(f"goal missing {k}: {str(g)[:80]}")
        for i in g.get("action_ids", []):
            if i not in want: errs.append(f"{g.get('goal_id')}: id {i} not in this window's assignable set")
            seen[i] += 1
        for k, v in g.items():
            if isinstance(v, str) and TIME_RE.search(v): errs.append(f"{g.get('goal_id')}.{k} contains a time expression: {v[:60]}")
    for i in resp.get("unassigned_action_ids", []):
        if i not in want: errs.append(f"unassigned id {i} not in window")
        seen[i] += 1
    for i, n in seen.items():
        if n > 2: errs.append(f"{i} used {n} times")
        elif n == 2: warns.append(f"{i} shared by 2 goals")
    miss = [i for i in assign_ids if i not in seen]
    if miss: errs.append(f"{len(miss)} window ids not covered: {miss[:5]}")
    return errs, warns
def attach_times(goals, acts):
    t = {a["action_id"]: a for a in acts}
    for g in goals:
        ids = sorted(g["action_ids"], key=lambda i: t[i]["start_s"]); g["action_ids"] = ids
        g["start_s"] = t[ids[0]]["start_s"]; g["end_s"] = max(t[i]["end_s"] for i in ids); g["n_actions"] = len(ids)
        g["time_source"] = "copied from HD_EPIC_Narrations.pkl by code"
        gaps = [t[ids[k + 1]]["start_s"] - t[ids[k]]["end_s"] for k in range(len(ids) - 1)]
        g["n_interruptions_gt60s"] = sum(1 for x in gaps if x > 60)
    return goals
def run_method(vid, method, system, build_prompt, out_dir):
    """Generic window loop. build_prompt(vid, label, window, prev_goals) -> user prompt string."""
    acts, label = load_actions(vid); os.makedirs(out_dir, exist_ok=True)
    json.dump({"video_id": vid, "existing_label": label, "source": "HD_EPIC_Narrations.pkl (official)", "actions": acts}, open(f"{out_dir}/input_actions.json", "w"), indent=1)
    goals = {}; order = []; unassigned = []; wlog = []
    for w in windows(acts):
        tag = f"w{w['idx']:02d}"; p = f"{out_dir}/{tag}.json"; aid = [a["action_id"] for a in w["assign"]]
        prev = [goals[g] for g in order[-8:]] if method != 'C' else [goals[g] for g in order]  # C: all goals stay open (interleaving across the whole video)
        if not os.path.exists(p):
            for attempt in range(3):
                resp = call(system, build_prompt(vid, label, w, prev), f"{tag}{'' if not attempt else f'_r{attempt}'}", vid, f"hdepic_goal_gen_{method}")
                errs, warns = validate_window(resp, aid, set(goals)); resp["_validation"] = {"errors": errs, "warnings": warns}
                if not errs: break
                print(f"  {tag}: {len(errs)} errors, retrying: {errs[:3]}", flush=True)
            json.dump(resp, open(p, "w"), indent=1, ensure_ascii=False)
        resp = json.load(open(p)); wlog.append({"window": tag, **resp.get("_validation", {})})
        for g in resp.get("goals", []):
            ext = g.get("extends_goal_id")
            if ext and ext in goals: goals[ext]["action_ids"] += g["action_ids"]; goals[ext]["windows"].append(tag); continue
            gid = f"{method}_g{len(order) + 1}"
            goals[gid] = {"goal_id": gid, "description": g["description"], "parent_chain": g.get("parent_chain"), "action_ids": list(g["action_ids"]), "windows": [tag], "model_goal_id": g.get("goal_id")}
            order.append(gid)
        unassigned += resp.get("unassigned_action_ids", [])
        print(f"  {tag}: {len(resp.get('goals', []))} goals, {len(resp.get('unassigned_action_ids', []))} unassigned", flush=True)
    G = attach_times([goals[g] for g in order], acts)
    for g in G: g["size_ok_4_20"] = 4 <= g["n_actions"] <= 20
    merged = {"video_id": vid, "method": method, "model": MODEL, "existing_label": label, "goals": G, "unassigned_action_ids": unassigned, "window_validation": wlog,
              "verification_status": "candidate (provisional, not verified)"}
    json.dump(merged, open(f"{out_dir}/merged.json", "w"), indent=1, ensure_ascii=False)
    sizes = [g["n_actions"] for g in G]
    print(f"  {vid} {method}: {len(G)} goals; sizes min/med/max {min(sizes)}/{sorted(sizes)[len(sizes)//2]}/{max(sizes)}; in 4-20: {sum(g['size_ok_4_20'] for g in G)}; unassigned {len(unassigned)}", flush=True)
    return merged
