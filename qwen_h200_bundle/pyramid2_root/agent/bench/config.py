"""所有路径与词表。不含逻辑。"""
from pathlib import Path

HDEPIC   = Path("/mnt/work_new/weihanxu/HD-EPIC")
OUT      = Path("/mnt/work_new/weihanxu/output")
SHARED   = OUT / "_shared"
CLIPS    = SHARED / "clips"

VIDEO    = "P08-20240620-180825"          # 最短的一个，28.2 分钟

# clip 参数：三档统一，288² 是 stride-32 下 fps=2 时 5 分钟能塞进 65536 的最大分辨率
CLIP_SEC, LONG_SEC = 30.0, 300.0
SIZE, FPS = 288, 2

GEMINI_MODEL = "gemini-3.5-flash"          # 3.6-flash 实测 80s/次，太慢
GEMINI_FALLBACKS = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]
QWEN_PATH = "/mnt/work_new/weihanxu/agent/Qwen3-Omni/Qwen3-Omni-30B-A3B-Instruct"

SKIP_SOUNDS = {"background", "human"}
IMPULSIVE   = {"beep", "click", "footstep", "zip", "spray"}

# 声音标签 -> 自然措辞。绝不把原始标签给模型，否则考的是词表不是听觉。
SOUND_PHRASE = {
 "metal / plastic collision": "metal and plastic knocking together",
 "stir / mix / whisk": "stirring or whisking",
 "footstep": "footsteps",
 "plastic-only collision": "two plastic objects knocking together",
 "cut / chop": "chopping",
 "metal / wood collision": "metal hitting wood",
 "metal-only collision": "two metal objects knocking together",
 "open / close": "something being opened or closed",
 "rustle": "rustling",
 "water": "running water",
 "metal / ceramic collision": "metal hitting ceramic",
 "scrub / scrape / scour / wipe": "scrubbing or wiping",
 "beep": "an electronic beep",
 "ceramic-only collision": "two ceramic objects knocking together",
 "plastic / wood collision": "plastic hitting wood",
 "sizzling / boiling": "sizzling or boiling",
 "metal / glass collision": "metal hitting glass",
 "slide object": "an object sliding",
 "glass-only collision": "two glass objects knocking together",
 "wood-only collision": "two wooden objects knocking together",
 "click": "a click",
 "plastic / ceramic collision": "plastic hitting ceramic",
 "wood / glass collision": "wood hitting glass",
 "plastic / marble collision": "plastic hitting a stone worktop",
 "plastic / glass collision": "plastic hitting glass",
 "kettle / mixer / appliance": "an appliance running",
 "pour": "pouring",
 "ceramic / wood collision": "ceramic hitting wood",
 "metal / marble collision": "metal hitting a stone worktop",
 "paper-only collision": "paper rustling against paper",
 "zip": "a zip",
 "glass / marble collision": "glass hitting a stone worktop",
 "metal / paper collision": "metal hitting paper",
 "plastic / paper collision": "plastic hitting paper",
 "ceramic / marble collision": "ceramic hitting a stone worktop",
 "ceramic / glass collision": "ceramic hitting glass",
 "hoover / fan": "a fan or extractor running",
 "spray": "a spray",
 "cloth-only collision": "cloth against cloth",
}
# 设备/环境声：常在画面外持续发声，fuse / conflict 两类靠它
DEVICE_SOUNDS = {"water", "sizzling / boiling", "kettle / mixer / appliance",
                 "hoover / fan", "beep", "spray"}

# Easy 层：声音 <-> 可见物体的对应。牵强的对应会让「冗余一致」名不副实。
SOUND_OBJECT_HINT = {
 "cut / chop": ["knife", "board"],
 "stir / mix / whisk": ["spoon", "whisk", "fork", "spatula"],
 "water": ["tap", "sink"],
 "beep": ["timer", "oven", "microwave"],
 "open / close": ["fridge", "refrigerator", "drawer", "cupboard", "door"],
 "pour": ["bottle", "jug", "kettle", "carton"],
 "sizzling / boiling": ["pan", "pot"],
 "scrub / scrape / scour / wipe": ["sponge", "cloth", "brush", "towel"],
 "zip": ["bag"],
}

FIXTURE_NAME = {
 "counter": "the kitchen counter", "hob": "the hob", "sink": "the sink",
 "fridge": "the fridge", "cupboard": "a cupboard", "drawer": "a drawer",
 "dishwasher": "the dishwasher", "oven": "the oven", "table": "the table",
 "floor": "the floor", "bin": "the bin", "microwave": "the microwave",
 "shelf": "a shelf", "freezer": "the freezer",
}
# 这些名词是固定设施，绝不能当成「被操作的物体」
FIXTURE_NOUNS = {"counter", "kitchen top", "countertop", "tabletop", "sink", "hob",
                 "cupboard", "drawer", "tap", "worktop", "shelf", "floor", "oven",
                 "fridge", "refrigerator", "dishwasher", "bin", "microwave"}

# 新增两个 agent
VIDEOLLAMA2_PATH = "DAMO-NLP-SG/VideoLLaMA2.1-7B-AV"
VIDEOLLAMA2_REPO = "/mnt/work_new/weihanxu/agent/VideoLLaMA2"   # audio_visual 分支
MINICPMO_PATH = "openbmb/MiniCPM-o-4_5"
