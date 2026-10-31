"""10-25 v8(用户定):skill 内的难度阶梯,2-down-1-up。层与 skill 不变,每个 skill 4 档;档 = 题型 + 窗长 + cluster 的程序量
(一般 skill:interference 分;L4 goal_conditioned_planning:cutoff 后剩余阶段数;plan_gap_filling:隐藏步数)。
搜索:从 start_level 起,同一档连续 2 题对 → 升一档(换 event);错 1 题 → 降一档(换 event);2 次反转 / 到顶 / 到底 / 预算用完停;
边界 = 反转点档位均值(到顶 = 4.5,到底 = 0.5,未收敛 = 最后两题档位均值,标 unconverged)。
验证:边界下一档 1 题(预期对)+ 上一档 1 题(预期错),两个预期都成立 → boundary_confirmed。
Examiner 只在 ctx.difficulty 给的题型 / 窗长内出题(examiner._difficulty_checks 核对),策略仍是 coverage,scope 内未问过的条目优先。"""
import json, math, statistics
import l3ext as LX

GENERIC = {1: {"format": "single_choice", "window_max_sec": 30.0, "band": "low"},
           2: {"format": "single_choice", "window_max_sec": 30.0, "band": "high"},
           3: {"format": "multi_select", "window_max_sec": 15.0, "band": "any"},
           4: {"format": "short_answer", "window_max_sec": 10.0, "band": "any"}}
PLAN = {1: {"format": "single_choice", "window_max_sec": 30.0, "remaining": None},
        2: {"format": "plan", "window_max_sec": 30.0, "remaining": (1, 2)},
        3: {"format": "plan", "window_max_sec": 30.0, "remaining": (3, 5)},
        4: {"format": "plan", "window_max_sec": 30.0, "remaining": (6, 999)}}
GAP = {1: {"format": "single_choice", "n_hidden": (1, 1)}, 2: {"format": "single_choice", "n_hidden": (2, 2)},
       3: {"format": "single_choice", "n_hidden": (3, 3)}, 4: {"format": "gap_steps", "n_hidden": (2, 3)}}
# 10-27 晚(用户定):L4 两个 skill 统一成「题型 × 规模」四档(contract l4_ladder = "unified";v12 及以前仍用上面的 PLAN / GAP)
PLAN_U = {1: {"format": "single_choice", "window_max_sec": 30.0, "remaining": None},
          2: {"format": "single_choice", "window_max_sec": 30.0, "remaining": None, "distractors": "task_steps"},
          3: {"format": "plan", "window_max_sec": 30.0, "remaining": (1, 2)},
          4: {"format": "plan", "window_max_sec": 30.0, "remaining": (3, 999)}}
GAP_U = {1: {"format": "single_choice", "n_hidden": (1, 1)}, 2: {"format": "single_choice", "n_hidden": (2, 3)},
         3: {"format": "gap_steps", "n_hidden": (1, 2)}, 4: {"format": "gap_steps", "n_hidden": (3, 3)}}
NOTE_U = {
    "goal_conditioned_planning": {1: "single choice: the next sub-goal after the cutoff (the official choices may be reused in a fresh order)",
                                  2: "single choice: the next sub-goal after the cutoff, but DO NOT reuse the official choices: build the 3 distractors from other recorded sub-goals of this task (already done, or not yet due) or plausible-but-wrong actions",
                                  3: "plan (stages): 1-2 recorded stages remain after the cutoff", 4: "plan (stages): 3 or more recorded stages remain"},
    "plan_gap_filling": {1: "single choice, 1 hidden step, tail = 6 s clip", 2: "single choice, 2-3 hidden steps, tail = first frame",
                         3: "gap_steps: write the 1-2 hidden steps yourself", 4: "gap_steps: write the 3 hidden steps yourself"},
}
_L4_UNIFIED = False          # run_layer 按 contract.l4_ladder 设

