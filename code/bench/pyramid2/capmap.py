"""capability_map.json(capability-v2)的读取与逐题解析;生成 data/ 副本时注入 lifecycle。"""
import json
import p2config as P

LIFECYCLE_OVERRIDE = {"high_plan_next": "retired"}
LEVEL_RULE = {"medium_order": {"span_sec": 15, "gap_sec": 5}}
# capability-v3(2026-10-13,用户定):L2 = 理解一个 event,模态绑定只是其中一个方面。
V3_OVERRIDES = {
    "easy_sound_object":  {"skill": "sound_action_binding", "reason": "v3:两个 sound binding 合并——这一声对应 event 里的哪个动作 / 物体"},
    "low_sound_movement": {"skill": "sound_action_binding", "reason": "v3:并入 sound_action_binding"},
    "low_spatial_near":   {"level": "L1", "skill": "spatial_near", "lifecycle": "control_variant", "reason": "v3:本质是 L1 单时刻关系,只是时刻靠声音找;作 L1 spatial 的对照变体(anchor=sound),不单列 skill"},
    "low_spatial_side":   {"level": "L1", "skill": "spatial_side", "lifecycle": "control_variant", "reason": "v3:同上"},
}
V3_NEW = {
    "action_recognition": {"level": "L2", "skill": "action_recognition", "status": "provisional", "lifecycle": "active",
                           "reason": "v3:这个 event 做了什么动作(verb + object)", "conditions": "单帧可见的物体识别归 L1;动作的目的归 L3"},
    "event_object_role":  {"level": "L2", "skill": "event_object_role", "status": "provisional", "lifecycle": "active",
                           "reason": "v3:event 里被操作的物体 / 工具 / 目的地(narration 名词对;Ego4D EASG 的 instrument / destination)", "conditions": "只问物体名归 L1"},
}
TAXONOMY_V3 = "capability-v3"


def write_capability_map():
    src = json.loads(P.CAPMAP_SRC.read_text())
    for k, m in src["skills"].items():
        m.setdefault("lifecycle", LIFECYCLE_OVERRIDE.get(k, "active"))
        if k in LEVEL_RULE:
            m["level_rule"] = LEVEL_RULE[k]
        if k in V3_OVERRIDES:
            m["v2"] = {kk: m.get(kk) for kk in ("level", "skill", "reason")}
            m.update(V3_OVERRIDES[k])
    for k, m in V3_NEW.items():
        src["skills"].setdefault(k, dict(m))
    src["taxonomy_version"] = TAXONOMY_V3
    src["v3_note"] = "2026-10-13 用户定:L1 = 一个时刻直接可观察;L2 = 理解一个 event(动作、被操作物 / 工具 / 目的地、前后状态、短跨度先后、局部活动、声音-动作对应);L3 = 跨 event。sound_anchored_spatial_* 降为 L1 spatial 的对照变体(control_variant),不单列。"
    src["generated_from"] = str(P.CAPMAP_SRC)
    (P.DATA / "capability_map.json").write_text(json.dumps(src, indent=1, ensure_ascii=False))
    return src


def _span(evidence):
    ts = sorted((r["time"]["start_sec"], r["time"]["end_sec"]) for r in evidence if r.get("time"))
    if not ts:
        return None
    gaps = [max(0.0, ts[i + 1][0] - ts[i][1]) for i in range(len(ts) - 1)]
    return max(b for a, b in ts) - min(a for a, b in ts), (max(gaps) if gaps else 0.0)


def resolve(cap, original_skill, evidence=None):
    m = cap["skills"].get(original_skill)
    if m is None:
        return {"original_skill": original_skill, "capability_layer": None, "capability_skill": original_skill,
                "classification_status": "unresolved", "lifecycle": "unknown", "relation_operation": None, "note": "not in capability_map"}
    layer, skill, note = m["level"], m["skill"], ""
    if original_skill == "medium_order":
        sp = _span(evidence or [])
        if sp is None:
            layer, note = "unresolved", "medium_order: timing evidence missing"
        else:
            span, gap = sp
            rule = m.get("level_rule", LEVEL_RULE["medium_order"])
            if span <= rule["span_sec"] and gap <= rule["gap_sec"]:
                layer, skill, note = "L2", "action_temporal_order", f"span {span:.1f}s gap {gap:.1f}s -> L2"
            else:
                layer, skill, note = "L3", "inter_event_temporal_reasoning", f"span {span:.1f}s gap {gap:.1f}s -> L3"
    return {"original_skill": original_skill, "capability_layer": layer, "capability_skill": skill,
            "classification_status": m.get("status", "provisional"), "lifecycle": m.get("lifecycle", "active"),
            "relation_operation": m.get("relation_operation"), "note": note or m.get("conditions", "")}


def skills_for_layer(cap, layer, include_retired=False):
    """[(original_skill, capability_skill)];medium_order 两层都列(逐题再判)。"""
    out, seen = [], set()
    for k, m in cap["skills"].items():
        if m.get("lifecycle", "active") in ("retired", "control_variant") and not include_retired:
            continue
        lv = m["level"]
        if lv == layer or (lv == "L2/L3" and layer in ("L2", "L3")):
            sk = m["skill"]
            if lv == "L2/L3":
                sk = "action_temporal_order" if layer == "L2" else "inter_event_temporal_reasoning"
            if sk in seen:                      # 两个旧 subtype 合并成一个 capability skill 时只列一次
                continue
            seen.add(sk); out.append((k, sk))
    return out


def original_for(cap, capability_skill):
    for k, m in cap["skills"].items():
        if m["skill"] == capability_skill or capability_skill in m["skill"].replace(" ", "").split("/"):
            return k
    return None
