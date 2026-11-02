"""派生空间关系(hdepic_e,10-27):复刻 agent/bench/pyramid/spatial.py 的几何规则,输入 = 官方 assoc/mask 搬运(3D 落点)+ 官方声音 + SLAM 位姿(pose_hdepic)。
输出 spatial_relation 记录(字段与旧 hdepic.spatial_derived / geo3d 记录一致,retrieve.SKILL_NEEDS 的 spatial_* 规格直接可用):
  nearest        anchor_kind movement:某物放下那一刻,窗口内可见物体里离它最近的(d ≤ 0.8 m,余量 0.4 m,≥3 个远的干扰项)         -> spatial_near
  nearest        anchor_kind sound:一声响时恰有一个物体在被搬动,离它最近的(d ≤ 1.0 m,余量 0.35 m,≥2 个远的)                 -> sound_anchored_spatial_near
  farthest / nearest_final   30 s 窗口结束时,离参照物最远 / 最近的(余量 0.4 m,≥4 候选)                                      -> inter_event_spatial_extreme
  order_by_distance          三个物体按到参照物的距离由近到远(相邻间隔 ≥ 0.4 m)                                               -> inter_event_spatial_order
  side_left / side_right     anchor movement / sound:那一刻在「我」最左 / 最右的物体(device frame,横向余量 0.30 m,距离 0.2–2.5 m,相机稳定) -> spatial_side / sound_anchored_spatial_side
静止位置 = 可证明的静止(某次搬运在 T 前结束且其后没再搬;或在 T 后开始且之前没搬完)。物体名剥尾数字;固定设施 / 流水线残名 / unknown 不作物体。
epistemic measurement;source hdepic_e.spatial_derived;flags DERIVED(side 另加 EGO_POSE)。"""
import json, math, hashlib, collections, re
from pathlib import Path
import p2config as P
from ids import evidence_id
from adapters.base import Adapter, record
from adapters.hdepic_methode import load_samples, DS
from adapters.hdepic_e_spatial import ASSOC, MASKS, movements, _sample_windows, sample_at
from store import read_jsonl

SRC = "hdepic_e.spatial_derived"
WIN, STRIDE = 30.0, 15.0
NEAR_L1, MARG = 0.8, 0.4
NEAR_L2, MARG_L2 = 1.0, 0.35
MARG_L3, GAP_L4 = 0.4, 0.4
MIN_CAND = 4
EGO_MARG, EGO_MIN_R, EGO_MAX_R = 0.30, 0.2, 2.5
CAP = 160                      # 每种关系每视频最多条数(按 fact_id 排序取,确定性)
FIXTURE_NOUNS = {"counter", "kitchen top", "countertop", "tabletop", "sink", "hob", "cupboard", "drawer", "tap", "worktop", "shelf", "floor", "oven",
                 "fridge", "refrigerator", "dishwasher", "bin", "microwave", "cabinet", "wall", "door", "window", "stove", "table"}
ARTIFACT = re.compile(r"^track\s*\d+|skipped", re.I)
BACKGROUND = {"background", "silence", "none", "noise"}


def _norm(s): return re.sub(r"\s+", " ", re.sub(r"\d+$", "", (s or "").strip().lower())).strip()


def _head(s):
    t = _norm(s).split(); return t[-1] if t else ""


def _clean(name):
    if not name or ARTIFACT.search(name) or "unknown" in name.lower(): return None
    n = _norm(name)
    if not n or any(re.search(rf"\b{re.escape(w)}\b", n) for w in FIXTURE_NOUNS): return None
    return n


def _xyz(v): return v if (isinstance(v, (list, tuple)) and len(v) == 3) else None


def _dist(a, b): return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(3)))


def _fid(video, subtype, gold, eids, t0):
    return hashlib.sha256(f"{video}|{subtype}|{gold}|{','.join(eids)}|{t0:.1f}".encode()).hexdigest()[:16]


