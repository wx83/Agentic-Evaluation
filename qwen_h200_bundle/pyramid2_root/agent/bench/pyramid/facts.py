"""按层挖掘经校验的事实元组 (gold, kind, eids, window, distractors)。

包装 bench/primitives.py 而不改它。两处修正:
1. Medium 不再经 salient_sounds(±15s 唯一性与「窗口内出现 2-6 次」自相矛盾,原路只剩 3 条)。
   改为 stride-15 扫窗,对全部 nameable 标签数窗口内的干净计数。
2. Easy 供给太少(约 66),补两个同样一行可读出答案的子类:easy_sound(窗口内该声音在、
   干扰声音不在)与 easy_move(窗口内唯一一次 from->to 搬动)。

每题打 subtype 标签,gold 全部由程序推导,Gemini 之后只写措辞。
"""
import json, hashlib, random, argparse, collections, math
import pconfig as P
import config as C
import primitives as PRIM
import spatial as SP
import infer as IN
import formats as FM
from timeline_index import TimelineIndex


def _fid(video, subtype, gold, eids, t0):
    raw = f"{video}|{subtype}|{gold}|{','.join(eids)}|{t0:.1f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _win_around(ix, t):
    """以 t 为中心的固定 30 秒窗口,夹到 [0, duration]。"""
    t0 = min(max(0.0, t - P.WIN_SEC / 2), max(0.0, ix.duration - P.WIN_SEC))
    return t0, t0 + P.WIN_SEC


def _stride_wins(ix):
    t = 0.0
    while t + P.WIN_SEC <= ix.duration:
        yield t, t + P.WIN_SEC
        t += P.STRIDE


def count_clean(ix, label, t0, t1):
    """边界干净的窗口内计数:该标签所有与 [t0-3,t1+3] 相交的事件都必须完整落在
    [t0+0.5, t1-0.5] 内,否则计数有歧义,返回 None。"""
    evs = ix.sounds_between(t0 - 3, t1 + 3, label)
    inside = [e for e in evs if e.t_start >= t0 + 0.5 and e.t_end <= t1 - 0.5]
    return len(inside) if len(inside) == len(evs) else None


def _mv_name(m):
    return (m.extra.get("object_name") or m.text or "").strip()


def _dnorm(s):
    """去重用的归一化。注意 PRIM._norm 会剥掉结尾数字 —— 那对物体名是对的
    ("egg 1"/"egg 2" 本就是同一种东西),对计数选项却是灾难("2"/"3" 全变空串)。
    所以纯数字按原值比。"""
    s = (s or "").strip()
    return s if s.isdigit() else PRIM._norm(s)


def _drop_unknown(ds):
    """PRIM.distractors 的 OBJECT 池不认识 "unknown pan" 这类残名(primitives.py 不改:
    build_bench.py 也在用),在这里滤掉。"""
    return None if ds is None else [d for d in ds if "unknown" not in (d or "").lower()]


def clean_distractors(ds, gold):
    """primitives._norm 会去掉结尾数字,标注里的 "egg 1"/"egg 2" 会双双变成 "egg",
    于是同一个选项出现两次(实测 3.9% 的题中招)。去重后不足 3 个即拒收该事实。"""
    if not ds:
        return None
    seen, out = {_dnorm(gold)}, []
    for d in ds:
        n = _dnorm(d)
        if n in seen:
            continue
        seen.add(n)
        out.append(d)
    return out[:3] if len(out) >= 3 else None


def _pack(video, tier, subtype, kind, t0, t1, gold, eids, ev_t,
          distractors, sound_label=None, **extra):
    return {"fact_id": _fid(video, subtype, gold, eids, t0),
            "video_id": video, "tier": tier, "subtype": subtype, "kind": kind,
            "t0": round(t0, 2), "t1": round(t1, 2), "gold": gold,
            "evidence_event_ids": eids, "evidence_t": round(ev_t, 2),
            "_sound_label": sound_label, "distractors": distractors, **extra}


# ---------- 各层挖掘 ----------

def _window_objs(ix, t0, t1):
    v = {PRIM._norm(x) for x in ix.visible_in(t0, t1)}
    v |= {PRIM._norm(m.extra.get("object_name") or "") for m in ix.in_window(t0, t1, "movement")}
    return v


def _tokens(n):
    return set(re.split(r"[^a-z]+", (n or "").lower())) - {""}


def _pick_by_head(cands, gold, rng):
    """每个中心词最多一个、与 gold 不同类,打乱后取 3;不足 3 返回 None(不回退随机)。

    「不同类」按词元判:标注里有 "spoon-unknown" 这类残名,只比 _head_noun 会把它和 "spoon"
    当成两种东西,于是出现 spoon / spoon-unknown 两个近乎相同的选项。"""
    gh, gt, by = PRIM._head_noun(gold), _tokens(gold), {}
    for n in sorted(cands):
        h = PRIM._head_noun(n)
        if not h or h == gh or "unknown" in _tokens(n) or PRIM._head_noun(gold) in _tokens(n) \
                or h in gt:
            continue
        by.setdefault(h, n)
    pool = sorted(by.values())
    rng.shuffle(pool)
    return pool[:3] if len(pool) >= 3 else None


def hint_distractors(ix, label, gold, t0, t1, rng):
    """声音 -> 物体题的干扰项:同样**能发出这种声音**的物体(匹配 SOUND_OBJECT_HINT),
    且在 [t0-2, t1+2] 内不出现。原来取随机缺席物体,「搅拌声 -> 勺子 vs 芒果」盲答 75%。"""
    hints = C.SOUND_OBJECT_HINT.get(label) or []
    near = _window_objs(ix, t0 - 2, t1 + 2)
    cands = {PRIM._norm(n) for n in ix.object_names
             if not PRIM.is_fixture(n) and not PRIM.is_artifact(n)
             and any(h in n.lower() for h in hints)} - near - {PRIM._norm(gold)}
    return _pick_by_head(cands, gold, rng)


