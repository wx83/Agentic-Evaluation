"""11-04 晚 v31(用户定:cross_event / object_location_at_time / object_state_change 只是读标注,改成真要时空推理的版本;GT 仍全来自官方
object_move、mask 3D、SLAM 位姿、association_id):
  object_location_at_event      「<事件 B> 那一刻,X 在哪?」题面不说 X 中间被挪过;X 在 A..B 之间至少挪过一次且位置变了;选项 = fixture + 「在佩戴者手里」
                                档 = A..B 之间 X 的移动次数(越多越难)
  object_displacement_direction 「从 <事件 A> 到 <事件 B>,X 被挪到了你(B 时刻)的哪个方向 / 离 <fixture> 更近还是更远?」
                                dir 型:位移向量在 B 时刻相机坐标系的方位(前 / 左 / 后 / 右,离扇区边界 ≥ 15°);fix 型:到 Digital-Twin fixture 质心的距离变化(|Δ| ≥ 0.3 m)
                                档 = 角度 / 距离余量四分位
  object_identity_continuity    「<事件 B> 用的 X,是不是 <事件 A> 用的那个?」(同名多实例时,GT = association_id 是否相同)
                                或「从 A 到 B,X 被放下过几次?」(GT = 该实例 object_move 计数:0 / 1 / 2 / ≥3)
                                档 = A..B 间隔时长四分位
选项与参考由程序填;clip 连续 ≤ 60 s;盲猜可答作废重出。"""
import collections, math, random, re
import numpy as np
import sg as SG
import l3ext as LX

RS_SKILLS = ["object_location_at_event", "object_displacement_direction", "object_identity_continuity"]
SKILL_DEFS = {
    "object_location_at_event": "L3 (spatio-temporal tracking): at the moment of a described event, where is a named object that was moved (possibly more than once) since an earlier event - which fixture, or in the wearer's hand",
    "object_displacement_direction": "L3 (spatio-temporal, egocentric / metric): between two described events an object was moved - in which direction relative to the wearer at the later moment, or closer to / farther from a named fixture (3D)",
    "object_identity_continuity": "L3 (identity through time): is the object used at the later event the same instance as at the earlier event / how many times was it put down in between",
}
MAX_CLIP, PRE, POST, PER_SKILL = 60.0, 5.0, 2.0, 12
MIN_GAP, MIN_DISP, DIR_MARGIN, FIX_DELTA = 8.0, 0.3, 15.0, 0.3        # 11-04 晚(用户定,不 tailor):按标注精度定阈值 —— mask 3D 锚点误差 ~0.05–0.1 m,位移 / 距离变化 ≥ 0.3 m 才可信;方向余量 ≥ 15°(与 v26 一致);出不了题的 task 报 NOT_EVALUATED
HAND = "in the camera wearer's hand"
DIRS = ["ahead of you", "to your left", "behind you", "to your right"]
CF = ["closer to it", "farther from it", "about the same distance", "it was not moved"]
CNT = ["not put down at all", "put down once", "put down twice", "put down three or more times"]
_CACHE = {}


def _base(name): return re.sub(r"\s*\d+$", "", (name or "").strip().lower())
def _t(r): return float(r["time"]["start_sec"]), float(r["time"]["end_sec"])
def _dist3(a, b): return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def clusters(store, ti, plan, skill):
    key = (ti["task_id"], id(plan))
    if key not in _CACHE: _CACHE[key] = _build(store, ti, plan)
    return list(_CACHE[key].get(skill, []))


def _dir_at(POSE, vid, T, vec):
    """位移向量 vec(世界系)在 T 时刻相机坐标系里的水平方位:(sector, margin_deg) 或 None。"""
    p = POSE.at(vid, T)
    if p is None: return None
    cam, R = p
    f = LX._horiz(R @ np.array([0.0, 0.0, 1.0])); l = LX._horiz(R @ np.array([0.0, 1.0, 0.0]))
    if f is None or l is None: return None
    fwd = vec[0] * f[0] + vec[1] * f[1]; lat = vec[0] * l[0] + vec[1] * l[1]
    ang = math.degrees(math.atan2(lat, fwd))                     # 0 = 正前,+ = 左
    a = abs(ang)
    sec = DIRS[0] if a < 45 else (DIRS[2] if a > 135 else (DIRS[1] if ang > 0 else DIRS[3]))
    margin = min(abs(a - 45), abs(a - 135)) if 45 <= a <= 135 else (45 - a if a < 45 else a - 135)
    return sec, margin, round(ang, 1)


