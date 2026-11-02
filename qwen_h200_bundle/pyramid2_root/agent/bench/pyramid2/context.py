"""每轮 Runtime Context(1012.md §9)。Examiner 看 compact 过的 evidence;Solver 永远看不到这个对象。"""
import json, hashlib
import p2config as P

DROP_VALUE_KEYS = {"mask_ids", "bbox_1408", "bbox_px", "centre_xyz", "t0_sound_eids", "t1_sound_eids", "start_xyz", "end_xyz", "xyz", "start", "end", "pairs", "image_wh", "note",
                   "objects", "critical_frames"}


def compact(r, role, cluster_id):
    v = {k: x for k, x in (r.get("value") or {}).items() if k not in DROP_VALUE_KEYS and x not in (None, [], "")}
    if r["kind"] == "spatial_relation":
        v = dict(r.get("value") or {})          # 派生空间关系:完整保留(距离、候选、余量)
    if r["kind"] == "task_segment" and isinstance(v.get("steps"), list):
        v["steps"] = [{"idx": s.get("idx"), "text": s.get("text"), "t0": s.get("t0")} for s in v["steps"]]
    return {"evidence_id": r["evidence_id"], "version": r["version"], "role": role, "evidence_cluster_id": cluster_id,
            "kind": r["kind"], "domain": r["domain"],
            "time": {"start_sec": r["time"]["start_sec"], "end_sec": r["time"]["end_sec"]},
            "entities": [{"entity_id": e.get("entity_id"), "id_space": e.get("id_space"), "name": e.get("name")} for e in r.get("entities") or []],
            "value": v, "epistemic_type": r["epistemic_type"], "solver_access": r["solver_access"],
            "modalities": r["modalities_supporting_fact"], "verification": r["verification"]["status"],
            "coverage_completeness": r["coverage"]["completeness"], "quality_flags": r["quality_flags"],
            **({"checks": [{"method": c.get("method"), "verdict": c.get("verdict"), "confidence": c.get("confidence")} for c in r["checks"]]} if r.get("checks") else {})}


def history_view(rows, max_q=160):
    out = []
    for h in rows:
        out.append({"turn": h["turn"], "phase": h.get("phase", "DIAGNOSIS"), "skill": h["capability_skill"],
                    "evidence_cluster_id": h["evidence_cluster_id"], "format": h["format"], "strategy": h.get("strategy"),
                    "tests_hypothesis": h.get("tests_hypothesis"), "question": (h["question"] or "")[:max_q],
                    "verdict": h["verdict"], "solver_answer": (str(h.get("parsed") if h.get("parsed") is not None else h.get("solver_answer")))[:80],
                    "unresolved_issue": h.get("unresolved_issue"), "interference_score": h.get("interference_score"),
                    **({"sample_id": h["sample_id"]} if h.get("sample_id") else {}),
                    **({"causal_cause_idx": h["causal_cause_idx"]} if h.get("causal_cause_idx") is not None else {})})
    return out


def task_context_for(store, clusters):
    """EgoPlan:每个 cluster 所属样本的 goal + 已完成步骤 + gold 下一步(answer_only)。非 egoplan cluster 返回空。"""
    _ = store.evidence
    out = []
    for c in clusters:
        tid = c.get("sample_id")
        if not tid:
            continue
        recs = store.by_event.get(tid, [])
        seg = next((r for r in recs if r["kind"] == "task_segment"), None)
        if seg is None:
            continue
        nxt = next((r for r in recs if r["kind"] == "task_step" and r["value"].get("is_next_action")), None)
        step_rec = {r["value"].get("idx"): r for r in recs if r["kind"] == "task_step" and not r["value"].get("is_next_action")}
        narr_rec = {r["value"].get("step_idx"): r for r in recs if r["kind"] == "action_narration"}
        w0, w1 = c["window"]; cutoff = c.get("observation_cutoff")
        steps = []
        for s_ in seg["value"].get("steps") or []:
            k = s_["idx"]
            steps.append({"idx": k, "text": s_["text"], "t0": s_["t0"], "t1": s_["t1"],
                          "in_clip_window": bool(s_["t1"] >= w0 - 1e-6 and s_["t0"] <= w1 + 1e-6),
                          "before_cutoff": True if cutoff is None else bool(s_["t1"] <= float(cutoff) + 1e-6),
                          "evidence_ids": [x["evidence_id"] for x in (step_rec.get(k), narr_rec.get(k)) if x]})
        out.append({"evidence_cluster_id": c["evidence_cluster_id"], "task_id": tid, "goal": seg["value"].get("goal"),
                    "scenario": seg["value"].get("scenario"), "task_window": [seg["time"]["start_sec"], seg["time"]["end_sec"]],
                    "clip_window": c["window"], "observation_cutoff": cutoff, "steps": steps,
                    "next_action": ({"text": nxt["value"].get("text"), "choices": nxt["value"].get("choices"), "gold_letter": nxt["value"].get("gold_letter"),
                                     "time": [nxt["time"]["start_sec"], nxt["time"]["end_sec"]], "evidence_id": nxt["evidence_id"], "solver_access": "answer_only",
                                     "note": "recorded step after the task's observation cutoff; never observable; reference answers only"} if nxt else None)})
    return out


