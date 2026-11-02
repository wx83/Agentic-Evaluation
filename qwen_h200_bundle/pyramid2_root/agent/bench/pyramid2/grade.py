"""判分:选择题规则判;short_answer / plan 先规则后 Gemini judge(provisional,gold 未经人工核验)。"""
import json, re
import prompt as BP
import formats as FM

JUDGE_SYS = """You are the Verifier for a multimodal benchmark. You receive a question, a frozen reference answer
(with accepted alternatives and an optional rubric) and a Solver's answer. Decide whether the Solver's answer is
correct with respect to the reference. Treat the reference as the sole standard; do not use outside knowledge
to overrule it. For plan items, accept alternative valid orderings when the rubric allows it and judge by the
rubric criteria. Return exactly one JSON object: {"correct": true|false, "score": 0.0-1.0, "reason": "<one sentence>"}."""

# 10-24 v6(plan_mode = "stages"):plan 题三项分开判 —— coverage(参考每个阶段能否按顺序在 Solver 的行里找到对应;多行对一阶段、
# 更细的行、同义都算;"continue / keep X" 由任何做 X 的阶段覆盖)、order、contradiction(与参考或 clip 末状态矛盾的行;一致的多余细节不扣)。
# correct = 全覆盖 + 顺序对 + 0 矛盾;coverage 比例单独记在 plan_eval,区分「理解对但写得细 / 没写完」与「答偏」。
# beyond_horizon(10-24 22:45 首跑发现):Solver 不知道官方 step 在哪结束,会继续写同一道菜后面的阶段(如 paneer);这些不与 clip 末状态矛盾,只记录不扣分。
STAGES_JUDGE_SYS = """You are the Verifier for a plan item in a multimodal benchmark. The reference answer is the ordered list of
coarse stages (sub-goals) that were actually carried out after the clip ended. The Solver, who saw only the clip, listed the
stages it believes remain. Judge the Solver's list against the reference only; do not use outside knowledge to overrule it.
Score three things:
1. coverage: for each reference stage, in order, find the Solver line(s) that accomplish the same thing. Synonyms count; a
   finer-grained line, or several consecutive lines together, may cover one reference stage; a reference stage that only says
   "continue / keep / finish doing X" is covered by any Solver stage that does X. A stage is uncovered only when no Solver line
   accomplishes it.
2. order: whether the covered stages appear in the Solver's list in the reference order (ignore pairs the rubric marks as
   interchangeable; ignore uncovered stages).
3. contradictions: Solver lines that conflict with the reference or with the state at the end of the clip: a stage the
   reference shows was already completed before the clip ended (e.g. "chop the broccoli" when the reference starts by
   transferring the chopped broccoli), an action the reference rules out, or an undoing of a reference stage. Extra
   fine-grained lines that are consistent with the reference are NOT contradictions and are not penalised.
4. beyond_horizon: Solver lines that are neither covered nor contradictions - plausible later work (another dish,
   ingredient or cleaning that the reference does not mention). The Solver does not know where the reference's horizon ends,
   so list these separately and do NOT count them as contradictions.
Return exactly one JSON object:
{"coverage": [{"stage": 1, "solver_lines": [<Solver line numbers, [] if uncovered>]}, ...], "n_covered": <int>,
 "n_stages": <int>, "order_ok": true|false, "contradictions": ["<quoted Solver line> - <why it conflicts>", ...],
 "beyond_horizon": ["<quoted Solver line>", ...], "reason": "<one sentence>"}"""


def _norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).strip()


def _answer_line(raw):
    m = re.search(r"(?im)^\s*answer\s*[:：]\s*(.+?)\s*$", raw or "")
    return m.group(1).strip() if m else (raw or "").strip().splitlines()[0] if raw else ""


