# 10-28 pyramid2 v15:sub-goal 结构版(用户定)

状态:task 55(P09 R02 S07,鸡肉芝士球裹粉)→ task 39(P07 R02 S02,鹰嘴豆冲洗擦干)Gemini 4 self 臂运行中(`run_v15.sh`,01:14 起)。代码 `agent/bench/pyramid2/sg.py`,prompt `1028_prompts_hdepic_e_v15.md`。

## 为什么改

v13 task 09 第一题就在 scope 外:`scope.cluster_steps` 只从 core 记录的 idx 取 sub-goal,spatial / sound / movement 锚的 cluster 没有 idx → scope 排序和 skill_scope 对 10 个 skill 失效。讨论后用户决定不修补,改结构。

## 设计(用户定)

| 层 | 单位 | clip | 四档 | 题面 |
|---|---|---|---|---|
| L1 perception | 一个 event 的时刻 | event ±5 s | 感知量四分位(spatial 余量 / 面积 / ±5 s 内 narration 数)+ 题型 | 给 event 描述 + clip 内时间位置 |
| L2 understanding | 一个 event | ≤ sub-goal:10 / 20 / 40 s / 整段 | 窗口长度 | 只给 event 描述,不给时间 |
| L3 inference | 跨 sub-goal 的相关 event | 1 档两段 10 s 拼接(无关内容剪掉);2 档 + 第三个相关 event;3 档混一段无关片段;4 档 A→B 连续 ≤180 s(顺序题 = 两长半段乱序) | 段数 | 不给 event 线索;顺序题段乱序 |
| L4 planning | sub-goal 起点的决策点 | 前一个 sub-goal 整段,cutoff = 决策点 | 题型 × 规模(v13 统一四档) | 显示 goal |

- planner(gemini-3.1-pro)只看 goal + sub-goal 文字,写「完成每个 sub-goal 必然发生的 event」(动作 / 声音 / 位置 / 状态)、L3 关系、L4 决策点;不看标注。程序把 event 对到 sub-goal 内 narration / sound / movement 拿时间;没列的不出题。
- history 按 sub-goal 分组(每组 ≤6,每层 ≤2),L1–L3 的 cutoff = clip 末尾;阶梯 2-down-1-up 起 2 档,无验证题。
- 暂未纳入:plan_gap_filling、inter_event_spatial_*、egocentric_frame_transform、gaze、L4 状态题。Qwen 待实测 180 s。

## task 55 / 39 dry-run

`runs/p2_hdepicE_1023t_g4_v15_self__{55,39}/sg_dry.md`:55 = 15 event 全部对上、5 关系、7 决策点;39 = 15 event、5 关系、6 决策点。task 55 没有 spatial 记录(spatial_near / side 不测);两 task 都没有 hidden_state / spatial_state 关系。

## 跑的过程中的修正(02:30–02:50)

- L3 乱序段的 cutoff 原取最后显示段的末尾,改为所有段最晚末尾;3–4 段拼接 clip 时长容差按段数放宽(bench/clips.py probe tol)。
- task 55 L3 每个 skill 只有 1–2 个 planner 关系,2 档答一题就 exhausted(cross_event 2.0、causal 2.0、temporal 1.75)。加 `sg.derived_relations`:只用 planner 列的 event 两两派生跨 sub-goal 的 temporal_order(≤6)和共享物体的 object_continuity(≤6),标 source = derived,planner 关系先问。task 39 的 L3 pool 由 4/12/4 变 26/34/4。task 55 的 L3、L4 待 39 跑完后用新代码重跑,gold 对应层重放。

## v16(10-28 下午,用户定):L2 / L3 阶梯重定义

| 层 | 1 档 | 2 档 | 3 档 | 4 档 |
|---|---|---|---|---|
| L1 | 10 s,感知量最易四分位,单选 | 第二四分位 | 第三四分位 | 最难四分位,短答 |
| L2 | 15 s,单选 | 30 s,单选 | 整个 sub-goal,单选 | 整个 sub-goal,短答 |
| L3 | sub-goal k + k+1 整段,单选 | 前一个 + 两个 + 后一个 | 以两个为中心扩到 180 s,单选 | 同 3 档,短答 |
| L4 | 单选官方选项 | 单选换干扰项 | 开放剩 1–2 阶段 | 开放剩 3+ 阶段 |

