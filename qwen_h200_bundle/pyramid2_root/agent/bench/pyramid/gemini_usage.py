"""Gemini 用量汇总:读 runlog 留下的逐次调用记录(logs/{gemini,generator}/gemini_calls.jsonl)。

    python3 gemini_usage.py                 # 按天 × 角色
    python3 gemini_usage.py --since 2026-09-28 --by key

- 角色:agent = 被评测的 gemini agent(clip30 / blind / memory 作答);generator = 出题 / 选题;judge = open 简答判分。
- 一次「调用」= 一次 generate_content 请求,含重试与回退;报错的请求单列(一般不计费,但占 RPM)。
- token 数从 2026-09-28 起才记录(usage_metadata);此前只有 prompt 字符数,视频 token 无从估计。
- key 只记指纹(sha256 前 8 位),可按 key 区分用量;key 本身不落盘。
"""
import argparse, collections, json
import pconfig as P

FILES = {"agent": P.LOGROOT / "gemini" / "gemini_calls.jsonl",
         "generator": P.LOGROOT / "generator" / "gemini_calls.jsonl",
         "judge": P.LOGROOT / "judge" / "gemini_calls.jsonl"}


def rows(since=None):
    for role, f in FILES.items():
        if not f.exists():
            continue
        for l in f.open():
            try:
                r = json.loads(l)
            except json.JSONDecodeError:
                continue
            if since and r.get("ts", "") < since:
                continue
            r["_role"] = role
            yield r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="YYYY-MM-DD,只统计此后")
    ap.add_argument("--by", default="day", choices=["day", "key", "model"])
    a = ap.parse_args()
    agg = collections.defaultdict(lambda: collections.Counter())
    for r in rows(a.since):
        k = {"day": r.get("ts", "")[:10], "key": r.get("key_id") or "(未记录)",
             "model": r.get("model") or "?"}[a.by]
        c = agg[(k, r["_role"])]
        c["calls"] += 1
        c["err"] += bool(r.get("error"))
        c["video"] += "<file:" in (r.get("prompt") or "")
        c["chars"] += r.get("prompt_chars") or 0
        for t in ("tok_in", "tok_out", "tok_think", "tok_total"):
            if r.get(t) is not None:
                c[t] += r[t]
                c[t + "_n"] += 1
    print(f"{a.by:12s} {'role':9s} {'calls':>6s} {'err':>5s} {'video':>6s} "
          f"{'tok_in':>10s} {'tok_out':>8s} {'tok_total':>10s} {'有token的调用':>8s}")
    tot = collections.Counter()
    for (k, role), c in sorted(agg.items()):
        print(f"{k:12s} {role:9s} {c['calls']:6d} {c['err']:5d} {c['video']:6d} "
              f"{c['tok_in']:10d} {c['tok_out']:8d} {c['tok_total']:10d} {c['tok_total_n']:8d}")
        tot.update(c)
    print(f"{'合计':12s} {'':9s} {tot['calls']:6d} {tot['err']:5d} {tot['video']:6d} "
          f"{tot['tok_in']:10d} {tot['tok_out']:8d} {tot['tok_total']:10d} {tot['tok_total_n']:8d}")


if __name__ == "__main__":
    main()
