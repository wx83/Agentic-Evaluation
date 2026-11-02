# pyramid2 — 按 `experiments/daily_report/1012.md` 的 prompts 实现的 evidence store + adaptive examiner

设计与决定见 `experiments/daily_report/1012_plan.md`(2026-10-12 用户批准)。

## 布局

```
output/pyramid_v2/
  data/raw_annotations/<alias>     symlink -> 原始 annotation(hdepic / ego4d / hdepic_annot / epic_kitchens / object_memory / pyramid_seed43 / benchmarks)
  data/media_manifest.jsonl        一行一个源视频(ffprobe 的 fps / 分辨率 / 音轨 + 每个 annotation source 的 coverage)
  data/evidence.jsonl              统一 evidence record(1012.md §8):evidence_id 稳定(上游 id 或内容 hash),provenance.legacy_eid 保留 timeline_index 的位置 id
  data/items.jsonl                 已有 QA(pyramid 旧题 / HD-EPIC VQA / Ego4D nlq, egoschema, egoplan, videgothink)作 seed
  data/candidates.jsonl            Examiner 产出的候选题(report 时从 runs/<id>/candidates.jsonl 合并)
  data/capability_map.json         pyramid/capability_map.json 的生成副本 + lifecycle(high_plan_next=retired)+ medium_order.level_rule
  data/extension_registry.json     human-context / 物体识别等新 skill(provisional,默认不启用;run_contract.extension_registry.enabled_skills 启用)
  data/verification_policy.json    每个 source 的初始 verification 规则 + review CSV 映射
  data/build_manifest.json         每次 build 读过的文件 sha / 记录数
  contracts/<run_id>.json          run contract(模型、视频、预算、frozen_policy)
  runs/<run_id>/                   run_contract.json, L<k>/{history,hypotheses}.jsonl, L<k>/{state,summary}.json, contexts/, candidates.jsonl, usage.jsonl, run.log, report.md
  media/<dataset>/<video>/         非 HD-EPIC 的裁剪缓存(HD-EPIC 仍用 output/_shared/clips/)
```

## 命令

```bash
cd agent/bench/pyramid2
python3 build_data.py all                      # init + config + media + evidence + items + policy(幂等)
python3 build_data.py evidence --only ego4d    # 只重建某个来源
python3 cli.py check-joins                     # 旧 facts / task_timeline 的位置 id 100% 能 join
python3 cli.py dry-run --video P02-20240211-120927 --layer L2 --skill sound_object_binding --summary
python3 cli.py preflight --contract ../../../output/pyramid_v2/contracts/p2_smoke_1012_hdepic.json
python3 cli.py propose --contract <c> --video <v> --layer L1 --skill sound_recognition   # 单轮调试
./run_smoke.sh <contract.json> [L1 L2 ...]     # nohup 后台 + 同 run_id 自动续跑
python3 cli.py run --contract <c> --levels L1 --n 3 --mock "W,W,C"   # 离线 mock(状态机单测)
python3 cli.py report --run-id <id>            # report.md + 合并 candidates
python3 cli.py audit-leaks
```

## 预算超参数(用户按 quota 定)

`cli.py run` 的 `--base / --followups / --confirm / --max-hyp-tests` 覆盖 contract 里的 `per_skill_base`(每 skill 基础题 = 独立 cluster 数,默认 3)、
`per_skill_followups`(答错后最多追问几次:换 event → 换干扰更少的 event → 换题型,默认 3)、`frozen_policy.confirmation.items_per_skill`(确认题数,默认 3)、
`max_hypothesis_tests`(单个假设最多检验几次,默认 3)。给了任一项就切到 `budget_mode: per_skill`:层预算 = 有证据的 skill 数 × (base + followups),
轮次上限 = 1.5 × 层预算 + 3;追问额度用完的假设记 inconclusive。例:`python3 cli.py run --contract c.json --followups 1 --confirm 2`。
`include_skills` 只跑指定 skill(其它层记 SKIPPED_BY_CONTRACT)。

## 模块

| 文件 | 作用 |
|---|---|
| `p2config.py` | 路径、视频列表、prompt 切分表 |
| `schema.py` / `ids.py` | 字段词表与校验;稳定 id |
| `adapters/{hdepic,task_timeline,ego4d}.py` | 原始 annotation -> evidence record(后置:hdepic_annot / tactile / object_memory / benchmarks) |
| `build_data.py` / `policy.py` / `items.py` | 构建 data/*;verification 初始规则与 review 回填;seed items |
| `store.py` | 读 jsonl + 索引(by_video / by_kind / by_legacy / 区间) |
| `capmap.py` | capability-v2 解析(medium_order 逐题按跨度判 L2/L3) |
| `retrieve.py` | `SKILL_NEEDS`:skill -> anchor / core / future kinds;生成 evidence cluster(含干扰度) |
| `context.py` | §9 runtime context;`strip_for_confirmation` |
| `prompts.py` | 从 1012.md 切 shared + L1–L4 prompt;`HARNESS` 输出契约 |
| `examiner.py` | Examiner 调用(system/user 分离)、`check_output`、`solver_payload` |
| `controller.py` | adaptive 诊断循环(假设:chance_error / interference / format_sensitivity / item_defect / skill_unstable)、§0.2 停止判定、固定 CONFIRMATION、续跑 |
| `solver.py` / `grade.py` | Solver(内联 clip,模型钉死不回退)/ 规则判分 + Gemini judge(provisional) |
| `p2report.py` / `mock.py` | report.md;离线 mock |

## 已知限制(2026-10-12)

- gold 全部是 Examiner 的 proposed_reference_answer(未人工核验);open/plan 题由 Gemini judge 判。
- HD-EPIC L4:task_timeline 212 条全是 draft → `STOP_INSUFFICIENT_EVIDENCE`;Ego4D L4 用 goalstep(官方人工)的 step/substep。
- gemini-3.7-flash 经 NVIDIA 网关关不掉 thinking(`thinking_budget=0` 仍有思考 token),Solver 输出上限设 512/1024。
- `cross_scene_spatial_reasoning`、replan、tactile、hand_object_role 在 `retrieve.SKILL_NEEDS` 里是 None(无证据或未实现)。
