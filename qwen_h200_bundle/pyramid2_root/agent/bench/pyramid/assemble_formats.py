"""answer-format 对照试验的组卷:从已有 mc 题套(pooled_clip30 每层 100 题)按子类均衡抽 N 题作基题,
对每道基题生成 yn / ms / open(或 tf4)/ open_x(或 tf4_x)四种格式;mc 直接复用基题与其已有结果。

    PYRAMID_SEED=43 python3 assemble_formats.py            # 生成 + verify + mock 校准
    PYRAMID_SEED=43 python3 assemble_formats.py --n 40 --base pooled_clip30

产物:P.SETS/formats/L{l}_{fmt}.json(fmt ∈ yn, ms, open, open_x;open 文件里按子类混有 open / tf4 项)
      P.SETS/formats/base_ids.json(基题 id,供跨格式配对分析)
      P.STATE/calib/formats/*.jsonl(mock oracle / random 校准)
"""
import argparse, collections, hashlib, json, random
import pconfig as P
import facts as F
import phrase as PH
import verify as V
import formats as FM
import evaluate
from timeline_index import TimelineIndex
from agent_mock_fmt import MockFmtAgent

_IX = {}


def ix_of(v):
    if v not in _IX:
        _IX[v] = TimelineIndex(v)
    return _IX[v]


def _sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def sample_base(qs, n):
    """按子类轮转、子类内按 sha(qid) 排序,抽 n 题。"""
    by = collections.defaultdict(list)
    for q in qs:
        by[q["subtype"]].append(q)
    for v in by.values():
        v.sort(key=lambda q: _sha(q["question_id"]))
    out = []
    while len(out) < n and any(by.values()):
        for st in sorted(by):
            if by[st] and len(out) < n:
                out.append(by[st].pop(0))
    return out


def _template_item(f):
    """把一条 fact 按模板组成 mc 题,只为跑 verify.check(兄弟 fact 的健全性)。"""
    opts = [f["gold"]] + list(f["distractors"])
    it = {"question_id": "sib_" + f["fact_id"], "question": PH.offline_question(f),
          "answer": f["gold"], "options": [f"{'ABCD'[i]}. {o}" for i, o in enumerate(opts)],
          "_gold_idx": 0, "_distractors": list(f["distractors"]), "kind": f["kind"],
          "t0": f["t0"], "t1": f["t1"], "evidence_event_ids": f["evidence_event_ids"],
          "subtype": f["subtype"]}
    if f.get("windows"):
        it["windows"] = f["windows"]
    return it


def load_facts():
    pool = F.load_all()
    by_id, by_win = {}, collections.defaultdict(list)
    for fs in pool.values():
        for f in fs:
            by_id[f["fact_id"]] = f
            if not f.get("windows"):
                by_win[(f["video_id"], round(f["t0"], 2), round(f["t1"], 2))].append(f)
    return by_id, by_win


_SIB_OK = {}


def siblings(fact, by_win):
    """同窗口、非本 fact、过 verify 的兄弟 fact(同子类也可:真陈述互不矛盾)。"""
    out = []
    for f in by_win.get((fact["video_id"], round(fact["t0"], 2), round(fact["t1"], 2)), []):
        if f["fact_id"] == fact["fact_id"]:
            continue
        if f["fact_id"] not in _SIB_OK:
            try:
                _SIB_OK[f["fact_id"]] = not V.check(ix_of(f["video_id"]), _template_item(f), f)
            except Exception:
                _SIB_OK[f["fact_id"]] = False
        if _SIB_OK[f["fact_id"]]:
            out.append(f)
    return out


def build_level(level, base_qs, by_id, by_win, rng):
    sets = {fmt: [] for fmt in ("yn", "ms", "open", "open_x")}
    rejected, stats = [], collections.defaultdict(collections.Counter)
    yn_flip = collections.Counter()
    base_qs = sorted(base_qs, key=lambda q: _sha(q["question_id"]))
    for i, q in enumerate(base_qs):
        fact = by_id.get(q["fact_id"])
        if fact is None:
            # 题套建于 facts 缓存重建之前(seed43 L3 的 14 道计数题):fact_id 不含干扰项,
            # 题里带的 gold / 干扰项 / 证据本就是 verify 过的,按题重建 fact 即可
            fact = {k: q[k] for k in ("fact_id", "video_id", "tier", "subtype", "kind", "t0", "t1",
                                      "evidence_event_ids", "evidence_t", "_sound_label") if k in q}
            fact.update({"gold": q["answer"], "distractors": list(q["_distractors"])})
            if q.get("windows"):
                fact["windows"] = q["windows"]
            stats["rebuilt_fact"][q["subtype"]] += 1
        ix = ix_of(q["video_id"])
        q = dict(q, level=level)
        items = []
        # yn:按子类交替 yes / no
        truth = yn_flip[q["subtype"]] % 2 == 0
        yn_flip[q["subtype"]] += 1
        items.append(FM.build_yn(q, fact, truth, rng))
        # ms:目标 k 按 1,2,3 轮转;兄弟不足自动降
        k_target = [1, 2, 3][i % 3]
        ms, k = FM.build_ms(q, fact, k_target, siblings(fact, by_win), rng, ix=ix)
        if ms:
            stats["ms_k"][k] += 1
            items.append(ms)
        else:
            rejected.append({"question_id": q["question_id"] + "#ms", "errors": ["ms 凑不齐 4 条陈述"]})
        for slot in ("open", "open_x"):
            fmt = FM.slot_format(slot, q["subtype"])
            it = FM.build_open(q, fact, fmt) if fmt.startswith("open") else FM.build_tf4(q, fact, fmt)
            it["_slot"] = slot
            items.append(it)
        for it in items:
            # yn / ms 没有 question 字段;evaluate 的结果行要记题面,给一个可读版本
            if "question" not in it:
                it["question"] = it.get("statement") or ("Which of these statements are true? " +
                                                          " | ".join(it["statements"]))
            errs = V.check(ix, it, fact)
            if errs:
                rejected.append({"question_id": it["question_id"], "errors": errs})
                continue
            slot = it.pop("_slot", it["fmt"])
            sets[slot].append(it)
            stats[slot][it["fmt"]] += 1
            stats["subtype"][it["subtype"]] += 1
    return sets, rejected, stats


