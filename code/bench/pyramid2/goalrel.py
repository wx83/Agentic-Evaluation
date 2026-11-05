"""11-03 v28(用户定):题目必须和最终 goal 有关 —— 问到的物体 / fixture 必须出现在 goal、sub-goal 文字或 planner event 的 objects 里
(fixture 另加:goal 物体被放到 / 拿起的 fixture)。只做池子后过滤,不改各 builder;contract["goal_relevance"] 为真时启用。"""
import collections
import sg as SG

_FIX_WORDS = {"sink", "counter", "hob", "stove", "cooker", "oven", "fridge", "freezer", "bin", "dishwasher", "microwave", "table", "cupboard", "drawer", "shelf",
              "washing machine", "boiler", "worktop", "countertop", "tap", "faucet", "kettle", "toaster"}
_FIX_ALIAS = {"stove": "hob", "cooker": "hob", "worktop": "counter", "countertop": "counter", "freezer": "fridge", "fridgefreezer": "fridge", "tap": "sink", "faucet": "sink"}


def _norm_fix(k):
    k = (k or "").lower().strip()
    return _FIX_ALIAS.get(k, k)


def goal_sets(store, ti, plan):
    """返回 (物体 token 集, fixture 名集)。"""
    toks = _t(ti.get("goal") or "")
    for s in ti.get("steps") or []: toks |= _t(s.get("text") or "")
    for sg_ in (plan or {}).get("sub_goals") or []:
        for e in sg_.get("events") or []:
            for o in e.get("objects") or []: toks |= _t(o)
    fix = {_norm_fix(w) for w in _FIX_WORDS if SG._stem(w) in toks or w in toks}
    for w in list(toks):
        if w in _FIX_ALIAS or w in _FIX_WORDS: fix.add(_norm_fix(w))
    vid = ti["video_id"]
    for r in SG._recs(store, vid, ti["t0"], ti["t1"], kinds={"object_move"}):       # goal 物体被放到 / 拿起的 fixture 也算 goal 相关
        v = r["value"] or {}
        if _t(v.get("object_name") or "") & toks:
            for k in ("from_fixture_kind", "to_fixture_kind"):
                f = _norm_fix(v.get(k))
                if f and f != "mid-air": fix.add(f)
    return toks, fix


_SPELL = {"yoghurt": "yogurt", "chilli": "chili", "chillies": "chili", "courgette": "zucchini", "coriander": "cilantro", "aubergine": "eggplant"}


def _t(s):
    return {_SPELL.get(w, w) for w in SG._toks(s or "")} | {_SPELL.get(w, w) for w in (s or "").lower().split()}


def _rel_obj(name, toks): return bool(_t(name) & toks)
def _rel_fix(name, fix): return _norm_fix(name) in fix


def asked(c):
    """一个 cluster 问到的 (物体列表, fixture 列表);都为空 = 这个 skill 没有可过滤的对象(事件本身就来自 goal)。"""
    sg_ = c.get("sg") or {}
    objs, fixs = [], []
    if sg_.get("ed"): objs = [sg_["ed"].get("object")]
    elif sg_.get("sc"):
        sc = sg_["sc"]; objs = [sc.get("object")]
        if sc.get("type") in ("nearest_before", "nearest_after"): objs.append(sc.get("answer"))
        elif sc.get("type") == "closer_farther": objs.append(sc.get("reference"))
    elif sg_.get("rf"):
        rf = sg_["rf"]
        fixs = [rf["fixture"]] if rf.get("skill") == "fixture_clock_direction" else [rf.get("F1"), rf.get("F3")]
    elif sg_.get("box_choice"): objs = [sg_.get("object")]
    return [o for o in objs if o], [f for f in fixs if f]


def filter_pool(cap, clusters, store, ti, plan):
    toks, fix = goal_sets(store, ti, plan)
    keep, drop = [], collections.Counter()
    for c in clusters:
        objs, fixs = asked(c)
        bad = [o for o in objs if not _rel_obj(o, toks)] + [f for f in fixs if not _rel_fix(f, fix)]
        if bad:
            drop[", ".join(bad)] += 1
            c.setdefault("sg", {})["goal_irrelevant"] = bad
        else: keep.append(c)
    return keep, drop, (sorted(toks), sorted(fix))
