"""11-03 v29(用户定:用这一套跑 AEA example,L3 加 spatial audio reasoning):四个 L3 skill,GT = SAVVY-Bench speech 标注里「说话那一刻同伴相对佩戴者的方位 / 距离」
(utterance 记录的 bearing_deg(+ = 左)/ partner_distance_m,来自官方 MPS 轨迹 + 同伴录像轨迹)。题面用「同伴说了什么」定时刻(要听),不给时间。
  speaker_direction      同伴说 <话> 那一刻,他 / 她在你的 front-left / front-right / back-left / back-right(离象限边界 ≥ 10°)
  turn_to_face_speaker   同伴说 <话> 那一刻(多半不在画面里),你要怎么转才能正对他 / 她:左 ~90 / 右 ~90 / 转身 / 几乎不转(离区间边界 ≥ 10°)
  speaker_approach       从同伴说 <A> 到说 <B>,同伴离你更近了 / 更远了 / 差不多(|Δ| ≥ 0.5 m 或 ≤ 0.25 m)
  nearest_utterance      clip 里同伴说的四句话,哪一句是离你最近时说的(最近与次近差 ≥ 0.3 m)
档 = 几何余量四分位(角度 / 距离差);选项与参考全由程序填;盲猜硬过滤同 v26。"""
import collections, math, random, re
import sg as SG

SA_SKILLS = ["speaker_direction", "turn_to_face_speaker", "speaker_approach", "nearest_utterance", "sound_direction"]
QUADS = ["front-left", "front-right", "back-left", "back-right"]
TURNS = ["turn left about a quarter turn", "turn right about a quarter turn", "turn around", "almost no turn"]
APPR = ["closer to you (by more than half a metre)", "farther from you (by more than half a metre)", "about the same distance (within a quarter of a metre)", "the partner had left the room"]
MIN_MARGIN, MIN_RANGE, MAX_RANGE = 10.0, 0.3, 6.0
APPR_DELTA, APPR_SAME, APPR_GAP = (0.5, 0.25, (3.0, 90.0))
NU_MARGIN, NU_SPAN = 0.3, 120.0
PRE, PER_SKILL, FOV_HALF = 20.0, 12, 50.0
FRAME = ("egocentric: relative to you (the camera wearer), facing the way your camera faces at the moment the partner says it; horizontal direction / straight-line distance "
         "from your head to the partner's head (SAVVY-Bench ground truth from the official trajectories of both recordings)")
SKILL_DEFS = {
    "speaker_direction": "L3 (spatial audio, egocentric frame): at the moment the partner says a quoted / paraphrased sentence (the partner may be out of view), in which horizontal direction is the partner relative to the wearer's facing: front-left / front-right / back-left / back-right",
    "turn_to_face_speaker": "L3 (spatial audio, frame-aware): at the moment the partner says a quoted sentence, how the wearer would have to turn to face the partner (left ~90 / right ~90 / turn around / almost no turn)",
    "speaker_approach": "L3 (spatial audio over time): between the partner saying sentence A and later sentence B, did the partner get closer to the wearer, farther, or stay about the same distance",
    "nearest_utterance": "L3 (spatial audio, integration over the clip): of four partner sentences heard in the clip, which one was said from the shortest distance to the wearer",
    "sound_direction": "L3 (spatial audio, single-person AEA): when a described sound of the task happens (a fridge door, a tap, a can set down), from which horizontal direction relative to the wearer's facing it comes: front / your left / your right / behind you (sounding fixture located in 3D)",
}
SECTORS = ["straight ahead of you", "to your left", "to your right", "behind you"]
_CACHE = {}


def _quad(ang):          # ang: + = left
    q = ("front" if abs(ang) < 90 else "back") + "-" + ("left" if ang > 0 else "right")
    return q, min(abs(ang), abs(90 - abs(ang)), abs(180 - abs(ang)))


def _turn(ang):
    a = abs(ang)
    if a < 30: return TURNS[3], 30 - a
    if a >= 135: return TURNS[2], a - 135
    return (TURNS[0] if ang > 0 else TURNS[1]), min(a - 30, 135 - a)


def clusters(store, ti, plan, skill):
    key = (ti["task_id"], id(plan))
    if key not in _CACHE: _CACHE[key] = _build(store, ti, plan)
    return list(_CACHE[key].get(skill, []))


