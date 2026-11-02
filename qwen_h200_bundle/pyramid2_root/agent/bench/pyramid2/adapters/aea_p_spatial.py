"""AEA(aea_p)空间 / 视线记录(10-27 用户定:fixture 3D 用 SAM3 + 官方 MPS;物体转移时间只取 legacy 声音事件;全部 needs_verification)。
输入 experiments/aea_protocol/sam3_fixtures/:review/<rec>/gates.json(实例 centre / sound_checks)、lifted/<rec>.json(instance -> obj_ids)、seg/<rec>/<prompt>.npz(逐帧 mask / bbox)、
frames/<rec>/frames.json(5 fps 帧 z 与 K)、gaze/<rec>.json(规范系视线 10 Hz)、confirmed_<rec>.json(用户确认的实例 -> 题面名;没有则 .provisional.json,仅供 mock)。
  object_visible_track        每个确认实例的可见段(SAM3 masklet 帧,间隔 >1 s 断开)                                   source aea_p.sam3_mps
  object_mask_anchor          每实例在样本窗内 ≤3 个 1 s 锚点(bbox_px 704 px 系,frame_size)                          source aea_p.sam3_mps
  object_location_transition  confirmed.transitions:t0 = t0_sound 首条 start,t1 = t1_sound 末条 stop;from/to = 最近 fixture  source aea_p.sound_transition(+ 同内容 object_move)
  spatial_relation            锚点 = 样本窗内 sound(anchor_kind sound)/ narration(anchor_kind movement)时刻;参照 = the camera wearer(位姿);候选 = 窗内可见的确认 fixture
                              nearest / farthest / nearest_final / order_by_distance(世界系距离)、side_left / side_right(规范系横向,pose_aea)  source aea_p.spatial_derived
  sound_source_direction      发声物匹配到确认实例的 sound:声音起点时该实例相对佩戴者的水平方位(可见时用 mask 质心方向,否则 3D 中心)  source aea_p.spatial_derived
  gaze_sample                 每个 sound / narration 锚点时刻的视线(规范系 yaw / pitch -> 六向)                            source aea_p.mps_gaze
基础 adapter(aea_p)须先入库:本 adapter 从 evidence.jsonl 读 aea_p 的 sound / narration 行。"""
import json, math, re, collections, hashlib
from pathlib import Path
import numpy as np
import p2config as P
from ids import evidence_id
from adapters.base import Adapter, record
from adapters.aea_protocol import DS, load_samples
from adapters.hdepic_e_spatial_derived import EGO_FRAME
from store import read_jsonl

SF = Path("/mnt/work_new/weihanxu/experiments/aea_protocol/sam3_fixtures")
SRC_FIX, SRC_TRANS, SRC_SP, SRC_GAZE = "aea_p.sam3_mps", "aea_p.sound_transition", "aea_p.spatial_derived", "aea_p.mps_gaze"
FPS = 5.0
WIN = 30.0
NEAR_MAX, MARG, MIN_CAND, GAP = 1.5, 0.4, 4, 0.4
EGO_MARG, EGO_MIN_R, EGO_MAX_R = 0.30, 0.2, 3.5
CAP = 60
SYN = {"refrigerator": ["refrigerator", "fridge"], "sink": ["sink", "tap", "faucet", "water"], "faucet": ["tap", "faucet", "sink"], "trash can": ["trash", "bin", "garbage"],
       "cabinet": ["cabinet", "cupboard"], "drawer": ["drawer"], "television": ["tv", "television"], "couch": ["sofa", "couch"], "coffee table": ["table"], "dining table": ["table"],
       "table": ["table"], "kitchen counter": ["counter", "island"], "paper towel": ["paper towel"], "soda can": ["can"], "plastic container": ["container", "packaging"], "shelf": ["shelf"], "stove": ["hob", "stove", "oven"]}
ALLO_WEARER = {"type": "allocentric", "reference_object": "the camera wearer", "viewpoint": None, "origin": "the camera wearer's position at the anchor moment (device position from the official MPS trajectory)",
               "projection": "3D Euclidean distance from the wearer's position to each fixture's 3D centre (official SLAM world frame, metres)", "orientation": "none: distances are viewpoint-independent",
               "comparison": "relative among the listed candidates only, not absolute", "handedness": None, "intrinsic_available": False,
               "question_must_state": "distance from the camera wearer at that moment (straight-line, independent of where the wearer faces), among the listed candidates"}


