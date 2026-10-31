"""Adaptive 诊断循环(plan §0.1)+ 停止 / 固定 CONFIRMATION 判定(plan §0.2)。
状态落盘到 runs/<run_id>/L<k>/{history.jsonl, hypotheses.jsonl, state.json, summary.json};同 run_id 重跑 = 续跑。"""
import json, math, random, time, collections, sys, hashlib
from pathlib import Path
import p2config as P
import retrieve, capmap, context as CX, examiner as EX, prompts
import scope as SC, chain
import staircase as ST            # 10-25 v8:skill 内难度阶梯(contract difficulty_mode = "staircase")
import sg as SG
_SYS_TOK, _TRIM_STATS = {}, []     # 10-28:Qwen examiner 裁剪用(每层系统提示 token 数;逐轮裁剪统计)                   # 10-28 v15:sub-goal 结构版(contract sg_mode)
from store import Store, read_jsonl, write_jsonl

LAYERS = ["L1", "L2", "L3", "L4"]
_SCOPE_BY_TASK = None          # run() 里由 scope.ensure 填(EgoPlan);其它数据集为空
_SG_PLAN = None                # 10-28 v15:sg.ensure 填的 {task_id: plan}
NEXT_STRATEGY = {"chance_error": "same_skill_new_event", "interference": "same_skill_cleaner_event",
                 "format_sensitivity": "same_event_new_format", "skill_unstable": "same_skill_new_event",
                 "lucky_pass": "same_skill_new_event"}      # 10-24 v7(contract followup_on_pass):答对也换 event 追问一次,防偶然对


