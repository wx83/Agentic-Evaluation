"""L3 推断与 L4 规划:事实挖掘与重推的唯一真相源(facts.py 与 verify.py 共用)。

L3 推断(需要整合整个窗口,而不只是数数):
- 目的推断:narration 自带目的从句("pick up the tea towel **to dry the hands**")。
  干扰项优先取**难负例** —— 同一视频别处、同一动词或同一物体的目的 —— 否则
  「tap the egg -> to crack it」这类题不看视频也能从题面猜中。
- 总体目标:recipe_timestamps 的高层活动段,窗口须整个落在一段之内。
L4 规划(可跨场景,输入为两段 30 s 拼接):
- 取物:物体在场景 1 被放下,几分钟后场景 2 结束时要用它 —— 该去哪拿?
- 路线:同上,但问物体在观察者的哪个象限(SLAM 位姿 + 物体 3D;front/back × left/right,距边界 >= 15 度)。
- 下一步:recipe 段 k 末尾的 30 s,问接下来做什么(段 k+1)。
"""
import json, math, re, collections
import pconfig as P
import config as C
import primitives as PRIM

_DETS = ("a ", "an ", "the ", "some ", "his ", "her ", "their ", "my ", "one ", "two ", "another ")


def with_the(n):
    n = (n or "").strip()
    return n if n.lower().startswith(_DETS) else f"the {n}"


def win_around(duration, t):
    t0 = min(max(0.0, t - P.WIN_SEC / 2), max(0.0, duration - P.WIN_SEC))
    return t0, t0 + P.WIN_SEC


def clean_obj(nm):
    nm = (nm or "").strip()
    if not nm or PRIM.is_fixture(nm) or PRIM.is_artifact(nm) or "unknown" in nm.lower():
        return None
    return PRIM._norm(nm) or None


def mv_name(m):
    return (m.extra.get("object_name") or m.text or "").strip()


# ================= 目的推断 =================

PURPOSE_RE = re.compile(r"\b(?:in order )?(to [a-z][a-z' ]{2,60}?)(?:[.,;]|$| so | and then | while "
                        r"| before | after | using | with (?:my|the|both) )", re.I)
MAX_PURPOSE_WORDS = 8


def main_pair(e):
    m = e.extra.get("main_actions") or []
    return (m[0][0].lower(), m[0][1].lower()) if m and len(m[0]) == 2 else None


# ================= L4 next action(EgoPlan 式):片段切在动作前,gold = 下一条 narration 的 verb+noun =================

TRIVIAL_NOUNS = {"hand", "hands", "left hand", "right hand", "both hands", "phone", "camera", "finger", "fingers"}
TRIVIAL_VERBS = {"continue", "keep", "hold", "check", "look", "wait", "think", "watch", "walk", "move", "turn", "reach"}
CUT_BEFORE_ACT = 0.5       # 片段在 gold 动作开始前这么多秒结束(EgoPlan-Bench2 的取法)
POST_SEC = 10.0            # 干扰项动作在片段结束后这么多秒内也不得出现


def main_classes(e):
    m = e.extra.get("main_action_classes") or []
    return (m[0][0], m[0][1]) if m and len(m[0]) == 2 else None


def action_phrase(pair):
    return f"{pair[0]} {with_the(pair[1])}"


def pairs_in(ix, t0, t1):
    return {main_pair(x) for x in ix.in_window(t0, t1, "narration") if main_pair(x)}


def seg_at(segs, t):
    for i, sg in enumerate(segs):
        if sg[0] <= t < sg[1]:
            return i
    return None


