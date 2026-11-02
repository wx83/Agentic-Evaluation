"""Solver:只看 solver_payload + 实际媒体;每题新 session;模型钉死不回退。"""
import json, re, time
import p2config as P
import media as M
import prompt as BP           # bench/prompt.py: MCQ prompt + score_choice
import formats as FM          # pyramid/formats.py: instr("plan") 等

_SYS = None

# 10-24 v6(plan_mode = "stages"):plan 题按阶段作答,与参考(cutoff 后记录的 sub-goal)同粒度;行数由 Solver 按阶段数定,不再要求 verb+object 短动作 / 4-8 行
PLAN_STAGES_INSTR = ("Starting from where the clip ends, list the remaining stages needed to finish the task the camera wearer is doing, in order. "
                     "One numbered line per stage, written at the level of what gets accomplished (for example 'chop the rest of the vegetables', "
                     "'cook them in the pan'), not individual hand movements. Use as many lines as there are stages (usually 1-6). "
                     "Reply with the numbered lines only, nothing else.")


def build_prompt(payload, mat, history_text=None, plan_mode=None, goal=None, goal_phrase=None):
    """history_text(10-14):下层题 + 答案的文字块,放在题目之前;task_conditions 为空时不加任何 goal 行。
    goal(10-27 晚,用户定):L4 题给出这一步的官方 goal(contract.l4_show_goal);L1–L3 不给。"""
    fmt, q = payload["format"], payload["question"]
    cond = payload.get("task_conditions")
    pre = ""
    if goal:
        pre += ("The camera wearer's goal for this task (given to you; it is " + (goal_phrase or "the recipe step they are working on") + "): " + goal.strip() + "\n"
                "\"The task\" in the question means this goal; it is finished when this goal is achieved.\n\n")
    if cond:
        pre += "Conditions: " + (cond if isinstance(cond, str) else json.dumps(cond, ensure_ascii=False)) + "\n"
    if history_text:
        pre += history_text.rstrip("\n") + "\n\n"
    if mat and mat.get("time_map", {}).get("kind") == "concat":
        segs = mat["time_map"]["segments"]
        if mat.get("cards"):
            pre += ("The clip is %d segments joined back to back. Each segment is preceded by a 1-second title card ('Segment 1', 'Segment 2'); "
                    "segment footage at clip time: %s.\n") % (len(segs), ", ".join(f"segment {k + 1} = {s['clip_start']:.0f}-{s['clip_end']:.0f}s" for k, s in enumerate(segs)))
        else:
            pre += "The clip is %d segments joined back to back (segment boundaries at clip time: %s).\n" % (
                len(segs), ", ".join(f"{s['clip_start']:.0f}-{s['clip_end']:.0f}s" for s in segs))
    if payload.get("sg_item"):                                   # 10-28 v15:多段拼接(乱序 / 顺序)说明
        if payload["sg_item"].get("shuffled"):
            pre += "The segments come from different moments of the same activity and are NOT in chronological order; work out the true order from what you see.\n"
        else:
            pre += "The segments come from different moments of the same activity, in chronological order; some time passed between them. Combine what you see in all segments.\n"
    if payload.get("integration_item"):
        pre += "The two segments come from two different moments of the same activity, in chronological order; some time passed between them. Combine what you see in both segments.\n"
    if payload.get("gap_item"):
        pre += ("Segment 1 ends where a hidden part of the activity begins; segment 2 starts right after the hidden part. "
                "Work out what happened in between from the state before and after (and from the earlier answers above, if any).\n")
    if payload.get("observation_cutoff") is not None:
        pre += "The clip ends at the moment you must answer; do not assume what happens afterwards.\n"
    if fmt == "single_choice":
        return pre + BP.build(q, payload["options"])
    if fmt == "multi_select":
        return pre + ("Question: " + q + "\nStatements:\n" + "\n".join(payload["options"]) +
                      "\n\nSelect every statement that is true for this clip (one or more).\nReply on exactly two lines, nothing else:\n"
                      "Answer: <letters separated by commas, or NONE>\nTime: <M:SS>   (when in the clip the evidence you used occurs)")
    if fmt == "short_answer":
        return pre + f"Question: {q}\n\nReply on exactly two lines, nothing else:\nAnswer: <a short phrase>\nTime: <M:SS>   (when in the clip the evidence you used occurs)"
    if fmt == "plan":
        if plan_mode == "stages":
            return pre + f"Question: {q}\n\n" + PLAN_STAGES_INSTR
        label = "Goal" if q.lstrip().lower().startswith("goal") else "Task"
        return pre + f"{label}: {q}\n\n" + FM.instr("plan")
    if fmt == "bbox":
        return pre + (f"Question: {q}\n\nLook at the FIRST frame of the clip. Reply on exactly two lines, nothing else:\n"
                      "Box: <x_min>, <y_min>, <x_max>, <y_max>   (percent of the frame width and height, 0-100, origin at the top-left corner; x is horizontal, y is vertical)\n"
                      "Time: 0:00")
    if fmt == "gap_steps":
        n = (payload.get("gap_item") or {}).get("n_hidden") or 1
        return pre + (f"Question: {q}\n\nList, in order, the {n} step{'s' if n > 1 else ''} the person carried out between the end of segment 1 and the start of segment 2. "
                      f"Reply with exactly {n} numbered line{'s' if n > 1 else ''}, each one short action (verb + object), nothing else.")
    raise ValueError(fmt)