def grade(cand, sol, contract, run_dir=None):
    out = cand["output"]; pub, pri = out["public"], out["private"]
    fmt, raw = pub["format"], sol["raw"]
    ref = pri["proposed_reference_answer"]
    res = {"verdict": "wrong", "score": 0.0, "parsed": None, "judge": None, "reason": None, "plan_eval": None}
    if fmt == "single_choice":
        idx = BP.score_choice(raw, pub["options"])
        res["parsed"] = "ABCD"[idx] if idx is not None else None
        g = str(ref).strip().upper()[:1]
        ok = res["parsed"] == g
        res.update(verdict="correct" if ok else "wrong", score=float(ok), judge="rule")
    elif fmt == "multi_select":
        parsed, _ = FM.parse("ms", raw)
        res["parsed"] = parsed
        g = "".join(sorted(set(re.findall(r"[A-E]", str(ref).upper()))))
        p = "".join(sorted(set(parsed or "")))
        ok = parsed is not None and p == g
        jac = len(set(p) & set(g)) / len(set(p) | set(g)) if (set(p) | set(g)) else 0.0
        res.update(verdict="correct" if ok else "wrong", score=round(jac, 3), judge="rule")
    elif fmt == "short_answer":
        a = _answer_line(raw); res["parsed"] = a
        cands = [ref] + list(pri.get("accepted_alternatives") or [])
        na = _norm(a)
        hit = any(na and (_norm(c) == na or (_norm(c) in na and len(_norm(c)) > 2) or (na in _norm(c) and len(na) > 2)) for c in cands if isinstance(c, str))
        if hit:
            res.update(verdict="correct", score=1.0, judge="rule")
        else:
            res.update(**_judge(pub, pri, a, contract, run_dir))
    elif fmt == "bbox":                                        # 10-27 object_grounding:IoU >= 0.5 算对;Gemini 习惯的 [ymin,xmin,ymax,xmax] 顺序也试一次,取大者并记录
        import l3ext as LX
        got = LX.parse_bbox(raw); want = LX.parse_bbox(str(ref))
        res["parsed"] = got
        if got is None or want is None:
            res.update(verdict="wrong", score=0.0, judge="rule", reason="no box parsed")
        else:
            v1 = LX.iou(got, want); sw = [got[1], got[0], got[3], got[2]]; v2 = LX.iou(sw, want)
            v, swapped = (v2, True) if v2 > v1 + 0.05 else (v1, False)
            res.update(verdict="correct" if v >= 0.5 else "wrong", score=round(v, 3), judge="rule", reason=f"IoU {v:.2f}" + (" (yx order)" if swapped else ""))
    elif fmt == "gap_steps":                                   # 10-24:允许 1 行;逐行编号解析,再交 judge 按 rubric 判
        lines = [m.group(1).strip() for m in re.finditer(r"(?m)^\s*\d+\s*[.)]\s*(.+?)\s*$", raw or "")]
        lines = [l for l in lines if not re.match(r"(?i)^(time|because)\s*[:：]", l)]
        if not lines:
            one = [l.strip() for l in (raw or "").splitlines() if l.strip() and not re.match(r"(?i)^(time|answer)\s*[:：]", l.strip())]
            lines = one[:1]
        res["parsed"] = lines
        if not lines:
            res.update(verdict="wrong", score=0.0, judge="rule", reason="no steps")
        else:
            res.update(**_judge(pub, pri, "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines)), contract, run_dir))
    elif fmt == "plan" and contract.get("plan_mode") == "stages":    # 10-24 v6:阶段级;允许 1 行;judge 三项(见 STAGES_JUDGE_SYS)
        lines = [m.group(1).strip() for m in re.finditer(r"(?m)^\s*\d+\s*[.)]\s*(.+?)\s*$", raw or "")]
        lines = [l for l in lines if not re.match(r"(?i)^(time|because)\s*[:：]", l)]
        res["parsed"] = lines
        if not lines:
            res.update(verdict="wrong", score=0.0, judge="rule", reason="no numbered steps")
        else:
            res.update(**_judge_stages(pub, pri, lines, contract, run_dir))
    elif fmt == "plan":
        lines, _ = FM.parse("plan", raw); res["parsed"] = lines
        if not lines:
            res.update(verdict="wrong", score=0.0, judge="rule", reason="no numbered steps")
        else:
            res.update(**_judge(pub, pri, "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines)), contract, run_dir))
    return res


def _judge(pub, pri, answer, contract, run_dir):
    import nv_gemini as NV
    from examiner import call, jparse
    user = json.dumps({"question": pub["question"], "task_conditions": pub.get("task_conditions"),
                       "reference_answer": pri["proposed_reference_answer"], "accepted_alternatives": pri.get("accepted_alternatives"),
                       "acceptance_criteria": pri.get("acceptance_criteria"), "rubric": pri.get("rubric"),
                       "solver_answer": answer}, ensure_ascii=False)
    try:
        text, u = call(JUDGE_SYS, user, contract.get("judge_model", contract["examiner_model"]), max_tokens=2048,
                       thinking="default", run_dir=run_dir, role="judge")
        j = jparse(text)
        ok = bool(j.get("correct"))
        return {"verdict": "correct" if ok else "wrong", "score": float(j.get("score", float(ok))),
                "judge": contract.get("judge_model", contract["examiner_model"]) + "/provisional", "reason": j.get("reason")}
    except Exception as e:
        return {"verdict": "evidence_unresolved", "score": 0.0, "judge": "judge_failed", "reason": str(e)[:200]}


def _judge_stages(pub, pri, lines, contract, run_dir):
    """plan_mode = stages 的 judge:返回 verdict / score(= coverage 比例)/ plan_eval{n_covered, n_stages, order_ok, contradictions, coverage}。"""
    from examiner import call, jparse
    ref_raw = str(pri["proposed_reference_answer"])
    ref_lines = [m.group(1).strip() for m in re.finditer(r"(?m)^\s*\d+\s*[.)]\s*(.+?)\s*$", ref_raw)] or [ref_raw.strip()]
    user = json.dumps({"question": pub["question"], "reference_stages": [f"{i+1}. {l}" for i, l in enumerate(ref_lines)],
                       "accepted_alternatives": pri.get("accepted_alternatives"), "rubric": pri.get("rubric"),
                       "solver_lines": [f"{i+1}. {l}" for i, l in enumerate(lines)]}, ensure_ascii=False)
    model = contract.get("judge_model", contract["examiner_model"])
    try:
        text, u = call(STAGES_JUDGE_SYS, user, model, max_tokens=2048, thinking="default", run_dir=run_dir, role="judge")
        j = jparse(text)
        n_st = len(ref_lines)
        cov = [c for c in (j.get("coverage") or []) if isinstance(c, dict)]
        n_cov = sum(1 for c in cov if c.get("solver_lines")) if cov else int(j.get("n_covered") or 0)
        n_cov = max(0, min(n_cov, n_st))
        order_ok = bool(j.get("order_ok", True)); contra = [str(x) for x in (j.get("contradictions") or [])]
        beyond = [str(x) for x in (j.get("beyond_horizon") or [])]          # 参考范围(官方 step)之外的合理阶段:记录、不扣分
        ok = n_cov >= n_st and order_ok and not contra
        return {"verdict": "correct" if ok else "wrong", "score": round(n_cov / n_st, 3) if n_st else 0.0,
                "judge": model + "/stages", "reason": j.get("reason"),
                "plan_eval": {"n_covered": n_cov, "n_stages": n_st, "order_ok": order_ok, "contradictions": contra, "beyond_horizon": beyond, "coverage": cov}}
    except Exception as e:
        return {"verdict": "evidence_unresolved", "score": 0.0, "judge": "judge_failed", "reason": str(e)[:200]}