def next_action_derive(ix, e):
    """以 narration e 为 gold 动作:片段 [t1-30, t1],t1 = e 开始前 0.5 s。
    返回 dict(gold, t0, t1, pair, classes, goal, seg) 或 None。
    anticipation 门:gold 的 verb+noun 不在片段内出现;gold 的 noun 类别不等于片段最后两条 narration 的
    noun 类别(排除「放下 X 又拿起 X」);gold 之后 0.3 s 内没有另一条不同动作同时开始。"""
    pair, cls = main_pair(e), main_classes(e)
    if not pair or not cls or pair[1] in TRIVIAL_NOUNS or pair[0] in TRIVIAL_VERBS:
        return None
    t1 = round(e.t_start - CUT_BEFORE_ACT, 2)
    t0 = round(t1 - P.WIN_SEC, 2)
    if t0 < 0:
        return None
    win = sorted(ix.in_window(t0, t1, "narration"), key=lambda x: x.t_start)
    if not win or pair in {main_pair(x) for x in win}:
        return None
    if any((main_classes(x) or (None, None))[1] == cls[1] for x in win[-2:]):
        return None
    co = [x for x in ix.in_window(e.t_start - 0.01, e.t_start + 0.3, "narration")
          if x.eid != e.eid and x.t_start >= e.t_start - 0.01 and main_pair(x) and main_pair(x) != pair]
    if co:
        return None
    segs = recipe_segs(ix.video_id, ix.duration)
    k = seg_at(segs, t1)
    if k is None or not segs[k][3]:            # 没有 recipe_id 的段(Put away items 等)不出题
        return None
    return {"gold": action_phrase(pair), "t0": t0, "t1": t1, "pair": pair, "classes": cls,
            "goal": segs[k][2], "seg": k}


def next_action_distractor_ok(ix, pair, t0, t1):
    return pair not in pairs_in(ix, t0 - 2.0, t1 + POST_SEC)


def next_action_distractors(ix, d, rng):
    """同视频的其它动作:verb 类与 noun 类都不同于 gold(EgoPlan 的「不同语义类别」),片段前后不出现,
    head noun 两两不同;优先同一活动段内的动作。不足 3 个时放宽为「任一类别不同」并返回 relax=True。"""
    segs = recipe_segs(ix.video_id, ix.duration)
    s0, s1 = (segs[d["seg"]][0], segs[d["seg"]][1]) if d.get("seg") is not None else (-1.0, -1.0)
    gpair, gcls = d["pair"], d["classes"]
    seen, cand = set(), []
    for x in ix.narrations:
        pr, cl = main_pair(x), main_classes(x)
        if not pr or not cl or pr in seen or pr == gpair or pr[1] in TRIVIAL_NOUNS or pr[0] in TRIVIAL_VERBS:
            continue
        seen.add(pr)
        if PRIM._head_noun(pr[1]) == PRIM._head_noun(gpair[1]):
            continue
        if not next_action_distractor_ok(ix, pr, d["t0"], d["t1"]):
            continue
        cand.append((pr, cl, s0 <= x.t_start < s1))
    def pick(strict):
        pool = [c for c in cand if ((c[1][0] != gcls[0] and c[1][1] != gcls[1]) if strict
                                    else (c[1][0] != gcls[0] or c[1][1] != gcls[1]))]
        inseg = [c for c in pool if c[2]]; rest = [c for c in pool if not c[2]]
        rng.shuffle(inseg); rng.shuffle(rest)
        out, heads = [], set()
        for pr, cl, _ in inseg + rest:
            h = PRIM._head_noun(pr[1])
            if h in heads:
                continue
            heads.add(h); out.append(pr)
            if len(out) == 3:
                break
        return out if len(out) == 3 else None
    ds = pick(True)
    if ds:
        return ds, False
    ds = pick(False)
    return (ds, True) if ds else (None, False)


