"""EPIC-Sounds 上的纯声音三层金字塔 + answer-format 对照(experiments/answer_expansion.md 的外部数据验证)。

EPIC-Sounds 只有声音标注(类别 + 起止时间),没有 narration / 物体 / 3D,所以层级用纯声音的证据结构:
- L1 easy_sound          窗口里听得到哪种声音(单条证据)
- L2 low_sound_next      听到 X 之后紧接着是什么声音(锚点 + 邻居,两个信号;干扰项取**同窗口别处**的声音)
- L3 medium_count        某种声音响了几次(通听全窗口)
- L3 medium_sound_order  三种声音首次出现的先后(通听全窗口)
gold 全部由 EPIC-Sounds 时间戳程序推出,check_fact 在同一窗口重推。

    python3 epic_sounds.py build                 # 挖事实 + 组 mc / yn / ms / open / open_x + 裁 clip + mock 校准
    python3 epic_sounds.py report                # 汇总 results
"""
import argparse, collections, csv, hashlib, json, random, subprocess, sys
from pathlib import Path
import pconfig as P
import config as C
import facts as F
import phrase as PH
import formats as FM

ANN = Path("/mnt/data_new/epic-sounds-annotations")
VIDEOS = Path("/mnt/data_new/EPIC-KITCHENS")
WINDOWS = [("P02_133", 15.0, 45.0), ("P09_08", 45.0, 75.0)]
OUT = C.OUT / "epic_sounds"
NEVER = {"footstep"}
ABSENT_W = 30.0
LEVEL = {"easy_sound": 1, "low_sound_next": 2, "medium_count": 3, "medium_sound_order": 3}
TIER = {1: "Easy", 2: "Low", 3: "Medium"}
SLOTS = ["yn", "mc", "ms", "open", "open_x"]


def _ts(s):
    h, m, x = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(x)


_EV, _FREQ = {}, collections.Counter()


def events(video):
    """[(t_start, t_end, class, annotation_id)],按起点排序。train + validation 合并。"""
    if not _EV:
        for f in ("train", "validation"):
            for r in csv.DictReader((ANN / f"EPIC_Sounds_{f}.csv").open()):
                _EV.setdefault(r["video_id"], []).append(
                    (_ts(r["start_timestamp"]), _ts(r["stop_timestamp"]), r["class"], r["annotation_id"]))
                _FREQ[r["class"]] += 1
        for v in _EV.values():
            v.sort()
    return _EV[video]


def nameable(c):
    return c in C.SOUND_PHRASE and c not in C.SKIP_SOUNDS and c not in NEVER


def window(video, t0, t1):
    ev = events(video)
    touch = [e for e in ev if e[0] < t1 and e[1] > t0]
    inside = [e for e in touch if e[0] >= t0 and e[1] <= t1]
    return touch, inside


def absent_classes(video, t0, t1):
    near = {e[2] for e in events(video) if e[0] < t1 + ABSENT_W and e[1] > t0 - ABSENT_W}
    return sorted(c for c in _FREQ if nameable(c) and c not in near)


def _pick_absent(video, t0, t1, gold_cls, rng, n=3, exclude=()):
    """频次与 gold 相近者优先(全数据集计数的 1/3–3 倍);gold 是碰撞类时至多一个碰撞类。"""
    g = _FREQ[gold_cls] or 1
    ok = [c for c in absent_classes(video, t0, t1) if c != gold_cls and c not in exclude]
    near = [c for c in ok if g / 3 <= _FREQ[c] <= g * 3]
    far = [c for c in ok if c not in near]
    rng.shuffle(near); rng.shuffle(far)
    out, coll = [], 0
    for c in near + far:
        if "collision" in c and "collision" in gold_cls:
            if coll >= 1:
                continue
            coll += 1
        out.append(c)
        if len(out) == n:
            break
    return out


def _fact(video, t0, t1, subtype, kind, gold, distractors, evs, label=None, **extra):
    eids = [e[3] for e in evs]
    fid = hashlib.sha256(f"{video}|{subtype}|{gold}|{','.join(eids)}|{t0:.1f}".encode()).hexdigest()[:16]
    return {"fact_id": fid, "dataset": "epic_sounds", "video_id": video, "tier": TIER[LEVEL[subtype]],
            "subtype": subtype, "kind": kind, "t0": t0, "t1": t1, "gold": gold,
            "distractors": distractors, "evidence_event_ids": eids,
            "evidence_t": round(sum((e[0] + e[1]) / 2 for e in evs) / len(evs), 2),
            "_sound_label": label, **extra}


# ---------- 各子类的推导(挖掘与重推共用) ----------

