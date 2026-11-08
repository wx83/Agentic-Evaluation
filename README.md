# pyramid2 Expected-event planner(scope planner,11-03 版)— 独立包

pyramid2 四层评测里出题前的那一步:**只看 goal + 有序 sub-goal 文字**(不看视频、不看标注、不生成任何时间戳),让 Gemini 写出每个 sub-goal「必然发生的 event」,再加相邻 sub-goal 之间的 L3 关系和 L4 决策点。之后程序(`sg.match_events`,不在本包主体里,见 reference/sg.py)把这些 event 对到官方标注记录拿时间;**标注里有但 planner 没列的东西不出题**。

这是 10-28 v15 用户定的「sub-goal 结构版」planner,替代了 10-14 的 scope planner(按 need-to-know 挑标注记录);11-03 v29 加了 `speech` 事件类型与 `annotated_events` / `source_ids`(AEA 两人录像:planner 从已标注的 speech / sound 事件里选并引用 id)。

## 文件

| 文件 | 内容 |
|---|---|
| `planner.py` | 独立可运行版:`build_input` / `validate` 与 pyramid2 `sg.py` 逐字一致;LLM 调用直接走 OpenRouter(OpenAI 协议),不依赖 evidence store;`--prompt` 选三个 prompt 变体之一(见下节) |
| `prompts/planner_subgoal_events.md` | 变体 `hdepic`:HD-EPIC Method E 的 planner system prompt(默认) |
| `prompts/planner_subgoal_events_aea_single.md` | 变体 `aea_single`:AEA 单人 protocol clip |
| `prompts/planner_subgoal_events_aea_duo.md` | 变体 `aea_duo`:AEA 两人录像(SAVVY speech / sound 标注) |
| `examples/hdepic_task61.{input,output}.json` | HD-EPIC P07_R07_S03「Pulse all the dressing ingredients…」:6 sub-goal → 13 event、5 relation(Gemini 3.1 Pro,11-03,变体 `hdepic`) |
| `examples/aea_strawberry.{input,output}.json` | AEA loc1_script1_seq6_rec1 s0「Wash and eat a strawberry」:6 sub-goal → 13 event、3 relation(Gemini 3.1 Pro,11-03,变体 `aea_single`) |
| `reference/sg.py` | pyramid2 里的原文件(planner + match_events + 四层 cluster 构造),只作对照 |

## Prompt 变体(三个版本,代码相同)

planner 的代码只有一份(`sg.py` 的 `build_input` / `validate` / `plan_one`),**不同数据集只换 system prompt**。pyramid2 从每个 contract 的 `prompt_md` 文件里取 `## 8.` 节当 planner prompt;本包把实际用到的三个版本原样拷了出来(逐字节一致,所以 prompt hash 和 pyramid2 的 `sg_cache` 对得上):

| 变体(`--prompt`) | 本包文件 | 取自 pyramid2 prompt 文件 | 用于 | 和 `hdepic` 的区别 |
|---|---|---|---|---|
| `hdepic`(默认) | `prompts/planner_subgoal_events.md` | `1104_prompts_hdepic_e_v30.md` §8(与 `1028_…_v16.md`、`1102_…_v24.md` 的 §8 完全相同) | HD-EPIC Method E:v15 / v16 / v24 / v30b / v31 全部 contract | — |
| `aea_single` | `prompts/planner_subgoal_events_aea_single.md` | `1103_prompts_aea_p_v29.md` §8 | AEA 单人 protocol clip:v29 `p2_aeaP_1103_g4_v29_self__*` | 场景说明改为 Aria Everyday Activities 单人录像;输入里没有 `annotated_events`,只有 sub-goal 文字暗示说话时才写 speech 事件;允许 `speech` 类型和 `source_ids` 字段 |
| `aea_duo` | `prompts/planner_subgoal_events_aea_duo.md` | `1103_prompts_aea_s_v29.md` §8 | AEA 两人录像(SAVVY):v29 `p2_aeaS_1103_g4_v29_self__*` | 每个 sub-goal 带 `annotated_events`(speech:id / text / topic / speaker = wearer \| partner;sound:id / text / object);speech 和 sound 事件**必须**来自 annotated_events 并填 `source_ids`;同伴说的每一句都要单独列成一个 speech 事件(spatial-audio 题的锚点);声音只列已标注的 |

核对方法(11-08 做过):`sha1(prompt + json.dumps(input, sort_keys=True))[:10]`。`examples/hdepic_task61` 用 `hdepic` 得到 `dfcab200a6`,`examples/aea_strawberry` 用 `aea_single` 得到 `082706ddc4`,两个都和 pyramid2 `pyramid_v2/data/sg_cache/` 里的缓存文件名一致。

