"""扫窗口 -> 组装四级链 -> 干扰项 -> 校验 -> chains.json"""
import json, random, hashlib, argparse, collections
import config as C
from timeline_index import TimelineIndex
import primitives as P

TIERS = ["Easy", "Low", "Medium", "High"]

Q = {
 "Easy":   "You can hear {snd} in this clip. Which object visible on screen is producing it?",
 "Low":    "At the moment {snd} is heard, which object is the camera wearer handling?",
 "Medium": "How many separate times is {snd} heard in this clip?",
 "High":   "Put these three actions in the order they happen in this clip.",
}


def shuffled(gold, distr, qid):
    opts = [gold] + list(distr)
    rng = random.Random(int(hashlib.sha256(qid.encode()).hexdigest()[:8], 16))
    rng.shuffle(opts)
    gi = opts.index(gold)
    return [f"{'ABCD'[i]}. {o}" for i, o in enumerate(opts)], gi


def build_chain(ix, anchor, rng, chain_no):
    t0 = max(0.0, anchor.mid() - C.CLIP_SEC / 2)
    t1 = min(ix.duration, t0 + C.CLIP_SEC)
    t0 = max(0.0, t1 - C.CLIP_SEC)
    # Easy 不需要「同标签 ±15s 唯一」——问的是哪个可见物体在发声，重复出现不影响答案。
    # 只有 Low（"听到 X 的那一刻"）才需要唯一锚点。
    all_sounds = ix.sounds_between(t0, t1)
    win_sounds = [s for s in P.salient_sounds(ix) if t0 <= s.mid() <= t1]

    found = {}
    for s in all_sounds:                              # Easy
        r = P.find_easy(ix, s)
        if r: found["Easy"] = r; break
    for s in win_sounds:                              # Low
        r = P.find_low(ix, s)
        if r and r["gold"] != found.get("Easy", {}).get("gold"):
            found["Low"] = r; break
    for s in ix.sounds_between(t0, t1):               # Medium（定窗后才算）
        r = P.find_medium(ix, s, t0, t1)
        if r: found["Medium"] = r; break
    r = P.find_high(ix, t0, t1)                       # High
    if r: found["High"] = r

    if len(found) < 4:
        return None, f"缺层:{sorted(set(TIERS)-set(found))}"
    golds = [found[t]["gold"] for t in TIERS]
    if len(set(golds)) < 4:
        return None, "层间 gold 重复"

    # 5 分钟长窗口，证据随机落位
    lead = rng.uniform(0, C.LONG_SEC - C.CLIP_SEC)
    L0 = max(0.0, min(t0 - lead, ix.duration - C.LONG_SEC))
    L1 = min(ix.duration, L0 + C.LONG_SEC)
    needle = (t0 - L0) / max(1e-6, (L1 - L0))

    steps = []
    for tier in TIERS:
        f = found[tier]
        qid = f"{ix.video_id}_c{chain_no:02d}_{tier}"
        kind = f["kind"]
        sl = f.get("sound").label if f.get("sound") is not None else None
        dk = "COUNT" if kind == "COUNT" else ("ORDER" if kind == "ORDER" else "OBJECT")
        distr = P.distractors(ix, dk, f["gold"], t0, t1, rng, sl)
        if not distr:
            return None, f"{tier} 干扰项不足"
        opts, gi = shuffled(f["gold"], distr, qid)
        q = Q[tier].format(snd=C.SOUND_PHRASE[sl]) if sl else Q[tier]
        if tier == "High":
            q += "\n(" + "; ".join(sorted(f["gold"].split(" -> "))) + ")"
        item = {"question_id": qid, "tier": tier, "question": q,
                "answer": f["gold"], "options": opts,
                "correct_option": "ABCD"[gi], "_gold_idx": gi,
                "kind": kind, "_distractors": distr, "_sound_label": sl,
                "evidence_event_ids": f["eids"],
                "evidence_t": round(ix.ev(f["eids"][0]).mid(), 2)}
        errs = P.verify(ix, item, t0, t1)
        if errs:
            return None, f"{tier}: {errs[0]}"
        # 层间不泄底：下层题干/选项不得含上层 gold
        for prev in steps:
            if prev["answer"].lower() in q.lower():
                return None, "层间泄底"
        steps.append(item)

    return {"chain_id": f"{ix.video_id}_c{chain_no:02d}", "video_id": ix.video_id,
            "clip_start": round(t0, 2), "clip_end": round(t1, 2),
            "long_start": round(L0, 2), "long_end": round(L1, 2),
            "needle_position": round(needle, 3), "steps": steps}, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=C.VIDEO)
    ap.add_argument("--n-chains", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    ix = TimelineIndex(a.video)
    rng = random.Random(a.seed)
    sal = P.salient_sounds(ix)
    chains, rejects, used = [], collections.Counter(), []
    for s in sal:
        if len(chains) >= a.n_chains:
            break
        if any(abs(s.mid() - u) < C.CLIP_SEC for u in used):   # 窗口互不重叠
            continue
        c, why = build_chain(ix, s, rng, len(chains))
        if c:
            chains.append(c); used.append(s.mid())
        else:
            rejects[why.split(":")[0]] += 1

    C.SHARED.mkdir(parents=True, exist_ok=True)
    (C.SHARED / "chains.json").write_text(json.dumps(
        {"video_id": a.video, "n_chains": len(chains),
         "clip_sec": C.CLIP_SEC, "long_sec": C.LONG_SEC,
         "size": C.SIZE, "fps": C.FPS, "seed": a.seed,
         "chains": chains}, ensure_ascii=False, indent=1))
    print(f"生成 {len(chains)} 条链  ->  {C.SHARED/'chains.json'}")
    print("拒绝原因分布:", dict(rejects.most_common(8)))
    tot = sum(rejects.values()) + len(chains)
    print(f"拒绝率: {sum(rejects.values())}/{tot} = {sum(rejects.values())/max(1,tot):.0%}")


if __name__ == "__main__":
    main()
