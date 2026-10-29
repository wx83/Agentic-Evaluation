"""masks + 深度 + 位姿 → 物体 3D 质心轨迹 / 静止区间 / 持握段 → 移动事件 + 空间关系 → evidence 记录(10-15 按 Benchmark_Ground_Truth_Annotation_Spec 重写)。
参照系 = 本 clip 第 1 帧相机(run_da3.load_da3);所有记录 provenance model_prediction、flags DERIVED + MODEL_ESTIMATED_3D;经 finalize.py 合 Gemini / fixture 后由 adapters/geo3d.py 进 store。
kinds:spatial_frame / camera_calibration(每 clip 1)、camera_pose(每帧)、object_instance(每实例)、object_observation(每实例每帧)、
      object_position_interval(静止区间)、object_move / object_location_transition(持握段前后的静止位置)、spatial_relation(nearest / farthest / order_by_distance / near / distance / side_left / side_right / ego_behind / ego_sector)。
  $HOLI -m geo3d.derive --samples all [--no-gemini]"""
import json, argparse, math, collections, re, sys
from pathlib import Path
import numpy as np
from scipy import ndimage
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from . import cfg
from . import quality as Q
from . import alias as AL
from .run_da3 import load_da3
from adapters.base import record
from ids import evidence_id
import schema

PUT_VERBS = {"put", "place", "drop", "set", "lay", "leave", "rest", "return", "hang"}
PICK_VERBS = {"pick", "take", "grab", "lift", "remove", "get", "hold"}
STOP = {"the", "a", "an", "his", "her", "their", "its", "of", "with", "on", "in", "into", "from", "to", "at", "and", "c", "#c", "#unsure", "up", "down", "out", "off"}
SECTORS = ["front-left", "front-right", "back-left", "back-right"]
SURFACE_WORDS = {"wall", "floor", "ground", "ceiling", "deck", "tile", "tiles", "sink", "oven", "stove", "counter", "countertop", "table", "workbench", "bench", "desk", "shelf", "cabinet", "door", "window", "fence", "heater", "lamp", "faucet", "tap"}
def is_surface_like(name):
    return bool({w for w in re.findall(r"[a-z]+", name.lower())} & SURFACE_WORDS)


def stem(w):
    for suf in ("ing", "ies", "es", "ed", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf): return w[: -len(suf)]
    return w


def unpack(m_packed, hh, ww):
    return np.unpackbits(m_packed)[: hh * ww].reshape(hh, ww).astype(bool)


def load_tracks(cd):
    """-> {name: {"instances": {inst_id: {"frames": [...], "masks": {fi: bool mask at half-res}, "probs": {fi: p}}}, "hw": (hh, ww)}}"""
    od = Path(cd) / "sam3"; summ = json.loads((od / "tracks.json").read_text()); out = {}
    for name, info in summ["names"].items():
        if not info.get("instances"): continue
        z = np.load(od / f"{info['slug']}.npz"); hh, ww = [int(x) for x in z["hw"]]
        M = z["masks"]; Pq = z["probs"]
        present = (Pq > 0) | M.any(axis=2)                       # [K, N]
        order = np.argsort(-present.sum(1))                      # 帧数最多的实例优先
        if len(order) > 20 and name != "hand":                   # 碎片类(leaves and debris 之类)被切成上百个实例:只留前 12 个
            order = order[:12]
        inst = {}
        for k in order:
            fr = [int(fi) for fi in np.nonzero(present[k])[0]]
            if len(fr) < cfg.MIN_TRACK: continue
            inst[f"{name}#{int(z['obj_ids'][k])}"] = {"frames": fr, "masks": {fi: unpack(M[k, fi], hh, ww) for fi in fr}, "probs": {fi: float(Pq[k, fi]) for fi in fr}}
        if inst: out[name] = {"instances": inst, "hw": (hh, ww)}
    return out


def backproject_median(depth, conf, K, mask_half, erode=cfg.ERODE):
    """mask(半分辨率)→ 缩到深度分辨率、腐蚀、conf 过滤 → 相机系质心(按轴中位)。返回 (Xc, stats) 或 (None, stats)。"""
    h, w = depth.shape; hh, ww = mask_half.shape
    ys = (np.arange(h) * hh / h).astype(int).clip(0, hh - 1); xs = (np.arange(w) * ww / w).astype(int).clip(0, ww - 1)
    M = mask_half[ys][:, xs]
    area0 = int(M.sum())
    if area0 >= 200 and erode > 1:
        M = ndimage.binary_erosion(M, structure=np.ones((erode, erode), bool))
    valid = M & np.isfinite(depth) & (depth > 0.05)
    if valid.sum() >= 20:
        thr = np.percentile(conf[valid], 20); valid &= conf >= thr
    n = int(valid.sum())
    if n < 10:
        return None, {"n_px": n, "area": area0}
    vv, uu = np.nonzero(valid); d = depth[vv, uu]
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    X = (uu - cx) / fx * d; Y = (vv - cy) / fy * d; Z = d
    Xc = np.array([np.median(X), np.median(Y), np.median(Z)])
    cu, cv = float(np.median(uu)), float(np.median(vv))
    border = cu < cfg.BORDER_FRAC * w or cu > (1 - cfg.BORDER_FRAC) * w or cv < cfg.BORDER_FRAC * h or cv > (1 - cfg.BORDER_FRAC) * h
    iqr = float(np.percentile(d, 75) - np.percentile(d, 25)) / max(float(np.median(d)), 1e-6)
    return Xc, {"n_px": n, "area": area0, "depth_iqr_rel": round(iqr, 3), "border": bool(border), "px": [cu, cv]}


def centroids(cd, da3, tracks):
    """每个实例每帧的世界系质心 + 元信息。hand 实例用于 hand_overlap。"""
    fr = cfg.load_frames(cd)["frames"]; N = len(fr)
    hands = {}
    for name, tr in tracks.items():
        if name == "hand":
            for inst in tr["instances"].values():
                for fi, m in inst["masks"].items():
                    hands[fi] = (hands[fi] | m) if fi in hands else m
    out = {}; H, W = da3["meta"]["frame_hw"]
    for name, tr in tracks.items():
        if name == "hand": continue
        hh, ww = tr["hw"]; sy, sx = H / hh, W / ww
        for iid, inst in tr["instances"].items():
            rows = []
            for fi in inst["frames"]:
                if fi >= N: continue
                m = inst["masks"][fi]
                Xc, st = backproject_median(da3["depth"][fi], da3["conf"][fi], da3["K"][fi], m)
                if Xc is None: continue
                Xw = (da3["c2w"][fi] @ np.array([*Xc, 1.0]))[:3]
                ho = float((m & hands[fi]).sum() / max(m.sum(), 1)) if fi in hands else 0.0
                ys_, xs_ = np.nonzero(m)      # 2D 框 / 质心换算到帧分辨率(frame_hw),mask 本身留在 sam3/<slug>.npz
                bbox = [round(float(xs_.min() * sx), 1), round(float(ys_.min() * sy), 1), round(float((xs_.max() + 1) * sx), 1), round(float((ys_.max() + 1) * sy), 1)] if len(ys_) else None
                cpx = [round(float(xs_.mean() * sx), 1), round(float(ys_.mean() * sy), 1)] if len(ys_) else None
                rows.append({"fi": fi, "t": fr[fi]["t_abs"], "xyz": [round(float(x), 4) for x in Xw], "xc": [round(float(x), 4) for x in Xc],
                             "range": round(float(np.linalg.norm(Xc)), 3), "prob": inst["probs"][fi], "hand_overlap": round(ho, 3), "bbox": bbox, "centroid_px": cpx,
                             "mask_ref": f"sam3/{cfg.slug(name)}.npz obj_id={iid.split('#')[-1]} frame={fi} (packbits {hh}x{ww})", **st})
            if len(rows) >= cfg.MIN_TRACK:
                out[iid] = {"name": name, "rows": rows}
    return out


