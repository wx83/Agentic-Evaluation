#!/usr/bin/env python3
"""Method E:给 HD-EPIC 每个官方 recipe step 拆 sub-goal(EgoPlan-Bench2 的做法)。

做法:官方 recipe step = 一段的 summary;把这个 step 全部 step_times + prep_times 时间段里的官方 narration 按时间排好交给 Gemini,
让它提出 overall goal、若干 sub-goal(每个带自己的 action_ids,4–20 条为宜)、以及与 step 无关的 action。
不在任何 step 里的 narration(加上各 step 判成无关的)按时间每 120 条一个 no-step 窗口,用同一个 prompt 再分组。
模型只引用 action_id,不写时间;sub-goal 的起止时间由程序从官方 narration 抄。

与 pyramid2 用的 experiments/hdepic_goal_gen/method_e.py 的 prompt、分段、校验、合并逻辑相同,
只把 Gemini 调用换成 OpenRouter(OpenAI 协议),标注路径改成参数。输出 <out>/merged.json 就是 pyramid2 adapter hdepic_methode 读的文件。

用法:
  export OPENROUTER_API_KEY=sk-or-...
  python3 method_e.py --annot /path/to/hd-epic/annotations/data --video P08-20240617-184909 [--recipe P08_R07] [-o out/P08-20240617-184909]
  python3 method_e.py --stats out/          # 对一批输出算分布(sub-goal 数 / narration 数 / 时长 / 被打断)
"""
import json, os, re, sys, time, collections, argparse, statistics, urllib.request

MODEL = "google/gemini-3.1-pro-preview"

SYS = """You extract task goals from one segment of an egocentric kitchen video, in the way EgoPlan-Bench2 built goals from Ego4D segment summaries.

You receive a SUMMARY of the segment (an official recipe step written by the dataset annotators, or a note that the segment is not covered by any recipe step) and the official timestamped action narrations inside the segment. The narrations of one recipe step may be non-contiguous because the person interleaves tasks.

Extract:
1. overall_goal: what this segment accomplishes, in your own short imperative phrase (do not just copy the summary).
2. goals: the subgoals, each a short imperative phrase for one clear purpose, each with its action_ids in chronological order. Prefer 4 to 20 actions per goal; do not make single-action goals and do not merge different purposes to reach a count.
3. unrelated_action_ids: actions in this segment that do not serve the summary's purpose (e.g. phone use, unrelated tidying while waiting). Do not force them into a goal.

Rules: use only the given narrations; never invent actions, ingredients or steps; refer to actions only by action_id; NEVER write times, durations or frame numbers in any output field. Every input action_id must appear exactly once, in a goal or in unrelated_action_ids. Return only JSON."""
USR = """Video ID: {VID}
Recipe: {RECIPE}
Segment {SEG}
Summary: {SUMMARY}

Actions in this segment ({N}):
{ACTIONS}

Return JSON: {{"overall_goal": "...", "goals": [{{"goal_id": "e1", "description": "...", "action_ids": ["..."], "rationale": "<one sentence, no times>"}}], "unrelated_action_ids": ["..."]}}"""
NOSTEP_SUMMARY = "Not covered by any official recipe step (typically cleaning, weighing/logging ingredients, waiting, serving, or unrelated activity). Group these into goals by purpose; leave truly purposeless actions unrelated."


# ---------------------------------------------------------------- 官方标注
def load_annot(annot):
    import pandas as pd
    nar = pd.read_pickle(f"{annot}/narrations-and-action-segments/HD_EPIC_Narrations.pkl")
    rec = json.load(open(f"{annot}/high-level/complete_recipes.json"))
    return nar, rec


def load_actions(nar, rec, vid):
    nv = nar[nar.video_id == vid].sort_values(["start_timestamp", "end_timestamp"])
    acts = [{"action_id": r.unique_narration_id, "start_s": round(float(r.start_timestamp), 2), "end_s": round(float(r.end_timestamp), 2), "narration": r.narration.strip(),
             "verbs": list(r.verbs), "nouns": list(r.nouns)} for r in nv.itertuples()]
    labels = [f"{rv['name']} ({rid})" for rid, rv in rec.items() for c in rv["captures"] if vid in c["videos"]]
    return acts, ("; ".join(labels) or None)


def fmt_action(a):
    return f'{a["action_id"]} [{a["start_s"]:.2f}-{a["end_s"]:.2f}s] {a["narration"]}'