MAX_TOKENS = {"single_choice": 512, "multi_select": 512, "short_answer": 512, "plan": 1024, "gap_steps": 512, "bbox": 256}   # 3.7-flash 的 thinking 关不掉,输出配额要留给思考


QWEN_URL = None     # 10-23:contract.solver_backend == "qwen_http" 时由 solve()/solve_blind() 设置(contract.qwen_url,默认 http://127.0.0.1:8765)
QWEN_SEND_MEDIA = False   # 10-28 晚(迁移到 H200):contract.qwen_send_media = true 时把 clip 文件内容 base64 放进请求(media_b64),远程服务器不需要能读本机路径


def ask_qwen(media_path, text, max_tokens=96, run_dir=None, meta=None):
    """Qwen3-Omni 本地服务(qwen_server.py):同样 fresh session / 每题独立。"""
    import urllib.request
    t0 = time.time(); err = None; out = None; u = {}
    for attempt in range(3):
        try:
            body = {"media_path": str(media_path) if media_path else None, "text": text, "max_new_tokens": max_tokens}
            if QWEN_SEND_MEDIA and media_path:
                import base64
                body["media_b64"] = base64.b64encode(open(media_path, "rb").read()).decode(); body["media_path"] = None
            req = urllib.request.Request(QWEN_URL + "/ask", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=1800).read())
            if "error" in r: err = r["error"]; time.sleep(5); continue
            out = r["raw"]; u = {"tok_in": r["meta"].get("n_input_tokens"), "tok_out": None, "tok_think": None, "model_version": r.get("model"), "peak_gpu_mb": r["meta"].get("peak_gpu_mb")}; err = None
            if out is not None: break
            err = "empty"
        except Exception as e_:
            err = f"{type(e_).__name__}: {str(e_)[:200]}"; time.sleep(10)
    if run_dir is not None:
        from examiner import _log
        _log(run_dir, "solver" if media_path else "solver_blind", {"model": "qwen3-omni", "latency_sec": round(time.time() - t0, 2), "error": err, **u, **(meta or {})})
    if err: raise RuntimeError(f"solver(qwen) call failed: {err}")
    return out, u


def _backend(contract):
    global QWEN_URL, QWEN_SEND_MEDIA
    if contract.get("solver_backend") == "qwen_http":
        QWEN_URL = contract.get("qwen_url", "http://127.0.0.1:8765"); QWEN_SEND_MEDIA = bool(contract.get("qwen_send_media")); return "qwen_http"
    return "gemini"


