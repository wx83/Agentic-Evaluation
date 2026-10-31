"""金字塔评测的常量。把 bench/ 加进 sys.path,其余模块 import pconfig 即可平铺 import。"""
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent          # .../agent/bench
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

import config as C                                       # noqa: E402  bench 的词表与路径

VIDEOS = [
    "P02-20240211-120927",
    "P03-20240216-185832",
    "P06-20240511-102207",
    "P08-20240620-180825",
    "P09-20240623-120359",
]
# PYRAMID_CLIPS=<json>:clip 模式 —— 事实只取落在这几个 30 s 窗口里的,题的窗口统一改成 clip 窗口
# (L4 例外,见 clip_pyramid.restrict),同层不再做窗口去重。文件由 clip_pyramid.py select 生成。
CLIPS = None
if __import__("os").environ.get("PYRAMID_CLIPS"):
    import json as _json
    CLIPS = _json.loads(Path(__import__("os").environ["PYRAMID_CLIPS"]).read_text())["clips"]
# PYRAMID_VIDEOS=a,b 覆盖视频列表(2026-10-11:在第 6 个视频 P08-20240618-163547 上跑新 clip 的小金字塔)
if __import__("os").environ.get("PYRAMID_VIDEOS"):
    VIDEOS = [v for v in __import__("os").environ["PYRAMID_VIDEOS"].split(",") if v]

# (tier, 层级权重)。第 k 层答对一题得 k 分。
LEVELS = [("Easy", 1), ("Low", 2), ("Medium", 3), ("High", 4)]
TIER_OF_LEVEL = {k: t for t, k in LEVELS}

N_TARGET = 100          # 每层题数(裁到恰好这么多)
N_REQUEST = 140         # 每轮候选数(校验会拒掉一部分)
PASS_MIN = 80           # 100 题里 >=80 才晋级(恰好 80% 算过)
PHRASE_BATCH = 10       # 每次 Gemini 措辞调用带几条事实
# PYRAMID_SEED 换一个数就是一次独立复现:重新抽事实、重新选 few-shot 样例、
# 重新生成题面。产物走独立目录,不覆盖既有结果。
SEED = int(__import__("os").environ.get("PYRAMID_SEED", "42"))
WIN_SEC = 30.0          # 与 0830 一致的固定证据窗口
STRIDE = 15.0
FACT_REUSE_MAX = 3      # 同一条 fact 跨臂最多用几次
TEMPLATE_FRAC_MAX = 0.20  # 每套题里模板措辞(非 Gemini)的上限

# 2026-10-11:easy_goal(「这段 clip 的总体目标是什么」)是对整个 clip 的推理,不该在 L1 出;
# L3 已有 medium_goal(inference)。此集合里的子类不进任何新组的题套(已落盘的题套不受影响)。
EXCLUDE_SUBTYPES = {"easy_goal"}

ARMS = ["shared_l1", "per_agent", "pooled"]
# 输入档:memory=timeline 渲染成文本(检索天花板);clip30=同一窗口的 30 秒视频+音频
MODES = ["memory", "clip30", "blind"]   # blind = 不给任何输入,只读题 —— 量化「不看视频也能猜」
# clip30_mute = 同一 clip、音轨换成等长静音 —— 量化「不听声音也能答」(2026-09-28 静音消融)
MODES = MODES + ["clip30_mute"]
AGENTS = ["gemini", "qwen"]

# ---- answer-format 细分(2026-09-28,experiments/answer_expansion.md)----
# 同一道题出五种作答格式:yn 是非 / mc 单选(现状)/ ms 不定项 / open 简答 / open_x 简答+解释。
# open 只对「去掉选项仍可独立作答且答案唯一」的子类;其余子类第 4/5 档改为逐项 True/False(tf4 / tf4_x)。
FORMATS = ["yn", "mc", "ms", "open", "open_x", "plan", "plan_x"]
OPEN_OK = {"easy_sound_object", "easy_move", "low_sound_movement", "medium_count",
           "medium_order", "medium_spatial_order", "medium_sound_order", "easy_goal",
           "medium_purpose", "low_purpose", "high_plan_route", "high_gaze_pickup",
           "high_plan_next_action", "high_replan", "high_plan_next_step"}
FMT_MAX_TOKENS = {"yn": 64, "mc": 64, "ms": 64, "tf4": 96, "tf4_x": 192, "open": 96, "open_x": 192, "plan": 400, "plan_x": 512}
FMT_CHANCE = {"yn": 0.5, "mc": 0.25, "ms": 1 / 15, "tf4": 1 / 16, "tf4_x": 1 / 16, "open": 0.0, "open_x": 0.0, "plan": 0.0, "plan_x": 0.0}
N_FORMAT_PER_LEVEL = 40      # 对照试验每层基题数(从 pooled_clip30 每层 100 题按子类均衡抽)
JUDGE_CACHE = C.SHARED / "judge_cache.jsonl"

AGENT_INTERPRETER = {
    "gemini": "/home/weihanxu/miniconda3/envs/gemini/bin/python",
    "qwen":   "/home/weihanxu/miniconda3/envs/timechatcap/bin/python",
    "mock":   sys.executable,
}