def segments(rec, vid, acts, recipe_id=None):
    """每个官方 step 一段:step_times + prep_times 里、中点落在段内的 narration(可以不连续)。"""
    spans = []; recipe = None
    for rid, rv in rec.items():
        if recipe_id and rid != recipe_id: continue
        for c in rv["captures"]:
            if vid not in c["videos"]: continue
            recipe = f'{rv["name"]} ({rid})'
            for kind in ("step_times", "prep_times"):
                for sid, lst in c.get(kind, {}).items():
                    for x in lst:
                        if x["video"] == vid: spans.append((x["start"], x["end"], sid, rv["steps"].get(sid, sid)))
    by_step = collections.OrderedDict(); covered = set()
    for a in acts:
        mid = (a["start_s"] + a["end_s"]) / 2
        hit = sorted({(sid, txt) for s0, s1, sid, txt in spans if s0 <= mid <= s1})
        if hit:
            sid, txt = hit[0]; by_step.setdefault(sid, {"summary": f"Recipe step {sid.split('_')[-1]}: {txt}", "ids": []})["ids"].append(a["action_id"]); covered.add(a["action_id"])
    return [{"seg_id": sid, "kind": "step", **v} for sid, v in by_step.items()], covered, recipe


# ---------------------------------------------------------------- LLM + 校验
def call_llm(system, prompt, model=MODEL, api_key=None, base_url="https://openrouter.ai/api/v1"):
    key = api_key or os.environ["OPENROUTER_API_KEY"]
    body = {"model": model, "temperature": 0, "max_tokens": 65535, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    for attempt in range(4):
        try:
            req = urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=900).read())
            t = r["choices"][0]["message"]["content"].strip()
            if t.startswith("```"): t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
            return json.loads(t[t.find("{"):t.rfind("}") + 1])
        except Exception as e:
            print(f"  attempt {attempt + 1} failed: {str(e)[:160]}", flush=True); time.sleep(30 * (attempt + 1))
    raise RuntimeError("LLM call failed")


TIME_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:s|sec|seconds?|min|minutes?)\b|\b\d{1,2}:\d{2}\b")
def validate_window(resp, assign_ids):
    """硬错误(返回后重试):缺字段、引用不在本段的 id、写了时间、id 用了 3 次以上、有 id 没被覆盖。"""
    errs, warns = [], []; want = set(assign_ids); seen = collections.Counter()
    for g in resp.get("goals", []):
        for k in ("goal_id", "description", "action_ids"):
            if k not in g: errs.append(f"goal missing {k}: {str(g)[:80]}")
        for i in g.get("action_ids", []):
            if i not in want: errs.append(f"{g.get('goal_id')}: id {i} not in this window's assignable set")
            seen[i] += 1
        for k, v in g.items():
            if isinstance(v, str) and TIME_RE.search(v): errs.append(f"{g.get('goal_id')}.{k} contains a time expression: {v[:60]}")
    for i in resp.get("unassigned_action_ids", []):
        if i not in want: errs.append(f"unassigned id {i} not in window")
        seen[i] += 1
    for i, n in seen.items():
        if n > 2: errs.append(f"{i} used {n} times")
        elif n == 2: warns.append(f"{i} shared by 2 goals")
    miss = [i for i in assign_ids if i not in seen]
    if miss: errs.append(f"{len(miss)} window ids not covered: {miss[:5]}")
    return errs, warns


def attach_times(goals, acts):
    t = {a["action_id"]: a for a in acts}
    for g in goals:
        ids = sorted(g["action_ids"], key=lambda i: t[i]["start_s"]); g["action_ids"] = ids
        g["start_s"] = t[ids[0]]["start_s"]; g["end_s"] = max(t[i]["end_s"] for i in ids); g["n_actions"] = len(ids)
        g["time_source"] = "copied from HD_EPIC_Narrations.pkl by code"
        gaps = [t[ids[k + 1]]["start_s"] - t[ids[k]]["end_s"] for k in range(len(ids) - 1)]
        g["n_interruptions_gt60s"] = sum(1 for x in gaps if x > 60)
    return goals