def check_next_action(ix, item, fact, errs):
    e = ix.ev(fact["_ref_eid"])
    d = next_action_derive(ix, e) if e is not None else None
    if not d or abs(d["t0"] - item["t0"]) > 0.02 or abs(d["t1"] - item["t1"]) > 0.02 or d["gold"] != item["answer"]:
        errs.append("next action 重推不符")
        return
    if fact.get("_goal") and d["goal"] != fact["_goal"]:
        errs.append("next action goal 标签不符")
    dp = [tuple(x) for x in fact.get("_dpairs") or []]
    if len(dp) != 3 or [action_phrase(x) for x in dp] != list(fact["distractors"]):
        errs.append("next action 干扰项与 _dpairs 不符")
    heads = {PRIM._head_noun(d["pair"][1])}
    for pr in dp:
        if not next_action_distractor_ok(ix, pr, d["t0"], d["t1"]):
            errs.append(f"next action 干扰项 '{action_phrase(pr)}' 在片段前后出现")
        h = PRIM._head_noun(pr[1])
        if h in heads:
            errs.append(f"next action 干扰项 head noun 重复 '{h}'")
        heads.add(h)
    ql = item["question"].lower()
    import formats as FM
    base = FM.toks("The camera wearer is working on. Right after this clip ends, what is the camera wearer "
                   "going to do next? Which of these statements are true for this clip? Answer with a short "
                   "verb phrase, e.g. open the drawer.")
    gt = FM.toks(d["gold"]) - base
    if gt & (FM.toks(ql) - FM.toks(fact.get("_goal") or "")):
        errs.append("next action 题面含 gold 的动词或物体")
    if fact.get("_goal") and fact["_goal"].lower() not in ql:
        errs.append("next action 题面未原文给出 goal")


# ================= L4 replan:视频里自然发生的偏差 =================

DEV_RE = re.compile(r"realis|realiz|forgot|forget|instead|change (?:my |their )?mind|accident|dropped|drops?\b|fell|fall|spill|"
                    r"stuck|not working|isn't working|\bagain\b|still (?:wet|dirty|on|open|closed)|too (?:hot|much|full|many)|"
                    r"go back|went back|goes back|missing|\bempty\b|mistake|wrong|oops|forgotten|not yet", re.I)
DROP_RE = re.compile(r"drop|fall|fell|spill", re.I)
CLEAN_VERBS = {"wipe", "clean", "mop", "pick up", "pick"}


def replan_candidates(ix):
    """返回 [(e_dev, e_rec, e_plan, keyword)]:偏差 narration、其后第一条非琐碎动作(纠正)、偏差前一条动作(原计划)。
    片段将取 [e_rec.t_start-0.5-30, e_rec.t_start-0.5],要求偏差时刻落在片段内。"""
    narr = sorted(ix.narrations, key=lambda x: x.t_start)
    out = []
    for i, e in enumerate(narr):
        kw = None
        m = DEV_RE.search(e.text or "")
        if m:
            kw = m.group(0).lower()
        else:
            pr = main_pair(e)
            if pr and pr[0] in CLEAN_VERBS:
                prev = [x for x in narr[max(0, i - 40):i] if e.t_start - x.t_start <= 20 and DROP_RE.search(x.text or "")
                        and main_pair(x) and PRIM._head_noun(main_pair(x)[1]) == PRIM._head_noun(pr[1])]
                if prev:
                    kw = "after-drop " + pr[0]
        if not kw:
            continue
        rec = None
        for x in narr[i + 1:]:
            pr = main_pair(x)
            if x.t_start < e.t_start + 0.5:
                continue
            if pr and pr[1] not in TRIVIAL_NOUNS and pr[0] not in TRIVIAL_VERBS:
                rec = x
                break
        if rec is None:
            continue
        t1 = round(rec.t_start - CUT_BEFORE_ACT, 2); t0 = round(t1 - P.WIN_SEC, 2)
        if t0 < 0 or e.t_start < t0:
            continue
        plan = next((x for x in reversed(narr[:i]) if main_pair(x) and main_pair(x)[1] not in TRIVIAL_NOUNS), None)
        out.append((e, rec, plan, kw))
    return out


