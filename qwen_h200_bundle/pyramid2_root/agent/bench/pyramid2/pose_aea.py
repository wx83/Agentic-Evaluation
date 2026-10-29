#!/usr/bin/env python3
"""AEA 设备 6DoF 轨迹(10-27,与 pose_hdepic 同 API:at / to_device / available):官方 MPS closed_loop_trajectory.csv -> 10 Hz -> SAVVY 视频秒。
时间:z = device 秒 − 第一帧 RGB 的 device 时刻(data/aea_p_samples.json 的 rgb_t0 = legacy narration t0 = VRS RGB 首帧,已核对一致)。
轴向(10-27 实测):Aria device frame 的 +Z 相对 RGB 光轴低头约 38°,所以这里不用 device 轴,而用「RGB 相机规范系」canon:
  列 = [down, left, forward](RGB 相机 +Y / -X / +Z 在 device 系的方向,由 frames.json 的 T_world_cam 与 closed-loop 位姿求得,存在缓存 R_device_canon);
  at() 返回 R_world_canon = R_world_device @ R_device_canon,于是 to_device / l3ext._bearing 的「R@[0,0,1] = 前、R@[0,1,0] = 左」成立;世界 z 向上。
缓存 output/_shared/pose/pose_<rec>.json(pose_version 1,字段同 pose_hdepic)。
用法:python3 pose_aea.py build <rec>...   |   python3 pose_aea.py check <rec> <z> <x> <y> <z3d>(打印某时刻某点的 device 系方位)"""
import json, bisect, sys, csv
from pathlib import Path
import numpy as np
import pose_hdepic as PH

AEA = Path("/mnt/data_new/AEA")
POSE_DIR = PH.POSE_DIR
HZ = 10.0
POSE_VERSION = 1


def rgb_t0(rec):
    import p2config as P
    f = P.DATA / "aea_p_samples.json"
    if f.exists():
        for s in json.loads(f.read_text())["samples"]:
            if s["video_id"] == rec: return float(s["rgb_t0"])
    fj = Path(f"/mnt/work_new/weihanxu/experiments/aea_protocol/sam3_fixtures/frames/{rec}/frames.json")
    if fj.exists(): return float(json.loads(fj.read_text())["rgb_t0_device"])
    raise KeyError(f"{rec}: no rgb_t0 (samples / frames.json)")


def build(rec, force=False):
    POSE_DIR.mkdir(parents=True, exist_ok=True)
    f = POSE_DIR / f"pose_{rec}.json"
    if f.exists() and not force:
        d = json.loads(f.read_text())
        if d.get("pose_version") == POSE_VERSION: return d
    src = AEA / rec / "mps/slam/closed_loop_trajectory.csv"
    t0 = rgb_t0(rec); step = max(1, int(round(1000.0 / HZ))); rows = []
    with open(src) as fh:
        rd = csv.reader(fh); head = next(rd)
        ci = {k: head.index(k) for k in ("tracking_timestamp_us", "tx_world_device", "ty_world_device", "tz_world_device", "qx_world_device", "qy_world_device", "qz_world_device", "qw_world_device", "quality_score")}
        for i, r in enumerate(rd):
            if i % step: continue
            rows.append([float(r[ci[k]]) for k in ci])
    assert len(rows) > 100, f"{rec}: trajectory extraction failed ({len(rows)} rows)"
    a = np.array(rows, dtype=float)
    Rdc = _canon_from_frames(rec, a, t0)
    d = {"pose_version": POSE_VERSION, "video_id": rec, "source_zip": str(src), "source_member": "closed_loop_trajectory.csv", "source_crc": "",
         "clock_offset_sec": round(t0, 6), "clock_offset_std_sec": 0.0, "resample_hz": HZ, "n": len(a), "R_device_canon": np.round(Rdc, 6).tolist(),
         "t": [round(x / 1e6 - t0, 4) for x in a[:, 0]], "pos": [[round(v, 5) for v in r] for r in a[:, 1:4]],
         "quat": [[round(v, 6) for v in r] for r in a[:, 4:8]], "q": [round(v, 2) for v in a[:, 8]]}
    f.write_text(json.dumps(d))
    return d