def build_context(contract, layer, skill_pair, mapping, clusters, store, state, phase="DIAGNOSIS", hypothesis=None,
                  seed_items=None, max_ctx_per_cluster=40, scope_by_task=None, used_scope_ids=(), tree_node=None):
    original_skill, capability_skill = skill_pair
    ev = []
    cl_meta = []
    for c in clusters:
        for r in c["core"]:
            ev.append(compact(r, "target", c["evidence_cluster_id"]))
        ctx = c["context"][:max_ctx_per_cluster]
        for r in ctx:
            ev.append(compact(r, "context", c["evidence_cluster_id"]))
        tested = [h for h in state.get("history", []) if h["evidence_cluster_id"] == c["evidence_cluster_id"]]
        cl_meta.append({"evidence_cluster_id": c["evidence_cluster_id"], "media_id": c["media_id"], "video_id": c["video_id"], "sample_id": c.get("sample_id"),
                        "window": c["window"], "observation_cutoff": c["observation_cutoff"],
                        "two_windows_allowed": c["two_windows_allowed"], "interference": c["interference"],
                        **({"windows": c["windows"], "gap": {k: v for k, v in c["gap"].items() if k not in ("hidden_texts", "all_step_texts")} | {"hidden_steps": c["gap"]["hidden_texts"]}} if c.get("gap") else {}),
                        **({"l3ext": c["l3ext"], **({"windows": c["windows"]} if c.get("windows") else {})} if c.get("l3ext") else {}),
                        **({"sg": c["sg"], **({"windows": c["windows"]} if c.get("windows") else {})} if c.get("sg") else {}),   # 10-28 v15
                        "n_target_records": len(c["core"]), "n_context_records_shown": len(ctx), "n_context_records_total": len(c["context"]),
                        "already_tested": [{"turn": h["turn"], "format": h["format"], "verdict": h["verdict"]} for h in tested]})
    hyps = [h for h in state.get("hypotheses", []) if h["status"] == "open"]
    ctx = {
        "run_id": contract["run_id"], "protocol_version": contract["protocol_version"],
        "evaluation_protocol": contract["evaluation_protocol"], "taxonomy_version": contract["taxonomy_version"],
        "prompt_version": contract["prompt_version"], "phase": phase, "current_layer": layer,
        "current_skill": capability_skill, "capability_mapping": mapping,
        "extension_registry": {"registry_version": store.registry.get("registry_version"),
                               "enabled_skills": contract.get("extension_registry", {}).get("enabled_skills", [])},
        "coverage_targets": contract.get("coverage_targets", []),
        "solver_input_spec": contract["solver_input_spec"],
        "diagnosis_hypothesis": hypothesis,
        "evidence_clusters": cl_meta,
        "verified_evidence": ev,
        "verified_seed_items": seed_items or [],
        "current_layer_history": history_view(state.get("history", [])) if phase == "DIAGNOSIS" else [],
        "coverage": state.get("coverage", {}) if phase == "DIAGNOSIS" else {},
        "unresolved_hypotheses": hyps if phase == "DIAGNOSIS" else [],
        "remaining_budget": state.get("remaining_budget"),
        "frozen_policy": contract.get("frozen_policy") if phase == "CONFIRMATION" else None,
        "confirmation_slot": state.get("confirmation_slot") if phase == "CONFIRMATION" else None,
    }
    tc = task_context_for(store, clusters)
    if tc:
        ctx["task_context"] = tc
        if scope_by_task:
            import scope as SC
            ctx["skill_scope"], ctx["plan_phases"] = SC.entries_for(scope_by_task, layer, capability_skill, clusters, tc, used_scope_ids=used_scope_ids)
    if contract.get("allowed_formats"):
        ctx["allowed_formats"] = list(contract["allowed_formats"])
    if contract.get("plan_mode"):                   # 10-24 v6:plan 题阶段级(参考 = cutoff 后记录的 sub-goal),Examiner 与校验据此切换
        ctx["plan_mode"] = contract["plan_mode"]
    if tree_node:                                   # 10-22 题树:本轮只为这一个节点出题
        ctx["tree_node"] = tree_node
    return ctx


