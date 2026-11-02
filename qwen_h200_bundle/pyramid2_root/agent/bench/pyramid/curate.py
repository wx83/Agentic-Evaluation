"""选题器:按层间 memory(上一层作答摘要)决定下一层**考哪些事实**。gold 仍由程序推出。

分工:
- 程序:挖事实(facts.py)、给每条事实算难度特征、定 gold、verify 在窗口上重推。
- Gemini:读上一层的错题画像,从候选卡片里挑出下一层该考的,并写一句「针对哪条弱点」。
- 护栏:Gemini 的输出一律当**提议**,由程序裁定(幻觉 id、单一子类独大、gold 取值集中、
  窗口重叠),不足部分用程序顺序补齐。

为什么需要它:adapt.py 的 selection_weights.subtype 以**上一层**的子类名为键,而下一层
候选是另一个 tier 的子类,assemble._weighted_order 里 w_sub.get(subtype) 永远查不到 ——
子类维自适应跨层从未生效。「L1 的 ego 题错得多 -> L2 多考 ego」这种语义映射,
要么靠题族对照(pconfig.SUBTYPE_FAMILY,启发式选题器用它),要么交给 Gemini。

卡片里**不给 gold**:选题只决定考什么技能、多难,不该看着答案挑。
"""
import json, hashlib, math, collections
import pconfig as P
import config as C
import primitives as PRIM
import spatial as SP

FAM = P.SUBTYPE_FAMILY


# ---------- 难度特征(全部现算,与 verify 用的是同一套 derive_*) ----------

def _r2(x):
    return None if x is None else round(float(x), 2)


def features(ix, f):
    """一条事实「有多难」的程序化刻画。只描述题,不含答案。"""
    st, t0, t1 = f["subtype"], f["t0"], f["t1"]
    out = {}
    try:
        if st == "easy_spatial_near":
            r = SP.derive_l1(ix, ix.ev(f["_ref_eid"]), t0, t1)
            out = {"d_gold_m": _r2(r["d_gold"]), "margin_m": _r2(r["present"][0][0] - r["d_gold"])}
        elif st == "low_spatial_near":
            r = SP.derive_l2(ix, ix.ev(f["_ref_eid"]), t0, t1)
            out = {"d_gold_m": _r2(r["d_gold"]), "margin_m": _r2(r["present"][0][0] - r["d_gold"])}
        elif st == "medium_spatial_extreme":
            mode = f.get("_mode", "far")
            r = SP.derive_l3(ix, f["_ref"], t0, t1, mode)
            rk = r["ranked"]
            gap = (rk[-1][0] - rk[-2][0]) if mode == "far" else (rk[1][0] - rk[0][0])
            out = {"d_gold_m": _r2(r["d_gold"]), "margin_m": _r2(gap), "n_objects": len(rk)}
        elif st in ("high_spatial_order", "medium_spatial_order"):
            ds = f.get("_dists") or []
            if len(ds) == 3:
                out = {"margin_m": _r2(min(ds[1] - ds[0], ds[2] - ds[1]))}
        elif st in ("easy_spatial_side", "low_spatial_side"):
            mode = f.get("_mode", "right")
            r = SP.derive_ego_side(ix, ix.ev(f["_ref_eid"]), t0, t1, mode)
            k = (lambda c: c[1]) if mode == "right" else (lambda c: -c[1])
            s = sorted(r["cands"], key=k)
            out = {"margin_m": _r2(k(s[1]) - k(s[0])), "n_objects": len(s)}
        elif st == "medium_count":
            out = {"count": int(f["gold"])}
        elif st in ("medium_purpose", "low_purpose"):
            out = {"hard_negatives": f.get("_n_hard", 0)}
        elif st == "high_plan_retrieve":
            out = {"scene_gap_s": _r2(f.get("_gap_s"))}
        elif st == "high_plan_route":
            out = {"angle_margin_deg": _r2(f.get("_angle_margin")), "scene_gap_s": _r2(f.get("_gap_s"))}
        elif st in ("high_order", "medium_order"):
            evs = sorted((ix.ev(e) for e in f["evidence_event_ids"]), key=lambda e: e.t_start)
            out = {"min_gap_s": _r2(min(b.t_start - a.t_start for a, b in zip(evs, evs[1:])))}
    except Exception:
        out = {}
    return {k: v for k, v in out.items() if v is not None}


