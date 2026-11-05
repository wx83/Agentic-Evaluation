"""11-02 v24(用户定):回到 v17 遍历式出题(每个 event × 每个适用 skill 出一题,2-down-1-up 只管档位),四层按「时间尺度 × 模态」重排、改名:
  L1 Frame Perception     单帧(event 中心帧,题面不提时间):object_recognition(图里手里 / 正在操作的是什么)、
                          object_box_choice(程序在帧上画 A/B/C/D 四个框,问目标物体在哪个框里;原 bbox 输出题去掉)
  L2 Temporal Grounding   整个 sub-goal 的 clip(带音轨):action_recognition / event_object_role 改为「哪个时间段在做 X」(选项 = 程序生成的 clip 内时间段,
                          4 档写区间);sound_action_binding / sound_movement_binding(声音 ↔ 动作 / 移动,跨模态)、action_temporal_order 保留
  L3 Spatio-temporal      某时刻物体间关系(spatial_near / spatial_side / sound_anchored_spatial_*,时刻由 event 描述定,solver 要先定位再比)、
     Reasoning            同一物体 a→b 的位置 / 状态变化(object_location_at_time / object_state_change)、相邻 sub-goal 两个 event 的关系
                          (cross_event_integration / causal_prerequisite_reasoning / hidden_state_inference;clip 连续 ≤ 60 s,放不下则两段拼接)
  L4 Goal-conditioned     不变(sg.l4_clusters)
     Planning
合约:layers = "v24"(controller.active_skills 用 LAYERS_V24 覆盖 capability_map 的分层;sg.build_pools 转到这里;prompts 用 HARNESS_RULES)。
所有时间仍来自标注;Examiner 不写时间;选项时间段由程序按 event 记录生成。"""
import json, re, random, hashlib, math, collections
from pathlib import Path
import p2config as P
import retrieve as R
import sg as SG

NAMES = {"L1": "Frame Perception", "L2": "Temporal Grounding", "L3": "Spatio-temporal Reasoning", "L4": "Goal-conditioned Planning"}
L1_SKILLS = ["object_recognition", "object_box_choice"]
L2_SKILLS = ["action_recognition", "event_object_role", "action_temporal_order", "sound_action_binding", "sound_movement_binding", "sound_localization"]   # 11-04 v30:+ sound_localization(audio-only)
L2_MODALITY = {"action_recognition": "video_only", "event_object_role": "video_only", "action_temporal_order": "video_only",            # 11-04 v30(用户定):L2 = 定位 × 模态条件
               "sound_action_binding": "av", "sound_movement_binding": "av", "sound_localization": "audio_only"}
_V30 = {"modality": False}                                        # build_pools 按 contract.l2_modality 打开;autofill 据此给 L2 clip 换 mute / aonly 变体
SND_MAX_SAME = 3                                                  # sound_localization:同类声音在 sub-goal 里 ≤ 3 次才出(要数第 n 次)
ORD = {1: "first", 2: "second", 3: "third", 4: "fourth"}
L3_EVENT_SKILLS = {"spatial_near": "relation_at_time", "spatial_side": "relation_at_time", "sound_anchored_spatial_near": "relation_at_time",
                   "sound_anchored_spatial_side": "relation_at_time", "object_location_at_time": "change_over_time", "object_state_change": "change_over_time"}
L3_REL_SKILLS = ["cross_event_integration", "causal_prerequisite_reasoning", "hidden_state_inference"]
import v26ed as ED
import v27rf as RF
import goalrel as GR
import v29sa as SA
import v30chain as CH
import v31rsn as RS                                           # 11-04 晚 v31:三个关联 skill 的时空推理版                                         # 11-04 v30:L3 链式(L2 锚点 + 再一跳)
L3_SKILLS = list(L3_EVENT_SKILLS) + L3_REL_SKILLS + ["spatial_change"] + ED.ED_SKILLS + RF.RF_SKILLS + SA.SA_SKILLS + CH.CH_SKILLS + RS.RS_SKILLS      # 11-03 v26:ego_direction_unseen / turn_to_face(v26ed.py)      # spatial_change(11-02 晚,用户:L3 要问 t3→t4 的位置变化):答案由官方 3D 位置算
L4_SKILLS = ["goal_conditioned_planning"]
LAYERS_V24 = {**{s: "L1" for s in L1_SKILLS}, **{s: "L2" for s in L2_SKILLS}, **{s: "L3" for s in L3_SKILLS}, **{s: "L4" for s in L4_SKILLS}}
TG_SKILLS = {"action_recognition", "event_object_role", "sound_localization"}          # L2 temporal grounding:选项 = 时间段(程序生成)
FORMAT_OF = {1: "single_choice", 2: "single_choice", 3: "single_choice", 4: "short_answer"}
L3_EVENT_WINDOWS = {1: 20.0, 2: 40.0, 3: None, 4: None}          # relation_at_time / change_over_time:档 = 窗口(None = 整个 sub-goal)
L3_REL_MAX_SEC = 60.0                                            # 相邻 sub-goal 关系题:连续 clip ≤ 60 s,放不下则两段(各 event ± 5 s)拼接
TG_MIN_OPT_SEC = 4.0                                             # 时间段选项最短 4 s
TG_FAR_SEC = {1: 10.0, 2: 5.0, 3: 2.0}                           # 11-04 v30b:3 档 0 → 2 s(紧邻 1 s 对谁都不可能)
TG_PADS = [5.0, 10.0, 15.0, 20.0]                           # 档 1 / 2 / 3:干扰时间段离正确段至少这么远(越近越难)
FRAME_PX = 768                                                   # 单帧 jpg 短边
TW_IOU_MIN = 0.3                                                 # 4 档写区间:IoU ≥ 0.3 算对
FIX_FILL = ["counter", "sink", "cupboard", "table", "hob", "fridge", "drawer"]   # 组合题 L3 选项补位的 fixture 种类


def _opt_text(o): return re.sub(r"^\s*[A-E]\s*[\.\):]\s*", "", str(o or "")).strip().lower()

SKILL_DEFS = {
    "object_recognition": "L1 (single frame): which object is in hand / being handled in the image",
    "object_box_choice": "L1 (single frame): four lettered boxes are drawn on the image; which box contains the named object",
    "action_recognition": "L2 (temporal grounding): in which time span of the sub-goal clip does the described action happen",
    "event_object_role": "L2 (temporal grounding): in which time span does the action on the named object / with the named tool / to the named destination happen",
    "action_temporal_order": "L2: the order of two actions inside one sub-goal",
    "sound_action_binding": "L2 (cross-modal): which action / object produced the sound heard",
    "sound_movement_binding": "L2 (cross-modal): which object movement coincides with the sound",
    "spatial_near": "L3 (relation at a moment): at the moment of the described event, which listed object is nearest to a reference object (3D positions)",
    "spatial_side": "L3 (relation at a moment): at the moment of the described event, which listed object is leftmost / rightmost from the wearer's viewpoint",
    "sound_anchored_spatial_near": "L3 (relation at a moment, moment given by a sound): which listed object is nearest to a reference object when the sound occurs",
    "sound_anchored_spatial_side": "L3 (relation at a moment, moment given by a sound): which listed object is leftmost / rightmost when the sound occurs",
    "object_location_at_time": "L3 (location at a named moment): on which surface / fixture / container the object is at the moment of the described event (counter vs sink vs cupboard), or where it was before / after the movement",
    "object_state_change": "L3 (change over time): where an object was taken from and where it went in one movement",
}
SKILL_DEFS["spatial_change"] = "L3 (spatial change between two moments, 3D): after an object is moved, which listed object is it now nearest to / did it get closer to or farther from a reference object / which of the listed objects changed place between the two moments"
SKILL_DEFS.update(ED.SKILL_DEFS); SKILL_DEFS.update(RF.SKILL_DEFS); SKILL_DEFS.update(SA.SKILL_DEFS); SKILL_DEFS.update(CH.SKILL_DEFS); SKILL_DEFS.update(RS.SKILL_DEFS)
SKILL_DEFS["sound_localization"] = "L2 (temporal grounding, AUDIO ONLY: the Solver gets the soundtrack with a black picture): in which time span of the clip is the described sound (its class and, if repeated, which occurrence) heard"
for _k in L3_REL_SKILLS: SKILL_DEFS[_k] = "L3 (relation between an event of sub-goal k and an event of the adjacent sub-goal k+1): " + SG.SKILL_DEFS.get(_k, "") if _k in SG.SKILL_DEFS else "L3: relation between two events of adjacent sub-goals"


def _fmt_t(sec):
    sec = max(0.0, float(sec)); m = int(sec // 60); s = sec - 60 * m
    return f"{m}:{s:04.1f}" if s != int(s) else f"{m}:{int(s):02d}"


def _mmss(sec):
    sec = max(0, int(round(float(sec)))); return f"{sec // 60}:{sec % 60:02d}"


# ---------------------------------------------------------------- L1:单帧
def _frame_events(meta):
    for e in meta["events"]:
        c = (e["time"][0] + e["time"][1]) / 2
        e["frame_sec"] = round(c, 3); e["window_frame"] = [round(c, 3), round(c + 1.0, 3)]
        e["window_L1"] = e["window_frame"]
    meta["frame"] = True; meta["v24"] = True; meta["v24_event"] = True
    meta["tiers"] = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0}
    meta["band_rule"] = "tier = quartile of the perceptual quantity (object_recognition: number of other narrations within ±5 s); the Solver sees ONE IMAGE (the frame at the event's centre), not a clip"
    return meta


def l1_frame_clusters(store, ti, plan, skill):
    out = []
    for c in SG.l12_clusters(store, ti, plan, skill, "L1"):
        c["sg"] = _frame_events(c["sg"]); out.append(c)
    return out


def _iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _bbox_norm(v):
    if v.get("bbox_1408"): return [float(x) / 1408.0 for x in v["bbox_1408"]]
    if v.get("bbox_px") and v.get("frame_size"): S = float(v["frame_size"]); return [float(x) / S for x in v["bbox_px"]]
    return None


def _base(name): return re.sub(r"\s*\d+$", "", (name or "").strip().lower())


def _synthetic_boxes(target, n, rng, others=()):
    """与目标同尺寸的框,放在 3×3 网格的其它格子里(不与目标 / 已有框重叠);不够时随机位置。"""
    w, h = target[2] - target[0], target[3] - target[1]
    taken = [target] + list(others); out = []
    cells = [(cx, cy) for cx in (1 / 6, 1 / 2, 5 / 6) for cy in (1 / 6, 1 / 2, 5 / 6)]
    rng.shuffle(cells)
    for cx, cy in cells:
        if len(out) >= n: break
        x0 = min(max(0.0, cx - w / 2), 1 - w); y0 = min(max(0.0, cy - h / 2), 1 - h)
        b = [round(x0, 4), round(y0, 4), round(x0 + w, 4), round(y0 + h, 4)]
        if all(_iou(b, t) < 0.05 for t in taken): out.append(b); taken.append(b)
    tries = 0
    while len(out) < n and tries < 200:
        tries += 1
        x0 = rng.uniform(0, 1 - w); y0 = rng.uniform(0, 1 - h)
        b = [round(x0, 4), round(y0, 4), round(x0 + w, 4), round(y0 + h, 4)]
        if all(_iou(b, t) < 0.05 for t in taken): out.append(b); taken.append(b)
    return out