class Geo:
    """一个视频的几何基元(搬运 / 可见 / 静止位置)。"""
    def __init__(self, vid, moves, tracks):
        self.vid = vid
        self.by = collections.defaultdict(list)
        for m in moves:
            if _xyz(m["start_xyz"]) is None or _xyz(m["end_xyz"]) is None: continue
            n = _clean(m["name"])
            if not n: continue
            self.by[n].append(m)
        for n in self.by: self.by[n].sort(key=lambda m: (m["t0"], m["eid"]))
        self.tracks = tracks              # [(name_norm, t0, t1)]
        self.moves = sorted(moves, key=lambda m: m["t0"])
        self.D = max([m["t1"] for m in moves] + [t1 for _, _, t1 in tracks] + [1.0])

    def visible(self, t0, t1):
        return {n for n, a, b in self.tracks if a <= t1 and b >= t0}

    def rest_at(self, name, T, t0, t1):
        ms = self.by.get(name)
        if not ms: return None
        best = None
        for m in ms:
            te, ts = m["t1"], m["t0"]
            if te <= T and t0 <= te <= t1 and not any(x["t0"] > te and x["t0"] < T for x in ms):
                c = (T - te, m["eid"], m["end_xyz"], te)
                if best is None or c[:2] < best[:2]: best = c
            if ts >= T and t0 <= ts <= t1 and not any(x["t1"] < ts and x["t1"] > T for x in ms):
                c = (ts - T, m["eid"], m["start_xyz"], ts)
                if best is None or c[:2] < best[:2]: best = c
        return (best[2], best[1], best[3]) if best else None

    def rank_others(self, ref, p, T, t0, t1):
        vis = self.visible(t0, t1); rh = _head(ref); out = []
        for n in self.by:
            if n == ref or n not in vis or _head(n) == rh: continue
            r = self.rest_at(n, T, t0, t1)
            if r is None: continue
            out.append((_dist(p, r[0]), n, r[1]))
        out.sort(key=lambda x: (x[0], x[1])); return out

    def win_around(self, t):
        t0 = min(max(0.0, t - WIN / 2), max(0.0, self.D - WIN)); return round(t0, 3), round(t0 + WIN, 3)

    def stride_wins(self):
        t = 0.0
        while t + WIN <= self.D:
            yield round(t, 3), round(t + WIN, 3); t += STRIDE


def names_ok(names):
    heads = [_head(n) for n in names]; return len(set(heads)) == len(heads) and all(heads)


def disjoint(ref, gold): return gold not in ref and ref not in gold


def _interp(m, T):
    a, b = m["start_xyz"], m["end_xyz"]; span = m["t1"] - m["t0"]
    f = 0.0 if span <= 0 else max(0.0, min(1.0, (T - m["t0"]) / span))
    return [a[i] + f * (b[i] - a[i]) for i in range(3)]


ALLO_FRAME = lambda ref: {"type": "allocentric", "reference_object": ref, "viewpoint": None, "origin": f"the resting position of the reference object ({ref})",
                          "projection": "3D Euclidean distance between resting positions (HD-EPIC digital-twin world frame, metres)", "orientation": "none: 3D distances in the scene are viewpoint-independent",
                          "comparison": "relative among the listed candidates only, not absolute", "handedness": None, "intrinsic_available": False,
                          "question_must_state": f"relative to the {ref} (scene distance, independent of where the wearer stands), among the listed candidates"}
EGO_FRAME = lambda side: {"type": "egocentric", "reference_object": "the camera wearer", "viewpoint": "the camera wearer at reference_timestamp", "origin": "device (camera) centre at reference_timestamp",
                          "projection": "device lateral axis (+Y = the wearer's left, -Y = right), objects' resting positions", "orientation": "the way the device faces at reference_timestamp; not assumed to equal body facing",
                          "comparison": "relative position among the listed candidates only, not absolute", "handedness": "the wearer's own left / right as the camera faces", "intrinsic_available": False,
                          "direction_rule": f"extreme: farthest to the wearer's {side} among the candidates", "question_must_state": "from the camera wearer's own viewpoint at that moment (egocentric: the wearer's left/right as the camera faces), relative to the wearer, among the listed candidates"}


