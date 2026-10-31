"""Scope planner(10-14 用户定):goal + plan -> 每层每 skill「问哪些 event、推什么关系、避免什么」。
每样本一次 Gemini 调用(contract.scope_model,默认 examiner_model),缓存 data/scope_cache/<task_id>.<hash>.json,run 里复制到 runs/<run>/scope/。
Examiner 每轮只看本层本 skill 的条目(context.build_context -> entries_for);cluster 选择按命中排序(controller.pool_for -> cluster_hit)。"""
import json, hashlib, time, collections
from pathlib import Path
import p2config as P
import prompts, retrieve

SKILL_DEFS = {
    "object_recognition":             ("L1", "The object the camera wearer handles at one moment of a recorded step: ask what is in hand / being manipulated when a visible cue happens. Not the purpose."),
    "action_recognition":             ("L2", "What action (verb + object) is performed within one recorded step shown in the clip."),
    "event_object_role":              ("L2", "Within one recorded step: which object is acted on, which tool is used, where it goes (destination)."),
    "activity_recognition":           ("L2", "Which recorded step / local activity the clip shows at a given moment."),
    "action_temporal_order":          ("L2", "Order of recorded steps that are directly shown close together (span <= 15 s)."),
    "inter_event_temporal_reasoning": ("L3", "Order / count / progress across steps spread over the task (span > 15 s): what came before what, how many times an action recurred, which steps are already done by the cutoff."),
    "action_purpose_inference":       ("L3", "Why a recorded step was done (its purpose for the task), inferred from context without naming the goal."),
    "next_step_prediction":           ("L3", "The recorded step that follows the cutoff; the Solver sees the clip only up to the cutoff."),
    "goal_conditioned_planning":      ("L4", "At the task cutoff: what action to take next (the four official choices) or the next 4-8 steps to finish the task."),
    "plan_gap_filling":               ("L4", "Given the end of sub-goal k and the start of sub-goal k+m, which sub-goals were carried out in between (recorded order); event_refs = [k, k+m]."),
}
import p2config as P
import l3ext as _LX                                    # 10-27 L3 扩展 skill(定义 / note 在 l3ext.py)
SKILL_DEFS.update(_LX.SCOPE_DEFS)
# 10-27 晚 v13(用户:scope planner 要给每个 skill 划考试范围):v11 起启用、此前没交给 planner 的 9 个 skill。
# 只有 contract.scope_all_skills = true 时才交给 planner(v12 及以前的 run 不变)。
V13_SKILL_DEFS = {
    "spatial_near":                ("L1", "At one moment inside a recorded sub-goal: which of the listed objects is nearest / farthest to a reference object (3D positions from the dataset; candidates listed in the question)."),
    "spatial_side":                ("L1", "At one moment inside a recorded sub-goal: which of the listed objects is leftmost / rightmost from the camera wearer's viewpoint at that moment."),
    "object_location_at_time":     ("L1", "Where (on which fixture / surface / container) an object is put down at one moment of a recorded sub-goal."),
    "object_state_change":         ("L2", "Within one recorded sub-goal: an object's start and end location / state through one movement (where it was taken from, where it went)."),
    "sound_action_binding":        ("L2", "Within one recorded sub-goal: which action / object produced a sound heard in the clip."),
    "sound_movement_binding":      ("L2", "Within one recorded sub-goal: which object movement produced / coincides with a sound."),
    "sound_anchored_spatial_near": ("L2", "The moment is fixed by a sound inside a recorded sub-goal; at that moment, which listed object is nearest to the reference object."),
    "sound_anchored_spatial_side": ("L2", "The moment is fixed by a sound inside a recorded sub-goal; at that moment, which listed object is leftmost / rightmost for the wearer."),
    "inter_event_spatial_extreme": ("L3", "After several placements across sub-goals, which listed object ends nearest / farthest to a reference (needs integrating where things were put in different sub-goals)."),
    "inter_event_spatial_order":   ("L3", "After several placements across sub-goals, the order of the listed objects by distance to a reference."),
}
SKILL_DEFS.update(V13_SKILL_DEFS)
LAYERS = ["L1", "L2", "L3", "L4"]
CACHE = P.DATA / "scope_cache"
SKILL_NOTE = {
    **_LX.SCOPE_NOTES,
    "_default": "evidence_steps are recorded steps that can be shown inside a 30 s clip window; the item asks about what is visible.",
    "next_step_prediction": "evidence_steps are CANDIDATE TARGET steps: for each, the clip ends exactly where that step starts (observation cutoff), "
                            "so the Solver has NOT seen it; the item asks which recorded step comes next and the reference is that step itself. "
                            "'next' = the official next action, which is the target only when the cutoff is the task's observation frame.",
    "goal_conditioned_planning": "the clip ends at the task's observation frame (after all recorded steps); 'segment' = the whole recorded progress, "
                                 "'next' = the official next action, which is the reference answer.",
    "inter_event_temporal_reasoning": "evidence_steps are anchor steps of 60 s windows; the item must integrate at least two steps more than 15 s apart.",
    "spatial_near": "evidence_steps are the sub-goals during which a dataset-derived nearest / farthest relation holds at one moment; pick those whose reference object is an ingredient / tool / container of the goal.",
    "spatial_side": "evidence_steps are the sub-goals during which a dataset-derived left / right relation (wearer's view) holds at one moment; pick goal objects.",
    "object_location_at_time": "evidence_steps are the sub-goals in which a recorded put-down happens; pick put-downs of goal objects.",
    "object_state_change": "evidence_steps are the sub-goals containing a recorded movement (pick-up -> put-down) of an object; pick goal objects.",
    "sound_action_binding": "evidence_steps are the sub-goals containing an annotated sound; pick sounds produced by goal actions (chopping, sizzling, pouring), not background.",
    "sound_movement_binding": "evidence_steps are the sub-goals where an annotated sound coincides with a recorded object movement; pick goal objects.",
    "sound_anchored_spatial_near": "evidence_steps are the sub-goals where a sound fixes the moment of a derived nearest relation; pick goal objects / goal sounds.",
    "sound_anchored_spatial_side": "evidence_steps are the sub-goals where a sound fixes the moment of a derived left / right relation; pick goal objects / goal sounds.",
    "inter_event_spatial_extreme": "evidence_steps are the sub-goals whose end has a derived nearest / farthest relation built from earlier placements; pick goal objects.",
    "inter_event_spatial_order": "evidence_steps are the sub-goals whose end has a derived distance order built from earlier placements; pick goal objects.",
    "plan_gap_filling": "evidence_steps are HEAD steps k that have a tail step k+m (m = 2, 3 or 4) in this task; an entry's event_refs must be [k, k+m]; "
                        "the Solver sees only the last seconds of k and the first seconds (or frame) of k+m and must name the hidden steps in between.",
}


