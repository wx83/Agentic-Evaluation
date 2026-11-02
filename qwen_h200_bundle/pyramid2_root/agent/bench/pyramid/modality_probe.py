#!/usr/bin/env python3
"""L2 模态探针(2026-10-10):同一道题、同一 30 s 窗口,四种输入条件,量化「答案到底靠的是画面还是声音」。

动机:静音消融(1009_qwen_omni_vs_gemini.md §5)只证明了「去掉声音不掉分」,即画面足够;
但用户观察到 Gemini 在同时给音视频时会**选择性只读音频**。要测这个,得补上另外两条臂:

  av      原 clip(音+视)                       —— 基线
  v_only  同 clip、音轨换等长静音(evaluate.muted)  —— 只能看
  a_only  同 clip、画面换等长纯黑、音轨原样        —— 只能听
  a_swap  原画面 + **另一道题的 clip 的音轨**(同一视频、窗口不重叠、答案不同)
          —— 音画冲突:答案跟着画面走还是跟着声音走

逐题判定(av 条件答对的题):
  V-sufficient  v_only 也对           ;A-sufficient  a_only 也对
  needs-both    v_only 错且 a_only 错  —— L2「整体事件多模态理解」真正想要的题
  audio-led     a_swap 时答案落到 donor 题的答案上 —— 「选择性读音频」的直接证据

结果按后端、层分子目录:
  <POUT>/results/modality_probe/{nv,google}/gemini/L<level>/<cond>.jsonl   (+ logs/、swap_map.json)
两个后端跑的是同一个模型(gemini-3.5-flash,temp 0),NV vs Google 的一致率顺便作为网关等价性检查。

用法(seed 43 的 pooled_clip30 L2,100 题 × 4 条件):
  GEM=/home/weihanxu/miniconda3/envs/gemini/bin/python
  PYRAMID_SEED=43 GEMINI_BACKEND=nv     $GEM modality_probe.py run            # NV(默认后端)
  PYRAMID_SEED=43 GEMINI_BACKEND=google $GEM modality_probe.py run            # Google 直连
  PYRAMID_SEED=43 python3 modality_probe.py report                            # -> report/modality_probe_L<level>.md
可选:--conds av,v_only --limit 5 --level 2 --arm pooled_clip30
"""
import argparse, json, random, subprocess, sys
from pathlib import Path
import pconfig as P

CONDS = ["av", "v_only", "a_only", "a_swap"]
BACKENDS = ["nv", "google"]


def out_dir(backend=None, level=2, agent_dir=None):
    return P.POUT / "results" / "modality_probe" / (backend or P.BACKEND) / (agent_dir or P.AGENT_DIR) / f"L{level}"


def load_set(arm, level):
    f = P.SETS / arm / "pooled" / f"L{level}.json"
    d = json.loads(f.read_text())
    return d["questions"]


# ---------- 媒体变体(内容寻址:文件名带条件后缀,存在即复用)----------
def _probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout.strip().split(",")
    return int(out[0]), int(out[1]), out[2]


def _run(cmd, out):
    """临时文件带 pid:两个后端并行跑时同时生成同一变体,同名 tmp 会互相 rename 掉对方的。"""
    import os
    tmp = out.with_name(f"{out.stem}.tmp{os.getpid()}{out.suffix}")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", *cmd, str(tmp)], check=True)
    if out.exists():            # 对方已经生成好了,用它的
        tmp.unlink(missing_ok=True)
    else:
        tmp.rename(out)


def base_clip(q):
    import clips
    return clips.ensure_clip(q["video_id"], q["t0"], q["t1"])


def v_only(q):
    import evaluate
    return evaluate.muted(base_clip(q))


def a_only(q):
    src = base_clip(q)
    out = src.with_name(src.stem + "_aonly" + src.suffix)
    if not out.exists():
        w, h, fps = _probe(src)
        # 画面换成等长纯黑(保留分辨率/帧率,容器与基线一致),音轨原样拷贝
        _run(["-i", str(src), "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={fps}",
              "-map", "1:v", "-map", "0:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
              "-c:a", "copy", "-shortest"], out)
    return out


