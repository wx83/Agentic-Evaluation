"""11-02 v22(用户定):自上而下的题树出题。
每个 L4 决策点 k 一棵树:L4(下一步)← 1–2 条 L3 关系事实(相邻 sub-goal 的结果怎么接)← 每条 L3 两条 L2 结果事实(sub-goal 做成了什么)← 每条 L2 一到两条 L1 感知事实。
树由 Gemini 规划(plan_trees,只看 goal / sub-goal 文字 / 已匹配到标注的 event),节点共享(同一 sub-goal 的 L2 结果只出一题);
出题自下而上执行(L1 → L4),每个节点用现有 cluster + run_turn 出一题,题必须测这条事实;上层节点的 private.required_facts 由程序填成子节点题的 candidate_id;
L3 / L4 仍做四重必需性校验(controller._necessity,contract.necessity_layers)。节点 → candidate_id 映射存 run_dir/tree22_map.json。"""
import json, hashlib, time, re
from pathlib import Path
import p2config as P
import sg as SG

L2_SKILL = {"outcome": "action_recognition", "state": "object_state_change"}
L1_SKILL = {"object": "object_recognition", "location": "object_location_at_time"}
L3_SKILL = {"object_continuity": "cross_event_integration", "state_change": "cross_event_integration", "causal_prerequisite": "causal_prerequisite_reasoning", "hidden_state": "hidden_state_inference"}

PLAN_SYS = """You design a dependency tree of facts for a first-person cooking video benchmark. A recipe step (goal) is split into sub-goals (official order).
For each decision point k (the start of sub-goal k, k >= 2) build one tree:
- L4 node (node_id "dp<k>.L4"): the fact "after sub-goal k-1 the next sub-goal is k". depends_on 1-2 L3 nodes.
- L3 nodes (node_id "dp<k>.L3.<a|b>"): a RELATION between sub-goal k-1 and sub-goal k-2 (adjacent only), rel_type one of
  "causal_prerequisite" (k-1 is possible because of a specific thing k-2 produced or placed), "object_continuity" (what specifically happened to the same object between k-2 and k-1),
  "hidden_state" (a specific appliance / container setting made in k-2 that is not visible during k-1). depends_on exactly two L2 nodes (outcome of k-1, outcome of k-2).
  L3 HIDDEN-SLOT RULE: the solver will watch ONLY sub-goal k-1 and must recover the identity_slot from k-2. So the identity_slot of an L3 node MUST be a specific thing that
  (a) is observable in sub-goal k-2 (name it with the words of k-2's events / narrations / object moves), (b) is NOT visible and NOT mentioned during sub-goal k-1 (it was left behind,
  put away, replaced, or is a setting / amount / count / side-of-counter / which-of-several that cannot be seen in k-1), and (c) cannot be guessed from the recipe or common sense
  (a generic "colander", "sink", "bowl" that any cook would use is NOT acceptable; "the small white bowl on the left of the hob", "the 2nd shelf of the fridge", "the blue packet", "setting 6" are).
  identity_slot is REQUIRED for every L3 node; if no such hidden slot exists for decision point k, omit the L3 node (and the L4 node that would depend on it).
  Propose up to THREE L3 nodes per decision point (dp<k>.L3.a / .b / .c), each hinging on a DIFFERENT hidden identity slot (a container, a surface / side, a setting / count, a tool); several will be filtered out later, so prefer more candidates over fewer.
- L2 nodes (node_id "sg<j>.L2", ONE per sub-goal j, shared by all trees): the OUTCOME of sub-goal j as one sentence that names WHICH object / container / place / setting was involved
  (e.g. "The chickpeas were dried on the paper towels spread on the baking tray", not "the chickpeas were dried"). kind = "outcome". depends_on 1-2 L1 nodes.
- L1 nodes (node_id "sg<j>.L1.<a|b>"): a PERCEPTION fact at ONE listed event of sub-goal j: kind "object" (which specific object is handled) or "location" (which specific surface / container / fixture it is put on or taken from).
  Give the event_id (must be one of the listed matched events of that sub-goal).
IDENTITY RULE (most important): every fact must contain at least one IDENTITY SLOT that can be observed in the video but cannot be inferred from the recipe text or common sense:
which specific container / bowl / packet / tool, which specific surface / shelf / cabinet / side of the counter, which specific appliance setting or amount, how many pieces, which of several similar objects.
A fact that only states the kind of action ("the biscuits were crushed", "the breadcrumbs were poured into a bowl") is NOT acceptable. Use the object names, narrations and locations given for each sub-goal; do not invent objects.
If the input contains "fixed_nodes", those L1 / L2 nodes are already final: copy them verbatim (same node_id, fact, identity_slot, sub_goal, kind, event_id, depends_on) and plan ONLY the L3 / L4 nodes on top of them (L3 depends_on must reference the fixed sg<j>.L2 ids).
Return exactly one JSON object: {"nodes": [{"node_id": "...", "layer": "L1|L2|L3|L4", "fact": "...", "identity_slot": "<the specific thing the fact hinges on>", "sub_goal": <int>, "kind": "<object|location|outcome>", "rel_type": "<L3 only>", "event_id": "<L1 only>", "depends_on": ["node_id", ...]}]}"""