NOTE = {
    "generic": {1: "easiest: 30 s clip, single choice, an event with few competing objects/actions/sounds in the window",
                2: "30 s clip, single choice, an event with more competing objects/actions/sounds in the window",
                3: "15 s clip (choose the sub-window that contains the target moment), multi_select with 3-5 checkable statements",
                4: "10 s clip, short_answer: the Solver must produce the answer itself (object name / verb + object / number / order)"},
    "goal_conditioned_planning": {1: "single choice: the next sub-goal after the cutoff", 2: "plan (stages): 1-2 recorded stages remain after the cutoff",
                                  3: "plan (stages): 3-5 recorded stages remain", 4: "plan (stages): 6 or more recorded stages remain"},
    "plan_gap_filling": {1: "single choice, 1 hidden step, tail = 6 s clip", 2: "single choice, 2 hidden steps, tail = first frame",
                         3: "single choice, 3 hidden steps, tail = first frame", 4: "gap_steps: write the 2-3 hidden steps yourself"},
}


def ladder(skill):
    if skill in LX.LADDER: return LX.LADDER[skill]              # 10-27 L3 扩展 skill:档 = 跨度 / 延迟 / clip 外物体数 / 距离,题型基本不变
    if _L4_UNIFIED and skill in ("goal_conditioned_planning", "plan_gap_filling"):
        return PLAN_U if skill == "goal_conditioned_planning" else GAP_U
    return PLAN if skill == "goal_conditioned_planning" else GAP if skill == "plan_gap_filling" else GENERIC


def knob(store, skill, c):
    """cluster 的难度程序量(全部来自标注 / 程序,不来自模型)。"""
    if skill == "plan_gap_filling":
        return int((c.get("gap") or {}).get("n_hidden") or 0)
    if skill in LX.LADDER:
        return LX.knob(c)
    if skill == "goal_conditioned_planning":
        cut, sid = c.get("observation_cutoff"), c.get("sample_id")
        if cut is None or not sid:
            return 0
        steps = [r for r in store.by_event.get(sid, []) if r["kind"] == "task_step" and not r["value"].get("is_next_action")]
        return sum(1 for r in steps if r["time"]["start_sec"] >= float(cut) - 1e-6)
    return int((c.get("interference") or {}).get("score") or 0)


def _filter(skill, level, knobs):
    L = ladder(skill)[level]
    if skill == "goal_conditioned_planning":
        if L["remaining"] is None:
            return lambda k: True
        lo, hi = L["remaining"]; return lambda k: lo <= k <= hi
    if skill == "plan_gap_filling":
        lo, hi = L["n_hidden"]; return lambda k: lo <= k <= hi
    if skill in LX.LADDER:
        return LX.level_filter(skill, level)
    med = statistics.median(knobs) if knobs else 0
    if L["band"] == "low": return lambda k: k <= med
    if L["band"] == "high": return lambda k: k >= med
    return lambda k: True


def spec_for(skill, level):
    L = ladder(skill)[level]
    if skill in LX.LADDER:
        return {"level": level, "format": L["format"], "window_max_sec": L.get("window_max_sec", 30.0), "window_min_sec": 10.0, "note": LX.NOTE[skill][level],
                "rule": "controller-fixed difficulty: use exactly this format; the offered clusters already match this level's knob (span / delay / objects outside the clip / prerequisite distance); same skill, same layer"}
    kind = skill if skill in ("goal_conditioned_planning", "plan_gap_filling") else "generic"
    note = (NOTE_U if (_L4_UNIFIED and kind != "generic") else NOTE)[kind][level]
    spec = {"level": level, "format": L["format"], "window_max_sec": L.get("window_max_sec", 30.0), "window_min_sec": 10.0,
            "note": note, "rule": "controller-fixed difficulty: use exactly this format and at most this clip length; same skill, same layer"}
    if L.get("distractors"):
        spec["distractors"] = L["distractors"]
        spec["rule"] += "; distractors = task_steps: the options must NOT be the official four choices; write 3 distractors from this task's other recorded sub-goals or plausible-but-wrong actions"
    return spec