def _opts(q):
    return [o.split(". ", 1)[-1].strip().lower() for o in q["options"]]


def pick_donors(qs, seed):
    """每题挑一个 donor(窗口不重叠、答案不同),优先级:
    同一视频且 donor 答案正好是本题的干扰项(v2,这样「跟声音走」才有落点,seed43 L2 有 69/100 题可满足)
    > 任意视频且答案在选项里 > 同一视频 > 任意。确定性。"""
    rng = random.Random(seed)
    donors = {}
    for q in qs:
        cands = [d for d in qs if d["question_id"] != q["question_id"] and d["answer"] != q["answer"]
                 and abs(d["t0"] - q["t0"]) >= (q["t1"] - q["t0"])]
        same = [d for d in cands if d["video_id"] == q["video_id"]]
        in_opt = [d for d in cands if d["answer"].lower() in _opts(q)]
        same_in = [d for d in same if d in in_opt]
        pool = same_in or in_opt or same or cands
        d = rng.choice(pool)
        donors[q["question_id"]] = {"donor_qid": d["question_id"], "donor_video": d["video_id"],
                                    "donor_t0": d["t0"], "donor_t1": d["t1"], "donor_answer": d["answer"],
                                    "donor_subtype": d["subtype"], "same_video": d["video_id"] == q["video_id"],
                                    "donor_in_options": d in in_opt}
    return donors


def a_swap(q, donor):
    import clips
    src = base_clip(q)
    dsrc = clips.ensure_clip(donor["donor_video"], donor["donor_t0"], donor["donor_t1"])
    tag = f"{donor['donor_video'][:3]}_{int(donor['donor_t0'] * 1000)}"
    out = src.with_name(src.stem + f"_swap{tag}" + src.suffix)
    if not out.exists():
        _run(["-i", str(src), "-i", str(dsrc), "-map", "0:v", "-map", "1:a",
              "-c:v", "copy", "-c:a", "aac", "-shortest"], out)
    return out


def build_variants(qs, conds, donors):
    from concurrent.futures import ThreadPoolExecutor
    fn = {"av": base_clip, "v_only": v_only, "a_only": a_only,
          "a_swap": lambda q: a_swap(q, donors[q["question_id"]])}
    paths = {}
    for c in conds:
        # clip 模式下多道题共用同一窗口:按唯一 (video, t0, t1[, donor]) 去重后再并行生成,
        # 否则两个线程同时写同一个 tmp 文件会互相 rename 掉对方的
        key = lambda q: (q["video_id"], q["t0"], q["t1"]) + ((donors[q["question_id"]]["donor_qid"],) if c == "a_swap" else ())
        uniq = {}
        for q in qs:
            uniq.setdefault(key(q), q)
        with ThreadPoolExecutor(6) as ex:
            res = dict(zip(uniq, ex.map(fn[c], uniq.values())))
        paths[c] = {q["question_id"]: str(res[key(q)]) for q in qs}
        print(f"  [{c}] {len(uniq)} 个 clip 就绪({len(qs)} 题)", flush=True)
    return paths


# ---------- run ----------
def run(a):
    import runlog, evaluate
    runlog.start(f"modality_probe_{P.BACKEND}_{P.AGENT_DIR}", agent="gemini")
    qs = load_set(a.arm, a.level)
    if a.limit:
        qs = qs[:a.limit]
    conds = a.conds.split(",")
    od = out_dir(level=a.level); od.mkdir(parents=True, exist_ok=True)
    donors = pick_donors(load_set(a.arm, a.level), P.SEED)      # donor 永远从全集挑,limit 不影响
    (od / "swap_map.json").write_text(json.dumps(donors, ensure_ascii=False, indent=1))
    print(f"[modality_probe] backend={P.BACKEND} agent_model={P.AGENT_MODEL} key_id={__import__('gemini_io').key_id()} "
          f"set={a.arm}/L{a.level} n={len(qs)} conds={conds} -> {od}", flush=True)
    paths = build_variants(qs, conds, donors)
    agent = evaluate.make_agent("gemini")
    for c in conds:
        setdata = {"arm": f"modality_probe_{c}", "scope": "pooled", "level": a.level,
                   "questions": [{**q, "clip_path": paths[c][q["question_id"]]} for q in qs]}
        evaluate.run_set(agent, "gemini", setdata, od / f"{c}.jsonl", mode="clip30")


