"""11-03 试验模式(Pyramid_Claude_Guide):基于下层弱点的组合出题。合约 comp_mode = true 时启用,默认关闭走 v24 原路径。
三件事分开:Layer(solver 做什么操作)由 v24 定;Tier(出题条件:题型 / clip / 候选数)沿用 v24 不动;本模块只在当前 event、skill、tier 允许的候选里
选「必须区分已知混淆物体 / 次序」的证据组合与干扰项,并把来源记进 private.comp 与 comp_log.jsonl。
依赖链(最小):L1 object_recognition → L2 action_recognition / event_object_role(时间段题) → L3 object_state_change / object_location_at_time。
  L2 组合:同 sub-goal 里存在「同动作、不同物体」(object_swap)或「同动作同物体的另一次」(ordinal_swap)的真实 narration,干扰段强制取这些段;
          题面必须点名目标物体,有 ordinal 替代时必须写第几次。换锚点 → 正确段换成另一个选项(答案改变)。
  L3 组合:同一 clip 里目标物体有另一次移动(ordinal)或混淆物体也移动(object_swap);答案 = 移动终点(fixture 种类,相同时用 3D 最近参照物);
          换锚点后终点必须不同,否则 fallback(same_gold)。
profile:从已有 v24 self run 的 history 建(L1 按物体名、L2 按 verb+object),≥3 event 测到;≥2 event 多数票错且错误率 ≥ 2/3 → weak;≥3 event 全对 → strong;其余 unknown。
评测 event(及与它共享记录的 event)不参与自己的 profile(逐题排除)。profile 只给控制器选题 / 配对,solver 的 history 仍按 v24 构造。"""
import json, re, hashlib, collections, math, time
from pathlib import Path
import p2config as P
import sg as SG

THRESH = {"min_events": 3, "weak_min_wrong_events": 2, "weak_err_rate": 2 / 3, "strong_min_events": 3}
TG_SKILLS = {"action_recognition", "event_object_role"}
L3_SKILLS = {"object_state_change", "object_location_at_time"}
PREREQ = {"action_recognition": "object_recognition", "event_object_role": "object_recognition",
          "object_state_change": "action_recognition", "object_location_at_time": "action_recognition"}
CHAIN = {"action_recognition": "L1.object_recognition->L2.action_recognition", "event_object_role": "L1.object_recognition->L2.event_object_role",
         "object_state_change": "L1.object_recognition->L2.action_recognition->L3.object_state_change", "object_location_at_time": "L1.object_recognition->L2.action_recognition->L3.object_location_at_time"}
FIXTURE_WORDS = {"counter": "on the counter", "table": "on the table", "sink": "in the sink", "cupboard": "in the cupboard", "cabinet": "in the cabinet", "hob": "on the hob", "stove": "on the stove",
                 "fridge": "in the fridge", "drawer": "in the drawer", "shelf": "on the shelf", "oven": "in the oven", "floor": "on the floor", "bin": "in the bin", "dishwasher": "in the dishwasher"}


def _base(name): return re.sub(r"\s*\d+$", "", (name or "").strip().lower())


def _opt_text(o): return re.sub(r"^\s*[A-E]\s*[\.\):]\s*", "", str(o or "")).strip().lower()


def _vn(rec):
    """narration -> (verb stem, object stem, object text)。"""
    v = rec["value"] or {}
    vs = [SG._stem(x) for x in (v.get("verbs") or []) if x]
    nouns = [n for n in (v.get("nouns") or []) if n]
    if not vs or not nouns:
        txt = SG._narr_text(rec); toks = re.findall(r"[a-z]+", txt.lower())
        if not vs and toks: vs = [SG._stem(toks[0])]
        if not nouns and len(toks) > 1: nouns = [toks[-1]]
    ns = [SG._stem(n.split()[-1]) for n in nouns]
    return (vs[0] if vs else None), (ns[0] if ns else None), (nouns[0].lower() if nouns else None)


