"""HD-EPIC 子集 -> evidence。narration/sound/movement 经 TimelineIndex(保留位置 legacy_eid),
assoc/mask/recipe/complete_recipes/gaze 直接读 raw/*.json。"""
import json, re
from pathlib import Path
import p2config as P
import config as C
from timeline_index import TimelineIndex
from ids import evidence_id, legacy_eid
from adapters.base import Adapter, record, rel_source

ROOT = Path(P.SOURCES["hdepic"])
VROOT = Path(P.SOURCES["hdepic_videos"])
GROOT = Path(P.SOURCES["hdepic_gaze"])
DS = "hdepic"
HUMAN = {"source_type": "human_annotation", "dataset": DS}


def media_id(vid): return f"{DS}/{vid}"


def _prov(src, file, rid=None, idx=None, leg=None, derived=None):
    d = {**HUMAN, "source": src, "source_file": rel_source(file), "source_record_id": rid,
         "source_index": idx, "legacy_eid": leg, "derived_from": derived or []}
    return d


def _cov(t0, t1, target, completeness):
    return {"scope_start_sec": round(t0, 3), "scope_end_sec": round(t1, 3), "target_type": target,
            "completeness": completeness}


def _name_entity(name):
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    return {"entity_id": f"name:{slug}", "id_space": "name_only", "name": name}