def box_choice_clusters(store, ti, plan, skill="object_box_choice"):
    """每个落在期望 event 附近的 mask 锚点一个 cluster:帧 = mask 的帧,框 = 目标 bbox + 3 个干扰框(同一帧 ±0.5 s 内其它 track 的 mask 框优先,其余同尺寸合成框),字母随机;档 = 目标框面积四分位(越小越难)。"""
    vid = ti["video_id"]; m = store.media_of_video(vid); D = (m or {}).get("duration_sec") or 1e9
    masks = sorted([r for r in SG._recs(store, vid, ti["t0"] - 1, ti["t1"] + 1, kinds={"object_mask_anchor"}) if _bbox_norm(r["value"] or {}) and (r["value"] or {}).get("name")],
                   key=lambda r: r["time"]["start_sec"])
    pre = []; used_t = []
    for s in ti["steps"]:
        sg_ = next((x for x in plan["sub_goals"] if x["idx"] == s["idx"]), None)
        if not sg_: continue
        evs = [e for e in sg_["events"] if e.get("matched")]
        if not evs: continue
        for r in masks:
            t = r["time"]["start_sec"]; name = r["value"]["name"]
            if not (s["t0"] - 0.5 <= t <= min(s["t1"], D - 1.5)): continue
            eid = SG._near_event(r, evs)
            if eid is None or any(abs(t - u) < 2.0 for u in used_t): continue
            base = _base(name)
            if any(q is not r and abs(q["time"]["start_sec"] - t) <= 1.0 and _base(q["value"].get("name")) == base for q in masks): continue   # 同名多实例:框不唯一
            tb = _bbox_norm(r["value"])
            if tb[2] <= tb[0] or tb[3] <= tb[1] or (tb[2] - tb[0]) * (tb[3] - tb[1]) > 0.5: continue
            rng = random.Random(r["evidence_id"])
            others = []
            for q in masks:                                     # 同帧(±0.5 s)其它物体的框当干扰框
                if q is r or abs(q["time"]["start_sec"] - t) > 0.5 or q["value"].get("track_id") == r["value"].get("track_id"): continue
                qb = _bbox_norm(q["value"])
                if qb and _iou(qb, tb) < 0.05 and all(_iou(qb, o) < 0.05 for o in others): others.append([round(x, 4) for x in qb])
            others = others[:3]
            others += _synthetic_boxes(tb, 3 - len(others), rng, others)
            boxes = [{"bbox": [round(x, 4) for x in tb], "target": True}] + [{"bbox": b, "target": False} for b in others[:3]]
            rng.shuffle(boxes)
            for L, b in zip("ABCD", boxes): b["letter"] = L
            target_letter = next(b["letter"] for b in boxes if b["target"])
            used_t.append(t)
            core = [r] + SG._recs(store, vid, t - 5, t + 5, kinds={"action_narration"})
            if s["idx"] in ti["step_rec"]: core.append(ti["step_rec"][s["idx"]])
            ev = next(e for e in evs if e["event_id"] == eid)
            meta = {"kind": "L1", "idx": s["idx"], "sub_goal_text": s["text"], "sub_goal_window": [s["t0"], s["t1"]], "v24": True, "v24_event": True, "frame": True, "box_choice": True,
                    "frame_sec": round(t, 3), "object": base, "mask_id": r["evidence_id"], "fixture": r["value"].get("fixture_kind") or r["value"].get("fixture"),
                    "boxes": [{"letter": b["letter"], "bbox": b["bbox"]} for b in boxes], "target_letter": target_letter,
                    "events": [{**{k: ev[k] for k in ("event_id", "type", "description", "objects", "time", "records")}, "frame_sec": round(t, 3), "window_frame": [round(t, 3), round(min(D, t + 1.0), 3)], "window_L1": [round(t, 3), round(min(D, t + 1.0), 3)]}],
                    "anchor_event": {r["evidence_id"]: eid}, "knob": {r["evidence_id"]: {"kind": "area_neg", "value": round(-(tb[2] - tb[0]) * (tb[3] - tb[1]), 5)}},
                    "tiers": {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0},
                    "band_rule": "tier = quartile of the target box area (4 = smallest box); the Solver sees ONE IMAGE with four lettered boxes drawn on it and picks the letter"}
            pre.append((s, t, r, core, meta))
    bands = SG._bands({meta["mask_id"]: meta["knob"][meta["mask_id"]]["value"] for _, _, _, _, meta in pre})
    out = []
    for s, t, r, core, meta in pre:
        meta["bands"] = {k: [meta["mask_id"]] if bands.get(meta["mask_id"]) == k else [] for k in (1, 2, 3, 4)}
        w = [round(t, 3), round(min(D, t + 1.0), 3)]
        out.append(SG._mk_cluster(skill, ti, store, windows=[w], cutoff=None, anchor=r, core=core, sg_meta=meta))
    out.sort(key=lambda c: (c["sg"]["idx"], c["sg"]["frame_sec"]))
    return out