def static_intervals(rows, r=cfg.STATIC_R, min_s=cfg.STATIC_MIN_S):
    """静止区间:连续观测、排除被持握帧、最大位移 ≤ r、时长 ≥ min_s;位置 = 中位。"""
    pts = [x for x in rows if x["hand_overlap"] <= cfg.HAND_OVERLAP]
    ivs = []; i = 0
    while i < len(pts):
        j = i; P = [pts[i]["xyz"]]
        while j + 1 < len(pts):
            cand = np.array(P + [pts[j + 1]["xyz"]])
            if np.max(np.linalg.norm(cand[:, None] - cand[None], axis=2)) <= r: P.append(pts[j + 1]["xyz"]); j += 1
            else: break
        if pts[j]["t"] - pts[i]["t"] >= min_s:
            arr = np.array(P)
            ivs.append({"t0": pts[i]["t"], "t1": pts[j]["t"], "n": len(P), "xyz": [round(float(v), 4) for v in np.median(arr, 0)],
                        "std_m": round(float(np.linalg.norm(arr.std(0))), 3), "fi0": pts[i]["fi"], "fi1": pts[j]["fi"]})
        i = j + 1
    return ivs


def rest_at(ivs, rows, T, r=cfg.STATIC_R):
    """T 时刻的可证静止位置(仿 spatial.rest_at):含 T 的区间 → observed;否则 T 之前最后一个区间且其后到 T 没观测到离开 → last_seen;否则 T 之后第一个区间对称 → next_seen。返回 (xyz, how, iv)。"""
    for iv in ivs:
        if iv["t0"] - cfg.REST_PAD <= T <= iv["t1"] + cfg.REST_PAD: return iv["xyz"], "contains", iv
    before = [iv for iv in ivs if iv["t1"] < T]; after = [iv for iv in ivs if iv["t0"] > T]
    if before:
        iv = before[-1]; later = [x for x in rows if iv["t1"] < x["t"] <= T]
        if all(np.linalg.norm(np.array(x["xyz"]) - np.array(iv["xyz"])) <= r for x in later): return iv["xyz"], "before", iv
    if after:
        iv = after[0]; earlier = [x for x in rows if T <= x["t"] < iv["t0"]]
        if all(np.linalg.norm(np.array(x["xyz"]) - np.array(iv["xyz"])) <= r for x in earlier): return iv["xyz"], "after", iv
    return None, None, None


HOW2STATUS = {"contains": "observed", "before": "last_seen", "after": "next_seen"}


def cam_at(da3, frames, T):
    fi = int(np.argmin([abs(f["t_abs"] - T) for f in frames])); return fi, da3["c2w"][fi]


def camera_stable(da3, frames, T):
    idx = [f["k"] for f in frames if abs(f["t_abs"] - T) <= cfg.STAB_WIN]
    if len(idx) < 2: return True
    C = np.array([da3["c2w"][i][:3, 3] for i in idx]); return float(np.max(np.linalg.norm(C[:, None] - C[None], axis=2))) <= cfg.STAB_MOVE


def to_device_cv(c2w, xyz):
    """OpenCV 相机系:forward = z,lateral = -x(左正,与 spatial.py「最右 = lateral 最小」一致),down = y。"""
    v = c2w[:3, :3].T @ (np.array(xyz) - c2w[:3, 3])
    return float(v[2]), float(-v[0]), float(v[1]), float(np.linalg.norm(v))


def bearing_deg(fwd, left):
    """方位角:0 = 正前,+ = 左,±180 = 正后。"""
    return float(np.degrees(np.arctan2(left, fwd)))


def sector_of(deg):
    fb = "front" if abs(deg) < 90 else "back"; lr = "left" if deg > 0 else "right"
    margin = min(abs(deg), abs(abs(deg) - 90), 180 - abs(deg))
    return f"{fb}-{lr}", float(margin)


def horizontal_bearing(c2w, xyz, down_w):
    """重力对齐的方位角:把相机 forward 投到 ⟂ down 的水平面,left = forward × down。"""
    R = c2w[:3, :3]; c = c2w[:3, 3]; f = R[:, 2]; f_h = f - down_w * (f @ down_w)
    if np.linalg.norm(f_h) < 1e-6: return None
    f_h /= np.linalg.norm(f_h); l_h = np.cross(f_h, down_w); d = np.array(xyz) - c
    return bearing_deg(float(d @ f_h), float(d @ l_h))


def dist(a, b): return float(np.linalg.norm(np.array(a) - np.array(b)))


def make_matcher(names, alias_names):
    """文本 → canonical 物体名(别名也能匹配到 canonical)。"""
    cands = [(n, n) for n in names] + [(a, c) for a, c in alias_names.items()]
    def match(txt):
        toks = {stem(w) for w in re.findall(r"[a-z]+", (txt or "").lower()) if w not in STOP and len(w) > 2}
        best = None
        for n, canon in cands:
            nt = {stem(w) for w in re.findall(r"[a-z]+", n.lower())}
            if nt and nt <= toks and (best is None or len(nt) > best[0]): best = (len(nt), canon)
        return best[1] if best else None
    return match


