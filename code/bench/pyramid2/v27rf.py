"""11-03 v27(用户定):L3 再加两个 reference-frame transformation skill,GT = Digital-Twin fixture mesh 质心 + SLAM 相机位姿(pose_hdepic)。
  fixture_clock_direction  「<事件> 那一刻按你看的方向,<fixture> 在几点钟方向?」12 个 30° 扇区(12 = 正前,3 = 右,9 = 左),4 个钟点选项;fixture 视野外(|方位| ≥ 50°)、
                           离扇区边界 ≥ 7.5°、距离 1–5 m(质心太近时方位对站位敏感)、clip 里进过视野;同官方 VQA 3d_perception_fixture_location 题型
  layout_transform         「如果你站在 <F1> 前面朝 <F2>,<F3> 在你左 / 右 / 正前 / 正后?」站位 = 视频里相机靠近 F1 且面朝它时的平均位置;朝向 = F1 站位 → F2 质心;
                           F3 方位离 30° / 150° 边界 ≥ 15°、距离 ≥ 1 m;clip = sub-goal 前 60 s 且三者都进过视野
每 task 每 skill ≤ 12 题、答案类别贪心均衡、档 = 几何余量四分位;单选、程序填选项;题面不给时间。"""
import re, math, random, collections, glob, os
from pathlib import Path
import numpy as np
import sg as SG
import l3ext as LX

RF_SKILLS = ["fixture_clock_direction", "layout_transform"]
MESH_ROOT = Path(os.environ.get("HDEPIC_ROOT", "/mnt/data_new/hd-epic")) / "Digital-Twin" / "meshes"
MAJOR = {"sink": "sink", "hob": "hob", "oven": "oven", "fridge": "fridge", "fridgefreezer": "fridge", "bin": "bin", "dishwasher": "dishwasher", "microwave": "microwave",
         "table": "table", "washingmachine": "washing machine", "boiler": "boiler", "kettle": "kettle", "toaster": "toaster"}
FOV_HALF = 50.0; CLK_MARGIN = 7.5; CLK_RANGE = (1.0, 5.0); LT_MARGIN = 15.0; LT_MIN_RANGE = 1.0; LT_MIN_SEP = 0.8; MAX_CLIP = 60.0; PER_SKILL = 12
LT_OPTIONS = ["to your left", "to your right", "straight ahead of you", "behind you"]
FRAME_CLK = "egocentric at the moment named in the question: clock face laid flat around you, 12 o'clock = the direction the camera faces then, 3 o'clock = your right, 9 o'clock = your left, 6 o'clock = behind you; horizontal only"
FRAME_LT = "hypothetical egocentric frame: you stand where a person stands to use fixture F1 and face fixture F2; left / right / ahead / behind are relative to that facing; horizontal only"
SKILL_DEFS = {"fixture_clock_direction": "L3 (reference frame transformation, kitchen fixture + camera pose): at the moment of the described event, in which clock direction (relative to where the wearer looks) is a named fixture that is out of view",
              "layout_transform": "L3 (reference frame transformation, kitchen layout): if the wearer stood at fixture F1 facing fixture F2, would fixture F3 be to their left / right / ahead / behind"}

_MESH = {}


def meshes(part):
    if part not in _MESH:
        out = {}
        for p in glob.glob(str(MESH_ROOT / part / "*.obj")):
            V = np.array([[float(x) for x in l.split()[1:4]] for l in open(p) if l.startswith("v ")])
            if len(V): out[os.path.basename(p)[:-4]] = {"c": V.mean(0), "lo": V.min(0), "hi": V.max(0)}
        kinds = collections.Counter(n.split("_", 1)[1].split(".")[0] for n in out)
        big = {}
        for n, m in out.items():
            k = n.split("_", 1)[1].split(".")[0]
            if k in MAJOR and kinds[k] == 1: big[MAJOR[k]] = m          # 同类唯一才能用名字指代
        _MESH[part] = big
    return _MESH[part]


def _clock(ang):
    cf = ((-ang) % 360) / 30.0; clk = int(round(cf)) % 12 or 12
    return clk, abs((cf + 0.5) % 1 - 0.5) * 30.0


def _seen_in(POSE, vid, w, xyz, step=0.5):
    """窗口内某个时刻该点进过视野(|方位| < FOV_HALF 且 ≤ 5 m)。"""
    t = w[0]
    while t <= w[1]:
        b = LX._bearing(POSE, vid, t, xyz)
        if b and abs(b[0]) < FOV_HALF and b[3] <= 5.0: return True
        t += step
    return False


