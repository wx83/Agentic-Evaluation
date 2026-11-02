"""10-27 晚(用户定)每个 pyramid run 的分数。
skill 分 = 层号 + (边界 − 0.5) / 4:阶梯边界 b ∈ [0.5, 4.5],floor(0.5)= L.0,过第 1 档 = L.25,第 2 档 = L.5,第 3 档 = L.75,ceiling(4.5)= L+1.0。
层分 = 该层各 skill 分平均(落在 [L, L+1]);掌握量 = 层分 − L(0–1)。
pyramid 分 = 四层掌握量之和(0–4,「掌握了几层」);高度 = 从 L1 起掌握量 ≥ 0.5 的连续层数。
未收敛(examiner_failed / exhausted_at_level)的 skill 照算但标出;没有边界的 skill 不计入平均。
用法:python3 pyramid_score.py <run_dir>...  (或 import pyramid_score; pyramid_score.score_run(run_dir))"""
import json, re, sys
from pathlib import Path
import p2config as P

CONVERGED = {"reversals", "ceiling", "floor"}
LAYERS = ["L1", "L2", "L3", "L4"]


def _stop_reasons(run_dir):
    out = {}
    p = Path(run_dir) / "run.log"
    if not p.exists():
        return out
    for l in p.read_text(errors="ignore").splitlines():
        if "STAIRCASE_COMPLETE" in l and "boundaries" in l:
            for k, v in re.findall(r"([a-z_0-9]+)=([^ ,]+)", l.split("boundaries", 1)[1]):
                m = re.match(r"([^(]*)\(([^)]*)\)", v)
                out[k] = m.group(2) if m else ""
    return out


def skill_score(layer_no, boundary):
    return None if boundary is None else round(layer_no + (float(boundary) - 0.5) / 4, 3)


def score_run(run_dir):
    run_dir = Path(run_dir)
    reasons = _stop_reasons(run_dir)
    res = {"run": run_dir.name, "layers": {}, "skills": {}}
    total, height, chain = 0.0, 0, True
    for L in LAYERS:
        n = int(L[1])
        sp = run_dir / L / "state.json"
        if not sp.exists():
            res["layers"][L] = None
            chain = False
            continue
        stair = (json.loads(sp.read_text()).get("stair") or {})
        vals = []
        excluded = P.excluded_skills()
        for sk, v in stair.items():
            if not isinstance(v, dict) or sk in excluded:   # 全局拿掉的 skill(contact)不计分
                continue
            b = v.get("boundary")
            s = skill_score(n, b)
            reason = reasons.get(sk, v.get("stop_reason") or "")
            res["skills"][sk] = {"layer": L, "boundary": b, "score": s, "stop": reason, "converged": reason in CONVERGED}
            if s is not None:
                vals.append(s)
        if vals:
            ls = round(sum(vals) / len(vals), 3)
            mastery = round(ls - n, 3)
            res["layers"][L] = {"score": ls, "mastery": mastery, "n_skills": len(vals),
                                "n_converged": sum(1 for sk, r in res["skills"].items() if r["layer"] == L and r["converged"] and r["score"] is not None)}
            total += mastery
            if chain and mastery >= 0.5:
                height += 1
            else:
                chain = False
        else:
            res["layers"][L] = None
            chain = False
    res["pyramid"] = round(total, 3)
    res["height"] = height
    return res


def fmt(res):
    lines = [f"{res['run']}: pyramid {res['pyramid']:.2f} / 4, height {res['height']}"]
    for L in LAYERS:
        v = res["layers"].get(L)
        if not v:
            lines.append(f"  {L}: -")
            continue
        sks = [(sk, r) for sk, r in res["skills"].items() if r["layer"] == L]
        lines.append(f"  {L}: {v['score']:.2f} (mastery {v['mastery']:.2f}, {v['n_converged']}/{v['n_skills']} converged)")
        for sk, r in sks:
            lines.append(f"      {sk:34s} {'-' if r['score'] is None else f'{r['score']:.2f}'}  b={r['boundary']}{'' if r['converged'] else '  [' + (r['stop'] or 'no boundary') + ']'}")
    return "\n".join(lines)


if __name__ == "__main__":
    for d in sys.argv[1:]:
        r = score_run(d)
        print(fmt(r))
        (Path(d) / "score.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))


def html_block(prefix, runs_dir=None):
    """Space 概览用:<prefix>_self__* 每个 task 一行(pyramid 分 / 高度 / 四层层分),加逐 skill 折叠表。只有 self 臂跑阶梯,gold / none 是同题重放,没有自己的边界。"""
    import html as H
    from pathlib import Path
    runs_dir = Path(runs_dir or P.RUNS)
    parts = sorted(p for p in runs_dir.glob(f"{prefix}_self__*") if (p / "L1" / "state.json").exists())
    if not parts:
        return ""
    e = H.escape
    rows, det = [], []
    for p in parts:
        r = score_run(p)
        task = p.name.split("__", 1)[1]
        cells = []
        for L in LAYERS:
            v = r["layers"].get(L)
            cells.append("-" if not v else f'{v["score"]:.2f}<span class="muted"> ({v["n_converged"]}/{v["n_skills"]})</span>')
        rows.append(f'<tr><td>{e(task)}</td><td><b>{r["pyramid"]:.2f}</b> / 4</td><td>{r["height"]}</td>' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        sk = "".join(f'<tr><td>{e(v["layer"])}</td><td>{e(k)}</td><td>{"-" if v["score"] is None else f"{v["score"]:.2f}"}</td><td>{e(str(v["boundary"]))}</td><td>{e(v["stop"] or "")}{"" if v["converged"] else " <span class=\"muted\">(未收敛)</span>"}</td></tr>'
                     for k, v in r["skills"].items())
        det.append(f'<details><summary>task {e(task)} 逐 skill</summary><table><tr><th>层</th><th>skill</th><th>skill 分</th><th>边界</th><th>停止</th></tr>{sk}</table></details>')
    return ('<h4>pyramid 分数(self 臂;10-27 晚定义)</h4>'
            '<p class="sm">skill 分 = 层号 + (边界 − 0.5)/4:floor = L.0、过第 1 档 L.25、第 2 档 L.5、第 3 档 L.75、封顶 L+1.0;边界 = 2-down-1-up 阶梯两个反转点的均值。'
            '层分 = 该层 skill 分平均,括号 = 收敛 skill 数 / 计分 skill 数(未收敛 = examiner_failed / exhausted,边界是半截估计);pyramid 分 = 四层掌握量(层分 − 层号)之和,0–4;高度 = 从 L1 起掌握量 ≥ 0.5 的连续层数。gold / none 是同题重放,无阶梯边界。</p>'
            '<table><tr><th>task</th><th>pyramid</th><th>高度</th><th>L1</th><th>L2</th><th>L3</th><th>L4</th></tr>' + "".join(rows) + "</table>" + "".join(det))
