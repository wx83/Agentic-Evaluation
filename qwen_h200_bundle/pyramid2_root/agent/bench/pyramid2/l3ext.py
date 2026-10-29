#!/usr/bin/env python3
"""L3 扩展 skill(10-27 用户定:prompt §5 列的九项里原来只测「时间关系」,补上真正的跨时间整合 / 空间 / 隐藏状态 / 因果)。

cross_event_integration        两段相隔 Δ 秒的 clip(各 12 s,拼接 24 s)+ 必须同时用到两段证据才能答的题;档 = 两段相距秒数
hidden_state_inference         clip 之前 Δ 秒发生的状态改变(开 / 关 / 盖 / 插电)在 clip 里看不到,问 clip 结束时该物的状态;参考 = 最后一次状态改变 narration;档 = Δ
spatial_state_integration      clip 结束时若干物体中哪个离参照物最近 / 最远;位置 = 官方 3D 放置位置(mask_info),至少一个物体的放置发生在 clip 之外;档 = clip 外放置的物体数
causal_prerequisite_reasoning  clip 里的 sub-goal j 依赖哪个更早的 sub-goal i(物理前提);前提由 Examiner 按任务模型声明(needs_verification,gold_basis 标 EXAMINER_DECLARED);档 = 题型 / 距离

所有时间都来自标注(narration / sub-goal / 物体轨迹),模型不生成时间。cluster 带 "l3ext" = {"kind", ...}(Examiner 可见,Solver 不可见)。
answer_only 在这里的含义扩展为「不在 clip 里、只能用于参考答案」,包括 clip 之前的记录(原来只有 cutoff 之后)。"""
import math, random, re, collections
from pathlib import Path
import p2config as P
import ids
import retrieve as R

SKILLS = ("cross_event_integration", "hidden_state_inference", "spatial_state_integration", "causal_prerequisite_reasoning")
SEG_SEC = 12.0          # integration:每段长
WIN = 30.0
DS = "hdepic_e"
DATASETS = {"hdepic_e", "aea_p"}      # 10-27 晚:AEA protocol clip 也走这些 builder(记录格式相同;位姿按数据集选 pose_hdepic / pose_aea)
L3EXT_VERSION = 3       # 10-27 v10 pilot 后修正(hidden_state 宾语/自动停电器/插头、其它物体假陈述干扰项、integration 边界、causal 多选措辞与前提复用);每个 cluster 的 l3ext.v 记录版本

# ---------------------------------------------------------------- 阶梯(staircase 用)
LADDER = {
    "cross_event_integration": {1: {"format": "single_choice", "knob": (0, 20)}, 2: {"format": "single_choice", "knob": (20, 60)},
                                3: {"format": "single_choice", "knob": (60, 180)}, 4: {"format": "single_choice", "knob": (180, 1e9)}},
    "hidden_state_inference": {1: {"format": "single_choice", "knob": (0, 45)}, 2: {"format": "single_choice", "knob": (45, 150)},
                               3: {"format": "single_choice", "knob": (150, 400)}, 4: {"format": "single_choice", "knob": (400, 1e9)}},
    "spatial_state_integration": {1: {"format": "single_choice", "knob": (0, 0)}, 2: {"format": "single_choice", "knob": (1, 1)},
                                  3: {"format": "single_choice", "knob": (2, 2)}, 4: {"format": "single_choice", "knob": (3, 9)}},
    "causal_prerequisite_reasoning": {1: {"format": "single_choice", "knob": (1, 1e9), "distance": (1, 2)}, 2: {"format": "single_choice", "knob": (3, 1e9), "distance": (3, 999)},
                                      3: {"format": "multi_select", "knob": (3, 1e9)}, 4: {"format": "short_answer", "knob": (1, 1e9)}},
}
for _sk in LADDER:
    for _L in LADDER[_sk].values(): _L.setdefault("window_max_sec", 30.0)
NOTE = {
    "cross_event_integration": {1: "two 12 s segments from the same task, almost adjacent (< 20 s apart); the item must need evidence from BOTH segments",
                                2: "two 12 s segments 20-60 s apart; the item must need evidence from both",
                                3: "two 12 s segments 1-3 minutes apart; the item must need evidence from both",
                                4: "two 12 s segments more than 3 minutes apart; the item must need evidence from both"},
    "hidden_state_inference": {1: "the state change happened less than 45 s before the clip ends (and is NOT in the clip)",
                               2: "the state change happened 45 s - 2.5 min before the clip ends",
                               3: "the state change happened 2.5 - 7 min before the clip ends",
                               4: "the state change happened more than 7 min before the clip ends"},
    "spatial_state_integration": {1: "all four candidate objects were put down inside the clip",
                                  2: "one of the four candidate objects was put down before the clip (its resting place must be recalled)",
                                  3: "two of the four candidate objects were put down before the clip",
                                  4: "three or four of the candidate objects were put down before the clip"},
    "causal_prerequisite_reasoning": {1: "single choice: the prerequisite is 1-2 recorded sub-goals before the one shown",
                                      2: "single choice: the prerequisite is 3 or more sub-goals before the one shown",
                                      3: "multi_select: 3-5 earlier sub-goals, mark which ones are physical prerequisites of the shown one (at least one true, one false)",
                                      4: "short_answer: name the prerequisite sub-goal yourself (verb + object)"},
}


def knob(c):
    m = c.get("l3ext") or {}
    k = m.get("kind")
    if k == "integration": return float(m.get("span_sec") or 0)
    if k == "hidden_state": return float(m.get("delta_sec") or 0)
    if k == "spatial": return int(m.get("n_out") or 0)
    if k == "causal": return int(m.get("max_distance") or 0)
    return 0


def level_filter(skill, level):
    lo, hi = LADDER[skill][level]["knob"]
    return lambda k: lo <= k <= hi


# ---------------------------------------------------------------- 共用
def _ds(r): return (r.get("provenance") or {}).get("dataset")


def _steps(store, vid):
    """task_id -> [ {idx, text, t0, t1, rec} ] 按 idx 排序(只取 hdepic_e 的 sub-goal,不含 next 记录)。"""
    by = collections.defaultdict(list)
    for a in store.of_kind(vid, "task_step", status="verified"):
        if _ds(a) not in DATASETS or a["value"].get("is_next_action") or not a.get("event_id"): continue
        by[a["event_id"]].append({"idx": int(a["value"].get("idx") or 0), "text": a["value"].get("text") or "", "t0": a["time"]["start_sec"], "t1": a["time"]["end_sec"], "rec": a})
    return {t: sorted(v, key=lambda s: s["idx"]) for t, v in by.items()}


def _segs(store, vid):
    return {a["event_id"]: a for a in store.of_kind(vid, "task_segment", status="verified") if _ds(a) in DATASETS and a.get("event_id")}


def _narr(store, vid, t0, t1):
    return [r for r in store.in_window(vid, t0, t1, kinds={"action_narration"}, status="verified") if _ds(r) in DATASETS and r["solver_access"] != "answer_only"]


def _ctx(store, vid, wins, core_ids, skill):
    seen, out = set(core_ids), []
    for w in wins:
        for r in store.in_window(vid, w[0], w[1], status="verified"):
            if r["evidence_id"] in seen or r["kind"] not in R.ALL_CTX or r["solver_access"] == "answer_only" or r["kind"] == "task_step": continue
            seen.add(r["evidence_id"]); out.append(r)
    return R._trim_context(out, skill)


def _step_at(S, t):
    """包含 t 的 sub-goal(没有就最近的)。"""
    for s in S:
        if s["t0"] - 0.5 <= t <= s["t1"] + 0.5: return s
    return min(S, key=lambda s: min(abs(s["t0"] - t), abs(s["t1"] - t))) if S else None


def _ntext(r): return (r["value"].get("narration") or r["value"].get("text") or "").strip()


def _cluster(skill, vid, m, store, *, windows, cutoff, anchor, sample_id, anchor_step_idx, core, meta, two=False):
    w0, w1 = windows[0][0], windows[-1][1]
    core_ids = sorted({r["evidence_id"] for r in core})
    meta = dict(meta); meta.setdefault("v", L3EXT_VERSION)
    core_ids = list(core_ids) + ["anchor:" + str((anchor or {}).get("evidence_id"))]   # v3:同窗口不同锚点(hidden_state 的 other_states 让 core 集合相同)不能共用 cluster id
    return {"evidence_cluster_id": ids.cluster_id(skill, vid, w0, w1, core_ids), "capability_skill": skill, "video_id": vid,
            "media_id": anchor.get("media_id") or m["media_id"], "window": [w0, w1], **({"windows": [list(w) for w in windows]} if two else {}),
            "observation_cutoff": cutoff, "anchor_id": anchor["evidence_id"], "sample_id": sample_id, "anchor_kind": anchor["kind"], "anchor_is_next": False,
            "anchor_step_idx": anchor_step_idx, "core": core, "context": _ctx(store, vid, windows, core_ids, skill), "two_windows_allowed": two,
            "l3ext": meta, "interference": R.interference(store, vid, w0, w1, core_ids, dataset=m.get("dataset"))}


def _stratified(out, skill, seed, max_clusters, prefer=None):
    """按档位轮流取,保证每档都有 cluster;prefer(c) 为真的 cluster 在同档内优先。"""
    rng = random.Random(f"{seed}|{skill}"); rng.shuffle(out)
    by = collections.defaultdict(list)
    for c in out:
        k = knob(c); lv = next((L for L in (1, 2, 3, 4) if level_filter(skill, L)(k)), None)
        by[lv].append(c)
    if prefer:
        for L in by: by[L].sort(key=lambda c: 1 if prefer(c) else 0)      # 优先的排在末尾,pop 先取
    res, i = [], 0
    while len(res) < max_clusters and any(by.values()):
        for L in (1, 2, 3, 4):
            if by[L]: res.append(by[L].pop())
            if len(res) >= max_clusters: break
    return res


# ---------------------------------------------------------------- 1. cross_event_integration
def integration_clusters(store, vid, skill, m, *, seed=0, max_clusters=80):
    D = m.get("duration_sec") or 1e9; out = []
    segs = _segs(store, vid)
    for tid, S in _steps(store, vid).items():
        for i, k in enumerate(S):
            for j in S[i + 1:]:
                w1 = [round(max(0.0, k["t1"] - SEG_SEC), 3), round(k["t1"], 3)]
                w2 = [round(j["t0"], 3), round(min(D, j["t0"] + SEG_SEC), 3)]
                if w1[1] > w2[0] - 1.0 or w1[1] - w1[0] < 8 or w2[1] - w2[0] < 8: continue
                n1 = [r for r in _narr(store, vid, *w1) if w1[0] - 0.05 <= r["time"]["start_sec"] <= w1[1] - 0.5]   # v2:只把在段内开始的 narration 当 observed(边界切断的动作不算)
                n2 = [r for r in _narr(store, vid, *w2) if w2[0] - 0.05 <= r["time"]["start_sec"] <= w2[1] - 0.5]
                if not n1 or not n2: continue
                span = round(w2[0] - w1[1], 1)
                core = [k["rec"], j["rec"]] + n1 + [r for r in n2 if r["evidence_id"] not in {x["evidence_id"] for x in n1}]
                if tid in segs: core.append(segs[tid])
                meta = {"kind": "integration", "span_sec": span, "head_idx": k["idx"], "tail_idx": j["idx"], "n_between": j["idx"] - k["idx"] - 1,
                        "windows": [w1, w2], "head_text": k["text"], "tail_text": j["text"]}
                out.append(_cluster(skill, vid, m, store, windows=[w1, w2], cutoff=w2[1], anchor=k["rec"], sample_id=tid, anchor_step_idx=k["idx"], core=core, meta=meta, two=True))
    return _stratified(out, skill, seed, max_clusters)


# ---------------------------------------------------------------- 2. hidden_state_inference
STATE_VERB = {"turn on": "on", "switch on": "on", "turn off": "off", "switch off": "off", "open": "open", "close": "closed", "shut": "closed",
              "cover": "covered", "uncover": "uncovered", "plug in": "plugged in", "plug": "plugged in", "unplug": "unplugged"}