def _stand_pos(POSE, vid, ti, xyz):
    """站在 fixture 前的位置:视频里相机离质心 ≤ 1.2 m 且面朝它(|方位| < 40°)的采样位置均值(至少 5 个样本)。"""
    d = POSE.load(vid); lo = np.searchsorted(d["_t"], max(0, ti["t0"] - 120)); hi = np.searchsorted(d["_t"], ti["t1"] + 120)
    pts = []
    for i in range(lo, hi, 5):
        T = float(d["_t"][i]); b = LX._bearing(POSE, vid, T, xyz)
        if b and b[3] <= 1.2 and abs(b[0]) < 40: pts.append(POSE.at(vid, T)[0][:2])
    return np.mean(pts, 0) if len(pts) >= 5 else None


_CACHE = {}


def clusters(store, ti, plan, skill):
    key = (ti["task_id"], id(plan))
    if key not in _CACHE: _CACHE[key] = _build(store, ti, plan)
    return list(_CACHE[key].get(skill, []))


def _build(store, ti, plan):
    vid = ti["video_id"]; part = vid.split("-")[0]; POSE = LX._pose(store, vid)
    out = {s: [] for s in RF_SKILLS}
    if POSE is None or not POSE.available(vid): return out
    big = meshes(part)
    if len(big) < 3: return out
    m = store.media_of_video(vid); D = (m or {}).get("duration_sec") or 1e9
    evs = sorted([e for e in plan["events"].values() if e.get("matched")], key=lambda e: e["centre"])
    # ---- fixture_clock_direction
    pre = []
    for e in evs:
        T = next((x for x in (float(e["time"][1]), float(e["centre"])) if x <= ti["t1"] + 0.5 and POSE.at(vid, x) is not None), None)
        if T is None: continue
        w = [round(max(0.0, T - MAX_CLIP), 3), round(T, 3)]
        cands = []
        for name, mm in big.items():
            b = LX._bearing(POSE, vid, T, mm["c"])
            if b is None or not (CLK_RANGE[0] <= b[3] <= CLK_RANGE[1]) or abs(b[0]) < FOV_HALF: continue
            clk, marg = _clock(b[0])
            if marg < CLK_MARGIN or not _seen_in(POSE, vid, w, mm["c"]): continue
            cands.append({"fixture": name, "clock": clk, "margin": marg, "ang": b[0], "rng": b[3], "w": w})
        if not cands: continue
        used = collections.Counter(p[2]["clock"] for p in pre)
        random.Random(e["event_id"]).shuffle(cands)
        pre.append(("fixture_clock_direction", e, min(cands, key=lambda c: used[c["clock"]]), T))
    out["fixture_clock_direction"] = _emit_clock(store, ti, POSE, _cap(pre), vid)
    # ---- layout_transform
    names = sorted(big); stand = {n: _stand_pos(POSE, vid, ti, big[n]["c"]) for n in names}
    triples = []
    for a in names:
        if stand[a] is None: continue
        for b in names:
            if b == a: continue
            f = big[b]["c"][:2] - stand[a]
            if np.linalg.norm(f) < 0.8: continue
            f = f / np.linalg.norm(f); l = np.array([-f[1], f[0]])
            for c3 in names:
                if c3 in (a, b): continue
                v = big[c3]["c"][:2] - stand[a]; rng = float(np.linalg.norm(v))
                if rng < LT_MIN_RANGE or float(np.linalg.norm(big[c3]["c"][:2] - big[b]["c"][:2])) < LT_MIN_SEP: continue        # F2 / F3 水平上叠在一起(hob 上 oven 下)不出
                ang = math.degrees(math.atan2(float(v @ l), float(v @ f)))
                sec = LT_OPTIONS[2] if abs(ang) < 30 else LT_OPTIONS[3] if abs(ang) > 150 else (LT_OPTIONS[0] if ang > 0 else LT_OPTIONS[1])
                marg = min(abs(abs(ang) - 30), abs(abs(ang) - 150))
                if marg < LT_MARGIN: continue
                triples.append({"F1": a, "F2": b, "F3": c3, "answer": sec, "ang": ang, "margin": marg, "rng": rng, "stand": [round(float(x), 2) for x in stand[a]]})
    pre = []
    for s_ in ti["steps"]:
        w = [round(s_["t0"], 3), round(min(s_["t1"], s_["t0"] + MAX_CLIP, D), 3)]
        if w[1] - w[0] < 10: continue
        seen = {n for n in names if _seen_in(POSE, vid, w, big[n]["c"], step=1.0)}
        ok = [t for t in triples if {t["F1"], t["F2"], t["F3"]} <= seen]
        if not ok: continue
        rng_ = random.Random(f"{ti['task_id']}:{s_['idx']}"); rng_.shuffle(ok)
        picked = []
        for _ in range(2):                                                   # 每个 sub-goal 最多 2 题,答案均衡、三元组不重复
            used = collections.Counter(p[2]["answer"] for p in pre)
            taken = [q[2] for q in pre] + picked                                                                    # 同一三元组整个 task 只出一次(俯视图核验:13 的 hob→sink→fridge 出了两遍)
            c = next((t for t in sorted(ok, key=lambda t: used[t["answer"]]) if all(t is not q and (t["F1"], t["F2"], t["F3"]) != (q["F1"], q["F2"], q["F3"]) for q in taken) and not any(q["F1"] == t["F1"] and q["F3"] == t["F3"] for q in picked)), None)
            if c is None: break
            picked.append(c); pre.append(("layout_transform", s_, c, w))
    out["layout_transform"] = _emit_layout(store, ti, _cap(pre), vid)
    return out


