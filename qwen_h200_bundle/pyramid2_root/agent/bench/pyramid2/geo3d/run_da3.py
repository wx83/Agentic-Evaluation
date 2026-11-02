"""Depth Anything 3(holi env):无位姿输入,一次前向得到 metric 深度 + 相机位姿(w2c, OpenCV)+ 内参(处理分辨率,cx=W/2)。
  HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True $HOLI -m geo3d.run_da3 --samples all"""
import json, time, argparse
from pathlib import Path
import numpy as np
from . import cfg


def load_model():
    import torch
    from depth_anything_3.api import DepthAnything3
    m = DepthAnything3.from_pretrained(cfg.DA3_MODEL).to("cuda")
    return m


def run_da3(model, cd, process_res=cfg.DA3_RES):
    import torch
    cd = Path(cd); fr = cfg.load_frames(cd)
    paths = [str(cd / "frames" / f["file"]) for f in fr["frames"]]
    torch.cuda.reset_peak_memory_stats(); t0 = time.time()
    pred = model.inference(paths, extrinsics=None, intrinsics=None, process_res=process_res, process_res_method="upper_bound_resize",
                           ref_view_strategy="saddle_balanced", use_ray_pose=False, export_dir=None)
    dt = time.time() - t0; peak = torch.cuda.max_memory_allocated() / 1e9
    od = cd / "da3"; od.mkdir(exist_ok=True)
    np.savez_compressed(od / "results.npz", depth=pred.depth.astype(np.float32), conf=(pred.conf.astype(np.float32) if pred.conf is not None else np.ones_like(pred.depth, np.float32)),
                        extrinsics=np.asarray(pred.extrinsics, np.float64), intrinsics=np.asarray(pred.intrinsics, np.float64))
    meta = {"model": cfg.DA3_MODEL, "n_frames": len(paths), "process_res": process_res, "proc_hw": list(pred.depth.shape[1:]), "frame_hw": fr["frame_hw"],
            "is_metric": int(pred.is_metric), "scale_factor": (float(pred.scale_factor) if pred.scale_factor is not None else None),
            "extrinsics_convention": "world_to_camera, OpenCV (x right, y down, z forward); c2w = inv", "intrinsics_note": "at proc_hw, principal point at centre",
            "depth_median_m": float(np.nanmedian(pred.depth)), "depth_p10_p90_m": [float(np.nanpercentile(pred.depth, 10)), float(np.nanpercentile(pred.depth, 90))],
            "seconds": round(dt, 1), "peak_gpu_gb": round(peak, 1), "files": [f["file"] for f in fr["frames"]]}
    (od / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def load_da3(cd):
    cd = Path(cd); z = np.load(cd / "da3" / "results.npz"); meta = json.loads((cd / "da3" / "meta.json").read_text())
    w2c = z["extrinsics"]
    if w2c.shape[1] == 3:
        w2c = np.concatenate([w2c, np.tile(np.array([[[0, 0, 0, 1.0]]]), (len(w2c), 1, 1))], 1)
    c2w = np.linalg.inv(w2c)
    # 参照系 = 本 clip 第 1 帧的相机(用户 10-15 定):原点 = 第 1 帧相机中心,轴 = 第 1 帧 OpenCV 相机轴(x 右、y 下、z 前),米。
    # DA3 自己的参考视角(saddle_balanced 选的中间帧)只留在 results.npz 里,这里统一换到第 1 帧系;所有下游(derive / eval / 页面)都经由本函数拿位姿。
    raw_c2w0 = c2w[0].copy(); T0 = np.linalg.inv(raw_c2w0)
    c2w = np.einsum("ij,njk->nik", T0, c2w); w2c = np.linalg.inv(c2w)
    down = c2w[:, :3, 1].mean(0); down = down / np.linalg.norm(down)
    ref = {"kind": "first_frame_camera", "frame_index": 0, "axes": "OpenCV camera axes of frame 0: x right, y down, z forward; origin = frame-0 camera centre; metres",
           "gravity_world_estimate": np.round(down, 4).tolist(), "gravity_source": "estimate: mean camera down (+y) axis over the clip; no IMU",
           "da3_raw_c2w_frame0": np.round(raw_c2w0, 5).tolist()}
    h, w = meta["proc_hw"]; H, W = meta["frame_hw"]
    K = z["intrinsics"]; S = np.diag([W / w, H / h, 1.0]); K_frame = np.einsum("ij,njk->nik", S, K)
    return {"depth": z["depth"], "conf": z["conf"], "w2c": w2c, "c2w": c2w, "K": K, "K_frame": K_frame, "meta": meta, "ref": ref}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--samples", nargs="*", default=["all"]); ap.add_argument("--process-res", type=int, default=cfg.DA3_RES); a = ap.parse_args()
    model = load_model()
    for s in cfg.samples(a.samples):
        cd = cfg.clip_dir(s["sample_id"])
        if not (cd / "frames.json").exists():
            print("no frames:", s["sample_id"]); continue
        m = run_da3(model, cd, a.process_res)
        print(f"{s['scenario']:12s} {s['sample_id'][-6:]} {m['n_frames']} frames -> depth {m['proc_hw']} metric={m['is_metric']} scale={m['scale_factor']} median {m['depth_median_m']:.2f} m (p10-p90 {m['depth_p10_p90_m'][0]:.2f}-{m['depth_p10_p90_m'][1]:.2f}) {m['seconds']}s peak {m['peak_gpu_gb']} GB", flush=True)


if __name__ == "__main__":
    main()