def _utts(store, ti):
    vid = ti["video_id"]
    U = [r for r in SG._recs(store, vid, ti["t0"] - 1, ti["t1"] + 1, kinds={"utterance"}) if (r["value"] or {}).get("speaker") == "partner" and (r["value"] or {}).get("bearing_deg") is not None
         and "UNRELATED_TO_GOAL" not in r["quality_flags"]]
    return sorted(U, key=lambda r: r["time"]["start_sec"])


def _step_of(ti, t):
    return next((s for s in ti["steps"] if s["t0"] - 1 <= t <= s["t1"] + 1), None)


def _ev_for(plan, rid):
    return next((e for e in plan["events"].values() if rid in (e.get("records") or [])), None)


def _utt_pub(r):
    v = r["value"]; return {"id": r["evidence_id"], "event_ref": v.get("event_ref"), "text": v.get("text"), "topic": v.get("topic"), "t": [r["time"]["start_sec"], r["time"]["end_sec"]]}


def _mk(store, ti, plan, sk, anchor, w, core, sa, knob, rel_key):
    s = _step_of(ti, anchor["time"]["start_sec"])
    ev = _ev_for(plan, anchor["evidence_id"])
    meta = {"kind": "L3", "v24": True, "l3_kind": "spk", "tier": None, "format": "single_choice", "rel_id": f"sa_{sk[:4]}_{rel_key}", "rel_type": sk,
            "idx": s["idx"] if s else None, "sub_goal_text": s["text"] if s else None, "sub_goal_window": [s["t0"], s["t1"]] if s else None,
            "sa": {"skill": sk, "frame": FRAME, **sa}, "knob": knob,
            "events": ([{k: ev[k] for k in ("event_id", "sub_goal", "type", "description", "objects", "time", "records") if k in ev}] if ev else []),
            "windows": [list(w)], "n_segments": 1, "total_sec": round(w[1] - w[0], 1),
            "window_rule": f"one continuous clip ending at the end of the anchor utterance (<= {PRE + 90:.0f} s); tier = quartile of the geometric margin (4 = smallest); single_choice",
            "band_rule": "tier = quartile of the margin that decides the answer (angle to the nearest option boundary / distance difference); smaller margin = harder"}
    return SG._mk_cluster(sk, ti, store, windows=[list(w)], cutoff=None, anchor=anchor, core=core, sg_meta=meta)