def _cap(pre):
    if len(pre) <= PER_SKILL: return pre
    idx = sorted({int(i * len(pre) / PER_SKILL) for i in range(PER_SKILL)}); return [pre[i] for i in idx]


def _core_for(store, ti, vid, w, T):
    core = SG._recs(store, vid, w[0], w[1], kinds={"action_narration"})
    step = next((s_ for s_ in ti["steps"] if s_["t0"] - 0.5 <= T <= s_["t1"] + 0.5), None)
    if step and step["idx"] in ti["step_rec"]: core.append(ti["step_rec"][step["idx"]])
    return list({r["evidence_id"]: r for r in core}.values()), step


def _emit_clock(store, ti, POSE, rows, vid):
    bands = SG._bands({f"{e['event_id']}:{c['fixture']}": -c["margin"] for _, e, c, T in rows}); out = []
    for _, e, c, T in rows:
        tier = bands.get(f"{e['event_id']}:{c['fixture']}", 2); w = c["w"]
        rng_ = random.Random(e["event_id"] + c["fixture"]); pool = [k for k in range(1, 13) if min(abs(k - c["clock"]), 12 - abs(k - c["clock"])) >= 2]
        dis = []
        while len(dis) < 3 and pool:
            k = rng_.choice(pool); dis.append(k); pool = [x for x in pool if min(abs(x - k), 12 - abs(x - k)) >= 2]
        opts = [f"{k} o'clock" for k in sorted(dis + [c["clock"]])]
        core, step = _core_for(store, ti, vid, w, T)
        for rid in e["records"]:
            r = store.get(rid)
            if r is not None and r["solver_access"] != "answer_only": core.append(r)
        core = list({r["evidence_id"]: r for r in core}.values())
        anchor = next((r for r in core if r["kind"] == "action_narration"), core[0])
        meta = {"kind": "L3", "v24": True, "l3_kind": "ref_frame", "tier": tier, "format": "single_choice", "rel_id": f"rf_clk_{e['event_id']}_{c['fixture'].replace(' ', '')}", "rel_type": "fixture_clock_direction",
                "idx": step["idx"] if step else None, "this_sub_goal": step["idx"] if step else None,
                "rf": {"skill": "fixture_clock_direction", "fixture": c["fixture"], "moment_desc": e["description"], "moment_event": e["event_id"], "options": opts, "answer": f"{c['clock']} o'clock",
                       "bearing_deg": round(c["ang"], 1), "margin_deg": round(c["margin"], 1), "range_m": round(c["rng"], 2), "frame": FRAME_CLK,
                       "note": f"the {c['fixture']} (digital-twin mesh centre) is at bearing {c['ang']:+.0f} deg (+ = left) = {c['clock']} o'clock, {c['rng']:.1f} m away, outside the camera's view at that moment; it came into view earlier in the clip"},
                "events": [{k_: e[k_] for k_ in ("event_id", "sub_goal", "type", "description", "objects", "time", "records")}],
                "windows": [list(w)], "n_segments": 1, "total_sec": round(w[1] - w[0], 1),
                "window_rule": f"one continuous clip of up to {MAX_CLIP:.0f} s ending at the moment of the event; tier {tier} = quartile of the clock-sector margin (4 = smallest); single_choice",
                "band_rule": "tier = quartile of the angular margin to the nearest clock-sector boundary; smaller = harder"}
        out.append(SG._mk_cluster("fixture_clock_direction", ti, store, windows=[w], cutoff=w[1], anchor=anchor, core=core, sg_meta=meta))
    out.sort(key=lambda c: c["window"][0]); return out


