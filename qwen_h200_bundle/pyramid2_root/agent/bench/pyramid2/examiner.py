"""Examiner 调用(system = shared + layer prompt + harness,user = runtime context JSON)、输出校验、Solver 可见载荷。"""
import json, re, time
import p2config as P
import schema, prompts, media as M
from ids import candidate_id
from context import context_hash

_PROMPTS = {}


def _prompts(contract=None):
    """按 contract.prompt_md 取 prompt(缓存按路径);没指定就用 P.MD。"""
    from pathlib import Path as _P
    path = (contract or {}).get("prompt_md") or str(P.MD)
    if path not in _PROMPTS:
        _PROMPTS[path] = prompts.md_prompts(_P(path))
    return _PROMPTS[path]


def _log(run_dir, kind, rec):
    run_dir.mkdir(parents=True, exist_ok=True)
    with open(run_dir / "usage.jsonl", "a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "role": kind, **rec}, ensure_ascii=False) + "\n")


def jparse(text):
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    try:
        return json.loads(t)
    except Exception:
        i, j = t.find("{"), t.rfind("}")
        if i >= 0 and j > i:
            return json.loads(t[i:j + 1])
        raise


def call(system, user_json, model, max_tokens=8192, thinking="default", run_dir=None, role="examiner", meta=None):
    import nv_gemini as NV, logging
    logging.getLogger("google_genai").setLevel(logging.ERROR); logging.getLogger("google_genai.models").setLevel(logging.ERROR)
    from google.genai import types
    kw = dict(temperature=0.0, max_output_tokens=max_tokens, system_instruction=system, response_mime_type="application/json")
    if thinking == "off":
        kw["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    t0 = time.time(); err = None; text = None; u = {}
    for attempt in range(5):
        try:
            r = NV.client().models.generate_content(model=model, contents=user_json, config=types.GenerateContentConfig(**kw))
            um = getattr(r, "usage_metadata", None)
            g = lambda k: getattr(um, k, None) if um is not None else None
            fin = str(getattr(r, "candidates", None) and r.candidates[0].finish_reason)
            u = {"tok_in": g("prompt_token_count"), "tok_out": g("candidates_token_count"), "tok_think": g("thoughts_token_count"),
                 "model_version": getattr(r, "model_version", None), "finish_reason": fin}
            text = r.text; err = None
            if text and "MAX_TOKENS" not in fin:
                break
            err = f"empty or truncated response ({fin})"
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:300]}"
            if any(x in err for x in ("404", "NOT_FOUND")):
                break
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "RateLimit" in err:
                if attempt >= 4:                       # 10-14:TPM 配额 429 等 75 s 再试,最多 5 次
                    break
                time.sleep(75); continue
            time.sleep(2 * (attempt + 1))
    if run_dir is not None:
        _log(run_dir, role, {"model": model, "latency_sec": round(time.time() - t0, 2), "error": err, **u, **(meta or {})})
    if err:
        raise RuntimeError(f"{role} call failed: {err}")
    return text, u


def call_qwen(system, user_json, url, max_tokens=4096, run_dir=None, role="examiner", meta=None):
    """10-28(用户:Qwen 出题 + Qwen 回答,两者分开):Examiner 走本地 qwen_server(qwen_server.py,每请求新 session,和 Solver 的请求互不共享任何上下文)。
    system + 运行时 JSON 拼成一条纯文字 prompt;只取返回里的第一个 JSON 对象。"""
    import urllib.request
    text = system.rstrip() + "\n\nRUNTIME CONTEXT (JSON):\n" + user_json + "\n\nReturn exactly one JSON object as specified under OUTPUT / HARNESS CONTRACT, and nothing else (no markdown fence, no commentary)."
    t0 = time.time(); err = None; out = None; u = {}
    for attempt in range(3):
        try:
            req = urllib.request.Request(url + "/ask", data=json.dumps({"media_path": None, "text": text, "max_new_tokens": max_tokens}).encode(), headers={"Content-Type": "application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=3600).read())
            if "error" in r: err = r["error"]; time.sleep(5); continue
            out = r["raw"]; u = {"tok_in": r["meta"].get("n_input_tokens"), "tok_out": None, "tok_think": None, "model_version": r.get("model"), "latency_model_sec": r["meta"].get("latency_sec")}; err = None
            if out: break
            err = "empty"
        except Exception as e_:
            err = f"{type(e_).__name__}: {str(e_)[:200]}"; time.sleep(10)
    if run_dir is not None:
        _log(run_dir, role, {"model": "qwen3-omni", "latency_sec": round(time.time() - t0, 2), "error": err, **u, **(meta or {})})
    if err: raise RuntimeError(f"{role}(qwen) call failed: {err}")
    return out, u


def propose(ctx, layer, contract, run_dir=None, dry_run=False):
    sys_p = prompts.system_prompt(layer, _prompts(contract))
    user = json.dumps(ctx, ensure_ascii=False)
    if dry_run:
        return {"_dry_run": True, "system_chars": len(sys_p), "user_chars": len(user)}, {}
    if contract.get("examiner_backend") == "qwen_http":
        text, u = call_qwen(sys_p, user, contract.get("qwen_examiner_url") or contract.get("qwen_url", "http://127.0.0.1:8765"), max_tokens=contract.get("examiner_max_tokens", 4096),
                            run_dir=run_dir, role="examiner", meta={"layer": layer, "skill": ctx.get("current_skill"), "phase": ctx.get("phase")})
    else:
        text, u = call(sys_p, user, contract["examiner_model"], max_tokens=contract.get("examiner_max_tokens", 8192),
                       thinking=contract.get("examiner_thinking", "default"), run_dir=run_dir, role="examiner",
                       meta={"layer": layer, "skill": ctx.get("current_skill"), "phase": ctx.get("phase")})
    try:
        out = jparse(text)
        if isinstance(out, list):                       # 偶尔把对象包成数组
            out = next((x for x in out if isinstance(x, dict)), None)
        if not isinstance(out, dict):
            raise TypeError(f"top-level JSON is {type(out).__name__}, not object")
    except Exception as e:
        if run_dir is not None:
            with open(run_dir / "examiner_failures.jsonl", "a") as f:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "layer": layer, "phase": ctx.get("phase"),
                                    "skill": ctx.get("current_skill"), "error": f"{type(e).__name__}: {str(e)[:200]}",
                                    "finish_reason": u.get("finish_reason"), "raw": text[:6000]}, ensure_ascii=False) + "\n")
        raise RuntimeError(f"examiner returned invalid JSON ({type(e).__name__}: {str(e)[:80]}; finish={u.get('finish_reason')}, len={len(text)})")
    if contract.get("examiner_backend") == "qwen_http":            # 10-28:Qwen 常把 media_id 的 "/" 写成 ":",按 cluster 的真实 media_id 纠正(只改分隔符,其余校验照旧)
        _mids = {m.get("media_id") for m in ctx.get("evidence_clusters") or [] if m.get("media_id")}
        for ref in (out.get("public") or {}).get("media_refs") or []:
            mid = ref.get("media_id")
            if isinstance(mid, str) and mid not in _mids:
                fix = next((m for m in _mids if m.replace("/", ":") == mid.replace("/", ":")), None)
                if fix: ref["media_id"] = fix
    out["_raw_len"] = len(text)
    return out, u