def _build(store, ti, plan):
    vid = ti["video_id"]; m = store.media_of_video(vid); D = (m or {}).get("duration_sec") or 1e9
    out = {s: [] for s in SA_SKILLS}
    U = _utts(store, ti)                                        # 单人 AEA 没有同伴 utterance:只出 sound_direction
    narr = lambda a, b: SG._recs(store, vid, a, b, kinds={"action_narration", "sound_event"})
    pre = {s: [] for s in SA_SKILLS}
    # --- speaker_direction / turn_to_face_speaker:每句同伴的话一个候选;同一句只给一个 skill(交替),out-of-view 优先
    for i, r in enumerate(U):
        v = r["value"]; ang = float(v["bearing_deg"]); rng = float(v.get("partner_distance_m") or 0)
        if not (MIN_RANGE <= rng <= MAX_RANGE): continue
        T = float(r["time"]["end_sec"]); w = [round(max(0.0, T - PRE), 3), round(min(D, T + 0.5), 3)]
        q, qm = _quad(ang); tb, tm = _turn(ang); inview = abs(ang) < FOV_HALF
        core = [r] + [x for x in U if w[0] <= x["time"]["start_sec"] <= w[1] and x is not r] + narr(w[0], w[1]) + ([ti["step_rec"][_step_of(ti, T)["idx"]]] if _step_of(ti, T) and _step_of(ti, T)["idx"] in ti["step_rec"] else [])
        base = {"utterance": _utt_pub(r), "bearing_deg": round(ang, 1), "distance_m": round(rng, 2), "partner_in_view_likely": inview, "quadrant": q, "turn": tb}
        if qm >= MIN_MARGIN:
            pre["speaker_direction"].append((r, w, core, {**base, "options": list(QUADS), "answer": q, "margin_deg": round(qm, 1),
                                                           "note": f"when the partner says {v['text']!r} they are at bearing {ang:+.0f} deg (+ = left), {rng:.2f} m away = {q}; {'likely in view' if inview else 'likely out of the camera view'}"}, -qm, v["event_ref"]))
        if tm >= MIN_MARGIN:
            pre["turn_to_face_speaker"].append((r, w, core, {**base, "options": list(TURNS), "answer": tb, "margin_deg": round(tm, 1),
                                                              "note": f"when the partner says {v['text']!r} they are at bearing {ang:+.0f} deg (+ = left), {rng:.2f} m away: to face them = {tb}; {'likely in view' if inview else 'likely out of the camera view'}"}, -tm, v["event_ref"]))
    # 同一句话只给一个 skill:按句子交替,out-of-view 优先放进 speaker_direction
    seen = set()
    for sk in ("speaker_direction", "turn_to_face_speaker"):
        keep = []
        for it in sorted(pre[sk], key=lambda it: (it[3]["partner_in_view_likely"], it[0]["time"]["start_sec"])):
            ref = it[5]
            if ref in seen: continue
            other = "turn_to_face_speaker" if sk == "speaker_direction" else "speaker_direction"
            if any(x[5] == ref for x in pre[other]) and len(keep) > len([x for x in pre[other] if x[5] not in seen]) : continue
            seen.add(ref); keep.append(it)
        pre[sk] = keep
    # --- speaker_approach:相邻(或隔一句)的两句同伴话,距离差明显或几乎不变
    for i, a in enumerate(U):
        for b in U[i + 1:i + 3]:
            da, db = a["value"].get("partner_distance_m"), b["value"].get("partner_distance_m")
            if da is None or db is None: continue
            gap = b["time"]["start_sec"] - a["time"]["end_sec"]
            if not (APPR_GAP[0] <= gap <= APPR_GAP[1]): continue
            d = float(db) - float(da)
            if abs(d) >= APPR_DELTA: ans = APPR[0] if d < 0 else APPR[1]; marg = abs(d) - APPR_DELTA
            elif abs(d) <= APPR_SAME: ans = APPR[2]; marg = APPR_SAME - abs(d)
            else: continue
            w = [round(max(0.0, a["time"]["start_sec"] - 3.0), 3), round(min(D, b["time"]["end_sec"] + 0.5), 3)]
            core = [a, b] + [x for x in U if w[0] <= x["time"]["start_sec"] <= w[1] and x not in (a, b)] + narr(w[0], w[1])
            pre["speaker_approach"].append((b, w, core, {"utterance": _utt_pub(b), "utterance_a": _utt_pub(a), "utterance_b": _utt_pub(b), "distance_a_m": round(float(da), 2), "distance_b_m": round(float(db), 2),
                                                        "options": list(APPR), "answer": ans, "margin_m": round(marg, 2), "partner_in_view_likely": abs(float(b["value"]["bearing_deg"])) < FOV_HALF,
                                                        "note": f"partner distance {float(da):.2f} m when saying {a['value']['text']!r} -> {float(db):.2f} m when saying {b['value']['text']!r} (delta {d:+.2f} m) = {ans}"},
                                           -marg, f"{a['value']['event_ref']}_{b['value']['event_ref']}"))
    # --- nearest_utterance:滑动取 4 句同伴话(跨度 ≤ NU_SPAN),最近与次近差 ≥ NU_MARGIN
    for i in range(len(U) - 3):
        four = U[i:i + 4]
        if four[-1]["time"]["end_sec"] - four[0]["time"]["start_sec"] > NU_SPAN: continue
        ds = [(float(x["value"]["partner_distance_m"]), x) for x in four if x["value"].get("partner_distance_m") is not None]
        if len(ds) < 4: continue
        ds.sort(key=lambda t: t[0]); marg = ds[1][0] - ds[0][0]
        if marg < NU_MARGIN: continue
        best = ds[0][1]
        w = [round(max(0.0, four[0]["time"]["start_sec"] - 3.0), 3), round(min(D, four[-1]["time"]["end_sec"] + 0.5), 3)]
        core = list(four) + narr(w[0], w[1])
        opts = [x["value"]["text"] for x in four]
        pre["nearest_utterance"].append((best, w, core, {"utterance": _utt_pub(best), "utterances": [_utt_pub(x) for x in four], "distances_m": {x["value"]["event_ref"]: round(float(x["value"]["partner_distance_m"]), 2) for x in four},
                                                        "options": opts, "answer": best["value"]["text"], "margin_m": round(marg, 2), "partner_in_view_likely": abs(float(best["value"]["bearing_deg"])) < FOV_HALF,
                                                        "note": f"distances when the partner says each of the four sentences: " + "; ".join(f"{x['value']['text']!r}: {float(x['value']['partner_distance_m']):.2f} m" for x in four) + f"; nearest = {best['value']['text']!r} (runner-up {ds[1][0]:.2f} m)"},
                                        -marg, f"{four[0]['value']['event_ref']}_{four[-1]['value']['event_ref']}"))
    # --- sound_direction(单人 AEA):sound_source_direction 记录(发声 fixture 的 3D 方位)
    SD = sorted([r for r in SG._recs(store, vid, ti["t0"] - 1, ti["t1"] + 1, kinds={"sound_source_direction"}) if (r["value"] or {}).get("bearing_deg") is not None], key=lambda r: r["time"]["start_sec"])
    used_t = []
    for r in SD:
        v = r["value"]; ang = float(v["bearing_deg"]); T = float(r["time"]["end_sec"])
        if any(abs(T - u) < 2.0 for u in used_t): continue
        a = abs(ang); sec = SECTORS[0] if a <= 45 else (SECTORS[3] if a >= 135 else (SECTORS[1] if ang > 0 else SECTORS[2]))
        marg = float(v.get("margin_deg") if v.get("margin_deg") is not None else min(abs(45 - a), abs(135 - a)))
        if marg < 7.5: continue
        used_t.append(T)
        snd = store.get(v.get("sound_eid")) if v.get("sound_eid") else None
        w = [round(max(0.0, T - PRE), 3), round(min(D, T + 0.5), 3)]
        core = [r] + ([snd] if snd else []) + narr(w[0], w[1])
        lbl = v.get("sound_label") or ((snd or {}).get("value") or {}).get("label") or "the sound"
        pre["sound_direction"].append((r, w, core, {"utterance": {"id": r["evidence_id"], "event_ref": v.get("sound_eid"), "text": lbl, "topic": v.get("source_name"), "t": [r["time"]["start_sec"], T]},
                                                    "sound_label": lbl, "source_name": v.get("source_name"), "bearing_deg": round(ang, 1), "distance_m": v.get("range_m"), "options": list(SECTORS), "answer": sec, "margin_deg": round(marg, 1),
                                                    "partner_in_view_likely": a < FOV_HALF,
                                                    "note": f"the sound {lbl!r} ({v.get('source_name')}) comes from bearing {ang:+.0f} deg (+ = left), {v.get('range_m')} m away = {sec} (sector rule: front |b| <= 45, back >= 135)"},
                                       -marg, (v.get("sound_eid") or r["evidence_id"]).split(":")[-1]))
    # --- 每 skill 均衡答案类别、限量、分档
    for sk, items in pre.items():
        if not items: continue
        cnt = collections.Counter(); picked = []
        for it in sorted(items, key=lambda it: (cnt[it[3]["answer"]], it[0]["time"]["start_sec"])):
            if len(picked) >= PER_SKILL: break
            picked.append(it); cnt[it[3]["answer"]] += 1
        picked.sort(key=lambda it: it[1][0])
        bands = SG._bands({it[5]: it[4] for it in picked})
        for r, w, core, sa, knob, key in picked:
            c = _mk(store, ti, plan, sk, r, w, core, sa, knob, key)
            c["sg"]["tier"] = bands.get(key, 2)
            out[sk].append(c)
    return out


