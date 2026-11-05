# pyramid2 v31 bundle(11-04)— branch `v31`:在另一台 server 上跑 v31 / v30b

同一内容(外加 P08 源视频)也在私有 HF dataset WitneyWW/pyramid2-v31-1104。

这个包把 pyramid2 当前代码(v31 状态)、全部 prompt、合约(= 全部超参数)、四个 task 所需的数据子集和下层 seed run 放在一起,
目标是在任何一台有 ffmpeg 和 OpenRouter key 的 Linux 机器上直接跑 v31(三个时空推理 L3 skill),也能跑 v30b(L2 模态条件 + 链式 L3,全四层)。

## 0. v31 在测什么

Examiner = Gemini 3.1 Pro 出题(含 sub-goal planner、judge),Solver = Gemini 4(`google/gemini-4-argon`,每题答 3 次取多数),都走 OpenRouter。
四层:L1 Frame Perception → L2 Localization × 模态(只画面 / 只音轨 / 视听)→ L3 Spatio-temporal Reasoning → L4 Planning。
每个 skill 四档难度,2-down-1-up 阶梯找边界,mastery = (边界 − 0.5) / 4;每题先盲测(不看 clip、无 history),盲测答对的题作废重出。

v31 只跑 L3 的三个新 skill(`code/bench/pyramid2/v31rsn.py`),它们替换原来只读标注的 cross_event / object_location_at_time / object_state_change:

| skill | 问法 | ground truth | 档 |
|---|---|---|---|
| object_location_at_event | 「<事件 B> 那一刻,X 在哪?」题面不提 X 被挪过、不提事件 A;选项 = fixture + 在佩戴者手里 | 官方 object_move 链 → B 时刻的 fixture / 手持 | A..B 之间 X 的移动次数四分位 |
| object_displacement_direction | 「从 A 到 B,X 整体被挪到了你的前 / 左 / 后 / 右」(SLAM 位姿)或「X 离 <fixture> 更近还是更远」(3D) | start_xyz / end_xyz + SLAM 相机位姿 / Digital-Twin fixture 质心 | 角度 / 距离余量四分位 |
| object_identity_continuity | 「B 用的 X 是不是 A 用的那个」/「A 到 B 之间 X 被放下几次」 | association_id / object_move 计数 | A–B 间隔四分位 |

题量(dry-run):task 61 = 6 + 7 + 2,62 = 4 + 8 + 1,13 = 10 + 12 + 2,55 = 0 + 4 + 0。63 / 39 出不了题(object_move 全是 counter 内小位移,P02 无 SLAM 位姿),不在本包。

## 1. 目录

```
code/bench/pyramid2/   pyramid2 全部代码(v24.py 四层定义;v26ed / v27rf / v29sa / v30chain / v31rsn 各 skill 模块;sg.py 遍历与阶梯;chain.py history;controller / examiner / solver / grade)
code/bench/{clips,config,primitives,prompt,timeline_index}.py, code/bench/pyramid/   依赖
code/gemini/{nv_gemini,or_gemini}.py   Gemini 调用 shim;GEMINI_BACKEND=openrouter 走 or_gemini(OpenAI 协议,视频内联)
prompts/               所有 prompt(见 §3)
pyramid_v2/contracts/  v28(seed 用)、v30、v30b、v31 合约
pyramid_v2/data/       四个视频的 evidence 子集(5935 条官方标注记录)、media_manifest、capability_map、skill_exclusions、sg_cache(planner 缓存,10 个)
pyramid_v2/runs/       seed run:v28 self 13 / 55 的 L1+L2,v30b self 61 / 62 / 63 的 L1(v30b 的 L2 等本机跑完再补)
output/_shared/pose/   四个视频的 SLAM 位姿缓存(pose_<video>.json)
hd-epic/Digital-Twin/meshes/{P01,P07,P08,P09}/   fixture mesh(OBJ)
hd-epic/video/         源视频不在 GitHub 里:P01 / P07 / P09 用 setup_data.sh 从公开数据集下载,P08 从私有 dataset WitneyWW/pyramid2-v31-1104(hd-epic/video/P08/)下载
run_v31.sh, setup_data.sh, requirements.txt
```

## 2. 安装与运行

