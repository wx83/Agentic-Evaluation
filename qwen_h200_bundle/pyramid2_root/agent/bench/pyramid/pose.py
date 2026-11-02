"""相机 6DoF 轨迹:从 HD-EPIC 的 SLAM zip 定向提取 -> 10 Hz -> mp4 秒。

产物 output/pyramid*/data/pose_<video>.json 是**确定性可重建的输入数据**,不是派生 gold:
文件里记下源 zip 路径、成员 CRC、时钟偏移与重采样率,`--verify` 能原样重建并比对。
verify.py 加载同一份 cache 后独立重算几何 —— 与它重新调用 PRIM.find_easy 是同构的。

device frame 的轴向是**实测定出来的**,不是照搬文档(P08,397 个 movement + 3083 个行走采样):
  +Z = 前   行走方向在 Z 上 mean=+0.357(三轴最大,且 Z 非上轴)
  -Y = 右   被操作物体 lateral mean=-0.32(右手操作),同号率 97%
  +X = 下   世界「上」方向在 X 上 mean=-0.845,**同号率 100%**
交叉验证:被操作物体落在 (+0.34, -0.32, +0.31) = 下 34 / 右 32 / 前 31 cm,
正是右手在身前台面操作的姿态;由重力分量反推低头约 24 度(看台面),吻合。
"""
import json, subprocess, re, bisect
import numpy as np
import pconfig as P
import config as C

SLAM_ROOT = "/mnt/data_new/hd-epic/SLAM-and-Gaze"
# 相机轨迹是**输入数据**,不是某次实验的派生产物 —— 放共享目录,
# 不随 PYRAMID_SEED / PYRAMID_SMOKE 分叉(否则每棵树都要重解一遍 5 GB zip)。
POSE_DIR = C.OUT / "_shared" / "pose"
HZ = 10.0                  # 重采样率(原始约 1.1 kHz)
POSE_VERSION = 1


def _slam_member(video):
    """(zip 路径, 成员名, 成员 CRC) —— <N> 取自同目录的 vrs_to_multi_slam.json。"""
    part = video.split("-")[0]
    mapf = f"{SLAM_ROOT}/{part}/SLAM/multi/vrs_to_multi_slam.json"
    m = json.loads(open(mapf).read())
    n = m.get(f"{part}/{video}.vrs")
    if n is None:
        raise KeyError(f"{video} 不在 {mapf} 里")
    z = f"{SLAM_ROOT}/{part}/SLAM/multi/{n}.zip"
    member = f"{n}/slam/closed_loop_trajectory.csv"
    out = subprocess.run(["unzip", "-v", z, member], capture_output=True, text=True).stdout
    crc = ""
    for line in out.splitlines():
        if member in line:
            parts = line.split()
            if len(parts) >= 7:
                crc = parts[6]
    return z, member, crc


def _clock_offset(video):
    """vrs_device_time - mp4_time,实测是常数(P08 std 仅 9.6 ms)。"""
    part = video.split("-")[0]
    f = C.HDEPIC / "videos" / part / f"{video}_mp4_to_vrs_time_ns.csv"
    mp4, vrs = [], []
    with open(f) as fh:
        next(fh)
        for i, line in enumerate(fh):
            if i % 50:
                continue
            a = line.split(",")
            mp4.append(float(a[0]) / 1e9)
            vrs.append(float(a[2]) / 1e9)
    d = np.array(vrs) - np.array(mp4)
    return float(d.mean()), float(d.std())