def spec_for(cap, level, c=None):
    sg_ = (c or {}).get("sg") or {}; sa = sg_.get("sa") or {}
    what = {"speaker_direction": "ask in which horizontal direction the partner is relative to you at the moment they say it: front-left / front-right / back-left / back-right",
            "turn_to_face_speaker": "ask how you would have to turn, at that moment, to face the partner: left about a quarter turn / right about a quarter turn / turn around / almost no turn",
            "speaker_approach": "ask whether, between the partner saying sentence A (sg.sa.utterance_a) and later sentence B (sg.sa.utterance_b), the partner got closer to you, farther from you, or stayed about the same distance",
            "nearest_utterance": "ask which of the four partner sentences listed as the options was said from the shortest straight-line distance to you; do NOT repeat or quote any of the four sentences in the question (they are the options), and no moment needs to be fixed",
            "sound_direction": "ask from which horizontal direction, relative to you, the described sound (sg.sa.sound_label) comes at the moment it is heard: straight ahead / your left / your right / behind you"}[cap]
    return {"level": level, "format": "single_choice", "window_max_sec": None, "window_min_sec": None,
            "note": f"L3 {cap} tier {sg_.get('tier', level)} (spatial audio): media_refs = EXACTLY the offered window; the clip ends right after the partner says sg.sa.utterance.text; "
                    f"identify the moment ONLY by quoting or closely paraphrasing what the partner says (never a time, never 'at the start/end of the clip'); "
                    f"{what}; STATE THE FRAME: relative to you (the camera wearer), facing the way your camera faces at that moment, horizontal direction / straight-line distance to the partner; "
                    "the partner may be out of view, so the Solver must use the sound of the voice and its memory of where the partner was; "
                    "the program fills the four options (sg.sa.options) and the reference (sg.sa.answer): write placeholder options; do NOT say or hint where the partner is",
            "rule": "controller-fixed: single_choice; window = the offered window; no time position; the moment is named by the partner's words; egocentric frame stated"}


