"""让 Gemini 给非单选格式写题面(2026-09-29 用户决定:五种格式都由 Gemini 措辞)。

要写的东西:
- yn:一条陈述(把候选断言为答案;Gemini 不知道真假)
- ms:四条陈述,每条一个 (fact, cand) 包,单独改写
- open / open_x:题干(输出格式那句话由程序固定追加);tf4 / tf4_x 沿用单选的 Gemini 题干,不另写
每次调用 10 个包;结果按 sha(包|版本) 缓存;过不了 formats.check 的包回退模板并计数。

    GEMINI_API_KEY=... python3 phrase_formats.py --levels 1 2 3 4          # 读 sets/formats,写 sets/formats_gem
"""
import argparse, collections, hashlib, json, re, time
import pconfig as P
import config as C
import gemini_io
import formats as FM
import verify as V
from timeline_index import TimelineIndex

VERSION = "f1"
BATCH = 10
FORMAT_HINT = {   # open 题干后固定追加的输出格式句(与 formats.open_question 一致)
    "COUNT": "Answer with a single integer.",
    "ORDER": "List all three in order, separated by ' -> '.",
    "OBJECT": "Answer with the name of the object.",
    "NEAREST": "Answer with the name of the object.",
    "PURPOSE": "Answer in one short, direct phrase starting with 'to'.",
    "GOAL": "Answer in one short, direct phrase.",
    "ROUTE": "Answer with exactly one of: left-front, left-back, right-front, right-back.",
    "ACTION": "Answer with a short verb phrase, e.g. 'open the drawer'.",
    "REPLAN": "Answer with a short verb phrase, e.g. 'open the drawer'.",
    "STEP": "Answer with a short phrase naming the action and the object.",
}
_IX = {}
_FACTS = {}


def ix_of(v):
    if v not in _IX:
        _IX[v] = TimelineIndex(v)
    return _IX[v]


def _packet(kind, fact, cand=None, template=None):
    p = {"kind": kind, "subtype": fact["subtype"], "clip_length_sec": 30,
         "template_wording": template}
    if fact.get("_sound_label"):
        p["sound_natural_phrase"] = C.SOUND_PHRASE.get(fact["_sound_label"], "")
    for k in ("_ref", "_anchor", "_mode", "_from", "_to", "_object"):
        if fact.get(k):
            p[k.strip("_")] = fact[k]
    if kind == "statement":
        p["candidate"] = cand
        p["other_candidates_never_mention"] = [c for c in [fact["gold"]] + list(fact["distractors"]) if c != cand]
    else:
        p["correct_answer_never_mention"] = fact["gold"]
        p["wrong_options_never_mention"] = list(fact["distractors"])
    return p


def _prompt(packets):
    return "\n".join([
        "You rewrite questions for an audio-visual benchmark over 30-second first-person kitchen clips.",
        "Each packet below has a `kind`:",
        "- kind = statement: write ONE declarative sentence that asserts `candidate` as the answer to the",
        "  situation described by `template_wording`. Keep every time anchor (the sound, 'when X is put",
        "  down', 'by the end of the clip'). Mention `candidate` verbatim. Never mention any of",
        "  `other_candidates_never_mention`, and never hint whether the sentence is true.",
        "- kind = open_stem: write ONE self-contained question with no options, answerable from the clip",
        "  alone, with the same meaning as `template_wording`. Never write 'which of these / the following'.",
        "  Never mention `correct_answer_never_mention` or any of `wrong_options_never_mention`.",
        "  Do not add an output-format instruction; it is appended by the program.",
        "Common rules: refer to sounds only by `sound_natural_phrase`; keep the given left/right side and",
        "the given reference object; for two-scene clips keep the two-scene wording; no words such as",
        "'annotation', 'label', 'timeline', 'fact'. Vary the phrasing from the template.",
        "",
        "Packets:",
        json.dumps(packets, ensure_ascii=False, indent=1),
        "",
        'Return a JSON array, one object per packet, same order: [{"id": "...", "text": "..."}]',
    ])


def _cache_path(key):
    d = P.CACHE.parent / "phrasing_formats"
    d.mkdir(parents=True, exist_ok=True)
    return d / (key + ".json")


def phrase_packets(packets):
    """packets: {id: packet}. 返回 {id: text}(失败的不在返回里)。"""
    out, todo = {}, []
    for pid, pk in packets.items():
        key = hashlib.sha256(f"{pid}|{json.dumps(pk, sort_keys=True)}|{VERSION}".encode()).hexdigest()[:24]
        cf = _cache_path(key)
        if cf.exists():
            out[pid] = json.loads(cf.read_text())["text"]
        else:
            todo.append((pid, pk, cf))
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        try:
            raw, mid = gemini_io.gen(_prompt([dict(pk, id=pid) for pid, pk, _ in batch]), role="generator")
        except RuntimeError as e:
            print(f"  [phrase_formats] 批次失败: {e}", flush=True); continue
        got = {it.get("id"): (it.get("text") or "").strip() for it in (gemini_io.jparse(raw) or []) if isinstance(it, dict)}
        for pid, pk, cf in batch:
            if got.get(pid):
                cf.write_text(json.dumps({"text": got[pid], "model": mid}, ensure_ascii=False))
                out[pid] = got[pid]
    return out