def _hardness(feat):
    """启发式里的「难」:余量越小越难;计数越大越难;事件间隔越小越难。越小越先考。"""
    if "margin_m" in feat:
        return feat["margin_m"]
    if "count" in feat:
        return -feat["count"]
    if "min_gap_s" in feat:
        return feat["min_gap_s"]
    if "angle_margin_deg" in feat:
        return feat["angle_margin_deg"] / 60.0
    if "hard_negatives" in feat:
        return -feat["hard_negatives"]
    return 0.0


def card(ix, f):
    c = {"id": f["fact_id"], "subtype": f["subtype"], "family": FAM.get(f["subtype"], "other"),
         "video": f["video_id"][:3]}
    if f.get("_mode"):
        c["relation"] = f["_mode"]
    ref = f.get("_ref") or f.get("_anchor")
    if ref:
        c["reference"] = ref
    if f.get("_sound_label"):
        c["sound"] = C.SOUND_PHRASE.get(f["_sound_label"], f["_sound_label"])
    c.update(features(ix, f))
    return c


# ---------- memory 的族级汇总 ----------

def family_acc(summary):
    """把上一层的 by_subtype 按题族加权合并 —— 跨层能对上的只有族。"""
    agg = collections.defaultdict(lambda: [0, 0.0])
    for st, v in (summary.get("by_subtype") or {}).items():
        fam = FAM.get(st, "other")
        agg[fam][0] += v["n"]
        agg[fam][1] += v["acc"] * v["n"]
    return {k: round(c / n, 3) for k, (n, c) in agg.items() if n}


def _overall(summary):
    n = summary.get("n") or 0
    return (summary.get("n_correct", 0) / n) if n else 1.0


# ---------- 护栏 ----------

def _interleave(head):
    """按子类做平滑加权轮转:子类内部保持原优先级,任何前缀里各子类的占比都与整段一致。

    assemble 只从队首往后取到够数为止(pilot 2:队首 70 条只用了前 50 条)。不交错的话,
    保底补进来、排在队尾的子类会整类落选(L3 的总体目标与时序排序因此为 0)。"""
    by = collections.OrderedDict()
    for f in head:
        by.setdefault(f["subtype"], []).append(f)
    w = {k: len(v) for k, v in by.items()}
    credit = {k: 0.0 for k in by}
    out = []
    while any(by.values()):
        live = [k for k in by if by[k]]
        for k in live:
            credit[k] += w[k]
        k = max(live, key=lambda x: (credit[x], -list(by).index(x)))
        credit[k] -= sum(w[x] for x in live)
        out.append(by[k].pop(0))
    return out


