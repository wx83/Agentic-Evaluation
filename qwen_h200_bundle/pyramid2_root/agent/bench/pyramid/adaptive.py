"""1001 real experiment: adaptive examiner within each pyramid level, gated level to level.

    export GEMINI_API_KEY=...            # shell only, never written to disk
    PYRAMID_SEED=43 $GEM adaptive.py --run-id real_1001 --n 50 --pass-acc 0.8

One loop per level (experiments/1001_exp.md, sections 3-12):

  1. the program draws a shortlist of VERIFIED evidence cards for the level (each card
     has been re-derived on its window by verify.check before it is offered);
  2. the Gemini examiner (shared examiner prompt + level specification, read verbatim
     from the md) picks one card, a format and writes the question -> ASK json;
  3. the item validator rebuilds the item around the program's gold / distractors /
     statements and runs verify.check; a rejected item is NOT a model error -- the
     examiner gets the validator's errors and retries, then falls back to the template;
  4. the target model gets a fresh context with only the 30 s AV clip + public question;
  5. scoring is deterministic where possible (letter, exact set, rule), judge otherwise;
  6. history / skill state / policy gates are recomputed and the loop repeats.

A level ends after exactly N scored items. accuracy >= PASS_ACC -> LEVEL_PASSED and the
next level starts; otherwise STOP_NOT_DEMONSTRATED and the run stops there.
Everything is resumable: rows are appended to <run>/L<k>/items.jsonl.
"""
import argparse, collections, hashlib, json, random, re, sys, time
from pathlib import Path

import pconfig as P
import config as C
import facts as F
import phrase as PH
import verify as V
import formats as FM
import assemble as A
import assemble_formats as AF
import phrase_formats as PF
import gemini_io
import judge
import score
import prompt as PR
import clips
from agent_gemini import PyramidGeminiAgent

MD = Path("/mnt/work_new/weihanxu/experiments/1001_exp.md")
LEVEL_NAME = {1: "L1", 2: "L2", 3: "L3", 4: "L4"}
LEVEL_SKILLS = {
    1: ["easy_sound", "easy_sound_object", "easy_move", "easy_spatial_near", "easy_spatial_side"],
    2: ["low_sound_movement", "low_spatial_near", "low_spatial_side"],
    3: ["medium_count", "medium_order", "medium_spatial_extreme", "medium_spatial_order",
        "medium_purpose", "medium_goal"],
    4: ["high_plan_next_action", "high_plan_route"],   # 10-08: next 改为 EgoPlan 式下一动作;trajectory / replan 待人工核验数据到位后加入
}
FMT_OF = {"single_choice": "mc", "multi_select": "ms", "short_answer": "open", "plan": "plan"}
FMT_NAME = {v: k for k, v in FMT_OF.items()}
REVISIT_FRAC = 0.20          # at most this share of a level's items may re-test a used cluster
GEN_RETRIES = 2              # examiner retries after a validator rejection, then template fallback
MAX_GOLD_SHOW = 90
MAX_TARGET_ERRORS = 15       # consecutive target API errors before the run gives up (no idle spinning)
TARGET_MODEL = C.GEMINI_MODEL  # set by --target-model; the examiner keeps C.GEMINI_MODEL
EXAMINER = "gemini"          # "gemini" | "openai"; set by --examiner. The examiner is text-only.


def examiner_gen(prompt, max_tokens):
    if EXAMINER == "openai":
        import openai_io
        return openai_io.gen(prompt, max_tokens=max_tokens, role="generator")
    return gemini_io.gen(prompt, max_tokens=max_tokens, role="generator")


# ------------------------------------------------------------------ prompts from the md
def md_prompts():
    """Shared examiner prompt (sec. 5) and the four level specs (sec. 6-9), verbatim."""
    text = MD.read_text()
    out = {}
    for key, head in (("shared", "## 5. "), (1, "## 6. "), (2, "## 7. "), (3, "## 8. "), (4, "## 9. ")):
        i = text.index("\n" + head)
        j = text.index("```text\n", i) + len("```text\n")
        out[key] = text[j:text.index("\n```", j)]
    return out


# ------------------------------------------------------------------ evidence pool
_IX = {}
_VALID = {}


def ix_of(v):
    return AF.ix_of(v)


def template_item(f, qid="pre"):
    if f["kind"] == "PLAN":
        return plan_item(f, qid)
    return A._make_item(f, PH.offline_question(f), qid, 0, "template", None)