def _emit_layout(store, ti, rows, vid):
    bands = SG._bands({f"{s_['idx']}:{c['F1']}:{c['F2']}:{c['F3']}": -c["margin"] for _, s_, c, w in rows}); out = []
    for _, s_, c, w in rows:
        tier = bands.get(f"{s_['idx']}:{c['F1']}:{c['F2']}:{c['F3']}", 2)
        core, step = _core_for(store, ti, vid, w, w[0] + 0.1)
        anchor = ti["step_rec"].get(s_["idx"]) or core[0]
        meta = {"kind": "L3", "v24": True, "l3_kind": "ref_frame", "tier": tier, "format": "single_choice", "rel_id": f"rf_lt_s{s_['idx']}_{c['F1']}_{c['F2']}_{c['F3']}".replace(" ", ""), "rel_type": "layout_transform",
                "idx": s_["idx"], "this_sub_goal": s_["idx"],
                "rf": {"skill": "layout_transform", "F1": c["F1"], "F2": c["F2"], "F3": c["F3"], "options": list(LT_OPTIONS), "answer": c["answer"],
                       "bearing_deg": round(c["ang"], 1), "margin_deg": round(c["margin"], 1), "range_m": round(c["rng"], 2), "frame": FRAME_LT,
                       "note": f"standing position for the {c['F1']} = mean camera position when the wearer used it ({c['stand']}); facing the {c['F2']}; the {c['F3']} (mesh centre) is then at bearing {c['ang']:+.0f} deg (+ = left), {c['rng']:.1f} m away; all three fixtures come into view in the clip"},
                "events": [], "windows": [list(w)], "n_segments": 1, "total_sec": round(w[1] - w[0], 1),
                "window_rule": f"the first {MAX_CLIP:.0f} s of the sub-goal (all three fixtures come into view in it); tier {tier} = quartile of the angular margin (4 = smallest); single_choice",
                "band_rule": "tier = quartile of the angular margin to the nearest sector boundary (30 / 150 deg); smaller = harder"}
        out.append(SG._mk_cluster("layout_transform", ti, store, windows=[w], cutoff=w[1], anchor=anchor, core=core, sg_meta=meta))
    out.sort(key=lambda c: c["window"][0]); return out


def spec_for(cap, level, c=None):
    sg_ = (c or {}).get("sg") or {}; rf = sg_.get("rf") or {}
    if cap == "fixture_clock_direction":
        note = (f"L3 fixture_clock_direction tier {sg_.get('tier', level)}: media_refs = EXACTLY the offered window (it ends at the moment of the event sg.rf.moment_desc); name that moment by describing the event (never by time) "
                f"and ask in which clock direction the {rf.get('fixture')} is, given the direction you (the camera wearer) are looking at that moment: say explicitly that 12 o'clock is straight ahead, 3 o'clock your right, 9 o'clock your left, 6 o'clock behind you; "
                "the fixture is out of view at that moment; the program fills the four clock options (sg.rf.options) and the reference (sg.rf.answer): write placeholder options; never hint at the direction")
    else:
        note = (f"L3 layout_transform tier {sg_.get('tier', level)}: media_refs = EXACTLY the offered window (the clip shows the kitchen; no moment is involved); ask a hypothetical: 'If you stood at the {rf.get('F1')} (where a person stands to use it) facing the {rf.get('F2')}, where would the {rf.get('F3')} be?' "
                "- name all three fixtures exactly, say the answer is relative to that imagined position and facing, horizontal only; the program fills the options (sg.rf.options: to your left / to your right / straight ahead of you / behind you) and the reference (sg.rf.answer): write placeholder options; never hint at the answer; no time words")
    return {"level": level, "format": "single_choice", "window_max_sec": None, "window_min_sec": None, "note": note,
            "rule": "controller-fixed: single_choice; window = the offered window; no time position; frame stated explicitly"}


