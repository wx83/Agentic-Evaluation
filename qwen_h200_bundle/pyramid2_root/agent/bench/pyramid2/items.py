"""seed items:已有 QA / planning 题 -> items.jsonl(含 private.gold_answer)。"""
import json, re
from pathlib import Path
import p2config as P
from ids import item_id
from adapters.base import rel_source
from store import read_jsonl

TIME_RE = re.compile(r"<TIME (\d\d):(\d\d):(\d\d(?:\.\d+)?) video 1>")


def _item(source, benchmark, video_id, oid, file, question, fmt, options, gold, media_refs, *, subtype=None,
          cutoff=None, task_conditions=None, evidence_refs=None, status="verified", method="dataset_gt", flags=None,
          extra=None, reference_frame=None, tolerance=None, target_ids=None, event_refs=None, answerability="answerable"):
    """10-15 spec §10 字段:reference_frame(world / camera_at_time / semantic_fixture + reference_timestamp)、tolerance(数值 / 时间 / 角度容差)、
    target_ids / event_refs(题目涉及的实例与事件 evidence_id)进 private;answerability(answerable / ambiguous / insufficient_evidence)进 public。"""
    return {"item_id": item_id(source, video_id, oid), "item_version": 1,
            "source": {"dataset": source.split("_")[0], "benchmark": benchmark, "original_id": str(oid), "file": rel_source(file)},
            "video_id": video_id, "original_subtype": subtype, "capability_mapping": None,
            "taxonomy_version": P.TAXONOMY_VERSION, "registry_version": P.REGISTRY_VERSION,
            "public": {"question": question, "options": options, "format": fmt, "media_refs": media_refs,
                       "observation_cutoff": cutoff, "task_conditions": task_conditions,
                       "allowed_inputs": {"modalities": ["video", "audio"], "allowed_tools": []}, "answerability": answerability},
            "private": {"gold_answer": gold, "accepted_alternatives": [], "acceptance_criteria": [], "rubric": [],
                        "evidence_refs": evidence_refs or [], "gold_verification_status": status,
                        "verification_method": method, "review_id": None, "reference_version": None,
                        "reference_frame": reference_frame, "tolerance": tolerance, "target_ids": list(target_ids or []), "event_refs": list(event_refs or []), **(extra or {})},
            "quality_flags": list(flags or [])}


def from_pyramid_sets(videos):
    root = Path(P.SOURCES["pyramid_seed43"])
    out = []
    for f in sorted((root / "adaptive").glob("*/L*/items.jsonl")):
        run = f.parts[-3]
        for r in read_jsonl(f):
            vid = r["video_id"]
            if vid not in videos:
                continue
            w = r.get("window") or [r.get("t0"), r.get("t1")]
            fmt = {"mc": "single_choice", "ms": "multi_select", "open": "short_answer", "open_x": "short_answer",
                   "plan": "plan", "plan_x": "plan", "yn": "yes_no", "tf4": "true_false_4"}.get(r.get("fmt"), r.get("fmt"))
            if fmt not in ("single_choice", "multi_select", "short_answer", "plan"):
                continue
            legacy = r.get("evidence_event_ids") or []
            out.append(_item("hdepic_pyramid", f"pyramid adaptive {run}", vid, r["question_id"], f, r["question"], fmt,
                             r.get("options"), r.get("gold_shown") or r.get("answer"),
                             [{"media_id": f"hdepic/{vid}", "windows": [[w[0], w[1]]], "modalities": ["video", "audio"]}],
                             subtype=r.get("skill"), status="needs_verification", method=None,
                             extra={"legacy_evidence_eids": legacy, "cluster": r.get("cluster")}))
    for f in sorted((root / "sets").glob("*/*/L*.json")):
        d = json.loads(f.read_text())
        qs = d.get("questions", []) if isinstance(d, dict) else d
        arm, scope = (d.get("arm"), d.get("scope")) if isinstance(d, dict) else (f.parts[-3], f.parts[-2])
        for q in qs:
            vid = q.get("video_id")
            if vid not in videos or "question" not in q:
                continue
            out.append(_item("hdepic_pyramid", f"pyramid set {arm}/{scope}", vid, q["question_id"], f,
                             q["question"], "single_choice", q.get("options"), q.get("correct_option") or q.get("answer"),
                             [{"media_id": f"hdepic/{vid}", "windows": [[q["t0"], q["t1"]]], "modalities": ["video", "audio"]}],
                             subtype=q.get("subtype"), status="needs_verification", method=None,
                             extra={"legacy_evidence_eids": q.get("evidence_event_ids") or [], "fact_id": q.get("fact_id")}))
    return out