# ---------------------------------------------------------------- L2:整个 sub-goal 的 clip
def l2_clusters(store, ti, plan, skill):
    out = []
    for c in SG.l12_clusters(store, ti, plan, skill, "L2"):
        meta = c["sg"]; meta["v24"] = True; meta["v24_event"] = True
        meta["sg_events_all"] = [{"event_id": e["event_id"], "type": e["type"], "description": e["description"], "time": e["time"]} for e in meta["events"]]
        meta["modality"] = L2_MODALITY.get(skill)               # 11-04 v30:video_only / audio_only / av(contract.l2_modality 打开才生效)
        if skill in TG_SKILLS:                                  # temporal grounding:四档都看整个 sub-goal;档 = 干扰时间段离正确段多远 / 4 档写区间
            meta["tg"] = True
            _m = store.media_of_video(ti["video_id"]); _D = (_m or {}).get("duration_sec") or 1e9
            _h = int(hashlib.sha1(c["evidence_cluster_id"].encode()).hexdigest()[:6], 16)
            pa, pb = TG_PADS[_h % len(TG_PADS)], TG_PADS[(_h // 7) % len(TG_PADS)]      # 11-04 晚 v30b:clip 起止各向外伸 5–20 s(每 cluster 固定),否则 sub-goal 第一个事件永远在 0:00 → 答案永远 A
            c["window"] = [round(max(0.0, c["window"][0] - pa), 3), round(min(_D, c["window"][1] + pb), 3)]
            meta["tg_pad"] = [pa, pb]
            win = c["window"]; L = round(win[1] - win[0], 3)
            keep = []
            if skill == "sound_localization":                   # 11-04 v30:正确段 = 对到该 event 的声音记录(同类 ≤ 3 次,题面说第 n 次);干扰段 = 其它声音
                snds = [r for r in SG._recs(store, ti["video_id"], win[0], win[1], kinds={"sound_event"}) if "BACKGROUND_CLASS" not in r["quality_flags"] and (r["value"] or {}).get("label")]
                by_lab = collections.Counter(r["value"]["label"] for r in snds)
                for e in meta["events"]:
                    mine = [store.get(rid) for rid, eid in meta["anchor_event"].items() if eid == e["event_id"]]
                    mine = [r for r in mine if r is not None and r["kind"] == "sound_event" and by_lab.get((r["value"] or {}).get("label"), 9) <= SND_MAX_SAME]
                    if not mine: continue
                    c0 = (float(e["time"][0]) + float(e["time"][1])) / 2
                    r = min(mine, key=lambda x: abs((float(x["time"]["start_sec"]) + float(x["time"]["end_sec"])) / 2 - c0))
                    lab = r["value"]["label"]; ts = float(r["time"]["start_sec"])
                    n_same = by_lab[lab]; ordinal = 1 + sum(1 for x in snds if x["value"]["label"] == lab and float(x["time"]["start_sec"]) < ts)
                    if float(r["time"]["end_sec"]) - ts > 0.6 * L: continue        # 声音段太长(连续切菜 20 s)没法定位
                    e["tg_span"] = [round(ts, 3), round(float(r["time"]["end_sec"]), 3)]
                    e["sound"] = {"record": r["evidence_id"], "label": lab, "ordinal": ordinal, "n_same_in_clip": n_same,
                                  "desc": (f"the {ORD.get(ordinal, str(ordinal) + 'th')} '{lab}' sound" if n_same > 1 else f"the '{lab}' sound")}
                    keep.append(e)
                meta["anchor_event"] = {rid: eid for rid, eid in meta["anchor_event"].items() if any(e.get("sound", {}).get("record") == rid for e in keep)}
                meta["sg_events_all"] = [{"event_id": "snd:" + r["evidence_id"].split(":")[-1], "type": "sound", "description": r["value"]["label"], "time": [float(r["time"]["start_sec"]), float(r["time"]["end_sec"])]} for r in snds]
            for e in (meta["events"] if skill != "sound_localization" else []):   # 正确段 = event 记录里最短的那条 narration(event 并集常常等于整个 sub-goal,没法定位)
                spans = []
                for rid in e.get("records") or []:
                    r = store.get(rid)
                    if r is not None and r["kind"] in ("action_narration", "object_location_transition", "object_move", "sound_event", "utterance"):
                        spans.append([float(r["time"]["start_sec"]), float(r["time"]["end_sec"])])
                core = min(spans, key=lambda x: x[1] - x[0]) if spans else list(e["time"])
                e["tg_span"] = [round(core[0], 3), round(core[1], 3)]
                if (core[1] - core[0]) <= 0.6 * L: keep.append(e)
            dropped = [e["event_id"] for e in meta["events"] if e not in keep]
            meta["events"] = keep
            meta["anchor_event"] = {r: eid for r, eid in meta["anchor_event"].items() if eid not in dropped}
            if not keep: continue
            meta["tiers"] = {1: L, 2: L, 3: L, 4: L}
            for e in meta["events"]: e["window_L2"] = {1: list(win), 2: list(win), 3: list(win), 4: list(win)}
            meta["band_rule"] = "the clip is always the whole sub-goal; tiers 1-3: options are four time spans of the clip (program-generated; distractor spans at least 10 / 5 / 0 s away from the true span); tier 4: the Solver writes the start-end span itself (IoU >= 0.3)"
        out.append(c)
    return out


# ---------------------------------------------------------------- L3:时空推理
def l3_event_clusters(store, ti, plan, skill):
    """relation_at_time / change_over_time:cluster = sub-goal(与 L2 相同),窗口档 20 / 40 / 整段 / 整段短答;kind 记 L3。"""
    out = []
    for c in SG.l12_clusters(store, ti, plan, skill, "L2"):
        meta = c["sg"]; meta["kind"] = "L3"; meta["v24"] = True; meta["v24_event"] = True; meta["l3_kind"] = L3_EVENT_SKILLS[skill]
        win = c["window"]; D = win[1] - win[0]
        meta["tiers"] = {t: (w if w is not None else round(D, 3)) for t, w in L3_EVENT_WINDOWS.items()}
        def _win_for(e, L):
            if L is None: return [win[0], win[1]]
            c0 = (e["time"][0] + e["time"][1]) / 2; a = max(win[0], c0 - L / 2); b = min(win[1], a + L); a = max(win[0], b - L)
            return [round(a, 3), round(b, 3)]
        for e in meta["events"]: e["window_L2"] = {t: _win_for(e, w) for t, w in L3_EVENT_WINDOWS.items()}
        if L3_EVENT_SKILLS[skill] == "change_over_time":                                      # 11-03 v25:选项只能用本视频 object_move 里出现过的 fixture
            fx = collections.Counter(v for r in SG._recs(store, ti["video_id"], 0, 1e9, kinds={"object_move"}) for k in ("from_fixture_kind", "to_fixture_kind") for v in [(r["value"] or {}).get(k)] if v and v != "mid-air")
            meta["video_fixtures"] = [k for k, _ in fx.most_common(8)]
        meta["band_rule"] = ("tier = clip length around the event (20 s / 40 s / whole sub-goal / whole sub-goal + short answer); the question names the moment by the event "
                             "(what is being done), never by time: the Solver must first find the moment, then answer the spatial relation / the before-after change")
        out.append(c)
    return out


def l3_relation_clusters(store, ti, plan, skill):
    """相邻 sub-goal 两个 event 的关系:clip = [A 起 − 5, B 止 + 5] 连续(≤ 60 s);放不下则两段 A ± 5、B ± 5 拼接(顺序,带 Segment 卡)。四档同窗口,1-3 单选 4 短答。"""
    vid = ti["video_id"]; m = store.media_of_video(vid); D = (m or {}).get("duration_sec") or 1e9
    steps = {s_["idx"]: s_ for s_ in ti["steps"]}; out = []
    for rel in plan["relations"]:
        if rel["skill"] != skill: continue
        evs = [plan["events"][e] for e in rel["events"] if plan["events"].get(e, {}).get("matched")]
        if len(evs) < 2: continue
        evs.sort(key=lambda e: e["centre"]); A, B = evs[0], evs[-1]
        ka, kb = A["sub_goal"], B["sub_goal"]
        if kb - ka != 1 or ka not in steps or kb not in steps: continue
        w = [round(max(0.0, A["time"][0] - SG.EVENT_PAD), 3), round(min(D, B["time"][1] + SG.EVENT_PAD), 3)]
        if w[1] - w[0] <= L3_REL_MAX_SEC:
            windows = [w]; two = False
        else:
            windows = [SG._seg(A["centre"], D), SG._seg(B["centre"], D)]; two = True
            if windows[0][1] > windows[1][0]: windows = [[windows[0][0], windows[1][1]]]; two = False
        core = []
        for ww in windows:
            core += [r for r in SG._recs(store, vid, ww[0], ww[1], kinds={"action_narration", "sound_event", "object_move", "object_location_transition", "spatial_relation", "utterance"})
                     if SG._near_event(r, evs, pad=SG.EVENT_PAD) is not None or any(r["evidence_id"] in e["records"] for e in evs)]
        for e in evs:
            for rid in e["records"]:
                r = store.get(rid)
                if r is not None and r["solver_access"] != "answer_only": core.append(r)
        core = list({r["evidence_id"]: r for r in core}.values())
        for k_ in (ka, kb):
            if k_ in ti["step_rec"] and ti["step_rec"][k_]["evidence_id"] not in {r["evidence_id"] for r in core}: core.append(ti["step_rec"][k_])
        if len(core) < 2: continue
        total = round(sum(x[1] - x[0] for x in windows), 1)
        for tier in (1, 2, 3, 4):
            meta = {"kind": "L3", "v24": True, "l3_kind": "relation", "tier": tier, "rel_id": rel["rel_id"], "rel_type": rel["type"], "rel_source": rel.get("source", "planner"),
                    "ask": rel["ask"], "answer_hint": rel["answer_hint"], "idx": [ka, kb], "this_sub_goal": kb,
                    "events": [{k: e[k] for k in ("event_id", "sub_goal", "type", "description", "objects", "time", "records")} for e in evs],
                    "windows": [list(x) for x in windows], "n_segments": len(windows), "total_sec": total,
                    "window_rule": ("one continuous clip from 5 s before the earlier event to 5 s after the later event" if not two else
                                    "two 10 s segments (earlier event ± 5 s, later event ± 5 s) joined in order with 'Segment k' title cards") + {1: "; single choice", 2: "; single choice", 3: "; single choice", 4: "; short answer"}[tier]}
            anchor = next((r for r in core if r["evidence_id"] in A["records"]), core[0])
            c = SG._mk_cluster(skill, ti, store, windows=windows, cutoff=windows[-1][1], anchor=anchor, core=core, sg_meta=meta, two=two)
            if two: c["windows"] = [list(x) for x in windows]
            out.append(c)
    return out


# ---------------------------------------------------------------- L3:spatial_change(t3 → t4 的 3D 位置变化)
SC_MIN_MOVE = 0.1           # 物体位移 ≥ 0.1 m 才算移动(11-03 v25:原 0.15)
SC_MIN_MARGIN = 0.1         # nearest_after:最近与次近的距离差 ≥ 0.1 m
SC_MIN_DELTA = 0.2          # closer_farther:|Δ距离| ≥ 0.2 m;which_moved:移动者位移 ≥ 0.2 m(参照物在该时段无记录移动)
SC_REF_PAD = 20.0           # 参照物锚点取移动前后 20 s 内
SC_TYPES = {"nearest_after": "after the move, which listed object is it nearest to", "closer_farther": "did it get closer to or farther from the reference object",
            "which_moved": "which of the listed objects changed place between the two moments",
            "nearest_before": "at the start moment (before the move), which listed object is it nearest to"}      # 11-03 v25:relation_at_time 的程序算版
SC_CF_OPTIONS = ["closer to it", "farther from it", "about the same distance", "it was not moved at all"]


def _dist3(a, b): return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def spatial_change_clusters(store, ti, plan, skill="spatial_change"):
    vid = ti["video_id"]; m = store.media_of_video(vid); D = (m or {}).get("duration_sec") or 1e9
    moves = [r for r in SG._recs(store, vid, ti["t0"], ti["t1"], kinds={"object_move"}) if (r["value"] or {}).get("start_xyz") and (r["value"] or {}).get("end_xyz")]
    masks = [r for r in SG._recs(store, vid, ti["t0"] - SC_REF_PAD, ti["t1"] + SC_REF_PAD, kinds={"object_mask_anchor"}) if (r["value"] or {}).get("xyz") and (r["value"] or {}).get("name")]
    evs = sorted([e for e in plan["events"].values() if e.get("matched")], key=lambda e: e["centre"])
    def _ev_near(t, pad=8.0):
        c = [e for e in evs if abs(e["centre"] - t) <= pad]
        return min(c, key=lambda e: abs(e["centre"] - t)) if c else None
    pre = []
    for mv in moves:
        v = mv["value"]; ts, te = float(mv["time"]["start_sec"]), float(mv["time"]["end_sec"])
        disp = _dist3(v["start_xyz"], v["end_xyz"])
        if disp < SC_MIN_MOVE: continue
        obj = _base(v.get("object_name") or ""); tid = v.get("track_id")
        if not obj: continue
        refs = {}
        for r in masks:                                          # 参照物:别的 track 的锚点;锚点时刻与这次移动之间该 track 没有任何 object_move(静止,位置可信)
            rv = r["value"]; t = r["time"]["start_sec"]
            if rv.get("track_id") == tid: continue
            lo, hi = min(t, ts), max(t, te)
            if any(q["value"].get("track_id") == rv.get("track_id") and q["time"]["start_sec"] <= hi and q["time"]["end_sec"] >= lo for q in moves): continue
            nm = _base(rv["name"])
            if not nm or nm == obj: continue
            if nm not in refs or abs(t - (ts + te) / 2) < abs(refs[nm]["t"] - (ts + te) / 2):
                refs[nm] = {"name": nm, "xyz": rv["xyz"], "t": t, "id": r["evidence_id"]}
        if len(refs) < 1: continue                                   # 11-03 v25:每种题型自己要求参照物数量
        for nm, rf in refs.items():
            rf["d_start"] = round(_dist3(v["start_xyz"], rf["xyz"]), 3); rf["d_end"] = round(_dist3(v["end_xyz"], rf["xyz"]), 3)
        eA, eB = _ev_near(ts), _ev_near(te)
        if eA is not None and eB is not None and eA["event_id"] == eB["event_id"]: eA = None     # 同一个 event:起点改用物体自己的移动来描述
        mom = {"start_desc": eA["description"] if eA else f"before the {obj} is picked up from the {v.get('from_fixture_kind') or 'surface'}",
               "end_desc": eB["description"] if eB else f"after the {obj} is put down on the {v.get('to_fixture_kind') or 'surface'}",
               "start_event": eA["event_id"] if eA else None, "end_event": eB["event_id"] if eB else None}
        items = []
        by_end = sorted(refs.values(), key=lambda r: r["d_end"]); by_start = sorted(refs.values(), key=lambda r: r["d_start"])
        if len(by_end) >= 4 and by_end[1]["d_end"] - by_end[0]["d_end"] >= SC_MIN_MARGIN and by_start[0]["name"] != by_end[0]["name"]:
            cand = by_end[:4]
            items.append({"type": "nearest_after", "key": "nearest_after", "candidates": [r["name"] for r in cand], "answer": by_end[0]["name"], "knob": -round(by_end[1]["d_end"] - by_end[0]["d_end"], 3),
                          "note": f"nearest at the start was {by_start[0]['name']} ({by_start[0]['d_start']} m); at the end {by_end[0]['name']} ({by_end[0]['d_end']} m), runner-up {by_end[1]['name']} ({by_end[1]['d_end']} m)"})
        if len(by_start) >= 4 and by_start[1]["d_start"] - by_start[0]["d_start"] >= SC_MIN_MARGIN:          # 11-03 v25:移动前那一刻谁最近(relation_at_time)
            cand = by_start[:4]
            items.append({"type": "nearest_before", "key": "nearest_before", "candidates": [r["name"] for r in cand], "answer": by_start[0]["name"], "knob": -round(by_start[1]["d_start"] - by_start[0]["d_start"], 3),
                          "note": f"at the start {by_start[0]['name']} is nearest ({by_start[0]['d_start']} m), runner-up {by_start[1]['name']} ({by_start[1]['d_start']} m); after the move the nearest is {by_end[0]['name']}"})
        for best in sorted(refs.values(), key=lambda r: -abs(r["d_end"] - r["d_start"]))[:2]:                # 11-03 v25:最多两个参照物各一题
            if abs(best["d_end"] - best["d_start"]) >= SC_MIN_DELTA:
                items.append({"type": "closer_farther", "key": "closer_farther_" + re.sub(r"[^a-z0-9]+", "", best["name"])[:12], "reference": best["name"], "candidates": list(SC_CF_OPTIONS), "answer": SC_CF_OPTIONS[0] if best["d_end"] < best["d_start"] else SC_CF_OPTIONS[1],
                              "knob": -round(abs(best["d_end"] - best["d_start"]), 3), "note": f"distance to {best['name']}: {best['d_start']} m -> {best['d_end']} m"})
        static = [r for r in refs.values() if r["name"] != obj][:3]
        if disp >= SC_MIN_DELTA and len(static) >= 3:
            items.append({"type": "which_moved", "key": "which_moved", "candidates": [obj] + [r["name"] for r in static], "answer": obj, "knob": -round(disp, 3),
                          "note": f"{obj} moved {disp:.2f} m ({v.get('from_fixture_kind')} -> {v.get('to_fixture_kind')}); the others have no recorded movement in this span"})
        if not items: continue
        w = [round(max(0.0, ts - SG.EVENT_PAD), 3), round(min(D, te + SG.EVENT_PAD), 3)]
        if w[1] - w[0] <= L3_REL_MAX_SEC: windows, two = [w], False
        else:
            windows = [SG._seg(ts, D), SG._seg(te, D)]; two = True
            if windows[0][1] > windows[1][0]: windows, two = [[windows[0][0], windows[1][1]]], False
        core = [mv] + [store.get(r["id"]) for r in refs.values() if store.get(r["id"]) is not None]
        for ww in windows: core += SG._recs(store, vid, ww[0], ww[1], kinds={"action_narration"})
        for e in (eA, eB):
            if e:
                for rid in e["records"]:
                    r = store.get(rid)
                    if r is not None and r["solver_access"] != "answer_only": core.append(r)
        core = list({r["evidence_id"]: r for r in core}.values())
        step = next((s_ for s_ in ti["steps"] if s_["t0"] - 0.5 <= te <= s_["t1"] + 0.5), None)
        if step and step["idx"] in ti["step_rec"]: core.append(ti["step_rec"][step["idx"]])
        for it in items:
            rng = random.Random(mv["evidence_id"] + it["key"]); cands = list(it["candidates"])
            if it["type"] != "closer_farther": rng.shuffle(cands)
            pre.append((mv, it, cands, windows, two, core, mom, obj, [e for e in (eA, eB) if e], step, disp))
    bands = SG._bands({f"{mv['evidence_id']}:{it['key']}": it["knob"] for mv, it, *_ in pre})
    out = []
    for mv, it, cands, windows, two, core, mom, obj, evl, step, disp in pre:
        tier = bands.get(f"{mv['evidence_id']}:{it['key']}", 2)
        fmt = "single_choice" if (it["type"] == "closer_farther" or tier < 4) else "short_answer"
        meta = {"kind": "L3", "v24": True, "l3_kind": "spatial_change", "tier": tier, "format": fmt, "rel_id": f"sc_{mv['evidence_id'][-8:]}_{it['key']}", "rel_type": it["type"],
                "idx": step["idx"] if step else None, "this_sub_goal": step["idx"] if step else None,
                "sc": {"type": it["type"], "object": obj, "moved_from": mv["value"].get("from_fixture_kind"), "moved_to": mv["value"].get("to_fixture_kind"), "displacement_m": round(disp, 2),
                       "reference": it.get("reference"), "options": cands, "answer": it["answer"],
                       "moments": (mom if it["type"] != "which_moved" else      # 11-03:which_moved 的两个时刻 = clip 起止(事件 / 物体自己的移动会点名答案)
                                   ({"start_desc": "the start of the clip", "end_desc": "the end of the clip", "start_event": None, "end_event": None} if not two else
                                    {"start_desc": "the first segment of the clip", "end_desc": "the second segment of the clip", "start_event": None, "end_event": None})),
                       "note": it["note"], "ask": SC_TYPES[it["type"]]},
                "events": [{k: e[k] for k in ("event_id", "sub_goal", "type", "description", "objects", "time", "records")} for e in evl],
                "windows": [list(x) for x in windows], "n_segments": len(windows), "total_sec": round(sum(x[1] - x[0] for x in windows), 1),
                "window_rule": ("one continuous clip from 5 s before the move starts to 5 s after it ends" if not two else "two 10 s segments (start of the move ± 5 s, end of the move ± 5 s) joined in order with title cards") + f"; tier {tier} = quartile of the 3D margin (4 = smallest); format {fmt}",
                "band_rule": "tier = quartile of the 3D margin that decides the answer (nearest_after: gap between nearest and runner-up; closer_farther: |change of distance|; which_moved: displacement); smaller margin = harder"}
        c = SG._mk_cluster(skill, ti, store, windows=windows, cutoff=windows[-1][1], anchor=mv, core=core, sg_meta=meta, two=two)
        if two: c["windows"] = [list(x) for x in windows]
        out.append(c)
    out.sort(key=lambda c: c["window"][0])
    return out


# ---------------------------------------------------------------- pools
def build_pools(store, contract, plan_by_task, skills, layer, seed=0):
    pools = {}
    _V30["modality"] = bool(contract.get("l2_modality"))         # 11-04 v30
    for cap in skills:
        cl = []
        for tid, plan in plan_by_task.items():
            if not plan: continue
            ti = SG.task_info(store, tid)
            if LAYERS_V24.get(cap) != layer: continue
            n0 = len(cl)
            if cap == "object_box_choice": cl += box_choice_clusters(store, ti, plan, cap)
            elif layer == "L1": cl += l1_frame_clusters(store, ti, plan, cap)
            elif layer == "L2": cl += l2_clusters(store, ti, plan, cap)
            elif cap in L3_EVENT_SKILLS: cl += l3_event_clusters(store, ti, plan, cap)
            elif cap in L3_REL_SKILLS: cl += l3_relation_clusters(store, ti, plan, cap)
            elif cap == "spatial_change": cl += spatial_change_clusters(store, ti, plan, cap)
            elif cap in ED.ED_SKILLS: cl += ED.clusters(store, ti, plan, cap)
            elif cap in RF.RF_SKILLS: cl += RF.clusters(store, ti, plan, cap)
            elif cap in SA.SA_SKILLS: cl += SA.clusters(store, ti, plan, cap)      # 11-03 v29:AEA spatial audio
            elif cap in CH.CH_SKILLS: cl += CH.clusters(store, ti, plan, cap)      # 11-04 v30:链式 L3
            elif cap in RS.RS_SKILLS: cl += RS.clusters(store, ti, plan, cap)      # 11-04 晚 v31
            elif layer == "L4": cl += SG.l4_clusters(store, ti, plan, cap)
            if contract.get("goal_relevance") and len(cl) > n0:            # 11-03 v28:只留问到 goal 相关物体 / fixture 的题
                kept, drop, _ = GR.filter_pool(cap, cl[n0:], store, ti, plan); cl = cl[:n0] + kept
                if drop: _plog(contract, f"{layer} {cap}: goal_relevance dropped {sum(drop.values())} (kept {len(cl)}): " + "; ".join(f"{k} x{v}" for k, v in drop.most_common(6)))
        pools[cap] = cl
    if contract.get("comp_mode"):                                # 11-03 试验模式(comp.py):给 TG / L3 位置变化 cluster 挂组合候选
        import comp as _C
        prof = comp_profile(contract)
        for tid, plan in plan_by_task.items():
            if not plan: continue
            ti = SG.task_info(store, tid)
            sub = {k: [c for c in v if c.get("sample_id") == tid] for k, v in pools.items()}
            _C.attach(store, ti, plan, sub, contract, prof, contract["run_id"], log=lambda m: _plog(contract, f"{layer} {tid}: {m}"))
    return pools


def _plog(contract, msg):
    try:
        with open(P.RUNS / contract["run_id"] / "run.log", "a") as f: f.write(f"[{__import__('time').strftime('%H:%M:%S')}] {msg}\n")
    except Exception: pass


_PROFILE = {}


def comp_profile(contract):
    """profile 来源:contract.comp_profile_runs(run id 列表)或 comp_profile_path;首次建好后写到 run 目录 comp_profile.json 并冻结(同一 run 内不再变)。"""
    import comp as _C
    rid = contract["run_id"]
    if rid in _PROFILE: return _PROFILE[rid]
    pp = P.RUNS / rid / "comp_profile.json"
    if pp.exists(): _PROFILE[rid] = json.loads(pp.read_text()); return _PROFILE[rid]
    if contract.get("comp_profile_path"): prof = json.loads(Path(contract["comp_profile_path"]).read_text())
    else: prof = _C.build_profile([P.RUNS / r for r in (contract.get("comp_profile_runs") or [])], contract.get("comp_thresholds"))
    pp.parent.mkdir(parents=True, exist_ok=True); pp.write_text(json.dumps(prof, ensure_ascii=False, indent=1))
    _PROFILE[rid] = prof; return prof


# ---------------------------------------------------------------- 档位接口
def _modality_note(sg_):
    """11-04 v30:L2 模态条件写进 Examiner 的 spec(contract.l2_modality 打开时)。"""
    if not _V30["modality"]: return ""
    m = (sg_ or {}).get("modality")
    return {"video_only": " MODALITY: the Solver receives this clip WITHOUT SOUND - the question must be answerable from the picture alone (do not rely on any sound).",
            "audio_only": " MODALITY: the Solver receives ONLY THE SOUNDTRACK (the picture is black) - the question must be answerable from what is heard alone; describe sounds, never what is seen.",
            "av": " MODALITY: the Solver receives picture and sound; the question must need BOTH (what is heard bound to what is seen)."}.get(m or "", "")


def spec_for(cap, level, c=None, contract=None):
    layer = LAYERS_V24.get(cap); sg_ = (c or {}).get("sg") or {}
    fmt = FORMAT_OF[level]
    if layer == "L1":
        if cap == "object_box_choice":
            return {"level": level, "format": "single_choice", "window_max_sec": 1.5, "window_min_sec": 0.9, "image": True,
                    "note": f"L1 object_box_choice tier {level}: the Solver sees ONE IMAGE (the mask frame) with four lettered boxes drawn by the program (sg.boxes); "
                            f"ask which box contains sg.object; options are filled by the program ('A. the box labelled A' ...); reference = sg.target_letter; the box is quartile {level} by area (4 = smallest)",
                    "rule": "controller-fixed: format single_choice; media_refs window = exactly the offered 1 s window (variant frame); do NOT describe where the object is or when; name the object exactly as sg.object"}
        return {"level": level, "format": fmt, "window_max_sec": 1.5, "window_min_sec": 0.9, "image": True, **({"band_enforce": False} if (contract or {}).get("l1_band_enforce") is False else {}),
                "note": f"L1 tier {level}: the Solver sees ONE IMAGE = the frame at the centre of the chosen event (sg.events[i].window_frame; use it EXACTLY as media_refs[0].windows[0]); "
                        f"the question must NOT mention time or the clip ('in this image, what is the person holding?'); the cited anchor record must be in sg.bands[{level}]",
                "rule": "controller-fixed: exactly this format; window = the event's window_frame; cite a band record; no time words"}
    comp_note = ""
    if sg_.get("comp_mode") and sg_.get("comp_by_event"):
        ok_ = [k for k, v in sg_["comp_by_event"].items() if not v.get("fallback")]
        if ok_: comp_note = (" COMPOSED ITEM (sg.comp_by_event[event]): the clip also contains the same action on a confusable object and / or another occurrence of the same action on this object (comp.alts); "
                             "name the target object exactly (comp.target.object) and, when comp.target.n_same > 1, say which occurrence ('the first time ...'); the program puts the alternative spans / endpoints among the options.")
    if layer == "L2":
        if sg_.get("tg") or cap in TG_SKILLS:
            f2 = "time_window" if level == 4 else "single_choice"
            return {"level": level, "format": f2, "window_max_sec": None, "window_min_sec": None, "tg": True,
                    "note": f"L2 temporal grounding tier {level}: media_refs = EXACTLY the whole offered sub-goal window; "
                            + ("the question describes the SOUND only by its class and, if it occurs more than once, which occurrence (use sg.events[i].sound.desc, e.g. \"the second 'metal-only collision' sound\"); never mention the action or the object (the Solver hears only the soundtrack with a black picture); cite the sound record sg.events[i].sound.record in evidence_refs; this is a WHEN question (the reference is that sound's time span, filled by the program), NOT a direction question - no spatial-audio annotation is needed; " if cap == "sound_localization"
                               else "the question describes the event in words (action + object / tool / destination) and asks WHEN in the clip it happens; ")
                            + _modality_note(sg_)
                            + ("options and the reference letter are filled by the program (four time spans of the clip; write 4 placeholder options like 'A. <span>'); " if level < 4 else "format time_window: the Solver writes 'Time: M:SS-M:SS' (clip time); the program fills the reference span; ")
                            + "never give any time position in the question" + comp_note,
                    "rule": "controller-fixed: exactly this format; window = the whole offered sub-goal window; the question must not reveal when"}
        w = SG.L2_WINDOWS[level]; wl = w if w is not None else (round(c["window"][1] - c["window"][0], 3) if c else None)
        return {"level": level, "format": fmt, "window_max_sec": wl, "window_min_sec": min(SG.MIN_WIN, wl or SG.MIN_WIN),
                "note": f"L2 tier {level}: clip at most {wl:.0f} s inside the sub-goal, containing the event; the question describes the sound / events in words and gives NO time position" + (" ; short_answer: reference = a short phrase with accepted_alternatives" if fmt == "short_answer" else "") + _modality_note(sg_),
                "rule": "controller-fixed: exactly this format and at most this clip length; never say when in the clip the event happens"}
    if layer == "L3" and cap in L3_EVENT_SKILLS:
        w = L3_EVENT_WINDOWS[level]; wl = w if w is not None else (round(c["window"][1] - c["window"][0], 3) if c else None)
        kind = L3_EVENT_SKILLS[cap]
        return {"level": level, "format": fmt, "window_max_sec": wl, "window_min_sec": min(SG.MIN_WIN, wl or SG.MIN_WIN),
                "note": (f"L3 {kind} tier {level}: clip at most {wl:.0f} s inside the sub-goal, containing the event; the question names the MOMENT by describing the event "
                         "('when the lid is placed on the counter, which of these is nearest to the kettle?'), never by time; "
                         + ("relation_at_time: ask the spatial relation among listed objects at that moment (state the reference frame and the candidate set as usual)" if kind == "relation_at_time"
                            else "change_over_time: ask where the object is at the named moment (which surface / fixture / container, e.g. on the counter or in the sink) or where it was before / ends up after the movement"
                                 + (f"; single_choice options must be four DIFFERENT places taken from this list of fixtures that really occur in this video: {sg_.get('video_fixtures')} (the correct one and three others from the list); do not invent places" if sg_.get("video_fixtures") and fmt == "single_choice" else ""))
                         + ("; short_answer: reference = a short phrase with accepted_alternatives" if fmt == "short_answer" else "") + comp_note
                         + (" For change_over_time composed items the program fills the options (endpoints) and the reference: write placeholder options and never reveal the endpoint in the question." if comp_note and kind == "change_over_time" else "")),
                "rule": "controller-fixed: exactly this format and at most this clip length; no time position in the question"}
    if cap in ED.ED_SKILLS: return ED.spec_for(cap, level, c)
    if cap in RF.RF_SKILLS: return RF.spec_for(cap, level, c)
    if cap in SA.SA_SKILLS: return SA.spec_for(cap, level, c)
    if cap in CH.CH_SKILLS: return CH.spec_for(cap, level, c)
    if cap in RS.RS_SKILLS: return RS.spec_for(cap, level, c)
    if cap == "spatial_change":
        sc = sg_.get("sc") or {}; f3 = sg_.get("format") or fmt
        return {"level": level, "format": f3, "window_max_sec": None, "window_min_sec": None,
                "note": f"L3 spatial_change ({sc.get('type')}) tier {sg_.get('tier', level)}: media_refs = EXACTLY the offered window(s); the question names the two moments by sg.sc.moments (start_desc / end_desc) or the object's own move, never by time; "
                        f"ask {sc.get('ask')} about '{sc.get('object')}' measured in real-world (3D) distance; the program fills the options (sg.sc.options) and the reference (sg.sc.answer): write placeholder options",
                "rule": "controller-fixed: exactly this format; windows = the offered window(s); no time position; name the two moments" + ("; which_moved: NEVER name the moved object (it is the answer) - the moments are the start and the end of the clip" if sc.get("type") == "which_moved" else "; name the object")}
    if layer == "L3":
        return {"level": level, "format": fmt, "window_max_sec": None, "window_min_sec": None,
                "note": {1: "L3 relation tier 1: single choice", 2: "L3 relation tier 2: single choice", 3: "L3 relation tier 3: single choice",
                         4: "L3 relation tier 4: short_answer (the Solver states the relation itself, with accepted_alternatives)"}[level] + "; media_refs = EXACTLY the offered window(s)",
                "rule": "controller-fixed: exactly this format; media_refs = the offered window(s); the question names only the object / action of the later sub-goal and gives NO time position"}
    return None


# ---------------------------------------------------------------- 程序补齐(选项 / 窗口 / 参考)
def _tg_options(c, ev, level, win, rng, forbid=(), must=()):
    """时间段选项(clip 内秒)。11-04 v30 重写(修泄漏:旧版干扰段长短不一、受档距挤到一侧,正确段 59/63 在 A/D 且 41/63 最长):
    正确段 = event 核心记录 ±1 s(≥ 4 s);干扰段一律与正确段等长、在 1 s 网格上取,其它 event 的段也先改成等长(以其中点为中心);
    档距 far(10 / 5 / 2 s)= 干扰段与正确段的最小间隔;正确段前后各放几个干扰段(k_before ∈ 可行集合里均匀随机)→ 正确字母 A–D 均匀;
    两侧都放不下时才允许单侧;far 按 far → far/2 → 2 → 1 逐级放宽;仍凑不齐返回 (None, None, None)。"""
    span = ev.get("tg_span") or ev["time"]
    a, b = float(span[0]), float(span[1])
    w0, w1 = float(win[0]), float(win[1]); D = w1 - w0
    def _pad(x, y):
        x, y = x - 1.0, y + 1.0
        if y - x < TG_MIN_OPT_SEC: m_ = (x + y) / 2; x, y = m_ - TG_MIN_OPT_SEC / 2, m_ + TG_MIN_OPT_SEC / 2
        x = max(0.0, x - w0); y = min(D, y - w0); x = max(0.0, min(x, y - 1.0)); return [round(x, 1), round(y, 1)]
    tgt = _pad(a, b); L = float(round(tgt[1] - tgt[0]))
    tgt = [round(max(0.0, min(D - L, (a + b) / 2 - w0 - L / 2))), 0]; tgt[1] = tgt[0] + L        # 整秒等长:M:SS 显示后四段长度一致(v30 首跑 11/40 题长度不齐)
    if 4 * L + 3.0 > D:                                          # 短 clip:四段等长放不下 → 统一缩短(仍包住事件核心 [a,b]),最短 2.5 s
        L = float(max(2, int((D - 3.0) / 4), int((b - a) + 0.5))); m_ = (a + b) / 2 - w0
        s0 = float(round(max(0.0, min(D - L, m_ - L / 2)))); tgt = [s0, s0 + L]
    gap = lambda s, t: max(0.0, max(s[0], t[0]) - min(s[1], t[1]))
    key = lambda s: f"{_mmss(s[0])}-{_mmss(s[1])}"
    far0 = TG_FAR_SEC.get(level, 0.0)
    def _eq(x0, x1):                                             # 等长化(整秒起点):以中点为中心取 L 长
        m_ = (x0 + x1) / 2; s0 = float(round(max(0.0, min(D - L, m_ - L / 2)))); return [s0, s0 + L]
    fixed = []                                                   # 组合题必放的替代段(等长化后)
    for m_ in must:
        s_ = _eq(float(m_[0]) - w0, float(m_[1]) - w0)
        if iou_1d(s_, tgt) <= 0.2 and all(iou_1d(s_, d) <= 0.5 for d in fixed): fixed.append(s_)
    others = []
    for e in (c["sg"].get("sg_events_all") or []):
        if e["event_id"] == ev["event_id"]: continue
        s_ = _eq(float(e["time"][0]) - w0, float(e["time"][1]) - w0)
        if key(s_) != key(tgt): others.append(s_)
    for far, dd in [(far0, 1.0), (far0 / 2, 1.0), (2.0, 1.0), (1.0, 1.0), (1.0, -L / 2), (0.5, -L / 2), (-1.0, -L / 2)]:      # 最后几轮:短 clip 允许干扰段彼此重叠一半;far<0 = 与正确段也可轻微重叠(IoU ≤ 0.2,老规则)
        def ok(s_, dist, far=far, dd=dd):
            if s_[1] - s_[0] < 1.0 or key(s_) == key(tgt) or any(key(s_) == key(d) for d in dist): return False
            if any(gap(s_, f) < 0.5 for f in forbid): return False          # 干扰段不能盖住同一动作的另一次出现
            near_t = gap(s_, tgt) >= far if far >= 0 else iou_1d(s_, tgt) <= 0.2
            return near_t and all((gap(s_, d) >= dd if dd >= 0 else iou_1d(s_, d) <= 0.5) for d in dist)
        grid = [[float(i), float(i) + L] for i in range(0, int(max(0.0, D - L)) + 1)]
        rng.shuffle(grid)
        pool_b = [s_ for s_ in others + grid if (s_[0] + s_[1]) / 2 < (tgt[0] + tgt[1]) / 2 and ok(s_, fixed)]
        pool_a = [s_ for s_ in others + grid if (s_[0] + s_[1]) / 2 >= (tgt[0] + tgt[1]) / 2 and ok(s_, fixed)]
        need = 3 - len(fixed)
        if need <= 0:
            opts = sorted([tgt] + fixed[:3], key=lambda s: s[0]); return opts, opts.index(tgt), far
        def _take(pool, k, dist):
            out = []
            for s_ in pool:
                if len(out) >= k: break
                if ok(s_, dist + out): out.append(s_)
            return out
        feas = []
        for kb in range(0, need + 1):                               # 正确段之前放 kb 个、之后放 need-kb 个
            db = _take(pool_b, kb, fixed); da = _take(pool_a, need - kb, fixed + db)
            if len(db) == kb and len(da) == need - kb: feas.append((kb, db + da))
        if feas:
            kb, dist = feas[rng.randrange(len(feas))]
            opts = sorted([tgt] + fixed + dist, key=lambda s: s[0]); return opts, opts.index(tgt), far
    return None, None, None


def _shuffle_options(pub, pri, c):
    texts = [re.sub(r"^\s*[A-D]\s*[\.\):]\s*", "", o or "").strip() for o in pub["options"]]
    ref = str(pri["proposed_reference_answer"]).strip().upper()[:1]; ans = texts["ABCD".index(ref)]
    rng = random.Random(hashlib.sha1((c.get("evidence_cluster_id", "") + "|" + (pub.get("question") or "")).encode()).hexdigest())
    rng.shuffle(texts)
    pub["options"] = [f"{L}. {t}" for L, t in zip("ABCD", texts)]; pri["proposed_reference_answer"] = "ABCD"[texts.index(ans)]


def autofill(out, ctx, c):
    sg_ = c.get("sg") or {}; pub = out.get("public") or {}; pri = out.get("private") or {}
    if not sg_.get("v24") or not isinstance(pub, dict) or not isinstance(pri, dict): return
    filled = list(pri.get("autofilled") or []); d = ctx.get("difficulty") or {}
    refs = pub.get("media_refs") or []
    if sg_.get("frame"):                                        # L1:窗口 = 帧窗口,variant frame(+ boxes)
        ev = next((x for x in sg_.get("events") or [] if x["event_id"] == pri.get("sg_event_id")), None) or (sg_["events"][0] if sg_.get("events") else None)
        if ev is not None and refs:
            if sg_.get("box_choice"):
                want = [sg_["frame_sec"], round(sg_["frame_sec"] + 1.0, 3)]          # 画框题:帧 = mask 的帧(unit 的 event 对象来自别的 cluster,其 window_frame 是 event 中心)
            else:                                                                   # object_recognition:帧 = Examiner 引用的第一条 narration 的起点 + 0.5 s(event 并集的中心帧可能已换了手里的东西)
                offered = {r["evidence_id"]: r for r in ctx.get("verified_evidence") or []}
                rid = next((x if isinstance(x, str) else x.get("evidence_id") for x in (pri.get("evidence_refs") or []) if (x if isinstance(x, str) else x.get("evidence_id")) in offered and offered[x if isinstance(x, str) else x.get("evidence_id")]["kind"] in ("action_narration", "object_location_transition", "object_move", "utterance", "sound_event")), None)
                if rid is not None:
                    r = offered[rid]; t0_, t1_ = float(r["time"]["start_sec"]), float(r["time"]["end_sec"])
                    t = round(min(t0_ + 0.5, (t0_ + t1_) / 2), 3); want = [t, round(t + 1.0, 3)]; filled.append("frame_at_cited_record")
                else:
                    want = list(ev["window_frame"])
            if [list(map(float, w)) for w in (refs[0].get("windows") or []) if len(w) == 2] != [want]: refs[0]["windows"] = [want]; filled.append("window_frame")
            refs[0]["variant"] = "frame"
            if sg_.get("box_choice"):
                refs[0]["boxes"] = [{"letter": b["letter"], "bbox": b["bbox"]} for b in sg_["boxes"]]
                pub["options"] = [f"{L}. the box labelled {L}" for L in "ABCD"]; pub["format"] = "single_choice"
                pri["proposed_reference_answer"] = sg_["target_letter"]; filled += ["options", "reference"]
                if not pri.get("sg_event_id"): pri["sg_event_id"] = ev["event_id"]; filled.append("sg_event_id")
            pub["observation_cutoff"] = want[1]
        del refs[1:]
    elif sg_.get("tg"):                                         # L2 temporal grounding:窗口 = 整个 sub-goal;选项 / 参考 = 程序生成
        win = list(c["window"])
        if refs:
            refs[0]["windows"] = [win]; del refs[1:]; filled.append("window_whole")
        ev = next((x for x in sg_.get("events") or [] if x["event_id"] == pri.get("sg_event_id")), None) or (sg_["events"][0] if sg_.get("events") else None)
        if ev is not None:
            if not pri.get("sg_event_id"): pri["sg_event_id"] = ev["event_id"]; filled.append("sg_event_id")
            rng = random.Random(hashlib.sha1((c["evidence_cluster_id"] + ev["event_id"] + str(d.get("level"))).encode()).hexdigest())
            offered = {r["evidence_id"]: r for r in ctx.get("verified_evidence") or []}
            rid = next((x if isinstance(x, str) else x.get("evidence_id") for x in (pri.get("evidence_refs") or []) if (x if isinstance(x, str) else x.get("evidence_id")) in offered and offered[x if isinstance(x, str) else x.get("evidence_id")]["kind"] in ("action_narration", "object_location_transition", "object_move", "utterance", "sound_event")), None)
            if rid is not None and not (ev.get("sound") and sg_.get("modality") == "audio_only"):   # 正确段 = Examiner 引用的那条记录(题面描述的就是它);sound_localization 固定用计划的声音记录
                r = offered[rid]; ev = dict(ev, tg_span=[float(r["time"]["start_sec"]), float(r["time"]["end_sec"])])
            span = ev.get("tg_span") or ev["time"]
            a, b = float(span[0]) - float(win[0]), float(span[1]) - float(win[0])
            # 同一动作的其它出现(与题面描述 / 引用记录共享 ≥ 2 个实词的 narration):干扰段必须避开
            qt = SG._toks((pub.get("question") or "") + " " + (offered[rid]["value"].get("text") or offered[rid]["value"].get("narration") or "" if rid is not None else ""))
            forbid = []
            for r in offered.values():
                if r["kind"] != "action_narration" or r["evidence_id"] == rid: continue
                rt = SG._toks(r["value"].get("text") or r["value"].get("narration") or "")
                if len(rt & qt) >= 2:
                    forbid.append([float(r["time"]["start_sec"]) - float(win[0]), float(r["time"]["end_sec"]) - float(win[0])])
            pri["tg_forbid_sec"] = [[round(x, 1), round(y, 1)] for x, y in forbid]
            comp_ = (sg_.get("comp_by_event") or {}).get(ev["event_id"]) if sg_.get("comp_mode") else None
            must = []
            if comp_ and not comp_.get("fallback"):
                must = [a["span"] for a in comp_["alts"]]
                forbid = [f for f in forbid if not any(abs(f[0] - (a["span"][0] - float(win[0]))) < 0.5 for a in comp_["alts"])]
                ev = dict(ev, tg_span=comp_["target"]["span"]); span = comp_["target"]["span"]; a, b = float(span[0]) - float(win[0]), float(span[1]) - float(win[0])
            elif comp_: pri["comp_fallback"] = comp_["fallback"]
            if d.get("level", 1) < 4:
                opts, ci, far_used = _tg_options(c, ev, int(d.get("level", 1)), win, rng, forbid=forbid, must=must)
                pri["tg_far_used"] = far_used
                if opts is None:
                    pri["tg_error"] = "could not build four distinct time-span options (event span too long for this clip)"; return
                pub["format"] = "single_choice"
                pub["options"] = [f"{L}. {_mmss(s[0])}-{_mmss(s[1])}" for L, s in zip("ABCD", opts)]
                pri["proposed_reference_answer"] = "ABCD"[ci]; pri["tg_options_sec"] = opts; pri["tg_event_sec"] = [round(a, 1), round(b, 1)]
                filled += ["options", "reference"]
            else:
                pub["format"] = "time_window"; pub.pop("options", None)
                ref = [round(max(0.0, a - 1.0), 1), round(b + 1.0, 1)]
                pri["proposed_reference_answer"] = f"{_mmss(ref[0])}-{_mmss(ref[1])}"; pri["tw_ref_sec"] = ref; pri["tg_event_sec"] = [round(a, 1), round(b, 1)]
                filled += ["reference", "format_time_window"]
            if must:
                import comp as _C
                alt_letters = {}
                if pub.get("format") == "single_choice":
                    for a_ in comp_["alts"]:
                        s_ = [float(a_["span"][0]) - float(win[0]), float(a_["span"][1]) - float(win[0])]
                        j = next((i for i, o in enumerate(pri["tg_options_sec"]) if iou_1d(o, s_) > 0.3), None)
                        alt_letters[a_["rec"]] = "ABCD"[j] if j is not None else None
                nopt = len(pub.get("options") or [])
                pk = _C.pair_key(c.get("sample_id"), c.get("capability_skill") or ctx.get("current_skill") or sg_.get("skill"), d, float(win[1]) - float(win[0]), nopt)
                keep = [a_ for a_ in comp_["alts"] if pub.get("format") != "single_choice" or (alt_letters.get(a_["rec"]) and alt_letters[a_["rec"]] != pri["proposed_reference_answer"])]
                if keep:
                    pri["comp"] = {**_C.private_block(dict(comp_, alts=keep), c, ev, d, pk), "target_gold": pri["proposed_reference_answer"], "alt_gold": {a_["rec"]: alt_letters.get(a_["rec"]) for a_ in keep},
                                   "dropped_alts": [a_["rec"] for a_ in comp_["alts"] if a_ not in keep]}
                    filled.append("comp")
                else: pri["comp_fallback"] = "alternative_spans_not_placed_as_distinct_options"
        pub["observation_cutoff"] = win[1]
    elif sg_.get("l3_kind") == "change_over_time" and sg_.get("comp_mode"):     # 11-03 组合题:选项 = 目标终点 + 替代锚点终点 + 其它 fixture
        import comp as _C
        ev = next((x for x in sg_.get("events") or [] if x["event_id"] == pri.get("sg_event_id")), None) or (sg_["events"][0] if sg_.get("events") else None)
        comp_ = (sg_.get("comp_by_event") or {}).get(ev["event_id"]) if ev else None
        if comp_ and not comp_.get("fallback") and (d.get("format") == "single_choice"):
            rng = random.Random(hashlib.sha1((c["evidence_cluster_id"] + ev["event_id"] + "comp").encode()).hexdigest())
            extra = [r.get("to") for r in comp_["alts"]] + list(FIX_FILL)
            opts, ci = _C.fill_l3_options(comp_, rng, extra_fixtures=[x for x in extra if x])
            if opts:
                pub["options"] = [f"{L}. {o}" for L, o in zip("ABCD", opts)]; pri["proposed_reference_answer"] = "ABCD"[ci]
                wins_ = [list(map(float, w)) for ref in (pub.get("media_refs") or []) for w in (ref.get("windows") or []) if len(w) == 2]
                wsec = sum(w[1] - w[0] for w in wins_) if wins_ else 0.0
                pk = _C.pair_key(c.get("sample_id"), c.get("capability_skill") or ctx.get("current_skill") or sg_.get("skill"), d, wsec, 4)
                alt_gold = {a["rec"]: "ABCD"[[_opt_text(o) for o in pub["options"]].index(_C.answer_phrase(comp_["answer_kind"], a["alt_answer"]).lower())] if _C.answer_phrase(comp_["answer_kind"], a["alt_answer"]).lower() in [_opt_text(o) for o in pub["options"]] else None for a in comp_["alts"]}
                pri["comp"] = {**_C.private_block(comp_, c, ev, d, pk), "target_gold": pri["proposed_reference_answer"], "alt_gold": alt_gold}
                filled += ["options", "reference", "comp"]
            else: pri["comp_fallback"] = "could_not_fill_four_options"
        elif comp_ and comp_.get("fallback"): pri["comp_fallback"] = comp_["fallback"]
    elif sg_.get("l3_kind") == "spatial_change":                # L3 spatial_change:窗口 / 选项 / 参考全由程序定
        sc = sg_["sc"]; want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]
        if refs:
            refs[0]["windows"] = [list(w) for w in want]; del refs[1:]; filled.append("windows")
        fmt = sg_.get("format") or "single_choice"
        pub["format"] = fmt
        if fmt == "single_choice":
            pub["options"] = [f"{L}. {o}" for L, o in zip("ABCD", sc["options"][:4])]
            pri["proposed_reference_answer"] = "ABCD"[sc["options"].index(sc["answer"])]
        else:
            pub.pop("options", None); pri["proposed_reference_answer"] = sc["answer"]
            pri["accepted_alternatives"] = sorted(set((pri.get("accepted_alternatives") or []) + [sc["answer"]]))
        pri["sg_rel_id"] = sg_["rel_id"]; pri["sc_note"] = sc["note"]; filled += ["options", "reference", "sg_rel_id"]
        pub["observation_cutoff"] = want[-1][1]
    elif sg_.get("l3_kind") == "ego_dir":                       # 11-03 v26:ego_direction_unseen / turn_to_face
        filled += ED.autofill(out, ctx, c)
    elif sg_.get("l3_kind") == "ref_frame":                     # 11-03 v27
        filled += RF.autofill(out, ctx, c)
    elif sg_.get("l3_kind") == "spk":                           # 11-03 v29
        filled += SA.autofill(out, ctx, c)
    elif sg_.get("l3_kind") == "chain":                         # 11-04 v30
        filled += CH.autofill(out, ctx, c)
    elif sg_.get("l3_kind") == "rsn":                           # 11-04 晚 v31
        filled += RS.autofill(out, ctx, c)
    elif sg_.get("l3_kind") == "relation":                      # L3 关系:窗口 = cluster 的 window(s)
        want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]
        if refs:
            got = [list(map(float, w)) for w in (refs[0].get("windows") or []) if len(w) == 2]
            if got != want: refs[0]["windows"] = [list(w) for w in want]; filled.append("windows")
            del refs[1:]
        if pri.get("sg_rel_id") != sg_.get("rel_id"): pri["sg_rel_id"] = sg_.get("rel_id"); filled.append("sg_rel_id")
        pub["observation_cutoff"] = want[-1][1]
    if _V30["modality"] and pub.get("format") == "single_choice" and "options" not in filled and len(pub.get("options") or []) == 4 and str(pri.get("proposed_reference_answer") or "").strip().upper()[:1] in "ABCD":
        _shuffle_options(pub, pri, c); filled.append("options_shuffled")            # 11-04 晚 v30b:Examiner 写的选项正确答案 7/10 在 A → 按种子打乱并重映射参考字母
    if _V30["modality"] and sg_.get("kind") == "L2" and sg_.get("modality") in ("video_only", "audio_only") and refs and not sg_.get("frame"):   # 11-04 v30:L2 模态条件
        v = "mute" if sg_["modality"] == "video_only" else "aonly"
        if refs[0].get("variant") != v: refs[0]["variant"] = v; filled.append("modality_" + v)
        pri["modality"] = sg_["modality"]
    elif _V30["modality"] and sg_.get("kind") == "L2" and sg_.get("modality"): pri["modality"] = sg_["modality"]
    if filled: pri["autofilled"] = sorted(set(filled))