def log(run_dir, msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(run_dir / "run.log", "a") as f:
        f.write(line + "\n")


# ------------------------------------------------------------------ state
class LayerState:
    def __init__(self, run_dir, layer, contract):
        self.dir = run_dir / layer; self.dir.mkdir(parents=True, exist_ok=True)
        self.layer, self.c = layer, contract
        self.history = read_jsonl(self.dir / "history.jsonl")
        self.hypotheses = read_jsonl(self.dir / "hypotheses.jsonl")
        st = self.dir / "state.json"
        s = json.loads(st.read_text()) if st.exists() else {}
        self.turn = s.get("turn", 0); self.phase = s.get("phase", "DIAGNOSIS")
        self.stop_reason = s.get("stop_reason"); self.solver_errors = s.get("solver_errors", 0)
        self.frozen_clusters = set(s.get("frozen_clusters", [])); self.consec_inconclusive = s.get("consec_inconclusive", 0)
        self.confirmation = s.get("confirmation")
        self.not_evaluated = s.get("not_evaluated", {})
        self.unresolved_by_skill = s.get("unresolved_by_skill", {})      # skill -> 连续 REQUEST_VERIFICATION / INCONCLUSIVE 次数
        self.examiner_errors = s.get("examiner_errors", 0)
        self.stair = s.get("stair") or {}                                  # v8:skill -> 阶梯状态
        self.pools = {}; self.skills = []; self.base_by = {}

    @property
    def scored(self):
        return [h for h in self.history if h["phase"] == "DIAGNOSIS" and h["verdict"] in ("correct", "wrong")]

    def used_clusters(self):
        return {h["evidence_cluster_id"] for h in self.history if h.get("evidence_cluster_id")} | self.frozen_clusters

    def save(self):
        write_jsonl(self.dir / "hypotheses.jsonl", self.hypotheses)
        (self.dir / "state.json").write_text(json.dumps({
            "turn": self.turn, "phase": self.phase, "stop_reason": self.stop_reason, "solver_errors": self.solver_errors,
            "frozen_clusters": sorted(self.frozen_clusters), "consec_inconclusive": self.consec_inconclusive,
            "confirmation": self.confirmation, "not_evaluated": self.not_evaluated,
            "unresolved_by_skill": self.unresolved_by_skill, "examiner_errors": self.examiner_errors,
            "stair": self.stair}, indent=1, ensure_ascii=False))

    def append_history(self, row):
        self.history.append(row)
        with open(self.dir / "history.jsonl", "a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def by_skill(self):
        out = {}
        for sk in self.skills:
            cap = sk[1]
            rows = [h for h in self.scored if h["capability_skill"] == cap]
            cl = collections.OrderedDict()
            for h in rows:
                cl.setdefault(h["evidence_cluster_id"], []).append(h)
            first = [v[0] for v in cl.values()]
            out[cap] = {"scored": len(rows), "correct": sum(h["verdict"] == "correct" for h in rows),
                        "clusters": len(cl), "cluster_first_correct": sum(h["verdict"] == "correct" for h in first),
                        "formats": dict(collections.Counter(h["format"] for h in rows)),
                        "open_hypotheses": [h["hypothesis_id"] for h in self.hypotheses if h["skill"] == cap and h["status"] == "open"],
                        "unused_clusters": len([c for c in self.pools.get(cap, []) if c["evidence_cluster_id"] not in self.used_clusters()])}
        return out

    def coverage(self):
        by = self.by_skill()
        dom = collections.Counter()
        for h in self.scored:
            dom[h.get("domain") or "?"] += 1
        return {"by_skill": by, "by_domain": dict(dom), "scored": len(self.scored),
                "correct": sum(h["verdict"] == "correct" for h in self.scored),
                "turns": self.turn, "not_evaluated": self.not_evaluated}


# ------------------------------------------------------------------ hypotheses
def _hid(skill, typ, turn):
    return f"h:{skill}:{typ}:{turn}"


def open_hypothesis(state, skill, typ, cluster_id, turn, note="", forbid_formats=None, orig_turn=None):
    ot = orig_turn or turn
    orig_row = next((x for x in state.history if x["turn"] == ot), None)
    h = {"hypothesis_id": _hid(skill, typ, turn), "skill": skill, "type": typ, "evidence_cluster_id": cluster_id,
         "original_turn": ot, "opened_turn": turn, "tests": [], "status": "open",
         "strategy_required": NEXT_STRATEGY[typ], "forbidden_formats": forbid_formats or [], "note": note,
         "original_scope_id": (orig_row or {}).get("scope_id"), "original_sample_id": (orig_row or {}).get("sample_id")}
    state.hypotheses.append(h)
    return h


def _pool_scores(state, skill):
    return sorted(c["interference"]["score"] for c in state.pools.get(skill, []))


def update_hypotheses(state, row, contract):
    """按 §0.1 规则:答错开假设;follow-up 结果判定并开下一级假设。"""
    if row["phase"] != "DIAGNOSIS" or row["verdict"] not in ("correct", "wrong"):
        return
    skill, turn = row["capability_skill"], row["turn"]
    maxt = contract["frozen_policy"]["confirmation"].get("max_hypothesis_tests", 3)
    h = next((x for x in state.hypotheses if x["hypothesis_id"] == row.get("tests_hypothesis") and x["status"] == "open"), None)
    ok = row["verdict"] == "correct"
    if h is None:
        if not ok and not any(x["skill"] == skill and x["status"] == "open" for x in state.hypotheses):
            open_hypothesis(state, skill, "chance_error", row["evidence_cluster_id"], turn, note="first wrong answer on this skill")
        elif ok and contract.get("followup_on_pass") and not any(x["skill"] == skill and (x["status"] == "open" or x["type"] == "lucky_pass") for x in state.hypotheses):
            # v7:每 skill 第一次答对也开一个假设,换一个 event(scope 内未问过的优先)再问一次;再对 = 通过成立,错 = 可能偶然对 -> 接 chance_error 链
            open_hypothesis(state, skill, "lucky_pass", row["evidence_cluster_id"], turn, note="first correct answer on this skill: verify on a fresh event")
        return
    h["tests"].append(turn)
    orig_cl = h["evidence_cluster_id"]
    orig_rows = [x for x in state.history if x["evidence_cluster_id"] == orig_cl and x["verdict"] == "wrong"]
    orig_formats = sorted({x["format"] for x in state.history if x["evidence_cluster_id"] == orig_cl})
    orig_score = next((c["interference"]["score"] for c in state.pools.get(skill, []) if c["evidence_cluster_id"] == orig_cl), None)
    scores = _pool_scores(state, skill)
    med = scores[len(scores) // 2] if scores else 0
    if h["type"] == "chance_error":
        if ok:
            h["status"] = "supported"; h["note"] = "new event answered correctly -> chance error"
        else:
            h["status"] = "refuted"
            if orig_score is not None and orig_score >= med and any(c["interference"]["score"] < orig_score for c in state.pools.get(skill, []) if c["evidence_cluster_id"] not in state.used_clusters()):
                open_hypothesis(state, skill, "interference", orig_cl, turn, orig_turn=h["original_turn"], note=f"orig interference {orig_score} >= pool median {med}")
            else:
                open_hypothesis(state, skill, "format_sensitivity", orig_cl, turn, orig_turn=h["original_turn"], forbid_formats=orig_formats)
    elif h["type"] == "interference":
        if ok:
            h["status"] = "supported"; h["note"] = "cleaner event answered correctly -> interference_sensitive"
        else:
            h["status"] = "refuted"
            open_hypothesis(state, skill, "format_sensitivity", orig_cl, turn, orig_turn=h["original_turn"], forbid_formats=orig_formats)
    elif h["type"] == "format_sensitivity":
        if ok:
            h["status"] = "supported"; h["note"] = "same event, new format answered correctly -> format_sensitive; original item needs_review"
            for x in orig_rows:
                x["needs_review"] = True
        else:
            h["status"] = "refuted"
            open_hypothesis(state, skill, "skill_unstable", orig_cl, turn, orig_turn=h["original_turn"])
    elif h["type"] == "lucky_pass":
        if ok:
            h["status"] = "refuted"; h["note"] = "fresh event also answered correctly -> pass holds (not lucky)"
        else:
            h["status"] = "supported"; h["note"] = "fresh event answered wrong -> original pass may be lucky"
            if not any(x["skill"] == skill and x["status"] == "open" for x in state.hypotheses):
                open_hypothesis(state, skill, "chance_error", row["evidence_cluster_id"], turn, note="wrong answer on the pass-verification event")
    elif h["type"] == "skill_unstable":
        wrong_tests = sum(1 for t in h["tests"] if any(x["turn"] == t and x["verdict"] == "wrong" for x in state.history))
        if wrong_tests >= 2:
            h["status"] = "supported"; h["note"] = f"{wrong_tests} further wrong answers on fresh events"
        elif len(h["tests"]) >= maxt:
            h["status"] = "refuted"; h["note"] = "mixed results on fresh events"
    if h["status"] == "open" and len(h["tests"]) >= maxt:
        h["status"] = "inconclusive"


def skill_verdicts(state, contract):
    pol = contract["frozen_policy"]["confirmation"]
    by = state.by_skill()
    out = {}
    if getattr(state, "stair", None):                                      # v8 阶梯:结论 = 边界档位剖面,不再是 stable_pass / unstable
        for cap, s in by.items():
            st = state.stair.get(cap)
            if cap in state.not_evaluated or not st:
                out[cap] = {"verdict": "not_evaluated", "reason": state.not_evaluated.get(cap, "no staircase state")}; continue
            sm = ST.summary(st)
            b = sm["boundary"]
            v = "not_started" if b is None else ("boundary>=4" if b > 4 else "boundary<1" if b < 1 else f"boundary {b}")
            out[cap] = {"verdict": v, "scored": s["scored"], "correct": s["correct"], "clusters": s["clusters"], "staircase": sm,
                        "turns": [h["turn"] for h in state.scored if h["capability_skill"] == cap]}
        return out
    for cap, s in by.items():
        if cap in state.not_evaluated:
            v = "evidence_unresolved" if state.not_evaluated[cap].startswith("evidence_unresolved") else "not_evaluated"
            out[cap] = {"verdict": v, "reason": state.not_evaluated[cap]}; continue
        hyps = [h for h in state.hypotheses if h["skill"] == cap]
        if s["scored"] == 0:
            out[cap] = {"verdict": "inconclusive", "reason": "no scored items"}; continue
        if s["open_hypotheses"]:
            out[cap] = {"verdict": "inconclusive", "reason": "open hypotheses", "hypotheses": s["open_hypotheses"]}; continue
        sup = {h["type"] for h in hyps if h["status"] == "supported"}
        invalid = sum(1 for h in state.history if h["capability_skill"] == cap and h["verdict"] == "item_invalid")
        wrong = s["clusters"] - s["cluster_first_correct"]
        # 被 chance_error 假设解释掉的错(换 event 后答对)不算能力问题
        explained = sum(1 for h in hyps if h["type"] == "chance_error" and h["status"] == "supported")
        explained = min(explained, max(1, int(0.2 * s["clusters"])))     # 偶然错最多抵消 1 个(或 20% cluster),反复偶然就不是偶然
        wrong_unexplained = max(0, wrong - explained)
        if s["clusters"] >= pol["min_distinct_clusters"] and wrong_unexplained == 0:
            v = "stable_pass"
        elif "skill_unstable" in sup or (s["clusters"] >= 3 and wrong / s["clusters"] >= 1 / 3):
            v = "unstable"
        elif "interference" in sup:
            v = "interference_sensitive"
        elif "format_sensitivity" in sup:
            v = "format_sensitive"
        elif invalid and invalid >= max(1, wrong):
            v = "item_defects_suspected"
        elif s["clusters"] < pol["min_distinct_clusters"]:
            v = "inconclusive"
        else:
            v = "mixed"
        out[cap] = {"verdict": v, "scored": s["scored"], "correct": s["correct"], "clusters": s["clusters"],
                    "cluster_first_correct": s["cluster_first_correct"], "wrong_explained_as_chance": explained,
                    "supported_hypotheses": sorted(sup),
                    "pass_verified_on_fresh_event": any(h["type"] == "lucky_pass" and h["status"] == "refuted" for h in hyps),
                    "turns": [h["turn"] for h in state.scored if h["capability_skill"] == cap]}
    return out


# ------------------------------------------------------------------ skill selection
def active_skills(store, layer, contract):
    enabled = set(contract.get("extension_registry", {}).get("enabled_skills", []))
    out = list(capmap.skills_for_layer(store.capmap, layer))
    for k, m in store.registry["skills"].items():
        if k in enabled and (m["layer"] == layer or layer in m["layer"].split("/")):
            out.append((k, k))
    inc = contract.get("include_skills")
    if inc:
        out = [(o, c) for o, c in out if c in inc or o in inc]
    excl = P.excluded_skills()                               # 10-27:data/skill_exclusions.json(contact 四个)全局不出题
    out = [(o, c) for o, c in out if c not in excl and o not in excl]
    return [(o, c) for o, c in out if retrieve.SKILL_NEEDS.get(c) is not None]


def base_for(state, contract, cap):
    """每 skill 基础题数:整数,或 "scope" = 该 skill 的 scope 条目数(封顶 per_skill_base_max)。"""
    b = contract.get("per_skill_base", 3)
    b = (contract.get("per_skill_base_by_skill") or {}).get(cap, b)        # 10-21:按 skill 覆盖(如只有 L4 用 "scope" = 每个决策点一题)
    if b == "scope":
        tids = sorted({c.get("sample_id") for c in state.pools.get(cap, []) if c.get("sample_id")})
        n = SC.n_entries(_SCOPE_BY_TASK, state.layer, cap, tids) if _SCOPE_BY_TASK else 0
        return max(1, min(contract.get("per_skill_base_max", 6), n or contract.get("per_skill_base_min", 2)))
    b = int(b)
    if contract.get("per_skill_base_per_sample"):      # 10-23:基础题数按样本数放大(每个样本每层每 skill 都要有题,history 才接得上)
        ns = len({c.get("sample_id") for c in state.pools.get(cap, []) if c.get("sample_id")}) or 1
        b = b * ns
    return b


def build_pools(store, state, contract, max_per_video=12):
    if contract.get("sg_mode"):                                   # 10-28 v15:按 sub-goal / event / relation / 决策点建 pool
        pools = SG.build_pools(store, contract, _SG_PLAN or {}, [c for o, c in state.skills], state.layer, seed=contract["seed"])
        for orig, cap in state.skills:
            state.pools[cap] = pools.get(cap, [])
            if not state.pools[cap]:
                state.not_evaluated[cap] = "no expected-event cluster for this skill on this task (sg mode)"
        return
    for orig, cap in state.skills:
        cl = []
        task_only = contract.get("task_only_clusters") and contract.get("task_sample_id")      # 10-27 v13:只用本 task 时间段内的 cluster(先多取再过滤)
        for vid in contract["videos"]:
            cl += retrieve.clusters(store, vid, cap, seed=contract["seed"], max_clusters=(200 if task_only else max_per_video),
                                    modalities=contract["solver_input_spec"]["modalities"], min_gap=contract.get("cluster_min_gap", 10.0))
        if task_only:
            cl = [x for x in cl if x.get("sample_id") == contract["task_sample_id"]]
        rng = random.Random(f"{contract['seed']}|{state.layer}|{cap}")
        rng.shuffle(cl)
        state.pools[cap] = cl
        if not cl:
            state.not_evaluated[cap] = "no verified evidence cluster for this skill on the run's videos"
    live = [c for o, c in state.skills if c not in state.not_evaluated]
    if contract.get("budget_mode") == "per_skill":            # 层预算 = Σ_skill(基础 + 追问);基础可按 scope 条目数定
        state.base_by = {c: base_for(state, contract, c) for c in live}
        contract["n_per_layer"] = max(1, sum(state.base_by[c] + contract.get("per_skill_followups", 3) for c in live))
        contract["turn_budget_per_layer"] = int(contract["n_per_layer"] * 1.5) + 3


def pick_skill(state, contract):
    """返回 (skill_pair, hypothesis|None)。有 open 假设的 skill 优先;其次 scored 最少。"""
    by = state.by_skill()
    used = state.used_clusters()
    n = contract["n_per_layer"]
    live = [(o, c) for o, c in state.skills if c not in state.not_evaluated]
    if not live:
        return None, None
    per_skill = contract.get("budget_mode") == "per_skill"
    fu = contract.get("per_skill_followups", 3)
    base_by = getattr(state, "base_by", None) or {}
    def base_of(c):
        if c in base_by: return base_by[c]
        b = (contract.get("per_skill_base_by_skill") or {}).get(c, contract.get("per_skill_base", 3))
        return int(b) if b != "scope" else 3
    cap_per = None if per_skill else math.ceil(n / len(live)) + 3
    followups = collections.Counter(h["capability_skill"] for h in state.scored if h.get("tests_hypothesis"))
    for h in sorted([h for h in state.hypotheses if h["status"] == "open"], key=lambda h: h["opened_turn"]):
        pair = next(((o, c) for o, c in live if c == h["skill"]), None)
        if per_skill and followups[h["skill"]] >= fu:          # 追问额度用完:假设记 inconclusive,不再追
            h["status"] = "inconclusive"; h["note"] = (h.get("note") or "") + " | follow-up budget exhausted"
            continue
        if pair and pool_for(state, pair[1], h):
            return pair, h
    avail = [(by[c]["scored"], c, (o, c)) for o, c in live if any(x["evidence_cluster_id"] not in used for x in state.pools[c])]
    if per_skill:
        # 基础题:先把每个 skill 补到 base 个独立 cluster;再按 scored < cap 填
        need_base = [t for t in avail if by[t[1]]["clusters"] < base_of(t[1])]
        if need_base:
            need_base.sort(key=lambda t: (by[t[1]]["clusters"] - base_of(t[1]), t[1])); return need_base[0][2], None
    cands = [t for t in avail if t[0] < (base_of(t[1]) + fu if per_skill else cap_per)]
    if not cands:
        cands = avail                      # 其它 skill 都耗尽时放开单 skill 上限,把预算用在还有证据的 skill 上
    if not cands:
        return None, None
    cands.sort(key=lambda t: (t[0], t[1]))
    return cands[0][2], None


def scope_tier(state, cap, x):
    """10-27 v13:0 = 命中本 skill 未问过的 scope 条目,1 = 只命中问过的条目,2 = 无条目。"""
    if not (_SCOPE_BY_TASK and x.get("sample_id")):
        return 2
    used_sid = {(h.get("sample_id"), h.get("scope_id")) for h in state.history if h["capability_skill"] == cap and h.get("scope_id")}
    ents = SC.cluster_entries(_SCOPE_BY_TASK, state.layer, cap, x)
    return 0 if any((x.get("sample_id"), s_) not in used_sid for s_ in ents) else (1 if ents else 2)


def _rank(state, cap, fresh):
    """10-14:scope 命中的 cluster 排前(scope_mode prefer / strict),其次下层历史更深的样本排前(chain_prefer_history);稳定排序。"""
    c = state.c
    if not fresh:
        return fresh
    key = []
    used_sid = {(h.get("sample_id"), h.get("scope_id")) for h in state.history if h["capability_skill"] == cap and h.get("scope_id")}   # 10-23:按 (样本, 条目) 记,scope_id 跨样本重名
    for x in fresh:
        hit = 0
        if _SCOPE_BY_TASK and c.get("scope_mode", "prefer") != "off" and x.get("sample_id"):
            ents = SC.cluster_entries(_SCOPE_BY_TASK, state.layer, cap, x)
            hit = len([s_ for s_ in ents if (x.get("sample_id"), s_) not in used_sid]) + (0.5 if ents else 0)    # 未问过的条目越多越靠前;只含问过的排在无条目之前
        d = chain.depth(state.dir.parent, state.layer, x["sample_id"]) if (c.get("chain_prefer_history") and x.get("sample_id")) else 0
        nv = sum(1 for h in state.history if h["capability_skill"] == cap and h.get("video_id") == x.get("video_id") and h.get("verdict") in ("correct", "wrong")) \
             if c.get("spread_videos") else 0                                  # 10-21:spread_videos = 先问本 skill 还没问过(或问得少)的视频
        key.append((nv, -hit, -d))
    order = sorted(range(len(fresh)), key=lambda i: key[i])
    out = [fresh[i] for i in order]
    if c.get("scope_mode") == "strict":
        hits = [fresh[i] for i in order if key[i][0] < 0]
        out = hits or out
    return out


def pool_for(state, cap, hyp, k=2):
    used = state.used_clusters()
    pool = state.pools.get(cap, [])
    if hyp is None or hyp["type"] in ("chance_error", "skill_unstable", "lucky_pass"):
        fresh = _rank(state, cap, [c for c in pool if c["evidence_cluster_id"] not in used])      # _rank:scope 内未问过的条目优先,其次 scope 外
        if hyp is not None:
            failed_vids = {h["video_id"] for h in state.history if h["capability_skill"] == cap and h["verdict"] == "wrong"}
            fresh.sort(key=lambda c: c["video_id"] in failed_vids)
        return fresh[:k]
    if hyp["type"] == "interference":
        orig = next((c for c in pool if c["evidence_cluster_id"] == hyp["evidence_cluster_id"]), None)
        if orig is None:
            return []
        fresh = [c for c in pool if c["evidence_cluster_id"] not in used and c["interference"]["score"] < orig["interference"]["score"]]
        fresh.sort(key=lambda c: c["interference"]["score"])
        return fresh[:k]
    if hyp["type"] == "format_sensitivity":
        orig = next((c for c in pool if c["evidence_cluster_id"] == hyp["evidence_cluster_id"]), None)
        return [orig] if orig and orig["evidence_cluster_id"] not in state.frozen_clusters else []
    return []


# ------------------------------------------------------------------ decide (§0.2)
def decide(state, contract):
    pol = contract["frozen_policy"]["confirmation"]
    live = [c for o, c in state.skills if c not in state.not_evaluated]
    if not live:
        return "STOP", "STOP_INSUFFICIENT_EVIDENCE"
    if state.solver_errors >= contract["max_solver_errors"]:
        return "STOP", "STOP_SOLVER_ERRORS"
    if state.examiner_errors >= 5:
        return "STOP", "STOP_EXAMINER_ERRORS"
    # 某 skill 连续 3 次 REQUEST_VERIFICATION / INCONCLUSIVE -> 该 skill evidence_unresolved(移出候选),其它 skill 继续
    for cap, n in list(state.unresolved_by_skill.items()):
        if n >= 3 and cap not in state.not_evaluated:
            reqs = [h.get("unresolved_issue") for h in state.history if h["capability_skill"] == cap and h["verdict"] in ("evidence_unresolved", "inconclusive")]
            state.not_evaluated[cap] = "evidence_unresolved: examiner requested verification 3x: " + " | ".join(str(r)[:160] for r in reqs[-3:])
            live = [c for o, c in state.skills if c not in state.not_evaluated]
            if not live:
                return "STOP", "STOP_EXAMINER_INCONCLUSIVE"
    n_scored, budget_left = len(state.scored), state.turn < contract["turn_budget_per_layer"]
    if n_scored < contract["n_per_layer"] and budget_left:
        pair, hyp = pick_skill(state, contract)
        if pair is not None:
            return "CONTINUE", None
    # 诊断结束(预算满 / 无可继续的 skill):开着的假设 -> inconclusive
    for h in state.hypotheses:
        if h["status"] == "open":
            h["status"] = "inconclusive"; h["note"] = (h.get("note") or "") + " | budget or evidence exhausted"
    verdicts = skill_verdicts(state, contract)
    used = state.used_clusters()
    confirmable = [c for c, v in verdicts.items() if v["verdict"] not in ("not_evaluated", "inconclusive", "evidence_unresolved")
                   and len([x for x in state.pools[c] if x["evidence_cluster_id"] not in used]) >= 1]
    if confirmable:
        return "BEGIN_CONFIRMATION", None
    return "STOP", "STOP_BUDGET" if not budget_left or n_scored >= contract["n_per_layer"] else "STOP_NO_DIAGNOSTIC_VALUE"


# ------------------------------------------------------------------ one turn
def _mapping(store, orig, cap, core):
    if orig in store.capmap["skills"]:
        return capmap.resolve(store.capmap, orig, core)
    m = store.registry["skills"][orig]
    return {"original_skill": orig, "capability_layer": m["layer"], "capability_skill": cap,
            "classification_status": m.get("status", "provisional"), "lifecycle": "extension", "relation_operation": None}


def _history_row(state, layer, cand, pair, cluster, hyp, phase, verdict, sol=None, gr=None, errors=None, difficulty=None):
    out = cand["output"] if cand else {}
    pub = (out.get("public") or {}) if isinstance(out.get("public"), dict) else {}
    pri = (out.get("private") or {}) if isinstance(out.get("private"), dict) else {}
    return {"turn": state.turn, "phase": phase, "layer": layer, "candidate_id": cand["candidate_id"] if cand else None,
            "item_id": cand["candidate_id"] if cand else None, "item_version": 1,
            "original_skill": pair[0], "capability_skill": pair[1], "domain": pri.get("domain"),
            "evidence_cluster_id": cluster["evidence_cluster_id"] if cluster else out.get("evidence_cluster_id"),
            "video_id": cluster["video_id"] if cluster else None,
            "format": pub.get("format"), "strategy": out.get("strategy"), "tests_hypothesis": hyp["hypothesis_id"] if hyp else None,
            "question": pub.get("question"), "options": pub.get("options"), "media_refs": pub.get("media_refs"),
            "reference": pri.get("proposed_reference_answer"), "solver_answer": sol["raw"] if sol else None,
            "parsed": gr["parsed"] if gr else None, "verdict": verdict, "score": gr["score"] if gr else None,
            "judge": gr["judge"] if gr else None, "judge_reason": gr.get("reason") if gr else None,
            "plan_eval": gr.get("plan_eval") if gr else None,
            "failed_rubric_criteria": [], "unresolved_issue": out.get("unresolved_issue") or (out.get("verification_request") if out.get("action") == "REQUEST_VERIFICATION" else None),
            "check_errors": errors or [], "media": sol["media"] if sol else None, "model": sol["model"] if sol else None,
            "media_flags": (sol or {}).get("media_flags", []),
            "interference_score": cluster["interference"]["score"] if cluster else None,
            "sample_id": cluster.get("sample_id") if cluster else None, "scope_id": pri.get("scope_id"),
            "causal_cause_idx": (pri.get("causal") or {}).get("cause_idx") if isinstance(pri.get("causal"), dict) else None,
            "solver_prompt": sol.get("prompt") if sol else None, "history_used": sol.get("history_used") if sol else None,
            **({"sg": {"idx": cluster["sg"].get("idx"), "kind": cluster["sg"].get("kind"), "tier": cluster["sg"].get("tier"), "rel_id": cluster["sg"].get("rel_id"),
                       "event_id": pri.get("sg_event_id"), "n_segments": cluster["sg"].get("n_segments"),
                       "window_sec": round(sum(float(w[1]) - float(w[0]) for m_ in (pub.get("media_refs") or []) for w in (m_.get("windows") or []) if len(w) == 2), 1)}} if cluster and cluster.get("sg") else {}),
            "selection_reason": out.get("selection_reason"), "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **({"difficulty_level": difficulty.get("level"), "difficulty_format": difficulty.get("format"), "stair_phase": difficulty.get("phase"),
                "stair_expect": difficulty.get("expect")} if difficulty else {})}


SEED_SKILL_MAP = {   # 旧 subtype -> capability skill(seed items 给 Examiner 参考)
    "easy_tactile_property": ["tactile_check_recognition", "tactile_property_inference"], "low_tactile_sound": ["sound_tactile_binding"],
    "low_tactile_visual": ["visual_tactile_binding"], "medium_tactile_infer": ["tactile_hidden_state_inference"],
    "medium_tactile_relation": ["tactile_relation_inference", "tactile_aware_planning"], "needs_touch_control": ["needs_touch_awareness"],
    "high_tactile_next": ["next_action_prediction", "tactile_aware_planning"], "noav_control": [],
}


def seed_items_for(store, cap, clusters, limit=3):
    core = {r["evidence_id"] for c in clusters for r in c["core"]}
    out = []
    for it in store.items:
        subs = SEED_SKILL_MAP.get(it.get("original_subtype") or "", None)
        if subs is not None and cap not in subs:
            continue
        if subs is None and it.get("original_subtype") != cap:
            continue
        refs = {(r if isinstance(r, str) else r.get("evidence_id")) for r in (it["private"].get("evidence_refs") or [])}
        if not refs & core:
            continue
        pri = it["private"]
        out.append({"item_id": it["item_id"], "original_subtype": it.get("original_subtype"), "question": it["public"]["question"],
                    "format": it["public"]["format"], "options": it["public"].get("options"), "gold_answer": pri.get("gold_answer"),
                    "gold_verification_status": pri.get("gold_verification_status"), "verification_method": pri.get("verification_method"),
                    "input_window": it["public"].get("media_refs"), "observation_cutoff": it["public"].get("observation_cutoff"),
                    "task_conditions": it["public"].get("task_conditions"), "evidence_refs": sorted(refs & core),
                    "note": "existing human-written QA; valid only for its original question / window / format"})
        if len(out) >= limit:
            break
    return out


def run_turn(store, state, contract, run_dir, pair, hyp, clusters, phase, mock=None, node=None, difficulty=None):
    """一轮:build_context -> Examiner -> check(重试一次)-> Solver -> grade -> history。返回 history row。
    node(10-22 题树):本轮只为这个节点出题;history 只带它的子节点;row/cand 记 tree 字段。"""
    import solver as SV, grade as GR
    layer = state.layer; orig, cap = pair
    state.turn += 1
    mapping = _mapping(store, orig, cap, clusters[0]["core"])
    hyp_view = None
    if hyp:
        hyp_view = {k: hyp[k] for k in ("hypothesis_id", "type", "strategy_required", "forbidden_formats", "note")}
        hyp_view["original_cluster_id"] = hyp["evidence_cluster_id"]; hyp_view["original_scope_id"] = hyp.get("original_scope_id"); hyp_view["original_sample_id"] = hyp.get("original_sample_id")
    rb = {"scored_items_remaining": contract["n_per_layer"] - len(state.scored), "turns_remaining": contract["turn_budget_per_layer"] - state.turn}
    st_view = {"history": state.history, "hypotheses": state.hypotheses, "coverage": state.coverage(), "remaining_budget": rb,
               "confirmation_slot": state.confirmation.get("slot") if (phase == "CONFIRMATION" and state.confirmation) else None}
    seeds = seed_items_for(store, cap, clusters) if phase == "DIAGNOSIS" else []
    used_sid = [(h.get("sample_id"), h.get("scope_id")) for h in state.history if h["capability_skill"] == cap and h.get("scope_id") and h["verdict"] in ("correct", "wrong")]
    ctx = CX.build_context(contract, layer, pair, mapping, clusters, store, st_view, phase=phase, hypothesis=hyp_view, seed_items=seeds,
                           scope_by_task=_SCOPE_BY_TASK, used_scope_ids=used_sid, tree_node=node)
    if phase == "CONFIRMATION":
        ctx = CX.strip_for_confirmation(ctx)
    if difficulty:                                     # v8:controller 定本题的档(题型 / 窗长),Examiner 与校验器都看它
        ctx["difficulty"] = difficulty
    if contract.get("examiner_backend") == "qwen_http" and not contract.get("sg_mode"):   # 10-28(用户定):Qwen 出题时把输入裁到 ≤ 50k token;落盘的 context 就是 Examiner 看到的
        if layer not in _SYS_TOK:
            _SYS_TOK[layer] = CX.n_tokens(prompts.system_prompt(layer, EX._prompts(contract)))
        ctx, _ts = CX.trim_for_budget(ctx, contract, _SYS_TOK[layer])
        if _ts["tok_before"] != _ts["tok_after"] or _ts["hist_before"] != _ts["hist_after"]:
            log(run_dir, f"  {layer} turn {state.turn} qwen-ctx {_ts['tok_before']}->{_ts['tok_after']} tok (budget {_ts['budget']}); context recs {_ts['ctx_before']}->{_ts['ctx_after']}, history {_ts['hist_before']}->{_ts['hist_after']}, clusters {_ts['clusters_before']}->{_ts['clusters_after']}")
        _TRIM_STATS.append({"layer": layer, "turn": state.turn, **_ts})
    (run_dir / "contexts").mkdir(exist_ok=True)
    (run_dir / "contexts" / f"{layer}_{state.turn:03d}.json").write_text(json.dumps(ctx, ensure_ascii=False))
    ph = prompts.prompt_hash(layer, EX._prompts(contract))
    errors, out, u, cand = [], None, {}, None
    for attempt in range(int(contract.get("examiner_attempts", 2))):
        if mock:
            out, u = mock.examine(ctx, clusters, hyp), {}
        else:
            ctx_try = dict(ctx)
            if errors:
                ctx_try["item_validation_result"] = {"previous_output_rejected": True, "errors": errors}
            try:
                out, u = EX.propose(ctx_try, layer, contract, run_dir=run_dir)
            except Exception as e:              # 畸形 JSON / 截断 / 网关错误:不让进程崩,记错误后重试一次
                msg = f"examiner_call_failed: {str(e)[:200]}"
                log(run_dir, f"  {layer} turn {state.turn} {msg}")
                out, u = {"action": "INCONCLUSIVE", "selection_reason": msg, "public": None, "private": None, "_examiner_error": True}, {}
                errors = [msg]
                if any(x in msg for x in ("429", "404", "RESOURCE_EXHAUSTED", "NOT_FOUND")):
                    break
                continue
        errors = EX.check_output(out, ctx, store)
        if phase == "DIAGNOSIS" and out.get("action") == "BEGIN_CONFIRMATION":
            errors = ["BEGIN_CONFIRMATION is not accepted: the controller decides phase transitions from the frozen budget, "
                      "and this skill's diagnostic budget is not exhausted. Propose a diagnostic item from the offered clusters "
                      "(PROPOSE_DIAGNOSTIC), or REQUEST_VERIFICATION only if no offered cluster can support a valid item."]
        if hyp and out.get("action") in ("PROPOSE_DIAGNOSTIC",):
            if out.get("strategy") != hyp["strategy_required"]:
                errors.append(f"strategy must be {hyp['strategy_required']} for hypothesis {hyp['hypothesis_id']}")
            if hyp["type"] == "format_sensitivity" and (out.get("public") or {}).get("format") in hyp["forbidden_formats"]:
                errors.append(f"format must differ from {hyp['forbidden_formats']}")
            if hyp["type"] in ("chance_error", "interference", "skill_unstable", "lucky_pass") and out.get("evidence_cluster_id") == hyp["evidence_cluster_id"]:
                errors.append("must use a different evidence cluster than the original item's")
        if phase == "CONFIRMATION" and out.get("action") == "PROPOSE_CONFIRMATION":
            want = contract["frozen_policy"]["confirmation"]["format"]
            if (out.get("public") or {}).get("format") != want:
                errors.append(f"confirmation format must be {want}")
        if not errors:
            break
        log(run_dir, f"  {layer} turn {state.turn} examiner output rejected (attempt {attempt+1}): {errors[:3]}")
    cl_used = next((c for c in clusters if c["evidence_cluster_id"] == out.get("evidence_cluster_id")), clusters[0])
    cand = EX.make_candidate(out, ctx, contract, layer, state.turn, u, ph, cl_used, errors)
    if difficulty: cand["difficulty"] = difficulty
    if cl_used.get("sg") and isinstance((out.get("public") or None), dict) and (cl_used["sg"].get("n_segments") or 1) > 1:   # 10-28 v15:多段拼接给 Solver 的说明(乱序 / 顺序)
        out["public"]["sg_item"] = {"segments": cl_used["sg"]["n_segments"], "shuffled": bool(cl_used["sg"].get("segments_shuffled"))}
    if node:
        cand["tree_node"] = {k: node.get(k) for k in ("node_id", "layer", "skill", "event_refs", "depends_on", "why_needed", "task_id", "cutoff_step", "dp_cutoff")}
    with open(run_dir / "candidates.jsonl", "a") as f:        # 每个 run 自己一份;report 时合并进 data/candidates.jsonl
        f.write(json.dumps(cand, ensure_ascii=False) + "\n")
    act = out.get("action")
    if out.get("_examiner_error"):
        state.examiner_errors += 1
        row = _history_row(state, layer, cand, pair, cl_used, hyp, phase, "env_failure", errors=errors, difficulty=difficulty)
    elif act == "BEGIN_CONFIRMATION":          # Examiner 两次都想提前进确认:记 examiner_declined,不计分、不计入核验计数
        state.examiner_errors = 0
        row = _history_row(state, layer, cand, pair, cl_used, hyp, phase, "examiner_declined", errors=errors, difficulty=difficulty)
    elif errors:
        state.examiner_errors = 0
        row = _history_row(state, layer, cand, pair, cl_used, hyp, phase, "item_invalid", errors=errors, difficulty=difficulty)
        state.consec_inconclusive = 0
    elif act in ("PROPOSE_DIAGNOSTIC", "PROPOSE_CONFIRMATION"):
        state.examiner_errors = 0
        hist = None; gr_pre = None
        if contract.get("history_mode") in ("self", "gold") and cl_used.get("sample_id"):
            only = node["depends_on"] if (node and contract.get("history_scope") == "tree") else None     # 10-22 题树:只带子节点
            hist = chain.history_for(run_dir, layer, cl_used["sample_id"], contract["history_mode"], cap=contract.get("history_cap", 12),
                                     exclude_same_answer=contract.get("history_exclude_same_answer", True), current=cand,
                                     respect_cutoff=contract.get("history_respect_cutoff", False), only_scope_ids=only, only_base=contract.get("history_only_base", False),
                                     label=contract.get("history_label"), select=contract.get("history_select"), per_layer=contract.get("history_per_layer", 8),
                                     per_subgoal=contract.get("history_per_subgoal", 6), render=contract.get("history_render", "full"),
                                     event_ids=([e["event_id"] for e in (cl_used.get("sg") or {}).get("events", [])] if layer != "L4" else None))
        try:
            n_rep = int(contract.get("solver_reps", 1))
            if mock:
                sol = mock.solve(cand, history_text=hist["text"] if hist else None)
            elif n_rep > 1:                              # 10-22:self 臂也多次重答取多数
                sol, gr_pre, reps = chain.solve_reps(cand, contract, store, run_dir, hist["text"] if hist else None, n_rep); sol["reps"] = reps
            else:
                sol = SV.solve(cand, contract, store, run_dir=run_dir, history_text=hist["text"] if hist else None)
            if hist:
                sol["history_used"] = {k: v for k, v in hist.items() if k != "text"}
            state.solver_errors = 0
        except Exception as e:
            state.solver_errors += 1
            log(run_dir, f"  {layer} turn {state.turn} solver error #{state.solver_errors}: {str(e)[:160]}")
            row = _history_row(state, layer, cand, pair, cl_used, hyp, phase, "env_failure", errors=[str(e)[:200]], difficulty=difficulty)
            state.append_history(row); state.save()
            return row
        gr = gr_pre or (mock.grade(cand, sol) if mock else GR.grade(cand, sol, contract, run_dir=run_dir))
        row = _history_row(state, layer, cand, pair, cl_used, hyp, phase, gr["verdict"], sol=sol, gr=gr, difficulty=difficulty)
        if sol.get("reps"): row["reps"] = sol["reps"]
        state.consec_inconclusive = 0; state.unresolved_by_skill[cap] = 0
    elif act == "REQUEST_VERIFICATION":
        row = _history_row(state, layer, cand, pair, cl_used, hyp, phase, "evidence_unresolved", difficulty=difficulty)
        state.frozen_clusters.add(cl_used["evidence_cluster_id"])
        state.consec_inconclusive += 1; state.unresolved_by_skill[cap] = state.unresolved_by_skill.get(cap, 0) + 1
        if phase == "DIAGNOSIS":
            h2 = open_hypothesis(state, cap, "chance_error", cl_used["evidence_cluster_id"], state.turn) if False else None
            hd = {"hypothesis_id": _hid(cap, "item_defect", state.turn), "skill": cap, "type": "item_defect",
                  "evidence_cluster_id": cl_used["evidence_cluster_id"], "original_turn": state.turn, "opened_turn": state.turn,
                  "tests": [], "status": "supported", "strategy_required": "request_verification", "forbidden_formats": [],
                  "note": str(out.get("verification_request"))[:300]}
            state.hypotheses.append(hd)
            for x in state.history:
                if x["evidence_cluster_id"] == cl_used["evidence_cluster_id"] and x["verdict"] == "wrong":
                    x["needs_review"] = True
            if hyp and hyp["status"] == "open":
                hyp["status"] = "inconclusive"; hyp["note"] = "examiner requested verification"
    else:  # INCONCLUSIVE / BEGIN_CONFIRMATION(由 controller 决定,这里只记录)
        row = _history_row(state, layer, cand, pair, cl_used, hyp, phase, "inconclusive", difficulty=difficulty)
        state.consec_inconclusive += 1; state.unresolved_by_skill[cap] = state.unresolved_by_skill.get(cap, 0) + 1
    if node:
        row["tree"] = {k: node.get(k) for k in ("node_id", "depends_on", "task_id", "cutoff_step", "dp_cutoff", "why_needed")}
    state.append_history(row)
    if phase == "DIAGNOSIS" and not difficulty:        # 阶梯模式不用假设链,升降由 staircase 决定
        update_hypotheses(state, row, contract)
    state.save()
    return row


# ------------------------------------------------------------------ confirmation
def run_confirmation(store, state, contract, run_dir, mock=None):
    pol = contract["frozen_policy"]["confirmation"]
    layer = state.layer
    verdicts = skill_verdicts(state, contract)
    if state.confirmation is None:
        rng = random.Random(f"{contract['seed']}|{layer}|confirmation")
        used = state.used_clusters()
        slots = []
        for cap, v in verdicts.items():
            if v["verdict"] in ("not_evaluated", "inconclusive", "evidence_unresolved"):
                continue
            fresh = [c for c in state.pools[cap] if c["evidence_cluster_id"] not in used]
            rng.shuffle(fresh)
            fresh = _rank(state, cap, fresh)                  # 确认题也优先含未问过 scope 条目的 cluster
            picked = fresh[: pol["items_per_skill"]]
            if len(picked) < pol["items_per_skill"]:
                v["confirmation_note"] = f"confirmation_not_filled: only {len(picked)} fresh clusters"
            for c in picked:
                slots.append({"skill": cap, "evidence_cluster_id": c["evidence_cluster_id"], "format": pol["format"], "done": False})
        slots = slots[: pol.get("max_items", 12)]
        state.confirmation = {"slots": slots, "diagnosis_verdicts": verdicts, "results": {}}
        state.phase = "CONFIRMATION"; state.save()
        log(run_dir, f"{layer}: BEGIN_CONFIRMATION with {len(slots)} slots over {len({s['skill'] for s in slots})} skills")
    for slot in state.confirmation["slots"]:
        if slot["done"]:
            continue
        cap = slot["skill"]; pair = next((o, c) for o, c in state.skills if c == cap)
        cl = next((c for c in state.pools[cap] if c["evidence_cluster_id"] == slot["evidence_cluster_id"]), None)
        if cl is None:
            slot["done"] = True; slot["verdict"] = "slot_missing"; continue
        state.confirmation["slot"] = slot
        row = run_turn(store, state, contract, run_dir, pair, None, [cl], "CONFIRMATION", mock=mock)
        slot["done"] = True; slot["verdict"] = row["verdict"]; slot["turn"] = row["turn"]
        state.save()
    res = {}
    for cap in {s["skill"] for s in state.confirmation["slots"]}:
        rows = [s for s in state.confirmation["slots"] if s["skill"] == cap and s["verdict"] in ("correct", "wrong")]
        n_ok = sum(1 for s in rows if s["verdict"] == "correct")
        acc = n_ok / len(rows) if rows else None
        res[cap] = {"n": len(rows), "correct": n_ok, "acc": acc,
                    "result": None if not rows else ("confirmed_pass" if acc >= pol["pass_threshold"] else "confirmed_fail"),
                    "not_filled": len(rows) < pol["items_per_skill"]}
    state.confirmation["results"] = res
    state.phase = "DONE"; state.save()
    return res


# ------------------------------------------------------------------ layer loop
def run_layer(store, state, contract, run_dir, mock=None):
    layer = state.layer
    state.skills = active_skills(store, layer, contract)
    build_pools(store, state, contract)
    log(run_dir, f"{layer}: skills {[c for o, c in state.skills]}; pools {{{', '.join(f'{c}:{len(state.pools[c])}' for o, c in state.skills)}}}; NOT_EVALUATED {sorted(state.not_evaluated)}")
    if state.phase == "DONE":
        log(run_dir, f"{layer}: already done ({state.stop_reason})"); return
    if contract.get("include_skills") and not state.skills:
        state.stop_reason = "SKIPPED_BY_CONTRACT"; state.phase = "DONE"; state.save(); write_summary(state, contract)
        log(run_dir, f"{layer}: SKIPPED_BY_CONTRACT (no include_skills in this layer)"); return
    if contract.get("difficulty_mode") == "staircase":                      # v8
        ST.run_layer(store, state, contract, run_dir, run_turn=run_turn, log=log, rank=_rank, mock=mock)
        write_summary(state, contract); return
    while state.phase == "DIAGNOSIS":
        act, reason = decide(state, contract)
        if act == "STOP":
            state.stop_reason = reason; state.phase = "DONE"; state.save()
            log(run_dir, f"{layer}: {reason} after {state.turn} turns, {len(state.scored)} scored"); break
        if act == "BEGIN_CONFIRMATION":
            state.stop_reason = "DIAGNOSIS_COMPLETE"; break
        pair, hyp = pick_skill(state, contract)
        clusters = pool_for(state, pair[1], hyp)
        if not clusters:
            if hyp: hyp["status"] = "inconclusive"; hyp["note"] = "no suitable cluster for required strategy"
            state.save(); continue
        row = run_turn(store, state, contract, run_dir, pair, hyp, clusters, "DIAGNOSIS", mock=mock)
        log(run_dir, f"  {layer} t{state.turn:02d} {pair[1]:32s} {row['format'] or '-':13s} {row['strategy'] or '-':24s} -> {row['verdict']}"
                     f"{' [h:' + hyp['type'] + ']' if hyp else ''} scored={len(state.scored)}")
    if state.phase in ("CONFIRMATION",) or state.stop_reason == "DIAGNOSIS_COMPLETE":
        run_confirmation(store, state, contract, run_dir, mock=mock)
    write_summary(state, contract)


def write_summary(state, contract):
    sc = state.scored
    cl = collections.OrderedDict()
    for h in sc:
        cl.setdefault(h["evidence_cluster_id"], []).append(h)
    first = [v[0] for v in cl.values()]
    s = {"layer": state.layer, "stop_reason": state.stop_reason, "phase": state.phase, "turns": state.turn,
         "scored": len(sc), "correct": sum(h["verdict"] == "correct" for h in sc),
         "raw_acc": round(sum(h["verdict"] == "correct" for h in sc) / len(sc), 3) if sc else None,
         "cluster_dedup_acc": round(sum(h["verdict"] == "correct" for h in first) / len(first), 3) if first else None,
         "followup_items": sum(1 for h in sc if h.get("tests_hypothesis")),
         "by_verdict": dict(collections.Counter(h["verdict"] for h in state.history if h["phase"] == "DIAGNOSIS")),
         "by_format": dict(collections.Counter(h["format"] for h in sc)),
         "by_skill": skill_verdicts(state, contract),
         "stair": {c: ST.summary(st) for c, st in (getattr(state, "stair", None) or {}).items()} or None,
         "hypotheses": state.hypotheses,
         "confirmation": state.confirmation and {"results": state.confirmation.get("results"), "slots": state.confirmation.get("slots")},
         "not_evaluated": state.not_evaluated}
    (state.dir / "summary.json").write_text(json.dumps(s, indent=1, ensure_ascii=False))
    return s


def resummarize(contract, layers=None):
    """用当前规则重算已完成层的 summary.json(不调模型)。"""
    store = Store()
    for layer in (layers or LAYERS):
        st = LayerState(P.RUNS / contract["run_id"], layer, contract)
        if not st.history and st.phase != "DONE":
            continue
        st.skills = active_skills(store, layer, contract); build_pools(store, st, contract)
        write_summary(st, contract); print(f"{contract['run_id']}/{layer}: summary rewritten ({st.phase}, {len(st.scored)} scored)")


def reopen(run_id, layer):
    """把已 STOP 的层重新打开(保留 history),下次 run 从 DIAGNOSIS 续跑。"""
    d = P.RUNS / run_id / layer; st = d / "state.json"
    s = json.loads(st.read_text())
    s.update(phase="DIAGNOSIS", stop_reason=None, consec_inconclusive=0, confirmation=None)
    st.write_text(json.dumps(s, indent=1, ensure_ascii=False))
    print(f"{run_id}/{layer} reopened (turn {s['turn']})")


def run(contract, levels=None, mock=None):
    run_dir = P.RUNS / contract["run_id"]; run_dir.mkdir(parents=True, exist_ok=True)
    cp = run_dir / "run_contract.json"
    if cp.exists():
        old = json.loads(cp.read_text())
        for k in ("examiner_model", "solver_model", "videos", "seed", "n_per_layer"):
            if old.get(k) != contract.get(k):
                log(run_dir, f"WARNING: contract {k} changed since first run: {old.get(k)} -> {contract.get(k)}")
    cp.write_text(json.dumps(contract, indent=1, ensure_ascii=False))
    store = Store()
    mk = None
    if mock:
        from mock import Mock
        mk = Mock(mock, store)
    global _SCOPE_BY_TASK, _SG_PLAN
    _SCOPE_BY_TASK = None; _SG_PLAN = None
    prompts.SG_ON = bool(contract.get("sg_mode"))
    if contract.get("sg_mode"):                                   # 10-28 v15:goal -> 期望 event 的 planner(每 task 一次,缓存)
        tids = [contract["task_sample_id"]] if contract.get("task_sample_id") else SC.task_ids_for(store, contract)
        _SG_PLAN = SG.ensure(contract, store, run_dir, task_ids=tids)
        for tid, pl in _SG_PLAN.items():
            n_ev = sum(1 for e in (pl or {}).get("events", {}).values()); n_m = sum(1 for e in (pl or {}).get("events", {}).values() if e.get("matched"))
            log(run_dir, f"sg planner: {tid}: {n_ev} expected events ({n_m} matched to annotations), {len((pl or {}).get('relations') or [])} relations, {len((pl or {}).get('decision_points') or [])} decision points" if pl else f"sg planner FAILED for {tid}")
    retrieve.EGOPLAN_L4_INTERMEDIATE = bool(contract.get("l4_intermediate_cutoffs"))
    import store as _ST; _ST.ACCEPT_SOURCES.update(contract.get("accept_unverified_sources") or [])
    for _k, _a in (("gap_sizes", "GAP_SIZES"), ("gap_head_sec", "GAP_HEAD_SEC"), ("gap_tail_sec", "GAP_TAIL_SEC"), ("gap_tail_frame_sec", "GAP_TAIL_FRAME_SEC")):
        if contract.get(_k) is not None: setattr(retrieve, _a, contract[_k])
    if contract.get("scope_mode", "prefer") != "off":
        tids = SC.task_ids_for(store, contract)
        if tids:
            _SCOPE_BY_TASK = SC.ensure(contract, store, run_dir, task_ids=tids, mock=mk)
            n_ok = sum(1 for v in _SCOPE_BY_TASK.values() if v)
            log(run_dir, f"scope planner: {n_ok}/{len(tids)} tasks have a scope (mode {contract.get('scope_mode', 'prefer')})")
    for layer in (levels or LAYERS):
        layer = layer if layer.startswith("L") else f"L{layer}"
        state = LayerState(run_dir, layer, contract)
        run_layer(store, state, contract, run_dir, mock=mk)
    log(run_dir, "run finished")
