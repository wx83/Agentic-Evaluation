"""无 GT 的质量评估 + 可视化:深度自洽、位姿合理性、静止物体重投影、与 Gemini 4 空间条目一致性、arm-reach;depth_preview.mp4、trajectory_topdown.png;eval.json / summary.json。
  $HOLI -m geo3d.eval --samples all"""
import json, argparse, subprocess, collections, re
from pathlib import Path
import numpy as np
from . import cfg
from .run_da3 import load_da3
from .derive import load_tracks, to_device_cv, stem, STOP
from . import quality as Q


def depth_consistency(da3, gap=1, step=4, central=0.8):
    """帧 i 反投影 → 帧 i+gap 重投影,比较投影深度与该帧预测深度;逐对误差见 quality.depth_pairs。"""
    return Q.summarize_pairs(Q.depth_pairs(da3, gap, step, central), gap)


pose_sanity = Q.pose_sanity


def reprojection(da3, positions, frames):
    """静止区间位置投回每个可见帧,与 mask 质心像素比较(像素 / 宽度)。"""
    errs = []
    H, W = da3["meta"]["frame_hw"]; h, w = da3["meta"]["proc_hw"]
    for n, o in positions["objects"].items():
        for iv in o["intervals"]:
            P = np.array(iv["xyz"] + [1.0])
            for x in o["rows"]:
                if not (iv["t0"] <= x["t"] <= iv["t1"]) or "px" not in x: continue
                fi = x["fi"]; Xc = (da3["w2c"][fi] @ P)[:3]
                if Xc[2] <= 0.05: continue
                K = da3["K"][fi]; u = K[0, 0] * Xc[0] / Xc[2] + K[0, 2]; v = K[1, 1] * Xc[1] / Xc[2] + K[1, 2]
                errs.append(np.hypot(u - x["px"][0], v - x["px"][1]) / w)
    errs = np.array(errs)
    return {"n": int(len(errs)), "median_frac_width": (round(float(np.median(errs)), 4) if len(errs) else None), "frac_le_3pct": (round(float((errs <= 0.03).mean()), 3) if len(errs) else None)}


def gemini_agreement(s, positions, da3, frames):
    """Gemini 4 的 spatial 条目 vs DA3 推导:left_of/right_of ↔ lateral 差;near/next_to ↔ 距离 ≤ 0.8 m;in_front_of 只报告两种读法。"""
    t0 = s["window"][0]; objs = positions["objects"]; out = []; agree = collections.Counter()
    def pos_at(name, T):
        o = objs.get(name)
        if not o: return None
        rows = [x for x in o["rows"] if abs(x["t"] - T) <= 1.0]
        if not rows: return None
        return np.median(np.array([x["xyz"] for x in rows]), 0)
    def resolve(nm):
        nm = (nm or "").lower().strip()
        if nm in objs: return nm
        toks = {stem(w) for w in re.findall(r"[a-z]+", nm) if w not in STOP}
        for n in objs:
            if toks and ({stem(w) for w in re.findall(r"[a-z]+", n)} & toks): return n
        return None
    for x in s["gemini"].get("spatial") or []:
        try: T = t0 + float(x.get("t"))
        except Exception: continue
        rel = str(x.get("relation") or "").lower(); a = resolve(x.get("object")); b = resolve(x.get("reference")) if str(x.get("reference")).lower() != "wearer" else "wearer"
        row = {"t": round(T, 2), "object": x.get("object"), "relation": rel, "reference": x.get("reference"), "resolved": [a, b], "verdict": "n/a"}
        if a and (b or b == "wearer"):
            pa = pos_at(a, T); pb = pos_at(b, T) if b != "wearer" else None
            fi = int(np.argmin([abs(f["t_abs"] - T) for f in frames])); c2w = da3["c2w"][fi]
            if pa is not None and (pb is not None or b == "wearer"):
                fa, la, _, ra = to_device_cv(c2w, pa)
                if b == "wearer":
                    fb, lb, rb = 0.0, 0.0, 0.0
                else:
                    fb, lb, _, rb = to_device_cv(c2w, pb)
                if rel in ("left_of", "right_of"):
                    dl = la - lb; pred = "left_of" if dl > 0.1 else "right_of" if dl < -0.1 else "ambiguous"
                    row.update(lateral_diff_m=round(dl, 3), geo_says=pred, verdict=("agree" if pred == rel else "disagree" if pred != "ambiguous" else "ambiguous"))
                elif rel in ("near", "next_to", "close_to"):
                    d = float(np.linalg.norm(pa - pb)) if pb is not None else ra
                    row.update(dist_m=round(d, 3), verdict=("agree" if d <= cfg.NEAR_L1 else "disagree"))
                elif rel == "in_front_of":
                    row.update(forward_diff_m=round(fa - fb, 3), note="closer-to-camera reading: object nearer than reference" , verdict="reported")
                else:
                    row["verdict"] = "skipped"
            else:
                row["verdict"] = "no_position"
        agree[row["verdict"]] += 1; out.append(row)
    return {"entries": out, "counts": dict(agree)}