def _build(store, ti, plan):
    vid = ti["video_id"]; m = store.media_of_video(vid); D = (m or {}).get("duration_sec") or 1e9
    T0, T1 = ti["t0"], ti["t1"]
    moves = sorted([r for r in SG._recs(store, vid, T0 - 2, T1 + 2, kinds={"object_move"}) if (r["value"] or {}).get("object_name") and (r["value"] or {}).get("association_id")], key=lambda r: _t(r)[0])
    narr = SG._recs(store, vid, T0 - 2, T1 + 2, kinds={"action_narration"})
    evs = sorted([e for e in plan["events"].values() if e.get("matched")], key=lambda e: e["centre"])
    fx = collections.Counter(v for r in moves for k in ("from_fixture_kind", "to_fixture_kind") for v in [(r["value"] or {}).get(k)] if v and v != "mid-air")
    video_fixtures = [k for k, _ in fx.most_common(8)]
    POSE = LX._pose(store, vid)
    try:
        import v27rf as RF; MESH = RF.meshes(vid.split("-")[0])
    except Exception: MESH = {}
    def _step_of(t): return next((s for s in ti["steps"] if s["t0"] - 0.5 <= t <= s["t1"] + 0.5), None)
    def _ev_objs(e): return SG._toks(" ".join(e.get("objects") or []) + " " + (e.get("description") or ""))
    def _core(w, extra):
        core = list(extra) + [r for r in narr if _t(r)[0] <= w[1] and _t(r)[1] >= w[0]]
        core = list({r["evidence_id"]: r for r in core}.values()); st = _step_of(w[1])
        if st and st["idx"] in ti["step_rec"]: core.append(ti["step_rec"][st["idx"]])
        return core, st
    def _evmeta(*es): return list({e["event_id"]: {k_: e[k_] for k_ in ("event_id", "sub_goal", "type", "description", "objects", "time", "records")} for e in es if e}.values())
    def _opts(answer, pool, rid, fixed=None):
        opts = [answer] + [p for p in (fixed or []) if p != answer]
        for k in pool:
            if k not in opts: opts.append(k)
        opts = opts[:4]; rr = random.Random(rid); rr.shuffle(opts); return opts
    by_assoc = collections.defaultdict(list)
    for r in moves: by_assoc[r["value"]["association_id"]].append(r)
    out = {sk: [] for sk in RS_SKILLS}; pre = {sk: [] for sk in RS_SKILLS}
    pairs = [(a, b) for i, a in enumerate(evs) for b in evs[i + 1:] if MIN_GAP <= float(b["time"][1]) - float(a["time"][0]) and float(b["time"][1]) + POST - max(0.0, float(a["time"][0]) - PRE) <= MAX_CLIP]
    for a, b in pairs:
        ta0, ta1 = float(a["time"][0]), float(a["time"][1]); tb0, tb1 = float(b["time"][0]), float(b["time"][1])
        w = [round(max(0.0, ta0 - PRE), 3), round(min(D, tb1 + POST), 3)]
        for aid, mvs in by_assoc.items():
            obj = _base(mvs[0]["value"]["object_name"])
            if not obj or SG._toks(obj) & _ev_objs(b): continue                 # B 正在操作它:位置显然(在手里)
            between = [x for x in mvs if ta1 - 0.5 <= _t(x)[0] <= tb0 + 0.5]
            if not between: continue
            # 同名其它实例在 clip 里也动过:指代不清
            if any(_base(x["value"]["object_name"]) == obj and x["value"]["association_id"] != aid and w[0] <= _t(x)[0] <= w[1] for x in moves): continue
            before = [x for x in mvs if _t(x)[1] <= ta1 + 0.5]
            loc_a = (before[-1]["value"].get("to_fixture_kind") if before else between[0]["value"].get("from_fixture_kind"))
            last = between[-1]
            loc_b = HAND if _t(last)[0] <= tb0 <= _t(last)[1] else last["value"].get("to_fixture_kind")
            if not loc_b or loc_b == "mid-air" or (loc_b == loc_a and len(between) < 2): continue      # 位置没变且只动一次:不用追踪也能答(动 ≥2 次 = 拿走又放回,要追踪)
            core, st = _core(w, between + ([before[-1]] if before else []))
            for rid_ in a["records"] + b["records"]:
                r = store.get(rid_)
                if r is not None and r["solver_access"] != "answer_only": core.append(r)
            core = list({r["evidence_id"]: r for r in core}.values())
            rid = f"rs_loc_{a['event_id']}_{b['event_id']}_{aid[:6]}"
            pool = [k for k in video_fixtures if k != loc_b] + [HAND]
            if loc_b != HAND and loc_a and loc_a != "mid-air": pool = [loc_a] + [k for k in pool if k != loc_a]
            opts = _opts(loc_b, pool, rid)
            pre["object_location_at_event"].append((len(between), {
                "kind": "L3", "v24": True, "l3_kind": "rsn", "tier": None, "format": "single_choice", "rel_id": rid, "rel_type": "object_location_at_event",
                "idx": st["idx"] if st else None, "this_sub_goal": st["idx"] if st else None,
                "rs": {"skill": "object_location_at_event", "object": obj, "assoc": aid, "event_a": a["event_id"], "desc_a": a["description"], "event_b": b["event_id"], "desc_b": b["description"],
                       "n_moves_between": len(between), "loc_at_a": loc_a, "answer": loc_b, "options": opts, "chain": [(x["value"].get("from_fixture_kind"), x["value"].get("to_fixture_kind"), round(_t(x)[0] - w[0], 1)) for x in between],
                       "frame": "allocentric: the fixture the object rests on / in at the moment of event B (or in the wearer's hand if it is being carried then); from the official 3D object-movement annotation",
                       "note": f"{obj} was at {loc_a} around event A and is moved {len(between)}x in between; at event B it is {loc_b}"},
                "events": _evmeta(a, b), "windows": [w], "n_segments": 1, "total_sec": round(w[1] - w[0], 1),
                "window_rule": f"one continuous clip from 5 s before event A to 2 s after event B (<= {MAX_CLIP:.0f} s)",
                "band_rule": "tier = quartile of the number of times the object is moved between A and B (more moves = harder); the question must NOT say the object was moved"}, w, core, between[0]))
            # identity continuity: 同名多实例 → 是否同一实例;否则「放下几次」
            if SG._toks(obj) & _ev_objs(a):
                pass
            used_a = [x for x in moves if _base(x["value"]["object_name"]) == obj and _t(x)[0] <= ta1 + 3 and _t(x)[1] >= ta0 - 3]
            used_b = [x for x in moves if _base(x["value"]["object_name"]) == obj and _t(x)[0] <= tb1 + 3 and _t(x)[1] >= tb0 - 3]
            if used_a and used_b and len({x["value"]["association_id"] for x in moves if _base(x["value"]["object_name"]) == obj}) >= 2:
                same = used_a[0]["value"]["association_id"] == used_b[0]["value"]["association_id"]
                ans = "yes, the same one" if same else "no, a different one"
                rid2 = f"rs_idn_{a['event_id']}_{b['event_id']}_{obj.replace(' ', '')[:8]}"
                core2, st2 = _core(w, used_a + used_b)
                pre["object_identity_continuity"].append((tb1 - ta0, {
                    "kind": "L3", "v24": True, "l3_kind": "rsn", "tier": None, "format": "single_choice", "rel_id": rid2, "rel_type": "object_identity_continuity",
                    "idx": st2["idx"] if st2 else None, "this_sub_goal": st2["idx"] if st2 else None,
                    "rs": {"skill": "object_identity_continuity", "variant": "same_instance", "object": obj, "event_a": a["event_id"], "desc_a": a["description"], "event_b": b["event_id"], "desc_b": b["description"],
                           "answer": ans, "options": [ans] + [o for o in ("yes, the same one", "no, a different one", "neither event involves it", "it cannot be told from the clip") if o != ans][:3],
                           "frame": "identity: the same physical instance (official object association id) handled at event A and at event B",
                           "note": f"{obj} at A assoc {used_a[0]['value']['association_id'][:6]}, at B assoc {used_b[0]['value']['association_id'][:6]} -> {ans}"},
                    "events": _evmeta(a, b), "windows": [w], "n_segments": 1, "total_sec": round(w[1] - w[0], 1),
                    "window_rule": f"one continuous clip from 5 s before event A to 2 s after event B (<= {MAX_CLIP:.0f} s)", "band_rule": "tier = quartile of the time between A and B"}, w, core2, used_a[0]))
            elif used_a and used_b and used_a[0]["value"]["association_id"] == used_b[0]["value"]["association_id"]:
                n_down = sum(1 for x in mvs if ta1 - 0.5 < _t(x)[1] < tb0 + 0.5 and (x["value"].get("to_fixture_kind") not in (None, "mid-air")))
                ans = CNT[min(n_down, 3)]
                rid2 = f"rs_cnt_{a['event_id']}_{b['event_id']}_{aid[:6]}"
                core2, st2 = _core(w, mvs)
                pre["object_identity_continuity"].append((tb1 - ta0, {
                    "kind": "L3", "v24": True, "l3_kind": "rsn", "tier": None, "format": "single_choice", "rel_id": rid2, "rel_type": "object_identity_continuity",
                    "idx": st2["idx"] if st2 else None, "this_sub_goal": st2["idx"] if st2 else None,
                    "rs": {"skill": "object_identity_continuity", "variant": "put_down_count", "object": obj, "event_a": a["event_id"], "desc_a": a["description"], "event_b": b["event_id"], "desc_b": b["description"],
                           "answer": ans, "options": list(CNT), "n_put_down": n_down,
                           "frame": "identity through time: the same instance (official association id) used at A and at B; count its recorded placements (object_move with a fixture destination) strictly between A and B",
                           "note": f"{obj} (same instance at A and B) put down {n_down}x between A and B"},
                    "events": _evmeta(a, b), "windows": [w], "n_segments": 1, "total_sec": round(w[1] - w[0], 1),
                    "window_rule": f"one continuous clip from 5 s before event A to 2 s after event B (<= {MAX_CLIP:.0f} s)", "band_rule": "tier = quartile of the time between A and B"}, w, core2, used_a[0]))
    # displacement direction / fixture distance:每个 object_move(位移 ≥ 0.3 m),A = 起点附近事件,B = 终点附近事件
    def _ev_near(t, pad=8.0):
        c = [e for e in evs if abs(e["centre"] - t) <= pad]
        return min(c, key=lambda e: abs(e["centre"] - t)) if c else None
    for mv in moves:
        v = mv["value"]
        if not (v.get("start_xyz") and v.get("end_xyz")): continue
        disp = _dist3(v["start_xyz"], v["end_xyz"])
        if disp < MIN_DISP: continue
        ts, te = _t(mv); obj = _base(v["object_name"]); aid = v["association_id"]
        eA, eB = _ev_near(ts, 10.0), _ev_near(te, 10.0)
        if eA is None or eB is None: continue                                     # 同一事件也可以问(「在 <事件> 中 X 被往哪个方向挪」)
        if any(_base(x["value"]["object_name"]) == obj and x["value"]["association_id"] != aid and ts - 10 <= _t(x)[0] <= te + 10 for x in moves): continue
        w = [round(max(0.0, min(ts, float(eA["time"][0])) - PRE), 3), round(min(D, max(te, float(eB["time"][1])) + POST), 3)]
        if w[1] - w[0] > MAX_CLIP: continue
        TB = float(eB["time"][1])
        vec = (float(v["end_xyz"][0]) - float(v["start_xyz"][0]), float(v["end_xyz"][1]) - float(v["start_xyz"][1]))
        core, st = _core(w, [mv])
        for rid_ in eA["records"] + eB["records"]:
            r = store.get(rid_)
            if r is not None and r["solver_access"] != "answer_only": core.append(r)
        core = list({r["evidence_id"]: r for r in core}.values())
        base_rs = {"object": obj, "assoc": aid, "move": mv["evidence_id"], "event_a": eA["event_id"], "desc_a": eA["description"], "event_b": eB["event_id"], "desc_b": eB["description"], "same_event": eA["event_id"] == eB["event_id"],
                   "from_fixture": v.get("from_fixture_kind"), "to_fixture": v.get("to_fixture_kind"), "displacement_m": round(disp, 2)}
        d = _dir_at(POSE, vid, TB, vec) if POSE is not None and POSE.available(vid) else None
        if d and d[1] >= DIR_MARGIN and math.hypot(*vec) >= MIN_DISP:
            sec, margin, ang = d; rid = f"rs_dir_{mv['evidence_id'].split(':')[-1][:12]}"
            pre["object_displacement_direction"].append((-margin, {
                "kind": "L3", "v24": True, "l3_kind": "rsn", "tier": None, "format": "single_choice", "rel_id": rid, "rel_type": "object_displacement_direction",
                "idx": st["idx"] if st else None, "this_sub_goal": st["idx"] if st else None,
                "rs": dict(base_rs, skill="object_displacement_direction", variant="direction", answer=sec, options=list(DIRS), margin_deg=round(margin, 1), bearing_deg=ang,
                           frame="egocentric at the moment of event B: the direction of the object's net displacement (from where it was at A to where it is at B), relative to the way the camera wearer faces at B (SLAM camera pose + official 3D object positions)",
                           note=f"{obj} moved {disp:.2f} m {v.get('from_fixture_kind')} -> {v.get('to_fixture_kind')}; displacement bearing at B = {ang:+.0f} deg (+ = left) -> {sec}"),
                "events": _evmeta(eA, eB), "windows": [w], "n_segments": 1, "total_sec": round(w[1] - w[0], 1),
                "window_rule": f"one continuous clip from 5 s before event A to 2 s after event B (<= {MAX_CLIP:.0f} s)",
                "band_rule": "tier = quartile of the angular margin to the nearest sector boundary (45 / 135 deg); smaller = harder"}, w, core, mv))
        for fname, mesh in (MESH or {}).items():
            if fname in (obj,) or SG._toks(fname) & SG._toks(obj): continue
            d0, d1 = _dist3(v["start_xyz"], mesh["c"]), _dist3(v["end_xyz"], mesh["c"])
            if abs(d1 - d0) < FIX_DELTA or max(d0, d1) > 6.0: continue
            if fname in (v.get("from_fixture_kind"), v.get("to_fixture_kind")): continue          # 起点 / 终点就是它:题面会泄漏
            rid = f"rs_fix_{mv['evidence_id'].split(':')[-1][:12]}_{fname.replace(' ', '')}"
            pre["object_displacement_direction"].append((-abs(d1 - d0), {
                "kind": "L3", "v24": True, "l3_kind": "rsn", "tier": None, "format": "single_choice", "rel_id": rid, "rel_type": "object_displacement_direction",
                "idx": st["idx"] if st else None, "this_sub_goal": st["idx"] if st else None,
                "rs": dict(base_rs, skill="object_displacement_direction", variant="fixture_distance", fixture=fname, answer=(CF[0] if d1 < d0 else CF[1]), options=list(CF), delta_m=round(d1 - d0, 2),
                           frame=f"allocentric, metric: real-world 3D distance from the object to the {fname} (digital-twin fixture centre) at A vs at B",
                           note=f"{obj}: distance to {fname} {d0:.2f} m -> {d1:.2f} m"),
                "events": _evmeta(eA, eB), "windows": [w], "n_segments": 1, "total_sec": round(w[1] - w[0], 1),
                "window_rule": f"one continuous clip from 5 s before event A to 2 s after event B (<= {MAX_CLIP:.0f} s)",
                "band_rule": "tier = quartile of |distance change| to the fixture; smaller = harder"}, w, core, mv))
    for sk in RS_SKILLS:
        rows = pre[sk]
        if not rows: continue
        bands = SG._bands({m_["rel_id"]: k for k, m_, _w, _c, _a in rows})
        seen = set(); picked = []; used = collections.Counter(); cap_same = max(2, PER_SKILL // 2)
        for k, m_, w, core, anchor in sorted(rows, key=lambda x: x[2][0]):
            if m_["rel_id"] in seen: continue
            ans = m_["rs"]["answer"]
            if used[ans] >= cap_same: continue
            seen.add(m_["rel_id"]); used[ans] += 1
            m_["tier"] = bands.get(m_["rel_id"], 2); m_["format"] = "short_answer" if m_["tier"] == 4 and sk == "object_location_at_event" else "single_choice"
            m_["window_rule"] += f"; tier {m_['tier']}"
            picked.append((m_, w, core, anchor))
        if len(picked) > PER_SKILL:
            idx = sorted({int(i * len(picked) / PER_SKILL) for i in range(PER_SKILL)}); picked = [picked[i] for i in idx]
        for m_, w, core, anchor in picked:
            out[sk].append(SG._mk_cluster(sk, ti, store, windows=[list(w)], cutoff=w[1], anchor=anchor, core=core, sg_meta=m_))
    return out


# ---------------------------------------------------------------- Examiner 接口
def spec_for(cap, level, c=None):
    sg_ = (c or {}).get("sg") or {}; rs = sg_.get("rs") or {}; fmt = sg_.get("format") or "single_choice"
    what = {"object_location_at_event": f"ask where the {rs.get('object', 'object')!r} is AT THE MOMENT of event B ({rs.get('desc_b', '')!r}): on / in which fixture, or in the wearer's hand; name event B by describing it; do NOT mention that the object was moved, where it was earlier, or event A",
            "object_displacement_direction": ((f"ask: during the event {rs.get('desc_b', '')!r}, in which direction relative to you (facing the way the camera faces at the end of that event) was the {rs.get('object', 'object')!r} moved overall" if rs.get("same_event")
                                               else f"ask: between event A ({rs.get('desc_a', '')!r}) and event B ({rs.get('desc_b', '')!r}), in which direction relative to you (facing the way the camera faces at the moment of B) was the {rs.get('object', 'object')!r} moved overall") if rs.get("variant") == "direction"
                                              else f"ask: between event A ({rs.get('desc_a', '')!r}) and event B ({rs.get('desc_b', '')!r}), did the {rs.get('object', 'object')!r} end up closer to or farther from the {rs.get('fixture', 'fixture')} (real-world 3D distance)"),
            "object_identity_continuity": (f"ask whether the {rs.get('object', 'object')!r} used at event B ({rs.get('desc_b', '')!r}) is the same physical one that was used at event A ({rs.get('desc_a', '')!r})" if rs.get("variant") == "same_instance"
                                           else f"ask how many times the {rs.get('object', 'object')!r} was put down (placed on a surface or in a container) between event A ({rs.get('desc_a', '')!r}) and event B ({rs.get('desc_b', '')!r})")}[cap]
    return {"level": level, "format": fmt, "window_max_sec": None, "window_min_sec": None,
            "note": f"L3 {cap} tier {sg_.get('tier', level)} (spatio-temporal reasoning over official 3D / pose / identity annotations): media_refs = EXACTLY the offered window; {what}; "
                    + ("the program fills the options (sg.rs.options) and the reference (sg.rs.answer): write placeholder options; " if fmt == "single_choice" else "short_answer: the Solver names the place; the program fills the reference; ")
                    + "never give a time position; never state or hint at the answer; name events only by describing them",
            "rule": "controller-fixed: exactly this format; media_refs = the offered window; private.sg_rel_id = sg.rel_id"}


def autofill(out, ctx, c):
    sg_ = c.get("sg") or {}; rs = sg_["rs"]; pub = out.setdefault("public", {}); pri = out.setdefault("private", {}); refs = pub.get("media_refs") or []
    want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]; filled = []
    if refs: refs[0]["windows"] = [list(w) for w in want]; del refs[1:]; filled.append("windows")
    fmt = sg_.get("format") or "single_choice"; pub["format"] = fmt
    if fmt == "single_choice":
        texts = [(o if (o == HAND or rs["skill"] != "object_location_at_event") else f"on / in the {o}") for o in rs["options"][:4]]
        pub["options"] = [f"{L}. {o}" for L, o in zip("ABCD", texts)]
        pri["proposed_reference_answer"] = "ABCD"[rs["options"].index(rs["answer"])]
    else:
        pub.pop("options", None); pri["proposed_reference_answer"] = rs["answer"]; pri["accepted_alternatives"] = [rs["answer"], f"on the {rs['answer']}", f"in the {rs['answer']}"]
    pri["sg_rel_id"] = sg_["rel_id"]; pri["rs_note"] = rs["note"]; pri["frame_of_reference"] = rs["frame"]
    pub["observation_cutoff"] = want[-1][1]
    return filled + ["options", "reference", "sg_rel_id"]


