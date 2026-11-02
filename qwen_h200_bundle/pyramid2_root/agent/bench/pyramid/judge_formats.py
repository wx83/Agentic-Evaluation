"""open 简答的后处理判分:把 evaluate 留下的 score_by="pending" 行交给 judge(gemini 环境跑)。

    PYRAMID_SEED=43 $GEM judge_formats.py                 # 扫 results/formats/**/*.jsonl
    PYRAMID_SEED=43 $GEM judge_formats.py --dry           # 只数待判多少,不调用

judge 把回答映射到 [gold + 3 干扰项] 之一或 none;映射到 gold 才算对。行里改写 correct / score /
score_by="judge" / judge_match,并在 logs/<qid>.json 同步。已判过的(缓存)不再调用。
"""
import argparse, json
from pathlib import Path
import pconfig as P
import judge


def process(path, dry=False):
    rows = [json.loads(l) for l in path.open() if l.strip()]
    n_pend = sum(r.get("score_by") == "pending" and not r.get("error") for r in rows)
    if dry or not n_pend:
        return n_pend, 0
    n_call = 0
    for r in rows:
        if r.get("score_by") != "pending" or r.get("error"):
            continue
        reply = r.get("parsed") or ""
        ds = [o[3:] for o in (r.get("options") or [])] if r.get("options") else None
        if ds is None:
            ds = r["_distractors"] if "_distractors" in r else None
        if ds is None:
            raise KeyError(f"{r['question_id']} 行里没有干扰项,无法 judge")
        m, cached, model = judge.map_to_candidate(r["question_id"], r["question"], reply,
                                                  r["answer"], [d for d in ds if d != r["answer"]])
        n_call += not cached
        ok = (m == r["answer"])
        r.update({"correct": ok, "score": float(ok), "score_by": "judge",
                  "judge_match": m, "judge_model": model})
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    logdir = path.parent / "logs"
    for r in rows:
        if r.get("score_by") == "judge":
            lp = logdir / f"{r['question_id']}.json"
            if lp.exists():
                d = json.loads(lp.read_text())
                d.update({k: r[k] for k in ("correct", "score", "score_by", "judge_match", "judge_model")})
                lp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    return n_pend, n_call


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(P.RESULTS / "formats"))
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    tot_p = tot_c = 0
    for path in sorted(Path(a.root).rglob("*.jsonl")):
        if "/logs/" in str(path):
            continue
        n_pend, n_call = process(path, a.dry)
        if n_pend:
            print(f"  {path.relative_to(a.root)}: 待判 {n_pend}, 新调用 {n_call}")
        tot_p += n_pend; tot_c += n_call
    print(f"合计 待判 {tot_p}, judge 新调用 {tot_c}")


if __name__ == "__main__":
    main()