def anchors(s, match, moves):
    """锚点时刻 [{t, kind, ref, note, put}];kind ∈ gemini_spatial / gemini_action / narration / move_end / window_end。"""
    t0 = s["window"][0]; out = []
    g = s["gemini"]
    for x in g.get("spatial") or []:
        try: t = t0 + float(x.get("t"))
        except Exception: continue
        out.append({"t": round(t, 3), "kind": "gemini_spatial", "ref": match(x.get("object")) or match(x.get("reference")), "note": f'{x.get("object")} {x.get("relation")} {x.get("reference")}', "put": False})
    for a in g.get("actions") or []:
        vb = str(a.get("verb") or "").lower().split()
        if vb and stem(vb[0]) in PUT_VERBS:
            try: t = t0 + float(a.get("t1"))
            except Exception: continue
            out.append({"t": round(t, 3), "kind": "gemini_action", "ref": match(a.get("object")), "note": f'{a.get("verb")} {a.get("object")}', "put": True})
    for n_ in s.get("gt_narrations") or []:
        m = match(n_["text"])
        if m:
            put = bool({stem(w) for w in re.findall(r"[a-z]+", n_["text"].lower())} & PUT_VERBS)
            out.append({"t": round(t0 + n_["t"], 3), "kind": "narration", "ref": m, "note": n_["text"], "put": put})
    for mv in moves:
        if mv.get("end_xyz") is not None:
            out.append({"t": round(mv["t_end"], 3), "kind": "move_end", "ref": mv["object"], "note": f'{mv["object"]} placed (move {mv["k"]})', "put": True, "move_k": (mv["object"], mv["k"])})
    out.append({"t": round(s["window"][1] - 0.5, 3), "kind": "window_end", "ref": None, "note": "end of window", "put": False})
    seen = set(); uniq = []
    for a in sorted(out, key=lambda a: a["t"]):
        key = (round(a["t"], 1), a["ref"], a["kind"])
        if key in seen: continue
        seen.add(key); uniq.append(a)
    return uniq[:80]


def anchor_kind_out(a):
    """retrieve.SKILL_NEEDS 的 L1 spatial skill 只接受 anchor_kind=movement:放下 / 拿起类锚点统一记 movement,原 kind 存 anchor_source。"""
    if a["kind"] in ("gemini_action", "move_end") or (a["kind"] == "narration" and a.get("put")): return "movement"
    return a["kind"]


def held_segments(rows):
    segs = []; cur = []
    for idx, x in enumerate(rows):
        if x["hand_overlap"] > cfg.HAND_OVERLAP: cur.append(idx)
        else:
            if len(cur) >= cfg.HOLD_MIN_FRAMES: segs.append((cur[0], cur[-1]))
            cur = []
    if len(cur) >= cfg.HOLD_MIN_FRAMES: segs.append((cur[0], cur[-1]))
    return segs


def derive_moves(s, objs, match):
    """相邻两个静止区间之间的位移 ≥ STATIC_R → 物体被移动过(spec §7.2:从离开稳定位置到重新稳定);≥ MOVE_MIN_DISP 记 object_location_transition,否则 object_move。
    持握帧(hand_overlap)与 narration / Gemini 动作只作辅助证据(2 fps 下手部重叠极少达到阈值)。"""
    t0 = s["window"][0]; moves = []
    narr = [(t0 + n_["t"], n_["text"], match(n_["text"])) for n_ in (s.get("gt_narrations") or [])]
    acts = []
    for a in (s["gemini"].get("actions") or []):
        try: acts.append((t0 + float(a.get("t0")), t0 + float(a.get("t1")), f'{a.get("verb")} {a.get("object")}', match(a.get("object"))))
        except Exception: pass
    handled = {(o.get("name") or "").lower() for o in (s["gemini"].get("objects") or []) if o.get("handled_by_wearer")}
    manip = {m for t, tx, m in narr if m and ({stem(w) for w in re.findall(r"[a-z]+", tx.lower())} & (PUT_VERBS | PICK_VERBS))}
    for n, o in objs.items():
        # 10-15 晚:Gemini 核验 16 条 move 只认 1 条,其余全是 sink / oven / wall / deck / floor 这类固定面的漂移 → 只对被拿放的物体(probe handled_by_wearer 或 narration 拿 / 放到它)推导,表面类名字一律不推
        if is_surface_like(n) or not (n in handled or o.get("track_name") in handled or n in manip): continue
        rows, ivs = o["rows"], o["ivs"]; k = 0
        for j in range(len(ivs) - 1):
            st, en = ivs[j], ivs[j + 1]; disp = dist(st["xyz"], en["xyz"])
            if disp < cfg.STATIC_R: continue                          # 同一位置因缺帧被切成两段,不是移动
            ta, tb = st["t1"], en["t0"]; gap = [x for x in rows if ta < x["t"] < tb]
            held = sum(1 for x in gap if x["hand_overlap"] > cfg.HAND_OVERLAP)
            trig = next(({"kind": "narration", "t": round(t, 3), "text": tx} for t, tx, m in narr if m == n and ta - 1.5 <= t <= tb + 1.5), None) \
                or next(({"kind": "gemini_action", "t": round(a0, 3), "text": tx} for a0, a1, tx, m in acts if m == n and a0 <= tb + 1 and a1 >= ta - 1), None)
            moves.append({"object": n, "k": k, "start_iv": j, "end_iv": j + 1, "t_start": round(ta, 3), "t_end": round(tb, 3), "gap_s": round(tb - ta, 3),
                          "held": None, "hand_frames": held, "n_obs_in_gap": len(gap), "start_xyz": st["xyz"], "end_xyz": en["xyz"],
                          "displacement_m": round(disp, 3), "is_transition": bool(disp >= cfg.MOVE_MIN_DISP),
                          "label": f"{n}: moved {disp:.2f} m between resting places ({ta:.1f}-{tb:.1f}s)", "trigger": trig})
            k += 1
    return moves


