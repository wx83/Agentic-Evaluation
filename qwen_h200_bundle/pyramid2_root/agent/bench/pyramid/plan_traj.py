"""L4 goal -> trajectory:分段、参考轨迹推导、Gemini 草稿、人工核验回写、判分指标。

    PYRAMID_SEED=43 python plan_traj.py segment             # 打印每个视频的候选段与参考步骤数
    PYRAMID_SEED=43 python plan_traj.py draft [--video V]   # Gemini 写 goal 句 + 每步短语 -> P.ANNOT/plan_traj_<video>.json(status=draft)
    PYRAMID_SEED=43 python plan_traj.py ingest-review       # 读 review CSV(section=plan_traj)回写 status
    python plan_traj.py selftest                            # metrics() 单元用例

单位 = recipe_timestamps 活动段(同 recipe 且总长 < 60 s 的相邻段合并),保留 45–180 s 且有 recipe_id 的段。
参考轨迹 = 段内 narration 按 (verb_class, head noun) 合并成 span,取最长的 4–8 个并恢复时序。
"""
import sys, json, re, collections, pathlib, random
import pconfig as P
import config as C
import infer as IN
import primitives as PRIM

MIN_SEG, MAX_SEG, MERGE_BELOW = 45.0, 180.0, 60.0
MIN_STEPS, MAX_STEPS = 4, 8
MANIP = {"take", "put", "move", "hold", "open", "close", "pick up", "put down", "place", "grab", "lift", "lift up"}
STATE_VERBS = {"cut", "pour", "add", "mix", "stir", "wash", "turn on", "turn off", "switch on", "switch off",
               "crack", "peel", "chop", "slice", "whisk", "fry", "boil", "season", "sprinkle", "spread", "knead"}


def annot_path(video):
    P.ANNOT.mkdir(parents=True, exist_ok=True)
    return P.ANNOT / f"plan_traj_{video}.json"


# ---------------- 分段 ----------------
def segments(video, duration):
    segs = IN.recipe_segs(video, duration)
    out, i = [], 0
    while i < len(segs):
        s0, s1, lab, rid = segs[i]
        labs = [lab]; j = i + 1
        while j < len(segs) and segs[j][3] == rid and rid and (segs[j][1] - s0) < MERGE_BELOW:
            s1 = segs[j][1]; labs.append(segs[j][2]); j += 1
        s1 = min(s1, duration - 0.5)
        if rid and MIN_SEG <= s1 - s0 <= MAX_SEG:
            out.append({"seg_id": f"{video[:3]}_s{len(out):02d}", "t0": round(s0, 2), "t1": round(s1, 2),
                        "recipe_id": rid, "activity_label": " / ".join(labs)})
        i = j
    return out


def recipe_step_for(video, seg):
    """complete_recipes 里与该段 step_times 重叠最多的 step(只作 side info)。"""
    f = C.HDEPIC / "annotations" / video / "raw" / "complete_recipes.json"
    if not f.exists():
        return None
    best = None
    for rid, rec in json.loads(f.read_text()).items():
        for cap in rec.get("captures", []):
            if video not in cap.get("videos", []):
                continue
            for sid, ivs in cap.get("step_times", {}).items():
                ov = sum(max(0.0, min(seg["t1"], iv["end"]) - max(seg["t0"], iv["start"]))
                         for iv in ivs if iv["video"] == video)
                if ov > 0 and (best is None or ov > best[0]):
                    best = (ov, sid, rec["steps"].get(sid, ""), rec["name"])
    return None if best is None else {"step_id": best[1], "step_text": best[2], "recipe_name": best[3], "overlap_s": round(best[0], 1)}


# ---------------- 参考轨迹 ----------------
def derive_reference(ix, t0, t1):
    ev = sorted(ix.in_window(t0, t1, "narration"), key=lambda x: x.t_start)
    spans = []
    for e in ev:
        pr, cl = IN.main_pair(e), IN.main_classes(e)
        if not pr or not cl or pr[1] in IN.TRIVIAL_NOUNS or pr[0] in IN.TRIVIAL_VERBS:
            continue
        head = PRIM._head_noun(pr[1])
        if spans and spans[-1]["noun"] == head and (spans[-1]["vcls"] == cl[0] or pr[0] in MANIP or spans[-1]["verb"] in MANIP) \
                and e.t_start - spans[-1]["t1"] < 5:
            spans[-1]["t1"] = max(spans[-1]["t1"], e.t_end); spans[-1]["eids"].append(e.eid)
            if pr[0] in STATE_VERBS and spans[-1]["verb"] not in STATE_VERBS:
                spans[-1]["verb"], spans[-1]["text"] = pr[0], e.text
            continue
        spans.append({"verb": pr[0], "noun": head, "vcls": cl[0], "text": e.text, "eids": [e.eid],
                      "t0": e.t_start, "t1": e.t_end})
    spans = [s for s in spans if s["t1"] - s["t0"] >= 3 or s["verb"] in STATE_VERBS]
    seen, uniq = set(), []                           # 同一 (verb, noun) 只保留第一次(开/关水龙头来回不算步骤)
    for s in spans:
        k = (s["verb"], s["noun"])
        if k in seen or (s["verb"] in ("turn off", "switch off", "close", "put down") and len(uniq) and uniq[-1]["noun"] == s["noun"]):
            continue
        seen.add(k); uniq.append(s)
    spans = uniq
    if len(spans) > MAX_STEPS:
        # 优先保留改变状态的动作,其次按时长;再恢复时序
        ranked = sorted(spans, key=lambda s: (0 if s["verb"] in STATE_VERBS else 1, -(s["t1"] - s["t0"])))
        keep = sorted(ranked[:MAX_STEPS], key=lambda s: s["t0"])
    else:
        keep = spans
    if len(keep) < MIN_STEPS:
        return None
    steps = [{"idx": i + 1, "text": IN.action_phrase((s["verb"], s["noun"])), "verb": s["verb"], "noun": s["noun"],
              "eids": s["eids"], "t0": round(s["t0"], 2), "t1": round(s["t1"], 2)} for i, s in enumerate(keep)]
    prereq = [[a["idx"], b["idx"]] for a in steps for b in steps if a["idx"] < b["idx"] and a["noun"] == b["noun"]
              and a["verb"] in MANIP and b["verb"] in STATE_VERBS]
    return steps, prereq


