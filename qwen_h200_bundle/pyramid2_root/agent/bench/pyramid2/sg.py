"""10-28 v15(用户定,sub-goal 结构版):
planner 只看 goal + sub-goal 文字,写出「完成每个 sub-goal 必然发生的 event」(动作 / 声音 / 位置变化 / 状态变化),不看标注;
程序把 event 对到 sub-goal 时间段内的 narration / sound / movement 记录拿时间(narration 太碎,只用来定时间);标注里有、planner 没列的东西不出题。
clip 按 sub-goal 切:
  L1  event 前后各 5 s(题面给 event 描述 + clip 内时间位置);难度 = 感知量分位(面积 / 距离余量 / 干扰)+ 题型
  L2  窗口 ≤ sub-goal:10 / 20 / 40 s / 整个 sub-goal(题面只给 event 描述,不给时间);难度 = 窗口长度
  L3  跨 sub-goal 的相关 event:1 档两段各 10 s 拼接(无关内容全剪掉);2 档 + 第三个相关 event;3 档混一段无关片段;4 档 A 到 B 连续(≤180 s,放不下则两段各 90 s)
  L4  决策点 = sub-goal 起点(planner 去掉重复),clip = 前一个 sub-goal 整段,cutoff = 本 sub-goal 起点;题型 × 规模四档(staircase.PLAN_U 不变)
history 按 sub-goal 分组(chain.select_by_subgoal)。所有时间来自标注。cluster 带 "sg" 字段(Examiner 可见,Solver 不可见)。"""
import json, hashlib, time, re, random, collections, statistics
from pathlib import Path
import p2config as P
import ids
import retrieve as R

CACHE = P.DATA / "sg_cache"
DS = {"hdepic_e"}
EVENT_PAD = 5.0                      # L1 / L3 段:event 中心 ± 5 s
L2_WINDOWS = {1: 15.0, 2: 30.0, 3: None, 4: None}       # v16(10-28 用户定):15 / 30 / 整段单选 / 整段短答;None = 整个 sub-goal
L3_MAX_SEC = 180.0                   # v16:L3 = 本 sub-goal + 相邻 sub-goal 的连续窗口,1 档两段、2 档前+本+后、3/4 档以 pair 为中心扩到 180 s(3 单选,4 短答)
MIN_WIN = 10.0
FORMAT_OF = {1: "single_choice", 2: "single_choice", 3: "single_choice", 4: "short_answer"}     # v16:各层 1-3 档单选,4 档开放作答
L3_REL_SKILL = {"object_continuity": "cross_event_integration", "state_change": "cross_event_integration",
                "causal_prerequisite": "causal_prerequisite_reasoning", "hidden_state": "hidden_state_inference", "spatial_end_state": "spatial_state_integration"}
L1_SKILLS = ["object_recognition", "spatial_near", "spatial_side", "object_location_at_time", "object_grounding"]
L2_SKILLS = ["action_recognition", "event_object_role", "action_temporal_order", "sound_action_binding", "object_state_change", "sound_movement_binding",
             "sound_anchored_spatial_near", "sound_anchored_spatial_side"]
L3_SKILLS = sorted(set(L3_REL_SKILL.values()))
L4_SKILLS = ["goal_conditioned_planning"]
LAYER_OF = {**{s: "L1" for s in L1_SKILLS}, **{s: "L2" for s in L2_SKILLS}, **{s: "L3" for s in L3_SKILLS}, **{s: "L4" for s in L4_SKILLS}}
EVENT_TYPES = ("action", "sound", "placement", "state")
SKILL_DEFS = {
    "object_recognition": "L1: which object is in hand / being handled at the moment of the event",
    "spatial_near": "L1: at the moment of the event, which of the listed objects is nearest to a reference object (3D positions from the dataset)",
    "spatial_side": "L1: at the moment of the event, which listed object is leftmost / rightmost from the wearer's viewpoint",
    "object_location_at_time": "L1: on which surface / fixture / container an object is put down at the event",
    "object_grounding": "L1: localise the object of the event in a frame (bounding box)",
    "action_recognition": "L2: what action (verb + object) the event is",
    "event_object_role": "L2: which object is acted on, with which tool, to which destination in the event",
    "action_temporal_order": "L2: the order of two actions shown close together inside one sub-goal",
    "sound_action_binding": "L2: which action / object produced the sound heard",
    "object_state_change": "L2: where an object was taken from and where it went in one movement",
    "sound_movement_binding": "L2: which object movement coincides with the sound",
    "sound_anchored_spatial_near": "L2: at the moment of a sound, which listed object is nearest to a reference object",
    "sound_anchored_spatial_side": "L2: at the moment of a sound, which listed object is leftmost / rightmost for the wearer",
}
REL_DEFS = {
    "object_continuity": "the same object / ingredient appears in an event of sub-goal k and an event of the ADJACENT sub-goal k+1; what happened to it between them (chopped broccoli -> in the pan)",
    "state_change": "how the state of an object differs between the two events (whole -> chopped, empty -> full, raw -> browned)",
    "causal_prerequisite": "the earlier event is a physical prerequisite of the later one (could not be done without it)",
    "hidden_state": "an appliance / container state was set in the earlier event and is not visible in the later segment; what is its state at the end of the later segment",
    "spatial_end_state": "after placements in the two events, which listed object ends nearest / farthest to a reference object (needs 3D records)",
}
_STOP = {"the", "a", "an", "and", "of", "for", "to", "on", "in", "with", "up", "out", "by", "from", "at", "its", "his", "her", "their", "some", "into", "onto",
         "my", "your", "our", "it", "is", "be", "or", "as", "then", "so", "that", "this", "while", "using", "use", "hand", "hands", "left", "right", "both"}


