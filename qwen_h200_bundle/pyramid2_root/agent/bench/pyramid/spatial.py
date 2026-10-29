"""空间事实的挖掘与重推 —— facts.py 与 verify.py 共用的唯一真相源。

四层共用一个基元:**某个命名物体在某一时刻的静止位置**。难度差异全部由
「要整合窗口里多少信息」承担,题型本身不变,于是 L1->L4 的落差可以干净地
归给空间推理,而不会和题型变化混淆。

3D 来源:timeline.json 的 movement 事件自带 extra.start_xyz / end_xyz
(HD-EPIC 数字孪生,覆盖约 98%),坐标是**场景固定的真实米制**世界系 ——
同一 fixture 在整段录制中的观测 std 只有 0.05-0.2 m。

设计上刻意避开的三条死路(实测,不要再走回头路):
1. 「挨着哪个电器」—— 厨房 landmark 质心本就挤在一起(hob<->oven 0.47 m),
   且嵌入式电器就在台面正下方,严格门限下全库只剩 20 条。
2. 「在什么高度」—— 4500 次观测里 3600 次在台面高度,gold 先验可直接猜。
3. 「被搬了多远」—— 中位位移只有 0.10-0.20 m,分不开。
"""
import math
import primitives as PRIM

# ---- 阈值(全部以米为单位)----
NEAR_L1 = 0.8      # L1 gold 必须真的「近」
MARG = 0.4         # gold 与最近的干扰项之间的距离余量
NEAR_L2 = 1.0      # L2 放宽一点:声音锚点已经贡献了难度
MARG_L2 = 0.35
MARG_L3 = 0.4      # 极值层:gold 与次名的余量
GAP_L4 = 0.4       # 排序层:三元组相邻间隔

MIN_CAND = 4       # 至少要有 4 个候选才能凑出四选一


def _xyz(v):
    return v if (isinstance(v, (list, tuple)) and len(v) == 3) else None


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def mv_name(m):
    return (m.extra.get("object_name") or m.text or "").strip()


def _clean_name(nm):
    """物体名可用 <=> 非空、非固定设施、非标注流水线产物。"""
    if not nm:
        return None
    if PRIM.is_fixture(nm) or PRIM.is_artifact(nm):
        return None
    # 标注里的 "unknown pan" / "spoon-unknown" / "unknown" 是残名,不是能在画面里认出的物体
    if "unknown" in nm.lower():
        return None
    n = PRIM._norm(nm)
    return n or None


_MOVABLE_CACHE = {}


def movables(ix):
    """该视频里所有「带 3D 且物体名干净」的 movement,按归一化物体名分组。

    分组键用 PRIM._norm(剥尾部数字),与现有 OBJECT 子类的 gold 形态一致 ——
    "egg 1"/"egg 2" 本就该视为同一种东西。
    """
    key = ix.video_id
    if key in _MOVABLE_CACHE:
        return _MOVABLE_CACHE[key]
    by = {}
    for m in ix.movements:
        if _xyz(m.extra.get("start_xyz")) is None or _xyz(m.extra.get("end_xyz")) is None:
            continue
        n = _clean_name(mv_name(m))
        if not n:
            continue
        by.setdefault(n, []).append(m)
    for n in by:
        by[n].sort(key=lambda e: (e.t_start, e.eid))
    _MOVABLE_CACHE[key] = by
    return by


_VIS_CACHE = {}


def visible_norm(ix, t0, t1):
    """窗口内视觉可见的物体名(归一化)。用 assoc track 覆盖判定。"""
    key = (ix.video_id, round(t0, 2), round(t1, 2))
    if key not in _VIS_CACHE:
        _VIS_CACHE[key] = {PRIM._norm(x) for x in ix.visible_in(t0, t1)}
    return _VIS_CACHE[key]


