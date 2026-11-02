"""题树 planner(10-22):每个决策点一棵依赖树(L4 根 ← L3 ← L2 ← L1,题目级依赖,允许跳层),自顶向下规划、自底向上作答。
每决策点一次 Gemini 调用(contract.tree_model,默认 examiner_model),prompt = 1022_prompts_tree.md §9;缓存 data/tree_cache/<task>.dp<K>.<hash>.json,
run 里复制到 runs/<run>/trees/。节点只引用已标注步骤 idx,时间由程序从标注取。"""
import json, hashlib, time, collections
from pathlib import Path
import p2config as P
import scope as SC

SKILLS = {k: v for k, v in SC.SKILL_DEFS.items() if k not in ("action_purpose_inference", "plan_gap_filling")}      # 8 个 A 档 skill
LAYERS = ["L1", "L2", "L3", "L4"]
CACHE = P.DATA / "tree_cache"
MAX_NODES = 9


def _prompt(contract):
    import examiner as EX
    p = EX._prompts(contract)
    if not p.get("tree"):
        raise KeyError(f"prompt file {p.get('_path')} has no '## 9.' tree section")
    return p["tree"]


def step_ints(cluster):
    return sorted(x for x in SC.cluster_steps(cluster) if isinstance(x, int))


def decision_points(pools, task_id, seg):
    """L4 pool 里该样本的每个 cluster = 一个决策点;cutoff_step K = 第一个起点 >= cutoff 的步骤 idx(中间截断),最终截断 K = n+1。"""
    steps = seg["value"].get("steps") or []; n = len(steps)
    out, seen = [], set()
    for c in sorted([c for c in pools.get("goal_conditioned_planning", []) if c.get("sample_id") == task_id], key=lambda c: c["observation_cutoff"] or 0):
        cut = c["observation_cutoff"]
        if c.get("l4_intermediate"):
            K = next((s["idx"] for s in steps if s["t0"] >= cut - 0.5), None)
            if K is None: continue
        else:
            K = n + 1
        if K in seen: continue
        seen.add(K); out.append({"cutoff_step": K, "cutoff": cut, "cluster_id": c["evidence_cluster_id"], "final": not c.get("l4_intermediate")})
    return out


def coverable(pools, task_id, K):
    cov = {}
    for sk in SKILLS:
        if sk == "goal_conditioned_planning": continue
        steps = set()
        for c in pools.get(sk, []):
            if c.get("sample_id") != task_id: continue
            if sk == "next_step_prediction":
                a = c.get("anchor_step_idx")
                if a is not None and int(a) <= K: steps.add(int(a))
            else:
                steps |= {s for s in step_ints(c) if s < K}
        cov[sk] = sorted(steps)
    return cov


def build_input(store, contract, task_id, pools, dp):
    seg, nxt = SC.task_record(store, task_id)
    if seg is None: return None
    v = seg["value"]; steps = v.get("steps") or []; K = dp["cutoff_step"]
    nxt_text = (nxt["value"].get("text") if nxt else None) if dp["final"] else next((s["text"] for s in steps if s["idx"] == K), None)
    cov = coverable(pools, task_id, K)
    return {"task_id": task_id, "goal": v.get("goal"), "scenario": v.get("scenario"),
            "steps": [{"idx": s["idx"], "text": s["text"]} for s in steps],
            "cutoff_step": K, "steps_done": [s["idx"] for s in steps if s["idx"] < K],
            "next_action": {"text": nxt_text, "is_final": dp["final"], "choices": (nxt["value"].get("choices") if (nxt and dp["final"]) else None)},
            "skills": {sk: {"layer": SKILLS[sk][0], "definition": SKILLS[sk][1], "coverable_steps": cov.get(sk, [])} for sk in SKILLS if sk != "goal_conditioned_planning"},
            "max_nodes": MAX_NODES}


