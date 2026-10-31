"""Solver 的跨层 history(10-14 用户定):self = 下层题 + Solver 自己的回答(对错都给);gold = 下层题 + 参考答案。
replay = gold 臂对 self run 的全部计分题逐题重答(同题同 clip,只换 history);compare = 两臂成对比较。
history_label(10-26 用户定):history 文字块的抬头 / 每行前缀说明答案的来源:None|"neutral" = 原来的中性写法「Answer given」(两臂不可区分);
"own" = 说明这是模型自己之前给的、未核实的回答;"verified" = 说明这些答案已核实为正确、可当事实用。contract 键 history_label;臂名 selfv / goldv。"""
import json, re, time, collections
from pathlib import Path
import p2config as P
from store import Store, read_jsonl

LAYERS = ["L1", "L2", "L3", "L4"]
LAYER_NAME = {"L1": "perception", "L2": "understanding", "L3": "reasoning", "L4": "planning"}
_LETTER = re.compile(r"^\s*\(?([A-E])[\.\)\:]\s*")


def _norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


def _opt_text(options, letter):
    for o in options or []:
        m = _LETTER.match(o or "")
        if m and m.group(1) == str(letter).strip().upper()[:1]:
            return _LETTER.sub("", o).strip()
    return None


def answer_text(row, mode, render="full"):
    """展示给 Solver 的答案文字。gold = reference(字母展开成选项文字);self = parsed(没有就 raw 首行)。
    render="qa"(10-30,合约 history_render):history 不展示选项,选择题答案只给选项文字、不带字母(字母没有选项就没意义)。"""
    fmt, opts = row.get("format"), row.get("options")
    if render == "qa" and fmt in ("single_choice", "multi_select"):
        letters = re.findall(r"[A-E]", str(row.get("reference") if mode == "gold" else (row.get("parsed") or "")).upper())
        texts = [_opt_text(opts, L) for L in letters]
        if letters and all(texts): return "; ".join(texts)
        if mode == "gold": return str(row.get("reference"))
    if mode == "gold":
        ref = row.get("reference")
        if fmt == "single_choice":
            t = _opt_text(opts, ref); return f"{str(ref).strip().upper()[:1]}. {t}" if t else str(ref)
        if fmt == "multi_select":
            letters = re.findall(r"[A-E]", str(ref).upper())
            return "; ".join(f"{L}. {_opt_text(opts, L) or ''}" for L in letters) or str(ref)
        return str(ref)
    p = row.get("parsed")
    if fmt == "single_choice" and p:
        t = _opt_text(opts, p); return f"{p}. {t}" if t else str(p)
    if fmt == "multi_select" and p:
        return "; ".join(f"{L}. {_opt_text(opts, L) or ''}" for L in p)
    if fmt == "plan" and isinstance(p, list) and p:
        return " ".join(f"{i + 1}. {l}" for i, l in enumerate(p))
    if p:
        return str(p)
    raw = row.get("solver_answer") or ""
    m = re.search(r"(?im)^\s*answer\s*[:：]\s*(.+?)\s*$", raw)
    return (m.group(1) if m else raw.strip().splitlines()[0] if raw.strip() else "(no answer)").strip()


def gold_text(row):
    return _norm(answer_text(row, "gold"))


def current_gold_text(cand):
    out = cand["output"]; pub, pri = out["public"], out["private"]
    row = {"format": pub.get("format"), "options": pub.get("options"), "reference": pri.get("proposed_reference_answer")}
    return gold_text(row)


def lower_rows(run_dir, layer, sample_id):
    run_dir = Path(run_dir)
    out = []
    for k in LAYERS[: LAYERS.index(layer)]:
        for h in read_jsonl(run_dir / k / "history.jsonl"):
            if h.get("sample_id") == sample_id and h.get("verdict") in ("correct", "wrong") and h.get("capability_skill") not in P.excluded_skills():   # 10-27:排除的 skill 不进 history
                out.append(h)
    out.sort(key=lambda h: (LAYERS.index(h["layer"]), h["turn"]))
    return out


def depth(run_dir, layer, sample_id):
    return len(lower_rows(run_dir, layer, sample_id))


