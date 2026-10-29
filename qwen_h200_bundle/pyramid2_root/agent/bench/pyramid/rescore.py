"""用修好的解析器重新评分已有结果。原始回复都在 logs/<qid>.json 里,不必重跑模型。
只改 parsed_index / correct,其余字段原样保留;改动量打印出来供核对。"""
import json, sys, glob, os
from pathlib import Path
import pconfig as P   # 把 bench/ 加进 sys.path
import score

def _is_live(p):
    """有进程正在往这个文件追加就别动它 —— 整体重写会覆盖并发写入。"""
    import subprocess
    r = subprocess.run(["pgrep", "-af", "evaluate.py"], capture_output=True, text=True)
    return str(p) in r.stdout


def rescore(jsonl, force=False):
    p = Path(jsonl); logdir = p.parent / "logs"
    if _is_live(p) and not force:
        print(f"  跳过(有进程正在写入): {p.name} —— 跑完再重评")
        return 0, 0, 0
    rows = [json.loads(l) for l in p.open() if l.strip()]
    changed = 0
    for r in rows:
        lf = logdir / f"{r['question_id']}.json"
        if not lf.exists():
            continue
        raw = json.loads(lf.read_text()).get("raw_response") or ""
        idx = score.score_choice(raw, r["options"]) if "options" in r else None
        if idx is None and "options" not in r:
            continue
        ok = (idx == r["gold_index"]) and not r.get("error")
        if idx != r.get("parsed_index") or ok != r["correct"]:
            r["parsed_index"], r["correct"] = idx, ok
            changed += 1
            d = json.loads(lf.read_text()); d.update(parsed_index=idx, correct=ok)
            lf.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    if changed:
        p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return changed, len(rows), sum(r["correct"] for r in rows)

if __name__ == "__main__":
    tot = 0
    for f in sorted(glob.glob(sys.argv[1])):
        ch, n, c = rescore(f)
        tot += ch
        if ch:
            print(f"  {f.split('results/')[-1]}: 修正 {ch} 题 -> {c}/{n}")
    print(f"共修正 {tot} 题")
