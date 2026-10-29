"""从 1012.md 原样切出 Shared Examiner System Prompt 与 L1-L4 prompt(仿 adaptive.md_prompts)。"""
import hashlib
import p2config as P


def md_prompts(path=None):
    """按标题切 ```text 块;可选段(task_context / scope)文件里没有就跳过。"""
    text = (path or P.MD).read_text()
    out = {}
    for key, head in P.PROMPT_HEADS.items():
        i = text.find("\n" + head)
        if i < 0:
            if key in P.OPTIONAL_HEADS:
                continue
            raise KeyError(f"prompt section {head!r} missing in {path or P.MD}")
        j = text.index("```text\n", i) + len("```text\n")
        out[key] = text[j:text.index("\n```", j)].strip("\n")
    out["_path"] = str(path or P.MD)
    return out


# harness 定义的输出对象与格式规则:1012.md 第 180 行 "Return the harness-defined JSON object"
HARNESS = """
HARNESS CONTRACT (fixed by the program; it narrows the rules above and never loosens them)

Input: the user message is the runtime context JSON. verified_evidence[] holds annotation records.
Each record has role "target" (evidence of the skill under test, grouped by evidence_cluster_id) or
role "context" (everything else verified in the same window; use it to avoid distractors that are
actually true and to judge answerability). Only records with solver_access "observed" describe what
the Solver can perceive in the clip; "answer_only" records happen after observation_cutoff and may be
used for the reference answer only.

Output exactly one JSON object with these keys:
  action, layer, skill, strategy, tests_hypothesis, selection_reason, evidence_cluster_id,
  public{media_refs, observation_cutoff, format, question, options, task_conditions, gap_item (gap items only)},
  private{domain, evidence_refs, proposed_reference_answer, gold_answer, accepted_alternatives,
          acceptance_criteria, rubric, coverage_requirements, classification_status,
          gold_verification_status, validation_status, answerability_note, gap (gap items only)},
  verification_request
- strategy is one of: coverage, same_skill_new_event, same_skill_cleaner_event, same_event_new_format,
  request_verification. tests_hypothesis is the hypothesis_id being tested or null. A diagnosis_hypothesis of
  type lucky_pass means the previous item on this skill was answered correctly: propose the same skill on a
  different event (same_skill_new_event; unasked in-scope entries first) to check that the pass was not lucky.
- evidence_cluster_id must be one of the target clusters offered this turn.
- public.media_refs: list of {"media_id", "windows": [[start_sec, end_sec], ...]} using source-video
  seconds; windows must lie inside the cluster's offered window; one window unless the cluster says
  two_windows_allowed. Each window must be 10-30 seconds long (never shorter than 10 s): the Solver
  needs context before and after the target moment. public.observation_cutoff: seconds, or null; when
  the cluster has an observation_cutoff the window must end exactly at it.
- format single_choice: public.options = exactly 4 strings "A. ...", "B. ...", "C. ...", "D. ..." in a
  random order containing exactly one correct option; proposed_reference_answer = the letter.
  Distractors must be plausible but contradicted or unsupported by the context records.
- format multi_select: 3-5 statements "A. ...", ...; proposed_reference_answer = letters of the true
  ones (e.g. "A, C"), each truth value must be checkable from the records.
- format short_answer: no options; proposed_reference_answer = a short phrase; list accepted_alternatives.
- format plan: public.question asks what remains to be done for the task the camera wearer is doing (never
  naming the goal). Default: proposed_reference_answer = a numbered list of 4-8 steps; rubric lists the
  criteria to accept alternative valid plans. When the context carries "plan_mode": "stages": the question
  must NOT state a number of steps (ask for "the remaining stages, in order"); proposed_reference_answer =
  one numbered line per recorded task_step after observation_cutoff, in recorded order, at most the next 8,
  each paraphrased but keeping the same verb and object; rubric = which adjacent stages may be swapped and
  which Solver stages would contradict the state at the end of the clip; accepted_alternatives = one coarser
  paraphrase of the same list.
- GAP items (clusters that carry "gap" and "windows"; skill plan_gap_filling): public.media_refs must use
  EXACTLY the two offered windows (segment 1 = end of the head step, segment 2 = start of the tail step);
  the hidden steps between them are the answer_only task_step records. public.gap_item = {"n_hidden": N}.
  format single_choice: each option is a sequence of steps joined by " → " (the correct one lists the N
  hidden steps in recorded order; distractors follow the offered distractor_skeletons: order_violation /
  state_conflict / plausible_unobserved / skip, rewritten in natural words, same length as N except skip).
  format gap_steps: no options; proposed_reference_answer = a numbered list of the N hidden steps; rubric
  = step recall by verb+object, required orderings, no step contradicting the segments.
  private.gap = {"head_idx", "tail_idx", "hidden_idx", "order_constraints": [[earlier_idx, later_idx], ...]
  (only pairs that are physical preconditions), "distractor_types": {"B": "...", ...} for the three
  distractor letters, "distractor_evidence": {"B": [evidence_id, ...], ...} (head/tail records that
  contradict each distractor)}. Never quote a hidden step's text in public.question.
__L3EXT_RULES__
- DIFFICULTY (contexts that carry "difficulty"): the controller fixes this item's difficulty level for the current
  skill. public.format must be exactly difficulty.format and the total clip length must not exceed
  difficulty.window_max_sec (still at least 10 s: choose the sub-window of the offered window that contains the target
  moment). Keep testing the SAME skill at the SAME layer: a harder level changes only the format, the clip length and the
  event, never what is being asked. multi_select: 3-5 statements about the target event, each checkable from the records,
  at least one true and one false. short_answer: the reference is a short phrase (object name, verb + object, a number, or
  an ordered list) with accepted_alternatives. plan and gap_steps follow their own rules above. strategy = "coverage".
- action must be exactly one of the names listed under OUTPUT above (e.g. PROPOSE_DIAGNOSTIC in
  DIAGNOSIS, PROPOSE_CONFIRMATION in CONFIRMATION); no other action names exist.
- Phase transitions, budgets and stopping are decided by the controller from the frozen policy, not
  by you. In DIAGNOSIS keep returning PROPOSE_DIAGNOSTIC while clusters are offered, even if the
  Solver has answered several items correctly; the controller will start CONFIRMATION when the
  per-skill budget is used. Do not return BEGIN_CONFIRMATION. Use REQUEST_VERIFICATION only when
  no offered cluster can support a valid item, and INCONCLUSIVE never on your own initiative.
- Never put an annotation label, evidence id, timestamp of the answer, or the answer itself in
  public.question. Describe sounds only in natural words (never the label vocabulary).
- The Solver sees only the clip, whose time starts at 0; it never sees source-video seconds. Never
  write absolute source timestamps in public.question. Anchor moments by describing what is seen or
  heard ("when the tap is turned on"), by order ("the second time ..."), or by clip-relative time
  ("about 10 seconds into the clip") computed from the window start.
- private.evidence_refs: list of evidence_id strings from this turn's records.
- Always set private.gold_answer = null, gold_verification_status = "needs_verification",
  validation_status = "PENDING_VALIDATION".
- For a non-item action, set public and private to null and fill verification_request (what is
  missing and what verification would resolve it) or selection_reason (why stopping).
"""


SG_ON = False      # 10-28 v15:controller.run 按 contract.sg_mode 设;追加 sg.HARNESS_RULES


def system_prompt(layer, prompts=None):
    p = prompts or md_prompts()
    extra = ("\n" + p["task_context"] + "\n") if p.get("task_context") else ""
    h = HARNESS
    if SG_ON:
        import sg as _SG
        h = HARNESS.rstrip("\n") + "\n" + _SG.HARNESS_RULES
    return p["shared"] + "\n\n" + p[layer] + "\n" + extra + h


def prompt_hash(layer, prompts=None):
    return hashlib.sha256(system_prompt(layer, prompts).encode()).hexdigest()[:12]


if __name__ == "__main__":
    p = md_prompts()
    print({k: len(v) for k, v in p.items()})
    for k, v in p.items():
        print(k, "->", v.splitlines()[0])


# 10-27:L3 / 感知扩展 skill 的 HARNESS 规则由 l3ext.HARNESS_RULES 提供(一处维护,新增 skill 只改 l3ext.py)
import l3ext as _LX
HARNESS = HARNESS.replace("__L3EXT_RULES__\n", _LX.HARNESS_RULES.strip("\n") + "\n")
