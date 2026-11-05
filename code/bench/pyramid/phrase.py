"""事实 -> 题面措辞。gold 与干扰项始终由程序固定,Gemini 只写 question 文本。

- few-shot 样例来自 output/_shared/chains.json(0830 的 8 条链)。
- 磁盘缓存键 sha256(fact_id|summary_sha|PROMPT_VERSION)。
- --offline / 无 key / Gemini 产出两次未过校验时,回退每 subtype 固定模板,
  标 phrasing="template"(每套上限 pconfig.TEMPLATE_FRAC_MAX)。
- 从 L2 起,prompt 前置上一层的作答摘要(自适应只作用在措辞风格与选材,绝不碰 gold)。
"""
import json, hashlib, random, re
import pconfig as P
import config as C
import gemini_io

PROMPT_VERSION = "v10"     # v2: easy_sound 禁止提任何声音(v1 泄漏 gold)
                           # v3: 干扰项去重后重建(见 facts.clean_distractors)
                           # v4: 新增四个 spatial 子类的措辞规则
                           # v5: spatial 题面强制保留时刻锚点(v4 被简化成无锚点问句)
                           # v6: 新增两个 ego 子类(参照是摄像者本人)
                           # v7: 关系变体(near / 反方向 ego);spatial 范例按 (子类,关系) 匹配
                           # v8: L3 推断(目的/总体目标)、L4 规划(下一步/跨场景取物/路线);排序下放 L3
                           # v9: 目的题改为声音定时刻、不点名动作;L1 声音->物体与搬动题换同类干扰项
# Tier intent: The cognitive level of the question
TIER_INTENT = {
    "Easy":   "one piece of evidence, read off directly — either the sound and a visible object "
              "confirm each other, or a single placement answers it",
    "Low":    "two complementary cues: the sound gives the time anchor, the picture gives the answer",
    "Medium": "inference over the whole clip — why an action was done, what the overall activity "
              "is, how often something happens, the order of events, or where things end up",
    "High":   "planning — what the camera wearer will do next, where to go to fetch something seen "
              "earlier, or which way to head; the video may join two scenes of the same kitchen",
}


def _scenes(fact):
    """跨场景题的开场白:交代片中有跳切,以及两段相隔多久。"""
    g = fact.get("_gap_s") or 0
    when = "about a minute" if g < 90 else f"about {round(g / 60)} minutes"
    return f"This video shows two scenes from the same kitchen, recorded {when} apart."


def _shuffled_parts(fact):
    """High 层题面里列出的三个动作:种子打乱且不等于 gold 顺序。"""
    parts = fact["gold"].split(" -> ")
    rng = random.Random(fact["fact_id"])
    order = parts[:]
    while True:
        rng.shuffle(order)
        if order != parts:
            return order


_DETS = ("a ", "an ", "the ", "some ", "his ", "her ", "their ", "my ", "one ", "two ")


def _the(name):
    """标注里的物体名有的自带限定词("some cling film"),再套 "the" 就成了
    "the some cling film"。已带限定词的原样用。"""
    n = (name or "").strip()
    return n if n.lower().startswith(_DETS) else f"the {n}"


