"""程序化校验闸门:每道候选题在固定窗口上重推 gold,措辞不合格即拒,只丢弃不修补。"""
import re
import pconfig as P
import config as C
import primitives as PRIM
import memory as MEM
import facts as F
import spatial as SP
import infer as IN

META_WORDS = ("annotation", "timeline", "metadata", "ground truth")
# 跨场景题:输入是两段 30 s 拼接,题面必须交代这一点,否则被测者不知道片中有跳切
SCENE_WORDS = ("scene", "two moments", "two clips", "two parts", "earlier", "later on")

# spatial 题的「最近/最远」只在某一个时刻成立 —— 参照物自己就是被搬动的那个,
# 30 秒里位置会变。题面必须留下时刻锚点,否则答案不唯一。
# (实测 gemini-3.5-flash 会把模板简化成 "Which object is closest to the spoon?",
#  正是这道门要拦的。)
TIME_ANCHOR = ("moment", "when ", "by the end", "end of the clip", "end of this clip",
               "ends up", "end up", "put down", "puts down", "putting down",
               "sets down", "places", "placed", "at that point", "at the time",
               "after ", "finally", "final position", "come to rest", "comes to rest")


def _window_objects(ix, t0, t1):
    vis = {PRIM._norm(x) for x in ix.visible_in(t0, t1)}
    for m in ix.in_window(t0, t1, "movement"):
        nm = (m.extra.get("object_name") or m.text or "").strip()
        if nm:
            vis.add(PRIM._norm(nm))
    return vis


def _check_object(ix, item, errs):
    """OBJECT 类:gold 在窗口内,干扰项在 [t0-2,t1+2] 都不在,且与 gold 不同头名词。"""
    t0, t1 = item["t0"], item["t1"]
    if PRIM._norm(item["answer"]) not in _window_objects(ix, t0, t1):
        errs.append("gold 物体不在窗口内")
    around = _window_objects(ix, t0 - 2, t1 + 2)
    gh = PRIM._head_noun(item["answer"])
    for d in item["_distractors"]:
        if PRIM._norm(d) in around:
            errs.append(f"干扰项 '{d}' 在窗口内也为真")
        if PRIM._head_noun(d) == gh:
            errs.append(f"干扰项 '{d}' 与 gold 同头名词")