def arm_reach(s, positions):
    return Q.arm_reach(s, positions["objects"])


def render_depth_preview(cd, da3, tracks, fps=5):
    """RGB | turbo 深度 | mask 叠加,写 depth_preview.mp4。"""
    from PIL import Image, ImageDraw
    import matplotlib; cm = matplotlib.colormaps["turbo"]
    cd = Path(cd); fr = cfg.load_frames(cd)["frames"]; tmp = cd / "preview_frames"; tmp.mkdir(exist_ok=True)
    for f in tmp.glob("*.jpg"): f.unlink()
    D = da3["depth"]; h, w = D.shape[1:]; vmax = float(np.nanpercentile(D, 95))
    colors = [(255, 80, 80), (80, 255, 80), (80, 160, 255), (255, 200, 60), (220, 80, 255), (60, 220, 220), (255, 140, 0), (160, 255, 160)]
    names = [n for n in tracks if n != "hand"]
    for f in fr:
        fi = f["k"]; rgb = Image.open(cd / "frames" / f["file"]).convert("RGB").resize((w, h))
        dep = Image.fromarray((cm(np.clip(D[fi] / vmax, 0, 1))[..., :3] * 255).astype(np.uint8))
        ov = rgb.copy(); dr = ImageDraw.Draw(ov, "RGBA")
        for ci, n in enumerate(names):
            for inst in tracks[n]["instances"].values():
                m = inst["masks"].get(fi)
                if m is None: continue
                mm = Image.fromarray((m * 255).astype(np.uint8)).resize((w, h), Image.NEAREST)
                col = colors[ci % len(colors)]; layer = Image.new("RGBA", (w, h), col + (90,)); ov.paste(layer, (0, 0), mm)
                ys, xs = np.nonzero(np.array(mm))
                if len(xs): dr.text((int(xs.min()), max(0, int(ys.min()) - 10)), n, fill=col + (255,))
        canvas = Image.new("RGB", (w * 3, h)); canvas.paste(rgb, (0, 0)); canvas.paste(dep, (w, 0)); canvas.paste(ov.convert("RGB"), (2 * w, 0))
        ImageDraw.Draw(canvas).text((4, 4), f"t={f['t_abs']:.1f}s  depth 0-{vmax:.1f} m", fill=(255, 255, 255))
        canvas.save(tmp / f"{fi:05d}.jpg", quality=85)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-framerate", str(fps), "-i", str(tmp / "%05d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", str(cd / "depth_preview.mp4")], check=True)
    for f in tmp.glob("*.jpg"): f.unlink()
    tmp.rmdir()