def ask(media_path, text, model, thinking="off", max_tokens=96, run_dir=None, meta=None):
    import nv_gemini as NV, logging
    logging.getLogger("google_genai").setLevel(logging.ERROR); logging.getLogger("google_genai.models").setLevel(logging.ERROR)
    from google.genai import types
    part = types.Part.from_bytes(data=open(media_path, "rb").read(), mime_type="video/mp4")
    kw = dict(temperature=0.0, top_p=0.001, max_output_tokens=max_tokens)
    if "gemini-4" in model:                        # 10-23:Gemini 4 不接受 thinking_budget,只接受 thinking_level;留足输出给思考
        kw["thinking_config"] = types.ThinkingConfig(thinking_level="low"); kw["max_output_tokens"] = max(max_tokens, 4096)
    elif thinking == "off":
        kw["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    else:
        kw["max_output_tokens"] = max(max_tokens, 4096)
    t0 = time.time(); err = None; text_out = None; u = {}
    for attempt in range(5):
        try:
            r = NV.client().models.generate_content(model=model, contents=[part, "\n" + text + "\n"],
                                                    config=types.GenerateContentConfig(**kw))
            um = getattr(r, "usage_metadata", None)
            g = lambda k: getattr(um, k, None) if um is not None else None
            u = {"tok_in": g("prompt_token_count"), "tok_out": g("candidates_token_count"), "tok_think": g("thoughts_token_count"),
                 "model_version": getattr(r, "model_version", None)}
            text_out = r.text; err = None
            if text_out:
                break
            fin = str(getattr(r, "candidates", None) and r.candidates[0].finish_reason)
            err = f"empty response ({fin})"
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:300]}"
            if any(x in err for x in ("404", "NOT_FOUND")):
                break
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "RateLimit" in err:
                if attempt >= 4:
                    break
                time.sleep(75); continue
            time.sleep(2 * (attempt + 1))
    if run_dir is not None:
        from examiner import _log
        _log(run_dir, "solver", {"model": model, "latency_sec": round(time.time() - t0, 2), "error": err, **u, **(meta or {})})
    if err:
        raise RuntimeError(f"solver call failed: {err}")
    return text_out, u


CARD_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def with_cards(mat):
    """concat clip → 每段前插 1 s 黑底白字「Segment k」卡(同分辨率 / 帧率,静音);返回新 mat(cards=True,segments 的 clip 时间顺延)。"""
    import subprocess
    from pathlib import Path
    src = Path(mat["path"]); out = src.with_name(src.stem + "_cards.mp4")
    segs = mat["time_map"]["segments"]
    if not out.exists():
        pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0", str(src)],
                            capture_output=True, text=True, check=True).stdout.strip().split(",")
        w, h, fps = pr[0], pr[1], pr[2]
        fc, ins = [], ""
        for k, s in enumerate(segs):
            fc.append(f"color=c=black:s={w}x{h}:r={fps}:d=1,drawtext=fontfile={CARD_FONT}:text='Segment {k + 1}':fontcolor=white:fontsize=36:x=(w-tw)/2:y=(h-th)/2,format=yuv420p,setsar=1[c{k}]")
            fc.append(f"anullsrc=r=48000:cl=stereo,atrim=0:1,asetpts=PTS-STARTPTS[ca{k}]")
            fc.append(f"[0:v]trim=start={s['clip_start']}:end={s['clip_end']},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[v{k}]")
            fc.append(f"[0:a]atrim=start={s['clip_start']}:end={s['clip_end']},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo[a{k}]")
            ins += f"[c{k}][ca{k}][v{k}][a{k}]"
        fc.append(f"{ins}concat=n={2 * len(segs)}:v=1:a=1[v][a]")
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)], check=True, capture_output=True)
    new, acc = [], 0.0
    for s in segs:
        d = s["clip_end"] - s["clip_start"]; acc += 1.0
        new.append(dict(s, clip_start=round(acc, 3), clip_end=round(acc + d, 3))); acc += d
    return dict(mat, path=out, cards=True, duration=round(acc, 3), time_map=dict(mat["time_map"], segments=new, cards=True))


