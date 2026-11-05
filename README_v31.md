---
pretty_name: pyramid2 v31 bundle (HD-EPIC Method E)
license: other
language: [zh, en]
---
# pyramid2 v31 bundle(11-04)— 换服务器跑 v30b / v31

同一内容也在 GitHub `wx83/Agentic-Evaluation` 的 branch `v31`(不含源视频)。这里(私有 HF dataset `WitneyWW/pyramid2-v31-1104`)多了 9 个源视频。

**状态(11-04 22:15 更新)**:v30b 的 61 / 62 / 63 三个 task 已在原服务器跑完,L1–L4 完整 history + score.json 都在 `pyramid_v2/runs/`,**不需要在新服务器重跑任何下层**;结果摘要见 §6。
新服务器只要:`hf download WitneyWW/pyramid2-v31-1104 --repo-type dataset --local-dir pyramid2_v31`(约 12 GB,含全部 9 个源视频和所有标注,不再依赖 /mnt/data_new)→ `pip install -r requirements.txt` → 设 `OPENROUTER_API_KEY` → `./run_v31.sh 61 62 13 55`(每 task 约 $5–10,只跑 L3 的三个 v31 skill)。held-out task(h4 / h5)要先 `./run_full.sh hX` 跑全四层再 `./run_v31.sh hX`。

## 0. 这是什么

pyramid2:给第一人称厨房视频(HD-EPIC,task = 官方 recipe step,sub-goal = 官方 sub-step)出题的自适应四层评测。
Examiner = Gemini 3.1 Pro(出题、sub-goal planner、judge),Solver = Gemini 4(`google/gemini-4-argon`,每题答 3 次取多数),都走 OpenRouter。
每个 skill 四档难度、2-down-1-up 阶梯找边界,mastery = (边界 − 0.5) / 4;每题先盲测(不看 clip、无 history),盲测答对即作废重出。
所有时间、位置、距离来自官方标注(narration / sound / object_move 3D / mask 3D / SLAM 位姿 / Digital-Twin fixture mesh),模型不生成时间戳。

| 层 | 输入 | skill(v30 / v31) |
|---|---|---|
| L1 Frame Perception | 单帧 | object_recognition、object_box_choice |
| L2 Localization × 模态 | 整个 sub-goal clip(起止各外伸 5–20 s) | 只画面(无声):action_recognition、event_object_role、action_temporal_order;只音轨(黑画面):sound_localization;视听:sound_action_binding、sound_movement_binding |
| L3 Spatio-temporal Reasoning | 连续 clip ≤ 60 s,时刻只用事件 / 声音描述 | 链式:sound_object_location、sound_object_nearest;3D:spatial_change、ego_direction_unseen、turn_to_face、spatial_near / side;v30b 还含 cross_event / object_location_at_time / object_state_change / causal / hidden_state;**v31 用下面三个替换这三个「读标注」的** |
| L4 Planning | 决策点前的 clip + 官方 goal | goal_conditioned_planning |

### v31 的三个 skill(`code/bench/pyramid2/v31rsn.py`)

| skill | 问法 | ground truth | 档 |
|---|---|---|---|
| object_location_at_event | 「<事件 B> 那一刻 X 在哪」,题面不提 X 被挪过、不提事件 A;选项 = fixture + 在佩戴者手里;X 在 A..B 之间必须挪过且位置变了(或挪 ≥ 2 次) | 官方 object_move 链 | A..B 之间移动次数四分位 |
| object_displacement_direction | 「从 A 到 B,X 整体被挪到了你的前 / 左 / 后 / 右」(位移向量在 B 时刻 SLAM 相机系的方位,余量 ≥ 15°)或「X 离 <fixture> 更近还是更远」(到 Digital-Twin fixture 质心的 3D 距离,|Δ| ≥ 0.3 m);位移 ≥ 0.3 m | start_xyz / end_xyz + 位姿 / mesh | 角度 / 距离余量四分位 |
| object_identity_continuity | 「B 用的 X 是不是 A 用的那个」(同名多实例;GT = association_id)/「A 到 B 之间 X 被放下几次」(object_move 计数) | association_id / object_move | A–B 间隔四分位 |

阈值按标注精度定(mask 3D 误差 ~0.05–0.1 m → 位移 ≥ 0.3 m;方向余量 15°),**不按某几个 task 的题量调**;出不了题的 task 报 NOT_EVALUATED。

### 题量与 task 选择(dry-run,不花钱)

| task | 说明 | location / displacement / identity |
|---|---|---|
| 61 P07_R07_S03、62 P08_R04_S04 | v30 / v30b 跑完的 task,L1 / L2 seed 已在本包 | 6 / 7 / 2、4 / 8 / 1(0.15 m 阈值时;0.3 m 下更少) |
| 13 P01_R05_S02、55 P09_R02_S07 | v28 跑过 | 10 / 12 / 2、0 / 4 / 0 |
| h1 P02_R06_S03、h2 P09_R03_S04 | held-out | 2 / 1 / 0、0 / 3 / 0 |
| h3 P09_R01_S02 | held-out | 5 / 4 / 2 |
| **h4 P08_R08_S04** | held-out,7 次 fixture 变化 | **12 / 5 / 8** |
| **h5 P08_R06_S02** | held-out | **9 / 12 / 3** |