OPPOSITE = {"on": "off", "off": "on", "open": "closed", "closed": "open", "covered": "uncovered", "uncovered": "covered", "plugged in": "unplugged", "unplugged": "plugged in"}
_ONOFF = {"hob", "stove", "burner", "gas", "induction", "oven", "grill", "tap", "faucet", "water", "light", "lights", "lamp", "extractor", "fan", "hood", "kettle",
          "microwave", "blender", "mixer", "toaster", "fryer", "cooker", "dishwasher", "radio", "tv", "television", "speaker", "heater", "heat", "flame", "stovetop", "cooktop", "appliance"}
_OPENCLOSE = {"fridge", "refrigerator", "freezer", "oven", "microwave", "dishwasher", "window", "lid", "cooker", "fryer", "steamer", "tin", "can", "jar", "bottle"}
_COVER = {"pan", "pot", "saucepan", "bowl", "dish", "cooker", "wok", "kettle", "casserole", "tray", "plate", "container", "jug"}
_NOUN_NORM = {"water": "tap", "faucet": "tap", "lights": "light", "stovetop": "hob", "cooktop": "hob", "stove": "hob", "burner": "hob", "gas": "hob", "flame": "hob",
              "refrigerator": "fridge", "television": "tv", "extractor": "extractor fan", "hood": "extractor fan"}


_STATE_RE = re.compile(r"\b(turn(?:s|ed|ing)? (?:on|off)|switch(?:es|ed|ing)? (?:on|off)|open(?:s|ed|ing)?|clos(?:e|es|ed|ing)|shut(?:s|ting)?|cover(?:s|ed|ing)?|uncover(?:s|ed|ing)?|plug(?:s|ged|ging)? in|unplug(?:s|ged|ging)?)\b")
_VB_NORM = {"turns": "turn", "turned": "turn", "turning": "turn", "switches": "switch", "switched": "switch", "switching": "switch", "opens": "open", "opened": "open", "opening": "open",
            "closes": "close", "closed": "close", "closing": "close", "shuts": "shut", "shutting": "shut", "covers": "cover", "covered": "cover", "covering": "cover",
            "uncovers": "uncover", "uncovered": "uncover", "uncovering": "uncover", "plugs": "plug", "plugged": "plug", "plugging": "plug", "unplugs": "unplug", "unplugged": "unplug", "unplugging": "unplug"}


def _norm_vb(vb):
    w = (vb or "").lower().strip().replace("-", " ").split()
    if not w: return ""
    w[0] = _VB_NORM.get(w[0], w[0])
    return " ".join(w)


def _pairs(r):
    """hdepic_e narration 没有 pairs:verbs × nouns 配对(状态动词配第一个合法宾语);没有 verbs 时从文本正则取动词。"""
    v = r["value"]; verbs = [_norm_vb(x) for x in (v.get("verbs") or [])]
    if not verbs:
        verbs = [_norm_vb(m_.group(1)) for m_ in _STATE_RE.finditer(_ntext(r).lower())]
    nouns = [(n or "").lower().strip() for n in (v.get("nouns") or [])]
    if not nouns:
        return []
    return [(vb, nn) for vb in verbs if STATE_VERB.get(vb) for nn in nouns]


_CONTROL = ("plug", "socket", "switch", "button", "knob", "dial", "handle")
_AUTO_OFF = {"microwave", "kettle", "toaster", "blender", "mixer", "timer", "grinder", "food processor", "processor"}   # 自动停 / 瞬时电器:「on」不可靠
_AUTO_CLOSE = {"trash can", "bin", "pedal bin", "garbage can", "trash", "dustbin", "rubbish bin", "recycling bin"}   # v3:脚踏 / 弹簧盖,「open」不保持
_KEEP_FULL = ("trash can", "garbage can", "pedal bin", "rubbish bin", "recycling bin", "air fryer", "deep fryer", "rice cooker", "slow cooker", "pressure cooker")   # v3:复合名保留,不取 head(「can」「fryer」会歧义)
_COVER_INSTR = {"plate", "lid", "cloth", "foil", "towel", "film", "paper", "cover", "tea towel", "cling film", "saucer", "board"}   # 盖的工具,不是被盖的容器
DEFAULT_STATE = {"fridge door": "closed", "freezer": "closed", "oven door": "closed", "microwave door": "closed", "dishwasher": "closed", "window": "closed",
                 "bottle": "closed", "jar": "closed", "tin": "closed", "can": "closed", "trash can": "closed", "tap": "off", "light": "off", "extractor fan": "off", "tv": "off", "radio": "off", "speaker": "off"}
_COVER_RE = re.compile(r"\b(?:un)?cover(?:s|ed|ing)?\s+(?:up\s+|over\s+)?(?:the|a|an|my|this|that|these|those|some)?\s*([a-z][a-z\-' ]*)")


def _cover_object(text, nouns):
    """cover / uncover 的直接宾语:文本里 cover 后面的名词短语匹配到的 noun;是盖子类或找不到 -> None(v2:「flip the plate ... to cover the bowl」取 bowl)。"""
    for m_ in _COVER_RE.finditer((text or "").lower()):
        tail = m_.group(1).strip()
        for nn in sorted(nouns, key=len, reverse=True):
            if nn and tail.startswith(nn):
                if nn in _COVER_INSTR or nn.split()[-1] in _COVER_INSTR: return None
                return nn
    return None


def _state_events(store, vid, t0, t1):
    """窗口内的状态改变 narration -> [(rec, object, state)]。v2:直接宾语是开关 / 插头的整条跳过;cover 取被盖物;自动停的电器不出「on」。"""
    out = []
    for r in _narr(store, vid, t0, t1):
        nouns = [(n or "").lower().strip() for n in (r["value"].get("nouns") or [])]
        if nouns and any(b in nouns[0] for b in _CONTROL): continue            # 「turn on the microwave plug」:说的是插头,不是电器
        for vb, nn in _pairs(r):
            st = STATE_VERB.get(vb)
            if not st: continue
            if any(b in nn for b in _CONTROL): continue
            if st in ("covered", "uncovered") and _cover_object(_ntext(r), nouns) != nn: continue
            head = nn.split()[-1] if nn else ""
            ok = (st in ("on", "off") and head in _ONOFF) or (st in ("open", "closed") and head in _OPENCLOSE) or \
                 (st in ("covered", "uncovered") and head in _COVER) or (st in ("plugged in", "unplugged"))
            if not ok: continue
            obj = next((k for k in _KEEP_FULL if nn.endswith(k)), _NOUN_NORM.get(head, head))
            if obj == "oven" and st in ("open", "closed"): obj = "oven door"
            if obj == "fridge" and st in ("open", "closed"): obj = "fridge door"
            if obj == "microwave" and st in ("open", "closed"): obj = "microwave door"
            if st == "on" and obj in _AUTO_OFF: continue
            if st == "open" and obj in _AUTO_CLOSE: continue
            out.append((r, obj, st)); break
    return out


def hidden_state_clusters(store, vid, skill, m, *, seed=0, max_clusters=80):
    D = m.get("duration_sec") or 1e9; out = []
    segs = _segs(store, vid); steps = _steps(store, vid)
    for tid, S in steps.items():
        seg = segs.get(tid)
        if seg is None: continue
        T0, T1 = seg["time"]["start_sec"], seg["time"]["end_sec"]
        # v3:状态事件向后多看 600 s,用于证伪「状态保持」(下一次同物体事件若又设成同一状态,说明中间有未 narrate 的反向变化)
        evs_all = sorted(_state_events(store, vid, max(0.0, T0 - 600), min(D, T1 + 600)), key=lambda x: x[0]["time"]["start_sec"])
        evs = [e for e in evs_all if e[0]["time"]["start_sec"] <= T1]
        for n, (rec, obj, st) in enumerate(evs):
            s_end = rec["time"]["end_sec"]
            nxt = next((e for e in evs_all if e[1] == obj and e[0]["time"]["start_sec"] > rec["time"]["start_sec"]), None)
            if nxt and nxt[2] == st: continue          # v3:tap on … (no narrated off) … tap on again => it was turned off unnarrated; reference unreliable
            limit = min(T1, nxt[0]["time"]["start_sec"] - 0.5) if nxt else T1
            if limit - s_end < 12: continue
            # 候选窗口:锚在 (s_end+3, limit) 内的 narration,30 s 居中,不含状态改变本身,结束 ≤ limit
            used = []
            cands = [r for r in _narr(store, vid, s_end + 3, limit) if r["evidence_id"] != rec["evidence_id"]]
            for a in cands:
                w = [max(s_end + 1.0, a["time"]["start_sec"] - 15.0), 0.0]; w[1] = min(limit, D, w[0] + WIN)
                if w[1] - w[0] < 10 or w[0] < T0 - 60 or w[1] > T1 + 0.5: continue
                if any(abs(w[0] - u) < 10 for u in used): continue
                inwin = _narr(store, vid, w[0], w[1])
                if len(inwin) < 2: continue
                delta = round(w[1] - s_end, 1)
                obj_in = any(obj.split()[0] in " ".join((r["value"].get("nouns") or []) + [_ntext(r)]).lower() for r in inwin)
                used.append(w[0])
                stp = _step_at(S, (w[0] + w[1]) / 2)
                # v2:其它物体在 clip 结束时的已知状态(各自最后一次改变在 w[1] 之前)-> Examiner 用它们造「假陈述」干扰项;clip 之前改变的优先
                last = {}
                for r2, o2, s2 in evs:
                    if o2 == obj or r2["time"]["start_sec"] >= w[1] - 0.5: continue
                    last[o2] = (r2, s2)
                others = sorted(({"object": o2, "state": s2, "opposite": OPPOSITE[s2], "changed_at_sec": r2["time"]["start_sec"], "in_clip": r2["time"]["start_sec"] >= w[0],
                                  "evidence_id": r2["evidence_id"]} for o2, (r2, s2) in last.items()), key=lambda x: (x["in_clip"], -x["changed_at_sec"]))[:6]
                core = [dict(rec, solver_access="answer_only")] + inwin + ([stp["rec"]] if stp else []) + [seg]
                if nxt: core.append(dict(nxt[0], solver_access="answer_only"))
                have = {r["evidence_id"] for r in core}
                for o in others:
                    if o["in_clip"] or o["evidence_id"] in have: continue
                    core.append(dict(last[o["object"]][0], solver_access="answer_only")); have.add(o["evidence_id"])
                meta = {"kind": "hidden_state", "object": obj, "state": st, "opposite": OPPOSITE[st], "state_event": {"t0": rec["time"]["start_sec"], "t1": s_end, "text": _ntext(rec)},
                        "delta_sec": delta, "object_in_clip": bool(obj_in), "next_change_sec": nxt[0]["time"]["start_sec"] if nxt else None,
                        "prior_default": DEFAULT_STATE.get(obj) == st, "other_states": others,
                        "note": "the state-change narration is NOT inside the clip; the state still holds at the end of the clip. other_states = recorded states of OTHER objects at the end of the clip (for false distractor statements)"}
                out.append(_cluster(skill, vid, m, store, windows=[[round(w[0], 3), round(w[1], 3)]], cutoff=round(w[1], 3), anchor=rec, sample_id=tid,
                                    anchor_step_idx=stp["idx"] if stp else None, core=core, meta=meta))
    return _stratified(out, skill, seed, max_clusters, prefer=lambda c: not (c.get("l3ext") or {}).get("prior_default"))


# ---------------------------------------------------------------- 3. spatial_state_integration
def _base(name): return re.sub(r"\s*\d+$", "", (name or "").strip().lower())


_BAD_NAME = ("part of", "piece of", "pieces of", "slice of", "slices of", "bit of", "cut off", "peel", "skin", "waste", "scrap", "end of", "ends of", "half of", "stalk", "leftover", "remaining")