class HdEpic(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        self.vids = list(videos or P.HDEPIC_VIDEOS)
        self._files = []
        self._meta = {}

    def videos(self): return self.vids

    def meta(self, vid):
        if vid not in self._meta:
            p = ROOT / vid / "metadata.json"
            self._files.append(p)
            self._meta[vid] = json.loads(p.read_text())
        return self._meta[vid]

    def video_path(self, vid):
        return next(VROOT.glob(f"*/{vid}.mp4"))

    def media(self):
        rows = []
        for vid in self.vids:
            m = self.meta(vid)
            vp = self.video_path(vid)
            part = vid[:3]
            gz = GROOT / part / f"mps_{vid}_vrs.zip"
            rows.append({"media_id": media_id(vid), "dataset": DS, "video_id": vid, "kind": "source_video",
                         "path": str(vp), "fps": m["fps"], "duration_sec": m["duration_sec"],
                         "resolution": None, "audio": None, "time_base": "source_video_seconds",
                         "offset_to_source_sec": 0.0, "parent_media_id": None,
                         "aux": {"gaze_vrs_zip": str(gz) if gz.exists() else None,
                                 "mp4_to_vrs_csv": str(vp.with_name(f"{vid}_mp4_to_vrs_time_ns.csv")),
                                 "vrs_to_mp4_log": str(vp.with_name(f"{vid}_vrs_to_mp4_log.json"))},
                         "annotation_sources": self.coverage(vid), "quality_flags": []})
        return rows

    def coverage(self, vid):
        m = self.meta(vid); D = m["duration_sec"]; bs = m["by_source"]
        return [
            {"source": "hdepic.sound", "n": bs.get("sound", 0), "coverage": {"start_sec": 0, "end_sec": D, "target_type": "sound_label", "completeness": "complete"}},
            {"source": "hdepic.narration", "n": bs.get("narration", 0), "coverage": {"start_sec": 0, "end_sec": D, "target_type": "action", "completeness": "complete"}},
            {"source": "hdepic.movement", "n": bs.get("movement", 0), "coverage": {"start_sec": 0, "end_sec": D, "target_type": "tracked_object", "completeness": "complete"}},
            {"source": "hdepic.assoc", "n": None, "coverage": {"start_sec": 0, "end_sec": D, "target_type": "tracked_object", "completeness": "complete"}},
            {"source": "hdepic.mask", "n": None, "coverage": {"start_sec": 0, "end_sec": D, "target_type": "object_anchor", "completeness": "partial"}},
            {"source": "hdepic.recipe", "n": None, "coverage": {"start_sec": 0, "end_sec": D, "target_type": "activity_segment", "completeness": "complete"}},
            {"source": "hdepic.gaze_priming", "n": None, "coverage": {"start_sec": 0, "end_sec": D, "target_type": "gaze_priming", "completeness": "partial"}},
            {"source": "hdepic.vqa", "n": m.get("n_vqa"), "coverage": {"start_sec": 0, "end_sec": D, "target_type": "qa", "completeness": "partial"}},
        ]

    def records(self, vid):
        m = self.meta(vid); D = m["duration_sec"]; fps = m["fps"]; mid = media_id(vid)
        root = ROOT / vid
        tl = root / "timeline.json"; self._files.append(tl)
        ix = TimelineIndex(vid)
        # 位置 id: TimelineIndex 的顺序
        for ev in ix.events:
            i = int(ev.eid.rsplit(":", 1)[1])
            if ev.source == "sound":
                flags = ["BACKGROUND_CLASS"] if ev.label in C.SKIP_SOUNDS else []
                yield record(
                    evidence_id=evidence_id(DS, vid, "sound", t0=ev.t_start, t1=ev.t_end, label=ev.label),
                    video_id=vid, media_id=mid, kind="sound_event", domain="physical.objects_properties",
                    t0=ev.t_start, t1=ev.t_end,
                    value={"label": ev.label, "label_phrase": C.SOUND_PHRASE.get(ev.label),
                           "device_sound": ev.label in C.DEVICE_SOUNDS},
                    epistemic="observation", modalities=["audio"],
                    provenance=_prov("hdepic.sound", root / "raw" / "sounds.json", idx=i, leg=legacy_eid(vid, "sound", i)),
                    coverage=_cov(0, D, "sound_label", "complete"), flags=flags)
            elif ev.source == "narration":
                ex = ev.extra
                nid = ex.get("unique_narration_id") or ""
                key = nid[len(vid) + 1:] if nid.startswith(vid + "-") else (nid or None)
                ents = [_name_entity(n) for n in (ex.get("nouns") or [])]
                yield record(
                    evidence_id=evidence_id(DS, vid, "narration", key, t0=ev.t_start, t1=ev.t_end, label=ev.label, text=ev.text),
                    video_id=vid, media_id=mid, kind="action_narration", domain="physical.dynamics",
                    t0=ev.t_start, t1=ev.t_end,
                    value={"narration": ev.text, "label": ev.label, "verbs": ex.get("verbs"), "nouns": ex.get("nouns"),
                           "pairs": ex.get("pairs"), "hands": ex.get("hands"), "unique_narration_id": nid},
                    epistemic="observation", modalities=["video"], entities=ents,
                    provenance=_prov("hdepic.narration", root / "raw" / "narrations.json", rid=nid, idx=i, leg=legacy_eid(vid, "narration", i)),
                    coverage=_cov(0, D, "action", "complete"))
            elif ev.source == "movement":
                ex = ev.extra
                aid, tid = ex.get("association_id"), ex.get("track_id")
                trans = bool(ex.get("is_transition")) and " -> " in ev.label and "mid-air" not in ev.label
                kind = "object_location_transition" if trans else "object_move"
                val = {"object_name": ex.get("object_name") or ev.text, "label": ev.label,
                       "association_id": aid, "track_id": tid,
                       "from_fixture": ex.get("from_fixture"), "to_fixture": ex.get("to_fixture"),
                       "from_fixture_kind": ix.fixture_kind(ex.get("from_fixture") or ""),
                       "to_fixture_kind": ix.fixture_kind(ex.get("to_fixture") or ""),
                       "start_xyz": ex.get("start_xyz"), "end_xyz": ex.get("end_xyz"),
                       "is_transition": bool(ex.get("is_transition")),
                       "relation_type": "observed_transition" if trans else "observed_motion"}
                ents = [{"entity_id": aid, "id_space": "hdepic_assoc", "name": val["object_name"]}] if aid else [_name_entity(val["object_name"])]
                yield record(
                    evidence_id=evidence_id(DS, vid, "movement", f"{aid}:{tid}" if aid and tid else None,
                                            t0=ev.t_start, t1=ev.t_end, label=ev.label, text=ev.text),
                    video_id=vid, media_id=mid, kind=kind,
                    domain="physical.spatial" if trans else "physical.dynamics",
                    t0=ev.t_start, t1=ev.t_end, value=val, epistemic="observation", modalities=["video"],
                    entities=ents,
                    provenance=_prov("hdepic.movement", tl, rid=tid, idx=i, leg=legacy_eid(vid, "movement", i)),
                    coverage=_cov(0, D, "tracked_object", "complete"))
        # assoc tracks + masks
        ap = root / "raw" / "assoc_info.json"; self._files.append(ap)
        assoc = json.loads(ap.read_text()); assoc = assoc[list(assoc)[0]]
        mp = root / "raw" / "mask_info.json"; self._files.append(mp)
        masks = json.loads(mp.read_text()); masks = masks[list(masks)[0]]
        mask_owner = {}
        for aid, o in assoc.items():
            name = (o.get("name") or "").strip()
            for k, tr in enumerate(o.get("tracks", [])):
                ts = tr.get("time_segment")
                if not (ts and len(ts) == 2):
                    continue
                for mk in tr.get("masks", []):
                    mask_owner[mk] = (aid, name, tr.get("track_id"))
                yield record(
                    evidence_id=evidence_id(DS, vid, "assoc", f"{aid}:{k}"),
                    video_id=vid, media_id=mid, kind="object_visible_track", domain="physical.objects_properties",
                    t0=ts[0], t1=ts[1],
                    value={"name": name, "association_id": aid, "track_id": tr.get("track_id"), "mask_ids": tr.get("masks", [])},
                    epistemic="observation", modalities=["video"],
                    entities=[{"entity_id": aid, "id_space": "hdepic_assoc", "name": name}],
                    provenance=_prov("hdepic.assoc", ap, rid=tr.get("track_id")),
                    coverage=_cov(0, D, "tracked_object", "complete"))
        for mk, mv in masks.items():
            t = mv["frame_number"] / fps
            own = mask_owner.get(mk)
            ents = [{"entity_id": own[0], "id_space": "hdepic_assoc", "name": own[1]}] if own else []
            ents.append({"entity_id": mk, "id_space": "hdepic_mask", "name": own[1] if own else None})
            yield record(
                evidence_id=evidence_id(DS, vid, "mask", mk),
                video_id=vid, media_id=mid, kind="object_mask_anchor", domain="physical.spatial", t0=t, t1=t,
                value={"name": own[1] if own else None, "frame_number": mv["frame_number"], "bbox_1408": mv.get("bbox"),
                       "xyz": mv.get("3d_location"), "fixture": mv.get("fixture"),
                       "fixture_kind": ix.fixture_kind(mv.get("fixture") or ""), "track_id": own[2] if own else None},
                epistemic="measurement", modalities=["video"], entities=ents,
                provenance=_prov("hdepic.mask", mp, rid=mk), coverage=_cov(0, D, "object_anchor", "partial"))
        # recipe timestamps
        rp = root / "raw" / "recipe_timestamps.json"
        if rp.exists():
            self._files.append(rp)
            for i, r in enumerate(json.loads(rp.read_text())):
                def _t(x, default):
                    try: return float(x)
                    except (TypeError, ValueError): return default
                t0, t1 = _t(r["start_time"], 0.0), _t(r["end_time"], D)
                yield record(
                    evidence_id=evidence_id(DS, vid, "recipe", t0=t0, t1=t1, label=r.get("high_level_activity_label", ""), text=r.get("recipe_id", "")),
                    video_id=vid, media_id=mid, kind="recipe_step", domain="task.structure", t0=t0, t1=t1,
                    value={"recipe_id": r.get("recipe_id") or None, "activity_label": r.get("high_level_activity_label")},
                    epistemic="observation", modalities=["video"],
                    provenance=_prov("hdepic.recipe", rp, idx=i), coverage=_cov(0, D, "activity_segment", "complete"))
        cp = root / "raw" / "complete_recipes.json"
        if cp.exists():
            self._files.append(cp)
            for rid, r in json.loads(cp.read_text()).items():
                yield record(
                    evidence_id=evidence_id(DS, vid, "recipe_text", rid),
                    video_id=vid, media_id=mid, kind="task_recipe", domain="human.goals_preferences", t0=0, t1=D,
                    value={"recipe_id": rid, "name": r.get("name"), "type": r.get("type"), "steps": r.get("steps")},
                    epistemic="stipulated_condition", modalities=[], solver_access="stipulated",
                    provenance=_prov("hdepic.complete_recipes", cp, rid=rid), coverage=_cov(0, D, "recipe", "complete"))
        # 派生:官方 recipe_timestamps 分段(人工)作 task_segment,段内 narration(人工)作 task_step(确定性 join,不含模型)
        rp2 = root / "raw" / "recipe_timestamps.json"
        if rp2.exists():
            segs = json.loads(rp2.read_text())
            recipes = json.loads(cp.read_text()) if cp.exists() else {}
            narr = sorted([e_ for e_ in ix.narrations], key=lambda e_: e_.t_start)
            for i, r in enumerate(segs):
                def _t(x, default):
                    try: return float(x)
                    except (TypeError, ValueError): return default
                t0, t1 = _t(r["start_time"], 0.0), _t(r["end_time"], D)
                inside = [e_ for e_ in narr if t0 <= e_.t_start < t1]
                if not (20 <= t1 - t0 <= 300 and 4 <= len(inside) <= 25):
                    continue
                rid_ = r.get("recipe_id") or ""
                rname = next((v2.get("name") for k2, v2 in recipes.items() if rid_ and k2.endswith(rid_)), None)
                tid = f"{vid[:3]}_r{i:02d}"
                goal = r.get("high_level_activity_label") or ""
                steps = [{"idx": k2 + 1, "text": e_.text, "t0": round(e_.t_start, 3), "t1": round(e_.t_end, 3)} for k2, e_ in enumerate(inside)]
                leg = [e_.eid for e_ in inside]
                cov = {"scope_start_sec": t0, "scope_end_sec": t1, "target_type": "task", "completeness": "complete"}
                prov = {**HUMAN, "source_type": "dataset_annotation_join", "source": "hdepic.recipe_tasks", "source_file": rel_source(rp2),
                        "source_record_id": tid, "source_index": i, "legacy_eid": None, "derived_from_legacy": leg,
                        "method": "recipe_timestamps segment (human) + narrations inside it (human)"}
                yield record(
                    evidence_id=evidence_id(DS, vid, "recipe_task", tid), video_id=vid, media_id=mid, kind="task_segment",
                    domain="task.structure", t0=t0, t1=t1, event_id=tid,
                    value={"task_id": tid, "goal": goal, "activity_label": goal, "recipe_id": rid_ or None, "recipe_name": rname,
                           "n_steps": len(steps), "steps": steps, "status": "verified"},
                    epistemic="observation", modalities=["video"],
                    entities=[{"entity_id": tid, "id_space": "task", "name": goal}], provenance=prov, coverage=cov,
                    flags=["STEPS_ARE_NARRATIONS", "COARSE_GOAL_LABEL"])
                for k2, e_ in enumerate(inside):
                    ex = e_.extra
                    yield record(
                        evidence_id=evidence_id(DS, vid, "recipe_task", f"{tid}/s{k2 + 1}"), video_id=vid, media_id=mid, kind="task_step",
                        domain="task.structure", t0=e_.t_start, t1=e_.t_end, event_id=tid,
                        value={"task_id": tid, "idx": k2 + 1, "text": e_.text, "verb": (ex.get("verbs") or [None])[0], "noun": (ex.get("nouns") or [None])[0],
                               "goal": goal, "status": "verified"},
                        epistemic="observation", modalities=["video"],
                        entities=[{"entity_id": tid, "id_space": "task", "name": goal}],
                        provenance={**prov, "source_record_id": f"{tid}/s{k2 + 1}", "derived_from_legacy": [e_.eid]}, coverage=cov,
                        flags=["STEPS_ARE_NARRATIONS"])
        gp = root / "raw" / "gaze_priming.json"
        if gp.exists():
            self._files.append(gp)
            g = json.loads(gp.read_text()); g = g[list(g)[0]]
            for k, v in g.items():
                s, e = v.get("start") or {}, v.get("end") or {}
                if "frame" not in s:
                    continue
                t0 = s["frame"] / fps; t1 = (e.get("frame", s["frame"])) / fps
                yield record(
                    evidence_id=evidence_id(DS, vid, "gaze_priming", k),
                    video_id=vid, media_id=mid, kind="gaze_fixation", domain="human.attention", t0=t0, t1=t1,
                    value={"start": s, "end": e}, epistemic="measurement", modalities=["gaze"],
                    provenance=_prov("hdepic.gaze_priming", gp, rid=k), coverage=_cov(0, D, "gaze_priming", "partial"))

    def files_read(self): return list(self._files)