# ---------------- Gemini 草稿 ----------------
DRAFT_PROMPT = """You help build a cooking-planning benchmark. Below is one segment of a first-person kitchen video:
the recipe, the recipe step it belongs to (if known), and the narrated actions in order (with start times in seconds).

Recipe: {recipe}
Recipe step (context only): {step}
Narrated actions ({t0:.0f}-{t1:.0f} s):
{lines}

A rough program-derived list of sub-actions (may contain noise):
{steps}

Write:
1. "goal": ONE sentence (<= 20 words) stating what the camera wearer is trying to achieve in this segment, phrased as a
   desired end state (e.g. "Get the chopped onions frying in the pan"). It must NOT list the steps, must not contain
   "then", "and then" or ";", and must not mention more than one of the step verbs.
2. "steps": 4 to 8 sub-actions, in the order they happen, that a competent cook would list as THE plan for this goal:
   each a short imperative phrase (3-6 words) naming the action and the object. Merge fiddly manipulations into one
   step (e.g. several tap on/off into "rinse the bowl"), drop detours that do not serve the goal, never invent actions
   that are not narrated. Give each step the start time (seconds) of the first narration it covers.
Reply with ONE JSON object: {{"goal": "...", "steps": [{{"text": "...", "t": <seconds>}}, ...]}}"""


def draft(video=None):
    import adaptive as A, gemini_io
    vids = [video] if video else P.VIDEOS
    for v in vids:
        ix = A.ix_of(v); f = annot_path(v)
        doc = json.loads(f.read_text()) if f.exists() else {"video_id": v, "version": "pt1", "segments": []}
        if "--force" in sys.argv:
            doc["segments"] = []
        have = {s["seg_id"] for s in doc["segments"]}
        for seg in segments(v, ix.duration):
            if seg["seg_id"] in have:
                continue
            ref = derive_reference(ix, seg["t0"], seg["t1"])
            if not ref:
                continue
            steps, prereq = ref
            step = recipe_step_for(v, seg)
            lines = "\n".join(f"[{e.t_start:.1f}] {e.text}" for e in sorted(ix.in_window(seg["t0"], seg["t1"], "narration"), key=lambda x: x.t_start))
            prompt = DRAFT_PROMPT.format(recipe=(step or {}).get("recipe_name", "unknown"), step=(step or {}).get("step_text", "unknown"),
                                         t0=seg["t0"], t1=seg["t1"], lines=lines[:6000],
                                         steps="\n".join(f"{s['idx']}. {s['text']}" for s in steps))
            try:
                txt, _ = gemini_io.gen(prompt, max_tokens=400, role="generator")
                m = re.search(r"\{.*\}", txt, re.S); j = json.loads(m.group(0)) if m else {}
            except Exception as ex:
                j = {"error": str(ex)[:120]}
            gsteps = j.get("steps") if isinstance(j.get("steps"), list) else []
            narr = sorted(ix.in_window(seg["t0"], seg["t1"], "narration"), key=lambda x: x.t_start)
            ref = []
            for k, g in enumerate(gsteps):
                if not isinstance(g, dict) or not g.get("text"):
                    continue
                try:
                    t = float(g.get("t"))
                except (TypeError, ValueError):
                    t = seg["t0"]
                near = min(narr, key=lambda x: abs(x.t_start - t)) if narr else None
                words = re.findall(r"[a-z]+", str(g["text"]).lower())
                ref.append({"idx": len(ref) + 1, "text": str(g["text"]).strip(), "verb": words[0] if words else "",
                            "noun": words[-1] if words else "", "eids": [near.eid] if near else [], "t0": round(t, 2),
                            "t1": round(near.t_end if near else t, 2)})
            if not (MIN_STEPS <= len(ref) <= MAX_STEPS):
                ref = steps                                   # Gemini 失败则退回规则版
            ref = sorted(ref, key=lambda r: r["t0"])
            for k, r_ in enumerate(ref):
                r_["idx"] = k + 1
            prereq = [[a["idx"], b["idx"]] for a in ref for b in ref if a["idx"] < b["idx"] and a["noun"] == b["noun"]
                      and a["verb"] in MANIP and b["verb"] in STATE_VERBS]
            doc["segments"].append(dict(seg, recipe_step=step, goal=j.get("goal", ""), goal_draft=j.get("goal", ""),
                                        reference_steps=ref, reference_rule=[s_["text"] for s_ in steps], prereq=prereq,
                                        status="draft", annotator="", note=""))
            f.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        print(v, len(doc["segments"]), "segments drafted ->", f, flush=True)