def offline_question(fact):
    st = fact["subtype"]
    ph = C.SOUND_PHRASE.get(fact.get("_sound_label") or "", "")
    if st == "easy_sound_object":
        return f"You can hear {ph} in this clip. Which object visible on screen is producing it?"
    if st == "easy_sound":
        return "Which of the following sounds can be heard during this clip?"
    if st == "easy_move":
        return (f"During this clip, one object is moved from {fact['_from']} to {fact['_to']}. "
                f"Which object is it?")
    if st == "low_sound_movement":
        return f"At the moment you hear {ph}, which object is the camera wearer handling?"
    if st == "medium_count":
        return f"How many separate times is {ph} heard in this clip?"
    if st == "low_sound_next":
        return f"Right after you hear {ph}, which of these sounds do you hear next?"
    if st == "medium_sound_order":
        return ("Put these three sounds in the order they are first heard in this clip.\n(" +
                "; ".join(_shuffled_parts(fact)) + ")")
    if st in ("high_order", "medium_order"):
        return ("Put these three actions in the order they happen in this clip.\n(" +
                "; ".join(_shuffled_parts(fact)) + ")")
    ref = _the(fact.get("_ref"))
    if st == "easy_spatial_near":
        return (f"The camera wearer puts down {ref} during this clip. "
                f"Which of these objects does it end up closest to?")
    if st == "low_spatial_near":
        return (f"At the moment you hear {ph}, the camera wearer is handling {ref}. "
                f"Which of these other objects is it closest to right then?")
    if st == "medium_spatial_extreme":
        rel = "closest to" if fact.get("_mode") == "near" else "furthest away from"
        return (f"By the end of this clip, which of these objects ends up "
                f"{rel} {ref}?")
    if st in ("high_spatial_order", "medium_spatial_order"):
        return (f"Put these three objects in order of how close they end up to "
                f"{ref} by the end of the clip, closest first.\n(" +
                "; ".join(_shuffled_parts(fact)) + ")")
    if st in ("medium_purpose", "low_purpose"):
        return f"At the moment you hear {ph}, what is the camera wearer trying to do?"
    if st == "medium_goal":
        return "Taking the whole clip into account, what is the camera wearer mainly working on?"
    if st == "easy_goal":
        return "What activity is the camera wearer working on in this clip?"
    if st == "high_gaze_destination":
        return (f"At the end of this clip the camera wearer is holding {_the(fact['_object'])}. "
                f"Where are they about to put it down?")
    if st == "high_gaze_pickup":
        return "Which object is the camera wearer about to pick up right after this clip ends?"
    if st == "high_plan_next":
        return ("Judging from what the camera wearer is doing in this clip, "
                "what are they most likely to do next?")
    if st == "high_plan_next_action":
        return (f"The camera wearer is working on: {fact['_goal']}. "
                f"Right after this clip ends, what is the camera wearer going to do next?")
    if st == "high_replan":
        g = f"The camera wearer is working on: {fact['_goal']}. " if fact.get("_goal") else ""
        return (f"{g}Something does not go as planned in this clip. "
                f"What should the camera wearer do right after the clip ends?")
    if st == "high_plan_trajectory":
        return fact["_goal"]                           # plan 格式的题面就是 goal 句
    if st == "high_plan_next_step":
        return (f"The camera wearer is working on: {fact['_goal']} "
                f"Right after this clip ends, what should the camera wearer do next?")
    if st == "high_plan_retrieve":
        return (f"{_scenes(fact)} At the end of the second scene, the camera wearer wants "
                f"{_the(fact['_object'])} again. Where should they go to get it?")
    if st == "high_plan_route":
        return (f"{_scenes(fact)} At the very end of the second scene, the camera wearer wants to "
                f"walk over to {_the(fact['_object'])} they put down in the first scene. "
                f"Relative to the direction they are facing, in which quadrant is it?")
    if st == "easy_spatial_side":
        return (f"At the moment the camera wearer puts down {_the(fact['_anchor'])}, "
                f"which of these objects is furthest to their {fact.get('_mode', 'right')}?")
    if st == "low_spatial_side":
        return (f"At the moment you hear {ph}, which of these objects is furthest "
                f"to the camera wearer's {fact.get('_mode', 'left')}?")
    raise ValueError(st)


def _exemplars(tier, n=3, facts=None):
    """tier 通用范例(chains.json,全是非 spatial 的四种模板句)+ 按批内 spatial
    (子类, 关系) 匹配的真实范例(spatial_exemplars.json)—— 否则 spatial 批看到的
    全是非 spatial 的例句,「以 spatial 题为模板」就落空了。"""
    d = json.loads(P.EXEMPLARS.read_text())
    ex = [s for c in d["chains"] for s in c["steps"] if s["tier"] == tier]
    rng = random.Random(f"{P.SEED}|{tier}")
    rng.shuffle(ex)
    ex = ex[:n]
    if facts and P.SPATIAL_EXEMPLARS.exists():
        bank = json.loads(P.SPATIAL_EXEMPLARS.read_text())
        keys = sorted({f"{f['subtype']}|{f.get('_mode', '')}" for f in facts
                       if "spatial" in f["subtype"]})
        for k in keys:
            ex += bank.get(k, [])[:2]
    return ex


def _fact_packet(fact):
    p = {"fact_id": fact["fact_id"], "subtype": fact["subtype"],
         "clip_length_sec": 30, "correct_answer": fact["gold"],
         "distractors": fact["distractors"]}
    if fact.get("_sound_label"):
        p["sound_natural_phrase"] = C.SOUND_PHRASE[fact["_sound_label"]]
    if fact["subtype"] == "easy_move":
        p["moved_from"], p["moved_to"] = fact["_from"], fact["_to"]
    if fact["subtype"] in ("high_order", "medium_order"):
        p["three_actions_shuffled"] = _shuffled_parts(fact)
    if fact.get("_ref"):
        p["reference_object"] = fact["_ref"]
        p["relation"] = ("furthest" if fact["subtype"] == "medium_spatial_extreme"
                         and fact.get("_mode", "far") == "far" else "closest")
    if fact["subtype"] in ("high_spatial_order", "medium_spatial_order"):
        p["three_objects_shuffled"] = _shuffled_parts(fact)
    if fact.get("_action"):
        p["action"] = fact["_action"]
    if fact.get("_object"):
        p["object"] = fact["_object"]
    if fact.get("_goal"):
        p["goal"] = fact["_goal"]                      # 粗粒度活动标签,题面须原文给出
    if fact.get("windows"):
        p["two_scenes"] = True
        p["scene_intro"] = _scenes(fact)
    if fact["subtype"] in ("easy_spatial_side", "low_spatial_side"):
        p["ego_side"] = fact.get("_mode", "right")     # 相对「摄像者本人」的左/右
        if fact.get("_anchor"):
            p["anchor_object"] = fact["_anchor"]       # 只用来点时刻,绝不能当选项
    return p


