"""作答结果 -> 下一层出题的条件摘要。纯程序,不调 LLM。

摘要含两类信息:
- selection_weights:subtype/video/sound 三个维度的选材权重 w = 1 + 2*(1-acc),
  错得越多的格子下一层被抽中越多(w ∈ [1,3],不会清零任何格子)。
- missed_examples:错题样例(≤10),给措辞 prompt 做风格参照。
pooled 时把所有存活 agent 在同一批题上的作答合并(每题每 agent 一次 trial)。
"""
import json, hashlib
import pconfig as P


def _acc_by(trials, key):
    agg = {}
    for q, ok in trials:
        k = q.get(key) or ""
        n, c = agg.get(k, (0, 0))
        agg[k] = (n + 1, c + ok)
    return {k: {"n": n, "acc": round(c / n, 3)} for k, (n, c) in agg.items() if k}


def _weights(acc_map):
    return {k: round(1 + 2 * (1 - v["acc"]), 3) for k, v in acc_map.items()}


def build_summary(arm, scope, level, set_path, results_by_agent):
    """results_by_agent: {agent: jsonl 路径}。写 adapt/<arm>/<scope>/L<level>_summary.json。"""
    P.ensure_dirs()
    setdata = json.loads(open(set_path).read())
    qs = {q["question_id"]: q for q in setdata["questions"]}
    trials, per_agent, missed_by_qid = [], {}, {}
    for agent, path in results_by_agent.items():
        rows = [json.loads(l) for l in open(path) if l.strip()]
        n_correct = 0
        for r in rows:
            q = qs.get(r["question_id"])
            if not q:
                continue
            ok = bool(r["correct"])
            n_correct += ok
            trials.append((q, ok))
            if not ok:
                chosen = (q["options"][r["parsed_index"]][3:]
                          if r.get("parsed_index") is not None else None)
                missed_by_qid.setdefault(r["question_id"], {
                    "fact_id": q["fact_id"],        # 选题器据此回查该题的难度特征
                    "question": q["question"], "gold": q["answer"],
                    "subtype": q["subtype"], "video": q["video_id"][:3],
                    "chosen_by": {}})["chosen_by"][agent] = chosen
        per_agent[agent] = {"n": len(rows), "n_correct": n_correct,
                            "passed": n_correct >= _gate(len(rows))}

    by_subtype = _acc_by(trials, "subtype")
    n_trials = len(trials)
    c_trials = sum(ok for _, ok in trials)
    # 被多数 agent 答错的排前面
    missed = sorted(missed_by_qid.values(), key=lambda m: -len(m["chosen_by"]))[:10]
    out = {"arm": arm, "scope": scope, "level": level,
           "agents": sorted(results_by_agent), "per_agent": per_agent,
           "n": n_trials, "n_correct": c_trials,
           "by_subtype": by_subtype,
           "by_video": _acc_by(trials, "video_id"),
           "by_sound": _acc_by(trials, "_sound_label"),
           "missed_examples": missed,
           "no_errors": not missed,
           "selection_weights": {
               "subtype": _weights(by_subtype),
               "video": _weights(_acc_by(trials, "video_id")),
               "sound": _weights(_acc_by(trials, "_sound_label"))}}
    out["summary_sha"] = hashlib.sha256(
        json.dumps(out, sort_keys=True).encode()).hexdigest()[:16]
    d = P.ADAPT / arm / scope
    d.mkdir(parents=True, exist_ok=True)
    (d / f"L{level}_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def _gate(n):
    """通过线:n=100 时是 80;冒烟测试的小 n 按 80% 向上取整。"""
    import math
    return math.ceil(0.8 * n) if n else 1
