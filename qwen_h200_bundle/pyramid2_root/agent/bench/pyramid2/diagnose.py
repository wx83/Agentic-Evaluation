#!/usr/bin/env python3
"""题树归因(10-22):对一个 self run(tree run 或 propagate run)里 L4 答错的每个决策点,按层从低到高对答错的后代节点做 repair:
该节点换成参考答案,其到根的祖先链按 self 规则(其它子节点仍用本 run 自己的答案)自底向上重答 ×reps;第一个能让根答对的节点 = 归因(层 / skill)。
后代全对而根错 = 规划失败(planning);所有 repair 都救不回 = unexplained。结果 runs/<self>/diagnosis.json + repairs.jsonl。
  python3 diagnose.py --self p2_egoplan_1022_tree_flash [--reps 3]"""
import json, argparse, time
from pathlib import Path
import p2config as P
from store import Store, read_jsonl
import intervene as IV

LAYERS = ["L1", "L2", "L3", "L4"]


def path_to_root(nid, rows):
    """nid 的祖先链(父 → 祖父 → … → 根),树里每个节点只有一个父。"""
    out = []
    cur = nid
    while True:
        par = next((r["tree"]["node_id"] for r in rows.values() if cur in (r["tree"].get("depends_on") or [])), None)
        if par is None: break
        out.append(par); cur = par
    return out


def repair(root, node, rows, cands, contract, store, out_dir, reps, log):
    """返回 (root_correct, steps):重答 node 的祖先链;每个祖先的 history = 其子节点,node → gold,已重答的祖先 → 新答案,其它 → self 原答案。"""
    new_ans = {node["tree"]["node_id"]: ("gold", None)}
    steps = []
    for aid in path_to_root(node["tree"]["node_id"], rows):
        a = rows[aid]; items = []
        for c in IV.children_of(a, rows):
            cid = c["tree"]["node_id"]
            if cid in new_ans:
                mode, parsed = new_ans[cid]
                items.append((c, "gold") if mode == "gold" else (c, f"letters:{parsed}"))
            else:
                items.append((c, "self"))
        res = IV.solve(cands[a["candidate_id"]], contract, store, out_dir, IV.render(items), reps)
        p = res["parsed"]; letters = p if isinstance(p, str) else ", ".join(p or [])
        new_ans[aid] = ("new", letters)
        steps.append({"node_id": aid, "layer": a["layer"], "verdict": res["verdict"], "votes": res["votes"], "self_verdict": a["verdict"]})
        log(f"    repair {node['tree']['node_id']} -> re-answer {aid} ({a['layer']}): {a['verdict']} -> {res['verdict']} votes={res['votes']}")
        with open(out_dir / "repairs.jsonl", "a") as f:
            f.write(json.dumps({"root": root["tree"]["node_id"], "repaired": node["tree"]["node_id"], "reanswered": aid, "layer": a["layer"], **res, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}, ensure_ascii=False) + "\n")
    return (steps[-1]["verdict"] == "correct") if steps else False, steps


def run(self_rid, reps=3, force=False):
    rd, contract, cands, rows = IV.load_run(self_rid)
    if (rd / "diagnosis.json").exists() and not force:
        print(f"{rd / 'diagnosis.json'} exists; skip (use --force to redo)"); return
    store = Store(); out_dir = rd / "diagnosis"; out_dir.mkdir(exist_ok=True)
    log = lambda m: print(m, flush=True)
    roots = sorted([r for r in rows.values() if r["layer"] == "L4"], key=lambda r: (r.get("sample_id"), r["tree"]["cutoff_step"]))
    out = []
    for root in roots:
        rid_ = root["tree"]["node_id"]; des = [rows[d] for d in IV.descendants_of(rid_, rows)]
        rec = {"root": rid_, "sample_id": root.get("sample_id"), "cutoff_step": root["tree"]["cutoff_step"], "root_verdict": root["verdict"],
               "n_descendants": len(des), "wrong_descendants": [d["tree"]["node_id"] for d in des if d["verdict"] == "wrong"], "attribution": None, "repairs": []}
        if root["verdict"] == "correct":
            rec["attribution"] = {"kind": "success"}
        elif not rec["wrong_descendants"]:
            rec["attribution"] = {"kind": "planning", "note": "all descendants correct, root wrong"}
        else:
            wrong = sorted([d for d in des if d["verdict"] == "wrong"], key=lambda d: (LAYERS.index(d["layer"]), d["turn"]))
            for d in wrong:
                ok, steps = repair(root, d, rows, cands, contract, store, out_dir, reps, log)
                rec["repairs"].append({"node_id": d["tree"]["node_id"], "layer": d["layer"], "skill": d["capability_skill"], "root_fixed": ok, "steps": steps})
                if ok:
                    rec["attribution"] = {"kind": "bottleneck", "node_id": d["tree"]["node_id"], "layer": d["layer"], "skill": d["capability_skill"]}; break
            if rec["attribution"] is None:
                rec["attribution"] = {"kind": "unexplained", "note": "no single repair fixed the root"}
        log(f"{rid_} [{root.get('sample_id','')[-10:]}] root {root['verdict']} wrong_desc {len(rec['wrong_descendants'])} -> {rec['attribution']}")
        out.append(rec)
    (rd / "diagnosis.json").write_text(json.dumps({"self_run": self_rid, "reps": reps, "decision_points": out}, indent=1, ensure_ascii=False))
    print("->", rd / "diagnosis.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--self", dest="self_rid", required=True); ap.add_argument("--reps", type=int, default=3); ap.add_argument("--force", action="store_true")
    a = ap.parse_args(); run(a.self_rid, reps=a.reps, force=a.force)