# ---------- report ----------
def _rows(backend, cond, level=2):
    f = out_dir(backend, level) / f"{cond}.jsonl"
    if not f.exists():
        return {}
    rows = [json.loads(l) for l in f.open() if l.strip()]
    return {r["question_id"]: r for r in rows if not r.get("error")}


def _mcnemar(b, c):
    """精确二项检验(配对):b = 只在 A 对, c = 只在 B 对。"""
    from math import comb
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(k + 1)) / 2 ** n * 2
    return min(1.0, p)


def _pct(c, n):
    return f"{100 * c / n:.0f}% ({c}/{n})" if n else "—"


def report(a):
    qs = {q["question_id"]: q for q in load_set(a.arm, a.level)}
    donors = {}
    for b in BACKENDS:
        f = out_dir(b, a.level) / "swap_map.json"
        if f.exists():
            donors = json.loads(f.read_text()); break
    L = [f"# L{a.level} 模态探针(seed {P.SEED},{a.arm} L{a.level},gemini-3.5-flash,temp 0)", "",
         "条件:av 原 clip;v_only 静音;a_only 黑屏保留音轨;a_swap 原画面 + 另一题的音轨(音画冲突)。",
         "括号是「对 / 题数」;报错行不计入。p 为配对 McNemar 精确检验(与 av 比)。", ""]
    data = {b: {c: _rows(b, c, a.level) for c in CONDS} for b in BACKENDS}
    # 底线:同一套题的 blind(不给任何输入)历史结果(Google 直连,results/pooled_clip30_blind)
    bf = P.POUT / "results" / f"{a.arm}_blind" / "gemini" / f"L{a.level}.jsonl"
    blind = {r["question_id"]: r for r in (json.loads(l) for l in bf.open() if l.strip())
             if not r.get("error")} if bf.exists() else {}
    if blind:
        L += [f"底线 blind(不给输入,历史结果 {bf.relative_to(P.POUT)}):"
              f"{_pct(sum(bool(r['correct']) for r in blind.values()), len(blind))}", ""]
    for b in BACKENDS:
        R = data[b]
        if not R["av"]:
            L += [f"## 后端 {b}:无结果", ""]; continue
        subtypes = sorted({r["subtype"] for r in R["av"].values()})
        L += [f"## 后端 {b}", "", "### 1. 各条件正确率", "",
              "| subtype | n | blind | av | v_only | a_only | a_swap | Δv_only (p) | Δa_only (p) | Δa_swap (p) |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for st in subtypes + ["ALL"]:
            ids = [i for i, r in R["av"].items() if st == "ALL" or r["subtype"] == st]
            bl = [i for i in ids if i in blind]
            cell, delta = [_pct(sum(bool(blind[i]["correct"]) for i in bl), len(bl))], []
            for c in CONDS:
                common = [i for i in ids if i in R[c]]
                k = sum(bool(R[c][i]["correct"]) for i in common)
                cell.append(_pct(k, len(common)))
                if c != "av" and common:
                    b1 = sum(R["av"][i]["correct"] and not R[c][i]["correct"] for i in common)
                    c1 = sum(R[c][i]["correct"] and not R["av"][i]["correct"] for i in common)
                    acc_av = sum(bool(R["av"][i]["correct"]) for i in common) / len(common)
                    delta.append(f"{100 * (k / len(common) - acc_av):+.0f} pp (p={_mcnemar(b1, c1):.2f})")
                elif c != "av":
                    delta.append("—")
            L.append(f"| {st} | {len(ids)} | " + " | ".join(cell) + " | " + " | ".join(delta) + " |")
        # 逐题模态判定
        if R["v_only"] and R["a_only"]:
            L += ["", "### 2. 逐题判定(以 av 答对的题为分母)", "",
                  "| subtype | av 对 | V-sufficient | A-sufficient | both-sufficient | needs-both | 只靠 av 对且 a_swap 仍对 |",
                  "|---|---|---|---|---|---|---|"]
            for st in subtypes + ["ALL"]:
                ids = [i for i, r in R["av"].items() if (st == "ALL" or r["subtype"] == st) and r["correct"]
                       and i in R["v_only"] and i in R["a_only"]]
                v = [i for i in ids if R["v_only"][i]["correct"]]
                aa = [i for i in ids if R["a_only"][i]["correct"]]
                both = [i for i in ids if i in v and i in aa]
                nb = [i for i in ids if i not in v and i not in aa]
                sw = [i for i in nb if i in R["a_swap"] and R["a_swap"][i]["correct"]]
                L.append(f"| {st} | {len(ids)} | {_pct(len(v), len(ids))} | {_pct(len(aa), len(ids))} | "
                         f"{_pct(len(both), len(ids))} | {_pct(len(nb), len(ids))} | {_pct(len(sw), len(nb))} |")
            nb_all = [i for i, r in R["av"].items() if r["correct"] and i in R["v_only"] and i in R["a_only"]
                      and not R["v_only"][i]["correct"] and not R["a_only"][i]["correct"]]
            L += ["", f"needs-both 题 id({len(nb_all)}):" + ", ".join(sorted(nb_all)), ""]
        # 音画冲突:答案跟谁走
        if R["a_swap"] and donors:
            L += ["### 3. 音画冲突(a_swap):答案跟画面还是跟声音", "",
                  "donor 答案若在本题选项里才能判「跟声音」(v2 donor 优先挑答案正好是本题干扰项的同视频片段)。"
                  "对 spatial 子类,换来的音轨本身不编码答案,此列只反映抗噪;sound_movement 子类才是真正的冲突测试。", "",
                  "| subtype | n(donor 在选项中) | 跟画面(=gold) | 跟声音(=donor) | 其他 | av 对→swap 错 |",
                  "|---|---|---|---|---|---|"]
            for st in subtypes + ["ALL"]:
                ids = [i for i, r in R["av"].items() if (st == "ALL" or r["subtype"] == st) and i in R["a_swap"]]
                vis = aud = oth = 0; n_in = 0
                flip = sum(R["av"][i]["correct"] and not R["a_swap"][i]["correct"] for i in ids)
                for i in ids:
                    d = donors.get(i, {}); r = R["a_swap"][i]
                    opts = [o.split(". ", 1)[-1].strip().lower() for o in r["options"]]
                    if d.get("donor_answer", "").lower() not in opts:
                        continue
                    n_in += 1
                    pi = r.get("parsed_index")
                    if pi == r["gold_index"]: vis += 1
                    elif pi is not None and opts[pi] == d["donor_answer"].lower(): aud += 1
                    else: oth += 1
                L.append(f"| {st} | {n_in} | {_pct(vis, n_in)} | {_pct(aud, n_in)} | {_pct(oth, n_in)} | {flip}/{len(ids)} |")
            L.append("")
    # 后端一致性
    if data["nv"]["av"] and data["google"]["av"]:
        L += ["## NV vs Google 一致性(同模型、temp 0;逐题 parsed_index 相同的比例)", "",
              "| cond | n | 同答案 | acc nv | acc google |", "|---|---|---|---|---|"]
        for c in CONDS:
            common = [i for i in data["nv"][c] if i in data["google"][c]]
            same = sum(data["nv"][c][i]["parsed_index"] == data["google"][c][i]["parsed_index"] for i in common)
            an = sum(bool(data["nv"][c][i]["correct"]) for i in common)
            ag = sum(bool(data["google"][c][i]["correct"]) for i in common)
            L.append(f"| {c} | {len(common)} | {_pct(same, len(common))} | {_pct(an, len(common))} | {_pct(ag, len(common))} |")
        L.append("")
    txt = "\n".join(L)
    P.REPORT.mkdir(parents=True, exist_ok=True)
    outf = P.REPORT / f"modality_probe_L{a.level}.md"
    outf.write_text(txt)
    print(txt); print(f"\n-> {outf}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "report"])
    ap.add_argument("--arm", default="pooled_clip30")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--conds", default=",".join(CONDS))
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    (run if a.cmd == "run" else report)(a)


if __name__ == "__main__":
    main()