_EGO = re.compile(r"\b(you|your|yourself|wearer|camera)\b")


def checks(out, ctx, c, q, wins):
    sg_ = c.get("sg") or {}; rs = sg_["rs"]; cap = rs["skill"]; e = []
    if not (SG._toks(rs["object"]) & SG._toks(q)): e.append(f"{cap}: name the object ({rs['object']!r})")
    if len(SG._toks(rs["desc_b"]) & SG._toks(q)) < 2: e.append(f"{cap}: name event B by describing it ({rs['desc_b']!r})")
    if cap == "object_location_at_event":
        if len(SG._toks(rs["desc_a"]) & SG._toks(q)) >= 3 or re.search(r"\b(moved|move|relocat|carried|taken|brought|picked up|put down|placed)\b", q):
            e.append(f"{cap}: do not mention event A or that the object was moved - only ask where it is at the moment of event B")
        if rs["answer"] != HAND and re.search(r"\b" + re.escape(rs["answer"]) + r"\b", q): e.append(f"{cap}: do not name the answer fixture")
        if not re.search(r"\b(where|which (fixture|surface|place)|on which|in which|on what|in what)\b", q): e.append(f"{cap}: ask WHERE the object is")
    else:
        if not rs.get("same_event") and len(SG._toks(rs["desc_a"]) & SG._toks(q)) < 2: e.append(f"{cap}: name event A by describing it ({rs['desc_a']!r})")
        if cap == "object_displacement_direction":
            if rs.get("variant") == "direction":
                if not _EGO.search(q): e.append(f"{cap}: state the frame: relative to you, facing the way the camera faces at the moment of event B")
                if re.search(r"\b(ahead of you|behind you|to your (left|right)|forward|backward)\b", q): e.append(f"{cap}: do not name any direction option")
                if not re.search(r"\b(direction|which way|where to)\b", q): e.append(f"{cap}: ask in which direction the object was moved")
            else:
                if not (SG._toks(rs["fixture"]) & SG._toks(q)): e.append(f"{cap}: name the fixture ({rs['fixture']!r})")
                if not re.search(r"\b(closer|nearer|farther|further|distance)\b", q): e.append(f"{cap}: ask closer / farther (real-world distance)")
                if not re.search(r"\b(3d|three-dimensional|real-world|actual|physical|straight-line|in space)\b", q): e.append(f"{cap}: say the distance is real-world (3D), not on the screen")
        if cap == "object_identity_continuity":
            if rs.get("variant") == "same_instance" and not re.search(r"\b(same|identical|different)\b", q): e.append(f"{cap}: ask whether it is the same one")
            if rs.get("variant") == "put_down_count" and not re.search(r"\b(how many times|number of times|how often)\b", q): e.append(f"{cap}: ask how many times it was put down")
            if re.search(r"\b(once|twice|three|same one|different one)\b", q) and rs.get("variant") == "put_down_count": e.append(f"{cap}: do not name an option in the question")
    if SG._TIME_CUE.search(q): e.append(f"{cap}: no time position in the question")
    want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]
    if len(wins) != len(want) or any(abs(wins[i][j] - want[i][j]) > 0.05 for i in range(len(want)) for j in (0, 1)):
        e.append(f"{cap}: media_refs must be exactly the offered window {want} (got {wins})")
    return e


HARNESS = """    - object_location_at_event / object_displacement_direction / object_identity_continuity (sg.l3_kind = rsn; sg.rs; 11-04 v31, SPATIO-TEMPORAL
      REASONING replacing the read-the-annotation items): object_location_at_event - name event B by describing it and ask where the named object is
      at that moment (fixture or in the wearer's hand); NEVER mention event A, that the object was moved, or where it was before (tracking it is
      the task). object_displacement_direction - name events A and B; variant "direction": ask in which direction, relative to you facing as the
      camera faces at B, the object was moved overall; variant "fixture_distance": ask whether it ended up closer to or farther from the named
      fixture (real-world 3D distance). object_identity_continuity - variant "same_instance": is the object used at B the same physical one as at A;
      variant "put_down_count": how many times was it put down between A and B. Never name the answer, never give a time. media_refs = EXACTLY the
      offered window; the program fills options (sg.rs.options) and the reference (sg.rs.answer); private.sg_rel_id = sg.rel_id.
"""