def _prompt(contract):
    import examiner as EX
    p = EX._prompts(contract)
    if not p.get("scope"):
        raise KeyError(f"prompt file {p.get('_path')} has no '## 8.' scope section")
    return p["scope"]


def task_ids_for(store, contract):
    """contract.videos 里 egoplan 样本的 task_id(= task_segment.event_id)。"""
    _ = store.evidence
    out = []
    for vid in contract.get("videos", []):
        for r in store.by_video.get(vid, []):
            if r["kind"] == "task_segment" and r["provenance"].get("dataset") in retrieve.TASK_DATASETS and r.get("event_id"):
                out.append(r["event_id"])
    return sorted(set(out))


def task_record(store, task_id):
    _ = store.evidence                      # 触发索引
    recs = store.by_event.get(task_id, [])
    seg = next((r for r in recs if r["kind"] == "task_segment"), None)
    nxt = next((r for r in recs if r["kind"] == "task_step" and r["value"].get("is_next_action")), None)
    return seg, nxt


def anchors_by_skill(store, contract, seg):
    """每个 skill 在该样本上实际有 cluster 的锚点步骤(避免 scope 指向没有证据的 event)。"""
    skills = [s for s in contract.get("include_skills") or list(SKILL_DEFS) if s in SKILL_DEFS
              and (contract.get("scope_all_skills") or s not in V13_SKILL_DEFS)]
    excl = P.excluded_skills(); skills = [s for s in skills if s not in excl]
    out = {}
    for sk in skills:
        retrieve.EGOPLAN_L4_INTERMEDIATE = bool(contract.get("l4_intermediate_cutoffs"))
        cl = retrieve.clusters(store, seg["video_id"], sk, seed=contract.get("seed", 0), max_clusters=40, min_gap=contract.get("cluster_min_gap", 10.0))
        refs = set()
        for c in cl:
            if c.get("sample_id") != seg["event_id"]:
                continue
            if c.get("anchor_kind") == "task_segment":
                refs.add("segment")
            elif c.get("anchor_is_next"):
                refs.add("next")
            elif c.get("anchor_step_idx") is not None:
                refs.add(int(c["anchor_step_idx"]))
        out[sk] = sorted(refs, key=lambda x: (isinstance(x, str), x))
    return out


