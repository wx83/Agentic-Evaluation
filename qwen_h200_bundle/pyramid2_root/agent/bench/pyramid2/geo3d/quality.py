"""位姿 / 深度质量与尺度状态(10-15 spec §5.2 / §4.4):
  depth_pairs(da3, gap)     每对 (i, i+gap) 的深度自洽相对误差中位(帧 i 反投影 → 帧 i+gap 重投影,与该帧预测深度比);eval.depth_consistency 的逐对版本
  per_frame(da3, frames)    每帧 {depth_rel_err_next, speed_mps, rot_deg_per_s, valid}
  clip_level(da3, frames, arm_reach, depth_gap1)  {pose_valid, pose_valid_interval, scale_status, scale_check, reasons}
scale_status 只有 metric_estimated / metric_suspect 两档:DA3 的米制尺度是模型估计,这里从不写 metric_verified。"""
import numpy as np
from . import cfg


def depth_pairs(da3, gap=1, step=4, central=0.8):
    """-> {i: median_rel_err}(只含有效帧对)。"""
    D, C, K, w2c, c2w = da3["depth"], da3["conf"], da3["K"], da3["w2c"], da3["c2w"]; N, h, w = D.shape
    m0 = int(h * (1 - central) / 2); m1 = int(w * (1 - central) / 2)
    vv, uu = np.mgrid[m0:h - m0:step, m1:w - m1:step]; vv = vv.ravel(); uu = uu.ravel()
    out = {}
    for i in range(0, N - gap):
        j = i + gap; d = D[i, vv, uu]; ok = np.isfinite(d) & (d > 0.05) & (C[i, vv, uu] >= np.percentile(C[i], 30))
        if ok.sum() < 50: continue
        fx, fy, cx, cy = K[i][0, 0], K[i][1, 1], K[i][0, 2], K[i][1, 2]
        X = np.stack([(uu[ok] - cx) / fx * d[ok], (vv[ok] - cy) / fy * d[ok], d[ok], np.ones(ok.sum())])
        Xj = (w2c[j] @ c2w[i]) @ X; z = Xj[2]
        fxj, fyj, cxj, cyj = K[j][0, 0], K[j][1, 1], K[j][0, 2], K[j][1, 2]
        u2 = fxj * Xj[0] / np.maximum(z, 1e-6) + cxj; v2 = fyj * Xj[1] / np.maximum(z, 1e-6) + cyj
        inb = (z > 0.05) & (u2 >= 0) & (u2 < w - 1) & (v2 >= 0) & (v2 < h - 1)
        if inb.sum() < 50: continue
        dj = D[j, np.round(v2[inb]).astype(int), np.round(u2[inb]).astype(int)]
        out[i] = float(np.median(np.abs(z[inb] - dj) / np.maximum(dj, 1e-6)))
    return out


def summarize_pairs(pairs, gap):
    errs = np.array(list(pairs.values()))
    return {"gap": gap, "n_pairs": int(len(errs)), "median_rel_err": (round(float(np.median(errs)), 4) if len(errs) else None),
            "frac_pairs_le_5pct": (round(float((errs <= 0.05).mean()), 3) if len(errs) else None)}


def per_frame(da3, frames, pairs1=None):
    """每帧质量:与下一帧的深度自洽误差、相机速度、角速度;valid = 三项都在阈值内(最后一帧沿用前一对)。"""
    pairs1 = depth_pairs(da3, 1) if pairs1 is None else pairs1
    C = da3["c2w"][:, :3, 3]; R = da3["c2w"][:, :3, :3]; t = np.array([f["t_abs"] for f in frames]); N = len(frames)
    out = []
    for i in range(N):
        j = i + 1 if i + 1 < N else i - 1
        if j < 0 or j >= N:
            out.append({"frame_index": i, "depth_rel_err_next": None, "speed_mps": None, "rot_deg_per_s": None, "valid": True}); continue
        dt = max(abs(t[j] - t[i]), 1e-6); sp = float(np.linalg.norm(C[j] - C[i]) / dt)
        Rr = R[i].T @ R[j]; rot = float(np.degrees(np.arccos(np.clip((np.trace(Rr) - 1) / 2, -1, 1))) / dt)
        de = pairs1.get(min(i, j))
        valid = sp <= cfg.POSE_MAX_SPEED and rot <= cfg.POSE_MAX_ROT and (de is None or de <= cfg.PAIR_DEPTH_ERR)
        out.append({"frame_index": i, "depth_rel_err_next": (round(de, 4) if de is not None else None), "speed_mps": round(sp, 3), "rot_deg_per_s": round(rot, 1), "valid": bool(valid)})
    return out


