#!/usr/bin/env python3
"""pyramid2 命令行:dry-run / propose / run / report / preflight / check-joins / audit-leaks / stats。"""
import argparse, json, sys, collections
from pathlib import Path
import p2config as P
from store import Store, read_jsonl


def load_contract(path):
    c = json.loads(Path(path).read_text())
    for k in ("run_id", "examiner_model", "solver_model", "solver_input_spec"):
        assert k in c, f"contract missing {k}"
    c.setdefault("protocol_version", P.PROTOCOL_VERSION); c.setdefault("evaluation_protocol", "OFFLINE_QA")
    c.setdefault("taxonomy_version", P.TAXONOMY_VERSION); c.setdefault("prompt_version", P.PROMPT_VERSION)
    c.setdefault("n_per_layer", 30); c.setdefault("turn_budget_per_layer", 45); c.setdefault("max_solver_errors", 15)
    c.setdefault("seed", 1012); c.setdefault("extension_registry", {"enabled_skills": []})
    c.setdefault("frozen_policy", {"confirmation": {"items_per_skill": 3, "max_items": 12, "format": "single_choice",
                                                    "pass_threshold": 0.8, "min_distinct_clusters": 3, "max_hypothesis_tests": 3}})
    return c


def default_contract(run_id="dry", **kw):
    c = {"run_id": run_id, "examiner_model": "gcp/google/gemini-3.1-pro-preview", "solver_model": "gcp/google/gemini-3.7-flash",
         "judge_model": "gcp/google/gemini-3.1-pro-preview", "examiner_thinking": "default", "examiner_max_tokens": 8192,
         "solver_thinking": "off", "phase": "DIAGNOSIS", "dataset": None, "videos": [],
         "solver_input_spec": {"modalities": ["video", "audio"], "permitted_media": [], "observation_cutoff": None,
                               "allowed_tools": [], "memory_policy": "fresh_context_per_item"},
         "coverage_targets": ["physical.objects_properties", "physical.spatial", "physical.dynamics", "task.structure"]}
    c.update(kw)
    import tempfile, json as _j
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); _j.dump(c, f); f.close()
    return load_contract(f.name)


def _skill_pair(store, layer, skill):
    import capmap
    for orig, cap in capmap.skills_for_layer(store.capmap, layer, include_retired=True):
        if cap == skill or orig == skill:
            return orig, cap
    reg = store.registry["skills"]
    if skill in reg:
        return skill, skill
    raise SystemExit(f"skill {skill} not in capability_map for {layer} nor extension registry")


