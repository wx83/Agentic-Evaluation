#!/usr/bin/env python3
"""Audio tags per Method-E sub-goal from ground truth + rules (no Gemini): official HD-EPIC sound events inside the sub-goal, an
audio label (audio_critical / audio_helpful / visual_sufficient) using the av_goal_finder lexicon, and cue types (completion / location).
Usage: python -I audio_tags.py <out_dir> ...   -> <out_dir>/audio_tags.json"""
import json, os, sys, re, glob
import pandas as pd
sys.path.insert(0, "/mnt/work_new/weihanxu/experiments/av_goal_finder"); import find_av_goals as F
A = "/mnt/data_new/hd-epic/annotations/data"
def ts(s): h, m, sec = s.split(":"); return int(h) * 3600 + int(m) * 60 + float(sec)
_snd = None
def sounds(vid):
    global _snd
    if _snd is None:
        _snd = pd.read_csv(f"{A}/audio-annotations/HD_EPIC_Sounds.csv"); _snd["t0"] = _snd.start_timestamp.map(ts); _snd["t1"] = _snd.stop_timestamp.map(ts)
    s = _snd[_snd.video_id == vid]; return [{"t0": r.t0, "t1": r.t1, "class": r["class"]} for _, r in s.iterrows()]
# cue types (ours): what a sound can tell an agent
COMPLETION = {"beep": "appliance / timer finished or started", "click": "switch, lid or latch state changed", "sizzling / boiling": "pan or pot reached cooking temperature", "kettle / mixer / appliance": "appliance running (stops when done)"}
LOCATION = {"water": "sink / tap", "sizzling / boiling": "hob", "kettle / mixer / appliance": "appliance fixture (kettle, blender, air fryer...)", "open / close": "cupboard, drawer or fridge", "beep": "appliance fixture (oven, microwave, scale)", "cut / chop": "chopping board on counter", "scrub / scrape / scour / wipe": "sink or counter", "footstep": "person moving between zones"}
def episodes(ids, T, gap=20.0):
    out = []
    for i in sorted(ids, key=lambda i: T[i]["start_s"]):
        a, b = T[i]["start_s"], T[i]["end_s"]
        if out and a - out[-1][1] <= gap: out[-1][1] = max(out[-1][1], b)
        else: out.append([a, b])
    return out
def official_step_labels(vid):
    """per official step id -> av_goal_finder label (if the goal is in goals.jsonl)."""
    out = {}
    for l in open("/mnt/work_new/weihanxu/experiments/av_goal_finder/out/goals.jsonl"):
        g = json.loads(l)
        if g.get("dataset") != "hd-epic" or g.get("recording") != vid: continue
        for s in g["steps"]:
            k = s.get("step_id"); out.setdefault(k, s["audio"]["label"])  # step_times entry wins over prep if both present
    return out
def tag(out_dir):
    M = json.load(open(f"{out_dir}/merged.json")); vid = M["video_id"]; acts = json.load(open(f"{out_dir}/input_actions.json"))["actions"]; T = {a["action_id"]: a for a in acts}
    ev = sounds(vid); step_lab = official_step_labels(vid); res = {"video_id": vid, "sub_goals": {}, "official_step_labels": step_lab, "source": "HD_EPIC_Sounds.csv (official events) + av_goal_finder rules (ours); no model"}
    for g in M["goals"]:
        st = {"t0": g["start_s"], "t1": g["end_s"], "episodes": episodes(g["action_ids"], T), "text": g["description"]}
        inside = [e for e in ev if F.ep_overlap(st, e["t0"], e["t1"]) > 0]
        narr = " ".join(T[i]["narration"] for i in g["action_ids"])
        lex_main = F.lex_cues(g["description"]); lex_ctx = F.lex_cues(narr)
        strong_lex = sorted({c for w, c in lex_main if w >= 1.0})
        strong_ev = F.strong_sound_classes(inside, st, g["description"] + " " + narr, g["description"] + " " + narr)  # sub-goal text is short, so narrations may ground sustained sounds too (differs from step-level rule)
        dur = max(1e-3, sum(b - a for a, b in st["episodes"]))
        s_ann = min(1.0, sum(F.sound_w(e["class"]) * F.ep_overlap(st, e["t0"], e["t1"]) for e in inside) / dur * 2.0) if inside else 0.0
        s_lex = max([w for w, _ in lex_main] + [0.6 * w for w, _ in lex_ctx] + [0.0])
        label = "audio_critical" if (strong_lex or strong_ev) else ("audio_helpful" if (s_lex >= 0.6 or s_ann >= 0.3) else "visual_sufficient")
        classes = sorted({e["class"] for e in inside})
        res["sub_goals"][g["goal_id"]] = {"label": label, "cue_words": strong_lex or sorted({c for _, c in lex_main})[:6], "strong_sound_classes": strong_ev, "sound_event_coverage": round(s_ann, 2),
            "completion_cues": {c: COMPLETION[c] for c in classes if c in COMPLETION}, "location_cues": {c: LOCATION[c] for c in classes if c in LOCATION},
            "sound_events": [{"t0": round(e["t0"], 1), "t1": round(e["t1"], 1), "class": e["class"]} for e in sorted(inside, key=lambda e: e["t0"])],
            "official_step_label": step_lab.get(g["segment"]) if not g["segment"].startswith("nostep") else None}
    json.dump(res, open(f"{out_dir}/audio_tags.json", "w"), indent=1)
    from collections import Counter; c = Counter(x["label"] for x in res["sub_goals"].values()); print(os.path.basename(out_dir), dict(c), "| sub-goals with any sound event:", sum(1 for x in res["sub_goals"].values() if x["sound_events"]), "/", len(res["sub_goals"]))
if __name__ == "__main__":
    for d in sys.argv[1:]: tag(d.rstrip("/"))