def confirmed(rec):
    for f in (SF / f"confirmed_{rec}.json", SF / f"confirmed_{rec}.provisional.json"):
        if f.exists(): return json.loads(f.read_text()), f
    return None, None


def _sample_windows():
    by = {}
    for s in load_samples(): by.setdefault(s["video_id"], []).append((s["sample_id"], float(s["t0"]), float(s["t1"])))
    return by


def sample_at(wins, vid, t):
    for sid, a, b in wins.get(vid, []):
        if a - 0.5 <= t <= b + 0.5: return sid
    return None


def _fid(*parts): return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def _head(n): t = (n or "").split(); return t[-1] if t else ""


def names_ok(names): h = [_head(n) for n in names]; return len(set(h)) == len(h) and all(h)


class AeaPSpatial(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        self.vids = sorted({s["video_id"] for s in load_samples() if (not videos or s["video_id"] in videos) and confirmed(s["video_id"])[0] and (SF / f"review/{s['video_id']}/gates.json").exists()})
        self._files = [P.DATA / "aea_p_samples.json", P.DATA / "evidence.jsonl"]
        self._ev = None

    def videos(self): return self.vids
    def media(self): return []

    def coverage(self, vid):
        cf, f = confirmed(vid)
        return [{"source": SRC_FIX, "n": len(cf["instances"]), "provenance": f"model (SAM3 masks + official MPS semidense; instance list {f.name})", "coverage": {"start_sec": None, "end_sec": None, "target_type": "fixture", "completeness": "partial"}},
                {"source": SRC_SP, "n": None, "provenance": "derived (wearer pose from official MPS + fixture 3D centres)", "coverage": {"start_sec": None, "end_sec": None, "target_type": "spatial_relation", "completeness": "partial"}},
                {"source": SRC_GAZE, "n": None, "provenance": "official MPS eye gaze (canonical RGB frame)", "coverage": {"start_sec": None, "end_sec": None, "target_type": "gaze", "completeness": "partial"}}]

    # ---------------------------------------------------------------- 输入
    def _evidence(self, vid):
        if self._ev is None:
            self._ev = collections.defaultdict(list)
            for r in read_jsonl(P.DATA / "evidence.jsonl"):
                if r["provenance"].get("dataset") == DS and r["kind"] in ("sound_event", "action_narration") and r.get("event_id"): self._ev[r["video_id"]].append(r)
        return self._ev[vid]

    def _load(self, vid):
        cf, cff = confirmed(vid); self._files += [cff, SF / f"review/{vid}/gates.json", SF / f"lifted/{vid}.json", SF / f"frames/{vid}/frames.json", SF / f"gaze/{vid}.json"]
        G = {g["instance"]: g for g in json.load(open(SF / f"review/{vid}/gates.json"))}
        L = {i["instance"]: i for i in json.load(open(SF / f"lifted/{vid}.json"))["instances"]}
        F = json.load(open(SF / f"frames/{vid}/frames.json")); z_of = [fr["z"] for fr in F["frames"]]; K = np.array(F["K"]); S = F["size"][0]
        inst = {}
        names = dict(cf["instances"]); names.update({iid: nm for nm, ids in (cf.get("movable") or {}).items() for iid in ids})   # movable 实例(can 的两个静止段)也载入
        for iid, name in names.items():
            g = G.get(iid) or {}; l = L.get(iid) or {}
            if not g or not l: continue
            prompt = l["prompt"]; D = np.load(SF / f"seg/{vid}/{prompt.replace(' ', '_')}.npz"); ms = int(D["mask_size"])
            rows = [i for i in range(len(D["frame"])) if int(D["obj_id"][i]) in set(l["obj_ids"])]
            frames = sorted({int(D["frame"][i]) for i in rows}); zs = [z_of[f] for f in frames]
            segs, cur = [], None                           # 可见段(间隔 > 1 s 断开)
            for z in zs:
                if cur and z - cur[1] <= 1.05: cur[1] = z
                else:
                    if cur: segs.append(tuple(cur))
                    cur = [z, z]
            if cur: segs.append(tuple(cur))
            per_frame = {}
            for i in rows:
                f = int(D["frame"][i]); m = np.unpackbits(D["mask"][i])[: ms * ms].reshape(ms, ms).astype(bool)
                if m.sum() == 0: continue
                ys, xs = np.nonzero(m); cen = (float(xs.mean() + 0.5) * S / ms, float(ys.mean() + 0.5) * S / ms)
                x, y, w, h = [float(v) for v in D["box"][i]]
                if f not in per_frame or m.mean() > per_frame[f]["area"]:
                    per_frame[f] = {"z": z_of[f], "area": float(m.mean()), "bbox": [x, y, x + w, y + h], "centroid": cen, "prob": float(D["prob"][i])}
            inst[iid] = {"name": name, "centre": g["centre"], "segs": segs, "frames": per_frame, "sound_source": bool(g.get("sound_source")), "sound_checks": g.get("sound_checks") or []}
        gz = json.load(open(SF / f"gaze/{vid}.json"))
        return cf, inst, {"K": K, "S": S}, gz

    # ---------------------------------------------------------------- 几何
    @staticmethod
    def _visible(inst, iid, t0, t1):
        return any(a <= t1 and b >= t0 for a, b in inst[iid]["segs"])

    @staticmethod
    def _frame_at(inst, iid, T, tol=0.3):
        fs = [v for v in inst[iid]["frames"].values() if abs(v["z"] - T) <= tol]
        return min(fs, key=lambda v: abs(v["z"] - T)) if fs else None

    def _bearing(self, PA, vid, inst, iid, T, cam_K):
        """实例相对佩戴者的水平方位(度,0 = 正前,+ = 左):可见时 = mask 质心的像平面方向(「在画面里的哪边」),否则 3D 中心对位姿。"""
        fr = self._frame_at(inst, iid, T)
        p = PA.at_loose(vid, T)
        if p is None: return None
        cam, R = p; fwd, lat, down, rng = PA.to_device(cam, R, inst[iid]["centre"])
        if fr is not None:
            K = cam_K["K"]; u = fr["centroid"][0]; ang = math.degrees(math.atan((K[0, 2] - u) / K[0, 0])); src = "mask_centroid"
        else:
            ang = math.degrees(math.atan2(lat, fwd)); src = "centre_3d"
        return ang, rng, src, (fwd, lat)

    # ---------------------------------------------------------------- 记录
    def records(self, vid):
        import pose_aea as PA
        cf, inst, cam_K, gz = self._load(vid); mid = f"{DS}/{vid}"; wins = _sample_windows()
        prov = lambda src, rid, method=None: {"source_type": "model_generated" if src == SRC_FIX else "derived", "dataset": DS, "source": src, "upstream_provenance": "model (SAM3 + MPS semidense)" if src == SRC_FIX else "derived",
                                              "source_file": f"experiments/aea_protocol/sam3_fixtures/review/{vid}/gates.json", "source_record_id": rid, "derived_from": [], **({"method": method} if method else {})}
        static = [i for i in inst if i not in {x for v in (cf.get("movable") or {}).values() for x in v}]   # 候选集 / 最近 fixture 只用静态实例
        # 1. 可见段 + mask 锚点
        for iid in inst:
            name = inst[iid]["name"]; ent = [{"entity_id": f"name:{name.replace(' ', '_')}", "id_space": "name_only", "name": name}]
            for k, (a, b) in enumerate(inst[iid]["segs"]):
                yield record(evidence_id=evidence_id(DS, vid, "track", f"{iid}:{k}"), video_id=vid, media_id=mid, kind="object_visible_track", domain="physical.objects_properties",
                             t0=a, t1=max(b, a + 0.2), event_id=sample_at(wins, vid, (a + b) / 2), value={"name": name, "association_id": iid, "track_id": f"{iid}:{k}", "mask_ids": [], "static": iid in static, "centre_xyz": inst[iid]["centre"]},
                             epistemic="observation", modalities=["video"], entities=ent, provenance=prov(SRC_FIX, f"{iid}:{k}"),
                             coverage={"scope_start_sec": None, "scope_end_sec": None, "target_type": "tracked_object", "completeness": "partial"}, flags=["MODEL_SEGMENTATION"])
            for sid, t0, t1 in wins.get(vid, []):
                cands = sorted((v for v in inst[iid]["frames"].values() if t0 <= v["z"] <= t1 - 1.0), key=lambda v: -v["area"]); picked = []
                for v in cands:
                    if any(abs(v["z"] - p["z"]) < 3 for p in picked): continue
                    picked.append(v)
                    if len(picked) == 3: break
                for v in picked:
                    yield record(evidence_id=evidence_id(DS, vid, "mask", f"{iid}:{v['z']:.1f}"), video_id=vid, media_id=mid, kind="object_mask_anchor", domain="physical.spatial", t0=v["z"], t1=v["z"], event_id=sid,
                                 value={"name": name, "frame_number": int(round(v["z"] * FPS)), "bbox_px": [round(x, 1) for x in v["bbox"]], "frame_size": cam_K["S"], "frame_geometry": "704 px linear pinhole render of the VRS RGB (NOT the SAVVY video geometry)",
                                        "xyz": inst[iid]["centre"], "fixture": None, "fixture_kind": None, "track_id": iid, "mask_area_frac": round(v["area"], 4)},
                                 epistemic="measurement", modalities=["video"], entities=ent, provenance=prov(SRC_FIX, f"{iid}:{v['z']:.1f}"),
                                 coverage={"scope_start_sec": None, "scope_end_sec": None, "target_type": "object_anchor", "completeness": "partial"}, flags=["MODEL_SEGMENTATION"])
        # 2. 转移(时间 = 声音事件)
        ev = self._evidence(vid); sounds = sorted((r for r in ev if r["kind"] == "sound_event"), key=lambda r: r["time"]["start_sec"]); narrs = sorted((r for r in ev if r["kind"] == "action_narration"), key=lambda r: r["time"]["start_sec"])
        moves = []
        for k, tr in enumerate(cf.get("transitions") or []):
            s0 = [s for s in sounds if s["value"]["label"].lower() == tr["t0_sound"].lower()]; s1 = [s for s in sounds if s["value"]["label"].lower() == tr["t1_sound"].lower()]
            a, b = inst.get(tr["from_instance"]), inst.get(tr["to_instance"])
            if not (s0 and s1 and a and b): continue
            t0, t1 = s0[0]["time"]["start_sec"], s1[-1]["time"]["end_sec"]
            near = lambda c: min(static, key=lambda i: np.linalg.norm(np.array(inst[i]["centre"]) - np.array(c)))
            byname = {inst[i]["name"]: i for i in static}
            fa = byname.get(tr.get("from_fixture")) or near(a["centre"]); fb = byname.get(tr.get("to_fixture")) or near(b["centre"]); name = tr["object"]   # confirmed 里写了 from/to 就用它,否则最近 fixture
            val = {"object_name": name, "association_id": tr["from_instance"], "track_id": f"transition:{k}", "from_fixture": inst[fa]["name"], "to_fixture": inst[fb]["name"], "from_fixture_kind": inst[fa]["name"], "to_fixture_kind": inst[fb]["name"],
                   "start_xyz": a["centre"], "end_xyz": b["centre"], "n_masks": None, "label": f"{name}: {inst[fa]['name']} -> {inst[fb]['name']}", "is_transition": fa != fb, "relation_type": "observed_transition" if fa != fb else "observed_motion",
                   "time_source": "legacy sound events (" + tr["t0_sound"] + " .. " + tr["t1_sound"] + ")", "position_source": "SAM3 + MPS centres of the two static instances", "t0_sound_eids": [s["evidence_id"] for s in s0], "t1_sound_eids": [s["evidence_id"] for s in s1]}
            ent = [{"entity_id": f"name:{name.replace(' ', '_')}", "id_space": "name_only", "name": name}]
            eid = evidence_id(DS, vid, "transition", str(k)); moves.append((t0, t1, eid))
            for kind in ("object_location_transition", "object_move"):
                yield record(evidence_id=eid if kind == "object_location_transition" else evidence_id(DS, vid, "move", str(k)), video_id=vid, media_id=mid, kind=kind, domain="physical.spatial", t0=t0, t1=t1, event_id=sample_at(wins, vid, t1),
                             value=val, epistemic="observation", modalities=["video", "audio"], entities=ent,
                             provenance={**prov(SRC_TRANS, str(k)), "derived_from": [s["evidence_id"] for s in s0 + s1]},
                             coverage={"scope_start_sec": None, "scope_end_sec": None, "target_type": "object_movement", "completeness": "partial"}, flags=["TIME_FROM_SOUND", "POSITION_FROM_MODEL"])
        # 3. spatial_relation(锚点 = 样本窗内的 sound / narration)
        anchors = [("sound", (s["time"]["start_sec"] + s["time"]["end_sec"]) / 2, s) for s in sounds if sample_at(wins, vid, s["time"]["start_sec"])] + \
                  [("movement", n["time"]["start_sec"], n) for n in narrs if sample_at(wins, vid, n["time"]["start_sec"])]
        facts = []
        for akind, T, arec in anchors:
            t0, t1 = round(max(0.0, T - WIN / 2), 3), round(max(0.0, T - WIN / 2) + WIN, 3)
            p = PA.at_loose(vid, T)
            if p is None: continue
            cam, R = p; vis = [i for i in static if self._visible(inst, i, t0, t1)]
            ranked = sorted(((float(np.linalg.norm(np.array(inst[i]["centre"]) - cam)), inst[i]["name"], i) for i in vis), key=lambda x: (x[0], x[1]))
            base = dict(akind=akind, T=T, t0=t0, t1=t1, aeid=arec["evidence_id"], slabel=arec["value"].get("label") if akind == "sound" else None, atext=arec["value"].get("text") if akind == "movement" else None)
            if len(ranked) >= MIN_CAND:
                d0, gold, gi = ranked[0]; far = [x for x in ranked[1:] if x[0] >= d0 + MARG]
                if d0 <= NEAR_MAX and len(far) >= 3 and names_ok([gold] + [x[1] for x in far[:3]]):
                    facts.append(dict(base, rel="nearest", ref="the camera wearer", gold=gold, d=d0, marg=MARG, wrong=[x[1] for x in far[:3]], cands=[gold] + [x[1] for x in far[:3]], ids=[gi] + [x[2] for x in far[:3]]))
                dF, goldF, giF = ranked[-1]
                if dF - ranked[-2][0] >= MARG and names_ok([goldF] + [x[1] for x in ranked[:3]]):
                    facts.append(dict(base, rel="farthest", ref="the camera wearer", gold=goldF, d=dF, marg=MARG, wrong=[x[1] for x in ranked[:3]], cands=[goldF] + [x[1] for x in ranked[:3]], ids=[giF] + [x[2] for x in ranked[:3]]))
                if ranked[1][0] - d0 >= MARG and names_ok([gold] + [x[1] for x in ranked[-3:]]):
                    facts.append(dict(base, rel="nearest_final", ref="the camera wearer", gold=gold, d=d0, marg=MARG, wrong=[x[1] for x in ranked[-3:]], cands=[gold] + [x[1] for x in ranked[-3:]], ids=[gi] + [x[2] for x in ranked[-3:]]))
            if len(ranked) >= 3:
                n = len(ranked); done = False
                for i in range(n - 2):
                    for j in range(i + 1, n - 1):
                        if ranked[j][0] - ranked[i][0] < GAP: continue
                        for k in range(j + 1, n):
                            if ranked[k][0] - ranked[j][0] < GAP: continue
                            tri = [ranked[i], ranked[j], ranked[k]]; names = [x[1] for x in tri]
                            if not names_ok(names): continue
                            perms = [" -> ".join(pp) for pp in ([names[0], names[2], names[1]], [names[2], names[1], names[0]], [names[2], names[0], names[1]])]
                            facts.append(dict(base, rel="order_by_distance", ref="the camera wearer", gold=" -> ".join(names), d=None, marg=GAP, wrong=perms, cands=names, ids=[x[2] for x in tri], dists=[round(x[0], 3) for x in tri])); done = True; break
                        if done: break
                    if done: break
            ps = PA.at(vid, T)                                   # side:要求位姿稳定
            if ps is not None:
                cam, R = ps; res = []
                for i in vis:
                    f_, l_, _, rng = PA.to_device(cam, R, inst[i]["centre"])
                    if EGO_MIN_R <= rng <= EGO_MAX_R: res.append((f_, l_, rng, inst[i]["name"], i))
                if len(res) >= MIN_CAND:
                    for mode in ("right", "left"):
                        key = (lambda x: x[1]) if mode == "right" else (lambda x: -x[1])
                        s_ = sorted(res, key=lambda x: (key(x), x[3]))
                        if key(s_[1]) - key(s_[0]) < EGO_MARG: continue
                        g = s_[0]; others = list(reversed(s_[-3:]))
                        if not names_ok([g[3]] + [x[3] for x in others]): continue
                        facts.append(dict(base, rel="side_" + mode, ref="the camera wearer", gold=g[3], d=None, marg=EGO_MARG, mode=mode, lat=g[1], wrong=[x[3] for x in others], cands=[g[3]] + [x[3] for x in others], ids=[g[4]] + [x[4] for x in others]))
        by = collections.defaultdict(list)
        for f in facts:
            f["fact_id"] = _fid(vid, f["rel"], f["akind"], f["gold"], ",".join(f["ids"]), f"{f['T']:.1f}"); by[(f["rel"], f["akind"])].append(f)
        DEFN = {"nearest": "Among the listed fixtures visible in the window, the one closest to the camera wearer at the anchor moment (3D distance from the wearer's position to the fixture).",
                "nearest_final": "Among the listed fixtures, the one closest to the camera wearer at the anchor moment.",
                "farthest": "Among the listed fixtures visible in the window, the one farthest from the camera wearer at the anchor moment.",
                "order_by_distance": "Ordering of the three fixtures by 3D distance from the camera wearer at the anchor moment, nearest first.",
                "side_right": "At the anchor moment, the fixture farthest to the CAMERA WEARER'S RIGHT in the wearer's own view (reference frame = the camera as it faces then).",
                "side_left": "At the anchor moment, the fixture farthest to the CAMERA WEARER'S LEFT in the wearer's own view (reference frame = the camera as it faces then)."}
        for key_, fs in by.items():
            fs.sort(key=lambda f: f["fact_id"])
            for f in fs[:CAP]:
                rel = f["rel"]; ego = rel.startswith("side_")
                val = {"relation": rel, "relation_definition": DEFN[rel], "anchor_kind": f["akind"], "anchor_time_sec": round(f["T"], 3), "window": [f["t0"], f["t1"]],
                       "reference_object": f["ref"], "answer_object": f["gold"], "verified_wrong_answers": f["wrong"], "absent_in_window": [],
                       "d_gold_m": round(f["d"], 3) if f.get("d") is not None else None, "margin_m": f["marg"], "lateral_gold_m": round(f["lat"], 3) if f.get("lat") is not None else None,
                       "side_mode": f.get("mode"), "anchor_sound_label": f.get("slabel"), "anchor_object": None, "anchor_narration": f.get("atext"), "dists_m": f.get("dists"),
                       "frame": "camera (canonical RGB frame at anchor time: left/right of the wearer)" if ego else "world (official MPS SLAM frame, metres)",
                       "query_frame": {"type": "camera_at_time" if ego else "world", "reference_timestamp": round(f["T"], 3)},
                       "frame_of_reference": EGO_FRAME(f["mode"]) if ego else ALLO_WEARER,
                       "candidate_set": {"names": f["cands"], "completeness": "user-confirmed static fixtures (SAM3 + MPS 3D centres) visible in the window; distractors are geometry-verified"},
                       "original_subtype": ("low" if f["akind"] == "sound" else "easy") + ("_spatial_side" if ego else "_spatial_near" if rel == "nearest" else "_spatial_extreme" if rel in ("farthest", "nearest_final") else "_spatial_order"), "fact_id": f["fact_id"]}
                yield record(evidence_id=evidence_id(DS, vid, "spatial", f["fact_id"]), video_id=vid, media_id=mid, kind="spatial_relation", domain="physical.spatial",
                             t0=f["T"], t1=f["T"], event_id=sample_at(wins, vid, f["T"]), value=val, epistemic="measurement", modalities=["video"] + (["audio"] if f["akind"] == "sound" else []),
                             entities=[{"entity_id": "name:" + f["gold"].replace(" ", "_"), "id_space": "name_only", "name": f["gold"]}],
                             provenance={**prov(SRC_SP, f["fact_id"], "adapters/aea_p_spatial.py: wearer position / heading from pose_aea (official MPS), fixture centres from SAM3 + semidense"), "derived_from": [f["aeid"]] + [evidence_id(DS, vid, "track", f"{i}:0") for i in f["ids"]]},
                             coverage={"scope_start_sec": f["t0"], "scope_end_sec": f["t1"], "target_type": "spatial_relation", "completeness": "partial"},
                             flags=["DERIVED", "POSITION_FROM_MODEL"] + (["EGO_POSE"] if ego else []))
        # 4. sound_source_direction
        for s in sounds:
            if not sample_at(wins, vid, s["time"]["start_sec"]): continue
            obj = ((s["value"].get("object") or "") + " " + (s["value"].get("label") or "")).lower()
            hits = [i for i in static if any(re.search(rf"\b{re.escape(k)}\b", obj) for k in SYN.get(inst[i]["name"], [inst[i]["name"]]))]
            hits = [i for i in hits if inst[i]["sound_source"]] or hits
            if len(hits) != 1: continue
            iid = hits[0]; T = s["time"]["start_sec"]; b = self._bearing(PA, vid, inst, iid, T, cam_K)
            if b is None: continue
            ang, rng, src, _ = b; a = abs(ang)
            sector = "front" if a <= 45 else "back" if a >= 135 else ("left" if ang > 0 else "right"); margin = min(abs(a - 45), abs(a - 135))
            bucket = "within 1 m" if rng < 1.0 else "1-2 m" if rng < 2.0 else "more than 2 m"
            yield record(evidence_id=evidence_id(DS, vid, "sound_source", s["evidence_id"].split(":")[-1]), video_id=vid, media_id=mid, kind="sound_source_direction", domain="physical.spatial", t0=T, t1=s["time"]["end_sec"], event_id=sample_at(wins, vid, T),
                         value={"sound_label": s["value"].get("label"), "sound_eid": s["evidence_id"], "source_instance": iid, "source_name": inst[iid]["name"], "bearing_deg": round(ang, 1), "sector": sector, "margin_deg": round(margin, 1),
                                "range_m": round(rng, 2), "range_bucket": bucket, "bearing_source": src, "frame": "canonical RGB camera frame at the sound onset (0 = straight ahead, + = wearer's left)",
                                "sector_rule": "front: |bearing| <= 45; back: >= 135; else left / right"},
                         epistemic="measurement", modalities=["audio", "video"], entities=[{"entity_id": "name:" + inst[iid]["name"].replace(" ", "_"), "id_space": "name_only", "name": inst[iid]["name"]}],
                         provenance={**prov(SRC_SP, s["evidence_id"], "adapters/aea_p_spatial.py: bearing of the sounding fixture from the wearer at sound onset (mask centroid when visible, else 3D centre vs pose_aea)"), "derived_from": [s["evidence_id"]]},
                         coverage={"scope_start_sec": None, "scope_end_sec": None, "target_type": "sound_source", "completeness": "partial"}, flags=["DERIVED", "POSITION_FROM_MODEL"])
        # 5. gaze_sample
        gt = np.asarray(gz["t"]); gy = np.asarray(gz["yaw_deg"]); gp = np.asarray(gz["pitch_deg"])
        for akind, T, arec in anchors:
            i = int(np.argmin(np.abs(gt - T)))
            if abs(gt[i] - T) > 0.15: continue
            yaw, pitch = float(gy[i]), float(gp[i])
            h = "front" if abs(yaw) <= 15 else ("left" if yaw > 0 else "right"); v = "up" if pitch > 0 else "down"
            margin = min(abs(abs(yaw) - 15), abs(pitch))
            yield record(evidence_id=evidence_id(DS, vid, "gaze", arec["evidence_id"].split(":")[-1] + ":" + akind), video_id=vid, media_id=mid, kind="gaze_sample", domain="human.attention", t0=T, t1=T, event_id=sample_at(wins, vid, T),
                         value={"yaw_deg": round(yaw, 1), "pitch_deg": round(pitch, 1), "sector": f"{h}-{v}", "horizontal": h, "vertical": v, "margin_deg": round(margin, 1), "anchor_kind": akind, "anchor_eid": arec["evidence_id"],
                                "anchor_label": arec["value"].get("label") or arec["value"].get("text"), "frame": "canonical RGB camera frame (relative to where the camera faces); yaw + = left, pitch + = up",
                                "sector_rule": "front: |yaw| <= 15; up/down by the sign of pitch"},
                         epistemic="measurement", modalities=["gaze"], entities=[],
                         provenance={"source_type": "dataset_annotation", "dataset": DS, "source": SRC_GAZE, "upstream_provenance": "official MPS eye gaze (model estimate)", "source_file": f"AEA/{vid}/mps/eye_gaze/general_eye_gaze.csv", "source_record_id": f"{T:.2f}", "derived_from": [arec["evidence_id"]]},
                         coverage={"scope_start_sec": None, "scope_end_sec": None, "target_type": "gaze", "completeness": "partial"}, flags=["MPS_ESTIMATE"])

    def items(self): return iter(())
    def files_read(self): return [f for f in self._files if f]
