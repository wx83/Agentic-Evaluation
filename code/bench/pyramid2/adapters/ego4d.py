"""Ego4D 子集(ego4d_annotations.json,已统一到 parent 秒)-> evidence;QA 类来源留给 items。"""
import json
from pathlib import Path
import p2config as P
from ids import evidence_id, legacy_eid
from adapters.base import Adapter, record, rel_source

ROOT = Path(P.SOURCES["ego4d"])
MERGED = ROOT / "ego4d_annotations.json"
DS = "ego4d"
ITEM_SOURCES = {"nlq", "egoschema", "egoplan1", "egoplan2", "videgothink"}
KIND = {"narration": "action_narration", "fho": "hand_object_interaction", "fho_sta": "next_active_object",
        "fho_lta": "future_action_sequence", "fho_oscc_pnr": "object_state_change", "easg": "action_scene_graph",
        "paco": "object_parts_attributes", "moments": "activity_moment", "vq": "visual_query_track",
        "ego4d_sounds": "sound_event"}
DOMAIN = {"action_narration": "physical.dynamics", "hand_object_interaction": "physical.dynamics",
          "next_active_object": "physical.dynamics", "future_action_sequence": "task.structure",
          "object_state_change": "physical.dynamics", "action_scene_graph": "physical.dynamics",
          "object_parts_attributes": "physical.objects_properties", "activity_moment": "task.structure",
          "visual_query_track": "physical.objects_properties", "sound_event": "physical.objects_properties",
          "task_segment": "task.structure", "task_step": "task.structure", "utterance": "human.communication",
          "person_talking": "human.social", "person_looking": "human.attention"}
ANSWER_ONLY = {"fho_sta", "fho_lta"}
MODAL = {"ego4d_sounds": ["audio"], "utterance": ["audio"], "person_talking": ["video", "audio"]}
COMPLETE = {"goalstep": "complete"}


def media_id(uid): return f"{DS}/{uid}"


