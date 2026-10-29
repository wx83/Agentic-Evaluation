"""L4 预判题:用 HD-EPIC 官方 eye-gaze priming(raw/gaze_priming.json)。

官方标注对每次拿起(start)/ 放下(end)记录:此前 10 s 内视线是否先落到该位置(frame_primed >= 0)、
提前了多少秒(prime_gap)。视线先于动作 —— 所以把片段**截在动作发生之前**,让被测者预判:
- high_gaze_destination  正拿着 X,接下来会把它放到哪?(gold = to_fixture)
- high_gaze_pickup       接下来会拿起哪个物体?(gold = 物体名)
片段里**不画注视点**:被测者只能从头部转动与场景推断。facts.py 与 verify.py 共用本模块的 derive。
"""
import json
import pconfig as P
import config as C
import primitives as PRIM
import infer as IN

MIN_GAP = 1.5        # 视线至少提前这么多秒,截断后视线已到位而动作还没发生
CUT_BEFORE = 1.0     # 片段结束在动作前 1 s
HELD_MIN = 0.5       # destination:截断时物体已在手里至少这么久
QUIET = 3.0          # pickup:截断前这么多秒内 gold 物体没被动过
MATCH_TOL = 0.15     # priming 条目与 movement 事件的起止时间容差

_PRIM = {}


def priming(ix):
    """{movement eid: {"start": prime_stats|None, "end": prime_stats|None}},按起止时间与 movement 一一对上的才收。"""
    v = ix.video_id
    if v not in _PRIM:
        d = json.loads((C.HDEPIC / "annotations" / v / "raw" / "gaze_priming.json").read_text())[v]
        out = {}
        for x in d.values():
            if not isinstance(x.get("start"), dict) or not isinstance(x.get("end"), dict):
                continue
            ts, te = x["start"]["frame"] / 30.0, x["end"]["frame"] / 30.0
            m = [e for e in ix.movements
                 if abs(e.t_start - ts) < MATCH_TOL and abs(e.t_end - te) < MATCH_TOL]
            if len(m) != 1:
                continue
            out[m[0].eid] = {s: (x[s].get("prime_stats") if isinstance(x[s].get("prime_stats"), dict)
                                 else None) for s in ("start", "end")}
        _PRIM[v] = out
    return _PRIM[v]


def _primed(ps):
    return bool(ps) and ps.get("frame_primed", -2) >= 0 and ps.get("prime_gap", 0) >= MIN_GAP


def _win(t_cut):
    return (round(t_cut - P.WIN_SEC, 2), round(t_cut, 2)) if t_cut - P.WIN_SEC >= 0 else None


def derive_destination(ix, m):
    """m = 被放下的那次 movement。返回 {gold, prev, object, t0, t1, gap} 或 None。"""
    ps = priming(ix).get(m.eid, {}).get("end")
    nm = IN.clean_obj(IN.mv_name(m))
    gold = ix.fixture_pretty(m.extra.get("to_fixture"))
    prev = ix.fixture_pretty(m.extra.get("from_fixture"))
    if not _primed(ps) or not nm or not gold or not prev or gold == prev:
        return None
    w = _win(m.t_end - CUT_BEFORE)
    if not w or m.t_start > w[1] - HELD_MIN:                 # 截断时还没拿起来
        return None
    # 同一物体在窗口内此前已被放到过 gold:答案已经演过一遍
    for e in ix.movements:
        if e is not m and IN.clean_obj(IN.mv_name(e)) == nm and e.t_end > w[0] and e.t_end <= w[1] \
                and ix.fixture_pretty(e.extra.get("to_fixture")) == gold:
            return None
    return {"gold": gold, "prev": prev, "object": nm, "t0": w[0], "t1": w[1],
            "gap": ps["prime_gap"], "dist": ps.get("dist_to_cam")}