def fact_ok(f):
    """A fact is offered to the examiner only if it still re-derives on its window today."""
    k = f["fact_id"]
    if k not in _VALID:
        try:
            _VALID[k] = not V.check(ix_of(f["video_id"]), template_item(f), f)
        except Exception:
            _VALID[k] = False
    return _VALID[k]


def clip_id(f):
    if f.get("windows"):
        return f["video_id"][:3] + "_" + "+".join(f"{a:.1f}-{b:.1f}" for a, b in f["windows"])
    return f"{f['video_id'][:3]}_{f['t0']:.1f}-{f['t1']:.1f}"


def ms_item(f, by_win):
    """Program-built multi-select item (4 statements, 1-3 true, every truth value verified)."""
    if f["kind"] in ("PLAN",):
        return None
    rng = random.Random("ms|" + f["fact_id"])
    base = template_item(f, "ms_" + f["fact_id"])
    # Sibling statements must come from the SAME level: build_ms otherwise falls back to
    # other tiers, which put L2 "at the moment you hear X ..." statements into L1 items
    # (2 of the 6 multi-select items of run real_1001; found in the 10-01 audit).
    sibs = [x for x in AF.siblings(f, by_win) if x.get("tier") == f.get("tier")]
    try:
        it, k = FM.build_ms(base, f, rng.choice([1, 2, 2, 3]), sibs, rng,
                            ix=ix_of(f["video_id"]))
    except Exception:
        return None
    if not it or V.check(ix_of(f["video_id"]), it, f):
        return None
    return it


def plan_item(f, qid):
    """plan 格式的题:题面 = goal 句;模型看的片段是段开始前 30 s(f['_clip'])。"""
    return {"question_id": qid, "tier": f["tier"], "subtype": f["subtype"], "kind": f["kind"], "video_id": f["video_id"],
            "t0": f["t0"], "t1": f["t1"], "fmt": "plan", "question": f["_goal"], "answer": f["gold"], "options": None,
            "_distractors": [], "_sound_label": None, "evidence_event_ids": f["evidence_event_ids"],
            "evidence_t": f["evidence_t"], "fact_id": f["fact_id"], "phrasing": "template", "_clip": f["_clip"],
            "_steps": f["_steps"], "_prereq": f.get("_prereq") or [], "_goal": f["_goal"]}


def card_of(f, by_win, tested):
    pk = PH._fact_packet(f)
    if f["kind"] == "PLAN":
        c = {"evidence_cluster_id": f["fact_id"], "skill": f["subtype"], "av_input_id": clip_id(f),
             "goal": f["_goal"], "reference_answer": f["_steps"], "verified_wrong_answers": [],
             "allowed_formats": ["plan"],
             "note": "open generation: the question is the goal sentence verbatim; the program grades the step list"}
        if tested:
            c["already_tested"] = [{"format": FMT_NAME[r["fmt"]], "correct": r["correct"]} for r in tested]
        return c, None
    c = {"evidence_cluster_id": f["fact_id"], "skill": f["subtype"], "av_input_id": clip_id(f),
         "reference_answer": f["gold"], "verified_wrong_answers": list(f["distractors"])}
    for k in ("sound_natural_phrase", "moved_from", "moved_to", "three_actions_shuffled",
              "reference_object", "relation", "three_objects_shuffled", "action", "object",
              "two_scenes", "scene_intro", "ego_side", "anchor_object", "goal"):
        if k in pk:
            c[k] = pk[k]
    fmts = ["single_choice"]
    ms = ms_item(f, by_win)
    if ms is not None:
        fmts.append("multi_select")
        c["multi_select_statements"] = [{"letter": s[0], "text": s[3:], "true": src["truth"]}
                                        for s, src in zip(ms["statements"], ms["_stmt_src"])]
    if f["subtype"] in P.OPEN_OK and f["kind"] in PF.FORMAT_HINT:
        fmts.append("short_answer")
    c["allowed_formats"] = fmts
    if tested:
        c["already_tested"] = [{"format": FMT_NAME[r["fmt"]], "correct": r["correct"]} for r in tested]
    return c, ms


