"""唯一读 timeline.json / assoc_info.json 的模块。"""
import json, re, collections
from dataclasses import dataclass
from typing import Optional
import config as C

FIX_RE = re.compile(r"^(P\d\d)_([a-z]+)\.(\d+)$")


@dataclass(frozen=True)
class Ev:
    eid: str; source: str; t_start: float; t_end: float
    text: str; label: str; extra: dict
    def mid(self): return (self.t_start + self.t_end) / 2


class TimelineIndex:
    def __init__(self, video_id: str):
        self.video_id = video_id
        root = C.HDEPIC / "annotations" / video_id
        d = json.loads((root / "timeline.json").read_text())
        self.duration = d["duration_sec"]
        self.by_source = d["by_source"]
        self.events = []
        cnt = collections.Counter()
        for e in d["events"]:
            s = e["source"]; i = cnt[s]; cnt[s] += 1
            ex = e.get("extra") or {}
            if e.get("is_transition") is not None:
                ex = {**ex, "is_transition": e["is_transition"]}
            self.events.append(Ev(f"{video_id}:{s}:{i}", s, e["t_start"], e["t_end"],
                                  e.get("text") or "", e.get("label") or "", ex))
        self.sounds = [e for e in self.events
                       if e.source == "sound" and e.label not in C.SKIP_SOUNDS]
        self.narrations = [e for e in self.events if e.source == "narration"]
        self.movements = [e for e in self.events if e.source == "movement"]
        self.transitions = [m for m in self.movements
                            if m.extra.get("is_transition") and " -> " in m.label
                            and "mid-air" not in m.label]
        self.by_sound_label = collections.defaultdict(list)
        for s in self.sounds:
            self.by_sound_label[s.label].append(s)
        self._by_eid = {e.eid: e for e in self.events}

        # 视觉可见区间：assoc_info 的 tracks[].time_segment
        a = json.loads((root / "raw" / "assoc_info.json").read_text())
        a = a[list(a)[0]]
        self.segs = []            # (t0, t1, 物体名)
        for _, o in a.items():
            nm = (o.get("name") or "").strip()
            for tr in o.get("tracks", []):
                ts = tr.get("time_segment")
                if nm and ts and len(ts) == 2:
                    self.segs.append((ts[0], ts[1], nm))
        self.segs.sort()
        self.object_names = sorted({n for _, _, n in self.segs})

    # ---- 查询 ----
    def ev(self, eid): return self._by_eid[eid]

    def visible_at(self, t):
        """该时刻视觉上可见的物体名（assoc track 覆盖 t）。"""
        return sorted({n for a, b, n in self.segs if a <= t <= b})

    def visible_in(self, t0, t1):
        return sorted({n for a, b, n in self.segs if a < t1 and b > t0})

    def in_window(self, t0, t1, source=None):
        return [e for e in self.events
                if e.t_start < t1 and e.t_end > t0 and (source is None or e.source == source)]

    def sounds_between(self, t0, t1, label=None):
        return [s for s in self.sounds if s.t_start < t1 and s.t_end > t0
                and (label is None or s.label == label)]

    def fixture_kind(self, name) -> Optional[str]:
        if not name or name == "mid-air": return None
        m = FIX_RE.match(name)
        return m.group(2) if m else None

    def fixture_pretty(self, name) -> Optional[str]:
        k = self.fixture_kind(name)
        return C.FIXTURE_NAME.get(k) if k else None

    def nameable_sounds(self, top=22):
        c = collections.Counter(s.label for s in self.sounds)
        return {l for l, _ in c.most_common(top)}
