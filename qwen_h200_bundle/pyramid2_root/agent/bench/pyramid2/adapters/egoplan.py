"""EgoPlan-Bench2(benchmarks_1011/raw/egoplan2/EgoPlan-Bench2.json,Ego4D 视频,30 fps)-> evidence + 官方 4 选 1 作 seed item。
每条样本 = 一个 goal 段 [task_start_frame, current_observation_frame];plan = 已完成步骤(observed)+ gold 下一步(answer_only)。
  task_segment      goal + 步骤表(不含下一步)                     source egoplan.bench2
  task_step × n     已完成步骤(verb / noun / nouns)                 source egoplan.bench2
  task_step (next)  gold 下一步 + 4 选项,answer_only,[obs, obs+1 s]   source egoplan.bench2
  action_narration  已完成步骤再作 narration(锚在 narration 的 skill 用) source egoplan.progress_narration
抽样:python3 -m adapters.egoplan select --n 20 --seed 1014  -> data/egoplan_samples.json(adapter 只读这个文件)。
"""
import json, random, re, collections, argparse, os
from pathlib import Path
import p2config as P
from ids import evidence_id
from adapters.base import Adapter, record, rel_source

DS = "egoplan"
FPS = 30.0
RAW2 = Path(P.SOURCES["benchmarks"]) / "raw" / "egoplan2" / "EgoPlan-Bench2.json"
VIDEOS = Path("/mnt/data_new/ego4d/v2/full_scale")
SAMPLES = P.DATA / "egoplan_samples.json"


def samples_paths():
    """adapter 读的样本文件:主文件 data/egoplan_samples.json + 环境变量 EGOPLAN_SAMPLES 里的额外文件(逗号分隔;10-21 pilot 用)。
    主文件永远在内,所以 build_data 全量重建不会丢 20 条主样本。"""
    out = [SAMPLES]
    for x in (os.environ.get("EGOPLAN_SAMPLES") or "").split(","):
        if x.strip() and Path(x.strip()) not in out:
            out.append(Path(x.strip()))
    return out


def load_samples():
    seen, rows = set(), []
    for sp in samples_paths():
        if not sp.exists(): continue
        for s in json.loads(sp.read_text())["samples"]:
            if s["sample_id"] not in seen:
                seen.add(s["sample_id"]); rows.append(s)
    return rows
PREPS = {"on", "in", "into", "with", "from", "onto", "to", "of", "off", "under", "over", "at", "for", "out", "up", "down"}
SOURCE = "egoplan.bench2"
SOURCE_NARR = "egoplan.progress_narration"


def split_narration(text):
    """'put dough on table' -> verb 'put', nouns ['dough', 'table'](按介词切,去冠词)。"""
    toks = [t for t in re.findall(r"[a-z0-9'-]+", (text or "").lower())]
    if not toks:
        return None, []
    verb, rest = toks[0], toks[1:]
    nouns, cur = [], []
    for t in rest:
        if t in PREPS or t in ("the", "a", "an", "and", "then"):
            if cur: nouns.append(" ".join(cur)); cur = []
            continue
        cur.append(t)
    if cur: nouns.append(" ".join(cur))
    return verb, [n for n in nouns if n]


def uid_of(r):
    return r["sample_id"].rsplit("_", 1)[0]


def derive(r):
    """原记录 -> 加秒数的样本 dict。"""
    uid = uid_of(r)
    t0, t1 = r["task_start_frame"] / FPS, r["current_observation_frame"] / FPS
    steps = []
    for k, s in enumerate(r["task_progress_metadata"]):
        a, b = s["start_frame"] / FPS, max(s["stop_frame"], s["start_frame"]) / FPS
        verb, nouns = split_narration(s["narration_text"])
        steps.append({"idx": k + 1, "text": s["narration_text"], "t0": round(a, 3), "t1": round(b, 3), "verb": verb, "nouns": nouns})
    choices = {L: r[f"choice_{L.lower()}"] for L in "ABCD"}
    return {"sample_id": r["sample_id"], "video_id": uid, "goal": r["task_goal"], "scenario": r.get("scenario"), "domain": r.get("domain"),
            "t0": round(t0, 3), "t1": round(t1, 3), "steps": steps,
            "next_action": {"text": r["answer"], "choices": choices, "gold_letter": r["golden_choice_idx"]},
            "raw_index": r.get("_raw_index")}