def shortlist(level, pool, by_win, hist, rng, n_total):
    """~12 unused verified cards balanced over the skills that still need evidence,
    plus a few already-tested clusters the examiner may revisit."""
    skills = LEVEL_SKILLS[level]
    used = collections.defaultdict(list)
    for r in hist:
        used[r["cluster"]].append(r)
    used_clips = {r["clip"] for r in hist}
    state = skill_state(level, hist, n_total)
    remaining = n_total - len(hist)
    deficit = {s: state["by_skill"][s]["distinct_deficit"] for s in skills}
    forced = [s for s in skills if deficit[s] > 0] if sum(deficit.values()) >= remaining else None
    per = max(2, 12 // len(forced or skills))
    by_skill = collections.defaultdict(list)
    for f in pool:
        by_skill[f["subtype"]].append(f)
    cards, facts, msitems = [], {}, {}
    for s in (forced or skills):
        cand = [f for f in by_skill[s] if f["fact_id"] not in used]
        rng.shuffle(cand)
        cand.sort(key=lambda f: clip_id(f) in used_clips)        # unseen clips first (stable)
        got = 0
        for f in cand:
            if got >= per:
                break
            if not fact_ok(f):
                continue
            c, ms = card_of(f, by_win, None)
            cards.append(c); facts[f["fact_id"]] = f; msitems[f["fact_id"]] = ms
            got += 1
    n_rev = sum(1 for r in hist if r.get("revisit"))
    if forced is None and n_rev < int(REVISIT_FRAC * n_total):
        by_id = {f["fact_id"]: f for f in pool}
        # most informative revisits first: wrong answers, then clusters seen in one format only
        order = sorted(used.items(), key=lambda kv: (all(r["correct"] for r in kv[1]), -kv[1][-1]["turn"]))
        for cid, rs in order[:4]:
            if len(rs) >= 3 or cid not in by_id:
                continue
            c, ms = card_of(by_id[cid], by_win, rs)
            done = {FMT_NAME[r["fmt"]] for r in rs}
            c["allowed_formats"] = [x for x in c["allowed_formats"] if x not in done] or c["allowed_formats"]
            cards.append(c); facts[cid] = by_id[cid]; msitems[cid] = ms
    return cards, facts, msitems, forced


# ------------------------------------------------------------------ state / policy
def min_distinct(level, n_total):
    return max(2, int(0.6 * n_total / len(LEVEL_SKILLS[level])))


def skill_state(level, hist, n_total):
    need = min_distinct(level, n_total)
    by = {}
    for s in LEVEL_SKILLS[level]:
        rs = [r for r in hist if r["skill"] == s]
        fm = collections.defaultdict(lambda: [0, 0])
        for r in rs:
            fm[FMT_NAME[r["fmt"]]][0] += 1
            fm[FMT_NAME[r["fmt"]]][1] += bool(r["correct"])
        d = len({r["cluster"] for r in rs})
        by[s] = {"items": len(rs), "correct": sum(bool(r["correct"]) for r in rs),
                 "distinct_evidence_clusters": d, "distinct_required": need,
                 "distinct_deficit": max(0, need - d),
                 "by_format": {k: {"n": v[0], "correct": v[1]} for k, v in fm.items()},
                 "clips": len({r["clip"] for r in rs})}
    cl = collections.defaultdict(list)
    for r in hist:
        cl[r["cluster"]].append(r)
    incons = [c for c, rs in cl.items() if len({bool(r["correct"]) for r in rs}) > 1]
    n, c = len(hist), sum(bool(r["correct"]) for r in hist)
    return {"by_skill": by, "inconsistent_clusters": incons,
            "wrong_clusters": [r["cluster"] for r in hist if not r["correct"]][-12:],
            "revisit_items": sum(1 for r in hist if r.get("revisit")),
            "policy_gates": {"scored_items": n, "correct": c,
                             "accuracy_so_far": round(c / n, 3) if n else None,
                             "all_required_skills_covered": all(v["distinct_deficit"] == 0 for v in by.values())}}


def pass_policy(level, n_total, pass_acc):
    return {
        "required_skills": LEVEL_SKILLS[level],
        "evaluation_scope": "30-second first-person clips from 5 HD-EPIC kitchen videos (P02, P03, P06, P08, P09); "
                            "conclusions hold for this clip collection only",
        "minimum_distinct_evidence": {s: min_distinct(level, n_total) for s in LEVEL_SKILLS[level]},
        "required_format_coverage": "report performance per format; use at least two formats per skill "
                                    "where the offered cards allow it",
        "performance_requirements": f"at least {pass_acc:.0%} of the {n_total} scored items correct "
                                    f"(= {int(-(-pass_acc * n_total // 1))} items); fixed before the run",
        "confirmation_requirements": f"at most {int(REVISIT_FRAC * n_total)} items may revisit an "
                                     "already-tested evidence cluster; revisits are robustness evidence only",
        "maximum_questions": n_total,
        "insufficient_evidence_rule": "items rejected by the validator or failing on an API error are not "
                                      "scored and do not count toward the budget",
        "decision": "The program closes the level after exactly maximum_questions scored items and applies "
                    "performance_requirements. Until then the only useful action is ASK.",
    }


def history_view(hist):
    out = []
    for r in hist:
        out.append({"q": r["turn"], "skill": r["skill"], "evidence_cluster_id": r["cluster"],
                    "clip": r["clip"], "format": FMT_NAME[r["fmt"]], "question": r["question"][:160],
                    "reference": str(r["gold_shown"])[:MAX_GOLD_SHOW],
                    "response": str(r["parsed_shown"])[:MAX_GOLD_SHOW],
                    "verified_score": "correct" if r["correct"] else "incorrect",
                    "scored_by": r["score_by"], "item_valid": True})
    return out


RUNTIME_RULES = """
RUN CONFIGURATION (fixed by the experimenter; it narrows the options above, it never loosens them)
- Choose exactly one card from EVIDENCE_POOL by its evidence_cluster_id and one of that card's
  allowed_formats. Cards not listed are unavailable this turn; verification budget is 0, so
  REQUEST_VERIFICATION cannot be served -- pick a listed card instead.
- The reference answer, the wrong answers and the multi-select statements on a card are verified and
  FIXED. You write the public question text only.
  single_choice: write the question; the program attaches the four options (reference + the three
    verified wrong answers) in a random order. Set public.options to null.
  multi_select: the program shows the card's four statements verbatim, lettered as listed, under
    "select all that apply". Set public.question to "Which of these statements are true for this clip?"
    and private.reference_answer to the letters of the true statements (e.g. "A, C").
  short_answer: write a self-contained question with no options and no "which of these"; the program
    appends the output-format sentence. private.reference_answer must equal the card's reference_answer.
- Refer to a sound only by the card's sound_natural_phrase. Never use the words annotation, timeline,
  label, memory, fact, metadata, ground truth, or "collision".
- A question must not contain its reference answer. For easy_sound do not name or describe any sound.
- Spatial skills: keep the given relation / side and reference_object, and keep the time anchor
  (the moment the object is put down, the moment the sound is heard, or by the end of the clip).
- For two_scenes cards start the question with scene_intro verbatim.
- Cards with a `goal` (high_plan_next_action): start the question with "The camera wearer is working on:
  <goal>." verbatim, then ask what they will do right after the clip ends; never name any action or object.
- high_replan cards: same goal sentence, then say that something does not go as planned in the clip WITHOUT
  saying what, and ask what they should do right after the clip ends.
- high_plan_trajectory cards offer only the format "plan": public.question is the card's goal sentence verbatim;
  the program shows the clip of the moments BEFORE the segment and grades the model's numbered step list
  against reference_answer.
- medium_order / medium_spatial_order: list the three shuffled items in the given shuffled order.
- LEVEL_PASSED and the STOP actions are issued by the program when the budget is used up. Return ASK.
- Output one JSON object with the fields: action, level, skill, unresolved_issue, selection_reason,
  strategy, evidence_cluster_id, public{av_input_id, format, question, options},
  private{evidence_ids, reference_answer, accepted_equivalents, scoring_rubric, verification_status},
  verification_request, stop_report.
"""


def build_prompt(prompts, level, cards, hist, n_total, pass_acc, forced, feedback=None):
    st = skill_state(level, hist, n_total)
    parts = [prompts["shared"], "", "LEVEL_SPEC:", prompts[level], RUNTIME_RULES,
             "TARGET_MODEL:", json.dumps({"id": TARGET_MODEL, "input": "30 s video with audio + the public question",
                                          "context": "fresh for every question", "thinking": "off"}),
             "", "EVALUATION_SCOPE:", pass_policy(level, n_total, pass_acc)["evaluation_scope"],
             "", "EVIDENCE_POOL (verified cards available this turn):",
             json.dumps(cards, ensure_ascii=False, indent=1),
             "", "EVALUATION_HISTORY:", json.dumps(history_view(hist), ensure_ascii=False),
             "", "SKILL_STATE:", json.dumps(st, ensure_ascii=False),
             "", "PASS_POLICY:", json.dumps(pass_policy(level, n_total, pass_acc), ensure_ascii=False),
             "", "BUDGET:", json.dumps({"questions_remaining": n_total - len(hist), "verification_remaining": 0})]
    if forced:
        parts += ["", "COVERAGE NOTE: the remaining budget is only enough to reach minimum_distinct_evidence, "
                      f"so this turn offers cards for the skills still short of it: {forced}."]
    if feedback:
        parts += ["", "ITEM VALIDATION RESULT for your previous proposal this turn (rejected; not shown to "
                      "the target model). Propose a corrected item, or choose another card:",
                  json.dumps(feedback, ensure_ascii=False)]
    return "\n".join(parts)


# ------------------------------------------------------------------ item construction + validation
def _norm(s):
    return re.sub(r"[^a-z0-9>]+", " ", str(s or "").lower()).strip()


def make_item(prop, facts, msitems, qid, gold_idx, model):
    """Examiner proposal -> (item, errors). The item is rebuilt around program gold."""
    errs = []
    if (prop or {}).get("action") != "ASK":
        return None, [f"action must be ASK (got {(prop or {}).get('action')!r}); stop decisions are made by the program"]
    cid = prop.get("evidence_cluster_id")
    f = facts.get(cid)
    if f is None:
        return None, [f"evidence_cluster_id {cid!r} is not one of the offered cards"]
    pub, prv = prop.get("public") or {}, prop.get("private") or {}
    fmt = FMT_OF.get(str(pub.get("format", "")).lower().replace("-", "_"))
    if fmt is None:
        return None, [f"unknown format {pub.get('format')!r}"]
    q = (pub.get("question") or "").strip()
    ix = ix_of(f["video_id"])
    if prop.get("skill") and prop["skill"] != f["subtype"]:
        errs.append(f"skill {prop['skill']!r} does not match the card's skill {f['subtype']!r}")
    if fmt == "ms":
        it = msitems.get(cid)
        if it is None:
            return None, ["multi_select is not available for this card"]
        it = dict(it, question_id=qid)
        ref = "".join(sorted(set(re.findall(r"\b([ABCD])\b", str(prv.get("reference_answer", "")).upper()))))
        if ref != it["_gold_set"]:
            errs.append(f"private.reference_answer letters {ref!r} != verified true statements {it['_gold_set']!r}")
        it["question"] = "Which of these statements are true for this clip?"
        errs += V.check(ix, it, f)
        return it, errs
    if fmt == "plan" or f["kind"] == "PLAN":
        if f["kind"] != "PLAN":
            return None, ["plan format is only available for high_plan_trajectory cards"]
        it = plan_item(f, qid)
        errs += V.check(ix, it, f)
        return it, errs
    if not q:
        return None, ["public.question is empty"]
    if _norm(prv.get("reference_answer")) != _norm(f["gold"]):
        errs.append(f"private.reference_answer {prv.get('reference_answer')!r} != card reference_answer {f['gold']!r}")
    base = A._make_item(f, q, qid, gold_idx, "gemini", model)
    errs += V.check(ix, base, f)
    if fmt == "mc":
        return base, errs
    if f["subtype"] not in P.OPEN_OK or f["kind"] not in PF.FORMAT_HINT:
        return None, ["short_answer is not allowed for this card"]
    it = FM.build_open(base, f, "open")
    it.update({"question_id": qid, "question": q.rstrip() + " " + PF.FORMAT_HINT[f["kind"]], "phrasing": "gemini"})
    errs += V.check(ix, it, f)
    return it, errs


def template_fallback(f, fmt, msitems, qid, gold_idx):
    """Used when the examiner's wording is rejected GEN_RETRIES+1 times: same card, same format,
    fixed template wording (phrasing='template')."""
    if fmt == "ms" and msitems.get(f["fact_id"]) is not None:
        return dict(msitems[f["fact_id"]], question_id=qid,
                    question="Which of these statements are true for this clip?", phrasing="template")
    if f["kind"] == "PLAN":
        return plan_item(f, qid)
    base = A._make_item(f, PH.offline_question(f), qid, gold_idx, "template", None)
    if fmt == "open" and f["subtype"] in P.OPEN_OK:
        it = FM.build_open(base, f, "open")
        it.update({"question_id": qid, "phrasing": "template"})
        return it
    return base


# ------------------------------------------------------------------ target + scoring
def ask_target(agent, it):
    f_windows = it.get("windows")
    c0, c1 = it.get("_clip") or (it["t0"], it["t1"])          # plan 题:段开始前 30 s,不是段本身
    media = (clips.ensure_episodes(it["video_id"], [tuple(w) for w in f_windows]) if f_windows
             else clips.ensure_clip(it["video_id"], c0, c1))
    fmt = it.get("fmt") or "mc"
    text = PR.build(it["question"], it["options"]) if fmt == "mc" else FM.build_prompt(it)
    agent.max_tokens = P.FMT_MAX_TOKENS[fmt]
    last = None
    for attempt in range(3):
        sess = None
        try:
            sess = agent.start({"steps": [it], "clip_start": it["t0"]}, media=media, memory=None)
            raw, meta = sess.ask(text)
            return raw, meta, text, str(media), None
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:400]}"
            time.sleep(5 * (attempt + 1))
        finally:
            if sess is not None:
                sess.close()
    return "", {}, text, str(media), last


