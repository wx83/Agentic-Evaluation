"""抽帧:任务窗口 [t0,t1] 按 2 fps 从原视频抽 jpg(宽 1008),帧 k ↔ mp4 帧 round(t0*30)+15k,t_abs = t0 + k/2。不去畸变(pinhole 假设)。
  --meta-only:不动 jpg,只给 frames.json 补 ffprobe 时间元数据(fps 恒定性、time_base、视频 / 音频 start_time、t_abs 基准、容差)(10-15 spec §5.1)。"""
import json, subprocess, argparse, time
from pathlib import Path
from . import cfg


def probe_time(video):
    """ffprobe 视频 / 音频流的时间元数据。"""
    def q(sel, ents):
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries", f"stream={ents}", "-of", "json", str(video)], capture_output=True, text=True).stdout
        st = (json.loads(out or "{}").get("streams") or [{}])[0]; return st
    v = q("v:0", "r_frame_rate,avg_frame_rate,time_base,start_time,nb_frames,duration"); a = q("a:0", "start_time,sample_rate,channels")
    def fr(x):
        try: n, d = str(x).split("/"); return float(n) / float(d)
        except Exception: return None
    rfr, afr = fr(v.get("r_frame_rate")), fr(v.get("avg_frame_rate"))
    nb = int(v["nb_frames"]) if v.get("nb_frames") not in (None, "N/A") else None; dur = float(v["duration"]) if v.get("duration") not in (None, "N/A") else None
    const = bool(rfr and afr and abs(rfr - afr) < 1e-6 and (nb is None or dur is None or abs(nb / rfr - dur) < 0.1))
    vs = float(v.get("start_time") or 0.0); as_ = float(a.get("start_time") or 0.0) if a else None
    return {"source_fps": rfr, "avg_fps": afr, "fps_constant": const, "video_time_base": v.get("time_base"), "nb_frames": nb, "duration_s": dur,
            "video_start_time_s": vs, "audio_start_time_s": as_, "av_offset_s": (round(vs - as_, 4) if as_ is not None else None),
            "audio": ({"sample_rate": a.get("sample_rate"), "channels": a.get("channels")} if a else None)}


def time_meta(video, fps=cfg.FPS):
    pt = probe_time(video)
    return {**pt, "t_abs_basis": "source_video_seconds = mp4_frame / source_fps (EgoPlan frame-index convention; stream start_time NOT added)",
            "sampling": {"fps": fps, "t_abs": "t0 + k / fps", "mp4_frame": "round(t0 * 30) + (30 / fps) * k", "assumes_constant_fps": True},
            "time_uncertainty_s": round(0.5 / fps, 3), "rest_tolerance": {"time_pad_s": cfg.REST_PAD, "radius_m": cfg.STATIC_R}}


def extract_frames(video, t0, t1, out_dir, fps=cfg.FPS, width=cfg.FRAME_W):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.jpg"): f.unlink()
    step = int(round(30 / fps))
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", str(video),
                    "-vf", f"select=not(mod(n\\,{step})),scale={width}:-2", "-fps_mode", "vfr", "-q:v", "2", "-start_number", "0", str(out_dir / "%05d.jpg")], check=True)
    files = sorted(out_dir.glob("*.jpg"))
    frames = [{"k": k, "file": f.name, "t_abs": round(t0 + k / fps, 3), "mp4_frame": int(round(t0 * 30)) + step * k} for k, f in enumerate(files)]
    return frames


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--samples", nargs="*", default=["all"]); ap.add_argument("--meta-only", action="store_true"); a = ap.parse_args()
    for s in cfg.samples(a.samples):
        cd = cfg.clip_dir(s["sample_id"]); t0, t1 = s["window"]; video = cfg.VIDEOS / f"{s['video_id']}.mp4"
        if a.meta_only:
            fj = json.loads((cd / "frames.json").read_text()); n_before = len(fj["frames"]); old = json.dumps(fj["frames"])
            fj.update(time_meta(video)); assert json.dumps(fj["frames"]) == old and n_before == len(fj["frames"])
            (cd / "frames.json").write_text(json.dumps(fj, indent=1))
            print(f"{s['scenario']:12s} {s['sample_id'][-6:]} meta: fps {fj['source_fps']} const {fj['fps_constant']} v_start {fj['video_start_time_s']} av_off {fj['av_offset_s']} frames {n_before}", flush=True)
            continue
        tt = time.time(); fr = extract_frames(video, t0, t1, cd / "frames")
        from PIL import Image
        w, h = Image.open(cd / "frames" / fr[0]["file"]).size
        (cd / "frames.json").write_text(json.dumps({"sample_id": s["sample_id"], "video_id": s["video_id"], "t0": t0, "t1": t1, "fps": cfg.FPS,
                                                     "frame_hw": [h, w], "undistorted": False, "camera_note": "GoPro wide-angle, no calibration; pinhole assumed",
                                                     **time_meta(video), "frames": fr}, indent=1))
        print(f"{s['scenario']:12s} {s['sample_id'][-6:]} {t0:.1f}-{t1:.1f}s -> {len(fr)} frames {w}x{h} ({time.time()-tt:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