_LETTER = re.compile(r"^\s*\(?([A-E])[\.\)\:]\s*")


def _opt_text(o):
    return _LETTER.sub("", o or "").strip().lower()


def check_output(out, ctx, store):
    """语义校验:结构(schema)、cluster/evidence 归属、cutoff、媒体窗口、答案泄漏、选项合法。返回错误列表(空 = 通过)。"""
    errs = schema.validate_candidate(out, ctx["phase"])
    if errs or out.get("action") not in ("PROPOSE_DIAGNOSTIC", "PROPOSE_CONFIRMATION"):
        return errs
    pub, pri = out["public"], out["private"]
    cl = {c["evidence_cluster_id"]: c for c in ctx["evidence_clusters"]}
    cid = out.get("evidence_cluster_id")
    if cid not in cl:
        return [f"evidence_cluster_id {cid} not offered"]
    c = cl[cid]
    if c.get("sg"):                                           # 10-28:由 cluster 唯一确定的形式字段程序补齐(sg.autofill),再校验
        import sg as _SG
        _SG.autofill(out, ctx, c)
    offered = {r["evidence_id"]: r for r in ctx["verified_evidence"]}
    refs = pri.get("evidence_refs") or []
    bad = [x for x in refs if (x if isinstance(x, str) else x.get("evidence_id")) not in offered]
    if bad:
        errs.append(f"evidence_refs not in context: {bad[:3]}")
    cutoff = pub.get("observation_cutoff")
    if c.get("sg") and c["sg"].get("kind") in ("L1", "L2", "L3") and cutoff is None and c["observation_cutoff"] is not None:   # 10-28 v15:L1-L3 的 cutoff = clip 结束,程序补
        wins_ = [w for ref in (pub.get("media_refs") or []) for w in (ref.get("windows") or []) if len(w) == 2]
        cutoff = pub["observation_cutoff"] = round(max(float(w[1]) for w in wins_), 3) if wins_ else c["observation_cutoff"]
    if c["observation_cutoff"] is not None:
        if cutoff is None:
            errs.append("cluster has observation_cutoff but public.observation_cutoff is null")
        elif abs(float(cutoff) - c["observation_cutoff"]) > 0.5 and not (c.get("sg") and c["sg"].get("kind") in ("L1", "L2")):
            errs.append(f"observation_cutoff {cutoff} != cluster cutoff {c['observation_cutoff']}")
    used_ao = [offered[x if isinstance(x, str) else x["evidence_id"]] for x in refs if (x if isinstance(x, str) else x.get("evidence_id")) in offered]
    if any(r["solver_access"] == "answer_only" for r in used_ao) and cutoff is None:
        errs.append("answer_only evidence used but no observation_cutoff")
    # media refs
    mr = pub.get("media_refs") or []
    for ref in mr:
        if ref.get("media_id") != c["media_id"]:
            errs.append(f"media_id {ref.get('media_id')} != cluster media {c['media_id']}")
            continue
        if c.get("sg"):                                           # 10-28 v15:窗口规则在 sg.checks(段数 / 长度 / 含 event)
            errs += M.validate_ref(ref, store, cutoff=cutoff, max_windows=max(1, len(c.get("windows") or [])), max_len=None, min_len=(0.9 if c["sg"].get("grounding") else 5.0))
            if c["sg"].get("kind") in ("L1", "L2") and c["observation_cutoff"] is None:      # 程序把 cutoff 填成 clip 末尾(history 截断用),Examiner 不用管
                ws_ = [w for w in (ref.get("windows") or []) if len(w) == 2]
                if ws_: pub["observation_cutoff"] = round(max(float(w[1]) for w in ws_), 3)
            continue
        if (c.get("l3ext") or {}).get("kind") == "integration":   # 10-27 integration 题:两窗固定 = cluster 的 windows(各 12 s)
            errs += M.validate_ref(ref, store, cutoff=cutoff, max_windows=2, max_len=P.CLIP_SEC + 0.5, min_len=7.0)
            continue
        if (c.get("l3ext") or {}).get("kind") == "grounding":     # 10-27 grounding:1 s clip,窗口 = cluster 窗口
            errs += M.validate_ref(ref, store, cutoff=cutoff, max_windows=1, max_len=2.0, min_len=0.9)
            got = [list(map(float, w)) for w in (ref.get("windows") or []) if len(w) == 2]
            if len(got) != 1 or abs(got[0][0] - c["window"][0]) > 0.05 or abs(got[0][1] - c["window"][1]) > 0.05:
                errs.append(f"grounding item: media_refs window must be exactly the offered 1 s window {c['window']}")
            continue
        if c.get("gap"):                                        # 10-24 gap 题:两窗固定 = cluster 的 windows(头尾各几秒),不许改
            errs += M.validate_ref(ref, store, cutoff=cutoff, max_windows=2, max_len=P.CLIP_SEC + 0.5, min_len=0.9)
            want = [list(map(float, w)) for w in c["windows"]]; got = [list(map(float, w)) for w in (ref.get("windows") or []) if len(w) == 2]
            if len(got) != 2 or any(abs(g_[i] - w_[i]) > 0.05 for g_, w_ in zip(got, want) for i in (0, 1)):
                errs.append(f"gap item windows must be exactly the offered head/tail windows {want}, got {got}")
            continue
        e = M.validate_ref(ref, store, cutoff=cutoff, max_windows=2 if c["two_windows_allowed"] else 1, max_len=P.CLIP_SEC + 0.5)
        errs += e
        w0, w1 = c["window"]
        for w in ref.get("windows") or []:
            if len(w) == 2 and (w[0] < w0 - 0.01 or w[1] > w1 + 0.01) and not c["two_windows_allowed"]:
                errs.append(f"window {w} outside offered window {c['window']}")
    # answer leakage / options
    q = (pub.get("question") or "").lower()
    ref = pri.get("proposed_reference_answer")
    fmt = pub.get("format")
    if fmt == "single_choice":
        opts = pub.get("options") or []
        letters = [(_LETTER.match(o or "") or [None, None])[1] for o in opts]
        if letters != ["A", "B", "C", "D"]:
            errs.append("options must be lettered A-D in order")
        if str(ref).strip().upper()[:1] not in ("A", "B", "C", "D"):
            errs.append("reference must be a letter for single_choice")
        texts = [_opt_text(o) for o in opts]
        if len(set(texts)) < len(texts):
            errs.append("duplicate options")
        for t in texts:
            if t and t in q and len(t) > 3:
                errs.append(f"option text appears in question: {t!r}")
    elif fmt == "multi_select":
        if not re.fullmatch(r"\s*(?:[A-E]\s*,?\s*)+", str(ref).upper()):
            errs.append("multi_select reference must be letters")
    elif fmt in ("short_answer", "plan", "gap_steps"):
        if isinstance(ref, str) and len(ref) > 3 and ref.lower() in q:
            errs.append("reference answer appears in question")
    # 绝对秒数泄漏:题面里出现 >= clip 总长(多窗拼接按总长)的秒数
    wlen = sum((float(w[1]) - float(w[0]) for ref in mr for w in (ref.get("windows") or []) if len(w) == 2)) or P.CLIP_SEC
    for m_ in re.finditer(r"(\d{2,5}(?:\.\d+)?)\s*(?:s\b|sec|seconds?)", q):
        if float(m_.group(1)) > wlen + 1:
            errs.append(f"absolute source timestamp in question: {m_.group(0)!r} (clip is {wlen:.0f}s)"); break
    used_recs = [offered[x if isinstance(x, str) else x["evidence_id"]] for x in refs if (x if isinstance(x, str) else x.get("evidence_id")) in offered]
    errs += _frame_statement_checks(q, used_recs)
    errs += _spatial_gold_fields(pri, used_recs)
    for coach in ("previous question", "previous answer", "earlier answer", "you said", "you answered", "you previously",
                  "last time", "correct your", "try again", "this time"):
        if coach in q:
            errs.append(f"question references earlier answers (coaching): {coach!r}")
    for bad_word in ("annotation", "timeline", "ground truth", "evidence_id", "label:"):
        if bad_word in q:
            errs.append(f"forbidden word in question: {bad_word}")
    if re.search(r"\b(hdepic|hdepic_e|ego4d|egoplan|aea_p):[A-Za-z0-9-]+:", q):
        errs.append("evidence id leaked into question")
    tc = next((t for t in (ctx.get("task_context") or []) if t.get("evidence_cluster_id") == cid), None)
    if tc:
        vis = set()
        for r_ in offered.values():
            if r_.get("solver_access") != "observed": continue
            v_ = r_.get("value") or {}
            for w_ in re.findall(r"[a-z]+", ((v_.get("text") or "") + " " + " ".join(v_.get("nouns") or []) + " " + (v_.get("name") or "") + " " + (v_.get("label") or "")).lower()):
                if len(w_) > 2: vis.add(_stem(w_))
        errs += _task_context_checks(pub, tc, q, visible=frozenset(vis))
        errs += _reference_checks(out, ctx, cid, tc)
        errs += _plan_stage_checks(out, ctx, tc)
        errs += _scope_coverage_checks(out, ctx, cid)
    if c.get("gap"):
        errs += _gap_checks(out, c, q)
    if c.get("l3ext"):
        import l3ext
        errs += l3ext.checks(out, ctx, c, store)
    if c.get("sg") and c["sg"].get("kind") in ("L1", "L2", "L3"):
        import sg as _SG
        errs += _SG.checks(out, ctx, c, store)
    if fmt == "gap_steps" and not c.get("gap"):
        errs.append("format gap_steps is only for plan_gap_filling clusters")
    errs += _tree_checks(out, ctx)
    errs += _difficulty_checks(out, ctx, c)
    return errs