题量取决于 task 的标注丰富度(≥ 0.3 m 移动数、fixture 变化数、同实例重复使用数),不取决于规则;所以要先用这三个数筛 task(h4 / h5 这类),而不是降阈值。63 / 39 一道都出不了(counter 内小位移、P02 无位姿),不在本包。

## 1. 目录

```
code/bench/pyramid2/   全部代码(v24.py 四层定义;v26ed / v27rf / v29sa / v30chain / v31rsn 各 skill 模块;sg.py 遍历与阶梯;chain.py history;controller / examiner / solver / grade;diag_run.py 诊断)
code/bench/{clips,config,primitives,prompt,timeline_index}.py, code/bench/pyramid/, code/gemini/{nv_gemini,or_gemini}.py
prompts/               所有 prompt(§4)
pyramid_v2/contracts/  v28(seed)、v30、v30b(61/62/63 + h1–h5 全四层)、v31(61/62/13/55 + h1–h5 只 L3)
pyramid_v2/data/       9 个视频的 evidence 子集(32,621 条官方标注记录)、media_manifest、capability_map、skill_exclusions、sg_cache(planner 缓存 15 个,含 h1–h5)
pyramid_v2/runs/       seed run:v28 13 / 55 的 L1+L2;v30b 61 / 62 / 63 完整四层(history / score.json / usage.jsonl / run.log,11-04 22:15 跑完)+ diag_v30b_61_62_63.txt
output/_shared/pose/   9 个视频的 SLAM 位姿缓存;hd-epic/Digital-Twin/meshes/{P01,P02,P07,P08,P09}/ fixture mesh
hd-epic/video/         9 个源视频全部在此(约 11.7 GB;11-05 起);hd-epic/annotations/…/priming_info.json gaze priming 官方标注(gaze_primed_next_pickup 用)
run_v31.sh  run_full.sh  setup_data.sh  requirements.txt
```

## 2. 安装与运行

```bash
pip install -r requirements.txt          # python >= 3.10;另需 ffmpeg / ffprobe
./setup_data.sh                          # 校验 / 补下 9 个源视频(整包 hf download 时已带上,可跳过)
export OPENROUTER_API_KEY=sk-or-...      # 或写进 .secrets/openrouter_key
./run_v31.sh 61 62 13 55                 # v31 只跑 L3,L1/L2 history 从 seed run(61/62/63 = v30b 跑完的,13/55 = v28)复制;每 task 约 $5–10
./run_full.sh h4 && ./run_v31.sh h4      # held-out:先用 v30b 规则跑全四层(约 $25–40),再跑 v31
```

脚本做的事:设 `P2_REPO / P2_ROOT / HDEPIC_ROOT / P2_POSE_DIR / GEMINI_BACKEND=openrouter` → 复制 seed 的 L1 / L2 → `cli.py sg-dry`(只建题池,打印三个 skill 的题数)→ `cli.py run --levels L3`(崩了同 run_id 续跑)→ `pyramid_score.py` + `diag_run.py`。
结果在 `pyramid_v2/runs/<run_id>/`:`L*/history.jsonl` 每题一行(question / options / reference / parsed / verdict / blind / sg 元数据),`candidates.jsonl`、`contexts/`(Examiner 的全部输入)、`usage.jsonl`(每次调用的 token)、`run.log`。

离线自检(不调模型):`cd code/bench/pyramid2 && P2_REPO=<本目录> python3 cli.py sg-dry --contract ../../../pyramid_v2/contracts/p2_hdepicE_1023t_g4_v31_self__h4.json`。

## 3. 每次 run 要看的三项诊断(`diag_run.py <run_dir> ...`)

换数据集 / task 时先看这三项有没有偏,再看分数:
1. 各 skill 盲猜率(四选一基线 25%;高于 45% = 选项或题面泄漏);
2. 参考答案字母分布(卡方对均匀;Examiner 写的选项、程序填的选项、时间段题分开);
3. 程序出题的余量分位数(档位是否覆盖 1–4)。
另输出 Examiner 调用 / turn、校验拒绝数、盲猜作废数(token 浪费;Examiner 占总 token 85% 以上,每次输入约 33k)。

已知并已修的泄漏(v31 起生效;v30b 的 run 是旧代码跑的,spatial_change 仍带此偏置):v24–v30 的 spatial_change 程序填选项答案在第一位(A 占 52%、盲猜 60%);Examiner 写的选项正确项 70–80% 在 A;时间段题正确段在 A / D 两端且最长。修法:程序填的候选按种子打乱、Examiner 写的选项打乱、时间段四段等长 + 两侧均匀 + clip 起止外伸。