HIST_HEADER = {
    "neutral": "Earlier questions about this same task, with the answers given:",
    "own": "Earlier questions about this same task, with the answers you yourself gave earlier. Those answers were not checked and some may be wrong; treat them as your own unverified impressions, not as facts:",
    "verified": "Earlier questions about this same task, with answers that have been checked and verified as correct. You can rely on them as established facts about this task:",
}
ANS_PREFIX = {"neutral": "Answer given", "own": "Your earlier (unverified) answer", "verified": "Verified correct answer"}


def render(rows, mode, label=None, render="full"):
    if not rows:
        return ""
    label = label or "neutral"
    L = [HIST_HEADER[label]]
    for i, h in enumerate(rows, 1):
        q = (h.get("question") or "").strip().replace("\n", " ")
        line = f"{i}. ({h['layer']} {LAYER_NAME.get(h['layer'], '')}) {q}"
        if h.get("options") and render != "qa":                       # 10-30 history_render=qa:只给题面 + 答案,不给选项
            line += " Options: " + " | ".join(o.strip() for o in h["options"])
        L.append(line)
        L.append(f"   {ANS_PREFIX[label]}: {answer_text(h, mode, render)}")
    return "\n".join(L) + "\n"


def _window_end(row):
    """history 行的 clip 窗口结束时刻(源视频秒);没有 media_refs 时返回 None。"""
    ends = [w[1] for m in (row.get("media_refs") or []) for w in (m.get("windows") or []) if isinstance(w, (list, tuple)) and len(w) == 2]
    return max(ends) if ends else None


_CANDS = {}


def _cands(run_dir):
    run_dir = Path(run_dir)
    if run_dir not in _CANDS:
        _CANDS[run_dir] = {c["candidate_id"]: c for c in read_jsonl(run_dir / "candidates.jsonl")}
    return _CANDS[run_dir]


_STORE = None


def _event_end(row, run_dir):
    """下层题「问到的事件」的结束时刻 = 该题 private.evidence_refs 里证据记录 time.end_sec 的最大值(源视频秒)。
    用事件时刻而不是 clip 窗口结束:Solver 在上层看不到下层的 clip,只看到题面 + 答案,泄露的是事件本身;窗口比事件长 10–30 s,按窗口过滤会把几乎所有题剔掉。
    没有 evidence_refs / 查不到时间时退回窗口结束。"""
    global _STORE
    cand = _cands(run_dir).get(row.get("candidate_id"))
    refs = ((cand or {}).get("output") or {}).get("private", {}).get("evidence_refs") or []
    if refs:
        if _STORE is None:
            _STORE = Store()
        ends = []
        for eid in refs:
            e = _STORE.evidence.get(eid) or {}
            t = e.get("time") or {}
            if isinstance(t, dict) and t.get("end_sec") is not None:
                ends.append(float(t["end_sec"]))
        if ends:
            return max(ends), "event"
    we = _window_end(row)
    return we, "window"


def _windows(media_refs):
    return [(float(w[0]), float(w[1])) for m in (media_refs or []) for w in (m.get("windows") or []) if isinstance(w, (list, tuple)) and len(w) == 2]


def _steps_of(sample_id):
    """该 task 的 sub-goal 时间段 [(idx, t0, t1)](task_step 记录,不含 answer_only 的 next)。"""
    global _STORE
    if _STORE is None:
        _STORE = Store()
    _ = _STORE.evidence
    out = []
    for r in _STORE.by_event.get(sample_id, []):
        if r["kind"] == "task_step" and not r["value"].get("is_next_action") and r.get("time"):
            out.append((r["value"].get("idx"), float(r["time"]["start_sec"]), float(r["time"]["end_sec"])))
    return out