GUESS_SYS = """You are a cook who knows this recipe step and its sub-goals (text only; you have NOT seen the video). One specific detail of a fact is blanked as ___.
Guess the blank in at most 6 words, using the most likely specific thing a cook would use or do here. Return exactly one JSON object: {"guess": "..."}"""


def _text_guessable(contract, run_dir, ti, node, sgs):
    """v23d:L3 身份槽若凭菜谱文字 + 常识就能猜到(猜词与槽词重合 ≥ 1/2),节点作废。只给官方 sub-goal 文字,不给 narration。"""
    from examiner import call, jparse
    slot = str(node.get("identity_slot") or ""); fact = str(node.get("fact") or "")
    blank = fact.replace(slot, "___") if slot and slot in fact else fact + " [the specific thing: ___]"
    inp = {"recipe_step": ti["goal"], "sub_goals": [{"idx": s["idx"], "text": s["text"]} for s in sgs], "fact_with_blank": blank}
    text, u = call(GUESS_SYS, json.dumps(inp, ensure_ascii=False), contract.get("scope_model", contract["examiner_model"]), max_tokens=2048, thinking="off", run_dir=run_dir, role="tree_guess")
    g = str((jparse(text) or {}).get("guess") or ""); st_, gt = SG._toks(slot), SG._toks(g)
    return (len(st_ & gt) * 3 >= 2 * len(st_)) if st_ else False, g          # 猜词覆盖槽词 ≥ 2/3 → 可猜


def _hash(obj):
    return hashlib.sha1(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]


