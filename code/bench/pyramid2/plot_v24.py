#!/usr/bin/env python3
"""11-03 三个 task 各层的变化图(SVG,无 matplotlib):python3 plot_v24.py [out.html]
图 1:每 task 一个面板,x = L1…L4,y = 通过率(%),系列 = v24 self / v24 goldlive / v24c self(组合题) / v24c none / v24c gold(后三者只有 L2 L3 时为 L2 L3);点旁标 n。
图 2:每 task 一个面板,各层 mastery(pyramid_score,只有自走阶梯的 self / goldlive 臂有);图 3:各层盲测可猜占比(v24 self)。
数据:output/pyramid_v2/runs/p2_hdepicE_1023t_g4_<ver>_<arm>__<task>/<L>/history.jsonl 与 score.json。"""
import sys, json, html
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import p2config as P

TASKS = ["55", "13", "39"]; LAYERS = ["L1", "L2", "L3", "L4"]
NAMES = {"L1": "Frame", "L2": "Grounding", "L3": "Spatio-temporal", "L4": "Planning"}
SERIES = [("v24 self", "p2_hdepicE_1023t_g4_v24_self__"), ("v24 goldlive", "p2_hdepicE_1023t_g4_v24_goldlive__"),
          ("v24c self (composed)", "p2_hdepicE_1023t_g4_v24c_self__"), ("v24c none", "p2_hdepicE_1023t_g4_v24c_none__"), ("v24c gold", "p2_hdepicE_1023t_g4_v24c_gold__"),
          ("v25 self (L3 hard)", "p2_hdepicE_1023t_g4_v25_self__"), ("v26 self (L3 + ego frame)", "p2_hdepicE_1023t_g4_v26_self__"), ("v27 self (+ ref frame)", "p2_hdepicE_1023t_g4_v27_self__")]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7a5bd6", "#5b8a3c", "#b0486a"]     # dataviz 参考调色板,固定顺序
INK, MUTED, GRID = "#1a1a19", "#6b6b66", "#e4e3de"


def rows(run, L):
    p = P.RUNS / run / L / "history.jsonl"
    if not p.exists(): return []
    return [json.loads(l) for l in open(p)]


def stats(run):
    out = {}
    for L in LAYERS:
        rs = [r for r in rows(run, L) if r.get("verdict") in ("correct", "wrong")]
        if not rs: continue
        out[L] = {"n": len(rs), "acc": sum(1 for r in rs if r["verdict"] == "correct") / len(rs),
                  "blind": (sum(1 for r in rs if r.get("blind_guessable")) / len(rs)) if any("blind_guessable" in r for r in rs) else None,
                  "comp": sum(1 for r in rs if r.get("comp")) }
    return out


def mastery(run):
    p = P.RUNS / run / "score.json"
    if not p.exists(): return {}
    s = json.loads(p.read_text())
    return {L: (v or {}).get("mastery") for L, v in (s.get("layers") or {}).items()}