def clip_level(frames, pf, depth_gap1, pose_sanity, arm_reach):
    """clip 级 pose_valid / scale_status。arm_reach = eval.arm_reach 的输出。"""
    reasons = []
    frac = depth_gap1.get("frac_pairs_le_5pct"); ms = pose_sanity.get("mean_speed_mps")
    pose_valid = bool(frac is not None and frac >= cfg.CLIP_DEPTH_FRAC and ms is not None and ms <= cfg.CLIP_MAX_MEAN_SPEED)
    if frac is None or frac < cfg.CLIP_DEPTH_FRAC: reasons.append(f"depth gap1 frac_le_5pct {frac} < {cfg.CLIP_DEPTH_FRAC}")
    if ms is None or ms > cfg.CLIP_MAX_MEAN_SPEED: reasons.append(f"mean speed {ms} m/s > {cfg.CLIP_MAX_MEAN_SPEED}")
    valid_t = [frames[x["frame_index"]]["t_abs"] for x in pf if x["valid"]]
    interval = [round(min(valid_t), 3), round(max(valid_t), 3)] if valid_t else None
    h = arm_reach.get("handled_median_range_lt_1m"); nr = arm_reach.get("narration_within_1m")
    score = h if h is not None else nr
    if score is None:
        scale_status, why = "metric_suspect", "no handled / narrated object to check arm reach"
    elif score >= cfg.ARM_REACH_MIN and pose_valid:
        scale_status, why = "metric_estimated", f"arm-reach check {score} >= {cfg.ARM_REACH_MIN}; depth self-consistency ok"
    else:
        scale_status, why = "metric_suspect", f"arm-reach check {score} (handled {h}, narration {nr}) or pose invalid"
    if scale_status == "metric_suspect": reasons.append(why)
    return {"pose_valid": pose_valid, "pose_valid_interval": interval, "n_valid_frames": sum(1 for x in pf if x["valid"]), "n_frames": len(pf),
            "scale_status": scale_status, "scale_check": {"method": "arm_reach", "handled_lt_1m": h, "narration_lt_1m": nr, "threshold": cfg.ARM_REACH_MIN, "note": why},
            "reasons": reasons}


def pose_sanity(da3, frames):
    C = da3["c2w"][:, :3, 3]; t = np.array([f["t_abs"] for f in frames])
    seg = np.linalg.norm(np.diff(C, axis=0), axis=1); dt = np.diff(t); sp = seg / np.maximum(dt, 1e-6)
    R = da3["c2w"][:, :3, :3]; ang = []
    for i in range(len(R) - 1):
        Rr = R[i].T @ R[i + 1]; ang.append(np.degrees(np.arccos(np.clip((np.trace(Rr) - 1) / 2, -1, 1))) / max(dt[i], 1e-6))
    return {"path_len_m": round(float(seg.sum()), 2), "mean_speed_mps": round(float(sp.mean()), 3), "max_speed_mps": round(float(sp.max()), 3),
            "frac_speed_gt_2": round(float((sp > 2).mean()), 3), "max_rot_deg_per_s": round(float(max(ang)), 1) if ang else None,
            "extent_m": [round(float(x), 2) for x in (C.max(0) - C.min(0))]}


def _stem(w):
    for suf in ("ing", "ies", "es", "ed", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf): return w[: -len(suf)]
    return w


STOP = {"the", "and", "with", "from", "into", "onto", "then", "that", "this", "his", "her", "their", "some", "one", "two", "left", "right", "hand", "hands"}


def arm_reach(s, objs):
    """尺度代理:narration 命中跟踪物体名时该时刻物体距相机 <1 m 的比例;Gemini 标 handled_by_wearer 的物体中位距离 <1 m 的比例。objs = {name: {rows}}。"""
    import re
    t0 = s["window"][0]; hits = []
    for n_ in s.get("gt_narrations") or []:
        toks = {_stem(w) for w in re.findall(r"[a-z]+", n_["text"].lower()) if w not in STOP and len(w) > 2}
        for n, o in objs.items():
            nt = {_stem(w) for w in re.findall(r"[a-z]+", n)}
            if nt and nt <= toks:
                T = t0 + n_["t"]; rows = [x for x in o["rows"] if abs(x["t"] - T) <= 1.0]
                if rows: hits.append(min(x["range"] for x in rows))
    handled = []
    for o in (s.get("gemini") or {}).get("objects") or []:
        nm = (o.get("name") or "").lower()
        if o.get("handled_by_wearer") and nm in objs:
            rr = [x["range"] for x in objs[nm]["rows"]]; handled.append(float(np.median(rr)))
    return {"narration_hits": len(hits), "narration_within_1m": (round(float(np.mean([h < 1.0 for h in hits])), 3) if hits else None),
            "handled_objects": len(handled), "handled_median_range_lt_1m": (round(float(np.mean([h < 1.0 for h in handled])), 3) if handled else None)}
