"""组卷:按自适应权重选事实 -> 措辞 -> 校验 -> 裁到恰好 100 题 -> gold 位置精确均衡。

- 选材权重来自上一层 summary 的 selection_weights(subtype/video/sound 三个维度相乘),
  绝不改 gold —— 自适应只决定挑哪些事实、怎么措辞。
- 事实复用登记:同一座金字塔(arm|scope)内每条 fact 只用一次;跨金字塔全局上限
  pconfig.FACT_REUSE_MAX 次。
- gold 位置:按 sha256(question_id) 排序后轮转分配 0..3,直方图精确 25/25/25/25。
- 校验失败只丢弃;Gemini 措辞失败回退模板(标记并限比例)。
"""
import json, hashlib, random, argparse
import pconfig as P
import memory as MEM
import facts as F
import phrase as PH
import verify as V
import curate as CU
from timeline_index import TimelineIndex

_IX = {}


def ix_of(video):
    if video not in _IX:
        _IX[video] = TimelineIndex(video)
    return _IX[video]


def _usage():
    f = P.DATA / "usage.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"fact_use": {}, "pyramid_used": {}}


def _save_usage(u):
    (P.DATA / "usage.json").write_text(json.dumps(u, ensure_ascii=False))


def _eligible(pool, arm, scope, usage):
    key = f"{arm}|{scope}"
    used_here = set(usage["pyramid_used"].get(key, []))
    return [f for f in pool
            if f["fact_id"] not in used_here
            and f["subtype"] not in P.EXCLUDE_SUBTYPES
            and usage["fact_use"].get(f["fact_id"], 0) < P.FACT_REUSE_MAX]


def _weighted_order(cands, summary, seed_str):
    """Efraimidis-Spirakis:按 u^(1/w) 排序 = 不放回加权采样的顺序。"""
    w_sub = (summary or {}).get("selection_weights", {}).get("subtype", {})
    w_vid = (summary or {}).get("selection_weights", {}).get("video", {})
    w_snd = (summary or {}).get("selection_weights", {}).get("sound", {})
    rng = random.Random(seed_str)
    keyed = []
    for f in cands:
        w = (w_sub.get(f["subtype"], 1.0) * w_vid.get(f["video_id"], 1.0) *
             w_snd.get(f.get("_sound_label") or "", 1.0))
        keyed.append((rng.random() ** (1.0 / max(w, 1e-6)), f))
    keyed.sort(key=lambda kv: -kv[0])
    return [f for _, f in keyed]


def _mix_subtypes(ordered, summary, seed_str):
    """按 subtype 加权轮流取,防止某个子类(如 easy_sound 池最大)独占整套题。
    子类内部保持 _weighted_order 给出的顺序,权重仍来自自适应 summary。"""
    by = {}
    for f in ordered:
        by.setdefault(f["subtype"], []).append(f)
    if len(by) <= 1:
        return ordered
    w = (summary or {}).get("selection_weights", {}).get("subtype", {})
    rng = random.Random(seed_str + "|mix")
    out = []
    while by:
        subs = list(by)
        s = rng.choices(subs, [w.get(x, 1.0) for x in subs])[0]
        out.append(by[s].pop(0))
        if not by[s]:
            del by[s]
    return out


def wins_of(f):
    """一题的证据窗口列表。跨场景题有两段(windows),其 t0/t1 只是总跨度、不代表证据范围。"""
    return [tuple(w) for w in f["windows"]] if f.get("windows") else [(f["t0"], f["t1"])]


def overlaps(f, kept_ws):
    return any(min(b1, b2) - max(a1, a2) >= P.WIN_SEC / 2
               for a1, b1 in wins_of(f) for a2, b2 in kept_ws)


def _dedupe_windows(ordered):
    """同层同视频窗口重叠 >=50%(15s)的只留先选中的。生成器,保持顺序。
    跨场景题逐段比较 —— 用总跨度比会把几分钟内的所有题都判成重叠。"""
    kept = {}
    for f in ordered:
        ws = kept.setdefault(f["video_id"], [])
        if overlaps(f, ws):
            continue
        ws.extend(wins_of(f))
        yield f