def _stem(w):
    w = w.lower()
    for suf in ("ing", "ies", "es", "ed", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            w = w[: -len(suf)]
            if suf == "ing" and len(w) > 2 and w[-1] == w[-2]: w = w[:-1]
            return w
    return w


def _toks(s):
    return {_stem(w) for w in re.findall(r"[a-z]+", (s or "").lower()) if w not in _STOP and len(w) > 2}


def _ds(r): return (r.get("provenance") or {}).get("dataset")


# ---------------------------------------------------------------- task / records
def task_info(store, task_id):
    _ = store.evidence
    recs = store.by_event.get(task_id, [])
    seg = next((r for r in recs if r["kind"] == "task_segment"), None)
    if seg is None: return None
    steps = sorted([{"idx": int(s["idx"]), "text": s["text"], "t0": float(s["t0"]), "t1": float(s["t1"])} for s in seg["value"].get("steps") or []], key=lambda s: s["idx"])
    step_rec = {int(r["value"].get("idx") or 0): r for r in recs if r["kind"] == "task_step" and not r["value"].get("is_next_action")}
    nxt = next((r for r in recs if r["kind"] == "task_step" and r["value"].get("is_next_action")), None)
    return {"task_id": task_id, "video_id": seg["video_id"], "media_id": seg.get("media_id"), "goal": seg["value"].get("goal"), "steps": steps,
            "t0": seg["time"]["start_sec"], "t1": seg["time"]["end_sec"], "seg": seg, "step_rec": step_rec, "next": nxt}


def _recs(store, vid, t0, t1, kinds=None):
    out = [r for r in store.in_window(vid, t0, t1, kinds=kinds, status="verified") if _ds(r) in DS and r["solver_access"] != "answer_only"]
    return out


# ---------------------------------------------------------------- 1. planner(goal + sub-goal 文字 -> 期望 event)
def _prompt(contract):
    import examiner as EX
    p = EX._prompts(contract)
    if not p.get("scope"):
        raise KeyError(f"prompt file {p.get('_path')} has no '## 8.' planner section")
    return p["scope"]


def build_input(store, contract, task_id):
    ti = task_info(store, task_id)
    if ti is None: return None
    skills = [s for s in (contract.get("include_skills") or list(LAYER_OF)) if s in LAYER_OF]
    return {"task_id": task_id, "goal": ti["goal"], "sub_goals": [{"idx": s["idx"], "text": s["text"]} for s in ti["steps"]],
            "skills": {s: SKILL_DEFS[s] for s in skills if s in SKILL_DEFS},
            "l3_relation_types": {k: v for k, v in REL_DEFS.items() if L3_REL_SKILL[k] in skills},
            "n_sub_goals": len(ti["steps"])}


def validate(out, inp):
    warn = []
    if not isinstance(out, dict) or not isinstance(out.get("sub_goals"), list):
        return None, ["no sub_goals list"]
    n = inp["n_sub_goals"]; allowed_sk = set(inp["skills"]); seen = set()
    clean = {"task_id": inp["task_id"], "goal": inp["goal"], "sub_goals": [], "relations": [], "decision_points": []}
    by_idx = {}
    for sg_ in out["sub_goals"]:
        if not isinstance(sg_, dict): continue
        try: idx = int(sg_.get("idx"))
        except Exception: continue
        if not (1 <= idx <= n): warn.append(f"sub_goal idx {idx} out of range"); continue
        evs = []
        for e in sg_.get("events") or []:
            if not isinstance(e, dict) or not e.get("description"): continue
            eid = str(e.get("event_id") or f"s{idx}e{len(evs) + 1}")
            if eid in seen: eid = f"s{idx}e{len(evs) + 1}_{len(seen)}"
            seen.add(eid)
            typ = str(e.get("type") or "action").lower()
            if typ not in EVENT_TYPES: typ = "action"
            sks = [s for s in (e.get("skills") or []) if s in allowed_sk]
            evs.append({"event_id": eid, "sub_goal": idx, "type": typ, "description": str(e["description"])[:200],
                        "objects": [str(x).lower()[:40] for x in (e.get("objects") or [])][:6], "verbs": [str(x).lower()[:30] for x in (e.get("verbs") or [])][:4],
                        "skills": sks, "relevance": str(e.get("relevance") or "")[:200]})
        by_idx[idx] = {"idx": idx, "events": evs, "irrelevant": str(sg_.get("irrelevant") or "")[:200]}
    for s in inp["sub_goals"]:
        clean["sub_goals"].append(by_idx.get(s["idx"], {"idx": s["idx"], "events": [], "irrelevant": ""}))
        if s["idx"] not in by_idx: warn.append(f"sub_goal {s['idx']}: no events")
    ev_sg = {e["event_id"]: e["sub_goal"] for sg_ in clean["sub_goals"] for e in sg_["events"]}
    for r in out.get("relations") or []:
        if not isinstance(r, dict): continue
        typ = str(r.get("type") or "")
        evs = [str(x) for x in (r.get("events") or []) if str(x) in ev_sg]
        if typ not in L3_REL_SKILL: warn.append(f"relation type {typ!r} dropped"); continue
        if len(evs) < 2 or len({ev_sg[x] for x in evs}) < 2: warn.append(f"relation {r.get('rel_id')}: needs >= 2 events from different sub-goals"); continue
        if max(ev_sg[x] for x in evs) - min(ev_sg[x] for x in evs) != 1: warn.append(f"relation {r.get('rel_id')}: events must come from ADJACENT sub-goals (v16)"); continue
        clean["relations"].append({"rel_id": str(r.get("rel_id") or f"r{len(clean['relations']) + 1}"), "type": typ, "skill": L3_REL_SKILL[typ], "events": evs[:3],
                                   "ask": str(r.get("ask") or "")[:300], "answer_hint": str(r.get("answer_hint") or "")[:200]})
    for d in out.get("decision_points") or []:
        if not isinstance(d, dict): continue
        try: idx = int(d.get("idx"))
        except Exception: continue
        if 2 <= idx <= n + 1:
            clean["decision_points"].append({"idx": idx, "real": bool(d.get("real", True)), "why": str(d.get("why") or "")[:200]})
    return clean, warn


def plan_one(contract, store, task_id, run_dir=None, force=False, mock=None):
    import examiner as EX
    inp = build_input(store, contract, task_id)
    if inp is None: return None
    CACHE.mkdir(parents=True, exist_ok=True)
    sys_p = _prompt(contract)
    h = hashlib.sha1((sys_p + json.dumps(inp, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()[:10]
    cp = CACHE / f"{task_id}.{h}.json"
    if cp.exists() and not force:
        return json.loads(cp.read_text())
    rec = {"task_id": task_id, "prompt_hash": h, "model": contract.get("scope_model", contract["examiner_model"]), "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "input": inp, "plan": None, "warnings": [], "usage": {}, "status": "failed"}
    last = None
    for attempt in range(2):
        try:
            text, u = EX.call(sys_p, json.dumps(inp, ensure_ascii=False), rec["model"], max_tokens=contract.get("scope_max_tokens", 16384),
                              thinking=contract.get("scope_thinking", "default"), run_dir=run_dir, role="scope", meta={"task_id": task_id})
            out = EX.jparse(text)
            clean, warn = validate(out, inp)
            if clean is None: raise ValueError("; ".join(warn))
            rec.update(plan=clean, warnings=warn, usage=u, status="ok", raw_len=len(text)); break
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:200]}"; rec["warnings"].append(f"attempt {attempt + 1}: {last}")
    if rec["plan"] is None: rec["error"] = last
    cp.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


# ---------------------------------------------------------------- 2. event -> 标注记录(拿时间)
def _narr_text(r): return (r["value"].get("text") or r["value"].get("narration") or "")


def _score(ev, r):
    """event 与一条记录的匹配分:宾语词干交集 ×2 + 动词交集 + 描述词交集。"""
    v = r["value"] or {}
    if r["kind"] == "action_narration":
        rt = _toks(_narr_text(r)) | {_stem(x) for n in (v.get("nouns") or []) for x in n.lower().split()} | {_stem(x) for n in (v.get("verbs") or []) for x in n.lower().split()}
    elif r["kind"] == "sound_event":
        rt = _toks(v.get("label_phrase") or v.get("label") or "")
    elif r["kind"] in ("object_move", "object_location_transition", "object_mask_anchor", "object_visible_track"):
        rt = _toks(v.get("object_name") or v.get("name") or "") | _toks(v.get("to_fixture_kind") or "")
    elif r["kind"] == "spatial_relation":
        rt = _toks(v.get("anchor_object") or "") | _toks(v.get("reference_object") or "")
    else:
        rt = set()
    objs = {_stem(x) for o in ev["objects"] for x in re.findall(r"[a-z]+", o) if x not in _STOP}
    verbs = {_stem(x) for o in ev["verbs"] for x in re.findall(r"[a-z]+", o) if x not in _STOP}
    desc = _toks(ev["description"]) - objs - verbs
    return 2 * len(objs & rt) + 1.5 * len(verbs & rt) + 0.5 * len(desc & rt), bool(objs & rt), bool(verbs & rt)


def match_events(store, ti, plan):
    """每个 event -> {time:[t0,t1], records:[ids], matched, best}。只在该 sub-goal 的时间段内找。"""
    vid = ti["video_id"]; steps = {s["idx"]: s for s in ti["steps"]}
    for sg_ in plan["sub_goals"]:
        s = steps[sg_["idx"]]
        narr = sorted(_recs(store, vid, s["t0"] - 0.3, s["t1"] + 0.3, kinds={"action_narration"}), key=lambda r: r["time"]["start_sec"])
        snd = _recs(store, vid, s["t0"], s["t1"], kinds={"sound_event"})
        mov = _recs(store, vid, s["t0"], s["t1"], kinds={"object_move", "object_location_transition"})
        for ev in sg_["events"]:
            scored = []
            for r in narr:
                sc, on, vn = _score(ev, r)
                if on or (vn and sc >= 1.5): scored.append((sc, r))
            ev["time"] = None; ev["records"] = []; ev["matched"] = False; ev["match_note"] = ""
            if ev["type"] == "sound":
                cand = [(sc, r) for r in snd for sc, on, vn in [_score(ev, r)] if sc > 0]
                if cand:
                    sc, r = max(cand, key=lambda x: x[0])
                    ev["time"] = [round(r["time"]["start_sec"], 3), round(r["time"]["end_sec"], 3)]; ev["records"] = [r["evidence_id"]]; ev["matched"] = True
                else:                                   # 10-28 晚(用户:这种题要先 filter 掉):没有标签对得上的声音记录,声音 event 不出题,也不拿 narration 的时间充数
                    ev["match_note"] = "no sound record in this sub-goal matches the described sound (labels: " + ", ".join(sorted({(r["value"] or {}).get("label") or "?" for r in snd})[:6]) + ")"
                    continue
            if ev["type"] == "placement" and not ev["matched"]:
                cand = [(sc, r) for r in mov for sc, on, vn in [_score(ev, r)] if on]
                if cand:
                    sc, r = max(cand, key=lambda x: x[0])
                    ev["time"] = [round(r["time"]["start_sec"], 3), round(r["time"]["end_sec"], 3)]; ev["records"] = [r["evidence_id"]]; ev["matched"] = True
            if scored:
                best = max(sc for sc, _ in scored)
                top = [r for sc, r in scored if sc >= max(1.0, best * 0.75)]
                # 连成一组:从最高分那条出发,向两侧沿链并入相邻(间隔 ≤ 2.0 s)且达标的 narration;总跨度 ≤ 12 s
                top.sort(key=lambda r: r["time"]["start_sec"])
                b = next(r for sc, r in scored if sc == best)
                grp = [b]; lo, hi = b["time"]["start_sec"], b["time"]["end_sec"]
                changed = True
                while changed:
                    changed = False
                    for r in top:
                        if r in grp: continue
                        a_, b_ = r["time"]["start_sec"], r["time"]["end_sec"]
                        if (lo - 2.0 <= b_ and a_ <= hi + 2.0) and max(hi, b_) - min(lo, a_) <= 12.0:
                            grp.append(r); lo, hi = min(lo, a_), max(hi, b_); changed = True
                t0, t1 = lo, hi
                if ev["time"] is None:
                    ev["time"] = [round(t0, 3), round(t1, 3)]
                else:                                   # 声音 / 放置已定时:取并集
                    ev["time"] = [round(min(t0, ev["time"][0]), 3), round(max(t1, ev["time"][1]), 3)]
                ev["records"] = sorted(set(ev["records"]) | {r["evidence_id"] for r in grp}); ev["matched"] = True
                ev["match_note"] = f"{len(grp)} narration(s), best score {best:.1f}"
            if ev["matched"]:
                ev["time"] = [round(max(ev["time"][0], s["t0"] - 1.0), 3), round(min(ev["time"][1], s["t1"] + 1.0), 3)]
                a, b2 = ev["time"]
                for r in snd + mov:
                    if a - 1.0 <= r["time"]["start_sec"] <= b2 + 1.0 and r["evidence_id"] not in ev["records"]:
                        if r["kind"] == "sound_event" and _score(ev, r)[0] <= 0: continue     # 10-28 晚:时间重合但标签无关的声音(footstep 等)不算这个 event 的证据
                        ev["records"].append(r["evidence_id"])
                ev["centre"] = round((a + b2) / 2, 3)
            else:
                ev["match_note"] = "no narration / sound / movement in this sub-goal matches the event's objects"
    plan["events"] = {e["event_id"]: e for sg_ in plan["sub_goals"] for e in sg_["events"]}
    for r in plan["relations"]: r.setdefault("source", "planner")
    plan["relations"] += derived_relations(plan)
    return plan


def derived_relations(plan, max_each=8):
    """v16:只在相邻 sub-goal 之间、共享物体词的 planner event 对派生 object_continuity(标 source = derived);planner 已给过的对不重复。"""
    evs = sorted([e for e in plan["events"].values() if e.get("matched")], key=lambda e: e["centre"])
    have = {tuple(sorted(r["events"][:2])) for r in plan["relations"]}
    objs = lambda e: {_stem(x) for o in e["objects"] for x in re.findall(r"[a-z]+", o) if x not in _STOP}
    out = []
    pairs = [(a, b) for i, a in enumerate(evs) for b in evs[i + 1:] if b["sub_goal"] - a["sub_goal"] == 1]
    for a, b in sorted(pairs, key=lambda p: (-len(objs(p[0]) & objs(p[1])), p[0]["sub_goal"], p[0]["centre"])):
        shared = objs(a) & objs(b)
        key = tuple(sorted([a["event_id"], b["event_id"]]))
        if not shared or key in have or len(out) >= max_each: continue
        have.add(key)
        out.append({"rel_id": f"d{len(out) + 1}", "type": "object_continuity", "skill": L3_REL_SKILL["object_continuity"], "events": [a["event_id"], b["event_id"]], "source": "derived",
                    "ask": f"what happened to the shared object ({', '.join(sorted(shared))}) between the earlier event and the later one; what the later event shows that the earlier did not",
                    "answer_hint": f"{a['description']} -> {b['description']}"})
    return out


def ensure(contract, store, run_dir=None, task_ids=None, force=False):
    out = {}
    for tid in task_ids or []:
        rec = plan_one(contract, store, tid, run_dir=run_dir, force=force)
        if rec is None or not rec.get("plan"):
            out[tid] = None; continue
        ti = task_info(store, tid)
        plan = match_events(store, ti, json.loads(json.dumps(rec["plan"])))
        out[tid] = plan
        if run_dir is not None:
            d = Path(run_dir) / "sgplan"; d.mkdir(parents=True, exist_ok=True)
            (d / f"{tid}.json").write_text(json.dumps({**rec, "plan": plan}, indent=1, ensure_ascii=False))
    return out


# ---------------------------------------------------------------- 3. cluster 构造
def _seg(centre, D, pad=EVENT_PAD):
    t0 = max(0.0, centre - pad); t1 = min(D, t0 + 2 * pad); t0 = max(0.0, t1 - 2 * pad)
    return [round(t0, 3), round(t1, 3)]


def _sg_window(s, D):
    t0, t1 = s["t0"], s["t1"]
    if t1 - t0 < MIN_WIN:
        c = (t0 + t1) / 2; t0 = max(0.0, c - MIN_WIN / 2); t1 = min(D, t0 + MIN_WIN); t0 = max(0.0, t1 - MIN_WIN)
    return [round(t0, 3), round(t1, 3)]


def _anchor_ok(spec, r):
    skip = set(spec.get("skip_flags") or [])
    if skip & set(r["quality_flags"]): return False
    if spec.get("anchor_value"):
        if not all(r["value"].get(k) in vals for k, vals in spec["anchor_value"].items()): return False
    if spec.get("anchor_pred") and not R.ANCHOR_PRED[spec["anchor_pred"]](r): return False
    return r["solver_access"] != "answer_only"


def _near_event(r, events, pad=EVENT_PAD * 1.5):
    """记录是否落在某个已匹配 event 的时间段附近;返回 event_id 或 None。"""
    t = (r["value"] or {}).get("anchor_time_sec") if r["kind"] == "spatial_relation" else None
    t = float(t) if t is not None else r["time"]["start_sec"]
    best = None
    for ev in events:
        if not ev.get("matched"): continue
        a, b = ev["time"]
        if a - pad <= t <= b + pad:
            d = 0.0 if a <= t <= b else min(abs(t - a), abs(t - b))
            if best is None or d < best[0]: best = (d, ev["event_id"])
    return best[1] if best else None


# ---- L1 感知量
def _area(mask_rec):
    bb = (mask_rec["value"] or {}).get("bbox_1408")
    if not bb or len(bb) != 4: return None
    return max(0.0, (bb[2] - bb[0]) * (bb[3] - bb[1])) / (1408.0 * 1408.0)


def l1_knob(store, skill, r, vid):
    """返回 (kind, value):value 越大越难。"""
    v = r["value"] or {}
    if skill in ("spatial_near", "spatial_side", "sound_anchored_spatial_near", "sound_anchored_spatial_side"):
        m = v.get("margin_m")
        return ("margin_m_neg", round(-float(m), 3)) if m is not None else ("margin_m_neg", 0.0)
    if skill == "object_grounding":
        a = _area(r); return ("area_neg", round(-(a or 0.0), 5))
    if skill == "object_location_at_time":
        tid = v.get("track_id"); te = r["time"]["end_sec"]
        masks = [m_ for m_ in store.in_window(vid, te - 3, te + 3, kinds={"object_mask_anchor"}, status="verified") if (m_["value"] or {}).get("track_id") == tid]
        if masks:
            a = max((_area(m_) or 0.0) for m_ in masks); return ("area_neg", round(-a, 5))
    # 默认:干扰 = ±5 s 内其它 narration 数
    t = r["time"]["start_sec"]
    n = sum(1 for x in store.in_window(vid, t - EVENT_PAD, t + EVENT_PAD, kinds={"action_narration"}, status="verified") if x["evidence_id"] != r["evidence_id"] and _ds(x) in DS)
    return ("n_other_narrations", n)


def _bands(vals):
    """{record_id: knob} -> {record_id: tier 1..4}(按秩四分位;越大越难)。"""
    if not vals: return {}
    order = sorted(vals, key=lambda k: vals[k])
    n = len(order); out = {}
    for i, k in enumerate(order):
        out[k] = min(4, int(4 * i / n) + 1) if n >= 4 else min(4, i + 1 + (4 - n) // 2)
    return out


def _mk_cluster(skill, ti, store, *, windows, cutoff, anchor, core, sg_meta, two=False):
    vid = ti["video_id"]; w0, w1 = min(w[0] for w in windows), max(w[1] for w in windows)      # 乱序段:window = 总覆盖范围
    core_ids = sorted({r["evidence_id"] for r in core})
    seen = set(core_ids); ctx = []
    for w in windows:
        for r in store.in_window(vid, w[0], w[1], status="verified"):
            if r["evidence_id"] in seen or r["kind"] not in R.ALL_CTX or r["solver_access"] == "answer_only" or _ds(r) not in DS or r["kind"] == "task_step": continue
            seen.add(r["evidence_id"]); ctx.append(r)
    ctx = R._trim_context(ctx, skill)
    key = core_ids + [f"sg:{sg_meta.get('tier', '')}:{sg_meta.get('kind')}:{sg_meta.get('rel_id', '')}:{sg_meta.get('idx', '')}"]
    return {"evidence_cluster_id": ids.cluster_id(skill, vid, w0, w1, key), "capability_skill": skill, "video_id": vid, "media_id": anchor.get("media_id") or ti["media_id"],
            "window": [w0, w1], **({"windows": [list(w) for w in windows]} if two else {}), "observation_cutoff": cutoff, "anchor_id": anchor["evidence_id"],
            "sample_id": ti["task_id"], "anchor_kind": anchor["kind"], "anchor_is_next": False, "anchor_step_idx": sg_meta.get("idx"),
            "core": core, "context": ctx, "two_windows_allowed": two, "sg": sg_meta,
            "interference": R.interference(store, vid, w0, w1, core_ids, dataset="hdepic_e")}


def grounding_clusters(store, ti, plan):
    """object_grounding:复用 l3ext.grounding_clusters(1 s clip、bbox 题型、官方框参考),只留本 task 内、落在期望 event 附近的 mask;档 = 面积四分位。"""
    import l3ext as LX
    vid = ti["video_id"]; m = store.media_of_video(vid)
    cl = [c for c in LX.grounding_clusters(store, vid, "object_grounding", m, seed=0, max_clusters=400) if c.get("sample_id") == ti["task_id"]]
    evs_by = {sg_["idx"]: [e for e in sg_["events"] if e.get("matched")] for sg_ in plan["sub_goals"]}
    keep = []
    for c in cl:
        s = next((x for x in ti["steps"] if x["t0"] - 0.5 <= c["l3ext"]["frame_sec"] <= x["t1"] + 0.5), None)
        if s is None: continue
        evs = evs_by.get(s["idx"], [])
        eid = _near_event(next(r for r in c["core"] if r["kind"] == "object_mask_anchor"), evs)
        if eid is None: continue
        c["sg"] = {"kind": "L1", "idx": s["idx"], "sub_goal_text": s["text"], "sub_goal_window": [s["t0"], s["t1"]], "grounding": True,
                   "events": [{k: e[k] for k in ("event_id", "type", "description", "objects", "time", "records")} for e in evs],
                   "anchor_event": {c["anchor_id"]: eid}, "knob": {c["anchor_id"]: {"kind": "area_neg", "value": round(-c["l3ext"]["area_frac"], 5)}},
                   "tiers": {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0}}
        keep.append(c)
    bands = _bands({c["anchor_id"]: c["sg"]["knob"][c["anchor_id"]]["value"] for c in keep})
    for c in keep:
        c["sg"]["bands"] = {t: [c["anchor_id"]] if bands.get(c["anchor_id"]) == t else [] for t in (1, 2, 3, 4)}
        c["sg"]["band_rule"] = "tier = quartile of the box area (4 = smallest box); format bbox, 1 s clip, first frame"
    keep.sort(key=lambda c: (c["sg"]["idx"], c["l3ext"]["frame_sec"]))
    return keep


def l12_clusters(store, ti, plan, skill, layer):
    """每个 sub-goal 一个 cluster:窗口 = sub-goal 整段;锚点 = skill 的锚记录里落在已匹配 event 附近的那些。"""
    vid = ti["video_id"]; m = store.media_of_video(vid); D = (m or {}).get("duration_sec") or 1e9
    if skill == "object_grounding": return grounding_clusters(store, ti, plan)
    spec = R.skill_spec(skill, "hdepic_e")
    if spec is None: return []
    out = []
    knobs_all = {}
    pre = []
    for s in ti["steps"]:
        sg_ = next((x for x in plan["sub_goals"] if x["idx"] == s["idx"]), None)
        if not sg_: continue
        evs = [e for e in sg_["events"] if e.get("matched") and (layer == "L2" or not e["skills"] or skill in e["skills"] or True)]
        if not evs: continue
        win = _sg_window(s, D)
        win = [round(min(win[0], min(e["time"][0] for e in evs)), 3), round(max(win[1], max(e["time"][1] for e in evs)), 3)]   # event 可超出 sub-goal 边界 ≤1 s:窗口跟着放宽,记录不漏
        anchors = []
        for k in spec["anchor"]:
            for r in _recs(store, vid, win[0], win[1], kinds={k}):
                if not _anchor_ok(spec, r): continue
                eid = _near_event(r, evs)
                if eid is None: continue
                anchors.append((r, eid))
        if not anchors: continue
        core_kinds = set(spec["core"])
        core = [r for r, _ in anchors]
        for r in _recs(store, vid, win[0], win[1]):
            if r["kind"] in core_kinds and r["evidence_id"] not in {x["evidence_id"] for x in core} and _near_event(r, evs) is not None and not (set(spec.get("skip_flags") or []) & set(r["quality_flags"])):
                core.append(r)
        have = {x["evidence_id"] for x in core}
        for e in evs:                                   # 10-28 晚:event 引用的记录必须进 core,Examiner 才能核对;store 里没有的从 event.records 里去掉
            keep_ids = []
            for rid in e["records"]:
                r = store.get(rid)
                if r is None or r["solver_access"] == "answer_only": continue
                keep_ids.append(rid)
                if rid not in have and win[0] - 1.0 <= r["time"]["start_sec"] <= win[1] + 1.0:
                    core.append(r); have.add(rid)
            e["records"] = keep_ids
        need = set(spec.get("need_kinds") or [])
        if need and not need <= {r["kind"] for r in core}: continue
        core.append(ti["step_rec"][s["idx"]]) if s["idx"] in ti["step_rec"] else None
        def _win_for(e, L):
            if L is None: return [win[0], win[1]]
            c0 = (e["time"][0] + e["time"][1]) / 2; a = max(win[0], c0 - L / 2); b = min(win[1], a + L); a = max(win[0], b - L)
            return [round(a, 3), round(b, 3)]
        meta = {"kind": layer, "idx": s["idx"], "sub_goal_text": s["text"], "sub_goal_window": [s["t0"], s["t1"]],
                "events": [{**{k: e[k] for k in ("event_id", "type", "description", "objects", "time", "records")},
                            "window_L1": _win_for(e, 2 * EVENT_PAD), "window_L2": {t: _win_for(e, w) for t, w in L2_WINDOWS.items()}} for e in evs],
                "anchor_event": {r["evidence_id"]: eid for r, eid in anchors},
                "tiers": ({1: 10.0, 2: 10.0, 3: 10.0, 4: 10.0} if layer == "L1" else {t: (w if w is not None else round(win[1] - win[0], 3)) for t, w in L2_WINDOWS.items()}),
                "irrelevant": sg_.get("irrelevant")}
        if layer == "L1":
            kn = {r["evidence_id"]: l1_knob(store, skill, r, vid) for r, _ in anchors}
            meta["knob"] = {k: {"kind": v[0], "value": v[1]} for k, v in kn.items()}
            knobs_all.update({k: v[1] for k, v in kn.items()})
        pre.append((s, win, anchors, core, meta))
    bands = _bands(knobs_all) if layer == "L1" else {}
    for s, win, anchors, core, meta in pre:
        if layer == "L1":
            meta["bands"] = {t: [k for k, b in bands.items() if b == t and k in meta["anchor_event"]] for t in (1, 2, 3, 4)}
            meta["band_rule"] = "difficulty tier t requires private.evidence_refs to include at least one anchor record listed in sg.bands[t] (perceptual quantity quartile; higher tier = harder)"
        out.append(_mk_cluster(skill, ti, store, windows=[win], cutoff=None, anchor=anchors[0][0], core=core, sg_meta=meta))   # cutoff 由程序事后填成 clip 末尾
    return out


def _distractor_window(ti, plan, lo, hi, D, rng, taken=()):
    """[lo, hi] 里不含任何已匹配 event、也不与 taken 窗口重叠的 10 s 窗口(无关内容);找不到就 None。"""
    spans = sorted([tuple(e["time"]) for e in plan["events"].values() if e.get("matched")] + [tuple(w) for w in taken])
    cands = []
    t = lo
    while t + 2 * EVENT_PAD <= hi:
        w = (t, t + 2 * EVENT_PAD)
        if not any(a - 1 < w[1] and b + 1 > w[0] for a, b in spans): cands.append(w)
        t += 5.0
    if not cands: return None
    w = rng.choice(cands); return [round(w[0], 3), round(w[1], 3)]


def l3_clusters(store, ti, plan, skill, seed=0):
    """v16(用户定):关系 = 相邻 sub-goal 的两个 event(A 在 k,B 在 k+1)。clip 永远是一段连续视频:
    1 档 = sub-goal k + k+1 整段;2 档 = k-1 + k + k+1 + k+2 里能取到的前后各一个(前 + 本 + 后);3 / 4 档 = 以 pair 中心扩到 180 s(3 单选,4 短答)。"""
    vid = ti["video_id"]; m = store.media_of_video(vid); D = (m or {}).get("duration_sec") or 1e9
    steps = {s_["idx"]: s_ for s_ in ti["steps"]}
    out = []
    for rel in plan["relations"]:
        if rel["skill"] != skill: continue
        evs = [plan["events"][e] for e in rel["events"] if plan["events"].get(e, {}).get("matched")]
        if len(evs) < 2: continue
        evs.sort(key=lambda e: e["centre"]); A, B = evs[0], evs[-1]
        ka, kb = A["sub_goal"], B["sub_goal"]
        if kb - ka != 1 or ka not in steps or kb not in steps: continue
        w1 = [round(min(steps[ka]["t0"], steps[kb]["t0"]), 3), round(max(steps[ka]["t1"], steps[kb]["t1"]), 3)]
        prev_, next_ = steps.get(ka - 1), steps.get(kb + 1)
        w2 = [round(prev_["t0"] if prev_ else w1[0], 3), round(next_["t1"] if next_ else w1[1], 3)]
        c_ = (w1[0] + w1[1]) / 2; half = L3_MAX_SEC / 2
        w3 = [round(max(0.0, c_ - half), 3), round(min(D, c_ + half), 3)]
        if w3[1] - w3[0] < w1[1] - w1[0]: w3 = list(w1)
        wins_by = {1: w1, 2: w2, 3: w3, 4: w3}
        for tier in (1, 2, 3, 4):
            w = wins_by[tier]
            if tier == 2 and w2 == w1: continue                                  # 没有前后 sub-goal 可加:2 档不存在
            if tier == 3 and w3[1] - w3[0] <= w2[1] - w2[0] + 1.0: w = w2        # 180 s 不比 2 档大:3 档沿用 2 档窗口(题型相同,等于再问一次)
            core = [r for r in _recs(store, vid, w[0], w[1], kinds={"action_narration", "sound_event", "object_move", "object_location_transition", "spatial_relation"})
                    if _near_event(r, evs, pad=EVENT_PAD) is not None or any(r["evidence_id"] in e["records"] for e in evs)]
            core = list({r["evidence_id"]: r for r in core}.values())
            for k_ in sorted(steps):
                if steps[k_]["t1"] >= w[0] and steps[k_]["t0"] <= w[1] and k_ in ti["step_rec"] and ti["step_rec"][k_]["evidence_id"] not in {r["evidence_id"] for r in core}:
                    core.append(ti["step_rec"][k_])
            if len(core) < 2: continue
            meta = {"kind": "L3", "tier": tier, "rel_id": rel["rel_id"], "rel_type": rel["type"], "rel_source": rel.get("source", "planner"), "ask": rel["ask"], "answer_hint": rel["answer_hint"],
                    "idx": [ka, kb], "this_sub_goal": kb, "events": [{k: e[k] for k in ("event_id", "sub_goal", "type", "description", "objects", "time", "records")} for e in evs],
                    "sub_goals_in_clip": [k_ for k_ in sorted(steps) if steps[k_]["t1"] >= w[0] and steps[k_]["t0"] <= w[1]],
                    "window_rule": {1: "sub-goal k and k+1 only", 2: "previous + the pair + next sub-goal", 3: "180 s centred on the pair, single choice", 4: "180 s centred on the pair, short answer"}[tier],
                    "n_segments": 1, "total_sec": round(w[1] - w[0], 1)}
            anchor = next((r for r in core if r["evidence_id"] in A["records"]), core[0])
            out.append(_mk_cluster(skill, ti, store, windows=[w], cutoff=w[1], anchor=anchor, core=core, sg_meta=meta, two=False))
    return out


def l4_clusters(store, ti, plan, skill):
    """决策点 = sub-goal k 起点(k ≥ 2,planner 标 real)+ task 结束点;clip = 前一个 sub-goal 整段(≥ 10 s),cutoff = 决策点。"""
    vid = ti["video_id"]; m = store.media_of_video(vid); D = (m or {}).get("duration_sec") or 1e9
    steps = ti["steps"]; n = len(steps); out = []
    real = {d["idx"]: d for d in plan.get("decision_points") or []}
    for k in range(2, n + 2):
        if real and k in real and not real[k]["real"]: continue
        prev = steps[k - 2]
        cutoff = steps[k - 1]["t0"] if k <= n else ti["t1"]
        t0 = prev["t0"]
        if cutoff - t0 < MIN_WIN: t0 = max(0.0, cutoff - MIN_WIN)
        win = [round(t0, 3), round(cutoff, 3)]
        core = [ti["seg"]] + [ti["step_rec"][s["idx"]] for s in steps if s["idx"] in ti["step_rec"] and s["t1"] <= cutoff + 0.1]
        core += [r for r in _recs(store, vid, win[0], win[1], kinds={"action_narration"})]
        fut = [dict(ti["step_rec"][s["idx"]], solver_access="answer_only") for s in steps if s["idx"] in ti["step_rec"] and s["t0"] >= cutoff - 1e-6][:3]
        if k > n and ti.get("next") is not None: fut = [dict(ti["next"], solver_access="answer_only")]
        core += fut
        remaining = [s for s in steps if s["t0"] >= cutoff - 1e-6]
        meta = {"kind": "L4", "idx": k, "prev_idx": prev["idx"], "decision": (real.get(k) or {}).get("why", ""), "n_remaining": len(remaining),
                "remaining_sub_goals": [{"idx": s["idx"], "text": s["text"]} for s in remaining], "final": k > n}
        out.append(_mk_cluster(skill, ti, store, windows=[win], cutoff=win[1], anchor=ti["step_rec"].get(prev["idx"], ti["seg"]), core=core, sg_meta=meta))
    return out


def build_pools(store, contract, plan_by_task, skills, layer, seed=0):
    pools = {}
    for cap in skills:
        cl = []
        for tid, plan in plan_by_task.items():
            if not plan: continue
            ti = task_info(store, tid)
            if layer in ("L1", "L2"): cl += l12_clusters(store, ti, plan, cap, layer)
            elif layer == "L3": cl += l3_clusters(store, ti, plan, cap, seed=seed)
            elif layer == "L4" and cap == "goal_conditioned_planning": cl += l4_clusters(store, ti, plan, cap)
        pools[cap] = cl
    return pools


# ---------------------------------------------------------------- 4. 阶梯接口
def spec_for(cap, level, c=None, contract=None):
    layer = LAYER_OF.get(cap)
    fmt = FORMAT_OF[level]
    if cap == "object_grounding":
        return {"level": level, "format": "bbox", "window_max_sec": 1.5, "window_min_sec": 0.9,
                "note": f"object_grounding tier {level}: 1 s clip starting at the offered mask frame (the offered window), format bbox; the target box is quartile {level} by area (4 = smallest)",
                "rule": "controller-fixed difficulty: format bbox; media_refs window = exactly the offered 1 s window; reference = the recorded box (l3ext.reference_answer)"}
    if layer == "L1":
        fb = (c or {}).get("sg", {}).get("band_fallback")
        return {"level": level, "format": fmt, "window_max_sec": 2 * EVENT_PAD, "window_min_sec": 2 * EVENT_PAD - 0.5,
                **({"band_fallback": True} if fb else {}), **({"band_enforce": False} if (contract or {}).get("l1_band_enforce") is False else {}),
                "note": f"L1 tier {level}: 10 s clip centred on the event; the question names the event AND its position in the clip ('about N seconds into the clip'); "
                        f"the perceptual target must be one of the anchor records in sg.bands[{level}] (quartile {level} of the skill's perceptual quantity, 4 = hardest)",
                "rule": "controller-fixed difficulty: exactly this format; clip 10 s inside the offered sub-goal window containing the cited event record; cite a band record"}
    if layer == "L2":
        w = L2_WINDOWS[level]; wl = w if w is not None else (round(c["window"][1] - c["window"][0], 3) if c else None)
        return {"level": level, "format": fmt, "window_max_sec": wl, "window_min_sec": min(MIN_WIN, wl or MIN_WIN),
                "note": f"L2 tier {level}: clip at most {wl:.0f} s, inside the sub-goal, containing the event; the question describes the event in words but gives NO time position; the Solver must find it" + (" ; short_answer: the Solver must state the action and object itself (reference = verb + object, with accepted_alternatives)" if fmt == "short_answer" else ""),
                "rule": "controller-fixed difficulty: exactly this format and at most this clip length; same skill; never say when in the clip the event happens"}
    if layer == "L3":
        return {"level": level, "format": fmt, "window_max_sec": None, "window_min_sec": None,
                "note": {1: "L3 tier 1: the clip is exactly sub-goal k and k+1; relate the event of k+1 to the event of k", 2: "L3 tier 2: the clip also includes the previous and the next sub-goal",
                         3: "L3 tier 3: 180 s of continuous video centred on the two sub-goals; single choice", 4: "L3 tier 4: the same 180 s clip; short_answer: the Solver states the relation itself (what was done to the ingredient before / what the earlier step provided), with accepted_alternatives"}[level],
                "rule": "controller-fixed difficulty: exactly this format; media_refs = EXACTLY the offered window; the question names only the object / action of the later sub-goal and gives NO time position"}
    return None


def _used_rel(state, cap):
    return {(h.get("sg") or {}).get("rel_id") for h in state.history if h["capability_skill"] == cap and (h.get("sg") or {}).get("rel_id") and h.get("verdict") in ("correct", "wrong")}


def _scored_clusters(state):
    """计过分的 cluster(item_invalid 的尝试不算用过,但同一 cluster 最多尝试 2 次)。"""
    n = collections.Counter(h["evidence_cluster_id"] for h in state.history if h.get("evidence_cluster_id"))
    scored = {h["evidence_cluster_id"] for h in state.history if h.get("verdict") in ("correct", "wrong") and h.get("evidence_cluster_id")}
    return scored | {k for k, v in n.items() if v >= 2} | set(state.frozen_clusters)


def pool_for_level(state, store, cap, level):
    pool = state.pools.get(cap, []); layer = LAYER_OF.get(cap)
    used = _scored_clusters(state)
    if layer in ("L1", "L2"):
        fresh = [c for c in pool if c["evidence_cluster_id"] not in used]
        cands = [c for c in fresh if c["sg"]["bands"].get(level)] if layer == "L1" else list(fresh)
        if not cands:                                             # sub-goal 用完:允许重用没在本档题型问过的 sub-goal
            asked = {(h["evidence_cluster_id"], h.get("difficulty_level")) for h in state.history}
            reuse = [c for c in pool if (c["evidence_cluster_id"], level) not in asked and c["evidence_cluster_id"] not in state.frozen_clusters]
            cands = [c for c in reuse if c["sg"]["bands"].get(level)] if layer == "L1" else reuse
            if not cands and layer == "L1" and fresh:             # 这一档没有感知量落在该四分位的 sub-goal:退回任意未用 sub-goal,记 band_fallback
                cands = [dict(c, sg=dict(c["sg"], band_fallback=True)) for c in fresh]
        cands.sort(key=lambda c: c["sg"]["idx"])
        return cands[:1]
    if layer == "L3":
        ur = _used_rel(state, cap)
        cands = [c for c in pool if c["sg"]["tier"] == level and c["sg"]["rel_id"] not in ur and c["evidence_cluster_id"] not in used]
        if not cands:
            cands = [c for c in pool if c["sg"]["tier"] == level and c["evidence_cluster_id"] not in used and c["evidence_cluster_id"] not in state.frozen_clusters]
        cands.sort(key=lambda c: (c["sg"].get("rel_source") == "derived", min(c["sg"]["idx"]), c["sg"]["rel_id"]))   # planner 的关系先问,派生的后问
        return cands[:1]
    if layer == "L4":
        import staircase as ST
        knobs = {c["evidence_cluster_id"]: c["sg"]["n_remaining"] for c in pool}
        filt = ST._filter(cap, level, list(knobs.values()))
        cands = [c for c in pool if c["evidence_cluster_id"] not in used and filt(knobs[c["evidence_cluster_id"]])]
        if state.c.get("l4_answerability"):
            import l4check as K
            memo = getattr(state, "_l4ans", None)
            if memo is None: memo = state._l4ans = {}
            keep = []
            for c in cands:
                k = (c["evidence_cluster_id"], level)
                if k not in memo:
                    ok, det = K.check(store, state.dir.parent, state.c, cap, c, level); memo[k] = ok
                    K.log(state.dir.parent, {"cluster": c["evidence_cluster_id"], "skill": cap, "level": level, "window": c.get("window"), "cutoff": c.get("observation_cutoff"), "ok": ok, **det})
                if memo[k]: keep.append(c)
            cands = keep
        cands.sort(key=lambda c: c["sg"]["idx"])
        return cands[:1]
    return []


def levels_available(state, store, cap):
    return [L for L in (1, 2, 3, 4) if pool_for_level(state, store, cap, L)]


# ---------------------------------------------------------------- 5. 校验(examiner.check_output 在 cluster 带 sg 时调用)
_TIME_CUE = re.compile(r"(\d+(?:\.\d+)?\s*(?:s\b|sec\b|seconds?)\s+(?:into|in|after|from)|(?:at|around|about|roughly|near)\s+(?:about\s+|around\s+)?\d+(?:\.\d+)?\s*(?:s\b|sec\b|seconds?)|\b\d{1,2}:\d\d\b|(?:start|beginning|end|middle|halfway)\s+of\s+the\s+clip|first\s+(?:few\s+)?seconds|last\s+(?:few\s+)?seconds)")


def autofill(out, ctx, c):
    """10-28(Qwen Examiner 不填形式字段、不理打回):由 cluster 唯一确定的字段程序补齐,记在 private.autofilled;内容(题面 / 选项 / 参考)不动。
    - sg_event_id:缺失时按引用的记录反推(anchor_event 映射 / 记录落在哪个 event 附近),否则 cluster 只有一个 event 时取它;
    - sg_rel_id:缺失时 = cluster 的关系;
    - 窗口:比档位最小长度短时,以原窗口中心居中扩到最小长度(不超出 offered 窗口);L3 窗口 = offered 窗口。"""
    sg_ = c.get("sg") or {}; pub = out.get("public") or {}; pri = out.get("private") or {}
    if not sg_ or not isinstance(pub, dict) or not isinstance(pri, dict): return
    filled = []
    d = ctx.get("difficulty") or {}
    if sg_.get("kind") in ("L1", "L2"):
        if not pri.get("sg_event_id"):
            refs = [x if isinstance(x, str) else x.get("evidence_id") for x in (pri.get("evidence_refs") or [])]
            ae = sg_.get("anchor_event") or {}
            eid = next((ae[r] for r in refs if r in ae), None)
            if eid is None:
                offered = {r["evidence_id"]: r for r in ctx.get("verified_evidence") or []}
                for r in refs:
                    if r in offered and offered[r]["kind"] != "task_step":
                        eid = _near_event(offered[r], sg_["events"])
                        if eid: break
            if eid is None and len(sg_.get("events") or []) == 1: eid = sg_["events"][0]["event_id"]
            if eid: pri["sg_event_id"] = eid; filled.append("sg_event_id")
        wmin = d.get("window_min_sec"); wmax = d.get("window_max_sec")
        ev = next((x for x in sg_.get("events") or [] if x["event_id"] == pri.get("sg_event_id")), None)
        for ref in pub.get("media_refs") or []:
            ws = ref.get("windows") or []
            if ev and len(ws) == 1 and len(ws[0]) == 2 and ev.get("window_L1"):
                a, b = float(ws[0][0]), float(ws[0][1]); ea, eb = ev["time"]
                ov = max(0.0, min(b, eb) - max(a, ea))
                if ov < min(3.0, 0.5 * (eb - ea)) and not (a <= (ea + eb) / 2 <= b):     # 窗口没盖住 event(Qwen 常从 event 结束时刻起切):换成该 event 的建议窗口
                    sug = ev["window_L1"] if sg_.get("kind") == "L1" else (ev.get("window_L2") or {}).get(d.get("level")) or ev.get("window_L2", {}).get(str(d.get("level"))) or ev["window_L1"]
                    ref["windows"] = [list(sug)]; filled.append("window_recentred"); continue
            ws = ref.get("windows") or []
            if len(ws) == 1 and len(ws[0]) == 2 and wmin and float(ws[0][1]) - float(ws[0][0]) < float(wmin) - 0.01:
                a, b = float(ws[0][0]), float(ws[0][1]); mid = (a + b) / 2; L = float(wmax or wmin)
                o0, o1 = float(c["window"][0]), float(c["window"][1])
                n0 = max(o0, mid - L / 2); n1 = min(o1, n0 + L); n0 = max(o0, n1 - L)
                ref["windows"] = [[round(n0, 3), round(n1, 3)]]; filled.append("window")
            elif len(ws) == 1 and len(ws[0]) == 2 and wmax and 0 < float(ws[0][1]) - float(ws[0][0]) - float(wmax) <= 2.0:   # 略超上限(≤2 s):居中裁到上限
                a, b = float(ws[0][0]), float(ws[0][1]); mid = (a + b) / 2; L = float(wmax)
                ref["windows"] = [[round(mid - L / 2, 3), round(mid + L / 2, 3)]]; filled.append("window")
            ws = ref.get("windows") or []
            if len(ws) == 1 and len(ws[0]) == 2:                                   # 越出 offered 窗口:整体平移进去(长度不变)
                a, b = float(ws[0][0]), float(ws[0][1]); o0, o1 = float(c["window"][0]), float(c["window"][1]); L = b - a
                if a < o0 - 0.01 or b > o1 + 0.01:
                    a = max(o0, min(a, o1 - L)); b = min(o1, a + L); a = max(o0, b - L)
                    ref["windows"] = [[round(a, 3), round(b, 3)]]; filled.append("window_shifted")
    if sg_.get("grounding") and isinstance(c.get("l3ext"), dict) and c["l3ext"].get("object"):     # grounding:private.grounding.object 由 cluster 定
        g = pri.get("grounding") if isinstance(pri.get("grounding"), dict) else {}
        if not g.get("object"): pri["grounding"] = {**g, "object": c["l3ext"]["object"]}; filled.append("grounding.object")
    elif sg_.get("kind") == "L3":
        if pri.get("sg_rel_id") != sg_.get("rel_id"): pri["sg_rel_id"] = sg_.get("rel_id"); filled.append("sg_rel_id")
        for ref in pub.get("media_refs") or []:
            want = [list(map(float, c["window"]))]
            ws = [list(map(float, w)) for w in (ref.get("windows") or []) if len(w) == 2]
            if ws != want: ref["windows"] = [list(c["window"])]; filled.append("window")
    if filled: pri["autofilled"] = sorted(set(filled))


def checks(out, ctx, c, store):
    e = []; sg_ = c["sg"]; layer = sg_["kind"]; pub, pri = out["public"], out["private"]
    q = (pub.get("question") or "").lower(); d = ctx.get("difficulty") or {}
    wins = [list(map(float, w)) for ref in (pub.get("media_refs") or []) for w in (ref.get("windows") or []) if len(w) == 2]
    total = sum(w[1] - w[0] for w in wins)
    refs = [x if isinstance(x, str) else x.get("evidence_id") for x in (pri.get("evidence_refs") or [])]
    offered = {r["evidence_id"]: r for r in ctx["verified_evidence"]}
    if layer in ("L1", "L2"):
        eid = pri.get("sg_event_id")
        ev_ids = {x["event_id"] for x in sg_["events"]}
        if eid not in ev_ids:
            e.append(f"private.sg_event_id must be one of the offered expected events {sorted(ev_ids)} (the question must be about that event)")
        elif sg_.get("grounding"):
            pass                                                   # 窗口 / 框 / 题型由 l3ext.checks(grounding)管
        else:
            ev = next(x for x in sg_["events"] if x["event_id"] == eid)
            if len(wins) != 1:
                e.append("L1 / L2 items use exactly one window")
            else:
                w = wins[0]; a, b = ev["time"]
                ov = max(0.0, min(w[1], b) - max(w[0], a))
                if not (w[0] - 0.01 <= (a + b) / 2 <= w[1] + 0.01) and ov < min(3.0, 0.5 * (b - a)):     # 长 event(持续的声音 / 冲洗):窗口与 event 重叠 ≥ 3 s 也算
                    e.append(f"the window {w} must contain the event {eid} (recorded at {a}-{b} s)")
                if w[0] < c["window"][0] - 0.01 or w[1] > c["window"][1] + 0.01:
                    e.append(f"window {w} outside the offered sub-goal window {c['window']}")
                if d.get("window_max_sec") and total > float(d["window_max_sec"]) + 0.01:
                    e.append(f"tier {d.get('level')}: clip must be at most {d['window_max_sec']:.0f} s (got {total:.1f} s)")
                if d.get("window_min_sec") and total < float(d["window_min_sec"]) - 0.01:
                    e.append(f"clip must be at least {d['window_min_sec']:.0f} s (got {total:.1f} s)")
            ev_toks = {_stem(x) for o in ev["objects"] for x in re.findall(r"[a-z]+", o) if x not in _STOP} | (_toks(ev["description"]))
            opts = " ".join(pub.get("options") or []).lower()
            if ev_toks and not (ev_toks & _toks(q + " " + opts)):
                e.append(f"question / options must refer to the event {eid} ({ev['description']!r}): none of its words appear")
        if layer == "L1":
            if not sg_.get("grounding") and not _TIME_CUE.search(q):
                e.append("L1: the question must give the event's position in the clip in words ('about 4 seconds into the clip', 'at the start of the clip') so the Solver does not have to search")
            band = set(sg_.get("bands", {}).get(d.get("level"), []) or sg_.get("bands", {}).get(str(d.get("level")), []))
            if sg_.get("band_fallback") or d.get("band_fallback") or d.get("band_enforce") is False: band = set()
            if band and not (band & set(refs)):
                e.append(f"L1 tier {d.get('level')}: private.evidence_refs must include one of the band anchor records {sorted(band)[:4]} (the perceptual target of this tier)")
        else:
            if _TIME_CUE.search(q):
                e.append("L2: the question must NOT say when in the clip the event happens (no 'N seconds into the clip', no 'at the start'); describe the event in words only")
    elif layer == "L3":
        if pri.get("sg_rel_id") != sg_["rel_id"]:
            e.append(f"private.sg_rel_id must be {sg_['rel_id']!r} (the offered relation)")
        want = [list(map(float, c["window"]))]
        if len(wins) != 1 or any(abs(wins[0][i] - want[0][i]) > 0.05 for i in (0, 1)):
            e.append(f"L3: media_refs must be exactly the offered window {want} (got {wins})")
        if _TIME_CUE.search(q):
            e.append("L3: no time position in the question")
        ev_a = sg_["events"][0]
        a_toks = {_stem(x) for v in ev_a.get("verbs", []) for x in re.findall(r"[a-z]+", v)} if ev_a.get("verbs") else set()
        if a_toks and (a_toks & _toks(q)) and pub.get("format") != "short_answer":
            e.append(f"L3: the question must not describe what happened in the earlier sub-goal ({ev_a['description']!r}); name only the object / action of the later sub-goal and ask for the relation")
        # 两个关系 event 的记录都要被引用
        for ev in sg_["events"][:2]:
            if not (set(ev["records"]) & set(refs)) and not any(_near_event(offered[r], [ev]) for r in refs if r in offered and offered[r]["kind"] != "task_step"):
                e.append(f"L3: private.evidence_refs must cite a record of event {ev['event_id']} ({ev['description']!r})")
    return e


# ---------------------------------------------------------------- 6. history 分组(chain.history_for select = by_subgoal)
PREFER = {"action_recognition": 0, "object_state_change": 0, "event_object_role": 1, "cross_event_integration": 1, "hidden_state_inference": 1, "object_recognition": 2}


def select_by_subgoal(rows, current, sample_id, per_subgoal=6, per_layer=2):
    """每个 sub-goal 最多 per_subgoal 条,每层最多 per_layer 条,优先能说明该 sub-goal 完成状态的 skill;按 sub-goal 顺序再按层排。"""
    by = collections.defaultdict(list)
    for h in rows:
        s = h.get("sg") or {}
        idx = s.get("idx")
        if isinstance(idx, list): idx = max(idx) if idx else None
        if idx is None:
            from chain import _windows, _steps_of, _overlap
            hw = _windows(h.get("media_refs")); st = _steps_of(sample_id)
            hit = [i for (i, a, b) in st for w in hw if _overlap(w, (a, b)) > 0]
            idx = max(hit) if hit else 0
        by[idx].append(h)
    out, stats = [], {}
    for idx in sorted(by):
        lr = sorted(by[idx], key=lambda h: (PREFER.get(h["capability_skill"], 3), h["turn"]))
        pick, cnt = [], collections.Counter()
        for h in lr:
            if cnt[h["layer"]] >= per_layer or len(pick) >= per_subgoal: continue
            pick.append(h); cnt[h["layer"]] += 1
        pick.sort(key=lambda h: (["L1", "L2", "L3", "L4"].index(h["layer"]), h["turn"]))
        for h in pick: h = dict(h); h["_group"] = idx
        out += [dict(h, _group=idx) for h in pick]
        stats[str(idx)] = {"n": len(pick), "available": len(lr)}
    return out, stats


def render_grouped(rows, mode, label=None):
    from chain import HIST_HEADER, ANS_PREFIX, LAYER_NAME, answer_text
    if not rows: return ""
    label = label or "neutral"
    L = [HIST_HEADER[label] + " They are grouped by the part of the task they belong to, in the order the parts happened."]
    g = None; i = 0
    for h in rows:
        if h.get("_group") != g:
            g = h.get("_group"); L.append(f"[Part {g}]")
        i += 1
        q = (h.get("question") or "").strip().replace("\n", " ")
        line = f"{i}. ({h['layer']} {LAYER_NAME.get(h['layer'], '')}) {q}"
        if h.get("options"): line += " Options: " + " | ".join(o.strip() for o in h["options"])
        L.append(line); L.append(f"   {ANS_PREFIX[label]}: {answer_text(h, mode)}")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- 7. HARNESS 规则(prompts.system_prompt 在 sg 模式追加)
HARNESS_RULES = """
- SUB-GOAL MODE (clusters that carry "sg"; v16, 10-28). Every cluster belongs to one task (task_context) and carries
  sg.events: the EXPECTED EVENTS a planner derived from the goal and the sub-goal text (what must happen to complete
  the sub-goal), each with the annotation records that fix its time. Only these events may be asked about; everything
  else in the window (wiping, changing hands, unrelated objects) is distraction and must never be the target.
  Formats: difficulty levels 1-3 are single_choice, level 4 is short_answer (no options; reference = a short phrase,
  with accepted_alternatives), except object_grounding (bbox) and L4 (its own ladder).
  * L1 (sg.kind = L1): one 10 s window inside the offered sub-goal window that contains the chosen event: use the event's
    sg.events[i].window_L1 EXACTLY as public.media_refs[0].windows[0] (and window_L2[level] for L2). public.question
    names the event in words AND its position in the clip ("about 4 seconds into the clip", "at the start of the clip"),
    then asks the perceptual fact (object in hand, nearest object, where it was put, the box). The cited anchor record
    must be in sg.bands[difficulty.level] (quartile of the perceptual quantity; 4 = hardest). private.sg_event_id = the
    event's id.
  * L2 (sg.kind = L2): one window of at most difficulty.window_max_sec inside the sub-goal window, containing the event
    (level 1 = 15 s, 2 = 30 s, 3 and 4 = the whole sub-goal). public.question describes the event in words ("when the
    breadcrumbs are poured onto the lid") but NEVER its time position: the Solver has to find it among the other
    actions. At level 4 (short_answer) ask for the action and its object / tool / destination in the Solver's own
    words. private.sg_event_id = the event's id.
  * L3 (sg.kind = L3): the cluster is one relation between an event of sub-goal k and an event of the ADJACENT
    sub-goal k+1 (sg.events, sg.rel_type, sg.ask, sg.answer_hint). public.media_refs = EXACTLY the offered window, one
    continuous clip (level 1 = the two sub-goals; 2 = plus the previous and next sub-goal; 3 and 4 = 180 s centred on
    the pair). The question names only the object / action of the LATER sub-goal and asks for the relation: what was
    done to this ingredient before, what the earlier step provided that this step needs, how its state changed, what
    state an appliance is in now. Never describe the earlier sub-goal's event in the question (that is the answer),
    never give a time position. Level 4 is short_answer. private.sg_rel_id = sg.rel_id; private.evidence_refs cite
    records of both events.
  * L4 (sg.kind = L4): the clip is the whole previous sub-goal and ends at the decision point (observation_cutoff);
    sg.remaining_sub_goals are the recorded sub-goals still to do (answer_only). Rules of goal_conditioned_planning apply
    (single choice = the next sub-goal; plan = the remaining stages).
"""