# ---------------------------------------------------------------- 校验
def checks(out, ctx, c, store):
    e = []; sg_ = c["sg"]; pub, pri = out["public"], out["private"]
    q = (pub.get("question") or "").lower(); d = ctx.get("difficulty") or {}
    wins = [list(map(float, w)) for ref in (pub.get("media_refs") or []) for w in (ref.get("windows") or []) if len(w) == 2]
    refs = [x if isinstance(x, str) else x.get("evidence_id") for x in (pri.get("evidence_refs") or [])]
    offered = {r["evidence_id"]: r for r in ctx["verified_evidence"]}
    if isinstance(pri.get("comp"), dict):
        import comp as _C
        e += _C.checks({"target": pri["comp"]["target"], "alts": pri["comp"]["alts"], "mode": pri["comp"]["mode"], "answer_kind": pri["comp"].get("answer_kind") or (sg_.get("comp_by_event") or {}).get(pri.get("sg_event_id"), {}).get("answer_kind")}, pub, pri)
    if sg_.get("tg") and sg_.get("modality") == "audio_only":                 # 11-04 v30 sound_localization:题面只描述声音
        ev_ = next((x for x in sg_.get("events") or [] if x["event_id"] == pri.get("sg_event_id")), None) or (sg_["events"][0] if sg_.get("events") else None)
        sd = (ev_ or {}).get("sound") or {}
        if sd:
            if not (SG._toks(sd["label"]) & SG._toks(q)): e.append(f"sound_localization: describe the sound by its class words ({sd['label']!r})")
            if sd["n_same_in_clip"] > 1 and ORD.get(sd["ordinal"], "") not in q and str(sd["ordinal"]) not in q: e.append(f"sound_localization: this sound occurs {sd['n_same_in_clip']} times in the clip - say which one ({ORD.get(sd['ordinal'])})")
            if not re.search(r"\b(sound|noise|heard|hear|clink|clatter|rustle)\b", q): e.append("sound_localization: refer to what is HEARD")
            objs = SG._toks(" ".join((ev_ or {}).get("objects") or []))
            if objs & SG._toks(q): e.append("sound_localization: do not name the object / action (the Solver only hears the soundtrack); describe the sound")
    if pri.get("tg_error"):
        e.append("temporal grounding: " + pri["tg_error"] + "; cite the single narration record of the described moment in private.evidence_refs (not the whole event)")
    if sg_.get("v24_event"):
        eid = pri.get("sg_event_id"); ev_ids = {x["event_id"] for x in sg_["events"]}
        if eid not in ev_ids:
            e.append(f"private.sg_event_id must be one of the offered expected events {sorted(ev_ids)}"); return e
        ev = next(x for x in sg_["events"] if x["event_id"] == eid)
        ev_toks = {SG._stem(x) for o in ev["objects"] for x in re.findall(r"[a-z]+", o) if x not in SG._STOP} | SG._toks(ev["description"])
        opts = " ".join(pub.get("options") or []).lower()
        if sg_.get("box_choice"):
            if sg_["object"] and not (SG._toks(sg_["object"]) & SG._toks(q)):
                e.append(f"object_box_choice: the question must name the target object {sg_['object']!r} (sg.object)")
            if re.search(r"\b(left|right|top|bottom|upper|lower|corner|centre|center|middle|next to|beside|near)\b", q):
                e.append("object_box_choice: do not describe where the object is in the image; ask only which lettered box contains it")
        elif ev_toks and not (ev_toks & SG._toks(q + " " + opts)):
            e.append(f"question / options must refer to the event {eid} ({ev['description']!r}): none of its words appear")
        if sg_.get("frame"):
            if SG._TIME_CUE.search(q) or re.search(r"\b(clip|video|seconds?|moment when|at the (start|end))\b", q):
                e.append("L1 (single frame): the question must not mention the clip, video or any time; the Solver sees one image ('In this image, ...')")
            if sg_.get("box_choice"):
                if len(wins) != 1 or abs(wins[0][0] - sg_["frame_sec"]) > 0.05:
                    e.append(f"L1 (single frame): media_refs[0].windows must start exactly at {sg_['frame_sec']} (the mask frame)")
            elif len(wins) != 1 or not (ev["time"][0] - 1.0 <= wins[0][0] <= ev["time"][1] + 1.0):
                e.append(f"L1 (single frame): the frame must lie inside the event {eid} (recorded at {ev['time']})")
            band = set(sg_.get("bands", {}).get(d.get("level"), []) or sg_.get("bands", {}).get(str(d.get("level")), []))
            if sg_.get("band_fallback") or d.get("band_fallback") or d.get("band_enforce") is False or sg_.get("box_choice"): band = set()
            if band and not (band & set(refs)):
                e.append(f"L1 tier {d.get('level')}: private.evidence_refs must include one of the band anchor records {sorted(band)[:4]}")
        else:
            if SG._TIME_CUE.search(q):
                e.append(f"{sg_['kind']}: the question must NOT say when in the clip the event happens; describe the event in words only")
            if len(wins) != 1:
                e.append("one window only")
            else:
                w = wins[0]; a, b = ev["time"]
                ov = max(0.0, min(w[1], b) - max(w[0], a))
                if not (w[0] - 0.01 <= (a + b) / 2 <= w[1] + 0.01) and ov < min(3.0, 0.5 * (b - a)):
                    e.append(f"the window {w} must contain the event {eid} (recorded at {a}-{b} s)")
                if w[0] < c["window"][0] - 0.01 or w[1] > c["window"][1] + 0.01:
                    e.append(f"window {w} outside the offered sub-goal window {c['window']}")
                total = w[1] - w[0]
                if d.get("window_max_sec") and total > float(d["window_max_sec"]) + 0.01:
                    e.append(f"tier {d.get('level')}: clip must be at most {d['window_max_sec']:.0f} s (got {total:.1f} s)")
                if d.get("window_min_sec") and total < float(d["window_min_sec"]) - 0.01:
                    e.append(f"clip must be at least {d['window_min_sec']:.0f} s (got {total:.1f} s)")
            if sg_.get("tg") and re.search(r"\b(first|second|third|last|before|after)\s+(the\s+)?(time|thing|action)\b", q) and False: pass
            if sg_.get("l3_kind") == "relation_at_time" and pub.get("format") == "single_choice":
                if not re.search(r"\b(when|while|as|at the moment|the moment)\b", q):
                    e.append("relation_at_time: the question must name the moment by the event ('when / while <event description>, which ...')")
            if sg_.get("l3_kind") == "change_over_time" and pub.get("format") == "single_choice":
                if not re.search(r"\b(before|after|from|where|end(s)? up|moved|taken|placed|put|on the|in the|into)\b", q):
                    e.append("change_over_time: the question must ask where the object is at the named moment, or before / after the movement")
                vf = sg_.get("video_fixtures")
                if vf and not sg_.get("comp_mode"):                                                   # 11-03 v25:每个选项要含一个本视频 fixture
                    bad = [o for o in (pub.get("options") or []) if not any(SG._toks(f) & SG._toks(o) for f in vf)]
                    if bad: e.append(f"change_over_time: every option must name one of the fixtures that occur in this video {vf}; not: {bad}")
    elif sg_.get("l3_kind") == "spatial_change":
        sc = sg_["sc"]
        if sc["type"] == "which_moved":                                  # 11-03:which_moved 的被移动物体就是答案,题面不能点名
            if SG._toks(sc["object"]) & SG._toks(q) - SG._toks(" ".join(o for o in sc["options"] if o != sc["object"])):
                e.append(f"spatial_change (which_moved): the question must NOT name {sc['object']!r} (it is the answer); ask 'between the start and the end of the clip, which of these objects changed place?'")
        elif not (SG._toks(sc["object"]) & SG._toks(q)):
            e.append(f"spatial_change: the question must name the moved object {sc['object']!r}")
        if sc["type"] == "closer_farther" and sc.get("reference") and not (SG._toks(sc["reference"]) & SG._toks(q)):
            e.append(f"spatial_change (closer_farther): the question must name the reference object {sc['reference']!r}")
        if not re.search(r"\b(when|while|after|before|between|once|by the time|start|beginning|end)\b", q):
            e.append("spatial_change: name the two moments by the events (sg.sc.moments) or by the object's own move ('after the X is put down ...'), never by time")
        q_tc = re.sub(r"\b(the\s+)?(start|beginning|end|first segment|second segment)\s+of\s+the\s+clip\b", " ", q) if sc["type"] == "which_moved" else q   # 11-03:which_moved 的时刻就是 clip 起止,不算时间提示
        if SG._TIME_CUE.search(q_tc): e.append("spatial_change: no time position in the question")
        want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]
        if len(wins) != len(want) or any(abs(wins[i][j] - want[i][j]) > 0.05 for i in range(len(want)) for j in (0, 1)):
            e.append(f"spatial_change: media_refs must be exactly the offered window(s) {want} (got {wins})")
        if sc["type"] in ("nearest_after", "nearest_before") and re.search(r"\b(closest|nearest)\b", q) and not re.search(r"\b(3d|three-dimensional|real-world|actual|physical|in space)\b", q):
            e.append("spatial_change (nearest_after): say that 'nearest' means real-world (3D) distance, not distance on the screen")
    elif sg_.get("l3_kind") == "ego_dir":
        e += ED.checks(out, ctx, c, q, wins)
    elif sg_.get("l3_kind") == "ref_frame":
        e += RF.checks(out, ctx, c, q, wins)
    elif sg_.get("l3_kind") == "spk":
        e += SA.checks(out, ctx, c, q, wins)
    elif sg_.get("l3_kind") == "chain":                                       # 11-04 v30
        e += CH.checks(out, ctx, c, q, wins)
    elif sg_.get("l3_kind") == "rsn":                                         # 11-04 晚 v31
        e += RS.checks(out, ctx, c, q, wins)
    elif sg_.get("l3_kind") == "relation":
        if pri.get("sg_rel_id") != sg_["rel_id"]:
            e.append(f"private.sg_rel_id must be {sg_['rel_id']!r}")
        want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]
        if len(wins) != len(want) or any(abs(wins[i][j] - want[i][j]) > 0.05 for i in range(len(want)) for j in (0, 1)):
            e.append(f"L3 relation: media_refs must be exactly the offered window(s) {want} (got {wins})")
        if SG._TIME_CUE.search(q): e.append("L3: no time position in the question")
        ev_a = sg_["events"][0]
        a_toks = {SG._stem(x) for v in ev_a.get("verbs", []) for x in re.findall(r"[a-z]+", v)} if ev_a.get("verbs") else set()
        if a_toks and (a_toks & SG._toks(q)) and pub.get("format") != "short_answer":
            e.append(f"L3: the question must not describe what happened in the earlier sub-goal ({ev_a['description']!r}); name only the later sub-goal's object / action and ask for the relation")
        for ev in sg_["events"][:2]:
            if not (set(ev["records"]) & set(refs)) and not any(SG._near_event(offered[r], [ev]) for r in refs if r in offered and offered[r]["kind"] != "task_step"):
                e.append(f"L3: private.evidence_refs must cite a record of event {ev['event_id']} ({ev['description']!r})")
    return e