# ---------------------------------------------------------------- 1. profile
def _row_pattern(row, skill):
    """一条 history 行 -> (pattern key, 是否答错, 误选方向)。L1 object_recognition:参考选项文字的物体词干;L2 tg:题面的 verb+object(由 sg.event 描述给,这里用题面词干近似)。"""
    if row.get("verdict") not in ("correct", "wrong"): return None
    if skill == "object_recognition":
        ref = row.get("reference"); opts = row.get("options") or []
        ref_txt = None
        if isinstance(ref, str) and len(ref.strip()) == 1 and opts:
            i = "ABCD".find(ref.strip().upper()); ref_txt = _opt_text(opts[i]) if 0 <= i < len(opts) else None
        elif isinstance(ref, str): ref_txt = ref.lower()
        if not ref_txt: return None
        toks = [SG._stem(w) for w in re.findall(r"[a-z]+", ref_txt) if w not in SG._STOP and len(w) > 2]
        key = toks[-1] if toks else None
        wrong_to = None
        if row["verdict"] == "wrong" and opts and isinstance(row.get("parsed"), str) and len(row["parsed"]) == 1:
            j = "ABCD".find(row["parsed"].upper()); wrong_to = _opt_text(opts[j]) if 0 <= j < len(opts) else None
        return (key, row["verdict"] == "wrong", wrong_to) if key else None
    if skill in TG_SKILLS:
        q = (row.get("question") or "").lower()
        m = re.search(r"when (?:does|do|did|is|are|was|were) (?:the )?(?:camera wearer|person|they|he|she)?\s*([a-z]+)(?:s|es|ed|ing)?\b(?:.*?\b(?:the|a|an)\s+([a-z ]+?))?[\?,]", q)
        toks = [SG._stem(w) for w in re.findall(r"[a-z]+", q) if w not in SG._STOP and len(w) > 2 and w not in ("clip", "camera", "wearer", "person", "when", "does", "moment", "first", "second", "time")]
        key = " ".join(toks[:2]) if toks else None
        return (key, row["verdict"] == "wrong", None) if key else None
    return None


def build_profile(run_dirs, thresholds=None):
    """run_dirs: 已有 v24 self run 目录;返回 {"version", "sources", "thresholds", "skills": {skill: {pattern: {events:{event_key: wrong}, confusions:{}}}}}。状态按 status() 逐题算(可排除 event)。"""
    th = dict(THRESH, **(thresholds or {}))
    stats = collections.defaultdict(lambda: collections.defaultdict(lambda: {"events": {}, "confusions": collections.Counter(), "records": {}}))
    for rd in run_dirs:
        rd = Path(rd)
        for L in ("L1", "L2"):
            hp = rd / L / "history.jsonl"
            if not hp.exists(): continue
            for line in open(hp):
                h = json.loads(line); sk = h.get("capability_skill")
                if sk not in {"object_recognition"} | TG_SKILLS: continue
                pr = _row_pattern(h, sk)
                if not pr: continue
                key, wrong, wrong_to = pr
                ek = f"{rd.name}:{(h.get('sg') or {}).get('event_id')}"
                st = stats[sk][key]
                st["events"][ek] = bool(wrong) or st["events"].get(ek, False)     # 同 event 多题:任一多数票错即记错(保守)
                st["records"].setdefault(ek, []).append({"turn": h["turn"], "verdict": h["verdict"], "tier": h.get("difficulty_level")})
                if wrong_to: st["confusions"][wrong_to] += 1
    out = {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "sources": [str(r) for r in run_dirs], "thresholds": th, "skills": {}}
    for sk, pats in stats.items():
        out["skills"][sk] = {k: {"events": v["events"], "confusions": dict(v["confusions"]), "records": v["records"]} for k, v in pats.items()}
    out["version"] = hashlib.sha1(json.dumps(out["skills"], sort_keys=True).encode()).hexdigest()[:10]
    return out


def status(profile, skill, pattern, exclude_events=()):
    """weak / strong / unknown + 分子分母。exclude_events = 当前评测 event 的 key(run:event_id)集合。"""
    th = profile.get("thresholds", THRESH)
    p = (profile.get("skills") or {}).get(skill, {}).get(pattern)
    if not p: return {"status": "unknown", "n_events": 0, "n_wrong_events": 0, "reason": "pattern not in profile"}
    ev = {k: w for k, w in p["events"].items() if k not in set(exclude_events)}
    n = len(ev); nw = sum(1 for w in ev.values() if w)
    if n >= th["min_events"] and nw >= th["weak_min_wrong_events"] and nw / n >= th["weak_err_rate"]: s = "weak"
    elif n >= th["strong_min_events"] and nw == 0: s = "strong"
    else: s = "unknown"
    return {"status": s, "n_events": n, "n_wrong_events": nw, "events": sorted(ev), "confusions": p.get("confusions", {}), "excluded": sorted(set(exclude_events) & set(p["events"]))}