def select(n=20, seed=1014, min_steps=3, min_dur=20.0, max_dur=300.0, out=SAMPLES, exclude_videos=()):
    """exclude_videos(10-21):另抽样本时排除已在其它样本文件里的视频(默认排除 data/egoplan_samples.json 的 20 条)。"""
    import media as M
    raw = json.loads(RAW2.read_text())
    for i, r in enumerate(raw):
        r["_raw_index"] = i
    excl = set(exclude_videos or ())
    cands = []
    for r in raw:
        uid = uid_of(r)
        if uid in P.EGO4D_VIDEOS or uid in excl:        # 避免和 ego4d adapter 的 source_video 行重复 / 与其它样本文件重复
            continue
        dur = (r["current_observation_frame"] - r["task_start_frame"]) / FPS
        if len(r["task_progress_metadata"]) < min_steps or not (min_dur <= dur <= max_dur):
            continue
        if not (VIDEOS / f"{uid}.mp4").exists():
            continue
        cands.append(r)
    rng = random.Random(seed)
    rng.shuffle(cands)
    by_sc = collections.defaultdict(list)
    for r in cands:
        by_sc[r.get("scenario") or "?"].append(r)
    order = sorted(by_sc)                              # scenario 轮转,每视频 1 条,要求有音轨
    rng.shuffle(order)
    picked, used_vid, probed = [], set(), {}
    while len(picked) < n and any(by_sc.values()):
        for sc in order:
            if len(picked) >= n:
                break
            while by_sc[sc]:
                r = by_sc[sc].pop()
                uid = uid_of(r)
                if uid in used_vid:
                    continue
                if uid not in probed:
                    probed[uid] = M.probe_full(str(VIDEOS / f"{uid}.mp4"))
                if not probed[uid]["audio"]["present"]:
                    continue
                used_vid.add(uid); picked.append(derive(r)); break
    picked.sort(key=lambda s: (s["scenario"] or "", s["sample_id"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"source": rel_source(RAW2), "seed": seed, "n": n, "filters": {"min_steps": min_steps, "dur": [min_dur, max_dur], "audio": True, "one_per_video": True,
                                                                                            "exclude_videos": sorted(excl)},
                               "n_candidates": len(cands), "samples": picked}, indent=1, ensure_ascii=False))
    return picked