def route_distractors(ix, fr, to, gold, t0, t1, rng):
    """搬动题的干扰项:本视频别处**走过同一路线**(from -> to)的物体,且在 [t0-2, t1+2] 内不出现。
    原来取随机缺席物体,「从台面搬到水槽 -> 杯子 vs 胶水盒」盲答 56%。"""
    near = _window_objs(ix, t0 - 2, t1 + 2)
    cands = set()
    for m in ix.transitions:
        if (ix.fixture_pretty(m.extra.get("from_fixture")), ix.fixture_pretty(m.extra.get("to_fixture"))) != (fr, to):
            continue
        nm = PRIM._norm(m.extra.get("object_name") or "")
        if nm and not PRIM.is_fixture(nm) and not PRIM.is_artifact(nm):
            cands.add(nm)
    return _pick_by_head(cands - near - {PRIM._norm(gold)}, gold, rng)


# ---- easy_sound 干扰项(2026-09-28 重做)----
# 旧版取「本视频最常见、但 [t0-2,t1+2] 内没标注」的声音:开关门、切菜、碰撞这类厨房里
# 随时在响、只是没标注的声音,于是干扰项可能其实也响了 —— seed43-46 实测 gemini 45% /
# qwen 27%,盲答 11% / 18%(低于随机:干扰项比 gold 更像「会听到的」)。
# 现在干扰声音须:±30 s 内都没有标注;窗口内 narration 的动作不暗示它(开柜子 -> 开关声);
# 且不取脚步声(常有而不标)。gold 也不取脚步声(两模型 0/8,耳机麦克风里几乎听不到)。
EASY_SOUND_NEVER = {"footstep"}
SOUND_FAR_W = 30.0
SOUND_IMPLIED_BY = {
    "open / close": {"open", "close", "shut"},
    "cut / chop": {"cut", "chop", "slice", "dice", "trim"},
    "stir / mix / whisk": {"stir", "mix", "whisk", "beat", "fold"},
    "water": {"wash", "rinse", "fill", "run", "turn-on", "turn-off"},
    "scrub / scrape / scour / wipe": {"wipe", "scrub", "scrape", "clean", "dry"},
    "pour": {"pour", "drain"},
    "sizzling / boiling": {"fry", "boil", "cook", "sear"},
    "rustle": {"unwrap", "wrap", "open", "fold", "crumple"},
    "kettle / mixer / appliance": {"blend", "switch", "turn-on"},
}


def sound_distractor_ok(ix, label, t0, t1):
    if label in C.SKIP_SOUNDS or label not in C.SOUND_PHRASE or label in EASY_SOUND_NEVER:
        return False
    if ix.sounds_between(t0 - SOUND_FAR_W, t1 + SOUND_FAR_W, label):
        return False
    verbs = {v.lower() for e in ix.in_window(t0 - 2, t1 + 2, "narration")
             for v in e.extra.get("verbs", [])}
    return not (verbs & SOUND_IMPLIED_BY.get(label, set()))


def easy_sound_distractors(ix, label, t0, t1, rng):
    """3 个合格干扰声音,**频次与 gold 相近者优先**(全视频计数在 gold 的 1/3–3 倍内),不够再放宽;
    gold 是碰撞类时至多一个碰撞类干扰项。
    09-28 第一版按频次降序取 —— 干扰项永远是本视频最常见的声音(开关门 / 切菜),语言先验就偏向它们:
    实测盲答 gemini 14% / qwen 28%,看视频也只有 50% / 35%,低于随机的盲答说明选项本身带偏。"""
    is_coll = lambda l: "collision" in l
    g = len(ix.by_sound_label.get(label, [])) or 1
    ok = [l for l in sorted(ix.by_sound_label) if l != label and sound_distractor_ok(ix, l, t0, t1)]
    near = [l for l in ok if g / 3 <= len(ix.by_sound_label[l]) <= g * 3]
    far = [l for l in ok if l not in near]
    rng.shuffle(near); rng.shuffle(far)
    pool, used_coll = [], 0
    for l in near + far:
        if is_coll(l) and is_coll(label):
            if used_coll >= 1:
                continue
            used_coll += 1
        pool.append(C.SOUND_PHRASE[l])
        if len(pool) == 3:
            return pool
    return None


def mine_easy(ix, rng):
    out, video = [], ix.video_id
    # 子类 1:easy_sound_object —— 沿用 find_easy(声音与可见物体互相印证)
    for s in PRIM.salient_sounds(ix):
        r = PRIM.find_easy(ix, s)
        if not r:
            continue
        t0, t1 = _win_around(ix, s.mid())
        if not (t0 <= s.t_start and s.t_end <= t1):
            continue
        d = clean_distractors(hint_distractors(ix, s.label, r["gold"], t0, t1, rng), r["gold"])
        if not d:
            continue
        out.append(_pack(video, "Easy", "easy_sound_object", "OBJECT",
                         t0, t1, r["gold"], r["eids"], s.mid(), d, s.label))
    # 子类 2:easy_sound —— gold 声音在窗口内,干扰声音见 easy_sound_distractors
    for s in PRIM.salient_sounds(ix):
        if s.label not in C.SOUND_PHRASE or s.label in EASY_SOUND_NEVER:
            continue
        t0, t1 = _win_around(ix, s.mid())
        if not (t0 + 0.5 <= s.t_start and s.t_end <= t1 - 0.5):
            continue
        d = clean_distractors(easy_sound_distractors(ix, s.label, t0, t1, rng),
                              C.SOUND_PHRASE[s.label])
        if not d:
            continue
        out.append(_pack(video, "Easy", "easy_sound", "SOUND",
                         t0, t1, C.SOUND_PHRASE[s.label], [s.eid], s.mid(), d, s.label))
    # 子类 3:easy_move —— 窗口内唯一一次 from->to 搬动
    for m in ix.transitions:
        nm = _mv_name(m)
        if not nm or PRIM.is_fixture(nm) or PRIM.is_artifact(nm):
            continue
        fr = ix.fixture_pretty(m.extra.get("from_fixture"))
        to = ix.fixture_pretty(m.extra.get("to_fixture"))
        if not fr or not to or fr == to:
            continue
        t0, t1 = _win_around(ix, m.mid())
        same = [x for x in ix.transitions
                if x.t_start < t1 and x.t_end > t0
                and ix.fixture_pretty(x.extra.get("from_fixture")) == fr
                and ix.fixture_pretty(x.extra.get("to_fixture")) == to]
        if len(same) != 1:
            continue
        gold = PRIM._norm(nm)
        d = clean_distractors(route_distractors(ix, fr, to, gold, t0, t1, rng), gold)
        if not d:
            continue
        out.append(_pack(video, "Easy", "easy_move", "OBJECT",
                         t0, t1, gold, [m.eid], m.mid(), d,
                         _from=fr, _to=to))
    return out


