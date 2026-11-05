"""11-04 v30(用户定:L3 = L2 的那一跳 + 再一跳):每道 L3 题的锚点是一个 L2 事件 / 声音,问的是它之后的空间事实。GT 全部由官方标注算:
  sound_object_location   「发出第 n 声 X 的那个物体,clip 结束时在哪个 fixture 上?」 sound_event ↔ 同时段 object_move 的物体 → 该 track 之后最后一次 object_move 的 to_fixture_kind
  sound_object_nearest    「发出 X 声的物体,之后(clip 结束时)离哪个候选物最近(真实 3D 距离)?」 同上 + 其它 track 的静止 mask 3D 锚点,最近与次近差 ≥ 0.1 m
  action_outcome_location 「<L2 的那个动作> 之后,被操作的物体最后放到哪个 fixture?」 narration 宾语 → 其后 object_move 链的 to_fixture_kind
题面不点名发声物体(那是 L2 的一跳),只描述声音(类别 + 第几次);档:1 = 同类声音唯一且物体结尾可见;2 = 同类声音多次要数第 n 声;3 = 物体结尾不在画面;4 = 不可见 + 短答。
sound_object_nearest / action_outcome_location 的档 = 3D 余量 / 动作到落点的时间差 的四分位。选项与参考由程序填;clip 连续 ≤ 60 s。"""
import collections, math, re
import sg as SG

CH_SKILLS = ["sound_object_location", "sound_object_nearest", "action_outcome_location"]
SKILL_DEFS = {
    "sound_object_location": "L3 (chained: sound -> object -> place): the object that made a described sound (e.g. the second metal collision) - on / in which fixture is it at the end of the clip",
    "sound_object_nearest": "L3 (chained: sound -> object -> 3D): the object that made a described sound - which listed object is it nearest to (real 3D distance) at the end of the clip",
    "action_outcome_location": "L3 (chained: action -> object -> place): after the described action, on / in which fixture does the handled object end up at the end of the clip",
}
MAX_CLIP, PRE, POST, MAX_SAME, PER_SKILL, MIN_MARGIN, BIND_GAP = 60.0, 5.0, 3.0, 3, 12, 0.1, 1.0
ORD = {1: "first", 2: "second", 3: "third", 4: "fourth"}
_CACHE = {}


def _base(name): return re.sub(r"\s*\d+$", "", (name or "").strip().lower())
def _dist3(a, b): return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))
def _t(r): return float(r["time"]["start_sec"]), float(r["time"]["end_sec"])
def _overlap(a, b): return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
def _fixture_phrase(kind): return f"the {kind}"


def clusters(store, ti, plan, skill):
    key = (ti["task_id"], id(plan))
    if key not in _CACHE: _CACHE[key] = _build(store, ti, plan)
    return list(_CACHE[key].get(skill, []))


def _chain_end(moves, track, t_from, t_cap):
    """同一 track 从 t_from 起的后续 move 链(start ≤ t_cap):返回链里最后一次 move(落点)。"""
    later = sorted([m for m in moves if m["value"].get("track_id") == track and t_from - 0.5 <= _t(m)[0] <= t_cap], key=lambda m: _t(m)[0])
    return later[-1] if later else None


def _visible_at(vis, track, t):
    return any(v["value"].get("track_id") == track and _t(v)[0] <= t + 0.5 and _t(v)[1] >= t - 1.0 for v in vis)


