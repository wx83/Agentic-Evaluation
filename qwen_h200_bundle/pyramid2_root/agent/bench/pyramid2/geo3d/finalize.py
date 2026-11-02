"""records.jsonl + verify.json + fixtures.json → records_final.jsonl(adapters/geo3d.py 读这个):
  (a) 顶层 checks:Gemini 4 的旁路核验(gemini4_relation / gemini4_static / gemini4_move / gemini4_ordinal_depth / gemini4_ordinal_lr / gemini4_trajectory / gemini4_alias / gemini4_fixture),
      放在顶层而不是 verification 里(build_data 会按 policy 重刷 verification);contradicted / no → flag GEMINI_CONTRADICTED。
  (b) fixture_candidate 记录 + 回填 object_position_interval / object_move 的 fixture 字段(status candidate)。
  $HOLI -m geo3d.finalize --samples all"""
import json, argparse, collections, time
from pathlib import Path
import numpy as np
from . import cfg
from adapters.base import record
from ids import evidence_id
import schema

NEG = {"contradicted", "no", "disagree"}


def _chk(method, verdict, conf, reason, ts, **extra):
    return {"method": method, "verdict": verdict, "confidence": conf, "reason": reason, "model": "gcp/google/gemini-4-argon", "ts": ts, **extra}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--samples", nargs="*", default=["all"]); a = ap.parse_args()
    for s in cfg.samples(a.samples):
        cd = cfg.clip_dir(s["sample_id"])
        if not (cd / "records.jsonl").exists(): print("no records:", s["sample_id"]); continue
        recs = [json.loads(l) for l in open(cd / "records.jsonl")]; by = {r["evidence_id"]: r for r in recs}
        pos = json.loads((cd / "positions.json").read_text())
        ver = json.loads((cd / "verify.json").read_text()) if (cd / "verify.json").exists() else {}
        fx = json.loads((cd / "fixtures.json").read_text()) if (cd / "fixtures.json").exists() else {"fixtures": {}, "intervals": {}}
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime((cd / "verify.json").stat().st_mtime)) if (cd / "verify.json").exists() else None
        checks = collections.defaultdict(list)
        for r in ver.get("relations", []):
            if r.get("eid") in by: checks[r["eid"]].append(_chk("gemini4_relation", r.get("verdict"), r.get("confidence"), r.get("reason"), ts, claim=r.get("claim")))
        for x in (ver.get("static") or {}).get("items", []):
            if x.get("eid") in by: checks[x["eid"]].append(_chk("gemini4_static", x.get("gemini"), x.get("confidence"), x.get("reason"), ts))
        for x in (ver.get("moves") or {}).get("items", []):
            if x.get("eid") in by: checks[x["eid"]].append(_chk("gemini4_move", x.get("gemini"), x.get("confidence"), x.get("reason"), ts))
        for mode in ("depth", "lr"):
            for x in (ver.get(f"ordinal_{mode}") or {}).get("items", []):
                for e in x.get("eids") or []:
                    if e in by: checks[e].append(_chk(f"gemini4_ordinal_{mode}", "agree" if x.get("agree") else "disagree", x.get("confidence"), x.get("reason"), ts, pair=[x["A"], x["B"]], geo_says=x.get("geo_says"), gemini=x.get("gemini")))
        tr = ver.get("trajectory") or {}
        if tr.get("eid") in by: checks[tr["eid"]].append(_chk("gemini4_trajectory", tr.get("consistent"), tr.get("confidence"), tr.get("reason"), ts))
        for lg in pos.get("alias_log", []):
            g = lg.get("gemini")
            if g:
                for iid in (lg["a"], lg["b"]):
                    e = next((r["evidence_id"] for r in recs if r["kind"] == "object_instance" and r["value"].get("instance_short") == iid), None)
                    if e: checks[e].append(_chk("gemini4_alias", g.get("same_object"), g.get("confidence"), g.get("reason"), ts, pair=[lg["a"], lg["b"]], decision=lg.get("decision")))
        for eid, x in (fx.get("intervals") or {}).items():
            if eid in by: checks[eid].append(_chk("gemini4_fixture", x.get("resting"), x.get("confidence"), x.get("reason"), ts, surface_kind=x.get("surface_kind"), surface_name=x.get("surface_name"), fixture_id=x.get("fixture_id")))
        n_contra = 0
        for eid, cl in checks.items():
            r = by[eid]; r["checks"] = cl
            if any(str(c.get("verdict", "")).lower() in NEG for c in cl if c["method"] in ("gemini4_relation", "gemini4_static", "gemini4_move")):
                if "GEMINI_CONTRADICTED" not in r["quality_flags"]: r["quality_flags"].append("GEMINI_CONTRADICTED"); n_contra += 1
        # fixtures
        vid = s["video_id"]; sid = s["sample_id"]; w0, w1 = s["window"]; WF = f"frame0_cam:{sid}"
        frame_rec = next((r for r in recs if r["kind"] == "spatial_frame"), None)
        base_flags = [f for f in (frame_rec["quality_flags"] if frame_rec else ["DERIVED", "MODEL_ESTIMATED_3D"]) if f not in ("GEMINI_CONTRADICTED",)]
        prov = dict((frame_rec or recs[0])["provenance"]); prov["derived_from"] = []
        new = []
        for fid, f in (fx.get("fixtures") or {}).items():
            der = [e for e in f["supported_intervals"] if e in by]
            new.append(record(evidence_id=evidence_id("egoplan", vid, "geo3d", f"{sid}/fixture/{fid.rsplit(':', 1)[-1]}"), video_id=vid, media_id=f"egoplan/{vid}", kind="fixture_candidate", domain="physical.spatial",
                              t0=w0, t1=w1, event_id=sid, value={**f, "entity_type": "fixture", "status": "candidate", "frame_id": WF, "unit": "m", "association_scope": sid,
                                                                 "source": "gemini4_fixture: per-interval 'what surface is the outlined object resting on', deduplicated by (kind, name)"},
                              epistemic="interpretation", modalities=["video"], entities=[{"entity_id": fid, "id_space": "geo3d_fixture", "name": f["name"]}],
                              provenance={**prov, "source_type": "model_prediction", "derived_from": der}, coverage={"scope_start_sec": w0, "scope_end_sec": w1, "target_type": "fixture_candidate", "completeness": "partial"},
                              flags=base_flags + ["FIXTURE_CANDIDATE"]))
        for eid, x in (fx.get("intervals") or {}).items():
            if eid in by and x.get("fixture_id"):
                v = by[eid]["value"]; v["fixture_id"] = x["fixture_id"]; v["fixture_kind"] = x["surface_kind"]; v["fixture_name"] = x["surface_name"]; v["fixture_status"] = "candidate"; v["fixture_confidence"] = x.get("confidence")
        for r in recs:
            if r["kind"] in ("object_move", "object_location_transition"):
                v = r["value"]; st, en = by.get(v.get("start_interval_ref")), by.get(v.get("end_interval_ref"))
                if st and st["value"].get("fixture_id"): v["from_fixture"] = st["value"]["fixture_id"]; v["from_fixture_kind"] = st["value"]["fixture_kind"]; v["fixture_status"] = "candidate"
                if en and en["value"].get("fixture_id"): v["to_fixture"] = en["value"]["fixture_id"]; v["to_fixture_kind"] = en["value"]["fixture_kind"]; v["fixture_status"] = "candidate"
        out = recs + new
        bad = [(r["evidence_id"], schema.validate_evidence(r)) for r in out if schema.validate_evidence(r)]
        assert not bad, bad[:3]
        with open(cd / "records_final.jsonl", "w") as f:
            for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        km = collections.Counter(c["method"] for cl in checks.values() for c in cl)
        print(f"{s['scenario']:12s} records {len(out)} (+{len(new)} fixture_candidate) | checks on {len(checks)} records {dict(km)} | GEMINI_CONTRADICTED {n_contra} | intervals with fixture {sum(1 for r in out if r['kind']=='object_position_interval' and r['value'].get('fixture_id'))}", flush=True)


if __name__ == "__main__":
    main()
