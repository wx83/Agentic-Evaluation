"""runs/<run_id>/ -> report.md(dataset × layer × skill 表、轨迹表、usage 汇总)。"""
import json, collections
from pathlib import Path
import p2config as P
from store import read_jsonl


def usage_summary(run_dir):
    rows = read_jsonl(run_dir / "usage.jsonl")
    by = collections.defaultdict(lambda: {"calls": 0, "errors": 0, "tok_in": 0, "tok_out": 0, "tok_think": 0})
    for r in rows:
        d = by[r["role"]]; d["calls"] += 1; d["errors"] += bool(r.get("error"))
        for k in ("tok_in", "tok_out", "tok_think"):
            d[k] += r.get(k) or 0
    return by


def merge_candidates(run_dir):
    """runs/<id>/candidates.jsonl -> data/candidates.jsonl(按 candidate_id 去重追加)。"""
    src = run_dir / "candidates.jsonl"
    if not src.exists():
        return 0
    dst = P.DATA / "candidates.jsonl"
    have = {json.loads(l)["candidate_id"] for l in open(dst)} if dst.exists() else set()
    n = 0
    with open(dst, "a") as f:
        for l in open(src):
            c = json.loads(l)
            if c["candidate_id"] not in have:
                f.write(l if l.endswith("\n") else l + "\n"); have.add(c["candidate_id"]); n += 1
    return n


def build(run_id, write=True):
    run_dir = P.RUNS / run_id
    merge_candidates(run_dir)
    c = json.loads((run_dir / "run_contract.json").read_text())
    L = [f"# pyramid2 run `{run_id}`", "",
         f"dataset {c.get('dataset')} · videos {len(c.get('videos', []))} · examiner `{c['examiner_model']}` · solver `{c['solver_model']}` · "
         f"n_per_layer {c['n_per_layer']} · seed {c['seed']} · prompt {c['prompt_version']}", "",
         "**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。", ""]
    L += ["## 每层概览", "", "| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |", "|---|---|---|---|---|---|---|---|---|---|"]
    for layer in ("L1", "L2", "L3", "L4"):
        sp = run_dir / layer / "summary.json"
        if not sp.exists():
            L.append(f"| {layer} | (not run) | | | | | | | | |"); continue
        s = json.loads(sp.read_text())
        bv = s["by_verdict"]
        conf = s.get("confirmation") and s["confirmation"].get("results")
        conf_s = ", ".join(f"{k}:{v['result']}({v['correct']}/{v['n']})" for k, v in (conf or {}).items()) or "-"
        L.append(f"| {layer} | {s['stop_reason']} | {s['turns']} | {s['scored']} | {s['correct']} | {s['raw_acc']} | {s['cluster_dedup_acc']} | {s['followup_items']} | "
                 f"{bv.get('item_invalid', 0)}/{bv.get('evidence_unresolved', 0)} | {conf_s} |")
    L += ["", "## 每层 × skill 诊断结论", "", "| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |", "|---|---|---|---|---|---|---|---|---|"]
    for layer in ("L1", "L2", "L3", "L4"):
        sp = run_dir / layer / "summary.json"
        if not sp.exists():
            continue
        s = json.loads(sp.read_text())
        conf = (s.get("confirmation") or {}).get("results") or {}
        for sk, v in s["by_skill"].items():
            cr = conf.get(sk)
            L.append(f"| {layer} | {sk} | {v['verdict']} | {v.get('scored', '')} | {v.get('correct', '')} | {v.get('clusters', '')} | {v.get('cluster_first_correct', '')} | "
                     f"{', '.join(v.get('supported_hypotheses', [])) or '-'} | {cr['result'] + f' ({cr[chr(99)+chr(111)+chr(114)+chr(114)+chr(101)+chr(99)+chr(116)]}/{cr[chr(110)]})' if cr and cr.get('result') else (v.get('reason') or '-')} |")
    for layer in ("L1", "L2", "L3", "L4"):
        hp = run_dir / layer / "history.jsonl"
        if not hp.exists():
            continue
        L += ["", f"## {layer} 轨迹", "", "| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |", "|---|---|---|---|---|---|---|---|---|---|"]
        for h in read_jsonl(hp):
            q = (h.get("question") or "").replace("|", "/")[:110]
            L.append(f"| {h['turn']} | {h['phase'][:4]} | {h['capability_skill']} | {h.get('format') or '-'} | {h.get('strategy') or '-'} | {(h.get('tests_hypothesis') or '-').split(':')[2] if h.get('tests_hypothesis') else '-'} | "
                     f"{h['verdict']} | {str(h.get('parsed'))[:30].replace('|', '/')} | {str(h.get('reference'))[:30].replace('|', '/')} | {q} |")
    u = usage_summary(run_dir)
    L += ["", "## Gemini 用量", "", "| role | calls | errors | tok_in | tok_out | tok_think |", "|---|---|---|---|---|---|"]
    for k, d in sorted(u.items()):
        L.append(f"| {k} | {d['calls']} | {d['errors']} | {d['tok_in']} | {d['tok_out']} | {d['tok_think']} |")
    md = "\n".join(L) + "\n"
    if write:
        (run_dir / "report.md").write_text(md)
    return md
