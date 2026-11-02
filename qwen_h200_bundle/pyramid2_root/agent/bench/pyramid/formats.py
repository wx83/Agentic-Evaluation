"""answer-format 层:同一 fact / 同一题在五种作答格式下的构造、提示、解析、判分与校验。

格式(pconfig.FORMATS):
- yn      一条陈述,答 yes / no(按子类 50/50 用 gold / 干扰项造真假陈述)
- mc      单选(现状,4 选 1;本模块不构造,只透传)
- ms      不定项:4 条陈述,1–3 条为真;真陈述来自本 fact 的 gold + 同窗口兄弟 fact 的 gold
- open    开放简答,只对 pconfig.OPEN_OK 的子类;其余子类退化为 tf4(保留原 4 选项,逐项 True/False)
- open_x  open + 一句解释(tf4 的对应物是 tf4_x)

陈述与 open 题干全部走模板、不走 Gemini 措辞:格式对照要控制的变量是作答形式,不是措辞。
gold / 干扰项一律沿用 mc 题的(已由 verify 在同窗口重推),本模块不产生新的 gold。
"""
import re
import pconfig as P
import config as C
import primitives as PRIM
import phrase as PH

STOP = frozenset("a an the to of in on it its their them my his her some and or with for up down "
                 "into out then".split())


def _cap(s):
    return s[:1].upper() + s[1:] if s else s


