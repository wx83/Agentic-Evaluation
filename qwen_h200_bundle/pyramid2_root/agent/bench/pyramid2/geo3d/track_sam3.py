"""SAM3 文字提示视频跟踪(SAM env 的 python,独立脚本,只用 numpy/torch/PIL/json):
  $SAMPY geo3d/track_sam3.py <clip_dir>   读 <clip_dir>/sam3/prompts.json(物体名列表),帧目录 <clip_dir>/frames
输出 sam3/<slug>.npz {frames int32[N], obj_ids int32[K], masks uint8 packbits [K,N,hh*ww/8], probs float32[K,N], boxes float32[K,N,4], hw[hh,ww]}(mask 存半分辨率)+ tracks.json"""
import sys, json, re, time
from pathlib import Path
import numpy as np, torch


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40] or "obj"


def main():
    cd = Path(sys.argv[1]); fdir = cd / "frames"; od = cd / "sam3"; od.mkdir(exist_ok=True)
    names = json.loads((od / "prompts.json").read_text())
    from sam3.model_builder import build_sam3_video_model
    t0 = time.time(); model = build_sam3_video_model(); print(f"model loaded {time.time()-t0:.0f}s", flush=True)
    summary = {"names": {}, "n_frames": None}
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        state = model.init_state(resource_path=str(fdir), offload_video_to_cpu=False)
        N = int(state["num_frames"]); summary["n_frames"] = N
        for name in names:
            t1 = time.time()
            model.add_prompt(state, frame_idx=0, text_str=name)
            per = {}   # obj_id -> {frame: (mask_half uint8, prob, box)}
            hh = ww = None
            for fi, out in model.propagate_in_video(state, start_frame_idx=0, max_frame_num_to_track=N, reverse=False):
                def npy(x): return x.detach().cpu().numpy() if hasattr(x, "detach") else np.asarray(x)
                ids = npy(out["out_obj_ids"]); masks = npy(out["out_binary_masks"]); probs = npy(out["out_probs"]); boxes = npy(out["out_boxes_xywh"])
                for j, oid in enumerate(ids):
                    m = masks[j][::2, ::2]; hh, ww = m.shape
                    per.setdefault(int(oid), {})[int(fi)] = (np.packbits(m.astype(np.uint8).ravel()), float(probs[j]), boxes[j].astype(np.float32))
            if not per:
                summary["names"][name] = {"instances": 0, "seconds": round(time.time() - t1, 1)}; print(f"  {name!r}: no instances", flush=True); continue
            oids = sorted(per); K = len(oids); nb = (hh * ww + 7) // 8
            M = np.zeros((K, N, nb), np.uint8); Pq = np.zeros((K, N), np.float32); B = np.zeros((K, N, 4), np.float32); cnt = []
            for k, oid in enumerate(oids):
                for fi, (pm, pr, bx) in per[oid].items():
                    M[k, fi, :len(pm)] = pm; Pq[k, fi] = pr; B[k, fi] = bx
                cnt.append(len(per[oid]))
            np.savez_compressed(od / f"{slug(name)}.npz", frames=np.arange(N, dtype=np.int32), obj_ids=np.array(oids, np.int32), masks=M, probs=Pq, boxes=B, hw=np.array([hh, ww], np.int32))
            summary["names"][name] = {"slug": slug(name), "instances": K, "frames_per_instance": cnt, "seconds": round(time.time() - t1, 1)}
            print(f"  {name!r}: {K} instances, frames {cnt} ({time.time()-t1:.0f}s)", flush=True)
    (od / "tracks.json").write_text(json.dumps(summary, indent=1))
    print("DONE", cd.name, flush=True)


if __name__ == "__main__":
    main()
