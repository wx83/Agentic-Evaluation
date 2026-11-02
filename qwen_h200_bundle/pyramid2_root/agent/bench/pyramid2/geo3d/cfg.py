"""geo3d 配置(10-14 晚):纯视频 3D 标注(DA3 深度+位姿,SAM3 文字跟踪)的路径与阈值。阈值抄自 pyramid/spatial.py / pose.py,不 import 它们。"""
import os, json
from pathlib import Path

ROOT = Path(os.environ.get("P2_ROOT", "/mnt/work_new/weihanxu/output/pyramid_v2"))
OUT = ROOT / "geo3d"
GEMINI_DIR = ROOT / "runs" / "annot_probe_1014" / "gemini-4-argon"
SAMPLES_JSON = ROOT / "data" / "egoplan_samples.json"
VIDEOS = Path("/mnt/data_new/ego4d/v2/full_scale")
SAM_PY = "/mnt/work_new/demo_dev/scenebind-interact-demo-v0/SAM/.conda/sam3/bin/python"
HOLI_PY = "/home/weihanxu/miniconda3/envs/holi/bin/python"
DA3_MODEL = "depth-anything/DA3NESTED-GIANT-LARGE"

FPS = 2.0            # 采样帧率
FRAME_W = 1008       # 抽帧宽(SAM3 原生 1008)
DA3_RES = 504        # DA3 process_res(长边)
STATIC_R = 0.2       # 静止:窗口内最大位移 ≤ 0.2 m
STATIC_MIN_S = 2.0   # 静止区间最短 2 s
ERODE = 5            # mask 腐蚀核
BORDER_FRAC = 0.05   # 质心在边缘 5% 内不参与关系推导
HAND_OVERLAP = 0.3   # 与手 mask 重叠 > 0.3 视为被持握
MIN_TRACK = 4        # 轨迹至少 4 帧
# 关系阈值(米),与 pyramid/spatial.py、pose.py 一致
NEAR_L1 = 0.8; MARG = 0.4; MIN_CAND = 4; MARG_L3 = 0.4; GAP_L4 = 0.4
EGO_MARG = 0.3; EGO_MIN_R = 0.2; EGO_MAX_R = 2.5; STAB_WIN = 0.5; STAB_MOVE = 0.25
# 质量 / 尺度 / 别名 / 方向阈值(10-15 spec 实施)
POSE_MAX_SPEED = 2.0      # 帧间相机速度 > 2 m/s 视为该帧位姿无效
POSE_MAX_ROT = 180.0      # 帧间角速度 > 180°/s 无效
PAIR_DEPTH_ERR = 0.10     # 相邻帧深度自洽相对误差 > 10% 无效
CLIP_DEPTH_FRAC = 0.6     # clip 级:gap1 ≤5% 的帧对比例 ≥ 0.6 才算 pose_valid
CLIP_MAX_MEAN_SPEED = 0.6 # clip 级:平均速度 ≤ 0.6 m/s
ARM_REACH_MIN = 0.5       # 尺度检查:手持 / narration 命中物体 <1 m 的比例 ≥ 0.5 → metric_estimated,否则 metric_suspect
ALIAS_D = 0.15; ALIAS_IOU = 0.5; ALIAS_IOU_PART = 0.2; ALIAS_MIN_COMMON = 4   # 同物异名:中心距 ≤0.15 m 且 mask IoU ≥0.5 自动合并;IoU <0.2 视为部件 / 支撑
BEHIND_F = -0.2; FRONT_F = 0.3; BEHIND_MARG = 0.3; MIN_ANGLE_MARGIN = 15.0; NEAR_BUF = 0.1
HOLD_MIN_FRAMES = 2       # 持握段:hand_overlap > HAND_OVERLAP 连续 ≥ 2 帧
MOVE_MIN_DISP = 0.3       # object_location_transition:两端静止且位移 ≥ 0.3 m
TIME_UNC = 0.25           # 2 fps 采样:时间不确定度 = 半个采样周期
REST_PAD = 0.26           # rest_at 的区间时间容差(秒)
PICK = ["baking", "blacksmith", "carpenter", "cleaning", "cooking", "decorating", "drawing", "mechanic", "repairing", "gardening"]


def samples(sel=None):
    """10 条探针样本(Gemini 文件 ∪ egoplan_samples.json),按 scenario 顺序;sel = sample_id 列表 / scenario 列表 / None(全部)。"""
    base = {s["sample_id"]: s for s in json.loads(SAMPLES_JSON.read_text())["samples"]}
    out = []
    for f in sorted(GEMINI_DIR.glob("*.json")):
        if f.name == "summary.json": continue
        g = json.loads(f.read_text()); s = base.get(g["sample_id"])
        if not s: continue
        out.append({**s, "window": g["window"], "gemini": g.get("annotation") or {}, "gt_narrations": g.get("gt_narrations") or [], "probe_clip": g.get("clip")})
    out.sort(key=lambda s: PICK.index(s["scenario"]) if s["scenario"] in PICK else 99)
    if sel and sel != ["all"]:
        out = [s for s in out if s["sample_id"] in sel or s["scenario"] in sel or s["sample_id"][-6:] in sel]
    return out


def clip_dir(sid):
    d = OUT / sid; d.mkdir(parents=True, exist_ok=True); return d


def load_frames(cd):
    return json.loads((Path(cd) / "frames.json").read_text())


def slug(name):
    import re
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40] or "obj"