# ---------------------------------------------------------------- 2. 依赖构造
def _event_narr(store, ev):
    recs = [store.get(r) for r in ev.get("records") or []]
    recs = [r for r in recs if r is not None and r["kind"] == "action_narration"]
    return min(recs, key=lambda r: r["time"]["end_sec"] - r["time"]["start_sec"]) if recs else None


def compose_tg(store, ti, plan, c, ev, profile, run_name):
    """L2 时间段题的组合:目标 = event 的核心 narration;替代 = 同 sub-goal 窗口里同动作不同物体 / 同动作同物体另一次的 narration。"""
    vid = ti["video_id"]; w0, w1 = c["window"]
    tgt = _event_narr(store, ev)
    if tgt is None: return None, "no_narration_for_event"
    v0, n0, ntxt = _vn(tgt)
    if not v0 or not n0: return None, "target_narration_has_no_verb_or_object"
    narr = [r for r in SG._recs(store, vid, w0, w1, kinds={"action_narration"}) if r["evidence_id"] != tgt["evidence_id"]]
    same = sorted([r for r in narr if _vn(r)[0] == v0 and _vn(r)[1] == n0] + [tgt], key=lambda r: r["time"]["start_sec"])
    ordinal = next(i for i, r in enumerate(same) if r["evidence_id"] == tgt["evidence_id"]) + 1
    alts = []
    for r in narr:
        rv, rn, rtxt = _vn(r)
        if rv != v0 or not rn: continue
        span = [float(r["time"]["start_sec"]), float(r["time"]["end_sec"])]
        gap = max(0.0, max(span[0], tgt["time"]["start_sec"]) - min(span[1], tgt["time"]["end_sec"]))
        if gap < 1.0: continue                                   # 与目标重叠:不是可区分的替代锚点
        if span[0] < w0 - 0.2 or span[1] > w1 + 0.2: continue    # 替代锚点必须完整在 clip 里(solver 看得到)
        kind = "ordinal_swap" if rn == n0 else "object_swap"
        alts.append({"kind": kind, "rec": r["evidence_id"], "span": [round(x, 3) for x in span], "object": rtxt or rn, "verb": rv,
                     "ordinal": (sorted(x["evidence_id"] for x in same).index(r["evidence_id"]) + 1) if kind == "ordinal_swap" and r in same else None,
                     "text": SG._narr_text(r)})
    if not alts: return None, "no_natural_distractor(same verb, other object / other occurrence) in the sub-goal"
    ek = f"{run_name}:{ev['event_id']}"
    shared = {f"{run_name}:{e['event_id']}" for e in plan["events"].values() if e is not ev and set(e.get("records") or []) & set(ev.get("records") or [])}
    pre = status(profile, "object_recognition", n0, exclude_events={ek} | shared)
    conf = pre.get("confusions") or {}
    for a in alts:                                               # 已知混淆对象优先,其次 ordinal
        a["is_known_confusion"] = any(SG._toks(a["object"]) & SG._toks(k) for k in conf)
    alts.sort(key=lambda a: (not a["is_known_confusion"], a["kind"] != "object_swap", a["span"][0]))
    return {"chain": CHAIN[c["capability_skill"]], "mode": "tg", "target": {"rec": tgt["evidence_id"], "span": [round(float(tgt["time"]["start_sec"]), 3), round(float(tgt["time"]["end_sec"]), 3)],
                                                                            "object": ntxt or n0, "object_key": n0, "verb": v0, "ordinal": ordinal, "n_same": len(same), "text": SG._narr_text(tgt)},
            "alts": alts[:3], "prereq": {"skill": "object_recognition", "pattern": n0, **pre},
            "profile_version": profile.get("version"), "event_key": ek, "excluded_from_profile": sorted({ek} | shared)}, None


def _moves_for(store, vid, w0, w1):
    return sorted([r for r in SG._recs(store, vid, w0, w1, kinds={"object_move", "object_location_transition"}) if r["value"].get("to_fixture_kind") or r["value"].get("end_xyz")],
                  key=lambda r: r["time"]["start_sec"])


def _endpoint(store, vid, mv, refs):
    """移动终点的答案:fixture 种类;给了 refs(3D 参照物)时返回 (fixture_kind, nearest_ref_name)。"""
    v = mv["value"]; fk = v.get("to_fixture_kind")
    near = None
    if v.get("end_xyz") and refs:
        d = sorted(((math.dist(v["end_xyz"], r["xyz"]), r["name"]) for r in refs), key=lambda x: x[0])
        if len(d) >= 2 and d[1][0] - d[0][0] >= 0.1: near = d[0][1]
    return fk, near


