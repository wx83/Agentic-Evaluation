#!/usr/bin/env python3
"""Expected-event planner(pyramid2 sub-goal planner,11-03 版)— 独立可运行版。

输入:一个 task 的 goal + 有序 sub-goal 文字(不给视频、不给标注、不生成时间)。
输出:每个 sub-goal 必然发生的 event(action / sound / placement / state / speech)、相邻 sub-goal 之间的 L3 关系、L4 决策点。
与 pyramid2 里 `sg.py` 的 build_input / validate / plan_one 逐字一致(见 reference/sg.py),只把 Gemini 调用换成直接走 OpenRouter(OpenAI 协议),
不依赖 evidence store。pyramid2 里后续的 `sg.match_events`(把 event 对到标注记录拿时间)不在本文件,见 reference/sg.py §2。

用法:
  export OPENROUTER_API_KEY=sk-or-...
  python3 planner.py examples/hdepic_task61.input.json -o out.json [--model google/gemini-3.1-pro-preview] [--skills a,b,c]
  python3 planner.py --validate-only out.json examples/hdepic_task61.input.json      # 只跑 validate
输入 JSON 最少要有 {"task_id", "goal", "sub_goals": [{"idx": 1, "text": "..."}]};可选 "annotated_events"(AEA 用:已标注的 speech / sound 事件,planner 从中选并引用 id)。
"""
import json, hashlib, time, re, sys, os, argparse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPT = HERE / "prompts" / "planner_subgoal_events.md"
DEFAULT_MODEL = "google/gemini-3.1-pro-preview"
EVENT_TYPES = ("action", "sound", "placement", "state", "speech")
L3_REL_SKILL = {"object_continuity": "cross_event_integration", "state_change": "cross_event_integration",
                "causal_prerequisite": "causal_prerequisite_reasoning", "hidden_state": "hidden_state_inference", "spatial_end_state": "spatial_state_integration"}
SKILL_DEFS = {
    "object_recognition": "L1: which object is in hand / being handled at the moment of the event",
    "spatial_near": "L1: at the moment of the event, which of the listed objects is nearest to a reference object (3D positions from the dataset)",
    "spatial_side": "L1: at the moment of the event, which listed object is leftmost / rightmost from the wearer's viewpoint",
    "object_location_at_time": "L1: on which surface / fixture / container an object is put down at the event",
    "object_grounding": "L1: localise the object of the event in a frame (bounding box)",
    "action_recognition": "L2: what action (verb + object) the event is",
    "event_object_role": "L2: which object is acted on, with which tool, to which destination in the event",
    "action_temporal_order": "L2: the order of two actions shown close together inside one sub-goal",
    "sound_action_binding": "L2: which action / object produced the sound heard",
    "object_state_change": "L2: where an object was taken from and where it went in one movement",
    "sound_movement_binding": "L2: which object movement coincides with the sound",
    "sound_anchored_spatial_near": "L2: at the moment of a sound, which listed object is nearest to a reference object",
    "sound_anchored_spatial_side": "L2: at the moment of a sound, which listed object is leftmost / rightmost for the wearer",
}
REL_DEFS = {
    "object_continuity": "the same object / ingredient appears in an event of sub-goal k and an event of the ADJACENT sub-goal k+1; what happened to it between them (chopped broccoli -> in the pan)",
    "state_change": "how the state of an object differs between the two events (whole -> chopped, empty -> full, raw -> browned)",
    "causal_prerequisite": "the earlier event is a physical prerequisite of the later one (could not be done without it)",
    "hidden_state": "an appliance / container state was set in the earlier event and is not visible in the later segment; what is its state at the end of the later segment",
    "spatial_end_state": "after placements in the two events, which listed object ends nearest / farthest to a reference object (needs 3D records)",
}
DEFAULT_SKILLS = list(SKILL_DEFS) + sorted(set(L3_REL_SKILL.values()))


