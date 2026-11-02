"""verification_policy.json:每个 source 的初始 verification + review CSV 回填。"""
import csv, hashlib, json
from pathlib import Path
import p2config as P

DEFAULT = {
    "policy_version": P.POLICY_VERSION,
    "default": {"status": "needs_verification", "method": None},
    "sources": {
        "hdepic.*": {"status": "verified", "method": "dataset_gt"},
        "hdepic.spatial_derived": {"status": "verified", "method": "derived_from_dataset_gt_3d"},
        "hdepic.recipe_tasks": {"status": "verified", "method": "join_of_dataset_gt"},
        "hdepic.contact_rich": {"status": "verified", "method": "lexicon_on_dataset_gt_narration"},
        "ego4d.contact_rich": {"status": "verified", "method": "lexicon_on_dataset_gt_narration"},
        "hdepic_e.*": {"status": "verified", "method": "dataset_gt"},                     # Method E 样本:官方 step / narration / sound
        "hdepic_e.gemini_subgoal": {"status": "needs_verification", "method": None},     # Gemini 切的 sub-goal:模型候选(contract 可 accept_unverified_sources 放行锚定)
        "hdepic_e.gemini_next": {"status": "needs_verification", "method": None},        # 最终截断参考 "step complete" + sub-goal 干扰项:规则派生自模型候选
        "aea_p.*": {"status": "needs_verification", "method": None},           # 10-27 晚 AEA protocol clip:goal / 步骤 / caption / 声音 / SAM3 3D 全是模型或 legacy,contract accept_unverified_sources 放行
        "egoplan.*": {"status": "verified", "method": "dataset_gt"},        # EgoPlan-Bench2 官方(GPT-4 生成 + 人工核验)goal / 步骤 / 下一步
        "egoplan.geo3d_da3_sam3": {"status": "needs_verification", "method": None},   # DA3+SAM3 纯视频 3D 估计:模型预测,只有人工 review ok 才 verified(精确 source 优先于 egoplan.*)
        "ego4d.*": {"rule": "ego4d_provenance", "human": "verified/dataset_gt",
                    "human-curated": "verified/dataset_gt", "human-verified": "verified/dataset_gt",
                    "model-assisted + human filter": "needs_verification", "automatic": "needs_verification"},
        "hdepic_annot.*": {"rule": "x06_record"},
        "epic_kitchens.tactile": {"rule": "field", "field": "verified", "true": "verified/human_review"},
        "object_memory.*": {"status": "needs_verification", "method": None},
        "pyramid_seed43.task_timeline": {"rule": "field", "field": "status", "verified": "verified/human_review",
                                         "draft": "needs_verification", "rejected": "rejected"},
        "pyramid_seed43.plan_traj": {"rule": "field", "field": "status", "verified": "verified/human_review",
                                     "draft": "needs_verification", "rejected": "rejected"},
    },
    "reviews": [
        {"name": "pyramid_review", "file": "reviews/pyramid_review.csv", "key": ["section", "question_id"],
         "targets": "items;tactile->tactile:<T>;plan_traj->task_timeline:<task_id>",
         "verified_if": {"question_check": "ok", "answer_check": "ok", "gt_check": "ok"}, "rejected_if_any": {"gt_check": "wrong"}},
        {"name": "hdepic_annot_review", "file": "reviews/annot_review.csv", "key": ["step", "item_id"],
         "targets": "evidence annotation_id", "verified_if": {"answer": "ok"}, "rejected_if_any": {"answer": "wrong"}},
        {"name": "ego4d_annot_review", "file": "reviews/ego4d_annot_review.csv", "key": ["section", "question_id"],
         "targets": "evidence via legacy_eid", "verified_if": {"check_content": "ok", "check_time": "ok"},
         "rejected_if_any": {"check_content": "wrong"}},
        {"name": "geo3d_review", "file": "reviews/geo3d_review.csv", "key": ["section", "question_id"],
         "targets": "evidence via reviews/geo3d_review_map.json (question_id -> evidence_ids); R/S/T/F 节改 status,D 节只进 checks",
         "verified_if": {"question_check": "ok", "gt_check": "ok"}, "rejected_if_any": {"question_check": "wrong"}},
    ],
    "aggregation": "每 (reviewer,key) 取最新一行;任一 rejected -> rejected;全 verified -> verified;否则 needs_verification",
}


def write_default_policy(force=False):
    p = P.DATA / "verification_policy.json"
    if not p.exists() or force:
        p.write_text(json.dumps(DEFAULT, indent=1, ensure_ascii=False))


def load_policy():
    p = P.DATA / "verification_policy.json"
    return json.loads(p.read_text()) if p.exists() else DEFAULT


def _split(s):
    st, _, m = s.partition("/")
    return {"status": st, "method": m or None, "review_id": None}


def initial_verification(r, pol):
    src = r["provenance"].get("source", "")
    ds = r["provenance"].get("dataset", "")
    rule = pol["sources"].get(src) or pol["sources"].get(ds + ".*") or pol["default"]
    if "rule" not in rule:
        return {"status": rule["status"], "method": rule.get("method"), "review_id": None}
    if rule["rule"] == "ego4d_provenance":
        up = r["provenance"].get("upstream_provenance", "unknown")
        return _split(rule.get(up, "needs_verification"))
    if rule["rule"] == "field":
        f = rule["field"]
        v = r["value"].get(f, r["provenance"].get("raw_" + f))
        return _split(rule.get(str(v).lower(), "needs_verification"))
    if rule["rule"] == "x06_record":
        st = (r["value"].get("_verification") or {}).get("status")
        hr = (r["value"].get("_verification") or {}).get("human_review")
        if st == "contradicted":
            return {"status": "rejected", "method": "pipeline_check", "review_id": None}
        if st == "supported" and hr not in (None, "pending"):
            return {"status": "verified", "method": "pipeline_check+human_review", "review_id": None}
        return {"status": "needs_verification", "method": None, "review_id": None}
    return {"status": "needs_verification", "method": None, "review_id": None}