_ARTIFACT = re.compile(r"^track\s*\d+|skipped|unknown", re.I)
_FIXTURE_WORDS = {"counter", "kitchen top", "countertop", "tabletop", "sink", "hob", "cupboard", "drawer", "tap", "worktop", "shelf", "floor", "oven", "fridge", "refrigerator", "dishwasher", "bin", "microwave", "cabinet", "wall", "door", "window", "stove", "table"}


def _nameable(name):
    """可当题面物体名:非流水线残名(track N / skipped / unknown)、非固定设施、不是「part of / slice of」这类碎片、≤4 个词。"""
    b = _base(name)
    if not b or len(b.split()) > 4 or _ARTIFACT.search(name or "") or any(x in b for x in _BAD_NAME): return False
    return not any(re.search(rf"\b{re.escape(w)}\b", b) for w in _FIXTURE_WORDS)


def _dist(a, b): return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def spatial_clusters(store, vid, skill, m, *, seed=0, max_clusters=80, margin=0.4):
    D = m.get("duration_sec") or 1e9; out = []
    segs = _segs(store, vid); steps = _steps(store, vid)
    moves = [r for r in store.of_kind(vid, "object_location_transition", status="verified") + store.of_kind(vid, "object_move", status="verified")
             if _ds(r) in DATASETS and (r["value"].get("end_xyz") or None)]
    by_obj = collections.defaultdict(list)
    for r in moves: by_obj[r["value"].get("association_id") or r["value"].get("object_name")].append(r)
    for k in by_obj: by_obj[k].sort(key=lambda r: r["time"]["end_sec"])
    if not by_obj: return []

    def positions_at(T):
        """T 时刻静止的物体:{obj -> (rec, xyz, placed_at)};被拿在手里(有轨迹跨 T)的排除。"""
        pos = {}
        for o, rs in by_obj.items():
            if any(r["time"]["start_sec"] <= T < r["time"]["end_sec"] for r in rs): continue
            prev = [r for r in rs if r["time"]["end_sec"] <= T]
            if not prev: continue
            last = prev[-1]; pos[o] = (last, last["value"]["end_xyz"], last["time"]["end_sec"])
        return pos

    for tid, S in steps.items():
        seg = segs.get(tid)
        if seg is None: continue
        T0, T1 = seg["time"]["start_sec"], seg["time"]["end_sec"]
        used = []
        for a in _narr(store, vid, T0, T1):
            w = [max(T0, a["time"]["start_sec"] - 15.0), 0.0]; w[1] = min(T1, D, w[0] + WIN)
            if w[1] - w[0] < 10 or any(abs(w[0] - u) < 10 for u in used): continue
            T = w[1]; pos = positions_at(T)
            # 参照物:clip 内放下的物体;候选:其它静止物体,基名互不相同且全库唯一
            names = collections.Counter(_base(r["value"].get("object_name")) for r, _, _ in pos.values())
            placed_in = [(o, v) for o, v in pos.items() if v[2] >= w[0] and names[_base(v[0]["value"].get("object_name"))] == 1 and _nameable(v[0]["value"].get("object_name"))]
            if not placed_in: continue
            used.append(w[0])
            rng_ = random.Random(f"{seed}|{vid}|{w[0]:.1f}")
            for ro, rv in placed_in[:2]:
                rb = _base(rv[0]["value"].get("object_name"))
                others = [(o, v, _dist(v[1], rv[1])) for o, v in pos.items() if o != ro and names[_base(v[0]["value"].get("object_name"))] == 1 and _base(v[0]["value"].get("object_name")) != rb]
                others = [x for x in others if 0.15 <= x[2] <= 6.0 and _nameable(x[1][0]["value"].get("object_name"))]
                if len(others) < 4: continue
                inside = [x for x in others if x[1][2] >= w[0]]; outside = [x for x in others if x[1][2] < w[0]]
                combos = []
                for n_out_t in (0, 1, 2, 3, 4):                      # 每个目标档位各凑最多 2 组候选
                    if len(inside) < 4 - n_out_t or len(outside) < n_out_t: continue
                    for _ in range(2):
                        combos.append(rng_.sample(inside, 4 - n_out_t) + rng_.sample(outside, n_out_t))
                seen_c = set()
                for cand in combos:
                  key = tuple(sorted(x[0] for x in cand))
                  if key in seen_c: continue
                  seen_c.add(key)
                  for rel in ("nearest", "farthest"):
                    ds = sorted(x[2] for x in cand)
                    mg = (ds[1] - ds[0]) if rel == "nearest" else (ds[-1] - ds[-2])
                    if mg < margin: continue
                    ans = cand[0] if rel == "nearest" else cand[-1]
                    n_out = sum(1 for x in cand if x[1][2] < w[0])
                    core_c = [dict(x[1][0], solver_access=("observed" if x[1][2] >= w[0] else "answer_only")) for x in cand]
                    core = [rv[0]] + core_c + _narr(store, vid, w[0], w[1])
                    stp = _step_at(S, T)
                    if stp: core.append(stp["rec"])
                    core.append(seg)
                    meta = {"kind": "spatial", "relation": rel, "reference": rb, "reference_placed_at": rv[2], "frame": "allocentric: straight-line distance between the objects' resting positions at the end of the clip; compare only the listed candidates",
                            "candidates": [{"name": _base(x[1][0]["value"].get("object_name")), "dist_m": round(x[2], 2), "placed_at": x[1][2], "in_clip": x[1][2] >= w[0], "fixture": x[1][0]["value"].get("to_fixture")} for x in cand],
                            "answer": _base(ans[1][0]["value"].get("object_name")), "margin_m": round(mg, 2), "n_out": n_out}
                    out.append(_cluster(skill, vid, m, store, windows=[[round(w[0], 3), round(w[1], 3)]], cutoff=round(w[1], 3), anchor=rv[0], sample_id=tid,
                                        anchor_step_idx=stp["idx"] if stp else None, core=core, meta=meta))
                    break                                              # 同一候选集只出一种关系(nearest 优先)
    return _stratified(out, skill, seed, max_clusters)


# ---------------------------------------------------------------- 4. causal_prerequisite_reasoning
def causal_clusters(store, vid, skill, m, *, seed=0, max_clusters=80):
    D = m.get("duration_sec") or 1e9; out = []
    segs = _segs(store, vid)
    for tid, S in _steps(store, vid).items():
        seg = segs.get(tid)
        for j in S[1:]:
            w = [round(max(0.0, j["t0"] - 5.0), 3), 0.0]; w[1] = round(min(D, w[0] + WIN), 3)
            if w[1] - w[0] < 10: continue
            earlier = [i for i in S if i["idx"] < j["idx"] and i["t1"] <= w[0] + 0.5]
            if not earlier: continue
            inwin = _narr(store, vid, w[0], w[1])
            if not inwin: continue
            core = [j["rec"]] + [dict(i["rec"], solver_access="answer_only") for i in earlier] + inwin + ([seg] if seg else [])
            meta = {"kind": "causal", "effect_idx": j["idx"], "effect_text": j["text"], "earlier": [{"idx": i["idx"], "text": i["text"]} for i in earlier],
                    "n_earlier": len(earlier), "max_distance": j["idx"] - earlier[0]["idx"],
                    "note": "the earlier sub-goals are NOT in the clip; the Examiner declares which of them is a physical prerequisite of the shown sub-goal (candidate reference, needs verification)"}
            out.append(_cluster(skill, vid, m, store, windows=[w], cutoff=w[1], anchor=j["rec"], sample_id=tid, anchor_step_idx=j["idx"], core=core, meta=meta))
    return _stratified(out, skill, seed, max_clusters)


BUILDERS = {"cross_event_integration": integration_clusters, "hidden_state_inference": hidden_state_clusters,
            "spatial_state_integration": spatial_clusters, "causal_prerequisite_reasoning": causal_clusters}


def clusters(store, vid, skill, m, *, seed=0, max_clusters=80):
    return BUILDERS[skill](store, vid, skill, m, seed=seed, max_clusters=max_clusters)


# ---------------------------------------------------------------- Examiner 校验
_STATE_WORDS = {"on": ["on", "switched on", "turned on", "running", "lit", "burning", "flowing"], "off": ["off", "switched off", "turned off", "not running", "unlit"],
                "open": ["open"], "closed": ["closed", "shut"], "covered": ["covered", "lid on", "with its lid", "with the lid on"], "uncovered": ["uncovered", "lid off", "without its lid", "without a lid"],
                "plugged in": ["plugged in", "plugged"], "unplugged": ["unplugged", "not plugged"]}
_END_WORDS = ("end of the clip", "clip ends", "at the end", "by the end", "when the clip finishes", "as the clip ends", "last moment", "final moment", "end of this clip")
_REL_WORDS = {"nearest": ("closest", "nearest", "shortest distance"), "farthest": ("farthest", "furthest", "greatest distance", "longest distance")}
_CAND_WORDS = ("of the following", "among the following", "among these", "of these", "listed", "of the four", "among the four", "which of")


def _opt_text(o): return re.sub(r"^\s*[A-E]\s*[\.\):]\s*", "", str(o or "")).strip().lower()


def _has(text, word):
    """词干级包含:word 的每个内容词(词干)都出现在 text 里。"""
    import examiner as EX
    tw = {EX._stem(t) for t in re.findall(r"[a-z]+", (text or "").lower())}
    ws = [EX._stem(t) for t in re.findall(r"[a-z]+", (word or "").lower()) if t not in EX._STOP and len(t) > 2]
    return bool(ws) and all(w in tw for w in ws)


def _loose(want, got):
    import examiner as EX
    return EX._loose_match(want, got) or EX._shares_object(want, got)