def check(ix, item, fact):
    """返回错误列表;空列表 = 通过。item 是组装后的题目条目,fact 是其来源事实。"""
    errs = []
    t0, t1 = item["t0"], item["t1"]
    # 证据事件必须落在窗口内(所有格式共用)
    for e in item["evidence_event_ids"]:
        try:
            ev = ix.ev(e)
        except KeyError:
            errs.append(f"证据 {e} 不存在")
            continue
        wins = [tuple(w) for w in item["windows"]] if item.get("windows") else [(t0, t1)]
        if not any(ev.t_start < b and ev.t_end > a for a, b in wins):
            errs.append(f"证据 {e} 落在窗口外")
    # plan 格式(goal -> trajectory):没有选项;只查 goal 不泄漏参考步骤、步骤数、段内证据
    if item.get("kind") == "PLAN":
        import formats as FM
        steps = fact.get("_steps") or []
        if not (4 <= len(steps) <= 8):
            errs.append("plan 参考步骤数不在 4-8")
        g = FM.toks(fact.get("_goal") or "")
        leak = sum(1 for st_ in steps if FM.toks(st_) and FM.toks(st_) <= g)
        if leak >= 2:
            errs.append("plan goal 句泄漏 >= 2 个参考步骤")
        if any(w in (item["question"] or "").lower() for w in META_WORDS):
            errs.append("plan goal 含 meta 词")
        if item["question"].strip() != (fact.get("_goal") or "").strip():
            errs.append("plan 题面必须是 goal 句原文")
        return errs
    # answer-format 题(yn / ms / tf4 / open):gold 与干扰项沿用 mc 题,只查格式自身(formats.check)
    if item.get("fmt") not in (None, "mc"):
        import formats as FM
        FM.check(ix, item, fact, errs)
        return errs
    q, gold = item["question"], item["answer"]

    # ---- 结构 ----
    if gold != fact["gold"]:
        errs.append("answer 与程序 gold 不一致")
    if sorted(item["_distractors"]) != sorted(fact["distractors"]):
        errs.append("干扰项与程序挖出的不一致")
    if len(set(item["options"])) != 4:
        errs.append("选项不足 4 个互异")
    bodies = [o[3:] for o in item["options"]]      # 必须比正文:带 "A. " 前缀永远互异
    if len(set(bodies)) != 4 or len({F._dnorm(b) for b in bodies}) != 4:
        errs.append(f"选项正文重复:{bodies}")
    if item["options"][item["_gold_idx"]][3:] != gold:
        errs.append("correct_option 与 answer 不一致")

    # ---- 措辞 ----
    ql = q.lower()
    if item["kind"] == "COUNT":
        if re.search(rf"\b{re.escape(gold)}\b", q):
            errs.append("题面泄漏计数 gold")
    elif item["kind"] != "ORDER" and MEM.contains_gold(q, gold):
        errs.append("题面泄漏 gold")
    lab = fact.get("_sound_label") or ""
    if "/" in lab and lab.lower() in ql:
        errs.append("题面出现原始声音标签")
    if "collision" in ql:
        errs.append("题面出现 'collision'(原始标签词)")
    for w in META_WORDS:
        if w in ql:
            errs.append(f"题面出现元词 '{w}'")
    if "spatial" in fact["subtype"] and not any(a in ql for a in TIME_ANCHOR):
        errs.append("spatial 题面缺时刻锚点(物体在窗口内会移动,'最近'需定时刻)")
    if item.get("windows") and not any(w in ql for w in SCENE_WORDS):
        errs.append("跨场景题面未交代两段场景")

    # ---- 按 subtype 在窗口上重推 ----
    st = fact["subtype"]
    if st == "easy_sound_object":
        r = PRIM.find_easy(ix, ix.ev(fact["evidence_event_ids"][0]))
        if not r or r["gold"] != gold:
            errs.append("find_easy 重推不符")
        _check_object(ix, item, errs)
    elif st == "easy_sound":
        if not ix.sounds_between(t0, t1, lab):
            errs.append("gold 声音不在窗口内")
        for d in item["_distractors"]:
            dl = P.PHRASE2LABEL.get(d)
            if dl is None:
                errs.append(f"干扰声音 '{d}' 无法反查标签")
            elif ix.sounds_between(t0 - 2, t1 + 2, dl):
                errs.append(f"干扰声音 '{d}' 在窗口内也响过")
            elif not F.sound_distractor_ok(ix, dl, t0, t1):
                errs.append(f"干扰声音 '{d}' 在 ±{F.SOUND_FAR_W:.0f}s 内响过或被窗口内动作暗示")
        if lab in F.EASY_SOUND_NEVER:
            errs.append(f"gold 声音 '{lab}' 不出题")
    elif st == "easy_move":
        mv = ix.ev(fact["evidence_event_ids"][0])
        if PRIM._norm(F._mv_name(mv)) != PRIM._norm(gold):
            errs.append("easy_move gold 与证据不符")
        fr, to = fact["_from"], fact["_to"]
        same = [x for x in ix.transitions
                if x.t_start < t1 and x.t_end > t0
                and ix.fixture_pretty(x.extra.get("from_fixture")) == fr
                and ix.fixture_pretty(x.extra.get("to_fixture")) == to]
        if len(same) != 1:
            errs.append("easy_move 窗口内同路径搬动不唯一")
        _check_object(ix, item, errs)
    elif st == "low_sound_movement":
        r = PRIM.find_low(ix, ix.ev(fact["evidence_event_ids"][0]))
        if not r or r["gold"] != gold:
            errs.append("find_low 重推不符")
        _check_object(ix, item, errs)
    elif st == "medium_count":
        n = F.count_clean(ix, lab, t0, t1)
        if n is None or str(n) != gold:
            errs.append(f"count 重算不符 {n}!={gold}")
        for d in item["_distractors"]:
            if not d.isdigit() or d == str(n):
                errs.append(f"计数干扰项 '{d}' 非法")
    elif st in ("high_order", "medium_order"):
        evs = [ix.ev(e) for e in fact["evidence_event_ids"]]
        if [e.eid for e in sorted(evs, key=lambda x: x.t_start)] != [e.eid for e in evs]:
            errs.append("ORDER 证据未按时序")
        if " -> ".join(PRIM._action(e) for e in evs) != gold:
            errs.append("ORDER gold 与证据重组不符")
        for a, b in zip(evs, evs[1:]):
            if b.t_start - a.t_start < PRIM.MIN_GAP_HIGH:
                errs.append("ORDER 事件间隔 <2s")
        for p in gold.split(" -> "):
            if not F.ACTION_RE.fullmatch(p) or "  " in p:
                errs.append(f"动作措辞残缺 '{p}'")
        parts = sorted(gold.split(" -> "))
        for d in item["_distractors"]:
            if sorted(d.split(" -> ")) != parts or d == gold:
                errs.append(f"排序干扰项 '{d}' 非法")
    elif st == "easy_spatial_near":
        r = SP.derive_l1(ix, ix.ev(fact["_ref_eid"]), t0, t1)
        if not r or r["gold"] != gold:
            errs.append("spatial L1 重推不符")
        else:
            SP.check_nearest(ix, item, fact, errs, r)
    elif st == "low_spatial_near":
        r = SP.derive_l2(ix, ix.ev(fact["_ref_eid"]), t0, t1)
        if not r or r["gold"] != gold:
            errs.append("spatial L2 重推不符")
        else:
            SP.check_nearest(ix, item, fact, errs, r)
    elif st in ("easy_spatial_side", "low_spatial_side"):
        mode = fact.get("_mode", "right")
        r = SP.derive_ego_side(ix, ix.ev(fact["_ref_eid"]), t0, t1, mode)
        if not r or r["gold"] != gold:
            errs.append(f"spatial ego({mode}) 重推不符")
        else:
            SP.check_ego(ix, item, fact, errs, r)
            # 锚点物体不得出现在选项里:题面要提它,提了就等于给答案划范围
            anc = fact.get("_anchor")
            if anc and any(PRIM._head_noun(o[3:]) == PRIM._head_noun(anc)
                           for o in item["options"]):
                errs.append("ego 锚点物体出现在选项中")
        # 方位一致性:几何重推只认 fact 里的 mode,题面把 right 写成 left 它看不出来 ——
        # 而那样题面与答案就自相矛盾了。左右必须恰好出现该出现的那个。
        other = "left" if mode == "right" else "right"
        # 用词边界:裸子串会把 "brightness" 里的 "right" 当成方位词误判
        if not re.search(rf"\b{mode}\b", ql):
            errs.append(f"ego 题面未点明方位 '{mode}'")
        if re.search(rf"\b{other}\b", ql):
            errs.append(f"ego 题面出现相反方位 '{other}'")
    elif st == "medium_spatial_extreme":
        mode = fact.get("_mode", "far")
        r = SP.derive_l3(ix, fact["_ref"], t0, t1, mode)
        if not r or r["gold"] != gold:
            errs.append("spatial L3 重推不符")
        else:
            SP.check_nearest(ix, item, fact, errs, r, far_mode=(mode == "far"))
    elif st in ("high_spatial_order", "medium_spatial_order"):
        r = SP.derive_l4(ix, fact["_ref"], t0, t1)
        if not r or r["gold"] != gold:
            errs.append("spatial L4 重推不符")
        else:
            ds = [x[0] for x in r["triple"]]
            if not all(b - a >= SP.GAP_L4 for a, b in zip(ds, ds[1:])):
                errs.append("spatial L4 三元组间隔不足")
        gp = gold.split(" -> ")
        parts = sorted(gp)
        if len(parts) != 3:
            errs.append("spatial L4 gold 不是三元组")
        for d in item["_distractors"]:
            if sorted(d.split(" -> ")) != parts or d == gold:
                errs.append(f"排序干扰项 '{d}' 非法")
        # ORDER 类豁免了 contains_gold(题面本就要列出三项),于是唯一的泄漏口是
        # **列出的顺序**:若三项在题面里恰好按 gold 顺序出现,答案就白送了。
        # 模板走 _shuffled_parts 不会触发;这道门防的是在线措辞把顺序改回来。
        pos = [ql.find(p.lower()) for p in gp]
        if all(x >= 0 for x in pos) and pos == sorted(pos):
            errs.append("spatial L4 题面按 gold 顺序列出三项(泄漏答案)")
        # 上面按首次出现位置判序,对「列一次」的正常题面是对的;这一条另外挡住
        # 把整条 gold 串直接写进题面的情形(模板用分号分隔,不会触发)。
        if gold.lower() in ql or gold.lower().replace(" -> ", " then ") in ql:
            errs.append("spatial L4 题面出现完整 gold 串")
    elif st in ("medium_purpose", "low_purpose"):
        IN.check_purpose(ix, item, fact, errs)
    elif st in ("medium_goal", "easy_goal"):
        IN.check_goal(ix, item, fact, errs, "recognition" if st == "easy_goal" else "inference")
    elif st in ("high_gaze_destination", "high_gaze_pickup"):
        import gaze as GZ
        GZ.check(ix, item, fact, errs)
    elif st == "high_plan_next":
        segs = IN.recipe_segs(ix.video_id, ix.duration)
        k = fact.get("_seg")
        w = IN.next_window(segs[k]) if k is not None and k + 1 < len(segs) else None
        if not w or abs(w[0] - t0) > 0.02 or abs(w[1] - t1) > 0.02 or segs[k + 1][2] != gold:
            errs.append("下一步重推不符")
        else:
            later = {x[2] for x in segs[k + 1:]}
            for d in item["_distractors"]:
                if d in later:
                    errs.append(f"下一步干扰项 '{d}' 是本视频之后的步骤")
    elif st == "high_plan_next_action":
        IN.check_next_action(ix, item, fact, errs)
    elif st == "high_replan":
        IN.check_replan(ix, item, fact, errs)
    elif st == "high_plan_next_step":
        IN.check_next_step(ix, item, fact, errs)
    elif st == "high_plan_retrieve":
        a = ix.ev(fact["_ref_eid"])
        nm, w = IN.clean_obj(IN.mv_name(a)), item.get("windows") or []
        if nm != fact.get("_object") or len(w) != 2:
            errs.append("取物题结构不符")
        else:
            if ix.fixture_pretty(a.extra.get("to_fixture")) != gold:
                errs.append("取物 gold 重推不符")
            if not IN.same_fixture(ix, nm, gold, a.t_end, w[1][1]):
                errs.append("场景 2 结束前物体被挪到了别的设施")
            if w[1][0] < w[0][1] + IN.MIN_SCENE_GAP:
                errs.append("两场景间隔不足")
            vocab = set(C.FIXTURE_NAME.values())
            for d in item["_distractors"]:
                if d == gold or d not in vocab:
                    errs.append(f"取物干扰项 '{d}' 非法")
    elif st == "high_plan_route":
        a = ix.ev(fact["_ref_eid"])
        nm = IN.clean_obj(IN.mv_name(a))
        r = IN.route_derive(ix.video_id, fact["_T"], a.extra["end_xyz"]) \
            if a.extra.get("end_xyz") else None
        if not r or r[0] != gold:
            errs.append("路线方向重推不符")
        elif r[1] < IN.MIN_ANGLE_MARGIN:
            errs.append("方向离扇区边界太近")
        if nm != fact.get("_object") or not IN.stationary(ix, nm, a.t_end, fact["_T"]):
            errs.append("场景 2 结束前物体被动过")
        if sorted(list(item["_distractors"]) + [gold]) != sorted(IN.SECTORS):
            errs.append("路线选项须恰为四个方向")
    else:
        errs.append(f"未知 subtype {st}")

    # ---- memory 渲染完整性:证据行必须在渲染文本里且未被截断 ----
    # 跨场景题的 t0/t1 是几分钟的总跨度,渲染必然超 250 行;它只走 clip30,不查这一项
    if not item.get("windows") and item.get("kind") not in ("ACTION", "REPLAN", "STEP"):
        _, meta = MEM.render(ix, t0, t1)
        if meta["truncated"]:
            errs.append("memory 渲染被截断")
    return errs