def pool_for_level(state, store, cap, level, rank):
    """该档可用的 cluster(未用过的优先;一般 skill 没有未用的时,允许用过但没用本档题型问过的 cluster)。按 scope 排序后再按程序量排。"""
    if state.c.get("sg_mode"):                                 # 10-28 v15
        import sg as _SG
        return _SG.pool_for_level(state, store, cap, level)
    pool = state.pools.get(cap, [])
    knobs = {c["evidence_cluster_id"]: knob(store, cap, c) for c in pool}
    filt = _filter(cap, level, list(knobs.values()))
    used = state.used_clusters()
    fmt = ladder(cap)[level]["format"]
    unused = [c for c in pool if c["evidence_cluster_id"] not in used]
    cands = [c for c in unused if filt(knobs[c["evidence_cluster_id"]])]
    if state.c.get("l4_answerability") and cap in ("goal_conditioned_planning", "plan_gap_filling"):   # 10-27 晚(用户):L4 可答性检查
        import l4check as K
        memo = getattr(state, "_l4ans", None)
        if memo is None: memo = state._l4ans = {}
        keep = []
        for c in cands:
            k = (c["evidence_cluster_id"], level)
            if k not in memo:
                ok, det = K.check(store, state.dir.parent, state.c, cap, c, level)
                memo[k] = ok
                K.log(state.dir.parent, {"cluster": c["evidence_cluster_id"], "skill": cap, "level": level, "window": c.get("windows") or c.get("window"),
                                         "cutoff": c.get("observation_cutoff"), "ok": ok, **det})
            if memo[k]: keep.append(c)
        cands = keep
    strict = cap in ("goal_conditioned_planning", "plan_gap_filling") or cap in LX.LADDER
    if not cands and not strict:
        cands = unused
    if not cands and not strict:
        asked = {(h["evidence_cluster_id"], h.get("format")) for h in state.history}
        cands = [c for c in pool if (c["evidence_cluster_id"], fmt) not in asked and c["evidence_cluster_id"] not in state.frozen_clusters]
    cands = rank(state, cap, cands)
    band = ladder(cap)[level].get("band", "any")
    if state.c.get("stair_scope_first"):                       # 10-27 v13:先按 scope 档(未问条目 > 问过条目 > 无条目),同档内再按程序量
        import controller as _CT
        cands.sort(key=lambda c: (_CT.scope_tier(state, cap, c), knobs[c["evidence_cluster_id"]] * (1 if band == "low" else -1)))
    else:
        cands.sort(key=lambda c: knobs[c["evidence_cluster_id"]] * (1 if band == "low" else -1))      # 稳定排序:scope 顺序内按程序量
    return cands[:2]


def levels_available(state, store, cap, rank):
    return [L for L in (1, 2, 3, 4) if pool_for_level(state, store, cap, L, rank)]


_START_CACHE = {}


def start_level_from(contract, cap):
    """10-27 晚(用户定 v14 实验):contract.stair_start_from = 上一个 run 的名字时,该 skill 的起始档 = 上次边界向下取整(0.5 → 1,2.5 → 2,4.5 → 4),
    上次没边界则用 stair_start_level。意图:跑多个 task 时第二个 task 起从上次边界附近起步,少走几步到反转点。"""
    src = contract.get("stair_start_from")
    default = int(contract.get("stair_start_level", 2))
    if not src:
        return default
    if src not in _START_CACHE:
        import p2config as P
        found = {}
        for L in ("L1", "L2", "L3", "L4"):
            sp = P.RUNS / src / L / "state.json"
            if sp.exists():
                for k, v in (json.loads(sp.read_text()).get("stair") or {}).items():
                    if isinstance(v, dict) and v.get("boundary") is not None:
                        found[k] = float(v["boundary"])
        _START_CACHE[src] = found
    b = _START_CACHE[src].get(cap)
    return default if b is None else max(1, min(4, int(math.floor(b))))


def new_state(contract, cap=None):
    return {"level": start_level_from(contract, cap), "streak": 0, "trace": [], "reversal_levels": [], "last_dir": None,
            "phase": "search", "stop": None, "boundary": None, "unconverged": False, "verify": [], "invalid_streak": 0, "floor_hits": 0}


def _next_level(level, avail, direction):
    ups = [L for L in avail if L > level] if direction == "up" else [L for L in avail if L < level]
    return (min(ups) if direction == "up" else max(ups)) if ups else None