def from_hdepic_vqa(videos):
    out = []
    for vid in videos:
        f = Path(P.SOURCES["hdepic"]) / vid / "raw" / "vqa.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        for task, qs in d.items():
            for qid, q in qs.items():
                ts = [int(h) * 3600 + int(m) * 60 + float(s) for h, m, s in TIME_RE.findall(q["question"])]
                if ts:
                    a, b = max(0.0, min(ts) - 20.0), max(ts) + 10.0
                else:
                    a, b = None, None
                flags = []
                if "<BBOX" in q["question"]: flags.append("BBOX_TOKEN_IN_QUESTION")
                if not ts: flags.append("NO_TIME_ANCHOR")
                opts = [f"{'ABCDE'[i]}. {c}" for i, c in enumerate(q["choices"])]
                out.append(_item("hdepic_vqa", "HD-EPIC VQA", vid, qid, f, q["question"], "single_choice", opts,
                                 "ABCDE"[q["correct_idx"]],
                                 [{"media_id": f"hdepic/{vid}", "windows": [[a, b]] if ts else [], "modalities": ["video", "audio"]}],
                                 subtype=f"hdepic_vqa:{task}", flags=flags))
    return out


def from_ego4d(videos):
    d = json.loads((Path(P.SOURCES["ego4d"]) / "ego4d_annotations.json").read_text())
    f = Path(P.SOURCES["ego4d"]) / "ego4d_annotations.json"
    out = []
    for uid in videos:
        v = d["videos"][uid]
        for src in ("nlq", "egoschema", "egoplan1", "egoplan2", "videgothink"):
            for i, e in enumerate(v["events"].get(src, []) or []):
                ex = e.get("extra") or {}
                t0, t1 = float(e["t_start"]), float(e.get("t_end", e["t_start"]))
                oid = ex.get("annotation_uid") or ex.get("sample_id") or f"{e.get('clip_uid')}_{i}"
                mr = [{"media_id": f"ego4d/{uid}", "windows": [[t0, t1]], "modalities": ["video", "audio"]}]
                status, method = "verified", "dataset_gt"
                flags = []
                if src == "nlq":
                    it = _item("ego4d_nlq", "Ego4D NLQ", uid, oid, f, e["text"], "short_answer", None,
                               f"window {t0:.1f}-{t1:.1f} s", [{"media_id": f"ego4d/{uid}", "windows": [], "modalities": ["video", "audio"]}],
                               subtype=f"nlq:{e.get('label')}", flags=["ANSWER_IS_TEMPORAL_WINDOW"])
                elif src == "egoschema":
                    gold = ex.get("answer")
                    opts = [f"{'ABCDE'[k]}. {o}" for k, o in enumerate(ex.get("options") or [])]
                    if gold is None:
                        flags.append("ANSWER_WITHHELD"); status, method = "needs_verification", None
                    it = _item("ego4d_egoschema", "EgoSchema", uid, oid, f, e["text"], "single_choice", opts,
                               ("ABCDE"[gold] if isinstance(gold, int) else gold), mr, subtype="egoschema", status=status, method=method, flags=flags)
                elif src in ("egoplan1", "egoplan2"):
                    ch = ex.get("choices") or {}
                    opts = [f"{k.upper()}. {vv}" for k, vv in sorted(ch.items())]
                    goal = e["text"].split("->")[0].replace("goal:", "").strip()
                    it = _item(f"ego4d_{src}", "EgoPlan-Bench" if src == "egoplan1" else "EgoPlan-Bench2", uid, oid, f,
                               f"The camera wearer's goal is: {goal}. What is the next action?", "single_choice", opts,
                               str(ex.get("gold")).upper(), mr, subtype=f"{src}:next_action", cutoff=t1,
                               task_conditions={"goal": goal}, status="verified", method="dataset_gt")
                else:  # videgothink
                    it = _item("ego4d_videgothink", "VidEgoThink", uid, oid, f, e["text"], "short_answer", None,
                               ex.get("answer"), mr, subtype=f"videgothink:{e.get('label')}",
                               status="needs_verification", method=None)
                out.append(it)
    return out


def build(only=None):
    only = set(only or ["pyramid_seeds", "hdepic_vqa", "ego4d", "tactile", "egoplan"])
    rows = []
    if "egoplan" in only:
        from adapters.egoplan import Egoplan
        rows += list(Egoplan().items())
    if "tactile" in only:
        from adapters.tactile import Tactile
        rows += list(Tactile().items())
    if "pyramid_seeds" in only: rows += from_pyramid_sets(set(P.HDEPIC_VIDEOS))
    if "hdepic_vqa" in only: rows += from_hdepic_vqa(P.HDEPIC_VIDEOS)
    if "ego4d" in only: rows += from_ego4d(P.EGO4D_VIDEOS)
    seen = {}
    for r in rows:
        seen[r["item_id"]] = r
    return sorted(seen.values(), key=lambda r: r["item_id"])
