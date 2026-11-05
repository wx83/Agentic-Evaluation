"""11-03 v26(用户定,按 SpaceAct 的 frame-aware 瓶颈):L3 新增两个 skill,GT = 官方 3D 位置 + SLAM 相机位姿(pose_hdepic)。
  ego_direction_unseen  某 planner event 结束那一刻,之前放下 / 看到过、此刻不在画面里的物体 X 在佩戴者的哪个方向(front-left / front-right / back-left / back-right,
                        水平方位,egocentric,以当时相机朝向为前)
  turn_to_face          同一类 (时刻, 物体),问要正对 X 该怎么转:左约 90° / 右约 90° / 转身 / 几乎不转(|方位| < 30 不转;30–135 左 / 右;≥ 135 转身)
同一个 (时刻, 物体) 只给一个 skill(两个 skill 轮流分),每 task 每 skill 最多 ED_PER_SKILL 题(按时间均匀取);档 = 方位角离边界余量的四分位(余量小 = 难);
全部单选、选项与参考由程序填;题面不给时间;clip = 从物体最后一次被看到(锚点)前 5 s 连续到提问时刻(≤ 60 s)。"""
import re, math, random, collections
import sg as SG
import l3ext as LX

ED_SKILLS = ["ego_direction_unseen", "turn_to_face"]
ED_QUADS = ["front-left", "front-right", "back-left", "back-right"]
ED_TURNS = ["turn left by about a quarter turn (about 90 degrees)", "turn right by about a quarter turn (about 90 degrees)",
            "turn around (about 180 degrees)", "almost no turn: it is roughly straight ahead"]
ED_MIN_MARGIN = 15.0        # 方位角离象限边界 / 转向区间边界 ≥ 15°
ED_RANGE = (0.3, 4.0)       # 物体到相机的水平距离
ED_MIN_GAP = 3.0            # 物体最后一次被看到(锚点)到提问时刻 ≥ 3 s(真的要记)
ED_MAX_CLIP = 60.0          # 连续 clip 上限
ED_PER_SKILL = 12           # 每 task 每 skill 最多题数
ED_PAD = 5.0
ED_MAX_SPREAD = 0.3         # 同 track 锚点互相偏差 > 0.3 m 不用(GT 核验 11-03 晚)
ED_FOV_HALF = 50.0          # |方位| < 50° 视为可能在画面里(Aria RGB 水平视野 ≈ 110°)
ED_FRAME = ("egocentric at the MOMENT named in the question: from the camera wearer's own viewpoint, facing the way the camera faces then; "
            "horizontal direction (ignore up / down) to where the object is resting then; the object was seen earlier in the clip and may be out of view at that moment")
SKILL_DEFS = {"ego_direction_unseen": "L3 (egocentric frame transform, 3D + camera pose): at the moment of the described event, in which horizontal direction (front-left / front-right / back-left / back-right, relative to the wearer's facing then) is a named object that was seen earlier and is now out of view",
              "turn_to_face": "L3 (egocentric frame transform, 3D + camera pose): at the moment of the described event, how would the wearer have to turn to face a named object that is now out of view (left ~90 / right ~90 / turn around / almost no turn)"}


def _turn(ang):
    a = abs(ang)
    if a < 30: return ED_TURNS[3], min(abs(a - 30), 1e9)
    if a >= 135: return ED_TURNS[2], abs(a - 135)
    return (ED_TURNS[0] if ang > 0 else ED_TURNS[1]), min(abs(a - 30), abs(a - 135))


_CACHE = {}


def clusters(store, ti, plan, skill):
    key = (ti["task_id"], id(plan))
    if key not in _CACHE: _CACHE[key] = _build(store, ti, plan)
    return list(_CACHE[key].get(skill, []))


