"""L4 replan 候选 -> Gemini 文本预筛草稿 -> 人工核验文件。

    PYRAMID_SEED=43 python replan_draft.py draft            # 读 data/replan_candidates.jsonl,写 data/replan_drafts.jsonl
    PYRAMID_SEED=43 python replan_draft.py ingest-review    # 读 experiments/pyramid_review.csv(section=replan),写 data/replan_verified.json

候选由 infer.replan_candidates 产出(narration 关键词 + 掉落后清理)。Gemini 只看 [t0-10, t1+15] 的 narration 文本,
判断是否真有「计划外」事件、类型、一句话 situation(不含纠正动作)、以及纠正动作短语;gold 必须等于程序推出的
e_rec 短语,否则记 gold_mismatch 供人工看。key 走 GEMINI_API_KEY 环境变量。
"""
import sys, json, re, collections, pathlib
import pconfig as P
import infer as IN
import gemini_io

DATA = P.DATA
CAND = DATA / "replan_candidates.jsonl"
DRAFT = DATA / "replan_drafts.jsonl"
VERIFIED = DATA / "replan_verified.json"
TYPES = ["dropped", "forgot step", "wrong object", "appliance state", "mind change", "stuck or failed action", "none"]

PROMPT = """You read first-person kitchen video narrations (one line per action, with start times in seconds).
Decide whether something does NOT go as planned around the marked line, i.e. an unforeseen situation that forces
the camera wearer to deviate from what they were doing: an object dropped or spilled, a step they forgot and had
to go back to, a wrong object picked, an appliance in an unexpected state, a stuck or failed action, or a change
of mind. Ordinary sequential cooking is NOT a deviation.

Narrations ({t0:.0f}-{t1:.0f} s; the clip shown to the test model ends at {cut:.1f} s, so lines after that are hidden from it):
{lines}

>>> marked line (the suspected deviation): [{t_dev:.1f}] {dev}
>>> the first narrated action after the clip ends: [{t_rec:.1f}] {rec}

Reply with ONE JSON object only:
{{"is_deviation": true/false,
 "deviation_type": one of {types},
 "visible_in_clip": true/false   (can a viewer notice the problem from what happens BEFORE {cut:.1f} s?),
 "situation": "<one sentence describing the problem, without saying what they do about it>",
 "recovery": "<verb + object: what the camera wearer actually does next to deal with it>",
 "recovery_is_first_action": true/false   (is the marked first action after the clip really the recovery, not an unrelated step?),
 "confidence": 0-1}}"""


def narr_lines(ix, t0, t1):
    ev = sorted(ix.in_window(t0, t1, "narration"), key=lambda x: x.t_start)
    return "\n".join(f"[{e.t_start:.1f}] {e.text}" for e in ev)


def _json(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def draft():
    import adaptive as A
    rows = [json.loads(l) for l in CAND.open()]
    seen, keep = set(), []
    for r in rows:                                   # 同一个纠正动作只保留第一条候选
        if r["rec_eid"] in seen:
            continue
        seen.add(r["rec_eid"]); keep.append(r)
    done = {}
    if DRAFT.exists():
        for l in DRAFT.open():
            d = json.loads(l); done[d["rec_eid"]] = d
    print(f"{len(rows)} candidates -> {len(keep)} unique recovery actions; {len(done)} already drafted", flush=True)
    with DRAFT.open("a") as out:
        for i, r in enumerate(keep):
            if r["rec_eid"] in done:
                continue
            ix = A.ix_of(r["video"])
            lines = narr_lines(ix, r["t0"] - 10, r["t1"] + 15)
            prompt = PROMPT.format(t0=r["t0"] - 10, t1=r["t1"] + 15, cut=r["t1"], lines=lines, t_dev=r["t_dev"],
                                   dev=r["dev_text"], t_rec=r["t_rec"], rec=r["rec_text"], types=json.dumps(TYPES))
            try:
                txt, mid = gemini_io.gen(prompt, max_tokens=400, role="generator")
                j = _json(txt) or {"parse_error": txt[:200]}
            except Exception as ex:
                j = {"error": f"{type(ex).__name__}: {str(ex)[:120]}"}
            d = dict(r, draft=j, gold_mismatch=bool(j.get("recovery")) and
                     IN.PRIM._head_noun(j.get("recovery", "")) != IN.PRIM._head_noun(r["gold"]))
            out.write(json.dumps(d, ensure_ascii=False) + "\n"); out.flush()
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{len(keep)}", flush=True)
    ds = [json.loads(l) for l in DRAFT.open()]
    dev = [d for d in ds if d["draft"].get("is_deviation") and d["draft"].get("visible_in_clip")
           and d["draft"].get("recovery_is_first_action")]
    print(f"drafted {len(ds)}; deviation & visible & recovery-first: {len(dev)}; by type:",
          collections.Counter(d["draft"].get("deviation_type") for d in dev).most_common())


def ingest_review(csv_path="/mnt/work_new/weihanxu/experiments/pyramid_review.csv"):
    import csv
    ds = {json.loads(l)["rec_eid"]: json.loads(l) for l in DRAFT.open()}
    ok = collections.defaultdict(list)
    for r in csv.DictReader(open(csv_path, encoding="utf-8")):
        if r["section"] != "replan":
            continue
        ok[r["question_id"]].append(r)
    verified = {}
    for qid, rs in ok.items():
        last = sorted(rs, key=lambda x: x["timestamp"])[-1]
        if last["gt_check"] == "ok" and last["question_check"] in ("ok", "") and qid in ds:
            d = ds[qid]; verified[qid] = dict(d, review=last)
    VERIFIED.write_text(json.dumps(verified, ensure_ascii=False, indent=1))
    print(f"verified {len(verified)} of {len(ok)} reviewed -> {VERIFIED}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "draft"
    {"draft": draft, "ingest-review": ingest_review}[cmd]()