def checks(out, ctx, c, store):
    """按 cluster.l3ext.kind 校验;返回错误列表。"""
    meta = c.get("l3ext") or {}
    kind = meta.get("kind")
    if not kind: return []
    pub, pri = out["public"], out["private"]
    q = (pub.get("question") or "").lower(); fmt = pub.get("format"); opts = pub.get("options") or []
    ref = str(pri.get("proposed_reference_answer") or "").strip()
    d = ctx.get("difficulty") or {}
    e = []
    offered = {r["evidence_id"]: r for r in ctx["verified_evidence"]}
    refs = [x if isinstance(x, str) else x.get("evidence_id") for x in (pri.get("evidence_refs") or [])]
    used = [offered[x] for x in refs if x in offered]
    def ref_opt_text():
        if fmt == "single_choice":
            L = ref.upper()[:1]
            return next((_opt_text(o) for o in opts if str(o).strip().upper().startswith(L)), "")
        return ref.lower()
    if kind == "integration":
        w1, w2 = meta["windows"]
        got = [list(map(float, w)) for m_ in (pub.get("media_refs") or []) for w in (m_.get("windows") or []) if len(w) == 2]
        if len(got) != 2 or any(abs(g[i] - w[i]) > 0.05 for g, w in zip(got, (w1, w2)) for i in (0, 1)):
            e.append(f"integration item: media_refs windows must be exactly the two offered segments {[w1, w2]}, got {got}")
        def in_w(r, w): return w[0] - 0.05 <= r["time"]["start_sec"] <= w[1] - 0.5      # v2:必须在段内开始(边界切断的动作不算)
        obs = [r for r in used if r["solver_access"] == "observed" and r["kind"] != "task_segment"]
        if not any(in_w(r, w1) for r in obs) or not any(in_w(r, w2) for r in obs):
            e.append("integration item: private.evidence_refs must include at least one observed record that BEGINS inside segment 1 AND one that begins inside segment 2 (the answer must need both)")
        edge = [r["evidence_id"] for r in obs if r["kind"] == "action_narration" and not (in_w(r, w1) or in_w(r, w2))]
        if edge:
            e.append(f"integration item: cited records {edge} begin outside the segments or in their last 0.5 s; cite only records that begin inside a segment and never count an action cut by a segment boundary")
        if not isinstance(pri.get("integration"), dict) or not pri["integration"].get("why_both_segments"):
            e.append("integration item: private.integration = {\"why_both_segments\": ...} must say what each segment contributes")
        if fmt == "single_choice" and not (pub.get("integration_item") or {}).get("segments") == 2:
            e.append("integration item: public.integration_item = {\"segments\": 2}")
    elif kind == "hidden_state":
        hs = pri.get("hidden_state") if isinstance(pri.get("hidden_state"), dict) else {}
        if (hs.get("state") or "").lower().strip() != meta["state"]:
            e.append(f"hidden_state item: private.hidden_state.state must be {meta['state']!r} (the last recorded state change before the clip), got {hs.get('state')!r}")
        if not _has(hs.get("object") or "", meta["object"]) and not _has(meta["object"], hs.get("object") or ""):
            e.append(f"hidden_state item: private.hidden_state.object must be {meta['object']!r}")
        if not _has(q, meta["object"].split()[0]) and not _has(ref_opt_text(), meta["object"].split()[0]):
            e.append(f"hidden_state item: the object ({meta['object']}) must be named in the question or in the reference option")
        if not any(w in q for w in _END_WORDS):
            e.append("hidden_state item: the question must ask about the state AT THE END OF THE CLIP (say so)")
        for bad in ("turn on", "turned on", "turns on", "switch on", "switched on", "turn off", "turned off", "turns off", "switched off", "opened", "closed the", "covered the", "plugged in", "unplugged", "earlier", "before the clip", "previously"):
            if bad in q: e.append(f"hidden_state item: question must not reveal or hint at the earlier state change ({bad!r})"); break
        rt = ref_opt_text()
        if not any(w in rt for w in _STATE_WORDS[meta["state"]]):
            e.append(f"hidden_state item: the reference option must state that the {meta['object']} is {meta['state']} (got {rt!r})")
        if fmt == "single_choice":
            others = [_opt_text(o) for o in opts if _opt_text(o) != rt]
            if not any(any(w in o for w in _STATE_WORDS[meta["opposite"]]) for o in others):
                e.append(f"hidden_state item: one distractor must state the opposite ({meta['opposite']})")
            if any(any(w in o for w in _STATE_WORDS[meta["state"]]) and not any(w in o for w in _STATE_WORDS[meta["opposite"]]) and not _names_other(o, meta) for o in others):
                e.append("hidden_state item: only the reference option may assert the true state")
            # v2:关于其它物体的干扰项必须是假陈述(与其记录状态相反)
            for o in others:
                for info in meta.get("other_states") or []:
                    if _has(o, info["object"]) and not _has(o, meta["object"]):
                        if _says(o, info["state"]) and not _says(o, info["opposite"]):
                            e.append(f"hidden_state item: option {o!r} is TRUE (the {info['object']} is {info['state']} at the end of the clip); a distractor about another object must assert the OPPOSITE of its recorded state")
                        break
            if len(opts) != 4: e.append("hidden_state item: exactly 4 options")
    elif kind == "spatial":
        sp = pri.get("spatial") if isinstance(pri.get("spatial"), dict) else {}
        if (sp.get("relation") or "") != meta["relation"]:
            e.append(f"spatial item: private.spatial.relation must be {meta['relation']!r}")
        if not _has(q, meta["reference"]):
            e.append(f"spatial item: the question must name the reference object ({meta['reference']}) that distances are measured from")
        if not any(w in q for w in _REL_WORDS[meta["relation"]]):
            e.append(f"spatial item: the question must ask for the {meta['relation']} object ({' / '.join(_REL_WORDS[meta['relation']])})")
        if not any(w in q for w in _END_WORDS):
            e.append("spatial item: the question must say the comparison is at the END OF THE CLIP (where things are resting then)")
        if not any(w in q for w in _CAND_WORDS):
            e.append("spatial item: the question must say the comparison is only among the listed options ('which of the following ...')")
        if fmt == "single_choice":
            texts = [_opt_text(o) for o in opts]
            for cnd in meta["candidates"]:
                if not any(_has(t, cnd["name"]) for t in texts):
                    e.append(f"spatial item: every candidate object must be an option (missing {cnd['name']!r})")
            rt = ref_opt_text()
            if not _has(rt, meta["answer"]):
                e.append(f"spatial item: the reference option must be {meta['answer']!r} (the recorded {meta['relation']} object)")
        if (sp.get("answer") or "") and not _has(sp["answer"], meta["answer"]):
            e.append(f"spatial item: private.spatial.answer must be {meta['answer']!r}")
    elif kind == "causal":
        ca = pri.get("causal") if isinstance(pri.get("causal"), dict) else {}
        earlier = {int(x["idx"]): x["text"] for x in meta["earlier"]}
        if int(ca.get("effect_idx") or -1) != int(meta["effect_idx"]):
            e.append(f"causal item: private.causal.effect_idx must be {meta['effect_idx']} (the sub-goal shown in the clip)")
        if not ca.get("mechanism"):
            e.append("causal item: private.causal.mechanism must explain the physical dependency in one sentence")
        for t in [meta["effect_text"]] + list(earlier.values()):
            if t and len(t) > 12 and t.lower() in q:
                e.append(f"causal item: do not quote a recorded sub-goal verbatim in the question ({t!r})"); break
        if fmt in ("single_choice", "multi_select") and len(opts) < min(4, len(earlier)):
            e.append(f"causal item: offer {min(4, len(earlier))} options (the task has {len(earlier)} earlier sub-goals)")
        if fmt == "multi_select" and not re.search(r"directly or indirectly|direct(?:ly)? or indirect(?:ly)?|including indirect", q):
            e.append("causal item (multi_select): the question must say 'directly or indirectly' (every listed step without which the shown action could not have happened as shown, through any chain, counts)")
        if fmt in ("single_choice", "short_answer"):
            ci = ca.get("cause_idx")
            try: ci = int(ci)
            except (TypeError, ValueError): ci = None
            if ci not in earlier:
                e.append(f"causal item: private.causal.cause_idx must be one of the offered earlier sub-goals {sorted(earlier)}")
            else:
                prior = collections.Counter()
                for h in ctx.get("current_layer_history") or []:
                    if h.get("skill") == "causal_prerequisite_reasoning" and h.get("sample_id") == c.get("sample_id") and h.get("verdict") != "item_invalid":
                        x = h.get("causal_cause_idx")
                        for y in (x if isinstance(x, list) else [x]):
                            if _safe_int(y) is not None: prior[_safe_int(y)] += 1
                lim = 1 if _RETRIEVE_RE.search(earlier[ci].lower()) else 2
                if prior[ci] >= lim:
                    e.append(f"causal item: sub-goal {ci} was already the declared prerequisite of {prior[ci]} earlier item(s) in this task (limit {lim}; retrieval / fetching steps once); pick a different prerequisite, preferring the nearest step that physically created the precondition")
                dist = int(meta["effect_idx"]) - ci; rng = LADDER["causal_prerequisite_reasoning"].get(int(d.get("level") or 0), {}).get("distance")
                if rng and not (rng[0] <= dist <= rng[1]):
                    e.append(f"causal item: at difficulty level {d.get('level')} the prerequisite must be {rng[0]}-{rng[1]} sub-goals before the shown one (got distance {dist})")
                if not _loose(earlier[ci], ref_opt_text()):
                    e.append(f"causal item: the reference must correspond to the declared prerequisite sub-goal {ci}: {earlier[ci]!r} (got {ref_opt_text()!r})")
        if fmt == "multi_select":
            mp = ca.get("option_steps") if isinstance(ca.get("option_steps"), dict) else {}
            cs = ca.get("cause_idx") if isinstance(ca.get("cause_idx"), list) else []
            letters = [str(o).strip().upper()[:1] for o in opts]
            if set(letters) != set(mp.keys()):
                e.append("causal item (multi_select): private.causal.option_steps must map every option letter to an earlier sub-goal idx")
            else:
                for L, idx in mp.items():
                    try: idx = int(idx)
                    except (TypeError, ValueError): idx = None
                    if idx not in earlier: e.append(f"causal item: option {L} maps to idx {idx} which is not an offered earlier sub-goal"); continue
                    ot = next(_opt_text(o) for o in opts if str(o).strip().upper().startswith(L))
                    if not _loose(earlier[idx], ot): e.append(f"causal item: option {L} must paraphrase sub-goal {idx}: {earlier[idx]!r}")
                want = sorted(L for L, idx in mp.items() if _safe_int(idx) in {_safe_int(x) for x in cs})
                got = sorted(re.findall(r"[A-E]", ref.upper()))
                if not cs or want != got:
                    e.append(f"causal item (multi_select): reference letters {got} must equal the options whose step is in private.causal.cause_idx {cs} -> {want}")
                if not (1 <= len(cs) < len(mp)):
                    e.append("causal item (multi_select): at least one option must be a prerequisite and at least one must not")
        pri.setdefault("gold_basis_flags", [])
        if "EXAMINER_DECLARED_PREREQUISITE" not in pri["gold_basis_flags"]: pri["gold_basis_flags"].append("EXAMINER_DECLARED_PREREQUISITE")
    return e


def _safe_int(x):
    try: return int(x)
    except (TypeError, ValueError): return None


_RETRIEVE_RE = re.compile(r"\b(get|gets|getting|got|retriev\w*|fetch\w*|take out|takes out|taking out|took out|bring\w*|brought|gather\w*|collect\w*|grab\w*)\b")


def _says(text, state):
    """选项文字是否断言某状态(整词匹配,避免 'on the counter' 误判为 on)。"""
    t = (text or "").lower()
    return any(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t) for w in _STATE_WORDS[state])


def _names_other(opt_text, meta):
    return any(_has(opt_text, o["object"]) and not _has(opt_text, meta["object"]) for o in (meta.get("other_states") or []))


# ---------------------------------------------------------------- prompt 规则(接在 HARNESS 后面)
HARNESS_RULES = """
- L3 EXTENSION clusters (clusters that carry "l3ext"; skills cross_event_integration / hidden_state_inference /
  spatial_state_integration / causal_prerequisite_reasoning). In these clusters "answer_only" records may also lie
  BEFORE the clip (not observable in it); they are reference material only, never to be described as seen.
  * cross_event_integration (l3ext.kind = integration): public.media_refs must use EXACTLY the two offered windows
    (segment 1 = end of sub-goal head_idx, segment 2 = start of sub-goal tail_idx, in chronological order, span_sec
    apart). Ask something that can only be answered by combining both segments (a count across both, an object or
    state that carries over, what changed between them, which action in segment 2 uses a result of segment 1).
    Never ask merely which segment came first (the order is given). private.evidence_refs must include observed
    records that BEGIN inside segment 1 and inside segment 2 (an action cut by a segment boundary is not shown and
    must not be counted); private.integration = {"why_both_segments": "..."}; public.integration_item =
    {"segments": 2}. Do not ask what happened in between the segments (that is plan_gap_filling).
  * hidden_state_inference (l3ext.kind = hidden_state): the answer_only narration is the LAST recorded change of
    l3ext.object before the clip, so at the end of the clip the object is in l3ext.state. Ask about the state at the
    end of the clip ("At the end of the clip, which of these is true?" or "... is the hob on or off?"). Exactly 4
    options, each a statement about ONE object's state at the end of the clip: (1) l3ext.object is in l3ext.state
    (reference); (2) l3ext.object is in the opposite state; (3)(4) FALSE statements about objects from
    l3ext.other_states, each asserting the OPPOSITE of that object's recorded state (prefer in_clip=false ones; the
    cited answer_only narrations are their evidence). If other_states offers fewer than two objects, use plausible
    but wrong states of l3ext.object instead. Never mention or hint at the earlier change in the question.
    private.hidden_state = {"object", "state"}. The Solver may infer the state from cues in the clip (flame, steam,
    sound, open door) or from earlier answers; "cannot be determined" is NOT an option here.
  * spatial_state_integration (l3ext.kind = spatial): l3ext.candidates are objects resting somewhere at the end of
    the clip (positions from the dataset's 3D annotation; those with in_clip=false were put down before the clip).
    Ask which of the four candidates is the l3ext.relation (nearest / farthest) object to l3ext.reference at the end
    of the clip, straight-line distance, comparing only the four listed options; name the reference object and say
    "at the end of the clip" and "which of the following" in the question. Options = the four candidate names (in
    random order); reference = l3ext.answer. private.spatial = {"relation", "reference", "answer"}.
  * causal_prerequisite_reasoning (l3ext.kind = causal): the clip shows sub-goal effect_idx; l3ext.earlier lists the
    task's earlier recorded sub-goals (answer_only). Choose the earlier sub-goal that is a PHYSICAL PREREQUISITE of
    what is shown (it could not be done, or not as shown, without it), at the distance required by the difficulty
    level, and ask which earlier step was necessary for the action in the clip (or, at level 4, to name it).
    private.causal = {"effect_idx", "cause_idx" (int; a list for multi_select), "mechanism": one sentence, and for
    multi_select "option_steps": {"A": idx, ...}}. Distractors = other earlier sub-goals that are NOT prerequisites.
    Offer 4 options when the task has 4 or more earlier sub-goals. In multi_select the question must say
    "directly or indirectly", and the reference includes every listed step that was needed through any chain.
    Do not reuse a prerequisite already declared for an earlier item of the same task (a retrieval / fetching step
    at most once); prefer the nearest step that physically created the precondition over generic fetching steps.
    Do not quote recorded sub-goal text verbatim. The reference is a declared constraint, flagged for verification.
"""