def score_item(it, raw):
    fmt = it.get("fmt") or "mc"
    if fmt == "mc":
        idx = score.score_choice(raw, it["options"])
        shown = it["options"][idx] if idx is not None else None
        return idx == it["_gold_idx"], "rule", shown, it["options"][it["_gold_idx"]]
    parsed, _ = FM.parse(fmt, raw)
    if fmt in ("plan", "plan_x"):
        import plan_traj as PT
        if not parsed:
            it["_plan_detail"] = {"score": 0.0, "correct": False, "map": [], "note": "unparsable"}
            return False, "rule", parsed, it["_steps"]
        mapping, _c, _m = judge.align_plan(it["question_id"], it["_goal"], parsed, it["_steps"])
        det = PT.metrics(mapping, len(it["_steps"]), it.get("_prereq") or [])
        det["rule_map"] = PT.rule_align(parsed, [{"idx": i + 1, "text": t, "verb": t.split()[0], "noun": t.split()[-1]}
                                                 for i, t in enumerate(it["_steps"])])
        it["_plan_detail"] = det
        return det["correct"], "judge", parsed, it["_steps"]
    ok, sc, by, _d = FM.score(fmt, parsed, it)
    if by == "pending":
        m, _c, _m = judge.map_to_candidate(it["question_id"], it["question"], parsed or "",
                                           it["answer"], list(it["_distractors"]))
        ok, by = (m == it["answer"]), "judge"
    gold = it["_gold_set"] if fmt == "ms" else it["answer"]
    return bool(ok), by, parsed, gold