def _make_item(fact, question, qid, gold_idx, phrasing, phrasing_model, note=None):
    rng = random.Random(qid)
    opts_body = [None] * 4
    opts_body[gold_idx] = fact["gold"]
    rest = [i for i in range(4) if i != gold_idx]
    ds = fact["distractors"][:]
    rng.shuffle(ds)
    for i, d in zip(rest, ds):
        opts_body[i] = d
    memtext, _ = MEM.render(ix_of(fact["video_id"]), fact["t0"], fact["t1"])
    return {
        "question_id": qid, "tier": fact["tier"], "subtype": fact["subtype"],
        "kind": fact["kind"], "video_id": fact["video_id"],
        "t0": fact["t0"], "t1": fact["t1"],
        "question": question, "answer": fact["gold"],
        "options": [f"{'ABCD'[i]}. {b}" for i, b in enumerate(opts_body)],
        "correct_option": "ABCD"[gold_idx], "_gold_idx": gold_idx,
        "_distractors": fact["distractors"], "_sound_label": fact["_sound_label"],
        "evidence_event_ids": fact["evidence_event_ids"], "evidence_t": fact["evidence_t"],
        "fact_id": fact["fact_id"], "phrasing": phrasing, "phrasing_model": phrasing_model,
        "memory_sha": hashlib.sha256(memtext.encode()).hexdigest()[:16],
        # 选题器给的「针对哪条弱点」;只入档审计,评测 prompt 只用 question/options
        **({"curation_note": note} if note else {}),
        # 跨场景题:evaluate 据此拼接两段 30 s 作为输入
        **({"windows": fact["windows"]} if fact.get("windows") else {}),
        # clip 模式:这题属于哪个 clip(窗口即 clip 窗口;L4 保留原窗口,只标归属)
        **({"clip_id": fact["clip_id"], "clip_window": fact["clip_window"]} if fact.get("clip_id") else {}),
    }


