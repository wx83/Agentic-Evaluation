#!/usr/bin/env python3
"""题树干预臂(10-22):对一个 tree run(self 臂)的每个非叶节点,用同一道题换 history 重答:
  gold     子节点 = 参考答案
  none     无 history(只看 clip)
  corrupt  子节点全 gold,只把边 e 的子节点换成一个错选项(每条边一行)
  control  子节点全 gold,再塞一条同任务别的决策点的题(错答案)
每题 ×reps 取多数;结果 runs/<self>/intervene/<arm>.jsonl(按 (node_id, edge) 续跑)。
  python3 intervene.py --self p2_egoplan_1022_tree_flash --arms gold,none,corrupt,control [--reps 3]"""
import json, argparse, random, time, collections
from pathlib import Path
import p2config as P
from store import Store, read_jsonl
import chain

LAYERS = ["L1", "L2", "L3", "L4"]


def load_run(rid):
    rd = P.RUNS / rid
    contract = json.loads((rd / "run_contract.json").read_text())
    cands = {c["candidate_id"]: c for c in read_jsonl(rd / "candidates.jsonl")} if (rd / "candidates.jsonl").exists() else {}
    if contract.get("replay_of"):                                  # propagate / replay run 没有自己的 candidates,题目来自源 run
        for c in read_jsonl(P.RUNS / contract["replay_of"] / "candidates.jsonl"):
            cands.setdefault(c["candidate_id"], c)
    rows = {}
    for L in LAYERS:
        for h in read_jsonl(rd / L / "history.jsonl"):
            if h.get("tree") and h["verdict"] in ("correct", "wrong"):
                rows[h["tree"]["node_id"]] = h
    return rd, contract, cands, rows


def as_answer_row(row, letters=None, mode="gold"):
    """渲染用的行副本:mode gold → parsed = 参考答案;letters 给了就用它(干预);mode self → 原样。"""
    r = dict(row)
    if mode == "gold" or letters is not None:
        ref = letters if letters is not None else r.get("reference")
        if r.get("format") == "single_choice":
            r["parsed"] = str(ref).strip().upper()[:1]
        elif r.get("format") == "multi_select":
            r["parsed"] = sorted(set(__import__("re").findall(r"[A-E]", str(ref).upper())))
        else:
            r["parsed"] = str(ref)
    return r


def render(items):
    """items = [(row, mode|'letters:XX')]:统一渲染成 Solver 看到的 history 文字(与 chain.render 同格式)。"""
    rows = []
    for row, mode in items:
        if isinstance(mode, str) and mode.startswith("letters:"):
            rows.append(as_answer_row(row, letters=mode.split(":", 1)[1]))
        else:
            rows.append(as_answer_row(row, mode=mode))
    rows.sort(key=lambda h: (LAYERS.index(h["layer"]), h["turn"]))
    return chain.render(rows, "self") if rows else None


def children_of(row, rows):
    return [rows[c] for c in (row["tree"].get("depends_on") or []) if c in rows]


def ancestors_of(nid, rows):
    out = []
    for r in rows.values():
        if nid in (r["tree"].get("depends_on") or []): out.append(r["tree"]["node_id"]); out += ancestors_of(r["tree"]["node_id"], rows)
    return out


def descendants_of(nid, rows):
    out = []
    for c in (rows[nid]["tree"].get("depends_on") or []):
        if c in rows: out.append(c); out += descendants_of(c, rows)
    return out


def solve(cand, contract, store, run_dir, hist_text, reps, blind=False):
    sol, gr, rr = chain.solve_reps(cand, contract, store, run_dir, hist_text, reps, blind=blind)
    return {"verdict": gr["verdict"], "parsed": gr["parsed"], "score": gr["score"], "raw": sol["raw"], "reps": rr, "prompt": sol["prompt"],
            "votes": [str(x.get("parsed") or "").strip().upper()[:1] for x in rr] if cand["output"]["public"].get("format") == "single_choice" else None}


def control_row(row, rows, rng):
    """同任务、别的决策点、不是本节点祖先 / 后代的计分题;优先最低层。"""
    anc = set(ancestors_of(row["tree"]["node_id"], rows)); des = set(descendants_of(row["tree"]["node_id"], rows))
    pool = [r for r in rows.values() if r.get("sample_id") == row.get("sample_id") and r["tree"]["cutoff_step"] != row["tree"]["cutoff_step"]
            and r["tree"]["node_id"] not in anc | des | {row["tree"]["node_id"]} and LAYERS.index(r["layer"]) < LAYERS.index(row["layer"])]
    if not pool: return None
    pool.sort(key=lambda r: (LAYERS.index(r["layer"]), r["turn"]))
    return rng.choice(pool[:4])


def run(self_rid, arms, reps=3, limit=None):
    rd, contract, cands, rows = load_run(self_rid)
    store = Store(); out_dir = rd / "intervene"; out_dir.mkdir(exist_ok=True)
    rng = random.Random(f"{self_rid}|intervene")
    nonleaf = [r for r in rows.values() if children_of(r, rows)]
    nonleaf.sort(key=lambda r: (LAYERS.index(r["layer"]), r["turn"]))
    if limit: nonleaf = nonleaf[:limit]
    for arm in arms:
        fp = out_dir / f"{arm}.jsonl"
        done = {(x["node_id"], x.get("edge")) for x in read_jsonl(fp)} if fp.exists() else set()
        n_new = 0
        for r in nonleaf:
            nid = r["tree"]["node_id"]; cand = cands[r["candidate_id"]]; ch = children_of(r, rows)
            jobs = []
            if arm == "gold": jobs = [(None, [(c, "gold") for c in ch])]
            elif arm == "none": jobs = [(None, [])]
            elif arm == "corrupt":
                for c in ch:
                    wl = chain.wrong_option(c, rng)
                    jobs.append((c["tree"]["node_id"], [(x, "gold") if x is not c else (x, f"letters:{wl}") for x in ch]))
            elif arm == "control":
                cr = control_row(r, rows, rng)
                if cr is None: continue
                jobs = [(f"ctrl:{cr['tree']['node_id']}", [(c, "gold") for c in ch] + [(cr, f"letters:{chain.wrong_option(cr, rng)}")])]
            for edge, items in jobs:
                if (nid, edge) in done: continue
                hist = render(items)
                try:
                    res = solve(cand, contract, store, out_dir, hist, reps)
                except Exception as e:
                    print(f"  {arm} {nid} {edge}: solver error {str(e)[:120]}"); continue
                rec = {"arm": arm, "node_id": nid, "edge": edge, "layer": r["layer"], "skill": r["capability_skill"], "sample_id": r.get("sample_id"),
                       "cutoff_step": r["tree"]["cutoff_step"], "candidate_id": r["candidate_id"], "format": r.get("format"), "reference": r.get("reference"),
                       "self_verdict": r["verdict"], "history_n": len(items), "history_text": hist, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **res}
                with open(fp, "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                done.add((nid, edge)); n_new += 1
                print(f"  {arm:8s} {nid:14s} edge={str(edge):22s} self={r['verdict']:7s} -> {res['verdict']} votes={res['votes']}", flush=True)
        print(f"{arm}: {n_new} new items -> {fp}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--self", dest="self_rid", required=True); ap.add_argument("--arms", default="gold,none,corrupt,control")
    ap.add_argument("--reps", type=int, default=None); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    _, contract, _, _ = load_run(a.self_rid)
    run(a.self_rid, [x.strip() for x in a.arms.split(",") if x.strip()], reps=a.reps or int(contract.get("solver_reps", 3)), limit=a.limit)


if __name__ == "__main__":
    main()