def build_input(task, skills=None):
    """task = {task_id, goal, sub_goals:[{idx,text,annotated_events?}]} -> planner 的 user JSON(与 sg.build_input 相同字段)。"""
    skills = [s for s in (skills or DEFAULT_SKILLS)]
    sgs = []
    for s in sorted(task["sub_goals"], key=lambda s: int(s["idx"])):
        d = {"idx": int(s["idx"]), "text": s["text"]}
        if s.get("annotated_events"): d["annotated_events"] = s["annotated_events"]
        sgs.append(d)
    return {"task_id": task["task_id"], "goal": task["goal"], "sub_goals": sgs,
            "skills": {s: SKILL_DEFS[s] for s in skills if s in SKILL_DEFS},
            "l3_relation_types": {k: v for k, v in REL_DEFS.items() if L3_REL_SKILL[k] in skills},
            "n_sub_goals": len(sgs)}


def validate(out, inp):
    """与 sg.validate 相同:裁掉越界 idx、未知 type / skill、非相邻 sub-goal 的 relation、越界 decision point;返回 (clean, warnings)。"""
    warn = []
    if not isinstance(out, dict) or not isinstance(out.get("sub_goals"), list):
        return None, ["no sub_goals list"]
    n = inp["n_sub_goals"]; allowed_sk = set(inp["skills"]); seen = set()
    clean = {"task_id": inp["task_id"], "goal": inp["goal"], "sub_goals": [], "relations": [], "decision_points": []}
    by_idx = {}
    for sg_ in out["sub_goals"]:
        if not isinstance(sg_, dict): continue
        try: idx = int(sg_.get("idx"))
        except Exception: continue
        if not (1 <= idx <= n): warn.append(f"sub_goal idx {idx} out of range"); continue
        evs = []
        for e in sg_.get("events") or []:
            if not isinstance(e, dict) or not e.get("description"): continue
            eid = str(e.get("event_id") or f"s{idx}e{len(evs) + 1}")
            if eid in seen: eid = f"s{idx}e{len(evs) + 1}_{len(seen)}"
            seen.add(eid)
            typ = str(e.get("type") or "action").lower()
            if typ not in EVENT_TYPES: typ = "action"
            sks = [s for s in (e.get("skills") or []) if s in allowed_sk]
            evs.append({"event_id": eid, "sub_goal": idx, "type": typ, "description": str(e["description"])[:200],
                        "objects": [str(x).lower()[:40] for x in (e.get("objects") or [])][:6], "verbs": [str(x).lower()[:30] for x in (e.get("verbs") or [])][:4],
                        "skills": sks, "relevance": str(e.get("relevance") or "")[:200],
                        "source_ids": [str(x) for x in (e.get("source_ids") or []) if isinstance(x, (str, int))][:6]})
        by_idx[idx] = {"idx": idx, "events": evs, "irrelevant": str(sg_.get("irrelevant") or "")[:200]}
    for s in inp["sub_goals"]:
        clean["sub_goals"].append(by_idx.get(s["idx"], {"idx": s["idx"], "events": [], "irrelevant": ""}))
        if s["idx"] not in by_idx: warn.append(f"sub_goal {s['idx']}: no events")
    ev_sg = {e["event_id"]: e["sub_goal"] for sg_ in clean["sub_goals"] for e in sg_["events"]}
    for r in out.get("relations") or []:
        if not isinstance(r, dict): continue
        typ = str(r.get("type") or "")
        evs = [str(x) for x in (r.get("events") or []) if str(x) in ev_sg]
        if typ not in L3_REL_SKILL: warn.append(f"relation type {typ!r} dropped"); continue
        if len(evs) < 2 or len({ev_sg[x] for x in evs}) < 2: warn.append(f"relation {r.get('rel_id')}: needs >= 2 events from different sub-goals"); continue
        if max(ev_sg[x] for x in evs) - min(ev_sg[x] for x in evs) != 1: warn.append(f"relation {r.get('rel_id')}: events must come from ADJACENT sub-goals (v16)"); continue
        clean["relations"].append({"rel_id": str(r.get("rel_id") or f"r{len(clean['relations']) + 1}"), "type": typ, "skill": L3_REL_SKILL[typ], "events": evs[:3],
                                   "ask": str(r.get("ask") or "")[:300], "answer_hint": str(r.get("answer_hint") or "")[:200]})
    for d in out.get("decision_points") or []:
        if not isinstance(d, dict): continue
        try: idx = int(d.get("idx"))
        except Exception: continue
        if 2 <= idx <= n + 1:
            clean["decision_points"].append({"idx": idx, "real": bool(d.get("real", True)), "why": str(d.get("why") or "")[:200]})
    return clean, warn


