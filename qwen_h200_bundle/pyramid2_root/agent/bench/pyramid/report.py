"""汇总:每臂每 agent 的逐层通过率(Wilson 区间)、停止层级、加权总分、校准行。

可比性告诫:per_agent 臂与 shared_l1 的 L2+ 里,不同 agent 答的是不同题,
跨 agent 只能定性比较;pooled 臂和共享 L1 是跨 agent 锚点;
主分析是同一 agent 的跨臂差值。
"""
import json, math
import pconfig as P


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def agent_rows(arm, agent):
    rows = []
    for _, k in P.LEVELS:
        f = P.RESULTS / arm / agent / f"L{k}.jsonl"
        if not f.exists():
            break
        rs = [r for r in (json.loads(l) for l in f.open() if l.strip())
              if not r.get("error")]
        n_err = sum(1 for l in f.open() if l.strip() and json.loads(l).get("error"))
        c, n = sum(r["correct"] for r in rs), len(rs)
        lo, hi = wilson(c, n)
        gate = math.ceil(0.8 * n) if n else 1
        rows.append({"level": k, "n": n, "n_correct": c, "n_error": n_err,
                     "pass_rate": round(c / n, 3) if n else None,
                     "wilson_95": [round(lo, 3), round(hi, 3)],
                     "gate": gate, "passed": c >= gate})
    return rows


def summarize():
    out = {"arms": {}, "note": ("per_agent 臂与 shared_l1 的 L2+ 中不同 agent 答不同题,"
                                "跨 agent 比较只能定性;主分析是同一 agent 的跨臂差值。")}
    for arm in P.ARMS:
        stf = P.STATE / f"{arm}.json"
        if not stf.exists():
            continue
        st = json.loads(stf.read_text())
        arm_out = {"agents": {}, "calibration": {}}
        for lvl, scopes in st.get("levels", {}).items():
            for scope, rec in scopes.items():
                if "calib" in rec:
                    cal = rec["calib"]["mock"]
                    arm_out["calibration"][f"{scope}/L{lvl}"] = {
                        "mock_random": round(cal["n_correct"] / max(cal["n"], 1), 3),
                        "oracle_ok": True}
        for agent in st.get("agents", []):
            rows = agent_rows(arm, agent)
            stop = 0
            score = 0
            for r in rows:
                score += r["level"] * r["n_correct"]
                if r["passed"]:
                    stop = r["level"]
                else:
                    break
            arm_out["agents"][agent] = {
                "levels": rows, "stop_level": stop, "weighted_score": score,
                "max_score": sum(k * r["n"] for r, (_, k) in zip(rows, P.LEVELS))}
        out["arms"][arm] = arm_out
    P.REPORT.mkdir(parents=True, exist_ok=True)
    (P.REPORT / "report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def print_table(out):
    for arm, a in out["arms"].items():
        print(f"\n=== {arm} ===")
        for agent, r in a["agents"].items():
            cells = "  ".join(
                f"L{x['level']}: {x['n_correct']}/{x['n']}"
                f" [{x['wilson_95'][0]:.2f},{x['wilson_95'][1]:.2f}]"
                f"{'✓' if x['passed'] else '✗'}" for x in r["levels"])
            print(f"  {agent:12s} stop=L{r['stop_level']}  "
                  f"score={r['weighted_score']}/{r['max_score']}  {cells}")
        for k, v in sorted(a["calibration"].items()):
            print(f"  [calib] {k}: random={v['mock_random']:.2f} oracle=1.00")
    print(f"\n{out['note']}")


if __name__ == "__main__":
    print_table(summarize())