def _stem(w):
    for suf in ("ing", "es", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w


def toks(s):
    return {_stem(w) for w in re.findall(r"[a-z]+", (s or "").lower()) if w not in STOP}


def slot_format(fmt, subtype):
    """第 4/5 档按子类落到 open 还是 tf4。其余格式原样。"""
    if fmt == "open":
        return "open" if subtype in P.OPEN_OK else "tf4"
    if fmt == "open_x":
        return "open_x" if subtype in P.OPEN_OK else "tf4_x"
    return fmt


# ================= 陈述模板(yn / ms) =================

def statement(fact, cand):
    """把 (fact, candidate) 写成一条可判真假的陈述。cand ∈ {gold} ∪ distractors。"""
    st = fact["subtype"]
    ph = C.SOUND_PHRASE.get(fact.get("_sound_label") or "", "")
    the = PH._the
    if st == "easy_sound":
        return f"{_cap(cand)} can be heard during this clip."
    if st == "easy_sound_object":
        return f"The {ph} you can hear in this clip is produced by {the(cand)}."
    if st == "easy_move":
        return (f"The object moved from {fact['_from']} to {fact['_to']} during this clip "
                f"is {the(cand)}.")
    if st == "low_sound_movement":
        return f"At the moment you hear {ph}, the camera wearer is handling {the(cand)}."
    if st == "medium_count":
        return f"{_cap(ph)} is heard exactly {cand} separate times in this clip."
    if st == "low_sound_next":
        return f"Right after you hear {ph}, the next sound you hear is {cand}."
    if st == "medium_sound_order":
        return ("In this clip these sounds are first heard in this order: " +
                ", then ".join(cand.split(" -> ")) + ".")
    if st in ("high_order", "medium_order"):
        return "In this clip the order of events is: " + ", then ".join(cand.split(" -> ")) + "."
    ref = the(fact.get("_ref"))
    if st == "easy_spatial_near":
        return (f"When the camera wearer puts down {ref} during this clip, the object it ends up "
                f"closest to is {the(cand)}.")
    if st == "low_spatial_near":
        return (f"At the moment you hear {ph}, the object closest to {ref} that the camera wearer "
                f"is handling is {the(cand)}.")
    if st == "medium_spatial_extreme":
        rel = "closest to" if fact.get("_mode") == "near" else "furthest away from"
        return f"By the end of this clip, the object that ends up {rel} {ref} is {the(cand)}."
    if st in ("high_spatial_order", "medium_spatial_order"):
        return (f"By the end of the clip, ordered from closest to {ref} to furthest, the objects "
                f"are: " + ", then ".join(cand.split(" -> ")) + ".")
    if st in ("medium_purpose", "low_purpose"):
        return f"At the moment you hear {ph}, the camera wearer is trying {cand}."
    if st in ("medium_goal", "easy_goal"):
        return f"Taking the whole clip into account, the camera wearer is mainly working on: {cand}."
    if st == "high_plan_next":
        return f"Right after this clip, the camera wearer will most likely: {cand}."
    if st == "high_plan_next_action":
        return f"Right after this clip, the camera wearer will {cand}."
    if st == "high_replan":
        return f"After noticing the problem in this clip, the camera wearer will {cand}."
    if st == "high_plan_next_step":
        return f"Right after this clip, the next step the camera wearer takes is: {cand}."
    if st == "high_gaze_destination":
        return (f"At the end of this clip the camera wearer is holding {the(fact['_object'])}; "
                f"they are about to put it down on or in {cand}.")
    if st == "high_gaze_pickup":
        return f"Right after this clip ends, the object the camera wearer picks up is {the(cand)}."
    if st == "high_plan_route":
        return (f"{PH._scenes(fact)} At the very end of the second scene, "
                f"{the(fact['_object'])} they put down in the first scene is to the camera wearer's "
                f"{cand}.")
    if st == "easy_spatial_side":
        return (f"At the moment the camera wearer puts down {the(fact['_anchor'])}, the object "
                f"furthest to their {fact.get('_mode', 'right')} is {the(cand)}.")
    if st == "low_spatial_side":
        return (f"At the moment you hear {ph}, the object furthest to the camera wearer's "
                f"{fact.get('_mode', 'left')} is {the(cand)}.")
    raise ValueError(st)


# ================= open 题干模板 =================

def open_question(fact):
    """无选项也能独立作答的题干,并写明输出格式(用户原则:数值给格式,实体给「名字」,描述要直接)。"""
    st = fact["subtype"]
    ph = C.SOUND_PHRASE.get(fact.get("_sound_label") or "", "")
    the = PH._the
    if st == "easy_sound_object":
        return (f"You can hear {ph} in this clip. Which object visible on screen is producing it? "
                f"Answer with the name of the object.")
    if st == "easy_move":
        return (f"During this clip, one object is moved from {fact['_from']} to {fact['_to']}. "
                f"Which object is it? Answer with the name of the object.")
    if st == "low_sound_movement":
        return (f"At the moment you hear {ph}, which object is the camera wearer handling? "
                f"Answer with the name of the object.")
    if st == "medium_count":
        return f"How many separate times is {ph} heard in this clip? Answer with a single integer."
    if st in ("high_order", "medium_order"):
        return ("Put these three actions in the order they happen in this clip: (" +
                "; ".join(PH._shuffled_parts(fact)) +
                "). List all three in order, separated by ' -> '.")
    if st == "medium_sound_order":
        return ("Put these three sounds in the order they are first heard in this clip: (" +
                "; ".join(PH._shuffled_parts(fact)) +
                "). List all three in order, separated by ' -> '.")
    if st in ("high_spatial_order", "medium_spatial_order"):
        return (f"Put these three objects in order of how close they end up to "
                f"{the(fact.get('_ref'))} by the end of the clip, closest first: (" +
                "; ".join(PH._shuffled_parts(fact)) +
                "). List all three in order, separated by ' -> '.")
    if st == "easy_goal":
        return ("What activity is the camera wearer working on in this clip? "
                "Answer in one short, direct phrase.")
    if st in ("medium_purpose", "low_purpose"):
        return (f"At the moment you hear {ph}, what is the camera wearer trying to do? "
                f"Answer in one short, direct phrase starting with 'to'.")
    if st == "high_gaze_pickup":
        return ("Which object is the camera wearer about to pick up right after this clip ends? "
                "Answer with the name of the object.")
    if st == "high_plan_next_step":
        return (f"The camera wearer is working on: {fact['_goal']} Right after this clip ends, what should the camera "
                f"wearer do next? Answer with a short phrase naming the action and the object.")
    if st == "high_replan":
        g = f"The camera wearer is working on: {fact['_goal']}. " if fact.get("_goal") else ""
        return (f"{g}Something does not go as planned in this clip: {fact['_situation']} What should the camera wearer "
                f"do right after the clip ends? Answer with a short verb phrase, e.g. 'open the drawer'.")
    if st == "high_plan_next_action":
        return (f"The camera wearer is working on: {fact['_goal']}. Right after this clip ends, what is "
                f"the camera wearer going to do next? Answer with a short verb phrase, e.g. 'open the drawer'.")
    if st == "high_plan_route":
        return (f"{PH._scenes(fact)} At the very end of the second scene, the camera wearer wants "
                f"to walk over to {the(fact['_object'])} they put down in the first scene. "
                f"Relative to the direction they are facing, where is it? Answer with exactly one of: "
                f"left-front, left-back, right-front, right-back.")
    raise ValueError(f"{st} 不在 OPEN_OK")


# ================= 提示语 =================

_TIME = "Time: <M:SS>   (when in the clip the evidence you used occurs)"
_WHY = "Because: <one sentence on what you saw or heard that supports your answer>"


def instr(fmt):
    if fmt == "yn":
        return ("Decide whether the statement above is true for this clip.\n"
                "Reply on exactly two lines, nothing else:\nAnswer: <yes/no>\n" + _TIME)
    if fmt == "ms":
        return ("One or more of the statements above are true for this clip (at least one is). "
                "Select ALL the true ones.\nReply on exactly two lines, nothing else:\n"
                "Answer: <letters of all true statements, comma-separated, e.g. A, C>\n" + _TIME)
    if fmt in ("tf4", "tf4_x"):
        n = "six" if fmt == "tf4_x" else "five"
        return (f"Judge each statement above for this clip.\nReply on exactly {n} lines, nothing else:\n"
                "A: <true/false>\nB: <true/false>\nC: <true/false>\nD: <true/false>\n" +
                (_WHY + "\n" if fmt == "tf4_x" else "") + _TIME)
    if fmt == "open":
        return "Reply on exactly two lines, nothing else:\nAnswer: <your answer>\n" + _TIME
    if fmt == "open_x":
        return ("Reply on exactly three lines, nothing else:\nAnswer: <your answer>\n" +
                _WHY + "\n" + _TIME)
    if fmt in ("plan", "plan_x"):
        return ("List the ordered steps you would take to achieve this goal, starting from the state shown in the clip. "
                "Reply with 4-8 numbered lines, each one short action (verb + object), nothing else." +
                ("\nThen add one line: " + _WHY if fmt == "plan_x" else ""))
    raise ValueError(fmt)


def build_prompt(item):
    fmt = item["fmt"]
    if fmt == "yn":
        return f"Statement: {item['statement']}\n\n{instr(fmt)}"
    if fmt == "ms":
        return ("Which of these statements are true for this clip?\nStatements:\n" +
                "\n".join(item["statements"]) + "\n\n" + instr(fmt))
    if fmt in ("tf4", "tf4_x"):
        return ("Question: " + item["question"] + "\nStatements:\n" +
                "\n".join(item["options"]) + "\n\n" + instr(fmt))
    if fmt in ("open", "open_x"):
        return f"Question: {item['question']}\n\n{instr(fmt)}"
    if fmt in ("plan", "plan_x"):
        return f"Goal: {item['question']}\n\n{instr(fmt)}"
    raise ValueError(fmt)


# ================= 构造 =================

def _base_fields(base, fact, fmt):
    keep = ("tier", "subtype", "kind", "video_id", "t0", "t1", "windows", "fact_id",
            "evidence_event_ids", "evidence_t", "_sound_label", "answer", "_distractors",
            "correct_option", "clip_path", "dataset")
    it = {"question_id": f"{base['question_id']}#{fmt}", "base_id": base["question_id"],
          "fmt": fmt, "level": base.get("level")}
    it.update({k: base[k] for k in keep if k in base})
    return it


def build_yn(base, fact, truth, rng):
    """truth=True 用 gold;False 用 rng 选的一个干扰项(难负例)。"""
    it = _base_fields(base, fact, "yn")
    cand = fact["gold"] if truth else rng.choice(sorted(fact["distractors"]))
    it.update({"statement": statement(fact, cand), "_yn_cand": cand,
               "_yn_truth": "yes" if truth else "no", "options": None})
    return it


def sound_fillers(ix, t0, t1):
    """本窗口可程序验证的补充陈述(兄弟 fact 不够时用):
    真 = 窗口内完整出现的可命名声音;假 = ±30 s 无标注且不被窗口内动作暗示的声音
    (与 easy_sound 的干扰项规则相同,facts.sound_distractor_ok)。返回 (真列表, 假列表),元素 (伪 fact, cand)。"""
    import facts as F
    present = sorted({x.label for x in ix.sounds_between(t0, t1)
                      if x.label in C.SOUND_PHRASE and x.label not in F.EASY_SOUND_NEVER
                      and x.t_start >= t0 and x.t_end <= t1})
    absent = [l for l in sorted(ix.by_sound_label) if F.sound_distractor_ok(ix, l, t0, t1)]
    mk = lambda lab: {"fact_id": f"win_sound:{lab}", "subtype": "easy_sound", "kind": "SOUND",
                      "_sound_label": lab, "gold": C.SOUND_PHRASE[lab], "distractors": [],
                      "video_id": ix.video_id, "t0": t0, "t1": t1, "tier": "Easy"}
    return ([(mk(l), C.SOUND_PHRASE[l]) for l in present],
            [(mk(l), C.SOUND_PHRASE[l]) for l in absent])


def build_ms(base, fact, k, siblings, rng, ix=None):
    """4 条陈述、k 条为真。真:本 fact 的 gold + 兄弟 fact 的 gold(同层优先),不够再用
    窗口声音补充陈述(sound_fillers);假:本 fact 与兄弟的干扰项 + 缺席声音。返回 (item, 实际 k)。"""
    it = _base_fields(base, fact, "ms")
    trues = [(fact, fact["gold"])]
    sibs = sorted(siblings, key=lambda f: f["fact_id"])
    rng.shuffle(sibs)
    sibs.sort(key=lambda f: f.get("tier") != fact.get("tier"))     # 稳定排序:同层在前
    ft, ff = sound_fillers(ix, fact["t0"], fact["t1"]) if ix is not None and not fact.get("windows") else ([], [])
    rng.shuffle(ft); rng.shuffle(ff)
    for f, c in [(f, f["gold"]) for f in sibs] + ft:
        if len(trues) >= k:
            break
        s = statement(f, c)
        if all(s != statement(g, cc) for g, cc in trues):
            trues.append((f, c))
    falses = [(fact, d) for d in sorted(fact["distractors"])]
    for f in sibs:
        falses += [(f, d) for d in sorted(f["distractors"])]
    falses += ff
    # 假陈述不得与任何真陈述同子类同候选(兄弟的干扰项在其窗口已验为假,但同子类里
    # 另一条 fact 的 gold 恰好是它的干扰项时会自相矛盾)
    true_keys = {(f["subtype"], c) for f, c in trues}
    falses = [(f, d) for f, d in falses if (f["subtype"], d) not in true_keys]
    # 本 fact 的干扰项优先(难负例),其余打乱补足
    own = [x for x in falses if x[0]["fact_id"] == fact["fact_id"]]
    rest = [x for x in falses if x[0]["fact_id"] != fact["fact_id"]]
    rng.shuffle(rest)
    falses = own + rest
    pool, seen = [], set()
    for f, c in trues:
        pool.append((f, c, True)); seen.add(statement(f, c))
    for f, d in falses:
        if len(pool) == 4:
            break
        s = statement(f, d)
        if s not in seen:
            pool.append((f, d, False)); seen.add(s)
    if len(pool) < 4:
        return None, 0
    rng.shuffle(pool)
    it["statements"] = [f"{'ABCD'[i]}. {statement(f, c)}" for i, (f, c, _) in enumerate(pool)]
    it["_stmt_src"] = [{"fact_id": f["fact_id"], "subtype": f["subtype"], "cand": c, "truth": t}
                       for f, c, t in pool]
    it["_gold_set"] = "".join("ABCD"[i] for i, (_, _, t) in enumerate(pool) if t)
    it["options"] = None
    return it, len(it["_gold_set"])


def build_tf4(base, fact, fmt):
    """保留 mc 的 4 个选项,逐项 True/False。按构造恰好 1 真。"""
    it = _base_fields(base, fact, fmt)
    it.update({"question": base["question"], "options": list(base["options"]),
               "_gold_idx": base["_gold_idx"]})
    return it


def build_open(base, fact, fmt):
    it = _base_fields(base, fact, fmt)
    it.update({"question": open_question(fact), "options": None})
    return it


# ================= 解析 =================

def _answer_line(raw):
    m = re.search(r"(?im)^\s*answer\s*[:：]\s*(.+?)\s*$", raw or "")
    if m:
        return m.group(1).strip()
    for line in (raw or "").strip().splitlines():
        l = line.strip()
        if l and not re.match(r"(?i)^(time|because)\s*[:：]", l):
            return l
    return None


def parse(fmt, raw):
    """返回结构化答案(解析失败 None)与解释文本。"""
    expl = None
    m = re.search(r"(?im)^\s*because\s*[:：]\s*(.+?)\s*$", raw or "")
    if m:
        expl = m.group(1).strip()
    if fmt in ("plan", "plan_x"):
        lines = [m.group(1).strip() for m in re.finditer(r"(?m)^\s*\d+\s*[.)]\s*(.+?)\s*$", raw or "")]
        lines = [l for l in lines if not re.match(r"(?i)^(time|because)\s*[:：]", l)]
        return (lines if len(lines) >= 2 else None), expl
    if fmt == "yn":
        a = _answer_line(raw)
        if a is None:
            return None, expl
        w = a.lower().strip("<>[]() ")            # Qwen 会把占位符的尖括号照抄:"Answer: <yes>"
        if re.match(r"^(yes|true|correct)\b", w):
            return "yes", expl
        if re.match(r"^(no|false|incorrect)\b", w):
            return "no", expl
        return None, expl
    if fmt == "ms":
        a = _answer_line(raw)
        if a is None:
            return None, expl
        if re.match(r"(?i)^\s*none\b", a):
            return "", expl
        letters = set(re.findall(r"\b([ABCD])\b", a.upper().replace("<", " ").replace(">", " ")))
        return "".join(sorted(letters)) if letters else None, expl
    if fmt in ("tf4", "tf4_x"):
        out = {}
        for L in "ABCD":
            # 允许 "A: <true>"(Qwen 照抄占位符的尖括号,实测 91/166 题因此解析失败)
            m = re.search(rf"(?im)^\s*\(?{L}[\)\.]?\s*[:：\-]\s*<?\s*(true|false|yes|no|t|f)\b", raw or "")
            if not m:
                return None, expl
            out[L] = m.group(1).lower() in ("true", "yes", "t")
        return "".join(L for L in "ABCD" if out[L]), expl
    if fmt in ("open", "open_x"):
        a = _answer_line(raw)
        return (a.strip("<>") if a else a), expl
    raise ValueError(fmt)


# ================= 判分 =================

_FB = [("back", r"\b(back|behind|rear|around)\b"), ("front", r"\b(front|ahead|forward|forwards)\b")]
_LR = [("left", r"\bleft\b"), ("right", r"\bright\b")]


def _direction(text):
    """自由回答 -> 象限(left/right × front/back),两个维度各取首次出现的词;缺一维返回 None。"""
    low = text.lower().replace("-", " ")

    def first(pairs):
        hits = [(m.start(), k) for k, rx in pairs for m in [re.search(rx, low)] if m]
        return min(hits)[1] if hits else None
    fb, lr = first(_FB), first(_LR)
    return f"{lr}-{fb}" if fb and lr else None


def _order_positions(reply, parts):
    """三项各自在回答里首次出现的位置;找不到或重合返回 None。"""
    low = reply.lower()
    pos = []
    for p in parts:
        keys = [p.lower()]
        np_ = re.sub(r"^\S+(?:\s+\S+)?\s+the\s+", "", p.lower())     # "pick up the cup" -> "cup"
        if np_ != p.lower():
            keys.append(np_)
        keys.append(PRIM._head_noun(p))
        i = next((low.find(k) for k in keys if k and low.find(k) >= 0), -1)
        if i < 0:
            return None
        pos.append(i)
    return pos if len(set(pos)) == 3 else None


def _hit(text, name):
    n = PRIM._norm(name)
    return bool(n) and re.search(rf"\b{re.escape(n)}\b", text) is not None


def score_open_rule(item, reply):
    """规则判分。返回 True / False / None(规则无结论,交 judge)。"""
    if not reply:
        return None
    kind, gold, ds = item["kind"], item["answer"], item["_distractors"]
    text = PRIM._norm(reply)
    if kind == "COUNT":
        m = re.search(r"-?\d+", reply)
        return (int(m.group()) == int(gold)) if m else None
    if kind == "ROUTE":
        d = _direction(reply)
        return (d == gold) if d else None
    if kind == "ORDER":
        parts = gold.split(" -> ")
        if item["subtype"] == "medium_sound_order":
            # 声音短语的中心词会相撞("... knocking together"),只认完整短语,其余交 judge
            low = reply.lower()
            pos = [low.find(p.lower()) for p in parts]
            pos = pos if min(pos) >= 0 and len(set(pos)) == 3 else None
            return (pos == sorted(pos)) if pos else None
        pos = _order_positions(reply, parts)
        return (pos == sorted(pos)) if pos else None
    if kind == "PURPOSE":
        g, dd = toks(gold), [toks(d) for d in ds]
        r = toks(reply)
        if g and g <= r:
            return True
        if any(d and d <= r for d in dd) and not (g & r):
            return False
        return None
    if item["subtype"] == "easy_goal":
        g, dd = toks(gold), [toks(d) for d in ds]
        gonly = g - set().union(*dd)
        r = toks(reply)
        if gonly & r and not any((d - g) & r for d in dd):
            return True
        if any((d - g) & r for d in dd) and not (gonly & r):
            return False
        return None
    if kind in ("ACTION", "REPLAN", "STEP"):
        # 动作短语:gold 的动词 + 物体词干都在回答里,且没有干扰项独有的词 -> 对;反之 -> 错;其余交 judge
        g, dd = toks(gold), [toks(d) for d in ds]
        r = toks(reply)
        donly = [d - g for d in dd]
        if g <= r and not any(d & r for d in donly):
            return True
        if any(d & r for d in donly) and not (g - set().union(*dd)) & r:
            return False
        return None
    # 物体名(OBJECT / NEAREST):归一化名或中心词
    hit_g = _hit(text, gold) or (PRIM._head_noun(text) == PRIM._head_noun(gold))
    hit_d = [d for d in ds if _hit(text, d)]
    if hit_g and not hit_d:
        return True
    if hit_d and not hit_g:
        return False
    return None


def score(fmt, parsed, item):
    """返回 (correct, score, score_by, detail)。open 的规则无结论时 correct=None、score_by="pending"。"""
    if fmt == "yn":
        ok = parsed is not None and parsed == item["_yn_truth"]
        return ok, float(ok), "rule", None
    if fmt == "ms":
        g = set(item["_gold_set"])
        p = set(parsed or "")
        jac = len(g & p) / len(g | p) if (g | p) else 0.0
        return (parsed is not None and p == g), jac, "rule", {"jaccard": round(jac, 3)}
    if fmt in ("tf4", "tf4_x"):
        g = "ABCD"[item["_gold_idx"]]
        if parsed is None:
            return False, 0.0, "rule", {"per_item": 0}
        n_ok = sum((L in parsed) == (L == g) for L in "ABCD")
        return n_ok == 4, n_ok / 4, "rule", {"per_item": n_ok}
    if fmt in ("open", "open_x"):
        r = score_open_rule(item, parsed)
        if r is None:
            return None, 0.0, "pending", None
        return r, float(r), "rule", None
    if fmt in ("plan", "plan_x"):
        return None, 0.0, "pending", None            # 由 adaptive.score_item 走 judge.align_plan + plan_traj.metrics
    raise ValueError(fmt)


# ================= 校验(verify.check 的格式分支) =================

# ORDER 题干按设计列出三项("Put these three actions ... (a; b; c)"),那不是依赖选项,不拦
_OPTION_WORDS = ("which of these", "which of the following", "of these objects", "of these sounds",
                 "options", "option ")


_NUM_WORDS = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven",
              "8": "eight", "9": "nine", "10": "ten"}


