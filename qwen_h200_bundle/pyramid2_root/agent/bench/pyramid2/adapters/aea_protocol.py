"""AEA protocol clip(experiments/aea_protocol/out/candidates.json,用户 10-27 选定)-> evidence。
样本 = 一个单人 protocol 式 clip:goal = Gemini goal,plan = Gemini 步骤;两者都是模型输出(needs_verification),时间全部由代码从 legacy narration 复制。
  task_segment        goal + 步骤表                                          source aea_p.gemini_goal     needs_verification
  task_step × n       步骤(idx / text / narration_ids)                       source aea_p.gemini_step     needs_verification
  task_step (next)    最终截断参考 = "the goal is complete" + 4 选项,answer_only source aea_p.gemini_next     needs_verification
  action_narration    clip 内 ±60 s 的 legacy narration(逐秒自动 caption)      source aea_p.legacy_caption  needs_verification
  sound_event         legacy sound(带发声物体 object)                        source aea_p.legacy_sound    needs_verification
时间轴 = SAVVY 小视频秒数 = VRS 秒 − 第一帧 RGB 时刻(rgb_t0)。没有 narration 的步骤取前后步骤之间的空档,标 TIME_INTERPOLATED。
Gemini 判为错误的 narration(wrong_narration_ids)不入库。
抽样:python3 -m adapters.aea_protocol select  -> data/aea_p_samples.json
"""
import json, random, re, argparse
from pathlib import Path
import p2config as P
from ids import evidence_id
from adapters.base import Adapter, record

DS = "aea_p"
X = Path("/mnt/work_new/weihanxu/experiments/aea_protocol")
ANN = Path("/mnt/work_new/weihanxu/qa/annotations/aea")
VID = Path("/mnt/work_new/parallact_data/data/aea_data/Video")
SAMPLES = P.DATA / "aea_p_samples.json"
PICKED = ["loc2_script1_seq6_rec1__s1", "loc1_script1_seq6_rec1__s0"]   # 用户 10-27 选定
SRC_GOAL, SRC_STEP, SRC_NEXT, SRC_NARR, SRC_SOUND = "aea_p.gemini_goal", "aea_p.gemini_step", "aea_p.gemini_next", "aea_p.legacy_caption", "aea_p.legacy_sound"
COMPLETE = "The goal is complete; nothing more needs to be done for it."
STOP = {"the", "a", "an", "and", "then", "some", "more", "into", "onto", "in", "on", "to", "from", "with", "of", "out", "up", "back"}


def _verb_noun(text):
    toks = [t for t in re.findall(r"[a-z0-9'-]+", (text or "").lower()) if t not in STOP]
    return (toks[0] if toks else None), (toks[1] if len(toks) > 1 else None)


_VERB_FIX = {"holding": "hold", "opening": "open", "closing": "close", "taking": "take", "putting": "put", "placing": "place", "walking": "walk", "sitting": "sit",
             "grabbing": "grab", "pouring": "pour", "picking": "pick", "carrying": "carry", "reaching": "reach", "looking": "look", "standing": "stand", "moving": "move",
             "turning": "turn", "pulling": "pull", "pushing": "push", "throwing": "throw", "washing": "wash", "drying": "dry", "eating": "eat", "cutting": "cut"}
_NOUN_STOP = STOP | {"is", "are", "was", "were", "be", "being", "while", "towards", "toward", "at", "by", "for", "it", "its", "his", "her", "their", "hand", "hands", "left", "right", "both", "one", "two", "down", "off", "over", "under", "near", "away", "again", "still", "something"}


def _parse_narration(text):
    """legacy 自动 caption("opening fridge" / "walking to counter")-> (verbs, nouns):首个 -ing / 动词原形为 verb,其余内容词为 nouns(粗略,只供 anchor_pred / 名词检查)。"""
    toks = re.findall(r"[a-z][a-z'-]*", (text or "").lower())
    verbs, nouns = [], []
    for i, t in enumerate(toks):
        if t in _NOUN_STOP: continue
        if not verbs and (t.endswith("ing") or t in _VERB_FIX.values()): verbs.append(_VERB_FIX.get(t, t[:-3] if t.endswith("ing") and t not in _VERB_FIX else t)); continue
        if t not in nouns: nouns.append(t)
    return verbs, nouns


