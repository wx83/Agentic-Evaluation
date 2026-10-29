"""Adapter 接口:每个原始来源 -> media rows / evidence records / coverage / items。"""
from pathlib import Path


def record(*, evidence_id, video_id, media_id, kind, domain, t0, t1, value, epistemic, modalities,
           solver_access="observed", entities=None, event_id=None, provenance=None, coverage=None,
           flags=None, time_base="source_video_seconds"):
    return {
        "evidence_id": evidence_id, "version": 1, "video_id": video_id, "media_id": media_id,
        "event_id": event_id, "kind": kind, "domain": domain,
        "time": {"start_sec": round(float(t0), 4), "end_sec": round(float(t1), 4), "time_base": time_base},
        "entities": entities or [], "value": value, "epistemic_type": epistemic,
        "modalities_supporting_fact": list(modalities), "solver_access": solver_access,
        "provenance": provenance or {},
        "verification": {"status": "needs_verification", "method": None, "review_id": None},
        "coverage": coverage or {"scope_start_sec": None, "scope_end_sec": None, "target_type": None,
                                 "completeness": "unknown"},
        "quality_flags": list(flags or []),
    }


class Adapter:
    dataset = ""

    def videos(self): return []
    def media(self): return []                 # media rows
    def coverage(self, video_id): return []    # [{source, n, coverage{...}}]
    def records(self, video_id): return iter(())
    def items(self): return iter(())
    def files_read(self): return []            # 实际读过的文件(Path),进 build_manifest


def rel_source(path):
    """真实路径 -> raw_annotations/<alias>/... 的别名路径(provenance.source_file 用)。"""
    import p2config as P
    p = str(Path(path))
    for alias, real in P.SOURCES.items():
        if p.startswith(real.rstrip("/") + "/") or p == real:
            return "raw_annotations/" + alias + p[len(real):]
    return p
