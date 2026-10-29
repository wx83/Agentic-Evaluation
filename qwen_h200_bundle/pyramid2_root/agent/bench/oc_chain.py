"""P03 bag of kale 的 OC-0..OC-7 八层链 -> _shared/chains_oc.json

Gold 全部来自 object_memory/P03-.../chunk_000 与 HD-EPIC P03 标注，逐条在
Question/object_centric_chain_P03_kale.json 里记了出处。这里只负责配干扰项、
打乱选项、写成 run_chains.py 能直接吃的格式，不做任何新的事实推断。
"""
import json, random, hashlib, argparse
import config as C

VIDEO = "P03-20240216-185832"
CHAIN = "P03_kale_oc"

# 两个证据窗口：物体在 0:11 出现，52 分钟后再出现。单窗口装不下这条链。
WINDOWS = [(0.0, 30.0), (3120.0, 3160.0)]

# OC-0 的 <REGION>：mask_info 里 bag_of_kale_01 的真实 bbox。
# 注意 gold 写的是「a bag of leafy greens」而不是「bag of kale」：全分辨率下框里只是
# 一只手抓着一袋透明塑料装的绿叶菜，同一画面右下角还有一袋一模一样的。kale 与 spring
# greens 在像素上不可分（memory 也把两者都记成 green plastic），把物种当 gold 等于出了
# 一道从画面推不出答案的题。下游各层改用回指「the bag you identified」，既不断言物种，
# 也顺带消掉了 <PREV> 字符串替换的指代漂移。
BOX = {"t": 11.433, "bbox_1408": [729.002, 823.746, 965.862, 1018.497], "color": "red"}

PREAMBLE = {
 "_default": (
    "This clip contains two excerpts from one continuous kitchen recording. Excerpt 1 is the "
    "first 30 seconds of the recording. Excerpt 2 begins 52 minutes later, at 52:00, and runs "
    "for 40 seconds. Report every Time: as a time in the ORIGINAL RECORDING (so a moment in "
    "excerpt 2 is around 52:0X), not as a position in this clip."),
 "memory": (
    "The notes below cover two excerpts from one continuous kitchen recording: 0:00-0:30 and "
    "52:00-52:40. Report every Time: as a time in the original recording."),
}

# tier, capability, 题面, gold, 三个干扰项, 证据绝对时刻, 证据 id, PREV 替换段
# prev_spans 是题面里由「上一层 agent 自己的答案」替换进来的片段。泄底闸门必须
# 先把它们抠掉再查 —— 否则每一条链都会被自己的设计判为泄底（build_bench.py:85 的原样就是如此）。
STEPS = [
 ("OC-0", "instance grounding",
  "A red box is drawn around one object at 0:11. Name the object inside it.",
  "a bag of leafy greens",
  ["a box of mushrooms", "a bunch of spring onion", "a cauliflower"],
  11.43, ["memory:object_memory[0].category", "mask:7377d7199fd74a2e"], [],
  {"memory": "At 0:11 the camera wearer picks something up with their left hand. Name it."}),

 ("OC-1", "immediate state recognition",
  "At 0:11, describe the state of the bag you identified on the single state dimension that "
  "its ongoing use makes relevant.",
  "inside the fridge bottom drawer, still full and intact",
  ["on the kitchen table", "held in the camera wearer's right hand",
   "on the floor in the large shopping bag"],
  11.43, ["memory:object_memory[0].current_state.spatial", "narration:10.76-12.07"], [], {}),

 ("OC-2", "state-transition recognition",
  "At 0:11 the bag you identified was <PREV:OC-1.state>. Play forward and report the first "
  "moment at which that no longer holds, and what it becomes.",
  "at about 0:14.6 it is placed on the table",
  ["at about 0:19, when it is pushed into the drawer",
   "at about 0:22, when it is put down on the floor",
   "it does not change within the excerpt"],
  14.63, ["narration:14.26-14.92", "movement:11.43-14.63"],
  [], {}),

 ("OC-3", "event ordering",
  "In the interval ending at <PREV:OC-2.time>, which object does the camera wearer set down or "
  "pick up immediately before touching the bag you identified?",
  "another bag of leafy greens, lifted from the shopping bag on the floor",
  ["the box of mushrooms", "the spring onion", "the fridge bottom drawer"],
  7.83, ["narration:7.47-8.19", "memory:object_memory[1]"], [], {}),

 ("OC-4", "long-video retrieval and location history",
  "Searching strictly before <PREV:OC-2.time>, at which fixture was the bag you identified "
  "resting the last time it was in the same place as <PREV:OC-3.object>, and roughly when?",
  "the fridge bottom drawer, at about 0:13.5",
  ["the kitchen table, at about 0:14.9",
   "the floor in the large shopping bag, at about 0:08",
   "they were never in the same place"],
  13.50, ["memory:object_memory[0].state_history[0]", "memory:object_memory[1].state_history[1]",
          "narration:11.99-13.62"],
  [], {}),

 ("OC-5", "causal attribution with contradiction detection",
  "Rustling of plastic is heard at 52:01. Is that consistent with the bag you identified being "
  "at <PREV:OC-4.fixture>, and what produced it?",
  "no - it has left the fridge; the rustle is the bag being taken from the table and pulled open "
  "on the way to the sink",
  ["yes - it is still in the drawer, and the rustle is the drawer being opened",
   "no - the rustle is a different plastic bag being emptied into the bin",
   "yes - the rustle is the bag settling in the drawer"],
  3124.50, ["sound:3121.07-3128.08", "narration:3120.61-3121.64", "narration:3121.64-3127.15"],
  [], {}),

 ("OC-6", "counterevidence checking",
  "Without reusing any time you have already named, is there a further interval anywhere in the "
  "recording in which the bag you identified is at <PREV:OC-4.fixture>?",
  "no - it is at the fridge only once and never returns, so the earlier answer is unsupported "
  "as a general location",
  ["yes - from about 52:01 to 52:35, at the sink",
   "yes - shortly after 0:19, when the drawer is pushed shut",
   "yes - at about 52:35, when it is put back"],
  3138.40, ["assoc:tracks=[[11.43,14.63],[3121.07,3155.67]]", "narration:3155.03-3155.94"],
  [], {}),

 ("OC-7", "information-gathering action selection",
  "Your last answer leaves the fate of the bag you identified undetermined. Which single action "
  "would settle it, and what would you expect to find?",
  "open the soft-plastic recycling bin - the bag should be inside, emptied and crumpled into a ball",
  ["re-watch the excerpt from the start",
   "open the fridge bottom drawer - the bag should still be inside",
   "look in the plastic colander - the bag should be inside it"],
  3155.48, ["narration:3148.94-3150.79", "narration:3150.40-3152.22", "narration:3155.03-3155.94"],
  [], {}),
]