def _build(store, ti, plan):
    vid = ti["video_id"]; POSE = LX._pose(store, vid)
    out = {s: [] for s in ED_SKILLS}
    if POSE is None or not POSE.available(vid): return out
    T0, T1 = ti["t0"], ti["t1"]
    moves = [r for r in SG._recs(store, vid, T0 - ED_MAX_CLIP, T1, kinds={"object_move"}) if (r["value"] or {}).get("end_xyz")]
    masks = [r for r in SG._recs(store, vid, T0 - ED_MAX_CLIP, T1, kinds={"object_mask_anchor"}) if (r["value"] or {}).get("xyz") and (r["value"] or {}).get("name")]
    vis = SG._recs(store, vid, T0 - ED_MAX_CLIP, T1 + 5, kinds={"object_visible_track"})
    anchors = []                                                   # (t, xyz, track_id, base_name, rec, how)
    for r in masks:
        v = r["value"]; anchors.append((float(r["time"]["start_sec"]), v["xyz"], v.get("track_id"), LX._base(v["name"]), r, f"seen on the {v.get('fixture_kind') or 'surface'}"))
    
    for r in moves:
        v = r["value"]; anchors.append((float(r["time"]["end_sec"]), v["end_xyz"], v.get("track_id"), LX._base(v.get("object_name") or ""), r, f"put down on the {v.get('to_fixture_kind') or 'surface'}"))
    anchors = [a for a in anchors if a[2] and a[3] and LX._nameable(a[3]) and "mid-air" not in a[5]]          # 11-03 晚 GT 核验:在手里(mid-air)的锚点不是静止位置,不用
    mask_by_track = collections.defaultdict(list)
    for r in masks: mask_by_track[r["value"].get("track_id")].append((float(r["time"]["start_sec"]), r["value"]["xyz"]))
    evs = sorted([e for e in plan["events"].values() if e.get("matched")], key=lambda e: e["centre"])
    pre = []
    for ei, e in enumerate(evs):
        T = None
        for cand_t in (float(e["time"][1]), float(e["centre"])):
            if cand_t <= T1 + 0.5 and POSE.at(vid, cand_t) is not None: T = cand_t; break
        if T is None: continue
        ev_objs = SG._toks(" ".join(e.get("objects") or []) + " " + (e.get("description") or ""))
        best = {}                                                  # track -> latest usable anchor
        for a in anchors:
            t, xyz, tid, base, rec, how = a
            if t > T - ED_MIN_GAP or t < T - (ED_MAX_CLIP - ED_PAD): continue
            if any(q["value"].get("track_id") == tid and t < float(q["time"]["start_sec"]) <= T for q in moves): continue      # 锚点之后又被挪过:位置不可信
            if tid not in best or t > best[tid][0]: best[tid] = a
        cands = []
        for tid, (t, xyz, _, base, rec, how) in best.items():
            if SG._toks(base) & ev_objs: continue                                                                           # 事件本身在操作它(在手里 / 画面里)
            if any(x["value"].get("track_id") == tid and float(x["time"]["start_sec"]) <= T and float(x["time"]["end_sec"]) >= T - 1.0 for x in vis): continue   # 此刻看得见
            w0 = max(0.0, t - ED_PAD)
            if any(b != base and False for b in ()): pass
            same = [a for a in anchors if a[3] == base and a[2] != tid and w0 <= a[0] <= T]                                    # 同名其它实例在 clip 里出现过:指代不清
            if same: continue
            if any(LX._dist(xyz, p) > ED_MAX_SPREAD for s_, p in mask_by_track.get(tid, []) if t - 0.5 <= s_ <= T): continue     # 同 track 其它锚点与它不一致(> 0.3 m):位置不可信
            b = LX._bearing(POSE, vid, T, xyz)
            if b is None: continue
            ang, fwd, lat, rng, quad, margin, _f = b
            if not (ED_RANGE[0] <= rng <= ED_RANGE[1]): continue
            turn, tmargin = _turn(ang)
            in_view = abs(ang) < ED_FOV_HALF                                                                                        # 水平方位在相机视野内:visible_track 判不可见不可靠(13 的 food processor 实际在画面里)
            cands.append({"track": tid, "object": base, "t_anchor": t, "xyz": xyz, "rec": rec, "how": how, "ang": ang, "fwd": fwd, "lat": lat, "rng": rng,
                          "quad": quad, "qmargin": margin, "turn": turn, "tmargin": tmargin, "in_view": in_view, "w": [round(w0, 3), round(T, 3)]})
        if not cands: continue
        rng_ = random.Random(e["event_id"]); rng_.shuffle(cands)
        q_ok = [c for c in cands if c["qmargin"] >= ED_MIN_MARGIN and not c["in_view"]]; t_ok = [c for c in cands if c["tmargin"] >= ED_MIN_MARGIN]   # unseen:视野内的不出;turn_to_face 保留但记 in_view
        first = ED_SKILLS[ei % 2]
        pick = {}
        for sk in (first, ED_SKILLS[1 - ED_SKILLS.index(first)]):
            pool = [c for c in (q_ok if sk == "ego_direction_unseen" else t_ok) if c["track"] not in {p["track"] for p in pick.values()}]
            if not pool: continue
            akey = "quad" if sk == "ego_direction_unseen" else "turn"
            used = collections.Counter(p[3][akey] for p in pre if p[0] == sk)              # 答案类别尽量均衡(否则一个 task 里 6/7 都是 back-right)
            pick[sk] = min(pool, key=lambda c: used[c[akey]])
        for sk, c in pick.items():
            if any(p[0] == sk and p[3]["object"] == c["object"] and abs(p[2] - T) < 0.5 for p in pre): continue                     # 两个 event 同一结束时刻 + 同一物体:只出一题
            pre.append((sk, e, T, c))
    for sk in ED_SKILLS:
        rows = sorted([p for p in pre if p[0] == sk], key=lambda p: p[2])
        if len(rows) > ED_PER_SKILL:                                   # 时间均匀取 ED_PER_SKILL 个
            idx = sorted({int(i * len(rows) / ED_PER_SKILL) for i in range(ED_PER_SKILL)}); rows = [rows[i] for i in idx]
        knobs = {f"{e['event_id']}:{c['track']}": -(c["qmargin"] if sk == "ego_direction_unseen" else c["tmargin"]) for _, e, T, c in rows}
        bands = SG._bands(knobs)
        for _, e, T, c in rows:
            k = f"{e['event_id']}:{c['track']}"; tier = bands.get(k, 2)
            w = c["w"]; margin = c["qmargin"] if sk == "ego_direction_unseen" else c["tmargin"]
            answer = c["quad"] if sk == "ego_direction_unseen" else c["turn"]; options = list(ED_QUADS) if sk == "ego_direction_unseen" else list(ED_TURNS)
            core = [c["rec"]] + SG._recs(store, vid, w[0], w[1], kinds={"action_narration"})
            for rid in e["records"]:
                r = store.get(rid)
                if r is not None and r["solver_access"] != "answer_only": core.append(r)
            core = list({r["evidence_id"]: r for r in core}.values())
            step = next((s_ for s_ in ti["steps"] if s_["t0"] - 0.5 <= T <= s_["t1"] + 0.5), None)
            if step and step["idx"] in ti["step_rec"]: core.append(ti["step_rec"][step["idx"]])
            side = "left" if c["lat"] >= 0 else "right"; fb = "ahead of" if c["fwd"] >= 0 else "behind"
            meta = {"kind": "L3", "v24": True, "l3_kind": "ego_dir", "tier": tier, "format": "single_choice", "rel_id": f"ed_{sk[:4]}_{e['event_id']}_{c['track'][-6:]}", "rel_type": sk,
                    "idx": step["idx"] if step else None, "this_sub_goal": step["idx"] if step else None,
                    "ed": {"skill": sk, "object": c["object"], "moment_desc": e["description"], "moment_event": e["event_id"], "options": options, "answer": answer,
                           "last_seen": f"{c['how']} {round(T - c['t_anchor'], 1)} s before the moment", "seen_gap_sec": round(T - c["t_anchor"], 1),
                           "bearing_deg": round(c["ang"], 1), "quadrant": c["quad"], "turn": c["turn"], "margin_deg": round(margin, 1), "range_m": round(c["rng"], 2),
                           "forward_m": round(c["fwd"], 2), "lateral_m": round(c["lat"], 2), "in_view_likely": c["in_view"], "frame": ED_FRAME,
                           "note": f"at the moment the {c['object']} is {round(abs(c['fwd']), 2)} m {fb} the wearer and {round(abs(c['lat']), 2)} m to the wearer's {side} (bearing {round(c['ang'], 0):+.0f} deg, + = left), {round(c['rng'], 2)} m away; it was last {c['how']} {round(T - c['t_anchor'], 1)} s earlier and has no visible track at the moment"},
                    "events": [{k_: e[k_] for k_ in ("event_id", "sub_goal", "type", "description", "objects", "time", "records")}],
                    "windows": [list(w)], "n_segments": 1, "total_sec": round(w[1] - w[0], 1),
                    "window_rule": f"one continuous clip from 5 s before the object was last seen to the moment of the event (<= {ED_MAX_CLIP:.0f} s); tier {tier} = quartile of the bearing margin (4 = smallest); single_choice",
                    "band_rule": "tier = quartile of the angular margin between the object's bearing and the nearest answer boundary (quadrant boundary / turn-bin boundary); smaller margin = harder"}
            cl = SG._mk_cluster(sk, ti, store, windows=[w], cutoff=w[1], anchor=c["rec"], core=core, sg_meta=meta)
            out[sk].append(cl)
        out[sk].sort(key=lambda c: c["window"][0])
    return out


