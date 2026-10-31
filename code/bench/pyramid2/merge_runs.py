#!/usr/bin/env python3
"""把 per-task run(<prefix>__00 … __09)合并成一个汇总 run 目录 <prefix>(history / candidates / scope / summary / usage 拼接;turn 加 task 偏移 100*k 保持唯一),
供 daily_1023.py / trajectory_eval.py / build.py 直接读。用法:python3 merge_runs.py p2_hdepicE_1023t_g4_self [more prefixes]"""
import json, sys, shutil, collections
from pathlib import Path
import p2config as P
from store import read_jsonl, write_jsonl
LAYERS = ["L1", "L2", "L3", "L4"]


def merge(prefix):
    parts = sorted(p for p in P.RUNS.glob(prefix + "__*") if (p / "run_contract.json").exists())
    dst = P.RUNS / prefix; dst.mkdir(exist_ok=True)
    for sub in ("scope", "contexts"): (dst / sub).mkdir(exist_ok=True)
    c0 = json.loads((parts[0] / "run_contract.json").read_text()); c0["run_id"] = prefix; c0["videos"] = sorted({v for p in parts for v in json.loads((p / "run_contract.json").read_text())["videos"]}); c0["merged_from"] = [p.name for p in parts]
    (dst / "run_contract.json").write_text(json.dumps(c0, indent=1, ensure_ascii=False))
    cands, usage, log = [], [], []
    for k, p in enumerate(parts):
        off = 100 * k
        cands += read_jsonl(p / "candidates.jsonl") if (p / "candidates.jsonl").exists() else []
        usage += read_jsonl(p / "usage.jsonl") if (p / "usage.jsonl").exists() else []
        if (p / "run.log").exists(): log.append(f"##### {p.name}\n" + (p / "run.log").read_text())
        for f in (p / "scope").glob("*.json"): shutil.copy(f, dst / "scope" / f.name)
    write_jsonl(dst / "candidates.jsonl", cands); write_jsonl(dst / "usage.jsonl", usage); (dst / "run.log").write_text("\n".join(log))
    for L in LAYERS:
        hist, hyps, summ = [], [], {"layer": L, "by_skill": {}, "stop_reason": "MERGED", "confirmation": {"results": {}, "slots": []}, "scored_items": 0, "correct": 0, "merged_from": [p.name for p in parts]}
        for k, p in enumerate(parts):
            off = 100 * k
            for h in (read_jsonl(p / L / "history.jsonl") if (p / L / "history.jsonl").exists() else []):
                h = dict(h); h["turn"] = h["turn"] + off; h["task_run"] = p.name; hist.append(h)
            for h in (read_jsonl(p / L / "hypotheses.jsonl") if (p / L / "hypotheses.jsonl").exists() else []):
                h = dict(h); h["task_run"] = p.name; hyps.append(h)
            sp = p / L / "summary.json"
            if sp.exists():
                s = json.loads(sp.read_text())
                for sk, v in (s.get("by_skill") or {}).items():
                    agg = summ["by_skill"].setdefault(sk, {"scored": 0, "correct": 0, "verdicts": collections.Counter()})
                    agg["scored"] += v.get("scored") or 0; agg["correct"] += v.get("correct") or 0; agg["verdicts"][v.get("verdict")] += 1
                for sk, r in ((s.get("confirmation") or {}).get("results") or {}).items():
                    a = summ["confirmation"]["results"].setdefault(sk, {"n": 0, "correct": 0, "results": collections.Counter()})
                    a["n"] += r.get("n") or 0; a["correct"] += r.get("correct") or 0; a["results"][r.get("result")] += 1
        if not hist: continue
        (dst / L).mkdir(exist_ok=True); write_jsonl(dst / L / "history.jsonl", hist); write_jsonl(dst / L / "hypotheses.jsonl", hyps)
        for sk, agg in summ["by_skill"].items():
            agg["verdict"] = " / ".join(f"{v}×{n}" for v, n in agg["verdicts"].most_common()); agg["verdicts"] = dict(agg["verdicts"])
        for sk, a in summ["confirmation"]["results"].items():
            a["result"] = " / ".join(f"{v}×{n}" for v, n in a["results"].most_common()); a["results"] = dict(a["results"])
        sc = [h for h in hist if h.get("verdict") in ("correct", "wrong")]; summ["scored_items"] = len(sc); summ["correct"] = sum(h["verdict"] == "correct" for h in sc)
        (dst / L / "summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print(prefix, "<-", len(parts), "task runs;", {L: sum(1 for h in read_jsonl(dst / L / "history.jsonl") if h.get("verdict") in ("correct", "wrong")) for L in LAYERS if (dst / L / "history.jsonl").exists()})


if __name__ == "__main__":
    for pre in sys.argv[1:]: merge(pre)
