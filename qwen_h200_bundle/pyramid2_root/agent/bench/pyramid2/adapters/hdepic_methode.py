"""HD-EPIC Method E(experiments/hdepic_goal_gen/out/E/<video>/merged.json)-> evidence。
样本 = 一个 (video, 官方 recipe step):goal = 官方 step 原文(ground truth),plan = 该 step 内的 Gemini sub-goal(模型候选,needs_verification),
narration 时间全部来自官方 HD_EPIC_Narrations.pkl。整份 recipe 不作 goal(太长),recipe 名只进 provenance。
  task_segment        goal(官方 step)+ sub-goal 表                         source hdepic_e.official_step    verified/dataset_gt
  task_step × n       sub-goal(idx / text / action_ids)                     source hdepic_e.gemini_subgoal   needs_verification(模型)
  task_step (next)    最终截断的参考 = "the step is complete" + 4 选项,answer_only source hdepic_e.gemini_next  needs_verification
  action_narration    step 内全部官方 narration(带 step_idx = sub-goal idx)  source hdepic_e.narration        verified/dataset_gt
  sound_event         官方 HD_EPIC_Sounds.csv 在样本窗口内的事件              source hdepic_e.sound            verified/dataset_gt
抽样:python3 -m adapters.hdepic_methode select [--n-per-video 1]  -> data/hdepic_e_samples.json
"""
import json, re, random, collections, argparse, os, glob
from pathlib import Path
import p2config as P
from ids import evidence_id
from adapters.base import Adapter, record

DS = "hdepic_e"
E_OUT = Path("/mnt/work_new/weihanxu/experiments/hdepic_goal_gen/out/E")
PICKS = Path("/mnt/work_new/weihanxu/experiments/hdepic_goal_gen/out/picks/top10_audio_subgoals.json")
HD = Path("/mnt/data_new/hd-epic")
SOUNDS = HD / "annotations/data/audio-annotations/HD_EPIC_Sounds.csv"
RECIPES = HD / "annotations/data/high-level/complete_recipes.json"
SAMPLES = P.DATA / "hdepic_e_samples.json"
SRC_STEP, SRC_SUB, SRC_NEXT, SRC_NARR, SRC_SOUND = "hdepic_e.official_step", "hdepic_e.gemini_subgoal", "hdepic_e.gemini_next", "hdepic_e.narration", "hdepic_e.sound"
COMPLETE = "The step is complete; nothing more needs to be done for it."
BACKGROUND = {"background", "footstep", "human", "rustle"}


def _ts(s):
    h, m, sec = s.split(":"); return int(h) * 3600 + int(m) * 60 + float(sec)


def _verb_noun(text):
    """sub-goal 描述 -> 首动词 + 首名词短语(粗略;只用于 value.verb/noun 字段)。"""
    toks = re.findall(r"[a-z0-9'-]+", (text or "").lower())
    if not toks: return None, None
    verb = toks[0]
    rest = [t for t in toks[1:] if t not in ("the", "a", "an", "and", "then", "some", "more", "into", "onto", "in", "on", "to", "from", "with", "of")]
    return verb, (rest[0] if rest else None)


def e_dirs():
    return sorted(p for p in glob.glob(str(E_OUT / "*")) if os.path.isdir(p) and os.path.exists(os.path.join(p, "merged.json")))


def candidate_steps(min_sub=3):
    """所有 (video, 官方 step) 候选:sub-goal ≥ min_sub;附 audio 统计与是否含 top10 audio sub-goal。"""
    picks = json.load(open(PICKS)) if PICKS.exists() else []
    pick_keys = {(p["video"], p["goal_id"]) for p in picks}
    rec = json.load(open(RECIPES)); out = []
    for d in e_dirs():
        M = json.load(open(f"{d}/merged.json")); tags = json.load(open(f"{d}/audio_tags.json"))["sub_goals"] if os.path.exists(f"{d}/audio_tags.json") else {}
        vid = M["video_id"]; rid = M["recipe"].split("(")[-1].rstrip(")"); rv = rec[rid]
        acts = {a["action_id"]: a for a in json.load(open(f"{d}/input_actions.json"))["actions"]}
        by = collections.defaultdict(list)
        for g in M["goals"]:
            if not g["segment"].startswith("nostep"): by[g["segment"]].append(g)
        for sid, gs in by.items():
            gs = sorted(gs, key=lambda g: g["start_s"])
            if len(gs) < min_sub: continue
            subs = []
            for k, g in enumerate(gs, 1):
                ids_ = sorted(g["action_ids"], key=lambda i: acts[i]["start_s"])
                subs.append({"idx": k, "text": g["description"], "t0": acts[ids_[0]]["start_s"], "t1": max(acts[i]["end_s"] for i in ids_), "action_ids": ids_,
                             "goal_id": g["goal_id"], "audio_label": (tags.get(g["goal_id"]) or {}).get("label"), "interrupted": bool(g["n_interruptions_gt60s"])})
            out.append({"sample_id": f"{vid}__{sid}", "video_id": vid, "official_step_id": sid, "goal": rv["steps"][sid], "recipe_id": rid, "recipe_name": rv["name"],
                        "e_dir": d, "t0": subs[0]["t0"], "t1": subs[-1]["t1"], "steps": subs,
                        "n_audio_critical": sum(1 for s in subs if s["audio_label"] == "audio_critical"),
                        "has_pick": any((vid, s["goal_id"]) in pick_keys for s in subs)})
    return out


