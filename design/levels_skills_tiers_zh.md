# pyramid2(HD-EPIC Method E,v16 / v17 sub-goal 结构)四层 × skill × 档位 一览

依据:`agent/bench/pyramid2/sg.py`(SKILL_DEFS / REL_DEFS / L2_WINDOWS / L3_MAX_SEC / l1_knob / _bands)、`staircase.py`(PLAN_U)、`retrieve.py`(skill_spec)、`data/skill_exclusions.json`。
通用规则:每个 skill 四档,1–3 档 single_choice、4 档 short_answer(object_grounding 全部 bbox,L4 3–4 档 plan);阶梯 2-down-1-up 找边界;一个 task = 一个官方 recipe step(goal),它的 sub-goal 由官方 step 文字给出,planner 只看文字写「必然发生的 event」,程序把 event 对到标注拿时间。

---

## L1 perception —— 一个 event 发生的那一刻,画面里有什么、在哪

- clip:event 中心 ±5 s(10 s);题面给 event 描述和它在 clip 里的时间位置。
- 档位规则(所有 L1 skill 共用):每道题必须锚在一条标注记录上,记录按「感知量」在本 task 内按秩分成四分位,1 档最易、4 档最难;4 档题型改短答。感知量按 skill 不同(见各 skill)。

| skill | 一句话测什么 | 锚记录(标注) | 1 → 4 档怎么分 |
|---|---|---|---|
| object_recognition | 这一刻手里拿的、正在操作的是什么物体 | action_narration | 干扰量 = 该时刻 ±5 s 内其它 narration 的条数,四分位;越多越难;4 档短答 |
| spatial_near | 这一刻,候选物体里哪个离参照物最近(3D 距离,与佩戴者位置无关) | spatial_relation(由官方 3D 位置派生) | 候选间的距离余量 margin 四分位,余量越小越难;4 档短答 |
| spatial_side | 这一刻,从佩戴者视角看候选物体里哪个最左 / 最右 | spatial_relation | 候选间的角度余量四分位,余量越小越难;4 档短答 |
| object_location_at_time | 这一刻物体被放到哪个台面 / 容器 / 固定物上 | object_location_transition | 放下处的物体 mask 面积四分位,越小越难;4 档短答 |
| object_grounding | 在一帧里框出 event 的目标物体 | object_mask_anchor | 目标框面积四分位,越小越难;四档都是 bbox(1 s clip 首帧),IoU ≥ 0.5 算对(v16qa 试 0.3) |

---

## L2 understanding —— 一个 sub-goal 里的一个 event,发生了什么

- clip 不超出该 sub-goal;题面只给 event 描述,不给时间。
- 档位规则(所有 L2 skill 共用):档 = 窗口长度。1 档 15 s、2 档 30 s、3 档整个 sub-goal(单选)、4 档整个 sub-goal(短答)。窗口以 event 为中心裁剪。

| skill | 一句话测什么 | 锚记录 |
|---|---|---|
| action_recognition | 这个 event 是什么动作(动词 + 宾语) | action_narration / hand_object_interaction |
| event_object_role | 动作作用在哪个物体上、用了什么工具、去向哪里 | action_narration / action_scene_graph |
| action_temporal_order | 同一 sub-goal 里相近的两个动作谁先谁后 | action_narration |
| object_state_change | 一次移动里物体从哪拿、放到哪 | object_location_transition / object_state_change |
| sound_action_binding | 听到的这个声音是哪个动作 / 物体发出的 | sound_event + action_narration |
| sound_movement_binding | 这个声音对应哪个物体的移动 | sound_event + object_location_transition |
| sound_anchored_spatial_near | 声音响起那一刻,候选物体里哪个离参照物最近 | spatial_relation + sound_event |
| sound_anchored_spatial_side | 声音响起那一刻,候选物体里哪个在佩戴者最左 / 最右 | spatial_relation + sound_event |

---

## L3 inference —— 相邻两个 sub-goal 的 event 之间的关系

