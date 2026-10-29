"""open 简答的 LLM judge:规则判不了时,把自由文本回答映射到「4 个已知候选之一或 none」。

- judge 看不到视频、不知道哪个候选是 gold(候选顺序按题 id 打乱)。
- gemini_io.gen(temp 0、JSON);结果按 sha(question|reply|candidates) 缓存到 pconfig.JUDGE_CACHE,
  同一回答永远只判一次;调用打 role="judge",gemini_usage.py 单独一栏。
- 只在 judge_formats.py 后处理里调用,evaluate.py 不依赖 Gemini 环境。
"""
import json, hashlib, random
import pconfig as P
import gemini_io

_CACHE = None


def _load():
    global _CACHE
    if _CACHE is None:
        _CACHE = {}
        if P.JUDGE_CACHE.exists():
            for l in P.JUDGE_CACHE.open():
                if l.strip():
                    r = json.loads(l)
                    _CACHE[r["key"]] = r
    return _CACHE


def _key(question, reply, cands):
    return hashlib.sha256("|".join([question, reply] + cands).encode()).hexdigest()[:16]


PROMPT = """You are grading a free-text answer to a question about a short kitchen video. You cannot see the video.
Decide which ONE of the candidate answers the reply means, or "none" if it matches none of them
(or is ambiguous between two). Match on meaning, not exact wording: synonyms, plural/singular,
articles and minor rephrasing count as the same; a different object, number, direction or purpose does not.

Question: {question}
Reply: {reply}
Candidates:
{cands}

Return JSON only: {{"match": <candidate number 1-{n} or "none">, "why": "<one short clause>"}}"""


def map_to_candidate(question_id, question, reply, gold, distractors):
    """返回 (matched_candidate_text 或 None, cached: bool, model)。"""
    cands = [gold] + list(distractors)
    rng = random.Random(question_id)
    order = list(range(len(cands)))
    rng.shuffle(order)
    shown = [cands[i] for i in order]
    key = _key(question, reply, shown)
    cache = _load()
    if key in cache:
        return cache[key]["match"], True, cache[key].get("model")
    txt, model = gemini_io.gen(PROMPT.format(question=question, reply=reply, n=len(shown),
                                             cands="\n".join(f"{i + 1}. {c}" for i, c in enumerate(shown))),
                               max_tokens=128, role="judge")
    j = gemini_io.jparse(txt) or {}
    m = j.get("match")
    match = shown[int(m) - 1] if isinstance(m, (int, str)) and str(m).isdigit() \
        and 1 <= int(m) <= len(shown) else None
    rec = {"key": key, "question_id": question_id, "reply": reply, "match": match,
           "why": j.get("why"), "model": model, "raw": txt[:300]}
    with P.JUDGE_CACHE.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    cache[key] = rec
    return match, False, model


PLAN_PROMPT = """You are grading a step-by-step cooking plan written by a model against the steps that were actually
performed in a video. You cannot see the video. For EACH predicted step, give the number of the reference step it
accomplishes, or null if it matches none. Rules: same action on the same object counts (synonyms and minor rephrasing
are fine); a step that only partially covers a reference step still counts; a different object, a different purpose,
or a step that is not in the reference list does not count. Never map two predicted steps to the same reference step
unless they genuinely repeat it.

Goal: {goal}
Reference steps (unordered):
{refs}
Predicted plan:
{preds}

Return JSON only: {{"map": [<reference number or null for predicted step 1>, ...], "why": "<one short clause>"}}"""


def align_plan(question_id, goal, pred_steps, ref_steps):
    """把预测步骤逐条对到参考步骤(1-based idx 或 None)。参考顺序按 question_id 打乱后给 judge,代码里还原。
    返回 (mapping, cached, model)。"""
    refs = list(ref_steps)
    rng = random.Random("plan|" + str(question_id))
    order = list(range(len(refs)))
    rng.shuffle(order)
    shown = [refs[i] for i in order]
    key = _key(goal, "\n".join(pred_steps), shown)
    cache = _load()
    if key in cache:
        return cache[key]["match"], True, cache[key].get("model")
    txt, model = gemini_io.gen(PLAN_PROMPT.format(goal=goal, refs="\n".join(f"{i + 1}. {c}" for i, c in enumerate(shown)),
                                                  preds="\n".join(f"{i + 1}. {c}" for i, c in enumerate(pred_steps))),
                               max_tokens=256, role="judge")
    j = gemini_io.jparse(txt) or {}
    raw_map = j.get("map") if isinstance(j.get("map"), list) else []
    mapping = []
    for i in range(len(pred_steps)):
        m = raw_map[i] if i < len(raw_map) else None
        if isinstance(m, (int, str)) and str(m).isdigit() and 1 <= int(m) <= len(shown):
            mapping.append(order[int(m) - 1] + 1)          # 还原为原始 1-based idx
        else:
            mapping.append(None)
    rec = {"key": key, "question_id": question_id, "reply": "\n".join(pred_steps), "match": mapping,
           "why": j.get("why"), "model": model, "raw": txt[:300]}
    with P.JUDGE_CACHE.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    cache[key] = rec
    return mapping, False, model