def mine_low(ix, rng):
    out = []
    for s in PRIM.salient_sounds(ix):
        r = PRIM.find_low(ix, s)
        if not r or s.label not in C.SOUND_PHRASE:
            continue
        t0, t1 = _win_around(ix, s.mid())
        if not (t0 <= s.t_start and s.t_end <= t1):
            continue
        d = clean_distractors(_drop_unknown(PRIM.distractors(ix, "OBJECT", r["gold"], t0, t1, rng)), r["gold"])
        if not d:
            continue
        out.append(_pack(ix.video_id, "Low", "low_sound_movement", "OBJECT",
                         t0, t1, r["gold"], r["eids"], s.mid(), d, s.label))
    return out


def count_distractors(g, rng):
    """计数题干扰项:取包含 gold 的连续 4 个非负整数,gold 的名次在可行范围内随机。

    原 PRIM.distractors("COUNT") 从 {g-2, g-1, g+1, g+2} 抽 3 个 —— gold 永远被夹在中间:
    seed42 的 500 道计数题,gold 在数值排序后 100% 落在第 2/3 位,盲答实测 83%。
    (primitives.py 不改:build_bench.py 也在用它。)
    """
    o = rng.choice([k for k in range(4) if g - k >= 0])
    return [str(x) for x in range(g - o, g - o + 4) if x != g]


def mine_medium(ix, rng):
    out, nameable = [], ix.nameable_sounds()
    for t0, t1 in _stride_wins(ix):
        # nameable_sounds 返回 set,直接迭代的顺序随 PYTHONHASHSEED 变 —— fact_id 集合
        # 不受影响(不含 distractors),但 rng 在循环里被逐个消耗,顺序一变每道题分到的
        # 干扰项就变了,SEED=42 便不再可复现。排序钉死。
        for label in sorted(nameable):
            if label not in C.SOUND_PHRASE:
                continue
            n = count_clean(ix, label, t0, t1)
            if n is None or not (2 <= n <= 6):
                continue
            evs = ix.sounds_between(t0, t1, label)
            d = clean_distractors(count_distractors(n, rng), str(n))
            if not d:
                continue
            mid = (evs[0].t_start + evs[-1].t_end) / 2
            out.append(_pack(ix.video_id, "Medium", "medium_count", "COUNT",
                             t0, t1, str(n), [e.eid for e in evs], mid, d, label))
    # gold 取值均衡:仅按 30% 封顶不够 —— 题库整体是 2/3/4/5/6 = 30/30/25/8/7,
    # 抽到一套题里「2」仍占 42%,盲答据此拿到 47%(看视频反而只有 26%)。
    # 改为按最少取值的 1.25 倍封顶,把各取值拉平(499 -> 约 213 条,需求约 84 条,够用)。
    return _balance_gold(out)


import re
ACTION_RE = re.compile(r"^\S.* the \S.*$")   # _action 的合法形态 "verb the noun"


def mine_high(ix, rng):
    out = []
    for t0, t1 in _stride_wins(ix):
        r = PRIM.find_high(ix, t0, t1)
        if not r:
            continue
        parts = r["gold"].split(" -> ")
        if len(set(parts)) != 3:            # _action 后措辞必须互异,否则排序题有歧义
            continue
        # narration label 的 verb/noun 部分可能为空,渲成 " the cup" 这类残句 -> 拒
        if any(not ACTION_RE.fullmatch(p) or "  " in p for p in parts):
            continue
        d = clean_distractors(PRIM.distractors(ix, "ORDER", r["gold"], t0, t1, rng), r["gold"])
        if not d:
            continue
        mid = sum(e.mid() for e in r["events"]) / 3
        out.append(_pack(ix.video_id, "High", "high_order", "ORDER",
                         t0, t1, r["gold"], r["eids"], mid, d))
    return out


# ---------- 空间层(四层各一个子类,共用 spatial.py 的基元) ----------

def _sp_eids(*groups):
    """证据 eid 去重保序。每个都必须与窗口重叠 —— rest_at 已保证样本时刻在窗口内。"""
    out = []
    for g in groups:
        for e in (g if isinstance(g, (list, tuple)) else [g]):
            if e and e not in out:
                out.append(e)
    return out


def mine_easy_spatial(ix, rng):
    """L1:某次搬动的落点为参照,问窗口内哪个物体离它最近。"""
    out, video = [], ix.video_id
    for m in ix.movements:
        if SP._xyz(m.extra.get("end_xyz")) is None:
            continue
        t0, t1 = _win_around(ix, m.mid())
        r = SP.derive_l1(ix, m, t0, t1)
        if not r:
            continue
        names = [r["gold"]] + [x[1] for x in r["present"]]
        if not SP.names_ok(names) or not SP.ref_gold_disjoint(r["ref"], r["gold"]):
            continue
        d = clean_distractors([x[1] for x in r["present"]], r["gold"])
        if not d:
            continue
        eids = _sp_eids(m.eid, r["gold_eid"], [x[2] for x in r["present"]])
        out.append(_pack(video, "Easy", "easy_spatial_near", "NEAREST",
                         t0, t1, r["gold"], eids, r["T"], d,
                         _ref=r["ref"], _ref_eid=m.eid,
                         _d_gold=round(r["d_gold"], 3), _marg=SP.MARG, _absent=[]))
    return out


def mine_low_spatial(ix, rng):
    """L2:声音定时刻(复用 find_low 的唯一性门),几何给答案。

    只有 2 个存在型干扰项(实测 3 个只剩 46 条不可用),第 3 个用缺席型补足 ——
    缺席证明沿用 verify._check_object 的既有机制。
    """
    out = []
    for s in PRIM.salient_sounds(ix):
        if s.label not in C.SOUND_PHRASE:
            continue
        t0, t1 = _win_around(ix, s.mid())
        if not (t0 <= s.t_start and s.t_end <= t1):
            continue
        r = SP.derive_l2(ix, s, t0, t1)
        if not r or not SP.ref_gold_disjoint(r["ref"], r["gold"]):
            continue
        present = [x[1] for x in r["present"]]
        pool = _drop_unknown(PRIM.distractors(ix, "OBJECT", r["gold"], t0, t1, rng)) or []
        absent = [p for p in pool if p not in present][:1]
        if not absent:
            continue
        if not SP.names_ok([r["gold"]] + present + absent):
            continue
        d = clean_distractors(present + absent, r["gold"])
        if not d or len(d) != 3:
            continue
        eids = _sp_eids(s.eid, r["mv_eid"], r["gold_eid"], [x[2] for x in r["present"]])
        out.append(_pack(ix.video_id, "Low", "low_spatial_near", "NEAREST",
                         t0, t1, r["gold"], eids, r["T"], d, s.label,
                         _ref=r["ref"], _ref_eid=s.eid,
                         _d_gold=round(r["d_gold"], 3), _marg=SP.MARG_L2,
                         _absent=[a for a in absent if a in d]))
    return out