def derive_next(video, t0, t1, x_cls):
    """X 在窗口内恰好一次且完整;其后(起点 >= X 终点、间隔 <= 5 s)第一个事件 N 类别不同、完整在窗口内,
    且 N 起点 ±0.5 s 内没有别的类别开始。返回 (X, N) 或 None。"""
    touch, inside = window(video, t0, t1)
    xs = [e for e in touch if e[2] == x_cls]
    if len(xs) != 1 or xs[0] not in inside:
        return None
    x = xs[0]
    after = [e for e in touch if e[0] >= x[1]]
    if not after:
        return None
    n = after[0]
    if n not in inside or n[2] == x_cls or not nameable(n[2]) or n[0] - x[1] > 5.0:
        return None
    if any(e is not n and e[2] != n[2] and abs(e[0] - n[0]) <= 0.5 for e in touch):
        return None
    if any(e is not x and e[0] < x[1] and e[1] > x[0] for e in touch):     # X 与别的声音重叠,锚点不干净
        return None
    return x, n


def derive_count(video, t0, t1, cls):
    touch, inside = window(video, t0, t1)
    es = [e for e in touch if e[2] == cls]
    if not (2 <= len(es) <= 6) or any(e not in inside for e in es):
        return None
    if any(b[0] - a[1] < 0.5 for a, b in zip(es, es[1:])):                 # 贴得太近会被听成一次
        return None
    return es


def first_heard(video, t0, t1):
    """{类别: 首次事件},只收该类别所有事件都完整落在窗口内的。"""
    touch, inside = window(video, t0, t1)
    out = {}
    for e in touch:
        if not nameable(e[2]):
            continue
        if any(x[2] == e[2] and x not in inside for x in touch):
            continue
        out.setdefault(e[2], e)
    return out


def mine(video, t0, t1):
    rng = random.Random(f"{P.SEED}|epic_sounds|{video}|{t0}")
    touch, inside = window(video, t0, t1)
    out = []
    present = sorted({e[2] for e in inside if nameable(e[2])})
    # L1
    for c in present:
        d = _pick_absent(video, t0, t1, c, rng)
        if len(d) == 3:
            e = next(x for x in inside if x[2] == c)
            out.append(_fact(video, t0, t1, "easy_sound", "SOUND", C.SOUND_PHRASE[c],
                             [C.SOUND_PHRASE[x] for x in d], [e], c))
    # L2
    in_win = sorted({e[2] for e in touch if nameable(e[2])})
    for c in present:
        r = derive_next(video, t0, t1, c)
        if not r:
            continue
        x, n = r
        hard = [k for k in in_win if k not in (c, n[2])]
        rng.shuffle(hard)
        d = hard[:3]
        if len(d) < 3:
            d += _pick_absent(video, t0, t1, n[2], rng, 3 - len(d), exclude=set(in_win))
        if len(d) == 3:
            out.append(_fact(video, t0, t1, "low_sound_next", "SOUND", C.SOUND_PHRASE[n[2]],
                             [C.SOUND_PHRASE[k] for k in d], [x, n], c, _next_cls=n[2],
                             _n_inwindow_distractors=sum(k in in_win for k in d)))
    # L3 计数
    for c in present:
        es = derive_count(video, t0, t1, c)
        if es:
            n = len(es)
            out.append(_fact(video, t0, t1, "medium_count", "COUNT", str(n),
                             F.count_distractors(n, rng), es, c))
    # L3 顺序:首次出现相隔 >= 1 s 的三种声音;按时间取不重叠的相邻三元组
    fh = sorted(first_heard(video, t0, t1).items(), key=lambda kv: kv[1][0])
    seq = []
    for c, e in fh:
        if not seq or e[0] - seq[-1][1][0] >= 1.0:
            seq.append((c, e))
    for i in range(0, len(seq) - 2, 3):
        tri = seq[i:i + 3]
        gold = " -> ".join(C.SOUND_PHRASE[c] for c, _ in tri)
        parts = gold.split(" -> ")
        perms = [" -> ".join(parts[j] for j in p)
                 for p in ([2, 0, 1], [1, 2, 0], [2, 1, 0], [0, 2, 1], [1, 0, 2])]
        rng.shuffle(perms)
        out.append(_fact(video, t0, t1, "medium_sound_order", "ORDER", gold, perms[:3],
                         [e for _, e in tri], None, _classes=[c for c, _ in tri]))
    return out


