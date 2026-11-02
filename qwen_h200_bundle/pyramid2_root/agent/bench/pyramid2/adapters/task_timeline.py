"""pyramid_seed43/annot 的 task_timeline_<vid>.json(Gemini 切任务)与 plan_traj_<vid>.json -> task_segment / task_step。"""
import json
from pathlib import Path
import p2config as P
from ids import evidence_id
from adapters.base import Adapter, record, rel_source

ROOT = Path(P.SOURCES["pyramid_seed43"]) / "annot"
DS = "hdepic"


class TaskTimeline(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        self.vids = [v for v in (videos or P.HDEPIC_VIDEOS) if (ROOT / f"task_timeline_{v}.json").exists()]
        self._files = []

    def videos(self): return self.vids

    def coverage(self, vid):
        return [{"source": "pyramid_seed43.task_timeline", "n": None,
                 "coverage": {"start_sec": None, "end_sec": None, "target_type": "task", "completeness": "unknown"}}]

    def records(self, vid):
        mid = f"{DS}/{vid}"
        p = ROOT / f"task_timeline_{vid}.json"; self._files.append(p)
        d = json.loads(p.read_text())
        for t in d.get("tasks", []):
            status = t.get("status", "draft")
            comp = "complete" if status == "verified" else "unknown"
            cov = {"scope_start_sec": t["t0"], "scope_end_sec": t["t1"], "target_type": "task", "completeness": comp}
            prov = {"source_type": "model_segmentation", "dataset": DS, "source": "pyramid_seed43.task_timeline",
                    "source_file": rel_source(p), "source_record_id": t["task_id"], "legacy_eid": None,
                    "derived_from": [], "raw_status": status, "annotator": t.get("annotator"), "note": t.get("note"),
                    "version_tag": d.get("version")}
            tid = evidence_id(DS, vid, "task", t["task_id"])
            yield record(
                evidence_id=tid, video_id=vid, media_id=mid, kind="task_segment", domain="task.structure",
                t0=t["t0"], t1=t["t1"], event_id=t["task_id"],
                value={"task_id": t["task_id"], "parent_task": t.get("parent_task"), "goal": t.get("goal"),
                       "n_steps": t.get("n_steps"), "partial": t.get("partial"), "status": status,
                       "steps": [{"idx": s.get("idx"), "text": s.get("text"), "t0": s.get("t0"), "t1": s.get("t1")} for s in t.get("steps", [])]},
                epistemic="interpretation", modalities=["video"], solver_access="observed",
                entities=[{"entity_id": t["task_id"], "id_space": "task", "name": t.get("goal")}],
                provenance=prov, coverage=cov, flags=[] if status == "verified" else ["DRAFT"])
            for s in t.get("steps", []):
                sid = f"{t['task_id']}/s{s.get('idx')}"
                yield record(
                    evidence_id=evidence_id(DS, vid, "task", sid), video_id=vid, media_id=mid, kind="task_step",
                    domain="task.structure", t0=s["t0"], t1=s.get("t1", s["t0"]), event_id=t["task_id"],
                    value={"task_id": t["task_id"], "idx": s.get("idx"), "text": s.get("text"), "verb": s.get("verb"),
                           "noun": s.get("noun"), "goal": t.get("goal"), "status": status},
                    epistemic="interpretation", modalities=["video"],
                    entities=[{"entity_id": t["task_id"], "id_space": "task", "name": t.get("goal")}],
                    provenance={**prov, "source_record_id": sid, "derived_from_legacy": list(s.get("eids") or [])},
                    coverage=cov, flags=[] if status == "verified" else ["DRAFT"])
        pp = ROOT / f"plan_traj_{vid}.json"
        if pp.exists():
            self._files.append(pp)
            d = json.loads(pp.read_text())
            for seg in d.get("segments", []):
                status = seg.get("status", "draft")
                cov = {"scope_start_sec": seg["t0"], "scope_end_sec": seg["t1"], "target_type": "task",
                       "completeness": "complete" if status == "verified" else "unknown"}
                prov = {"source_type": "model_segmentation", "dataset": DS, "source": "pyramid_seed43.plan_traj",
                        "source_file": rel_source(pp), "source_record_id": seg["seg_id"], "legacy_eid": None,
                        "derived_from": [], "raw_status": status, "version_tag": d.get("version")}
                yield record(
                    evidence_id=evidence_id(DS, vid, "plan_traj", seg["seg_id"]), video_id=vid, media_id=mid,
                    kind="task_segment", domain="task.structure", t0=seg["t0"], t1=seg["t1"], event_id=seg["seg_id"],
                    value={"task_id": seg["seg_id"], "goal": seg.get("goal"), "recipe_id": seg.get("recipe_id"),
                           "activity_label": seg.get("activity_label"), "status": status,
                           "steps": [{"idx": s.get("idx"), "text": s.get("text"), "t0": s.get("t0"), "t1": s.get("t1")} for s in seg.get("reference_steps", [])]},
                    epistemic="interpretation", modalities=["video"],
                    entities=[{"entity_id": seg["seg_id"], "id_space": "task", "name": seg.get("goal")}],
                    provenance=prov, coverage=cov, flags=[] if status == "verified" else ["DRAFT"])

    def files_read(self): return list(self._files)