def rest_at(ix, name, T, t0, t1):
    """物体 name 在时刻 T 的**可证明静止**位置。

    只有两种情形算数:
    - 某次 movement 在 T 之前结束(t_end <= T),且该物体在 (t_end, T) 内
      没有新的 movement 起始 —— 那么它一直停在 end_xyz;
    - 某次 movement 在 T 之后开始(t_start >= T),且该物体在 (T, t_start) 内
      没有 movement 结束 —— 那么它此前一直停在 start_xyz。

    样本时刻必须落在 [t0, t1] 内:这同时保证了它所属的事件与窗口重叠,
    满足 evidence_event_ids 的契约。多个候选取时间上离 T 最近的。

    返回 (xyz, eid, t_sample) 或 None。
    """
    ms = movables(ix).get(name)
    if not ms:
        return None
    best = None
    for m in ms:
        te, ts = m.t_end, m.t_start
        if te <= T and t0 <= te <= t1:
            if not any(x.t_start > te and x.t_start < T for x in ms):
                c = (T - te, m.eid, m.extra["end_xyz"], te)
                if best is None or c[:2] < best[:2]:
                    best = c
        if ts >= T and t0 <= ts <= t1:
            if not any(x.t_end < ts and x.t_end > T for x in ms):
                c = (ts - T, m.eid, m.extra["start_xyz"], ts)
                if best is None or c[:2] < best[:2]:
                    best = c
    return (best[2], best[1], best[3]) if best else None


def interp_xyz(m, T):
    """movement 进行中的位置:起讫点线性插值。确定性,verify 可逐位重推。"""
    a, b = m.extra["start_xyz"], m.extra["end_xyz"]
    span = m.t_end - m.t_start
    f = 0.0 if span <= 0 else max(0.0, min(1.0, (T - m.t_start) / span))
    return [a[i] + f * (b[i] - a[i]) for i in range(3)]


def rank_others(ix, ref_name, p, T, t0, t1):
    """窗口内除 ref 外所有物体,按到点 p 的距离升序。

    返回 [(d, name, eid), ...]。同距按名字排序,保证确定性。
    """
    vis = visible_norm(ix, t0, t1)
    rh = PRIM._head_noun(ref_name)
    out = []
    for n in movables(ix):
        if n == ref_name:
            continue
        if n not in vis:                  # 画面里看不见的,不该成为选项
            continue
        # 与参照同头名词的一律排除:参照 "some cling film" 配上选项
        # "roll of cling film",题面读者分不清问的是哪一个。
        if PRIM._head_noun(n) == rh:
            continue
        r = rest_at(ix, n, T, t0, t1)
        if r is None:
            continue
        out.append((dist(p, r[0]), n, r[1]))
    out.sort(key=lambda x: (x[0], x[1]))
    return out


# ---------- 通用门 ----------

def names_ok(names):
    """选项两两头名词不同(verify.py:49 会剥尾部数字,knife3 与 knife 会撞)。"""
    heads = [PRIM._head_noun(n) for n in names]
    return len(set(heads)) == len(heads) and all(heads)


def ref_gold_disjoint(ref, gold):
    """离线模板会写出 ref,而 MEM.contains_gold 是纯子串判定 ——
    ref="spoon holder" / gold="spoon" 会自我否决。"""
    return gold not in ref and ref not in gold


# ---------- 各层重推 ----------

def derive_l1(ix, m, t0, t1):
    """L1:以某次 movement 的落点为参照,问窗口内哪个物体离它最近。

    m 是参照 movement(fact["_ref_eid"] 取回)。
    """
    ref = _clean_name(mv_name(m))
    if not ref:
        return None
    T, p = m.t_end, m.extra.get("end_xyz")
    if _xyz(p) is None or not (t0 <= T <= t1):
        return None
    ranked = rank_others(ix, ref, p, T, t0, t1)
    if len(ranked) < MIN_CAND:
        return None
    d0, gold, geid = ranked[0]
    if d0 > NEAR_L1:
        return None
    far = [r for r in ranked[1:] if r[0] >= d0 + MARG]
    if len(far) < 3:
        return None
    return {"gold": gold, "ref": ref, "d_gold": d0, "gold_eid": geid,
            "present": far[:3], "ranked": ranked, "T": T}


