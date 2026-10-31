#!/usr/bin/env python3
"""把各来源 annotation 统一成 data/{media_manifest,evidence,items}.jsonl + 配置文件。幂等:源不变则产物逐字节不变。

  python3 build_data.py init                      # 目录 + symlink
  python3 build_data.py media                     # media_manifest.jsonl(ffprobe)
  python3 build_data.py evidence [--only hdepic,ego4d,task_timeline] [--videos a,b]
  python3 build_data.py config                    # capability_map.json(+lifecycle)/ extension_registry / verification_policy
  python3 build_data.py policy                    # 按 verification_policy 重打 verification(含 review 回填)
  python3 build_data.py items
  python3 build_data.py all
"""
import argparse, hashlib, json, os, sys, time, collections
from pathlib import Path
import p2config as P
import schema, ids
from store import read_jsonl, write_jsonl

ADAPTERS = {}


def _adapters(only=None, videos=None):
    from adapters.hdepic import HdEpic
    from adapters.task_timeline import TaskTimeline
    from adapters.ego4d import Ego4d
    from adapters.spatial_derived import SpatialDerived
    from adapters.tactile import Tactile
    from adapters.contact_rich import ContactRich
    from adapters.egoplan import Egoplan
    from adapters.hdepic_methode import HdEpicE
    from adapters.hdepic_e_spatial import HdEpicESpatial
    from adapters.hdepic_e_spatial_derived import HdEpicESpatialDerived
    from adapters.aea_protocol import AeaProtocol
    from adapters.aea_p_spatial import AeaPSpatial
    reg = {"hdepic_e": lambda: HdEpicE(videos),
           "aea_p": lambda: AeaProtocol(videos),                 # 10-27 晚:AEA protocol clip(goal / 步骤 / caption / 声音)
           "aea_p_spatial": lambda: AeaPSpatial(videos),         # 10-27 晚:SAM3+MPS fixture / 转移 / spatial_relation / 声源方向 / 视线(在 aea_p 之后单独跑)
           "hdepic_e_spatial": lambda: HdEpicESpatial(videos),     # 10-27:官方 assoc/mask 搬运 + 可见轨迹 + mask 锚点 + gaze priming + 活动段
           "hdepic_e_spatial_derived": lambda: HdEpicESpatialDerived(videos),   # 10-27:派生 spatial_relation(nearest / farthest / order / side)
           "hdepic": lambda: HdEpic(videos and [v for v in videos if v in P.HDEPIC_VIDEOS]),
           "contact": lambda: ContactRich(videos),
           "tactile": lambda: Tactile(videos),
           "spatial": lambda: SpatialDerived(videos and [v for v in videos if v in P.HDEPIC_VIDEOS]),
           "task_timeline": lambda: TaskTimeline(videos and [v for v in videos if v in P.HDEPIC_VIDEOS]),
           "ego4d": lambda: Ego4d(videos and [v for v in videos if v in P.EGO4D_VIDEOS]),
           "egoplan": lambda: Egoplan(videos)}
    try:
        from adapters.geo3d import Geo3d
        reg["geo3d"] = lambda: Geo3d(videos)          # DA3+SAM3 3D 估计(10-15),读 output/pyramid_v2/geo3d/<sid>/records_final.jsonl
    except ImportError:
        pass
    names = [n for n in (only or list(reg)) if n in reg]
    return {n: reg[n]() for n in names}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()[:16]


def manifest_load():
    p = P.DATA / "build_manifest.json"
    return json.loads(p.read_text()) if p.exists() else {"builds": {}}


