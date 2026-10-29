#!/usr/bin/env python3
"""experiments/daily_report/1022.md §B:题树评测结果(tree_eval.md 原文 + 每层概览 + 用量);替换 §B 之后的脚本段,§C 起人工段保留。
  python3 daily_1022.py [--agents flash=p2_egoplan_1022_tree_flash,pro=p2_egoplan_1022_tree_pro]"""
import json, argparse, time
from pathlib import Path
import p2config as P
import daily_1014 as D14

OUT = Path("/mnt/work_new/weihanxu/experiments/daily_report/1022.md")
MARK = "\n## B. 题树评测结果"


def build(agents):
    runs = [v for k, v in agents]
    L = [MARK.strip(), "", f"生成时间 {time.strftime('%Y-%m-%d %H:%M')} · runs {', '.join('`' + r + '`' for r in runs)} · 脚本 `pyramid2/daily_1022.py` + `tree_eval.py`(设计见 plan / §0)。",
         "**provisional**:L1–L3 参考答案是 Examiner 写的(待核);L4 中间决策点参考 = 截断后第一条记录步骤,最终点 = 官方 gold;3.1-pro 既是 Examiner 又是第二个 agent。", ""]
    for k, r in agents:
        if (P.RUNS / r / "L1" / "summary.json").exists():
            L += [f"### B.{k} 每层概览(`{r}`)", ""] + D14.overview(r) + [""]
    first = runs[0]; tp = P.RUNS / first / "tree_eval.md"
    if tp.exists():
        body = tp.read_text().split("\n", 1)[1]
        body = "\n".join(("### B." + l[3:] if l.startswith("## ") else ("#### " + l[4:] if l.startswith("### ") else l)) for l in body.splitlines())
        L += [body]
    else:
        L += ["(tree_eval.py 未跑)"]
    L += ["", "### B.用量", ""] + D14.usage(runs)
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--agents", default="flash=p2_egoplan_1022_tree_flash,pro=p2_egoplan_1022_tree_pro"); a = ap.parse_args()
    agents = [tuple(kv.split("=")) for kv in a.agents.split(",")]
    sec = build(agents)
    txt = OUT.read_text() if OUT.exists() else "# 2026-10-22\n"
    i = txt.find(MARK); k = txt.find("\n## C.")
    tail = txt[k:] if k >= 0 else ""
    head = txt[:i] if i >= 0 else (txt[:k] if k >= 0 else txt)
    OUT.write_text(head.rstrip("\n") + "\n\n" + sec + tail)
    print(f"wrote §B to {OUT} ({len(sec)} chars)")


if __name__ == "__main__":
    main()
