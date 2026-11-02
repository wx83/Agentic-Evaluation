#!/usr/bin/env python3
"""experiments/daily_report/1021.md §3:pilot self run 每层概览 + skill 诊断 + 轨迹评测(trajectory_eval 的 md)+ Gemini 用量;替换 §3 之后的脚本段,§4 起的人工段保留。
  python3 daily_1021.py [--self p2_egoplan_1021_pilot_self]"""
import json, argparse, time
from pathlib import Path
import p2config as P
import daily_1014 as D14

OUT = Path("/mnt/work_new/weihanxu/experiments/daily_report/1021.md")
MARK = "\n## 3. 结果"
ARMS = ["p2_egoplan_1021_pilot_gold", "p2_egoplan_1021_pilot_none", "p2_egoplan_1021_pilot_blindgold"]


def build(self_run):
    L = [MARK.strip(), "", f"生成时间 {time.strftime('%Y-%m-%d %H:%M')} · self run `{self_run}` · replay 臂 {', '.join('`' + a + '`' for a in ARMS if (P.RUNS / a).exists())} · 脚本 `pyramid2/daily_1021.py` + `trajectory_eval.py`。",
         "**provisional**:L1–L3 的参考答案是 Examiner 写的(needs_verification,已装进 review 站待核);L4 中间决策点的参考 = 截断后第一条记录步骤,最终点 = 官方 gold。", ""]
    L += ["### 3.1 self 臂每层概览", ""] + D14.overview(self_run) + ["", "### 3.2 每层 × skill 诊断结论(self)", ""] + D14.skills(self_run)
    L += ["", "### 3.3 追问策略分布(self)", ""] + D14.followups(self_run)
    tp = P.RUNS / self_run / "trajectory.md"
    if tp.exists():
        body = tp.read_text().split("\n", 1)[1]
        body = "\n".join(("### 3.4" + l[4:] if l.startswith("## 1") else "### 3.5" + l[4:] if l.startswith("## 2") else "### 3.6" + l[4:] if l.startswith("## 3") else "### 3.7" + l[4:] if l.startswith("## 4") else ("#" + l if l.startswith("### ") else l)) for l in body.splitlines())
        L += ["", body]
    else:
        L += ["", "### 3.4 轨迹评测", "", "(trajectory_eval.py 未跑)"]
    n, bad = D14.goal_leak_check(self_run) if False else (None, None)
    L += ["", "### 3.8 Gemini 用量", ""] + D14.usage([self_run] + ARMS)
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--self", dest="self_run", default="p2_egoplan_1021_pilot_self")
    a = ap.parse_args()
    sec = build(a.self_run)
    txt = OUT.read_text()
    i = txt.find(MARK); k = txt.find("\n## 4.")
    tail = txt[k:] if k >= 0 else ""
    head = txt[:i] if i >= 0 else (txt[:k] if k >= 0 else txt)
    OUT.write_text(head.rstrip("\n") + "\n\n" + sec + tail)
    print(f"wrote §3 to {OUT} ({len(sec)} chars)")


if __name__ == "__main__":
    main()
