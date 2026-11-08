# Scope planner(最新版)

输入一个任务的 goal + 有序 sub-goal 文字(不看视频、不生成时间),让 Gemini 列出每个 sub-goal 必然发生的 event、相邻 sub-goal 之间的关系、以及决策点。pyramid2 用这个结果决定出哪些题。

## 用法

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

## 输入

```json
{"task_id": "...", "goal": "Add broccoli and green beans to pan and stir",
 "sub_goals": [{"idx": 1, "text": "Chop the broccoli"},
               {"idx": 2, "text": "Add it to the pan", "annotated_events": [{"id": "S004", "type": "speech", "text": "..."}]}]}
```
`annotated_events` 只有 `aea_duo` 需要。完整例子见 `examples/*.input.json`。

## 输出

`plan` 里有三部分(例子见 `examples/*.output.json`):
- `sub_goals[].events[]`:每个 event 的 `type`(action / sound / placement / state / speech)、`description`、`objects`、`verbs`、`skills`、`source_ids`(引用的标注 id);
- `relations[]`:相邻 sub-goal 之间的两个 event 的关系(object_continuity / state_change / causal_prerequisite / hidden_state / spatial_end_state);
- `decision_points[]`:每个 sub-goal 开始前是不是一个真正的决策点。

不合规的输出(越界 idx、未知类型、不相邻的关系等)会被自动丢掉,记在 `warnings`。