def strip_for_confirmation(ctx):
    """程序删 history / hypotheses / coverage / 非 slot 内容(不靠 prompt 让模型忽略)。"""
    c = dict(ctx)
    c["phase"] = "CONFIRMATION"
    c["current_layer_history"] = []; c["unresolved_hypotheses"] = []; c["coverage"] = {}
    c["diagnosis_hypothesis"] = None; c["verified_seed_items"] = []
    for m in c["evidence_clusters"]:
        m["already_tested"] = []
    return c


def context_hash(ctx):
    return hashlib.sha256(json.dumps(ctx, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


# ---- 10-28(用户定:Qwen 做 Examiner 时输入裁到 ≤ 50k token;Gemini 合约不走这里)----
_TOK = None
QWEN_PATH = "/mnt/work_new/weihanxu/agent/Qwen3-Omni/Qwen3-Omni-30B-A3B-Instruct"


def n_tokens(s):
    """Qwen tokenizer 能 import 就用(base env 装了 transformers,不需要 torch),否则按实测 3.0 字/token 估。"""
    global _TOK
    if _TOK is None:
        try:
            from transformers import AutoTokenizer
            _TOK = AutoTokenizer.from_pretrained(QWEN_PATH)
        except Exception:
            _TOK = False
    return len(_TOK(s)["input_ids"]) if _TOK else int(len(s) / 3.0)


def _dist(rec, meta):
    ws = meta.get("windows") or [meta["window"]]
    w0, w1 = ws[0][0], ws[-1][1]
    t = rec["time"]
    return max(0.0, w0 - t["end_sec"], t["start_sec"] - w1)


def trim_for_budget(ctx, contract, sys_tokens):
    """规则(用户 10-28 定):① 本层 history 只留最后 examiner_history_rows 行;② 超预算时按「离本 cluster 题窗的时间距离」从远到近丢 role=context 的记录,
    cluster 的 target(core)记录全留;③ 仍超(两个候选 cluster 的 core 本身就超限)→ 整个丢掉排序靠后的 cluster。返回 (ctx, 统计)。"""
    budget = int(contract.get("examiner_ctx_budget_tokens", 50000)) - int(sys_tokens)
    hist_n = int(contract.get("examiner_history_rows", 20))
    d = lambda: n_tokens(json.dumps(ctx, ensure_ascii=False))
    ev = ctx.get("verified_evidence") or []
    st = {"tok_before": d(), "budget": budget, "hist_before": len(ctx.get("current_layer_history") or []),
          "ctx_before": sum(1 for e in ev if e.get("role") == "context"), "clusters_before": len(ctx.get("evidence_clusters") or [])}
    ctx["current_layer_history"] = (ctx.get("current_layer_history") or [])[-hist_n:]
    metas = {m["evidence_cluster_id"]: m for m in ctx.get("evidence_clusters") or []}
    tok = d()
    if tok > budget and ev:
        order = sorted((i for i, e in enumerate(ev) if e.get("role") == "context" and e["evidence_cluster_id"] in metas),
                       key=lambda i: (-_dist(ev[i], metas[ev[i]["evidence_cluster_id"]]), -(ev[i]["time"]["end_sec"] - ev[i]["time"]["start_sec"])))
        drop = set()
        for i in order:
            if tok <= budget:
                break
            drop.add(i); tok -= n_tokens(json.dumps(ev[i], ensure_ascii=False)) + 1
        ctx["verified_evidence"] = ev = [e for i, e in enumerate(ev) if i not in drop]
        for m in ctx.get("evidence_clusters") or []:
            m["n_context_records_shown"] = sum(1 for e in ev if e.get("role") == "context" and e["evidence_cluster_id"] == m["evidence_cluster_id"])
        tok = d()
    while tok > budget and len(ctx.get("evidence_clusters") or []) > 1 and contract.get("examiner_ctx_fallback", "drop_last_cluster") == "drop_last_cluster":
        gone = ctx["evidence_clusters"].pop()["evidence_cluster_id"]
        ctx["verified_evidence"] = ev = [e for e in ev if e["evidence_cluster_id"] != gone]
        tc = [t for t in ctx.get("task_context") or [] if t.get("evidence_cluster_id") != gone]
        if tc: ctx["task_context"] = tc
        for s in ctx.get("skill_scope") or []:
            if isinstance(s.get("evidence_cluster_ids"), list): s["evidence_cluster_ids"] = [c for c in s["evidence_cluster_ids"] if c != gone]
        ctx["skill_scope"] = [s for s in ctx.get("skill_scope") or [] if s.get("evidence_cluster_ids") or not isinstance(s.get("evidence_cluster_ids"), list)]
        tok = d()
    st.update(tok_after=tok, hist_after=len(ctx["current_layer_history"]), ctx_after=sum(1 for e in ev if e.get("role") == "context"),
              clusters_after=len(ctx.get("evidence_clusters") or []))
    return ctx, st