def mine_medium_spatial(ix, rng, mode="far"):
    """L3:通览整个窗口,问离参照**最远**(mode="far")或**最近**(mode="near")的那个。"""
    out = []
    for t0, t1 in _stride_wins(ix):
        vis = SP.visible_norm(ix, t0, t1)
        for ref in sorted(n for n in SP.movables(ix) if n in vis):
            r = SP.derive_l3(ix, ref, t0, t1, mode)
            if not r:
                continue
            names = [r["gold"]] + [x[1] for x in r["present"]]
            if not SP.names_ok(names) or not SP.ref_gold_disjoint(r["ref"], r["gold"]):
                continue
            d = clean_distractors([x[1] for x in r["present"]], r["gold"])
            if not d:
                continue
            eids = _sp_eids(r["ref_eid"], r["gold_eid"], [x[2] for x in r["present"]])
            out.append(_pack(ix.video_id, "Medium", "medium_spatial_extreme", "NEAREST",
                             t0, t1, r["gold"], eids, (t0 + t1) / 2, d,
                             _ref=r["ref"], _ref_eid=r["ref_eid"], _mode=mode,
                             _d_gold=round(r["d_gold"], 3), _marg=SP.MARG_L3, _absent=[]))
    return out


def mine_high_spatial(ix, rng):
    """L4:三个物体按到参照的远近排序,由近及远。

    gold 形如 "a -> b -> c",与 high_order 同形,于是 ORDER 的排列干扰项、
    箭头回显归一化、contains_gold 豁免全部直接继承。
    """
    out = []
    for t0, t1 in _stride_wins(ix):
        vis = SP.visible_norm(ix, t0, t1)
        for ref in sorted(n for n in SP.movables(ix) if n in vis):
            r = SP.derive_l4(ix, ref, t0, t1)
            if not r:
                continue
            parts = r["gold"].split(" -> ")
            if len({_dnorm(p) for p in parts}) != 3:
                continue
            if any(not SP.ref_gold_disjoint(r["ref"], p) for p in parts):
                continue
            d = clean_distractors(PRIM.distractors(ix, "ORDER", r["gold"], t0, t1, rng),
                                  r["gold"])
            if not d:
                continue
            eids = _sp_eids(r["ref_eid"], [x[2] for x in r["triple"]])
            out.append(_pack(ix.video_id, "High", "high_spatial_order", "ORDER",
                             t0, t1, r["gold"], eids, (t0 + t1) / 2, d,
                             _ref=r["ref"], _ref_eid=r["ref_eid"],
                             _dists=r["dists"], _order="near_first"))
    return out


# ---------- ego 层(需要 SLAM 位姿)----------

def _cap_by_gold(fs, frac=0.15, key=None):
    """给 gold 取值封顶:任何单一取值占比不得超过 frac。

    ego 题的 gold 先验天然倾斜(厨房工作区固定在一侧,右手操作),实测最高频能到
    27%;而 assemble.py 只均衡 gold **位置**,不均衡 gold **取值** —— 不封顶就能靠猜。
    做法:按 fact_id 排序后每个取值取前 m 个,m 取仍满足 frac 的最大值。
    """
    if not fs:
        return fs
    key = key or (lambda f: f["gold"])
    by = collections.defaultdict(list)
    for f in sorted(fs, key=lambda x: x["fact_id"]):
        by[key(f)].append(f)
    keys = sorted(by)
    best = [by[k][0] for k in keys]                  # 保底:每个取值各一条
    for m in range(2, max(len(v) for v in by.values()) + 1):
        kept = [f for k in keys for f in by[k][:m]]
        top = max(min(len(by[k]), m) for k in keys)
        if top > frac * len(kept):
            break
        best = kept
    return best


def mine_easy_ego(ix, rng, mode="right"):
    """L1 ego:放下某物那一刻,哪个物体在「我」最右(mode="right")/最左边。"""
    out = []
    for m in ix.movements:
        if SP._xyz(m.extra.get("end_xyz")) is None:
            continue
        t0, t1 = _win_around(ix, m.mid())
        r = SP.derive_ego_side(ix, m, t0, t1, mode)
        if not r:
            continue
        names = [r["gold"]] + [x[3] for x in r["present"]]
        if not SP.names_ok(names):
            continue
        d = clean_distractors([x[3] for x in r["present"]], r["gold"])
        if not d:
            continue
        eids = _sp_eids(m.eid, r["gold_eid"], [x[4] for x in r["present"]])
        out.append(_pack(ix.video_id, "Easy", "easy_spatial_side", "NEAREST",
                         t0, t1, r["gold"], eids, r["T"], d,
                         _ref_eid=m.eid, _mode=mode, _absent=[],
                         _anchor=r["anchor"], _lat_gold=round(r["lat_gold"], 3)))
    return _cap_by_gold(out)


def mine_low_ego(ix, rng, mode="left"):
    """L2 ego:声音定时刻,ego 方位给答案 —— 听到那一声时哪个物体在「我」左边。

    与 L1 的「最右」镜像,靠锚点类型区分(L1 用搬动、L2 用声音),正合 Low 层
    「声音给时间、画面给答案」的定义。
    (原本设计的是「哪个在你身后」,实测只有 22 条:要求物体窗口内**可见**
     与此刻在**身后**本就互相挤压 —— 身后的东西正是看不见的。已弃。)
    """
    out = []
    for s in PRIM.salient_sounds(ix):
        if s.label not in C.SOUND_PHRASE:
            continue
        t0, t1 = _win_around(ix, s.mid())
        if not (t0 <= s.t_start and s.t_end <= t1):
            continue
        r = SP.derive_ego_side(ix, s, t0, t1, mode)
        if not r:
            continue
        names = [r["gold"]] + [x[3] for x in r["present"]]
        if not SP.names_ok(names):
            continue
        d = clean_distractors([x[3] for x in r["present"]], r["gold"])
        if not d:
            continue
        eids = _sp_eids(s.eid, r["gold_eid"], [x[4] for x in r["present"]])
        out.append(_pack(ix.video_id, "Low", "low_spatial_side", "NEAREST",
                         t0, t1, r["gold"], eids, r["T"], d, s.label,
                         _ref_eid=s.eid, _mode=mode, _absent=[],
                         _lat_gold=round(r["lat_gold"], 3)))
    return _cap_by_gold(out)