def spec_for(cap, level, c=None):
    sg_ = (c or {}).get("sg") or {}; ed = sg_.get("ed") or {}
    what = ("ask in which horizontal direction the object is relative to the wearer at that moment: front-left / front-right / back-left / back-right"
            if cap == "ego_direction_unseen" else "ask how the wearer would have to turn, at that moment, to face the object: left about a quarter turn / right about a quarter turn / turn around / almost no turn")
    return {"level": level, "format": "single_choice", "window_max_sec": None, "window_min_sec": None,
            "note": f"L3 {cap} tier {sg_.get('tier', level)}: media_refs = EXACTLY the offered window; the clip ends at the moment of the event sg.ed.moment_desc; "
                    f"name that moment by describing the event (never by time) and name the object exactly as '{ed.get('object')}' (it was {ed.get('last_seen')} and may be out of view at that moment: answer from memory of where it is and how the wearer has moved); "
                    f"{what}; STATE THE FRAME: relative to you (the camera wearer), facing the way you are facing at that moment, horizontal direction to where the object is resting now; "
                    "the program fills the four options (sg.ed.options) and the reference (sg.ed.answer): write placeholder options; do NOT say where the object is or hint at the direction",
            "rule": "controller-fixed: single_choice; window = the offered window; no time position; name the moment by the event and the object by name; egocentric frame stated"}