# ------------------------------------------------------------------ level loop
def run_level(level, prompts, agent, run_dir, n_total, pass_acc, pool, by_win):
    d = run_dir / LEVEL_NAME[level]
    d.mkdir(parents=True, exist_ok=True)
    items_f, invalid_f = d / "items.jsonl", d / "invalid.jsonl"
    hist = [json.loads(l) for l in items_f.open()] if items_f.exists() else []
    rng = random.Random(f"{P.SEED}|adaptive|{level}")
    for _ in range(len(hist) * 3):
        rng.random()                                   # keep resumed runs from re-drawing the same cards
    turn_calls = 0
    target_errors = 0
    while len(hist) < n_total:
        turn = len(hist) + 1
        qid = f"ad_{run_dir.name}_L{level}_{turn:03d}"
        cards, facts, msitems, forced = shortlist(level, pool, by_win, hist, rng, n_total)
        if not cards:
            (d / "summary.json").write_text(json.dumps({"stop": "STOP_INSUFFICIENT_EVIDENCE", "scored": len(hist)}))
            return "STOP_INSUFFICIENT_EVIDENCE", hist
        gold_idx = rng.randrange(4)
        feedback, it, prop, mid, rejected = None, None, None, None, []
        for attempt in range(GEN_RETRIES + 1):
            try:
                raw, mid = examiner_gen(build_prompt(prompts, level, cards, hist, n_total, pass_acc, forced, feedback),
                                        max_tokens=2048)
                turn_calls += 1
                prop = gemini_io.jparse(raw)
                if isinstance(prop, list):
                    prop = prop[0] if prop else None
            except RuntimeError as e:
                prop, raw = None, f"ERROR {e}"
            cand, errs = make_item(prop, facts, msitems, qid, gold_idx, mid) if prop else (None, ["examiner returned no parsable JSON"])
            if cand is not None and not errs:
                it = cand
                break
            rec = {"turn": turn, "attempt": attempt, "errors": errs, "proposal": prop, "raw": (raw or "")[:1500]}
            rejected.append(rec)
            with invalid_f.open("a") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            feedback = {"your_proposal": {k: (prop or {}).get(k) for k in ("evidence_cluster_id", "skill", "public")},
                        "validator_errors": errs}
        phrasing = EXAMINER
        if it is None:
            cid = (prop or {}).get("evidence_cluster_id")
            f = facts.get(cid) or facts[cards[0]["evidence_cluster_id"]]
            want = FMT_OF.get(str(((prop or {}).get("public") or {}).get("format", "")).lower(), "mc")
            it = template_fallback(f, want, msitems, qid, gold_idx)
            if V.check(ix_of(f["video_id"]), it, f):
                it = template_fallback(f, "mc", msitems, qid, gold_idx)
            phrasing = "template"
        f = facts[it["fact_id"]]
        raw_t, meta, text, media, err = ask_target(agent, it)
        if err:
            with invalid_f.open("a") as fh:
                fh.write(json.dumps({"turn": turn, "target_error": err, "fact_id": f["fact_id"]}) + "\n")
            print(f"  [L{level}] turn {turn}: target API error, item not scored: {err[:120]}", flush=True)
            target_errors += 1
            if target_errors >= MAX_TARGET_ERRORS:
                raise SystemExit(f"[L{level}] {target_errors} consecutive target API errors; stopping "
                                 f"at {len(hist)}/{n_total} scored (rerun the same command to resume)")
            time.sleep(20)
            continue
        target_errors = 0
        ok, by, parsed, gold_shown = score_item(it, raw_t)
        fmt = it.get("fmt") or "mc"
        row = {"turn": turn, "question_id": qid, "level": level, "skill": f["subtype"], "cluster": f["fact_id"],
               "clip": clip_id(f), "video_id": f["video_id"], "window": [f["t0"], f["t1"]],
               "fmt": fmt, "question": it["question"], "options": it.get("options"),
               "statements": it.get("statements"), "gold_shown": gold_shown, "answer": it["answer"],
               "raw_response": raw_t, "parsed_shown": parsed, "correct": bool(ok), "score_by": by,
               "revisit": any(r["cluster"] == f["fact_id"] for r in hist),
               "phrasing": phrasing, "generator_model": mid, "target_model": meta.get("model"),
               "generator_attempts": len(rejected) + (phrasing != "template"), "n_rejected": len(rejected),
               "unresolved_issue": (prop or {}).get("unresolved_issue"),
               "selection_reason": (prop or {}).get("selection_reason"),
               "strategy": (prop or {}).get("strategy"), "forced_coverage": bool(forced),
               "prompt_to_target": text, "media": media, "latency_sec": meta.get("latency_sec"),
               "detail": it.get("_plan_detail"),
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        hist.append(row)
        with items_f.open("a") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        c = sum(bool(r["correct"]) for r in hist)
        print(f"  [L{level}] {turn:2d}/{n_total} {f['subtype']:<22} {FMT_NAME[fmt]:<13} "
              f"{'OK ' if ok else 'XX '} acc {c}/{len(hist)}  ({phrasing}, rejected {len(rejected)})", flush=True)
    c = sum(bool(r["correct"]) for r in hist)
    need = int(-(-pass_acc * n_total // 1))
    stop = "LEVEL_PASSED" if c >= need else "STOP_NOT_DEMONSTRATED"
    summary = {"level": level, "stop": stop, "scored": len(hist), "correct": c, "accuracy": round(c / len(hist), 3),
               "needed": need, "state": skill_state(level, hist, n_total),
               "by_format": {k: {"n": v[0], "correct": v[1]} for k, v in _fmt_tab(hist).items()},
               "distinct_clusters": len({r["cluster"] for r in hist}), "distinct_clips": len({r["clip"] for r in hist}),
               "template_fallbacks": sum(r["phrasing"] == "template" for r in hist),
               "rejected_proposals": sum(r["n_rejected"] for r in hist),
               "judge_scored": sum(r["score_by"] == "judge" for r in hist),
               "scope": pass_policy(level, n_total, pass_acc)["evaluation_scope"]}
    (d / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    return stop, hist


def _fmt_tab(hist):
    t = collections.defaultdict(lambda: [0, 0])
    for r in hist:
        t[FMT_NAME[r["fmt"]]][0] += 1
        t[FMT_NAME[r["fmt"]]][1] += bool(r["correct"])
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="real_1001")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--pass-acc", type=float, default=0.8)
    ap.add_argument("--levels", type=int, nargs="+", default=[1, 2, 3, 4])
    ap.add_argument("--no-gate", action="store_true", help="run every listed level regardless of the gate")
    ap.add_argument("--examiner", default="gemini", choices=["gemini", "openai"],
                    help="who writes the questions; the target is always Gemini")
    ap.add_argument("--target-model", default=C.GEMINI_MODEL, help="Gemini model id of the model under test")
    a = ap.parse_args()
    global EXAMINER, TARGET_MODEL
    EXAMINER = a.examiner
    TARGET_MODEL = a.target_model
    P.ensure_dirs()
    import runlog
    runlog.start(f"adaptive_{a.run_id}", agent="gemini")
    prompts = md_prompts()
    run_dir = P.POUT / "adaptive" / a.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    meta_f = run_dir / "run.json"
    meta = json.loads(meta_f.read_text()) if meta_f.exists() else {
        "run_id": a.run_id, "seed": P.SEED, "n_per_level": a.n, "pass_acc": a.pass_acc,
        "examiner": a.examiner,
        "generator_model": __import__("openai_io").MODEL if a.examiner == "openai" else C.GEMINI_MODEL, "target_model": a.target_model, "target_input": "clip30",
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "md": str(MD),
        "prompt_sha": {str(k): hashlib.sha256(v.encode()).hexdigest()[:12] for k, v in prompts.items()},
        "key_id": gemini_io.key_id(), "levels": {}}
    by_id, by_win = AF.load_facts()
    allp = F.load_all()
    # The cached seed-43 medium_goal facts predate the 09-28 goal split: their distractors no
    # longer pass verify.check, so none could be offered. Re-mine that one skill with the
    # current miner (same seed stream) and use those instead.
    fresh = []
    for v in P.VIDEOS:
        fresh += F.mine_goal(ix_of(v), random.Random(f"{P.SEED}|{v}|Medium|goal"))
    allp["Medium"] = [f for f in allp["Medium"] if f["subtype"] != "medium_goal"] + fresh
    meta["pool_note"] = f"medium_goal re-mined with current code ({len(fresh)} facts)"
    # 10-07: high_plan_route switched from four turn-sectors to four quadrants (front/back x
    # left/right, see infer.sector). The cached seed-43 route facts carry the old gold/options,
    # so re-mine that one skill with the current miner (same seed stream) and use those instead.
    fresh_r = []
    for v in P.VIDEOS:
        fresh_r += F.mine_plan_route(ix_of(v), random.Random(f"{P.SEED}|{v}|High|plan_route"))
    allp["High"] = [f for f in allp["High"] if f["subtype"] != "high_plan_route"] + fresh_r
    meta["pool_note"] += f"; high_plan_route re-mined as quadrants ({len(fresh_r)} facts)"
    # 10-08: EgoPlan-style next action (gold = next narration verb+noun, clip cut 0.5 s before it).
    fresh_a = []
    for v in P.VIDEOS:
        fresh_a += F.mine_plan_next_action(ix_of(v), random.Random(f"{P.SEED}|{v}|High|plan_next_action"))
    allp["High"] = [f for f in allp["High"] if f["subtype"] != "high_plan_next_action"] + fresh_a
    meta["pool_note"] += f"; high_plan_next_action mined with current code ({len(fresh_a)} facts)"
    # replan / trajectory come from human-verified files (empty until the review is done)
    fresh_c, fresh_b = [], []
    for v in P.VIDEOS:
        fresh_c += F.mine_replan(ix_of(v), random.Random(f"{P.SEED}|{v}|High|replan"))
        fresh_b += F.mine_plan_trajectory(ix_of(v), random.Random(f"{P.SEED}|{v}|High|plan_trajectory"))
    fresh_s = []
    for v in P.VIDEOS:
        fresh_s += F.mine_plan_next_step(ix_of(v), random.Random(f"{P.SEED}|{v}|High|plan_next_step"))
    allp["High"] = [f for f in allp["High"] if f["subtype"] not in ("high_replan", "high_plan_trajectory", "high_plan_next_step")] + fresh_c + fresh_b + fresh_s
    meta["pool_note"] += f"; high_replan {len(fresh_c)}, high_plan_trajectory {len(fresh_b)}, high_plan_next_step {len(fresh_s)} verified facts"
    agent = PyramidGeminiAgent(model=a.target_model)
    for level in a.levels:
        tier = P.TIER_OF_LEVEL[level]
        pool = [f for f in allp[tier] if f["subtype"] in LEVEL_SKILLS[level]]
        print(f"=== {LEVEL_NAME[level]} ({tier}): pool {len(pool)} facts, {a.n} items, pass >= {a.pass_acc:.0%}", flush=True)
        stop, hist = run_level(level, prompts, agent, run_dir, a.n, a.pass_acc, pool, by_win)
        c = sum(bool(r["correct"]) for r in hist)
        meta["levels"][str(level)] = {"stop": stop, "correct": c, "scored": len(hist),
                                      "finished": time.strftime("%Y-%m-%dT%H:%M:%S")}
        meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
        print(f"=== {LEVEL_NAME[level]}: {c}/{len(hist)} -> {stop}", flush=True)
        if stop != "LEVEL_PASSED" and not a.no_gate:
            print(f"gate not met at {LEVEL_NAME[level]}; higher levels are not run", flush=True)
            break


if __name__ == "__main__":
    main()