def load_reviews(pol=None):
    """三份 review CSV -> 归一行 [{name, key, reviewer, ts, verdict, note, raw}]。缺文件就跳过。"""
    pol = pol or load_policy()
    out = []
    for spec in pol["reviews"]:
        p = P.RAW / spec["file"]
        if not p.exists():
            continue
        with open(p, newline="") as f:
            for row in csv.DictReader(f):
                key = "|".join(str(row.get(k, "")) for k in spec["key"])
                rej = any(str(row.get(k, "")).strip() == v for k, v in spec["rejected_if_any"].items())
                ver = all(str(row.get(k, "")).strip() == v for k, v in spec["verified_if"].items())
                rid = spec["name"] + ":" + hashlib.sha1(f"{row.get('timestamp')}|{row.get('reviewer')}|{key}".encode()).hexdigest()[:10]
                out.append({"name": spec["name"], "key": key, "reviewer": row.get("reviewer"), "ts": row.get("timestamp"),
                            "verdict": "rejected" if rej else "verified" if ver else "needs_verification",
                            "note": row.get("note"), "review_id": rid, "raw": row})
    from store import write_jsonl
    write_jsonl(P.DATA / "reviews.jsonl", out)
    return out


def _aggregate(rows):
    latest = {}
    for r in rows:
        k = (r["reviewer"], r["key"])
        if k not in latest or (r["ts"] or "") > (latest[k]["ts"] or ""):
            latest[k] = r
    vs = [r["verdict"] for r in latest.values()]
    if not vs:
        return None, None
    rid = sorted(latest.values(), key=lambda r: r["ts"] or "")[-1]["review_id"]
    if "rejected" in vs:
        return "rejected", rid
    if all(v == "verified" for v in vs):
        return "verified", rid
    return "needs_verification", rid


GEO3D_SRC = "egoplan.geo3d_da3_sam3"


def load_geo3d_review_map():
    """reviews/geo3d_review_map.json(审核站 build.py 写)-> {evidence_id: [(section, question_id), ...]}。缺文件返回 {}。"""
    import collections
    p = P.REVIEWS / "geo3d_review_map.json"
    inv = collections.defaultdict(list)
    if not p.exists():
        return inv
    m = json.loads(p.read_text())
    for qid, q in (m.get("questions") or {}).items():
        for eid in q.get("evidence_ids") or []:
            inv[eid].append((q.get("section") or qid.split("-")[0], qid))
    return inv


def apply(rows, reviews, pol):
    """evidence 回填:plan_traj 节 -> task_timeline task;tactile -> tactile;hdepic_annot -> annotation_id;ego4d -> legacy;geo3d -> review_map。"""
    import collections
    n = collections.Counter()
    by_key = collections.defaultdict(list)
    for rv in reviews:
        by_key[(rv["name"], rv["key"])].append(rv)
    rmap_inv = load_geo3d_review_map()
    for r in rows:
        r["verification"] = initial_verification(r, pol) if r["verification"].get("review_id") is None else r["verification"]
        src = r["provenance"].get("source", "")
        cands = []
        if src in ("pyramid_seed43.task_timeline", "pyramid_seed43.plan_traj") and r["kind"] == "task_segment":
            cands.append(("pyramid_review", f"plan_traj|{r['value'].get('task_id')}"))
        elif src == "epic_kitchens.tactile":
            cands.append(("pyramid_review", f"tactile|{r['value'].get('sample_id')}"))
        elif src.startswith("hdepic_annot"):
            cands.append(("hdepic_annot_review", f"{r['value'].get('_step')}|{r['provenance'].get('source_record_id')}"))
        elif src == GEO3D_SRC:
            for sec, qid in rmap_inv.get(r["evidence_id"], []):
                key = ("geo3d_review", f"{sec}|{qid}")
                if sec == "D":                      # 深度序数题核的是 DA3 vs Gemini,不改 observation 的 status,只记旁路 check
                    for rv in by_key.get(key, []):
                        chk = {"method": "human_ordinal_depth", "verdict": (rv["raw"] or {}).get("question_check"), "confidence": None,
                               "reviewer": rv["reviewer"], "ts": rv["ts"], "review_id": rv["review_id"], "question_id": qid}
                        r.setdefault("checks", [])
                        if not any(c.get("review_id") == rv["review_id"] for c in r["checks"]): r["checks"].append(chk)
                else:
                    cands.append(key)
        for c in cands:
            if c in by_key:
                st, rid = _aggregate(by_key[c])
                if st:
                    r["verification"] = {"status": st, "method": "human_review", "review_id": rid}
                    if st == "rejected" and "HUMAN_REJECTED" not in r["quality_flags"]: r["quality_flags"].append("HUMAN_REJECTED")
                    n[st] += 1
    return n


def apply_items(items, reviews, pol):
    import collections
    n = collections.Counter()
    by_key = collections.defaultdict(list)
    for rv in reviews:
        if rv["name"] == "pyramid_review":
            by_key[rv["key"].split("|", 1)[1]].append(rv)
    for it in items:
        qid = it["source"].get("original_id")
        if qid in by_key:
            st, rid = _aggregate(by_key[qid])
            if st:
                it["private"]["gold_verification_status"] = st
                it["private"]["verification_method"] = "human_review"
                it["private"]["review_id"] = rid
                n[st] += 1
    return n