def derive_relations(s, cd, da3, objs, match, moves, qual):
    frames = cfg.load_frames(cd)["frames"]; w0, w1 = s["window"]
    metric_ok = qual["scale_status"] == "metric_estimated"
    down_w = np.array(da3["ref"]["gravity_world_estimate"], float)
    rels = []
    def positions_at(T):
        pos, basis = {}, {}
        for n, o in objs.items():
            p, how, iv = rest_at(o["ivs"], o["rows"], T)
            if p is not None:
                last = min(o["rows"], key=lambda x: abs(x["t"] - T))
                if not last.get("border"): pos[n] = p; basis[n] = {"how": how, "status": HOW2STATUS[how], "iv": o["ivs"].index(iv), "std_m": iv["std_m"]}
        return pos, basis
    for a in anchors(s, match, moves):
        T = a["t"]; pos, basis = positions_at(T)
        if len(pos) < 2: continue
        flags = (["LOW_CANDIDATES"] if len(pos) < cfg.MIN_CAND else [])
        base = {"T": T, "kind": a["kind"], "anchor_kind": anchor_kind_out(a), "note": a["note"], "move_k": a.get("move_k"), "basis": basis, "flags": flags}
        refs = [a["ref"]] if a.get("ref") in pos else ([] if a["kind"] != "window_end" else list(pos)[:6])
        for ref in refs:
            others = sorted(((dist(pos[ref], pos[n]), n) for n in pos if n != ref))
            if len(others) >= 2:
                d1, g1 = others[0]; d2 = others[1][0]
                if d1 <= cfg.NEAR_L1 and d2 - d1 >= cfg.MARG:
                    rels.append({**base, "relation": "nearest", "reference_object": ref, "answer_object": g1, "d_gold_m": round(d1, 3), "margin_m": round(d2 - d1, 3), "wrong": [n for _, n in others[1:]]})
                dF, gF = others[-1]; dF2 = others[-2][0]
                if dF - dF2 >= cfg.MARG_L3:
                    rels.append({**base, "relation": "farthest", "reference_object": ref, "answer_object": gF, "d_gold_m": round(dF, 3), "margin_m": round(dF - dF2, 3), "wrong": [n for _, n in others[:-1]]})
                # near(阈值型):答案 ≤ NEAR_L1 - buffer,错误选项 ≥ NEAR_L1 + buffer
                far = [n for d, n in others if d >= cfg.NEAR_L1 + cfg.NEAR_BUF]
                for d, n in others[:2]:
                    if d <= cfg.NEAR_L1 - cfg.NEAR_BUF and far:
                        rels.append({**base, "relation": "near", "reference_object": ref, "answer_object": n, "d_gold_m": round(d, 3), "margin_m": round(min(dd for dd, m in others if m in far) - d, 3), "wrong": far,
                                     "near_threshold_m": cfg.NEAR_L1, "buffer_m": cfg.NEAR_BUF})
                if metric_ok:      # 数值距离只在尺度检查通过的 clip 产出;容差 = max(0.2, 2σ)
                    unc = math.sqrt(basis[ref]["std_m"] ** 2 + basis[g1]["std_m"] ** 2)
                    rels.append({**base, "relation": "distance", "reference_object": ref, "answer_object": g1, "d_gold_m": round(d1, 3), "margin_m": None, "wrong": [],
                                 "uncertainty_m": round(unc, 3), "tolerance_m": round(max(0.2, 2 * unc), 3), "distance_type": "center_3d"})
            if len(others) >= 3:
                top = others[:3]
                if all(top[i + 1][0] - top[i][0] >= cfg.GAP_L4 for i in range(2)):
                    rels.append({**base, "relation": "order_by_distance", "reference_object": ref, "answer_object": " -> ".join(n for _, n in top), "d_gold_m": round(top[0][0], 3),
                                 "margin_m": round(min(top[i + 1][0] - top[i][0] for i in range(2)), 3), "wrong": []})
        # ego(相机参照系),只在相机稳定时
        if camera_stable(da3, frames, T):
            fi, c2w = cam_at(da3, frames, T)
            ego = {}
            for n, p in pos.items():
                fwd, l, dn, rng = to_device_cv(c2w, p)
                if cfg.EGO_MIN_R <= rng <= cfg.EGO_MAX_R: ego[n] = (fwd, l, rng)
            lat = {n: v[1] for n, v in ego.items() if v[0] > 0}
            ego_base = {**base, "reference_object": None, "d_gold_m": None, "camera_frame_index": fi}
            if len(lat) >= 2:
                srt = sorted(lat.items(), key=lambda kv: kv[1])
                if srt[1][1] - srt[0][1] >= cfg.EGO_MARG:
                    rels.append({**ego_base, "relation": "side_right", "answer_object": srt[0][0], "margin_m": round(srt[1][1] - srt[0][1], 3), "lateral_gold_m": round(srt[0][1], 3), "wrong": [n for n, _ in srt[1:]]})
                if srt[-1][1] - srt[-2][1] >= cfg.EGO_MARG:
                    rels.append({**ego_base, "relation": "side_left", "answer_object": srt[-1][0], "margin_m": round(srt[-1][1] - srt[-2][1], 3), "lateral_gold_m": round(srt[-1][1], 3), "wrong": [n for n, _ in srt[:-1]]})
            behind = [n for n, v in ego.items() if v[0] < cfg.BEHIND_F]; front = [n for n, v in ego.items() if v[0] > cfg.FRONT_F]
            if len(behind) == 1 and front and (min(ego[n][0] for n in front) - ego[behind[0]][0]) >= cfg.BEHIND_MARG:
                rels.append({**ego_base, "relation": "ego_behind", "answer_object": behind[0], "margin_m": round(min(ego[n][0] for n in front) - ego[behind[0]][0], 3), "forward_gold_m": round(ego[behind[0]][0], 3), "wrong": front})
            secs = []
            for n, (fwd, l, rng) in ego.items():
                b = bearing_deg(fwd, l); sec, marg = sector_of(b); bh = horizontal_bearing(c2w, pos[n], down_w)
                sec_h = sector_of(bh)[0] if bh is not None else None
                if marg >= cfg.MIN_ANGLE_MARGIN and sec_h == sec: secs.append((marg, n, sec, b, bh))
            for marg, n, sec, b, bh in sorted(secs, reverse=True)[:3]:
                rels.append({**ego_base, "relation": "ego_sector", "answer_object": n, "margin_m": None, "sector": sec, "sector_candidates": SECTORS, "wrong": [x for x in SECTORS if x != sec],
                             "bearing_deg": round(b, 1), "bearing_horizontal_deg": round(bh, 1), "angle_margin_deg": round(marg, 1)})
    # 去重:world 关系按 (relation, ref, answer, 两端位置基础区间) 只留最早锚点(几何完全相同);ego 关系按 (relation, answer, 候选集) 最多留 2 个锚点
    seen_w, seen_e, out = set(), {}, []
    for r in rels:
        if r["relation"] in ("nearest", "farthest", "order_by_distance", "near", "distance"):
            names = [r["answer_object"].split(" -> ")[0]] + ([r["reference_object"]] if r.get("reference_object") else [])
            key = (r["relation"], r.get("reference_object"), r["answer_object"], tuple(sorted((n, r["basis"][n]["iv"]) for n in names if n in r["basis"])))
            if key in seen_w: continue
            seen_w.add(key); out.append(r)
        elif r["relation"] in ("side_left", "side_right", "ego_behind"):
            key = (r["relation"], r["answer_object"], tuple(sorted(r.get("wrong", []))))
            seen_e[key] = seen_e.get(key, 0) + 1
            if seen_e[key] <= 2: out.append(r)
        else: out.append(r)
    rels = out
    best = {}
    for r in rels:
        if r["relation"] == "ego_sector":
            key = (r["answer_object"], r["sector"])
            if key not in best or r["angle_margin_deg"] > best[key]["angle_margin_deg"]: best[key] = r
    rels = [r for r in rels if r["relation"] != "ego_sector" or best[(r["answer_object"], r["sector"])] is r]
    return rels