def select(seg_ids=PICKED, out=SAMPLES, seed=1027):
    C = {c["seg_id"]: c for c in json.load(open(X / "out/candidates.json"))}
    picked = []
    for sid in seg_ids:
        c = C[sid]; rec = c["recording"]; o = json.load(open(X / f"out/{rec}.json")); N = {n["id"]: n for n in o["narration"]}
        sc = c["screen"]; m = sc["metrics"]; wrong = set(sc.get("wrong_narration_ids") or [])
        steps = []
        for k, st in enumerate(sc["steps"], 1):
            ids_ = [i for i in st.get("narration_ids", []) if i in N and i not in wrong]
            steps.append({"idx": k, "text": st["step"], "narration_ids": ids_,
                          "t0": min(N[i]["z0"] for i in ids_) if ids_ else None, "t1": max(N[i]["z1"] for i in ids_) if ids_ else None})
        for k, st in enumerate(steps):       # 无 narration 的步骤:取前一步结束到后一步开始的空档
            if st["t0"] is None:
                a = next((s["t1"] for s in reversed(steps[:k]) if s["t1"] is not None), m["z0"])
                b = next((s["t0"] for s in steps[k + 1:] if s["t0"] is not None), m["z1"])
                st.update(t0=a, t1=max(b, a + 0.5), interpolated=True)
        others = [s["text"] for s in steps][::-1][:3]
        rng = random.Random(f"{seed}|{sid}"); opts = others + [COMPLETE]; rng.shuffle(opts)
        choices = dict(zip("ABCD", opts)); gold = next(L for L, t in choices.items() if t == COMPLETE)
        picked.append({"sample_id": sid, "video_id": rec, "goal": c["goal"], "t0": m["z0"], "t1": m["z1"], "rgb_t0": o["rgb_t0"], "steps": steps,
                       "wrong_narration_ids": sorted(wrong), "verify": c.get("verify"),
                       "next_action": {"text": COMPLETE, "choices": choices, "gold_letter": gold}})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"source": "experiments/aea_protocol/out/candidates.json (two-pass Gemini screen)", "seed": seed, "samples": picked}, indent=1, ensure_ascii=False))
    return picked


def load_samples():
    return json.loads(SAMPLES.read_text())["samples"] if SAMPLES.exists() else []


