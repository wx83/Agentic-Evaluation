"""稳定 ID:evidence_id 优先用上游 id,没有就内容 hash;legacy_eid 保留 timeline_index 的位置 id 以便 join。"""
import hashlib, json


def _h(s, n=12):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n]


def evidence_id(dataset, video_id, source, upstream_id=None, *, t0=None, t1=None, label="", text=""):
    key = str(upstream_id) if upstream_id not in (None, "") else \
        "h" + _h(f"{video_id}|{source}|{float(t0):.3f}|{float(t1):.3f}|{label}|{text}")
    return f"{dataset}:{video_id}:{source}:{key}"


def legacy_eid(video_id, source, i):
    return f"{video_id}:{source}:{i}"


def content_hash(rec):
    """去掉 version / verification 后的规范化 hash;用来判断源记录是否变化。"""
    d = {k: v for k, v in rec.items() if k not in ("version", "verification")}
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def item_id(source, video_id, original_id):
    return f"it:{source}:{video_id}:{original_id}"


def candidate_id(run_id, layer, turn, ctx_hash):
    return f"cand:{run_id}:{layer}:{turn:03d}:{ctx_hash[:8]}"


def cluster_id(skill, video_id, t0, t1, core_ids):
    return _h(f"{skill}|{video_id}|{t0:.2f}|{t1:.2f}|{','.join(sorted(core_ids))}", 16)