def cmd_dry_run(a):
    import retrieve, capmap, context
    store = Store()
    c = load_contract(a.contract) if a.contract else default_contract()
    orig, cap = _skill_pair(store, a.layer, a.skill)
    m = store.capmap["skills"].get(orig)
    if m and m.get("lifecycle") == "retired" and not a.include_retired:
        print(f"skill {orig} lifecycle=retired; pass --include-retired to force", file=sys.stderr); sys.exit(2)
    enabled = set(c.get("extension_registry", {}).get("enabled_skills", []))
    if orig in store.registry["skills"] and orig not in enabled:
        print(json.dumps({"status": "NOT_EVALUATED", "reason": f"extension skill {orig} not enabled in run_contract"}, indent=1)); return
    cl = retrieve.clusters(store, a.video, cap, seed=c.get("seed", 0), max_clusters=a.n)
    if a.t0 is not None:
        cl = [x for x in cl if x["window"][0] >= a.t0 - 15 and x["window"][1] <= (a.t1 or 1e9) + 15] or cl[: a.n]
    if not cl:
        print(json.dumps({"status": "NO_EVIDENCE", "skill": cap, "video": a.video,
                          "excluded": retrieve.excluded_reasons(store, a.video, cap)}, indent=1, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    mapping = capmap.resolve(store.capmap, orig, cl[0]["core"]) if orig in store.capmap["skills"] else \
        {"original_skill": orig, "capability_layer": store.registry["skills"][orig]["layer"], "capability_skill": cap,
         "classification_status": "provisional", "lifecycle": "extension", "relation_operation": None}
    state = {"history": [], "hypotheses": [], "coverage": {}, "remaining_budget": {"scored_items": c.get("n_per_layer", 30), "turns": c.get("turn_budget_per_layer", 45)}}
    ctx = context.build_context(c, a.layer, (orig, cap), mapping, cl[: a.n], store, state)
    print(json.dumps(ctx, indent=1, ensure_ascii=False) if not a.summary else json.dumps(
        {"current_skill": ctx["current_skill"], "capability_mapping": ctx["capability_mapping"],
         "n_clusters": len(ctx["evidence_clusters"]), "clusters": [{k: v for k, v in x.items() if k != "already_tested"} for x in ctx["evidence_clusters"]],
         "n_evidence": len(ctx["verified_evidence"]),
         "kinds": dict(collections.Counter(e["role"] + "/" + e["kind"] for e in ctx["verified_evidence"])),
         "chars": len(json.dumps(ctx, ensure_ascii=False))}, indent=1, ensure_ascii=False))


def cmd_propose(a):
    """单轮调试:选一个 cluster 调 Examiner 一次。"""
    import retrieve, capmap, context, examiner, prompts
    store = Store(); c = load_contract(a.contract)
    orig, cap = _skill_pair(store, a.layer, a.skill)
    cl = retrieve.clusters(store, a.video, cap, seed=c["seed"], max_clusters=a.n)
    if not cl:
        raise SystemExit("no clusters")
    mapping = capmap.resolve(store.capmap, orig, cl[0]["core"]) if orig in store.capmap["skills"] else {"original_skill": orig, "capability_layer": a.layer, "capability_skill": cap, "classification_status": "provisional", "lifecycle": "extension"}
    state = {"history": [], "hypotheses": [], "coverage": {}, "remaining_budget": {"scored_items": c["n_per_layer"], "turns": c["turn_budget_per_layer"]}}
    sbt = None
    if c.get("scope_mode", "prefer") != "off":
        import scope as SC
        tids = sorted({x["sample_id"] for x in cl[: a.n] if x.get("sample_id")})
        sbt = SC.ensure(c, store, None, task_ids=tids) if tids else None
    ctx = context.build_context(c, a.layer, (orig, cap), mapping, cl[: a.n], store, state, scope_by_task=sbt)
    run_dir = P.RUNS / c["run_id"]; run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "contexts").mkdir(exist_ok=True)
    (run_dir / "contexts" / f"{a.layer}_propose_{a.skill}.json").write_text(json.dumps(ctx, indent=1, ensure_ascii=False))
    out, u = examiner.propose(ctx, a.layer, c, run_dir=run_dir, dry_run=a.dry_run)
    if a.dry_run:
        print(out); return
    errs = examiner.check_output(out, ctx, store)
    cand = examiner.make_candidate(out, ctx, c, a.layer, 0, u, prompts.prompt_hash(a.layer, examiner._prompts(c)), cl[0], errs)
    with open(P.DATA / "candidates.jsonl", "a") as f:
        f.write(json.dumps(cand, ensure_ascii=False) + "\n")
    print(json.dumps({"usage": u, "check_errors": errs, "output": out}, indent=1, ensure_ascii=False))


def cmd_preflight(a):
    import requests, nv_gemini as NV
    c = load_contract(a.contract)
    if NV.BACKEND == "google":      # Google AI Studio: no gateway model list; just probe each model below
        ids = None
    else:
        r = requests.get(f"{NV.BASE_URL}/v1/models", headers={"Authorization": f"Bearer {NV.load_key()}"}, timeout=30)
        ids = {m["id"] for m in r.json()["data"]}
    ok = True
    for k in ("examiner_model", "solver_model", "judge_model"):
        m = c.get(k)
        if not m: continue
        if (k == "examiner_model" and c.get("examiner_backend") == "qwen_http") or (k == "solver_model" and c.get("solver_backend") == "qwen_http"):   # 10-28:本地 Qwen 不在 NVIDIA 模型表里,改探活
            try:
                requests.get(c.get("qwen_url", "http://127.0.0.1:8799") + "/", timeout=5); probe = "OK(qwen_server up)"
            except Exception as e:
                probe = f"FAIL {type(e).__name__}"; ok = False
            print(f"{k:15s} {m:40s} listed=skipped probe={probe!r}"); continue
        present = True if ids is None else m in ids
        try:
            text, u = NV.gen("Reply with the single word OK.", model=m, max_tokens=512)
            probe = (text or "").strip()[:20]
        except Exception as e:
            probe = f"FAIL {type(e).__name__}: {str(e)[:120]}"; ok = False
        ok = ok and present and probe == "OK"
        print(f"{k:15s} {m:40s} listed={present} probe={probe!r}")
    print("key_id", NV.key_id(), "->", "PREFLIGHT OK" if ok else "PREFLIGHT FAILED")
    sys.exit(0 if ok else 1)


def cmd_check_joins(a):
    import glob
    store = Store(); _ = store.evidence
    tot = miss = 0
    for f in glob.glob(f"{P.SOURCES['pyramid_seed43']}/data/facts_*.json"):
        for tier, fs in json.load(open(f)).items():
            for fa in fs:
                for eid in fa.get("evidence_event_ids", []):
                    tot += 1; miss += eid not in store.by_legacy
    steps = store.by_kind["task_step"]
    unres = sum(1 for r in steps if "DERIVED_FROM_UNRESOLVED" in r["quality_flags"])
    print(f"facts refs {tot}, unresolved {miss}; task_step {len(steps)}, derived unresolved {unres}")
    sys.exit(0 if miss == 0 and unres == 0 else 1)


def cmd_audit_leaks(a):
    store = Store(); n = bad = 0
    for c in read_jsonl(P.DATA / "candidates.jsonl"):
        out = c.get("output") or {}
        if not isinstance(out.get("public"), dict):
            continue
        n += 1
        q = json.dumps(out["public"], ensure_ascii=False).lower()
        for ref in (out.get("private") or {}).get("evidence_refs") or []:
            r = store.get(ref if isinstance(ref, str) else ref.get("evidence_id"))
            lab = (r or {}).get("value", {}).get("label") if r and r["kind"] == "sound_event" else None
            # 只有标签词表式的 label(含 "/"、"collision"、"-only")原样出现才算泄漏;"click"/"water" 这类自然词不算
            if lab and ("/" in lab or "collision" in lab or "-only" in lab) and lab.lower() in q:
                bad += 1; print("label leak:", c["candidate_id"], lab)
        if "evidence_id" in q or ":narration:" in q or ":sound:" in q:
            bad += 1; print("id leak:", c["candidate_id"])
    print(f"audit-leaks: {n} candidates, {bad} leaks")


def cmd_stats(a):
    store = Store()
    cnt = collections.Counter((r["provenance"]["dataset"], r["kind"], r["verification"]["status"]) for r in store.evidence.values())
    for k, v in sorted(cnt.items()):
        print(f"{k[0]:7s} {k[1]:30s} {k[2]:18s} {v}")
    print("media:", len(store.media_rows), "items:", len(store.items))


def cmd_run(a):
    import controller
    c = load_contract(a.contract)
    if a.n: c["n_per_layer"] = a.n
    if a.run_id: c["run_id"] = a.run_id
    # 预算超参数(用户按 quota 定):每 skill 基础 cluster 数 / 答错后最多追问几次 / 确认题数 / 单个假设最多检验几次
    if a.base is not None or a.followups is not None or a.confirm is not None or a.max_hyp_tests is not None:
        c["budget_mode"] = "per_skill"
    if a.base is not None: c["per_skill_base"] = a.base
    if a.followups is not None: c["per_skill_followups"] = a.followups
    if a.confirm is not None: c["frozen_policy"]["confirmation"]["items_per_skill"] = a.confirm
    if a.max_hyp_tests is not None: c["frozen_policy"]["confirmation"]["max_hypothesis_tests"] = a.max_hyp_tests
    if a.history_mode: c["history_mode"] = None if a.history_mode == "none" else a.history_mode
    if a.scope_mode: c["scope_mode"] = a.scope_mode
    controller.run(c, levels=a.levels, mock=a.mock)


def cmd_scope(a):
    """只跑 scope planner(每样本一次 Gemini 调用,缓存);--task-id 限定;--force 重算。"""
    import scope as SC
    store = Store(); c = load_contract(a.contract)
    import store as _ST, retrieve as _RT; _ST.ACCEPT_SOURCES.update(c.get("accept_unverified_sources") or []); _RT.EGOPLAN_L4_INTERMEDIATE = bool(c.get("l4_intermediate_cutoffs"))
    for _k, _a in (("gap_sizes", "GAP_SIZES"), ("gap_head_sec", "GAP_HEAD_SEC"), ("gap_tail_sec", "GAP_TAIL_SEC"), ("gap_tail_frame_sec", "GAP_TAIL_FRAME_SEC")):
        if c.get(_k) is not None: setattr(_RT, _a, c[_k])
    tids = a.task_id or SC.task_ids_for(store, c)
    run_dir = P.RUNS / c["run_id"]; run_dir.mkdir(parents=True, exist_ok=True)
    for tid in tids:
        rec = SC.plan_one(c, store, tid, run_dir=run_dir, force=a.force, mock=("mock" if a.mock else None))
        if rec is None:
            print(tid, "NOT_FOUND"); continue
        sc = rec.get("scope") or {}
        n = {L: sum(len(v) for v in sc.get("layers", {}).get(L, {}).values()) for L in ("L1", "L2", "L3", "L4")}
        print(f"{tid}  status={rec.get('status')}  entries={n}  warnings={len(rec.get('warnings') or [])}  model={rec.get('model')}")
        if a.show and sc:
            print(json.dumps(sc, indent=1, ensure_ascii=False))
        if run_dir is not None:
            d = run_dir / "scope"; d.mkdir(exist_ok=True); (d / f"{tid}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))


def cmd_replay(a):
    import chain
    c = load_contract(a.contract); chain.replay(c, a.from_run, a.levels, history_from=("dst" if getattr(a, "propagate", False) else "src"))


def cmd_tree_run(a):
    import treerun
    c = load_contract(a.contract)
    if a.run_id: c["run_id"] = a.run_id
    treerun.run(c, levels=None, mock=a.mock)


def cmd_compare(a):
    import chain
    print(chain.compare(a.self_run, a.gold_run, write=True))


def cmd_resummarize(a):
    import controller
    c = load_contract(a.contract); controller.resummarize(c, a.levels)


def cmd_reopen(a):
    import controller
    for layer in a.levels:
        controller.reopen(a.run_id, layer if layer.startswith("L") else f"L{layer}")


def cmd_report(a):
    import p2report as report
    print(report.build(a.run_id, write=True))


def cmd_sg_dry(a):
    """10-28 v15:只跑 planner(缓存)+ 建各层 pool,不调 Examiner / Solver;写 runs/<run>/sg_dry.md 供核对。"""
    import controller as CT, sg as SG
    c = load_contract(a.contract); store = Store()
    import store as _ST; _ST.ACCEPT_SOURCES.update(c.get("accept_unverified_sources") or [])
    run_dir = P.RUNS / c["run_id"]; run_dir.mkdir(parents=True, exist_ok=True)
    plans = SG.ensure(c, store, run_dir, task_ids=[c["task_sample_id"]], force=a.force)
    pl = plans[c["task_sample_id"]]
    L = [f"# sg dry-run {c['run_id']}", ""]
    if not pl:
        print("planner failed"); return
    ti = SG.task_info(store, c["task_sample_id"])
    L += [f"goal: {pl['goal']}", ""]
    for sg_ in pl["sub_goals"]:
        s = next(x for x in ti["steps"] if x["idx"] == sg_["idx"])
        L.append(f"## sub-goal {s['idx']} [{s['t0']:.1f}-{s['t1']:.1f}, {s['t1']-s['t0']:.0f}s] {s['text']}")
        if sg_.get("irrelevant"): L.append(f"- irrelevant: {sg_['irrelevant']}")
        for e in sg_["events"]:
            L.append(f"- {e['event_id']} ({e['type']}) {e['description']} | objects {e['objects']} | skills {e['skills']} | "
                     + (f"time {e['time']} ({e['match_note']})" if e.get("matched") else f"UNMATCHED: {e.get('match_note')}"))
        L.append("")
    L.append("## relations (L3)")
    for r in pl["relations"]:
        L.append(f"- {r['rel_id']} {r['type']} -> {r['skill']}: {r['events']} | ask: {r['ask']} | hint: {r['answer_hint']}")
    L.append(""); L.append("## decision points (L4)")
    for d in pl["decision_points"]: L.append(f"- idx {d['idx']} real={d['real']}: {d['why']}")
    L.append("")
    CT._SG_PLAN = plans
    for layer in ("L1", "L2", "L3", "L4"):
        st = CT.LayerState(run_dir, layer, c); st.skills = CT.active_skills(store, layer, c); CT.build_pools(store, st, c)
        L.append(f"## {layer} pools")
        for o, cap in st.skills:
            cl = st.pools.get(cap, [])
            L.append(f"### {cap}: {len(cl)} clusters" + (f" (NOT_EVALUATED: {st.not_evaluated[cap]})" if cap in st.not_evaluated else ""))
            for x in cl:
                sg_ = x["sg"]
                if layer in ("L1", "L2"):
                    extra = f" bands {{{', '.join(f'{t}:{len(v)}' for t, v in sg_['bands'].items())}}} knob {sorted(set(k['kind'] for k in sg_['knob'].values()))}" if layer == "L1" else f" tiers {sg_['tiers']}"
                    L.append(f"- sg{sg_['idx']} win {x['window']} events {[e['event_id'] for e in sg_['events']]} anchors {len(sg_['anchor_event'])} core {len(x['core'])}{extra}")
                elif layer == "L3":
                    L.append(f"- {sg_['rel_id']} ({sg_.get('rel_source')}) tier {sg_['tier']} sub-goals {sg_.get('idx')} win {x['window']} ({sg_['total_sec']}s, {sg_.get('window_rule')}) in-clip {sg_.get('sub_goals_in_clip')} core {len(x['core'])}")
                else:
                    L.append(f"- decision idx {sg_['idx']} win {x['window']} cutoff {x['observation_cutoff']} remaining {sg_['n_remaining']} final={sg_['final']} core {len(x['core'])}")
        L.append("")
    (run_dir / "sg_dry.md").write_text("\n".join(L))
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    d = sp.add_parser("dry-run"); d.add_argument("--video", required=True); d.add_argument("--layer", required=True); d.add_argument("--skill", required=True)
    d.add_argument("--t0", type=float); d.add_argument("--t1", type=float); d.add_argument("--contract"); d.add_argument("--n", type=int, default=3)
    d.add_argument("--include-retired", action="store_true"); d.add_argument("--summary", action="store_true")
    p = sp.add_parser("propose"); p.add_argument("--contract", required=True); p.add_argument("--video", required=True); p.add_argument("--layer", required=True)
    p.add_argument("--skill", required=True); p.add_argument("--n", type=int, default=3); p.add_argument("--dry-run", action="store_true")
    r = sp.add_parser("run"); r.add_argument("--contract", required=True); r.add_argument("--run-id"); r.add_argument("--levels", nargs="*", default=["L1", "L2", "L3", "L4"])
    r.add_argument("--n", type=int); r.add_argument("--mock", help="mock solver script: 'wrong:<cluster_prefix>' or 'all_correct'")
    r.add_argument("--base", type=int, help="每 skill 基础题(独立 cluster)数,默认 contract 的 per_skill_base=3")
    r.add_argument("--followups", type=int, help="每 skill 答错后最多追问几次(偶然 / 干扰 / 题型),默认 3")
    r.add_argument("--confirm", type=int, help="确认阶段每 skill 题数,默认 3")
    r.add_argument("--max-hyp-tests", type=int, help="单个假设最多检验几次,默认 3")
    r.add_argument("--history-mode", choices=["none", "self", "gold"], help="Solver 的下层历史:self = 自己的回答,gold = 参考答案")
    r.add_argument("--scope-mode", choices=["prefer", "strict", "off"], help="scope planner 命中的 cluster:prefer 排前 / strict 只用 / off 不用")
    sc_ = sp.add_parser("scope"); sc_.add_argument("--contract", required=True); sc_.add_argument("--task-id", nargs="*"); sc_.add_argument("--force", action="store_true")
    sc_.add_argument("--show", action="store_true"); sc_.add_argument("--mock", action="store_true")
    rpl = sp.add_parser("replay"); rpl.add_argument("--contract", required=True); rpl.add_argument("--from-run", required=True); rpl.add_argument("--levels", nargs="*", default=None)
    rpl.add_argument("--propagate", action="store_true", help="10-22:下层 history 用本 run 自己的新答案(第二个 agent 的 self 臂)")
    tr = sp.add_parser("tree-run"); tr.add_argument("--contract", required=True); tr.add_argument("--run-id"); tr.add_argument("--mock", help="mock solver script, e.g. all_correct 或 W,C,C")
    cmp_ = sp.add_parser("compare"); cmp_.add_argument("--self-run", required=True); cmp_.add_argument("--gold-run", required=True)
    rp = sp.add_parser("report"); rp.add_argument("--run-id", required=True)
    ro = sp.add_parser("reopen"); ro.add_argument("--run-id", required=True); ro.add_argument("--levels", nargs="+", required=True)
    rs = sp.add_parser("resummarize"); rs.add_argument("--contract", required=True); rs.add_argument("--levels", nargs="*", default=None)
    pf = sp.add_parser("preflight"); pf.add_argument("--contract", required=True)
    sd = sp.add_parser("sg-dry"); sd.add_argument("--contract", required=True); sd.add_argument("--force", action="store_true")
    sp.add_parser("check-joins"); sp.add_parser("audit-leaks"); sp.add_parser("stats")
    a = ap.parse_args()
    globals()["cmd_" + a.cmd.replace("-", "_")](a)


if __name__ == "__main__":
    main()