SCOPE_DEFS = {
    "cross_event_integration":       ("L3", "Combine evidence from two moments of the task far apart in time (two short segments, span 20 s - several minutes): what carried over, what changed, counts across both; event_refs = [head, tail]."),
    "hidden_state_inference":        ("L3", "The state (on/off, open/closed, covered, plugged) of an appliance or container at the end of a clip, when the last change of that state happened before the clip and is not visible in it."),
    "spatial_state_integration":     ("L3", "Which of several objects resting around the kitchen is nearest / farthest to a reference object at the end of the clip, when some of them were put down before the clip (3D resting positions from the dataset)."),
    "causal_prerequisite_reasoning": ("L3", "Which earlier recorded sub-goal was a physical prerequisite of the sub-goal shown in the clip (explicit task model; prerequisite declared by the Examiner, candidate reference)."),
}
SCOPE_NOTES = {
    "cross_event_integration": "evidence_steps are HEAD sub-goals that have a later sub-goal in this task; an entry's event_refs must be [head, tail]; the Solver sees the last 12 s of head and the first 12 s of tail.",
    "hidden_state_inference": "evidence_steps are the sub-goals during which a 30 s clip can be cut after an earlier recorded state change (hob/tap/light on-off, door open-closed, pan covered); the item asks the state at the end of that clip.",
    "spatial_state_integration": "evidence_steps are the sub-goals during which a 30 s clip ends with a reference object just put down; candidates are other resting objects with recorded 3D positions.",
    "causal_prerequisite_reasoning": "evidence_steps are EFFECT sub-goals (idx >= 2) shown in a 30 s clip; the item asks which earlier sub-goal was its physical prerequisite.",
}


# ================================================================ 10-27 第二批(用户定:GT 最硬、填 prompt 空缺):
#   egocentric_frame_transform (L3)  clip 里看到 X 被放下;之后 wearer 走动 / 转身;问 clip 结束时 X 在 wearer 的前左 / 前右 / 后左 / 后右(位姿 + 3D 静止位置)
#   gaze_primed_next_pickup   (L3)  在 gaze priming 之后、手还没动时截断,问接下来会拿起什么(官方 priming + assoc 轨迹起点)
#   object_grounding          (L1)  1 s clip 的第一帧,给出命名物体的框(官方 mask bbox,IoU 判分)
QUADS = ("front-left", "front-right", "back-left", "back-right")
LADDER.update({
    "egocentric_frame_transform": {1: {"format": "single_choice", "knob": (0, 30)}, 2: {"format": "single_choice", "knob": (30, 90)},
                                   3: {"format": "single_choice", "knob": (90, 150)}, 4: {"format": "single_choice", "knob": (150, 360)}},
    "gaze_primed_next_pickup": {1: {"format": "single_choice", "knob": (0, 0.6)}, 2: {"format": "single_choice", "knob": (0.6, 2.5)},
                                3: {"format": "single_choice", "knob": (2.5, 6.0)}, 4: {"format": "single_choice", "knob": (6.0, 1e9)}},
    "object_grounding": {1: {"format": "bbox", "knob": (0.08, 1.0)}, 2: {"format": "bbox", "knob": (0.02, 0.08)},
                         3: {"format": "bbox", "knob": (0.007, 0.02)}, 4: {"format": "bbox", "knob": (0.0, 0.007)}},
})
for _sk in ("egocentric_frame_transform", "gaze_primed_next_pickup", "object_grounding"):
    for _L in LADDER[_sk].values(): _L.setdefault("window_max_sec", 30.0)
NOTE.update({
    "egocentric_frame_transform": {1: "the wearer's heading changed less than 30 degrees between putting the object down and the end of the clip",
                                   2: "heading changed 30-90 degrees (the object is now off to one side)", 3: "heading changed 90-150 degrees", 4: "the wearer turned around (150+ degrees): the object is behind them"},
    "gaze_primed_next_pickup": {1: "the clip ends less than 0.6 s before the pick-up (the hand is already reaching)", 2: "the clip ends 0.6-2.5 s before the pick-up, just after the wearer's gaze went to the object",
                                3: "the clip ends 2.5-6 s before the pick-up, before the gaze cue", 4: "the clip ends more than 6 s before the pick-up: predict from the task state alone"},
    "object_grounding": {1: "the object covers at least 8% of the frame", 2: "the object covers 2-8% of the frame", 3: "the object covers 0.7-2% of the frame", 4: "the object covers less than 0.7% of the frame (small / far)"},
})
_knob_old = knob


def knob(c):
    m = c.get("l3ext") or {}; k = m.get("kind")
    if k == "frame_transform": return float(m.get("heading_change_deg") or 0)
    if k == "next_pickup": return float(m.get("lead_sec") or 0)
    if k == "grounding": return float(m.get("area_frac") or 0)
    return _knob_old(c)


def _pose(store=None, vid=None):
    """位姿模块按视频所属数据集选(10-27 晚):aea_p -> pose_aea(官方 MPS,RGB 规范系),其它 -> pose_hdepic。"""
    try:
        if store is not None and vid is not None and (store.media_of_video(vid) or {}).get("dataset") == "aea_p":
            import pose_aea as POSE; return POSE
        import pose_hdepic as POSE; return POSE
    except Exception:
        return None


def _horiz(v):
    n = math.hypot(v[0], v[1]); return (v[0] / n, v[1] / n) if n > 1e-6 else None


def _bearing(POSE, vid, T, xyz):
    """T 时刻(位姿稳定)物体相对 wearer 的水平方位:返回 (angle_deg, forward_m, lateral_m, range_m, quadrant, margin_deg, forward_h) 或 None。世界 z 向上(重力 -z)。"""
    p = POSE.at(vid, T)
    if p is None: return None
    cam, R = p
    import numpy as np
    f = _horiz(R @ np.array([0.0, 0.0, 1.0])); l = _horiz(R @ np.array([0.0, 1.0, 0.0]))
    if f is None or l is None: return None
    v = (float(xyz[0]) - cam[0], float(xyz[1]) - cam[1])
    fwd = v[0] * f[0] + v[1] * f[1]; lat = v[0] * l[0] + v[1] * l[1]
    rng = math.hypot(*v)
    ang = math.degrees(math.atan2(lat, fwd))            # 0 = 正前,+ = 左
    quad = ("front" if fwd >= 0 else "back") + "-" + ("left" if lat >= 0 else "right")
    margin = min(abs(abs(ang) - 0), abs(abs(ang) - 90), abs(abs(ang) - 180))
    return ang, fwd, lat, rng, quad, margin, f


def frame_transform_clusters(store, vid, skill, m, *, seed=0, max_clusters=80):
    POSE = _pose(store, vid)
    if POSE is None or not POSE.available(vid): return []
    D = m.get("duration_sec") or 1e9; out = []
    segs = _segs(store, vid); steps = _steps(store, vid)
    moves = [r for r in store.of_kind(vid, "object_location_transition", status="verified") + store.of_kind(vid, "object_move", status="verified")
             if _ds(r) in DATASETS and r["value"].get("end_xyz")]
    by_obj = collections.defaultdict(list)
    for r in moves: by_obj[r["value"].get("association_id") or r["value"].get("object_name")].append(r)
    for tid, S in steps.items():
        seg = segs.get(tid)
        if seg is None: continue
        T0, T1 = seg["time"]["start_sec"], seg["time"]["end_sec"]
        narr = _narr(store, vid, T0, T1)
        for oid, rs in by_obj.items():
            rs.sort(key=lambda r: r["time"]["end_sec"])
            for i, p in enumerate(rs):
                t1 = p["time"]["end_sec"]; name = p["value"].get("object_name")
                if not (T0 <= t1 <= T1) or not _nameable(name): continue
                base = _base(name); x = p["value"]["end_xyz"]
                nxt = rs[i + 1]["time"]["start_sec"] if i + 1 < len(rs) else D
                b1 = _bearing(POSE, vid, t1, x)
                if b1 is None: continue
                used = []
                for a in narr:
                    T2 = a["time"]["start_sec"]
                    if T2 < t1 + 4 or T2 > min(t1 + 27, nxt - 0.5, T1): continue
                    if any(abs(T2 - u) < 5 for u in used): continue
                    w = [round(max(0.0, T2 - WIN), 3), round(T2, 3)]
                    if t1 < w[0] + 1.0: continue
                    # 同名其它实例在窗口内放下过 -> 指代不清
                    if any(_base(q["value"].get("object_name")) == base and q is not p and w[0] <= q["time"]["end_sec"] <= w[1] for q in moves): continue
                    b2 = _bearing(POSE, vid, T2, x)
                    if b2 is None or b2[5] < 15.0 or not (0.3 <= b2[3] <= 4.0): continue
                    f1, f2 = b1[6], b2[6]
                    heading = math.degrees(math.acos(max(-1.0, min(1.0, f1[0] * f2[0] + f1[1] * f2[1]))))
                    used.append(T2)
                    inwin = _narr(store, vid, w[0], w[1])
                    mentioned_end = any(base.split()[-1] in " ".join((r["value"].get("nouns") or []) + [_ntext(r)]).lower() for r in inwin if r["time"]["start_sec"] >= T2 - 5)
                    stp = _step_at(S, T2)
                    core = [p] + inwin + ([stp["rec"]] if stp else []) + [seg]
                    meta = {"kind": "frame_transform", "object": base, "placed_at_sec": round(t1, 2), "quadrant": b2[4], "bearing_deg": round(b2[0], 1), "margin_deg": round(b2[5], 1),
                            "forward_m": round(b2[1], 2), "lateral_m": round(b2[2], 2), "range_m": round(b2[3], 2), "heading_change_deg": round(heading, 1),
                            "quadrant_at_placement": b1[4], "mentioned_at_end": bool(mentioned_end),
                            "frame": "egocentric at the END of the clip: the wearer's own front/back and left/right as the device faces then; horizontal bearing to the object's resting position",
                            "options": list(QUADS)}
                    out.append(_cluster(skill, vid, m, store, windows=[w], cutoff=w[1], anchor=p, sample_id=tid, anchor_step_idx=stp["idx"] if stp else None, core=core, meta=meta))
    return _stratified(out, skill, seed, max_clusters)


_PRIME = {}


def _priming(vid):
    if not _PRIME:
        import json as _j
        p = Path("/mnt/data_new/hd-epic/annotations/data/eye-gaze-priming/priming_info.json")
        _PRIME.update(_j.load(open(p)) if p.exists() else {"_": {}})
    return _PRIME.get(vid) or {}


