#!/usr/bin/env python3
"""experiments/daily_report/1013.md:pyramid2 首轮小实验报告(叙述 + 两个 run 的 summary 自动拼表)。"""
import json, collections
from pathlib import Path
import p2config as P
from store import read_jsonl
import p2report

RUNS = {"hdepic": "p2_smoke_1012_hdepic", "ego4d": "p2_smoke_1012_ego4d",
        "hdepic·补测": "p2_fill_1013_hdepic", "ego4d·补测": "p2_fill_1013_ego4d",
        "hdepic·补测L1视觉": "p2_fill_1013b_hdepic", "tactile·补测": "p2_fill_1013_tactile", "tactile·补测b": "p2_fill_1013b_tactile",
        "hdepic·v3": "p2_v3_1013_hdepic", "ego4d·v3": "p2_v3_1013_ego4d",
        "hdepic·contact": "p2_contact_1013_hdepic", "ego4d·contact": "p2_contact_1013_ego4d"}
OUT = Path("/mnt/work_new/weihanxu/experiments/daily_report/1013.md")


def layer_rows(run_id):
    rd = P.RUNS / run_id
    rows = []
    for L in ("L1", "L2", "L3", "L4"):
        sp = rd / L / "summary.json"
        if not sp.exists():
            rows.append((L, None)); continue
        rows.append((L, json.loads(sp.read_text())))
    return rows