def autofill(out, ctx, c):
    sg_ = c.get("sg") or {}; ed = sg_["ed"]; pub = out.setdefault("public", {}); pri = out.setdefault("private", {}); refs = pub.get("media_refs") or []
    want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]; filled = []
    if refs: refs[0]["windows"] = [list(w) for w in want]; del refs[1:]; filled.append("windows")
    pub["format"] = "single_choice"
    pub["options"] = [f"{L}. {o}" for L, o in zip("ABCD", ed["options"][:4])]
    pri["proposed_reference_answer"] = "ABCD"[ed["options"].index(ed["answer"])]
    pri["sg_rel_id"] = sg_["rel_id"]; pri["ed_note"] = ed["note"]; pri["frame_of_reference"] = ed["frame"]
    pub["observation_cutoff"] = want[-1][1]
    return filled + ["options", "reference", "sg_rel_id"]


_EGO = re.compile(r"\b(you|your|yourself|wearer|wearer's|camera)\b")
_MOMENT = re.compile(r"\b(when|while|after|before|as|once|at the moment|by the time|just as|right after|the instant)\b")


def checks(out, ctx, c, q, wins):
    sg_ = c.get("sg") or {}; ed = sg_["ed"]; e = []; cap = ed["skill"]
    if not (SG._toks(ed["object"]) & SG._toks(q)): e.append(f"{cap}: the question must name the object {ed['object']!r}")
    if not _MOMENT.search(q): e.append(f"{cap}: name the moment by describing the event ({ed['moment_desc']!r}), e.g. 'at the moment the ... is ...', never by time")
    if not _EGO.search(q): e.append(f"{cap}: state the egocentric frame: relative to you / the camera wearer, facing the way you face at that moment")
    if SG._TIME_CUE.search(q): e.append(f"{cap}: no time position in the question")
    if cap == "ego_direction_unseen":
        if re.search(r"\b(front|back)-(left|right)\b", q): e.append(f"{cap}: do not name any quadrant in the question (they are the options)")
        if not re.search(r"\b(direction|where)\b", q): e.append(f"{cap}: ask in which direction the object is relative to the wearer")
    else:
        if not re.search(r"\b(turn|face|facing)\b", q): e.append(f"{cap}: ask how the wearer would have to turn to face the object")
        if re.search(r"\b(turn (left|right|around)|no turn|straight ahead)\b", q): e.append(f"{cap}: do not name any turn option in the question")
    if re.search(r"\b(to (your|the) (left|right)|behind you|in front of you|ahead of you)\b", q): e.append(f"{cap}: the question must not say where the object is (that is the answer)")
    want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]
    if len(wins) != len(want) or any(abs(wins[i][j] - want[i][j]) > 0.05 for i in range(len(want)) for j in (0, 1)):
        e.append(f"{cap}: media_refs must be exactly the offered window {want} (got {wins})")
    return e


HARNESS = """    - ego_direction_unseen / turn_to_face (sg.l3_kind = ego_dir; sg.ed; 11-03 v26): the clip runs from just before a named object
      (sg.ed.object) was last seen / put down to the moment of one event (sg.ed.moment_desc = the END of the clip); at that moment
      the object may be out of view. The question names the moment by describing that event (never a time), names the object exactly,
      and states the frame: relative to you (the camera wearer), facing the way you face at that moment, horizontal direction to
      where the object is resting now. ego_direction_unseen asks in which direction it is (options = front-left / front-right /
      back-left / back-right); turn_to_face asks how you would have to turn to face it (left ~90 / right ~90 / turn around / almost
      no turn). Never say or hint where the object is. media_refs = EXACTLY the offered window; the program fills the options
      (sg.ed.options) and the reference (sg.ed.answer): write placeholder options; private.sg_rel_id = sg.rel_id.
"""