def _choices(sample, all_steps_video, rng):
    """最终截断的 4 选项:正确 = COMPLETE;干扰 = 本 step 的 sub-goal(优先晚的),不足 3 个补同视频其它 step 的 sub-goal。"""
    own = [s["text"] for s in sample["steps"]][::-1]
    others = [s["text"] for o in all_steps_video if o["sample_id"] != sample["sample_id"] for s in o["steps"]]
    rng.shuffle(others)
    dis = (own + others)[:3]
    opts = dis + [COMPLETE]; rng.shuffle(opts)
    letters = "ABCD"; choices = {L: o for L, o in zip(letters, opts)}
    gold = next(L for L, o in choices.items() if o == COMPLETE)
    return choices, gold


def select(n_per_video=1, out=SAMPLES, seed=1023):
    cands = candidate_steps(); rng = random.Random(seed)
    by_vid = collections.defaultdict(list)
    for c in cands: by_vid[c["video_id"]].append(c)
    picked = []
    for vid, cs in sorted(by_vid.items()):
        cs.sort(key=lambda c: (not c["has_pick"], -c["n_audio_critical"], -len(c["steps"])))
        for c in cs[:n_per_video]:
            ch, gold = _choices(c, cs, random.Random(f"{seed}|{c['sample_id']}"))
            c = dict(c); c["next_action"] = {"text": COMPLETE, "choices": ch, "gold_letter": gold}
            picked.append(c)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"source": "experiments/hdepic_goal_gen/out/E (Method E) + complete_recipes.json", "seed": seed, "n_per_video": n_per_video,
                               "rule": "per video: steps containing a top-10 audio sub-goal first, then most audio_critical sub-goals, then most sub-goals; sub-goals >= 3",
                               "n_candidates": len(cands), "samples": picked}, indent=1, ensure_ascii=False))
    return picked


def load_samples():
    return json.loads(SAMPLES.read_text())["samples"] if SAMPLES.exists() else []