def _check_statement_text(text, cand, all_cands, errs, tag):
    """Gemini 写的陈述:必须写进自己的候选,不得写进同一事实的其他候选(否则真假不再由候选决定)。
    顺序类候选("a -> b -> c")按三项出现的先后判;计数候选接受数字或英文数词。"""
    low = text.lower()
    if " -> " in cand:
        parts = cand.split(" -> ")
        pos = [low.find(p.lower()) for p in parts]
        if min(pos) < 0:
            errs.append(f"{tag} 顺序陈述缺少某一项:{cand}")
        elif pos != sorted(pos):
            errs.append(f"{tag} 顺序陈述的先后与候选不符:{cand}")
        return                                   # 其他候选是同三项的别的排列,天然会"提到"
    if cand.isdigit():
        if not re.search(rf"\b({cand}|{_NUM_WORDS.get(cand, cand)})\b", low):
            errs.append(f"{tag} 陈述未包含计数 '{cand}'")
        for c in all_cands:
            if c != cand and re.search(rf"\b({c}|{_NUM_WORDS.get(c, c)})\b", low):
                errs.append(f"{tag} 陈述提到了其他计数 '{c}'")
        return
    norm = PRIM._norm(text)
    def hit(c):
        n = PRIM._norm(c)
        return bool(n) and n in norm
    if not hit(cand):
        errs.append(f"{tag} 陈述未包含候选 '{cand}'")
    for c in all_cands:
        if c != cand and hit(c) and PRIM._norm(c) not in PRIM._norm(cand):
            errs.append(f"{tag} 陈述提到了其他候选 '{c}'")