def guardrails(picks, pool, program_order, n, n_final=None):
    """把 Gemini(或启发式)的提议裁成一段合规的队首,再接程序顺序作兜底。

    picks: [fact_id...] 提议顺序;pool: {fact_id: fact};program_order: [fact...]。
    n: 队首长度(含校验拒绝的余量);n_final: 最终题数 —— 占比上下限按它算。
    (pilot 2 按队首 70 算 50% 上限 = 35 条,最终 50 题里路线题占了 70%。)
    返回 (ordered_facts, meta)。
    """
    nf = n_final or n
    max_sub = max(1, math.ceil(P.CURATE_MAX_SUB_FRAC * nf))
    max_gold = max(1, math.floor(P.CURATE_MAX_GOLD_FRAC * nf))
    avail = collections.Counter(f["subtype"] for f in program_order)
    min_sub = {s: min(math.ceil(P.CURATE_MIN_SUB_FRAC * nf), c) for s, c in avail.items()}

    meta = {"n_proposed": len(picks), "n_hallucinated": 0, "n_duplicate": 0,
            "n_cap_subtype": 0, "n_cap_gold": 0, "n_window": 0, "n_min_fill": 0}
    head, seen = [], set()
    sub_n, gold_n = collections.Counter(), collections.Counter()
    wins = collections.defaultdict(list)
    from_curator = set()

    def fits(f, count_fail=True):
        if sub_n[f["subtype"]] >= max_sub:
            if count_fail: meta["n_cap_subtype"] += 1
            return False
        if "spatial" in f["subtype"] and gold_n[f["gold"]] >= max_gold:
            if count_fail: meta["n_cap_gold"] += 1
            return False
        fw = [tuple(w) for w in f["windows"]] if f.get("windows") else [(f["t0"], f["t1"])]
        if any(min(b1, b2) - max(a1, a2) >= P.WIN_SEC / 2
               for a1, b1 in fw for a2, b2 in wins[f["video_id"]]):
            if count_fail: meta["n_window"] += 1
            return False
        return True

    def take(f):
        head.append(f); seen.add(f["fact_id"])
        sub_n[f["subtype"]] += 1
        if "spatial" in f["subtype"]:
            gold_n[f["gold"]] += 1
        wins[f["video_id"]].extend([tuple(w) for w in f["windows"]] if f.get("windows")
                                   else [(f["t0"], f["t1"])])

    # 1) 提议:丢幻觉与重复,其余过护栏
    for fid in picks:
        if len(head) >= n:
            break
        if fid in seen:
            meta["n_duplicate"] += 1; continue
        f = pool.get(fid)
        if f is None:
            meta["n_hallucinated"] += 1; continue
        if fits(f):
            take(f); from_curator.add(fid)

    # 2) 保底:池里有的子类至少 min_sub 条(从程序顺序补)
    for s, need in sorted(min_sub.items()):
        for f in program_order:
            if sub_n[s] >= need:
                break
            if f["subtype"] == s and f["fact_id"] not in seen and fits(f, False):
                take(f); meta["n_min_fill"] += 1

    # 3) 超长则从队尾撤回「所属子类已超保底」的提议
    while len(head) > n:
        for i in range(len(head) - 1, -1, -1):
            f = head[i]
            if sub_n[f["subtype"]] > min_sub.get(f["subtype"], 0):
                head.pop(i); sub_n[f["subtype"]] -= 1; seen.discard(f["fact_id"])
                break
        else:
            head.pop()

    # 4) 不足则用程序顺序补齐
    for f in program_order:
        if len(head) >= n:
            break
        if f["fact_id"] not in seen and fits(f, False):
            take(f)

    head = _interleave(head)
    meta["curated_fraction"] = round(sum(f["fact_id"] in from_curator for f in head)
                                     / max(len(head), 1), 3)
    meta["head_subtypes"] = dict(collections.Counter(f["subtype"] for f in head))
    tail = [f for f in program_order if f["fact_id"] not in seen]
    return head + tail, meta


# ---------- 两个选题器 ----------

def heuristic_picks(cards, summary):
    """离线 / A-B 基线:按题族正确率加权轮转,族内先考余量小的。确定性,不调 API。"""
    facc = family_acc(summary)
    base = _overall(summary)
    by = collections.defaultdict(list)
    for c in cards:
        by[c["family"]].append(c)
    for fam in by:
        by[fam].sort(key=lambda c: (_hardness(c), c["id"]))
    w = {fam: 1 + 2 * (1 - facc.get(fam, base)) for fam in by}
    credit = {fam: 0.0 for fam in by}
    out = []
    while any(by.values()):
        live = [f for f in by if by[f]]
        for fam in live:
            credit[fam] += w[fam]
        fam = max(live, key=lambda f: (credit[f], f))       # 平滑加权轮转
        credit[fam] -= sum(w[f] for f in live)
        out.append(by[fam].pop(0)["id"])
    return out, {fid: "heuristic" for fid in out}


def _exemplar_lines(cards_facts):
    """每个 (子类, 关系) 一条模板题 —— 用离线模板现造,保证总有,且与本池一致。"""
    import phrase as PH
    seen, lines = set(), []
    for f in cards_facts:
        key = (f["subtype"], f.get("_mode"))
        if key in seen:
            continue
        seen.add(key)
        try:
            q = PH.offline_question(f)
        except ValueError:
            continue
        rel = f" [{f['_mode']}]" if f.get("_mode") else ""
        lines.append(f"- {f['subtype']}{rel}: {q.splitlines()[0]}")
    return lines