- 关系由 planner 列出(只在相邻 sub-goal k−1 与 k 之间;违反相邻的丢弃),另按共享物体派生 object_continuity(≤8 条,标 derived,planner 关系先问)。
- clip 永远是一段连续视频;题面只说 sub-goal k 的对象 / 动作,不复述 k−1 的 event(那是答案)。
- 档位规则(所有 L3 skill 共用):档 = 窗口范围。1 档 = sub-goal k−1 + k 两段;2 档 = 前一个 + 这两个 + 后一个 sub-goal;3 档 = 以这两个为中心扩到 180 s(单选);4 档 = 同 3 档窗口,短答(自己说出关系)。没有前后 sub-goal 时 2 档不存在;180 s 不比 2 档大时 3 档沿用 2 档窗口。
- 已知实现偏差:相邻 sub-goal 在视频里不相邻(菜谱交错)时窗口没截断,v16 有 18 道 L3 clip 超过 200 s(最长 950 s)。

| skill(关系类型) | 一句话测什么 |
|---|---|
| cross_event_integration(object_continuity / state_change) | 同一食材 / 物体在前一个 sub-goal 被怎么处理过、放在了哪;状态从前一步到这一步怎么变(整个 → 切碎、空 → 满) |
| causal_prerequisite_reasoning(causal_prerequisite) | 这一步依赖前一步提供的什么(水从哪来、容器是谁准备的) |
| hidden_state_inference(hidden_state) | 前一步设定、现在画面里看不见的器具 / 容器状态(灶的档位、锅里有没有水) |
| spatial_state_integration(spatial_end_state) | 两步放置之后,候选物体里哪个离参照物最近 / 最远(需要 3D 记录;v16 的 task 里没有匹配到) |

v16 未纳入的 L3 skill(v12 / v13 有):inter_event_spatial_order / extreme、egocentric_frame_transform、gaze_primed_next_pickup、inter_event_temporal_reasoning(顺序题 v16 起去掉)。

---

## L4 planning —— 在 sub-goal 的起点,接下来该做什么

- 决策点 = 每个 sub-goal k(k ≥ 2)的起点 + task 结束点;clip = 前一个 sub-goal 整段(≥ 10 s),cutoff = 决策点;这一层显示官方 goal。
- 档位规则 = 题型 × 规模(staircase.PLAN_U):

| 档 | 题型 | 内容 |
|---|---|---|
| 1 | single_choice | 下一个 sub-goal 是什么,选项 = 官方给的四个选项(顺序打乱) |
| 2 | single_choice | 同上,但干扰项不能用官方选项,改从本 task 其它 sub-goal(已做过或还没到)或合理但错的动作里造 |
| 3 | plan(stages) | 写出剩下的阶段,cutoff 之后还剩 1–2 个 sub-goal |
| 4 | plan(stages) | 写出剩下的阶段,cutoff 之后还剩 3 个以上 sub-goal |

| skill | 一句话测什么 |
|---|---|
| goal_conditioned_planning | 已知 goal 和到目前为止做了什么,判断下一步 / 剩余步骤 |

plan 题判分:judge 按阶段逐条判 coverage、order、contradictions,三项全过算对;超出官方 step 范围的合理阶段(beyond_horizon)记录不扣分。
v16 未纳入:plan_gap_filling(v13 有,GAP_U:隐藏 1 / 2–3 / 1–2 / 3 步)。

---

## 全局拿掉的 skill(data/skill_exclusions.json,10-27 用户定)

contact_action_recognition(L1)、contact_feedback_binding(L2)、contact_state_inference(L3)等四个 contact skill:HD-EPIC 没有接触标注,题由 narration 动词词表造,v11 / v12 几乎全对,题太软。

---

## 分数怎么来(简版)

- 题:单选 / 多选规则判;短答先规则后 Gemini judge;bbox IoU;plan 三项;Gemini 三答取多数。无效题不计分、不动档。
- skill:阶梯边界 → skill 分 = 层号 + (边界 − 0.5)/4;mastery = 边界换算的 0–1。
- 层 = skill 分均值;pyramid = 四层 mastery 之和;高度 = 从 L1 起连续 mastery ≥ 0.5 的层数。
- 已知限制(10-30 盲测):L2 57%、L3 67% 的题不看视频也能答对;各层档位的通过率随档上升而非下降,档位尚未校准为难度。