def solve(cand, contract, store, run_dir=None, history_text=None):
    from examiner import solver_payload
    payload = solver_payload(cand)
    mat = M.materialize(payload["media_refs"][0], store)
    l4 = cand.get("layer") == "L4"
    if (l4 or contract.get("sg_mode")) and contract.get("segment_cards") and mat.get("time_map", {}).get("kind") == "concat":     # 10-27 晚:gap 题两段前加 1 s 文字卡;10-28 v15:L3 拼接题也加
        mat = with_cards(mat)
    goal = None
    if l4 and contract.get("l4_show_goal") and cand.get("sample_id"):
        _ = store.evidence
        seg = next((r for r in store.by_event.get(cand["sample_id"], []) if r["kind"] == "task_segment"), None)
        goal = (seg or {}).get("value", {}).get("goal")
    text = build_prompt(payload, mat, history_text=history_text, plan_mode=contract.get("plan_mode"), goal=goal, goal_phrase=contract.get("l4_goal_phrase"))   # 10-27 晚:AEA 不是 recipe step
    meta_ = {"layer": cand["layer"], "skill": cand["capability_skill"], "candidate_id": cand["candidate_id"]}
    if _backend(contract) == "qwen_http":
        raw, u = ask_qwen(mat["path"], text, max_tokens=MAX_TOKENS.get(payload["format"], 96), run_dir=run_dir, meta=meta_)
    else:
        raw, u = ask(mat["path"], text, contract["solver_model"], thinking=contract.get("solver_thinking", "off"),
                     max_tokens=MAX_TOKENS.get(payload["format"], 96), run_dir=run_dir, meta=meta_)
    return {"raw": raw, "prompt": text, "media": str(mat["path"]), "time_map": mat["time_map"], "usage": u,
            "media_flags": mat.get("flags", []), "model": u.get("model_version") or contract["solver_model"]}


def ask_text(text, model, max_tokens=512, run_dir=None, meta=None):
    """只传文字不传 clip(盲测臂,10-21 从 l4_leak.ask_text 搬来)。"""
    import nv_gemini as NV, logging
    logging.getLogger("google_genai").setLevel(logging.ERROR)
    from google.genai import types
    kw = dict(temperature=0.0, top_p=0.001, max_output_tokens=max_tokens, thinking_config=types.ThinkingConfig(thinking_budget=0))
    if "gemini-4" in model: kw.update(thinking_config=types.ThinkingConfig(thinking_level="low"), max_output_tokens=max(max_tokens, 4096))
    t0 = time.time(); err = None; out = None; u = {}
    for attempt in range(5):
        try:
            r = NV.client().models.generate_content(model=model, contents=[text], config=types.GenerateContentConfig(**kw))
            um = getattr(r, "usage_metadata", None); g = lambda k: getattr(um, k, None) if um is not None else None
            u = {"tok_in": g("prompt_token_count"), "tok_out": g("candidates_token_count"), "tok_think": g("thoughts_token_count"),
                 "model_version": getattr(r, "model_version", None)}
            out = r.text; err = None
            if out: break
            err = "empty"
        except Exception as e_:
            err = f"{type(e_).__name__}: {str(e_)[:200]}"
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "RateLimit" in err:
                if attempt >= 4: break
                time.sleep(75); continue
            time.sleep(2 * (attempt + 1))
    if run_dir is not None:
        from examiner import _log
        _log(run_dir, "solver_blind", {"model": model, "latency_sec": round(time.time() - t0, 2), "error": err, **u, **(meta or {})})
    if err: raise RuntimeError(f"solver(blind) call failed: {err}")
    return out, u


BLIND_PRE = "You cannot see any video for this item. Answer from the text alone; if the text does not determine the answer, make your best guess.\n\n"


def solve_blind(cand, contract, run_dir=None, history_text=None):
    """盲测臂:同一道题、同样的 history 文字,但不给 clip。返回结构与 solve 相同(media=None)。"""
    from examiner import solver_payload
    payload = solver_payload(cand)
    text = BLIND_PRE + build_prompt(payload, None, history_text=history_text, plan_mode=contract.get("plan_mode"))
    meta_ = {"layer": cand["layer"], "skill": cand["capability_skill"], "candidate_id": cand["candidate_id"]}
    if _backend(contract) == "qwen_http":
        raw, u = ask_qwen(None, text, max_tokens=MAX_TOKENS.get(payload["format"], 96), run_dir=run_dir, meta=meta_)
    else:
        raw, u = ask_text(text, contract["solver_model"], max_tokens=MAX_TOKENS.get(payload["format"], 96), run_dir=run_dir, meta=meta_)
    return {"raw": raw, "prompt": text, "media": None, "time_map": None, "usage": u, "media_flags": ["blind"],
            "model": u.get("model_version") or contract["solver_model"]}