```bash
pip install -r requirements.txt          # python >= 3.10;另需 ffmpeg / ffprobe 在 PATH
./setup_data.sh                          # 下载 P01 / P07 / P09 源视频(约 3.2 GB,来自公开数据集 WitneyWW/pyramid2-qwen-data-1028)
export OPENROUTER_API_KEY=sk-or-...      # 或把 key 写进 .secrets/openrouter_key
./run_v31.sh                             # = 61 62 13 55;也可 ./run_v31.sh 13
```

`run_v31.sh` 做的事:设 `P2_REPO / P2_ROOT / HDEPIC_ROOT / P2_POSE_DIR / GEMINI_BACKEND=openrouter` → 把 seed run 的 L1 / L2 复制进本 run 目录 →
`cli.py sg-dry`(只建题池,不花钱,打印三个 skill 的题数)→ `cli.py run --levels L3`(崩了按同 run_id 续跑)→ `pyramid_score.py`。
结果在 `pyramid_v2/runs/p2_hdepicE_1023t_g4_v31_self__<task>/`:`L3/history.jsonl` 每题一行(question / options / reference / parsed / verdict / blind),
`candidates.jsonl`、`contexts/`(Examiner 看到的全部输入)、`usage.jsonl`(每次模型调用的 token)、`run.log`。

跑 v30b(全四层,L2 模态条件 + 链式 L3):同样的环境变量下 `cd code/bench/pyramid2 && python3 cli.py run --contract $P2_ROOT/contracts/p2_hdepicE_1023t_g4_v30b_self__61.json --levels L1 L2 L3 L4`。

离线自检(不调模型):`cd code/bench/pyramid2 && P2_REPO=<本目录> python3 cli.py sg-dry --contract ../../../pyramid_v2/contracts/p2_hdepicE_1023t_g4_v31_self__61.json`,看 `pyramid_v2/runs/<run>/sg_dry.md`。

## 3. prompt 清单(prompts/)

| 文件 | 用在哪 |
|---|---|
| 1104_prompts_hdepic_e_v30.md | 合约 `prompt_md`:Shared Examiner System Prompt(## 2.)、L1–L4 各层 prompt(## 3.–6.)、task context(## 7.)、sub-goal planner(## 8.);末尾 v30 additions |
| examiner_system_L1..L4.md | 程序拼好的 Examiner system prompt 全文 = shared + 该层 prompt + task context + HARNESS 规则(含 v24 四层规则和每个 skill 模块的 HARNESS;L3 约 42k 字符) |
| planner_subgoal_events.md | sub-goal planner(Gemini 3.1 Pro):只看 goal + sub-goal 文字写必然发生的 event;结果缓存在 pyramid_v2/data/sg_cache |
| judge_single.md / judge_plan_stages.md | judge(单选 / 短答;plan 题按阶段) |
| solver_prompt_template_*.md | Solver 收到的文字(history 事实句块 + 模态说明 + 题 + 作答格式);clip 以内联视频随请求发出 |
| solver_blind_preamble.md | 盲测臂的前言 |
| history_facts_headers.md | history 事实句的三种抬头(neutral / own / verified;v31 用 neutral) |
| 1102_prompts_hdepic_e_v24.md | v28 seed run 用的 prompt(只为可追溯) |

history 的事实句由 `chain.render_facts_prog` 程序生成(合约 `history_render = facts2`),不调模型。

## 4. 合约里和费用 / 并发有关的字段

`solver_reps`(3)、`unit_retries`(2,盲猜作废后重出次数)、`examiner_attempts`、`blind_mark_only`(false = 所有 skill 盲猜作废)、`blind_hard_skills`、`l2_modality`、`history_render`、`include_skills`。
本机实测:Examiner 占 token 的 85% 以上(每次输入约 33k,大量命中缓存),v31 四个 task 只跑 L3 约 60 题,按 OpenRouter 标价约 $15,实际扣费约一半。

## 5. 已知限制

- seed run 里 61 / 62 的 L2 来自 v30b,本机 v30b 还在跑,这一版包里只有它们的 L1;脚本会提示并只带 L1 history。v30b 跑完后会补传 L2。
- 代码里 `.bak_*` 备份、daily_* 脚本、Qwen 服务端没有打包。
- HD-EPIC 官方标注原文件不在包里(evidence.jsonl 已是程序化后的记录);只有 eye-gaze priming skill 需要原文件,v31 不用。