def check_fact(f):
    """在同一窗口上重推 gold 与干扰项合法性。返回错误列表。"""
    errs, v, t0, t1 = [], f["video_id"], f["t0"], f["t1"]
    touch, inside = window(v, t0, t1)
    ph2c = {p: c for c, p in C.SOUND_PHRASE.items()}
    absent = set(absent_classes(v, t0, t1))
    st = f["subtype"]
    if st == "easy_sound":
        c = f["_sound_label"]
        if not any(e[2] == c for e in inside) or C.SOUND_PHRASE[c] != f["gold"]:
            errs.append("gold 声音不在窗口内")
        errs += [f"干扰声音 '{d}' 在 ±{ABSENT_W:.0f}s 内响过" for d in f["distractors"] if ph2c[d] not in absent]
    elif st == "low_sound_next":
        r = derive_next(v, t0, t1, f["_sound_label"])
        if not r or C.SOUND_PHRASE[r[1][2]] != f["gold"]:
            errs.append("下一个声音重推不符")
        for d in f["distractors"]:
            if ph2c[d] in (f["_sound_label"], f.get("_next_cls")):
                errs.append(f"干扰声音 '{d}' 与锚点或 gold 同类")
    elif st == "medium_count":
        es = derive_count(v, t0, t1, f["_sound_label"])
        if not es or str(len(es)) != f["gold"]:
            errs.append("计数重推不符")
        if any(not d.isdigit() or d == f["gold"] for d in f["distractors"]):
            errs.append("计数干扰项非法")
    elif st == "medium_sound_order":
        fh = first_heard(v, t0, t1)
        cs = f["_classes"]
        if any(c not in fh for c in cs):
            errs.append("顺序题的声音不满足「全部事件在窗口内」")
        else:
            ts = [fh[c][0] for c in cs]
            if ts != sorted(ts) or any(b - a < 1.0 for a, b in zip(ts, ts[1:])):
                errs.append("顺序重推不符或间隔不足 1 s")
        parts = sorted(f["gold"].split(" -> "))
        errs += [f"排序干扰项 '{d}' 非法" for d in f["distractors"]
                 if sorted(d.split(" -> ")) != parts or d == f["gold"]]
    if len(set(f["distractors"] + [f["gold"]])) != 4:
        errs.append("选项不足 4 个互异")
    return errs


class _NoIx:
    """formats.check 只在 ms 的窗口声音补充陈述里用 ix;这里不用补充陈述。"""


def ensure_clip(video, t0, t1):
    out = C.CLIPS / "epic_sounds" / video / f"{int(t0*1000)}_{int(t1*1000)}.mp4"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    src = VIDEOS / video.split("_")[0] / "videos" / f"{video}.MP4"
    # 与 bench/clips.py 同一套编码参数(288² / 15 fps / aac 48k),只是源文件不同
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", str(src),
                    "-map", "0:v:0", "-map", "0:a:0", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "23", "-pix_fmt", "yuv420p", "-vf", f"scale={C.SIZE}:{C.SIZE}", "-r", "15",
                    "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-ar", "48000",
                    "-movflags", "+faststart", str(out)], check=True, capture_output=True)
    return out


def mc_item(f, qid, gold_idx, clip):
    rng = random.Random(qid)
    ds = list(f["distractors"]); rng.shuffle(ds)
    body = ds[:gold_idx] + [f["gold"]] + ds[gold_idx:]
    return {"question_id": qid, "dataset": "epic_sounds", "tier": f["tier"], "subtype": f["subtype"],
            "kind": f["kind"], "video_id": f["video_id"], "t0": f["t0"], "t1": f["t1"],
            "question": PH.offline_question(f), "answer": f["gold"],
            "options": [f"{'ABCD'[i]}. {b}" for i, b in enumerate(body)],
            "correct_option": "ABCD"[gold_idx], "_gold_idx": gold_idx,
            "_distractors": list(f["distractors"]), "_sound_label": f["_sound_label"],
            "evidence_event_ids": f["evidence_event_ids"], "evidence_t": f["evidence_t"],
            "fact_id": f["fact_id"], "phrasing": "template", "clip_path": str(clip),
            "level": LEVEL[f["subtype"]]}