# ---------- L3 推断 / L4 规划(2026-09-14 重排)----------

def _balance_gold(fs, slack=1.25):
    """类别型 gold(路线的四个象限)按类均衡:每类至多 ceil(最少类 × slack) 条。
    实测方向分布偏(右转 37% / 左转 16%),不均衡就能靠猜「右转」拿分。"""
    if not fs:
        return fs
    by = collections.defaultdict(list)
    for f in sorted(fs, key=lambda x: x["fact_id"]):
        by[f["gold"]].append(f)
    cap = max(1, math.ceil(min(len(v) for v in by.values()) * slack))
    return [f for k in sorted(by) for f in by[k][:cap]]


def _narr_eids(ix, t0, t1, k=5):
    return [e.eid for e in ix.in_window(t0, t1, "narration")][:k]


def mine_purpose(ix, rng):
    """L3 目的推断:听到某声音那一刻,摄像者想做什么?题面只给声音、**不点名动作**。
    (点名动作的旧版盲答 76%:「拿住碗 -> 为了稳住它」读题即可推出。)"""
    out = []
    for s in PRIM.salient_sounds(ix):
        if s.label not in C.SOUND_PHRASE:
            continue
        r = IN.sound_purpose(ix, s)
        if not r:
            continue
        e, p = r
        t0, t1 = _win_around(ix, s.mid())
        if not (t0 <= e.t_start and e.t_end <= t1 and t0 <= s.t_start and s.t_end <= t1):
            continue
        d, n_hard = IN.purpose_distractors(ix, e, t0, t1, rng)
        if not d:
            continue
        out.append(_pack(ix.video_id, "Medium", "medium_purpose", "PURPOSE", t0, t1, p["purpose"],
                         [s.eid, e.eid], s.mid(), d, s.label,
                         _ref_eid=e.eid, _sound_eid=s.eid, _n_hard=n_hard))
    return _cap_by_gold(out)


def _mine_goal(ix, rng, mode, tier, subtype):
    """总体目标:窗口须整个落在一个 recipe 段内;干扰项按 mode 取(见 infer.goal_options)。"""
    out = []
    segs = IN.recipe_segs(ix.video_id, ix.duration)
    if len({s[2] for s in segs}) < 4:
        return out
    for t0, t1 in _stride_wins(ix):
        k = IN.seg_containing(segs, t0, t1)
        eids = _narr_eids(ix, t0, t1) if k is not None else []
        if not eids:
            continue
        d = clean_distractors(IN.goal_options(ix, segs, k, t0, t1, mode, rng), segs[k][2])
        if not d:
            continue
        out.append(_pack(ix.video_id, tier, subtype, "GOAL", t0, t1, segs[k][2], eids,
                         (t0 + t1) / 2, d, _seg=k, _goal_mode=mode))
    return _cap_by_gold(out)


def mine_goal(ix, rng):
    """L3 总体目标(inference):干扰项与 gold 共用物体/动作,认物排除不了,须推断阶段。"""
    return _mine_goal(ix, rng, "inference", "Medium", "medium_goal")


def mine_goal_recog(ix, rng):
    """L1 总体目标(recognition):看一眼画面里的东西就能认出活动、排除干扰项。"""
    return _mine_goal(ix, rng, "recognition", "Easy", "easy_goal")


def mine_plan_next(ix, rng):
    """L4 下一步规划:段 k 末尾 30 s,问接下来做什么。当前段标签作陷阱干扰项
    (「正在做的」不等于「接下来要做的」),其余取其他视频的活动。"""
    out = []
    segs = IN.recipe_segs(ix.video_id, ix.duration)
    mine = {s[2] for s in segs}
    others = [x for x in IN.labels_other_videos(ix.video_id) if x not in mine]
    for k in range(len(segs) - 1):
        a, b = segs[k], segs[k + 1]
        w = IN.next_window(a)
        if a[2] == b[2] or not w:
            continue
        eids = _narr_eids(ix, *w)
        if not eids:
            continue
        pool = others[:]
        rng.shuffle(pool)
        # 当前步骤作陷阱(「正在做」≠「接下来做」)—— 但若它之后还会重复出现,当作错误的
        # 「下一步」就有歧义了(实测 'Stir saucepan' 等步骤会做好几轮),此时不用它
        later = {x[2] for x in segs[k + 1:]}
        trap = [a[2]] if a[2] not in later else []
        d = clean_distractors(trap + pool, b[2])
        if not d:
            continue
        out.append(_pack(ix.video_id, "High", "high_plan_next", "NEXT", w[0], w[1], b[2], eids,
                         w[1], d, _seg=k))
    return _cap_by_gold(out)


def mine_plan_next_action(ix, rng):
    """L4 下一动作(EgoPlan-Bench2 式):片段切在 gold 动作开始前 0.5 s,gold = 该 narration 的 verb+noun,
    题面给当前活动段标签作 goal;干扰项取同视频里语义类别不同、片段前后都不出现的动作。
    每 30 s 至多一条;goal 标签与 gold 共用词的不出;按 gold 动词封顶 15%。"""
    out, last = [], -1e9
    for e in sorted(ix.narrations, key=lambda x: x.t_start):
        d = IN.next_action_derive(ix, e)
        if not d or d["t1"] - last < 30:
            continue
        if FM.toks(d["goal"]) & FM.toks(d["gold"]):      # goal 标签与 gold 共用词 -> 题面会泄漏
            continue
        ds, relax = IN.next_action_distractors(ix, d, rng)
        if not ds:
            continue
        dd = clean_distractors([IN.action_phrase(x) for x in ds], d["gold"])
        if not dd:
            continue
        eids = _narr_eids(ix, d["t0"], d["t1"], k=99)[-3:]
        if not eids:
            continue
        out.append(_pack(ix.video_id, "High", "high_plan_next_action", "ACTION", d["t0"], d["t1"], d["gold"],
                         eids, d["t1"] - 1, dd, _ref_eid=e.eid, _goal=d["goal"], _seg=d["seg"],
                         _verb=d["pair"][0], _classes=list(d["classes"]), _dpairs=[list(x) for x in ds],
                         _relax=relax))
        last = d["t1"]
    return _cap_by_gold(out, frac=0.15, key=lambda f: f["_verb"])