- L3 的关系只在相邻 sub-goal 之间(planner 关系违反的丢弃;派生关系只派生相邻共享物体的 object_continuity ≤8);顺序题(inter_event_temporal_reasoning)去掉;多选题去掉。
- L3 clip 永远是一段连续视频,题面只说后一个 sub-goal 的对象 / 动作,不复述前一个 event(程序查动词词干)。
- task 选 sub-goal 全部 < 90 s 的(21 个);先重跑 55 和 39(contracts v16_{self,gold}),run_v16.sh / run_v16_gold.sh;prompt 1028_prompts_hdepic_e_v16.md。
- v15 的 55 L3/L4 派生关系重跑已停止(旧设计),v15 结果保留在 Space 作对照。

## v16 的 L2 与 L3 的关系(同一个 event,L2 问它本身,L3 问它和前一个 sub-goal 的关系)

| | L2 understanding | L3 inference |
|---|---|---|
| 对象 | sub-goal k 里和 goal 相关的 event | 同一个 event 和相邻 sub-goal k-1 里 event 的关系 |
| 题问什么 | 这个 event 是什么动作、用什么、放到哪、哪个声音是它发的 | 这个食材之前被怎么处理过、这一步靠前一步的什么结果、状态从前一步到这一步怎么变、器具现在是什么状态 |
| 题面给什么 | event 的描述,不给时间 | 只给 sub-goal k 的对象或动作,不复述 k-1 的 event(那是答案) |
| clip | 不超出 sub-goal k:15 s / 30 s / 整段 / 整段 | 至少含 k-1 和 k 两段:两段 / 前加本加后 / 180 s / 180 s |
| 题型 | 1 到 3 档单选,4 档短答 | 同左 |
| 和下层的关系 | history 里带 L1 对这个 sub-goal 的题 | history 里带 L1、L2 对 k-1 和 k 两个 sub-goal 的题,所以 L2「认出了 k-1 的 event 是什么」会传给 L3 |

一句话:L2 是看懂一步,L3 是把这一步和上一步接起来;L3 的 clip 比 L2 的最长 clip 还长,多出来的正是上一步。

## 阶梯实际题数(v15 两个 task,每 skill 上限 12)

| 停止原因 | 用了几题 | skill 数(两 task 合计) |
|---|---|---|
| 两次反转收敛 | 5 到 8 | 11 |
| 到顶(4 档连对两次) | 6 到 10 | 6 |
| 到底(1 档连错两次) | 3 到 5 | 2 |
| 该档没题了(exhausted) | 1 到 7 | 10 |

每个 skill 平均 5 题左右,一个 task 70 到 78 题,没有 skill 到 12 题上限。瓶颈是题库不是收敛:L1、L2 每个 sub-goal 只能出一题;causal_prerequisite 两个 task 各只有 1 题。v16 起 task 39 用 `stair_start_from` 从 task 55 的边界起步(省爬坡的 1 到 3 题),exhausted 的 skill 只能靠多 task 累积。

## 10-29 01:13 self 对 goldlive(gold 臂自己走阶梯,history_mode=gold 直接 run;contracts v16_goldlive,run_v16_goldlive.sh)

| task | 臂 | L1 | L2 | L3 | L4 | pyramid | 计分题 |
|---|---|---|---|---|---|---|---|
| 55 | self | 0.31 | 0.50 | 0.66 | 0.75 | 2.22 | 65 |
| 55 | goldlive | 0.35 | 0.62 | 0.69 | 0.19 | 1.85 | 73 |
| 39 | self | 0.38 | 0.51 | 0.56 | 0.62 | 2.07 | 56 |
| 39 | goldlive | 0.62 | 0.79 | 0.69 | 0.44 | 2.54 | 40 |
| 07 | self | 0.50 | 0.55 | 0.53 | 0.62 | 2.21 | 76 |
| 07 | goldlive | 0.47 | 0.62 | 0.53 | 0.50 | 2.13 | 88 |
| 13 | self | 0.31 | 0.61 | 0.75 | 0.75 | 2.43 | 57 |
| 13 | goldlive | 0.44 | 0.52 | 0.88 | 0.75 | 2.59 | 83 |
| 05 | self | 0.33 | 0.51 | 0.38 | 0.75 | 1.96 | 72 |
| 05 | goldlive | 0.47 | 0.71 | 0.29 | 0.75 | 2.23 | 68 |