def _build_prompt(level, summary, cards, cards_facts, missed_feats, n):
    facc = family_acc(summary)
    fam_table = collections.defaultdict(list)
    for st, fam in FAM.items():
        fam_table[fam].append(st)
    missed = []
    for m in (summary.get("missed_examples") or [])[:10]:
        e = {k: m.get(k) for k in ("subtype", "gold", "video", "chosen_by")}
        e["family"] = FAM.get(m.get("subtype"), "other")
        e["question"] = (m.get("question") or "")[:160]
        if m.get("fact_id") in missed_feats:
            e["features"] = missed_feats[m["fact_id"]]
        missed.append(e)
    lines = [
        "You are the QUESTION SELECTOR for an adaptive audio-visual benchmark built from",
        "30-second first-person kitchen clips. The benchmark is a pyramid of four levels; you",
        f"are choosing the questions for level {level}. Answers are fixed by a program and",
        "are NOT shown to you — you decide only WHICH candidate questions to ask.",
        "",
        f"Memory of the previous level (level {level - 1}): the evaluated agent(s)",
        f"{', '.join(summary.get('agents', []))} scored {summary.get('n_correct')}/{summary.get('n')}.",
        "Accuracy by subtype (previous level's subtypes):",
        json.dumps(summary.get("by_subtype", {}), ensure_ascii=False),
        "Accuracy by FAMILY (use this to carry the signal across levels — subtype names",
        "differ between levels, families do not):",
        json.dumps(facc, ensure_ascii=False),
        "Accuracy by video:", json.dumps(summary.get("by_video", {}), ensure_ascii=False),
        "Accuracy by sound:", json.dumps(summary.get("by_sound", {}), ensure_ascii=False),
        "Questions they got wrong (with difficulty features where known):",
        json.dumps(missed, ensure_ascii=False),
        "",
        "Families and their subtypes:",
        json.dumps(dict(fam_table), ensure_ascii=False),
        "What each candidate subtype asks (one template each; [relation] where it varies):",
        *_exemplar_lines(cards_facts),
        "",
        "Difficulty features on the cards (smaller = harder unless noted):",
        "- margin_m: metres by which the correct object beats the runner-up (spatial / ego).",
        "- d_gold_m: distance of the correct object from the reference.",
        "- n_objects: how many objects compete in the clip (more = harder).",
        "- count: the number to be counted (larger = harder).",
        "- min_gap_s: seconds between the closest two events to be ordered.",
        "- hard_negatives: how many wrong purposes are near-misses (same verb/object) (larger = harder).",
        "- angle_margin_deg: degrees from the nearest direction boundary (smaller = harder).",
        "- scene_gap_s: seconds between the two scenes of a cross-scene question (larger = harder).",
        "- relation: which spatial relation / side the question asks about.",
        "",
        f"TASK: choose exactly {n} candidates, ordered by priority. Target the weaknesses the",
        "memory shows: favour families, sounds and videos with low accuracy, and within them",
        "harder features and the relations the agents got wrong. Keep variety — no single",
        f"subtype above {int(P.CURATE_MAX_SUB_FRAC * 100)}% of your picks, and every subtype present",
        f"in the candidates at least about {int(P.CURATE_MIN_SUB_FRAC * 100)}%. Use only ids from the list.",
        "",
        'Return a JSON array: [{"id": "<candidate id>", "target": "<=12 words: the weakness it probes"}]',
        "",
        "Candidates:",
        *[json.dumps(c, ensure_ascii=False) for c in cards],
    ]
    return "\n".join(lines)


