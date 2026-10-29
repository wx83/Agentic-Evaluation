"""HD-EPIC 官方标注 -> hdepic_e 的空间 / 轨迹 / gaze / 活动段记录(10-27,用户定「可标但没入库的全部入库」)。只导入 Method E 样本涉及的视频。
  object_location_transition   assoc track(拿起 … 放下):第一个 mask = 拿起处、最后一个 = 放下处,fixture 不同    source hdepic_e.object_movement
  object_move                  同上,fixture 相同
  object_visible_track         assoc track 的可见时段                                                             source hdepic_e.assoc
  object_mask_anchor           每个 mask:帧号 / bbox / 3D 位置 / fixture                                           source hdepic_e.mask
  gaze_fixation                eye-gaze-priming/priming_info.json:拿起 / 放下前的注视 3D 点                        source hdepic_e.gaze_priming
  recipe_step                  high-level/activities/<P>_recipe_timestamps.csv:活动段(recipe_id + 活动名)        source hdepic_e.activity
时间 = 官方 time_segment / frame_number ÷ 30 fps;坐标 = 官方数字孪生世界系(米)。policy hdepic_e.* -> verified/dataset_gt。"""
import json, csv, collections
from pathlib import Path
import p2config as P
from ids import evidence_id
from adapters.base import Adapter, record
from adapters.hdepic_methode import load_samples, DS, HD

ASSOC = HD / "annotations/data/scene-and-object-movements/assoc_info.json"
MASKS = HD / "annotations/data/scene-and-object-movements/mask_info.json"
PRIMING = HD / "annotations/data/eye-gaze-priming/priming_info.json"
ACTIV = HD / "annotations/data/high-level/activities"
FPS = 30.0
SRC = "hdepic_e.object_movement"


def _sample_windows():
    """{video_id: [(sample_id, t0, t1)]}(Method E 样本 = 官方 recipe step 的时间窗)。"""
    by = {}
    for s in load_samples():
        by.setdefault(s["video_id"], []).append((s["sample_id"], float(s["t0"]), float(s["t1"])))
    return by


def sample_at(wins, vid, t):
    for sid, a, b in wins.get(vid, []):
        if a - 0.5 <= t <= b + 0.5: return sid
    return None


def _fixture_kind(f):
    return (f or "").split("_", 1)[-1].split(".")[0] if f else None


def _durations(part):
    """video/<P>/durations.txt -> {video_id: sec}(格式宽松解析:行里有视频 id 和一个数)。"""
    f = HD / "video" / part / "durations.txt"
    out = {}
    if not f.exists(): return out
    import re
    for line in f.read_text().splitlines():
        m = re.search(r"(P\d\d-\d{8}-\d{6})", line); n = re.findall(r"(\d+(?:\.\d+)?)\s*$", line)
        if m and n:
            try: out[m.group(1)] = float(n[-1])
            except ValueError: pass
    return out


def movements(assoc, masks, vid):
    """[{oid, track_id, name, t0, t1, start_xyz, end_xyz, from_fixture, to_fixture, trans, eid}]"""
    out = []
    if vid in masks and isinstance(masks.get(vid), dict) and "frame_number" not in masks[vid]:   # 传的是整份 mask_info(按视频键)
        masks = masks[vid]
    for oid, o in (assoc.get(vid) or {}).items():
        name = (o.get("name") or "").strip()
        for tr in o.get("tracks") or []:
            t0, t1 = tr["time_segment"]
            ms = sorted([masks[k] for k in tr.get("masks") or [] if k in masks], key=lambda x: x.get("frame_number") or 0)
            if not ms: continue
            a, b = ms[0], ms[-1]
            trans = bool(a.get("fixture") and b.get("fixture") and a["fixture"] != b["fixture"])
            out.append({"oid": oid, "track_id": tr.get("track_id"), "name": name, "t0": float(t0), "t1": float(t1), "n_masks": len(ms),
                        "start_xyz": a.get("3d_location"), "end_xyz": b.get("3d_location"), "from_fixture": a.get("fixture"), "to_fixture": b.get("fixture"),
                        "trans": trans, "eid": evidence_id(DS, vid, "movement", f"{oid}:{tr.get('track_id')}")})
    return out