def _estimate(st, edge):
    """未收敛时的边界估计:已有反转点档位 + 当前停下处的边缘值(level±0.5)取均值。"""
    pts = list(st.get("reversal_levels") or []) + [edge]
    return round(statistics.mean(pts), 2)


def update_search(st, level, verdict, turn, contract, avail, reused=False):
    """按 2-down-1-up 更新;返回 'up' / 'down' / 'stay'。streak 只数同一档内连续对;到顶(第 4 档连对)= ceiling,到底(第 1 档两错)= floor;
    上下一档没有 cluster 可用 = exhausted_up / exhausted_down(边界取 level±0.5,标 unconverged)。"""
    st["trace"].append({"turn": turn, "level": level, "verdict": verdict, "reused": bool(reused)})
    budget = int(contract.get("stair_budget", 6))
    move = "stay"
    if verdict == "correct":
        st["streak"] += 1
        if st["streak"] >= 2:
            st["streak"] = 0
            if level >= 4:
                st["stop"] = "ceiling"; st["boundary"] = 4.5
            else:
                nxt = _next_level(level, avail, "up")
                if nxt is None:
                    st["stop"] = "exhausted_up"; st["boundary"] = _estimate(st, level + 0.5); st["unconverged"] = True
                else:
                    move = "up"; st["level"] = nxt
    else:
        st["streak"] = 0
        if level <= 1:
            st["floor_hits"] += 1
            if st["floor_hits"] >= 2:
                st["stop"] = "floor"; st["boundary"] = 0.5
        else:
            nxt = _next_level(level, avail, "down")
            if nxt is None:
                st["stop"] = "exhausted_down"; st["boundary"] = _estimate(st, level - 0.5); st["unconverged"] = True
            else:
                move = "down"; st["level"] = nxt
    if move in ("up", "down"):
        if st["last_dir"] is not None and move != st["last_dir"]:
            st["reversal_levels"].append(level)
        st["last_dir"] = move
    if st["stop"] is None and len(st["reversal_levels"]) >= 2:
        st["stop"] = "reversals"; st["boundary"] = round(statistics.mean(st["reversal_levels"]), 2)
    if st["stop"] is None and len(st["trace"]) >= budget:
        st["stop"] = "budget"; st["unconverged"] = True
        edge = st["level"] + (0.5 if st["last_dir"] == "up" else -0.5 if st["last_dir"] == "down" else 0.0)   # 最后一步往哪走,边界就在那一侧
        st["boundary"] = _estimate(st, edge) if st["reversal_levels"] else round(statistics.mean([t["level"] for t in st["trace"][-2:]] + [edge]), 2)
    if st["stop"] is not None:
        _plan_verify(st, contract)
    return move


def _plan_verify(st, contract):
    b = st["boundary"]; nv = int(contract.get("stair_verify", 2))
    st["phase"] = "verify"
    if nv <= 0 or st["stop"] in ("ceiling", "floor") or b is None:
        st["phase"] = "done"; return
    lo = max(1, math.floor(b)) if b % 1 else max(1, int(b) - 1)
    hi = min(4, math.ceil(b)) if b % 1 else min(4, int(b) + 1)
    plan = []
    if lo >= 1: plan.append({"level": lo, "expect": "correct", "verdict": None, "turn": None})
    if hi <= 4 and hi != lo: plan.append({"level": hi, "expect": "wrong", "verdict": None, "turn": None})
    st["verify"] = plan[:nv]
    if not st["verify"]:
        st["phase"] = "done"


def per_level(st):
    out = {}
    for t in st["trace"] + [v for v in st.get("verify", []) if v.get("verdict") in ("correct", "wrong")]:
        L = t["level"]; d = out.setdefault(L, [0, 0]); d[1] += 1; d[0] += t["verdict"] == "correct"
    return {str(k): f"{v[0]}/{v[1]}" for k, v in sorted(out.items())}