def manifest_save(m):
    (P.DATA / "build_manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False, sort_keys=True))


def cmd_init(a):
    P.ensure_dirs()
    for alias, real in P.SOURCES.items():
        link = P.RAW / alias
        if link.is_symlink() or link.exists():
            continue
        os.symlink(real, link)
    for alias in P.SOURCES:
        print(f"  {alias:16s} -> {os.readlink(P.RAW / alias)}  {'ok' if (P.RAW / alias).exists() else 'MISSING'}")


def cmd_media(a):
    import media as M
    rows = []
    for name, ad in _adapters(a.only, a.videos).items():
        for r in ad.media():
            pf = M.probe_full(r["path"])
            r["resolution"] = r.get("resolution") or pf["resolution"]
            r["fps"] = r.get("fps") or pf["fps"]
            r["duration_sec"] = r.get("duration_sec") or pf["duration_sec"]
            r["audio"] = pf["audio"]
            r["probe_duration_sec"] = pf["duration_sec"]
            errs = schema.validate_media(r)
            assert not errs, (r["media_id"], errs)
            rows.append(r)
    # 保留其它 adapter 已有的行
    old = {m["media_id"]: m for m in read_jsonl(P.DATA / "media_manifest.jsonl")}
    for r in rows:
        old[r["media_id"]] = r
    out = sorted(old.values(), key=lambda m: (m["dataset"], m["media_id"]))
    write_jsonl(P.DATA / "media_manifest.jsonl", out)
    print(f"media_manifest: {len(out)} rows ({len(rows)} rebuilt)")


def _resolve_derived(records):
    by_leg = {r["provenance"].get("legacy_eid"): r["evidence_id"] for r in records if r["provenance"].get("legacy_eid")}
    miss = 0
    for r in records:
        leg = r["provenance"].pop("derived_from_legacy", None)
        if leg:
            got = [by_leg.get(x) for x in leg]
            miss += sum(1 for g in got if g is None)
            r["provenance"]["derived_from"] = [g for g in got if g]
            if any(g is None for g in got):
                r["quality_flags"].append("DERIVED_FROM_UNRESOLVED")
    return miss


def cmd_evidence(a):
    import policy
    t0 = time.time()
    ads = _adapters(a.only, a.videos)
    new, files = [], []
    counts = collections.Counter()
    for name, ad in ads.items():
        for vid in ad.videos():
            n = 0
            for r in ad.records(vid):
                errs = schema.validate_evidence(r)
                if errs:
                    raise SystemExit(f"{name}/{vid}: invalid record {r['evidence_id']}: {errs}")
                new.append(r); n += 1
            counts[(name, vid)] = n
        files += ad.files_read()
    # derived_from(task_step 的 eids)-> 新 id
    old_all = read_jsonl(P.DATA / "evidence.jsonl")
    old = {r["evidence_id"]: r for r in old_all}
    rebuilt_videos = {(r["provenance"]["dataset"], r["video_id"]) for r in new}
    rebuilt_sources = {r["provenance"]["source"] for r in new}
    keep = [r for r in old_all if not ((r["provenance"]["dataset"], r["video_id"]) in rebuilt_videos
                                       and r["provenance"]["source"] in rebuilt_sources)]
    miss = _resolve_derived(new + keep)
    seen = collections.Counter()
    ndup = 0
    for r in new:
        k = r["evidence_id"]; seen[k] += 1
        if seen[k] > 1:                      # 上游完全重复的记录:加序号后缀,打 flag(顺序 = 源文件顺序,源不变即稳定)
            r["evidence_id"] = f"{k}~{seen[k]}"; r["quality_flags"].append("DUPLICATE_SOURCE_RECORD"); ndup += 1
    if ndup:
        print(f"  {ndup} duplicate source records renamed with ~n suffix")
    # versioning
    archive, bumped = [], 0
    for r in new:
        ch = ids.content_hash(r); r["content_hash"] = ch
        o = old.get(r["evidence_id"])
        if o is None:
            r["version"] = 1
        elif o.get("content_hash") == ch:
            r["version"] = o["version"]
            r["verification"] = o["verification"]
        else:
            r["version"] = o["version"] + 1; bumped += 1; archive.append(o)
    pol = policy.load_policy()
    stamped = 0
    for r in new:
        if r["verification"].get("method") in (None, "dataset_gt", "pipeline_status") or r["verification"].get("review_id") is None:
            r["verification"] = policy.initial_verification(r, pol); stamped += 1
    rows = sorted(new + keep, key=lambda r: (r["provenance"]["dataset"], r["video_id"], r["time"]["start_sec"], r["kind"], r["evidence_id"]))
    write_jsonl(P.DATA / "evidence.jsonl", rows)
    if archive:
        with open(P.DATA / "evidence_archive.jsonl", "a") as f:
            for o in archive:
                f.write(json.dumps(o, ensure_ascii=False, sort_keys=True) + "\n")
    m = manifest_load()
    m["builds"][time.strftime("%Y-%m-%dT%H:%M:%S")] = {
        "cmd": "evidence", "only": a.only, "videos": a.videos, "n_new": len(new), "n_total": len(rows), "bumped": bumped,
        "derived_unresolved": miss, "files": {str(f): {"sha": sha(f), "mtime": os.path.getmtime(f)} for f in sorted(set(files))},
        "seconds": round(time.time() - t0, 1)}
    manifest_save(m)
    print(f"evidence: {len(rows)} rows total, {len(new)} rebuilt, {bumped} version bumps, {miss} unresolved derived refs, {time.time()-t0:.0f}s")
    by = collections.Counter((r["provenance"]["dataset"], r["kind"], r["verification"]["status"]) for r in rows)
    for (ds, k, st), n in sorted(by.items()):
        print(f"  {ds:7s} {k:28s} {st:18s} {n}")


def cmd_config(a):
    import capmap
    capmap.write_capability_map()
    reg_p = P.DATA / "extension_registry.json"
    if not reg_p.exists() or a.force:
        reg = {"registry_version": P.REGISTRY_VERSION, "note": "新 skill 默认 provisional、未启用;启用靠 run_contract.extension_registry.enabled_skills。不覆盖 legacy mapping。",
               "skills": {
                   "explicit_statement": {"layer": "L1", "domain": "human.communication", "requires_kinds": ["utterance"], "status": "provisional"},
                   "participant_presence": {"layer": "L1", "domain": "human.social", "requires_kinds": ["person_talking", "person_looking"], "status": "provisional"},
                   "object_recognition": {"layer": "L1", "domain": "physical.objects_properties", "requires_kinds": ["visual_query_track", "object_parts_attributes", "hand_object_interaction"], "status": "provisional"},
                   "utterance_speaker_binding": {"layer": "L2", "domain": "human.communication", "requires_kinds": ["utterance", "person_talking"], "status": "provisional"},
                   "explicit_preference_statement": {"layer": "L3", "domain": "human.goals_preferences", "requires_kinds": ["utterance"], "status": "provisional"},
                   "hand_object_role": {"layer": "L2", "domain": "physical.dynamics", "requires_kinds": ["hand_object_role"], "status": "provisional"},
                   "hand_object_interaction_recognition": {"layer": "L2", "domain": "physical.dynamics", "requires_kinds": ["hand_object_interaction", "action_scene_graph"], "status": "merged", "note": "v3 并入 action_recognition(capability_map),不再单列"},
                   "object_attribute_visible": {"layer": "L1", "domain": "physical.objects_properties", "requires_kinds": ["object_visible_track"], "status": "provisional", "note": "可见属性(颜色 / 材质 / 大小),来自 HD-EPIC 物体名里的属性词"},
                   "hand_used": {"layer": "L1", "domain": "physical.dynamics", "requires_kinds": ["action_narration"], "status": "provisional", "note": "动作用的是哪只手(narration hands 字段)"},
                   "object_location_at_time": {"layer": "L1", "domain": "physical.spatial", "requires_kinds": ["object_location_transition"], "status": "provisional", "note": "放下那一刻物体在哪类 fixture 上(单帧位置,capability_map 的例外条款归 L1)"},
                   "tactile_check_recognition": {"layer": "L1", "domain": "physical.objects_properties", "requires_kinds": ["tactile_property_episode"], "status": "provisional", "note": "看得见的检查动作在查什么触觉属性(捏 = 软硬,拧 = 松紧);属性值本身不在 L1"},
                   "needs_touch_awareness": {"layer": "L3", "domain": "physical.objects_properties", "requires_kinds": ["tactile_property_episode"], "status": "provisional", "note": "控制项:该状态只有摸才知道,正确回答是「无法从视频 / 音频判断」;测模型会不会过度自信"},
                   "tactile_aware_planning": {"layer": "L4", "domain": "physical.objects_properties", "requires_kinds": ["tactile_property_episode"], "status": "provisional", "note": "给目标与当前状态,计划必须包含必要的触觉检查步骤(或等价的检测手段),并说明跳过的后果"},
                   "contact_action_recognition": {"layer": "L1", "domain": "physical.dynamics", "requires_kinds": ["contact_rich_action"], "status": "provisional", "note": "contact-rich:看得见的接触动作是什么(捏 / 拧 / 揉 / 按 / 刮 / 倒),对什么物体"},
                   "contact_feedback_binding": {"layer": "L2", "domain": "physical.dynamics", "requires_kinds": ["contact_rich_action"], "status": "provisional", "note": "contact-rich:这个 event 里的接触动作在感知什么反馈、event 结束时物体状态如何"},
                   "contact_state_inference": {"layer": "L3", "domain": "physical.objects_properties", "requires_kinds": ["contact_rich_action"], "status": "provisional", "note": "contact-rich:从接触线索推断隐藏状态(软硬 / 松紧 / 熟度),并判断该状态能否从视频 / 音频确定"},
                   "contact_conditioned_next_action": {"layer": "L4", "domain": "task.structure", "requires_kinds": ["contact_rich_action"], "status": "provisional", "note": "contact-rich:给目标与接触反馈,选下一步(记录的下一动作只是一个参考,rubric 接受其它合理选择)"},
               }}
        reg_p.write_text(json.dumps(reg, indent=1, ensure_ascii=False))
    import policy
    policy.write_default_policy(force=a.force)
    print("config written:", [p.name for p in (P.DATA / "capability_map.json", reg_p, P.DATA / "verification_policy.json")])


def cmd_policy(a):
    import policy
    pol = policy.load_policy()
    rows = read_jsonl(P.DATA / "evidence.jsonl")
    reviews = policy.load_reviews()
    n = policy.apply(rows, reviews, pol)
    write_jsonl(P.DATA / "evidence.jsonl", rows)
    print(f"policy: restamped {len(rows)} evidence rows; review promotions/demotions: {dict(n)}")
    items = read_jsonl(P.DATA / "items.jsonl")
    if items:
        n2 = policy.apply_items(items, reviews, pol)
        write_jsonl(P.DATA / "items.jsonl", items)
        print(f"policy: items {dict(n2)}")


def cmd_items(a):
    import items as IT
    rows = IT.build(a.only)
    write_jsonl(P.DATA / "items.jsonl", rows)
    print(f"items: {len(rows)}")
    print("  ", collections.Counter(r["source"]["benchmark"] for r in rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["init", "media", "evidence", "config", "policy", "items", "all"])
    ap.add_argument("--only", type=lambda s: s.split(","), default=None)
    ap.add_argument("--videos", type=lambda s: s.split(","), default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    P.ensure_dirs()
    if a.cmd == "all":
        cmd_init(a); cmd_config(a); cmd_media(a); cmd_evidence(a); cmd_items(a); cmd_policy(a)
    else:
        globals()["cmd_" + a.cmd](a)


if __name__ == "__main__":
    main()
