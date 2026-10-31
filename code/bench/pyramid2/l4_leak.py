#!/usr/bin/env python3
"""L4 泄漏检查(10-14 用户问「scope planner 看到 goal + gold plan 算不算作弊」):
 (1) 文字重叠:每道计分题的 Solver 可见文字(题面 / 选项 / history)里 goal 词、gold 词、scope ask 词、最后一步词的命中;
 (2) 盲测:Solver 不看视频,只看文字(无 history / self history / gold history),每题 3 次取多数;
 (3) 无 scope 消融:同 cluster 关掉 scope 让 Examiner 重出 L4 题,再让 Solver(看视频 + self history)作答。
输出 runs/p2_egoplan_1014_leak/l4_leak.json;site 的「L4 leak check」tab 读它。"""
import json, re, time, collections, sys
from pathlib import Path
import p2config as P
from store import Store, read_jsonl
import retrieve, capmap, context as CX, examiner as EX, solver as SV, grade as GR, chain, controller as CT, prompts
import prompt as BP

SELF, GOLD, OUT_RID = "p2_egoplan_1014_self", "p2_egoplan_1014_gold", "p2_egoplan_1014_leak"
OUT = P.RUNS / OUT_RID; OUT.mkdir(parents=True, exist_ok=True)
STOP = EX._STOP | {"the", "camera", "wearer", "clip", "video", "what", "which", "should", "next", "take", "action", "actions", "step", "steps",
                   "task", "they", "doing", "person", "about", "seconds", "into", "after", "before", "most", "following", "continue",
                   "given", "logical", "correct", "progress", "shown", "current", "observation", "end", "ends", "based", "far", "person",
                   "immediately", "does", "perform", "with", "that", "this", "when", "from", "specific", "list", "finish", "appropriate"}


def words(s):
    return {EX._stem(w) for w in re.findall(r"[a-z]+", (s or "").lower()) if w not in STOP and len(w) > 2}


def overlap(src, dst):
    a, b = words(src), words(dst)
    return sorted(a & b), len(a)


def text_metrics(h, s, scope_entry):
    q = h.get("question") or ""; opts = " ".join(h.get("options") or [])
    prompt = h.get("solver_prompt") or ""
    i = prompt.find("Earlier questions"); j = prompt.find("\nQuestion:")
    hist = prompt[i:j] if i >= 0 and j > i else ""
    gold = s["next_action"]["text"]; last = s["steps"][-1]["text"]
    m = {}
    for name, src in (("goal", s["goal"]), ("gold_next", gold), ("last_step", last), ("scope_ask", (scope_entry or {}).get("ask") or ""), ("scope_target", (scope_entry or {}).get("target") or "")):
        for where, dst in (("question", q), ("options", opts), ("history", hist)):
            hit, n = overlap(src, dst)
            m[f"{name}_in_{where}"] = {"hit": hit, "n_src": n}
    m["goal_phrase_in_solver_text"] = s["goal"].lower() in prompt.lower()
    m["gold_phrase_in_question"] = gold.lower() in q.lower()
    m["gold_phrase_in_history"] = gold.lower() in hist.lower()
    m["last_step_phrase_in_question"] = last.lower() in q.lower()
    return m


def ask_text(text, model, run_dir, meta, max_tokens=512):
    import nv_gemini as NV, logging
    logging.getLogger("google_genai").setLevel(logging.ERROR)
    from google.genai import types
    kw = dict(temperature=0.0, top_p=0.001, max_output_tokens=max_tokens, thinking_config=types.ThinkingConfig(thinking_budget=0))
    t0 = time.time(); err = None; out = None; u = {}
    for attempt in range(5):
        try:
            r = NV.client().models.generate_content(model=NV.resolve_model(model), contents=[text], config=types.GenerateContentConfig(**kw))
            um = getattr(r, "usage_metadata", None); g = lambda k: getattr(um, k, None) if um is not None else None
            u = {"tok_in": g("prompt_token_count"), "tok_out": g("candidates_token_count"), "tok_think": g("thoughts_token_count")}
            out = r.text; err = None
            if out: break
            err = "empty"
        except Exception as e_:
            err = f"{type(e_).__name__}: {str(e_)[:200]}"
            if "429" in err or "RateLimit" in err: time.sleep(75); continue
            time.sleep(2)
    EX._log(run_dir, "solver_blind", {"model": model, "latency_sec": round(time.time() - t0, 2), "error": err, **u, **meta})
    if err: raise RuntimeError(err)
    return out


