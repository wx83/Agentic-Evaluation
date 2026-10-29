"""题树 run(10-22):决策点按 cutoff 升序 → 树内自底向上(L1→L2→L3→L4)逐节点出题 + Solver 作答;每节点 cluster 固定为映射到的那个;
无追问、无确认(诊断靠干预臂 + 多次重答)。复用 controller.run_turn(node=...)、LayerState、write_summary。
  python3 cli.py tree-run --contract <c.json> [--mock all_correct]"""
import json
import p2config as P
import controller as CT, scope as SC, tree as TR, retrieve, chain
from store import Store


def _children_view(node, states):
    out = []
    for cid in node.get("depends_on") or []:
        for st in states.values():
            h = next((h for h in st.history if h.get("scope_id") == cid and h["verdict"] in ("correct", "wrong")), None)
            if h:
                out.append({"node_id": cid, "layer": h["layer"], "skill": h["capability_skill"], "question": h.get("question"), "options": h.get("options"),
                            "reference_answer": chain.answer_text(h, "gold")}); break
    return out


def run(contract, levels=None, mock=None):
    run_dir = P.RUNS / contract["run_id"]; run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_contract.json").write_text(json.dumps(contract, indent=1, ensure_ascii=False))
    store = Store(); mk = None
    if mock:
        from mock import Mock
        mk = Mock(mock, store)
    CT._SCOPE_BY_TASK = None
    retrieve.EGOPLAN_L4_INTERMEDIATE = bool(contract.get("l4_intermediate_cutoffs", True))
    states = {}
    for L in TR.LAYERS:
        st = CT.LayerState(run_dir, L, contract); st.skills = CT.active_skills(store, L, contract); CT.build_pools(store, st, contract); states[L] = st
    pools = {cap: st.pools[cap] for st in states.values() for o, cap in st.skills}
    tids = SC.task_ids_for(store, contract)
    trees = TR.ensure(contract, store, pools, run_dir=run_dir, task_ids=tids, mock=mk)
    n_dp = sum(len(v) for v in trees.values()); n_nodes = sum(len(r["nodes"] or []) for v in trees.values() for r in v)
    CT.log(run_dir, f"tree planner: {len(trees)} tasks, {n_dp} decision points, {n_nodes} nodes; failed {sum(1 for v in trees.values() for r in v if not r.get('nodes'))}")
    done = {h.get("scope_id") for st in states.values() for h in st.history if h.get("scope_id") and h["verdict"] in ("correct", "wrong")}   # item_invalid 的节点续跑时重出
    unmapped = []
    for tid in tids:
        for rec in sorted(trees.get(tid, []), key=lambda r: r["dp"]["cutoff"]):
            if not rec.get("nodes"): continue
            dp = rec["dp"]
            for node in TR.order(rec["nodes"]):
                if node["node_id"] in done: continue
                cl = TR.node_cluster(node, pools, tid, dp)
                if cl is None:
                    unmapped.append((tid, node["node_id"], node["skill"], node["event_refs"])); CT.log(run_dir, f"  unmapped node {node['node_id']} {node['skill']} refs {node['event_refs']}"); continue
                st = states[node["layer"]]; pair = next(((o, c) for o, c in st.skills if c == node["skill"]), None)
                if pair is None:
                    CT.log(run_dir, f"  skill {node['skill']} not active in {node['layer']}; node {node['node_id']} skipped"); continue
                nv = {k: node[k] for k in ("node_id", "layer", "skill", "event_refs", "ask", "avoid", "why_needed", "depends_on")}
                nv.update(task_id=tid, cutoff_step=dp["cutoff_step"], dp_cutoff=dp["cutoff"], children=_children_view(node, states))
                row = CT.run_turn(store, st, contract, run_dir, pair, None, [cl], "DIAGNOSIS", mock=mk, node=nv)
                done.add(node["node_id"])
                CT.log(run_dir, f"  {node['layer']} t{st.turn:02d} {node['node_id']:14s} {node['skill']:32s} {row['format'] or '-':13s} -> {row['verdict']} (children {len(nv['children'])})")
    for L, st in states.items():
        st.phase = "DONE"; st.stop_reason = "TREE_COMPLETE"; st.save(); CT.write_summary(st, contract)
    (run_dir / "trees.json").write_text(json.dumps({"tasks": tids, "trees": {t: [{"dp": r["dp"], "nodes": r["nodes"], "status": r["status"], "warnings": r["warnings"]} for r in v] for t, v in trees.items()},
                                                    "unmapped": unmapped}, indent=1, ensure_ascii=False))
    CT.log(run_dir, f"tree run finished; unmapped nodes {len(unmapped)}")