def _build(store, ti, plan):
    vid = ti["video_id"]; m = store.media_of_video(vid); D = (m or {}).get("duration_sec") or 1e9
    T0, T1 = ti["t0"], ti["t1"]
    moves = [r for r in SG._recs(store, vid, T0 - 2, T1 + 2, kinds={"object_move"}) if (r["value"] or {}).get("object_name") and (r["value"] or {}).get("track_id")]
    masks = [r for r in SG._recs(store, vid, T0 - 20, T1 + 20, kinds={"object_mask_anchor"}) if (r["value"] or {}).get("xyz") and (r["value"] or {}).get("name")]
    vis = SG._recs(store, vid, T0 - 2, T1 + 2, kinds={"object_visible_track"})
    sounds = sorted([r for r in SG._recs(store, vid, T0, T1, kinds={"sound_event"}) if "BACKGROUND_CLASS" not in r["quality_flags"] and (r["value"] or {}).get("label")], key=lambda r: _t(r)[0])
    narr = SG._recs(store, vid, T0 - 2, T1 + 2, kinds={"action_narration"})
    fx = collections.Counter(v for r in moves for k in ("from_fixture_kind", "to_fixture_kind") for v in [(r["value"] or {}).get(k)] if v and v != "mid-air")
    video_fixtures = [k for k, _ in fx.most_common(8)]
    evs = sorted([e for e in plan["events"].values() if e.get("matched")], key=lambda e: e["centre"])
    def _ev_near(t, pad=8.0):
        c = [e for e in evs if abs(e["centre"] - t) <= pad]
        return min(c, key=lambda e: abs(e["centre"] - t)) if c else None
    def _step_of(t): return next((s for s in ti["steps"] if s["t0"] - 0.5 <= t <= s["t1"] + 0.5), None)
    def _core(w, extra):
        core = list(extra) + [r for r in narr if _t(r)[0] <= w[1] and _t(r)[1] >= w[0]]
        core = list({r["evidence_id"]: r for r in core}.values())
        st = _step_of(w[1])
        if st and st["idx"] in ti["step_rec"]: core.append(ti["step_rec"][st["idx"]])
        return core, st
    def _loc_options(answer, prefer, rng_key):
        opts = [answer] + [p for p in prefer if p and p != answer and p != "mid-air"]
        for k in video_fixtures:
            if k not in opts: opts.append(k)
        for k in ("counter", "sink", "cupboard", "table", "hob", "fridge", "drawer", "bin"):
            if k not in opts: opts.append(k)
        opts = opts[:4]
        import random as _r
        rr = _r.Random(rng_key); rr.shuffle(opts)
        return opts
    out = {sk: [] for sk in CH_SKILLS}
    pre_near = []; pre_act = []
    # ---------- sound → object → place / nearest
    for s in sounds:
        ss, se = _t(s); lab = s["value"]["label"]
        cands = [mv for mv in moves if _overlap((ss - BIND_GAP, se + BIND_GAP), _t(mv)) > 0]
        objs = {_base(mv["value"]["object_name"]) for mv in cands}
        if len(objs) != 1: continue                                   # 声音同时对上两个物体 / 对不上:不出
        mv = max(cands, key=lambda x: _overlap((ss, se), _t(x))); obj = _base(mv["value"]["object_name"]); track = mv["value"]["track_id"]
        w0 = max(0.0, ss - PRE); fin = _chain_end(moves, track, _t(mv)[0], w0 + MAX_CLIP - POST)
        if fin is None: continue
        loc = (fin["value"] or {}).get("to_fixture_kind")
        if not loc or loc == "mid-air": continue
        w1 = min(D, _t(fin)[1] + POST)
        if w1 - w0 > MAX_CLIP or w1 - w0 < 6.0: continue
        same = [x for x in sounds if x["value"]["label"] == lab and w0 <= _t(x)[0] <= w1]
        n_same = len(same); ordinal = 1 + sum(1 for x in same if _t(x)[0] < ss)
        if n_same > MAX_SAME: continue
        # 同名其它实例在 clip 里也动过:指代不清
        if any(_base(x["value"]["object_name"]) == obj and x["value"].get("track_id") != track and w0 <= _t(x)[0] <= w1 for x in moves): continue
        visible = _visible_at(vis, track, _t(fin)[1])                 # 可见性看最后一次放下的那一刻(clip 还多 3 s 尾巴)
        gap_s = _t(fin)[1] - se                                        # 声音到最终落点的时间(中间再被挪过就长)
        tier = None                                                    # 档 = (同类声音次数 − 1) × 30 + gap 的四分位,下面统一算
        chain = sorted([x for x in moves if x["value"].get("track_id") == track and _t(mv)[0] - 0.5 <= _t(x)[0] <= _t(fin)[0] + 0.5], key=lambda x: _t(x)[0])
        from_kinds = [x["value"].get("from_fixture_kind") for x in chain]
        core, st = _core([w0, w1], [s] + chain + [v for v in vis if v["value"].get("track_id") == track and _t(v)[0] <= w1 and _t(v)[1] >= w0])
        eA, eB = _ev_near(ss), _ev_near(_t(fin)[1])
        events = [{k_: e[k_] for k_ in ("event_id", "sub_goal", "type", "description", "objects", "time", "records")} for e in [eA, eB] if e]
        events = list({e["event_id"]: e for e in events}.values())
        sdesc = f"the {ORD.get(ordinal, str(ordinal) + 'th')} '{lab}' sound" if n_same > 1 else f"the '{lab}' sound"
        base_ch = {"object": obj, "track": track, "sound_label": lab, "sound_id": s["evidence_id"], "sound_time": [round(ss, 2), round(se, 2)], "ordinal": ordinal, "n_same_in_clip": n_same,
                   "sound_desc": sdesc, "bound_move": mv["evidence_id"], "final_move": fin["evidence_id"], "final_time": [round(_t(fin)[0], 2), round(_t(fin)[1], 2)],
                   "visible_at_end": visible, "chain_fixtures": [x["value"].get("from_fixture_kind") for x in chain] + [loc],
                   "frame": "allocentric: the fixture (counter / sink / hob / cupboard ...) the object rests on or in at the end of the clip; from the official 3D object-movement annotation"}
        rid = f"ch_sol_{s['evidence_id'].split(':')[-1]}"
        opts = _loc_options(loc, from_kinds, rid)
        meta = {"kind": "L3", "v24": True, "l3_kind": "chain", "tier": tier, "format": "short_answer" if tier == 4 else "single_choice", "rel_id": rid, "rel_type": "sound_object_location",
                "idx": st["idx"] if st else None, "this_sub_goal": st["idx"] if st else None,
                "ch": dict(base_ch, skill="sound_object_location", options=opts, answer=loc, accepted=[loc, f"on the {loc}", f"in the {loc}", f"the {loc}"],
                           note=f"{sdesc} at {round(ss - w0, 1)} s of the clip is made by the {obj} (object_move {mv['value'].get('label')}); its last move in the clip ends on {loc} at {round(_t(fin)[1] - w0, 1)} s; {'visible' if visible else 'NOT visible'} at the end"),
                "events": events, "windows": [[round(w0, 3), round(w1, 3)]], "n_segments": 1, "total_sec": round(w1 - w0, 1),
                "window_rule": f"one continuous clip from 5 s before the sound to 3 s after the object's last move (<= {MAX_CLIP:.0f} s); tier {tier}",
                "band_rule": "tier 1 = the sound class occurs once in the clip and the object is visible at the end; 2 = the class occurs more than once (count the n-th); 3 = object not visible at the end; 4 = not visible + short answer"}
        meta["ch"]["gap_sec"] = round(gap_s, 1); meta["_knob"] = (n_same - 1) * 30.0 + gap_s
        out["sound_object_location"].append(SG._mk_cluster("sound_object_location", ti, store, windows=[[round(w0, 3), round(w1, 3)]], cutoff=w1, anchor=s, core=core, sg_meta=meta))
        # nearest:落点 3D vs 其它 track 的静止锚点
        exyz = (fin["value"] or {}).get("end_xyz")
        if exyz:
            tf = _t(fin)[1]; refs = {}
            for r in masks:
                rv = r["value"]; t = _t(r)[0]
                if rv.get("track_id") == track or abs(t - tf) > 20.0: continue
                lo, hi = min(t, tf), max(t, tf)
                if any(q["value"].get("track_id") == rv.get("track_id") and _t(q)[0] <= hi and _t(q)[1] >= lo for q in moves): continue
                nm = _base(rv["name"])
                if not nm or nm == obj: continue
                if nm not in refs or abs(t - tf) < abs(refs[nm]["t"] - tf): refs[nm] = {"name": nm, "xyz": rv["xyz"], "t": t, "id": r["evidence_id"], "rec": r}
            by = sorted(refs.values(), key=lambda r: _dist3(exyz, r["xyz"]))
            if len(by) >= 4 and _dist3(exyz, by[1]["xyz"]) - _dist3(exyz, by[0]["xyz"]) >= MIN_MARGIN:
                margin = _dist3(exyz, by[1]["xyz"]) - _dist3(exyz, by[0]["xyz"])
                pre_near.append((s, base_ch, [w0, w1], core + [r["rec"] for r in by[:4]], events, st, by[:4], margin, exyz))
    # ---------- action → object → place
    for e in evs:
        ev_objs = SG._toks(" ".join(e.get("objects") or []) + " " + (e.get("description") or ""))
        et0, et1 = float(e["time"][0]), float(e["time"][1])
        cands = [mv for mv in moves if (SG._toks(mv["value"]["object_name"]) & ev_objs) and et0 - 1.0 <= _t(mv)[0] <= et1 + 3.0]
        if not cands: continue
        mv = min(cands, key=lambda x: _t(x)[0]); obj = _base(mv["value"]["object_name"]); track = mv["value"]["track_id"]
        w0 = max(0.0, et0 - PRE); fin = _chain_end(moves, track, _t(mv)[0], w0 + MAX_CLIP - POST)
        if fin is None: continue
        loc = (fin["value"] or {}).get("to_fixture_kind"); frm = (mv["value"] or {}).get("from_fixture_kind")
        if not loc or loc == "mid-air": continue
        chain0 = sorted([x for x in moves if x["value"].get("track_id") == track and _t(mv)[0] - 0.5 <= _t(x)[0] <= _t(fin)[0] + 0.5], key=lambda x: _t(x)[0])
        kinds_in_chain = {k for x in chain0 for k in (x["value"].get("from_fixture_kind"), x["value"].get("to_fixture_kind")) if k and k != "mid-air"}
        if len(kinds_in_chain) < 2: continue                                       # 全程 counter -> counter:没有位置变化可问(厨房里绝大多数)
        w1 = min(D, _t(fin)[1] + POST)
        if w1 - w0 > MAX_CLIP or w1 - w0 < 6.0: continue
        if any(_base(x["value"]["object_name"]) == obj and x["value"].get("track_id") != track and w0 <= _t(x)[0] <= w1 for x in moves): continue
        visible = _visible_at(vis, track, _t(fin)[1]); gapsec = _t(fin)[1] - et1
        chain = sorted([x for x in moves if x["value"].get("track_id") == track and _t(mv)[0] - 0.5 <= _t(x)[0] <= _t(fin)[0] + 0.5], key=lambda x: _t(x)[0])
        core, st = _core([w0, w1], chain + [v for v in vis if v["value"].get("track_id") == track and _t(v)[0] <= w1 and _t(v)[1] >= w0])
        for rid_ in e["records"]:
            r = store.get(rid_)
            if r is not None and r["solver_access"] != "answer_only": core.append(r)
        core = list({r["evidence_id"]: r for r in core}.values())
        pre_act.append((e, obj, track, mv, fin, loc, frm, [w0, w1], core, st, visible, gapsec, [x["value"].get("from_fixture_kind") for x in chain]))
    # tiers by quartile
    bl = SG._bands({c["sg"]["rel_id"]: c["sg"].pop("_knob") for c in out["sound_object_location"]})
    for c in out["sound_object_location"]:
        c["sg"]["tier"] = bl.get(c["sg"]["rel_id"], 2); c["sg"]["format"] = "short_answer" if c["sg"]["tier"] == 4 else "single_choice"
        c["sg"]["window_rule"] = c["sg"]["window_rule"].replace("tier None", f"tier {c['sg']['tier']}")
        c["sg"]["band_rule"] = "tier = quartile of (occurrences of the sound class in the clip - 1) * 30 + seconds from the sound to the object's final placement; larger = harder (count the n-th sound, track the object through later moves)"
    bands = SG._bands({f"n:{s['evidence_id']}": -margin for s, _b, _w, _c, _e, _st, _by, margin, _x in pre_near})
    for s, bch, w, core, events, st, by, margin, exyz in pre_near:
        tier = bands.get(f"n:{s['evidence_id']}", 2); rid = f"ch_son_{s['evidence_id'].split(':')[-1]}"
        import random as _r
        opts = [r["name"] for r in by]; _r.Random(rid).shuffle(opts)
        meta = {"kind": "L3", "v24": True, "l3_kind": "chain", "tier": tier, "format": "short_answer" if tier == 4 else "single_choice", "rel_id": rid, "rel_type": "sound_object_nearest",
                "idx": st["idx"] if st else None, "this_sub_goal": st["idx"] if st else None,
                "ch": dict(bch, skill="sound_object_nearest", options=opts, answer=by[0]["name"], accepted=[by[0]["name"]], margin_m=round(margin, 3),
                           candidates={r["name"]: round(_dist3(exyz, r["xyz"]), 2) for r in by},
                           frame="allocentric: real-world straight-line (3D) distance between object positions from the official mask anchors, at the end of the clip; compare only among the four listed candidates",
                           note=f"after its last move the {bch['object']} is nearest to {by[0]['name']} ({round(_dist3(exyz, by[0]['xyz']), 2)} m), runner-up {by[1]['name']} ({round(_dist3(exyz, by[1]['xyz']), 2)} m)"),
                "events": events, "windows": [[round(w[0], 3), round(w[1], 3)]], "n_segments": 1, "total_sec": round(w[1] - w[0], 1),
                "window_rule": f"one continuous clip from 5 s before the sound to 3 s after the object's last move (<= {MAX_CLIP:.0f} s); tier {tier} = quartile of the 3D margin (4 = smallest)",
                "band_rule": "tier = quartile of (distance to runner-up - distance to nearest) at the end of the clip; smaller = harder"}
        out["sound_object_nearest"].append(SG._mk_cluster("sound_object_nearest", ti, store, windows=[[round(w[0], 3), round(w[1], 3)]], cutoff=w[1], anchor=s, core=core, sg_meta=meta))
    bands = SG._bands({f"a:{e['event_id']}": gapsec + (30.0 if not visible else 0.0) for e, *_r, visible, gapsec, _f in pre_act})
    for e, obj, track, mv, fin, loc, frm, w, core, st, visible, gapsec, from_kinds in pre_act:
        tier = bands.get(f"a:{e['event_id']}", 2); rid = f"ch_aol_{e['event_id']}"
        opts = _loc_options(loc, [frm] + from_kinds, rid)
        meta = {"kind": "L3", "v24": True, "l3_kind": "chain", "tier": tier, "format": "short_answer" if tier == 4 else "single_choice", "rel_id": rid, "rel_type": "action_outcome_location",
                "idx": st["idx"] if st else None, "this_sub_goal": st["idx"] if st else None,
                "ch": {"skill": "action_outcome_location", "object": obj, "track": track, "action_desc": e["description"], "action_event": e["event_id"], "action_time": [round(float(e["time"][0]), 2), round(float(e["time"][1]), 2)],
                       "bound_move": mv["evidence_id"], "final_move": fin["evidence_id"], "final_time": [round(_t(fin)[0], 2), round(_t(fin)[1], 2)], "from_fixture": frm, "visible_at_end": visible,
                       "gap_sec": round(gapsec, 1), "chain_fixtures": from_kinds + [loc], "options": opts, "answer": loc, "accepted": [loc, f"on the {loc}", f"in the {loc}", f"the {loc}"],
                       "frame": "allocentric: the fixture the object rests on or in at the end of the clip; from the official 3D object-movement annotation",
                       "note": f"the {obj} handled in '{e['description']}' is moved {frm or '?'} -> ... -> {loc}; its last move ends at {round(_t(fin)[1] - w[0], 1)} s of the clip, {round(gapsec, 1)} s after the action; {'visible' if visible else 'NOT visible'} at the end"},
                "events": [{k_: e[k_] for k_ in ("event_id", "sub_goal", "type", "description", "objects", "time", "records")}],
                "windows": [[round(w[0], 3), round(w[1], 3)]], "n_segments": 1, "total_sec": round(w[1] - w[0], 1),
                "window_rule": f"one continuous clip from 5 s before the action to 3 s after the object's last move (<= {MAX_CLIP:.0f} s); tier {tier}",
                "band_rule": "tier = quartile of (seconds from the end of the action to the object's final placement, + 30 if the object is not visible at the end); larger = harder"}
        out["action_outcome_location"].append(SG._mk_cluster("action_outcome_location", ti, store, windows=[[round(w[0], 3), round(w[1], 3)]], cutoff=w[1], anchor=mv, core=core, sg_meta=meta))
    for sk in CH_SKILLS:
        rows = sorted(out[sk], key=lambda c: c["window"][0])
        if True:                                                       # 答案类别配额:同一答案最多占一半(厨房里落点多半是 counter),其余按时间均匀取
            cap_same = max(2, PER_SKILL // 2); picked = []; used = collections.Counter()
            for c in sorted(rows, key=lambda c: (used[c["sg"]["ch"]["answer"]], c["window"][0])):
                pass
            rest = list(rows)
            while rest and len(picked) < PER_SKILL:
                rest = [c for c in rest if used[c["sg"]["ch"]["answer"]] < cap_same]       # 硬上限:同一答案最多 cap_same 题
                if not rest: break
                c = min(rest, key=lambda c: (used[c["sg"]["ch"]["answer"]], c["window"][0]))
                rest.remove(c); picked.append(c); used[c["sg"]["ch"]["answer"]] += 1
            rows = sorted(picked, key=lambda c: c["window"][0])
        out[sk] = rows
    return out


# ---------------------------------------------------------------- Examiner 接口
def spec_for(cap, level, c=None):
    sg_ = (c or {}).get("sg") or {}; ch = sg_.get("ch") or {}
    fmt = sg_.get("format") or "single_choice"
    what = {"sound_object_location": f"describe the sound ONLY as {ch.get('sound_desc', 'the described sound')!r} (never name the object that makes it - identifying it is part of the task), then ask on / in which fixture that object is at the END of the clip",
            "sound_object_nearest": f"describe the sound ONLY as {ch.get('sound_desc', 'the described sound')!r} (never name the object), then ask which of the four listed objects that object is nearest to at the END of the clip, in real-world (3D) distance",
            "action_outcome_location": f"name the action by describing it ({ch.get('action_desc', '')!r}; the object may be named), then ask on / in which fixture the handled object ends up at the END of the clip"}[cap]
    return {"level": level, "format": fmt, "window_max_sec": None, "window_min_sec": None,
            "note": f"L3 {cap} tier {sg_.get('tier', level)} (chained reasoning: an L2 grounding step + a spatial step): media_refs = EXACTLY the offered window; {what}; "
                    + ("the program fills the four options (sg.ch.options) and the reference (sg.ch.answer): write placeholder options; " if fmt == "single_choice" else "short_answer: the Solver names the fixture; the program fills the reference and accepted alternatives; ")
                    + "never give a time position, never name the answer fixture in the question; say 'at the end of the clip'",
            "rule": "controller-fixed: exactly this format; media_refs = the offered window; private.sg_rel_id = sg.rel_id"}


def autofill(out, ctx, c):
    sg_ = c.get("sg") or {}; ch = sg_["ch"]; pub = out.setdefault("public", {}); pri = out.setdefault("private", {}); refs = pub.get("media_refs") or []
    want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]; filled = []
    if refs: refs[0]["windows"] = [list(w) for w in want]; del refs[1:]; filled.append("windows")
    fmt = sg_.get("format") or "single_choice"; pub["format"] = fmt
    if fmt == "single_choice":
        pub["options"] = [f"{L}. {_fixture_phrase(o) if ch['skill'] != 'sound_object_nearest' else o}" for L, o in zip("ABCD", ch["options"][:4])]
        pri["proposed_reference_answer"] = "ABCD"[ch["options"].index(ch["answer"])]
    else:
        pub.pop("options", None); pri["proposed_reference_answer"] = ch["answer"]; pri["accepted_alternatives"] = ch.get("accepted") or [ch["answer"]]
    pri["sg_rel_id"] = sg_["rel_id"]; pri["ch_note"] = ch["note"]; pri["frame_of_reference"] = ch["frame"]
    pub["observation_cutoff"] = want[-1][1]
    return filled + ["options", "reference", "sg_rel_id"]