def next_pickup_clusters(store, vid, skill, m, *, seed=0, max_clusters=80):
    D = m.get("duration_sec") or 1e9; out = []
    segs = _segs(store, vid); steps = _steps(store, vid)
    tracks = [r for r in store.of_kind(vid, "object_visible_track", status="verified") if _ds(r) in DATASETS]
    moves = {r["value"].get("track_id"): r for r in store.of_kind(vid, "object_location_transition", status="verified") + store.of_kind(vid, "object_move", status="verified") if _ds(r) in DATASETS}
    gaze = {r["provenance"].get("source_record_id"): r for r in store.of_kind(vid, "gaze_fixation", status="verified") if _ds(r) in DATASETS}
    starts = sorted(((r["time"]["start_sec"], r) for r in tracks), key=lambda x: x[0])
    def track_at(t):
        best = None
        for s, r in starts:
            if abs(s - t) <= 0.15 and (best is None or abs(s - t) < abs(best[0] - t)): best = (s, r)
        return best[1] if best else None
    for tid, S in steps.items():
        seg = segs.get(tid)
        if seg is None: continue
        T0, T1 = seg["time"]["start_sec"], seg["time"]["end_sec"]
        # 本 task 内被拿起的物体(干扰项池)
        picked = [(r["time"]["start_sec"], _base(r["value"].get("name"))) for r in tracks if T0 <= r["time"]["start_sec"] <= T1 and _nameable(r["value"].get("name"))]
        for key, e in _priming(vid).items():
            s = e.get("start")
            if not isinstance(s, dict) or "frame" not in s: continue
            ps = s.get("prime_stats") or {}
            if (ps.get("frame_primed") or -1) < 0 or (ps.get("prime_gap") or 0) < 0.5: continue
            t_pick = s["frame"] / 30.0; t_prime = ps["frame_primed"] / 30.0
            if not (T0 + 10 <= t_pick <= T1): continue
            tr = track_at(t_pick)
            if tr is None or not _nameable(tr["value"].get("name")): continue
            base = _base(tr["value"].get("name"))
            pool = sorted({n for t, n in picked if n != base and _base(n).split()[-1] != base.split()[-1] and abs(t - t_pick) <= 240})
            if len(pool) < 3: continue
            mv = moves.get(tr["value"].get("track_id")); gz = gaze.get(key)
            for cut in (t_pick - 0.3, t_prime + 0.2, t_prime - 2.0, t_prime - 5.0):
                cut = round(min(cut, t_pick - 0.3), 3)
                if cut <= T0 + 8: continue
                w = [round(max(0.0, cut - WIN), 3), cut]
                inwin = _narr(store, vid, w[0], w[1])
                if len(inwin) < 2: continue
                lead = round(t_pick - cut, 2)
                stp = _step_at(S, cut)
                core = [dict(tr, solver_access="answer_only")] + ([dict(mv, solver_access="answer_only")] if mv else []) + ([dict(gz, solver_access="answer_only")] if gz else []) + inwin + ([stp["rec"]] if stp else []) + [seg]
                meta = {"kind": "next_pickup", "object": base, "pickup_sec": round(t_pick, 2), "primed_sec": round(t_prime, 2), "prime_gap_sec": ps.get("prime_gap"), "lead_sec": lead,
                        "gaze_cue_in_clip": cut >= t_prime, "distractor_pool": pool[:8], "dist_to_cam_m": ps.get("dist_to_cam"),
                        "note": "the answer is the object whose recorded pick-up starts lead_sec after the clip ends; the gaze priming (official annotation) happened at primed_sec"}
                out.append(_cluster(skill, vid, m, store, windows=[w], cutoff=cut, anchor=tr, sample_id=tid, anchor_step_idx=stp["idx"] if stp else None, core=core, meta=meta))
    return _stratified(out, skill, seed, max_clusters)


def _bbox_norm(v):
    """mask 锚点框 -> 归一化 [x0,y0,x1,y1]:hdepic_e 的 bbox_1408(1408 px 方图)或 aea_p 的 bbox_px + frame_size。"""
    if v.get("bbox_px") and v.get("frame_size"):
        S = float(v["frame_size"]); return [float(x) / S for x in v["bbox_px"]]
    if v.get("bbox_1408"):
        return [float(x) / 1408.0 for x in v["bbox_1408"]]
    return None


def grounding_clusters(store, vid, skill, m, *, seed=0, max_clusters=80):
    D = m.get("duration_sec") or 1e9; out = []
    segs = _segs(store, vid); steps = _steps(store, vid)
    masks = [r for r in store.of_kind(vid, "object_mask_anchor", status="verified") if _ds(r) in DATASETS and _bbox_norm(r["value"]) and r["value"].get("name")]
    masks.sort(key=lambda r: r["time"]["start_sec"])
    for tid, S in steps.items():
        seg = segs.get(tid)
        if seg is None: continue
        T0, T1 = seg["time"]["start_sec"], seg["time"]["end_sec"]
        used = []
        for r in masks:
            t = r["time"]["start_sec"]; name = r["value"]["name"]
            if not (T0 <= t <= T1 - 1.5) or not _nameable(name): continue
            if any(abs(t - u) < 3 for u in used): continue
            base = _base(name)
            if any(q is not r and abs(q["time"]["start_sec"] - t) <= 1.0 and _base(q["value"].get("name")) == base for q in masks): continue   # 同名多实例 -> 框不唯一
            x0, y0, x1, y1 = _bbox_norm(r["value"])          # 归一化 0-1(hdepic_e: bbox_1408 / 1408;aea_p: bbox_px / frame_size)
            if x1 <= x0 or y1 <= y0: continue
            area = (x1 - x0) * (y1 - y0)
            used.append(t)
            w = [round(t, 3), round(min(D, t + 1.0), 3)]
            ctxn = _narr(store, vid, t - 5, t + 5)
            stp = _step_at(S, t)
            core = [r] + ctxn + ([stp["rec"]] if stp else []) + [seg]
            meta = {"kind": "grounding", "object": base, "frame_sec": round(t, 3), "bbox_norm": [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)],
                    "area_frac": round(area, 4), "fixture": r["value"].get("fixture"), "reference_answer": ", ".join(f"{v * 100:.1f}" for v in (x0, y0, x1, y1)),
                    "note": "1 s clip; the box is for the FIRST frame; reference = official mask bbox as x_min, y_min, x_max, y_max in percent of frame width / height"}
            out.append(_cluster(skill, vid, m, store, windows=[w], cutoff=None, anchor=r, sample_id=tid, anchor_step_idx=stp["idx"] if stp else None, core=core, meta=meta))
    return _stratified(out, skill, seed, max_clusters)


BUILDERS.update({"egocentric_frame_transform": frame_transform_clusters, "gaze_primed_next_pickup": next_pickup_clusters, "object_grounding": grounding_clusters})
SKILLS = SKILLS + ("egocentric_frame_transform", "gaze_primed_next_pickup", "object_grounding")


def parse_bbox(text):
    """从作答里取 4 个数 -> 归一化 [x0,y0,x1,y1](百分比 / 0-1000 / 0-1 自动判);Gemini 式 [ymin,xmin,ymax,xmax] 只在明显超界时交换。"""
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", (text or "").replace("，", ","))]
    if len(nums) < 4: return None
    v = nums[:4]
    mx = max(v)
    if mx > 100.5: v = [x / 1000.0 for x in v]
    elif mx > 1.0: v = [x / 100.0 for x in v]
    x0, y0, x1, y1 = v
    if x1 < x0: x0, x1 = x1, x0
    if y1 < y0: y0, y1 = y1, y0
    return [max(0.0, min(1.0, x0)), max(0.0, min(1.0, y0)), max(0.0, min(1.0, x1)), max(0.0, min(1.0, y1))]


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


_checks_old = checks


def checks(out, ctx, c, store):
    meta = c.get("l3ext") or {}; kind = meta.get("kind")
    if kind not in ("frame_transform", "next_pickup", "grounding"):
        return _checks_old(out, ctx, c, store)
    pub, pri = out["public"], out["private"]
    q = (pub.get("question") or "").lower(); fmt = pub.get("format"); opts = pub.get("options") or []
    ref = str(pri.get("proposed_reference_answer") or "").strip(); e = []
    def ref_opt_text():
        L = ref.upper()[:1]; return next((_opt_text(o) for o in opts if str(o).strip().upper().startswith(L)), "")
    if kind == "frame_transform":
        ft = pri.get("frame_transform") if isinstance(pri.get("frame_transform"), dict) else {}
        if (ft.get("quadrant") or "").lower().replace(" ", "-") != meta["quadrant"]:
            e.append(f"frame_transform item: private.frame_transform.quadrant must be {meta['quadrant']!r} (horizontal bearing of the object's resting position from the device at the end of the clip)")
        if not _has(q, meta["object"].split()[-1]):
            e.append(f"frame_transform item: the question must name the object ({meta['object']}) by what the wearer did with it (it was put down in the clip)")
        if not any(w in q for w in _END_WORDS):
            e.append("frame_transform item: the question must ask about the END of the clip (say so)")
        import examiner as EX
        if not any(w in q for w in EX._VIEW_WORDS):
            e.append("frame_transform item: the question must say the direction is from the camera wearer's own viewpoint at the end of the clip (egocentric: as the camera faces then)")
        if ("left" in q or "right" in q) and not any(w in q for w in ("wearer's", "your", "their", "camera's", "own")):
            e.append("frame_transform item: left/right must be possessed (the wearer's / your left or right)")
        texts = [_opt_text(o).replace(" ", "-") for o in opts]
        for qd in QUADS:
            if not any(qd in t for t in texts): e.append(f"frame_transform item: options must be exactly the four quadrants {list(QUADS)} (missing {qd})")
        if meta["quadrant"] not in ref_opt_text().replace(" ", "-"):
            e.append(f"frame_transform item: the reference option must be {meta['quadrant']!r}")
        pri.setdefault("reference_frame", {"type": "camera_at_time", "reference_timestamp": c.get("observation_cutoff"), "frame_of_reference": {"type": "egocentric", "reference_object": "the camera wearer", "viewpoint": "the camera wearer at the end of the clip",
                       "projection": "horizontal bearing from the device to the object's resting position", "comparison": "absolute quadrant (front/back x left/right) with >= 15 deg margin from every boundary", "handedness": "the wearer's own left / right as the device faces at the end of the clip"}})
    elif kind == "next_pickup":
        if not any(w in q for w in ("next", "about to", "going to", "will the", "will pick", "pick up next", "reach for")):
            e.append("next_pickup item: the question must ask what the wearer will pick up NEXT (after the clip ends)")
        if _has(q, meta["object"]):
            e.append(f"next_pickup item: the question must not name the answer object ({meta['object']})")
        for bad in ("look", "gaze", "glance", "eyes", "stare"):
            if bad in q: e.append(f"next_pickup item: do not mention where the wearer looks ({bad!r}); the Solver must notice that itself"); break
        if fmt == "single_choice":
            if not _has(ref_opt_text(), meta["object"]):
                e.append(f"next_pickup item: the reference option must be the recorded next pick-up: {meta['object']!r}")
            others = [_opt_text(o) for o in opts if _opt_text(o) != ref_opt_text()]
            pool = meta.get("distractor_pool") or []
            if sum(1 for o in others if any(_has(o, pn) for pn in pool)) < 2:
                e.append(f"next_pickup item: at least two distractors must be objects the wearer handles elsewhere in this task: {pool[:6]}")
        np_ = pri.get("next_pickup") if isinstance(pri.get("next_pickup"), dict) else {}
        if not _has(np_.get("object") or "", meta["object"]):
            e.append(f"next_pickup item: private.next_pickup = {{\"object\": {meta['object']!r}}}")
    elif kind == "grounding":
        if fmt != "bbox":
            e.append("grounding item: format must be bbox")
        if not _has(q, meta["object"]):
            e.append(f"grounding item: the question must name the object ({meta['object']})")
        if not any(w in q for w in ("first frame", "start of the clip", "beginning of the clip", "opening frame", "very first")):
            e.append("grounding item: the question must say the box is for the FIRST frame of the clip")
        if pub.get("options"):
            e.append("grounding item: no options for format bbox")
        got = parse_bbox(ref)
        if got is None or iou(got, meta["bbox_norm"]) < 0.97:
            e.append(f"grounding item: proposed_reference_answer must be exactly the recorded box {meta['reference_answer']!r} (x_min, y_min, x_max, y_max in percent of frame width/height)")
        gr = pri.get("grounding") if isinstance(pri.get("grounding"), dict) else {}
        if not _has(gr.get("object") or "", meta["object"]):
            e.append(f"grounding item: private.grounding = {{\"object\": {meta['object']!r}}}")
    return e