def replan_distractors(ix, rec, plan_pair, t0, t1, rng, seg):
    """陷阱 1 = 原计划动作(偏差前一条),须不在片段结束后 10 s 内出现;另两个按 next_action 的规则取。"""
    gpair, gcls = main_pair(rec), main_classes(rec)
    out = []
    if plan_pair and plan_pair != gpair and PRIM._head_noun(plan_pair[1]) != PRIM._head_noun(gpair[1]) \
            and plan_pair not in pairs_in(ix, t1, t1 + POST_SEC):
        out.append(plan_pair)
    d = {"pair": gpair, "classes": gcls, "t0": t0, "t1": t1, "seg": seg}
    more, relax = next_action_distractors(ix, d, rng)
    heads = {PRIM._head_noun(x[1]) for x in out}
    for pr in more or []:
        h = PRIM._head_noun(pr[1])
        if pr in out or h in heads:
            continue
        out.append(pr); heads.add(h)
        if len(out) == 3:
            break
    return (out if len(out) == 3 else None), bool(plan_pair and out and out[0] == plan_pair)


def check_replan(ix, item, fact, errs):
    try:
        rec, dev = ix.ev(fact["_ref_eid"]), ix.ev(fact["_dev_eid"])
    except KeyError:
        errs.append("replan 事件不存在"); return
    t1 = round(rec.t_start - CUT_BEFORE_ACT, 2); t0 = round(t1 - P.WIN_SEC, 2)
    if abs(t0 - item["t0"]) > 0.02 or abs(t1 - item["t1"]) > 0.02:
        errs.append("replan 窗口重推不符")
    if dev.t_start < item["t0"] - 0.02:
        errs.append("replan 偏差时刻不在片段内")
    if item["answer"] != action_phrase(main_pair(rec)):
        errs.append("replan gold 与纠正动作不符")
    dp = [tuple(x) for x in fact.get("_dpairs") or []]
    if len(dp) != 3 or [action_phrase(x) for x in dp] != list(fact["distractors"]):
        errs.append("replan 干扰项与 _dpairs 不符")
    for pr in dp:
        if pr in pairs_in(ix, item["t0"] - 2.0, item["t1"] + POST_SEC) and pr != tuple(fact.get("_plan_pair") or ()):
            errs.append(f"replan 干扰项 '{action_phrase(pr)}' 在片段前后出现")
        if pr == tuple(fact.get("_plan_pair") or ()) and pr in pairs_in(ix, item["t1"], item["t1"] + POST_SEC):
            errs.append("replan 原计划干扰项在片段后出现")
    import formats as FM
    ql = item["question"].lower()
    base = FM.toks("The camera wearer is working on. Something does not go as planned in this clip. What should the "
                   "camera wearer do right after the clip ends? Which of these statements are true for this clip? "
                   "Answer with a short verb phrase, e.g. open the drawer.")
    if (FM.toks(item["answer"]) - base) & (FM.toks(ql) - FM.toks(fact.get("_goal") or "")):
        errs.append("replan 题面含 gold 的动词或物体")
    if item.get("fmt") in (None, "mc") and fact.get("_situation") and fact["_situation"].lower()[:40] in ql:
        errs.append("replan 单选题面不得给出 situation")