# ---------------------------------------------------------------- 帧 / 画框
def render_frame(src, t, out_path, boxes=None):
    """从源视频抽 t 秒的一帧(短边 FRAME_PX),可叠加字母框;已存在不重做。"""
    import subprocess
    from PIL import Image, ImageDraw, ImageFont
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists(): return out_path
    raw = out_path.with_name(out_path.stem.split("_boxes")[0] + "_raw.jpg")
    if not raw.exists():
        tmp = raw.with_name(raw.stem + f".tmp{random.randint(0, 10**6)}.jpg")
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-ss", f"{float(t):.3f}", "-i", str(src), "-frames:v", "1", "-vf", f"scale=-2:{FRAME_PX}", "-q:v", "2", str(tmp)], check=True, capture_output=True)
        tmp.replace(raw)
    if not boxes:
        if not out_path.exists():
            import shutil; shutil.copy(raw, out_path)
        return out_path
    im = Image.open(raw).convert("RGB"); W, H = im.size; dr = ImageDraw.Draw(im)
    try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(18, H // 24))
    except Exception: font = ImageFont.load_default()
    colors = {"A": (255, 60, 60), "B": (60, 200, 60), "C": (60, 120, 255), "D": (255, 200, 0)}
    for b in boxes:
        x0, y0, x1, y1 = [b["bbox"][0] * W, b["bbox"][1] * H, b["bbox"][2] * W, b["bbox"][3] * H]
        col = colors.get(b["letter"], (255, 255, 255))
        for k in range(3): dr.rectangle([x0 - k, y0 - k, x1 + k, y1 + k], outline=col)
        tw, th = dr.textbbox((0, 0), b["letter"], font=font)[2:]
        lx, ly = max(0, min(W - tw - 6, x0)), max(0, y0 - th - 6)
        dr.rectangle([lx, ly, lx + tw + 6, ly + th + 4], fill=col); dr.text((lx + 3, ly + 1), b["letter"], fill=(0, 0, 0), font=font)
    tmp = out_path.with_name(out_path.stem + f".tmp{random.randint(0, 10**6)}.jpg"); im.save(tmp, quality=90); tmp.replace(out_path)
    return out_path


def frame_path(video_id, t, boxes=None, out_dir=None):
    base = out_dir or (P.MEDIA / "frames" / video_id)
    tag = ("_boxes" + hashlib.sha1(json.dumps(boxes, sort_keys=True).encode()).hexdigest()[:8]) if boxes else ""
    return Path(base) / f"{int(round(float(t) * 1000))}{tag}.jpg"


# ---------------------------------------------------------------- 判分:time_window
def parse_time_window(raw):
    """'Time: 0:05-0:12' / '5.0-12.0 s' / '0:05 to 0:12' -> [a, b] 秒;解析不到返回 None。"""
    txt = raw or ""
    m = re.search(r"(?im)^\s*time\s*[:：]\s*(.+)$", txt)
    line = m.group(1) if m else txt
    ms = re.findall(r"(\d+):(\d\d(?:\.\d+)?)", line)
    if len(ms) >= 2:
        a, b = (int(ms[0][0]) * 60 + float(ms[0][1])), (int(ms[1][0]) * 60 + float(ms[1][1]))
    else:
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", line)]
        if len(nums) < 2: return None
        a, b = nums[0], nums[1]
    if b < a: a, b = b, a
    return [a, b]


def iou_1d(a, b):
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0])); ua = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / ua if ua > 0 else 0.0