_END = re.compile(r"\b(end of the clip|at the end|by the end|when the clip ends|as the clip ends|finally|last)\b")


def checks(out, ctx, c, q, wins):
    sg_ = c.get("sg") or {}; ch = sg_["ch"]; cap = ch["skill"]; e = []
    if cap in ("sound_object_location", "sound_object_nearest"):
        if not (SG._toks(ch["sound_label"]) & SG._toks(q)): e.append(f"{cap}: describe the sound with its class words ({ch['sound_label']!r})")
        if ch["n_same_in_clip"] > 1 and ORD.get(ch["ordinal"], "") not in q and f"{ch['ordinal']}" not in q: e.append(f"{cap}: the same sound occurs {ch['n_same_in_clip']} times in the clip - say which one ({ORD.get(ch['ordinal'])})")
        if SG._toks(ch["object"]) & SG._toks(q): e.append(f"{cap}: do not name the object ({ch['object']!r}) - identifying it from the sound is part of the task")
        if not re.search(r"\b(sound|noise|clink|clatter|rustle|heard|hear)\b", q): e.append(f"{cap}: refer to what is HEARD (the sound)")
    else:
        if len(SG._toks(ch["action_desc"]) & SG._toks(q)) < 2: e.append(f"{cap}: describe the action ({ch['action_desc']!r})")
    if cap != "sound_object_nearest":
        if re.search(r"\b" + re.escape(ch["answer"]) + r"\b", q): e.append(f"{cap}: do not name the answer fixture ({ch['answer']!r}) in the question")
        if not re.search(r"\b(where|which (fixture|surface|place|location)|on what|in what|on which|in which)\b", q): e.append(f"{cap}: ask WHERE (on / in which fixture) the object is")
    else:
        if not re.search(r"\b(nearest|closest|shortest distance)\b", q): e.append(f"{cap}: ask which listed object it is nearest to")
        if not re.search(r"\b(3d|three-dimensional|real-world|actual|physical|straight-line|in space)\b", q): e.append(f"{cap}: say the distance is real-world (3D) distance, not distance on the screen")
    if not _END.search(q): e.append(f"{cap}: say the question is about the END of the clip")
    if SG._TIME_CUE.search(_END.sub(" ", q)): e.append(f"{cap}: no time position in the question")   # 11-04 晚:'at the end of the clip' 是题面必需的,不算时间提示(v30 首跑 54 题全因此作废)
    want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]
    if len(wins) != len(want) or any(abs(wins[i][j] - want[i][j]) > 0.05 for i in range(len(want)) for j in (0, 1)):
        e.append(f"{cap}: media_refs must be exactly the offered window {want} (got {wins})")
    return e


HARNESS = """    - sound_object_location / sound_object_nearest / action_outcome_location (sg.l3_kind = chain; sg.ch; 11-04 v30, CHAINED L2 -> L3): every item
      contains an L2 grounding step plus a spatial step. sound_*: describe the sound ONLY by its class and, if it occurs more than once in the clip,
      which occurrence (sg.ch.sound_desc, e.g. "the second 'metal-only collision' sound"); NEVER name the object that makes it (that is what the Solver
      must work out); then ask where that object is at the END of the clip (sound_object_location: on / in which fixture; sound_object_nearest: which of
      the four listed objects it is nearest to, real-world 3D distance). action_outcome_location: describe the action (sg.ch.action_desc; the object
      may be named) and ask on / in which fixture the handled object ends up at the END of the clip. Never name the answer fixture, never give a time.
      media_refs = EXACTLY the offered window; the program fills options (sg.ch.options) and the reference (sg.ch.answer); private.sg_rel_id = sg.rel_id.
"""