def _difficulty_checks(out, ctx, c):
    """10-25 v8 阶梯:controller 定的档 = 题型 + 窗长上限;Examiner 只能在里面出题。"""
    d = ctx.get("difficulty")
    if not d:
        return []
    e = []
    pub = out["public"]; fmt = pub.get("format")
    if fmt != d.get("format"):
        e.append(f"difficulty level {d.get('level')} requires format {d.get('format')!r} (got {fmt!r})")
    if not c.get("gap") and not c.get("sg") and (c.get("l3ext") or {}).get("kind") != "integration" and d.get("window_max_sec"):
        total = sum(float(w[1]) - float(w[0]) for ref in (pub.get("media_refs") or []) for w in (ref.get("windows") or []) if len(w) == 2)
        if total > float(d["window_max_sec"]) + 0.01:
            e.append(f"difficulty level {d.get('level')}: the clip must be at most {d['window_max_sec']:.0f} s long (got {total:.1f} s); pick the sub-window that contains the target moment")
    if d.get("distractors") == "task_steps" and fmt == "single_choice":          # 10-27 晚 L4 统一四档第 2 档:不得复用官方四选项
        tcs = ctx.get("task_context") or []
        _nz = lambda x: re.sub(r"[^a-z0-9 ]+", " ", str(x or "").lower()).strip()
        official = {_nz(_opt_text(x)) for t in tcs for x in ((t.get("next_action") or {}).get("choices") or []) if x}
        opts = {_nz(_opt_text(o)) for o in (pub.get("options") or [])}
        if official and len(opts & official) >= 2:
            e.append(f"difficulty level {d.get('level')} (distractors = task_steps): options reuse the official choices; write distractors from this task's other recorded sub-goals or plausible-but-wrong actions")
    return e