def jparse(text):
    t = (text or "").strip()
    if t.startswith("```"): t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    try: return json.loads(t)
    except Exception:
        i, j = t.find("{"), t.rfind("}")
        if i >= 0 and j > i: return json.loads(t[i:j + 1])
        raise


def call_llm(system, user_json, model, max_tokens=16384, api_key=None, base_url="https://openrouter.ai/api/v1"):
    """OpenAI 协议(OpenRouter);temperature 0、JSON 输出。返回 (text, usage)。"""
    key = api_key or os.environ.get("OPENROUTER_API_KEY") or (Path(os.environ.get("OPENROUTER_API_KEY_FILE", "")).read_text().strip() if os.environ.get("OPENROUTER_API_KEY_FILE") else None)
    if not key: raise SystemExit("set OPENROUTER_API_KEY (or OPENROUTER_API_KEY_FILE)")
    body = {"model": model, "temperature": 0.0, "max_tokens": max_tokens, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_json}]}
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    err = None
    for attempt in range(5):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=600).read())
            ch = r["choices"][0]; u = r.get("usage") or {}
            return ch["message"]["content"], {"tok_in": u.get("prompt_tokens"), "tok_out": u.get("completion_tokens"), "finish_reason": ch.get("finish_reason"), "model": r.get("model")}
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:300]}"; time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"planner call failed: {err}")


def plan(task, model=DEFAULT_MODEL, skills=None, attempts=2, **kw):
    sys_p = PROMPT.read_text()
    inp = build_input(task, skills)
    h = hashlib.sha1((sys_p + json.dumps(inp, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()[:10]
    rec = {"task_id": inp["task_id"], "prompt_hash": h, "model": model, "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "input": inp, "plan": None, "warnings": [], "usage": {}, "status": "failed"}
    last = None
    for attempt in range(attempts):
        try:
            text, u = call_llm(sys_p, json.dumps(inp, ensure_ascii=False), model, **kw)
            clean, warn = validate(jparse(text), inp)
            if clean is None: raise ValueError("; ".join(warn))
            rec.update(plan=clean, warnings=warn, usage=u, status="ok", raw_len=len(text)); break
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:200]}"; rec["warnings"].append(f"attempt {attempt + 1}: {last}")
    if rec["plan"] is None: rec["error"] = last
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("input"); ap.add_argument("-o", "--out"); ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--skills", help="comma list; default = all skills in SKILL_DEFS + L3 relation skills"); ap.add_argument("--validate-only", metavar="OUTPUT_JSON")
    a = ap.parse_args()
    task = json.load(open(a.input))
    if a.validate_only:
        raw = json.load(open(a.validate_only)); raw = raw.get("plan", raw)
        clean, warn = validate(raw, build_input(task, a.skills.split(",") if a.skills else None)); print(json.dumps({"warnings": warn, "plan": clean}, indent=1, ensure_ascii=False)); sys.exit(0)
    rec = plan(task, model=a.model, skills=a.skills.split(",") if a.skills else None)
    s = json.dumps(rec, indent=1, ensure_ascii=False)
    (Path(a.out).write_text(s) if a.out else print(s))
    p = rec.get("plan") or {}
    print(f"[planner] {rec['status']}: {sum(len(x['events']) for x in p.get('sub_goals', []))} events, {len(p.get('relations', []))} relations, {len(p.get('decision_points', []))} decision points; warnings {len(rec['warnings'])}", file=sys.stderr)
