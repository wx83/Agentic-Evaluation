"""Fixture candidate(10-15 用户定):每个静止区间取物体可见面积最大的一帧 + 物体框,问 Gemini 4 它放在什么表面 / 家具上;按 (kind, name) 去重成 fixture_candidate。
全部是 candidate,不是 gold;每次调用记 usage(role verify3d, check fixture)。
  GEMINI_BACKEND=nv $HOLI -m geo3d.fixtures_gemini --samples all   → <clip>/fixtures.json"""
import json, argparse, re, collections, statistics
from pathlib import Path
import numpy as np
from . import cfg
from .verify_gemini import ask, render_marks, load_tracks_light

KINDS = ["table", "counter", "workbench", "desk", "floor", "ground", "shelf", "sink", "stove", "chair", "wall", "cabinet", "held_in_hand", "other"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--samples", nargs="*", default=["all"]); a = ap.parse_args()
    for s in cfg.samples(a.samples):
        cd = cfg.clip_dir(s["sample_id"])
        if not (cd / "positions.json").exists(): print("no positions:", s["sample_id"]); continue
        pos = json.loads((cd / "positions.json").read_text()); fr = cfg.load_frames(cd)["frames"]; tracks = load_tracks_light(cd)
        if not (pos.get("quality") or {}).get("pose_valid"):
            (cd / "fixtures.json").write_text(json.dumps({"sample_id": s["sample_id"], "fixtures": {}, "intervals": {}, "note": "pose invalid: no static intervals"}, indent=1)); print("pose invalid:", s["scenario"]); continue
        print(f"== {s['scenario']} {s['sample_id'][-6:]}", flush=True)
        per_iv = {}
        for n, o in pos["objects"].items():
            for iv in o["intervals"]:
                rows = [x for x in o["rows"] if iv["t0"] <= x["t"] <= iv["t1"] and x["hand_overlap"] <= cfg.HAND_OVERLAP] or [x for x in o["rows"] if iv["t0"] <= x["t"] <= iv["t1"]]
                if not rows: continue
                best = max(rows, key=lambda x: x.get("area", 0)); fi = best["fi"]
                im = render_marks(cd, tracks, fr, fi, [(n, o["iid"], n, "obj")])
                v = ask([im], f'The outlined object is "{n}". What surface, piece of furniture or fixture is it resting on (or attached to) at this moment? Return JSON: {{"surface_kind": one of {json.dumps(KINDS)}, "surface_name": "<short description, e.g. wooden workbench, kitchen counter, grass>", "resting_on_it": "yes"|"no"|"unsure", "confidence": 0-1, "reason": "<one sentence>"}}',
                        {"sample": s["sample_id"], "check": "fixture", "object": n, "t0": iv["t0"]})
                kind = str(v.get("surface_kind") or "other").lower().strip(); kind = kind if kind in KINDS else "other"
                name = re.sub(r"\s+", " ", str(v.get("surface_name") or kind).lower().strip())[:60]
                per_iv[iv["eid"]] = {"object": n, "t0": iv["t0"], "t1": iv["t1"], "frame": fi, "surface_kind": kind, "surface_name": name, "resting": str(v.get("resting_on_it", "")).lower()[:3],
                                     "confidence": v.get("confidence"), "reason": v.get("reason"), "xyz": iv["xyz"]}
                print(f"  {n[:18]:18s} {iv['t0']:.1f}-{iv['t1']:.1f} -> {kind} / {name} ({v.get('confidence')})", flush=True)
        # 去重:同 clip 内 (kind, name) → 一个 fixture_candidate
        groups = collections.defaultdict(list)
        for eid, x in per_iv.items():
            if x["surface_kind"] == "held_in_hand" or x["resting"] == "no": continue
            groups[(x["surface_kind"], x["surface_name"])].append((eid, x))
        fixtures = {}
        for (kind, name), items in groups.items():
            fid = f"geo3d:{s['sample_id']}:fixture:{cfg.slug(kind)}_{cfg.slug(name)}"
            xyz = np.median(np.array([x["xyz"] for _, x in items]), 0)
            fixtures[fid] = {"fixture_id": fid, "kind": kind, "name": name, "n_intervals": len(items), "confidence": round(statistics.median([float(x["confidence"] or 0) for _, x in items]), 3),
                             "evidence_frames": sorted({x["frame"] for _, x in items})[:8], "supported_intervals": [eid for eid, _ in items], "supported_objects": sorted({x["object"] for _, x in items}),
                             "position_world": [round(float(v), 4) for v in xyz], "representative_point": "median resting position of the objects Gemini said rest on it (NOT the fixture's own geometry)"}
            for eid, _ in items: per_iv[eid]["fixture_id"] = fid
        (cd / "fixtures.json").write_text(json.dumps({"sample_id": s["sample_id"], "model": "gcp/google/gemini-4-argon", "fixtures": fixtures, "intervals": per_iv}, indent=1, ensure_ascii=False))
        print(f"  fixtures: {len(fixtures)} from {len(per_iv)} intervals", flush=True)
    print("FIXTURES DONE", flush=True)


if __name__ == "__main__":
    main()