def _build_prompt(tier, facts, summary):
    ex = [{"question": e["question"], "answer": e["answer"]} for e in _exemplars(tier, facts=facts)]
    lines = [
        "You write questions for an audio-visual understanding benchmark over 30-second",
        "first-person kitchen clips. For each fact packet below, write ONE four-choice",
        f"question. Tier: {tier} ({TIER_INTENT[tier]}).",
        "",
        "Hard rules:",
        "- The correct answer and the distractors are FIXED facts; never change, rephrase",
        "  or contradict them. You only write the question text.",
        "- The question text must NOT contain the correct answer string.",
        "- Refer to sounds only by the provided sound_natural_phrase, never by any other name.",
        "- No meta-words: do not mention 'annotation', 'timeline', 'label', 'memory', 'fact'.",
        "- For subtype easy_sound the ANSWER IS ITSELF A SOUND: ask which sound is heard",
        "  without naming, describing or hinting at any sound anywhere in the question.",
        "  (Wrong: 'You can hear X. Which sound is occurring?' — that gives X away.)",
        "- For subtypes high_order / medium_order, list three_actions_shuffled in the given",
        "  (shuffled) order, e.g. on a second line in parentheses.",
        "- For the spatial subtypes (reference_object present): the spatial relation is FIXED —",
        "  use exactly the given `relation` (closest / furthest) and the given reference_object.",
        "  Never substitute either, and never invert the relation.",
        "- For the spatial subtypes, never state or hint WHERE any candidate object is, and never",
        "  describe the layout of the room. The viewer must judge the distances from the clip.",
        "- For the spatial subtypes the question MUST keep the TIME ANCHOR, because objects are",
        "  moved during the clip and 'closest' is only defined at one instant:",
        "    easy_spatial_near  -> the moment the reference object is put down",
        "    low_spatial_near   -> the moment that sound is heard",
        "    medium/high spatial -> where things end up BY THE END of the clip.",
        "  'Which object is closest to the spoon?' is WRONG — the spoon itself moves in the clip.",
        "- For subtypes high_spatial_order / medium_spatial_order, list three_objects_shuffled in the",
        "  given (shuffled) order, e.g. on a second line in parentheses.",
        "- For the ego subtypes (ego_side present) the reference is THE CAMERA WEARER THEMSELF,",
        "  not any object: ask which option is furthest to their `ego_side` (left/right) at that",
        "  moment. Use exactly the given side — never flip it, never switch to another relation.",
        "  anchor_object, when given, only names the moment ('as they put down the X') — it is",
        "  never one of the options, so never imply the answer is near it.",
        "- For low_purpose / medium_purpose: identify the moment ONLY by the sound_natural_phrase and ask what the",
        "  camera wearer is trying to do at that moment. Never name or describe the action or the",
        "  object being handled, and never state or hint at the purpose.",
        "- For easy_goal, medium_goal and high_plan_next: never name, paraphrase or hint at any option; ask",
        "  about the overall activity (goal) or what comes next (plan).",
        "- For high_replan: start with 'The camera wearer is working on: <goal>.' when a goal is given, say that",
        "  something does not go as planned in the clip WITHOUT describing what, and ask what they should do right",
        "  after the clip ends. Never name any action or object from the options.",
        "- For high_plan_trajectory the question is the given `goal` sentence verbatim; write nothing else.",
        "- For high_plan_next_step: start with 'The camera wearer is working on: <goal>' using the given `goal`",
        "  verbatim, then ask what they should do next right after the clip ends. Never name any step.",
        "- For high_plan_next_action: start with 'The camera wearer is working on: <goal>.' using the given",
        "  `goal` verbatim, then ask what they are going to do right after the clip ends. Never name,",
        "  paraphrase or hint at any action or object from the options.",
        "- For packets with two_scenes = true: begin with the given scene_intro sentence verbatim",
        "  and ask about the END of the second scene.",
        "- For high_plan_route the options are the four fixed quadrants relative to the wearer's facing",
        "  direction (left-front / left-back / right-front / right-back); never describe where anything is.",
        "- For high_gaze_destination: say that the clip ends while the camera wearer is holding the",
        "  given `object`, and ask where they are about to put it down. Never name any location.",
        "- For high_gaze_pickup: ask which object they are about to pick up right after the clip",
        "  ends. Never name or describe any object, and never say where they are looking.",
        "- One natural, self-contained question per packet, answerable from the clip alone.",
        "",
        "Style examples from earlier levels of this benchmark:",
        json.dumps(ex, ensure_ascii=False),
    ]
    if summary:
        agents = ", ".join(summary.get("agents", []))
        lines += [
            "",
            f"Adaptation context: the evaluated agent(s) ({agents}) just took the previous",
            f"level and scored {summary['n_correct']}/{summary['n']}. Per-category accuracy:",
            json.dumps(summary.get("by_subtype", {}), ensure_ascii=False),
        ]
        missed = summary.get("missed_examples", [])
        if missed:
            lines += [
                "Examples the agent(s) got wrong:",
                json.dumps(missed[:6], ensure_ascii=False),
                "Phrase the new questions in the styles the agent(s) found hard (indirect",
                "reference, paraphrase, requiring combining several moments) — but never",
                "change any fact, answer, or distractor.",
            ]
        else:
            lines.append("The agent(s) made no errors: keep the same difficulty and style.")
    lines += [
        "",
        "Fact packets:",
        json.dumps([_fact_packet(f) for f in facts], ensure_ascii=False, indent=1),
        "",
        'Return a JSON array, one object per packet, in the same order:',
        '[{"fact_id": "...", "question": "...", "answer_echo": "<copy of correct_answer>"}]',
    ]
    return "\n".join(lines)