# 选项 -> 它向下游发射的字段值。agent 选了哪个，下一层的题面就用哪个渲染 ——
# 这是「上一层答错，下一层就在错误前提上作答」得以成立的地方。
EMIT = {
 "OC-1": {o: {"state": o} for o in [
    "inside the fridge bottom drawer, still full and intact", "on the kitchen table",
    "held in the camera wearer's right hand", "on the floor in the large shopping bag"]},
 "OC-2": {
    "at about 0:14.6 it is placed on the table":        {"time": "0:14.6", "state": "on the table"},
    "at about 0:19, when it is pushed into the drawer": {"time": "0:19",   "state": "in the drawer"},
    "at about 0:22, when it is put down on the floor":  {"time": "0:22",   "state": "on the floor"},
    "it does not change within the excerpt":            {"time": "0:30",   "state": "unchanged"}},
 "OC-3": {o: {"object": o} for o in [
    "another bag of leafy greens, lifted from the shopping bag on the floor",
    "the box of mushrooms", "the spring onion", "the fridge bottom drawer"]},
 "OC-4": {
    "the fridge bottom drawer, at about 0:13.5":            {"fixture": "the fridge bottom drawer"},
    "the kitchen table, at about 0:14.9":                   {"fixture": "the kitchen table"},
    "the floor in the large shopping bag, at about 0:08":   {"fixture": "the floor, in the large shopping bag"},
    "they were never in the same place":                    {"fixture": "no shared location"}},
}


def shuffled(gold, distr, qid, salt=0):
    """与 build_bench.py 同一套：qid 的 sha256 决定顺序，可复现且与内容无关。
    salt 只用于位置均衡，不参与任何与内容相关的判断。"""
    opts = [gold] + list(distr)
    rng = random.Random(int(hashlib.sha256(f"{qid}#{salt}".encode()).hexdigest()[:8], 16))
    rng.shuffle(opts)
    return [f"{'ABCD'[i]}. {o}" for i, o in enumerate(opts)], opts.index(gold)


def balanced_shuffle(gold, distr, qid, counts):
    """位置均衡：把本题的 gold 放到目前用得最少的那个位置上。
    实测教训 —— Qwen 在第一轮里 8 题只答过 C 和 D，一次 A/B 都没选。若 gold 恰好偏在 C/D，
    单靠正确率根本分不出「答对」和「押对位置」。0830.md 的 balance_gold_positions 就是为这个。"""
    # 并列时按 qid 的哈希取舍，不按下标 —— 否则 gold 会排成 A,B,C,D,A,B,C,D 的规则循环，
    # 位置直方图漂亮了，但换成了另一种同样可利用的模式。
    def tie(i):
        return int(hashlib.sha256(f"{qid}~{i}".encode()).hexdigest()[:8], 16)
    want = min(range(4), key=lambda i: (counts[i], tie(i)))
    for salt in range(2000):
        opts, gi = shuffled(gold, distr, qid, salt)
        if gi == want:
            counts[gi] += 1
            return opts, gi, salt
    opts, gi = shuffled(gold, distr, qid, 0)
    counts[gi] += 1
    return opts, gi, 0