def summary(st):
    ver = [v for v in st.get("verify", []) if v.get("verdict") in ("correct", "wrong")]
    confirmed = bool(ver) and all(v["verdict"] == v["expect"] for v in ver) and len(ver) == len(st.get("verify", []))
    return {"boundary": st.get("boundary"), "stop": st.get("stop"), "unconverged": st.get("unconverged", False), "phase": st.get("phase"),
            "levels_tested": sorted({t["level"] for t in st["trace"]}), "per_level": per_level(st), "n_search": len(st["trace"]),
            "n_reused_events": sum(1 for t in st["trace"] if t.get("reused")), "trace": st["trace"],
            "reversal_levels": st.get("reversal_levels"), "verify": st.get("verify"), "boundary_confirmed": confirmed if ver else None}


def run_layer(store, state, contract, run_dir, *, run_turn, log, rank, mock=None):
    """阶梯模式的层循环(替代 decide/pick_skill/confirmation)。每轮挑一个未完成的 skill(已出题最少者),在它当前档出一题。"""
    global _L4_UNIFIED
    _L4_UNIFIED = contract.get("l4_ladder") == "unified"
    live = [(o, c) for o, c in state.skills if c not in state.not_evaluated]
    if not hasattr(state, "stair") or state.stair is None: state.stair = {}
    for o, c in live:
        state.stair.setdefault(c, new_state(contract, c))
    if contract.get("event_loop") and state.layer in ("L1", "L2", "L3"):      # 10-29 v17:按 event 遍历,阶梯只管档位
        import sg as _SG
        return _SG.run_layer_events(store, state, contract, run_dir, run_turn=run_turn, log=log, mock=mock)
    budget, nv = int(contract.get("stair_budget", 6)), int(contract.get("stair_verify", 2))
    contract["n_per_layer"] = max(1, len(live) * (budget + nv))
    contract["turn_budget_per_layer"] = max(int(contract.get("turn_budget_per_layer") or 0), int(contract["n_per_layer"] * 1.5) + 6)   # build_pools 按 base+追问 算的轮数预算太小,按阶梯预算放大
    while True:
        if state.solver_errors >= contract["max_solver_errors"]:
            state.stop_reason = "STOP_SOLVER_ERRORS"; break
        if state.examiner_errors >= 5:
            state.stop_reason = "STOP_EXAMINER_ERRORS"; break
        todo = [(o, c) for o, c in live if state.stair[c]["phase"] != "done"]
        if not todo:
            state.stop_reason = "STAIRCASE_COMPLETE"; break
        if state.turn >= contract["turn_budget_per_layer"]:
            state.stop_reason = "STOP_BUDGET"; break
        n_items = lambda c: sum(1 for h in state.history if h["capability_skill"] == c)
        if contract.get("skill_order") == "sequential":       # 10-27 晚(用户):一个 skill 的阶梯(搜索 + 验证)全部测完才换下一个 skill
            pair = todo[0]
        else:
            pair = min(todo, key=lambda p: (n_items(p[1]), p[1]))
        cap = pair[1]; st = state.stair[cap]
        if st["phase"] == "search":
            level = st["level"]; slot = None
        else:
            slot = next((v for v in st["verify"] if v["verdict"] is None), None)
            if slot is None:
                st["phase"] = "done"; state.save(); continue
            level = slot["level"]
        clusters = pool_for_level(state, store, cap, level, rank)
        if not clusters:
            if st["phase"] == "search":                     # 当前档没有 cluster 了:不悄悄换档,停下来按已有轨迹估边界(标 unconverged)
                st["stop"] = st["stop"] or "exhausted_at_level"; st["unconverged"] = True
                if st["boundary"] is None and st["trace"]:
                    st["boundary"] = _estimate(st, level + (0.5 if st["last_dir"] == "up" else -0.5 if st["last_dir"] == "down" else 0.0))
                _plan_verify(st, contract)
            else:
                slot["verdict"] = "no_cluster"
                if all(x["verdict"] is not None for x in st["verify"]): st["phase"] = "done"
            log(run_dir, f"  {state.layer} {cap}: no cluster for level {level} ({'search' if slot is None else 'verify'}) -> {st.get('stop')} boundary={st.get('boundary')}")
            state.save(); continue
        phase_at_ask, stop_before = st["phase"], st["stop"]
        used_before = state.used_clusters()
        spec = spec_for(cap, level)
        if contract.get("sg_mode") and cap not in ("goal_conditioned_planning", "plan_gap_filling"):   # 10-28 v15:L1-L3 的档由 sg 定(感知量 / 窗口 / 段数)
            import sg as _SG
            spec = _SG.spec_for(cap, level, clusters[0], contract=contract) or spec
        spec["phase"] = phase_at_ask
        if slot: spec["expect"] = slot["expect"]
        row = run_turn(store, state, contract, run_dir, pair, None, clusters, "DIAGNOSIS", mock=mock, difficulty=spec)
        v = row["verdict"]; reused = row.get("evidence_cluster_id") in used_before
        row["cluster_reused"] = reused
        if v in ("correct", "wrong"):
            st["invalid_streak"] = 0
            if phase_at_ask == "search":
                avail = sorted(set(levels_available(state, store, cap, rank) + [level]))
                row["stair_move"] = update_search(st, level, v, row["turn"], contract, avail, reused=reused)
            else:
                slot["verdict"] = v; slot["turn"] = row["turn"]
                if all(x["verdict"] is not None for x in st["verify"]):
                    st["phase"] = "done"
        else:
            st["invalid_streak"] += 1                   # 作废 / 证据未决的一轮:不计分、不动档,换一个 event 再出;只有连续作废达到上限才放弃这个 skill
            if st["invalid_streak"] >= int(contract.get("stair_invalid_limit", 3)):   # 10-28 晚(用户:被过滤的题不算分也不动档,继续问新的):上限可配,默认 3
                if phase_at_ask == "search" and st["boundary"] is None and st["trace"]:
                    st["boundary"] = round(statistics.mean(t["level"] for t in st["trace"][-2:]), 2); st["unconverged"] = True
                st["stop"] = st["stop"] or "examiner_failed"; st["phase"] = "done"
        just_stopped = st.get("stop") and not stop_before
        log(run_dir, f"  {state.layer} t{state.turn:02d} {cap:32s} L{level} {row['format'] or '-':13s} {phase_at_ask:6s}{' expect=' + slot['expect'] if slot else ''} -> {v}"
                     f"{' move=' + row['stair_move'] if row.get('stair_move') else ''}{' [reused event]' if reused else ''}"
                     f"{' | boundary=' + str(st['boundary']) + ' (' + str(st['stop']) + ')' if just_stopped else ''}")
        state.save()
    state.phase = "DONE"; state.save()
    log(run_dir, f"{state.layer}: {state.stop_reason} after {state.turn} turns; boundaries " +
        ", ".join(f"{c}={state.stair[c].get('boundary')}({state.stair[c].get('stop')})" for o, c in live))