def autofill(out, ctx, c):
    sg_ = c.get("sg") or {}; sa = sg_["sa"]; pub = out.setdefault("public", {}); pri = out.setdefault("private", {}); refs = pub.get("media_refs") or []
    want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]; filled = []
    if refs: refs[0]["windows"] = [list(w) for w in want]; del refs[1:]; filled.append("windows")
    pub["format"] = "single_choice"
    pub["options"] = [f"{L}. {o}" for L, o in zip("ABCD", sa["options"][:4])]
    pri["proposed_reference_answer"] = "ABCD"[sa["options"].index(sa["answer"])]
    pri["sg_rel_id"] = sg_["rel_id"]; pri["sa_note"] = sa["note"]; pri["frame_of_reference"] = sa["frame"]
    pub["observation_cutoff"] = want[-1][1]
    return filled + ["options", "reference", "sg_rel_id"]


_EGO = re.compile(r"\b(you|your|yourself|wearer|wearer's|camera)\b")
_PARTNER = re.compile(r"\b(partner|other person|guest|host|friend|companion|the person you are talking to|the person with you|he|she|they)\b", re.I)
_MOMENT = re.compile(r"\b(when|while|after|before|as|once|at the moment|by the time|just as|right after|the instant|says|said|asks|asked|mentions|replies|remarks)\b", re.I)


def _quoted(q, sa):
    toks = SG._toks(q)
    for u in [sa.get("utterance_a"), sa.get("utterance_b")] + (sa.get("utterances") or [sa.get("utterance")]):
        if not u: continue
        if len(SG._toks(u["text"]) & toks) >= 2 or (u.get("topic") and len(SG._toks(u["topic"]) & toks) >= 2): continue
        if len(SG._toks(u["text"])) == 1 and SG._toks(u["text"]) & toks: continue
        return u
    return None