# ---------------------------------------------------------------- HARNESS 规则(替换 sg.HARNESS_RULES)
HARNESS_RULES = """
- v24 LAYER MODE (clusters carry "sg" with sg.v24 = true; 11-02, user-defined). Every cluster belongs to one task (task_context) and
  carries sg.events: the EXPECTED EVENTS a planner derived from the goal and the sub-goal text, each with the annotation records
  that fix its time. Only these events may be asked about. Formats: difficulty levels 1-3 single_choice, level 4 short_answer,
  except L2 temporal grounding (level 4 = time_window), object_box_choice (always single_choice) and L4 (its own ladder).
  * L1 FRAME PERCEPTION (sg.kind = L1, sg.frame = true): the Solver sees ONE IMAGE, the frame at the centre of the chosen event.
    public.media_refs[0].windows[0] = the event's sg.events[i].window_frame EXACTLY (a 1 s window; the program extracts its first
    frame). The question speaks about "this image" and NEVER mentions the clip, the video, or any time. object_recognition: what
    is being held / handled in the image (distractors = other objects of this task). object_box_choice: the program draws four
    lettered boxes (sg.boxes) on the image; ask "Which box contains the <sg.object>?" naming the object exactly as sg.object and
    nothing about where it is; the program fills the options ("A. the box labelled A" ...) and the reference (sg.target_letter); write four
    placeholder options. private.sg_event_id = the event's id; cite the anchor record (object_box_choice: the mask record sg.mask_id).
  * L2 TEMPORAL GROUNDING (sg.kind = L2): the Solver sees the WHOLE sub-goal clip with audio and must find WHEN something happens.
    - action_recognition / event_object_role (sg.tg = true): media_refs = EXACTLY the offered sub-goal window. The question describes
      the event in words (the action, and for event_object_role the object / tool / destination) and asks when in the clip it
      happens ("In the clip, when does the camera wearer pour the breadcrumbs onto the lid?"). The PROGRAM generates the four time-span
      options and the reference letter (levels 1-3) or the reference span (level 4, format time_window: the Solver answers
      "Time: M:SS-M:SS"); write four placeholder options at levels 1-3 and any placeholder reference. Never give a time position and
      never describe neighbouring actions (they are the distractor spans).
    - sound_action_binding / sound_movement_binding: the question gives ONLY the sound ("the second metallic clink", "the running
      water sound") and asks which action / object movement produces it; the clip is at most difficulty.window_max_sec long
      (15 s / 30 s / whole sub-goal / whole sub-goal) and contains the sound. Never describe the action in the question.
    - action_temporal_order: which of two described actions comes first inside the sub-goal.
    private.sg_event_id = the event's id; no time words in any L2 question.
  * L3 SPATIO-TEMPORAL REASONING (sg.kind = L3):
    - relation_at_time (spatial_near / spatial_side / sound_anchored_spatial_near / sound_anchored_spatial_side; sg.l3_kind =
      relation_at_time): the clip is at most difficulty.window_max_sec (20 s / 40 s / whole sub-goal / whole sub-goal) inside the
      sub-goal and contains the event. The question names the MOMENT by describing the event (or the sound for sound_anchored_*),
      never by time, then asks the spatial relation among the listed candidates at that moment, stating the reference frame
      (egocentric / allocentric, from whose view) and that the comparison is only among the listed candidates. The Solver must first
      find the moment (an L2 skill) and then compare (L3).
    - change_over_time (object_location_at_time / object_state_change; sg.l3_kind = change_over_time): same clip rule; the question
      names the moment by its event and asks WHERE the object is then (which surface / fixture / container: on the counter, in the
      sink, in the cupboard ...), or where it was before and / or where it ends up after the movement. Any question about an
      object's place in the kitchen belongs here (L3), never in L1.
    - spatial_change (sg.l3_kind = spatial_change; sg.sc): one recorded object move (sg.sc.object, moved_from -> moved_to, 3D
      positions from the dataset) and reference objects with 3D positions. Question types (sg.sc.type): nearest_after ("after
      <end moment>, which of the listed objects is the <object> nearest to, in real-world distance?"), nearest_before ("at <start
      moment>, before the <object> is moved, which of the listed objects is it nearest to, in real-world distance?"), closer_farther ("between
      <start moment> and <end moment>, did the <object> end up closer to or farther from the <reference>?"), which_moved ("between
      <start moment> and <end moment>, which of these objects changed place?"). Name the moments with sg.sc.moments.start_desc /
      end_desc (events) or the object's own move; never a time. For which_moved the moments are the start and the end of the
      clip and the question must NOT name the moved object (it is the answer). media_refs = EXACTLY the offered window(s). The program fills the
      options (sg.sc.options) and the reference (sg.sc.answer): write placeholder options; private.sg_rel_id = sg.rel_id.
    - relation between adjacent sub-goals (cross_event_integration / causal_prerequisite_reasoning / hidden_state_inference;
      sg.l3_kind = relation): media_refs = EXACTLY the offered window(s) (one continuous clip from 5 s before the earlier event to
      5 s after the later one, or two 10 s segments joined with title cards when that would exceed 60 s). The question names only
      the later sub-goal's object / action and asks for the relation (what was done to it before, what the earlier step provided,
      what state an appliance is in now). Never describe the earlier event in the question; never give a time position.
      private.sg_rel_id = sg.rel_id; private.evidence_refs cite records of both events.
  * L4 GOAL-CONDITIONED PLANNING (sg.kind = L4): unchanged (the clip is the previous sub-goal and ends at the decision point;
    sg.remaining_sub_goals are answer_only; single choice = the next sub-goal; plan = the remaining stages).
  * COMPOSED ITEMS (contract comp_mode; sg.comp_by_event, 11-03): for L2 temporal grounding and L3 change_over_time the cluster may
    carry, per event, a composition: comp.target (the exact narration / move being asked, its object, which occurrence it is) and
    comp.alts (the same action on a confusable object, or another occurrence of the same action). Write the question so that
    confusing the object or the occurrence leads to a different option: name the target object exactly, say "the first / second
    time" when comp.target.n_same > 1, never describe the alternative events, never reveal the endpoint of a move. The program
    builds the options (alternative spans / endpoints become distractors) and the reference; write placeholder options.
    If comp_by_event[event].fallback is set, write an ordinary v24 item.
""" + ED.HARNESS + RF.HARNESS + SA.HARNESS + CH.HARNESS + RS.HARNESS + """  SOLVER VISIBILITY: the Solver sees only the image / clip and, in some runs, earlier questions about the same event with the
  answers given. It never sees the goal (except above L4 questions), the step list or the expected-event list.
"""