def plan_trees(store, contract, run_dir, plan, ti):
    """返回 nodes 列表;缓存 data/tree22_cache/<task>.<hash>.json 与 run_dir/tree22_plan.json。"""
    from examiner import call, jparse
    sgs = []
    for s in ti["steps"]:
        sg_ = next((x for x in plan["sub_goals"] if x["idx"] == s["idx"]), None)
        evs = [{"event_id": e["event_id"], "description": e["description"], "objects": e.get("objects"), "time": e["time"]} for e in (sg_["events"] if sg_ else []) if e.get("matched")]
        narr = []; locs = []
        for r in store.in_window(ti["video_id"], s["t0"], s["t1"], status="verified"):
            if r["solver_access"] == "answer_only": continue
            if r["kind"] == "action_narration" and len(narr) < 12: narr.append(str((r.get("value") or {}).get("text") or r.get("text") or "")[:80])
            if r["kind"] == "object_location_transition" and len(locs) < 12:
                v = r.get("value") or {}; locs.append(v.get("label") or f"{v.get('object_name')}: {v.get('from_fixture')} -> {v.get('to_fixture')}")
        sgs.append({"idx": s["idx"], "text": s["text"], "t0": s["t0"], "t1": s["t1"], "events": evs, "narrations": [x for x in narr if x], "object_moves": locs})
    dps = sorted({d["idx"] for d in (plan.get("decision_points") or []) if d.get("real", True)} or {s["idx"] for s in ti["steps"] if s["idx"] >= 2})
    inp = {"goal": ti["goal"], "sub_goals": sgs, "decision_points": [k for k in dps if k >= 2]}
    fixed = []
    if contract.get("tree_plan_reuse_from"):                                                   # v23c:L1/L2 节点沿用上一个 run 的规划(与其 L1/L2 题一一对应),只重新规划 L3/L4
        src = json.load(open(Path(P.RUNS) / contract["tree_plan_reuse_from"] / "tree22_plan.json"))["nodes"]
        fixed = [{k: v for k, v in n.items() if not k.startswith("_")} for n in src if n["layer"] in ("L1", "L2")]
        inp["fixed_nodes"] = fixed
    key = _hash({"inp": inp, "sys": PLAN_SYS})
    cdir = P.DATA / "tree22_cache"; cdir.mkdir(exist_ok=True); cf = cdir / f"{ti['task_id']}.{key}.json"
    if cf.exists():
        nodes = json.load(open(cf))["nodes"]
    else:
        text, u = call(PLAN_SYS, json.dumps(inp, ensure_ascii=False), contract.get("scope_model", contract["examiner_model"]), max_tokens=16384, thinking="default", run_dir=run_dir, role="tree_plan")
        nodes = jparse(text)["nodes"]
        if fixed: nodes = fixed + [n for n in nodes if n["layer"] in ("L3", "L4")]              # 固定节点以源 run 为准,planner 的 L1/L2 不用
        json.dump({"task_id": ti["task_id"], "input": inp, "nodes": nodes, "usage": u, "created": time.strftime("%Y-%m-%dT%H:%M:%S")}, open(cf, "w"), ensure_ascii=False, indent=1)
    # 清洗:L1 的 event_id 必须是该 sub-goal 的已匹配 event;去掉引用不存在节点的依赖
    ev_ok = {(s["idx"], e["event_id"]) for s in sgs for e in s["events"]}
    ids = {n["node_id"] for n in nodes}
    corpus = {s["idx"]: SG._toks(" ".join([s["text"]] + [e["description"] + " " + " ".join(e.get("objects") or []) for e in s["events"]] + s.get("narrations", []) + [str(x) for x in s.get("object_moves", [])])) for s in sgs}
    clean = []
    for n in nodes:
        n = dict(n); n["depends_on"] = [d for d in (n.get("depends_on") or []) if d in ids]
        if n["layer"] == "L1" and (int(n.get("sub_goal", -1)), n.get("event_id")) not in ev_ok:
            n["invalid"] = "event_id not a matched event of that sub-goal"
        if n["layer"] == "L3" and contract.get("tree_slot_hidden", True):                 # v23c:L3 的身份槽若出现在 k-1(clip 里那段)的文字里,它在 clip 里可见 → 不出;槽必须有且能在 k-2 的文字里找到
            k = int(n.get("sub_goal") or (re.search(r"dp(\d+)", n["node_id"]) or [0, 0])[1]); slot = SG._toks(str(n.get("identity_slot") or ""))   # sub_goal 缺省时从 node_id 取决策点
            if not slot:
                n["invalid"] = "L3 node has no identity_slot"
            elif len(slot & corpus.get(k - 1, set())) >= max(1, -(-2 * len(slot) // 3)):      # 槽的词 ≥ 2/3 出现在 k-1 文字里 → 视为可见
                n["invalid"] = f"identity_slot {sorted(slot & corpus.get(k - 1, set()))} appears in sub-goal {k-1} (visible in the clip)"
            elif contract.get("tree_slot_grounded", True) and not (slot & corpus.get(k - 2, set())):
                n["invalid"] = f"identity_slot {sorted(slot)} not grounded in sub-goal {k-2} text"
            elif contract.get("tree_slot_guess"):                                                  # v23d:纯文字盲猜
                try:
                    hit, g = _text_guessable(contract, run_dir, ti, n, sgs); n["text_guess"] = g
                    if hit: n["invalid"] = f"identity_slot guessable from recipe text (guess: {g!r})"
                except Exception as ex:
                    n["text_guess_error"] = str(ex)[:100]
        clean.append(n)
    json.dump({"nodes": clean, "cache": str(cf)}, open(Path(run_dir) / "tree22_plan.json", "w"), ensure_ascii=False, indent=1)
    return clean


def _map_path(run_dir): return Path(run_dir) / "tree22_map.json"


def load_map(run_dir):
    p = _map_path(run_dir); return json.load(open(p)) if p.exists() else {}


def save_map(run_dir, m): json.dump(m, open(_map_path(run_dir), "w"), ensure_ascii=False, indent=1)


def _cluster_for(node, state, store, ti, plan, contract):
    """给节点挑一个现有 cluster 并附 tree_node;返回 (cluster, skill, level) 或 (None, reason, None)。"""
    L = node["layer"]; sgi = int(node.get("sub_goal", -1))
    if L == "L1":
        cap0 = L1_SKILL.get(node.get("kind"), "object_recognition")
        for cap in (cap0, "object_recognition", "object_location_at_time", "spatial_near", "spatial_side"):   # v23:该 skill 在这个 event 没锚记录时退回其它 L1 skill 的 cluster(题仍测节点事实)
            for c in state.pools.get(cap, []):
                if c["sg"].get("idx") != sgi: continue
                ev = next((e for e in c["sg"]["events"] if e["event_id"] == node.get("event_id")), None)
                if ev is None: continue
                return SG._event_cluster(c, ev, 2), cap, 2
        for cap in (cap0, "object_recognition"):                                                                # 再退:同 sub-goal 任意 event 的 cluster,但指定本节点的 event 描述
            for c in state.pools.get(cap, []):
                if c["sg"].get("idx") == sgi and c["sg"].get("events"):
                    ev = dict(c["sg"]["events"][0]); return SG._event_cluster(c, ev, 2), cap, 2
        return None, f"no L1 cluster for sub-goal {sgi} event {node.get('event_id')} ({cap0})", None
    if L == "L2":
        cap = L2_SKILL.get(node.get("kind"), "action_recognition")
        for cap_ in (cap, "action_recognition", "object_state_change", "event_object_role"):
            c = next((c for c in state.pools.get(cap_, []) if c["sg"].get("idx") == sgi), None)
            if c: return dict(c, sg=dict(c["sg"])), cap_, 3
        return None, f"no L2 cluster for sub-goal {sgi}", None
    if L == "L3":
        cap = L3_SKILL.get(node.get("rel_type"), "cross_event_integration")
        # 两个 L2 子节点的 sub-goal → 各取该 sub-goal 第一个已匹配 event,合成一条相邻关系
        subs = sorted({int(x["sub_goal"]) for x in node.get("_children", []) if x["layer"] == "L2"})
        if len(subs) != 2 or subs[1] - subs[0] != 1: return None, f"L3 needs two adjacent L2 children (got {subs})", None
        evs = []
        for j in subs:
            sg_ = next((x for x in plan["sub_goals"] if x["idx"] == j), None)
            e = next((e for e in (sg_["events"] if sg_ else []) if e.get("matched")), None)
            if e is None: return None, f"sub-goal {j} has no matched event", None
            evs.append(e["event_id"])
        rel = {"rel_id": node["node_id"], "type": node.get("rel_type") or "object_continuity", "skill": cap, "events": evs, "ask": node["fact"], "answer_hint": node["fact"], "source": "tree22"}
        plan2 = dict(plan, relations=[rel])
        cls = SG.l3_clusters(store, ti, plan2, cap)
        c = next((c for c in cls if c["sg"]["tier"] == 2), None) or (cls[0] if cls else None)
        if c is None: return None, "l3_clusters produced nothing", None
        return c, cap, c["sg"]["tier"]
    if L == "L4" and node.get("kind") == "gap":                                      # v23b:头 = sub-goal k-2 末尾,尾 = sub-goal k 开头,隐藏 k-1(复用 retrieve.gap_clusters)
        import retrieve as R
        cap = "plan_gap_filling"
        m_ = store.media_of_video(ti["video_id"]); spec = R.skill_spec(cap, (m_ or {}).get("dataset"))
        gc = [c for c in R.gap_clusters(store, ti["video_id"], cap, spec, m_, seed=0, max_clusters=400) if c.get("sample_id") == ti["task_id"]]
        c = next((c for c in gc if c["gap"]["head_idx"] == sgi - 2 and c["gap"]["tail_idx"] == sgi and c["gap"]["n_hidden"] == 1), None)
        if c is None: return None, f"no gap cluster head {sgi-2} tail {sgi}", None
        c = dict(c); c["sg"] = {"kind": "L4", "idx": sgi, "n_segments": 2, "history_exclude_subgoals": [sgi - 1], "gap": True}
        return c, cap, 1                                                                 # GAP_U level 1 = 单选、隐藏 1 步
    if L == "L4":
        cap = "goal_conditioned_planning"
        c = next((c for c in state.pools.get(cap, []) if c["sg"].get("idx") == sgi), None)
        if c is None: return None, f"no L4 cluster for decision point {sgi}", None
        level = 1 if node.get("kind") != "remaining" else int(node.get("tier") or 3)    # v23b remaining:PLAN_U 3/4 档 = 写出剩余阶段
        return dict(c, sg=dict(c["sg"])), cap, level
    return None, "unknown layer", None


def run_tree_layer(store, state, contract, run_dir, *, run_turn, log, mock=None):
    import staircase as ST
    ST._L4_UNIFIED = contract.get("l4_ladder") == "unified"          # v23b:L4 的 PLAN_U / GAP_U 档位表
    layer = state.layer
    ti = SG.task_info(store, contract["task_sample_id"])
    import controller as CT
    plan = (CT._SG_PLAN or {}).get(contract["task_sample_id"])
    if plan is None: log(run_dir, f"{layer}: tree22: no sg plan"); return
    nodes = plan_trees(store, contract, run_dir, plan, ti)
    by_id = {n["node_id"]: n for n in nodes}
    for n in nodes: n["_children"] = [by_id[d] for d in n["depends_on"] if d in by_id]
    m = load_map(run_dir)
    mine = [n for n in nodes if n["layer"] == layer and not n.get("invalid")]
    if layer == "L4" and contract.get("l4_tiers"):                                      # 11-02 v23b:L4 完形填空档 —— gap(2 档)/ remaining(3/4 档)
        n_sg = len(ti["steps"]); extra = []
        for n in [x for x in mine if x["node_id"].endswith(".L4")]:
            k = int(n["sub_goal"])
            if "gap" in contract["l4_tiers"] and k - 2 >= 1:
                extra.append({"node_id": f"dp{k}.L4.gap", "layer": "L4", "kind": "gap", "sub_goal": k, "tier": 2, "fact": f"Between the end of sub-goal {k-2} and the start of sub-goal {k}, sub-goal {k-1} was carried out",
                              "depends_on": [f"sg{k-2}.L2"], "hidden_sub_goal": k - 1})
            if "remaining" in contract["l4_tiers"]:
                rem = n_sg - k + 1
                l3s = [x["node_id"] for x in nodes if x["layer"] == "L3" and int(x.get("sub_goal", 0)) <= k and (m.get(x["node_id"]) or {}).get("status") == "ok"][-3:]
                l2s = [f"sg{j}.L2" for j in (k - 1, k - 2) if j >= 1 and (m.get(f"sg{j}.L2") or {}).get("status") == "ok"]
                extra.append({"node_id": f"dp{k}.L4.rem", "layer": "L4", "kind": "remaining", "sub_goal": k, "tier": 3 if rem <= 2 else 4, "fact": f"After the decision point before sub-goal {k}, the remaining sub-goals are {k}..{n_sg}",
                              "depends_on": l3s or l2s or n["depends_on"], "n_remaining": rem})
        for x in extra: by_id[x["node_id"]] = x; x["_children"] = [by_id[d] for d in x["depends_on"] if d in by_id]
        mine += extra
    log(run_dir, f"{layer}: tree22: {len(mine)} nodes ({sum(1 for n in nodes if n['layer']==layer and n.get('invalid'))} invalid in plan); map has {len(m)} done")
    live = {c for o, c in state.skills}
    for o, c in state.skills: state.stair.setdefault(c, ST.new_state(contract, c))
    contract["n_per_layer"] = max(1, len(mine)); contract["turn_budget_per_layer"] = len(mine) * 3 + 6
    for n in sorted(mine, key=lambda x: (int(x.get("sub_goal", 0)), x["node_id"])):
        nid = n["node_id"]
        if nid in m: continue                                   # 续跑
        cl, cap, level = _cluster_for(n, state, store, ti, plan, contract)
        if cl is None:
            m[nid] = {"status": "no_cluster", "reason": cap}; save_map(run_dir, m); log(run_dir, f"  {layer} tree22 {nid}: skipped ({cap})"); continue
        if cap not in live:
            m[nid] = {"status": "skill_not_active", "reason": cap}; save_map(run_dir, m); log(run_dir, f"  {layer} tree22 {nid}: skill {cap} not active"); continue
        kids = [(d, m.get(d)) for d in n["depends_on"]]
        child_ids = [v["candidate_id"] for d, v in kids if v and v.get("candidate_id")]
        if layer != "L1" and n["depends_on"] and not child_ids:
            m[nid] = {"status": "children_failed", "reason": [d for d, _ in kids]}; save_map(run_dir, m); log(run_dir, f"  {layer} tree22 {nid}: all children failed -> skipped"); continue
        n["tier"] = n.get("tier") or (1 if layer == "L1" else min(4, max(1, len(child_ids))))   # v23:档 = 依赖几条子事实;v23b 的 L4 gap/remaining 自带档
        cl["sg"]["tree_node"] = {"node_id": nid, "layer": layer, "fact": n["fact"], "identity_slot": n.get("identity_slot"), "tier": n["tier"], "kind": n.get("kind"), "rel_type": n.get("rel_type"),
                                 "children": [{"node_id": d, "fact": by_id[d]["fact"], "fact_id": (v or {}).get("candidate_id")} for d, v in kids if d in by_id],
                                 "child_fact_ids": child_ids}
        cl["sg"]["unit"] = nid
        spec = (ST.spec_for(cap, level) if cap in ("plan_gap_filling", "goal_conditioned_planning") else SG.spec_for(cap, level, cl, contract=contract)); spec["phase"] = "search"
        if n.get("kind") in ("gap", "remaining"): cl["sg"]["tree_node"]["l4_kind"] = n["kind"]; cl["sg"]["tree_node"]["hidden_sub_goal"] = n.get("hidden_sub_goal")
        pair = next(((o, c) for o, c in state.skills if c == cap), (cap, cap))
        row = None
        for _try in range(1 + int(contract.get("unit_retries", 0))):
            row = run_turn(store, state, contract, run_dir, pair, None, [cl], "DIAGNOSIS", mock=mock, difficulty=spec)
            if row.get("sg") is not None: row["sg"]["unit"] = nid; row["sg"]["tree_node"] = nid
            if state.history: state.history[-1] = row
            state.save()
            log(run_dir, f"  {layer} tree22 {nid:12s} {cap:28s} L{level} -> {row['verdict']}" + (f" (retry {_try+1})" if _try else ""))
            if row["verdict"] in ("correct", "wrong"): break
        if row and row["verdict"] in ("correct", "wrong"):
            m[nid] = {"status": "ok", "candidate_id": row["candidate_id"], "verdict": row["verdict"], "turn": row["turn"], "skill": cap, "layer": layer, "fact": n["fact"], "children": child_ids, "tier": n.get("tier"), "identity_slot": n.get("identity_slot")}
        else:
            m[nid] = {"status": "failed", "last_verdict": row["verdict"] if row else None, "skill": cap, "layer": layer, "fact": n["fact"]}
        save_map(run_dir, m)
        if state.solver_errors >= contract["max_solver_errors"]: state.stop_reason = "STOP_SOLVER_ERRORS"; state.phase = "DONE"; state.save(); return
    for o, c in state.skills:
        st = state.stair[c]; st["stop"] = st.get("stop") or "tree"; st["phase"] = "done"
    ok = sum(1 for n in mine if (m.get(n["node_id"]) or {}).get("status") == "ok")
    state.stop_reason = f"TREE_COMPLETE {ok}/{len(mine)} nodes"; state.phase = "DONE"; state.save()
    log(run_dir, f"{layer}: TREE_COMPLETE {ok}/{len(mine)} nodes scored")
