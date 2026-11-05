import os
"""media_manifest 行 <-> 实际媒体;裁剪复用 bench/clips.py(加 src/vf/out_dir 后可跨数据集)。"""
import json, subprocess
from pathlib import Path
import p2config as P
import clips


def probe_full(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
                        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    out = {"duration_sec": float(d["format"]["duration"]), "resolution": None, "fps": None,
           "audio": {"present": False, "sample_rate": None, "channels": None}}
    for s in d["streams"]:
        if s["codec_type"] == "video" and out["resolution"] is None:
            out["resolution"] = [s["width"], s["height"]]
            num, den = s.get("r_frame_rate", "0/1").split("/")
            out["fps"] = round(int(num) / int(den), 3) if int(den) else None
        if s["codec_type"] == "audio":
            out["audio"] = {"present": True, "sample_rate": int(s.get("sample_rate") or 0), "channels": s.get("channels")}
    return out


def _vf(row):
    w, h = (row.get("resolution") or [P.CLIP_SIZE, P.CLIP_SIZE])
    if w == h:
        return f"scale={P.CLIP_SIZE}:{P.CLIP_SIZE}"
    return f"scale=-2:{P.CLIP_SIZE}" if w >= h else f"scale={P.CLIP_SIZE}:-2"


def _out_dir(row):
    if row["dataset"] == "hdepic":
        return None                      # 继续用 output/_shared/clips/<vid>/
    return P.MEDIA / row["dataset"] / row["video_id"]


def materialize(ref, store, force=False):
    """ref = {media_id, windows:[[a,b],...], variant?}. 返回 {path, windows, time_map, duration}。"""
    row = store.media(ref["media_id"])
    if row is None:
        raise KeyError(f"media_id {ref['media_id']} not in manifest")
    if row["kind"] == "precut_clip":
        return {"path": Path(row["path"]), "windows": None, "time_map": {"kind": "precut", "time_base": "precut_clip_seconds"},
                "duration": row.get("duration_sec")}
    wins = [[float(a), float(b)] for a, b in ref["windows"]]
    src, vf, out_dir = Path(os.path.expandvars(row["path"])), _vf(row), _out_dir(row)
    if ref.get("variant") == "frame":                        # 11-02 v24 L1:单帧 jpg(窗口起点那一帧),可叠加字母框
        import v24 as _V24
        t = wins[0][0]; boxes = ref.get("boxes") or None
        fp = _V24.frame_path(row["video_id"], t, boxes)
        _V24.render_frame(src, t, fp, boxes=boxes)
        return {"path": fp, "windows": wins, "time_map": {"kind": "frame", "time_base": "frame", "segments": [{"clip_start": 0.0, "clip_end": 0.0, "abs_start": t}]}, "duration": 0.0, "image": True, "flags": []}
    silent = not ((row.get("audio") or {}).get("present", True))
    if len(wins) == 1:
        a, b = wins[0]
        path = clips.ensure_clip(row["video_id"], a, b, force=force, src=src, vf=vf, out_dir=out_dir, silent_audio=silent)
    else:
        path = clips.ensure_episodes(row["video_id"], [tuple(w) for w in wins], force=force, src=src, vf=vf, out_dir=out_dir, silent_audio=silent)
    if ref.get("variant") == "mute":
        path = muted(path)
    if ref.get("variant") == "aonly":                        # 11-04 v30:audio-only 条件 = 画面换成等长纯黑,音轨原样
        path = audio_only(path)
    segs, acc = [], 0.0
    for a, b in wins:
        segs.append({"clip_start": round(acc, 3), "clip_end": round(acc + (b - a), 3), "abs_start": a})
        acc += b - a
    return {"path": path, "windows": wins,
            "time_map": {"kind": "concat" if len(wins) > 1 else "single", "time_base": "clip_local_seconds", "segments": segs},
            "duration": round(acc, 3), "flags": (["NO_SOURCE_AUDIO"] if silent else []) + ({"mute": ["VIDEO_ONLY"], "aonly": ["AUDIO_ONLY"]}.get(ref.get("variant") or "", []))}


def audio_only(path):
    """11-04 v30:黑画面(同分辨率 / 帧率)+ 原音轨,容器仍是 mp4(Gemini / OpenRouter 内联视频都能听)。"""
    out = Path(str(path)[:-4] + "_aonly.mp4")
    if not out.exists():
        pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0", str(path)],
                            capture_output=True, text=True, check=True).stdout.strip().split(",")
        w, h, fps = pr[0], pr[1], pr[2]
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(path), "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={fps}",
                        "-map", "1:v:0", "-map", "0:a:0", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)],
                       check=True, capture_output=True)
    return out


def muted(path):
    out = Path(str(path)[:-4] + "_mute.mp4")
    if not out.exists():
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-i", str(path), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)],
                       check=True, capture_output=True)
    return out


def to_abs_time(ref_or_windows, t_clip):
    wins = ref_or_windows["windows"] if isinstance(ref_or_windows, dict) else ref_or_windows
    return clips.clip_to_abs([tuple(w) for w in wins], t_clip)


def to_clip_time(ref_or_windows, t_abs):
    wins = ref_or_windows["windows"] if isinstance(ref_or_windows, dict) else ref_or_windows
    return clips.abs_to_clip([tuple(w) for w in wins], t_abs)


def validate_ref(ref, store, cutoff=None, max_windows=2, max_len=None, min_len=10.0):
    e = []
    row = store.media(ref.get("media_id"))
    if row is None:
        return [f"unknown media_id {ref.get('media_id')}"]
    wins = ref.get("windows") or []
    if row["kind"] == "precut_clip":
        D = row.get("duration_sec") or 0
        for w in wins:
            if not (len(w) == 2 and abs(float(w[0])) < 0.6 and abs(float(w[1]) - D) < 0.6):
                e.append(f"precut clip: only the whole clip [0, {D:.1f}] is allowed, got {w}")
        return e
    if not wins: e.append("no windows")
    if len(wins) > max_windows: e.append(f"more than {max_windows} windows")
    D = row.get("duration_sec") or 1e9
    for w in wins:
        if not (isinstance(w, (list, tuple)) and len(w) == 2): e.append(f"bad window {w}"); continue
        a, b = float(w[0]), float(w[1])
        if a < 0 or b > D + 0.5 or b <= a: e.append(f"window out of range {w}")
        if max_len and b - a > max_len + 0.01: e.append(f"window longer than {max_len}s: {w}")
        if min_len and b - a < min_len - 0.01: e.append(f"window shorter than {min_len}s: {w}")
        if cutoff is not None and b > cutoff + 0.01: e.append(f"window {w} extends past observation_cutoff {cutoff}")
    return e