- L1 没有 history,两臂的 L1 差(−0.03 到 +0.24)就是整条流水线(Examiner 出题 + 阶梯 + Solver 三答)的重复噪声水平。
- L2–L4 的差大多在同一量级:L2 goldlive 4/5 高,L3 3/5 高,L4 3/5 低(55 从 0.75 跌到 0.19,L4 只有 3–4 题);pyramid 均值 self 2.18 / goldlive 2.27,3 个 task 高、2 个低。
- 结论:history 用参考答案还是模型自己的答案,对 Gemini 4 没有超出噪声的系统差别;要判 history 的作用需要同一 task 多次重复或 none 臂。
- Qwen v16(Qwen 出题 + Qwen 答,autofill 形式字段):55 = 1.05(39 计分 / 36 无效),39 = 0.69(28 / 33);self≈gold。Qwen 出题一半过不了校验。

## 10-29 17:40 v17(按 event 遍历,阶梯只管档位)对 v16,task 55 / 39 / 05,self 与 goldlive 各自走阶梯

v17 = sg.run_layer_events:L1–L3 按 planner event 时间顺序遍历(每 sub-goal ≤3 个 event),每个 event 对每个适用 skill 出一题,档 = 该 skill 当前档,2-down-1-up 只管档位,收敛后继续在边界档出题(verify);history 只带同 event 的下层题(每层 ≤3);L4 沿用 v16。contracts v17_{self,goldlive}__{55,39,05}。

| task | 版本 | 臂 | L1 | L2 | L3 | L4 | pyramid | 计分题 | 收敛 skill | L1/L2 event 覆盖率 |
|---|---|---|---|---|---|---|---|---|---|---|
| 55 | v16 | self | 0.31 | 0.50 | 0.66 | 0.75 | 2.22 | 65 | 9/12 | 60% |
| 55 | v16 | goldlive | 0.35 | 0.62 | 0.69 | 0.19 | 1.85 | 73 | 10/12 | 59% |
| 55 | v17 | self | 0.58 | 0.62 | 0.69 | 0.75 | 2.65 | 99 | 8/12 | 99% |
| 55 | v17 | goldlive | 0.35 | 0.54 | 0.69 | 0.31 | 1.90 | 102 | 8/12 | 100% |
| 39 | v16 | self | 0.38 | 0.51 | 0.56 | 0.62 | 2.07 | 56 | 8/14 | 58% |
| 39 | v16 | goldlive | 0.62 | 0.79 | 0.69 | 0.44 | 2.54 | 40 | 6/11 | 44% |
| 39 | v17 | self | 0.54 | 0.69 | 0.56 | 0.56 | 2.35 | 76 | 5/13 | 100% |
| 39 | v17 | goldlive | 0.54 | 0.73 | 0.56 | 0.56 | 2.40 | 74 | 6/13 | 98% |
| 05 | v16 | self | 0.33 | 0.51 | 0.38 | 0.75 | 1.96 | 72 | 8/17 | 81% |
| 05 | v16 | goldlive | 0.47 | 0.71 | 0.29 | 0.75 | 2.23 | 68 | 8/17 | 77% |
| 05 | v17 | self | 0.20 | 0.58 | 0.33 | 0.75 | 1.86 | 74 | 7/17 | 100% |
| 05 | v17 | goldlive | 0.33 | 0.52 | 0.33 | 0.75 | 1.93 | 72 | 7/17 | 98% |