GAP_TYPES = {"order_violation", "state_conflict", "plausible_unobserved", "skip"}
_OBJ_EXTRA = {"continue", "keep", "finish", "begin", "start", "more", "another", "first", "second", "third", "remaining", "additional", "all", "then", "pan", "frying"}


def _shares_object(want, got):
    """改写后的参考步骤至少保留隐藏 sub-goal 的一个内容词(词干),否则视为不对应。"""
    skip = _STOP | _OBJ_EXTRA
    w = {_stem(t) for t in re.findall(r"[a-z]+", (want or "").lower()) if t not in skip and len(t) > 2}
    g = {_stem(t) for t in re.findall(r"[a-z]+", (got or "").lower()) if len(t) > 2}
    return not w or bool(w & g)


def _split_steps(text):
    """选项 / 参考里的步骤序列:按 '→' / '->' / ';' / 编号切。"""
    t = str(text or "")
    parts = re.split(r"\s*(?:→|->|=>|;|\n)\s*|\s*(?<!\d)\d+[\.)]\s+", t)
    return [p.strip(" .") for p in parts if p and p.strip(" .")]


def _gap_checks(out, c, q):
    """10-24 plan_gap_filling:private.gap 必填且与 cluster 一致;单选 = 4 个步骤序列选项,参考选项逐步对应隐藏 sub-goal,
    干扰项类型齐(≥2 步时必须含 order_violation);题面不含隐藏步骤原句;public.gap_item.n_hidden 正确。"""
    e = []; pub, pri = out["public"], out["private"]; g = c["gap"]; fmt = pub.get("format")
    if fmt not in ("single_choice", "gap_steps"):
        return [f"gap item format must be single_choice or gap_steps, got {fmt}"]
    pg = pri.get("gap") or {}
    if list(pg.get("hidden_idx") or []) != list(g["hidden_idx"]) or pg.get("head_idx") != g["head_idx"] or pg.get("tail_idx") != g["tail_idx"]:
        e.append(f"private.gap must repeat the cluster's gap (head {g['head_idx']}, hidden {g['hidden_idx']}, tail {g['tail_idx']})")
    if (pub.get("gap_item") or {}).get("n_hidden") != g["n_hidden"]:
        e.append(f"public.gap_item.n_hidden must be {g['n_hidden']}")
    hidden = g.get("hidden_steps") or g.get("hidden_texts") or []
    for h in hidden:
        t = (h or "").strip().lower()
        if t and len(t) > 3 and t in q:
            e.append(f"hidden step text appears in question: {t!r}")
    if not isinstance(pg.get("order_constraints"), list):
        e.append("private.gap.order_constraints must be a list (pairs [earlier_idx, later_idx] that are physical preconditions; may be empty)")
    ref = pri.get("proposed_reference_answer")
    if fmt == "single_choice":
        opts = pub.get("options") or []
        letter = str(ref).strip().upper()[:1]
        by = {(_LETTER.match(o or "") or [None, None])[1]: _opt_text(o) for o in opts}
        all_subs = [t.lower().strip() for t in (c["gap"].get("all_step_texts") or [])]
        def _nz(t): return re.sub(r"[^a-z0-9 ]+", " ", (t or "").lower()).split()
        for L_, txt in by.items():                                   # 10-24:选项必须改写,不得照抄任何 sub-goal 原文(下层 history 题里出现过这些原句)
            for seg_ in _split_steps(txt):
                if _nz(seg_) and any(_nz(seg_) == _nz(s_) for s_ in all_subs):
                    e.append(f"option {L_} copies a sub-goal text verbatim ({seg_!r}); rewrite every step in your own words"); break
        if letter in by:
            steps = _split_steps(by[letter])
            if len(steps) != len(hidden):
                e.append(f"reference option must list exactly {len(hidden)} steps joined by '→' (got {len(steps)})")
            else:
                for want, got in zip(hidden, steps):
                    if not _shares_object(want, got):
                        e.append(f"reference option step {got!r} does not describe hidden sub-goal {want!r} (must keep its object)"); break
        dt = pg.get("distractor_types") or {}
        others = [L for L in "ABCD" if L != letter]
        if set(dt) != set(others) or any(v not in GAP_TYPES for v in dt.values()):
            e.append(f"private.gap.distractor_types must map the 3 distractor letters {others} to one of {sorted(GAP_TYPES)}")
        elif len(hidden) >= 2 and "order_violation" not in dt.values():
            e.append("with 2+ hidden steps at least one distractor must be an order_violation")
        for L in others:
            if L in by and len(_split_steps(by[L])) > len(hidden) + 1:
                e.append(f"distractor {L} has too many steps")
        de = pg.get("distractor_evidence") or {}
        if any(L not in de for L in others):
            e.append("private.gap.distractor_evidence must give, for each distractor letter, the evidence_ids (head/tail records) that contradict it")
    else:
        steps = _split_steps(ref)
        if len(steps) != len(hidden):
            e.append(f"gap_steps reference must be a numbered list of exactly {len(hidden)} steps")
        if not pri.get("rubric"):
            e.append("gap_steps needs a rubric (step recall by verb+object, order_constraints, no step contradicting the segments)")
    return e