def _norm_echo(s):
    """回显只用来防张冠李戴(选项里的 gold 永远取自程序),
    所以箭头写法/空格/大小写/句末标点的差异不该算失败 ——
    逐字符比较实测把 High 层 94% 的候选误杀了。"""
    s = (s or "").strip().lower()
    for arrow in ("\u2192", "\u2014>", "\u2013>", "=>"):
        s = s.replace(arrow, "->")
    s = re.sub(r"\s*->\s*", " -> ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .;")


def _cache_key(fact, summary_sha):
    return hashlib.sha256(
        f"{fact['fact_id']}|{summary_sha}|{PROMPT_VERSION}".encode()).hexdigest()[:24]


def phrase_facts(facts, summary=None, offline=False):
    """返回 {fact_id: {"question","phrasing","phrasing_model"}}。失败的条目不在返回里
    (调用方决定是否模板回退)。"""
    P.ensure_dirs()
    summary_sha = (summary or {}).get("summary_sha", "none")
    out, todo = {}, []
    for f in facts:
        if offline:
            out[f["fact_id"]] = {"question": offline_question(f),
                                 "phrasing": "template", "phrasing_model": None}
            continue
        cf = P.CACHE / (_cache_key(f, summary_sha) + ".json")
        if cf.exists():
            out[f["fact_id"]] = json.loads(cf.read_text())
        else:
            todo.append(f)
    import time
    n_batches = -(-len(todo) // P.PHRASE_BATCH)
    for i in range(0, len(todo), P.PHRASE_BATCH):
        batch = todo[i:i + P.PHRASE_BATCH]
        tier = batch[0]["tier"]
        t0 = time.time()
        try:
            raw, mid = gemini_io.gen(_build_prompt(tier, batch, summary))
            items = gemini_io.jparse(raw) or []
        except RuntimeError as e:
            print(f"  [phrase] 批次失败: {e}", flush=True)
            continue
        print(f"  [phrase] {tier} 批 {i // P.PHRASE_BATCH + 1}/{n_batches} "
              f"({mid}, {time.time() - t0:.0f}s, 收到 {len(items)})", flush=True)
        got = {it.get("fact_id"): it for it in items if isinstance(it, dict)}
        drop = {"missing": 0, "echo": 0}
        for f in batch:
            it = got.get(f["fact_id"])
            if not it or not (it.get("question") or "").strip():
                drop["missing"] += 1
                continue
            if _norm_echo(it.get("answer_echo")) != _norm_echo(f["gold"]):
                drop["echo"] += 1             # 回显对不上 -> 措辞可能张冠李戴,弃
                continue
            rec = {"question": it["question"].strip(),
                   "phrasing": "gemini", "phrasing_model": mid}
            (P.CACHE / (_cache_key(f, summary_sha) + ".json")).write_text(
                json.dumps(rec, ensure_ascii=False))
            out[f["fact_id"]] = rec
        if drop["missing"] or drop["echo"]:
            print(f"    [phrase] 该批丢弃 {drop} (共 {len(batch)})", flush=True)
    return out