def _overlap(a, b):
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def select_relevant_balanced(rows, current, sample_id, per_layer=8):
    """10-27 晚(用户定):每个下层各取 ≤ per_layer 条。先取与本题 clip 窗口重叠、或落在同一 sub-goal 的题(重叠越多越前);
    不够时按 skill 轮流补(已选少的 skill 先补),每个 skill 取窗口中心离本题最近的。返回 (rows, stats)。"""
    cur_w = _windows(((current or {}).get("output") or {}).get("public", {}).get("media_refs"))
    steps = _steps_of(sample_id)
    sg = lambda ws: {i for (i, a, b) in steps for w in ws if _overlap(w, (a, b)) > 0}
    cur_sg = sg(cur_w)
    cur_mid = (sum((a + b) / 2 for a, b in cur_w) / len(cur_w)) if cur_w else None
    out, stats = [], {}
    for L in LAYERS:
        lr = [h for h in rows if h.get("layer") == L]
        if not lr:
            continue
        rel = []
        for h in lr:
            hw = _windows(h.get("media_refs"))
            ov = sum(_overlap(a, b) for a in hw for b in cur_w)
            if ov > 0 or (sg(hw) & cur_sg):
                rel.append((ov, h))
        rel.sort(key=lambda x: (-x[0], x[1]["turn"]))
        pick = [h for _, h in rel[:per_layer]]
        n_rel = len(pick)
        if len(pick) < per_layer:
            chosen = {id(h) for h in pick}
            dist = lambda h: abs(((lambda ws: sum((a + b) / 2 for a, b in ws) / len(ws))(_windows(h.get("media_refs"))) if _windows(h.get("media_refs")) else 1e9) - cur_mid) if cur_mid is not None else 0
            by_skill = collections.defaultdict(list)
            for h in lr:
                if id(h) not in chosen:
                    by_skill[h["capability_skill"]].append(h)
            for sk in by_skill:
                by_skill[sk].sort(key=dist)
            cnt = collections.Counter(h["capability_skill"] for h in pick)
            while len(pick) < per_layer and any(by_skill.values()):
                sk = min((s for s in by_skill if by_skill[s]), key=lambda s: (cnt[s], s))
                pick.append(by_skill[sk].pop(0)); cnt[sk] += 1
        out += pick
        stats[L] = {"n": len(pick), "relevant": n_rel, "available": len(lr), "skills": dict(collections.Counter(h["capability_skill"] for h in pick))}
    out.sort(key=lambda h: (LAYERS.index(h["layer"]), h["turn"]))
    return out, stats


def history_for(run_dir, layer, sample_id, mode, cap=12, exclude_same_answer=True, current=None, respect_cutoff=False, only_scope_ids=None, only_base=False, label=None,
                select=None, per_layer=8, per_subgoal=6, event_ids=None, render="full"):
    """返回 {mode, n, excluded, turns, text}。exclude_same_answer:两臂都按下层题的 gold 文字与本题 gold 文字相同来剔除,保证两臂题集一致。
    respect_cutoff(10-21):本题有 observation_cutoff 时,剔除窗口结束晚于 cutoff 的下层题(否则下层题会把 cutoff 之后的步骤带给 Solver);剔除的记在 excluded_after_cutoff。"""
    if mode in (None, "none"):
        return None
    rows = lower_rows(run_dir, layer, sample_id)
    if only_base:                                      # 10-23:只带下层基础题(排除追问 / 确认题),两臂题集一致
        rows = [h for h in rows if not h.get("tests_hypothesis") and not h.get("confirmation_slot")]
    if only_scope_ids is not None:                     # 10-22 题树:只带指定节点(子节点)的题
        want = set(only_scope_ids); rows = [h for h in rows if h.get("scope_id") in want]
    excluded = []; excluded_cut = []
    cut = (current or {}).get("output", {}).get("public", {}).get("observation_cutoff") if current else None
    if select in ("by_subgoal", "by_event") and cut is None and current is not None:          # 10-28 v15:没有 cutoff 的题按 clip 结束时刻截断 history
        ends = [w[1] for m_ in ((current.get("output") or {}).get("public", {}).get("media_refs") or []) for w in (m_.get("windows") or []) if isinstance(w, (list, tuple)) and len(w) == 2]
        cut = max(ends) if ends else None
    if respect_cutoff and cut is not None:
        keep = []
        for h in rows:
            we, how = _event_end(h, run_dir)
            if we is not None and we > float(cut) + 0.5:
                excluded_cut.append([h["layer"], h["turn"], round(we, 1), how])
            else:
                keep.append(h)
        rows = keep
    if exclude_same_answer and current is not None:
        cur = current_gold_text(current)
        keep = []
        for h in rows:
            if cur and gold_text(h) == cur:
                excluded.append([h["layer"], h["turn"]])
            else:
                keep.append(h)
        rows = keep
    sel_stats = None
    if select == "by_event" and event_ids:             # 10-29 v17:只带同 event 的下层题(L4 仍按 sub-goal)
        import sg as _SG
        rows, sel_stats = _SG.select_by_event(rows, set(event_ids), per_layer=per_layer)
    elif select == "by_subgoal" or (select == "by_event" and not event_ids):   # 10-28 v15:按 sub-goal 分组,每组 ≤ per_subgoal 条、每层 ≤ per_layer 条
        import sg as _SG
        rows, sel_stats = _SG.select_by_subgoal(rows, current, sample_id, per_subgoal=per_subgoal, per_layer=per_layer)
    elif select == "relevant_balanced":                  # 10-27 晚(用户定):每层先相关(同 sub-goal / 窗口重叠)再按 skill 均匀补;不再按「最后 N 条」截断
        rows, sel_stats = select_relevant_balanced(rows, current, sample_id, per_layer=per_layer)
    else:
        rows = rows[-cap:] if cap else rows
    return {"mode": mode, "label": label or "neutral", "n": len(rows), "excluded": excluded, "excluded_after_cutoff": excluded_cut, "cutoff": cut, "only_scope_ids": only_scope_ids, "only_base": only_base,
            "select": select, "per_layer": sel_stats,
            "turns": [[h["layer"], h["turn"]] for h in rows], "depth_available": depth(run_dir, layer, sample_id),
            "render": render,
            "text": (__import__("sg").render_grouped(rows, mode, label, render) if (select == "by_subgoal" or (select == "by_event" and not event_ids)) else globals()["render"](rows, mode, label, render))}