_VIEW_WORDS = ("camera wearer", "wearer's", "camera's perspective", "from the camera", "your right", "your left", "wearer's right", "wearer's left",
               "from the wearer", "point of view", "viewpoint", "as the camera faces", "the way the camera", "you are facing", "egocentric", "from where you")
_RELATIVE_WORDS = ("among", "of these", "of the following", "which of", "the following", "listed", "candidates", "of the objects", "between these", "out of these")


def _frame_statement_checks(q, used_recs):
    """用户 10-20:位置类题必须在题面写清 (1) 从谁的视角(egocentric 要说 from the camera wearer's viewpoint / 面朝方向;allocentric 要点名参照物),
    (2) 是相对位置、只在列出的候选里比,(3) 问的是记录里的那个极值 / 象限 / 方位。q 已小写。"""
    e = []
    for r_ in used_recs:
        if r_["kind"] != "spatial_relation":
            continue
        v = r_["value"]; rel = str(v.get("relation", "")); ref = str(v.get("reference_object") or "").lower()
        ego = rel.startswith("side_") or rel.startswith("ego_")
        if ego:
            if not any(w in q for w in _VIEW_WORDS):
                e.append(f"{rel}: question must say from whose viewpoint (egocentric: 'from the camera wearer's own viewpoint', the wearer's left/right as the camera faces)")
            if ("left" in q or "right" in q) and not any(w in q for w in ("wearer's", "your", "their", "camera's", "own")):
                e.append(f"{rel}: 'left'/'right' must be possessed (the wearer's / your / the camera's left or right), never bare")
        else:
            if ref and ref not in q and (ref.split()[-1] not in q):
                e.append(f"{rel}: question must name the reference object ({v.get('reference_object')!r}) the distance is relative to")
            if rel in ("nearest", "farthest", "order_by_distance", "near") and any(w in q for w in (" left", " right", "behind")):
                e.append(f"{rel}: allocentric distance relation; do not phrase it with left/right/behind")
        if rel in ("nearest", "farthest", "order_by_distance", "side_left", "side_right", "ego_behind") and not any(w in q for w in _RELATIVE_WORDS):
            e.append(f"{rel}: relative position; question must make clear it compares only the listed candidates ('among the following objects', 'which of these')")
        if rel.startswith("side_") and not any(w in q for w in ("farthest", "furthest", "most", "rightmost", "leftmost", "far right", "far left")):
            e.append("side relation: the derived fact is the object FARTHEST to one side; question must ask for the farthest/rightmost/leftmost, not merely 'to the right of X'")
        if rel in ("nearest", "farthest", "nearest_final") and not any(w in q for w in ("closest", "nearest", "farthest", "furthest")):
            e.append("near/far relation: question must ask for the closest/farthest object")
        if rel == "ego_behind" and "behind" not in q:
            e.append("ego_behind relation: question must ask which object is BEHIND the camera wearer")
        if rel == "ego_sector":
            if not any(w in q for w in ("front-left", "front-right", "back-left", "back-right", "front left", "front right", "back left", "back right", "quadrant")):
                e.append("ego_sector relation: question must ask for the quadrant (front-left / front-right / back-left / back-right) relative to the camera wearer")
            if not any(w in q for w in ("facing", "faces", "as the camera", "the way the camera", "from the camera wearer")):
                e.append("ego_sector relation: question must state the wearer's facing direction (the way the camera faces) as the reference")
    return e