HARNESS_RULES += """
  * egocentric_frame_transform (l3ext.kind = frame_transform): the clip shows the wearer putting l3ext.object down at
    placed_at_sec; afterwards the wearer moves / turns (heading_change_deg). Ask where that object is relative to the
    wearer AT THE END of the clip, from the wearer's own viewpoint as the camera faces then: options = exactly the four
    quadrants "front-left", "front-right", "back-left", "back-right" (random order); reference = l3ext.quadrant.
    Refer to the object by what the wearer did with it (never by its position); say "at the end of the clip" and "from the
    camera wearer's own viewpoint"; left/right always possessed. private.frame_transform = {"object", "quadrant"}.
  * gaze_primed_next_pickup (l3ext.kind = next_pickup): the clip ends lead_sec before the wearer picks up l3ext.object
    (recorded pick-up at pickup_sec; the wearer's gaze went to it at primed_sec). Ask which object the wearer will pick up
    next; options = that object + three objects from l3ext.distractor_pool (things handled elsewhere in this task); never
    name the answer in the question and never mention looking / gaze. private.next_pickup = {"object"}.
  * object_grounding (l3ext.kind = grounding; layer L1): a 1 s clip starting at the annotated frame. format "bbox": no
    options; ask for the bounding box of l3ext.object in the FIRST frame of the clip; proposed_reference_answer must be
    exactly l3ext.reference_answer (x_min, y_min, x_max, y_max in percent of frame width/height). private.grounding =
    {"object"}. Scoring = IoU with the recorded box (>= 0.5 correct).
"""
SCOPE_DEFS.update({
    "egocentric_frame_transform": ("L3", "After the wearer puts an object down and then moves or turns, where is that object relative to the wearer at the end of the clip (front/back x left/right, from the wearer's own viewpoint then); needs the clip to show the placement."),
    "gaze_primed_next_pickup": ("L3", "Which object the wearer will pick up next, asked just before the pick-up (clip ends 0.3-8 s before it); reference = the recorded pick-up, cue = the wearer's gaze / head turn."),
    "object_grounding": ("L1", "Give the bounding box of a named object in the first frame of a 1 s clip (official mask box; IoU scoring)."),
})
SCOPE_NOTES.update({
    "egocentric_frame_transform": "evidence_steps are the sub-goals during which a 30 s clip ends after a recorded placement, with the device pose known; the item asks the object's quadrant relative to the wearer at the end.",
    "gaze_primed_next_pickup": "evidence_steps are the sub-goals in which a recorded pick-up with gaze priming happens; the clip ends shortly before the pick-up.",
    "object_grounding": "evidence_steps are the sub-goals containing annotated object masks; the item asks for the box in the first frame of a 1 s clip.",
})


# ================================================================ 10-27 晚 AEA 专属(用户定首跑加两个;标注 = 官方 MPS 位姿 / 视线 + SAM3 fixture 3D,记录由 adapters/aea_p_spatial.py 产生)
#   gaze_direction (L1)             锚点(声音 / narration)时刻,佩戴者的视线相对相机朝向在哪个方向(六向);档 = 题型(左/前/右 三选 → 六向 → 多选陈述 → 简答)
#   sound_source_localization (L2)  一声响起时,发声 fixture 在佩戴者的哪个方向(front / left / right / back);档 = 题型(四向 → 八向 → 多选含距离 → 简答)
#   两者的 knob 只记录「离扇区边界的角度余量」(报告用),不参与分档。
GAZE_H = ("left", "front", "right"); GAZE_V = ("up", "down"); GAZE_SECTORS = tuple(f"{h}-{v}" for v in GAZE_V for h in GAZE_H)
DIRS4 = ("front", "left", "right", "back")
DIRS8 = ("front", "front-left", "left", "back-left", "back", "back-right", "right", "front-right")
LADDER.update({
    "gaze_direction": {1: {"format": "single_choice", "knob": (0, 1e9), "window_max_sec": 12.0}, 2: {"format": "multi_select", "knob": (0, 1e9), "window_max_sec": 12.0},
                       3: {"format": "short_answer", "knob": (0, 1e9), "window_max_sec": 12.0}, 4: {"format": "short_answer", "knob": (0, 1e9), "window_max_sec": 12.0}},
    "sound_source_localization": {1: {"format": "single_choice", "knob": (0, 1e9), "window_max_sec": 30.0}, 2: {"format": "single_choice", "knob": (0, 1e9), "window_max_sec": 20.0},
                                  3: {"format": "multi_select", "knob": (0, 1e9), "window_max_sec": 20.0}, 4: {"format": "short_answer", "knob": (0, 1e9), "window_max_sec": 15.0}},
})
NOTE.update({
    "gaze_direction": {1: "single choice with exactly four options, each one gaze sector (horizontal: the wearer's left / straight ahead / the wearer's right; vertical: up / down), the recorded sector among them: where the wearer's eyes point at the anchor moment (1 s before the clip ends), relative to where the camera faces",
                       2: "multi_select: 3-5 statements about where the wearer looks at the anchor moment (horizontal and/or vertical); mark the true ones (at least one true, one false)",
                       3: "short_answer: describe the gaze direction yourself (horizontal + vertical, relative to where the camera faces); the question may describe the anchor moment by the action / sound happening then",
                       4: "short_answer as level 3, but the question must NOT describe the anchor moment by any action or sound: only 'one second before the clip ends' (the Solver must locate the moment from the clip alone)"},
    "sound_source_localization": {1: "single choice with exactly the four directions front / the wearer's left / the wearer's right / back: from where (relative to the way the wearer faces) the sound came",
                                  2: "single choice with four compass directions (from front, front-left, left, back-left, back, back-right, right, front-right) including the recorded one and at least two of its neighbours (45 / 90 degrees away)",
                                  3: "multi_select: 3-5 statements combining direction and distance (within 1 m / 1-2 m / more than 2 m); mark the true ones (at least one true, one false)",
                                  4: "short_answer: name the direction (and the sounding fixture) yourself"},
})
_knob_old2 = knob


def knob(c):
    m = c.get("l3ext") or {}; k = m.get("kind")
    if k in ("gaze", "sound_source"): return float(m.get("margin_deg") or 0)
    return _knob_old2(c)


def _sector8(ang):
    i = int(round(((ang % 360) + 360) % 360 / 45.0)) % 8
    return DIRS8[i]


def gaze_clusters(store, vid, skill, m, *, seed=0, max_clusters=80):
    D = m.get("duration_sec") or 1e9; out = []
    segs = _segs(store, vid); steps = _steps(store, vid); _ = store.evidence
    recs = sorted((r for r in store.of_kind(vid, "gaze_sample", status="verified") if _ds(r) in DATASETS), key=lambda r: r["time"]["start_sec"])
    for tid, S in steps.items():
        seg = segs.get(tid)
        if seg is None: continue
        T0, T1 = seg["time"]["start_sec"], seg["time"]["end_sec"]; used = []
        for r in recs:
            T = r["time"]["start_sec"]; v = r["value"]
            if not (T0 - 0.5 <= T <= T1 + 0.5) or any(abs(T - u) < 3 for u in used): continue
            used.append(T)
            w = [round(max(0.0, T - 9.0), 3), round(min(D, T + 1.0), 3)]
            anc = store.evidence.get(v.get("anchor_eid")); stp = _step_at(S, T)
            core = [r] + ([anc] if anc else []) + _narr(store, vid, w[0], w[1]) + ([stp["rec"]] if stp else []) + [seg]
            meta = {"kind": "gaze", "anchor_sec": round(T, 3), "anchor_kind": v.get("anchor_kind"), "anchor_label": v.get("anchor_label"), "sector": v["sector"], "horizontal": v["horizontal"], "vertical": v["vertical"],
                    "yaw_deg": v.get("yaw_deg"), "pitch_deg": v.get("pitch_deg"), "margin_deg": v.get("margin_deg"),
                    "note": "the clip ends 1 s after the anchor moment; reference = the wearer's eye-gaze direction at that moment relative to where the camera faces (official MPS eye gaze; yaw + = left, pitch + = up)"}
            out.append(_cluster(skill, vid, m, store, windows=[w], cutoff=None, anchor=r, sample_id=tid, anchor_step_idx=stp["idx"] if stp else None, core=core, meta=meta))
    return _stratified(out, skill, seed, max_clusters)


def sound_source_clusters(store, vid, skill, m, *, seed=0, max_clusters=80):
    D = m.get("duration_sec") or 1e9; out = []
    segs = _segs(store, vid); steps = _steps(store, vid); _ = store.evidence
    recs = sorted((r for r in store.of_kind(vid, "sound_source_direction", status="verified") if _ds(r) in DATASETS), key=lambda r: r["time"]["start_sec"])
    for tid, S in steps.items():
        seg = segs.get(tid)
        if seg is None: continue
        T0, T1 = seg["time"]["start_sec"], seg["time"]["end_sec"]; used = []
        for r in recs:
            T = r["time"]["start_sec"]; v = r["value"]
            if not (T0 - 0.5 <= T <= T1 + 0.5) or any(abs(T - u) < 2 for u in used): continue
            used.append(T)
            w = [round(max(0.0, T - 10.0), 3), round(min(D, T + 5.0), 3)]
            snd = store.evidence.get(v.get("sound_eid")); stp = _step_at(S, T)
            core = [r] + ([snd] if snd else []) + _narr(store, vid, w[0], w[1]) + ([stp["rec"]] if stp else []) + [seg]
            meta = {"kind": "sound_source", "sound_sec": round(T, 3), "sound_label": v.get("sound_label"), "source_name": v.get("source_name"), "sector": v["sector"], "sector8": _sector8(float(v.get("bearing_deg") or 0)),
                    "bearing_deg": v.get("bearing_deg"), "range_m": v.get("range_m"), "range_bucket": v.get("range_bucket"), "margin_deg": v.get("margin_deg"), "bearing_source": v.get("bearing_source"),
                    "note": "reference = horizontal direction of the sounding fixture from the wearer at the sound onset, relative to where the camera faces (front |bearing| <= 45 deg, back >= 135, else left / right)"}
            out.append(_cluster(skill, vid, m, store, windows=[w], cutoff=None, anchor=r, sample_id=tid, anchor_step_idx=stp["idx"] if stp else None, core=core, meta=meta))
    return _stratified(out, skill, seed, max_clusters)


BUILDERS.update({"gaze_direction": gaze_clusters, "sound_source_localization": sound_source_clusters})
SKILLS = SKILLS + ("gaze_direction", "sound_source_localization")

_H_WORDS = {"left": ("left",), "right": ("right",), "front": ("front", "straight ahead", "ahead", "forward", "centre", "center", "directly in front")}
_V_WORDS = {"up": ("up", "upward", "upwards", "above"), "down": ("down", "downward", "downwards", "below")}
_DIST_PAT = (("within 1 m", r"(within|less than|under|closer than)\s*(1|one)\s*(m\b|metre|meter)|arm's reach|arm's length|within reach|very close"),
             ("1-2 m", r"(between\s*(1|one)\s*(and|to|-)\s*(2|two)|(1|one)\s*(-|to)\s*(2|two))\s*(m\b|metre|meter)"),
             ("more than 2 m", r"(more than|over|beyond|farther than|further than|at least)\s*(2|two)\s*(m\b|metre|meter)"))


def _word_dir(text, words):
    """文本里出现的方向词(按给定表);返回集合。"""
    t = " " + re.sub(r"[^a-z\- ]", " ", (text or "").lower()) + " "
    return {k for k, ws in words.items() if any(re.search(rf"(?<![a-z\-]){re.escape(w)}(?![a-z\-])", t) for w in ws)}


