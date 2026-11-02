#!/usr/bin/env python3
"""clip 模式的小金字塔(2026-10-11):在**新视频**上挑 N 个 30 s clip,四层题都只从这几个 clip 里出,
每层 n 题,然后对每层跑 modality_probe 四条件(av / v_only / a_only / a_swap),
看「看画面为主、基本不听」这个结论在每一层、每个 clip 上是否成立。

与主金字塔的区别(都由 PYRAMID_CLIPS 触发,见 pconfig / assemble):
  - 事实池只留落在某个 clip 里的事实(窗口重叠 >= OVERLAP_MIN);
  - L1–L3 的题窗口统一改成 clip 窗口(gold 由 verify 在新窗口上重推,不成立即拒);
  - L4 的窗口必须正好结束在决策点,不能挪:保留原窗口,只标归属(重叠 >= OVERLAP_MIN_HIGH);
  - 同层不做窗口去重(否则每个 clip 只剩 1 题)。

用法:
  export PYRAMID_SEED=1011 PYRAMID_VIDEOS=P08-20240618-163547
  python3 clip_pyramid.py select --n-clips 10                    # -> <POUT>/clips.json(贪心选供给最均衡的窗口)
  export PYRAMID_CLIPS=<POUT>/clips.json
  $GEM clip_pyramid.py run --n 30                                # 组卷+评测四层(orchestrate pooled/clip30/no-gate),再四条件探针
  python3 clip_pyramid.py report                                 # 汇总四层 × 四条件 × 每 clip
"""
import argparse, collections, json, subprocess, sys
from pathlib import Path
import pconfig as P

OVERLAP_MIN = 20.0        # L1–L3:原窗口与 clip 至少重叠 20 s(挪动 <= 10 s)才算属于该 clip
OVERLAP_MIN_HIGH = 15.0   # L4:保留原窗口,重叠 >= 15 s 即归属
CAP = 6                   # 选 clip 时每层每 clip 最多计 6 条(避免单层撑爆分数)
TIER_W = {"Easy": 1, "Low": 2, "Medium": 1, "High": 2}   # Low / High 供给稀缺,加权
# orchestrate / modality_probe 用**当前**解释器(需要 numpy 做 ego-side 校验;gemini conda 环境没有 numpy,
# 但系统 python3 有 numpy + google-genai)。评测子进程由 orchestrate 按 P.AGENT_INTERPRETER 分发,不受影响。
GEM = sys.executable
HERE = Path(__file__).resolve().parent


def clips_path():
    return P.POUT / "clips.json"


def _ov(f, c):
    return min(f["t1"], c["t1"]) - max(f["t0"], c["t0"])


# ---------- select ----------
def select(a):
    import facts as F
    from timeline_index import TimelineIndex
    pool = F.load_all()
    fs = [(t, f) for t, L in pool.items() for f in L if not f.get("windows")]
    W = P.WIN_SEC
    cands = []
    for v in P.VIDEOS:
        dur = TimelineIndex(v).duration
        for s in range(0, int(dur - W) + 1):
            c = {"video_id": v, "t0": float(s), "t1": float(s + W)}
            cnt = collections.Counter()
            for t, f in fs:
                if f["video_id"] == v and _ov(f, c) >= (OVERLAP_MIN_HIGH if t == "High" else OVERLAP_MIN):
                    cnt[t] += 1
            score = sum(TIER_W[t] * min(cnt[t], CAP) for t in TIER_W)
            cands.append((score, c, dict(cnt)))
    cands.sort(key=lambda x: -x[0])
    chosen = []
    for sc, c, cnt in cands:
        if all(cc["video_id"] != c["video_id"] or abs(cc["t0"] - c["t0"]) >= W for cc in chosen):
            chosen.append({**c, "score": sc, "supply": cnt})
        if len(chosen) == a.n_clips:
            break
    chosen.sort(key=lambda c: (c["video_id"], c["t0"]))
    for i, c in enumerate(chosen):
        c["clip_id"] = f"C{i:02d}"
    tot = collections.Counter()
    for c in chosen:
        tot.update(c["supply"])
        print(f"{c['clip_id']} {c['video_id']} [{c['t0']:.0f},{c['t1']:.0f}] score={c['score']} {c['supply']}")
    print("assignable total:", dict(tot))
    out = clips_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"videos": P.VIDEOS, "seed": P.SEED, "overlap_min": OVERLAP_MIN,
                               "overlap_min_high": OVERLAP_MIN_HIGH, "clips": chosen}, ensure_ascii=False, indent=1))
    print(f"-> {out}\n   export PYRAMID_CLIPS={out}")