# ---------------------------------------------------------------- 主流程
def run(nar, rec, vid, recipe_id=None, out=None, model=MODEL):
    acts, label = load_actions(nar, rec, vid); out = out or f"out/{vid}"; os.makedirs(out, exist_ok=True)
    json.dump({"video_id": vid, "existing_label": label, "source": "HD_EPIC_Narrations.pkl (official)", "actions": acts}, open(f"{out}/input_actions.json", "w"), indent=1)
    T = {a["action_id"]: a for a in acts}; segs, covered, recipe = segments(rec, vid, acts, recipe_id)
    goals = []; unrelated_pool = []; log = []
    def do(seg):
        p = f"{out}/{seg['seg_id']}.json"; ids = seg["ids"]
        if not os.path.exists(p):
            for attempt in range(3):
                r = call_llm(SYS, USR.format(VID=vid, RECIPE=recipe or label or "unknown", SEG=seg["seg_id"], SUMMARY=seg["summary"], N=len(ids), ACTIONS="\n".join(fmt_action(T[i]) for i in ids)), model)
                r.setdefault("unassigned_action_ids", r.pop("unrelated_action_ids", [])); errs, warns = validate_window(r, ids); r["_validation"] = {"errors": errs, "warnings": warns}
                if not errs: break
                print(f"  {seg['seg_id']}: {len(errs)} errors, retry: {errs[:2]}", flush=True)
            json.dump(r, open(p, "w"), indent=1, ensure_ascii=False)
        r = json.load(open(p)); log.append({"segment": seg["seg_id"], "n": len(ids), **r.get("_validation", {})})
        for g in r.get("goals", []):
            ids_ok = [i for i in g["action_ids"] if i in T]          # 模型偶尔引用不存在的 action_id:丢掉
            if not ids_ok: continue
            goals.append({"goal_id": f"E_g{len(goals) + 1}", "description": g["description"], "action_ids": ids_ok, "segment": seg["seg_id"], "segment_summary": seg["summary"],
                          "segment_overall_goal": r.get("overall_goal"), "model_goal_id": g.get("goal_id")})
        print(f"  {seg['seg_id']} ({seg['kind']}, {len(ids)} narr): {len(r.get('goals', []))} goals, {len(r.get('unassigned_action_ids', []))} unrelated | {r.get('overall_goal')}", flush=True)
        return [i for i in r.get("unassigned_action_ids", []) if i in T]
    for seg in segs: unrelated_pool += do(seg)
    rest = sorted([a["action_id"] for a in acts if a["action_id"] not in covered] + unrelated_pool, key=lambda i: T[i]["start_s"])
    for k in range(0, len(rest), 120):
        do({"seg_id": f"nostep_{k // 120:02d}", "kind": "nostep", "summary": NOSTEP_SUMMARY, "ids": rest[k:k + 120]})
    attach_times(goals, acts)
    for g in goals: g["size_ok_4_20"] = 4 <= g["n_actions"] <= 20
    assigned = {i for g in goals for i in g["action_ids"]}; un = [a["action_id"] for a in acts if a["action_id"] not in assigned]
    merged = {"video_id": vid, "method": "E", "model": model, "existing_label": label, "recipe": recipe, "goals": goals, "unassigned_action_ids": un,
              "window_validation": log, "verification_status": "candidate (provisional, not verified)"}
    json.dump(merged, open(f"{out}/merged.json", "w"), indent=1, ensure_ascii=False)
    print(f"  {vid}: {len(goals)} sub-goals from {len(segs)} step segments; unassigned {len(un)} -> {out}/merged.json", flush=True)
    return merged


def stats(root):
    """对 root 下所有 */merged.json 算 metrics(只统计官方 step 内的 sub-goal 和 no-step 分开)。"""
    ms = [json.load(open(os.path.join(root, d, "merged.json"))) for d in sorted(os.listdir(root)) if os.path.exists(os.path.join(root, d, "merged.json"))]
    def summ(gs):
        if not gs: return {"n": 0}
        n = [g["n_actions"] for g in gs]; dur = [g["end_s"] - g["start_s"] for g in gs]
        q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))]
        return {"n": len(gs), "narrations_per_subgoal": {"median": statistics.median(n), "p10": q(n, .1), "p90": q(n, .9)},
                "duration_s": {"median": round(statistics.median(dur), 1), "p10": round(q(dur, .1), 1), "p90": round(q(dur, .9), 1)},
                "share_4_20_narrations": round(sum(4 <= x <= 20 for x in n) / len(n), 3),
                "share_interrupted_gt60s": round(sum(1 for g in gs if g["n_interruptions_gt60s"]) / len(gs), 3)}
    step_g = [g for m in ms for g in m["goals"] if not g["segment"].startswith("nostep")]
    no_g = [g for m in ms for g in m["goals"] if g["segment"].startswith("nostep")]
    per_step = collections.Counter((m["video_id"], m.get("recipe"), g["segment"]) for m in ms for g in m["goals"] if not g["segment"].startswith("nostep"))
    sps = list(per_step.values())
    return {"n_examples": len(ms), "n_official_steps": len(sps),
            "subgoals_per_official_step": {"median": statistics.median(sps), "min": min(sps), "max": max(sps), "hist": dict(sorted(collections.Counter(sps).items()))} if sps else None,
            "in_official_step": summ(step_g), "no_step_windows": summ(no_g),
            "unassigned_narrations": sum(len(m["unassigned_action_ids"]) for m in ms),
            "windows_with_validation_errors": sum(1 for m in ms for w in m["window_validation"] if w.get("errors"))}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--annot", help="HD-EPIC annotations/data 目录(含 narrations-and-action-segments/ 和 high-level/)")
    ap.add_argument("--video", nargs="*", default=[]); ap.add_argument("--recipe", help="只用这个 recipe id(一段录像里有多个 recipe 时)")
    ap.add_argument("-o", "--out", help="输出目录(单个视频时);默认 out/<video>"); ap.add_argument("--model", default=MODEL)
    ap.add_argument("--stats", metavar="ROOT", help="对 ROOT/*/merged.json 算分布,打印 JSON")
    a = ap.parse_args()
    if a.stats: print(json.dumps(stats(a.stats), indent=1, ensure_ascii=False)); sys.exit(0)
    nar, rec = load_annot(a.annot)
    for v in a.video: run(nar, rec, v, a.recipe, a.out if len(a.video) == 1 else None, a.model)