def validate(tr, inp):
    """清洗:唯一 node_id;skill 在白名单且层匹配;refs ⊆ coverable 且 < K(next_step 单个 ref ≤ K;L4 = ["next"]);L1 单 ref;depends_on 指向严格更低层;
    恰好一个 L4 根;不可达节点删;≤ MAX_NODES。返回 (clean nodes, warnings) 或 (None, warnings)。"""
    warn = []
    if not isinstance(tr, dict) or not isinstance(tr.get("nodes"), list):
        return None, ["no nodes list"]
    K = inp["cutoff_step"]; cov = {sk: set(d["coverable_steps"]) for sk, d in inp["skills"].items()}
    nodes = {}
    for i, n in enumerate(tr["nodes"]):
        if not isinstance(n, dict): continue
        nid = str(n.get("node_id") or f"dp{K}-n{i}"); L = n.get("layer"); sk = n.get("skill")
        if nid in nodes: warn.append(f"{nid}: duplicate id dropped"); continue
        if L not in LAYERS or sk not in SKILLS or SKILLS[sk][0] != L: warn.append(f"{nid}: bad layer/skill {L}/{sk}"); continue
        refs = []
        for x in (n.get("event_refs") or []):
            if isinstance(x, str) and x.strip().lower() == "next": refs.append("next")
            elif isinstance(x, (int, float)) or (isinstance(x, str) and x.strip().isdigit()): refs.append(int(x))
        if L == "L4":
            refs = ["next"]
        elif sk == "next_step_prediction":                    # ref == K 与根同题(都是预测第 K 步),不允许
            refs = [r for r in refs if isinstance(r, int) and r in cov.get(sk, set()) and r < K][:1]
        else:
            refs = [r for r in refs if isinstance(r, int) and r in cov.get(sk, set()) and r < K]
            if L == "L1": refs = refs[:1]
        if not refs: warn.append(f"{nid}: no valid event_refs (coverable {sorted(cov.get(sk, []))[:12]})"); continue
        nodes[nid] = {"node_id": nid, "layer": L, "skill": sk, "event_refs": refs, "ask": str(n.get("ask") or "")[:400], "avoid": str(n.get("avoid") or "")[:300],
                      "depends_on": [str(d) for d in (n.get("depends_on") or [])], "why_needed": (str(n.get("why_needed"))[:300] if n.get("why_needed") else None)}
    roots = [n for n in nodes.values() if n["layer"] == "L4"]
    if len(roots) != 1: return None, warn + [f"need exactly one L4 root, got {len(roots)}"]
    for n in nodes.values():                       # 边只能指向严格更低层、且存在
        keep = []
        for d in n["depends_on"]:
            if d not in nodes: warn.append(f"{n['node_id']}: child {d} missing"); continue
            if LAYERS.index(nodes[d]["layer"]) >= LAYERS.index(n["layer"]): warn.append(f"{n['node_id']}: child {d} not in a lower layer"); continue
            keep.append(d)
        n["depends_on"] = keep
    reach, q = set(), [roots[0]["node_id"]]
    while q:
        x = q.pop(0)
        if x in reach: continue
        reach.add(x); q += nodes[x]["depends_on"]
    for nid in list(nodes):
        if nid not in reach: warn.append(f"{nid}: unreachable from root, dropped"); del nodes[nid]
    order = [roots[0]["node_id"]] + [nid for nid in nodes if nid != roots[0]["node_id"]]
    if len(order) > MAX_NODES:
        warn.append(f"more than {MAX_NODES} nodes, truncated"); drop = set(order[MAX_NODES:])
        for nid in drop: del nodes[nid]
        for n in nodes.values(): n["depends_on"] = [d for d in n["depends_on"] if d not in drop]
    return list(nodes.values()), warn


def mock_tree(inp):
    K = inp["cutoff_step"]; cov = {sk: d["coverable_steps"] for sk, d in inp["skills"].items()}
    nodes = [{"node_id": f"dp{K}-L4-1", "layer": "L4", "skill": "goal_conditioned_planning", "event_refs": ["next"], "ask": "mock", "avoid": "", "depends_on": [], "why_needed": None}]
    ie = [s for s in cov.get("inter_event_temporal_reasoning", []) if s < K][-2:]
    if ie:
        nodes.append({"node_id": f"dp{K}-L3-1", "layer": "L3", "skill": "inter_event_temporal_reasoning", "event_refs": ie, "ask": "mock", "avoid": "", "depends_on": [], "why_needed": "mock"}); nodes[0]["depends_on"].append(f"dp{K}-L3-1")
    ar = [s for s in cov.get("action_recognition", []) if s < K][-1:]
    if ar and ie:
        nodes.append({"node_id": f"dp{K}-L2-1", "layer": "L2", "skill": "action_recognition", "event_refs": ar, "ask": "mock", "avoid": "", "depends_on": [], "why_needed": "mock"}); nodes[1]["depends_on"].append(f"dp{K}-L2-1")
    ob = [s for s in cov.get("object_recognition", []) if s < K][-1:]
    if ob and ar and ie:
        nodes.append({"node_id": f"dp{K}-L1-1", "layer": "L1", "skill": "object_recognition", "event_refs": ob, "ask": "mock", "avoid": "", "depends_on": [], "why_needed": "mock"}); nodes[2]["depends_on"].append(f"dp{K}-L1-1")
    ns = [s for s in cov.get("next_step_prediction", []) if s < K][-1:]
    if ns:
        nodes.append({"node_id": f"dp{K}-L3-2", "layer": "L3", "skill": "next_step_prediction", "event_refs": ns, "ask": "mock", "avoid": "", "depends_on": [], "why_needed": "mock"}); nodes[0]["depends_on"].append(f"dp{K}-L3-2")
    return {"task_id": inp["task_id"], "cutoff_step": K, "nodes": nodes}