## 4. prompt 清单(prompts/)

| 文件 | 用在哪 |
|---|---|
| 1104_prompts_hdepic_e_v30.md | 合约 `prompt_md`:Shared Examiner System Prompt(## 2.)、L1–L4 各层 prompt(## 3.–6.)、task context(## 7.)、sub-goal planner(## 8.);末尾 v30 additions |
| examiner_system_L1..L4.md | 程序拼好的 Examiner system prompt 全文(shared + 层 prompt + task context + 全部 HARNESS 规则,L3 约 42k 字符) |
| planner_subgoal_events.md | sub-goal planner:只看 goal + sub-goal 文字写必然发生的 event;缓存在 pyramid_v2/data/sg_cache |
| judge_single.md / judge_plan_stages.md | judge |
| solver_prompt_template_*.md | Solver 收到的文字(history 事实句 + 模态说明 + 题 + 作答格式);clip 内联随请求发出 |
| solver_blind_preamble.md、history_facts_headers.md | 盲测前言;history 事实句抬头(v31 用 neutral) |
| 1102_prompts_hdepic_e_v24.md | v28 seed run 用的 prompt(可追溯) |

history 事实句由 `chain.render_facts_prog` 程序生成(`history_render = facts2`),不调模型。

## 5. 合约里和费用 / 并发有关的字段

`solver_reps`(3)、`unit_retries`(2)、`examiner_attempts`、`blind_mark_only`(false = 所有 skill 盲猜作废)、`blind_hard_skills`、`l2_modality`、`history_render`、`include_skills`。
减少 token 的下一步(未做):程序填 L1 / L2 选项让盲猜回到基线、unit_retries → 1、按 skill 熔断、裁剪 Examiner 输入。

## 6. v30b 结果(61 / 62 / 63,Examiner Gemini 3.1 Pro,Solver Gemini 4,self 臂;11-04)

逐层(只算 correct / wrong 的判分题;三 task 合并):

| 层 | 通过率 v30 → v30b | mastery 61 / 62 / 63 | 判分题 / 盲猜作废 / 校验作废(v30b) |
|---|---|---|---|
| L1 Frame Perception | 92% → 92%(L1 与 v30 共用) | 0.69 / 0.78 / 0.81 | 39 / 60 / 7 |
| L2 Localization × 模态 | 54% → 73% | 0.46 / 0.62 / 0.49 | 114 / 136 / 3 |
| L3 Spatio-temporal | 76% → 69% | 0.42 / 0.42 / 0.54 | 110 / 142 / 19 |
| L4 Planning | 88% → 78% | 0.44 / 0.44 / 0.38 | 9 / 6 / 2 |

- mastery 在 L1 > L2 ≳ L3 ≈ L4 上单调(L2 / L3 在 61 / 62 持平,63 L3 反超);通过率 L1 > L2 > L3 > L4 **不成立**(L4 题少、L3 的 cross_event / object_location_at_time 仍 96–100%,这正是 v31 要换掉的三个)。
- L2 按模态:只画面 81%(62/77)、视听 58%(14/24)、只音轨 54%(7/13)。sound_action_binding 36%、sound_localization 54%,是 L2 最难的两类;v30 里 sound_action_binding 0/10 是选项顺序泄漏,修后回到 5/14。
- 链式 L3:sound_object_location 70%(7/10)、sound_object_nearest 58%(11/19);有 L2 history 与无 history 的通过率差在噪声内(67% vs 1/1;57% vs 60%),和 v28 的 gold≈self 一致——history 事实句对这几题没有可测的帮助。
- 时间段题:45/45 四段等长,正确段字母 A/B/C/D = 6/14/14/11(卡方 3.8,不显著),v30 的「正确段在 A/D」已消。
- 仍存在的泄漏(v31 代码已修,v30b 跑的是旧代码):L1 Examiner 写的选项答案偏 A(19/7/6/4,卡方 15.3);spatial_change 程序填选项答案在首位(盲猜 54%)。盲猜率高于 45% 的 skill 还有 object_recognition 63%、object_box_choice 58%、action_temporal_order 71%、sound_*_binding 75–77%、object_state_change 75%、causal 9/9——这些盲猜答对的题都已作废重出,不进分数,但占了 52% 的 turn(344/665),是 token 浪费主因。
- 费用(OpenRouter 标价,按去重后的 usage.jsonl):61 $27、62 $30、63 $31,合计 ≈ $89;Examiner 调用 213–237 次 / task,校验拒绝 132 次。

v31 建议(跑之前不必再改代码,但有两点可选):① 把 L1 / L2 的选项也改成程序打乱或程序填充(盲猜率 58–77% 的那几类),能把作废 turn 减一半;② `unit_retries` 2 → 1。两者都只影响 token,不影响题的定义。