# ------------------------------------------------------------------ gold replay
def solve_reps(cand, contract, store, run_dir, history_text, n_rep=1, blind=False):
    """同题重答 n_rep 次(10-21,压 3.7-flash 关不掉 thinking 的重答噪声):单选按 parsed 字母取多数(平票取先出现的),
    其它题型取第 1 次;返回 (多数那次的 sol, 其 grade, reps 列表[{raw, parsed, verdict, score}])。blind=True 时不传 clip,只给文字。"""
    import solver as SV, grade as GR
    outs = []
    for k in range(n_rep):
        sol = SV.solve_blind(cand, contract, run_dir=run_dir, history_text=history_text) if blind else \
              SV.solve(cand, contract, store, run_dir=run_dir, history_text=history_text)
        gr = GR.grade(cand, sol, contract, run_dir=run_dir)
        outs.append((sol, gr))
    reps = [{"rep": k, "raw": so["raw"], "parsed": g["parsed"], "verdict": g["verdict"], "score": g["score"]} for k, (so, g) in enumerate(outs)]
    if n_rep == 1:
        return outs[0][0], outs[0][1], reps
    fmt = cand["output"]["public"].get("format")
    if fmt == "single_choice":
        keys = [str(g["parsed"] or "").strip().upper()[:1] for _, g in outs]
        cnt = collections.Counter(k for k in keys if k)
        if cnt:
            best = max(cnt.values()); win = next(k for k in keys if k and cnt[k] == best)
            i = keys.index(win)
            return outs[i][0], outs[i][1], reps
    return outs[0][0], outs[0][1], reps


def wrong_option(row, rng):
    """给干预臂造一个错答案:单选 = 随机一个非参考字母;多选 = 翻一个字母。返回新的 reference 字符串。"""
    fmt, opts, ref = row.get("format"), row.get("options") or [], str(row.get("reference") or "")
    letters = [(_LETTER.match(o) or [None, None])[1] for o in opts]
    letters = [l for l in letters if l]
    if fmt == "single_choice":
        pool = [l for l in letters if l != ref.strip().upper()[:1]]
        return rng.choice(pool) if pool else ref
    if fmt == "multi_select":
        cur = set(re.findall(r"[A-E]", ref.upper())); pool = letters or ["A", "B", "C"]
        flip = rng.choice(pool); cur = (cur - {flip}) if flip in cur else (cur | {flip})
        return ", ".join(sorted(cur)) or flip
    return ref