def build_set(arm, scope, level, summary=None, offline=False, n_target=None,
              select="program"):
    """生成 sets/<arm>/<scope>/L<level>.json,返回其路径。幂等:已存在直接返回。"""
    P.ensure_dirs()
    n_target = n_target or P.N_TARGET
    outdir = P.SETS / arm / scope
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"L{level}.json"
    if out.exists():
        return out

    tier = P.TIER_OF_LEVEL[level]
    usage = _usage()
    pool = _eligible(F.load_all()[tier], arm, scope, usage)
    if P.CLIPS:                                   # clip 模式:只留落在指定 clip 里的事实,窗口改成 clip 窗口
        import clip_pyramid as CP
        pool = CP.restrict(pool, tier)
    seed_str = f"{P.SEED}|{arm}|{scope}|L{level}"
    mixed = _mix_subtypes(_weighted_order(pool, summary, seed_str), summary, seed_str)
    # 选题器只**重排**候选(Gemini 按层间 memory 挑,或启发式);gold / 措辞 / 校验链不动。
    # 去窗口重叠放在重排之后:同一窗口的关系变体都要进候选,才谈得上「挑问哪种关系」。
    mixed, notes, selection, audit = CU.order(mixed, summary, level, n_target, select,
                                              offline, ix_of)
    # clip 模式下同一 clip 的题本来就同窗口,窗口去重会把每个 clip 砍到只剩 1 题
    ordered = list(mixed) if P.CLIPS else list(_dedupe_windows(mixed))

    kept, rejected, n_template = [], [], 0
    i = 0
    while len(kept) < n_target and i < len(ordered):
        # 按还缺多少取材(留 40% 拒绝余量),不要一上来就把 140 条全送去措辞
        need = n_target - len(kept)
        take = max(P.PHRASE_BATCH,
                   -(-int(need * 1.4) // P.PHRASE_BATCH) * P.PHRASE_BATCH)
        batch = ordered[i:i + min(take, P.N_REQUEST)]
        i += len(batch)
        phrased = PH.phrase_facts(batch, summary=summary, offline=offline)
        for f in batch:
            if len(kept) >= n_target:
                break
            rec = phrased.get(f["fact_id"])
            if rec is None:                       # Gemini 失败 -> 模板回退(限比例)
                if n_template >= P.TEMPLATE_FRAC_MAX * n_target:
                    rejected.append({"fact_id": f["fact_id"], "errors": ["措辞失败且模板配额用尽"]})
                    continue
                rec = {"question": PH.offline_question(f),
                       "phrasing": "template", "phrasing_model": None}
            qid = f"pyr_{arm}_{scope}_L{level}_{len(kept):03d}"
            item = _make_item(f, rec["question"], qid, 0, rec["phrasing"], rec["phrasing_model"],
                              notes.get(f["fact_id"]))
            errs = V.check(ix_of(f["video_id"]), item, f)
            if errs and rec["phrasing"] == "gemini":
                # Gemini 措辞被拒,再试模板一次(gold 不变,只有题面换)
                if n_template < P.TEMPLATE_FRAC_MAX * n_target:
                    item2 = _make_item(f, PH.offline_question(f), qid, 0, "template", None,
                                       notes.get(f["fact_id"]))
                    errs2 = V.check(ix_of(f["video_id"]), item2, f)
                    if not errs2:
                        rejected.append({"fact_id": f["fact_id"], "question": item["question"],
                                         "errors": errs, "note": "Gemini 措辞被拒,已回退模板"})
                        item, errs = item2, []
            if errs:
                rejected.append({"fact_id": f["fact_id"], "question": item["question"],
                                 "errors": errs})
                continue
            if item["phrasing"] == "template":
                n_template += 1
            kept.append((f, item))

    if len(kept) < n_target:
        print(f"  [assemble] 警告:{arm}/{scope}/L{level} 池耗尽,只有 {len(kept)} 题", flush=True)

    # gold 位置精确均衡:先按子类分组(组内按 sha 排序)再整体轮转 0..3,再重建选项。
    # 只做全局均衡不够:被测 agent 有位置偏好(gemini 避 A、qwen 偏 A,seed42 的 1200 题可见),
    # 某子类的 gold 若碰巧堆在 A,该子类正确率就被系统性压低 —— 而自适应会把这个假象
    # 当成「该题族弱」继续放大(pilot 实测:L1 ego 3/3 gold 在 A,非 spatial 0/13 在 A)。
    # 分组后轮转:全局仍精确 25/25/25/25,每个子类内部各位置相差不超过 1。
    kept.sort(key=lambda fi: (fi[0]["subtype"],
                              hashlib.sha256(fi[1]["question_id"].encode()).hexdigest()))
    final = []
    for j, (f, item) in enumerate(kept):
        final.append(_make_item(f, item["question"], item["question_id"], j % 4,
                                item["phrasing"], item["phrasing_model"],
                                notes.get(f["fact_id"])))
    hist = [sum(1 for it in final if it["_gold_idx"] == g) for g in range(4)]
    hist_by_sub = {st: [sum(1 for it in final if it["subtype"] == st and it["_gold_idx"] == g)
                        for g in range(4)] for st in sorted({it["subtype"] for it in final})}

    key = f"{arm}|{scope}"
    usage["pyramid_used"].setdefault(key, []).extend(it["fact_id"] for it in final)
    for it in final:
        usage["fact_use"][it["fact_id"]] = usage["fact_use"].get(it["fact_id"], 0) + 1
    _save_usage(usage)

    import config as C
    data = {"arm": arm, "scope": scope, "level": level, "tier": tier, "n": len(final),
            "seed": P.SEED, "offline": offline,
            "generator": {"model": C.GEMINI_MODEL, "fallbacks": C.GEMINI_FALLBACKS,
                          "prompt_version": PH.PROMPT_VERSION},
            "adapted_from": {"level": level - 1, "summary_sha": summary["summary_sha"]}
                            if summary else None,
            "gold_position_hist": hist,
            "gold_position_by_subtype": hist_by_sub,
            "selection": selection,
            "subtype_counts": {st: sum(it["subtype"] == st for it in final)
                               for st in sorted({it["subtype"] for it in final})},
            "n_rejected": len(rejected),
            "template_fraction": round(sum(it["phrasing"] == "template" for it in final)
                                       / max(len(final), 1), 3),
            "per_video_counts": {v: sum(it["video_id"] == v for it in final)
                                 for v in P.VIDEOS},
            "questions": final}
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    (outdir / f"L{level}_rejected.json").write_text(
        json.dumps(rejected, ensure_ascii=False, indent=1))
    if audit:
        audit["kept_fact_ids"] = [it["fact_id"] for it in final]
        (outdir / f"L{level}_curation.json").write_text(
            json.dumps(audit, ensure_ascii=False, indent=1))
    print(f"  [assemble] {arm}/{scope}/L{level}: {len(final)} 题 "
          f"(拒 {len(rejected)},模板 {data['template_fraction']:.0%}) -> {out}", flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=P.ARMS)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--level", type=int, required=True, choices=[1, 2, 3, 4])
    ap.add_argument("--summary", help="上一层 summary json 路径")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--n", type=int, default=0, help="题数(默认 100;冒烟测试用小值)")
    ap.add_argument("--select", default="program", choices=P.SELECT_MODES)
    a = ap.parse_args()
    s = json.loads(open(a.summary).read()) if a.summary else None
    build_set(a.arm, a.scope, a.level, summary=s, offline=a.offline,
              n_target=a.n or None, select=a.select)
