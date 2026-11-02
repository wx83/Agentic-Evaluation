"""skill -> 需要的 evidence;按 anchor 事件切 30 s 窗口生成 evidence cluster(核心证据 + 窗口内其它证据 + 干扰度)。"""
import random, collections
import p2config as P
import ids, capmap

W = P.CLIP_SEC
ALL_CTX = {"spatial_relation", "sound_event", "action_narration", "object_location_transition", "object_move", "object_visible_track",
           "object_mask_anchor", "recipe_step", "task_step", "task_segment", "utterance", "person_talking",
           "person_looking", "hand_object_interaction", "object_state_change", "activity_moment", "visual_query_track",
           "action_scene_graph", "object_parts_attributes"}

# capability_skill -> 需求。anchor: 决定窗口的事件;core: 出题依据;future: cutoff 之后、只给 Examiner 的 answer_only 证据
SKILL_NEEDS = {
    "sound_recognition":            {"anchor": ["sound_event"], "core": ["sound_event"], "skip_flags": ["BACKGROUND_CLASS"], "min_core": 1},
    "sound_event_count":            {"anchor": ["sound_event"], "anchor_pred": "countable_sound", "core": ["sound_event"], "skip_flags": ["BACKGROUND_CLASS"], "min_core": 2, "needs_complete": "hdepic.sound", "count_rule": True},
    "spatial_near":                 {"anchor": ["spatial_relation"], "anchor_value": {"relation": ["nearest", "near"], "anchor_kind": ["movement"]}, "core": ["spatial_relation", "object_location_transition", "object_move"], "min_core": 1},
    "spatial_side":                 {"anchor": ["spatial_relation"], "anchor_value": {"relation": ["side_left", "side_right", "ego_behind", "ego_sector"], "anchor_kind": ["movement"]}, "core": ["spatial_relation", "object_location_transition", "object_move"], "min_core": 1},
    "sound_object_binding":         {"anchor": ["sound_event"], "core": ["sound_event", "action_narration", "object_visible_track"], "skip_flags": ["BACKGROUND_CLASS"], "min_core": 2, "need_kinds": ["sound_event", "action_narration"]},
    "sound_action_binding":         {"anchor": ["sound_event"], "core": ["sound_event", "action_narration", "object_location_transition", "object_visible_track"], "skip_flags": ["BACKGROUND_CLASS", "MATERIAL_JUDGMENT_ONLY"], "min_core": 2, "need_kinds": ["sound_event", "action_narration"]},
    "action_recognition":           {"anchor": ["action_narration", "hand_object_interaction"], "anchor_pred": "has_verb", "core": ["action_narration", "hand_object_interaction", "object_location_transition", "object_visible_track"], "min_core": 2},
    "event_object_role":            {"anchor": ["action_narration", "action_scene_graph"], "anchor_pred": "has_roles", "core": ["action_narration", "action_scene_graph", "object_location_transition", "object_visible_track"], "min_core": 2},
    "object_state_change":          {"anchor": ["object_location_transition", "object_state_change"], "core": ["object_location_transition", "object_state_change", "action_narration", "hand_object_interaction"], "min_core": 1},
    "sound_movement_binding":       {"anchor": ["sound_event"], "core": ["sound_event", "object_location_transition", "object_move"], "skip_flags": ["BACKGROUND_CLASS"], "min_core": 2, "need_kinds": ["sound_event", "object_location_transition"]},
    "sound_anchored_spatial_near":  {"anchor": ["spatial_relation"], "anchor_value": {"relation": ["nearest"], "anchor_kind": ["sound"]}, "core": ["spatial_relation", "sound_event", "object_location_transition"], "skip_flags": ["BACKGROUND_CLASS"], "min_core": 2, "need_kinds": ["spatial_relation", "sound_event"]},
    "sound_anchored_spatial_side":  {"anchor": ["spatial_relation"], "anchor_value": {"relation": ["side_left", "side_right"], "anchor_kind": ["sound"]}, "core": ["spatial_relation", "sound_event", "object_location_transition"], "skip_flags": ["BACKGROUND_CLASS"], "min_core": 2, "need_kinds": ["spatial_relation", "sound_event"]},
    "activity_recognition":         {"anchor": ["recipe_step", "task_step", "activity_moment"], "core": ["recipe_step", "task_step", "activity_moment", "action_narration"], "min_core": 2, "anchor_verified_only": True},
    "action_temporal_order":        {"anchor": ["action_narration"], "core": ["action_narration"], "min_core": 3, "order_rule": "L2"},
    "inter_event_temporal_reasoning": {"anchor": ["action_narration"], "core": ["action_narration"], "min_core": 3, "window": 60, "order_rule": "L3"},
    "inter_event_spatial_extreme":  {"anchor": ["spatial_relation"], "anchor_value": {"relation": ["farthest", "nearest_final"]}, "core": ["spatial_relation", "object_location_transition"], "min_core": 2, "window": 60, "two_windows": True},
    "inter_event_spatial_order":    {"anchor": ["spatial_relation"], "anchor_value": {"relation": ["order_by_distance"]}, "core": ["spatial_relation", "object_location_transition"], "min_core": 2, "window": 60, "two_windows": True},
    "action_purpose_inference":     {"anchor": ["action_narration"], "core": ["action_narration", "task_step", "recipe_step"], "min_core": 2},
    "cross_scene_spatial_reasoning": None,          # 需要 pose 变换(旧 infer.py);本批不支持
    "next_action_prediction":       {"anchor": ["action_narration"], "core": ["action_narration"], "min_core": 2, "cutoff": "anchor_start", "future": ["action_narration", "next_active_object", "future_action_sequence"], "future_sec": 20, "future_max": 3},
    "next_activity_prediction":     None,           # retired
    "next_step_prediction":         {"anchor": ["task_step"], "core": ["task_step", "task_segment", "action_narration"], "min_core": 2, "cutoff": "anchor_start", "future": ["task_step"], "future_sec": 120, "anchor_verified_only": True, "pre_sec": 30, "future_max": 3},
    "goal_conditioned_planning":    {"anchor": ["task_segment"], "core": ["task_segment", "task_step", "action_narration", "recipe_step"], "min_core": 2, "cutoff": "anchor_start", "future": ["task_segment", "task_step"], "future_sec": 600, "anchor_verified_only": True, "pre_sec": 30, "need_kinds": ["task_segment", "task_step"], "skip_flags": ["WHOLE_VIDEO_GOAL", "DRAFT"], "anchor_min_steps": 2, "future_within_anchor": True},
    "plan_gap_filling":             {"anchor": ["task_step"], "core": ["task_step", "action_narration", "task_segment"], "min_core": 2, "gap": True, "anchor_verified_only": True},   # 10-24:头尾两段 clip,隐藏中间 sub-goal
    "failure_conditioned_replanning": None,         # 无 replan 证据
    "tactile_property_inference":   {"anchor": ["tactile_property_episode"], "core": ["tactile_property_episode"], "min_core": 1, "window": "anchor"},
    "sound_tactile_binding":        {"anchor": ["tactile_property_episode"], "anchor_value": {"impact_sound_resolves": ["yes", "partial"]}, "core": ["tactile_property_episode"], "min_core": 1, "window": "anchor"},
    "visual_tactile_binding":       {"anchor": ["tactile_property_episode"], "core": ["tactile_property_episode"], "min_core": 1, "window": "anchor"},
    "tactile_hidden_state_inference": {"anchor": ["tactile_property_episode"], "core": ["tactile_property_episode"], "min_core": 1, "window": "anchor"},
    "tactile_relation_inference":   {"anchor": ["tactile_property_episode"], "core": ["tactile_property_episode"], "min_core": 1, "window": "anchor"},
    "tactile_check_recognition":    {"anchor": ["tactile_property_episode"], "core": ["tactile_property_episode"], "min_core": 1, "window": "anchor"},
    "needs_touch_awareness":        {"anchor": ["tactile_property_episode"], "core": ["tactile_property_episode"], "min_core": 1, "window": "anchor"},
    "tactile_aware_planning":       {"anchor": ["tactile_property_episode"], "core": ["tactile_property_episode"], "min_core": 1, "window": "anchor"},
    "contact_action_recognition":   {"anchor": ["contact_rich_action"], "core": ["contact_rich_action", "action_narration", "object_visible_track"], "min_core": 2},
    "contact_feedback_binding":     {"anchor": ["contact_rich_action"], "core": ["contact_rich_action", "action_narration", "object_location_transition", "object_state_change"], "min_core": 2},
    "contact_state_inference":      {"anchor": ["contact_rich_action"], "core": ["contact_rich_action", "action_narration"], "min_core": 2, "cutoff": "anchor_end", "future": ["action_narration"], "future_sec": 20, "future_max": 3, "pre_sec": 30},
    "contact_conditioned_next_action": {"anchor": ["contact_rich_action"], "anchor_pred": "has_next", "core": ["contact_rich_action", "action_narration", "task_segment"], "min_core": 2, "cutoff": "anchor_end", "future": ["action_narration"], "future_sec": 20, "future_max": 3, "pre_sec": 30},
    "no_av_control": None, "needs_touch_control": None,
    # 10-27 L3 扩展(l3ext.py):只在 hdepic_e 有 builder;基础条目占位让 controller.active_skills 放行
    "cross_event_integration":      {"anchor": ["task_step"], "core": ["task_step", "action_narration"], "min_core": 2, "l3ext": True},
    "hidden_state_inference":       {"anchor": ["action_narration"], "core": ["action_narration"], "min_core": 2, "l3ext": True},
    "spatial_state_integration":    {"anchor": ["object_location_transition", "object_move"], "core": ["object_location_transition", "object_move", "action_narration"], "min_core": 2, "l3ext": True},
    "causal_prerequisite_reasoning": {"anchor": ["task_step"], "core": ["task_step", "action_narration"], "min_core": 2, "l3ext": True},
    "egocentric_frame_transform":   {"anchor": ["object_location_transition", "object_move"], "core": ["object_location_transition", "object_move", "action_narration"], "min_core": 2, "l3ext": True},
    "gaze_primed_next_pickup":      {"anchor": ["object_visible_track"], "core": ["object_visible_track", "gaze_fixation", "action_narration"], "min_core": 2, "l3ext": True},
    "object_grounding":             {"anchor": ["object_mask_anchor"], "core": ["object_mask_anchor", "action_narration"], "min_core": 1, "l3ext": True},
    # 10-27 晚 AEA 专属(l3ext.py 末尾;标注 = 官方 MPS 位姿 / 视线 + SAM3 fixture 3D)
    "gaze_direction":               {"anchor": ["gaze_sample"], "core": ["gaze_sample", "action_narration", "sound_event"], "min_core": 1, "l3ext": True},
    "sound_source_localization":    {"anchor": ["sound_source_direction"], "core": ["sound_source_direction", "sound_event", "action_narration"], "min_core": 1, "l3ext": True},
    # extension registry
    "explicit_statement":           {"anchor": ["utterance"], "core": ["utterance"], "min_core": 1, "skip_flags": ["EMPTY_TRANSCRIPT"]},
    "participant_presence":         {"anchor": ["person_talking", "person_looking"], "core": ["person_talking", "person_looking", "utterance"], "min_core": 1},
    "object_recognition":           {"anchor": ["visual_query_track", "object_parts_attributes", "hand_object_interaction", "object_location_transition"], "core": ["visual_query_track", "object_parts_attributes", "hand_object_interaction", "action_narration", "object_location_transition", "object_visible_track"], "min_core": 2},
    "object_attribute_visible":     {"anchor": ["object_visible_track"], "anchor_pred": "has_attribute", "core": ["object_visible_track", "object_location_transition", "action_narration"], "min_core": 2},
    "hand_used":                    {"anchor": ["action_narration"], "anchor_pred": "has_hand", "core": ["action_narration", "object_visible_track"], "min_core": 2},
    "object_location_at_time":      {"anchor": ["object_location_transition"], "anchor_pred": "has_fixture", "core": ["object_location_transition", "object_mask_anchor", "object_visible_track"], "min_core": 2},
    "utterance_speaker_binding":    {"anchor": ["utterance"], "core": ["utterance", "person_talking"], "min_core": 2, "need_kinds": ["utterance", "person_talking"], "skip_flags": ["EMPTY_TRANSCRIPT", "UNKNOWN_SPEAKER"]},
    "explicit_preference_statement": {"anchor": ["utterance"], "core": ["utterance"], "min_core": 1, "skip_flags": ["EMPTY_TRANSCRIPT"]},
    "hand_object_interaction_recognition": {"anchor": ["hand_object_interaction", "action_scene_graph"], "core": ["hand_object_interaction", "action_scene_graph", "action_narration"], "min_core": 1},
    "hand_object_role": None,
}