def _facts_for(level):
    """题套里每道题的 fact(基题 fact_id -> 从 assemble_formats 的来源重建:题里自带 gold/干扰项/字段)。"""
    return None


def process_level(level, src_dir, out_dir, stats):
    sets = {slot: json.loads((src_dir / f"L{level}_{slot}.json").read_text()) for slot in ("yn", "ms", "open", "open_x")}
    # 一道题的 fact 字段:题里已经带了 gold / 干扰项 / _sound_label 等;statement() 需要的额外字段从题里取
    def fact_of(q):
        # 题里没有 _anchor / _ref / _mode 这些模板字段:优先从 facts 缓存按 fact_id 取整条 fact
        f = dict(_FACTS.get(q["fact_id"]) or {})
        f.update({k: q[k] for k in q if k.startswith("_") or k in ("subtype", "kind", "video_id", "t0", "t1", "fact_id",
                                                                   "evidence_event_ids", "evidence_t", "windows")})
        f["gold"], f["distractors"] = q["answer"], list(q["_distractors"])
        return f
    packets, where = {}, {}
    for q in sets["yn"]["questions"]:
        f = fact_of(q)
        pid = f"{q['question_id']}"
        packets[pid] = _packet("statement", f, q["_yn_cand"], FM.statement(f, q["_yn_cand"]))
        where[pid] = ("yn", q, None)
    for q in sets["ms"]["questions"]:
        for i, sr in enumerate(q["_stmt_src"]):
            if sr["fact_id"].startswith("win_sound:"):
                continue                      # 窗口声音补充陈述:保持模板
            f = fact_of(q) if sr["fact_id"] == q["fact_id"] else None
            if f is None:
                continue                      # 兄弟 fact 的字段不在题里,保持模板
            pid = f"{q['question_id']}#{i}"
            packets[pid] = _packet("statement", f, sr["cand"], q["statements"][i][3:])
            where[pid] = ("ms", q, i)
    for q in sets["open"]["questions"]:
        if q["fmt"] != "open":
            continue
        f = fact_of(q)
        pid = q["question_id"]
        tmpl = re.sub(r"\s*(Answer with|List all three|Answer in one).*$", "", q["question"])
        packets[pid] = _packet("open_stem", f, template=tmpl)
        where[pid] = ("open", q, None)
    t0 = time.time()
    texts = phrase_packets(packets)
    stats["packets"] += len(packets); stats["got"] += len(texts); stats["sec"] += time.time() - t0
    # 回填 + 校验
    open_x = {q["question_id"].replace("#open_x", "#open"): q for q in sets["open_x"]["questions"]}
    for pid, (slot, q, i) in where.items():
        if pid not in texts:
            stats["missing"] += 1; continue
        f = fact_of(q); ix = ix_of(q["video_id"])
        trial = json.loads(json.dumps(q)); trial["phrasing"] = "gemini"
        if slot == "yn":
            trial["statement"] = texts[pid]; trial["question"] = texts[pid]
        elif slot == "ms":
            trial["statements"] = list(q["statements"]); trial["statements"][i] = f"{'ABCD'[i]}. {texts[pid]}"
            trial["question"] = "Which of these statements are true? " + " | ".join(trial["statements"])
        else:
            hint = FORMAT_HINT.get(q["kind"], "")
            if q["subtype"] in ("medium_purpose", "low_purpose"):
                hint = FORMAT_HINT["PURPOSE"]
            trial["question"] = texts[pid].rstrip() + " " + hint
        errs = V.check(ix, trial, f)
        if errs:
            stats["rejected"] += 1; stats["why"][errs[0][:30]] += 1; continue
        stats["accepted"] += 1
        q.update({k: trial[k] for k in ("statement", "statements", "question") if k in trial}); q["phrasing"] = "gemini"
        if slot == "open" and pid in open_x:
            qx = open_x[pid]; qx["question"] = trial["question"]; qx["phrasing"] = "gemini"
    out_dir.mkdir(parents=True, exist_ok=True)
    for slot, sd in sets.items():
        sd["phrasing"] = "gemini-formats " + VERSION
        sd["gemini_fraction"] = sum(q.get("phrasing") == "gemini" for q in sd["questions"]) / max(1, len(sd["questions"]))
        (out_dir / f"L{level}_{slot}.json").write_text(json.dumps(sd, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", nargs="+", type=int, default=[1, 2, 3, 4])
    ap.add_argument("--src", default=str(P.SETS / "formats"))
    ap.add_argument("--out", default=str(P.SETS / "formats_gem"))
    a = ap.parse_args()
    from pathlib import Path
    stats = collections.Counter(); stats["why"] = collections.Counter()
    import assemble_formats as AF
    _FACTS.update(AF.load_facts()[0])
    for L in a.levels:
        st = collections.Counter(); st["why"] = collections.Counter()
        process_level(L, Path(a.src), Path(a.out), st)
        print(f"L{L}: {dict((k, v) for k, v in st.items() if k != 'why')}", flush=True)
        stats.update({k: v for k, v in st.items() if k != "why"}); stats["why"].update(st["why"])
    print("合计:", dict((k, v) for k, v in stats.items() if k != "why"))
    print("拒因:", dict(stats["why"].most_common(8)))


if __name__ == "__main__":
    main()