def build_input(store, contract, task_id):
    seg, nxt = task_record(store, task_id)
    if seg is None:
        return None
    v = seg["value"]
    skills = anchors_by_skill(store, contract, seg)
    return {"task_id": task_id, "goal": v.get("goal"), "scenario": v.get("scenario"),
            "task_window": [seg["time"]["start_sec"], seg["time"]["end_sec"]],
            "observation_cutoff": seg["time"]["end_sec"],
            "steps": [{"idx": s["idx"], "text": s["text"], "t0": s["t0"], "t1": s["t1"]} for s in v.get("steps") or []],
            "next_action": {"text": nxt["value"].get("text"), "choices": nxt["value"].get("choices"), "gold_letter": nxt["value"].get("gold_letter")} if nxt else None,
            "skills": {sk: {"layer": SKILL_DEFS[sk][0], "definition": SKILL_DEFS[sk][1], "evidence_steps": refs, "evidence_note": SKILL_NOTE.get(sk, SKILL_NOTE["_default"])}
                       for sk, refs in skills.items()}}


def validate(sc, n_steps, skills):
    """清洗 planner 输出:refs 只能是 1..n / "next" / "segment";L1/L2 不得含 next;每 skill ≤ 4 条;返回 (clean, warnings)。"""
    warn = []
    if not isinstance(sc, dict) or not isinstance(sc.get("layers"), dict):
        return None, ["no layers object"]
    allowed = set(range(1, n_steps + 1)) | {"next", "segment"}
    clean = {"task_id": sc.get("task_id"), "goal": sc.get("goal"), "phases": [], "layers": {L: {} for L in LAYERS}}
    if isinstance(sc.get("skipped"), dict): clean["skipped"] = {str(k): str(v)[:200] for k, v in sc["skipped"].items()}     # 10-27 v13
    for ph in sc.get("phases") or []:
        if isinstance(ph, dict):
            idx = [int(i) for i in (ph.get("step_idx") or []) if str(i).isdigit() and 1 <= int(i) <= n_steps]
            if idx:
                clean["phases"].append({"name": str(ph.get("name") or "")[:80], "step_idx": idx})
    for L, byskill in sc["layers"].items():
        if L not in LAYERS or not isinstance(byskill, dict):
            warn.append(f"layer {L!r} dropped"); continue
        for sk, ents in byskill.items():
            if sk not in skills:
                warn.append(f"{L}/{sk}: unknown skill dropped"); continue
            if SKILL_DEFS.get(sk, (L,))[0] != L:
                warn.append(f"{L}/{sk}: skill belongs to {SKILL_DEFS[sk][0]}, dropped"); continue
            keep = []
            for i, e in enumerate(ents if isinstance(ents, list) else []):
                if not isinstance(e, dict):
                    continue
                refs = []
                for x in (e.get("event_refs") or []):
                    if isinstance(x, bool):
                        continue
                    if isinstance(x, (int, float)) or (isinstance(x, str) and x.strip().isdigit()):
                        xi = int(x)
                        if xi in allowed: refs.append(xi)
                    elif isinstance(x, str) and x.strip().lower() in ("next", "segment"):
                        refs.append(x.strip().lower())
                if L in ("L1", "L2") and "next" in refs:
                    warn.append(f"{L}/{sk}#{i}: 'next' removed (not observable)"); refs = [r for r in refs if r != "next"]
                if not refs:
                    warn.append(f"{L}/{sk}#{i}: no valid event_refs, dropped"); continue
                keep.append({"scope_id": str(e.get("scope_id") or f"{L}-{sk}-{len(keep) + 1}"), "event_refs": refs,
                             "target": e.get("target"), "relation": e.get("relation"), "ask": e.get("ask"), "avoid": e.get("avoid")})
                if len(keep) >= 40:
                    warn.append(f"{L}/{sk}: more than 40 entries, truncated"); break
            if keep:
                clean["layers"][L][sk] = keep
    return clean, warn