def derive_pickup(ix, m):
    """m = 即将被拿起的那次 movement。返回 {gold, t0, t1, gap} 或 None。"""
    ps = priming(ix).get(m.eid, {}).get("start")
    nm = IN.clean_obj(IN.mv_name(m))
    if not _primed(ps) or not nm:
        return None
    w = _win(m.t_start - CUT_BEFORE)
    if not w:
        return None
    for e in ix.movements:
        if e is m:
            continue
        if w[1] < e.t_start < m.t_start:                     # 截断后、gold 之前还有别的拿起
            return None
        if IN.clean_obj(IN.mv_name(e)) == nm and e.t_end > w[1] - QUIET and e.t_start < w[1]:
            return None                                       # gold 刚被动过 / 正在手里
    vis = {PRIM._norm(x) for x in ix.visible_in(w[0], w[1])}
    if nm not in vis:                                         # 片段里得看得到它
        return None
    return {"gold": nm, "t0": w[0], "t1": w[1], "gap": ps["prime_gap"], "dist": ps.get("dist_to_cam")}


def pickup_distractors(ix, r, rng):
    """片段里看得到、但截断后 10 s 内没被拿起的物体;优先取片段末 5 s 还可见的(同在眼前)。"""
    t0, t1, gold = r["t0"], r["t1"], r["gold"]
    soon = {IN.clean_obj(IN.mv_name(e)) for e in ix.movements if t1 - QUIET < e.t_start < t1 + 10
            or (e.t_start < t1 < e.t_end)}
    ok = lambda n: n and n != gold and n not in soon and not PRIM.is_fixture(n) \
        and not PRIM.is_artifact(n) and "unknown" not in n \
        and PRIM._head_noun(n) != PRIM._head_noun(gold)
    late = sorted({PRIM._norm(x) for x in ix.visible_in(t1 - 5, t1)} & {n for n in
                  (PRIM._norm(x) for x in ix.visible_in(t0, t1)) if ok(n)})
    rest = sorted({n for n in (PRIM._norm(x) for x in ix.visible_in(t0, t1)) if ok(n)} - set(late))
    rng.shuffle(late); rng.shuffle(rest)
    out, heads = [], {PRIM._head_noun(gold)}
    for n in late + rest:
        if PRIM._head_noun(n) in heads:
            continue
        heads.add(PRIM._head_noun(n)); out.append(n)
        if len(out) == 3:
            return out, sum(x in late for x in out)
    return None, 0


def check(ix, item, fact, errs):
    m = ix.ev(fact["_ref_eid"])
    st = fact["subtype"]
    r = derive_destination(ix, m) if st == "high_gaze_destination" else derive_pickup(ix, m)
    if not r or r["gold"] != item["answer"]:
        errs.append("注视预判重推不符"); return
    if abs(r["t0"] - item["t0"]) > 0.02 or abs(r["t1"] - item["t1"]) > 0.02:
        errs.append("注视预判窗口不符")
    cut = m.t_end if st == "high_gaze_destination" else m.t_start
    if item["t1"] > cut - CUT_BEFORE + 0.02:
        errs.append("片段没有截在动作之前")
    if st == "high_gaze_destination":
        vocab = set(C.FIXTURE_NAME.values())
        for d in item["_distractors"]:
            if d == item["answer"] or d not in vocab:
                errs.append(f"目的地干扰项 '{d}' 非法")
        if fact["_object"].lower() not in item["question"].lower():
            errs.append("题面未点明手里的物体")
    else:
        vis = {PRIM._norm(x) for x in ix.visible_in(item["t0"], item["t1"])}
        for d in item["_distractors"]:
            if PRIM._norm(d) not in vis:
                errs.append(f"拿起干扰项 '{d}' 片段里看不到")
            for e in ix.movements:
                if IN.clean_obj(IN.mv_name(e)) == d and item["t1"] - QUIET < e.t_start < item["t1"] + 10:
                    errs.append(f"拿起干扰项 '{d}' 随后也被拿起")