def blind_prompt(h, hist_text):
    pre = "You cannot see any video for this item. Answer from the text alone; if the text does not determine the answer, make your best guess.\n\n"
    if hist_text: pre += hist_text.rstrip("\n") + "\n\n"
    return pre + BP.build(h["question"], h["options"])


def history_text(run_dir, h, mode, cand):
    hh = chain.history_for(run_dir, "L4", h["sample_id"], mode, cap=12, exclude_same_answer=True, current=cand)
    return hh["text"], hh["n"]


def run_blind(rows, cands, contract, reps=3):
    res = {}
    for h in rows:
        if h["format"] != "single_choice": continue
        cand = cands[h["candidate_id"]]; ref = str(h["reference"]).strip().upper()[:1]
        per = {}
        for mode in ("none", "self", "gold"):
            ht, n = ("", 0) if mode == "none" else history_text(P.RUNS / SELF, h, mode, cand)
            votes = []
            for k in range(reps):
                raw = ask_text(blind_prompt(h, ht), contract["solver_model"], OUT, {"turn": h["turn"], "mode": mode, "rep": k})
                idx = BP.score_choice(raw, h["options"]); votes.append("ABCD"[idx] if idx is not None else None)
            maj = collections.Counter(v for v in votes if v).most_common(1)
            per[mode] = {"votes": votes, "majority": maj[0][0] if maj else None, "correct": bool(maj) and maj[0][0] == ref, "n_correct": sum(v == ref for v in votes), "history_n": n}
            print(f"  blind L4-{h['turn']:03d} {mode:4s} votes={votes} ref={ref} -> {'OK' if per[mode]['correct'] else 'x'}", flush=True)
        res[h["candidate_id"]] = per
    return res


def run_noscope(rows, cands, contract, store):
    """同 cluster、scope_mode=off 重出题 → Solver(视频 + self history)作答。"""
    res = {}
    c2 = dict(contract); c2["scope_mode"] = "off"; c2["run_id"] = OUT_RID
    import cli
    orig, cap = cli._skill_pair(store, "L4", "goal_conditioned_planning")
    for h in rows:
        cl = next((c for c in retrieve.clusters(store, h["video_id"], cap, seed=contract["seed"], max_clusters=40) if c["evidence_cluster_id"] == h["evidence_cluster_id"]), None)
        if cl is None:
            res[h["candidate_id"]] = {"error": "cluster not found"}; continue
        mapping = capmap.resolve(store.capmap, orig, cl["core"])
        state = {"history": [], "hypotheses": [], "coverage": {}, "remaining_budget": {"scored_items": 9, "turns": 12}}
        seeds = CT.seed_items_for(store, cap, [cl])
        ctx = CX.build_context(c2, "L4", (orig, cap), mapping, [cl], store, state, phase="DIAGNOSIS", hypothesis=None, seed_items=seeds, scope_by_task=None)
        assert "skill_scope" not in ctx
        out, u, errs = None, {}, []
        for attempt in range(2):
            ctx_try = dict(ctx)
            if errs: ctx_try["item_validation_result"] = {"previous_output_rejected": True, "errors": errs}
            try:
                out, u = EX.propose(ctx_try, "L4", c2, run_dir=OUT)
            except Exception as e_:
                errs = [f"examiner_call_failed: {str(e_)[:160]}"]; continue
            errs = EX.check_output(out, ctx, store)
            if not errs: break
        if out is None or out.get("action") != "PROPOSE_DIAGNOSTIC":
            res[h["candidate_id"]] = {"error": "; ".join(errs)[:300], "action": (out or {}).get("action")}; print(f"  noscope L4-{h['turn']:03d} FAILED {errs[:2]}", flush=True); continue
        cand = EX.make_candidate(out, ctx, c2, "L4", h["turn"], u, prompts.prompt_hash("L4", EX._prompts(c2)), cl, errs)
        with open(OUT / "candidates.jsonl", "a") as f: f.write(json.dumps(cand, ensure_ascii=False) + "\n")
        pub, pri = out["public"], out["private"]
        ht, n = history_text(P.RUNS / SELF, h, "self", cand)
        try:
            sol = SV.solve(cand, c2, store, run_dir=OUT, history_text=ht)
            gr = GR.grade(cand, sol, c2, run_dir=OUT)
            verdict, parsed, reason = gr["verdict"], gr["parsed"], gr.get("reason")
        except Exception as e_:
            verdict, parsed, reason = "env_failure", None, str(e_)[:160]
        res[h["candidate_id"]] = {"question": pub["question"], "options": pub.get("options"), "format": pub["format"], "reference": pri["proposed_reference_answer"],
                                  "check_errors": errs, "parsed": parsed, "verdict": verdict, "judge_reason": reason, "history_n": n,
                                  "selection_reason": out.get("selection_reason"), "solver_prompt": sol["prompt"] if verdict != "env_failure" else None,
                                  "media": sol["media"] if verdict != "env_failure" else None}
        print(f"  noscope L4-{h['turn']:03d} fmt={pub['format']} ref={pri['proposed_reference_answer']!s:.20} -> {verdict} | Q: {pub['question'][:100]}", flush=True)
    return res