# 按数据集覆盖(10-14 EgoPlan):只有 narration 步骤 + goal 段的数据,把锚点 / cutoff 改到 plan 上;其它数据集不受影响
def _step_idx_ge2(a): return (a["value"].get("step_idx") or a["value"].get("idx") or 0) >= 2
# 10-24 L4 plan_gap_filling 参数(controller / chain.replay / cli.scope 从 contract 覆盖)
GAP_SIZES = [2, 3, 4]        # m:头 k 与尾 k+m 之间隐藏 m-1 个 sub-goal
GAP_HEAD_SEC = 6.0           # 段 1 = 头 sub-goal 的最后几秒
GAP_TAIL_SEC = 6.0           # 段 2 = 尾 sub-goal 的开头几秒(隐藏 1 步时);隐藏 ≥2 步时用 GAP_TAIL_FRAME_SEC(只给第一帧)
GAP_TAIL_FRAME_SEC = 1.0
TASK_DATASETS = {"egoplan", "hdepic_e", "aea_p"}     # 10-23:goal+plan 结构的数据集(sample_id / per_step / scope / task_context 都按这个集合判);10-27 晚 + aea_p(AEA protocol clip)
SKILL_NEEDS_BY_DATASET = {
    "hdepic_e": {
        "object_recognition":        {"anchor": ["action_narration"], "anchor_pred": "has_noun", "core": ["action_narration", "task_step"], "min_core": 1},
        "sound_event_count":         {"anchor": ["sound_event"], "anchor_pred": "countable_sound", "core": ["sound_event"], "skip_flags": ["BACKGROUND_CLASS"], "min_core": 2, "needs_complete": "hdepic_e.sound", "count_rule": True},
        "inter_event_temporal_reasoning": {"anchor": ["task_step"], "core": ["task_step", "action_narration"], "min_core": 3, "window": 120, "anchor_verified_only": True},   # 跨 sub-goal:顺序 / 计数 / 完成状态
        "plan_gap_filling":          {"anchor": ["task_step"], "core": ["task_step", "action_narration", "task_segment"], "min_core": 2, "gap": True, "anchor_verified_only": True},
        "goal_conditioned_planning": {"anchor": ["task_segment"], "core": ["task_segment", "task_step", "action_narration"], "min_core": 2,
                                      "cutoff": "anchor_end", "pre_sec": 30, "future": ["task_step"], "future_sec": 3, "future_max": 1,
                                      "need_kinds": ["task_segment", "task_step"], "anchor_min_steps": 3, "anchor_verified_only": True},
        "next_step_prediction":      {"anchor": ["task_step"], "anchor_pred": "step_idx_ge2", "core": ["task_step", "task_segment", "action_narration"], "min_core": 2,
                                      "cutoff": "anchor_start", "pre_sec": 30, "future": ["task_step"], "future_sec": 60, "future_max": 3, "anchor_verified_only": True},
    },
    "aea_p": {   # 10-27 晚:AEA protocol clip(goal / 步骤 = 模型候选,narration = 自动 caption,声音 = legacy);同 hdepic_e 去掉 sound_event_count(coverage 未知)
        "object_recognition":        {"anchor": ["action_narration"], "anchor_pred": "has_noun", "core": ["action_narration", "task_step"], "min_core": 1},
        "inter_event_temporal_reasoning": {"anchor": ["task_step"], "core": ["task_step", "action_narration"], "min_core": 3, "window": 120, "anchor_verified_only": True},
        "plan_gap_filling":          {"anchor": ["task_step"], "core": ["task_step", "action_narration", "task_segment"], "min_core": 2, "gap": True, "anchor_verified_only": True},
        "goal_conditioned_planning": {"anchor": ["task_segment"], "core": ["task_segment", "task_step", "action_narration"], "min_core": 2,
                                      "cutoff": "anchor_end", "pre_sec": 30, "future": ["task_step"], "future_sec": 3, "future_max": 1,
                                      "need_kinds": ["task_segment", "task_step"], "anchor_min_steps": 3, "anchor_verified_only": True},
        "next_step_prediction":      {"anchor": ["task_step"], "anchor_pred": "step_idx_ge2", "core": ["task_step", "task_segment", "action_narration"], "min_core": 2,
                                      "cutoff": "anchor_start", "pre_sec": 30, "future": ["task_step"], "future_sec": 60, "future_max": 3, "anchor_verified_only": True},
    },
    "egoplan": {
        "object_recognition":        {"anchor": ["action_narration"], "anchor_pred": "has_noun", "core": ["action_narration", "task_step"], "min_core": 1},
        "goal_conditioned_planning": {"anchor": ["task_segment"], "core": ["task_segment", "task_step", "action_narration"], "min_core": 2,
                                      "cutoff": "anchor_end", "pre_sec": 30, "future": ["task_step"], "future_sec": 3, "future_max": 1,
                                      "need_kinds": ["task_segment", "task_step"], "anchor_min_steps": 3, "anchor_verified_only": True},
        "next_step_prediction":      {"anchor": ["task_step"], "anchor_pred": "step_idx_ge3", "core": ["task_step", "task_segment", "action_narration"], "min_core": 2,
                                      "cutoff": "anchor_start", "pre_sec": 30, "future": ["task_step"], "future_sec": 60, "future_max": 3, "anchor_verified_only": True},
    }
}