def _spatial_gold_fields(pri, used_recs):
    """10-15 spec §10:用到 spatial_relation 的题,private 必须带 reference_frame(ego 关系 = camera_at_time + reference_timestamp)、tolerance(distance)、target_ids。
    Examiner 没给就从锚点记录的 value.query_frame / tolerance_m / instance_ids 确定性补齐(不是模型猜的);给了但与记录矛盾才算错。
    锚点是 MODEL_ESTIMATED_3D 且未 verified 时,private.gold_basis_flags 加 MODEL_CHECKED_ONLY。"""
    e = []
    rels = [r for r in used_recs if r["kind"] == "spatial_relation"]
    if not rels:
        return e
    anchor = rels[0]; v = anchor.get("value") or {}
    qf = v.get("query_frame") or {"type": ("camera_at_time" if str(v.get("relation", "")).startswith(("side_", "ego_")) else "world"), "reference_timestamp": v.get("anchor_time_sec")}
    given = pri.get("reference_frame")
    if not isinstance(given, dict):
        pri["reference_frame"] = {"type": qf.get("type"), "reference_timestamp": qf.get("reference_timestamp"), "frame_id": qf.get("frame_id"), "camera_pose_ref": qf.get("camera_pose_ref"),
                                  "frame_of_reference": v.get("frame_of_reference"), "source": "filled_from_anchor_record"}
    else:
        if given.get("type") and qf.get("type") and given["type"] != qf["type"]:
            e.append(f"reference_frame.type {given.get('type')} != anchor record {qf.get('type')}")
        if not given.get("frame_of_reference") and v.get("frame_of_reference"):
            given["frame_of_reference"] = v["frame_of_reference"]          # 语义块(egocentric / allocentric、viewpoint、参照物)始终带上
        rt = given.get("reference_timestamp")
        if rt is not None and qf.get("reference_timestamp") is not None and abs(float(rt) - float(qf["reference_timestamp"])) > 0.5:
            e.append(f"reference_frame.reference_timestamp {rt} != anchor time {qf['reference_timestamp']}")
    if v.get("relation") == "distance":
        tol = pri.get("tolerance")
        if not isinstance(tol, dict) or tol.get("abs_m") is None:
            pri["tolerance"] = {"abs_m": v.get("tolerance_m") or 0.2, "basis": "max(0.2 m, 2σ of the two resting positions)", "source": "filled_from_anchor_record"}
        elif v.get("tolerance_m") is not None and float(tol["abs_m"]) < float(v["tolerance_m"]) - 1e-6:
            e.append(f"tolerance.abs_m {tol['abs_m']} tighter than the record's {v['tolerance_m']}")
    if not pri.get("target_ids"):
        ids_ = v.get("instance_ids") or {}
        pri["target_ids"] = sorted(set(ids_.values())) if isinstance(ids_, dict) else []
    if not pri.get("event_refs") and v.get("anchor_event_ref"):
        pri["event_refs"] = [v["anchor_event_ref"]]
    if any("MODEL_ESTIMATED_3D" in (r.get("quality_flags") or []) and (r.get("verification") or {}).get("status") != "verified" for r in rels):
        fl = pri.setdefault("gold_basis_flags", [])
        if "MODEL_CHECKED_ONLY" not in fl: fl.append("MODEL_CHECKED_ONLY")
    return e


def _tree_checks(out, ctx):
    """10-22 题树:scope_id 必须 = 节点 id;format ∈ allowed_formats;题面不得复述子节点答案或题面。"""
    e = []
    if out.get("action") not in ("PROPOSE_DIAGNOSTIC", "PROPOSE_CONFIRMATION"):
        return e
    pub = out.get("public") or {}; pri = out.get("private") or {}
    af = ctx.get("allowed_formats")
    if af and pub.get("format") not in af:
        e.append(f"format must be one of {af} (allowed_formats)")
    tn = ctx.get("tree_node")
    if not tn:
        return e
    if pri.get("scope_id") != tn["node_id"]:
        e.append(f"private.scope_id must be the tree node id {tn['node_id']!r}")
    q = _norm_ws(pub.get("question") or "").lower()          # 只查题面:选项里出现子节点答案是正常的(L4 选项 = 记录步骤)
    for ch in tn.get("children") or []:
        ans = _norm_ws(str(ch.get("reference_answer") or "")).lower()
        ans = ans.split(". ", 1)[1] if len(ans) > 3 and ans[1:3] == ". " else ans
        if len(ans) > 3 and ans in q:
            e.append(f"question restates a child node's answer ({ans[:40]!r}); the Solver already has it in history")
        cq = _norm_ws(str(ch.get("question") or "")).lower()
        if len(cq) > 40 and cq in q:
            e.append("question quotes a child node's question text")
    return e


def _norm_ws(s):
    return " ".join(s.split())