def calibrate(level, fmt, set_path, setdata):
    cdir = P.STATE / "calib" / "formats"
    cdir.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, oracle in (("mock_oracle", True), ("mock", False)):
        jl = cdir / f"L{level}_{fmt}_{name}.jsonl"
        if jl.exists():
            jl.unlink()
        c, n, _ = evaluate.run_set(MockFmtAgent(oracle=oracle), name, setdata, jl, mode="blind")
        out[name] = {"n_correct": c, "n": n}
    assert out["mock_oracle"]["n_correct"] == out["mock_oracle"]["n"], \
        f"mock_oracle 未达 100% —— 格式题结构有 bug,停:{set_path}"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=P.N_FORMAT_PER_LEVEL)
    ap.add_argument("--base", default="pooled_clip30", help="基题所在的题套 key(P.SETS/<base>/pooled/L*.json)")
    ap.add_argument("--levels", default="1,2,3,4")
    ap.add_argument("--no-calib", action="store_true")
    a = ap.parse_args()
    out_dir = P.SETS / "formats"
    out_dir.mkdir(parents=True, exist_ok=True)
    by_id, by_win = load_facts()
    base_ids = {}
    for level in [int(x) for x in a.levels.split(",")]:
        src = P.SETS / a.base / "pooled" / f"L{level}.json"
        qs = json.loads(src.read_text())["questions"]
        base = sample_base(qs, a.n)
        base_ids[level] = [q["question_id"] for q in base]
        rng = random.Random(f"{P.SEED}|formats|L{level}")
        sets, rejected, stats = build_level(level, base, by_id, by_win, rng)
        print(f"L{level}: 基题 {len(base)}  子类 {dict(collections.Counter(q['subtype'] for q in base))}")
        for slot, items in sets.items():
            path = out_dir / f"L{level}_{slot}.json"
            setdata = {"arm": "formats", "scope": "pooled", "level": level, "slot": slot,
                       "base_set": str(src), "n": len(items), "seed": P.SEED,
                       "fmt_counts": dict(stats[slot]),
                       "yn_yes_frac": (sum(i["_yn_truth"] == "yes" for i in items) / len(items)
                                       if slot == "yn" and items else None),
                       "ms_k_hist": dict(stats["ms_k"]) if slot == "ms" else None,
                       "questions": items}
            path.write_text(json.dumps(setdata, ensure_ascii=False, indent=1))
            line = f"  {slot:7s} {len(items):3d} 题  {dict(stats[slot])}"
            if slot == "yn":
                line += f"  yes 占比 {setdata['yn_yes_frac']:.2f}"
            if slot == "ms":
                line += f"  k 分布 {setdata['ms_k_hist']}"
            if not a.no_calib and items:
                cal = calibrate(level, slot, path, setdata)
                line += (f"  校准 oracle {cal['mock_oracle']['n_correct']}/{cal['mock_oracle']['n']}"
                         f" random {cal['mock']['n_correct']}/{cal['mock']['n']}")
            print(line)
        (out_dir / f"L{level}_rejected.json").write_text(json.dumps(rejected, ensure_ascii=False, indent=1))
        if rejected:
            print(f"  拒绝 {len(rejected)}:", collections.Counter(e for r in rejected for e in r["errors"]))
        if stats["rebuilt_fact"]:
            print(f"  按题重建 fact:{dict(stats['rebuilt_fact'])}")
    # 只跑部分层时保留其他层已有的 base_ids(曾因 --levels 3 把 L1/L2/L4 的记录覆盖掉)
    bp = out_dir / "base_ids.json"
    old = json.loads(bp.read_text()) if bp.exists() else {}
    old.update({str(k): v for k, v in base_ids.items()})
    bp.write_text(json.dumps(old, indent=1))


if __name__ == "__main__":
    main()
