"""geo3d(DA3 + SAM3 纯视频 3D 估计,10-15)→ evidence。只读 output/pyramid_v2/geo3d/<sid>/records_final.jsonl(derive → verify_gemini → fixtures_gemini → finalize 的产物),不在这里算任何东西。
source = egoplan.geo3d_da3_sam3;policy 让它保持 needs_verification,只有人工 review(reviews/geo3d_review.csv + geo3d_review_map.json)能升 verified;Gemini 的结果在顶层 checks。
media 行由 adapters/egoplan.py 负责(同一批 Ego4D 原视频);这里只补 coverage。"""
import json, collections
from pathlib import Path
import p2config as P
from adapters.base import Adapter

DS = "egoplan"
SOURCE = "egoplan.geo3d_da3_sam3"
GEO3D = P.ROOT / "geo3d"
SAMPLES = P.DATA / "egoplan_samples.json"


class Geo3d(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        d = json.loads(SAMPLES.read_text()) if SAMPLES.exists() else {"samples": []}
        self.samples = [s for s in d["samples"] if (not videos or s["video_id"] in videos) and (GEO3D / s["sample_id"] / "records_final.jsonl").exists()]
        self.by_vid = collections.defaultdict(list)
        for s in self.samples:
            self.by_vid[s["video_id"]].append(s)
        self.vids = sorted(self.by_vid)
        self._files = []

    def videos(self): return self.vids

    def media(self): return []          # egoplan adapter 已有 source_video 行

    def coverage(self, vid):
        ss = self.by_vid.get(vid, [])
        if not ss:
            return []
        return [{"source": SOURCE, "n": len(ss), "provenance": "model_prediction (DA3 metric depth + pose, SAM3 text tracking; Gemini 4 side checks; human review pending)",
                 "coverage": {"start_sec": min(s["t0"] for s in ss), "end_sec": max(s["t1"] for s in ss), "target_type": "3d_estimate", "completeness": "partial"}}]

    def records(self, vid):
        for s in self.by_vid.get(vid, []):
            cd = GEO3D / s["sample_id"]; p = cd / "records_final.jsonl"
            self._files.append(p)
            for q in (cd / "verify.json", cd / "fixtures.json", cd / "positions.json"):
                if q.exists(): self._files.append(q)
            for line in p.read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                r["provenance"]["source_file"] = f"geo3d/{s['sample_id']}/records_final.jsonl"
                yield r

    def files_read(self):
        rm = P.REVIEWS / "geo3d_review_map.json"
        return sorted(set(self._files)) + ([rm] if rm.exists() else [])