def _dir8_in(text):
    t = re.sub(r"[^a-z\- ]", " ", (text or "").lower())
    found = {d for d in DIRS8 if "-" in d and re.search(rf"(?<![a-z\-]){d}(?![a-z\-])", t)}
    if found: return found
    return {d for d in DIRS4 if re.search(rf"(?<![a-z\-]){d}(?![a-z\-])", t)} | ({"front"} if re.search(r"straight ahead|directly ahead|in front", t) else set())


def _dist_bucket(text):
    for b, pat in _DIST_PAT:
        if re.search(pat, (text or "").lower()): return b
    return None


_checks_old2 = checks


def checks(out, ctx, c, store):
    meta = c.get("l3ext") or {}; kind = meta.get("kind")
    if kind not in ("gaze", "sound_source"):
        return _checks_old2(out, ctx, c, store)
    import examiner as EX
    pub, pri = out["public"], out["private"]
    q = (pub.get("question") or "").lower(); fmt = pub.get("format"); opts = pub.get("options") or []
    ref = str(pri.get("proposed_reference_answer") or "").strip(); e = []
    level = int((ctx.get("difficulty") or {}).get("level") or 1)
    letters = [str(o).strip()[:1].upper() for o in opts]
    def ref_letters(): return {x.strip().upper()[:1] for x in re.split(r"[,;/ ]+", ref) if x.strip()}
    def opt_of(L): return next((_opt_text(o) for o in opts if str(o).strip().upper().startswith(L)), "")
    if kind == "gaze":
        if not any(w in q for w in ("look", "gaze", "eyes", "glance", "attention")):
            e.append("gaze item: the question must ask where the wearer is LOOKING (their gaze / eyes) at the anchor moment")
        if not any(w in q for w in ("camera faces", "camera is facing", "facing", "head is pointing", "relative to", "the way the camera", "straight ahead", "as the camera")):
            e.append("gaze item: say the direction is relative to where the camera / head faces at that moment (e.g. 'relative to the direction the camera faces')")
        if not any(w in q for w in ("1 s before the clip ends", "1 s before the end", "one second before", "second before the clip ends", "just before the clip ends", "near the end of the clip", "at the end of the clip", "as the clip ends", "last second", "final second", "right before the clip ends", "before the clip ends")):
            e.append("gaze item: anchor the moment: the gaze is asked for the moment 1 s before the clip ends (say 'just before the clip ends' or similar)")
        h, v = meta["horizontal"], meta["vertical"]
        if fmt == "single_choice":
            secs = [(_word_dir(_opt_text(o), _H_WORDS), _word_dir(_opt_text(o), _V_WORDS)) for o in opts]
            names = [f"{next(iter(a))}-{next(iter(b))}" if len(a) == 1 and len(b) == 1 else None for a, b in secs]
            if len(opts) != 4 or any(n is None for n in names) or len(set(names)) != 4 or any(n not in GAZE_SECTORS for n in names):
                e.append(f"gaze item: exactly four options, each naming ONE horizontal (the wearer's left / straight ahead / the wearer's right) and ONE vertical (up / down) gaze direction, all different, chosen from {list(GAZE_SECTORS)}")
            ro = opt_of(ref.upper()[:1])
            if h not in _word_dir(ro, _H_WORDS) or v not in _word_dir(ro, _V_WORDS):
                e.append(f"gaze item: the reference option must be the recorded sector {meta['sector']!r}")
        elif fmt == "multi_select":
            truth = {}
            for L, o in zip(letters, opts):
                hh, vv = _word_dir(_opt_text(o), _H_WORDS), _word_dir(_opt_text(o), _V_WORDS)
                if not hh and not vv: e.append(f"gaze item: option {L} must state a horizontal (left / straight ahead / right) and/or vertical (up / down) gaze direction"); continue
                if len(hh) > 1 or len(vv) > 1: e.append(f"gaze item: option {L} mixes several directions; one horizontal and/or one vertical direction per statement"); continue
                truth[L] = (not hh or h in hh) and (not vv or v in vv)
            if len(opts) < 3: e.append("gaze item: multi_select needs 3-5 statements")
            if truth and not (any(truth.values()) and not all(truth.values())): e.append("gaze item: multi_select needs at least one true and one false statement")
            want = {L for L, t in truth.items() if t}
            if truth and ref_letters() != want: e.append(f"gaze item: reference letters must be exactly the true statements {sorted(want)} (recorded gaze {meta['sector']})")
        elif fmt == "short_answer":
            if h not in _word_dir(ref, _H_WORDS) or v not in _word_dir(ref, _V_WORDS):
                e.append(f"gaze item: short_answer reference must state both directions of the recorded sector ({h}, {v})")
            if level >= 4:
                kw = [w for w in re.findall(r"[a-z]+", (meta.get("anchor_label") or "").lower()) if w not in EX._STOP and len(w) > 3]
                if any(_has(q, w) for w in kw):
                    e.append(f"gaze item (level 4): the question must not describe the anchor moment by its action / sound ({meta.get('anchor_label')!r}); say only 'one second before the clip ends'")
        for bad in ("annotation", "eye tracker", "eye-tracker", "gaze data"):
            if bad in q: e.append(f"gaze item: do not mention {bad!r}")
        g = pri.get("gaze") if isinstance(pri.get("gaze"), dict) else {}
        if (g.get("sector") or "").lower().replace(" ", "-") != meta["sector"]:
            e.append(f"gaze item: private.gaze = {{\"sector\": {meta['sector']!r}}}")
    else:   # sound_source
        label = (meta.get("sound_label") or "").lower()
        kw = [w for w in re.findall(r"[a-z]+", label) if w not in EX._STOP and len(w) > 3]
        if not any(w in q for w in ("sound", "noise", "hear", "heard", "audible")) and not any(_has(q, w) for w in kw):
            e.append(f"sound_source item: the question must refer to the sound ({meta.get('sound_label')!r}) by what is heard")
        if not any(w in q for w in EX._VIEW_WORDS) and not any(w in q for w in ("facing", "faces", "the way the camera", "where the camera is pointing")):
            e.append("sound_source item: the question must say the direction is relative to the way the camera wearer faces at that moment (egocentric)")
        if ("left" in q or "right" in q) and not any(w in q for w in ("wearer's", "your", "their", "camera's", "own")):
            e.append("sound_source item: left/right must be possessed (the wearer's / your left or right)")
        sec, sec8, bucket = meta["sector"], meta["sector8"], meta.get("range_bucket")
        if fmt == "single_choice":
            if level <= 1:
                ds = [_dir8_in(_opt_text(o)) for o in opts]
                if len(opts) != 4 or any(len(d) != 1 for d in ds) or {next(iter(d)) for d in ds} != set(DIRS4):
                    e.append(f"sound_source item (level 1): exactly four options = {list(DIRS4)} (one direction word each)")
                if _dir8_in(opt_of(ref.upper()[:1])) != {sec}:
                    e.append(f"sound_source item: the reference option must be the recorded direction {sec!r}")
            else:
                ds = [_dir8_in(_opt_text(o)) for o in opts]; names = [next(iter(d)) if len(d) == 1 else None for d in ds]
                i8 = DIRS8.index(sec8); neigh = {DIRS8[(i8 + k) % 8] for k in (-2, -1, 1, 2)}
                if len(opts) != 4 or any(n is None for n in names) or len(set(names)) != 4 or sec8 not in names or len(neigh & set(names)) < 2:
                    e.append(f"sound_source item (level 2): exactly four options, each ONE compass direction from {list(DIRS8)}, all different, including the recorded {sec8!r} and at least two of its neighbours {sorted(neigh)}")
                if _dir8_in(opt_of(ref.upper()[:1])) != {sec8}:
                    e.append(f"sound_source item: the reference option must be the recorded compass direction {sec8!r}")
        elif fmt == "multi_select":
            truth = {}
            for L, o in zip(letters, opts):
                t = _opt_text(o); d = _dir8_in(t); b = _dist_bucket(t)
                if not d: e.append(f"sound_source item: option {L} must state a direction (front / left / right / back or a compass direction)"); continue
                if len(d) > 1: e.append(f"sound_source item: option {L} names several directions"); continue
                dd = next(iter(d)); ok = (dd == sec8) if "-" in dd else (dd == sec)
                if b is not None: ok = ok and (b == bucket)
                truth[L] = ok
            if len(opts) < 3: e.append("sound_source item: multi_select needs 3-5 statements")
            if truth and not (any(truth.values()) and not all(truth.values())): e.append(f"sound_source item: need at least one true and one false statement (recorded: {sec} / {sec8}, {bucket})")
            want = {L for L, t in truth.items() if t}
            if truth and ref_letters() != want: e.append(f"sound_source item: reference letters must be exactly the true statements {sorted(want)}")
        elif fmt == "short_answer":
            d = _dir8_in(ref)
            if not d or not (sec in d or sec8 in d):
                e.append(f"sound_source item: short_answer reference must name the recorded direction ({sec} / {sec8})")
        ss = pri.get("sound_source") if isinstance(pri.get("sound_source"), dict) else {}
        if (ss.get("sector") or "").lower() != sec:
            e.append(f"sound_source item: private.sound_source = {{\"sector\": {sec!r}}}")
    return e


HARNESS_RULES += """
  * gaze_direction (l3ext.kind = gaze; layer L1; AEA): the clip ends 1 s after anchor_sec, when <anchor_label> happens. Ask where the
    camera wearer is LOOKING (eye gaze) at that moment, relative to the direction the camera faces then (say so, and say the moment
    is just before the clip ends). Level 1: single choice with exactly four options, each ONE horizontal (the wearer's left /
    straight ahead / the wearer's right) + ONE vertical (up / down) word, all different, the recorded sector among them; reference =
    l3ext.sector. Level 2: multi_select, 3-5 statements each naming one horizontal and/or one vertical gaze direction; true = agrees
    with the recorded sector. Level 3: short_answer naming both directions (the question may describe the moment by the action /
    sound then). Level 4: short_answer, but the question must NOT describe the moment by any action or sound: only "one second
    before the clip ends". Never mention eye tracking or annotation. private.gaze = {"sector": l3ext.sector}.
  * sound_source_localization (l3ext.kind = sound_source; layer L2; AEA, spatial audio): at sound_sec the sound <sound_label>
    is heard (its source is the fixture <source_name>, at range_m). Ask from which direction, relative to the way the camera wearer
    faces at that moment (egocentric; say so), the sound came. Level 1: exactly four options front / the wearer's left / the wearer's
    right / back, reference = l3ext.sector. Level 2: exactly four options, each ONE compass direction out of front, front-left, left,
    back-left, back, back-right, right, front-right, including the recorded l3ext.sector8 and at least two of its neighbours
    (45 or 90 degrees away); reference = l3ext.sector8. Level 3: multi_select, 3-5 statements combining a direction with
    (optionally) a distance phrase ("within 1 m", "1-2 m", "more than 2 m"); true = direction agrees (four-way vs sector,
    compass vs sector8) and the distance phrase, if any, equals range_bucket. Level 4: short_answer naming the direction (the
    sounding fixture may be named too). Refer to the sound by what is heard; left/right always possessed.
    private.sound_source = {"sector": l3ext.sector}.
"""
SCOPE_DEFS.update({
    "gaze_direction": ("L1", "Where the camera wearer's eyes are directed at one anchored moment of a sub-goal (left / straight ahead / right x up / down, relative to where the camera faces); reference = official eye-gaze estimate."),
    "sound_source_localization": ("L2", "From which direction, relative to the way the wearer faces, a sound of the task came (the sounding fixture located in 3D); spatial-audio question anchored to an annotated sound."),
})
SCOPE_NOTES.update({
    "gaze_direction": "evidence_steps are the sub-goals containing an anchored moment (a sound or a captioned action) with an eye-gaze sample; pick moments where the gaze relates to the goal (looking at the target object / destination).",
    "sound_source_localization": "evidence_steps are the sub-goals containing an annotated sound whose source fixture is known in 3D (appliance door, tap, drawer, table); pick sounds made by the goal's actions.",
})