class HdEpicE(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        self.samples = [s for s in load_samples() if not videos or s["video_id"] in videos]
        self.by_vid = collections.defaultdict(list)
        for s in self.samples: self.by_vid[s["video_id"]].append(s)
        self.vids = sorted(self.by_vid)
        self._sounds = None

    def videos(self): return self.vids

    def _vpath(self, vid): return HD / "video" / vid.split("-")[0] / f"{vid}.mp4"

    def media(self):
        return [{"media_id": f"{DS}/{vid}", "dataset": DS, "video_id": vid, "kind": "source_video", "path": str(self._vpath(vid)),
                 "fps": None, "duration_sec": None, "resolution": None, "audio": None, "time_base": "source_video_seconds",
                 "offset_to_source_sec": 0.0, "parent_media_id": None,
                 "aux": {"samples": [s["sample_id"] for s in self.by_vid[vid]], "recipe": self.by_vid[vid][0]["recipe_name"]},
                 "annotation_sources": self.coverage(vid), "quality_flags": []} for vid in self.vids]

    def coverage(self, vid):
        ss = self.by_vid.get(vid, [])
        if not ss: return []
        a, b = min(s["t0"] for s in ss), max(s["t1"] for s in ss)
        return [{"source": SRC_STEP, "n": len(ss), "provenance": "human (official recipe step + step_times)", "coverage": {"start_sec": a, "end_sec": b, "target_type": "task", "completeness": "partial"}},
                {"source": SRC_SUB, "n": sum(len(s["steps"]) for s in ss), "provenance": "model (gemini-3.1-pro, Method E)", "coverage": {"start_sec": a, "end_sec": b, "target_type": "task_step", "completeness": "partial"}},
                {"source": SRC_NARR, "n": sum(len(st["action_ids"]) for s in ss for st in s["steps"]), "provenance": "human", "coverage": {"start_sec": a, "end_sec": b, "target_type": "narration", "completeness": "partial"}},
                {"source": SRC_SOUND, "n": None, "provenance": "human", "coverage": {"start_sec": a, "end_sec": b, "target_type": "sound", "completeness": "complete"}}]

    def sounds(self, vid):
        if self._sounds is None:
            import pandas as pd
            df = pd.read_csv(SOUNDS); df["t0"] = df.start_timestamp.map(_ts); df["t1"] = df.stop_timestamp.map(_ts); self._sounds = df
        d = self._sounds[self._sounds.video_id == vid]
        return [{"t0": float(r.t0), "t1": float(r.t1), "cls": r["class"], "i": int(i)} for i, r in d.iterrows()]

    def records(self, vid):
        mid = f"{DS}/{vid}"
        for s in self.by_vid.get(vid, []):
            sid, goal = s["sample_id"], s["goal"]; d = s["e_dir"]
            acts = {a["action_id"]: a for a in json.load(open(f"{d}/input_actions.json"))["actions"]}
            cov = {"scope_start_sec": s["t0"], "scope_end_sec": s["t1"], "target_type": "task", "completeness": "complete"}
            ent = [{"entity_id": sid, "id_space": "task", "name": goal}]
            prov = {"source_type": "dataset_annotation", "dataset": DS, "source": SRC_STEP, "upstream_provenance": "human",
                    "source_file": "hd-epic/annotations/data/high-level/complete_recipes.json", "source_record_id": s["official_step_id"],
                    "recipe_id": s["recipe_id"], "recipe_name": s["recipe_name"], "derived_from": []}
            steps_pub = [{"idx": st["idx"], "text": st["text"], "t0": st["t0"], "t1": st["t1"], "action_ids": st["action_ids"]} for st in s["steps"]]
            seg_id = evidence_id(DS, vid, "official_step", f"{s['official_step_id']}/seg")
            yield record(evidence_id=seg_id, video_id=vid, media_id=mid, kind="task_segment", domain="task.structure", t0=s["t0"], t1=s["t1"], event_id=sid,
                         value={"task_id": sid, "goal": goal, "official_step_id": s["official_step_id"], "n_steps": len(steps_pub), "steps": steps_pub, "status": "verified",
                                "note": "goal = official recipe step (ground truth); steps = Gemini sub-goals (candidate, not verified)"},
                         epistemic="observation", modalities=["video"], entities=ent, provenance=prov, coverage=cov, flags=["STEPS_ARE_MODEL_SUBGOALS", "HDEPIC_METHOD_E"])
            for st in s["steps"]:
                k = st["idx"]; verb, noun = _verb_noun(st["text"]); narr_ids = [evidence_id(DS, vid, "narration", i.split("-")[-1]) for i in st["action_ids"]]
                yield record(evidence_id=evidence_id(DS, vid, "gemini_subgoal", f"{s['official_step_id']}/s{k}"), video_id=vid, media_id=mid, kind="task_step", domain="task.structure",
                             t0=st["t0"], t1=st["t1"], event_id=sid,
                             value={"task_id": sid, "idx": k, "text": st["text"], "verb": verb, "noun": noun, "goal": goal, "status": "candidate", "action_ids": st["action_ids"],
                                    "audio_label": st.get("audio_label"), "e_goal_id": st["goal_id"]},
                             epistemic="observation", modalities=["video"], entities=ent,
                             provenance={**prov, "source_type": "model_generated", "source": SRC_SUB, "upstream_provenance": "model", "model": "gcp/google/gemini-3.1-pro-preview",
                                         "source_file": f"experiments/hdepic_goal_gen/out/E/{os.path.basename(d)}/merged.json", "source_record_id": st["goal_id"], "derived_from": narr_ids},
                             coverage=cov, flags=["MODEL_SUBGOAL"] + (["INTERRUPTED"] if st.get("interrupted") else []))
                for i in st["action_ids"]:
                    a = acts[i]
                    yield record(evidence_id=evidence_id(DS, vid, "narration", i.split("-")[-1]), video_id=vid, media_id=mid, kind="action_narration", domain="physical.dynamics",
                                 t0=a["start_s"], t1=a["end_s"], event_id=sid,
                                 value={"text": a["narration"], "label": a["narration"], "verbs": a.get("verbs") or [], "nouns": a.get("nouns") or [], "step_idx": k, "task_id": sid,
                                        "unique_narration_id": i},
                                 epistemic="observation", modalities=["video"], entities=[],
                                 provenance={**prov, "source": SRC_NARR, "source_file": "hd-epic/annotations/data/narrations-and-action-segments/HD_EPIC_Narrations.pkl", "source_record_id": i},
                                 coverage={**cov, "target_type": "narration"}, flags=[])
            # 10-23:样本窗口 ±60 s 内不属于任何 sub-goal 的官方 narration 也放进来(event_id None):cutoff 前 30 s 窗口要有内容,追问也可用 scope 外 event
            used = {i for st in s["steps"] for i in st["action_ids"]}
            for i, a in acts.items():
                if i in used or a["end_s"] < s["t0"] - 60 or a["start_s"] > s["t1"] + 60: continue
                yield record(evidence_id=evidence_id(DS, vid, "narration", i.split("-")[-1]), video_id=vid, media_id=mid, kind="action_narration", domain="physical.dynamics",
                             t0=a["start_s"], t1=a["end_s"], event_id=None,
                             value={"text": a["narration"], "label": a["narration"], "verbs": a.get("verbs") or [], "nouns": a.get("nouns") or [], "step_idx": None, "task_id": None,
                                    "unique_narration_id": i, "outside_task": True},
                             epistemic="observation", modalities=["video"], entities=[],
                             provenance={**prov, "source": SRC_NARR, "source_file": "hd-epic/annotations/data/narrations-and-action-segments/HD_EPIC_Narrations.pkl", "source_record_id": i},
                             coverage={**cov, "target_type": "narration"}, flags=["OUTSIDE_TASK"])
            na = s["next_action"]
            yield record(evidence_id=evidence_id(DS, vid, "gemini_next", f"{s['official_step_id']}/next"), video_id=vid, media_id=mid, kind="task_step", domain="task.structure",
                         t0=s["t1"], t1=s["t1"] + 1.0, event_id=sid,
                         value={"task_id": sid, "idx": len(s["steps"]) + 1, "text": na["text"], "verb": None, "noun": None, "goal": goal, "is_next_action": True,
                                "choices": na["choices"], "gold_letter": na["gold_letter"], "status": "candidate"},
                         epistemic="observation", modalities=["video"], solver_access="answer_only", entities=ent,
                         provenance={**prov, "source_type": "derived", "source": SRC_NEXT, "upstream_provenance": "rule (final cutoff = step complete; distractors = sub-goals)", "source_record_id": f"{s['official_step_id']}/next"},
                         coverage=cov, flags=["STEP_COMPLETE_REFERENCE", "NEXT_ACTION_END_UNKNOWN"])
            for ev in self.sounds(vid):
                if ev["t1"] < s["t0"] - 5 or ev["t0"] > s["t1"] + 5: continue
                yield record(evidence_id=evidence_id(DS, vid, "sound", f"{ev['i']}"), video_id=vid, media_id=mid, kind="sound_event", domain="physical.dynamics",
                             t0=ev["t0"], t1=ev["t1"], event_id=sid, value={"label": ev["cls"], "label_phrase": ev["cls"], "class": ev["cls"]},
                             epistemic="observation", modalities=["audio"], entities=[],
                             provenance={**prov, "source": SRC_SOUND, "source_file": "hd-epic/annotations/data/audio-annotations/HD_EPIC_Sounds.csv", "source_record_id": str(ev["i"])},
                             coverage={**cov, "target_type": "sound"}, flags=(["BACKGROUND_CLASS"] if ev["cls"] in BACKGROUND else []))

    def items(self): return iter(())

    def files_read(self): return [SAMPLES, SOUNDS, RECIPES]


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("select"); s.add_argument("--n-per-video", type=int, default=1); s.add_argument("--seed", type=int, default=1023)
    sp.add_parser("show"); sp.add_parser("candidates")
    a = ap.parse_args()
    if a.cmd == "select":
        for c in select(a.n_per_video, seed=a.seed):
            print(f"{c['sample_id']:36s} {c['recipe_name'][:26]:26s} subs={len(c['steps'])} crit={c['n_audio_critical']} pick={c['has_pick']} {c['t0']/60:5.1f}-{c['t1']/60:5.1f} min | {c['goal'][:70]}")
    elif a.cmd == "candidates":
        for c in candidate_steps(): print(f"{c['sample_id']:36s} subs={len(c['steps'])} crit={c['n_audio_critical']} pick={c['has_pick']}")
    else:
        for s in HdEpicE().samples: print(s["sample_id"], s["goal"], len(s["steps"]))


if __name__ == "__main__":
    main()