class HdEpicESpatialDerived(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        vids = sorted({s["video_id"] for s in load_samples()})
        self.vids = [v for v in vids if not videos or v in videos]
        self._assoc = self._masks = None
        self._sounds = None
        self._files = [ASSOC, MASKS, P.DATA / "evidence.jsonl"]

    def _load(self):
        if self._assoc is None:
            self._assoc = json.load(open(ASSOC)); self._masks = json.load(open(MASKS))
            self._sounds = collections.defaultdict(list)
            for r in read_jsonl(P.DATA / "evidence.jsonl"):
                if r["kind"] == "sound_event" and r["provenance"].get("dataset") == DS and "BACKGROUND_CLASS" not in r.get("quality_flags", []):
                    self._sounds[r["video_id"]].append(r)

    def videos(self):
        self._load(); return [v for v in self.vids if v in self._assoc]

    def media(self): return []

    def coverage(self, vid):
        return [{"source": SRC, "n": None, "provenance": "derived (3D geometry on official object positions; SLAM pose for side relations)",
                 "coverage": {"start_sec": None, "end_sec": None, "target_type": "spatial_relation", "completeness": "partial"}}]

    def _geo(self, vid):
        moves = movements(self._assoc, self._masks, vid)
        tracks = []
        for oid, o in (self._assoc.get(vid) or {}).items():
            n = _clean(o.get("name"))
            if not n: continue
            for tr in o.get("tracks") or []: tracks.append((n, float(tr["time_segment"][0]), float(tr["time_segment"][1])))
        return Geo(vid, moves, tracks)

    # ---- 各关系
    def _facts(self, vid):
        g = self._geo(vid); out = []
        # L1 nearest @ movement end
        for m in g.moves:
            ref = _clean(m["name"]); p = _xyz(m["end_xyz"])
            if not ref or p is None: continue
            T = m["t1"]; t0, t1 = g.win_around((m["t0"] + m["t1"]) / 2)
            if not (t0 <= T <= t1): continue
            ranked = g.rank_others(ref, p, T, t0, t1)
            if len(ranked) < MIN_CAND: continue
            d0, gold, geid = ranked[0]
            if d0 > NEAR_L1: continue
            far = [r for r in ranked[1:] if r[0] >= d0 + MARG]
            if len(far) < 3 or not names_ok([gold] + [x[1] for x in far[:3]]) or not disjoint(ref, gold): continue
            out.append(dict(subtype="easy_spatial_near", rel="nearest", akind="movement", T=T, t0=t0, t1=t1, ref=ref, gold=gold, d=d0, marg=MARG,
                            wrong=[x[1] for x in far[:3]], eids=[m["eid"], geid] + [x[2] for x in far[:3]], cands=[gold] + [x[1] for x in far[:3]], anchor_eid=m["eid"]))
        # L2 nearest @ sound (exactly one movement within ±1.5 s)
        for s in self._sounds.get(vid, []):
            st, se = s["time"]["start_sec"], s["time"]["end_sec"]; mid = (st + se) / 2
            near = [m for m in g.moves if m["t0"] <= se + 1.5 and m["t1"] >= st - 1.5]
            if len(near) != 1: continue
            m = near[0]; ref = _clean(m["name"])
            if not ref or _xyz(m["start_xyz"]) is None or _xyz(m["end_xyz"]) is None: continue
            t0, t1 = g.win_around(mid)
            if not (t0 <= st and se <= t1): continue
            p = _interp(m, mid); ranked = g.rank_others(ref, p, mid, t0, t1)
            if len(ranked) < 2: continue
            d0, gold, geid = ranked[0]
            if d0 > NEAR_L2: continue
            far = [x for x in ranked[1:] if x[0] >= d0 + MARG_L2]
            if len(far) < 2 or not names_ok([gold] + [x[1] for x in far[:3]]) or not disjoint(ref, gold): continue
            out.append(dict(subtype="low_spatial_near", rel="nearest", akind="sound", T=mid, t0=t0, t1=t1, ref=ref, gold=gold, d=d0, marg=MARG_L2, slabel=s["value"].get("label"),
                            wrong=[x[1] for x in far[:3]], eids=[s["evidence_id"], m["eid"], geid] + [x[2] for x in far[:3]], cands=[gold] + [x[1] for x in far[:3]], anchor_eid=s["evidence_id"], mv_eid=m["eid"]))
        # L3 farthest / nearest_final, L4 order @ window end
        for t0, t1 in g.stride_wins():
            vis = g.visible(t0, t1); T = t1
            for ref in sorted(n for n in g.by if n in vis):
                rr = g.rest_at(ref, T, t0, t1)
                if rr is None: continue
                ranked = g.rank_others(ref, rr[0], T, t0, t1)
                if len(ranked) >= MIN_CAND:
                    for mode in ("far", "near"):
                        if mode == "far":
                            d0, gold, geid = ranked[-1]
                            if d0 - ranked[-2][0] < MARG_L3: continue
                            others = ranked[:3]; rel = "farthest"
                        else:
                            d0, gold, geid = ranked[0]
                            if ranked[1][0] - d0 < MARG_L3: continue
                            others = ranked[-3:]; rel = "nearest_final"
                        if not names_ok([gold] + [x[1] for x in others]) or not disjoint(ref, gold): continue
                        out.append(dict(subtype="medium_spatial_extreme", rel=rel, akind="movement", T=(t0 + t1) / 2, t0=t0, t1=t1, ref=ref, gold=gold, d=d0, marg=MARG_L3, mode=mode,
                                        wrong=[x[1] for x in others], eids=[rr[1], geid] + [x[2] for x in others], cands=[gold] + [x[1] for x in others], anchor_eid=rr[1]))
                if len(ranked) >= 3:
                    n = len(ranked); done = False
                    for i in range(n - 2):
                        for j in range(i + 1, n - 1):
                            if ranked[j][0] - ranked[i][0] < GAP_L4: continue
                            for k in range(j + 1, n):
                                if ranked[k][0] - ranked[j][0] < GAP_L4: continue
                                tri = [ranked[i], ranked[j], ranked[k]]; names = [x[1] for x in tri]
                                if not names_ok(names) or any(not disjoint(ref, nm) for nm in names): continue
                                gold = " -> ".join(names)
                                perms = [" -> ".join(pp) for pp in ([names[0], names[2], names[1]], [names[2], names[1], names[0]], [names[2], names[0], names[1]])]
                                out.append(dict(subtype="high_spatial_order", rel="order_by_distance", akind="movement", T=(t0 + t1) / 2, t0=t0, t1=t1, ref=ref, gold=gold, d=None, marg=GAP_L4,
                                                wrong=perms, eids=[rr[1]] + [x[2] for x in tri], cands=names, anchor_eid=rr[1], dists=[round(x[0], 3) for x in tri]))
                                done = True; break
                            if done: break
                        if done: break
        # ego side @ movement end / sound
        try:
            import pose_hdepic as POSE
            has_pose = POSE.available(vid)
        except Exception:
            has_pose = False
        if has_pose:
            def ego_cands(T, t0, t1):
                p = POSE.at(vid, T)
                if p is None: return None
                cam, R = p; vis = g.visible(t0, t1); res = []
                for n in g.by:
                    if n not in vis: continue
                    r = g.rest_at(n, T, t0, t1)
                    if r is None: continue
                    f_, l_, _, rng = POSE.to_device(cam, R, r[0])
                    if not (EGO_MIN_R <= rng <= EGO_MAX_R): continue
                    res.append((f_, l_, rng, n, r[1]))
                res.sort(key=lambda x: x[3]); return res
            anchors = [("movement", m["t1"], g.win_around((m["t0"] + m["t1"]) / 2), _clean(m["name"]), m["eid"], None) for m in g.moves if _xyz(m["end_xyz"]) is not None]
            for s in self._sounds.get(vid, []):
                st, se = s["time"]["start_sec"], s["time"]["end_sec"]; mid = (st + se) / 2; t0, t1 = g.win_around(mid)
                if t0 <= st and se <= t1: anchors.append(("sound", mid, (t0, t1), None, s["evidence_id"], s["value"].get("label")))
            for akind, T, (t0, t1), anchor_name, aeid, slabel in anchors:
                if not (t0 <= T <= t1): continue
                cands = ego_cands(T, t0, t1)
                if not cands: continue
                if anchor_name:
                    ah = _head(anchor_name); cands = [c for c in cands if c[3] != anchor_name and _head(c[3]) != ah]
                if len(cands) < MIN_CAND: continue
                for mode in ("right", "left"):
                    key = (lambda x: x[1]) if mode == "right" else (lambda x: -x[1])
                    s_ = sorted(cands, key=lambda x: (key(x), x[3]))
                    if key(s_[1]) - key(s_[0]) < EGO_MARG: continue
                    gold = s_[0]; others = list(reversed(s_[-3:]))
                    if len(others) < 3 or not names_ok([gold[3]] + [x[3] for x in others]): continue
                    out.append(dict(subtype=("easy" if akind == "movement" else "low") + "_spatial_side", rel="side_" + mode, akind=akind, T=T, t0=t0, t1=t1, ref="the camera wearer", gold=gold[3],
                                    d=None, marg=EGO_MARG, mode=mode, lat=gold[1], slabel=slabel, anchor_name=anchor_name,
                                    wrong=[x[3] for x in others], eids=[aeid, gold[4]] + [x[4] for x in others], cands=[gold[3]] + [x[3] for x in others], anchor_eid=aeid))
        # cap per relation(确定性)
        by = collections.defaultdict(list)
        for f in out:
            f["fact_id"] = _fid(vid, f["subtype"], f["gold"], f["eids"], f["t0"]); by[(f["rel"], f["akind"])].append(f)
        res = []
        for k, fs in by.items():
            fs.sort(key=lambda f: f["fact_id"]); res += fs[:CAP]
        return res

    def records(self, vid):
        self._load(); mid = f"{DS}/{vid}"; wins = _sample_windows()
        DEFN = {"nearest": lambda f: f"Among the objects visible in the window, the one closest to the {f['ref']} at the anchor moment (3D distance between resting positions).",
                "nearest_final": lambda f: f"After all placements in the window, the object closest to the {f['ref']} at the end of the window.",
                "farthest": lambda f: f"Among candidate objects whose resting positions are known in the window, the one farthest from the {f['ref']} at the end of the window; it may be out of view then.",
                "order_by_distance": lambda f: f"Ordering of the three objects by 3D distance from the {f['ref']} at the end of the window, nearest first.",
                "side_right": lambda f: "At the anchor moment, the object farthest to the CAMERA WEARER'S RIGHT in the wearer's own view (reference frame = the wearer / device, NOT the anchored object).",
                "side_left": lambda f: "At the anchor moment, the object farthest to the CAMERA WEARER'S LEFT in the wearer's own view (reference frame = the wearer / device, NOT the anchored object)."}
        for f in self._facts(vid):
            rel = f["rel"]; ego = rel.startswith("side_")
            val = {"relation": rel, "relation_definition": DEFN[rel](f), "anchor_kind": f["akind"], "anchor_time_sec": round(f["T"], 3), "window": [f["t0"], f["t1"]],
                   "reference_object": f["ref"], "answer_object": f["gold"], "verified_wrong_answers": f["wrong"], "absent_in_window": [],
                   "d_gold_m": round(f["d"], 3) if f.get("d") is not None else None, "margin_m": f["marg"], "lateral_gold_m": round(f["lat"], 3) if f.get("lat") is not None else None,
                   "side_mode": f.get("mode"), "anchor_sound_label": f.get("slabel"), "anchor_object": f.get("anchor_name"), "dists_m": f.get("dists"),
                   "frame": "camera (device frame at anchor time: left/right of the wearer)" if ego else "world (HD-EPIC digital twin, metres)",
                   "query_frame": {"type": "camera_at_time" if ego else "world", "reference_timestamp": round(f["T"], 3)},
                   "frame_of_reference": EGO_FRAME(f["mode"]) if ego else ALLO_FRAME(f["ref"]),
                   "candidate_set": {"names": f["cands"], "completeness": "objects with recorded resting positions, visible in the window; distractors are geometry-verified"},
                   "original_subtype": f["subtype"], "fact_id": f["fact_id"]}
            yield record(evidence_id=evidence_id(DS, vid, "spatial", f["fact_id"]), video_id=vid, media_id=mid, kind="spatial_relation", domain="physical.spatial",
                         t0=f["T"], t1=f["T"], event_id=sample_at(wins, vid, f["T"]), value=val, epistemic="measurement", modalities=["video"] + (["audio"] if f["akind"] == "sound" else []),
                         entities=[{"entity_id": "name:" + f["gold"].replace(" ", "_"), "id_space": "name_only", "name": f["gold"]}],
                         provenance={"source_type": "derived_3d_geometry", "dataset": DS, "source": SRC, "source_file": "hd-epic/annotations/data/scene-and-object-movements/mask_info.json",
                                     "source_record_id": f["fact_id"], "derived_from": list(dict.fromkeys(f["eids"])),
                                     "method": "adapters/hdepic_e_spatial_derived.py (port of bench/pyramid/spatial.py: provable rest positions, rank by 3D distance; side = device-frame lateral via pose_hdepic)"},
                         coverage={"scope_start_sec": f["t0"], "scope_end_sec": f["t1"], "target_type": "spatial_relation", "completeness": "partial"},
                         flags=["DERIVED"] + (["EGO_POSE"] if ego else []))

    def files_read(self): return list(self._files)
