"""读 data/*.jsonl 并建索引。记录只读;检索时的 solver_access 改写在副本上做。"""
import json, bisect, collections
from pathlib import Path
import p2config as P


def read_jsonl(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def write_jsonl(p, rows):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


ACCEPT_SOURCES = set()     # 10-23:contract.accept_unverified_sources —— 这些 source 的 needs_verification 记录在检索 / 锚定时按 verified 对待(记录本身状态不变,报告标 provisional)


def _status_ok(r, status):
    if r["verification"]["status"] == status:
        return True
    return status == "verified" and r["verification"]["status"] == "needs_verification" and r["provenance"].get("source") in ACCEPT_SOURCES


class Store:
    def __init__(self, data_dir=None):
        self.dir = Path(data_dir or P.DATA)
        self._ev = None; self._media = None; self._items = None
        self._cap = None; self._reg = None

    # ---- lazy loads ----
    @property
    def evidence(self):
        if self._ev is None:
            self._ev = {r["evidence_id"]: r for r in read_jsonl(self.dir / "evidence.jsonl")}
            self._index()
        return self._ev

    def _index(self):
        self.by_video = collections.defaultdict(list)
        self.by_kind = collections.defaultdict(list)
        self.by_legacy = {}
        self.by_entity = collections.defaultdict(list)
        self.by_event = collections.defaultdict(list)
        for r in self._ev.values():
            self.by_video[r["video_id"]].append(r)
            self.by_kind[r["kind"]].append(r)
            leg = (r.get("provenance") or {}).get("legacy_eid")
            if leg:
                self.by_legacy[leg] = r
            for e in r.get("entities") or []:
                self.by_entity[e.get("entity_id")].append(r)
            if r.get("event_id"):
                self.by_event[r["event_id"]].append(r)
        self._starts = {}
        for v, rs in self.by_video.items():
            rs.sort(key=lambda r: (r["time"]["start_sec"], r["time"]["end_sec"], r["kind"], r["evidence_id"]))
            self._starts[v] = [r["time"]["start_sec"] for r in rs]

    @property
    def media_rows(self):
        if self._media is None:
            self._media = {m["media_id"]: m for m in read_jsonl(self.dir / "media_manifest.jsonl")}
        return self._media

    @property
    def items(self):
        if self._items is None:
            self._items = read_jsonl(self.dir / "items.jsonl")
        return self._items

    @property
    def capmap(self):
        if self._cap is None:
            self._cap = json.loads((self.dir / "capability_map.json").read_text())
        return self._cap

    @property
    def registry(self):
        if self._reg is None:
            p = self.dir / "extension_registry.json"
            self._reg = json.loads(p.read_text()) if p.exists() else {"registry_version": P.REGISTRY_VERSION, "enabled_skills": [], "skills": {}}
        return self._reg

    # ---- queries ----
    def get(self, evidence_id, version=None):
        r = self.evidence.get(evidence_id)
        if r is not None and version is not None and r["version"] != version:
            return None
        return r

    def media(self, media_id):
        return self.media_rows.get(media_id)

    def media_of_video(self, video_id):
        rows = [m for m in self.media_rows.values() if m["video_id"] == video_id and m["kind"] == "source_video"]
        if not rows:
            return None
        # 10-27:同一视频既有 legacy(hdepic)又有 Method E(hdepic_e)media 行时优先 hdepic_e —— 否则 task 数据集的 per_step / sample_id 规格不生效(task 08 的教训)
        for pref in ("hdepic_e", "aea_p"):
            m = next((m for m in rows if m.get("dataset") == pref), None)
            if m: return m
        return rows[0]

    def videos(self, dataset=None):
        return sorted({r["video_id"] for r in self.evidence.values()
                       if dataset is None or r["provenance"].get("dataset") == dataset})

    def in_window(self, video_id, t0, t1, kinds=None, status=None):
        """与 [t0,t1] 相交的记录(instant 记录按 start 判)。"""
        _ = self.evidence
        rs = self.by_video.get(video_id, [])
        out = []
        for r in rs:
            a, b = r["time"]["start_sec"], r["time"]["end_sec"]
            if a > t1:
                break
            if b < t0 and not (a == b and t0 <= a <= t1):
                continue
            if a == b and not (t0 <= a <= t1):
                continue
            if kinds and r["kind"] not in kinds:
                continue
            if status and not _status_ok(r, status):
                continue
            out.append(r)
        return out

    def of_kind(self, video_id, kind, status="verified"):
        _ = self.evidence
        return [r for r in self.by_video.get(video_id, []) if r["kind"] == kind and (status is None or _status_ok(r, status))]

    def coverage(self, video_id, source):
        m = self.media_of_video(video_id)
        if not m:
            return None
        for s in m.get("annotation_sources", []):
            if s["source"] == source:
                return s
        return None

    def items_for(self, video_id, skill=None):
        return [it for it in self.items if it["video_id"] == video_id and (skill is None or it.get("original_subtype") == skill)]