- 覆盖率:v16 每个 skill 只问到 44–81% 的适用 event,v17 接近 100%。题数 v17 多 0–50%(55:99 对 65;05 持平)。
- self 对 goldlive 的差:v16 三个 task 为 −0.37 / +0.47 / +0.27,v17 为 −0.75 / +0.05 / +0.07。v17 在 39、05 上两臂几乎一致;55 的差全在 L1(0.58 对 0.35,L1 无 history)和 L4(0.75 对 0.31,3 题),仍是噪声。
- 收敛 skill 数没有变多:event 数仍少(每 skill 5–15 题),很多 skill 以 events_exhausted 收尾。

## 10-30 00:08 v16 新五个 task(16/24/29/44/54,5 个新参与者)self 与 goldlive

| task | sub-goal 数 | 臂 | L1 | L2 | L3 | L4 | pyramid | 计分题 |
|---|---|---|---|---|---|---|---|---|
| 16 | 11 | self | 0.53 | 0.78 | 1.00 | 0.38 | 2.69 | 79 |
| 16 | 11 | goldlive | 0.50 | 0.50 | 1.00 | 0.38 | 2.38 | 67 |
| 24 | 14 | self | 0.50 | 0.71 | 0.58 | 0.69 | 2.48 | 87 |
| 24 | 14 | goldlive | 0.45 | 0.59 | 0.58 | 0.69 | 2.31 | 80 |
| 29 | 10 | self | 0.23 | 0.69 | 0.69 | 0.50 | 2.11 | 80 |
| 29 | 10 | goldlive | 0.25 | 0.70 | 0.69 | 0.50 | 2.14 | 77 |
| 44 | 6 | self | 0.46 | 0.96 | 0.75 | 0.50 | 2.67 | 58 |
| 44 | 6 | goldlive | 0.36 | 0.90 | 1.00 | 0.50 | 2.75 | 64 |
| 54 | 10 | self | 0.58 | 0.64 | 1.00 | 0.00 | 2.22 | 72 |
| 54 | 10 | goldlive | 0.46 | 0.52 | 0.62 | 0.38 | 1.97 | — |

十个 task 合计(v16):self 与 goldlive 的 pyramid 之差均值接近 0、标准差约 0.3,与 L1(无 history)的噪声同量级;结论不变。

十个 task 汇总(v16):每层均值 self L1 0.41 / L2 0.65 / L3 0.69 / L4 0.56,goldlive 0.44 / 0.65 / 0.70 / 0.51;pyramid 均值 self 2.31(sd 0.25)、goldlive 2.29(sd 0.28);goldlive − self 逐 task −0.36 +0.47 −0.08 +0.16 +0.27 −0.31 −0.17 +0.03 +0.09 −0.25,均值 −0.02、sd 0.27。

## 10-30 13:00 v16qa:history 去选项 + bbox 阈值 0.3(用户:「可能要在 v16 上做这个改动」)

- 代码(都由合约键控制,默认不变,旧 run 不受影响;备份 *.bak_1030):
  - `history_render: "qa"`:chain.render / sg.render_grouped / answer_text 不展示 Options,选择题答案只给选项文字不带字母(gold 用 reference 展开,self 用 parsed 展开);history_for / controller / chain.replay 把合约键传进去,history_used 里记 render。
  - `bbox_iou_min: 0.3`:grade.py bbox 判对阈值从合约读,默认 0.5;reason 里记 `(min 0.3)`。按现有 self run 的 score 重算:Gemini v13–v17 81 道 bbox 题 21 对 → 42 对,Qwen 3 道 0 → 0。
- 合约 `g4_v16qa_{self,goldlive}__{55,39,05}`(= v16 同名合约 + 两个键;39 从 v16qa 55 的边界起步),`run_v16qa.sh`,两条线(55→39、05),日志 lane_v16qa_{a,b}.log,标 `V16QA_DONE`。预计每 run 1.3–1.6 h,全部约 6–7 h。
- 对照:v16 同三 task self / goldlive(上表)。

## 10-30 14:30 Gemini 4 总览页(用户:分数 + 每层通过率画图,附出题 / video / 答案)