def _scope_coverage_checks(out, ctx, cid):
    """scope = 覆盖清单(10-14 晚):有未问过的条目就必须选未问过的;追问换 event 时不得问原错题同一条目。"""
    e = []
    ss = ctx.get("skill_scope") or []
    if not ss:
        return e
    sid = (out.get("private") or {}).get("scope_id")
    unasked = [x for x in ss if not x.get("already_asked")]
    unasked_here = [x for x in unasked if cid in x.get("evidence_cluster_ids", [])]
    hyp = ctx.get("diagnosis_hypothesis") or {}
    if hyp.get("type") == "format_sensitivity":
        return e
    if sid is None:
        if unasked_here:
            e.append(f"skill_scope has unasked entries for this cluster ({[x['scope_id'] for x in unasked_here][:6]}); target one and set private.scope_id")
        return e
    ent = next((x for x in ss if x["scope_id"] == sid), None)
    if ent is None:
        e.append(f"scope_id {sid!r} is not among the offered skill_scope entries")
    elif ent.get("already_asked") and unasked_here:
        e.append(f"scope entry {sid!r} was already asked in this layer; cover an unasked entry instead ({[x['scope_id'] for x in unasked_here][:6]})")
    same_sample = any(t.get("evidence_cluster_id") == cid and t.get("task_id") == hyp.get("original_sample_id") for t in (ctx.get("task_context") or [])) if hyp.get("original_sample_id") else True
    if hyp.get("type") in ("chance_error", "interference", "skill_unstable", "lucky_pass") and hyp.get("original_scope_id") and sid == hyp["original_scope_id"] and same_sample:
        e.append(f"follow-up must target a different scope entry than the original item ({hyp['original_scope_id']!r})")
    return e


def _ref_text(pub, pri):
    ref = pri.get("proposed_reference_answer")
    if pub.get("format") == "single_choice":
        L = str(ref).strip().upper()[:1]
        for o in pub.get("options") or []:
            m = _LETTER.match(o or "")
            if m and m.group(1) == L:
                return _opt_text(o)
        return None
    return str(ref or "").strip().lower()


def _loose_match(want, got):
    """去冠词 / 标点、粗词干后比较:词集包含或 difflib ≥ 0.8。"""
    import difflib
    def toks(x):
        return [_stem(w) for w in re.findall(r"[a-z0-9]+", (x or "").lower()) if w not in ("the", "a", "an", "his", "her", "their", "its")]
    a, b = toks(want), toks(got)
    if not a or not b:
        return True
    return set(a) <= set(b) or set(b) <= set(a) or difflib.SequenceMatcher(None, " ".join(a), " ".join(b)).ratio() >= 0.8


def _reference_checks(out, ctx, cid, tc):
    """EgoPlan cutoff 题的参考答案是确定的:next_step_prediction = cutoff 处开始的第一条 answer_only 步骤;goal_conditioned_planning = next_action。"""
    e = []
    sk = ctx.get("current_skill"); pub, pri = out["public"], out["private"]
    if pub.get("format") not in ("single_choice", "short_answer") or sk == "plan_gap_filling":
        return e
    got = _ref_text(pub, pri)
    if sk == "next_step_prediction":
        ao = sorted([r for r in ctx["verified_evidence"] if r["evidence_cluster_id"] == cid and r["role"] == "target"
                     and r["solver_access"] == "answer_only" and r["kind"] == "task_step"], key=lambda r: r["time"]["start_sec"])
        if ao:
            want = (ao[0]["value"].get("text") or "").strip().lower()
            if want and got is not None and not _loose_match(want, got):
                e.append(f"next_step_prediction reference must be the first recorded step after the cutoff: {want!r} (got {got!r})")
    elif sk == "goal_conditioned_planning":
        cutoff = pub.get("observation_cutoff"); task_end = (tc.get("task_window") or [None, None])[1]
        if cutoff is not None and task_end is not None and float(cutoff) < float(task_end) - 0.5:
            # 中间截断(单视频演示 run):参考答案 = cutoff 后第一条记录步骤,官方选项不适用
            ao = sorted([r for r in ctx["verified_evidence"] if r["evidence_cluster_id"] == cid and r["role"] == "target"
                         and r["solver_access"] == "answer_only" and r["kind"] == "task_step"], key=lambda r: r["time"]["start_sec"])
            want = (ao[0]["value"].get("text") or "").strip().lower() if ao else ""
        else:
            want = ((tc.get("next_action") or {}).get("text") or "").strip().lower()
        if want and got is not None and not _loose_match(want, got):
            e.append(f"goal_conditioned_planning reference must be the recorded next action {want!r} (got {got!r})")
    return e


_STOP = {"the", "a", "an", "and", "of", "for", "to", "on", "in", "with", "up", "out", "by", "from", "at", "its", "his", "her", "their",
         "some", "into", "onto", "my", "your", "our", "it", "is", "be", "or", "as"}


# 10-25:英美 / 同义词归一(Examiner 改写 aubergine→eggplant 时宾语词干对应检查不该挂)
_SYN = {"eggplant": "aubergine", "zucchini": "courgette", "cilantro": "coriander", "skillet": "pan", "capsicum": "pepper", "refrigerator": "fridge",
        "faucet": "tap", "trash": "bin", "garbage": "bin", "stovetop": "stove", "hob": "stove", "burner": "stove", "cooktop": "stove", "chilli": "chili",
        "chillies": "chili", "chilies": "chili", "tumbler": "glass", "spatula": "spatula", "ladle": "spoon", "jug": "jug", "pitcher": "jug", "mixer": "blender"}