def mine_replan(ix, rng):
    """L4 replan:只用人工核验过的候选(data/replan_verified.json);gold = 偏差后的实际纠正动作,
    片段切在纠正动作前 0.5 s,偏差时刻在片段内。干扰项:原计划动作 + 两个语义类别不同、片段前后不出现的动作。"""
    f = P.DATA / "replan_verified.json"
    if not f.exists():
        return []
    out = []
    segs = IN.recipe_segs(ix.video_id, ix.duration)
    for qid, r in json.loads(f.read_text()).items():
        if r["video"] != ix.video_id:
            continue
        try:
            rec, dev = ix.ev(r["rec_eid"]), ix.ev(r["dev_eid"])
        except KeyError:
            continue
        gp = IN.main_pair(rec)
        if not gp:
            continue
        t1 = round(rec.t_start - IN.CUT_BEFORE_ACT, 2); t0 = round(t1 - P.WIN_SEC, 2)
        if t0 < 0 or dev.t_start < t0:
            continue
        k = IN.seg_at(segs, t1) if segs else None
        goal = segs[k][2] if k is not None and segs[k][3] else None
        plan_e = next((x for x in sorted(ix.narrations, key=lambda x: x.t_start) if x.t_start < dev.t_start and IN.main_pair(x)
                       and IN.main_pair(x)[1] not in IN.TRIVIAL_NOUNS), None)
        plan_pair = IN.main_pair(plan_e) if plan_e else None
        ds, has_plan = IN.replan_distractors(ix, rec, plan_pair, t0, t1, rng, k)
        if not ds:
            continue
        dd = clean_distractors([IN.action_phrase(x) for x in ds], IN.action_phrase(gp))
        if not dd:
            continue
        eids = _narr_eids(ix, t0, t1, k=99)[-3:]
        draft = r.get("draft") or {}
        out.append(_pack(ix.video_id, "High", "high_replan", "REPLAN", t0, t1, IN.action_phrase(gp), eids, dev.t_start, dd,
                         _ref_eid=rec.eid, _dev_eid=dev.eid, _goal=goal, _situation=draft.get("situation") or r.get("dev_text"),
                         _plan_pair=list(plan_pair) if has_plan else None, _dev_type=draft.get("deviation_type"),
                         _dpairs=[list(x) for x in ds], _review_qid=qid))
    return _cap_by_gold(out, frac=0.40, key=lambda f: f.get("_dev_type") or "")


def mine_plan_trajectory(ix, rng):
    """L4 goal -> trajectory:只用人工核验过的任务(P.ANNOT/task_timeline_<video>.json 里 status=verified)。
    fact 的 t0/t1 是任务本身(证据 = 每步首条 narration);给模型看的片段是任务开始前 30 s(_clip)。"""
    import task_timeline as TT
    out = []
    for t in TT.verified(ix.video_id):
        steps = t["steps"]
        if not (TT.MIN_STEPS <= len(steps) <= TT.MAX_STEPS) or not t.get("goal") or not (TT.MIN_TASK <= t["dur"] <= TT.MAX_TASK):
            continue
        c0 = max(0.0, t["t0"] - P.WIN_SEC)
        clip = [round(c0, 2), round(t["t0"], 2)] if t["t0"] >= 10 else [round(t["t0"], 2), round(t["t0"] + 10, 2)]
        out.append(_pack(ix.video_id, "High", "high_plan_trajectory", "PLAN", t["t0"], t["t1"],
                         json.dumps([s["text"] for s in steps]), [s["eids"][0] for s in steps if s["eids"]], t["t0"], [],
                         _goal=t["goal"], _steps=[s["text"] for s in steps], _prereq=[], _task_id=t["task_id"], _clip=clip))
    return out


def mine_plan_next_step(ix, rng, use_draft=False):
    """L4 下一步(任务粒度):goal 句 + 任务进行到第 k 步末尾的 30 s 片段,问下一步做什么。
    gold = 第 k+1 步;干扰项 = 一个已做完的步骤(状态追踪)+ 一个更靠后的步骤(顺序)+ 一个别的任务的步骤。
    只用人工核验过的任务(use_draft=True 时也用草稿,仅供冒烟测试)。"""
    import task_timeline as TT
    tasks = [t for t in (TT.load(ix.video_id) if use_draft else TT.verified(ix.video_id))
             if TT.MIN_STEPS <= len(t["steps"]) <= TT.MAX_STEPS and t.get("goal")]
    out = []
    for t in tasks:
        steps = t["steps"]
        others = [s["text"] for o in tasks if o is not t for s in o["steps"]]
        for k in range(1, len(steps) - 1):               # 至少做完 1 步,且后面还有 >= 1 步可当「更靠后」干扰项
            cut = steps[k + 1]["t0"] - IN.CUT_BEFORE_ACT   # 片段在第 k+1 步开始前结束
            t1 = round(cut, 2); t0 = round(t1 - P.WIN_SEC, 2)
            if t0 < t["t0"] - 5 or t0 < 0:                 # 片段要基本落在任务内
                continue
            gold = steps[k + 1]["text"]
            done = [s["text"] for s in steps[:k + 1]]; later = [s["text"] for s in steps[k + 2:]]
            if not later or not done:
                continue
            d_done = rng.choice(done); d_later = rng.choice(later)
            pool = [o for o in others if _dnorm(o) not in {_dnorm(x) for x in (gold, d_done, d_later)}]
            if not pool:
                continue
            d_other = rng.choice(pool)
            dd = clean_distractors([d_done, d_later, d_other], gold)
            if not dd:
                continue
            eids = _narr_eids(ix, t0, t1, k=99)[-3:]
            if not eids:
                continue
            out.append(_pack(ix.video_id, "High", "high_plan_next_step", "STEP", t0, t1, gold, eids, t1 - 1, dd,
                             _goal=t["goal"], _task_id=t["task_id"], _k=k, _steps=[s["text"] for s in steps],
                             _done=done, _dkinds=["done", "later", "other"]))
    return _cap_by_gold(out, frac=0.15, key=lambda f: f["_task_id"])


