"""contact-rich 动作:从已建好的 action_narration 证据(HD-EPIC / Ego4D,人工 narration)按动词词表派生 contact_rich_action 记录。
动作本身是人工标注(observation);「这个动作在感知什么反馈」是词表提示(interpretation),只作 Examiner 的上下文不作 gold。
下一步动作不另存:检索时把 anchor 之后的 narration 作 answer_only 的 future 证据。"""
import json, re
from pathlib import Path
import p2config as P
from ids import evidence_id
from adapters.base import Adapter, record
from store import read_jsonl

CONTACT = {"squeeze": ("squeeze/press", "firmness / ripeness"), "press": ("squeeze/press", "firmness / doneness / contact force"),
           "pinch": ("squeeze/press", "firmness"), "poke": ("squeeze/press", "doneness / softness"), "pat": ("squeeze/press", "firmness"),
           "knead": ("knead/shape", "dough consistency / stickiness"), "fold": ("knead/shape", "dough consistency"), "roll": ("knead/shape", "dough consistency / thickness"),
           "shape": ("knead/shape", "dough consistency"), "mash": ("knead/shape", "softness"), "crush": ("squeeze/press", "hardness"),
           "tighten": ("twist/screw", "tightness / resistance"), "screw": ("twist/screw", "tightness"), "unscrew": ("twist/screw", "tightness"), "twist": ("twist/screw", "resistance / tightness"),
           "stir": ("stir/mix", "resistance / consistency"), "mix": ("stir/mix", "consistency"), "whisk": ("stir/mix", "consistency"),
           "cut": ("cut/chop", "hardness / resistance"), "chop": ("cut/chop", "hardness"), "slice": ("cut/chop", "hardness / resistance"), "grate": ("cut/chop", "resistance"), "peel": ("cut/chop", "skin adhesion"),
           "scrub": ("wipe/scrub", "residue / friction"), "scrape": ("wipe/scrub", "residue / adhesion"), "wipe": ("wipe/scrub", "residue / wetness"), "rub": ("wipe/scrub", "texture / residue"), "wring": ("wipe/scrub", "wetness"),
           "shake": ("shake/tap", "contents / weight"), "tap": ("shake/tap", "hardness / hollowness"), "flip": ("shake/tap", "doneness / adhesion to pan"),
           "pour": ("pour/fill", "weight / fill level / flow"), "spread": ("spread", "consistency / coverage"), "touch": ("feel", "temperature / texture"), "feel": ("feel", "any tactile property")}
VERB_RE = re.compile(r"#C C (\w+)")


def _ego_verb(text):
    m = VERB_RE.search(text or "")
    if not m: return None
    w = m.group(1).lower()
    for k in CONTACT:
        if w == k or w == k + "s" or w == k + "es" or (k.endswith("e") and w == k[:-1] + "ing") or w == k + "ing" or (w.endswith("ies") and k == w[:-3] + "y"):
            return k
    return None


class ContactRich(Adapter):
    dataset = "derived"

    def __init__(self, videos=None):
        self.rows = [r for r in read_jsonl(P.DATA / "evidence.jsonl") if r["kind"] in ("action_narration", "task_segment")]
        self.vids = sorted({r["video_id"] for r in self.rows if r["kind"] == "action_narration"} & set(videos or {r["video_id"] for r in self.rows}))

    def videos(self): return self.vids

    def coverage(self, vid):
        return [{"source": "derived.contact_rich", "n": None, "coverage": {"start_sec": None, "end_sec": None, "target_type": "contact_rich_action", "completeness": "partial"}}]

    def records(self, vid):
        narr = sorted([r for r in self.rows if r["kind"] == "action_narration" and r["video_id"] == vid], key=lambda r: r["time"]["start_sec"])
        tasks = [r for r in self.rows if r["kind"] == "task_segment" and r["video_id"] == vid and r["verification"]["status"] == "verified" and "WHOLE_VIDEO_GOAL" not in r["quality_flags"]]
        for i, r in enumerate(narr):
            v = r["value"]; ds = r["provenance"]["dataset"]
            if ds in ("hdepic", "hdepic_e"):                       # 10-27:hdepic_e 的 narration 同样带官方 verbs 列表
                verb = next((x for x in (v.get("verbs") or []) if x in CONTACT), None)
            else:
                verb = _ego_verb(v.get("text") or v.get("narration"))
            if not verb:
                continue
            ctype, prop = CONTACT[verb]
            t0, t1 = r["time"]["start_sec"], r["time"]["end_sec"]
            nxt = [n for n in narr[i + 1: i + 4] if n["time"]["start_sec"] >= t1 - 0.05 and n["time"]["start_sec"] <= t1 + 20]
            goal = next((t["value"].get("goal") for t in tasks if t["time"]["start_sec"] - 0.1 <= t0 <= t["time"]["end_sec"] + 0.1), None)
            objs = v.get("nouns") or []
            yield record(
                evidence_id=evidence_id(ds, vid, "contact", r["evidence_id"].split(":", 3)[-1].replace(":", "_")),
                video_id=vid, media_id=r["media_id"], kind="contact_rich_action", domain="physical.dynamics",
                t0=t0, t1=max(t1, t0 + 0.5), event_id=r.get("event_id"),
                value={"verb": verb, "contact_type": ctype, "feedback_property_hint": prop, "objects": objs,
                       "narration": v.get("narration") or v.get("text"), "hands": v.get("hands"), "task_goal": goal,
                       "next_actions_recorded": [{"text": n["value"].get("narration") or n["value"].get("text"), "t0": n["time"]["start_sec"], "evidence_id": n["evidence_id"]} for n in nxt],
                       "note": "feedback_property_hint comes from a verb lexicon, not from annotation; the next actions are what the recording shows, not the only valid choice"},
                epistemic="interpretation", modalities=["video"], solver_access="observed",
                entities=[{"entity_id": "name:" + o.replace(" ", "_"), "id_space": "name_only", "name": o} for o in objs[:3]],
                provenance={"source_type": "derived_lexicon", "dataset": ds, "source": f"{ds}.contact_rich", "source_file": r["provenance"].get("source_file"),
                            "source_record_id": r["evidence_id"], "legacy_eid": None, "derived_from": [r["evidence_id"]] + [n["evidence_id"] for n in nxt],
                            "method": "contact-rich verb lexicon over human narrations (adapters/contact_rich.py)"},
                coverage={"scope_start_sec": t0, "scope_end_sec": t1, "target_type": "contact_rich_action", "completeness": "partial"},
                flags=["LEXICON_DERIVED"] + ([] if nxt else ["NO_RECORDED_NEXT_ACTION"]))

    def files_read(self): return [P.DATA / "evidence.jsonl"]