class AeaProtocol(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        self.samples = [s for s in load_samples() if not videos or s["video_id"] in videos]
        self.by_vid = {}
        for s in self.samples: self.by_vid.setdefault(s["video_id"], []).append(s)
        self.vids = sorted(self.by_vid)

    def videos(self): return self.vids

    def media(self):
        return [{"media_id": f"{DS}/{vid}", "dataset": DS, "video_id": vid, "kind": "source_video", "path": str(VID / f"{vid}.mp4"),
                 "fps": 20, "duration_sec": None, "resolution": [456, 456], "audio": "stereo (Aria mic 5+6)", "time_base": "source_video_seconds",
                 "offset_to_source_sec": 0.0, "parent_media_id": None,
                 "aux": {"samples": [s["sample_id"] for s in self.by_vid[vid]], "rgb_t0_vrs_sec": self.by_vid[vid][0]["rgb_t0"], "video_origin": "SAVVY undistorted small video"},
                 "annotation_sources": self.coverage(vid), "quality_flags": []} for vid in self.vids]

    def coverage(self, vid):
        ss = self.by_vid.get(vid, [])
        if not ss: return []
        a, b = min(s["t0"] for s in ss), max(s["t1"] for s in ss)
        cv = lambda t, c="partial": {"start_sec": a, "end_sec": b, "target_type": t, "completeness": c}
        return [{"source": SRC_GOAL, "n": len(ss), "provenance": "model (gemini-3.1-pro, two-pass screen)", "coverage": cv("task")},
                {"source": SRC_STEP, "n": sum(len(s["steps"]) for s in ss), "provenance": "model (gemini-3.1-pro)", "coverage": cv("task_step")},
                {"source": SRC_NARR, "n": None, "provenance": "model (legacy per-second automatic caption, SAVVY work files)", "coverage": cv("narration")},
                {"source": SRC_SOUND, "n": None, "provenance": "legacy SAVVY work files (origin unconfirmed)", "coverage": cv("sound", "unknown")}]

    def records(self, vid):
        mid = f"{DS}/{vid}"
        narr = json.load(open(ANN / f"narration/{vid}_narration.json")); snd = json.load(open(ANN / f"sound/{vid}_sound.json"))
        for s in self.by_vid.get(vid, []):
            sid, goal, t0v = s["sample_id"], s["goal"], s["rgb_t0"]
            cov = {"scope_start_sec": s["t0"], "scope_end_sec": s["t1"], "target_type": "task", "completeness": "complete"}
            ent = [{"entity_id": sid, "id_space": "task", "name": goal}]
            prov = {"source_type": "model_generated", "dataset": DS, "source": SRC_GOAL, "upstream_provenance": "model", "model": "gcp/google/gemini-3.1-pro-preview",
                    "source_file": "experiments/aea_protocol/out/candidates.json", "source_record_id": sid, "derived_from": []}
            steps_pub = [{"idx": st["idx"], "text": st["text"], "t0": st["t0"], "t1": st["t1"], "narration_ids": st["narration_ids"]} for st in s["steps"]]
            yield record(evidence_id=evidence_id(DS, vid, "goal", f"{sid}/seg"), video_id=vid, media_id=mid, kind="task_segment", domain="task.structure", t0=s["t0"], t1=s["t1"], event_id=sid,
                         value={"task_id": sid, "goal": goal, "n_steps": len(steps_pub), "steps": steps_pub, "status": "candidate",
                                "note": "goal and steps are Gemini outputs (not verified); times copied by code from legacy narration"},
                         epistemic="observation", modalities=["video"], entities=ent, provenance=prov, coverage=cov, flags=["GOAL_IS_MODEL", "STEPS_ARE_MODEL_SUBGOALS"])
            idx_of = {}
            for st in s["steps"]:
                for i in st["narration_ids"]: idx_of[i] = st["idx"]
                verb, noun = _verb_noun(st["text"])
                yield record(evidence_id=evidence_id(DS, vid, "gemini_step", f"{sid}/s{st['idx']}"), video_id=vid, media_id=mid, kind="task_step", domain="task.structure",
                             t0=st["t0"], t1=st["t1"], event_id=sid,
                             value={"task_id": sid, "idx": st["idx"], "text": st["text"], "verb": verb, "noun": noun, "goal": goal, "status": "candidate", "narration_ids": st["narration_ids"]},
                             epistemic="observation", modalities=["video"], entities=ent,
                             provenance={**prov, "source": SRC_STEP, "derived_from": [evidence_id(DS, vid, "narration", i) for i in st["narration_ids"]]},
                             coverage=cov, flags=["MODEL_SUBGOAL"] + (["TIME_INTERPOLATED"] if st.get("interpolated") else []))
            wrong = set(s["wrong_narration_ids"])
            for i, n in enumerate(narr):
                nid = f"N{i:03d}"; a, b = n["start_time"] - t0v, n["stop_time"] - t0v
                if nid in wrong or b < s["t0"] - 60 or a > s["t1"] + 60: continue
                k = idx_of.get(nid); inside = s["t0"] <= a <= s["t1"]
                yield record(evidence_id=evidence_id(DS, vid, "narration", nid), video_id=vid, media_id=mid, kind="action_narration", domain="physical.dynamics",
                             t0=a, t1=b, event_id=sid if inside else None,
                             value={"text": n["narration"], "label": n["narration"], "verbs": _parse_narration(n["narration"])[0], "nouns": _parse_narration(n["narration"])[1], "step_idx": k, "task_id": sid if inside else None,
                                    "unique_narration_id": nid, "outside_task": not inside},
                             epistemic="observation", modalities=["video"], entities=[],
                             provenance={**prov, "source_type": "dataset_annotation", "source": SRC_NARR, "upstream_provenance": "model (automatic caption)",
                                         "source_file": f"qa/annotations/aea/narration/{vid}_narration.json", "source_record_id": nid},
                             coverage={**cov, "target_type": "narration"}, flags=["AUTO_CAPTION"] + ([] if inside else ["OUTSIDE_TASK"]))
            na = s["next_action"]
            yield record(evidence_id=evidence_id(DS, vid, "gemini_next", f"{sid}/next"), video_id=vid, media_id=mid, kind="task_step", domain="task.structure",
                         t0=s["t1"], t1=s["t1"] + 1.0, event_id=sid,
                         value={"task_id": sid, "idx": len(s["steps"]) + 1, "text": na["text"], "verb": None, "noun": None, "goal": goal, "is_next_action": True,
                                "choices": na["choices"], "gold_letter": na["gold_letter"], "status": "candidate"},
                         epistemic="observation", modalities=["video"], solver_access="answer_only", entities=ent,
                         provenance={**prov, "source_type": "derived", "source": SRC_NEXT, "upstream_provenance": "rule (final cutoff = goal complete; distractors = steps)"},
                         coverage=cov, flags=["STEP_COMPLETE_REFERENCE", "NEXT_ACTION_END_UNKNOWN"])
            for i, e in enumerate(snd):
                a, b = e["start_time"] - t0v, e["stop_time"] - t0v
                if b < s["t0"] - 5 or a > s["t1"] + 5 or not (e.get("sound") or e.get("sound_event")): continue
                yield record(evidence_id=evidence_id(DS, vid, "sound", str(i)), video_id=vid, media_id=mid, kind="sound_event", domain="physical.dynamics",
                             t0=a, t1=b, event_id=sid,
                             value={"label": e["sound_event"], "label_phrase": f"{e['sound_event']} ({e['sound']})" if e.get("sound") else e["sound_event"], "class": e.get("sound") or None, "object": e.get("object") or None},
                             epistemic="observation", modalities=["audio"], entities=[],
                             provenance={**prov, "source_type": "dataset_annotation", "source": SRC_SOUND, "upstream_provenance": "legacy SAVVY work file (origin unconfirmed)",
                                         "source_file": f"qa/annotations/aea/sound/{vid}_sound.json", "source_record_id": str(i)},
                             coverage={**cov, "target_type": "sound", "completeness": "unknown"}, flags=([] if e.get("sound") else ["NO_SOUND_CLASS"]))   # 10-27:sound 字段空的事件也入库(can 取出),时间来自标注

    def items(self): return iter(())

    def files_read(self): return [SAMPLES, X / "out/candidates.json"]


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("select"); sp.add_parser("show")
    a = ap.parse_args()
    for s in (select() if a.cmd == "select" else load_samples()):
        print(s["sample_id"], f"{s['t0']}-{s['t1']}", s["goal"])
        for st in s["steps"]: print(f"   {st['idx']}. [{st['t0']}-{st['t1']}]{' (interp)' if st.get('interpolated') else ''} {st['text']}  {st['narration_ids']}")


if __name__ == "__main__":
    main()
