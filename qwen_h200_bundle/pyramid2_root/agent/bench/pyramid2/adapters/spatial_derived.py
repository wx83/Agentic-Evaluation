"""派生空间关系:复用旧管线 facts.py/spatial.py 在 HD-EPIC 数字孪生 3D 位置上算出的 nearest / side / farthest / order
(缓存在 output/pyramid_seed43|seed1011/data/facts_<vid>.json),转成 spatial_relation evidence record。
epistemic = measurement(由 dataset GT 的 3D 位置确定性推出),derived_from = 参与计算的 movement / sound 记录。"""
import json
from pathlib import Path
import p2config as P
from ids import evidence_id
from adapters.base import Adapter, record, rel_source

DS = "hdepic"
ROOTS = [Path(P.SOURCES["pyramid_seed43"]) / "data", Path("/mnt/work_new/weihanxu/output/pyramid_seed1011/data")]
REL = {"easy_spatial_near": "nearest", "low_spatial_near": "nearest", "medium_spatial_extreme": "farthest",
       "medium_spatial_order": "order_by_distance"}


class SpatialDerived(Adapter):
    dataset = DS

    def __init__(self, videos=None):
        self.vids = list(videos or P.HDEPIC_VIDEOS)
        self._files = []

    def videos(self): return [v for v in self.vids if self._file(v)]

    def _file(self, vid):
        for r in ROOTS:
            f = r / f"facts_{vid}.json"
            if f.exists():
                return f
        return None

    def coverage(self, vid):
        return [{"source": "hdepic.spatial_derived", "n": None,
                 "coverage": {"start_sec": None, "end_sec": None, "target_type": "spatial_relation", "completeness": "partial"}}]

    def records(self, vid):
        f = self._file(vid)
        if not f:
            return
        self._files.append(f)
        mid = f"{DS}/{vid}"
        d = json.loads(f.read_text())
        for tier, fs in d.items():
            for x in fs:
                st = x.get("subtype", "")
                if st in REL:
                    rel = REL[st]
                elif st in ("easy_spatial_side", "low_spatial_side"):
                    rel = "side_" + (x.get("_mode") or "right")
                else:
                    continue
                if st == "medium_spatial_extreme" and x.get("_mode") == "near":
                    rel = "nearest_final"
                anchor_kind = "sound" if x.get("_sound_label") else "movement"
                T = x.get("evidence_t")
                ref_obj = x.get("_ref") or x.get("_anchor")
                defn = {"nearest": f"Among the objects visible at the anchor moment, the one closest to the {ref_obj} (3D distance).",
                        "nearest_final": f"After all placements in the window, the object closest to the {ref_obj}.",
                        "farthest": f"Among candidate objects whose locations are known from placements in the window, the one farthest from the {ref_obj} at the anchor moment; the answer object may be out of view at that moment.",
                        "side_right": "At the anchor moment (when the anchored object is put down), the object farthest to the CAMERA WEARER'S RIGHT in the wearer's own view (reference frame = the wearer / camera, NOT the anchored object).",
                        "side_left": "At the anchor moment, the object farthest to the CAMERA WEARER'S LEFT in the wearer's own view (reference frame = the wearer / camera, NOT the anchored object).",
                        "order_by_distance": f"Ordering of the three objects by 3D distance from the {ref_obj} at the anchor moment, nearest first."}.get(rel, rel)
                val = {"relation": rel, "relation_definition": defn, "anchor_kind": anchor_kind, "anchor_time_sec": T,
                       "window": [x["t0"], x["t1"]], "reference_object": x.get("_ref") or x.get("_anchor"),
                       "answer_object": x["gold"], "verified_wrong_answers": x.get("distractors"),
                       "absent_in_window": x.get("_absent"), "d_gold_m": x.get("_d_gold"), "margin_m": x.get("_marg"),
                       "lateral_gold_m": x.get("_lat_gold"), "side_mode": x.get("_mode"),
                       "anchor_sound_label": x.get("_sound_label"), "frame": "world (HD-EPIC digital twin, metres)" if "side" not in rel else "camera (device frame at anchor time: left/right of the wearer)",
                       "original_subtype": st, "fact_id": x["fact_id"]}
                yield record(
                    evidence_id=evidence_id(DS, vid, "spatial", x["fact_id"]), video_id=vid, media_id=mid,
                    kind="spatial_relation", domain="physical.spatial", t0=T if T is not None else x["t0"], t1=T if T is not None else x["t1"],
                    value=val, epistemic="measurement", modalities=["video"] + (["audio"] if anchor_kind == "sound" else []),
                    entities=[{"entity_id": "name:" + (x["gold"] or "").replace(" ", "_"), "id_space": "name_only", "name": x["gold"]}],
                    provenance={"source_type": "derived_3d_geometry", "dataset": DS, "source": "hdepic.spatial_derived",
                                "source_file": rel_source(f), "source_record_id": x["fact_id"], "legacy_eid": None,
                                "derived_from_legacy": list(x.get("evidence_event_ids") or []),
                                "method": "agent/bench/pyramid/spatial.py (rest_at + rank_others / device-frame side), seed43 cache"},
                    coverage={"scope_start_sec": x["t0"], "scope_end_sec": x["t1"], "target_type": "spatial_relation", "completeness": "partial"},
                    flags=["DERIVED"])

    def files_read(self): return list(self._files)
