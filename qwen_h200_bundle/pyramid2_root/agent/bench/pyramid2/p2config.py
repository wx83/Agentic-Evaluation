"""pyramid2 常量与路径。把 bench/、pyramid/、gemini/ 加进 sys.path,其余模块平铺 import。"""
import os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent                                  # .../agent/bench
PYR = BENCH / "pyramid"
GEMINI_DIR = Path("/mnt/work_new/weihanxu/gemini")
for _p in (BENCH, PYR, GEMINI_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import config as C                                   # noqa: E402

ROOT = Path(os.environ.get("P2_ROOT", "/mnt/work_new/weihanxu/output/pyramid_v2"))
DATA = ROOT / "data"
RAW = DATA / "raw_annotations"
REVIEWS = RAW / "reviews"
RUNS = ROOT / "runs"
MEDIA = ROOT / "media"
LOGS = Path("/mnt/work_new/weihanxu/logs/pyramid2")

MD = Path("/mnt/work_new/weihanxu/experiments/daily_report/1013_prompts.md")   # draft2:并入 contact-rich / 触觉反馈(10-13);draft1 原件在 1012.md
PROMPT_VERSION = "physical-mental-draft2"
PROMPT_HEADS = {"shared": "## 2. ", "L1": "## 3. ", "L2": "## 4. ", "L3": "## 5. ", "L4": "## 6. ", "task_context": "## 7. ", "scope": "## 8. ", "tree": "## 9. "}
OPTIONAL_HEADS = {"task_context", "scope", "tree"}      # tree:1022_prompts_tree.md 的题树 planner(10-22)      # 1014_prompts_egoplan.md 才有;老 prompt 文件没有就跳过
TAXONOMY_VERSION = "capability-v3"     # 10-13 L2 重构;v2 原件 pyramid/capability_map.json 不动
REGISTRY_VERSION = "ext-v1"
POLICY_VERSION = "vp1"
PROTOCOL_VERSION = "independent-v1"
CAPMAP_SRC = PYR / "capability_map.json"

# raw_annotations/<alias> -> 真实路径(symlink,不复制)
SOURCES = {
    "hdepic": "/mnt/work_new/weihanxu/HD-EPIC/annotations",
    "hdepic_videos": "/mnt/work_new/weihanxu/HD-EPIC/videos",
    "hdepic_gaze": "/mnt/work_new/weihanxu/HD-EPIC/gaze",
    "hdepic_annot": "/mnt/work_new/weihanxu/hdepic_annot/P08-20240618-163547",
    "ego4d": "/mnt/work_new/weihanxu/Ego4d",
    "epic_kitchens": "/mnt/work_new/weihanxu/EPIC-KITCHENS",
    "object_memory": "/mnt/work_new/weihanxu/object_memory",
    "pyramid_seed43": "/mnt/work_new/weihanxu/output/pyramid_seed43",
    "benchmarks": "/mnt/work_new/weihanxu/benchmarks_1011",
}
HDEPIC_VIDEOS = ["P02-20240211-120927", "P03-20240216-185832", "P06-20240511-102207",
                 "P08-20240620-180825", "P09-20240623-120359", "P08-20240618-163547"]
EGO4D_VIDEOS = ["0e6fb738-05fc-4dd5-9746-a8e10efe8c20", "4c642620-db0e-4096-9ece-2b2c6fdb47b0",
                "53da674a-089d-428a-a719-e322b2de002b", "9adc0c59-1167-4311-abf3-7b57a0743b1d",
                "ab78f4e5-aa25-442c-933f-9b277b1d9715", "bd970f5b-3fd9-4ae9-9f2b-738e8ca54c1e",
                "e6f1accd-e18d-43ec-b854-e7633b15cbf7", "ff8a5283-bf6e-40ef-b662-c91216d24c0d"]
# 小实验(用户 10-12 定):HD-EPIC 5 + Ego4D 5
SMOKE_HDEPIC = HDEPIC_VIDEOS[:5]
SMOKE_EGO4D = ["ab78f4e5-aa25-442c-933f-9b277b1d9715", "9adc0c59-1167-4311-abf3-7b57a0743b1d",
               "bd970f5b-3fd9-4ae9-9f2b-738e8ca54c1e", "53da674a-089d-428a-a719-e322b2de002b",
               "e6f1accd-e18d-43ec-b854-e7633b15cbf7"]

CLIP_SEC = 30.0          # 单段题的默认窗口
CLIP_SIZE = 288          # 短边像素(与 bench 的 288² 一致)


SKILL_EXCLUSIONS = DATA / "skill_exclusions.json"


def excluded_skills():
    """10-27(用户:把 contact 先拿掉):全局不出题、不重放、不计分的 skill 集合(data/skill_exclusions.json);文件缺失 = 空集。"""
    import json
    try:
        return set(json.loads(SKILL_EXCLUSIONS.read_text())["skills"])
    except FileNotFoundError:
        return set()


def ensure_dirs():
    for p in (DATA, RAW, REVIEWS, RUNS, MEDIA, LOGS):
        p.mkdir(parents=True, exist_ok=True)
