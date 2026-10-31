"""四个难度层的出题器。每层都必须：唯一性闸门 -> 定窗 -> 窗口内重算 gold。"""
import re, random
import config as C

CAUSAL_LEAD, CAUSAL_LAG = 1.0, 2.0
UNIQ_W = 15.0          # 同标签声音在 ±15s 内唯一，"当你听到X那一刻"才有唯一所指
MIN_GAP_HIGH = 2.0     # High 层三事件最小间隔


def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"\d+$", "", (s or "").strip().lower())).strip()


ARTIFACT = re.compile(r"^track\s*\d+|skipped", re.I)


def is_artifact(name):
    """'track 203 (skipped)' 是标注流水线的产物，不是真实物体。"""
    return bool(ARTIFACT.search(name or ""))


def is_fixture(name):
    """'drawer of refrigerator' 这类复合名也必须判为固定设施。"""
    n = _norm(name)
    return any(re.search(rf"\b{re.escape(w)}\b", n) for w in C.FIXTURE_NOUNS)


def _head_noun(s):
    t = _norm(s).split()
    return t[-1] if t else ""


def salient_sounds(ix):
    """显著声音锚点：可命名、够长、同标签在 ±15s 内唯一。"""
    nameable = ix.nameable_sounds()
    out = []
    for s in ix.sounds:
        if s.label not in nameable:
            continue
        if (s.t_end - s.t_start) < 0.2 and s.label not in C.IMPULSIVE:
            continue
        near = [x for x in ix.by_sound_label[s.label]
                if x is not s and x.t_start < s.t_end + UNIQ_W and x.t_end > s.t_start - UNIQ_W]
        if near:
            continue
        out.append(s)
    return out


# ---------- 各层的候选发现（定窗前） ----------

def find_easy(ix, s):
    """Easy：声音与可见物体互相印证。恰好一个可见物体与该声音对应。"""
    hints = C.SOUND_OBJECT_HINT.get(s.label)
    if not hints:
        return None
    vis = ix.visible_at(s.mid())
    hit = [n for n in vis if any(h in n.lower() for h in hints)]
    if len(hit) != 1 or is_fixture(hit[0]) or is_artifact(hit[0]):
        return None
    return {"gold": _norm(hit[0]), "kind": "OBJECT", "eids": [s.eid], "sound": s}


def find_low(ix, s):
    """Low：声音给时间锚点，画面给答案。±1.5s 内恰好一个 movement。"""
    hit = [m for m in ix.movements if abs(m.t_start - s.mid()) <= 1.5 or
           (m.t_start <= s.mid() <= m.t_end)]
    hit = [m for m in hit if (m.extra.get("object_name") or "").strip()]
    if len(hit) != 1:
        return None
    obj = _norm(hit[0].extra["object_name"])
    if not obj or is_fixture(obj) or is_artifact(obj):
        return None
    return {"gold": obj, "kind": "OBJECT", "eids": [s.eid, hit[0].eid], "sound": s}


def find_medium(ix, s, t0, t1):
    """Medium：窗口内某声音标签出现 2-6 次，问次数。定窗后才算得准。"""
    n = len(ix.sounds_between(t0, t1, s.label))
    if not (2 <= n <= 6):
        return None
    return {"gold": str(n), "kind": "COUNT", "eids": [s.eid], "sound": s}


def find_high(ix, t0, t1):
    """High：窗口内三条 narration，标签互异且相邻间隔 >=2s，问先后顺序。"""
    ns = sorted([n for n in ix.in_window(t0, t1, "narration") if n.label],
                key=lambda e: e.t_start)
    seen, uniq = set(), []
    for n in ns:
        if n.label in seen:
            continue
        if uniq and n.t_start - uniq[-1].t_start < MIN_GAP_HIGH:
            continue
        seen.add(n.label); uniq.append(n)
    if len(uniq) < 3:
        return None
    tri = uniq[:3]
    return {"gold": " -> ".join(_action(e) for e in tri), "kind": "ORDER",
            "eids": [e.eid for e in tri], "events": tri}