def checks(out, ctx, c, q, wins):
    sg_ = c.get("sg") or {}; sa = sg_["sa"]; e = []; cap = sa["skill"]
    if cap == "sound_direction":
        if not (SG._toks(sa["sound_label"]) & SG._toks(q)) and not (sa.get("source_name") and SG._toks(sa["source_name"]) & SG._toks(q)): e.append(f"{cap}: the question must describe the sound ({sa['sound_label']!r}) so the moment is fixed by what is heard")
        if not re.search(r"\b(direction|where|from which)\b", q): e.append(f"{cap}: ask from which direction the sound comes")
        if re.search(r"\b(straight ahead|ahead of you|to your (left|right)|behind you|from (the|your) (left|right|front|back))\b", q): e.append(f"{cap}: do not name any direction in the question (they are the options)")
        if not _EGO.search(q): e.append(f"{cap}: state the egocentric frame: relative to you / the camera wearer, facing the way you face at that moment")
        if SG._TIME_CUE.search(q): e.append(f"{cap}: no time position in the question")
        want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]
        if len(wins) != len(want) or any(abs(wins[i][j] - want[i][j]) > 0.05 for i in range(len(want)) for j in (0, 1)):
            e.append(f"{cap}: media_refs must be exactly the offered window {want} (got {wins})")
        return e
    miss = _quoted(q, sa) if cap != "nearest_utterance" else None   # 11-04:nearest_utterance 四句话都在选项里,题面不引用
    if miss: e.append(f"{cap}: the question must quote or closely paraphrase what the partner says ({miss['text']!r}) so the moment is fixed by the words, not by time")
    if not _PARTNER.search(q): e.append(f"{cap}: refer to the other person as 'the partner' / 'the other person'")
    if cap != "nearest_utterance" and not _MOMENT.search(q): e.append(f"{cap}: anchor the moment on the partner's words ('when the partner says ...')")
    if not _EGO.search(q): e.append(f"{cap}: state the egocentric frame: relative to you / the camera wearer, facing the way you face at that moment")
    if SG._TIME_CUE.search(q): e.append(f"{cap}: no time position in the question")
    if cap == "speaker_direction" and re.search(r"\b(front|back)-(left|right)\b", q): e.append(f"{cap}: do not name any quadrant in the question (they are the options)")
    if cap == "turn_to_face_speaker" and re.search(r"\b(turn (left|right|around)|no turn|straight ahead)\b", q): e.append(f"{cap}: do not name any turn option in the question")
    if cap == "speaker_approach" and re.search(r"\b(closer|farther|further|nearer|same distance)\b", q) and not re.search(r"\b(closer|farther|further|nearer)\b.*\b(or|,)\b.*\b(closer|farther|further|nearer|same)\b", q):
        e.append(f"{cap}: do not state the answer (closer / farther / same) in the question; name the two sentences and ask what happened to the distance")
    if cap == "nearest_utterance" and not re.search(r"\b(closest|nearest|shortest|least)\b", q): e.append(f"{cap}: ask which sentence was said from the shortest distance to you")
    if cap == "nearest_utterance" and not re.search(r"\b(3d|three-dimensional|real-world|actual|physical|straight-line|in space)\b", q): e.append(f"{cap}: say that distance means real-world (straight-line) distance, not distance on the screen")
    if re.search(r"\b(to (your|the) (left|right)|behind you|in front of you|ahead of you)\b", q): e.append(f"{cap}: the question must not say where the partner is (that is the answer)")
    want = [list(map(float, w)) for w in (c.get("windows") or [c["window"]])]
    if len(wins) != len(want) or any(abs(wins[i][j] - want[i][j]) > 0.05 for i in range(len(want)) for j in (0, 1)):
        e.append(f"{cap}: media_refs must be exactly the offered window {want} (got {wins})")
    return e


HARNESS = """    - speaker_direction / turn_to_face_speaker / speaker_approach / nearest_utterance (sg.l3_kind = spk; sg.sa; 11-03 v29, AEA two-person
      recordings, SPATIAL AUDIO): the Solver hears the stereo audio of the wearer's glasses. The clip ends right after the partner says
      sg.sa.utterance.text. The question fixes the moment ONLY by quoting / closely paraphrasing the partner's words (never a time), calls
      the other person "the partner", and states the frame: relative to you (the camera wearer), facing the way your camera faces at that
      moment. speaker_direction: in which direction is the partner (front-left / front-right / back-left / back-right); turn_to_face_speaker:
      how you would turn to face them; speaker_approach: between sentence A (sg.sa.utterance_a) and sentence B (sg.sa.utterance_b), did the
      partner get closer / farther / stay about the same; nearest_utterance: which of the four partner sentences given as the options was said
      from the shortest real-world distance to you (do NOT quote any of them in the question; no moment to fix). Never say or hint where the partner is. media_refs = EXACTLY the offered window; the
      program fills the options (sg.sa.options) and the reference (sg.sa.answer): write placeholder options; private.sg_rel_id = sg.rel_id.
    - sound_direction (sg.l3_kind = spk; sg.sa; single-person AEA, SPATIAL AUDIO): the clip ends right after the described sound
      (sg.sa.sound_label, made by sg.sa.source_name). Fix the moment by describing the sound (never a time), state the egocentric frame,
      and ask from which direction it comes (options: straight ahead / your left / your right / behind you, program-filled). Never name a direction.
"""