def check_next_step(ix, item, fact, errs):
    """next_step:片段在第 k+1 步开始前 0.5 s 结束;gold = 第 k+1 步;干扰项 = 已做 / 更靠后 / 其它任务;题面含 goal 不含 gold。"""
    steps = fact.get("_steps") or []; k = fact.get("_k")
    if k is None or not (0 < k < len(steps) - 1) or steps[k + 1] != item["answer"]:
        errs.append("next_step gold 不是第 k+1 步"); return
    import task_timeline as TT
    t = next((x for x in TT.load(ix.video_id) if x["task_id"] == fact.get("_task_id")), None)
    if t is None:
        errs.append("next_step 任务不存在"); return
    cut = round(t["steps"][k + 1]["t0"] - CUT_BEFORE_ACT, 2)
    if abs(cut - item["t1"]) > 0.02 or abs(cut - P.WIN_SEC - item["t0"]) > 0.02:
        errs.append("next_step 窗口重推不符")
    ds = list(fact["distractors"]); done = fact.get("_done") or []
    if not any(d in done for d in ds):
        errs.append("next_step 缺少「已做完」干扰项")
    if not any(d in steps[k + 2:] for d in ds):
        errs.append("next_step 缺少「更靠后」干扰项")
    import formats as FM
    ql = item["question"].lower()
    base = FM.toks("The camera wearer is working on. Right after this clip ends, what should the camera wearer do next? "
                   "Which of these statements are true for this clip? Answer with a short phrase.")
    if (FM.toks(item["answer"]) - base - FM.toks(fact.get("_goal") or "")) & (FM.toks(ql) - FM.toks(fact.get("_goal") or "")):
        errs.append("next_step 题面含 gold 的词")
    if fact.get("_goal") and fact["_goal"].lower() not in ql:
        errs.append("next_step 题面未原文给出 goal")


def purpose_of(e):
    """narration 的主动作与目的从句;不合格返回 None。

    丢弃:目的过长(> 8 词);目的复述主动作(同一动词,或含主名词的中心词)——
    那样题面本身就等于答案。
    """
    mp = main_pair(e)
    pairs = [tuple(x.lower() for x in p) for p in (e.extra.get("pairs") or []) if len(p) == 2]
    if not mp or len(pairs) < 2:
        return None
    m = PURPOSE_RE.search(e.text or "")
    if not m:
        return None
    cl = re.sub(r"\s+", " ", m.group(1).strip().lower()).rstrip(" .,;")
    # narration 是第一人称("to dry my hand"),题面问的是摄像者 —— 统一成第三人称
    cl = re.sub(r"\bmy\b", "their", re.sub(r"\bmyself\b", "themselves", cl))
    pv = [p for p in pairs if p != mp and cl.startswith("to " + p[0])]
    if not pv or len(cl.split()) > MAX_PURPOSE_WORDS:
        return None
    if pv[0][0] == mp[0] or PRIM._head_noun(mp[1]) in cl.split():
        return None
    # 空泛目的:三词以内且以代词收尾("to open it" / "to crack it" / "to dry them")——
    # 对「拉抽屉」答「为了打开它」几乎是同义反复,不看视频也能选中
    w = cl.split()
    if len(w) <= 3 and w[-1] in ("it", "them", "this", "that", "these", "those"):
        return None
    return {"action": f"{mp[0]} {with_the(mp[1])}", "purpose": cl, "main": mp, "pverb": pv[0][0]}


_PURP = {}


def purposes(ix):
    if ix.video_id not in _PURP:
        _PURP[ix.video_id] = [(e, p) for e in ix.narrations for p in [purpose_of(e)] if p]
    return _PURP[ix.video_id]


def sound_purpose(ix, s):
    """声音 s 的时刻恰好落在唯一一条带目的的 narration 上 -> (e, p);否则 None。
    题面只给声音、不点名动作:点名动作时盲答 76%(「拿起毛巾 -> 为了擦手」读题即可推出)。"""
    hit = [(e, p) for e, p in purposes(ix) if e.t_start - 0.5 <= s.mid() <= e.t_end + 0.5]
    return hit[0] if len(hit) == 1 else None


def purpose_unique(ix, e, t0, t1):
    """窗口内同一主动作只出现这一次,「这个动作」才有唯一所指。"""
    mp = main_pair(e)
    return sum(main_pair(x) == mp for x in ix.in_window(t0, t1, "narration")) == 1


def purposes_near(ix, t0, t1):
    return {p["purpose"] for e, p in purposes(ix) if e.t_start < t1 + 2 and e.t_end > t0 - 2}