def _action(e):
    """narration 的 label 形如 'open/refrigerator door'，转成可读动作。"""
    lab = e.label
    if "/" in lab:
        v, n = lab.split("/", 1)
        return f"{v.split('+')[0].strip()} the {n.split('+')[0].strip()}"
    return lab


# ---------- 干扰项 ----------

def distractors(ix, kind, gold, t0, t1, rng, sound_label=None):
    if kind == "COUNT":
        g = int(gold)
        pool = [str(x) for x in (g - 2, g - 1, g + 1, g + 2) if x >= 0 and x != g]
        return rng.sample(pool, 3) if len(pool) >= 3 else None

    if kind == "SOUND":
        inw = {s.label for s in ix.sounds_between(t0 - 2, t1 + 2)}
        cluster = lambda l: set(re.split(r"[ /]+", l)) & {"collision"}
        pool, used_coll = [], 0
        for l, evs in sorted(ix.by_sound_label.items(), key=lambda kv: -len(kv[1])):
            if l in inw or l in C.SKIP_SOUNDS or l not in C.SOUND_PHRASE:
                continue
            if cluster(l) and cluster(sound_label or ""):
                if used_coll >= 1:
                    continue
                used_coll += 1
            pool.append(C.SOUND_PHRASE[l])
        return pool[:3] if len(pool) >= 3 else None

    if kind == "OBJECT":
        gh = _head_noun(gold)
        inw = {_norm(x) for x in ix.visible_in(t0 - 2, t1 + 2)}
        inw |= {_norm(m.extra.get("object_name", "")) for m in ix.in_window(t0 - 2, t1 + 2, "movement")}
        pool = []
        for n in ix.object_names:
            nn = _norm(n)
            if nn in inw or nn == _norm(gold) or _head_noun(nn) == gh:
                continue
            if is_fixture(nn) or is_artifact(nn):
                continue
            pool.append(nn)
        rng.shuffle(pool)
        return pool[:3] if len(pool) >= 3 else None

    if kind == "ORDER":
        parts = gold.split(" -> ")
        perms = []
        for p in ([2, 0, 1], [1, 2, 0], [2, 1, 0], [0, 2, 1], [1, 0, 2]):
            cand = " -> ".join(parts[i] for i in p)
            if cand != gold:
                perms.append(cand)
        rng.shuffle(perms)
        return perms[:3] if len(perms) >= 3 else None
    return None


# ---------- 校验：只在窗口内的事件上求值 ----------

def verify(ix, item, t0, t1):
    k, gold = item["kind"], item["answer"]
    errs = []
    if k == "COUNT":
        real = len(ix.sounds_between(t0, t1, item["_sound_label"]))
        if str(real) != gold:
            errs.append(f"count 重算不符 {real}!={gold}")
        for d in item["_distractors"]:
            if d == str(real):
                errs.append("干扰项与 gold 相同")
    elif k == "OBJECT":
        vis = {_norm(x) for x in ix.visible_in(t0, t1)}
        vis |= {_norm(m.extra.get("object_name", "")) for m in ix.in_window(t0, t1, "movement")}
        if _norm(gold) not in vis:
            errs.append("gold 物体不在窗口内")
        for d in item["_distractors"]:
            if _norm(d) in vis:
                errs.append(f"干扰项 '{d}' 在窗口内也为真")
    elif k == "ORDER":
        evs = [ix.ev(e) for e in item["evidence_event_ids"]]
        if [e.eid for e in sorted(evs, key=lambda x: x.t_start)] != [e.eid for e in evs]:
            errs.append("ORDER 证据未按时序")
    # 结构断言
    if len(set(item["options"])) != 4:
        errs.append("选项不足 4 个互异")
    if item["options"][item["_gold_idx"]][3:] != gold:
        errs.append("correct_option 与 answer 不一致")
    for e in item["evidence_event_ids"]:
        ev = ix.ev(e)
        if not (ev.t_start < t1 and ev.t_end > t0):
            errs.append(f"证据 {e} 落在窗口外")
    return errs