def replay(contract, from_run_id, levels=None, history_from="src"):
    """history_from="dst"(10-22 propagate):下层 history 从本 run 自己的新答案取(自底向上传播 = 第二个 agent 的 self 臂)。"""
    import controller as CT, solver as SV, grade as GR
    src = P.RUNS / from_run_id; dst = P.RUNS / contract["run_id"]; dst.mkdir(parents=True, exist_ok=True)
    (dst / "run_contract.json").write_text(json.dumps(contract, indent=1, ensure_ascii=False))
    store = Store()
    import store as _ST, retrieve as _RT; _ST.ACCEPT_SOURCES.update(contract.get("accept_unverified_sources") or []); _RT.EGOPLAN_L4_INTERMEDIATE = bool(contract.get("l4_intermediate_cutoffs"))
    for _k, _a in (("gap_sizes", "GAP_SIZES"), ("gap_head_sec", "GAP_HEAD_SEC"), ("gap_tail_sec", "GAP_TAIL_SEC"), ("gap_tail_frame_sec", "GAP_TAIL_FRAME_SEC")):
        if contract.get(_k) is not None: setattr(_RT, _a, contract[_k])
    cands = {c["candidate_id"]: c for c in read_jsonl(src / "candidates.jsonl")}
    mode = contract.get("history_mode", "gold")
    blind = not contract.get("solver_input_spec", {}).get("modalities")        # 10-21:modalities 空 = 盲测臂(只看文字,不传 clip)
    reps_by = contract.get("reps_by_layer") or {}                                # 10-21:{"L4": 3} = 该层每题重答 N 次取多数
    for layer in (levels or LAYERS):
        layer = layer if layer.startswith("L") else f"L{layer}"
        rows = [h for h in read_jsonl(src / layer / "history.jsonl") if h.get("verdict") in ("correct", "wrong")]
        excl = P.excluded_skills()                               # 10-27:全局排除的 skill(contact 四个)不重放
        n_excl = sum(1 for h in rows if h.get("capability_skill") in excl)
        rows = [h for h in rows if h.get("capability_skill") not in excl]
        if n_excl:
            CT.log(dst, f"{layer}: {n_excl} items of excluded skills skipped ({sorted(excl)})")
        if not rows:
            CT.log(dst, f"{layer}: nothing to replay"); continue
        st = CT.LayerState(dst, layer, contract)
        done = {h["candidate_id"] for h in st.history}
        n_new = 0
        for h in rows:
            if h["candidate_id"] in done:
                continue
            cand = cands.get(h["candidate_id"])
            if cand is None:
                CT.log(dst, f"{layer} t{h['turn']}: candidate missing, skipped"); continue
            only = (h.get("tree") or {}).get("depends_on") if (contract.get("history_scope") == "tree" and h.get("tree")) else None
            hist = history_for(dst if history_from == "dst" else src, layer, h.get("sample_id"), mode, cap=contract.get("history_cap", 12),
                               exclude_same_answer=contract.get("history_exclude_same_answer", True), current=cand,
                               respect_cutoff=contract.get("history_respect_cutoff", False), only_scope_ids=only, only_base=contract.get("history_only_base", False),
                               label=contract.get("history_label"), select=contract.get("history_select"), per_layer=contract.get("history_per_layer", 8),
                               per_subgoal=contract.get("history_per_subgoal", 6), render=contract.get("history_render", "full")) if h.get("sample_id") else None
            n_rep = max(1, int(reps_by.get(layer, contract.get("solver_reps", 1))))
            try:
                sol, gr, reps = solve_reps(cand, contract, store, dst, hist["text"] if hist else None, n_rep, blind=blind)
            except Exception as e:
                CT.log(dst, f"{layer} t{h['turn']}: solver error {str(e)[:160]}"); continue
            row = dict(h)
            row.update(solver_answer=sol["raw"], parsed=gr["parsed"], verdict=gr["verdict"], score=gr["score"], judge=gr["judge"],
                       judge_reason=gr.get("reason"), plan_eval=gr.get("plan_eval"), media=sol.get("media"), model=sol["model"], solver_prompt=sol["prompt"],
                       history_used=({k: v for k, v in hist.items() if k != "text"} if hist else None),
                       replay_of=from_run_id, self_verdict=h["verdict"], blind=blind, reps=reps, ts=time.strftime("%Y-%m-%dT%H:%M:%S"))
            st.append_history(row); st.turn = max(st.turn, row["turn"]); n_new += 1
            CT.log(dst, f"  {layer} t{row['turn']:02d} {row['capability_skill']:32s} replay({mode}) self={h['verdict']:7s} -> {gr['verdict']} (hist n={hist['n'] if hist else 0})")
        st.skills = CT.active_skills(store, layer, contract); CT.build_pools(store, st, contract)
        st.phase = "DONE"; st.stop_reason = f"REPLAY_OF:{from_run_id}"; st.save()
        CT.write_summary(st, contract)
        CT.log(dst, f"{layer}: replayed {n_new} items")
    CT.log(dst, "replay finished")