EGOPLAN_L4_INTERMEDIATE = False       # 单视频演示 run(contract.l4_intermediate_cutoffs):L4 也可在中间步骤处截断出题
L4_INTERMEDIATE_PRED = {"egoplan": "step_idx_ge4", "hdepic_e": "step_idx_ge2", "aea_p": "step_idx_ge2"}   # 10-23:HD-EPIC sub-goal 从第 2 个起每个起点都是决策点
EGOPLAN_L4_INTERMEDIATE_SPEC = {"anchor": ["task_step"], "anchor_pred": "step_idx_ge4", "core": ["task_step", "task_segment", "action_narration"], "min_core": 2,
                                "cutoff": "anchor_start", "pre_sec": 30, "future": ["task_step"], "future_sec": 60, "future_max": 3, "anchor_verified_only": True}


def skill_spec(capability_skill, dataset=None):
    ov = SKILL_NEEDS_BY_DATASET.get(dataset or "", {})
    if capability_skill in ov:
        return ov[capability_skill]
    return SKILL_NEEDS.get(capability_skill)


def _entities(recs):
    s = set()
    for r in recs:
        for e in r.get("entities") or []:
            if e.get("id_space") != "name_only" or True:
                s.add(e.get("entity_id"))
    return s


def interference_egoplan(store, video_id, t0, t1, core_ids):
    """plan 感知的干扰分(EgoPlan 没有声音 / 物体轨迹):窗口内其它步骤数 + 不同物体数 + 重复步骤数。"""
    recs = store.in_window(video_id, t0, t1, status="verified")
    core = set(core_ids)
    steps = [r for r in recs if r["kind"] == "task_step" and r["solver_access"] != "answer_only"]
    n_steps = sum(1 for r in steps if r["evidence_id"] not in core)
    n_obj = len({n for r in steps for n in (r["value"].get("nouns") or [])})
    texts = collections.Counter((r["value"].get("text") or "").strip().lower() for r in steps)
    n_rep = sum(c - 1 for c in texts.values() if c > 1)
    return {"n_other_steps": n_steps, "n_objects": n_obj, "n_repeated_steps": n_rep, "score": n_steps + n_obj + n_rep}