class Egoplan(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        self.samples = [s for s in load_samples() if not videos or s["video_id"] in videos]
        self.by_vid = collections.defaultdict(list)
        for s in self.samples:
            self.by_vid[s["video_id"]].append(s)
        self.vids = sorted(self.by_vid)

    def videos(self): return self.vids

    def media(self):
        rows = []
        for uid in self.vids:
            rows.append({"media_id": f"{DS}/{uid}", "dataset": DS, "video_id": uid, "kind": "source_video", "path": str(VIDEOS / f"{uid}.mp4"),
                         "fps": None, "duration_sec": None, "resolution": None, "audio": None, "time_base": "source_video_seconds",
                         "offset_to_source_sec": 0.0, "parent_media_id": None,
                         "aux": {"samples": [s["sample_id"] for s in self.by_vid[uid]], "scenario": self.by_vid[uid][0].get("scenario")},
                         "annotation_sources": self.coverage(uid), "quality_flags": []})
        return rows

    def coverage(self, uid):
        ss = self.by_vid.get(uid, [])
        if not ss:
            return []
        return [{"source": SOURCE, "n": len(ss), "provenance": "human-verified",
                 "coverage": {"start_sec": min(s["t0"] for s in ss), "end_sec": max(s["t1"] for s in ss), "target_type": "task", "completeness": "partial"}},
                {"source": SOURCE_NARR, "n": sum(len(s["steps"]) for s in ss), "provenance": "human",
                 "coverage": {"start_sec": min(s["t0"] for s in ss), "end_sec": max(s["t1"] for s in ss), "target_type": "narration", "completeness": "partial"}}]

    @staticmethod
    def ids(s):
        uid, sid = s["video_id"], s["sample_id"]
        return {"segment": evidence_id(DS, uid, "bench2", f"{sid}/seg"), "next": evidence_id(DS, uid, "bench2", f"{sid}/next"),
                "step": lambda k: evidence_id(DS, uid, "bench2", f"{sid}/s{k}"), "narr": lambda k: evidence_id(DS, uid, "progress_narration", f"{sid}/n{k}")}

    def records(self, uid):
        mid = f"{DS}/{uid}"
        for s in self.by_vid.get(uid, []):
            sid, goal = s["sample_id"], s["goal"]
            I = self.ids(s)
            cov = {"scope_start_sec": s["t0"], "scope_end_sec": s["t1"], "target_type": "task", "completeness": "complete"}
            ent = [{"entity_id": sid, "id_space": "task", "name": goal}]
            prov = {"source_type": "dataset_annotation", "dataset": DS, "source": SOURCE, "upstream_provenance": "human-verified",
                    "source_file": rel_source(RAW2), "source_record_id": sid, "source_index": s.get("raw_index"), "legacy_eid": None, "derived_from": []}
            steps_pub = [{"idx": st["idx"], "text": st["text"], "t0": st["t0"], "t1": st["t1"]} for st in s["steps"]]
            yield record(evidence_id=I["segment"], video_id=uid, media_id=mid, kind="task_segment", domain="task.structure",
                         t0=s["t0"], t1=s["t1"], event_id=sid,
                         value={"task_id": sid, "goal": goal, "scenario": s.get("scenario"), "domain_label": s.get("domain"),
                                "n_steps": len(steps_pub), "steps": steps_pub, "status": "verified"},
                         epistemic="observation", modalities=["video"], entities=ent, provenance=prov, coverage=cov,
                         flags=["STEPS_ARE_NARRATIONS", "EGOPLAN_BENCH2"])
            for st in s["steps"]:
                k = st["idx"]
                val = {"task_id": sid, "idx": k, "text": st["text"], "verb": st["verb"], "noun": (st["nouns"] or [None])[0],
                       "nouns": st["nouns"], "goal": goal, "status": "verified"}
                yield record(evidence_id=I["step"](k), video_id=uid, media_id=mid, kind="task_step", domain="task.structure",
                             t0=st["t0"], t1=st["t1"], event_id=sid, value=val, epistemic="observation", modalities=["video"],
                             entities=ent, provenance={**prov, "source_record_id": f"{sid}/s{k}"}, coverage=cov, flags=["STEPS_ARE_NARRATIONS"])
                yield record(evidence_id=I["narr"](k), video_id=uid, media_id=mid, kind="action_narration", domain="physical.dynamics",
                             t0=st["t0"], t1=st["t1"], event_id=sid,
                             value={"text": st["text"], "label": st["text"], "verbs": [st["verb"]] if st["verb"] else [], "nouns": st["nouns"],
                                    "step_idx": k, "task_id": sid},
                             epistemic="observation", modalities=["video"], entities=[],
                             provenance={**prov, "source": SOURCE_NARR, "upstream_provenance": "human", "source_record_id": f"{sid}/n{k}",
                                         "derived_from": [I["step"](k)]},
                             coverage={**cov, "target_type": "narration"}, flags=[])
            na = s["next_action"]
            verb, nouns = split_narration(na["text"])
            yield record(evidence_id=I["next"], video_id=uid, media_id=mid, kind="task_step", domain="task.structure",
                         t0=s["t1"], t1=s["t1"] + 1.0, event_id=sid,
                         value={"task_id": sid, "idx": len(s["steps"]) + 1, "text": na["text"], "verb": verb, "noun": (nouns or [None])[0], "nouns": nouns,
                                "goal": goal, "is_next_action": True, "choices": na["choices"], "gold_letter": na["gold_letter"], "status": "verified"},
                         epistemic="observation", modalities=["video"], solver_access="answer_only", entities=ent,
                         provenance={**prov, "source_record_id": f"{sid}/next"}, coverage=cov,
                         flags=["EGOPLAN_NEXT_ACTION", "NEXT_ACTION_END_UNKNOWN"])

    def items(self):
        from items import _item
        for s in self.samples:
            I = self.ids(s)
            na = s["next_action"]
            opts = [f"{L}. {na['choices'][L]}" for L in "ABCD"]
            q = ("Considering the progress shown in the video and the current observation in the last frame, "
                 "what action should the camera wearer take next?")
            yield _item("egoplan", "EgoPlan-Bench2", s["video_id"], s["sample_id"], RAW2, q, "single_choice", opts, na["gold_letter"],
                        [{"media_id": f"{DS}/{s['video_id']}", "windows": [[max(s["t0"], round(s["t1"] - 30.0, 3)), s["t1"]]], "modalities": ["video", "audio"]}],
                        subtype="goal_conditioned_planning", cutoff=s["t1"], task_conditions=None,
                        evidence_refs=[I["segment"], I["next"]], status="verified", method="dataset_gt",
                        extra={"original_question": f"Considering the progress shown in the video and my current observation in the last frame, "
                                                     f"what action should I take next in order to {s['goal']}?",
                               "task_goal": s["goal"], "scenario": s.get("scenario")})

    def files_read(self): return [RAW2] + samples_paths()


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("select"); s.add_argument("--n", type=int, default=20); s.add_argument("--seed", type=int, default=1014)
    s.add_argument("--min-steps", type=int, default=3); s.add_argument("--min-dur", type=float, default=20.0); s.add_argument("--max-dur", type=float, default=300.0)
    s.add_argument("--out", default=None, help="输出样本文件(默认 data/egoplan_samples.json)")
    s.add_argument("--exclude-from", default=None, help="排除这个样本文件里已有的视频(默认:--out 不是主文件时排除主文件的视频)")
    sp.add_parser("show")
    a = ap.parse_args()
    if a.cmd == "select":
        out = Path(a.out) if a.out else SAMPLES
        exf = Path(a.exclude_from) if a.exclude_from else (SAMPLES if out != SAMPLES else None)
        excl = [x["video_id"] for x in json.loads(exf.read_text())["samples"]] if exf and exf.exists() else []
        picked = select(a.n, a.seed, a.min_steps, a.min_dur, a.max_dur, out=out, exclude_videos=excl)
        print(f"selected {len(picked)} samples -> {out} (excluded {len(excl)} videos)")
        for s in picked:
            print(f"  {s['sample_id']}  {s['scenario']:12s} {s['t0']:7.1f}-{s['t1']:7.1f}s  steps={len(s['steps'])}  goal={s['goal']!r} -> next={s['next_action']['text']!r}")
        print("videos:", json.dumps([s["video_id"] for s in picked]))
    else:
        ad = Egoplan()
        for s in ad.samples:
            print(s["sample_id"], s["goal"], len(s["steps"]))


if __name__ == "__main__":
    main()