def compose_l3(store, ti, plan, c, ev, profile, run_name):
    """L3 位置变化题的组合:目标 = 与 event 对应的移动记录;替代 = 同 clip 里同物体的另一次移动(ordinal)或别的物体的移动(object_swap);终点必须不同。"""
    vid = ti["video_id"]; w0, w1 = c["window"]
    moves = _moves_for(store, vid, w0, w1)
    if not moves: return None, "no_move_record_in_clip"
    ev_objs = {SG._stem(x) for o in ev.get("objects") or [] for x in re.findall(r"[a-z]+", o) if x not in SG._STOP}
    ea, eb = ev["time"]
    def _obj(mv): return _base(mv["value"].get("object_name") or mv["value"].get("name") or "")
    cand = [m for m in moves if m["time"]["start_sec"] <= eb + 1 and m["time"]["end_sec"] >= ea - 1 and (SG._toks(_obj(m)) & ev_objs)]
    if not cand: cand = [m for m in moves if m["time"]["start_sec"] <= eb + 1 and m["time"]["end_sec"] >= ea - 1]
    if not cand: return None, "no_move_record_overlapping_the_event"
    tgt = min(cand, key=lambda m: abs((m["time"]["start_sec"] + m["time"]["end_sec"]) / 2 - (ea + eb) / 2))
    obj = _obj(tgt)
    masks = [r for r in SG._recs(store, vid, w0 - 20, w1 + 20, kinds={"object_mask_anchor"}) if r["value"].get("xyz") and r["value"].get("name")]
    refs = {}
    for r in masks:
        nm = _base(r["value"]["name"])
        if nm and nm != obj and nm not in refs: refs[nm] = {"name": nm, "xyz": r["value"]["xyz"]}
    refs = list(refs.values())
    fk0, near0 = _endpoint(store, vid, tgt, refs)
    same = [m for m in moves if _obj(m) == obj]
    ordinal = same.index(tgt) + 1 if tgt in same else 1
    alts = []
    for m in moves:
        if m is tgt: continue
        gap = max(0.0, max(m["time"]["start_sec"], tgt["time"]["start_sec"]) - min(m["time"]["end_sec"], tgt["time"]["end_sec"]))
        if gap < 1.0: continue
        fk, near = _endpoint(store, vid, m, refs)
        kind = "ordinal_swap" if _obj(m) == obj else "object_swap"
        if fk0 and fk and fk != fk0: ans_kind, a0, a1 = "fixture", fk0, fk
        elif near0 and near and near != near0: ans_kind, a0, a1 = "nearest", near0, near
        else: continue                                           # 换锚点答案不变:不是有效替代
        alts.append({"kind": kind, "rec": m["evidence_id"], "span": [round(float(m["time"]["start_sec"]), 3), round(float(m["time"]["end_sec"]), 3)], "object": _obj(m),
                     "ordinal": (same.index(m) + 1) if m in same else None, "answer_kind": ans_kind, "target_answer": a0, "alt_answer": a1,
                     "from": m["value"].get("from_fixture_kind"), "to": fk})
    if not alts:
        return None, ("same_gold_under_alternative_anchor" if len([m for m in moves if m is not tgt]) else "no_alternative_move_in_clip")
    ek = f"{run_name}:{ev['event_id']}"
    shared = {f"{run_name}:{e['event_id']}" for e in plan["events"].values() if e is not ev and set(e.get("records") or []) & set(ev.get("records") or [])}
    pre1 = status(profile, "object_recognition", SG._stem(obj.split()[-1]) if obj else obj, exclude_events={ek} | shared)
    pre2 = status(profile, "action_recognition", None, exclude_events={ek} | shared)
    kinds = collections.Counter(a["answer_kind"] for a in alts)
    ans_kind = "fixture" if kinds.get("fixture") else "nearest"
    alts = [a for a in alts if a["answer_kind"] == ans_kind]
    alts.sort(key=lambda a: (a["kind"] != "ordinal_swap", a["span"][0]))
    tgt_ans = alts[0]["target_answer"]
    return {"chain": CHAIN[c["capability_skill"]], "mode": "l3move", "answer_kind": ans_kind,
            "target": {"rec": tgt["evidence_id"], "span": [round(float(tgt["time"]["start_sec"]), 3), round(float(tgt["time"]["end_sec"]), 3)], "object": obj, "ordinal": ordinal, "n_same": len(same),
                       "from": tgt["value"].get("from_fixture_kind"), "to": fk0, "answer": tgt_ans},
            "alts": alts[:3], "prereq": {"skill": "object_recognition", "pattern": SG._stem(obj.split()[-1]) if obj else None, **pre1},
            "profile_version": profile.get("version"), "event_key": ek, "excluded_from_profile": sorted({ek} | shared)}, None


