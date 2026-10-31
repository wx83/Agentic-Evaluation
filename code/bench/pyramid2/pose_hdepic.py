#!/usr/bin/env python3
"""HD-EPIC 相机 6DoF 轨迹(移植自 agent/bench/pyramid/pose.py,10-27):SLAM zip 定向抽取 closed_loop_trajectory.csv -> 10 Hz -> mp4 秒。
缓存与旧管线共用 output/_shared/pose/pose_<video>.json(同格式 pose_version 1,已有的 6 个直接复用)。
视频 -> zip:SLAM/multi/vrs_to_multi_slam.json;不在里面的试 SLAM/other_aligned/<video>.zip。
时钟偏移:video/<P>/<video>_mp4_to_vrs_time_ns.csv(vrs_device_time - mp4_time,常数,std ~10 ms)。
device frame 轴向(旧管线实测):+Z 前、+Y 左 / -Y 右、+X 下。
用法:python3 pose_hdepic.py build <video>...   |   python3 pose_hdepic.py build --all-hdepic-e"""
import json, subprocess, bisect, sys
from pathlib import Path
import numpy as np

SLAM_ROOT = Path("/mnt/data_new/hd-epic/SLAM-and-Gaze")
VIDEO_ROOT = Path("/mnt/data_new/hd-epic/video")
POSE_DIR = Path("/mnt/work_new/weihanxu/output/_shared/pose")
HZ = 10.0
POSE_VERSION = 1


def _slam_member(video):
    part = video.split("-")[0]
    mapf = SLAM_ROOT / part / "SLAM" / "multi" / "vrs_to_multi_slam.json"
    n = json.loads(mapf.read_text()).get(f"{part}/{video}.vrs") if mapf.exists() else None
    if n is not None:
        z = SLAM_ROOT / part / "SLAM" / "multi" / f"{n}.zip"; member = f"{n}/slam/closed_loop_trajectory.csv"
    else:
        z = SLAM_ROOT / part / "SLAM" / "other_aligned" / f"{video}.zip"; member = f"{video}/slam/closed_loop_trajectory.csv"
        if not z.exists():
            raise KeyError(f"{video}: no SLAM zip (not in vrs_to_multi_slam.json, no other_aligned)")
    out = subprocess.run(["unzip", "-v", str(z), member], capture_output=True, text=True).stdout
    crc = ""
    for line in out.splitlines():
        if member in line:
            parts = line.split()
            if len(parts) >= 7: crc = parts[6]
    return str(z), member, crc


def _clock_offset(video):
    part = video.split("-")[0]
    f = VIDEO_ROOT / part / f"{video}_mp4_to_vrs_time_ns.csv"
    mp4, vrs = [], []
    with open(f) as fh:
        next(fh)
        for i, line in enumerate(fh):
            if i % 50: continue
            a = line.split(",")
            mp4.append(float(a[0]) / 1e9); vrs.append(float(a[2]) / 1e9)
    d = np.array(vrs) - np.array(mp4)
    return float(d.mean()), float(d.std())


def build(video, force=False):
    POSE_DIR.mkdir(parents=True, exist_ok=True)
    f = POSE_DIR / f"pose_{video}.json"
    if f.exists() and not force:
        d = json.loads(f.read_text())
        if d.get("pose_version") == POSE_VERSION: return d
    z, member, crc = _slam_member(video)
    off, off_std = _clock_offset(video)
    step = max(1, int(round(1100.0 / HZ)))
    awk = (r"NR==1{next} NR%%%d==0 {print $2, $4, $5, $6, $7, $8, $9, $10, $20}" % step)
    p = subprocess.run(f"unzip -p '{z}' '{member}' | awk -F, '{awk}'", shell=True, capture_output=True, text=True)
    rows = [l.split() for l in p.stdout.splitlines() if l.strip()]
    assert len(rows) > 1000, f"{video}: trajectory extraction failed ({len(rows)} rows)"
    a = np.array(rows, dtype=float)
    d = {"pose_version": POSE_VERSION, "video_id": video, "source_zip": z, "source_member": member, "source_crc": crc,
         "clock_offset_sec": round(off, 6), "clock_offset_std_sec": round(off_std, 6), "resample_hz": HZ, "n": len(a),
         "t": [round(x / 1e6 - off, 4) for x in a[:, 0]], "pos": [[round(v, 5) for v in r] for r in a[:, 1:4]],
         "quat": [[round(v, 6) for v in r] for r in a[:, 4:8]], "q": [round(v, 2) for v in a[:, 8]]}
    f.write_text(json.dumps(d))
    return d


_CACHE = {}


def available(video):
    return (POSE_DIR / f"pose_{video}.json").exists()


def load(video):
    if video not in _CACHE:
        d = build(video)
        d["_t"] = np.asarray(d["t"]); d["_pos"] = np.asarray(d["pos"]); d["_quat"] = np.asarray(d["quat"]); d["_q"] = np.asarray(d["q"])
        _CACHE[video] = d
    return _CACHE[video]


def R_of(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


MAX_DT, STAB_WIN, STAB_MOVE, MIN_QUALITY = 0.2, 0.5, 0.25, 0.5


def at(video, T):
    """T(mp4 秒)时刻的 (cam_xyz, R_world_device);采样不够近 / 质量差 / 前后 0.5 s 内相机移动 > 0.25 m 时 None。"""
    d = load(video); t = d["_t"]
    i = int(np.clip(np.searchsorted(t, T), 1, len(t) - 1))
    if i and abs(t[i - 1] - T) < abs(t[i] - T): i -= 1
    if abs(t[i] - T) > MAX_DT or d["_q"][i] < MIN_QUALITY: return None
    lo = bisect.bisect_left(d["t"], T - STAB_WIN); hi = bisect.bisect_right(d["t"], T + STAB_WIN)
    if hi - lo < 5: return None
    seg = d["_pos"][lo:hi]
    if float(np.linalg.norm(seg.max(0) - seg.min(0))) > STAB_MOVE: return None
    return d["_pos"][i], R_of(d["_quat"][i])


def to_device(cam, R, xyz):
    """世界 -> device frame:(forward=+Z, lateral=+Y 左 / -Y 右, down=+X, range)。"""
    v = R.T @ (np.asarray(xyz, dtype=float) - cam)
    return float(v[2]), float(v[1]), float(v[0]), float(np.linalg.norm(v))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "build":
        vids = args[1:]
        if vids == ["--all-hdepic-e"]:
            sys.path.insert(0, str(Path(__file__).parent))
            from adapters.hdepic_methode import load_samples
            vids = sorted({s["video_id"] for s in load_samples()})
        for v in vids:
            try:
                d = build(v)
                print(f"{v}  n={d['n']:6d}  offset={d['clock_offset_sec']:.3f}s (std {d['clock_offset_std_sec'] * 1000:.1f} ms)", flush=True)
            except Exception as ex:
                print(f"{v}  FAILED: {ex}", flush=True)
