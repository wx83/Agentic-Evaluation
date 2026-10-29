"""格式题的重判:用 logs/<qid>.json 里的原始回复按当前 formats.parse / score 重算(解析规则修正后用,不重跑模型)。
judge 已判过的行(score_by=judge)保留;open 行只重跑规则,规则无结论的仍记 pending。
    PYRAMID_SEED=43 python3 rescore_formats.py [--root DIR ...]
"""
import argparse, json
from pathlib import Path
import pconfig as P
import formats as FM


def process(path):
    rows = [json.loads(l) for l in path.open() if l.strip()]
    logdir = path.parent / "logs"
    n_ch = 0
    for r in rows:
        fmt = r.get("fmt")
        if not fmt or fmt == "mc" or r.get("error"):
            continue
        lp = logdir / f"{r['question_id']}.json"
        if not lp.exists():
            continue
        raw = json.loads(lp.read_text()).get("raw_response") or ""
        parsed, expl = FM.parse(fmt, raw)
        # 结果行里没有 kind / yn 真值 / ms 真集合,一律从题套取回(kind 缺失会让 COUNT/ROUTE 的规则失效)
        q = _truth(r)
        item = {"_yn_truth": q.get("_yn_truth"), "_gold_set": q.get("_gold_set"), "_gold_idx": r.get("gold_index"),
                "kind": q.get("kind"), "answer": r["answer"], "_distractors": r.get("_distractors") or [],
                "subtype": r["subtype"]}
        if fmt in ("open", "open_x") and r.get("score_by") == "judge":
            if parsed != r.get("parsed"):
                r["parsed"] = parsed; n_ch += 1
            continue
        correct, sc, by, detail = FM.score(fmt, parsed, item)
        new = {"parsed": parsed, "correct": correct, "score": sc, "score_by": by, "score_detail": detail, "explanation": expl}
        if any(r.get(k) != v for k, v in new.items()):
            r.update(new); n_ch += 1
            d = json.loads(lp.read_text()); d.update(new); lp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    if n_ch:
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return len(rows), n_ch


_SETS = {}


def _truth(r):
    """从题套文件找回 yn / ms 的真值(按 question_id)。"""
    for root in (P.SETS / "formats", P.SETS.parent.parent / "epic_sounds" / "sets"):
        for f in root.glob("L*_*.json"):
            if f not in _SETS:
                d = json.loads(f.read_text())          # L*_rejected.json 是列表,跳过
                _SETS[f] = {q["question_id"]: q for q in d["questions"]} if isinstance(d, dict) else {}
            q = _SETS[f].get(r["question_id"])
            if q:
                return q
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", nargs="+", default=[str(P.RESULTS / "formats")])
    a = ap.parse_args()
    tot = ch = 0
    for root in a.root:
        for path in sorted(Path(root).rglob("*.jsonl")):
            if "/logs/" in str(path):
                continue
            n, c = process(path); tot += n; ch += c
            if c:
                print(f"  {path.relative_to(root)}: 改动 {c}/{n}")
    print(f"合计 {tot} 行,改动 {ch}")


if __name__ == "__main__":
    main()