def attach(store, ti, plan, pools, contract, profile, run_name, log=None):
    """给 v24 的 TG cluster 与 L3 change_over_time cluster 挂 sg.comp_by_event(每个 event 一份组合或 fallback 原因)。"""
    n_ok = n_fb = 0; reasons = collections.Counter()
    for cap, clusters in pools.items():
        if cap not in TG_SKILLS and cap not in L3_SKILLS: continue
        for c in clusters:
            by = {}
            for ev in c["sg"].get("events") or []:
                comp, why = (compose_tg if cap in TG_SKILLS else compose_l3)(store, ti, plan, c, ev, profile, run_name)
                if comp: by[ev["event_id"]] = comp; n_ok += 1
                else: by[ev["event_id"]] = {"fallback": why}; n_fb += 1; reasons[why] += 1
            c["sg"]["comp_by_event"] = by; c["sg"]["comp_mode"] = True
    if log: log(f"comp_mode: {n_ok} composed, {n_fb} fallback {dict(reasons)}")
    return {"composed": n_ok, "fallback": n_fb, "reasons": dict(reasons)}


# ---------------------------------------------------------------- 3. 出题时:选项 / 校验 / 日志
def answer_phrase(kind, ans):
    return FIXTURE_WORDS.get(ans, f"on the {ans}") if kind == "fixture" else f"next to the {ans}"


def fill_l3_options(comp, rng, extra_fixtures=()):
    """L3 组合题选项:目标答案 + 各替代答案 + 其它 fixture 补足 4 个;返回 (options_text, correct_idx)。"""
    kind = comp["answer_kind"]; opts = [comp["target"]["answer"]]
    for a in comp["alts"]:
        if a["alt_answer"] not in opts: opts.append(a["alt_answer"])
    for f in extra_fixtures:
        if len(opts) >= 4: break
        if f and f not in opts: opts.append(f)
    opts = opts[:4]
    if len(opts) < 4: return None, None
    rng.shuffle(opts)
    return [answer_phrase(kind, o) for o in opts], opts.index(comp["target"]["answer"])


ORDINAL_WORDS = {1: "first", 2: "second", 3: "third", 4: "fourth"}


def checks(comp, pub, pri):
    e = []; q = (pub.get("question") or "").lower()
    if not (SG._toks(comp["target"]["object"]) & SG._toks(q)):
        e.append(f"composed item: the question must name the target object {comp['target']['object']!r}")
    needs_ord = comp["target"].get("n_same", 1) > 1 or any(a["kind"] == "ordinal_swap" for a in comp["alts"])
    if needs_ord and not re.search(r"\b(first|second|third|fourth|last|1st|2nd|3rd)\b", q):
        e.append(f"composed item: the same action on this object happens more than once in the clip; say which occurrence ('the {ORDINAL_WORDS.get(comp['target'].get('ordinal', 1), 'first')} time ...')")
    if comp.get("mode") == "l3move":
        for w in (comp["target"].get("from"), comp["target"].get("to")):
            if w and re.search(rf"\b{re.escape(w)}\b", q) and comp["answer_kind"] == "fixture":
                e.append(f"composed item: the question must not reveal the move's endpoint {w!r}")
    return e


def private_block(comp, c, ev, difficulty, pair_key):
    return {"chain": comp["chain"], "mode": comp["mode"], "skill": c.get("capability_skill") or comp.get("skill") or pair_key_skill(pair_key), "tier": (difficulty or {}).get("level"), "format": (difficulty or {}).get("format"),
            "source_event": ev["event_id"], "target": comp["target"], "alts": comp["alts"], "prereq": comp["prereq"], "profile_version": comp.get("profile_version"),
            "pair_key": pair_key, "excluded_from_profile": comp.get("excluded_from_profile")}


def log_item(run_id, rec):
    p = P.RUNS / run_id / "comp_log.jsonl"
    with open(p, "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def pair_key_skill(pk):
    return pk.split('|')[1] if isinstance(pk, str) and pk.count('|') >= 2 else None


def pair_key(task_id, skill, difficulty, window_sec, n_opts):
    return f"{task_id}|{skill}|t{(difficulty or {}).get('level')}|{(difficulty or {}).get('format')}|w{int(round(window_sec / 10.0) * 10)}|o{n_opts}"