class HdEpicESpatial(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        vids = sorted({s["video_id"] for s in load_samples()})
        self.vids = [v for v in vids if not videos or v in videos]
        self._assoc = self._masks = self._prime = None
        self._files = [ASSOC, MASKS, PRIMING]

    def _load(self):
        if self._assoc is None:
            self._assoc = json.load(open(ASSOC)); self._masks = json.load(open(MASKS))
            self._prime = json.load(open(PRIMING)) if PRIMING.exists() else {}

    def videos(self):
        self._load()
        return [v for v in self.vids if v in self._assoc]

    def media(self): return []          # media 行由 HdEpicE 提供

    def coverage(self, vid):
        self._load()
        n = sum(len(o["tracks"]) for o in self._assoc.get(vid, {}).values())
        return [{"source": SRC, "n": n, "provenance": "human (official 3D object movement annotation)", "coverage": {"start_sec": None, "end_sec": None, "target_type": "object_movement", "completeness": "complete"}},
                {"source": "hdepic_e.assoc", "n": n, "provenance": "human", "coverage": {"start_sec": None, "end_sec": None, "target_type": "tracked_object", "completeness": "complete"}},
                {"source": "hdepic_e.mask", "n": len(self._masks.get(vid, {})), "provenance": "human", "coverage": {"start_sec": None, "end_sec": None, "target_type": "object_anchor", "completeness": "partial"}},
                {"source": "hdepic_e.gaze_priming", "n": len(self._prime.get(vid, {})), "provenance": "human + MPS gaze", "coverage": {"start_sec": None, "end_sec": None, "target_type": "gaze_priming", "completeness": "partial"}},
                {"source": "hdepic_e.activity", "n": None, "provenance": "human", "coverage": {"start_sec": None, "end_sec": None, "target_type": "activity_segment", "completeness": "complete"}}]

    def records(self, vid):
        self._load()
        mid = f"{DS}/{vid}"; masks = self._masks.get(vid, {}); part = vid.split("-")[0]
        prov = lambda src, rid, file: {"source_type": "dataset_annotation", "dataset": DS, "source": src, "upstream_provenance": "human", "source_file": file, "source_record_id": rid, "derived_from": []}
        mask_owner = {}; wins = _sample_windows()
        # 1. 搬运 + 可见轨迹
        for oid, o in (self._assoc.get(vid) or {}).items():
            name = (o.get("name") or "").strip()
            ent = [{"entity_id": f"name:{name}", "id_space": "name_only", "name": name}, {"entity_id": oid, "id_space": "hdepic_assoc", "name": name}]
            for k, tr in enumerate(o.get("tracks") or []):
                t0, t1 = tr["time_segment"]
                for mk in tr.get("masks") or []: mask_owner[mk] = (oid, name, tr.get("track_id"))
                yield record(evidence_id=evidence_id(DS, vid, "assoc", f"{oid}:{k}"), video_id=vid, media_id=mid, kind="object_visible_track", domain="physical.objects_properties",
                             t0=t0, t1=t1, event_id=sample_at(wins, vid, (float(t0) + float(t1)) / 2), value={"name": name, "association_id": oid, "track_id": tr.get("track_id"), "mask_ids": tr.get("masks") or []},
                             epistemic="observation", modalities=["video"], entities=ent, provenance=prov("hdepic_e.assoc", tr.get("track_id"), "hd-epic/annotations/data/scene-and-object-movements/assoc_info.json"),
                             coverage={"scope_start_sec": None, "scope_end_sec": None, "target_type": "tracked_object", "completeness": "complete"})
        for mv in movements(self._assoc, self._masks, vid):
            val = {"object_name": mv["name"], "association_id": mv["oid"], "track_id": mv["track_id"], "from_fixture": mv["from_fixture"], "to_fixture": mv["to_fixture"],
                   "from_fixture_kind": _fixture_kind(mv["from_fixture"]), "to_fixture_kind": _fixture_kind(mv["to_fixture"]), "start_xyz": mv["start_xyz"], "end_xyz": mv["end_xyz"],
                   "n_masks": mv["n_masks"], "label": f"{mv['name']}: {mv['from_fixture']} -> {mv['to_fixture']}", "is_transition": mv["trans"],
                   "relation_type": "observed_transition" if mv["trans"] else "observed_motion"}
            yield record(evidence_id=mv["eid"], video_id=vid, media_id=mid, kind="object_location_transition" if mv["trans"] else "object_move", domain="physical.spatial",
                         t0=mv["t0"], t1=mv["t1"], event_id=sample_at(wins, vid, mv["t1"]), value=val, epistemic="observation", modalities=["video"],
                         entities=[{"entity_id": f"name:{mv['name']}", "id_space": "name_only", "name": mv["name"]}, {"entity_id": mv["oid"], "id_space": "hdepic_assoc", "name": mv["name"]}],
                         provenance=prov(SRC, f"{mv['oid']}:{mv['track_id']}", "hd-epic/annotations/data/scene-and-object-movements/assoc_info.json"),
                         coverage={"scope_start_sec": None, "scope_end_sec": None, "target_type": "object_movement", "completeness": "complete"})
        # 2. mask 锚点(帧 / bbox / 3D / fixture)
        for mk, mv in masks.items():
            t = (mv.get("frame_number") or 0) / FPS; own = mask_owner.get(mk)
            ents = ([{"entity_id": own[0], "id_space": "hdepic_assoc", "name": own[1]}, {"entity_id": f"name:{own[1]}", "id_space": "name_only", "name": own[1]}] if own else []) + [{"entity_id": mk, "id_space": "hdepic_mask", "name": own[1] if own else None}]
            yield record(evidence_id=evidence_id(DS, vid, "mask", mk), video_id=vid, media_id=mid, kind="object_mask_anchor", domain="physical.spatial", t0=t, t1=t, event_id=sample_at(wins, vid, t),
                         value={"name": own[1] if own else None, "frame_number": mv.get("frame_number"), "bbox_1408": mv.get("bbox"), "xyz": mv.get("3d_location"),
                                "fixture": mv.get("fixture"), "fixture_kind": _fixture_kind(mv.get("fixture")), "track_id": own[2] if own else None},
                         epistemic="measurement", modalities=["video"], entities=ents, provenance=prov("hdepic_e.mask", mk, "hd-epic/annotations/data/scene-and-object-movements/mask_info.json"),
                         coverage={"scope_start_sec": None, "scope_end_sec": None, "target_type": "object_anchor", "completeness": "partial"})
        # 3. gaze priming(官方 eye-gaze-priming)
        for k, v in (self._prime.get(vid) or {}).items():
            s, e = v.get("start") or {}, v.get("end") or {}
            if not isinstance(s, dict) or "frame" not in s: continue
            t0 = s["frame"] / FPS; t1 = (e.get("frame", s["frame"]) if isinstance(e, dict) else s["frame"]) / FPS
            yield record(evidence_id=evidence_id(DS, vid, "gaze_priming", k), video_id=vid, media_id=mid, kind="gaze_fixation", domain="human.attention", t0=t0, t1=max(t0, t1), event_id=sample_at(wins, vid, t1),
                         value={"start": s, "end": e if isinstance(e, dict) else {}}, epistemic="measurement", modalities=["gaze"],
                         provenance=prov("hdepic_e.gaze_priming", k, "hd-epic/annotations/data/eye-gaze-priming/priming_info.json"),
                         coverage={"scope_start_sec": None, "scope_end_sec": None, "target_type": "gaze_priming", "completeness": "partial"})
        # 4. 活动段(官方 recipe_timestamps)
        f = ACTIV / f"{part}_recipe_timestamps.csv"
        if f.exists():
            if f not in self._files: self._files.append(f)
            D = _durations(part).get(vid)
            with open(f) as fh:
                for i, r in enumerate(csv.DictReader(fh)):
                    if r.get("video_id") != vid: continue
                    def _t(x, default):
                        try: return float(x)
                        except (TypeError, ValueError): return default
                    t0 = _t(r.get("start_time"), 0.0); t1 = _t(r.get("end_time"), D if D else t0 + 1.0)
                    if t1 < t0 + 0.5: t1 = t0 + 0.5            # 官方表偶有 end < start / end 缺失:最短 0.5 s,记 flag
                    yield record(evidence_id=evidence_id(DS, vid, "activity", t0=t0, t1=t1, label=r.get("high_level_activity_label") or "", text=r.get("recipe_id") or ""),
                                 video_id=vid, media_id=mid, kind="recipe_step", domain="task.structure", t0=t0, t1=t1, event_id=sample_at(wins, vid, (t0 + t1) / 2),
                                 value={"recipe_id": r.get("recipe_id") or None, "activity_label": r.get("high_level_activity_label"), "end_is_video_end": (r.get("end_time") or "").strip() == "end",
                                        "raw_start": r.get("start_time"), "raw_end": r.get("end_time")},
                                 epistemic="observation", modalities=["video"], provenance=prov("hdepic_e.activity", str(i), f"hd-epic/annotations/data/high-level/activities/{part}_recipe_timestamps.csv"),
                                 coverage={"scope_start_sec": None, "scope_end_sec": None, "target_type": "activity_segment", "completeness": "complete"})

    def files_read(self): return list(self._files)