def _hash(contract, inp):
    return hashlib.sha1((_prompt(contract) + json.dumps(inp, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()[:10]


def plan_one(contract, store, task_id, dp, pools, run_dir=None, force=False, mock=None):
    import examiner as EX
    inp = build_input(store, contract, task_id, pools, dp)
    if inp is None: return None
    CACHE.mkdir(parents=True, exist_ok=True)
    h = _hash(contract, inp); K = dp["cutoff_step"]
    cp = CACHE / f"{task_id}.dp{K}.{h}{'.mock' if mock else ''}.json"
    if cp.exists() and not force:
        rec = json.loads(cp.read_text()); rec["dp"] = dp; return rec
    rec = {"task_id": task_id, "dp": dp, "prompt_hash": h, "model": "mock" if mock else contract.get("tree_model", contract["examiner_model"]),
           "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "input": inp, "nodes": None, "warnings": [], "usage": {}, "status": "failed"}
    if mock:
        rec["nodes"], rec["warnings"] = validate(mock_tree(inp), inp); rec["status"] = "ok"
    else:
        last = None
        for attempt in range(2):
            try:
                text, u = EX.call(_prompt(contract), json.dumps(inp, ensure_ascii=False), rec["model"], max_tokens=contract.get("tree_max_tokens", 8192),
                                  thinking=contract.get("tree_thinking", "default"), run_dir=run_dir, role="tree", meta={"task_id": task_id, "cutoff_step": K})
                out = EX.jparse(text)
                if isinstance(out, list): out = next((x for x in out if isinstance(x, dict)), None)
                nodes, warn = validate(out, inp)
                if nodes is None: raise ValueError("; ".join(warn))
                rec.update(nodes=nodes, warnings=warn, usage=u, status="ok", raw_len=len(text)); break
            except Exception as e:
                last = f"{type(e).__name__}: {str(e)[:200]}"; rec["warnings"].append(f"attempt {attempt + 1}: {last}")
        if rec["nodes"] is None: rec["error"] = last
    cp.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec


def prefix_of(task_id):
    return task_id[:8]


def namespace(rec, task_id):
    """node_id 只在决策点内唯一(dp5-L4-1),跨任务会撞 → 加任务前缀 <uid 前 8 位>:(新树与缓存树都在这里加,幂等)。"""
    pre = prefix_of(task_id) + ":"
    for n in rec.get("nodes") or []:
        if not n["node_id"].startswith(pre): n["node_id"] = pre + n["node_id"]
        n["depends_on"] = [d if d.startswith(pre) else pre + d for d in n.get("depends_on") or []]
    return rec


def ensure(contract, store, pools, run_dir=None, task_ids=None, force=False, mock=None):
    """返回 {task_id: [tree record per decision point]};run_dir 给了就写 runs/<run>/trees/<task>.json。"""
    out = {}
    for tid in (task_ids or SC.task_ids_for(store, contract)):
        seg, _ = SC.task_record(store, tid)
        if seg is None: continue
        recs = []
        for dp in decision_points(pools, tid, seg):
            rec = plan_one(contract, store, tid, dp, pools, run_dir=run_dir, force=force, mock=mock)
            if rec: recs.append(namespace(rec, tid))
        out[tid] = recs
        if run_dir is not None:
            d = Path(run_dir) / "trees"; d.mkdir(parents=True, exist_ok=True)
            (d / f"{tid}.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False))
    return out


def order(nodes):
    """自底向上:按层升序,同层按 node_id;depends_on 只指向更低层,所以层序即拓扑序。"""
    return sorted(nodes, key=lambda n: (LAYERS.index(n["layer"]), n["node_id"]))


def node_cluster(node, pools, task_id, dp):
    """节点 → cluster:L4 用决策点的 cluster;next_step 用 anchor_step_idx == ref;其它用覆盖步骤 ⊇ refs 的 cluster(优先锚点在 refs 里,其次窗口最短)。"""
    sk = node["skill"]; cands = [c for c in pools.get(sk, []) if c.get("sample_id") == task_id]
    if node["layer"] == "L4":
        return next((c for c in cands if c["evidence_cluster_id"] == dp["cluster_id"]), None)
    refs = [r for r in node["event_refs"] if isinstance(r, int)]
    if sk == "next_step_prediction":
        return next((c for c in cands if c.get("anchor_step_idx") is not None and int(c["anchor_step_idx"]) == refs[0]), None) if refs else None
    ok = [c for c in cands if set(refs) <= set(step_ints(c)) and (c.get("observation_cutoff") is None or c["observation_cutoff"] >= dp["cutoff"] - 0.5 or True)]
    if not ok: return None
    ok.sort(key=lambda c: (0 if (c.get("anchor_step_idx") is not None and int(c["anchor_step_idx"]) in refs) else 1, (c["window"][1] - c["window"][0])))
    return ok[0]