def interference(store, video_id, t0, t1, core_ids, dataset=None):
    if dataset in TASK_DATASETS:
        return interference_egoplan(store, video_id, t0, t1, core_ids)
    recs = store.in_window(video_id, t0, t1, status="verified")
    core = set(core_ids)
    n_snd = sum(1 for r in recs if r["kind"] == "sound_event" and r["evidence_id"] not in core and "BACKGROUND_CLASS" not in r["quality_flags"])
    n_obj = len({e["entity_id"] for r in recs if r["kind"] in ("object_visible_track", "object_move", "object_location_transition") for e in r["entities"]})
    n_mov = sum(1 for r in recs if r["kind"] in ("object_move", "object_location_transition", "object_state_change", "hand_object_interaction"))
    return {"n_other_sounds": n_snd, "n_visible_objects": n_obj, "n_movements": n_mov, "score": n_snd + n_obj + n_mov}


CTX_PRIORITY = ["action_narration", "sound_event", "object_location_transition", "utterance", "task_step", "task_segment",
                "hand_object_interaction", "object_state_change", "recipe_step", "activity_moment", "person_talking",
                "object_visible_track", "object_move", "action_scene_graph", "visual_query_track", "object_mask_anchor",
                "object_parts_attributes", "person_looking"]
SPATIAL = {"spatial_near", "spatial_side", "sound_anchored_spatial_near", "sound_anchored_spatial_side",
           "inter_event_spatial_extreme", "inter_event_spatial_order"}