def build():
    steps, seen, gold_slots = [], set(), {}
    pos_counts = [0, 0, 0, 0]
    for i, (tier, cap, q, gold, distr, ev_t, eids, prev_spans, by_mode) in enumerate(STEPS):
        qid = f"{CHAIN}_{tier}"
        assert len(distr) == 3 and gold not in distr, tier
        assert len(set(distr)) == 3, f"{tier} 干扰项重复"
        opts, gi, salt = balanced_shuffle(gold, distr, qid, pos_counts)
        # 用 gold 渲染一版题面：只用于泄底校验与人工阅读，跑的时候按 agent 的实际答案重渲
        q_gold = q
        subbed = []
        for tok, val in gold_slots.items():
            if tok in q_gold:
                q_gold = q_gold.replace(tok, val)
                subbed.append(val)
        prev_spans = list(prev_spans) + subbed
        assert "<PREV:" not in q_gold, f"{tier} 有槽位没填上: {q_gold}"
        # 层间不泄底 —— 修正版闸门：先抠掉 PREV 替换段，再查其余部分。
        # build_bench.py:85 的原写法（整句直接查）会把每一条链都判为泄底。
        masked = q_gold.lower()
        for span in prev_spans:
            assert span.lower() in masked, f"{tier} 声明的 PREV 段不在题面里: {span}"
            masked = masked.replace(span.lower(), " ")
        for prev in steps:
            assert prev["answer"].lower() not in masked, f"{tier} 泄底: {prev['answer']}"
            for o in prev["_distractors"]:
                assert o.lower() not in masked, f"{tier} 泄了 {prev['tier']} 的干扰项: {o}"
        assert not any(w in q.lower() for w in ("recycling", "colander")) or tier == "OC-7"
        steps.append({
            "question_id": qid, "tier": tier,
            "question": q_gold,               # gold 渲染版（兼容 & 人工阅读）
            "question_template": q,           # 真正要跑的：带 <PREV:...> 槽位
            "emit": EMIT.get(tier, {}),       # 选项 -> 下游字段值
            "answer": gold,
            "options": opts, "correct_option": "ABCD"[gi], "_gold_idx": gi,
            "kind": "OBJECT", "_capability": cap, "_distractors": distr, "_salt": salt,
            "evidence_event_ids": eids, "evidence_t": ev_t, "_prev_spans": prev_spans,
            "question_by_mode": by_mode,
            "_window": 0 if ev_t <= WINDOWS[0][1] else 1,
        })
        seen.add(gold)
        for f, v in EMIT.get(tier, {}).get(gold, {}).items():
            gold_slots[f"<PREV:{tier}.{f}>"] = v
    assert len(seen) == 8, "层间 gold 重复"
    chain = {
        "chain_id": CHAIN, "video_id": VIDEO,
        "windows": [list(w) for w in WINDOWS],
        "region_box": BOX, "preamble_by_mode": PREAMBLE,
        # 兼容既有 runner 的字段：clip=第一窗口，long=第二窗口
        "clip_start": WINDOWS[0][0], "clip_end": WINDOWS[0][1],
        "long_start": WINDOWS[1][0], "long_end": WINDOWS[1][1],
        "needle_position": 0.0,
        "steps": steps,
    }
    return chain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="chains_oc.json")
    a = ap.parse_args()
    c = build()
    C.SHARED.mkdir(parents=True, exist_ok=True)
    p = C.SHARED / a.out
    p.write_text(json.dumps(
        {"video_id": VIDEO, "n_chains": 1, "taxonomy": "object_centric.json v1.1",
         "templates": "Question/object_centric_templates.json v0.2",
         "gold_provenance": "Question/object_centric_chain_P03_kale.json",
         "windows": [list(w) for w in WINDOWS],
         "size": C.SIZE, "fps": C.FPS, "chains": [c]}, ensure_ascii=False, indent=1))
    print(f"写出 1 条 8 层链 -> {p}")
    hist = [s["_gold_idx"] for s in c["steps"]]
    h = [hist.count(i) for i in range(4)]
    print("gold 位置分布 A/B/C/D:", h, "最大偏差", max(h) - min(h))
    assert max(h) - min(h) <= 1, "位置不均衡，整轮结果不可解读"
    for s in c["steps"]:
        print(f"  {s['tier']}  gold={s['correct_option']}  ev_t={s['evidence_t']:8.2f}  w{s['_window']}  {s['answer'][:46]}")


if __name__ == "__main__":
    main()