def panel(title, series, ylab, ymax=100, fmt=lambda v: f"{v:.0f}", W=330, H=230):
    """series: list of (name, color, {L: (value, label)})。折线 + 点 + 点旁 n 标签。"""
    L0, R0, T0, B0 = 44, 12, 28, 34; pw, ph = W - L0 - R0, H - T0 - B0
    x = lambda i: L0 + pw * (i + 0.5) / len(LAYERS); y = lambda v: T0 + ph * (1 - v / ymax)
    g = [f'<text x="{L0}" y="16" font-size="13" font-weight="600" fill="{INK}">{html.escape(title)}</text>']
    for k in range(0, ymax + 1, ymax // 4):
        g.append(f'<line x1="{L0}" x2="{W - R0}" y1="{y(k):.1f}" y2="{y(k):.1f}" stroke="{GRID}"/><text x="{L0 - 6}" y="{y(k) + 4:.1f}" font-size="10" text-anchor="end" fill="{MUTED}">{fmt(k)}</text>')
    for i, L in enumerate(LAYERS):
        g.append(f'<text x="{x(i):.1f}" y="{H - 18}" font-size="11" text-anchor="middle" fill="{INK}">{L}</text><text x="{x(i):.1f}" y="{H - 6}" font-size="8.5" text-anchor="middle" fill="{MUTED}">{NAMES[L]}</text>')
    g.append(f'<text transform="rotate(-90)" x="{-(T0 + ph / 2):.1f}" y="11" font-size="10" text-anchor="middle" fill="{MUTED}">{html.escape(ylab)}</text>')
    for name, col, vals in series:
        pts = [(i, vals[L]) for i, L in enumerate(LAYERS) if L in vals and vals[L][0] is not None]
        if not pts: continue
        for (i1, v1), (i2, v2) in zip(pts, pts[1:]):
            if i2 == i1 + 1: g.append(f'<line x1="{x(i1):.1f}" y1="{y(v1[0]):.1f}" x2="{x(i2):.1f}" y2="{y(v2[0]):.1f}" stroke="{col}" stroke-width="2" fill="none"/>')
        for i, (v, lab) in pts:
            g.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="4" fill="{col}" stroke="#fff" stroke-width="2"><title>{html.escape(name)} {L if False else LAYERS[i]}: {fmt(v)} {html.escape(lab)}</title></circle>')
            if lab: g.append(f'<text x="{x(i) + 6:.1f}" y="{y(v) - 5:.1f}" font-size="8.5" fill="{MUTED}">{html.escape(lab)}</text>')
    return f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif">' + "".join(g) + "</svg>"


def legend(series):
    return '<div class="lg">' + "".join(f'<span><i style="background:{c}"></i>{html.escape(n)}</span>' for n, c in series) + "</div>"


def table(data):
    out = ['<table><tr><th>task</th><th>臂</th>' + "".join(f"<th>{L} 通过率 (n)</th>" for L in LAYERS) + "</tr>"]
    for t in TASKS:
        for name, pre in SERIES:
            st = data[t].get(name)
            if not st: continue
            out.append(f"<tr><td>{t}</td><td>{html.escape(name)}</td>" + "".join(f"<td>{st[L]['acc'] * 100:.0f}% ({st[L]['n']})</td>" if L in st else "<td>–</td>" for L in LAYERS) + "</tr>")
    out.append("</table>"); return "".join(out)


def main(out_path):
    data = {t: {name: stats(pre + t) for name, pre in SERIES} for t in TASKS}
    MAST = [SERIES[0], SERIES[1], SERIES[5], SERIES[6], SERIES[7]]                                                # 自走阶梯的臂才有 mastery
    mast = {t: {name: mastery(pre + t) for name, pre in MAST} for t in TASKS}
    figs1 = []; figs2 = []; figs3 = []
    for t in TASKS:
        s1 = [(name, COLORS[k], {L: (v["acc"] * 100, f"n={v['n']}") for L, v in data[t][name].items()}) for k, (name, _) in enumerate(SERIES) if data[t][name]]
        figs1.append(panel(f"task {t}: 通过率", s1, "通过率 %"))
        s2 = [(name, COLORS[SERIES.index((name, pre))], {L: (m * 100, "") for L, m in mast[t][name].items() if m is not None}) for name, pre in MAST if mast[t][name]]
        figs2.append(panel(f"task {t}: mastery(阶梯边界)", s2, "mastery × 100"))
        b = data[t]["v24 self"]
        s3 = [("v24 self 盲测可猜", COLORS[0], {L: (v["blind"] * 100, f"n={v['n']}") for L, v in b.items() if v["blind"] is not None})]
        figs3.append(panel(f"task {t}: 盲测可猜占比", s3, "可猜 %"))
    used = [(n, COLORS[k]) for k, (n, _) in enumerate(SERIES) if any(data[t][n] for t in TASKS)]
    css = "body{font-family:system-ui,sans-serif;max-width:1100px;margin:20px auto;padding:0 16px;color:#1a1a19;background:#fff}.row{display:flex;flex-wrap:wrap;gap:8px}.lg span{display:inline-flex;align-items:center;margin-right:14px;font-size:12px}.lg i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:5px}table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ddd;padding:3px 8px}h2{font-size:16px;margin-top:22px}"
    page = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v24 三 task 分层变化</title><style>{css}</style></head><body>
<h1 style="font-size:20px">pyramid2 v24:三个 task 从 L1 到 L4 的变化</h1>
<p style="font-size:13px;color:#6b6b66">L1 Frame Perception(单帧)→ L2 Temporal Grounding(整个 sub-goal clip)→ L3 Spatio-temporal Reasoning → L4 Goal-conditioned Planning。v24 self / goldlive 自走阶梯;v24c = 组合题(下层弱点)模式,none / gold 为同题换 history 的重放臂(只有 L2 L3);v25 = L3 加难(spatial 加权 + 可盲猜 skill 硬过滤),L1 L2 与 v24 self 相同。点旁 n = 计分题数。</p>
<h2>1. 通过率(看视频,多数票)</h2>{legend(used)}<div class="row">{"".join(figs1)}</div>
<h2>2. mastery(2-down-1-up 阶梯边界换算,0–1)</h2>{legend([u for u in used if u[0] in {n for n, _ in MAST}])}<div class="row">{"".join(figs2)}</div>
<h2>3. 盲测可猜占比(不看画面、不带 history 也答对;只标记不作废)</h2><div class="row">{"".join(figs3)}</div>
<h2>4. 数字</h2>{table(data)}
</body></html>"""
    Path(out_path).write_text(page, encoding="utf-8"); print("written", out_path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(P.ROOT / "reports" / "v24_three_tasks.html"))
