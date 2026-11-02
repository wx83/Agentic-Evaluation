"""任务-步骤时间表(L4 的统一数据底座):每个视频切成一串任务,每个任务 = goal 句 + 4–8 个子目标级步骤(带时间)。

    PYRAMID_SEED=43 python task_timeline.py draft [--video V] [--force]   # Gemini 按 narration 切任务 -> P.ANNOT/task_timeline_<video>.json
    PYRAMID_SEED=43 python task_timeline.py stats                         # 每视频任务数、步骤数、时长分布
    PYRAMID_SEED=43 python task_timeline.py ingest-review                 # 读 review CSV(section=plan_traj)回写 status

切法:narration 按 CHUNK_MIN 分钟分块(相邻块重叠 OVERLAP_MIN 分钟),每块让 Gemini 输出任务列表;跨块重叠 > 50% 的任务去重,
取更完整(步骤更多)的那条。不依赖 recipe_timestamps(P08 没有),菜谱名和步骤文本只作上下文。
L4 三档题都从这张表派生:next_step(第 k 步末尾 → 第 k+1 步)、trajectory(goal → 全部步骤)、replan(任务内的意外)。
"""
import sys, json, re, collections, pathlib
import pconfig as P
import config as C
import gemini_io

CHUNK_MIN, OVERLAP_MIN = 12.0, 2.0
MIN_STEPS, MAX_STEPS = 3, 8
MIN_TASK, MAX_TASK = 25.0, 600.0


def annot_path(video):
    P.ANNOT.mkdir(parents=True, exist_ok=True)
    return P.ANNOT / f"task_timeline_{video}.json"          # 备份文件 *.pre_split.json 不参与读取


def recipe_context(video):
    f = C.HDEPIC / "annotations" / video / "raw" / "complete_recipes.json"
    if not f.exists():
        return "unknown"
    out = []
    for rid, rec in json.loads(f.read_text()).items():
        if not any(video in c.get("videos", []) for c in rec.get("captures", [])):
            continue
        out.append(f"- {rec['name']}: " + " | ".join(f"{k}: {v}" for k, v in rec["steps"].items()))
    return "\n".join(out) or "unknown"


PROMPT = """You are segmenting a first-person cooking video into TASKS for a planning benchmark. Below are the narrated actions
of one time window (start time in seconds, one action per line). The person may be cooking several recipes in parallel
and interleaving chores (washing up, tidying).

Recipes being cooked in this video (context only; the narrations are the ground truth):
{recipes}

Narrated actions, {t0:.0f}-{t1:.0f} s:
{lines}

Split this window into TASKS. A task is a coherent sub-goal that a cook would plan as a unit and that takes roughly
1-8 minutes, e.g. "Get the onions chopped and into the pan", "Make the pizza dough", "Wash and put away the used
utensils". Rules:
- Tasks do not overlap; together they should cover the window except brief gaps. A task may contain a short unrelated
  interruption (e.g. a 5 s glance at the phone) but if the person switches to a different sub-goal for > 30 s, that is
  a different task.
- Each task has 4-8 STEPS: sub-goals a competent cook would list as the plan (e.g. "peel the onion", "chop the onion",
  "heat oil in the pan", "add onions to the pan"). Merge fiddly hand actions into one step; never list hand movements,
  tap on/off, or single grasps as steps; never invent actions that are not narrated. Steps are in the order performed.
- "goal": ONE sentence (<= 20 words) stating the desired end state of the task. It must not enumerate the steps and must
  not contain "then" or ";".
- If the window starts or ends in the middle of a task, still output that task with the steps you can see and set
  "partial_start" / "partial_end" to true.
- Give start/end times in seconds for the task and the start time of each step (first narration it covers).

Reply with ONE JSON object only:
{{"tasks": [{{"goal": "...", "t0": <s>, "t1": <s>, "partial_start": false, "partial_end": false,
            "steps": [{{"text": "...", "t": <s>}}, ...]}}, ...]}}"""