def overview_table():
    out = ["| dataset | layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | 无效 / 要求核验 | confirmation(skill: 结果 对/题) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for ds, rid in RUNS.items():
        for L, s in layer_rows(rid):
            if s is None:
                out.append(f"| {ds} | {L} | (未跑完) | | | | | | | | |"); continue
            if s["stop_reason"] == "SKIPPED_BY_CONTRACT": continue
            bv = s["by_verdict"]; conf = (s.get("confirmation") or {}).get("results") or {}
            cs = "; ".join(f"{k}: {v['result'].replace('confirmed_', '')} {v['correct']}/{v['n']}" for k, v in conf.items() if v.get("result")) or "-"
            out.append(f"| {ds} | {L} | {s['stop_reason']} | {s['turns']} | {s['scored']} | {s['correct']} | {s['raw_acc']} | {s['cluster_dedup_acc']} | {s['followup_items']} | {bv.get('item_invalid', 0)} / {bv.get('evidence_unresolved', 0)} | {cs} |")
    return out


def skill_table():
    out = ["| dataset | layer | capability skill | 诊断结论 | scored | 对 | cluster 数 | 首答对 | 支持的假设 | confirmation |", "|---|---|---|---|---|---|---|---|---|---|"]
    for ds, rid in RUNS.items():
        for L, s in layer_rows(rid):
            if s is None or s["stop_reason"] == "SKIPPED_BY_CONTRACT":
                continue
            conf = (s.get("confirmation") or {}).get("results") or {}
            inc = json.loads((P.RUNS / rid / "run_contract.json").read_text()).get("include_skills")
            for sk, v in s["by_skill"].items():
                if inc and sk not in inc: continue
                c = conf.get(sk)
                cs = f"{c['result'].replace('confirmed_', '')} {c['correct']}/{c['n']}" if c and c.get("result") else ("-" if v["verdict"] not in ("not_evaluated", "evidence_unresolved") else (v.get("reason") or "")[:70])
                out.append(f"| {ds} | {L} | {sk} | **{v['verdict']}** | {v.get('scored', '')} | {v.get('correct', '')} | {v.get('clusters', '')} | {v.get('cluster_first_correct', '')} | {', '.join(v.get('supported_hypotheses', [])) or '-'} | {cs} |")
    return out


def usage_table():
    out = ["| run | role | calls | errors | tok_in | tok_out | tok_think |", "|---|---|---|---|---|---|---|"]
    tot = collections.Counter()
    for ds, rid in RUNS.items():
        u = p2report.usage_summary(P.RUNS / rid)
        for k, d in sorted(u.items()):
            out.append(f"| {ds} | {k} | {d['calls']} | {d['errors']} | {d['tok_in']:,} | {d['tok_out']:,} | {d['tok_think']:,} |")
            tot["calls"] += d["calls"]; tot["tok_in"] += d["tok_in"]; tot["tok_out"] += d["tok_out"]; tot["tok_think"] += d["tok_think"]
    out.append(f"| **合计** | | {tot['calls']} | | {tot['tok_in']:,} | {tot['tok_out']:,} | {tot['tok_think']:,} |")
    return out


def strategy_table():
    out = ["| dataset | layer | formats | strategies | follow-up 结果(假设类型 → verdict) |", "|---|---|---|---|---|"]
    for ds, rid in RUNS.items():
        for L in ("L1", "L2", "L3", "L4"):
            hp = P.RUNS / rid / L / "history.jsonl"
            if not hp.exists():
                continue
            diag = [h for h in read_jsonl(hp) if h["phase"] == "DIAGNOSIS"]
            if not diag:
                continue
            fm = dict(collections.Counter(h["format"] for h in diag if h["format"]))
            st = dict(collections.Counter(h["strategy"] for h in diag if h["strategy"]))
            fo = collections.Counter((h["tests_hypothesis"].split(":")[2], h["verdict"]) for h in diag if h.get("tests_hypothesis"))
            fos = ", ".join(f"{k[0]}→{k[1]}:{v}" for k, v in sorted(fo.items())) or "-"
            out.append(f"| {ds} | {L} | {fm} | {st} | {fos} |")
    return out


def examples(rid, n=2):
    out = []
    for L in ("L1", "L2", "L3", "L4"):
        hp = P.RUNS / rid / L / "history.jsonl"
        if not hp.exists():
            continue
        rows = [h for h in read_jsonl(hp) if h["phase"] == "DIAGNOSIS" and h["verdict"] in ("correct", "wrong")]
        for h in rows[:n]:
            opts = " / ".join(o[:40] for o in (h.get("options") or [])) if h.get("options") else "-"
            out.append(f"- **{L} {h['capability_skill']}** [{h['format']}] → {h['verdict']}(答 {str(h.get('parsed'))[:30]},参考 {str(h.get('reference'))[:40]})  \n  Q: {(h.get('question') or '')[:220]}  \n  选项: {opts}")
    return out


NARRATIVE_HEAD = """# 2026-10-13 pyramid2 首轮小实验:按 1012.md prompts 的 adaptive 诊断 examiner

接 [1012.md](1012.md)(prompt 设计 draft1)与 [1012_plan.md](1012_plan.md)(实现计划,10-12 批准)。代码 `agent/bench/pyramid2/`(README 在内),数据 `output/pyramid_v2/`。本文 §0 是**现行标准**(10-14 更新),§1–§4 是按时间的过程记录。

## 0. 现行评测标准(10-14 最新:prompt `physical-mental-draft2` + capability-v3)

**Prompt**:[1013_prompts.md](1013_prompts.md) = 1012.md §2–§6 原文 + contact-rich / 触觉反馈加项(shared 的 CONTENT COVERAGE 与 EVIDENCE DISCIPLINE,各层 TARGETS;详见 §1.1)。调用:system = shared + 当前层 prompt + harness 契约(输出 JSON 字段、题型规则、窗口 10–30 s、题面不得含标签 / 绝对秒数 / 答案 / 对之前作答的提示、转换由 controller 决定);user = §9 runtime context。Examiner `gcp/google/gemini-3.1-pro-preview`,Solver `gcp/google/gemini-3.7-flash`(每题独立调用,只收题面 + clip),judge 3.1-pro(简答 / plan)。

**分层标准(capability-v3)**:L1 = 一个时刻直接可观察;L2 = 理解一个 event(动作、角色、前后状态、短跨度先后、局部活动、模态对应);L3 = 跨 event 关系或推断;L4 = 给目标 / 状态 / 约束选行动。**需要接触反馈的能力不是单独轨道,每层各有一个 skill**;EPIC-KITCHENS 的 14 个 tactile 片段与主数据的 contact-rich 动作是同一组 skill 的两个证据源。

| 层 | skill(主数据 HD-EPIC / Ego4D) | contact-rich(主数据 ↔ EPIC-KITCHENS 片段) | 证据与限制 |
|---|---|---|---|
| L1 一个时刻 | sound_recognition、sound_event_count(只数非材质类别、实例间隔 ≥ 1 s)、spatial_near、spatial_side(参照系 = 相机佩戴者,问最左 / 最右;声音锚定版只作对照)、object_recognition、object_attribute_visible、hand_used、object_location_at_time、explicit_statement、participant_presence | contact_action_recognition ↔ tactile_check_recognition | Ego4D 无人工声音标注、无 3D → 声音 / 空间 skill NOT_EVALUATED;HD-EPIC 无语音 → explicit_statement / participant_presence 只在 Ego4D |
| L2 一个 event | action_recognition、event_object_role、object_state_change、action_temporal_order(三动作跨度 ≤ 15 s 且间隔 ≤ 5 s)、activity_recognition、sound_action_binding(两个旧 sound binding 合并)、utterance_speaker_binding | contact_feedback_binding ↔ sound_tactile_binding / visual_tactile_binding | sound_* 只在 HD-EPIC;utterance_* 只在 Ego4D |
| L3 跨 event / 推断 | inter_event_temporal_reasoning(跨度 > 15 s)、inter_event_spatial_extreme / order(答案物体在锚定时刻须不可见,否则按「末帧可答」排除)、action_purpose_inference、next_action_prediction、next_step_prediction、explicit_preference_statement | contact_state_inference ↔ tactile_hidden_state_inference / tactile_relation_inference / needs_touch_awareness | HD-EPIC 的 next_step 用官方 recipe 分段 + narration;cross_scene_spatial_reasoning 未实现(需相机位姿) |
| L4 规划 | goal_conditioned_planning | contact_conditioned_next_action ↔ tactile_aware_planning | HD-EPIC 任务 = 官方 recipe 分段 + 段内 narration,Ego4D = goalstep;failure_conditioned_replanning 未实现(无 replan 证据) |
| 对照 | noav_control(不给 clip)、needs_touch_control | | 定义在 capability_map,检索 / 无媒体变体尚未接(§5 第一条) |

classification_status 一律 provisional(按题型默认分配);逐题例外已自动化的:medium_order 的时间跨度、L3 空间题的可见性、sound_event_count 的类别与间隔。原 `pyramid/capability_map.json`(v2)不动,v3 由 `pyramid2/capmap.py` 的覆盖表生成到 `data/capability_map.json`。

**Adaptive 诊断与预算**(细节见 §1.2):程序选 skill → Examiner 看本层 history 出一题 → 程序校验 → Solver 独立作答 → 判分 → controller 按规则更新假设(偶然 / 干扰 / 题型 / 题目缺陷 / 能力不稳)。预算是用户超参数(`cli.py run --base --followups --confirm --max-hyp-tests`,默认 3/3/3/3):每 skill 3 个独立 cluster 的基础题 + 答错后最多 3 道追问 + 固定 CONFIRMATION 3 道单选(history 剥离,≥ 0.8 通过)。停止:有诊断价值 + 合格证据 + 预算 → 继续;诊断结束且有结论 → 一次确认;无证据 → NOT_EVALUATED;预算用完仍 open 的假设 → inconclusive。

**Review 站**:https://huggingface.co/spaces/WitneyWW/pyramid2-review ,只按层分 tab L1–L4,三个数据集的题混排、卡片标数据集,每题三项判断(题面 / 回答 / 参考答案)+ 参考答案依据的标注逐条列出。**Demo 站**:https://huggingface.co/spaces/WitneyWW/pyramid2-adaptive-demo ,HD-EPIC 每个 skill 的追问链与停止判定。

## 1. 做了什么(过程记录)

- **统一 evidence store**:HD-EPIC 6 视频 + Ego4D 8 视频的 annotation 全部转成 1012.md §8 的 evidence record(`data/evidence.jsonl`,60,647 条,含 1,916 条由 seed43 的 3D 推导复用得到的 `spatial_relation` 派生记录);evidence_id 稳定(上游 id 或内容 hash),`provenance.legacy_eid` 保留旧位置 id(旧 facts 的 16,123 条引用 100% 能 join);build 幂等;`media_manifest.jsonl` 14 个源视频;`items.jsonl` 4,781 条旧 QA 作 seed。
- **Examiner 调用**:system = 1012.md §2 shared prompt + 当前层 prompt + harness 输出契约;user = §9 runtime context JSON(当前 skill 的 evidence cluster + 窗口内其它证据 + 本层 history / coverage / 假设 / 预算)。输出按 §10 校验(`check_output`:cluster / evidence 归属、cutoff、窗口 10–30 s、题面不含绝对秒数 / 标签 / 答案 / 对之前作答的提示),不过的带错误反馈重试一次。
- **Adaptive 诊断循环**(用户 10-12 定):程序选 skill(有 open 假设的优先,其次题数最少);答错 → 四种追问:换 event(偶然?)/ 换干扰更少的 event(干扰?)/ 换题型(格式?)/ 请求核验(题目或 gold 问题?);结论 stable_pass / unstable / mixed / interference_sensitive / format_sensitive / item_defects_suspected / inconclusive / evidence_unresolved / not_evaluated。首轮每层固定 30 条计分题;10-13 起改为按 skill 预算(§0),之后进入一次**固定 CONFIRMATION**(每 skill 3 题,单选,阈值 0.8,history 全部剥离)。
- **Solver 隔离**:只收 `public`(题面 + 选项 + 任务条件)+ 实际裁出的 clip;每题独立一次调用,无历史、无反馈。
- **模型**:Examiner `gcp/google/gemini-3.1-pro-preview`,Solver `gcp/google/gemini-3.7-flash`,judge 3.1-pro(simple/plan 题);全部走 NVIDIA 网关。
- **首轮两个 run(10-12,capability-v2 + draft1)**:`p2_smoke_1012_hdepic`(P02 / P03 / P06 / P08-0620 / P09)与 `p2_smoke_1012_ego4d`(ab78f4e5 / 9adc0c59 / bd970f5b / 53da674a / e6f1accd,启用 explicit_statement / utterance_speaker_binding / object_recognition / hand_object_interaction_recognition 四个 extension skill)。之后的补测与重跑见 §4.4–§4.6。

**所有分数都是 provisional**:gold 是 Examiner 提的 `proposed_reference_answer`,未经人工核验;候选题全部在 `data/candidates.jsonl`(待 Validator / review 站核验)。

## 1.1 Prompt 更新:`physical-mental-draft2`(10-13 晚,contact-rich / 触觉反馈并入 generator prompt)

用户定:tactile 不是单独的轨道,每一层测试都要包含「需要接触反馈才能判断下一步」的题。做法是生成新版 prompt 文件 [1013_prompts.md](1013_prompts.md)(1012.md 的 §2–§6 原文 + 加项,原件不动),`pyramid2/prompts.py` 改读它,prompt_version = `physical-mental-draft2`。加项:

| 位置 | 加了什么 |
|---|---|
| Shared · CONTENT COVERAGE | 新域「contact-rich manipulation and tactile feedback」:只有摸才知道的属性(软硬、松紧、温度、质地、重量 / 满度、熟度)以及捏 / 按 / 拧 / 揉 / 搅 / 切 / 倒 / 刮等接触动作提供的反馈 |
| Shared · EVIDENCE DISCIPLINE | 触觉反馈永远不在 Solver 输入里;要区分「接触动作在画面 / 声音里显出来的」和「触觉属性本身」;词表推出的属性提示只是上下文不是 gold;只有摸才知道的状态,正确行为是说不可知或规划检查,不是猜 |
| L1 · CONTACT-RICH TARGETS | 识别看得见的接触动作和被接触的物体、用哪只手 / 工具;**不问**属性值(多硬 / 多紧 / 多热) |
| L2 · CONTACT-RICH TARGETS | 这个 event 里接触动作在感知什么反馈(阻力、软硬、粘附、满度),以及接触产生或揭示的 event 末状态(盖子拧不动了、面团不粘手了、锅满了);clip 没呈现的隐藏值不问 |
| L3 · PHYSICAL TARGETS | 从接触线索推断触觉 / 隐藏状态(含备选与不确定性);needs-touch 自知:「不摸无法判断」是合法且有时唯一正确的答案,要按此判分 |
| L4 · PHYSICAL PLANNING | 按刚获得的接触反馈选下一步(拧不动 / 还硬 / 还不粘:继续、停、调整或检查);状态无法用其它方式获知时计划要含触觉检查或等价手段并说明跳过的后果;记录的人类后续动作只是一个参考 |

证据侧对应:主数据用 narration 接触动词词表派生的 `contact_rich_action`(HD-EPIC 1,166 条、Ego4D 3,713 条;动作是人工标注,属性提示是词表,下一动作作 answer_only 参考),EPIC-KITCHENS 14 个片段是同一组能力的另一证据源。skill 对应:

| 层 | 主数据 skill | EPIC-KITCHENS 片段 skill |
|---|---|---|
| L1 | contact_action_recognition | tactile_check_recognition |
| L2 | contact_feedback_binding | sound_tactile_binding / visual_tactile_binding |
| L3 | contact_state_inference | tactile_hidden_state_inference / tactile_relation_inference / needs_touch_awareness |
| L4 | contact_conditioned_next_action | tactile_aware_planning |

注意:10-12/13 的首轮、补测、v3 重跑都用 draft1 prompt;`p2_contact_1013_*` 前几轮用 draft1,00:05 重启后(同 run_id 续跑)改用 draft2。重启的原因:draft1 下 Examiner 在 3 题全对后自己返回 `BEGIN_CONFIRMATION`,而进入确认阶段应由 controller 按预算决定;现在 harness 明确「转换由 controller 决定,Examiner 不返回 BEGIN_CONFIRMATION」,controller 收到时带反馈让它重出一题,两次仍如此记 `examiner_declined`(不计分、不计入核验计数)。

## 1.2 Adaptive 现在怎么实现(代码 `pyramid2/controller.py`,10-13 版)

**目的**:分辨一次答错是偶然、题目 / 标注有问题,还是这项能力确实不稳;测的是模型能否稳定答对这类题,不是被提示后能否改正。

**每一轮**(`controller.run_turn`):
1. **程序选 skill**(`pick_skill`,用户定):有待检验假设的 skill 优先;其次独立 cluster 不足基础数的 skill;再按已出题数最少。某 skill 的追问额度用完就不再追。
2. **检索证据**(`retrieve.clusters`):该 skill 的 anchor 事件切出 30 s 窗口(规划类是 cutoff 前 30 s),核心证据 + 窗口内其它 verified 证据(≤25 条,按相关性裁),每个 cluster 带干扰度(窗口内其它声音数 + 可见物体数 + 移动数)。每轮给 Examiner 2 个 cluster:正常覆盖给未用过的;检验「偶然 / 不稳」给新 event;检验「干扰」给干扰度低于原 event 的;检验「题型」只给原 event 并禁用已用过的题型。
3. **Examiner 看到的**(§9 runtime context):当前 skill 与 capability 映射、2 个 cluster 的证据(role = target / context,answer_only 单独标)、`verified_seed_items`(与该 cluster 共享证据、subtype 对得上的人工题,≤3 条)、本层 history(每题的 skill / cluster / 题型 / 策略 / 回答 / 判定)、coverage、open 假设与要求的 strategy、剩余预算。它出**一题**,输出按 §10 校验(`check_output`:cluster / 证据归属、cutoff、窗口 10–30 s、题面不含绝对秒数 / 标签 / 答案 / 对之前作答的提示、空间题须写明参照系与「最近 / 最远」、strategy 必须等于假设要求的、确认阶段题型固定);不过的带错误重试一次,再不过记 `item_invalid`。
4. **Solver 看到的**:只有 `public`(题面 + 选项 + 任务条件)+ 实际裁出的 clip(拼接段给段边界,有 cutoff 时说明 clip 在决策时刻结束);每题单独一次调用,无历史、无反馈。
5. **判分**:选择题规则判;简答 / plan 先规则再 Gemini judge(单独调用,只看冻结的 reference + rubric)。
6. **controller 更新假设**(规则,不靠模型):

| 情形 | 开的假设 | 下一题要求的 strategy | 判定 |
|---|---|---|---|
| 某 skill 第一次答错 | chance_error | same_skill_new_event(换 event 同 skill) | 新题对 → 偶然,关闭;又错 → 看原 event 干扰度:≥ 池子中位数开 interference,否则开 format_sensitivity |
| 干扰假设 | interference | same_skill_cleaner_event(干扰度更低的 event) | 对 → interference_sensitive;错 → 开 format_sensitivity |
| 题型假设 | format_sensitivity | same_event_new_format(同 event 换题型) | 对 → format_sensitive,原题标 needs_review;错 → 开 skill_unstable |
| 能力不稳 | skill_unstable | same_skill_new_event ×≤3 | 再错 ≥2 → supported;混合 → refuted,按独立 cluster 错误率判 unstable / mixed |
| Examiner 返回 REQUEST_VERIFICATION | item_defect(当轮开当轮关) | — | 该 cluster 冻结进人工核验队列;原题标 needs_review |

每个假设最多检验 `max_hypothesis_tests` 次,超过记 inconclusive;某 skill 连续 3 次要求核验 → 该 skill `evidence_unresolved`,只跳过它。

7. **什么时候停**(`decide`,用户定):仍有诊断价值(open 假设 / 有 skill 独立 cluster 不足)+ 有未用的合格 cluster + 有预算 → 继续;诊断结束且某 skill 有结论并还有未用 event → 一次固定 CONFIRMATION(每 skill `items_per_skill` 道单选,event 由 seed 抽,history 全部剥离,≥ 0.8 通过,不重复确认);没有 verified 证据的 skill → NOT_EVALUATED(不消耗预算);预算用完时仍 open 的假设 → inconclusive;整层没有任何 skill 有证据 → STOP_INSUFFICIENT_EVIDENCE。

**预算 = 用户的超参数**(按 quota 定,`cli.py run --base --followups --confirm --max-hyp-tests` 或 contract 字段):每 skill 基础题 = `per_skill_base` 个独立 cluster(默认 3),答错后最多追问 `per_skill_followups` 次(默认 3,覆盖偶然 → 干扰 → 题型三步),确认 `items_per_skill` 题(默认 3);层预算 = 有证据的 skill 数 × (base + followups)。首轮 run 用的是固定每层 30 题;10-13 起的补测与重跑都按 skill 预算。

**每个 skill 的结论**:stable_pass(≥ base 个独立 cluster 全对,最多 1 个被偶然解释掉的错)/ unstable / mixed / interference_sensitive / format_sensitive / item_defects_suspected / inconclusive / evidence_unresolved / not_evaluated;报告同时给 raw 与 cluster 去重准确率,追问题单列。

**分层(capability-v3,10-13 用户定)**:L1 = 一个时刻直接可观察(sound_recognition、sound_event_count、spatial_near / side、object_recognition、object_attribute_visible、hand_used、object_location_at_time、explicit_statement、participant_presence、tactile_check_recognition);L2 = 理解一个 event(action_recognition、event_object_role、object_state_change、action_temporal_order、activity_recognition、sound_action_binding、utterance_speaker_binding、sound / visual_tactile_binding);L3 = 跨 event 或推断(inter_event_temporal / spatial_*、action_purpose_inference、next_action / next_step_prediction、tactile_hidden_state / relation_inference、needs_touch_awareness);L4 = 规划(goal_conditioned_planning、tactile_aware_planning)。声音锚定的空间题从 L2 撤出,作 L1 spatial 的对照变体。sound_event_count 留在 L1(持续的检测计数,不涉及 event 间关系),但只数非材质类别、实例间隔 ≥ 1 s。空间题的派生记录加了 `relation_definition`(左右题的参照系是相机佩戴者,问的是「最右 / 最左」),L3 空间题要求答案物体在锚定时刻不可见,否则按「末帧可答」排除。

**模态与证据来源**:HD-EPIC 的视觉 L1 用物体可见区间 / mask 锚点 / narration 名词与左右手;L2 event 理解用 narration 的 verb–noun 对、物体位置变化,Ego4D 用 FHO / EASG / OSCC;tactile 用 EPIC-KITCHENS 14 个人工核验片段(属性 / 动作 / 为什么必须摸 / 后果 / 撞击声能否替代),人工题作 seed。

**Review 站**(仿 pyramid-review,一题一页,tab H1–H4 = HD-EPIC、E1–E4 = Ego4D,共 281 道计分题):私有 Space https://huggingface.co/spaces/WitneyWW/pyramid2-review ;回答同步到私有 dataset `WitneyWW/pyramid2-review-responses`(`pyramid2_review.csv`,列 timestamp / reviewer / section / question_id / turn / skill / question_check / answer_check / gt_check / note);clip 在私有 dataset `WitneyWW/pyramid2-review-media`。构建与发布脚本 `hf_space_pyramid2_review/build.py`(`python3 build.py` → `site/`;发布流程见 memory)。

**Adaptive 追问链 demo**(HD-EPIC L1–L3,每个 skill 一条链:答错 → 开假设 → 追问 → 结论 → 固定确认,每步显示 Examiner 看到的假设与候选 cluster、题面、Solver 回答、controller 的假设更新):私有 Space https://huggingface.co/spaces/WitneyWW/pyramid2-adaptive-demo ,代码 `hf_space_pyramid2_demo/build.py`。
"""

NARRATIVE_OBS = """
## 4. 观察

### 4.1 Examiner(gemini-3.1-pro-preview)的行为
- **证据不足时真的会拒绝出题**:HD-EPIC L1 的 spatial_near / spatial_side 一开始只给了 mask 的 3D 锚点(xyz 被我裁掉),Examiner 连续 4 次 `REQUEST_VERIFICATION`,要求「显式的距离 / 左右关系标注」。这是 1012.md §2「If evidence is insufficient, request … Do not guess」要的行为。修法是复用旧 `spatial.py` 的推导结果加入 `spatial_relation` 派生记录后,这两个 skill 才能出题。
- **被 `check_output` 拦下的输出**:窗口切到 cluster 之外、窗口只有 1.7 s、题面写源视频绝对秒数、自造 action 名(`generate_item`)、整个对象包成数组、JSON 被 thinking 吃掉输出配额截断(`examiner_max_tokens` 8192 → 16384 后消失)。全部有校验和重试,第二次仍不过记 `item_invalid`。
- **strategy 标注不严**:没有 open 假设时 Examiner 也常把 strategy 写成 `same_skill_new_event` 而不是 `coverage`(见 §3 策略分布);下一版要在 `check_output` 里强制「无假设 → coverage」。
- 题型选择保守:绝大多数是 single_choice;short_answer / multi_select 只在 format_sensitivity 追问时出现。
- Ego4D 上 `explicit_statement` 两次要求核验是对的:那几条 `utterance` 是 speaker −1、无文字的 AV 标注(已打 `EMPTY_TRANSCRIPT` / `UNKNOWN_SPEAKER` 并从检索排除)。

### 4.2 Solver(gemini-3.7-flash)
- 经网关 **关不掉 thinking**:`thinking_budget=0` 仍有约 250 个思考 token,`max_tokens=64` 会返回空;输出上限改 512 / 1024 后正常。报告里的 Solver 因此是「带 thinking 的 3.7-flash」。
- HD-EPIC:L2(单 event 内的声音-物体 / 声音-移动绑定、状态变化、局部活动识别)最稳;L1 的 **声音计数** 与 **左右方位** 基本不会;L3 的跨 event 空间极值 / 排序不稳,时序推理与目的推断稳定。
- 诊断结论与 CONFIRMATION 有几处不一致(如 HD-EPIC L1 spatial_near 诊断 6/6 全对但确认 1/3):确认只有 3 题、阈值 0.8,一题错就 fail;下一版要把确认题量和阈值作为 frozen_policy 的参数重新定,并让 Validator 先核验 gold 再下结论。
- **Ego4D L4 的分数由题型决定**:30 道 goal_conditioned_planning 里 Examiner 出了 14 道单选(规则判,11/14 对)和 16 道自由生成 plan(Gemini judge 对 Examiner 的参考步骤 + rubric 判,4/16 对);诊断结论 unstable,而 CONFIRMATION 按 frozen_policy 全是单选,3/3 通过。自由生成 plan 的低分一部分是 judge 对参考步骤的严格程度(参考未核验),一部分是 Solver 在 30 s 前文 + 目标句下给出的步骤与记录的人类后续不一致。L4 下一版要把题型固定并分别报告,plan 题的 rubric 需人工核验后再判。

### 4.3 数据与协议
- HD-EPIC L4 `STOP_INSUFFICIENT_EVIDENCE`:212 条 task_timeline 全是 draft,按政策不能进 verified pool;Ego4D L4 用 goalstep(官方人工)的 step / substep 出规划题。
- Ego4D 无完整声音标注 → 声音 / 空间 skill `NOT_EVALUATED`;两个 Ego4D 视频(4c642620、53da674a)没有音轨,裁剪时合成静音轨并标 `NO_SOURCE_AUDIO`。
- 单 skill 上限曾让 Ego4D L1 只出到 26 题(两个有证据的 skill 之一耗尽);已改为其它 skill 耗尽时放开。
- 某 skill 连续 3 次要求核验原本会停整层(HD-EPIC L1 第一次跑到 13 轮就停),已改为只跳过该 skill。

### 4.4 补测(10-13,run `p2_fill_1013_*`,按 skill 的预算:3 个独立 cluster 基础题 + 最多 3 道追问 + 确认 3 题)
- **HD-EPIC L3 next_step_prediction / L4 goal_conditioned_planning**:首轮没证据(task_timeline 全是 draft)。补测改用官方人工标注拼出任务:`recipe_timestamps` 的活动分段作 task_segment(goal = 活动标签),段内 narration 作 task_step(adapter `hdepic.recipe_tasks`,确定性 join,记 verified / join_of_dataset_gt;4 个视频 65 段可用,P08-0620 没有 recipe 标注)。结果:next_step_prediction 诊断 1/6(5 个 cluster)但确认 3/3;goal_conditioned_planning 诊断 4/6、确认 3/3。步骤粒度是 narration,比 Gemini 切的任务步骤细,Examiner 需要自己归纳 4–8 步参考计划(标 `STEPS_ARE_NARRATIONS`)。
- **Ego4D L1 participant_presence**(谁在说话 / 看向谁,AV 人工标注):诊断 3/6、确认 1/3 → 不稳定。
- **Ego4D L3 explicit_preference_statement**:Examiner 出了 4 题(全对)后连续 3 次 REQUEST_VERIFICATION,理由是剩余 utterance 只是对话碎片,不含明确偏好 → evidence_unresolved。这是数据侧限制:AV 子集这段录音里几乎没有明确偏好句。
- Ego4D 的声音 / 空间 skill 仍 NOT_EVALUATED(无人工声音标注、无 3D);tactile、hdepic_annot(hand_object_role)、replan、cross_scene_spatial_reasoning 的 adapter / 推导未接。
- 预算机制已改为 `budget_mode: per_skill`(contract 字段 `per_skill_base` / `per_skill_followups`;层预算 = 有证据的 skill 数 × 6,追问额度用完的假设记 inconclusive),首轮 run 仍是固定 30 题。

### 4.5 10-13 晚:视觉 L1、tactile 分层、capability-v3 L2 重构(全部按 skill 预算 3/3/3)
- **HD-EPIC L1 视觉感知**(run `p2_fill_1013b_hdepic`):object_recognition 5/6(确认 3/3)、object_attribute_visible 6/6(确认 2/3)、hand_used 2/6(确认 3/3)、object_location_at_time 4/6(确认 3/3)。L1 现在是视觉 4 + 声音 2 + 空间 2,不再偏音频。hand_used 的诊断与确认矛盾,怀疑题面锚定时刻不准,待 review。
- **tactile 分层**(runs `p2_fill_1013_tactile` / `p2_fill_1013b_tactile`,EPIC-KITCHENS 14 个人工核验片段,人工题作 seed):L1 tactile_check_recognition 6/6(确认 3/3);L2 sound_tactile_binding 6/6(3/3)、visual_tactile_binding 6/6(2/3);L3 tactile_property_inference 5/6(3/3)、tactile_hidden_state_inference 6/6(2/3)、tactile_relation_inference 6/6(3/3)、needs_touch_awareness 6/6(3/3,会承认「不摸无法判断」);L4 tactile_aware_planning 4/6(3/3)。比 10-02 的首跑高很多,但 gold 与人工说明同源、14 个片段被 8 个 skill 反复用,题间强相关,最需要人工核验。
- **capability-v3 L2 重构重跑**(`p2_v3_1013_hdepic` L1 + L2,`p2_v3_1013_ego4d` L2):
  - HD-EPIC L1(声音 / 空间 4 skill,空间题加了 relation_definition + 题面校验,计数只数非材质类别、实例间隔 ≥ 1 s):sound_recognition 4/6(确认 3/3)、spatial_near 3/6(2/3)、spatial_side 2/6(1/3)、sound_event_count 3/6(2/3);四个都被 interference 假设解释过 → 结论 unstable。和首轮相比 sound_recognition 从 6/6 降到 4/6,spatial_near 从 6/6 降到 3/6:题面校验后题更规范了,但分数更低,说明首轮那几道「全对」可能有措辞捷径。
  - HD-EPIC L2(理解一个 event):sound_action_binding 5/5(3/3)、object_state_change 5/5(3/3)、action_temporal_order 5/6(1/3)、activity_recognition 6/6(3/3)、action_recognition 5/8(3/3,mixed)、event_object_role 5/6(3/3)。
  - Ego4D L2:action_recognition 6/6(3/3)、event_object_role 5/6(3/3)、object_state_change 5/5(3/3)、activity_recognition 6/6(3/3)、action_temporal_order 5/8(2/3,unstable)、utterance_speaker_binding 2/5(无剩余 event,unstable)。
- 本日累计:582 条候选题(0 泄漏),review 站 561 张计分卡片(H1–H4 / E1–E4 / T1–T4),demo 站 32 个 skill 链。

### 4.6 contact-rich(10-13 深夜,runs `p2_contact_1013_{hdepic,ego4d}`,每层一个 skill,按 skill 3/3/3;前几轮 draft1、00:05 起 draft2)
| 层 | skill | HD-EPIC 诊断 / 确认 | Ego4D 诊断 / 确认 |
|---|---|---|---|
| L1 | contact_action_recognition | 6/6 · 3/3 | 6/6 · 3/3 |
| L2 | contact_feedback_binding | 6/6 · 3/3 | 6/6 · 3/3 |
| L3 | contact_state_inference | 6/6 · 3/3 | 6/6 · 3/3 |
| L4 | contact_conditioned_next_action | 5/6 · 2/3 | 6/6 · 3/3 |

**要警惕的捷径**:这批题几乎全对,但看题面就知道原因——「人拧了一根 cheese straw,这个接触动作主要感知什么反馈?」「只凭视频和音频,柜门的精确温度是多少?」这类题靠常识和题面本身就能答,不需要看 clip(后者的正确选项就是「无法判断」)。它测到的是 Solver 懂不懂「接触反馈」这个概念,还没测到它能不能从画面里读出接触线索。下一步必须加 **blind 对照**(同一题不给 clip,`noav_control`):blind 也对的题标 `shortcut_risk`,不算能力证据;同时让 Examiner 把题面里「做了什么动作」的描述去掉,改成只给时刻让 Solver 自己看。L4 的 HD-EPIC 一次错被判偶然、确认 2/3 fail,是唯一有区分度的信号。

## 5. 已知限制与下一步
-1. **contact-rich 题要做 blind 对照**(见 §4.6):不给 clip 再答一遍,blind 也对的标 shortcut_risk;并要求 Examiner 不在题面里复述接触动作。
0. **按 skill 预算全量重跑**:首轮是固定 30 题;现在 controller 支持按 skill 预算,把两个首轮 contract 加上 `budget_mode: per_skill` 重跑一遍即可与补测口径一致。
1. **gold 未核验**:`data/candidates.jsonl` 里的候选题要进 Validator / review 站核验后才能冻结为 `items.jsonl` 的 gold;本报告的准确率只能看相对趋势。
2. HD-EPIC L4 要先人工核验 task_timeline(review 站 P tab)才能出题;replan、tactile、hdepic_annot、object_memory 的 adapter 还没接(plan §7 第 5 步)。
3. `check_output` 要补:无假设时 strategy 必须是 coverage;确认阶段的 slot 格式与 skill 必须匹配(已有)。
4. CONFIRMATION 的题量 / 阈值、`min_distinct_clusters`、`max_hypothesis_tests` 都在 contract 的 frozen_policy 里,下一轮正式跑前定。
5. Examiner 单轮 20–35k 输入 token + 3–5k thinking,一层 45 轮约 1 小时;两个 run 共约 3.5 小时(含三次重启)。
"""


def build():
    L = [NARRATIVE_HEAD, "## 2. 每层概览", ""] + overview_table() + ["", "## 2.1 每层 × skill 诊断结论", ""] + skill_table()
    L += ["", "## 3. 题型 / 追问策略分布与 follow-up 结果", ""] + strategy_table()
    L += ["", "## 3.1 题目样例(每层前两道计分题)", "", "**HD-EPIC**", ""] + examples(RUNS["hdepic"]) + ["", "**Ego4D**", ""] + examples(RUNS["ego4d"])
    L += [NARRATIVE_OBS, "## 6. Gemini 用量(NVIDIA 网关,key_id 3948af16)", ""] + usage_table()
    L += ["", "完整轨迹:`output/pyramid_v2/runs/<run_id>/report.md`(每轮题面 / 回答 / 参考 / 策略);每轮发给 Examiner 的 context 在 `runs/<run_id>/contexts/`。", ""]
    OUT.write_text("\n".join(L))
    return OUT


if __name__ == "__main__":
    print(build())