# ------------------------------------------------------------------ 10-25 15:00:预算 6 → 12 续跑(用户定)
def reopen_for_budget(run_id, new_budget):
    """把因 budget 停下的 skill 重新打开继续搜(保留轨迹 / 当前档 / streak,清掉旧边界与验证计划);层状态改回 DIAGNOSIS。
    收敛(reversals / ceiling / floor)和 exhausted 的 skill 不动。返回 {layer: [skills reopened]}。"""
    import json as _json
    import p2config as _P
    out = {}
    for L in ("L1", "L2", "L3", "L4"):
        sp = _P.RUNS / run_id / L / "state.json"
        if not sp.exists(): continue
        s = _json.loads(sp.read_text()); stair = s.get("stair") or {}
        hit = []
        for sk, st in stair.items():
            if st.get("stop") == "budget" and len(st.get("trace") or []) < new_budget:
                st.update(phase="search", stop=None, boundary=None, unconverged=False, verify=[], invalid_streak=0); hit.append(sk)
        if hit:
            s.update(phase="DIAGNOSIS", stop_reason=None, confirmation=None, stair=stair)
            sp.write_text(_json.dumps(s, indent=1, ensure_ascii=False)); out[L] = hit
    return out


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) >= 3 and _sys.argv[1] == "reopen":
        for rid in _sys.argv[3:]:
            print(rid, reopen_for_budget(rid, int(_sys.argv[2])))