def mock_scope(inp):
    """mock:每个有证据的步骤一条(穷举式)。"""
    sc = {"task_id": inp["task_id"], "goal": inp["goal"], "phases": [{"name": "all", "step_idx": [s["idx"] for s in inp["steps"]]}], "layers": {L: {} for L in LAYERS}}
    for sk, d in inp["skills"].items():
        ents = [{"scope_id": f"{d['layer']}-{sk}-{i + 1}", "event_refs": [r], "target": f"mock {r}", "relation": "mock", "ask": "mock", "avoid": "mock"} for i, r in enumerate(d["evidence_steps"])]
        if ents:
            sc["layers"][d["layer"]][sk] = ents
    return sc


def _hash(contract, inp):
    sys_p = _prompt(contract)
    return hashlib.sha1((sys_p + json.dumps(inp, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()[:10]


def plan_one(contract, store, task_id, run_dir=None, force=False, mock=None):
    import examiner as EX
    inp = build_input(store, contract, task_id)
    if inp is None:
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    h = _hash(contract, inp)
    qwen_scope = (contract.get("scope_backend") or contract.get("examiner_backend")) == "qwen_http" and contract.get("scope_backend") != "gemini"
    cp = CACHE / f"{task_id}.{h}{'.mock' if mock else ''}{'.qwen' if qwen_scope else ''}.json"      # mock / qwen 的 scope 单独缓存(_hash 不含 model),不污染 Gemini 的
    if cp.exists() and not force:
        return json.loads(cp.read_text())
    skills = list(inp["skills"])
    n_steps = len(inp["steps"])
    rec = {"task_id": task_id, "prompt_hash": h, "model": "mock" if mock else contract.get("scope_model", contract["examiner_model"]),
           "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "input": inp, "scope": None, "warnings": [], "usage": {}, "status": "failed"}
    if mock:
        rec["scope"], rec["warnings"] = validate(mock_scope(inp), n_steps, skills); rec["status"] = "ok"
    else:
        sys_p = _prompt(contract)
        last = None
        for attempt in range(2):
            try:
                if qwen_scope:                                  # 10-28(用户定):scope planner 也可走本地 Qwen
                    text, u = EX.call_qwen(sys_p, json.dumps(inp, ensure_ascii=False), contract.get("qwen_examiner_url") or contract.get("qwen_url", "http://127.0.0.1:8799"),
                                           max_tokens=contract.get("scope_max_tokens", 6144), run_dir=run_dir, role="scope", meta={"task_id": task_id})
                else:
                    text, u = EX.call(sys_p, json.dumps(inp, ensure_ascii=False), rec["model"], max_tokens=contract.get("scope_max_tokens", 8192),
                                      thinking=contract.get("scope_thinking", "default"), run_dir=run_dir, role="scope", meta={"task_id": task_id})
                out = EX.jparse(text)
                if isinstance(out, list):
                    out = next((x for x in out if isinstance(x, dict)), None)
                clean, warn = validate(out, n_steps, skills)
                if clean is None:
                    raise ValueError("; ".join(warn))
                rec.update(scope=clean, warnings=warn, usage=u, status="ok", raw_len=len(text)); break
            except Exception as e:
                last = f"{type(e).__name__}: {str(e)[:200]}"
                rec["warnings"].append(f"attempt {attempt + 1}: {last}")
        if rec["scope"] is None:
            rec["error"] = last
    cp.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


def ensure(contract, store, run_dir=None, task_ids=None, force=False, mock=None):
    """返回 {task_id: scope}(失败的记 None);run_dir 给了就复制一份到 runs/<run>/scope/。"""
    tids = task_ids or task_ids_for(store, contract)
    out = {}
    for tid in tids:
        rec = plan_one(contract, store, tid, run_dir=run_dir, force=force, mock=mock)
        if rec is None:
            continue
        out[tid] = rec.get("scope")
        if run_dir is not None:
            d = Path(run_dir) / "scope"; d.mkdir(parents=True, exist_ok=True)
            (d / f"{tid}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return out


def _refs_of(scope_by_task, task_id, layer, skill):
    sc = (scope_by_task or {}).get(task_id)
    if not sc:
        return []
    return sc.get("layers", {}).get(layer, {}).get(skill, []) or []


def cluster_steps(cluster):
    """cluster 核心证据覆盖的步骤 idx(+ segment / next)。"""
    out = set()
    for r in cluster.get("core") or []:
        v = r.get("value") or {}
        if r["kind"] == "task_segment":
            out.add("segment")
        elif v.get("is_next_action"):
            out.add("next")
        else:
            k = v.get("step_idx") or v.get("idx")
            if k is not None:
                out.add(int(k))
    return out


def cluster_entries(scope_by_task, layer, skill, cluster):
    """该 cluster 里能问到的 scope 条目 id(条目的 event_refs 与 cluster 步骤有交集)。"""
    ents = _refs_of(scope_by_task, cluster.get("sample_id"), layer, skill)
    if not ents:
        return []
    steps = cluster_steps(cluster)
    return [e["scope_id"] for e in ents if set(e.get("event_refs", [])) & steps]


def cluster_hit(scope_by_task, layer, skill, cluster):
    """该 cluster 的锚点是否落在 scope 指定的 event 上。"""
    ents = _refs_of(scope_by_task, cluster.get("sample_id"), layer, skill)
    if not ents:
        return False
    refs = {r for e in ents for r in e.get("event_refs", [])}
    if cluster.get("anchor_kind") == "task_segment":
        return "segment" in refs
    if cluster.get("anchor_is_next"):
        return "next" in refs
    k = cluster.get("anchor_step_idx")
    return k is not None and int(k) in refs


def entries_for(scope_by_task, layer, skill, clusters, task_context, used_scope_ids=()):
    """Examiner context 用:本层本 skill 的 scope 条目,event_refs 映射到本轮 offered 的 evidence / cluster;只保留能映射的条目;标 already_asked。"""
    tc_by_cl = {t["evidence_cluster_id"]: t for t in task_context}
    seen, out, phases = set(), [], {}
    for c in clusters:
        tid = c.get("sample_id"); tc = tc_by_cl.get(c["evidence_cluster_id"])
        if not tid or tc is None:
            continue
        sc = (scope_by_task or {}).get(tid)
        if sc and tid not in phases:
            phases[tid] = sc.get("phases") or []
        core_ids = {r["evidence_id"] for r in c["core"]}
        step_ev = {s["idx"]: s["evidence_ids"] for s in tc["steps"]}
        seg_ev = [r["evidence_id"] for r in c["core"] if r["kind"] == "task_segment"]
        nxt_ev = [(tc.get("next_action") or {}).get("evidence_id")] if tc.get("next_action") else []
        for e in _refs_of(scope_by_task, tid, layer, skill):
            ev = []
            for r in e["event_refs"]:
                ev += seg_ev if r == "segment" else nxt_ev if r == "next" else step_ev.get(r, [])
            ev = [x for x in ev if x]
            if not (set(ev) & core_ids):
                continue
            key = (tid, e["scope_id"])
            if key in seen:
                nxt_entry = next(x for x in out if x["task_id"] == tid and x["scope_id"] == e["scope_id"])
                nxt_entry["evidence_cluster_ids"].append(c["evidence_cluster_id"]); continue
            seen.add(key)
            out.append({"task_id": tid, "scope_id": e["scope_id"], "event_refs": e["event_refs"], "evidence_ids": sorted(set(ev) & core_ids),
                        "evidence_cluster_ids": [c["evidence_cluster_id"]], "target": e.get("target"), "relation": e.get("relation"),
                        "ask": e.get("ask"), "avoid": e.get("avoid"), "already_asked": ((tid, e["scope_id"]) in set(map(tuple, used_scope_ids)))})
    out.sort(key=lambda x: x["already_asked"])          # 未问过的排前
    return out, phases


def n_entries(scope_by_task, layer, skill, task_ids):
    return sum(len(_refs_of(scope_by_task, tid, layer, skill)) for tid in task_ids)