def main(do_blind=True, do_noscope=True):
    store = Store()
    contract = json.loads((P.RUNS / SELF / "run_contract.json").read_text())
    samples = {s["sample_id"]: s for s in json.loads((P.DATA / "egoplan_samples.json").read_text())["samples"]}
    scopes = {}
    for f in (P.RUNS / SELF / "scope").glob("*.json"):
        r = json.loads(f.read_text()); scopes[r["task_id"]] = r["scope"]
    cands = {c["candidate_id"]: c for c in read_jsonl(P.RUNS / SELF / "candidates.jsonl")}
    gold_rows = {h["candidate_id"]: h for h in read_jsonl(P.RUNS / GOLD / "L4" / "history.jsonl")}
    rows = [h for h in read_jsonl(P.RUNS / SELF / "L4" / "history.jsonl") if h["verdict"] in ("correct", "wrong")]
    # (1) 文字重叠:全部四层
    metrics = {}
    for L in ("L1", "L2", "L3", "L4"):
        for h in read_jsonl(P.RUNS / SELF / L / "history.jsonl"):
            if h["verdict"] not in ("correct", "wrong"): continue
            s = samples[h["sample_id"]]
            ents = (scopes.get(h["sample_id"]) or {}).get("layers", {}).get(L, {}).get(h["capability_skill"], [])
            ent = next((x for x in ents if x["scope_id"] == h.get("scope_id")), None)
            metrics[h["candidate_id"]] = {"layer": L, "turn": h["turn"], "skill": h["capability_skill"], "scope_entry": ent, **text_metrics(h, s, ent)}
    out = {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "metrics": metrics, "l4_items": [h["candidate_id"] for h in rows],
           "l4_scope_entries": {tid: (sc.get("layers", {}).get("L4", {}).get("goal_conditioned_planning") or []) for tid, sc in scopes.items() if sc}}
    (OUT / "l4_leak.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("text metrics done", flush=True)
    if do_blind:
        out["blind"] = run_blind(rows, cands, contract); (OUT / "l4_leak.json").write_text(json.dumps(out, indent=1, ensure_ascii=False)); print("blind done", flush=True)
    if do_noscope:
        out["noscope"] = run_noscope(rows, cands, contract, store); (OUT / "l4_leak.json").write_text(json.dumps(out, indent=1, ensure_ascii=False)); print("noscope done", flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main(do_blind="--no-blind" not in sys.argv, do_noscope="--no-noscope" not in sys.argv)