def gemini_picks(level, summary, cards, cards_facts, missed_feats, n, cache_key):
    cdir = P.POUT / "cache" / "curation"
    cdir.mkdir(parents=True, exist_ok=True)
    cf = cdir / f"{cache_key}.json"
    if cf.exists():
        rec = json.loads(cf.read_text())
    else:
        import gemini_io
        prompt = _build_prompt(level, summary, cards, cards_facts, missed_feats, n)
        raw, mid = gemini_io.gen(prompt, max_tokens=8192)
        items = gemini_io.jparse(raw) or []
        rec = {"model": mid, "items": [it for it in items if isinstance(it, dict)],
               "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:16]}
        cf.write_text(json.dumps(rec, ensure_ascii=False))
    picks = [str(it.get("id", "")) for it in rec["items"]]
    notes = {str(it.get("id", "")): (it.get("target") or "")[:120] for it in rec["items"]}
    return picks, notes, rec.get("model")


# ---------- 入口 ----------

def order(mixed, summary, level, n_target, select, offline, ix_of):
    """assemble.build_set 调用:把程序顺序 `mixed`(未去窗口重叠)重排成选题器的顺序。

    返回 (ordered, notes, selection_meta, audit)。select=="program" 或无摘要时原样返回。
    """
    if select == "program" or not summary:
        why = "program" if select == "program" else "program(no-memory:L1)"
        return mixed, {}, {"mode": why}, None
    n = min(P.N_REQUEST, max(P.PHRASE_BATCH, math.ceil(n_target * 1.4)))
    pool_facts = mixed[:P.CURATE_POOL_MULT * n]
    pool = {f["fact_id"]: f for f in pool_facts}
    cards = [card(ix_of(f["video_id"]), f) for f in pool_facts]

    missed_feats = {}
    ids = {m.get("fact_id") for m in summary.get("missed_examples") or [] if m.get("fact_id")}
    if ids:
        import facts as F
        allf = {f["fact_id"]: f for fs in F.load_all().values() for f in fs}
        for fid in ids:
            if fid in allf:
                missed_feats[fid] = features(ix_of(allf[fid]["video_id"]), allf[fid])

    mode = "heuristic" if (select == "heuristic" or offline) else "gemini"
    key = hashlib.sha256("|".join([",".join(sorted(pool)), summary.get("summary_sha", ""),
                                   P.CURATE_VERSION, str(n), mode]).encode()).hexdigest()[:24]
    model = None
    if mode == "gemini":
        try:
            picks, notes, model = gemini_picks(level, summary, cards, pool_facts, missed_feats, n, key)
        except RuntimeError as e:
            print(f"  [curate] Gemini 选题失败,回退启发式: {e}", flush=True)
            picks, notes = heuristic_picks(cards, summary)
            mode = "heuristic(fallback)"
    else:
        picks, notes = heuristic_picks(cards, summary)

    ordered, g = guardrails(picks, pool, mixed, n, n_final=n_target)
    meta = {"mode": mode if not (offline and select == "gemini") else "heuristic(offline)",
            "curator_model": model, "curate_version": P.CURATE_VERSION,
            "n_head": n, "n_cards": len(cards), "curation_sha": key, **g}
    if mode.startswith("gemini") and g["curated_fraction"] < P.CURATE_MIN_FRACTION:
        print(f"  [curate] 警告:Gemini 有效挑选仅 {g['curated_fraction']:.0%}", flush=True)
    audit = {"selection": meta, "family_acc_prev": family_acc(summary),
             "cards": cards, "picks": picks, "notes": notes}
    return ordered, notes, meta, audit


# ---------- 范例库 ----------

def build_exemplars(set_globs, per_key=3):
    """从已通过 verify、Gemini 措辞的 spatial 题里,每个 (子类, 关系) 取 per_key 条作模板。"""
    import glob, facts as F
    allf = {f["fact_id"]: f for fs in F.load_all().values() for f in fs}
    bank = collections.defaultdict(list)
    for g in set_globs:
        for path in sorted(glob.glob(g)):
            if path.endswith(("_rejected.json", "_curation.json")):
                continue
            for q in json.loads(open(path).read()).get("questions", []):
                if "spatial" not in q["subtype"] or q.get("phrasing") != "gemini":
                    continue
                f = allf.get(q["fact_id"])
                key = f"{q['subtype']}|{(f or {}).get('_mode', '')}"
                if len(bank[key]) < per_key and all(e["question"] != q["question"] for e in bank[key]):
                    bank[key].append({"question": q["question"], "answer": q["answer"],
                                      "subtype": q["subtype"], "relation": (f or {}).get("_mode")})
    P.SPATIAL_EXEMPLARS.write_text(json.dumps(dict(bank), ensure_ascii=False, indent=1))
    return dict(bank)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-exemplars", nargs="+", metavar="SETS_GLOB")
    a = ap.parse_args()
    if a.build_exemplars:
        b = build_exemplars(a.build_exemplars)
        for k, v in sorted(b.items()):
            print(f"{k:34s} {len(v)} 条")
        print("->", P.SPATIAL_EXEMPLARS)