def build():
    import evaluate
    from agent_mock_fmt import MockFmtAgent
    sets = {(l, s): [] for l in (1, 2, 3) for s in SLOTS}
    rejected, n = [], collections.Counter()
    for video, t0, t1 in WINDOWS:
        clip = ensure_clip(video, t0, t1)
        facts = mine(video, t0, t1)
        facts = [f for f in facts if not (check_fact(f) and rejected.append(
            {"fact": f["fact_id"], "subtype": f["subtype"], "errors": check_fact(f)}) is None)]
        rng = random.Random(f"{P.SEED}|epic_sounds|fmt|{video}")
        for f in sorted(facts, key=lambda f: (f["subtype"], f["fact_id"])):
            L, st = LEVEL[f["subtype"]], f["subtype"]
            i = n[st]; n[st] += 1
            base = mc_item(f, f"es_{video}_{int(t0)}_{st}_{i:02d}", i % 4, clip)
            items = {"mc": dict(base, fmt="mc", base_id=base["question_id"]),
                     "yn": FM.build_yn(base, f, i % 2 == 0, rng)}
            sibs = [g for g in facts if g["fact_id"] != f["fact_id"]]
            ms, _ = FM.build_ms(base, f, [1, 2, 3][i % 3], sibs, rng, ix=None)
            if ms:
                items["ms"] = ms
            for slot in ("open", "open_x"):
                fmt = FM.slot_format(slot, st)
                items[slot] = (FM.build_open(base, f, fmt) if fmt.startswith("open")
                               else FM.build_tf4(base, f, fmt))
            for slot, it in items.items():
                if "question" not in it:
                    it["question"] = it.get("statement") or ("Which of these statements are true? " +
                                                              " | ".join(it["statements"]))
                errs = []
                if slot != "mc":
                    FM.check(_NoIx(), it, f, errs)
                if errs:
                    rejected.append({"question_id": it["question_id"], "errors": errs}); continue
                sets[(L, slot)].append(it)
    (OUT / "sets").mkdir(parents=True, exist_ok=True)
    (OUT / "calib").mkdir(parents=True, exist_ok=True)
    for (L, slot), items in sorted(sets.items()):
        sd = {"arm": "epic_sounds", "scope": "pooled", "level": L, "slot": slot, "n": len(items),
              "windows": WINDOWS, "fmt_counts": dict(collections.Counter(i["fmt"] for i in items)),
              "subtype_counts": dict(collections.Counter(i["subtype"] for i in items)), "questions": items}
        (OUT / "sets" / f"L{L}_{slot}.json").write_text(json.dumps(sd, ensure_ascii=False, indent=1))
        cal = {}
        for name, oracle in (("oracle", True), ("random", False)):
            jl = OUT / "calib" / f"L{L}_{slot}_{name}.jsonl"
            jl.unlink(missing_ok=True)
            c, k, _ = evaluate.run_set(MockFmtAgent(oracle), name, sd, jl, mode="blind")
            cal[name] = f"{c}/{k}"
        assert cal["oracle"].split("/")[0] == cal["oracle"].split("/")[1], (L, slot, cal)
        print(f"L{L} {slot:7s} {len(items):2d} 题 {sd['subtype_counts']} {sd['fmt_counts']} 校准 {cal}")
    (OUT / "sets" / "rejected.json").write_text(json.dumps(rejected, ensure_ascii=False, indent=1))
    print("拒绝", len(rejected), rejected[:3])


def report():
    lines = ["# EPIC-Sounds 纯声音三层 × answer format\n",
             f"片段:{WINDOWS};gold 由 EPIC-Sounds 时间戳程序推出。\n"]
    rep = []
    for agent in ("gemini", "qwen"):
        for mode in ("clip30", "blind"):
            d = OUT / "results" / agent / mode
            if not d.exists():
                continue
            lines += [f"\n## {agent} × {mode}\n", "| level | " + " | ".join(SLOTS) + " |",
                      "|---|" + "---|" * len(SLOTS)]
            for L in (1, 2, 3):
                cells = []
                for slot in SLOTS:
                    f = d / f"L{L}_{slot}.jsonl"
                    rs = [json.loads(l) for l in f.open() if l.strip()] if f.exists() else []
                    rs = [r for r in rs if not r.get("error")]
                    pend = sum(r.get("score_by") == "pending" for r in rs)
                    if not rs:
                        cells.append("—"); continue
                    c = sum(bool(r["correct"]) for r in rs)
                    ch = sum(P.FMT_CHANCE[r.get("fmt") or "mc"] for r in rs) / len(rs)
                    acc = c / max(1, len(rs) - pend)
                    rep.append({"agent": agent, "mode": mode, "level": L, "slot": slot, "n": len(rs),
                                "correct": c, "pending": pend, "acc": round(acc, 3), "chance": round(ch, 3)})
                    cells.append(f"{acc:.0%} ({c}/{len(rs) - pend}, chance {ch:.0%})" +
                                 (f" +{pend} 待判" if pend else ""))
                lines.append(f"| L{L} | " + " | ".join(cells) + " |")
    (OUT / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "report"])
    a = ap.parse_args()
    build() if a.cmd == "build" else report()
