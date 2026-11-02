"""L4 plan_gap_filling(10-24):干扰项骨架,程序按四类规则从 sub-goal 列表生成,Examiner 只负责写成自然语言。
skeleton = {"type", "steps": [{"idx": int|None, "text"}], "note"};类型:
  order_violation      隐藏序列里交换一对步骤(Examiner 用 order_constraints 确认它打破了物理前提,否则换别的对)
  state_conflict       把一步换成头之前已完成 / 尾之后才发生的 sub-goal(与头尾画面状态矛盾)
  plausible_unobserved 把一步换成同视频其它 task 的 sub-goal(合理但尾画面不支持)
  skip                 少做一步(隐藏 1 步时 = 「两段之间没有别的步骤」)"""
import random

NONE_STEP = {"idx": None, "text": "No intermediate step: segment 2 follows segment 1 directly"}


def _txt(s): return {"idx": s["idx"], "text": s["text"]}


def skeletons(head, hidden, tail, task_steps, other_steps, seed=0):
    """head/hidden/tail/task_steps: {idx, text, t0, t1};other_steps: 同视频其它 task 的 {idx, text, task_id}。返回 3 个骨架(可能不足 3)。"""
    rng = random.Random(f"{seed}|{head['idx']}|{tail['idx']}")
    H = [_txt(s) for s in hidden]; out = []
    k, km = head["idx"], tail["idx"]
    before = [s for s in task_steps if s["idx"] < k]; after = [s for s in task_steps if s["idx"] > km]
    # 1. order_violation(≥2 步):交换首尾或相邻一对
    if len(H) >= 2:
        i, j = (0, len(H) - 1) if len(H) == 2 or rng.random() < 0.5 else (0, 1)
        sw = list(H); sw[i], sw[j] = sw[j], sw[i]
        out.append({"type": "order_violation", "steps": sw, "note": f"hidden steps {H[i]['idx']} and {H[j]['idx']} swapped; valid only if one is a precondition of the other (declare it in order_constraints), otherwise replace this skeleton"})
    # 2. state_conflict:优先用尾之后的步骤(更有诱惑力),其次头之前
    pool = (after + before)
    if pool:
        rep = rng.choice(pool); pos = rng.randrange(len(H)); sc = list(H); sc[pos] = _txt(rep)
        out.append({"type": "state_conflict", "steps": sc, "note": f"step {rep['idx']} happens {'after the tail' if rep['idx'] > km else 'before the head'}; it contradicts the state visible in segment {'2' if rep['idx'] > km else '1'}"})
    # 3. plausible_unobserved:同视频其它 task 的 sub-goal
    if other_steps:
        rep = rng.choice(other_steps); pos = rng.randrange(len(H)); pu = list(H); pu[pos] = {"idx": None, "text": rep["text"]}
        out.append({"type": "plausible_unobserved", "steps": pu, "note": f"a step of another task in the same video ({rep.get('task_id')}); nothing in segment 2 supports it"})
    # 4. skip
    if len(H) >= 2:
        drop = rng.randrange(len(H)); sk = [s for i, s in enumerate(H) if i != drop]
        out.append({"type": "skip", "steps": sk, "note": f"hidden step {H[drop]['idx']} omitted; the state in segment 2 cannot be reached without it"})
    else:
        out.append({"type": "skip", "steps": [NONE_STEP], "note": "claims nothing happened between the segments; segment 2 shows a state that needed the hidden step"})
    # 去重(步骤文字序列相同的只留一个),优先保证 order_violation 在内,凑 3 个
    seen, uniq = set(), []
    for s in out:
        key = tuple(x["text"] for x in s["steps"])
        if key == tuple(x["text"] for x in H) or key in seen: continue
        seen.add(key); uniq.append(s)
    first = [s for s in uniq if s["type"] == "order_violation"]; rest = [s for s in uniq if s["type"] != "order_violation"]
    return (first + rest)[:3]
