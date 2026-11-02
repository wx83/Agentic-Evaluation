"""ffmpeg 裁剪 + 内容寻址缓存。必须重编码：-c copy 会把切点吸附到关键帧。"""
import json, subprocess, sys, hashlib
import config as C


def _box_filter(box, t0, t1):
    """把 mask_info 的 1408² bbox 换算到 SIZE²，只在证据时刻前后 ±0.35s 画出来。
    整段都画框等于把答案钉在屏幕上，物体一动框就错位。"""
    if not box or not (t0 <= box["t"] <= t1):
        return None
    k = C.SIZE / 1408.0
    x1, y1, x2, y2 = [v * k for v in box["bbox_1408"]]
    a, b = box["t"] - t0 - 0.35, box["t"] - t0 + 0.35
    return ("drawbox=x=%.0f:y=%.0f:w=%.0f:h=%.0f:color=%s:t=2:"
            "enable='between(t,%.2f,%.2f)'" % (x1, y1, x2 - x1, y2 - y1,
                                                box.get("color", "red"), max(0, a), b))


def clip_path(video_id, t0, t1, box=None, out_dir=None):
    tag = ""
    if box and t0 <= box["t"] <= t1:
        tag = "_box" + hashlib.sha1(json.dumps(box, sort_keys=True).encode()).hexdigest()[:6]
    return (out_dir or (C.CLIPS / video_id)) / f"{int(t0*1000)}_{int(t1*1000)}{tag}.mp4"


def ensure_clip(video_id, t0, t1, force=False, box=None, src=None, vf=None, out_dir=None, silent_audio=False):
    """src/vf/out_dir/silent_audio(2026-10-12 pyramid2 加):非 HD-EPIC 源、非方形视频、无音轨源(合成静音轨);不传时行为与原来完全一致。"""
    out = clip_path(video_id, t0, t1, box, out_dir)
    if out.exists() and not force:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    src = src or next((C.HDEPIC / "videos").glob(f"*/{video_id}.mp4"))
    vf = vf or f"scale={C.SIZE}:{C.SIZE}"
    bf = _box_filter(box, t0, t1)
    if bf:
        vf += "," + bf
    if silent_audio:
        cmd = ["ffmpeg", "-nostdin", "-y", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", str(src),
               "-f", "lavfi", "-t", f"{t1 - t0:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
               "-map", "0:v:0", "-map", "1:a:0", "-shortest",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
               "-pix_fmt", "yuv420p", "-vf", vf, "-r", "15",
               "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-ar", "48000",
               "-movflags", "+faststart", str(out)]
    else:
        cmd = ["ffmpeg", "-nostdin", "-y", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}",
               "-i", str(src), "-map", "0:v:0", "-map", "0:a:0",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
               "-pix_fmt", "yuv420p", "-vf", vf, "-r", "15",
               "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-ar", "48000",
               "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    probe(out, expect=t1 - t0)
    return out


def probe(p, expect=None, tol=0.30):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,codec_name",
                        "-of", "json", str(p)], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    dur = float(d["format"]["duration"])
    types = {s["codec_type"] for s in d["streams"]}
    assert "audio" in types, f"{p} 没有音轨！"
    if expect is not None:
        assert abs(dur - expect) < tol, f"{p} 时长 {dur:.2f} != 期望 {expect:.2f}"
    return dur, types


if __name__ == "__main__":
    ch = json.loads((C.SHARED / "chains.json").read_text())
    n = 0
    for c in ch["chains"]:
        for a, b in ((c["clip_start"], c["clip_end"]), (c["long_start"], c["long_end"])):
            p = ensure_clip(c["video_id"], a, b)
            dur, types = probe(p)
            n += 1
            print(f"  {p.name:22s} {dur:7.2f}s  {sorted(types)}  {p.stat().st_size/1e6:6.1f} MB")
    print(f"共 {n} 个 clip -> {C.CLIPS}")


# ---- 多片段（episodes）：长时程链的证据跨越几十分钟，单个窗口装不下 ----

def episodes_path(video_id, windows, box=None, out_dir=None):
    key = "_".join(f"{int(a*1000)}-{int(b*1000)}" for a, b in windows)
    h = hashlib.sha1((key + json.dumps(box, sort_keys=True)).encode()).hexdigest()[:8]
    return (out_dir or (C.CLIPS / video_id)) / f"ep_{h}.mp4"


def ensure_episodes(video_id, windows, box=None, force=False, src=None, vf=None, out_dir=None, silent_audio=False):
    """把 N 个窗口各自裁好再拼成一条 mp4。各片段编码参数一致，拼接可以 -c copy。
    绝对时间不再等于片内时间，题面里必须自己声明每段的绝对起点。"""
    out = episodes_path(video_id, windows, box, out_dir)
    if out.exists() and not force:
        return out
    parts = [ensure_clip(video_id, a, b, force=force, box=box, src=src, vf=vf, out_dir=out_dir, silent_audio=silent_audio) for a, b in windows]
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)],
                   check=True, capture_output=True)
    lst.unlink()
    probe(out, expect=sum(b - a for a, b in windows), tol=0.20 + 0.15 * len(windows))   # 10-28:每段 -c copy 拼接各带 ~0.14 s 余量,3-4 段时按段数放宽
    return out


def clip_to_abs(windows, t_clip):
    """片内秒 -> 原片绝对秒。落在片段边界之外时夹到最后一段。"""
    acc = 0.0
    for a, b in windows:
        d = b - a
        if t_clip <= acc + d:
            return a + (t_clip - acc)
        acc += d
    return windows[-1][1]


def abs_to_clip(windows, t_abs):
    acc = 0.0
    for a, b in windows:
        if a <= t_abs <= b:
            return acc + (t_abs - a)
        acc += b - a
    return None
