"""离线测试用:mock Examiner(从第一个 cluster 造一道合法 single_choice / short_answer 题)+ 按脚本答题的 mock Solver。
script 例:"W,W,W,C,C,C,..." 逐次消费;耗尽后全部 C。"""
import itertools


class Mock:
    def __init__(self, script, store):
        self.seq = [x.strip().upper() for x in (script or "").split(",") if x.strip()]
        self.i = 0; self.store = store

    def examine(self, ctx, clusters, hyp):
        c = clusters[0]
        fmt = "single_choice"
        if hyp and hyp["type"] == "format_sensitivity":
            fmt = "short_answer" if "single_choice" in hyp["forbidden_formats"] else "single_choice"
        if ctx["phase"] == "CONFIRMATION":
            fmt = "single_choice"
        diff = ctx.get("difficulty") or {}                          # v8 阶梯:按 controller 给的档出题型 / 窗长
        if diff.get("format"): fmt = diff["format"]
        strat = hyp["strategy_required"] if hyp else "coverage"
        core = [e for e in ctx["verified_evidence"] if e["role"] == "target" and e["evidence_cluster_id"] == c["evidence_cluster_id"]]
        # scope 覆盖:选这个 cluster 上第一个未问过的条目(没有就 null)
        hyp_sid = (hyp or {}).get("original_scope_id")
        ents = [x for x in (ctx.get("skill_scope") or []) if c["evidence_cluster_id"] in x.get("evidence_cluster_ids", []) and not x.get("already_asked") and x["scope_id"] != hyp_sid]
        scope_id = ents[0]["scope_id"] if ents else None
        if ctx.get("tree_node"):                                   # 10-22 题树:scope_id = 节点 id
            scope_id = ctx["tree_node"]["node_id"]
        w = list(c["window"])
        wmax = float(diff.get("window_max_sec") or 30.0)
        if c.get("observation_cutoff") is not None:                # cutoff 题:窗口 ≤ 30 s 且结束在 cutoff
            w = [max(w[0], c["observation_cutoff"] - wmax), c["observation_cutoff"]]
        elif w[1] - w[0] > wmax: w = [w[0], w[0] + wmax]
        opts = ["A. alpha", "B. beta", "C. gamma", "D. delta"]
        ao = sorted([e for e in ctx["verified_evidence"] if e.get("solver_access") == "answer_only" and (e.get("value") or {}).get("text")], key=lambda e: (e.get("time") or {}).get("start_sec", 0))
        if ao: opts[1] = "B. " + ao[0]["value"]["text"]            # 参考答案校验要求 = 截断后第一条记录步骤
        gap_pri = {}
        if c.get("gap"):                                               # 10-24 gap 题:两窗 = cluster 给的;参考 = 隐藏步骤;干扰项按骨架
            g = c["gap"]; fmt = diff.get("format") or "single_choice"
            ref = " → ".join(g.get("hidden_steps") or g.get("hidden_texts") or []); sk = g.get("distractor_skeletons") or []
            para = lambda t: t + " (rephrased)"
            texts = [" → ".join(para(h) for h in (g.get("hidden_steps") or g.get("hidden_texts") or []))] + [" → ".join(para(x["text"]) for x in s_["steps"]) for s_ in sk][:3]
            while len(texts) < 4: texts.append(f"mock distractor {len(texts)}")
            opts = [f"{L}. {t}" for L, t in zip("ABCD", texts)]
            types = [s_["type"] for s_ in sk] + ["plausible_unobserved"] * 3
            ev_ids = [e_["evidence_id"] for e_ in core[:2]] or ["mock"]
            gap_pri = {"gap": {"head_idx": g["head_idx"], "tail_idx": g["tail_idx"], "hidden_idx": g["hidden_idx"], "order_constraints": [],
                               "distractor_types": {L: t_ for L, t_ in zip("BCD", types)}, "distractor_evidence": {L: ev_ids for L in "BCD"}}}
            pub = {"media_refs": [{"media_id": c["media_id"], "windows": [list(c["windows"][0]), list(c["windows"][1])]}], "observation_cutoff": c["observation_cutoff"],
                   "format": fmt, "question": f"Mock gap question {scope_id or ''}: between the two segments, what did the person do?", "task_conditions": None,
                   "options": opts, "gap_item": {"n_hidden": g["n_hidden"]}}
            ans = "A"
        else:
            if fmt == "multi_select": opts = ["A. alpha is true", "B. beta is true", "C. gamma is false"]
            pub = {"media_refs": [{"media_id": c["media_id"], "windows": [w]}], "observation_cutoff": c["observation_cutoff"],
                   "format": fmt, "question": f"Mock question {scope_id or ''} about what happens in this clip?", "task_conditions": None,
                   "options": opts if fmt in ("single_choice", "multi_select") else None}
            ans = "B" if fmt == "single_choice" else "A, B" if fmt == "multi_select" else "beta"
            if fmt == "plan":                                        # 阶段级参考 = task_context 里 cutoff 之后的 sub-goal(≤8)
                tc = next((t for t in (ctx.get("task_context") or []) if t.get("evidence_cluster_id") == c["evidence_cluster_id"]), None)
                cut = c.get("observation_cutoff")
                rem = [s_["text"] for s_ in ((tc or {}).get("steps") or []) if cut is not None and s_["t0"] >= float(cut) - 1e-6][:8]
                ans = "\n".join(f"{i+1}. {t}" for i, t in enumerate(rem)) or "1. mock stage"
        sp_anchor = next((e for e in core if e["kind"] == "spatial_relation"), None)
        if sp_anchor and not c.get("l3ext"):                            # 10-27 spatial 锚点:题面按 _frame_statement_checks 的要求写(参照物 / 关系词 / 只在候选里比 / 视角)
            v = sp_anchor.get("value") or {}; rel = v.get("relation", ""); ref = v.get("reference_object") or "the reference object"
            cands = [v.get("answer_object")] + list(v.get("verified_wrong_answers") or [])[:3]
            while len(cands) < 4: cands.append(f"mock object {len(cands)}")
            fmt = diff.get("format") or "single_choice"
            if rel.startswith("side_"):
                q = f"Mock {scope_id or ''}: at that moment, from the camera wearer's own viewpoint, which of the following objects is farthest to the wearer's {rel.split('_')[1]}?"
            elif rel == "order_by_distance":
                q = f"Mock {scope_id or ''}: among the following orderings, which lists these objects from closest to farthest from the {ref} at the end of the clip?"
            else:
                q = f"Mock {scope_id or ''}: among the following objects, which is the {'closest' if rel in ('nearest', 'near', 'nearest_final') else 'farthest'} to the {ref} at that moment?"
            w = list(c["window"]); wmax = float(diff.get("window_max_sec") or 30.0)
            T = float(v.get("anchor_time_sec") or w[0]); w = [max(w[0], min(T - wmax / 2, w[1] - wmax)), 0]; w[1] = min(c["window"][1], w[0] + wmax)
            if fmt == "multi_select":
                opts = [f"A. The {cands[0]} is the answer.", f"B. The {cands[1]} is the answer.", f"C. The {cands[2]} is the answer."]; ans = "A"
            elif fmt == "short_answer":
                opts = None; ans = cands[0]
            else:
                opts = [f"{L}. {t}" for L, t in zip("ABCD", cands)]; ans = "A"
            pub = {"media_refs": [{"media_id": c["media_id"], "windows": [[round(w[0], 3), round(w[1], 3)]]}], "observation_cutoff": c["observation_cutoff"], "format": fmt, "question": q, "task_conditions": None, "options": opts}
            return {"action": "PROPOSE_CONFIRMATION" if ctx["phase"] == "CONFIRMATION" else "PROPOSE_DIAGNOSTIC", "layer": ctx["current_layer"], "skill": ctx["current_skill"], "strategy": strat,
                    "tests_hypothesis": hyp["hypothesis_id"] if hyp else None, "selection_reason": "mock", "evidence_cluster_id": c["evidence_cluster_id"], "public": pub,
                    "private": {"domain": "physical.spatial", "evidence_refs": [sp_anchor["evidence_id"]], "proposed_reference_answer": ans, "gold_answer": None,
                                "reference_frame": {"type": "camera_at_time" if rel.startswith("side_") else "world", "reference_timestamp": v.get("anchor_time_sec")},
                                "accepted_alternatives": [], "acceptance_criteria": [], "rubric": ["mock rubric"], "coverage_requirements": [], "classification_status": "provisional",
                                "gold_verification_status": "needs_verification", "validation_status": "PENDING_VALIDATION", "answerability_note": None, "scope_id": scope_id}, "verification_request": None}
        if c.get("l3ext"):                                             # 10-27 L3 扩展:按 cluster.l3ext 造合法题,参考与校验器一致
            mt = c["l3ext"]; k = mt["kind"]; fmt = diff.get("format") or "single_choice"
            base = {"media_refs": [{"media_id": c["media_id"], "windows": [list(x) for x in (c.get("windows") or [c["window"]])]}], "observation_cutoff": c["observation_cutoff"],
                    "format": fmt, "task_conditions": None, "options": None}
            core_all = [e for e in ctx["verified_evidence"] if e["evidence_cluster_id"] == c["evidence_cluster_id"]]
            ev_ids = [e["evidence_id"] for e in core[:2]] or ["mock"]
            extra = {}
            if k == "frame_transform":
                quads = ["front-left", "front-right", "back-left", "back-right"]
                pub = dict(base, question=f"Mock {scope_id or ''}: at the end of the clip, from the camera wearer's own viewpoint as the camera faces then, where is the {mt['object']} that the wearer put down earlier? (the wearer's left/right)", options=[f"{L}. {q_}" for L, q_ in zip("ABCD", quads)])
                ans = "ABCD"[quads.index(mt["quadrant"])]; extra = {"frame_transform": {"object": mt["object"], "quadrant": mt["quadrant"]}}
            elif k == "next_pickup":
                names = [mt["object"]] + list(mt["distractor_pool"])[:3]
                pub = dict(base, question="Mock item: which object will the camera wearer pick up next, right after the clip ends?", options=[f"{L}. the {n_}" for L, n_ in zip("ABCD", names)])
                ans = "A"; extra = {"next_pickup": {"object": mt["object"]}}
            elif k == "grounding":
                pub = dict(base, format="bbox", question=f"Mock {scope_id or ''}: in the first frame of the clip, where is the {mt['object']}? Give its bounding box.", options=None)
                ans = mt["reference_answer"]; extra = {"grounding": {"object": mt["object"]}}
            elif k == "gaze":                                          # 10-27 晚 AEA
                h, v, sec = mt["horizontal"], mt["vertical"], mt["sector"]; lvl = int(diff.get("level") or 1)
                qg = f"Mock {scope_id or ''}: just before the clip ends, where is the camera wearer looking, relative to the direction the camera faces?" if lvl < 4 else "Mock: one second before the clip ends, where is the camera wearer looking, relative to the direction the camera faces?"
                if fmt == "single_choice":
                    allsec = ["left-up", "front-up", "right-up", "left-down", "front-down", "right-down"]; picks = [sec] + [x for x in allsec if x != sec][:3]
                    pub = dict(base, question=qg, options=[f"{L}. {('to the wearer' + chr(39) + 's ' + x.split('-')[0]) if x.split('-')[0] != 'front' else 'straight ahead'} and {x.split('-')[1]}" for L, x in zip("ABCD", picks)]); ans = "A"
                elif fmt == "multi_select":
                    oh = [x for x in ("left", "front", "right") if x != h][0]
                    pub = dict(base, question=qg, options=[f"A. The wearer looks to the {h}." if h != "front" else "A. The wearer looks straight ahead.", f"B. The wearer looks {v}.", f"C. The wearer looks to the {oh}." if oh != "front" else "C. The wearer looks straight ahead."]); ans = "A, B"
                else:
                    pub = dict(base, question=qg); ans = f"{h} and {v}"
                extra = {"gaze": {"sector": sec}}
            elif k == "sound_source":                                  # 10-27 晚 AEA
                sec, sec8, bucket = mt["sector"], mt["sector8"], mt.get("range_bucket"); lvl = int(diff.get("level") or 1)
                qs = f"Mock {scope_id or ''}: when the {mt['sound_label']} sound is heard, from which direction relative to the way the camera wearer faces does it come?"
                if fmt == "single_choice" and lvl <= 1:
                    dirs = ["front", "left", "right", "back"]; pub = dict(base, question=qs, options=[f"{L}. {'the wearer' + chr(39) + 's ' if d in ('left', 'right') else ''}{d}" for L, d in zip("ABCD", dirs)]); ans = "ABCD"[dirs.index(sec)]
                elif fmt == "single_choice":
                    D8 = ["front", "front-left", "left", "back-left", "back", "back-right", "right", "front-right"]; i8 = D8.index(sec8); dirs = [sec8, D8[(i8 + 1) % 8], D8[(i8 - 1) % 8], D8[(i8 + 4) % 8]]
                    pub = dict(base, question=qs, options=[f"{L}. {d}" for L, d in zip("ABCD", dirs)]); ans = "A"
                elif fmt == "multi_select":
                    od = [d for d in ("front", "left", "right", "back") if d != sec][0]
                    pub = dict(base, question=qs, options=[f"A. It comes from the {sec}, {bucket}.", f"B. It comes from the {od}.", f"C. It comes from the {sec}."]); ans = "A, C"
                else:
                    pub = dict(base, question=qs); ans = f"from the {sec} ({mt['source_name']})"
                extra = {"sound_source": {"sector": sec}}
            elif k == "integration":
                w1, w2 = mt["windows"]
                a1 = next((e["evidence_id"] for e in core_all if e.get("solver_access") == "observed" and e["kind"] != "task_segment" and w1[0] - .05 <= e["time"]["start_sec"] <= w1[1] - .5), None)   # v2:在段内开始
                a2 = next((e["evidence_id"] for e in core_all if e.get("solver_access") == "observed" and e["kind"] != "task_segment" and w2[0] - .05 <= e["time"]["start_sec"] <= w2[1] - .5), None)
                ev_ids = [x for x in (a1, a2) if x]
                pub = dict(base, question=f"Mock integration {scope_id or ''}: combining both segments, how many times is the pan stirred in total?", options=["A. once", "B. twice", "C. three times", "D. never"], integration_item={"segments": 2})
                ans = "B"; extra = {"integration": {"why_both_segments": "mock"}}
            elif k == "hidden_state":
                o, st, op = mt["object"], mt["state"], mt["opposite"]
                oth = [x for x in (mt.get("other_states") or []) if not x.get("in_clip")][:2]      # v2:其它物体的假陈述(记录状态的反面)
                tail = [f"The {x['object']} is {x['opposite']}." for x in oth] + [f"The {o} has been removed.", f"The {o} is broken."]
                pub = dict(base, question=f"Mock {scope_id or ''}: at the end of the clip, which of these is true?", options=[f"A. The {o} is {st}.", f"B. The {o} is {op}.", f"C. {tail[0]}", f"D. {tail[1]}"])
                ans = "A"; extra = {"hidden_state": {"object": o, "state": st}}
            elif k == "spatial":
                names = [x["name"] for x in mt["candidates"]]
                pub = dict(base, question=f"Mock {scope_id or ''}: at the end of the clip, which of the following is {mt['relation']} to the {mt['reference']}?", options=[f"{L}. the {n}" for L, n in zip("ABCD", names)])
                ans = "ABCD"[names.index(mt["answer"])]; extra = {"spatial": {"relation": mt["relation"], "reference": mt["reference"], "answer": mt["answer"]}}
            else:   # causal
                earlier = mt["earlier"]; lvl = int(diff.get("level") or 1)
                want = [x for x in earlier if (1 <= mt["effect_idx"] - x["idx"] <= 2)] if lvl == 1 else [x for x in earlier if mt["effect_idx"] - x["idx"] >= 3] if lvl == 2 else earlier
                import collections as _co, re as _re
                prior = _co.Counter()
                for h in ctx.get("current_layer_history") or []:
                    if h.get("skill") == "causal_prerequisite_reasoning" and h.get("verdict") != "item_invalid":
                        x = h.get("causal_cause_idx")
                        for y in (x if isinstance(x, list) else [x]):
                            if isinstance(y, int): prior[y] += 1
                def _ok(x):   # v2:同一前提最多用 2 次,取物类步骤 1 次(与 l3ext.checks 一致)
                    lim = 1 if _re.search(r"\b(get|gets|getting|got|retriev\w*|fetch\w*|take out|takes out|taking out|took out|bring\w*|brought|gather\w*|collect\w*|grab\w*)\b", x["text"].lower()) else 2
                    return prior[x["idx"]] < lim
                cause = next((x for x in (want or earlier) if _ok(x)), (want or earlier)[0])
                if fmt == "multi_select":
                    pick = earlier[-4:] if len(earlier) >= 2 else earlier
                    pub = dict(base, question=f"Mock {scope_id or ''}: which earlier steps were, directly or indirectly, necessary for the action in the clip?", options=[f"{L}. {x['text']} (rephrased)" for L, x in zip("ABCDE", pick)])
                    ans = "A"; extra = {"causal": {"effect_idx": mt["effect_idx"], "cause_idx": [pick[0]["idx"]], "mechanism": "mock", "option_steps": {L: x["idx"] for L, x in zip("ABCDE", pick)}}}
                elif fmt == "short_answer":
                    pub = dict(base, question=f"Mock {scope_id or ''}: name the earlier step that was necessary for the action in the clip."); ans = cause["text"]
                    extra = {"causal": {"effect_idx": mt["effect_idx"], "cause_idx": cause["idx"], "mechanism": "mock"}}
                else:
                    others = [x for x in earlier if x is not cause][:3]
                    texts = [cause["text"] + " (rephrased)"] + [x["text"] + " (rephrased)" for x in others]
                    while len(texts) < 4: texts.append(f"mock distractor {len(texts)}")
                    pub = dict(base, question=f"Mock {scope_id or ''}: which earlier step was necessary for the action in the clip?", options=[f"{L}. {t}" for L, t in zip("ABCD", texts)])
                    ans = "A"; extra = {"causal": {"effect_idx": mt["effect_idx"], "cause_idx": cause["idx"], "mechanism": "mock"}}
            return {"action": "PROPOSE_CONFIRMATION" if ctx["phase"] == "CONFIRMATION" else "PROPOSE_DIAGNOSTIC",
                    "layer": ctx["current_layer"], "skill": ctx["current_skill"], "strategy": strat, "tests_hypothesis": hyp["hypothesis_id"] if hyp else None,
                    "selection_reason": "mock", "evidence_cluster_id": c["evidence_cluster_id"], "public": pub,
                    "private": {"domain": "physical.dynamics", "evidence_refs": ev_ids, "proposed_reference_answer": ans, "gold_answer": None, **extra,
                                "accepted_alternatives": [], "acceptance_criteria": [], "rubric": ["mock rubric"], "coverage_requirements": [],
                                "classification_status": "provisional", "gold_verification_status": "needs_verification", "validation_status": "PENDING_VALIDATION",
                                "answerability_note": None, "scope_id": scope_id}, "verification_request": None}
        if c.get("gap") and fmt == "gap_steps":
            pub["options"] = None; ans = "\n".join(f"{i+1}. {h}" for i, h in enumerate(c["gap"].get("hidden_steps") or c["gap"].get("hidden_texts") or ["mock"]))
        return {"action": "PROPOSE_CONFIRMATION" if ctx["phase"] == "CONFIRMATION" else "PROPOSE_DIAGNOSTIC",
                "layer": ctx["current_layer"], "skill": ctx["current_skill"], "strategy": strat,
                "tests_hypothesis": hyp["hypothesis_id"] if hyp else None, "selection_reason": "mock",
                "evidence_cluster_id": c["evidence_cluster_id"], "public": pub,
                "private": {"domain": "physical.dynamics", "evidence_refs": [e["evidence_id"] for e in core[:2]],
                            "proposed_reference_answer": ans, "gold_answer": None, **gap_pri,
                            "accepted_alternatives": [], "acceptance_criteria": [], "rubric": ["mock rubric"], "coverage_requirements": [],
                            "classification_status": "provisional", "gold_verification_status": "needs_verification",
                            "validation_status": "PENDING_VALIDATION", "answerability_note": None, "scope_id": scope_id},
                "verification_request": None}

    def solve(self, cand, history_text=None):
        v = self.seq[self.i] if self.i < len(self.seq) else "C"
        self.i += 1; self.last_v = v
        fmt = cand["output"]["public"]["format"]
        gold = str(cand["output"]["private"].get("proposed_reference_answer") or "B").strip()[:1]
        wrongl = "A" if gold != "A" else "B"
        if fmt == "bbox":
            full = str(cand["output"]["private"].get("proposed_reference_answer") or "10, 10, 20, 20")
            raw = f"Box: {full}\nTime: 0:00" if v == "C" else "Box: 0.0, 0.0, 3.0, 3.0\nTime: 0:00"
        else:
            raw = (f"Answer: {gold}\nTime: 0:10" if v == "C" else f"Answer: {wrongl}\nTime: 0:10") if fmt == "single_choice" else \
                  ("Answer: beta\nTime: 0:10" if v == "C" else "Answer: zeta\nTime: 0:10")
        import solver as SV
        from examiner import solver_payload
        return {"raw": raw, "prompt": SV.build_prompt(solver_payload(cand), None, history_text=history_text), "media": "mock.mp4", "time_map": None, "usage": {}, "model": "mock"}

    def grade(self, cand, sol):
        import grade as GR
        fmt = cand["output"]["public"]["format"]
        if fmt != "single_choice":                                   # 非单选题型:按脚本直接给判定(不调 judge)
            ok = getattr(self, "last_v", "C") == "C"
            return {"verdict": "correct" if ok else "wrong", "score": float(ok), "parsed": sol["raw"].split("\n")[0], "judge": "rule", "reason": None}
        return GR.grade(cand, sol, {"examiner_model": "mock"})