def ingest_review(csv_path="/mnt/work_new/weihanxu/experiments/pyramid_review.csv"):
    import csv
    rows = collections.defaultdict(list)
    for r in csv.DictReader(open(csv_path, encoding="utf-8")):
        if r["section"] == "plan_traj":
            rows[r["question_id"]].append(r)
    n = 0
    for v in P.VIDEOS:
        f = annot_path(v)
        if not f.exists():
            continue
        doc = json.loads(f.read_text())
        for seg in doc["segments"]:
            rs = rows.get(seg["seg_id"])
            if not rs:
                continue
            last = sorted(rs, key=lambda x: x["timestamp"])[-1]
            good = all(last[k] == "ok" for k in ("question_check", "answer_check", "gt_check"))
            seg["status"] = "verified" if good else ("rejected" if "wrong" in (last["question_check"], last["gt_check"]) else "draft")
            seg["annotator"], seg["note"] = last["reviewer"], last["note"]; n += 1
        f.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    print("ingested", n, "reviews")


def verified_segments(video):
    f = annot_path(video)
    if not f.exists():
        return []
    return [s for s in json.loads(f.read_text())["segments"] if s.get("status") == "verified"]


# ---------------- 判分 ----------------
def _lcs(a, b):
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            dp[i + 1][j + 1] = dp[i][j] + 1 if x == y else max(dp[i][j + 1], dp[i + 1][j])
    return dp[-1][-1]


def metrics(mapping, n_ref, prereq=()):
    """mapping: 每条预测步骤对应的参考 idx(1-based)或 None。"""
    preds = list(mapping)
    hit = [m for m in preds if m]
    matched = sorted(set(hit))
    precision = len(hit) / len(preds) if preds else 0.0
    recall = len(matched) / n_ref if n_ref else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    seq = []
    for m in hit:                                     # 去重保序
        if m not in seq:
            seq.append(m)
    order = _lcs(seq, sorted(seq)) / len(seq) if len(seq) > 1 else 1.0
    pos = {m: i for i, m in enumerate(seq)}
    pairs = [(a, b) for a, b in prereq if a in pos and b in pos]
    viol = sum(1 for a, b in pairs if pos[a] > pos[b]) / len(pairs) if pairs else 0.0
    score = 0.5 * f1 + 0.3 * order + 0.2 * (1 - viol)
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3), "order": round(order, 3),
            "halluc_rate": round(1 - precision, 3), "missing_rate": round(1 - recall, 3), "prereq_viol": round(viol, 3),
            "score": round(score, 3), "correct": bool(score >= 0.6 and recall >= 0.5), "map": preds}


def rule_align(pred_steps, ref_steps):
    """词干重叠的规则对齐(只做诊断):恰有一个参考步骤共享 head noun 且动词同义时给 idx,否则 None。"""
    import formats as FM
    out = []
    for ptxt in pred_steps:
        pt = FM.toks(ptxt)
        cands = [r["idx"] for r in ref_steps if FM._stem(r["noun"]) in pt and (FM.toks(r["verb"]) & pt)]
        out.append(cands[0] if len(cands) == 1 else None)
    return out


def selftest():
    pr = [[1, 3]]
    assert metrics([1, 2, 3, 4], 4, pr)["score"] == 1.0
    m = metrics([4, 3, 2, 1], 4, pr); assert m["f1"] == 1.0 and m["order"] == 0.25 and m["prereq_viol"] == 1.0, m
    m = metrics([None, None, None], 4); assert m["f1"] == 0.0 and not m["correct"], m
    m = metrics([1, 2], 4); assert m["recall"] == 0.5 and m["precision"] == 1.0, m
    m = metrics([1, 1, 2, None], 4); assert m["recall"] == 0.5 and m["precision"] == 0.75, m
    print("selftest ok")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "segment"
    if cmd == "segment":
        import adaptive as A
        tot = 0
        for v in P.VIDEOS:
            ix = A.ix_of(v); ss = segments(v, ix.duration); ok = 0
            for s in ss:
                r = derive_reference(ix, s["t0"], s["t1"])
                if r:
                    ok += 1
            print(v, len(ss), "segments,", ok, "with 4-8 reference steps"); tot += ok
        print("TOTAL usable", tot)
    elif cmd == "draft":
        draft(sys.argv[sys.argv.index("--video") + 1] if "--video" in sys.argv else None)
    elif cmd == "ingest-review":
        ingest_review()
    elif cmd == "selftest":
        selftest()