def _trim_context(ctx, skill, cap=25):
    """窗口内其它证据按相关性裁剪:非空间题不给 mask 锚点;同类过多时保留时间均匀的子集。"""
    if skill not in SPATIAL:
        ctx = [r for r in ctx if r["kind"] != "object_mask_anchor"]
    ctx = [r for r in ctx if not (r["kind"] == "sound_event" and "BACKGROUND_CLASS" in r["quality_flags"])]
    pr = {k: i for i, k in enumerate(CTX_PRIORITY)}
    ctx.sort(key=lambda r: (pr.get(r["kind"], 99), r["time"]["start_sec"]))
    if len(ctx) <= cap:
        return sorted(ctx, key=lambda r: r["time"]["start_sec"])
    # 每种 kind 至多 cap//3,再按优先级填满
    out, per = [], collections.Counter()
    for r in ctx:
        if per[r["kind"]] < max(3, cap // 3):
            out.append(r); per[r["kind"]] += 1
        if len(out) >= cap:
            break
    return sorted(out, key=lambda r: r["time"]["start_sec"])


ATTR_WORDS = {"wooden", "wood", "metal", "glass", "plastic", "ceramic", "paper", "silver", "blue", "red", "green", "white", "black",
              "yellow", "pink", "orange", "grey", "gray", "brown", "small", "smaller", "large", "larger", "big", "empty", "clean", "dirty"}


def _has_attr(r):
    nm = (r["value"].get("name") or "").lower().split()
    return any(w in ATTR_WORDS for w in nm) and len(nm) >= 2


def _has_hand(r):
    h = r["value"].get("hands") or []
    return bool(h) and h != ["both hands", "right hand"]


def _has_fixture(r):
    return bool(r["value"].get("to_fixture_kind")) and r["value"].get("to_fixture_kind") != "mid-air"


def _has_verb(r):
    v = r["value"]
    return bool(v.get("verbs")) or (r["kind"] == "hand_object_interaction" and bool(v.get("label")))


def _has_roles(r):
    v = r["value"]
    if r["kind"] == "action_scene_graph":
        return "object" in (v.get("text") or "")
    return len(v.get("nouns") or []) >= 2 or bool(v.get("pairs"))


COUNTABLE = {"water", "beep", "open / close", "cut / chop", "stir / mix / whisk", "footstep", "rustle", "pour", "sizzling / boiling",
             "click", "spray", "zip", "scrub / scrape / scour / wipe", "slide object", "kettle / mixer / appliance", "hoover / fan"}


def _countable(r):
    """L1 计数只数不含材质判断的类别(collision 的材质标签是感知判断,见 1013.md)。"""
    return r["value"].get("label") in COUNTABLE


def _has_next(r):
    return bool(r["value"].get("next_actions_recorded")) and "NO_RECORDED_NEXT_ACTION" not in r["quality_flags"]


def _has_noun(r):
    return bool(r["value"].get("nouns"))


def _step_idx_ge3(r):
    return (r["value"].get("idx") or 0) >= 3


def _step_idx_ge4(r):
    return (r["value"].get("idx") or 0) >= 4


ANCHOR_PRED = {"has_attribute": _has_attr, "has_hand": _has_hand, "has_fixture": _has_fixture, "has_verb": _has_verb, "has_roles": _has_roles,
               "countable_sound": _countable, "has_next": _has_next, "has_noun": _has_noun, "step_idx_ge3": _step_idx_ge3, "step_idx_ge4": _step_idx_ge4, "step_idx_ge2": _step_idx_ge2}


def _window_for(spec, anchor, D):
    pre = spec.get("pre_sec")
    w = spec.get("window", W)
    a0 = anchor["time"]["start_sec"]
    if w == "anchor":                      # 用 anchor 自己的区间(tactile 片段 / 预切 clip)
        return [round(a0, 3), round(anchor["time"]["end_sec"], 3)], None
    aw = (anchor.get("value") or {}).get("window")
    if aw and len(aw) == 2 and spec.get("cutoff") != "anchor_start":
        return [round(float(aw[0]), 3), round(float(aw[1]), 3)], None
    if spec.get("cutoff") == "anchor_start":
        t0 = max(0.0, a0 - (pre or W)); t1 = a0
        if t1 - t0 < 5:
            return None
        return [round(t0, 3), round(t1, 3)], round(a0, 3)
    if spec.get("cutoff") == "anchor_end":
        a1 = anchor["time"]["end_sec"]; t0 = max(0.0, a1 - (pre or W)); t1 = a1
        if t1 - t0 < 5:
            return None
        return [round(t0, 3), round(t1, 3)], round(a1, 3)
    # 普通:anchor 居中
    t0 = max(0.0, a0 - w / 2); t1 = min(D, t0 + w)
    t0 = max(0.0, t1 - w)
    return [round(t0, 3), round(t1, 3)], None


def _step_idx_at(store, video_id, event_id, t):
    """10-27:task 数据集里无 step idx 的锚点(spatial / sound / movement)-> 所在 sub-goal 的 idx(scope 条目按 idx 对)。"""
    if not event_id: return None
    best = None
    for r in store.by_event.get(event_id, []):
        if r["kind"] != "task_step" or r["value"].get("is_next_action"): continue
        a, b = r["time"]["start_sec"], r["time"]["end_sec"]
        if a - 0.5 <= t <= b + 0.5: return int(r["value"].get("idx") or 0)
        d = min(abs(a - t), abs(b - t))
        if best is None or d < best[0]: best = (d, int(r["value"].get("idx") or 0))
    return best[1] if best and best[0] <= 30 else None


def model_checked(r, min_conf=0.7):
    """needs_verification 但有 Gemini supported 旁路核验且无 contradicted 的记录(geo3d dry-run 用)。"""
    if r["verification"]["status"] == "verified":
        return True
    if r["verification"]["status"] != "needs_verification" or "GEMINI_CONTRADICTED" in r["quality_flags"]:
        return False
    return any(str(c.get("method", "")).startswith("gemini4_") and c.get("verdict") in ("supported", "yes", "agree") and (c.get("confidence") or 0) >= min_conf
               for c in (r.get("checks") or []))


def clusters(store, video_id, capability_skill, *, seed=0, max_clusters=80, min_gap=10.0, modalities=("video", "audio"), _spec=None, accept_model_checked=False):
    """该 skill 在该视频上的候选 evidence cluster(已按 seed 打乱、去重叠)。空列表 = 该 skill 无合格证据。
    accept_model_checked=True:锚点 / 窗口记录放宽到「有 Gemini supported check 的 needs_verification」(只用于 geo3d dry-run,cluster 带 model_checked_only)。"""
    m = store.media_of_video(video_id)
    if m is None:
        return []
    spec = _spec or skill_spec(capability_skill, m.get("dataset"))
    if spec is None:
        return []
    if _spec is None and EGOPLAN_L4_INTERMEDIATE and m.get("dataset") in TASK_DATASETS and capability_skill == "goal_conditioned_planning":
        ispec = dict(EGOPLAN_L4_INTERMEDIATE_SPEC, anchor_pred=L4_INTERMEDIATE_PRED.get(m.get("dataset"), "step_idx_ge4"))
        extra = clusters(store, video_id, capability_skill, seed=seed, max_clusters=max_clusters, min_gap=min_gap, modalities=modalities, _spec=ispec)
        base_ = clusters(store, video_id, capability_skill, seed=seed, max_clusters=max_clusters, min_gap=min_gap, modalities=modalities, _spec=spec)
        for c in extra: c["l4_intermediate"] = True
        base_cuts = [c.get("observation_cutoff") for c in base_ if c.get("observation_cutoff") is not None]
        extra = [c for c in extra if not any(abs((c.get("observation_cutoff") or -1e9) - b) < 0.5 for b in base_cuts)]   # 10-21:中间截断点与官方截断重合的去掉
        return (base_ + extra)[:max_clusters]
    if spec.get("gap"):
        return gap_clusters(store, video_id, capability_skill, spec, m, seed=seed, max_clusters=max_clusters, modalities=modalities)
    if spec.get("l3ext"):                                      # 10-27 L3 扩展 skill:builder 在 l3ext.py
        import l3ext
        return l3ext.clusters(store, video_id, capability_skill, m, seed=seed, max_clusters=max_clusters)   # builder 自己只取 hdepic_e 记录(视频的 media 行可能是 legacy 数据集的)
    D = m["duration_sec"] or 1e9
    if spec.get("needs_complete"):
        cov = store.coverage(video_id, spec["needs_complete"])
        if not cov or cov["coverage"].get("completeness") != "complete":
            return []
    anchors = []
    for k in spec["anchor"]:
        anchors += store.of_kind(video_id, k, status="verified") if not accept_model_checked else [r for r in store.of_kind(video_id, k, status=None) if model_checked(r)]
    if m.get("dataset") in TASK_DATASETS:                       # 10-27:task 数据集只用本数据集的记录(同一视频的 legacy hdepic 记录是重复的 narration / sound / movement)
        anchors = [a for a in anchors if (a.get("provenance") or {}).get("dataset") == m.get("dataset")]
    skip = set(spec.get("skip_flags") or [])
    anchors = [a for a in anchors if not (skip & set(a["quality_flags"]))]
    if spec.get("anchor_value"):
        av = spec["anchor_value"]
        anchors = [a for a in anchors if all(a["value"].get(k) in vals for k, vals in av.items())]
    if spec.get("anchor_pred"):
        anchors = [a for a in anchors if ANCHOR_PRED[spec["anchor_pred"]](a)]
    if spec.get("anchor_verified_only"):
        from store import _status_ok
        anchors = [a for a in anchors if _status_ok(a, "verified")]
    if spec.get("anchor_min_steps"):
        anchors = [a for a in anchors if len((a["value"].get("steps") or [])) >= spec["anchor_min_steps"]]
    if not spec.get("cutoff"):                 # 没有 cutoff 的 skill 不能锚在 answer_only 记录上(EgoPlan 的 gold 下一步)
        anchors = [a for a in anchors if a["solver_access"] != "answer_only"]
    rng = random.Random(f"{seed}|{video_id}|{capability_skill}")
    rng.shuffle(anchors)
    out, used, used_steps = [], [], set()
    core_kinds, fut_kinds = set(spec["core"]), set(spec.get("future") or [])
    per_step = m.get("dataset") in TASK_DATASETS          # EgoPlan:每个锚点步骤最多一个 cluster(「换 event」= 换步骤)
    for a in anchors:
        wc = _window_for(spec, a, D)
        if wc is None:
            continue
        (t0, t1), cutoff = wc
        if per_step:
            sidx = (a["value"].get("step_idx") or a["value"].get("idx")) if a["kind"] in ("task_step", "action_narration") else None
            sk_ = (a["kind"], a.get("event_id"), sidx if sidx is not None else a["evidence_id"])   # 10-27:无 step idx 的锚点(spatial / sound / movement)按记录去重,不再整类只留 1 个
            if sk_ in used_steps:
                continue
            used_steps.add(sk_)
        if any(abs(t0 - u) < min_gap for u in used):
            continue
        recs = store.in_window(video_id, t0, t1, status="verified") if not accept_model_checked else [r for r in store.in_window(video_id, t0, t1) if model_checked(r)]
        if m.get("dataset") in TASK_DATASETS:
            recs = [r for r in recs if (r.get("provenance") or {}).get("dataset") == m.get("dataset")]
        recs = [r for r in recs if not (set(r["modalities_supporting_fact"]) - set(modalities) - {""}) or r["solver_access"] == "stipulated"]
        core = [r for r in recs if r["kind"] in core_kinds and not (skip & set(r["quality_flags"]))]
        if spec.get("cutoff") in ("anchor_start", "anchor_end"):
            # 核心 = anchor 本身 + cutoff 之后 future_sec 内的 future kinds(answer_only)+ 窗口内 observed 核心
            f_end = min(D, a["time"]["end_sec"]) if spec.get("future_within_anchor") else min(D, cutoff + spec.get("future_sec", 20))
            fut = store.in_window(video_id, cutoff, f_end, kinds=fut_kinds, status="verified")
            fut = [r for r in fut if r["time"]["start_sec"] >= cutoff - 1e-6 and not (skip & set(r["quality_flags"]))]
            if spec.get("future_within_anchor"):
                fut = [r for r in fut if r["evidence_id"] == a["evidence_id"] or (r["kind"] == "task_step" and r["time"]["end_sec"] <= a["time"]["end_sec"] + 0.1 and (r["value"].get("task_id") in (None, a["value"].get("task_id")) if r["provenance"]["dataset"] == "hdepic" else True))]
            fut = sorted(fut, key=lambda r: (r["evidence_id"] != a["evidence_id"], r["time"]["start_sec"]))
            if spec.get("future_max"):
                fut = [r for r in fut if r["evidence_id"] == a["evidence_id"]] + [r for r in fut if r["evidence_id"] != a["evidence_id"]][: spec["future_max"]]
            fut = [dict(r, solver_access="answer_only") for r in fut]
            if a["evidence_id"] not in {r["evidence_id"] for r in fut}:
                fut.insert(0, dict(a, solver_access="answer_only" if spec.get("cutoff") == "anchor_start" else "observed"))
            core = [r for r in core if r["time"]["end_sec"] <= cutoff + 1e-6] + fut
        else:
            core = [r for r in core if r["solver_access"] != "answer_only"]
        if a["evidence_id"] not in {r["evidence_id"] for r in core}:
            core.insert(0, a)
        need = set(spec.get("need_kinds") or [])
        if need and not need <= {r["kind"] for r in core}:
            continue
        if len(core) < spec.get("min_core", 1):
            continue
        if spec.get("min_entities") and len(_entities(core)) < spec["min_entities"]:
            continue
        if spec.get("count_rule"):
            lab = a["value"].get("label")
            same = sorted([r for r in core if r["kind"] == "sound_event" and r["value"].get("label") == lab], key=lambda r: r["time"]["start_sec"])
            gaps = [same[i + 1]["time"]["start_sec"] - same[i]["time"]["end_sec"] for i in range(len(same) - 1)]
            if len(same) < 2 or len(same) > 6 or (gaps and min(gaps) < 1.0):
                continue                   # 实例太少 / 太多 / 相邻间隔 < 1 s(「几次」有歧义)→ 不作计数 cluster
            core = same + [r for r in core if r not in same]
        if capability_skill in ("inter_event_spatial_extreme", "inter_event_spatial_order") and a["kind"] == "spatial_relation":
            # capability_map 例外「末帧直接可答归 L1」:答案物体在锚定时刻若可见,就不是跨 event 推理 → 跳过
            T = a["value"].get("anchor_time_sec") or a["time"]["start_sec"]
            ans = (a["value"].get("answer_object") or "").split(" -> ")[0].strip().lower()
            vis = {(r["value"].get("name") or "").lower() for r in store.in_window(video_id, T - 0.5, T + 0.5, kinds={"object_visible_track"}, status="verified")}
            if ans and ans in vis:
                continue
        if spec.get("order_rule"):
            narr = sorted([r for r in core if r["kind"] == "action_narration"], key=lambda r: r["time"]["start_sec"])
            if len(narr) < 3:
                continue
            # 取 anchor 附近连续三条,按 medium_order 规则判层
            i = next((j for j, r in enumerate(narr) if r["evidence_id"] == a["evidence_id"]), 0)
            trip = narr[max(0, i - 1): max(0, i - 1) + 3] if len(narr) >= 3 else narr
            sp = capmap._span(trip)
            lv = "L2" if sp and sp[0] <= 15 and sp[1] <= 5 else "L3"
            if lv != spec["order_rule"]:
                continue
            core = trip
        core_ids = [r["evidence_id"] for r in core]
        ctx = [r for r in recs if r["evidence_id"] not in set(core_ids) and r["kind"] in ALL_CTX and r["solver_access"] != "answer_only"]
        ctx = _trim_context(ctx, capability_skill)
        used.append(t0)
        out.append({"evidence_cluster_id": ids.cluster_id(capability_skill, video_id, t0, t1, core_ids),
                    "capability_skill": capability_skill, "video_id": video_id, "media_id": a.get("media_id") or m["media_id"],
                    "window": [t0, t1], "observation_cutoff": cutoff, "anchor_id": a["evidence_id"],
                    "sample_id": a.get("event_id") if m.get("dataset") in TASK_DATASETS else None,
                    "anchor_kind": a["kind"], "anchor_is_next": bool(a["value"].get("is_next_action")),
                    "anchor_step_idx": ((a["value"].get("step_idx") or a["value"].get("idx")) if a["kind"] in ("task_step", "action_narration") else None) if a["kind"] in ("task_step", "action_narration") else _step_idx_at(store, video_id, a.get("event_id"), a["time"]["start_sec"]),
                    "core": core, "context": ctx, "two_windows_allowed": bool(spec.get("two_windows")),
                    "interference": interference(store, video_id, t0, t1, core_ids, dataset=m.get("dataset"))})
        if len(out) >= max_clusters:
            break
    return out


_VN_SKIP = {"continue", "keep", "finish", "begin", "start", "resume", "the", "a", "an", "to", "more", "another", "first", "second", "third", "remaining", "additional", "all", "some", "of", "and", "then"}


def _norm_vn(text):
    """sub-goal 文字 -> (动词, 宾语) 粗键,去掉 continue / finish / begin 这类前缀与序数,词干化;用来判「几乎同一步」。"""
    import re as _re
    toks = [w for w in _re.findall(r"[a-z]+", (text or "").lower()) if w not in _VN_SKIP]
    if not toks: return ("", "")
    def stem(w):
        if w.endswith("ing") and len(w) > 5:
            w = w[:-3]
            if len(w) > 3 and w[-1] == w[-2]: w = w[:-1]        # chopping -> chop, stirring -> stir
        elif w.endswith("es") and len(w) > 4: w = w[:-2]
        elif w.endswith("s") and len(w) > 3: w = w[:-1]
        return w
    return (stem(toks[0]), stem(toks[1]) if len(toks) > 1 else "")


def gap_clusters(store, video_id, capability_skill, spec, m, *, seed=0, max_clusters=80, modalities=("video", "audio")):
    """10-24 plan_gap_filling:同一 task 的连续 sub-goal 段 k..k+m,头 = 最后 GAP_HEAD_SEC,尾 = 开头 GAP_TAIL_SEC(隐藏 1 步)或第一帧(隐藏 ≥2 步),
    隐藏 sub-goal 作 answer_only 参考。cluster 带 windows / gap / 干扰项骨架;observation_cutoff = 尾窗结束。"""
    from store import _status_ok
    import gap_distractors as GD
    D = m.get("duration_sec") or 1e9
    steps = [a for a in store.of_kind(video_id, "task_step", status="verified") if not a["value"].get("is_next_action") and a.get("event_id")]
    by_task = {}
    for a in steps: by_task.setdefault(a["event_id"], []).append(a)
    segs = {a["event_id"]: a for a in store.of_kind(video_id, "task_segment", status="verified") if a.get("event_id")}
    def rec2step(a): return {"idx": int(a["value"].get("idx") or 0), "text": a["value"].get("text") or "", "t0": a["time"]["start_sec"], "t1": a["time"]["end_sec"], "task_id": a.get("event_id"), "_rec": a}
    out = []
    for tid, recs in by_task.items():
        S = sorted((rec2step(a) for a in recs), key=lambda s: s["idx"])
        others = [s for t2, r2 in by_task.items() if t2 != tid for s in map(rec2step, r2)]
        for i, head in enumerate(S):
            for mm in GAP_SIZES:
                j = i + mm
                if j >= len(S): continue
                tail = S[j]; hidden = S[i + 1: j]
                if S[j]["idx"] - head["idx"] != mm: continue                       # idx 必须连续
                keys = [_norm_vn(s_["text"]) for s_ in [head] + hidden + [tail]]
                if len(set(keys)) < len(keys): continue   # 头 / 隐藏 / 尾里有「几乎同一步」(stir ×3、peel garlic ×2)就不出题:答案无法区分
                if any(h["t0"] < head["t1"] - 1.0 or h["t1"] > tail["t0"] + 1.0 for h in hidden): continue   # 隐藏段必须夹在头尾之间
                hw = [round(max(head["t0"], head["t1"] - GAP_HEAD_SEC), 3), round(head["t1"], 3)]
                tl = GAP_TAIL_SEC if len(hidden) == 1 else GAP_TAIL_FRAME_SEC
                tw = [round(tail["t0"], 3), round(min(D, max(tail["t0"] + tl, tail["t0"] + 1.0, min(tail["t1"], tail["t0"] + tl))), 3)]
                if hw[1] - hw[0] < 1.0 or tw[1] - tw[0] < 0.9: continue
                cutoff = tw[1]
                recs_in = [x for w in (hw, tw) for x in store.in_window(video_id, w[0], w[1], status="verified")]
                recs_in = [x for x in recs_in if not (set(x["modalities_supporting_fact"]) - set(modalities) - {""}) or x["solver_access"] == "stipulated"]
                seen = set(); uniq = []
                for x in recs_in:
                    if x["evidence_id"] in seen: continue
                    seen.add(x["evidence_id"]); uniq.append(x)
                core = [head["_rec"], tail["_rec"]] + [dict(h["_rec"], solver_access="answer_only") for h in hidden]
                if tid in segs: core.append(segs[tid])
                core_ids = {x["evidence_id"] for x in core}
                core += [x for x in uniq if x["kind"] == "action_narration" and x["evidence_id"] not in core_ids and x["solver_access"] != "answer_only" and (x["value"].get("task_id") in (None, tid))]
                core_ids = {x["evidence_id"] for x in core}
                ctx = [x for x in uniq if x["evidence_id"] not in core_ids and x["kind"] in ALL_CTX and x["solver_access"] != "answer_only" and x["kind"] != "task_step"]
                ctx = _trim_context(ctx, capability_skill)
                sk = GD.skeletons(head, hidden, tail, S, others, seed=seed)
                out.append({"evidence_cluster_id": ids.cluster_id(capability_skill, video_id, hw[0], tw[1], sorted(core_ids)),
                            "capability_skill": capability_skill, "video_id": video_id, "media_id": head["_rec"].get("media_id") or m["media_id"],
                            "window": [hw[0], tw[1]], "windows": [hw, tw], "observation_cutoff": cutoff, "anchor_id": head["_rec"]["evidence_id"],
                            "sample_id": tid, "anchor_kind": "task_step", "anchor_is_next": False, "anchor_step_idx": head["idx"],
                            "gap": {"head_idx": head["idx"], "tail_idx": tail["idx"], "hidden_idx": [h["idx"] for h in hidden], "n_hidden": len(hidden),
                                    "head_window": hw, "tail_window": tw, "tail_mode": "clip" if len(hidden) == 1 else "frame", "difficulty": "A" if len(hidden) == 1 else "B",
                                    "hidden_texts": [h["text"] for h in hidden], "head_text": head["text"], "tail_text": tail["text"], "distractor_skeletons": sk,
                                    "all_step_texts": [s_["text"] for s_ in S] + [o["text"] for o in others]},
                            "core": core, "context": ctx, "two_windows_allowed": True,
                            "interference": interference(store, video_id, hw[0], tw[1], sorted(core_ids), dataset=m.get("dataset"))})
    rng = random.Random(f"{seed}|{video_id}|{capability_skill}"); rng.shuffle(out)
    return out[:max_clusters]


def excluded_reasons(store, video_id, capability_skill, modalities=("video", "audio")):
    """dry-run 用:为什么这个 skill 在这个视频上没有 cluster。"""
    m = store.media_of_video(video_id)
    spec = skill_spec(capability_skill, m.get("dataset") if m else None)
    if spec is None:
        return ["skill_not_supported_by_retrieval"]
    r = []
    if spec.get("needs_complete"):
        cov = store.coverage(video_id, spec["needs_complete"])
        if not cov or cov["coverage"].get("completeness") != "complete":
            r.append(f"coverage_incomplete:{spec['needs_complete']}")
    n_anchor = sum(len(store.of_kind(video_id, k, status=None)) for k in spec["anchor"])
    n_ver = sum(len(store.of_kind(video_id, k, status="verified")) for k in spec["anchor"])
    if n_anchor == 0: r.append("no_anchor_evidence")
    elif n_ver == 0: r.append(f"not_verified:{n_anchor} anchor records need verification")
    return r or ["constraints_not_met"]