# ------------------------------------------------------------------ compare
def compare(self_run, gold_run, write=True):
    sd, gd = P.RUNS / self_run, P.RUNS / gold_run
    L = [f"# self vs gold history:`{self_run}` vs `{gold_run}`", "",
         "self = Solver 看到下层题 + 自己的回答;gold = 同一批题,下层答案换成参考答案(L1–L3 的参考答案是 Examiner 的 proposed_reference_answer,未人工核验)。", "",
         "| layer | n | self 对 | gold 对 | self acc | gold acc | self✗→gold✓ | self✓→gold✗ | history 深度(中位 / 0 条的题) | 剔除同答案 |", "|---|---|---|---|---|---|---|---|---|---|"]
    by_skill = collections.defaultdict(lambda: [0, 0, 0])
    tot = [0, 0, 0, 0, 0]
    for layer in LAYERS:
        s_rows = {h["candidate_id"]: h for h in read_jsonl(sd / layer / "history.jsonl") if h.get("verdict") in ("correct", "wrong")}
        g_rows = {h["candidate_id"]: h for h in read_jsonl(gd / layer / "history.jsonl") if h.get("verdict") in ("correct", "wrong")}
        ids = [i for i in s_rows if i in g_rows]
        if not ids:
            continue
        sc = sum(s_rows[i]["verdict"] == "correct" for i in ids); gc = sum(g_rows[i]["verdict"] == "correct" for i in ids)
        up = sum(s_rows[i]["verdict"] == "wrong" and g_rows[i]["verdict"] == "correct" for i in ids)
        dn = sum(s_rows[i]["verdict"] == "correct" and g_rows[i]["verdict"] == "wrong" for i in ids)
        depths = sorted(((g_rows[i].get("history_used") or {}).get("n", 0)) for i in ids)
        exc = sum(len((g_rows[i].get("history_used") or {}).get("excluded") or []) for i in ids)
        med = depths[len(depths) // 2] if depths else 0
        L.append(f"| {layer} | {len(ids)} | {sc} | {gc} | {sc / len(ids):.2f} | {gc / len(ids):.2f} | {up} | {dn} | {med} / {sum(1 for d in depths if d == 0)} | {exc} |")
        for i in ids:
            k = (layer, s_rows[i]["capability_skill"]); by_skill[k][0] += 1
            by_skill[k][1] += s_rows[i]["verdict"] == "correct"; by_skill[k][2] += g_rows[i]["verdict"] == "correct"
        tot[0] += len(ids); tot[1] += sc; tot[2] += gc; tot[3] += up; tot[4] += dn
    if tot[0]:
        L.append(f"| **all** | {tot[0]} | {tot[1]} | {tot[2]} | {tot[1] / tot[0]:.2f} | {tot[2] / tot[0]:.2f} | {tot[3]} | {tot[4]} | | |")
    L += ["", "| layer | skill | n | self 对 | gold 对 |", "|---|---|---|---|---|"]
    for (layer, sk), (n, a, b) in sorted(by_skill.items()):
        L.append(f"| {layer} | {sk} | {n} | {a} | {b} |")
    # scope 命中率
    L += ["", "| layer | 计分题 | 有 scope_id | 有 history(n>0) |", "|---|---|---|---|"]
    for layer in LAYERS:
        rows = [h for h in read_jsonl(sd / layer / "history.jsonl") if h.get("verdict") in ("correct", "wrong")]
        if rows:
            L.append(f"| {layer} | {len(rows)} | {sum(1 for h in rows if h.get('scope_id'))} | {sum(1 for h in rows if (h.get('history_used') or {}).get('n', 0) > 0)} |")
    md = "\n".join(L) + "\n"
    if write:
        (gd / "compare.md").write_text(md)
    return md
