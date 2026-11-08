# Scope planner(最新版)+ Method E(sub-goal 生成)

两步,上游到下游:

1. **Method E**(`method_e/`):HD-EPIC 官方 recipe step → Gemini 拆成 sub-goal(EgoPlan-Bench2 的做法)。
2. **Scope planner**(`planner.py`):goal + sub-goal → 每个 sub-goal 必然发生的 event、关系、决策点。

## 1. Scope planner

输入一个任务的 goal + 有序 sub-goal 文字(不看视频、不生成时间),让 Gemini 列出每个 sub-goal 必然发生的 event、相邻 sub-goal 之间的关系、以及决策点。pyramid2 用这个结果决定出哪些题。

### 用法

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY=sk-or-...

python3 planner.py examples/hdepic_task61.input.json  -o out.json                        # HD-EPIC
python3 planner.py examples/aea_strawberry.input.json -o out.json --prompt aea_single    # AEA 单人
python3 planner.py my_task.json                        -o out.json --prompt aea_duo       # AEA 两人
```

`--prompt` 只是选数据集对应的 prompt,planner 本身是同一个:

| `--prompt` | 文件 | 用于 |
|---|---|---|
| `hdepic`(默认) | `prompts/hdepic.md` | HD-EPIC |
| `aea_single` | `prompts/aea_single.md` | AEA 单人录像 |
| `aea_duo` | `prompts/aea_duo.md` | AEA 两人录像(每个 sub-goal 带已标注的 speech / sound,planner 只能从里面选并引用 id) |

### 输入

```json
{"task_id": "...", "goal": "Add broccoli and green beans to pan and stir",
 "sub_goals": [{"idx": 1, "text": "Chop the broccoli"},
               {"idx": 2, "text": "Add it to the pan", "annotated_events": [{"id": "S004", "type": "speech", "text": "..."}]}]}
```
`annotated_events` 只有 `aea_duo` 需要。完整例子见 `examples/*.input.json`。

### 输出

`plan` 里有三部分(例子见 `examples/*.output.json`):
- `sub_goals[].events[]`:每个 event 的 `type`(action / sound / placement / state / speech)、`description`、`objects`、`verbs`、`skills`、`source_ids`(引用的标注 id);
- `relations[]`:相邻 sub-goal 之间的两个 event 的关系(object_continuity / state_change / causal_prerequisite / hidden_state / spatial_end_state);
- `decision_points[]`:每个 sub-goal 开始前是不是一个真正的决策点。

不合规的输出(越界 idx、未知类型、不相邻的关系等)会被自动丢掉,记在 `warnings`。

## 2. Method E:recipe step → sub-goal

输入:HD-EPIC 一段录像。每个官方 recipe step 当一段的 summary,把这个 step 时间段里的官方 narration 按时间排好交给 Gemini 3.1 Pro(temperature 0);它输出这段的 overall goal、若干 sub-goal(每个引用自己的 narration id,4–20 条为宜)、以及和 step 无关的 narration。不在任何 step 里的 narration 每 120 条一组同样处理。模型不写时间,sub-goal 的起止时间由程序从官方 narration 抄。prompt 原文在 `method_e/method_e.py` 开头。

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY=sk-or-...
python3 method_e/method_e.py --annot /path/to/hd-epic/annotations/data --video P08-20240617-184909 -o out/P08-20240617-184909
python3 method_e/method_e.py --stats out/        # 对一批输出算下面这些 metrics
```

输出 `out/<video>/merged.json`(pyramid2 读的就是这个文件):`goals[]` 每个 sub-goal 有 `description`、`action_ids`、`segment`(官方 step id 或 `nostep_xx`)、`start_s` / `end_s`、`n_actions`、`n_interruptions_gt60s`。

**例子**(`method_e/examples/`,每个文件 = 真实发给 Gemini 的输入 + 它的原始返回 + 最终带时间的 sub-goal):

| 文件 | 官方 step | narration → sub-goal |
|---|---|---|
| `P08-20240617-184909__P08_R07_S06.json` | Slice onion, chili pepper, and bell pepper and place to side | 30 → 3(切洋葱 / 切辣椒 / 去籽切甜椒) |
| `P06-20240510-090328__P06_R01_S01.json` | Mix the uttapam pancake mix into water in a bowl until a smooth batter is prepared and set it aside for 10-15 minutes. | 92 → 8 |
| `P03-20240218-190556__P03_R02_S01.json` | Wash potatoes, peel and cut them into small cubes | 107 → 9 |

**Metrics**(pyramid2 现用的 50 份输出,`method_e/metrics.json`):

| | 官方 step 内 | no-step 窗口 |
|---|---|---|
| sub-goal 数 | 1281 | 1999 |
| 每个 sub-goal 的 narration 数(中位 / p10–p90) | 10 / 4–17 | 10 / 5–18 |
| 每个 sub-goal 时长(中位 / p10–p90) | 29.5 s / 10–122 s | 24.1 s / 8–96 s |
| narration 数在 4–20 内的比例 | 94% | 96% |
| 中间被打断 > 60 s 的比例 | 9.8% | 8.5% |

259 个官方 step,每个 step 拆成的 sub-goal 数中位 4(1–21)。没分进任何 sub-goal 的 narration 共 1583 条;校验没过、重试 3 次仍有错的窗口 1 个。sub-goal 是模型候选,未人工核验。
