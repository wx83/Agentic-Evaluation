#!/usr/bin/env python3
"""11-01:按「依赖式分层 + 空间单列」重算 v16 / v17 的层 mastery、pyramid、通过率,并扣掉盲测可猜题(blindnone = self 的盲测,blindgl = goldlive 的盲测)。
用法:python3 new_layers.py [out.md]"""
import json, os, glob, sys, statistics as st
from collections import defaultdict
R = "/mnt/work_new/weihanxu/output/pyramid_v2/runs"
NEW = {"L1": ["object_recognition", "object_location_at_time"],
       "L2": ["action_recognition", "event_object_role", "object_state_change", "sound_action_binding", "sound_movement_binding"],
       "L3": ["cross_event_integration", "causal_prerequisite_reasoning", "hidden_state_inference", "action_temporal_order"],
       "L4": ["goal_conditioned_planning"],
       "S": ["object_grounding", "spatial_near", "spatial_side", "sound_anchored_spatial_near", "sound_anchored_spatial_side", "spatial_state_integration"]}
OLD_LAYER = {"object_recognition": 1, "object_location_at_time": 1, "object_grounding": 1, "spatial_near": 1, "spatial_side": 1,
             "action_recognition": 2, "event_object_role": 2, "object_state_change": 2, "action_temporal_order": 2, "sound_action_binding": 2,
             "sound_movement_binding": 2, "sound_anchored_spatial_near": 2, "sound_anchored_spatial_side": 2,
             "cross_event_integration": 3, "causal_prerequisite_reasoning": 3, "hidden_state_inference": 3, "spatial_state_integration": 3, "goal_conditioned_planning": 4}
LAYER_OF = {s: L for L, ss in NEW.items() for s in ss}
TASKS = {"v16": ["05", "07", "13", "16", "24", "29", "39", "44", "54", "55"], "v17": ["55", "39", "05"]}
BLIND = {"self": "blindnone", "goldlive": "blindgl"}


def skill_mastery(run):
    p = f"{R}/{run}/score.json"
    if not os.path.exists(p): return {}
    s = json.load(open(p))
    return {k: v["score"] - OLD_LAYER[k] for k, v in s["skills"].items() if v.get("boundary") is not None and k in LAYER_OF}


def layer_mastery(sm):
    out = {}
    for L, ss in NEW.items():
        xs = [sm[k] for k in ss if k in sm]
        out[L] = st.mean(xs) if xs else None
    out["pyr"] = sum(out[L] for L in ("L1", "L2", "L3", "L4") if out[L] is not None)
    return out


def items(run, blind_run=None):
    """每题:新层、档、看视频对错、是否可猜(盲测对)。blind_run 没有就 guess=None。"""
    bl = {}
    if blind_run and os.path.isdir(f"{R}/{blind_run}"):
        for L in "L1 L2 L3 L4".split():
            p = f"{R}/{blind_run}/{L}/history.jsonl"
            if os.path.exists(p):
                for l in open(p):
                    h = json.loads(l)
                    if h.get("verdict") in ("correct", "wrong"): bl[h["candidate_id"]] = h["verdict"] == "correct"
    out = []
    for L in "L1 L2 L3 L4".split():
        p = f"{R}/{run}/{L}/history.jsonl"
        if not os.path.exists(p): continue
        for l in open(p):
            h = json.loads(l)
            if h.get("verdict") not in ("correct", "wrong") or h["capability_skill"] not in LAYER_OF: continue
            out.append({"layer": LAYER_OF[h["capability_skill"]], "skill": h["capability_skill"], "tier": int(h["difficulty_level"]),
                        "ok": h["verdict"] == "correct", "guess": bl.get(h["candidate_id"])})
    return out, bool(bl)


def tier_score(its):
    """四档均分代理 = 各档通过率平均(没题的档不算)。"""
    by = defaultdict(lambda: [0, 0])
    for x in its: by[x["tier"]][0] += x["ok"]; by[x["tier"]][1] += 1
    vals = [c / n for c, n in by.values() if n]
    return st.mean(vals) if vals else None