def build(video, force=False):
    """提取并缓存。返回 pose dict。"""
    POSE_DIR.mkdir(parents=True, exist_ok=True)
    f = POSE_DIR / f"pose_{video}.json"
    if f.exists() and not force:
        d = json.loads(f.read_text())
        if d.get("pose_version") == POSE_VERSION:
            return d
    z, member, crc = _slam_member(video)
    off, off_std = _clock_offset(video)
    step = max(1, int(round(1100.0 / HZ)))      # 原始约 1.1 kHz
    awk = (r"NR==1{next} NR%%%d==0 {print $2, $4, $5, $6, $7, $8, $9, $10, $20}" % step)
    p = subprocess.run(f"unzip -p {z} '{member}' | awk -F, '{awk}'",
                       shell=True, capture_output=True, text=True)
    rows = [l.split() for l in p.stdout.splitlines() if l.strip()]
    assert len(rows) > 1000, f"{video} 轨迹抽取失败(仅 {len(rows)} 行)"
    a = np.array(rows, dtype=float)
    d = {"pose_version": POSE_VERSION, "video_id": video,
         "source_zip": z, "source_member": member, "source_crc": crc,
         "clock_offset_sec": round(off, 6), "clock_offset_std_sec": round(off_std, 6),
         "resample_hz": HZ, "n": len(a),
         "t": [round(x / 1e6 - off, 4) for x in a[:, 0]],     # -> mp4 秒
         "pos": [[round(v, 5) for v in r] for r in a[:, 1:4]],
         "quat": [[round(v, 6) for v in r] for r in a[:, 4:8]],  # qx,qy,qz,qw
         "q": [round(v, 2) for v in a[:, 8]]}
    f.write_text(json.dumps(d))
    return d


_CACHE = {}


def load(video):
    if video not in _CACHE:
        d = build(video)
        d["_t"] = np.asarray(d["t"])
        d["_pos"] = np.asarray(d["pos"])
        d["_quat"] = np.asarray(d["quat"])
        d["_q"] = np.asarray(d["q"])
        _CACHE[video] = d
    return _CACHE[video]


def R_of(q):
    """四元数 (qx,qy,qz,qw) -> 世界<-device 旋转矩阵。"""
    x, y, z, w = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w),     2 * (x * z + y * w)],
        [2 * (x * y + z * w),     1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w),     2 * (y * z + x * w),     1 - 2 * (x * x + y * y)]])


MAX_DT = 0.2          # 与最近采样点的时间差上限
STAB_WIN = 0.5        # 稳定性检查窗口(秒)
STAB_MOVE = 0.25      # 该窗口内相机位移上限(米)
MIN_QUALITY = 0.5


def at(video, T):
    """T 时刻(mp4 秒)的相机位姿,要求采样够近、质量达标、且前后 0.5 s 内相机没大动。

    「我的左边」只在相机稳定时才有确定所指 —— 边走边转的时刻不出题。
    返回 (cam_xyz, R) 或 None。
    """
    d = load(video)
    t = d["_t"]
    i = int(np.clip(np.searchsorted(t, T), 1, len(t) - 1))
    if i and abs(t[i - 1] - T) < abs(t[i] - T):
        i -= 1
    if abs(t[i] - T) > MAX_DT or d["_q"][i] < MIN_QUALITY:
        return None
    lo = bisect.bisect_left(d["t"], T - STAB_WIN)
    hi = bisect.bisect_right(d["t"], T + STAB_WIN)
    if hi - lo < 5:
        return None
    seg = d["_pos"][lo:hi]
    if float(np.linalg.norm(seg.max(0) - seg.min(0))) > STAB_MOVE:
        return None
    return d["_pos"][i], R_of(d["_quat"][i])


def to_device(cam, R, xyz):
    """世界坐标 -> device frame。返回 (forward, lateral, down, range)。

    forward = +Z(前)   lateral = +Y(左) / -Y(右)   down = +X(下)
    """
    v = R.T @ (np.asarray(xyz) - cam)
    return float(v[2]), float(v[1]), float(v[0]), float(np.linalg.norm(v))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--verify", action="store_true", help="重建并比对 CRC / 偏移 / 行数")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    for v in P.VIDEOS:
        if a.verify:
            old = json.loads((POSE_DIR / f"pose_{v}.json").read_text())
            z, member, crc = _slam_member(v)
            off, _ = _clock_offset(v)
            ok = (crc == old["source_crc"]
                  and abs(off - old["clock_offset_sec"]) < 1e-3
                  and z == old["source_zip"])
            print(f"{v[:3]}  CRC {'一致' if crc == old['source_crc'] else '不符'}  "
                  f"offset {old['clock_offset_sec']:.3f}s  n={old['n']}  -> {'OK' if ok else '异常'}")
        else:
            d = build(v, force=a.force)
            print(f"{v[:3]}  n={d['n']:6d}  offset={d['clock_offset_sec']:.3f}s "
                  f"(std {d['clock_offset_std_sec']*1000:.1f}ms)  crc={d['source_crc']}", flush=True)