# 所有关系都只在候选集(answer_object + verified_wrong_answers,即同一时刻有 3D 位置的物体)里比,不是全场景绝对(用户 10-15 强调)
def frame_of_reference(relation, reference_object, T):
    """空间关系的参照系语义(用户 10-20:左右 / 远近类题必须写清 from whose view、egocentric / allocentric / intrinsic、参照物、相对位置)。
    query_frame 给几何(轴、位姿引用);这里给题面必须表达的语义。intrinsic(物体自身 front / left)本流水线没有物体朝向 GT,不产出。"""
    ego = relation in ("side_left", "side_right", "ego_behind", "ego_sector")
    if ego:
        return {"type": "egocentric", "viewpoint": f"the camera wearer (camera centre) at {float(T):.2f}s", "origin": "camera centre at reference_timestamp",
                "orientation": "the way the camera faces at reference_timestamp (camera +z); camera forward is NOT assumed to equal body forward",
                "handedness": "the wearer's own left / right (camera -x = left, +x = right)", "reference_object": "the camera wearer",
                "projection": {"side_left": "camera lateral axis", "side_right": "camera lateral axis", "ego_behind": "camera forward axis",
                               "ego_sector": "horizontal bearing in camera axes (front/back by +z, left/right by -x)"}[relation],
                "direction_rule": {"side_left": "extreme: farthest to the wearer's left among the candidates", "side_right": "extreme: farthest to the wearer's right among the candidates",
                                   "ego_behind": f"forward < {cfg.BEHIND_F} m = behind the wearer; forward > {cfg.FRONT_F} m = in front",
                                   "ego_sector": f"4 quadrants front-left / front-right / back-left / back-right; bearing >= {cfg.MIN_ANGLE_MARGIN} deg from every boundary"}[relation],
                "comparison": "relative position among the listed candidates only, not absolute", "intrinsic_available": False,
                "question_must_state": "from the camera wearer's own viewpoint at that moment (egocentric: the wearer's left/right as the camera faces), relative to the wearer, among the listed candidates"}
    rel_cmp = relation in ("nearest", "farthest", "order_by_distance", "near")
    return {"type": "allocentric", "viewpoint": None, "origin": (f"the resting position of the reference object ({reference_object})" if reference_object else "the scene"),
            "orientation": "none: 3D centre distances in the scene are viewpoint-independent", "handedness": None, "reference_object": reference_object,
            "projection": "3D Euclidean distance between resting positions (frame-0 camera axes, metres)", "direction_rule": None,
            "comparison": ("relative among the listed candidates only, not absolute" if rel_cmp else "numeric with tolerance"), "intrinsic_available": False,
            "question_must_state": (f"relative to {reference_object} (scene distance, independent of where the wearer stands), among the listed candidates" if reference_object else "scene distance")}


DEF = {"nearest": "ALLOCENTRIC (scene distance relative to the reference object, independent of viewpoint): among the listed candidate objects only (answer_object + verified_wrong_answers), the one whose resting position is closest (3D, metres) to the reference object's resting position at the anchor time; relative to the candidates, not the whole scene",
       "farthest": "ALLOCENTRIC (scene distance relative to the reference object, independent of viewpoint): among the listed candidate objects only, the one whose resting position is farthest (3D, metres) from the reference object at the anchor time; relative to the candidates, not the whole scene",
       "order_by_distance": "ALLOCENTRIC (scene distance relative to the reference object): among the listed candidate objects only, the three nearest to the reference, ordered by increasing 3D distance, with ≥0.4 m between neighbours",
       "near": f"answer_object's resting position is within {cfg.NEAR_L1 - cfg.NEAR_BUF} m (3D centre distance) of the reference object at the anchor time; the listed wrong answers are ≥ {cfg.NEAR_L1 + cfg.NEAR_BUF} m away",
       "distance": "3D centre-to-centre distance (metres, DA3 metric estimate) between reference_object and answer_object at the anchor time; tolerance_m = max(0.2, 2σ of the two resting positions); only emitted when the clip's scale_status is metric_estimated",
       "side_right": "EGOCENTRIC (from the camera wearer's own viewpoint at the anchor time; left/right = the wearer's own, as the camera faces): among the listed candidate objects only (those in front of the camera wearer at the anchor time), the one farthest to the wearer's RIGHT (camera frame, lateral = -x); relative to the candidates, not the whole scene",
       "side_left": "EGOCENTRIC (from the camera wearer's own viewpoint at the anchor time; left/right = the wearer's own, as the camera faces): among the listed candidate objects only (those in front of the camera wearer at the anchor time), the one farthest to the wearer's LEFT (camera frame, lateral = -x); relative to the candidates, not the whole scene",
       "ego_behind": f"EGOCENTRIC (relative to the camera wearer at the anchor time, as the camera faces): among the listed candidate objects only, answer_object is the one BEHIND the camera wearer at the anchor time (camera-frame forward < {cfg.BEHIND_F} m) while every wrong answer is in front (forward > {cfg.FRONT_F} m)",
       "ego_sector": f"EGOCENTRIC (from the camera wearer's own viewpoint at the anchor time): the quadrant of answer_object relative to the camera wearer at the anchor time: front/back by camera forward axis, left/right by camera lateral axis; bearing ≥ {cfg.MIN_ANGLE_MARGIN}° from every quadrant boundary and the gravity-aligned horizontal bearing gives the same quadrant"}