def _obj_transitions(ix):
    by = collections.defaultdict(list)
    for m in ix.transitions:
        n = IN.clean_obj(IN.mv_name(m))
        if n:
            by[n].append(m)
    return {n: sorted(v, key=lambda m: (m.t_start, m.eid)) for n, v in sorted(by.items())}


def mine_plan_retrieve(ix, rng):
    """L4 跨场景取物:场景 1 看到 X 被放到某处;几分钟后场景 2 结束时要用 X —— 去哪拿?
    场景 2 截止在取回动作之前(否则看到取回就等于看到答案);X 期间不得被动过。
    干扰项先放 X 此前所在的位置(陷阱:记住的是旧位置),再补本视频其他设施。"""
    out = []
    vocab = IN.fixture_vocab(ix)
    for nm, ms in _obj_transitions(ix).items():
        for a, b in zip(ms, ms[1:]):
            gold = ix.fixture_pretty(a.extra.get("to_fixture"))
            if not gold or gold != ix.fixture_pretty(b.extra.get("from_fixture")):
                continue
            if not 60 <= b.t_start - a.t_end <= 600:
                continue
            A = IN.scene_a(ix, a)
            B = (round(b.t_start - 2 - P.WIN_SEC, 2), round(b.t_start - 2, 2))
            if not A or B[0] < A[1] + IN.MIN_SCENE_GAP or \
                    not IN.same_fixture(ix, nm, gold, a.t_end, B[1]):
                continue
            prev = ix.fixture_pretty(a.extra.get("from_fixture"))
            pool = [x for x in vocab if x not in (gold, prev)]
            rng.shuffle(pool)
            d = clean_distractors(([prev] if prev and prev != gold else []) + pool, gold)
            if not d:
                continue
            out.append(_pack(ix.video_id, "High", "high_plan_retrieve", "PLACE", A[0], B[1], gold,
                             [a.eid], a.mid(), d, _ref_eid=a.eid, _object=nm,
                             windows=[list(A), list(B)], _gap_s=round(B[0] - A[1], 1)))
    # 设施类别少且严重偏向台面(实测 104/131 = 79% 是 "the kitchen counter"),15% 封顶不现实;
    # 40% 保住 45 条,代价是盲猜「台面」的上限约 40%。根治要把位置细化到具体哪一块台面。
    return _cap_by_gold(out, frac=0.40)


def mine_plan_route(ix, rng):
    """L4 路线规划:场景 1 看到 X 被放下;场景 2 结束时要走过去拿 —— X 在观察者的哪个象限?
    方位由 SLAM 位姿与 X 的 3D 落点现算;要求相机稳定、距离 0.5–5 m、离象限边界(0/±90/180°)>= 15 度。"""
    out = []
    moves = IN.moves_by_obj(ix)
    for nm, ms in _obj_transitions(ix).items():
        for a in ms:
            if SP._xyz(a.extra.get("end_xyz")) is None:
                continue
            A = IN.scene_a(ix, a)
            if not A:
                continue
            nxt = min([m.t_start for m in moves.get(nm, []) if m.t_start > a.t_end] + [ix.duration])
            T = a.t_end + 90
            while T <= min(nxt - 5, a.t_end + 600, ix.duration):
                T2 = round(T, 2)
                B = (round(T2 - P.WIN_SEC, 2), T2)
                if B[0] >= A[1] + IN.MIN_SCENE_GAP:
                    r = IN.route_derive(ix.video_id, T2, a.extra["end_xyz"])
                    if r and 0.5 <= r[3] <= 5.0 and r[1] >= IN.MIN_ANGLE_MARGIN:
                        d = [x for x in IN.SECTORS if x != r[0]]
                        rng.shuffle(d)
                        out.append(_pack(ix.video_id, "High", "high_plan_route", "ROUTE", A[0], B[1],
                                         r[0], [a.eid], a.mid(), d, _ref_eid=a.eid, _object=nm,
                                         _T=T2, windows=[list(A), list(B)],
                                         _gap_s=round(B[0] - A[1], 1), _angle=round(r[2], 1),
                                         _angle_margin=round(r[1], 1)))
                        break                          # 每次放下只取一个时刻
                T += 60
    return _balance_gold(out)


def mine_gaze_destination(ix, rng):
    """L4 注视预判:片段截在放下之前,问手里的 X 接下来会放到哪(gold = to_fixture)。
    干扰项先放 X 的来处(陷阱:放回原处),再补本视频其他设施。"""
    import gaze as GZ
    out, vocab = [], IN.fixture_vocab(ix)
    for m in ix.movements:
        r = GZ.derive_destination(ix, m)
        if not r:
            continue
        pool = [x for x in vocab if x not in (r["gold"], r["prev"])]
        rng.shuffle(pool)
        d = clean_distractors([r["prev"]] + pool, r["gold"])
        if not d:
            continue
        out.append(_pack(ix.video_id, "High", "high_gaze_destination", "PLACE", r["t0"], r["t1"],
                         r["gold"], [m.eid], m.t_start, d, _ref_eid=m.eid, _object=r["object"],
                         _prime_gap=r["gap"], _from=r["prev"]))
    return _cap_by_gold(out, frac=0.40)


def mine_gaze_pickup(ix, rng):
    """L4 注视预判:片段截在拿起之前,问接下来会拿起哪个物体。干扰项是片段里看得到、随后没被拿起的物体。"""
    import gaze as GZ
    out = []
    for m in ix.movements:
        r = GZ.derive_pickup(ix, m)
        if not r:
            continue
        d, n_late = GZ.pickup_distractors(ix, r, rng)
        d = clean_distractors(d, r["gold"])
        if not d or not SP.names_ok([r["gold"]] + d):
            continue
        eids = [e.eid for e in ix.in_window(r["t0"], r["t1"], "narration")][-3:]
        if not eids:
            continue
        out.append(_pack(ix.video_id, "High", "high_gaze_pickup", "OBJECT", r["t0"], r["t1"],
                         r["gold"], eids, r["t1"] - 1, d, _ref_eid=m.eid,
                         _prime_gap=r["gap"], _n_late_distractors=n_late))
    return _cap_by_gold(out)