- `hf_space_pyramid2_gemini_overview_1030/build.py` → 私有 Space `WitneyWW/pyramid2-gemini-overview-1030`。index:三组 inline SVG(每 task 的 pyramid 柱状图;每层通过率 = 该层计分题答对比例,点 = run、横线 = 版本均值;每层 mastery)+ 汇总 + 36 个 run 的表(v12/13/14/15 self,v16/v17 self + goldlive;gold 重放和 v16gl/v17gl 别名不列)。v16/v17 的 26 个 run 各一页题目 / clip / Solver 三答 / 参考答案 / judge 理由(只列计分题)。
- clip 复用主站已编码的 476 个(390 MB),所以这个 Space 一次推送就占 0.4 GB;再更新一两次要换 Space 或 squash。
- v16qa task 13 跑完后再 build 一次会自动加进去(VERSIONS 已含 v16qa)。

## 10-30 14:10 盲测诊断:v16 task 13 的题不给 clip、不带 history(run g4_v16_blindnone__13,replay 自 v16 self 13)

| 层 | 盲测通过率 | 看视频(self) | 单选盲测 |
|---|---|---|---|
| L1 | 7/17 = 41% | 10/17 = 59% | 7/12 = 58% |
| L2 | 12/26 = 46% | 24/26 = 92% | 11/22 = 50% |
| L3 | 8/11 = 73% | 10/11 = 91% | 7/9 = 78% |
| L4 | 0/3 = 0% | 3/3 = 100% | 0/2 |

- L3 的单选题四分之三不看视频也能答对(常识 + Examiner 写的干扰项可排除),L3 的高通过率大半是语言先验;L2 看视频 92% 对盲测 46%,是真正「要看」的层;L1 单选盲测 58% 也偏高(10 s clip 的题面已经描述了事件)。
- 结论:层间通过率 L3 > L2 > L1 不是能力差,是可猜性差;校准题库时要用盲测臂把「不看视频能答对」的题剔掉或改干扰项。

## 10-30 16:30 盲测扩到 v16 全部 10 个 task(runs g4_v16_blindnone__*,run_blindnone_v16.sh)

| 层 | 看视频通过率 | 盲测能对(可猜)占比 | 去掉可猜题后通过率 | 题数 |
|---|---|---|---|---|
| L1 | 118/169 = 70% | 44% | 48/95 = 51% | 169 → 95 |
| L2 | 334/404 = 83% | 57% | 123/174 = 71% | 404 → 174 |
| L3 | 84/93 = 90% | 67% | 22/31 = 71% | 93 → 31 |
| L4 | 29/36 = 81% | 25% | 22/27 = 81% | 36 → 27 |

- 去掉可猜题后 L3 = L2 = 71%,L1 51%,L4 81%;L3 高于 L2 的那部分完全是可猜题。L4 可猜比例最低(25%),计划题真的要看。
- 按 skill 剔题后掉得最多的:object_location_at_time(43 → 17 道,高档全错)、sound_action_binding(69 → 22,去猜后只过 1 档)、causal_prerequisite(26 → 7);event_object_role / sound_movement_binding / sound_anchored_spatial_near 去猜前后都在 1 档就过不了。
- mastery 不能剔题重算(阶梯路径);用「合并十个 task、从 1 档起连续通过率 ≥ 50% 的最高档」做代理的话 L1 0.60→0.50、L2 0.56→0.44、L3 0.83→0.50、L4 0.00→0.75,但代理对 1 档的几道题极敏感(L4 全部题时 1 档 0/3 就归零),只能看方向。
- 用途:校准题库时先过盲测臂,可猜题换干扰项或不计;声音类 skill 的高分不可信。

## 10-30 15:27 v16qa task 13 结果(history 去选项 + bbox IoU 0.3;self 与 goldlive 各自走阶梯)