def _stem(w):
    w = _SYN.get(w, w)
    for suf in ("ing", "ies", "es", "ed", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _plan_stage_checks(out, ctx, tc):
    """10-24 v6 plan_mode = stages:plan 题题面不给步数;参考 = cutoff 之后记录的 sub-goal(最多 8 个)按顺序逐行,每行与记录步骤对应;要有 rubric。"""
    e = []
    pub, pri = out["public"], out["private"]
    if pub.get("format") != "plan" or ctx.get("plan_mode") != "stages":
        return e
    q = (pub.get("question") or "").lower()
    if re.search(r"\b\d+\s*(?:-|–|to)\s*\d+\s*(?:steps?|stages?|actions?)\b", q) or re.search(r"\b(?:next|following)\s+\d+\s+(?:steps?|stages?|actions?)\b", q):
        e.append("stages mode: the question must not state how many steps/stages to list (the Solver decides the count); ask for the remaining stages, in order")
    cutoff = pub.get("observation_cutoff")
    remaining = [s_ for s_ in (tc.get("steps") or []) if cutoff is not None and s_["t0"] >= float(cutoff) - 1e-6][:8]
    if not remaining:
        return e + ["stages mode: no recorded sub-goal after the cutoff; use single_choice ('the step is complete') instead of plan"]
    lines = _split_steps(pri.get("proposed_reference_answer"))
    if len(lines) != len(remaining):
        e.append(f"stages mode: reference must list exactly the {len(remaining)} recorded sub-goals after the cutoff, one numbered line each in recorded order (got {len(lines)} lines)")
    else:
        for l, s_ in zip(lines, remaining):
            if not (_loose_match((s_.get("text") or "").lower(), (l or "").lower()) or _shares_object(s_.get("text"), l)):
                e.append(f"stages mode: reference line {l!r} does not correspond to the recorded sub-goal {s_.get('text')!r} (keep the same verb and object)"); break
    if not pri.get("rubric"):
        e.append("stages mode: rubric must say which adjacent stages are interchangeable and which Solver stages would contradict the clip's end state")
    return e


def _task_context_checks(pub, tc, q, visible=frozenset()):
    """EgoPlan(10-14 用户定):Solver 看不到 goal / 步骤表 -> task_conditions 必须空,题面不得说出 goal、不得出现 cutoff 之后的步骤。
    10-25:visible = 窗口内 observed 记录里出现过的词(食材 / 物体名),这些词题面可以说(画面里看得见),不算复述 goal;只有 goal 里的目的性词才算。"""
    e = []
    if pub.get("task_conditions") not in (None, {}, "", []):
        e.append("task_conditions must be null: the Solver never sees the goal or the plan")
    goal = (tc.get("goal") or "").strip().lower()
    opts_text = " ".join(_opt_text(o) for o in (pub.get("options") or []))
    if goal and len(goal) > 3 and (goal in q or goal in opts_text):
        e.append("goal text appears in question/options; refer only to 'the task the camera wearer is doing'")
    gw = [w for w in re.findall(r"[a-z]+", goal) if w not in _STOP and len(w) > 2 and _stem(w) not in visible]
    qw = {_stem(w) for w in re.findall(r"[a-z]+", q)}
    hit = [w for w in gw if _stem(w) in qw]
    verb = gw[0] if gw else None
    if len(hit) >= 3 or (verb and _stem(verb) in qw and any(_stem(w) in qw for w in gw[1:])):
        e.append(f"question restates the goal (goal words {hit}); describe only what is visible, never the task's purpose")
    cutoff = pub.get("observation_cutoff")
    future = [(tc.get("next_action") or {}).get("text")]
    if cutoff is not None:
        future += [s_["text"] for s_ in tc.get("steps") or [] if s_["t0"] >= float(cutoff) - 1e-6]
    for txt in future:
        t = (txt or "").strip().lower()
        if t and len(t) > 3 and t in q:
            e.append(f"recorded step after the cutoff appears in question: {t!r}")
    return e


def solver_payload(cand):
    """唯一的 Solver 可见序列化入口:只取 public。"""
    pub = cand["output"]["public"]
    return {"format": pub["format"], "question": pub["question"], "options": pub.get("options"),
            "task_conditions": pub.get("task_conditions"), "media_refs": pub["media_refs"],
            "observation_cutoff": pub.get("observation_cutoff"), **({"gap_item": pub["gap_item"]} if pub.get("gap_item") else {}),
            **({"sg_item": pub["sg_item"]} if pub.get("sg_item") else {})}


def make_candidate(out, ctx, contract, layer, turn, usage, prompt_h, cluster, errors):
    ch = context_hash(ctx)
    return {"candidate_id": candidate_id(contract["run_id"], layer, turn, ch), "run_id": contract["run_id"], "layer": layer,
            "turn": turn, "phase": ctx["phase"], "video_id": cluster["video_id"] if cluster else None,
            "original_subtype": ctx["capability_mapping"]["original_skill"] if ctx.get("capability_mapping") else None,
            "capability_skill": ctx.get("current_skill"), "registry_version": P.REGISTRY_VERSION,
            "taxonomy_version": P.TAXONOMY_VERSION, "prompt_version": contract.get("prompt_version", P.PROMPT_VERSION), "prompt_hash": prompt_h,
            "scope_id": ((out.get("private") or {}) if isinstance(out.get("private"), dict) else {}).get("scope_id"),
            "sample_id": cluster.get("sample_id") if cluster else None,
            "context_hash": ch, "model": contract["examiner_model"], "usage": usage,
            "check_errors": errors, "output": out, "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