def _canon_from_frames(rec, a, t0):
    """R_device_canon:列 = RGB 相机(旋正线性针孔)的 +Y(down)/ -X(left)/ +Z(forward)在 device 系的方向;用 frames.json 的 T_world_cam 对 closed-loop 位姿求平均。"""
    fj = Path(f"/mnt/work_new/weihanxu/experiments/aea_protocol/sam3_fixtures/frames/{rec}/frames.json")
    if not fj.exists():
        print(f"[pose_aea] {rec}: no frames.json -> R_device_canon = identity (device axes)", file=sys.stderr); return np.eye(3)
    F = json.loads(fj.read_text()); t = a[:, 0] / 1e6 - t0; Rs = []
    for fr in F["frames"][::10]:
        i = int(np.argmin(np.abs(t - fr["z"])))
        if abs(t[i] - fr["z"]) > 0.15: continue
        Rwd = R_of(a[i, 4:8]); Rwc = np.array(fr["T_world_cam"])[:3, :3]; Rs.append(Rwd.T @ Rwc)
    U, _, Vt = np.linalg.svd(np.mean(Rs, 0)); Rdc = U @ Vt
    return np.stack([Rdc[:, 1], -Rdc[:, 0], Rdc[:, 2]], axis=1)      # columns: down, left, forward


_CACHE = {}


def available(rec):
    return (POSE_DIR / f"pose_{rec}.json").exists() or (AEA / rec / "mps/slam/closed_loop_trajectory.csv").exists()


def load(rec):
    if rec not in _CACHE:
        d = build(rec)
        d["_t"] = np.asarray(d["t"]); d["_pos"] = np.asarray(d["pos"]); d["_quat"] = np.asarray(d["quat"]); d["_q"] = np.asarray(d["q"]); d["_Rdc"] = np.asarray(d.get("R_device_canon") or np.eye(3))
        _CACHE[rec] = d
    return _CACHE[rec]


R_of = PH.R_of
MAX_DT, STAB_WIN, STAB_MOVE, MIN_QUALITY = PH.MAX_DT, PH.STAB_WIN, PH.STAB_MOVE, PH.MIN_QUALITY


def at(rec, T):
    """T(SAVVY 视频秒)时刻的 (cam_xyz, R_world_device);采样不够近 / 质量差 / 前后 0.5 s 内移动 > 0.25 m 时 None(规则同 pose_hdepic)。"""
    d = load(rec); t = d["_t"]
    i = int(np.clip(np.searchsorted(t, T), 1, len(t) - 1))
    if i and abs(t[i - 1] - T) < abs(t[i] - T): i -= 1
    if abs(t[i] - T) > MAX_DT or d["_q"][i] < MIN_QUALITY: return None
    lo = bisect.bisect_left(d["t"], T - STAB_WIN); hi = bisect.bisect_right(d["t"], T + STAB_WIN)
    if hi - lo < 5: return None
    seg = d["_pos"][lo:hi]
    if float(np.linalg.norm(seg.max(0) - seg.min(0))) > STAB_MOVE: return None
    return d["_pos"][i], R_of(d["_quat"][i]) @ d["_Rdc"]


def at_loose(rec, T):
    """不检查稳定性的位姿(声音 / 视线锚点在走动中也要方位)。"""
    d = load(rec); t = d["_t"]
    i = int(np.clip(np.searchsorted(t, T), 1, len(t) - 1))
    if i and abs(t[i - 1] - T) < abs(t[i] - T): i -= 1
    if abs(t[i] - T) > MAX_DT: return None
    return d["_pos"][i], R_of(d["_quat"][i]) @ d["_Rdc"]


to_device = PH.to_device


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "build":
        for v in args[1:]:
            d = build(v, force=True); print(f"{v}  n={d['n']}  t {d['t'][0]:.2f}..{d['t'][-1]:.2f}  rgb_t0={d['clock_offset_sec']}")
    elif args and args[0] == "check":
        rec, z = args[1], float(args[2]); xyz = [float(x) for x in args[3:6]]
        p = at_loose(rec, z); cam, R = p
        fwd, lat, down, rng = to_device(cam, R, xyz)
        import math
        print(f"z={z}: forward={fwd:.2f} lateral(+left)={lat:.2f} down={down:.2f} range={rng:.2f} bearing={math.degrees(math.atan2(lat, fwd)):.1f} deg (0 = front, + = left)")