class Ego4d(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        self.vids = list(videos or P.EGO4D_VIDEOS)
        self._d = None

    def _data(self):
        if self._d is None:
            self._d = json.loads(MERGED.read_text())
        return self._d

    def videos(self): return self.vids

    def provenance_of(self, src):
        return self._data()["sources"].get(src, {}).get("provenance", "unknown")

    def media(self):
        rows = []
        for uid in self.vids:
            v = self._data()["videos"][uid]
            rows.append({"media_id": media_id(uid), "dataset": DS, "video_id": uid, "kind": "source_video",
                         "path": str(ROOT / v["video"]), "fps": v.get("fps"), "duration_sec": v.get("duration_sec"),
                         "resolution": v.get("resolution"), "audio": None, "time_base": "source_video_seconds",
                         "offset_to_source_sec": 0.0, "parent_media_id": None,
                         "aux": {"scenarios": v.get("scenarios")},
                         "annotation_sources": self.coverage(uid), "quality_flags": []})
        return rows

    def coverage(self, uid):
        v = self._data()["videos"][uid]; D = v["duration_sec"]
        out = []
        for src, evs in v["events"].items():
            if not evs:
                continue
            comp = COMPLETE.get(src, "partial")
            if src == "narration":
                comp = "partial"          # instants, 不保证每个动作都有
            out.append({"source": f"ego4d.{src}", "n": len(evs), "provenance": self.provenance_of(src),
                        "coverage": {"start_sec": 0, "end_sec": D, "target_type": src, "completeness": comp}})
        return out

    def records(self, uid):
        v = self._data()["videos"][uid]; D = v["duration_sec"]; mid = media_id(uid)
        for src, evs in v["events"].items():
            if src in ITEM_SOURCES:
                continue
            prov_kind = self.provenance_of(src)
            epi = "observation" if prov_kind == "human" else "interpretation"
            comp = COMPLETE.get(src, "partial")
            cov = {"scope_start_sec": 0, "scope_end_sec": D, "target_type": src, "completeness": comp}
            for i, e in enumerate(evs):
                t0, t1 = float(e["t_start"]), float(e.get("t_end", e["t_start"]))
                flags = []
                if t1 < t0: t1 = t0
                if abs(t1 - t0) < 1e-6: flags.append("INSTANT")
                if t0 < 0:
                    flags.append("NEGATIVE_TIME"); t0 = 0.0; t1 = max(t1, 0.0)
                ex = e.get("extra") or {}
                prov = {"source_type": "dataset_annotation", "dataset": DS, "source": f"ego4d.{src}",
                        "upstream_provenance": prov_kind, "source_file": rel_source(MERGED),
                        "source_record_id": ex.get("annotation_uid") or ex.get("unique_id"), "source_index": i,
                        "clip_uid": e.get("clip_uid") or None, "legacy_eid": legacy_eid(uid, src, i), "derived_from": []}
                base = dict(video_id=uid, media_id=mid, t0=t0, t1=t1, epistemic=epi, provenance=prov, coverage=cov)
                if src == "av":
                    k = ex.get("kind")
                    if k == "transcription":
                        pid = str(ex.get("person_id"))
                        uf = list(flags)
                        if not (e.get("text") or "").strip(): uf.append("EMPTY_TRANSCRIPT")
                        if pid in ("-1", "None", ""): uf.append("UNKNOWN_SPEAKER")
                        yield record(evidence_id=evidence_id(DS, uid, "av_transcription", t0=t0, t1=t1, label=e.get("label", ""), text=e.get("text", "")),
                                     kind="utterance", domain=DOMAIN["utterance"], epistemic="participant_report",
                                     modalities=["audio"], value={"transcript": e.get("text"), "speaker_id": f"person_{pid}", "label": e.get("label")},
                                     entities=[{"entity_id": f"person_{pid}", "id_space": "ego4d_person", "name": f"person {pid}"}],
                                     flags=uf, **{kk: vv for kk, vv in base.items() if kk != "epistemic"})
                    elif k in ("talking", "looking"):
                        pid = str(ex.get("person")); kind = "person_talking" if k == "talking" else "person_looking"
                        yield record(evidence_id=evidence_id(DS, uid, f"av_{k}", t0=t0, t1=t1, label=e.get("label", ""), text=str(ex)),
                                     kind=kind, domain=DOMAIN[kind], modalities=["video", "audio"] if k == "talking" else ["video"],
                                     value={"person_id": f"person_{pid}", "target": ex.get("target"), "is_at_me": ex.get("is_at_me"), "label": e.get("label")},
                                     entities=[{"entity_id": f"person_{pid}", "id_space": "ego4d_person", "name": f"person {pid}"}],
                                     flags=flags, **base)
                    continue
                if src == "goalstep":
                    # depth -1 = 整段视频总目标(只作背景,标 WHOLE_VIDEO_GOAL);depth 0 = step(作 task_segment,goal = label 的步骤名);depth 1 = substep(task_step)
                    depth = ex.get("depth")
                    kind = "task_segment" if depth in (-1, 0) else "task_step"
                    label = e.get("label") or ""
                    goal = label.split(":", 1)[1].strip() if (depth == 0 and ":" in label) else (label if depth == 0 else e.get("text"))
                    val = {"text": e.get("text"), "label": label, "depth": depth, "relevance": ex.get("relevance"), "goal": goal if depth != 1 else None}
                    if depth == 0:
                        subs = [s2 for s2 in evs if (s2.get("extra") or {}).get("depth") == 1 and s2["t_start"] >= t0 - 0.05 and s2["t_end"] <= t1 + 0.05]
                        val["steps"] = [{"idx": k2 + 1, "text": s2.get("text"), "t0": round(float(s2["t_start"]), 3), "t1": round(float(s2["t_end"]), 3), "label": s2.get("label")} for k2, s2 in enumerate(sorted(subs, key=lambda x: x["t_start"]))]
                        val["n_steps"] = len(val["steps"])
                    if depth == -1:
                        flags = flags + ["WHOLE_VIDEO_GOAL"]
                    yield record(evidence_id=evidence_id(DS, uid, "goalstep", t0=t0, t1=t1, label=label, text=e.get("text", "")),
                                 kind=kind, domain="task.structure", modalities=["video"], value=val,
                                 entities=[], flags=flags, **base)
                    continue
                kind = KIND.get(src)
                if kind is None:
                    continue
                val = {"text": e.get("text"), "label": e.get("label"), **{k2: v2 for k2, v2 in ex.items() if k2 not in ("annotation_uid",)}}
                upstream = ex.get("annotation_uid") or ex.get("unique_id")
                if src == "vq" and upstream:
                    upstream = f"{upstream}:{ex.get('query_video_frame')}"
                yield record(evidence_id=evidence_id(DS, uid, src, upstream, t0=t0, t1=t1, label=e.get("label", ""), text=e.get("text", "")),
                             kind=kind, domain=DOMAIN[kind], modalities=MODAL.get(src, ["video"]),
                             solver_access="answer_only" if src in ANSWER_ONLY else "observed",
                             value=val, entities=[], flags=flags, **base)

    def files_read(self): return [MERGED]