## 与仓库其它 branch 的关系

所有 branch 用的都是这一个 planner(sg.py 的 sub-goal planner),区别只在各 branch 打包的是哪个时期的 `sg.py` 和 prompt:

| branch | `code/bench/pyramid2/sg.py` | 里面带的 planner prompt |
|---|---|---|
| `scope-planner`(本 branch) | `reference/sg.py` = 11-03 最终版 | 三个变体全有(`prompts/`) |
| `v31` | 与 `reference/sg.py` 逐字节相同 | `prompts/1102_…_v24.md`、`prompts/1104_…_v30.md`(§8 = 变体 `hdepic`) |
| `gemini-solver` / `qwen-solver` | 10-28 v16 时期的旧版(还没有 v29 的 speech / `annotated_events` 支持) | `prompts/1028_…_v16.md`(§8 = 变体 `hdepic`) |
| `main` | 索引;`scope_planner/` 目录是 11-05 从本 branch 拷过去的,**只有 `hdepic` 变体** | — |

AEA 两个变体只在本 branch 有;要在别的 branch 上跑 AEA,从这里拿 prompt。

## 运行

```bash
export OPENROUTER_API_KEY=sk-or-...
python3 planner.py examples/hdepic_task61.input.json -o out.json          # 默认 google/gemini-3.1-pro-preview,temperature 0,JSON 输出
python3 planner.py my_task.json --skills object_recognition,action_recognition,sound_action_binding,cross_event_integration
python3 planner.py --validate-only out.json examples/hdepic_task61.input.json   # 只跑 validate(不调模型)
python3 planner.py examples/aea_strawberry.input.json --prompt aea_single -o out_aea.json   # AEA 单人
python3 planner.py my_aea_duo_task.json --prompt aea_duo -o out_duo.json                   # AEA 两人(sub_goals 里带 annotated_events)
```

输入 JSON:
```json
{"task_id": "...", "goal": "Add broccoli and green beans to pan and stir",
 "sub_goals": [{"idx": 1, "text": "Chop the broccoli"}, {"idx": 2, "text": "Add it to the pan", "annotated_events": [{"id": "u12", "type": "speech", "text": "..."}]}]}
```
要逐字复现某个示例的输入(和 prompt hash),`--skills` 传示例 input 里 `skills` 的 key 加上 `l3_relation_types` 对应的 relation skill;`skills` 不给就用 `SKILL_DEFS` 全部 + 四个 L3 relation skill;给了就只让 planner 在这些 skill 里标 event 可考的 skill,并按 skill 过滤 `l3_relation_types`。

输出 = `{"task_id", "prompt_hash", "model", "created", "input", "plan", "warnings", "usage", "status"}`,其中 `plan`:
- `sub_goals[].events[]`:`event_id`(s3e1)、`type`(action / sound / placement / state / speech)、`description`、`objects`(标注者会用的名字,小写)、`verbs`、`skills`、`relevance`、`source_ids`(只有引用 annotated_events 时非空);`irrelevant` = 这个 sub-goal 里与 goal 无关的部分;
- `relations[]`:`type` ∈ object_continuity / state_change / causal_prerequisite / hidden_state / spatial_end_state → `skill`;`events` 两个且必须来自**相邻** sub-goal(k, k+1),`ask`、`answer_hint`;
- `decision_points[]`:idx 2..n+1,`real`、`why`。

## validate 做的裁剪(和 pyramid2 完全一样)
- sub-goal idx 越界 → 丢;event 没 description → 丢;type 不在五种里 → 改 action;skills 只留输入里有的;字段截长(description 200 / relevance 200 / ask 300);
- relation:type 未知 → 丢;事件 < 2 个或来自同一 sub-goal → 丢;不相邻 → 丢(v16 规则);
- decision point:idx 不在 2..n+1 → 丢;
- 两次尝试都解析失败 → `status: failed`,`error` 字段。
每条裁剪进 `warnings`。

## 在 pyramid2 里的位置
`sg.plan_one`(本包 `plan`)→ 缓存到 `pyramid_v2/data/sg_cache/<task_id>.<prompt_hash>.json` → `sg.match_events` 把每个 event 对到该 sub-goal 时间段内的 narration / sound_event / object_move / utterance 记录(词干匹配打分,声音事件没有对得上的记录就不出题)→ `sg.derived_relations` 补相邻 sub-goal 共享物体的 object_continuity → 四层 cluster。完整运行环境见 branch `v31`。