def emit_records(s, cd, da3, frames, qual, pf, calib, inst_all, objs, aliases, parts, moves, rels, tracks):
    vid = s["video_id"]; sid = s["sample_id"]; mid = f"egoplan/{vid}"; w0, w1 = s["window"]; fj = cfg.load_frames(cd)
    WF = f"frame0_cam:{sid}"
    E = lambda key: evidence_id("egoplan", vid, "geo3d", f"{sid}/{key}")
    prov0 = {"source_type": "model_prediction", "dataset": "egoplan", "source": "egoplan.geo3d_da3_sam3", "source_file": str(Path(cd).relative_to(cfg.ROOT)),
             "method": f"{cfg.DA3_MODEL} pose-free (metric depth + w2c) + SAM3 text tracking; geo3d/derive.py v2", "world_frame": WF, "legacy_eid": None, "derived_from": []}
    def prov(derived=()): return {**prov0, "derived_from": list(derived)}
    cov = {"scope_start_sec": w0, "scope_end_sec": w1, "target_type": "3d_estimate", "completeness": "partial"}
    base_flags = ["DERIVED", "MODEL_ESTIMATED_3D"] + (["POSE_FAILED"] if not qual["pose_valid"] else []) + (["SCALE_SUSPECT"] if qual["scale_status"] != "metric_estimated" else [])
    def ent(n, iid_short): return [{"entity_id": f"geo3d:{sid}:{iid_short}", "id_space": "geo3d_track", "name": n}, {"entity_id": f"name:{n}", "id_space": "name_only", "name": n}]
    def rec(key, kind, t0, t1, value, *, entities=None, derived=(), flags=(), epistemic="interpretation"):
        return record(evidence_id=E(key), video_id=vid, media_id=mid, kind=kind, domain="physical.spatial", t0=t0, t1=t1, event_id=sid, value=value,
                      epistemic=epistemic, modalities=["video"], entities=entities or [], provenance=prov(derived), coverage=cov, flags=base_flags + list(flags))
    recs = []
    frame_eid, calib_eid = E("frame"), E("calib")
    ref = da3["ref"]
    recs.append(rec("frame", "spatial_frame", w0, w1, {
        "frame_id": WF, "map_id": WF, "origin_definition": f"camera centre of sampled frame 0 (t_abs {frames[0]['t_abs']} s); DA3 raw reference view re-expressed via T0 = inv(raw_c2w_frame0)",
        "axis_convention": "OpenCV camera axes of frame 0: x right, y down, z forward", "handedness": "right_handed", "unit": "m",
        "scale_status": qual["scale_status"], "scale_source": f"DA3 metric head (scale_factor {da3['meta']['scale_factor']:.4f}); {qual['scale_check']['note']}", "scale_check": qual["scale_check"],
        "gravity_or_up_source": ref["gravity_source"], "gravity_world_estimate": ref["gravity_world_estimate"], "parent_frame": None, "transform_from_parent": None,
        "native_frame_note": "DA3 pose-free output is in its own reference view (saddle_balanced); da3_raw_c2w_frame0 maps back", "da3_raw_c2w_frame0": ref["da3_raw_c2w_frame0"],
        "pose_valid": qual["pose_valid"], "pose_valid_interval": qual["pose_valid_interval"], "n_valid_frames": qual["n_valid_frames"], "n_frames": qual["n_frames"], "quality": qual["quality"],
        "pose_fail_reasons": qual["reasons"], "calibration_ref": calib_eid, "time": {"basis": fj.get("t_abs_basis"), "source_fps": fj.get("source_fps"), "fps_constant": fj.get("fps_constant"),
        "av_offset_s": fj.get("av_offset_s"), "time_uncertainty_s": fj.get("time_uncertainty_s", cfg.TIME_UNC), "rest_tolerance": fj.get("rest_tolerance")}}))
    recs.append(rec("calib", "camera_calibration", w0, w1, {**calib, "frame_id": WF, "applies_to": {"frames": [0, len(frames) - 1], "t": [w0, w1]}}))
    for f in frames:
        fi = f["k"]; q = pf[fi]
        recs.append(rec(f"cam{fi:04d}", "camera_pose", f["t_abs"], f["t_abs"], {
            "frame_index": fi, "mp4_frame": f["mp4_frame"], "frame_id": WF, "calibration_ref": calib_eid, "c2w": np.round(da3["c2w"][fi], 5).tolist(), "convention": "OpenCV c2w (T_world_from_camera), column vectors",
            "K_frame": np.round(da3["K_frame"][fi], 3).tolist(), "frame_hw": da3["meta"]["frame_hw"], "proc_hw": da3["meta"]["proc_hw"], "metric": bool(da3["meta"]["is_metric"]), "scale_factor": da3["meta"]["scale_factor"],
            "valid": bool(q["valid"] and qual["pose_valid"]), "quality": {k: q[k] for k in ("depth_rel_err_next", "speed_mps", "rot_deg_per_s")}, "time_uncertainty_s": cfg.TIME_UNC, "interpolated": False,
            "pose_method": "DA3 pose-free, re-expressed in frame-0 camera (run_da3.load_da3)", "reference": (ref if fi == 0 else {"kind": "first_frame_camera", "frame_index": 0})},
            derived=[calib_eid], flags=([] if q["valid"] else ["POSE_FRAME_INVALID"])))
    # hands as entities(只有 instance,不出 observation)
    for hid, inst in (tracks.get("hand") or {}).get("instances", {}).items():
        recs.append(rec(f"inst/{hid}", "object_instance", frames[inst["frames"][0]]["t_abs"], frames[inst["frames"][-1]]["t_abs"],
                        {"instance_id": f"geo3d:{sid}:{hid}", "instance_short": hid, "name": "hand", "entity_type": "hand", "association_scope": sid, "aliases": [], "alias_of": None, "part_of": None,
                         "track_source": f"SAM3 text prompt 'hand' obj_id {hid.split('#')[-1]}", "n_frames": len(inst["frames"]), "fixture_id": None}, entities=ent("hand", hid)))
    obs_eid = {}
    canon_of = {iid: aliases[iid]["canonical"] for iid in aliases}
    for iid, c in inst_all.items():
        n = c["name"]; tn = c.get("track_name", n); slug = cfg.slug(tn); oid = iid.split("#")[-1]; key = f"{slug}#{oid}"; rows = c["rows"]
        al = [a for a, v in aliases.items() if v["canonical"] == iid]
        sib = [j for j, cc in inst_all.items() if cc["name"] == n and j != iid]
        pp = [p for p in parts if iid in (p["a"], p["b"])]
        recs.append(rec(f"inst/{key}", "object_instance", rows[0]["t"], rows[-1]["t"], {
            "instance_id": f"geo3d:{sid}:{iid}", "instance_short": iid, "name": n, "entity_type": "object", "association_scope": sid, "aliases": [{"instance": a, "name": inst_all.get(a, {}).get("name") or a.split("#")[0], **{k: aliases[a][k] for k in ("d_m", "iou", "method")}} for a in al],
            "alias_of": canon_of.get(iid), "part_of_or_support_candidates": [{"other": (p["b"] if p["a"] == iid else p["a"]), "d_m": p["d_m"], "iou": p["iou"], "relation": p["relation"]} for p in pp],
            "track_source": f"SAM3 text prompt '{tn}' obj_id {oid}", "track_name": tn, "n_frames": len(rows), "co_visible_siblings": sib, "is_canonical_for_name": (objs.get(n, {}).get("iid") == iid), "fixture_id": None},
            entities=ent(n, iid), flags=(["MULTI_INSTANCE"] if sib else []) + (["CO_LOCATED"] if pp else [])))
        for x in rows:
            fi = x["fi"]; f = frames[fi]; e = E(f"{key}/obs{fi:04d}"); obs_eid[(iid, fi)] = e
            vis = "truncated_border" if x.get("border") else "occluded_by_hand" if x["hand_overlap"] > cfg.HAND_OVERLAP else "visible"
            lifted = qual["pose_valid"] and pf[fi]["valid"]
            recs.append(rec(f"{key}/obs{fi:04d}", "object_observation", x["t"], x["t"], {
                "object": n, "instance_id": f"geo3d:{sid}:{iid}", "frame_index": fi, "mp4_frame": f["mp4_frame"], "frame_id": WF, "unit": "m", "camera_pose_ref": E(f"cam{fi:04d}"),
                "bbox_xyxy_px": x.get("bbox"), "bbox_convention": f"[xmin,ymin,xmax,ymax] px, origin top-left, half-open, at frame_hw {da3['meta']['frame_hw'][0]}x{da3['meta']['frame_hw'][1]}", "centroid_px": x.get("centroid_px"),
                "mask_ref": {"file": f"sam3/{slug}.npz", "obj_id": int(oid), "frame": fi, "hw": list(tracks[tn]["hw"]), "encoding": "packbits", "image_transform": "half of frame_hw"},
                "visibility": vis, "representative_point": "visible_surface_median (eroded mask, conf-filtered, per-axis median of back-projected points)",
                "observation_status": "observed" if lifted else "not_lifted", "position": (x["xyz"] if lifted else None), "xyz_cam": (x["xc"] if lifted else None), "depth_z_m": (round(x["xc"][2], 3) if lifted else None), "range_m": (x["range"] if lifted else None),
                "uncertainty": {"depth_iqr_rel": x.get("depth_iqr_rel"), "bound_m": (round(x["range"] * x.get("depth_iqr_rel", 0), 3) if lifted and x.get("depth_iqr_rel") is not None else None), "xyz_std_m": None},
                "mask_px": x.get("n_px"), "seg_prob": round(float(x["prob"]), 3), "hand_overlap": x["hand_overlap"], "touches_border": x.get("border"), "depth_iqr_rel": x.get("depth_iqr_rel")},
                entities=ent(n, iid), derived=[E(f"cam{fi:04d}"), calib_eid], flags=([] if lifted else ["NOT_LIFTED"])))
    iv_eid = {}
    for n, o in objs.items():
        iid = o["iid"]; key = f"{cfg.slug(o.get('track_name', n))}#{iid.split('#')[-1]}"
        for k, iv in enumerate(o["ivs"]):
            e = E(f"{key}/static{k}"); iv_eid[(n, k)] = e
            recs.append(rec(f"{key}/static{k}", "object_position_interval", iv["t0"], iv["t1"], {
                "object": n, "instance_id": f"geo3d:{sid}:{iid}", "status": "static", "frame_id": WF, "unit": "m", "xyz_world": iv["xyz"], "position": iv["xyz"], "representative_point": "median of per-frame visible_surface_median over the interval",
                "observation_status": "observed", "uncertainty": {"xyz_std_m": iv["std_m"]}, "xyz_std_m": iv["std_m"], "n_frames": iv["n"], "visible_frames_total": len(o["rows"]),
                "observation_refs": [obs_eid.get((iid, iv["fi0"])), obs_eid.get((iid, iv["fi1"]))], "fixture_id": None, "fixture_kind": None, "fixture_status": None, "fixture_confidence": None,
                "rest_tolerance": {"time_pad_s": cfg.REST_PAD, "radius_m": cfg.STATIC_R}},
                entities=ent(n, iid), derived=[x for x in (obs_eid.get((iid, iv["fi0"])), obs_eid.get((iid, iv["fi1"]))) if x], flags=(["MULTI_INSTANCE"] if n in {c["name"] for j, c in inst_all.items() if j != iid} else [])))
    for mv in moves:
        n = mv["object"]; iid = objs[n]["iid"]; key = f"{cfg.slug(objs[n].get('track_name', n))}#{iid.split('#')[-1]}/move{mv['k']}"; mv["eid"] = E(key)
        kind = "object_location_transition" if mv["is_transition"] else "object_move"
        der = [iv_eid[(n, mv["start_iv"])]] if mv["start_iv"] is not None else []
        der += [iv_eid[(n, mv["end_iv"])]] if mv["end_iv"] is not None else []
        recs.append(rec(key, kind, mv["t_start"], mv["t_end"], {
            "object_name": n, "instance_id": f"geo3d:{sid}:{iid}", "label": mv["label"], "frame_id": WF, "unit": "m", "association_id": None, "track_id": f"geo3d:{sid}:{iid}",
            "from_fixture": None, "to_fixture": None, "from_fixture_kind": None, "to_fixture_kind": None, "fixture_status": None,
            "start_xyz": mv["start_xyz"], "end_xyz": mv["end_xyz"], "start_interval_ref": (iv_eid[(n, mv["start_iv"])] if mv["start_iv"] is not None else None), "end_interval_ref": (iv_eid[(n, mv["end_iv"])] if mv["end_iv"] is not None else None),
            "displacement_m": mv["displacement_m"], "is_transition": mv["is_transition"], "relation_type": "observed_transition" if mv["is_transition"] else "observed_motion",
            "gap_s": mv["gap_s"], "n_obs_in_gap": mv["n_obs_in_gap"], "hand_frames_in_gap": mv["hand_frames"], "segmentation_rule": f"consecutive static intervals (>= {cfg.STATIC_MIN_S} s, radius {cfg.STATIC_R} m) of the same tracked instance whose positions differ by >= {cfg.STATIC_R} m; t_start = end of the earlier interval, t_end = start of the later one; transition if displacement >= {cfg.MOVE_MIN_DISP} m; path in between is NOT observed (no interpolation)",
            "trigger": mv["trigger"]}, entities=ent(n, iid), derived=der, flags=(["ENDPOINT_MISSING"] if mv["start_xyz"] is None or mv["end_xyz"] is None else [])))
    for i, r in enumerate(rels):
        n_ans = r["answer_object"].split(" -> ")[0]; iid = objs[n_ans]["iid"]; names = [n_ans] + ([r["reference_object"]] if r.get("reference_object") else []) + [w for w in r.get("wrong", []) if w in objs]
        basis = {n: {"status": r["basis"][n]["status"], "interval_ref": iv_eid.get((n, r["basis"][n]["iv"])), "std_m": r["basis"][n]["std_m"]} for n in names if n in r["basis"]}
        ego = r["relation"] in ("side_left", "side_right", "ego_behind", "ego_sector")
        qf = ({"type": "camera_at_time", "frame_id": WF, "reference_timestamp": r["T"], "camera_frame_index": r.get("camera_frame_index"), "camera_pose_ref": E(f"cam{r['camera_frame_index']:04d}"),
               "axes": "camera forward = +z, left = -x; bearing 0 = forward, positive = left", "projection": "camera_axes (horizontal bearing stored alongside for ego_sector)"} if ego
              else {"type": "world", "frame_id": WF, "reference_timestamp": r["T"], "camera_frame_index": None, "camera_pose_ref": None, "axes": "frame-0 camera axes, metres", "projection": None})
        val = {"relation": r["relation"], "relation_definition": DEF[r["relation"]], "anchor_kind": r["anchor_kind"], "anchor_source": r["kind"], "anchor_time_sec": r["T"], "window": [w0, w1],
               "anchor_event_ref": (next((m["eid"] for m in moves if (m["object"], m["k"]) == r.get("move_k")), None) if r.get("move_k") else None),
               "reference_object": r.get("reference_object"), "answer_object": r["answer_object"], "verified_wrong_answers": r.get("wrong", []), "absent_in_window": None,
               "instance_ids": {n: f"geo3d:{sid}:{objs[n]['iid']}" for n in names if n in objs}, "candidate_set": {"names": names, "completeness": "tracked_prompts_only (objects named by the Gemini probe and tracked by SAM3)"},
               "d_gold_m": r.get("d_gold_m"), "margin_m": r.get("margin_m"), "lateral_gold_m": r.get("lateral_gold_m"), "side_mode": (r["relation"].replace("side_", "") if r["relation"].startswith("side_") else None),
               "distance_type": "center_3d", "query_frame": qf, "frame_of_reference": frame_of_reference(r["relation"], r.get("reference_object"), r["T"]), "position_basis": basis, "rest_tolerance": {"time_pad_s": cfg.REST_PAD, "radius_m": cfg.STATIC_R},
               "anchor_sound_label": None, "frame": (f"camera (device frame at anchor time, world {WF})" if ego else f"world (DA3 metric estimate, {WF})"), "original_subtype": None, "fact_id": f"geo3d:{sid}:{i}", "anchor_note": r["note"]}
        for k in ("near_threshold_m", "buffer_m", "uncertainty_m", "tolerance_m", "forward_gold_m", "sector", "sector_candidates", "bearing_deg", "bearing_horizontal_deg", "angle_margin_deg"):
            if k in r: val[k] = r[k]
        der = [b["interval_ref"] for b in basis.values() if b.get("interval_ref")] + ([qf["camera_pose_ref"]] if ego else [])
        rkey = f"rel/{r['relation']}/{r['T']:.3f}/{cfg.slug(r.get('reference_object') or '-')}/{cfg.slug(r['answer_object'])}" + (f"/{cfg.slug(r['sector'])}" if r.get("sector") else "")
        r["eid"] = E(rkey)
        recs.append(rec(rkey, "spatial_relation", r["T"], r["T"], val, entities=ent(n_ans, iid), derived=der,
                        flags=r["flags"] + (["LAST_SEEN_BASIS"] if any(b["status"] != "observed" for b in basis.values()) else [])))
    bad = [(x["evidence_id"], schema.validate_evidence(x)) for x in recs if schema.validate_evidence(x)]
    assert not bad, bad[:3]
    return recs, frame_eid, calib_eid, obs_eid, iv_eid


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--samples", nargs="*", default=["all"]); ap.add_argument("--no-gemini", action="store_true"); a = ap.parse_args()
    for s in cfg.samples(a.samples):
        cd = cfg.clip_dir(s["sample_id"])
        if not (cd / "sam3" / "tracks.json").exists() or not (cd / "da3" / "meta.json").exists():
            print("missing da3/sam3:", s["sample_id"]); continue
        da3 = load_da3(cd); frames = cfg.load_frames(cd)["frames"]; tracks = load_tracks(cd); cents = centroids(cd, da3, tracks)
        # 质量(位姿)
        pairs1 = Q.depth_pairs(da3, 1); pf = Q.per_frame(da3, frames, pairs1); dg1 = Q.summarize_pairs(pairs1, 1); ps = Q.pose_sanity(da3, frames)
        # 别名
        aliases, parts, alog = AL.detect(cents, tracks, cd, frames, s, use_gemini=not a.no_gemini)
        alias_names = AL.merge_names(cents, aliases, parts, alog)          # 名字级:{alias_name: canonical_name}
        inst_all = {}
        for iid, c in cents.items():
            if iid in aliases: continue
            inst_all[iid] = {**c, "track_name": c["name"], "name": alias_names.get(c["name"], c["name"])}
        # 每个名字取帧数最多的实例;multi = 同名两实例共视 ≥ 3 s
        by_name = {}
        for iid, c in inst_all.items():
            if c["name"] not in by_name or len(c["rows"]) > len(inst_all[by_name[c["name"]]]["rows"]): by_name[c["name"]] = iid
        multi = set()
        for iid, c in inst_all.items():
            cn = by_name[c["name"]]
            if iid != cn and len({x["fi"] for x in c["rows"]} & {x["fi"] for x in inst_all[cn]["rows"]}) >= int(3 * cfg.FPS): multi.add(c["name"])
        objs = {n: {"iid": iid, "track_name": inst_all[iid]["track_name"], "rows": inst_all[iid]["rows"], "ivs": static_intervals(inst_all[iid]["rows"])} for n, iid in by_name.items()}
        ar = Q.arm_reach(s, objs)
        qual = Q.clip_level(frames, pf, dg1, ps, ar); qual["quality"] = {"depth_gap1": dg1, "pose": ps, "arm_reach": ar}
        match = make_matcher(list(objs), alias_names)
        if qual["pose_valid"]:
            moves = derive_moves(s, objs, match); rels = derive_relations(s, cd, da3, objs, match, moves, qual)
        else:
            moves, rels = [], []
            for o in objs.values(): o["ivs"] = []
        H, W = da3["meta"]["frame_hw"]; h, w = da3["meta"]["proc_hw"]
        calib = {"camera_model": "pinhole_assumed", "K_source": "Depth Anything 3 estimate (principal point fixed at centre: cx = W/2, cy = H/2)", "K_proc": np.round(da3["K"][0], 3).tolist(), "K_frame": np.round(da3["K_frame"][0], 3).tolist(),
                 "proc_hw": [h, w], "frame_hw": [H, W], "source_resolution_hw": [1080, 1920], "resize_transform": f"source 1920x1080 -> ffmpeg scale width {W} -> DA3 upper_bound_resize {cfg.DA3_RES} (K_proc at proc_hw; K_frame = S @ K_proc)",
                 "distortion": "unknown (GoPro wide-angle, not rectified; treated as pinhole)", "rectified": False, "parameter_source": "model_estimate", "per_frame_K": True}
        recs, frame_eid, calib_eid, obs_eid, iv_eid = emit_records(s, cd, da3, frames, qual, pf, calib, inst_all, objs, aliases, parts, moves, rels, tracks)
        for n, o in objs.items():
            for k, iv in enumerate(o["ivs"]): iv["eid"] = iv_eid[(n, k)]
            for x in o["rows"]: x["obs_eid"] = obs_eid.get((o["iid"], x["fi"]))
        pos = {"sample_id": s["sample_id"], "world_frame": {"name": f"frame0_cam:{s['sample_id']}", **da3["ref"]}, "frame_eid": frame_eid, "calib_eid": calib_eid, "quality": qual, "per_frame_quality": pf,
               "aliases": aliases, "alias_names": alias_names, "parts": parts, "alias_log": alog, "calibration": calib,
               "objects": {n: {"iid": o["iid"], "track_name": o["track_name"], "iid_full": f"geo3d:{s['sample_id']}:{o['iid']}", "eid_inst": evidence_id("egoplan", s["video_id"], "geo3d", f"{s['sample_id']}/inst/{cfg.slug(o['track_name'])}#{o['iid'].split('#')[-1]}"),
                               "n_rows": len(o["rows"]), "intervals": o["ivs"], "rows": o["rows"]} for n, o in objs.items()},
               "multi_instance": sorted(multi), "moves": moves,
               "relations": [{k: v for k, v in r.items() if k != "basis"} | {"basis": {n: {"status": b["status"], "iv": b["iv"], "std_m": b["std_m"]} for n, b in r["basis"].items()}} for r in rels]}
        (cd / "positions.json").write_text(json.dumps(pos, indent=1, ensure_ascii=False))
        with open(cd / "records.jsonl", "w") as f:
            for r in recs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        kinds = collections.Counter(r["kind"] for r in recs); rt = collections.Counter(r["relation"] for r in rels)
        print(f"{s['scenario']:12s} pose_valid {qual['pose_valid']} scale {qual['scale_status']} | objects {len(objs)} aliases {len(aliases)} parts {len(parts)} multi {sorted(multi)} | intervals {sum(len(o['ivs']) for o in objs.values())} moves {len(moves)} ({sum(m['is_transition'] for m in moves)} transitions) | relations {dict(rt)} | records {dict(kinds)}", flush=True)


if __name__ == "__main__":
    main()