def derive_l2(ix, s, t0, t1):
    """L2:声音定时刻,几何给答案。

    s 是锚点声音。复用 PRIM.find_low 的「±1.5s 内恰好一个 movement」唯一性门,
    被操作物体的位置由该 movement 起讫点在 s.mid() 处线性插值得到。
    """
    r = PRIM.find_low(ix, s)
    if not r:
        return None
    m = ix.ev(r["eids"][1])
    if _xyz(m.extra.get("start_xyz")) is None or _xyz(m.extra.get("end_xyz")) is None:
        return None
    ref = _clean_name(mv_name(m))
    if not ref:
        return None
    T = s.mid()
    if not (t0 <= T <= t1):
        return None
    p = interp_xyz(m, T)
    ranked = rank_others(ix, ref, p, T, t0, t1)
    if len(ranked) < 2:
        return None
    d0, gold, geid = ranked[0]
    if d0 > NEAR_L2:
        return None
    far = [x for x in ranked[1:] if x[0] >= d0 + MARG_L2]
    # 实测「3 个存在型干扰项」只剩 46 条不可用;2 个存在型已足以维持空间区分度
    # (仍无法靠「在不在画面里」作答),第 3 个用已验证的缺席证明补足。
    if len(far) < 2:
        return None
    return {"gold": gold, "ref": ref, "d_gold": d0, "gold_eid": geid,
            "present": far[:2], "ranked": ranked, "T": T, "mv_eid": m.eid}


def derive_l3(ix, ref, t0, t1, mode="far"):
    """L3:通览整个窗口,问离参照**最远**的那个(mode="far")。

    T 取 t1 —— 即「这段片子结束时各物体的最终位置」,强制看完全程。
    """
    T = t1
    rr = rest_at(ix, ref, T, t0, t1)
    if rr is None:
        return None
    ranked = rank_others(ix, ref, rr[0], T, t0, t1)
    if len(ranked) < MIN_CAND:
        return None
    if mode == "far":
        d0, gold, geid = ranked[-1]
        if d0 - ranked[-2][0] < MARG_L3:
            return None
        others = ranked[:3]
    else:
        d0, gold, geid = ranked[0]
        if ranked[1][0] - d0 < MARG_L3:
            return None
        others = ranked[-3:]
    if len(others) < 3:
        return None
    return {"gold": gold, "ref": ref, "d_gold": d0, "gold_eid": geid,
            "present": others, "ranked": ranked, "T": T, "ref_eid": rr[1]}


def derive_l4(ix, ref, t0, t1):
    """L4:三个物体按到参照的远近排序,由近及远。

    取「间隔最好」的三元组:按距离序扫描,第一个满足两个相邻间隔都 >= GAP_L4 的组合。
    """
    T = t1
    rr = rest_at(ix, ref, T, t0, t1)
    if rr is None:
        return None
    ranked = rank_others(ix, ref, rr[0], T, t0, t1)
    if len(ranked) < 3:
        return None
    n = len(ranked)
    for i in range(n - 2):
        for j in range(i + 1, n - 1):
            if ranked[j][0] - ranked[i][0] < GAP_L4:
                continue
            for k in range(j + 1, n):
                if ranked[k][0] - ranked[j][0] < GAP_L4:
                    continue
                tri = [ranked[i], ranked[j], ranked[k]]
                names = [x[1] for x in tri]
                if not names_ok(names):
                    continue
                return {"gold": " -> ".join(names), "ref": ref,
                        "triple": tri, "ranked": ranked, "T": T,
                        "ref_eid": rr[1], "dists": [round(x[0], 3) for x in tri]}
    return None