def check(ix, item, fact, errs):
    """格式题的结构校验。gold / 干扰项 / 证据窗口与 mc 题相同,这里只查格式自身的一致性与泄漏。"""
    fmt = item["fmt"]
    if item["answer"] != fact["gold"]:
        errs.append("answer 与程序 gold 不一致")
    if sorted(item["_distractors"]) != sorted(fact["distractors"]):
        errs.append("干扰项与程序挖出的不一致")
    if fmt == "yn":
        c, t = item["_yn_cand"], item["_yn_truth"]
        if (c == fact["gold"]) != (t == "yes"):
            errs.append("yn 真值与候选不一致")
        if c != fact["gold"] and c not in fact["distractors"]:
            errs.append("yn 候选既非 gold 也非干扰项")
        if item.get("phrasing") == "gemini":
            _check_statement_text(item["statement"], c, [fact["gold"]] + list(fact["distractors"]), errs, "yn")
        elif item["statement"] != statement(fact, c):
            errs.append("yn 陈述与模板不符")
    elif fmt == "ms":
        src, sts = item["_stmt_src"], item["statements"]
        if len(sts) != 4 or len({s[3:] for s in sts}) != 4:
            errs.append("ms 陈述不足 4 条互异")
        gs = item["_gold_set"]
        if not (1 <= len(gs) <= 3):
            errs.append(f"ms 真陈述数 {len(gs)} 不在 1–3")
        if gs != "".join("ABCD"[i] for i, s in enumerate(src) if s["truth"]):
            errs.append("ms _gold_set 与来源真值不一致")
        if not any(s["fact_id"] == fact["fact_id"] and s["truth"] for s in src):
            errs.append("ms 未包含本 fact 的 gold 陈述")
        if item.get("phrasing") == "gemini":
            for st_, sr in zip(sts, src):
                others = [fact["gold"]] + list(fact["distractors"]) if sr["fact_id"] == fact["fact_id"] else []
                _check_statement_text(st_[3:], sr["cand"], others, errs, "ms")
        for s in src:
            if s["fact_id"] == fact["fact_id"]:
                ok = (s["cand"] == fact["gold"]) if s["truth"] else (s["cand"] in fact["distractors"])
                if not ok:
                    errs.append(f"ms 本 fact 陈述候选与真值不符:{s['cand']}")
            elif s["fact_id"].startswith("win_sound:"):
                # 窗口声音补充陈述:在本窗口上重推真伪
                import facts as F
                lab = s["fact_id"].split(":", 1)[1]
                t0, t1 = item["t0"], item["t1"]
                present = any(x.t_start >= t0 and x.t_end <= t1 for x in ix.sounds_between(t0, t1, lab))
                if s["truth"] and not present:
                    errs.append(f"ms 补充陈述声音 '{lab}' 不在窗口内")
                if not s["truth"] and not F.sound_distractor_ok(ix, lab, t0, t1):
                    errs.append(f"ms 补充陈述声音 '{lab}' 未通过缺席规则")
    elif fmt in ("tf4", "tf4_x"):
        if len(set(item["options"])) != 4 or item["options"][item["_gold_idx"]][3:] != fact["gold"]:
            errs.append("tf4 选项 / gold 位置不一致")
    elif fmt in ("open", "open_x"):
        if item["subtype"] not in P.OPEN_OK:
            errs.append(f"{item['subtype']} 不允许 open 格式")
        q = item["question"]
        ql = q.lower()
        if item["kind"] == "COUNT":
            if re.search(rf"\b{re.escape(fact['gold'])}\b", q):
                errs.append("open 题面泄漏计数 gold")
        elif item["kind"] != "ORDER" and fact["gold"].lower() in ql:
            errs.append("open 题面泄漏 gold")
        if any(w in ql for w in _OPTION_WORDS):
            errs.append("open 题面仍依赖选项措辞")
    else:
        errs.append(f"未知格式 {fmt}")