def purpose_distractors(ix, e, t0, t1, rng):
    """难负例优先:同一视频别处、与本题同动词或同物体中心词的目的;每个目的动词最多一次。"""
    p = purpose_of(e)
    near = purposes_near(ix, t0, t1)
    hard, soft = [], []
    for e2, p2 in sorted(purposes(ix), key=lambda x: x[0].eid):
        if p2["purpose"] in near or p2["purpose"] == p["purpose"]:
            continue
        similar = (p2["main"][0] == p["main"][0]
                   or PRIM._head_noun(p2["main"][1]) == PRIM._head_noun(p["main"][1]))
        (hard if similar else soft).append(p2)
    rng.shuffle(hard); rng.shuffle(soft)
    out, verbs = [], {p["pverb"]}
    for p2 in hard + soft:
        if p2["pverb"] in verbs or p2["purpose"] in out:
            continue
        verbs.add(p2["pverb"]); out.append(p2["purpose"])
        if len(out) == 3:
            return out, sum(1 for x in out if x in {h["purpose"] for h in hard})
    return None, 0


def check_purpose(ix, item, fact, errs):
    t0, t1 = item["t0"], item["t1"]
    r = sound_purpose(ix, ix.ev(fact["_sound_eid"]))
    if not r or r[0].eid != fact["_ref_eid"] or r[1]["purpose"] != item["answer"]:
        errs.append("目的重推不符"); return
    p = r[1]
    # 题面不得点名动作:主动作的动词与物体中心词都不许出现(否则又退回可盲猜)
    ql = item["question"].lower()
    for w in (p["main"][0], PRIM._head_noun(p["main"][1])):
        if w and re.search(rf"\b{re.escape(w)}\b", ql):
            errs.append(f"题面点名了动作('{w}')")
    near = purposes_near(ix, t0, t1)
    for d in item["_distractors"]:
        w = d.split()
        if d in near:
            errs.append(f"干扰目的 '{d}' 在窗口内也成立")
        if len(w) < 2 or w[0] != "to" or w[1] == p["pverb"]:
            errs.append(f"干扰目的 '{d}' 非法(须 'to <另一动词> ...')")


# ================= 高层活动:总体目标 / 下一步 =================

_SEGS = {}


def recipe_segs(video, duration):
    """[(start, end, label, recipe_id)],按起点排序;end 写成 'end' 的补为视频时长。"""
    if video not in _SEGS:
        rt = json.loads((C.HDEPIC / "annotations" / video / "raw" / "recipe_timestamps.json").read_text())
        def tf(x):
            try:
                return float(x)
            except ValueError:
                return float(duration)
        _SEGS[video] = sorted((tf(r["start_time"]), tf(r["end_time"]),
                               r["high_level_activity_label"].strip(), r.get("recipe_id") or "")
                              for r in rt)
    return _SEGS[video]


def seg_containing(segs, t0, t1, margin=2.0):
    hit = [i for i, s in enumerate(segs) if s[0] + margin <= t0 and t1 <= s[1] - margin]
    return hit[0] if len(hit) == 1 else None


def goal_distractor_pool(segs, k):
    """同视频其他段的标签,排除相邻段(边界不精确时相邻段可能部分可见)。"""
    near = {segs[j][2] for j in (k - 1, k, k + 1) if 0 <= j < len(segs)}
    return sorted({s[2] for s in segs} - near)


# ---- 总体目标按「能否靠认物排除干扰项」拆成两档(2026-09-28)----
# 旧版 medium_goal 实测 gemini 83% / qwen 73%(seed43-46 合并):一半题开头 3 s 的画面
# 就只指向 gold("Prepare mango" 对 "Wash frying pan lid"),看一眼即答,不是推断。
# - recognition(L1 easy_goal):gold 的词在窗口证据里出现,干扰项的词既不与 gold 共用、
#   也不在窗口里 —— 认出画面里的东西就能排除干扰项。
# - inference(L3 medium_goal):三个干扰项都与 gold 或窗口共用物体/动作
#   ("Bake puff pastry" / "Filling Tarts" 对 "Continue prepare puff pastry"),
#   认物排除不了,只能从动作序列推断处在哪个阶段。
# 两档都先剔除与 gold 近义的标签("Tidy up" 对 "Clean up and Tidy")—— 那是歧义题。
GOAL_STOP = frozenset("a an the and or of to in on it them its their for with from up into out "
                      "continue continuing prepare preparing more some put away stuff item items "
                      "hand hands get then".split())


