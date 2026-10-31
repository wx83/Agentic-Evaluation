"""EPIC-KITCHENS tactile 样本(tactile/tactile_samples.json,14 条,人工写的属性 / 动作 / 无触觉说明 / 后果 / 撞击声判断)
-> tactile_property_episode evidence + L1 人工题(answers_graded.json)作 items。T09 / T11 只有预切 clip(源偏移未知)。"""
import json, subprocess
from pathlib import Path
import p2config as P
from ids import evidence_id, item_id
from adapters.base import Adapter, record, rel_source

ROOT = Path(P.SOURCES["epic_kitchens"])
SAMPLES = ROOT / "tactile" / "tactile_samples.json"
GRADED = ROOT / "tactile" / "run_free_1002" / "answers_graded.json"
DS = "epic_kitchens"
IMPACT = {"能": "yes", "部分": "partial", "不能": "no"}


def _dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)], capture_output=True, text=True)
    try: return float(json.loads(r.stdout)["format"]["duration"])
    except Exception: return None


class Tactile(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        self.samples = json.loads(SAMPLES.read_text())
        self.vids = sorted({s["video"] for s in self.samples} & set(videos or {s["video"] for s in self.samples}))

    def videos(self): return self.vids

    def _precut(self, s):
        """t0 为 None 的样本:用 clip 字段的预切文件作媒体。"""
        return ROOT / s["clip"] if s.get("t0") is None and s.get("clip") else None

    def media(self):
        rows = []
        for vid in self.vids:
            p = next(ROOT.glob(f"*/videos/{vid}.MP4"))
            rows.append({"media_id": f"{DS}/{vid}", "dataset": DS, "video_id": vid, "kind": "source_video", "path": str(p),
                         "fps": None, "duration_sec": None, "resolution": None, "audio": None, "time_base": "source_video_seconds",
                         "offset_to_source_sec": 0.0, "parent_media_id": None, "aux": {},
                         "annotation_sources": self.coverage(vid), "quality_flags": []})
        for s in self.samples:
            pc = self._precut(s)
            if pc and s["video"] in self.vids:
                rows.append({"media_id": f"{DS}/{s['id']}_precut", "dataset": DS, "video_id": s["video"], "kind": "precut_clip", "path": str(pc),
                             "fps": None, "duration_sec": _dur(pc), "resolution": None, "audio": None, "time_base": "precut_clip_seconds",
                             "offset_to_source_sec": None, "parent_media_id": f"{DS}/{s['video']}", "aux": {"sample": s["id"]},
                             "annotation_sources": [], "quality_flags": ["UNKNOWN_SOURCE_OFFSET"]})
        return rows

    def coverage(self, vid):
        n = sum(1 for s in self.samples if s["video"] == vid)
        return [{"source": "epic_kitchens.tactile", "n": n, "coverage": {"start_sec": None, "end_sec": None, "target_type": "tactile_episode", "completeness": "partial"}}]

    def records(self, vid):
        for s in self.samples:
            if s["video"] != vid:
                continue
            pc = self._precut(s)
            if pc:
                mid, t0, t1, tb = f"{DS}/{s['id']}_precut", 0.0, (_dur(pc) or 0.0), "precut_clip_seconds"
            else:
                mid, t0, t1, tb = f"{DS}/{vid}", float(s["t0"]), float(s["t1"]), "source_video_seconds"
            val = {"sample_id": s["id"], "property": s.get("prop"), "action_zh": s.get("action"), "scenario_en": s.get("q"),
                   "why_touch_needed_zh": s.get("no_tactile"), "consequence_zh": s.get("consequence"),
                   "impact_sound_resolves": IMPACT.get(s.get("impact_sound"), s.get("impact_sound")),
                   "impact_sound_reason_zh": s.get("impact_sound_reason"), "audio_evidence_zh": s.get("audio_evidence"),
                   "verified": bool(s.get("verified"))}
            yield record(
                evidence_id=evidence_id(DS, vid, "tactile", s["id"]), video_id=vid, media_id=mid, kind="tactile_property_episode",
                domain="physical.objects_properties", t0=t0, t1=t1, time_base=tb, event_id=s["id"],
                value=val, epistemic="interpretation", modalities=["video", "audio"], solver_access="observed",
                entities=[], provenance={"source_type": "human_annotation", "dataset": DS, "source": "epic_kitchens.tactile",
                                         "source_file": rel_source(SAMPLES), "source_record_id": s["id"], "legacy_eid": None, "derived_from": []},
                coverage={"scope_start_sec": t0, "scope_end_sec": t1, "target_type": "tactile_episode", "completeness": "partial"},
                flags=(["PRECUT_CLIP", "UNKNOWN_SOURCE_OFFSET"] if pc else []))

    def items(self):
        if not GRADED.exists():
            return
        by = {s["id"]: s for s in self.samples}
        for x in json.loads(GRADED.read_text()):
            s = by.get(x["id"])
            if not s or x.get("gold") in (None, "") or s["video"] not in self.vids:
                continue
            pc = self._precut(s)
            mr = [{"media_id": f"{DS}/{s['id']}_precut", "windows": [], "modalities": ["video", "audio"]}] if pc else \
                 [{"media_id": f"{DS}/{s['video']}", "windows": [[float(s["t0"]), float(s["t1"])]], "modalities": ["video", "audio"]}]
            yield {"item_id": item_id("epic_tactile", s["video"], f"{x['id']}_{x['level']}_{x['skill']}"), "item_version": 1,
                   "source": {"dataset": DS, "benchmark": "tactile samples 1001 (human-written)", "original_id": f"q_{x['id']}_{x['skill']}", "file": rel_source(GRADED)},
                   "video_id": s["video"], "original_subtype": x["skill"], "capability_mapping": None,
                   "taxonomy_version": P.TAXONOMY_VERSION, "registry_version": P.REGISTRY_VERSION,
                   "public": {"question": x["q"], "options": None, "format": "short_answer", "media_refs": mr, "observation_cutoff": None,
                              "task_conditions": None, "allowed_inputs": {"modalities": ["video", "audio"], "allowed_tools": []}},
                   "private": {"gold_answer": x["gold"], "accepted_alternatives": [], "acceptance_criteria": [], "rubric": [],
                               "evidence_refs": [{"evidence_id": evidence_id(DS, s["video"], "tactile", s["id"]), "version": 1}],
                               "gold_verification_status": "verified", "verification_method": "human_review", "review_id": None, "reference_version": None,
                               "basis": x.get("basis")},
                   "quality_flags": []}

    def files_read(self): return [SAMPLES, GRADED]