# 取物规划(mine_plan_retrieve)暂不启用:盲答 65% —— gold 79% 是「台面」,且「酸奶 -> 冰箱」
# 这类常识不看视频就能答。细化到设施实例后供给不足 51 条且挡不住单实例设施的常识,待重新设计。
INFER_PLAN_MINERS = [("Medium", "purpose", mine_purpose), ("Medium", "goal", mine_goal),
                     ("Easy", "goal_recog", mine_goal_recog),
                     ("High", "plan_next", mine_plan_next),
                     ("High", "plan_next_action", mine_plan_next_action),
                     ("High", "replan", mine_replan),
                     ("High", "plan_trajectory", mine_plan_trajectory),
                     ("High", "plan_next_step", mine_plan_next_step),
                     ("High", "plan_route", mine_plan_route),
                     ("High", "gaze_destination", mine_gaze_destination),
                     ("High", "gaze_pickup", mine_gaze_pickup)]

# 排序题下放到 L3(推断层),L4 腾给规划题。子类改名、fact_id 随之重算。
ORDER_DOWN = {"high_order": "medium_order", "high_spatial_order": "medium_spatial_order"}
# 目的推断下放到 L2(2026-09-28):声音定一个时刻、那条 narration 的目的从句给答案 ——
# 正是 L2「声音定时刻 + 另一信号给答案」的证据结构,不需要通看窗口。
# 挖掘仍走原来的 ("Medium", "purpose") rng 流,干扰项逐字节不变,已有实测可直接沿用。
PURPOSE_DOWN = {"medium_purpose": "low_purpose"}


MINERS = {"Easy": mine_easy, "Low": mine_low, "Medium": mine_medium, "High": mine_high}

EGO_MINERS = {"Easy": mine_easy_ego, "Low": mine_low_ego}

def _variant(miner, mode):
    """关系变体:子类名不变、_mode 取默认之外的另一值,供选题器挑「问哪种关系」。

    fact_id 原本不含 _mode —— 同一锚点的 left/right 若恰好同 gold 同证据就会撞 id。
    所以变体把 mode 编进 id;默认 mode 的 id 不动,已有题库与 usage.json 不受影响。
    """
    def run(ix, rng):
        out = []
        for f in miner(ix, rng, mode):
            f["fact_id"] = _fid(f["video_id"], f"{f['subtype']}#{mode}", f["gold"],
                                f["evidence_event_ids"], f["t0"])
            out.append(f)
        return out
    return run


VARIANT_MINERS = {"Easy": _variant(mine_easy_ego, "left"),
                  "Low": _variant(mine_low_ego, "right"),
                  "Medium": _variant(mine_medium_spatial, "near")}

SPATIAL_MINERS = {"Easy": mine_easy_spatial, "Low": mine_low_spatial,
                  "Medium": mine_medium_spatial, "High": mine_high_spatial}


def mine_video(video):
    """挖一个视频的全部四层,带磁盘缓存。"""
    P.ensure_dirs()
    f = P.DATA / f"facts_{video}.json"
    if f.exists():
        return json.loads(f.read_text())
    ix = TimelineIndex(video)
    facts = {}
    for tier, miner in MINERS.items():
        rng = random.Random(f"{P.SEED}|{video}|{tier}")
        facts[tier] = miner(ix, rng)
    # 空间子类走**独立的 rng 流**:现有子类的 fact_id 因此逐字节不变,
    # usage.json 的复用记账与已生成的题套继续有效。
    for tier, miner in SPATIAL_MINERS.items():
        rng = random.Random(f"{P.SEED}|{video}|{tier}|spatial")
        facts[tier] = facts.get(tier, []) + miner(ix, rng)
    # ego 再一条独立 rng 流(同理:不扰动上面两族已有的 fact_id)
    for tier, miner in EGO_MINERS.items():
        rng = random.Random(f"{P.SEED}|{video}|{tier}|ego")
        facts[tier] = facts.get(tier, []) + miner(ix, rng)
    # 关系变体(near / 反方向 ego):第四条独立 rng 流
    for tier, miner in VARIANT_MINERS.items():
        rng = random.Random(f"{P.SEED}|{video}|{tier}|variant")
        facts[tier] = facts.get(tier, []) + miner(ix, rng)
    # L3 推断 / L4 规划:各自独立 rng 流
    for tier, stream, miner in INFER_PLAN_MINERS:
        rng = random.Random(f"{P.SEED}|{video}|{tier}|{stream}")
        facts[tier] = facts.get(tier, []) + miner(ix, rng)
    keep, moved = [], []
    for fc in facts.get("High", []):          # 别用 f:外层的 f 是缓存文件路径
        if fc["subtype"] in ORDER_DOWN:
            fc["subtype"], fc["tier"] = ORDER_DOWN[fc["subtype"]], "Medium"
            fc["fact_id"] = _fid(fc["video_id"], fc["subtype"], fc["gold"],
                                 fc["evidence_event_ids"], fc["t0"])
            moved.append(fc)
        else:
            keep.append(fc)
    facts["High"], facts["Medium"] = keep, facts.get("Medium", []) + moved
    keep, moved = [], []
    for fc in facts.get("Medium", []):
        if fc["subtype"] in PURPOSE_DOWN:
            fc["subtype"], fc["tier"] = PURPOSE_DOWN[fc["subtype"]], "Low"
            fc["fact_id"] = _fid(fc["video_id"], fc["subtype"], fc["gold"],
                                 fc["evidence_event_ids"], fc["t0"])
            moved.append(fc)
        else:
            keep.append(fc)
    facts["Medium"], facts["Low"] = keep, facts.get("Low", []) + moved
    f.write_text(json.dumps(facts, ensure_ascii=False))
    return facts


def load_all():
    """{tier: [fact,...]} 跨 5 个视频合并。"""
    pool = collections.defaultdict(list)
    for v in P.VIDEOS:
        for tier, fs in mine_video(v).items():
            pool[tier].extend(fs)
    return pool


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()
    pool = load_all()
    print(f"{'tier':8s} {'total':>6s}  per-video / per-subtype")
    for tier, _ in P.LEVELS:
        fs = pool[tier]
        bv = collections.Counter(f["video_id"][:3] for f in fs)
        bs = collections.Counter(f["subtype"] for f in fs)
        print(f"{tier:8s} {len(fs):6d}  {dict(bv)}  {dict(bs)}")