def autofill(out, ctx, c):
    sg_ = c.get("sg") or {}; rf = sg_["rf"]; pub = out.setdefault("public", {}); pri = out.setdefault("private", {}); refs = pub.get("media_refs") or []
    want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]; filled = []
    if refs: refs[0]["windows"] = [list(w) for w in want]; del refs[1:]; filled.append("windows")
    pub["format"] = "single_choice"; pub["options"] = [f"{L}. {o}" for L, o in zip("ABCD", rf["options"][:4])]
    pri["proposed_reference_answer"] = "ABCD"[rf["options"].index(rf["answer"])]
    pri["sg_rel_id"] = sg_["rel_id"]; pri["rf_note"] = rf["note"]; pri["frame_of_reference"] = rf["frame"]; pub["observation_cutoff"] = want[-1][1]
    return filled + ["options", "reference", "sg_rel_id"]


_EGO = re.compile(r"\b(you|your|yourself|wearer|camera)\b")
_MOMENT = re.compile(r"\b(when|while|after|before|as|once|at the moment|by the time|just as|right after|the instant)\b")


def checks(out, ctx, c, q, wins):
    sg_ = c.get("sg") or {}; rf = sg_["rf"]; cap = rf["skill"]; e = []
    if SG._TIME_CUE.search(q): e.append(f"{cap}: no time position in the question")
    if not _EGO.search(q): e.append(f"{cap}: state the frame relative to you / the camera wearer")
    if cap == "fixture_clock_direction":
        if not (SG._toks(rf["fixture"]) & SG._toks(q)): e.append(f"{cap}: the question must name the fixture {rf['fixture']!r}")
        if not _MOMENT.search(q): e.append(f"{cap}: name the moment by describing the event ({rf['moment_desc']!r}), never by time")
        if not re.search(r"o'?clock|clock", q): e.append(f"{cap}: ask for the clock direction and explain the clock face (12 = straight ahead, 3 = your right, 9 = your left, 6 = behind)")
        if re.search(r"\b(1[0-2]|[1-9]) o'?clock\b", q) and not re.search(r"\b12 o'?clock\b.*\b3 o'?clock\b", q): pass
        # 11-04 修:只在提到 fixture 的那句里查泄漏;钟面说明句("3 is to your right")不算泄漏(v27 把 36 题全拒了)
        fx_toks = SG._toks(rf["fixture"])
        fx_sents = [s_ for s_ in re.split(r"(?<=[.?!])\s+", q) if fx_toks & SG._toks(s_)]
        if any(re.search(r"\b(to (your|the) (left|right)|behind you|in front of you|ahead of you)\b", s_) and not re.search(r"\b(1[0-2]|[1-9])\b", s_) for s_ in fx_sents):
            e.append(f"{cap}: do not say where the fixture is")
    else:
        for k in ("F1", "F2", "F3"):
            if not (SG._toks(rf[k]) & SG._toks(q)): e.append(f"{cap}: the question must name the fixture {rf[k]!r}")
        if not re.search(r"\b(stood|stand|standing|were standing)\b", q) or not re.search(r"\b(facing|faced|face)\b", q): e.append(f"{cap}: phrase it as 'if you stood at the {rf['F1']} facing the {rf['F2']} ...'")
        if re.search(r"\b(to (your|the) (left|right)|behind you|straight ahead|in front of you|ahead of you)\b", q): e.append(f"{cap}: do not name any option in the question")
    want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]
    if len(wins) != len(want) or any(abs(wins[i][j] - want[i][j]) > 0.05 for i in range(len(want)) for j in (0, 1)):
        e.append(f"{cap}: media_refs must be exactly the offered window {want} (got {wins})")
    return e


HARNESS = """    - fixture_clock_direction / layout_transform (sg.l3_kind = ref_frame; sg.rf; 11-03 v27): reference-frame transformation on the
      kitchen's fixed fixtures (sink, hob, oven, fridge ...), answers from the digital-twin fixture positions and the camera pose.
      fixture_clock_direction: the clip ends at the moment of one event (sg.rf.moment_desc); ask in which clock direction the named
      fixture (sg.rf.fixture, out of view then) is, given where you are looking at that moment, and explain the clock face
      (12 = straight ahead, 3 = your right, 9 = your left, 6 = behind you); options = four clock values. layout_transform: no
      moment; ask the hypothetical "if you stood at the <F1> (where one stands to use it) facing the <F2>, where would the <F3>
      be?" (to your left / right / straight ahead / behind you). Name the fixtures exactly, never hint at the answer, no time
      words. media_refs = EXACTLY the offered window; the program fills the options (sg.rf.options) and the reference
      (sg.rf.answer): write placeholder options; private.sg_rel_id = sg.rel_id.
"""