# PYRAMID_SMOKE=1 时全部产物走隔离目录,冒烟测试不污染正式题库与复用登记
import os
_base = "pyramid_smoke" if os.environ.get("PYRAMID_SMOKE") else "pyramid"
if SEED != 42:
    _base += f"_seed{SEED}"          # 换 seed = 另一次独立复现,产物互不干扰
POUT = C.OUT / _base
DATA = POUT / "data"
CACHE = POUT / "cache" / "phrasing"
SETS = POUT / "sets"
# Gemini 后端:nv(默认,NVIDIA 网关)/ google(原直连)。题库、缓存、事实复用共用;
# 只有**结果**按后端分开:google 仍写 results/(历史结果都在这里,不动),nv 写 results_nv/。
BACKEND = os.environ.get("GEMINI_BACKEND", "nv")
assert BACKEND in ("nv", "google"), f"GEMINI_BACKEND={BACKEND} 只能是 nv / google"
RESULTS = POUT / ("results" if BACKEND == "google" else "results_nv")
# GEMINI_AGENT_MODEL=...:只换**被评测的 agent** 的模型(出题/措辞仍用 C.GEMINI_MODEL)。
# 结果目录按模型分:默认模型仍叫 gemini/,其他叫 gemini@<model>/。
AGENT_MODEL = os.environ.get("GEMINI_AGENT_MODEL") or C.GEMINI_MODEL
# GEMINI_THINKING=on:被评测 agent 开 thinking(默认关,见 agent_gemini.py 注释);目录加 +think 后缀
AGENT_THINKING = os.environ.get("GEMINI_THINKING", "off").lower() in ("on", "1", "true")
AGENT_DIR = ("gemini" if AGENT_MODEL == C.GEMINI_MODEL else f"gemini@{AGENT_MODEL}") + ("+think" if AGENT_THINKING else "")
ADAPT = POUT / "adapt"
ANNOT = POUT / "annot"          # 人工标注(goal 句、参考轨迹、replan 核验),不随重 mine 重建
REPORT = POUT / "report"
STATE = POUT / "state"

# 运行日志:按 agent 分子目录,与 output 分开存放
LOGROOT = C.OUT / "logs"

EXEMPLARS = C.SHARED / "chains.json"     # few-shot 样例来源(0830 的 8 条链)

# 措辞 -> 标签的反查表,easy_sound 的干扰项校验要用。值必须互异。
PHRASE2LABEL = {v: k for k, v in C.SOUND_PHRASE.items()}
assert len(PHRASE2LABEL) == len(C.SOUND_PHRASE), "SOUND_PHRASE 的措辞有重复"


def ensure_dirs():
    for p in (DATA, CACHE, SETS, RESULTS, ADAPT, REPORT, STATE):
        p.mkdir(parents=True, exist_ok=True)


# ---------- 选题器(curate.py):Gemini 按层间 memory 挑题,gold 仍由程序推出 ----------
SELECT_MODES = ["gemini", "heuristic", "program"]
CURATE_VERSION = "c1"
CURATE_POOL_MULT = 2          # 候选卡片 = 程序顺序前 CURATE_POOL_MULT × N_REQUEST 条
CURATE_MAX_SUB_FRAC = 0.50    # 护栏:单一子类占比上限(防自适应把一层推成单一题型)
CURATE_MIN_SUB_FRAC = 0.10    # 护栏:池中有的子类至少这么多(可用数不足时取可用数)
CURATE_MAX_GOLD_FRAC = 0.15   # 护栏:spatial 题任一 gold 取值占比上限
CURATE_MIN_FRACTION = 0.50    # Gemini 有效挑选占比低于此值时告警

# 子类 -> 题族。层间摘要的 by_subtype 是**上一层**的子类名,与本层候选对不上
# (这正是 _weighted_order 的子类维跨层从未生效的原因);按族对照才能跨层传递。
SUBTYPE_FAMILY = {
    "easy_sound": "sound_id", "easy_sound_object": "sound_id",
    "easy_move": "movement", "low_sound_movement": "movement",
    "medium_count": "count",
    "high_order": "order",
    "easy_spatial_near": "spatial_exo", "low_spatial_near": "spatial_exo",
    "medium_spatial_extreme": "spatial_exo", "high_spatial_order": "spatial_exo",
    "easy_spatial_side": "spatial_ego", "low_spatial_side": "spatial_ego",
}
SPATIAL_EXEMPLARS = C.SHARED / "spatial_exemplars.json"
# L3 推断 / L4 规划的新子类(2026-09-14 重排):排序题下放到 L3,L4 改为规划
SUBTYPE_FAMILY.update({
    "medium_purpose": "intent", "low_purpose": "intent", "medium_goal": "intent", "easy_goal": "intent",
    "medium_order": "order", "medium_spatial_order": "spatial_exo",
    "high_plan_retrieve": "plan", "high_plan_route": "plan", "high_plan_next": "plan",
    "high_gaze_destination": "plan", "high_gaze_pickup": "plan",
    "high_plan_next_action": "plan", "high_plan_trajectory": "plan", "high_replan": "plan", "high_plan_next_step": "plan",
})
MULTI_SCENE = {"high_plan_retrieve", "high_plan_route"}   # 输入为两段 30 s 拼接