| run | L1 | L2 | L3 | L4 | pyramid |
|---|---|---|---|---|---|
| v16 self | 0.31(10/17,无效 2) | 0.61(24/26,无效 17) | 0.75(10/11) | 0.75(3/3) | 2.43 |
| v16 goldlive | 0.44(16/22) | 0.52(33/44) | 0.88(13/14) | 0.75(3/3) | 2.59 |
| v16qa self | 0.38(13/19,无效 2) | 0.45(41/54,无效 0) | 1.00(12/12) | 0.44(5/7) | 2.27 |
| v16qa goldlive | 0.38(8/14,无效 5) | 0.54(42/54,无效 0) | 1.00(12/12) | 0.50(4/5) | 2.41 |

- bbox:阈值 0.3 多判对 1 道(IoU 0.39),object_grounding 边界 0.5(floor)→ 1.5;L1 +0.07。
- history 去选项:self 与 goldlive 的差仍在噪声内(2.27 对 2.41;v16 是 2.43 对 2.59),去掉选项没有让两臂拉开。history_used.render = qa,solver_prompt 里确认只有题面 + 答案文字。
- 不可比的部分:v16 的 L2 有 17 道无效(10-28 sg 匹配 bug),v16qa 时 sg.py 已被另一会话更新(10-29 13:12、10-30 13:21 两版),L2 无效 0,所以 L2 题集不同(26 对 54 道),L2 的 0.61 → 0.45 不能归到去选项;L3 / L4 题少,1.00 / 0.44 都是 3–12 道题的波动。
- 结论:两个改动都没有超出噪声;bbox 0.3 的作用符合预期(多过一档),history 去选项不改变 self≈gold。

## 10-31 减去盲测臂后的每层分数与通过率(v16 self,10 个 task 合计)

「分数」用四档均分代理(= 去盲测后每档通过率的平均,即期望能过的档数 / 4);阶梯 mastery 不能剔题重算,列原值作对照。

| 层 | 阶梯 mastery(原) | 通过率 全部 | 通过率 去盲测后 | 四档均分 全部 | 四档均分 去盲测后 | 题数 全部 → 剩 |
|---|---|---|---|---|---|---|
| L1 | 0.41 | 70% | 51% | 0.70 | 0.53 | 169 → 95 |
| L2 | 0.65 | 83% | 71% | 0.81 | 0.70 | 404 → 174 |
| L3 | 0.69 | 90% | 71% | 0.88 | 0.67 | 93 → 31 |
| L4 | 0.56 | 81% | 81% | 0.54 | 0.57 | 36 → 27 |

- 去盲测后四层通过率 51 / 71 / 71 / 81,四档均分 0.53 / 0.70 / 0.67 / 0.57:L2 ≈ L3,L1 最低,L4 居中;层间差比原来小一半。
- 去盲测后各档通过率仍随档上升(L1 39→45→79→50%,L2 55→68→75→82%),档位未校准的结论不变。
- skill 层面掉得最多:object_location_at_time 79→53%、sound_action_binding 81→55%、causal_prerequisite 88→57%、hidden_state 67→0%(1 题);L4 goal_conditioned_planning 81→81% 不变。

## 10-31 盲测臂补 v17(55/39/05)与 v16qa(13)

| 版本 | 层 | 看视频通过率 | 可猜占比 | 去掉可猜题后 |
|---|---|---|---|---|
| v17(3 task) | L1 | 37/58 = 64% | 41% | 16/34 = 47% |
| | L2 | 121/144 = 84% | 57% | 46/62 = 74% |
| | L3 | 32/36 = 89% | 67% | 8/12 = 67% |
| | L4 | 10/11 = 91% | 36% | 6/7 = 86% |
| v16qa(task 13) | L1 | 13/19 = 68% | 53% | 4/9 = 44% |
| | L2 | 41/54 = 76% | 59% | 13/22 = 59% |
| | L3 | 12/12 = 100% | 92% | 1/1 |
| | L4 | 5/7 = 71% | 29% | 5/5 |

- v17 与 v16 十 task 的数字几乎一致(可猜占比 L1 41–44%、L2 57%、L3 67%;去猜后 L1 47–51%、L2 71–74%、L3 67–71%);event 遍历不改变可猜性。
- v16qa task 13 的 L3 12 道里 11 道可猜,去猜后只剩 1 道。
