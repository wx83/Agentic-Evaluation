"""10-27 晚(用户:L4 加可答性检查):L4 题出题前先筛 cluster。
参考答案每一步的关键物体(sub-goal 文字里动词后的第一个名词短语的中心词)必须出现在以下任一来源,否则该 cluster 不出题:
  1. clip 窗口内、cutoff 之前开始的标注记录(narration / 物体轨迹 / mask 等;不含 task_segment / task_step / recipe_step 这些带 goal 或未来步骤的记录);
  2. 这一步的 goal 原文(contract.l4_show_goal 时 Solver 看得到);
  3. 这道题会带的下层 history(按 contract 的 history 规则现算)。
goal_conditioned_planning:第 1 档(单选)只查 cutoff 后第 1 个 sub-goal;plan 档查 cutoff 后的 sub-goal(≤ 8 个);cutoff 后没有 sub-goal(参考 = step complete)直接通过。
plan_gap_filling:查隐藏的 sub-goal。结果写 runs/<run>/L4/answerability.jsonl。"""
import json, re
from pathlib import Path

SKIP_KINDS = {"task_segment", "task_step", "recipe_step"}
PREP = {"to", "into", "in", "on", "onto", "with", "from", "for", "at", "over", "under", "and", "then", "until", "using", "off", "out", "up", "back",
        "by", "inside", "onto", "through", "while", "before", "after", "of"}
STOP = {"the", "a", "an", "some", "all", "remaining", "rest", "its", "their", "his", "her", "first", "second", "third", "fourth", "other", "more",
        "few", "two", "three", "both", "each", "any", "small", "large", "big", "new", "same"}
GENERIC = {"food", "mixture", "it", "them", "everything", "ingredients", "contents", "dish", "step", "stuff", "items", "things", "area", "workspace",
           "counter", "worktop", "hands", "hand", "doneness", "shape", "tools", "utensils", "workspace"}


def _tok(s):
    return re.findall(r"[a-z]+", (s or "").lower())


PARTITIVE = {"ends", "end", "half", "piece", "pieces", "batch", "part", "bit", "bits", "slice", "slices", "chunk", "chunks", "rest", "remainder",
             "stirring", "mixing", "frying", "cooking", "chopping", "heat", "halves", "chunk", "doneness"}
VERBS = {"retrieve", "get", "take", "grab", "fetch", "pick", "weigh", "wash", "rinse", "prepare", "peel", "crush", "add", "cut", "slice", "chop", "stir",
         "mix", "blend", "pour", "place", "put", "set", "transfer", "trim", "halve", "season", "fry", "cook", "boil", "heat", "melt", "spread", "fill",
         "measure", "extract", "turn", "switch", "adjust", "open", "close", "remove", "return", "clean", "wipe", "dry", "check", "press", "scrape",
         "loosen", "fold", "flip", "serve", "cover", "uncover", "continue", "finish", "begin", "start", "perform", "complete", "separate", "grate",
         "squeeze", "drain", "shake", "dice", "mince", "store", "move", "carry", "bring", "use", "attempt", "try"}


def key_object(text):
    """sub-goal 文字 → 关键物体中心词(None = 没找到)。跳过开头的动词串(含「, and」连接的多个动词)和介词 / 小品词,
    取到下一个介词前的最后一个非停用词;部分名词(ends / piece / batch / stirring …)继续往后找真正的物体。"""
    t = _tok(text)
    i = 0
    while True:
        while i < len(t) and (t[i] in VERBS or t[i] == "and" or t[i] in PREP or t[i] in STOP):
            i += 1
        span = []
        while i < len(t) and t[i] not in PREP:
            span.append(t[i]); i += 1
        span = [w for w in span if w not in STOP]
        head = span[-1] if span else None
        if head is None and i >= len(t):
            return None
        if head is None or head in PARTITIVE or head in VERBS:
            if i >= len(t):
                return head
            continue
        return head