def main():
    L = []
    f2 = lambda x: "-" if x is None else f"{x:.2f}"
    pct = lambda its: f"{sum(x['ok'] for x in its)}/{len(its)}={sum(x['ok'] for x in its) / len(its) * 100:.0f}%" if its else "-"
    L.append("# 依赖式分层 + 空间单列:v16 / v17 重算(self 与 goldlive;扣盲测可猜题)\n")
    L.append("新分层:L1 = object_recognition, object_location_at_time;L2 = action_recognition, event_object_role, object_state_change, sound_action_binding, sound_movement_binding;"
             "L3 = cross_event_integration, causal_prerequisite_reasoning, hidden_state_inference, action_temporal_order;L4 = goal_conditioned_planning;S(空间轨,不进 pyramid)= object_grounding, spatial_near, spatial_side, sound_anchored_spatial_near/side, spatial_state_integration。\n")
    L.append("mastery = 阶梯边界换算(score.json);pyramid = L1–L4 mastery 之和;「去猜后」= 扣掉盲测臂(不看 clip、不带 history)也答对的题;四档均分 = 各档通过率的平均(剔题后 mastery 的代理)。\n")
    for ver, tasks in TASKS.items():
        L.append(f"\n## {ver}({len(tasks)} 个 task)\n")
        agg = {arm: {"mast": defaultdict(list), "its": []} for arm in ("self", "goldlive")}
        rows_t = []
        for t in tasks:
            line = [t]
            for arm in ("self", "goldlive"):
                run = f"p2_hdepicE_1023t_g4_{ver}_{arm}__{t}"
                lm = layer_mastery(skill_mastery(run))
                for k, v in lm.items():
                    if v is not None: agg[arm]["mast"][k].append(v)
                its, has_blind = items(run, f"p2_hdepicE_1023t_g4_{ver}_{BLIND[arm]}__{t}")
                agg[arm]["its"] += its
                line.append(" / ".join(f2(lm[k]) for k in ("L1", "L2", "L3", "L4")) + f" (S {f2(lm['S'])}) pyr **{lm['pyr']:.2f}**" + ("" if has_blind else " [无盲测]"))
            rows_t.append(line)
        L.append("### 每个 task 的新层 mastery(L1 / L2 / L3 / L4,括号空间轨,pyramid)\n")
        L.append("| task | self | goldlive |\n|---|---|---|")
        for r in rows_t: L.append(f"| {r[0]} | {r[1]} | {r[2]} |")
        L.append("\n### 汇总(task 均值)\n")
        L.append("| 层 | self mastery | goldlive mastery | self 通过率 | goldlive 通过率 | self 可猜占比 | goldlive 可猜占比 | self 去猜后通过率 | goldlive 去猜后通过率 | self 四档均分 全部→去猜后 | goldlive 四档均分 全部→去猜后 |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for Lk in ("L1", "L2", "L3", "L4", "S", "pyr"):
            cells = [Lk if Lk != "pyr" else "pyramid"]
            for arm in ("self", "goldlive"):
                m = agg[arm]["mast"][Lk]; cells.append(f"{st.mean(m):.2f} (sd {st.pstdev(m):.2f})" if m else "-")
            if Lk == "pyr":
                L.append("| " + " | ".join(cells + ["-"] * 8) + " |"); continue
            for arm in ("self", "goldlive"):
                its = [x for x in agg[arm]["its"] if x["layer"] == Lk]
                cells.append(pct(its))
            for arm in ("self", "goldlive"):
                its = [x for x in agg[arm]["its"] if x["layer"] == Lk and x["guess"] is not None]
                cells.append(f"{sum(x['guess'] for x in its) / len(its) * 100:.0f}%" if its else "-")
            for arm in ("self", "goldlive"):
                its = [x for x in agg[arm]["its"] if x["layer"] == Lk and x["guess"] is False]
                cells.append(pct(its))
            for arm in ("self", "goldlive"):
                a = [x for x in agg[arm]["its"] if x["layer"] == Lk]; b = [x for x in a if x["guess"] is False]
                cells.append(f"{f2(tier_score(a))} → {f2(tier_score(b))}")
            L.append("| " + " | ".join(cells) + " |")
        L.append("\n### 按 skill(两臂合计:mastery 均值 / 通过率 / 可猜占比 / 去猜后通过率)\n")
        L.append("| 新层 | skill | self mastery | goldlive mastery | 通过率(两臂) | 可猜占比 | 去猜后通过率(题数) |\n|---|---|---|---|---|---|---|")
        for Lk, ss in NEW.items():
            for s in ss:
                ms = {arm: [skill_mastery(f"p2_hdepicE_1023t_g4_{ver}_{arm}__{t}").get(s) for t in tasks] for arm in ("self", "goldlive")}
                ms = {arm: [x for x in v if x is not None] for arm, v in ms.items()}
                its = [x for arm in ("self", "goldlive") for x in agg[arm]["its"] if x["skill"] == s]
                if not its and not ms["self"]: continue
                g = [x for x in its if x["guess"] is not None]; k = [x for x in its if x["guess"] is False]
                L.append(f"| {Lk} | {s} | {f2(st.mean(ms['self'])) if ms['self'] else '-'} | {f2(st.mean(ms['goldlive'])) if ms['goldlive'] else '-'} | {pct(its)} | "
                         f"{(sum(x['guess'] for x in g) / len(g) * 100):.0f}% | {pct(k)} ({len(k)}) |" if g else f"| {Lk} | {s} | {f2(st.mean(ms['self'])) if ms['self'] else '-'} | {f2(st.mean(ms['goldlive'])) if ms['goldlive'] else '-'} | {pct(its)} | - | - |")
    out = "\n".join(L) + "\n"
    if len(sys.argv) > 1: open(sys.argv[1], "w").write(out)
    print(out)


if __name__ == "__main__":
    main()