def plot_topdown(cd, da3, positions, frames):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    C = da3["c2w"][:, :3, 3]; down = da3["c2w"][:, :3, 1].mean(0); down /= np.linalg.norm(down)      # 相机 y 轴均值作重力代理
    fwd0 = da3["c2w"][0, :3, 2]; e1 = fwd0 - down * (fwd0 @ down); e1 /= np.linalg.norm(e1); e2 = np.cross(e1, down)      # forward × down = left(OpenCV);原来 down × forward 是 right,y 轴标签镜像
    P = lambda X: np.stack([np.asarray(X) @ e1, np.asarray(X) @ e2], -1)
    fig, ax = plt.subplots(figsize=(6, 6)); cp = P(C); ax.plot(cp[:, 0], cp[:, 1], "-", color="#1f2937", lw=1.5, label="camera path")
    ax.scatter(cp[0, 0], cp[0, 1], c="green", s=60, zorder=5, label="start"); ax.scatter(cp[-1, 0], cp[-1, 1], c="red", s=60, zorder=5, label="end")
    for n, o in positions["objects"].items():
        for iv in o["intervals"]:
            q = P(iv["xyz"]); ax.scatter(q[0], q[1], s=40, zorder=4); ax.annotate(n, (q[0], q[1]), fontsize=8, xytext=(3, 3), textcoords="offset points")
    ax.set_aspect("equal"); ax.grid(alpha=.3); ax.set_xlabel("m (initial forward)"); ax.set_ylabel("m (initial left)"); ax.legend(fontsize=8)
    ax.set_title(f"{positions['sample_id'][-10:]}  top-down (gravity ≈ mean camera down)")
    fig.tight_layout(); fig.savefig(Path(cd) / "trajectory_topdown.png", dpi=110); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--samples", nargs="*", default=["all"]); ap.add_argument("--no-media", action="store_true"); a = ap.parse_args()
    summ = []
    for s in cfg.samples(a.samples):
        cd = cfg.clip_dir(s["sample_id"])
        if not (cd / "positions.json").exists(): print("no positions:", s["sample_id"]); continue
        da3 = load_da3(cd); frames = cfg.load_frames(cd)["frames"]; positions = json.loads((cd / "positions.json").read_text()); tracks = load_tracks(cd)
        ev = {"sample_id": s["sample_id"], "scenario": s["scenario"], "n_frames": len(frames), "da3": {k: da3["meta"][k] for k in ("seconds", "peak_gpu_gb", "scale_factor", "depth_median_m")},
              "depth_consistency_gap1": depth_consistency(da3, 1), "depth_consistency_gap5": depth_consistency(da3, 5), "pose": pose_sanity(da3, frames),
              "reprojection": reprojection(da3, positions, frames), "gemini": gemini_agreement(s, positions, da3, frames), "arm_reach": arm_reach(s, positions),
              "n_objects": len(positions["objects"]), "n_intervals": sum(len(o["intervals"]) for o in positions["objects"].values()),
              "n_moves": len(positions.get("moves", [])), "n_transitions": sum(1 for m in positions.get("moves", []) if m.get("is_transition")),
              "aliases": len(positions.get("aliases", {})), "parts": len(positions.get("parts", [])),
              "quality": {k: positions["quality"].get(k) for k in ("pose_valid", "pose_valid_interval", "n_valid_frames", "n_frames", "scale_status", "scale_check", "reasons")},
              "relations": dict(collections.Counter(r["relation"] for r in positions["relations"]))}
        (cd / "eval.json").write_text(json.dumps(ev, indent=1, ensure_ascii=False))
        if not a.no_media:
            render_depth_preview(cd, da3, tracks); plot_topdown(cd, da3, positions, frames)
        summ.append(ev)
        g = ev["gemini"]["counts"]
        print(f"{s['scenario']:12s} pose_valid {ev['quality']['pose_valid']} scale {ev['quality']['scale_status']} | depth gap1 {ev['depth_consistency_gap1']['median_rel_err']} gap5 {ev['depth_consistency_gap5']['median_rel_err']} | path {ev['pose']['path_len_m']} m max {ev['pose']['max_speed_mps']} m/s | reproj {ev['reprojection']['median_frac_width']} | gemini {g} | reach {ev['arm_reach']} | rel {ev['relations']}", flush=True)
    cfg.OUT.mkdir(exist_ok=True)
    old = json.loads((cfg.OUT / "summary.json").read_text()) if (cfg.OUT / "summary.json").exists() else []
    keep = {x["sample_id"]: x for x in old}; keep.update({x["sample_id"]: x for x in summ})
    (cfg.OUT / "summary.json").write_text(json.dumps(list(keep.values()), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