def _stem(w):
    w = w[:-3] + "y" if w.endswith("ies") else w[:-2] if w.endswith("es") and len(w) > 4 else w[:-1] if w.endswith("s") and len(w) > 3 else w
    return w[:6]


def found(obj, text_tokens):
    if obj is None or obj in GENERIC:
        return True
    st = _stem(obj)
    return any(_stem(x) == st for x in text_tokens)


def _steps(store, sid):
    out = []
    for r in store.by_event.get(sid, []):
        if r["kind"] == "task_step" and not r["value"].get("is_next_action") and r.get("time"):
            out.append({"idx": r["value"].get("idx"), "text": r["value"].get("text") or "", "t0": float(r["time"]["start_sec"])})
    return sorted(out, key=lambda x: (x["t0"], x["idx"] or 0))


def _goal(store, sid):
    seg = next((r for r in store.by_event.get(sid, []) if r["kind"] == "task_segment"), None)
    return (seg or {}).get("value", {}).get("goal") or ""


def _clip_tokens(store, vid, windows):
    end = max(b for a, b in windows)
    toks = []
    for r in store.by_video.get(vid, []):
        t = r.get("time") or {}
        if r["kind"] in SKIP_KINDS or t.get("start_sec") is None or t.get("end_sec") is None:
            continue
        if (r.get("solver_access") or "") == "answer_only":
            continue
        if any(t["end_sec"] >= a and t["start_sec"] <= b for a, b in windows) and t["start_sec"] < end - 0.05:
            v = r.get("value") or {}
            toks += _tok(" ".join(str(v.get(k) or "") for k in ("text", "name", "label", "noun", "nouns", "object", "objects", "noun_class", "verb")))
    return toks


def check(store, run_dir, contract, cap, cluster, level):
    """返回 (ok, detail)。"""
    import chain
    sid, vid = cluster.get("sample_id"), cluster.get("video_id")
    windows = [tuple(w) for w in (cluster.get("windows") or [cluster.get("window")]) if w]
    steps = _steps(store, sid)
    if cap == "plan_gap_filling":
        g = cluster.get("gap") or {}
        hid = set(g.get("hidden_idx") or [])
        targets = [s for s in steps if s["idx"] in hid]
    else:
        cut = float(cluster.get("observation_cutoff") or max(b for a, b in windows))
        rem = [s for s in steps if s["t0"] >= cut - 1e-6]
        targets = rem[:1] if int(level) == 1 else rem[:8]
    if not targets:
        return True, {"targets": [], "note": "no recorded sub-goal after the cutoff (reference = step complete)"}
    goal = _goal(store, sid) if contract.get("l4_show_goal") else ""
    cur = {"output": {"public": {"observation_cutoff": cluster.get("observation_cutoff"), "media_refs": [{"windows": [list(w) for w in windows]}]},
                      "private": {}}}
    hist = chain.history_for(run_dir, "L4", sid, contract.get("history_mode"), cap=contract.get("history_cap", 12),
                             exclude_same_answer=False, current=cur, respect_cutoff=contract.get("history_respect_cutoff", False),
                             only_base=contract.get("history_only_base", False), select=contract.get("history_select"),
                             per_layer=contract.get("history_per_layer", 8)) if contract.get("history_mode") in ("self", "gold") else None
    src = {"clip": _clip_tokens(store, vid, windows), "goal": _tok(goal), "history": _tok((hist or {}).get("text"))}
    det, ok = [], True
    for s in targets:
        obj = key_object(s["text"])
        where = [k for k, toks in src.items() if found(obj, toks)] if obj and obj not in GENERIC else ["generic"]
        det.append({"idx": s["idx"], "text": s["text"], "object": obj, "found_in": where})
        ok = ok and bool(where)
    return ok, {"targets": det}


def log(run_dir, rec):
    p = Path(run_dir) / "L4" / "answerability.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