# ---------- restrict(assemble.build_set 调用)----------
def restrict(pool, tier):
    import facts as F
    out = []
    for f in pool:
        if f.get("windows"):
            continue
        best = max((c for c in P.CLIPS if c["video_id"] == f["video_id"]), key=lambda c: _ov(f, c), default=None)
        if best is None:
            continue
        ov = _ov(f, best)
        g = dict(f, clip_id=best["clip_id"], clip_window=[best["t0"], best["t1"]])
        if tier == "High":
            if ov < OVERLAP_MIN_HIGH:
                continue
        else:
            if ov < OVERLAP_MIN:
                continue
            if not (best["t0"] <= f.get("evidence_t", best["t0"]) <= best["t1"]):
                continue
            g["_orig_window"] = [f["t0"], f["t1"]]
            g["t0"], g["t1"] = best["t0"], best["t1"]
            g["fact_id"] = F._fid(f["video_id"], f["subtype"], f["gold"], f["evidence_event_ids"], g["t0"])
        out.append(g)
    return out


# ---------- run ----------
def run(a):
    assert P.CLIPS, "先 export PYRAMID_CLIPS=<POUT>/clips.json"
    env = dict(__import__("os").environ)
    cmd = [GEM, str(HERE / "orchestrate.py"), "--arm", "pooled", "--mode", "clip30", "--agents", "gemini",
           "--no-gate", "--select", a.select, "--limit", str(a.n)]
    if a.offline:
        cmd.append("--offline")
    print("[clip_pyramid] " + " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=str(HERE), env=env)
    assert r.returncode == 0, "orchestrate 失败"
    if a.no_probe:
        return
    for level in (1, 2, 3, 4):
        setf = P.SETS / "pooled_clip30" / "pooled" / f"L{level}.json"
        if not setf.exists():
            print(f"[clip_pyramid] L{level} 无题套,跳过探针", flush=True); continue
        cmd = [GEM, "-W", "ignore", str(HERE / "modality_probe.py"), "run", "--arm", "pooled_clip30", "--level", str(level)]
        print("[clip_pyramid] " + " ".join(cmd), flush=True)
        r = subprocess.run(cmd, cwd=str(HERE), env=env)
        assert r.returncode == 0, f"modality_probe L{level} 失败"


# ---------- report ----------
def _pct(c, n):
    return f"{100 * c / n:.0f}% ({c}/{n})" if n else "—"


def report(a):
    import modality_probe as MP
    clips = {c["clip_id"]: c for c in (P.CLIPS or json.loads(clips_path().read_text())["clips"])}
    L = [f"# clip 金字塔(seed {P.SEED},{', '.join(P.VIDEOS)},{len(clips)} clips,每层 <= {a.n} 题,gemini-3.5-flash,后端 {P.BACKEND})", "",
         "每层四条件:av 原 clip / v_only 静音 / a_only 黑屏留音 / a_swap 原画面+另一题音轨。括号「对/题数」。", ""]
    L += ["## clips", "", "| clip | video | window | 供给 Easy/Low/Medium/High |", "|---|---|---|---|"]
    for c in clips.values():
        s = c["supply"]
        L.append(f"| {c['clip_id']} | {c['video_id']} | [{c['t0']:.0f}, {c['t1']:.0f}] | {s.get('Easy',0)}/{s.get('Low',0)}/{s.get('Medium',0)}/{s.get('High',0)} |")
    L += ["", "## 各层 × 条件", "", "| level | n | av | v_only | a_only | a_swap | needs-both(av 对里) | 跟声音(a_swap, donor 在选项) |", "|---|---|---|---|---|---|---|---|"]
    per_clip = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    needs_both_ids = {}
    for level in (1, 2, 3, 4):
        R = {c: MP._rows(P.BACKEND, c, level) for c in MP.CONDS}
        if not R["av"]:
            L.append(f"| L{level} | 0 | — | — | — | — | — | — |"); continue
        setq = {q["question_id"]: q for q in MP.load_set("pooled_clip30", level)}
        dmap_f = MP.out_dir(level=level) / "swap_map.json"
        donors = json.loads(dmap_f.read_text()) if dmap_f.exists() else {}
        ids = list(R["av"])
        cells = []
        for c in MP.CONDS:
            common = [i for i in ids if i in R[c]]
            cells.append(_pct(sum(bool(R[c][i]["correct"]) for i in common), len(common)))
            for i in common:
                cid = setq.get(i, {}).get("clip_id", "?")
                per_clip[cid][(level, c)][0] += bool(R[c][i]["correct"]); per_clip[cid][(level, c)][1] += 1
        avok = [i for i in ids if R["av"][i]["correct"] and i in R["v_only"] and i in R["a_only"]]
        nb = [i for i in avok if not R["v_only"][i]["correct"] and not R["a_only"][i]["correct"]]
        needs_both_ids[level] = nb
        n_in = aud = 0
        for i in ids:
            if i not in R["a_swap"] or i not in donors:
                continue
            r = R["a_swap"][i]; opts = [o.split(". ", 1)[-1].strip().lower() for o in r["options"]]
            d = donors[i]["donor_answer"].lower()
            if d in opts:
                n_in += 1
                pi = r.get("parsed_index")
                aud += pi is not None and pi != r["gold_index"] and opts[pi] == d
        L.append(f"| L{level} | {len(ids)} | " + " | ".join(cells) + f" | {_pct(len(nb), len(avok))} | {_pct(aud, n_in)} |")
    L += ["", "## 每个 clip 的 av / v_only / a_only(对/题数,四层合计)", "", "| clip | av | v_only | a_only | a_swap |", "|---|---|---|---|---|"]
    for cid in sorted(per_clip):
        row = []
        for c in MP.CONDS:
            k = sum(per_clip[cid][(lv, c)][0] for lv in (1, 2, 3, 4)); n = sum(per_clip[cid][(lv, c)][1] for lv in (1, 2, 3, 4))
            row.append(_pct(k, n))
        L.append(f"| {cid} | " + " | ".join(row) + " |")
    L += ["", "## needs-both 题(av 对、v_only 错、a_only 错)", ""]
    for lv, nb in needs_both_ids.items():
        setq = {q["question_id"]: q for q in MP.load_set("pooled_clip30", lv)} if nb else {}
        for i in nb:
            q = setq[i]
            L.append(f"- L{lv} {i} [{q.get('clip_id')}] ({q['subtype']}) {q['question']}  → {q['answer']}")
    txt = "\n".join(L)
    P.REPORT.mkdir(parents=True, exist_ok=True)
    out = P.REPORT / "clip_pyramid.md"
    out.write_text(txt); print(txt); print(f"\n-> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["select", "run", "report"])
    ap.add_argument("--n-clips", type=int, default=10)
    ap.add_argument("--n", type=int, default=30, help="每层题数")
    ap.add_argument("--select", default="program", choices=P.SELECT_MODES)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--no-probe", action="store_true")
    a = ap.parse_args()
    {"select": select, "run": run, "report": report}[a.cmd](a)


if __name__ == "__main__":
    main()