# ---------- 干扰项证伪 ----------

# ---------- ego(相机为参照,需要 SLAM 位姿)----------

EGO_MIN_R, EGO_MAX_R = 0.2, 2.5   # 相机—物体距离的可用带
EGO_MARG = 0.30                   # 左右题:gold 与次名的横向余量
BEHIND_F = -0.2                    # 判为「身后」的前向阈值
BEHIND_MARG = 0.30                # 身后题:gold 与次靠后的前向余量
FRONT_F = 0.3                     # 判为「身前」的前向阈值


def ego_cands(ix, T, t0, t1):
    """T 时刻窗口内每个可见物体在 device frame 的方位。

    返回 [(forward, lateral, rng, name, eid)],按名字排序保证确定性;
    相机在该时刻不稳定(边走边转)或位姿质量不达标时返回 None ——
    「我的左边」只在相机稳定时才有确定所指。
    """
    import pose as POSE
    p = POSE.at(ix.video_id, T)
    if p is None:
        return None
    cam, R = p
    vis = visible_norm(ix, t0, t1)
    out = []
    for n in movables(ix):
        if n not in vis:
            continue
        r = rest_at(ix, n, T, t0, t1)
        if r is None:
            continue
        f_, l_, _, rng = POSE.to_device(cam, R, r[0])
        if not (EGO_MIN_R <= rng <= EGO_MAX_R):
            continue
        out.append((f_, l_, rng, n, r[1]))
    out.sort(key=lambda x: x[3])
    return out


def derive_ego_side(ix, e, t0, t1, mode="right"):
    """L1 ego:那一刻哪个物体在「我」最右(或最左)边。

    lateral 为 +左 / -右,所以「最右」= lateral 最小。
    """
    T = e.t_end if e.source == "movement" else e.mid()
    if not (t0 <= T <= t1):
        return None
    cands = ego_cands(ix, T, t0, t1)
    if not cands:
        return None
    anchor = _clean_name(mv_name(e)) if e.source == "movement" else None
    if anchor:
        # 锚点物体本身不能当选项:题面要说「放下 X 那一刻」,X 若同时是 gold 就泄漏了。
        ah = PRIM._head_noun(anchor)
        cands = [c for c in cands if c[3] != anchor and PRIM._head_noun(c[3]) != ah]
    if len(cands) < MIN_CAND:
        return None
    key = (lambda x: x[1]) if mode == "right" else (lambda x: -x[1])
    s = sorted(cands, key=lambda x: (key(x), x[3]))
    if key(s[1]) - key(s[0]) < EGO_MARG:
        return None
    gold = s[0]
    others = list(reversed(s[-3:]))          # 最偏另一侧的三个,证伪最清晰
    if len(others) < 3:
        return None
    return {"gold": gold[3], "gold_eid": gold[4], "mode": mode, "anchor": anchor,
            "lat_gold": gold[1], "present": others, "cands": cands, "T": T}


def derive_ego_behind(ix, e, t0, t1):
    """L2 ego:那一刻哪个物体在「我」身后 —— 画面里看不见,必须靠整段运动推。

    取前向最小(最靠后)的那个,要求它确实在身后、且与次靠后的拉开 BEHIND_MARG。
    (不要求「恰好一个在身后」—— 实测那道门只剩 25 条,不够组卷。)
    干扰项取最靠前的三个,全部明确在身前,证伪清晰。
    """
    T = e.t_end if e.source == "movement" else e.mid()
    if not (t0 <= T <= t1):
        return None
    cands = ego_cands(ix, T, t0, t1)
    if not cands or len(cands) < MIN_CAND:
        return None
    s = sorted(cands, key=lambda x: (x[0], x[3]))
    gold = s[0]
    if gold[0] >= BEHIND_F:                 # gold 必须真在身后
        return None
    if s[1][0] - gold[0] < BEHIND_MARG:     # 与次靠后的拉开,否则「最靠后」有歧义
        return None
    others = sorted(cands, key=lambda x: (-x[0], x[3]))[:3]
    if any(c[0] <= FRONT_F for c in others):
        return None                          # 三个干扰项必须都明确在身前
    return {"gold": gold[3], "gold_eid": gold[4], "mode": "behind",
            "fwd_gold": gold[0], "present": others, "cands": cands, "T": T}