def goal_toks(s):
    out = set()
    for w in re.findall(r"[a-z]+", (s or "").lower()):
        if w in GOAL_STOP:
            continue
        for suf in ("ing", "es", "ed", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[:-len(suf)]
                break
        out.add(w)
    return out


def goal_window_toks(ix, t0, t1):
    """窗口证据:narration 的 nouns/verbs + 可见物体 + movement 物体名。"""
    words = []
    for e in ix.in_window(t0, t1, "narration"):
        words += e.extra.get("nouns", []) + e.extra.get("verbs", [])
    words += ix.visible_in(t0, t1)
    words += [mv_name(m) for m in ix.in_window(t0, t1, "movement")]
    return goal_toks(" ".join(words))


def goal_near_dup(a, b):
    """近义标签:词集相同或互为子集(含忽略大小写后相同)。"""
    ta, tb = goal_toks(a), goal_toks(b)
    return a.lower() == b.lower() or (ta and tb and (ta <= tb or tb <= ta))


def goal_eligible(gold, W, d, mode):
    """d 能否作 mode 档的干扰项。gold/W/d 见上;mode ∈ {"recognition", "inference"}。"""
    G, D = goal_toks(gold), goal_toks(d)
    if not D or goal_near_dup(gold, d):
        return False
    if mode == "recognition":
        return not (D & G) and not (D & W)
    return bool(D & (G | W))


def goal_options(ix, segs, k, t0, t1, mode, rng):
    """mode 档的 3 个干扰项;凑不齐返回 None。recognition 另要求 gold 的词在窗口证据里。"""
    gold, W = segs[k][2], goal_window_toks(ix, t0, t1)
    if mode == "recognition" and not (goal_toks(gold) & W):
        return None
    pool = [d for d in goal_distractor_pool(segs, k) if goal_eligible(gold, W, d, mode)]
    rng.shuffle(pool)
    out = []
    for d in pool:
        if not any(goal_near_dup(d, x) for x in out):
            out.append(d)
        if len(out) == 3:
            return out
    return None


def check_goal(ix, item, fact, errs, mode):
    t0, t1, gold = item["t0"], item["t1"], item["answer"]
    segs = recipe_segs(ix.video_id, ix.duration)
    k = seg_containing(segs, t0, t1)
    if k is None or segs[k][2] != gold:
        errs.append("总体目标重推不符"); return
    W = goal_window_toks(ix, t0, t1)
    if mode == "recognition" and not (goal_toks(gold) & W):
        errs.append("识别档:gold 的词不在窗口证据里")
    pool = set(goal_distractor_pool(segs, k))
    ds = item["_distractors"]
    for d in ds:
        if d not in pool:
            errs.append(f"目标干扰项 '{d}' 非法(本段或相邻段)")
        elif not goal_eligible(gold, W, d, mode):
            errs.append(f"目标干扰项 '{d}' 不符合{mode}档条件")
    if any(goal_near_dup(a, b) for i, a in enumerate(ds) for b in ds[i + 1:]):
        errs.append("目标干扰项之间近义")


def next_window(seg):
    t1 = seg[1] - 2.0
    return (round(t1 - P.WIN_SEC, 2), round(t1, 2)) if t1 - P.WIN_SEC >= seg[0] else None


_LABELS = {}


def labels_other_videos(video):
    """其他视频的高层活动标签 —— 下一步题的干扰项(不同菜谱,与本段所用食材不符)。"""
    if video not in _LABELS:
        out = set()
        for v in P.VIDEOS:
            if v == video:
                continue
            rt = json.loads((C.HDEPIC / "annotations" / v / "raw" / "recipe_timestamps.json").read_text())
            out |= {r["high_level_activity_label"].strip() for r in rt}
        _LABELS[video] = sorted(out)
    return _LABELS[video]


# ================= 跨场景:取物 / 路线 =================

_MOVES = {}


def moves_by_obj(ix):
    """物体名 -> 按时间排序的全部 movement(不只 transition),用于「期间没被动过」的证明。"""
    if ix.video_id not in _MOVES:
        by = collections.defaultdict(list)
        for m in ix.movements:
            n = clean_obj(mv_name(m))
            if n:
                by[n].append(m)
        for n in by:
            by[n].sort(key=lambda m: (m.t_start, m.eid))
        _MOVES[ix.video_id] = dict(by)
    return _MOVES[ix.video_id]


def stationary(ix, name, t_from, t_to):
    return not any(t_from < m.t_start <= t_to for m in moves_by_obj(ix).get(name, []))


def same_fixture(ix, name, fixture, t_from, t_to):
    """期间所在设施类别不变:允许原地摆弄(拿起又放回同一处),不允许挪到别的设施。
    取物题只关心「去哪拿」,原地摆弄不改变答案;实测「一动不动」门误杀了 68/70 条。"""
    for m in moves_by_obj(ix).get(name, []):
        if t_from < m.t_start <= t_to:
            # 只有「位置转移」才可能挪到别处。原地摆弄的 movement 通常不带设施信息
            # (from/to 皆 None)—— 它不改变所在设施,不能按「名字对不上」判成挪走
            if not m.extra.get("is_transition"):
                continue
            if ix.fixture_pretty(m.extra.get("to_fixture")) != fixture:
                return False
    return True


def fixture_vocab(ix):
    v = set()
    for m in ix.transitions:
        for k in ("from_fixture", "to_fixture"):
            p = ix.fixture_pretty(m.extra.get(k))
            if p:
                v.add(p)
    return sorted(v)


def scene_a(ix, a):
    t0, t1 = win_around(ix.duration, a.mid())
    return (round(t0, 2), round(t1, 2)) if t0 <= a.t_start and a.t_end <= t1 else None


MIN_SCENE_GAP = 30.0       # 两场景之间至少隔开这么久(不相邻、不重叠)

SECTORS = ("left-front", "left-back", "right-front", "right-back")
MIN_ANGLE_MARGIN = 15.0


def sector(deg):
    """方位角(+ 左 / - 右,0 = 正前)-> (象限, 距象限边界的角度余量)。
    以观察者为原点、朝向为前,按 Cartesian 四象限分(命名先左右再前后,如 left-back):|deg| < 90 为 front,否则 back;deg > 0 为 left。
    边界在 0°、±90°、180°,余量 = 到最近边界的角度。旧版四扇区(直行/左转/右转/掉头)把左后方
    (90°–135°)归为「左转」,而掉头也说得通,歧义大(见 real_1001 L4-06,105°)。"""
    a = abs(deg)
    fb = "front" if a < 90 else "back"
    lr = "left" if deg > 0 else "right"
    return f"{lr}-{fb}", min(a, abs(90 - a), 180 - a)


def route_derive(video, T, xyz):
    """T 时刻相机稳定时,物体 xyz 相对「我」的方位。返回 (方向, 余量, 角度, 距离) 或 None。"""
    import pose as POSE
    p = POSE.at(video, T)
    if p is None:
        return None
    f_, l_, _, rng = POSE.to_device(p[0], p[1], xyz)
    deg = math.degrees(math.atan2(l_, f_))
    s, marg = sector(deg)
    return s, marg, deg, rng