def _json(txt):
    j = gemini_io.jparse(txt)
    if isinstance(j, dict):
        return j
    m = re.search(r"\{.*\}", txt or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def chunks(duration):
    out, t = [], 0.0
    while t < duration:
        out.append((t, min(duration, t + CHUNK_MIN * 60)))
        t += (CHUNK_MIN - OVERLAP_MIN) * 60
    return out


def draft(video=None):
    import adaptive as A
    force = "--force" in sys.argv
    for v in ([video] if video else P.VIDEOS):
        f = annot_path(v)
        if f.exists() and not force:
            print(v, "exists, skip (use --force)"); continue
        ix = A.ix_of(v); narr = sorted(ix.narrations, key=lambda x: x.t_start)
        rec = recipe_context(v); raw_tasks = []
        for (c0, c1) in chunks(ix.duration):
            ev = [e for e in narr if c0 <= e.t_start < c1]
            if len(ev) < 10:
                continue
            lines = "\n".join(f"[{e.t_start:.1f}] {e.text}" for e in ev)
            prompt = PROMPT.format(recipes=rec, t0=c0, t1=c1, lines=lines)
            j = None
            for attempt in range(2):
                try:
                    txt, mid = gemini_io.gen(prompt, max_tokens=6000, role="generator")
                    j = _json(txt)
                    if j and isinstance(j.get("tasks"), list):
                        break
                except Exception as ex:
                    print("  gen error:", str(ex)[:100], flush=True)
            for t in (j or {}).get("tasks", []):
                try:
                    t0, t1 = float(t["t0"]), float(t["t1"])
                    steps = [{"text": str(s["text"]).strip(), "t0": float(s["t"])} for s in t.get("steps", []) if s.get("text")]
                except (KeyError, TypeError, ValueError):
                    continue
                if not steps or t1 <= t0:
                    continue
                raw_tasks.append({"goal": str(t.get("goal", "")).strip(), "t0": round(t0, 1), "t1": round(min(t1, ix.duration - 0.5), 1),
                                  "partial": bool(t.get("partial_start") or t.get("partial_end")), "steps": steps, "chunk": [c0, c1]})
            print(f"  {v} chunk {c0:.0f}-{c1:.0f}: {len((j or {}).get('tasks', []))} tasks", flush=True)
        tasks = merge(raw_tasks, narr)
        doc = {"video_id": v, "version": "tt1", "tasks": tasks}
        f.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        print(v, len(raw_tasks), "raw ->", len(tasks), "tasks ->", f, flush=True)


def merge(raw, narr):
    """跨块重叠 > 50% 的任务去重,保留步骤更多且非 partial 的;再按时间排序、编号、给每步配 eid 与结束时间。"""
    raw = sorted(raw, key=lambda t: (t["t0"], -len(t["steps"])))
    kept = []
    for t in raw:
        dup = None
        for k in kept:
            ov = min(t["t1"], k["t1"]) - max(t["t0"], k["t0"])
            if ov > 0.5 * min(t["t1"] - t["t0"], k["t1"] - k["t0"]):
                dup = k; break
        if dup is None:
            kept.append(t)
        elif (not t["partial"] and dup["partial"]) or (t["partial"] == dup["partial"] and len(t["steps"]) > len(dup["steps"])):
            kept[kept.index(dup)] = t
    kept.sort(key=lambda t: t["t0"])
    out = []
    for i, t in enumerate(kept):
        steps = sorted(t["steps"], key=lambda s: s["t0"])
        for k, s in enumerate(steps):
            near = min(narr, key=lambda x: abs(x.t_start - s["t0"])) if narr else None
            s["idx"] = k + 1; s["eids"] = [near.eid] if near else []
            s["t1"] = round(steps[k + 1]["t0"] if k + 1 < len(steps) else t["t1"], 1)
            w = re.findall(r"[a-z]+", s["text"].lower()); s["verb"], s["noun"] = (w[0] if w else ""), (w[-1] if w else "")
        out.append({"task_id": f"{narr[0].eid.split(':')[0][:3]}_t{i:02d}",
                    "goal": t["goal"], "t0": t["t0"], "t1": t["t1"], "dur": round(t["t1"] - t["t0"], 1),
                    "n_steps": len(steps), "ok_steps": MIN_STEPS <= len(steps) <= MAX_STEPS,
                    "partial": t["partial"], "steps": steps, "status": "draft", "annotator": "", "note": ""})
    return out


SPLIT_PROMPT = """You are checking ONE task from a cooking-video task timeline. A task must be a SINGLE coherent sub-goal that a cook
would plan as a unit (e.g. "Get the onions chopped and into the pan"). It must NOT bundle two different sub-goals
(e.g. "Tidy the counter AND prepare the salad", "Wash the dishes AND check the oven"). Brief interruptions (< 20 s)
inside one sub-goal do not split it.

Current task ({t0:.0f}-{t1:.0f} s): goal = "{goal}"
Current steps:
{steps}
Narrated actions in this window (start time in seconds):
{lines}

Decide whether this window contains ONE sub-goal or SEVERAL. If several, split it into consecutive, non-overlapping tasks
in time order; each must last >= 25 s, have 3-8 steps, and a goal sentence (<= 20 words, desired end state, no "then",
no ";", not two unrelated things joined by "and"). Give each task its start/end time and each step its start time.
Steps are sub-goals (merge fiddly hand actions; never invent actions not narrated).

Reply with ONE JSON object only:
{{"split": true/false, "tasks": [{{"goal": "...", "t0": <s>, "t1": <s>, "steps": [{{"text": "...", "t": <s>}}, ...]}}, ...]}}
(If split is false, return the single task, possibly with a cleaner goal and steps.)"""


def split(video=None):
    """对每个任务做一次拆分检查;拆开的子任务 id = 原 id + a/b/c,记 parent_task。原文件先存为 .pre_split.json。"""
    import adaptive as A
    for v in ([video] if video else P.VIDEOS):
        f = annot_path(v)
        if not f.exists():
            continue
        doc = json.loads(f.read_text())
        if doc.get("version") == "tt2" and "--force" not in sys.argv:
            print(v, "already split"); continue
        f.with_suffix(".pre_split.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        ix = A.ix_of(v); narr = sorted(ix.narrations, key=lambda x: x.t_start)
        new = []
        for t in doc["tasks"]:
            ev = [e for e in narr if t["t0"] <= e.t_start < t["t1"]]
            lines = "\n".join(f"[{e.t_start:.1f}] {e.text}" for e in ev)
            prompt = SPLIT_PROMPT.format(t0=t["t0"], t1=t["t1"], goal=t["goal"], lines=lines[:12000],
                                         steps="\n".join(f"{s['idx']}. {s['text']} ({s['t0']:.0f}s)" for s in t["steps"]))
            j = None
            for attempt in range(2):
                try:
                    txt, _ = gemini_io.gen(prompt, max_tokens=4000, role="generator"); j = _json(txt)
                    if j and isinstance(j.get("tasks"), list) and j["tasks"]:
                        break
                except Exception as ex:
                    print("  gen error:", str(ex)[:100], flush=True)
            subs = []
            for st in (j or {}).get("tasks", []):
                try:
                    s0, s1 = float(st["t0"]), float(st["t1"])
                    steps = [{"text": str(x["text"]).strip(), "t0": float(x["t"])} for x in st.get("steps", []) if x.get("text")]
                except (KeyError, TypeError, ValueError):
                    continue
                if s1 - s0 >= 25 and steps:
                    subs.append({"goal": str(st.get("goal", "")).strip(), "t0": round(max(s0, t["t0"]), 1), "t1": round(min(s1, t["t1"]), 1), "steps": steps})
            subs.sort(key=lambda x: x["t0"])
            if not subs:
                subs = [{"goal": t["goal"], "t0": t["t0"], "t1": t["t1"], "steps": [{"text": s["text"], "t0": s["t0"]} for s in t["steps"]]}]
            did_split = bool((j or {}).get("split")) and len(subs) > 1
            for k, st in enumerate(subs):
                steps = sorted(st["steps"], key=lambda s: s["t0"])
                for i, s in enumerate(steps):
                    near = min(narr, key=lambda x: abs(x.t_start - s["t0"])) if narr else None
                    s["idx"] = i + 1; s["eids"] = [near.eid] if near else []
                    s["t1"] = round(steps[i + 1]["t0"] if i + 1 < len(steps) else st["t1"], 1)
                    w = re.findall(r"[a-z]+", s["text"].lower()); s["verb"], s["noun"] = (w[0] if w else ""), (w[-1] if w else "")
                tid = t["task_id"] + ("abcdefgh"[k] if did_split else "")
                new.append({"task_id": tid, "parent_task": t["task_id"] if did_split else None, "goal": st["goal"], "t0": st["t0"], "t1": st["t1"],
                            "dur": round(st["t1"] - st["t0"], 1), "n_steps": len(steps), "ok_steps": MIN_STEPS <= len(steps) <= MAX_STEPS,
                            "partial": t.get("partial", False), "steps": steps,
                            "status": t["status"] if not did_split else "draft", "annotator": t.get("annotator", ""), "note": t.get("note", "")})
            print(f"  {t['task_id']} {t['t0']:.0f}-{t['t1']:.0f}s -> {len(subs)} task(s){' SPLIT' if did_split else ''}", flush=True)
        doc["tasks"] = new; doc["version"] = "tt2"
        f.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        print(v, len(new), "tasks after split ->", f, flush=True)


def load(video):
    f = annot_path(video)
    return json.loads(f.read_text())["tasks"] if f.exists() else []


def verified(video):
    return [t for t in load(video) if t.get("status") == "verified"]


def stats():
    tot = 0
    for v in P.VIDEOS:
        ts = load(v)
        if not ts:
            print(v, "no file"); continue
        ok = [t for t in ts if t["ok_steps"] and MIN_TASK <= t["dur"] <= MAX_TASK]
        print(f"{v}: {len(ts)} tasks, {len(ok)} usable (4-8 steps, {MIN_TASK:.0f}-{MAX_TASK:.0f} s); dur median "
              f"{sorted(t['dur'] for t in ts)[len(ts) // 2]:.0f}s; steps {collections.Counter(t['n_steps'] for t in ts).most_common(4)}; "
              f"status {collections.Counter(t['status'] for t in ts)}")
        tot += len(ok)
    print("TOTAL usable", tot)


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
        for t in doc["tasks"]:
            rs = rows.get(t["task_id"])
            if not rs:
                continue
            last = sorted(rs, key=lambda x: x["timestamp"])[-1]
            good = all(last[k] == "ok" for k in ("question_check", "answer_check", "gt_check"))
            t["status"] = "verified" if good else ("rejected" if "wrong" in (last["question_check"], last["answer_check"], last["gt_check"]) else "draft")
            t["annotator"], t["note"] = last["reviewer"], last["note"]; n += 1
        f.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    print("ingested", n, "reviews")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "split":
        split(sys.argv[sys.argv.index("--video") + 1] if "--video" in sys.argv else None)
    elif cmd == "draft":
        draft(sys.argv[sys.argv.index("--video") + 1] if "--video" in sys.argv else None)
    elif cmd == "stats":
        stats()
    elif cmd == "ingest-review":
        ingest_review()