def check_ego(ix, item, fact, errs, r):
    """ego 类的干扰项证伪 —— 全部用 verify 当场重推出来的 r,不读 fact 里存的几何量。"""
    t0, t1 = item["t0"], item["t1"]
    gold = item["answer"]
    mode = fact.get("_mode", "right")
    cm = {c[3]: c for c in r["cands"]}

    if PRIM._norm(gold) not in visible_norm(ix, t0, t1):
        errs.append("gold 物体在窗口内不可见")
    gh = PRIM._head_noun(gold)
    for d in item["_distractors"]:
        dn = PRIM._norm(d)
        if PRIM._head_noun(d) == gh:
            errs.append(f"干扰项 '{d}' 与 gold 同头名词")
        c = cm.get(dn)
        if c is None:
            errs.append(f"干扰项 '{d}' 无法在窗口内重推方位")
            continue
        if mode == "behind":
            if c[0] <= FRONT_F:
                errs.append(f"干扰项 '{d}' 前向 {c[0]:.2f} 未明确在身前")
        else:
            k = (lambda x: x[1]) if mode == "right" else (lambda x: -x[1])
            if k(c) - k(cm[PRIM._norm(gold)]) < EGO_MARG:
                errs.append(f"干扰项 '{d}' 横向与 gold 差 {k(c)-k(cm[PRIM._norm(gold)]):.2f} 不足")


def check_nearest(ix, item, fact, errs, r, far_mode=False):
    """NEAREST 类的干扰项证伪。

    `r` 必须是 verify 当场用 derive_* **重推出来**的结果,不是 fact 里存的值 ——
    这样几何量全部现算,fact 的 _d_gold / _ref 只作调试留痕,不参与判定。

    每个干扰项要么 (a) 在窗口内**存在**且重推距离与 gold 拉开余量,
    要么 (b) 在 [t0-2, t1+2] 内**不存在**(沿用 verify._check_object 的既有证明)。
    """
    import verify as V          # 延迟导入:verify 也 import 本模块
    t0, t1 = item["t0"], item["t1"]
    gold = item["answer"]
    absent = {PRIM._norm(x) for x in (fact.get("_absent") or [])}
    marg = fact.get("_marg", MARG)
    dmap = {n: d for d, n, _ in r["ranked"]}
    d_gold = r["d_gold"]

    if PRIM._norm(gold) not in visible_norm(ix, t0, t1):
        errs.append("gold 物体在窗口内不可见")
    if not ref_gold_disjoint(r["ref"], gold):
        errs.append("参照与 gold 互为子串")

    around = V._window_objects(ix, t0 - 2, t1 + 2)
    gh = PRIM._head_noun(gold)
    for d in item["_distractors"]:
        dn = PRIM._norm(d)
        if PRIM._head_noun(d) == gh:
            errs.append(f"干扰项 '{d}' 与 gold 同头名词")
        if dn in absent:
            if dn in around:
                errs.append(f"缺席型干扰项 '{d}' 其实在窗口内")
            continue
        dd = dmap.get(dn)
        if dd is None:
            errs.append(f"干扰项 '{d}' 无法在窗口内重推位置")
        elif far_mode:
            if dd > d_gold - marg:
                errs.append(f"干扰项 '{d}' 距离 {dd:.2f} 未比 gold({d_gold:.2f}) 近足够")
        elif dd < d_gold + marg:
            errs.append(f"干扰项 '{d}' 距离 {dd:.2f} 未比 gold({d_gold:.2f}) 远足够")
