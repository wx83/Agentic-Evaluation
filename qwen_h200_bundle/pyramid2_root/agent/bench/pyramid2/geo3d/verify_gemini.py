"""用 Gemini 4 评估 DA3+SAM3 生成的 3D 数据(用户 10-15 要求),三类核验,每条 {verdict, confidence, reason}:
 (a) 关系核验:每条 spatial_relation 给锚点前后 3 帧(答案绿 / 参照蓝 / 其它灰框 + 标签)问是否成立;
 (b) 序数核验(DA3 深度 / 位姿质量代理):同帧可见、DA3 距离差 ≥0.3 m 的物体对,问「A/B 哪个离相机更近」与 DA3 range 比;左右同理(lateral 差 ≥0.3 m);
 (c) 静止核验:每个静止区间给首尾两帧问物体是否没动;相机轨迹给 top-down 图 + 4 关键帧让它定性描述。
  GEMINI_BACKEND=nv python3 -m geo3d.verify_gemini --samples all     → <clip>/verify.json, geo3d/verify_summary.json, usage 记 geo3d/usage.jsonl(role verify3d)"""
import json, argparse, io, time, random, collections, re, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, "/mnt/work_new/weihanxu/gemini")
from . import cfg

MODEL = "gcp/google/gemini-4-argon"
MAX_REL, MAX_PAIR, MAX_STATIC, MAX_MOVE = 40, 12, 20, 12     # 10-15:关系 / 静止尽量全核(每条都是潜在题目),序数对减到 12
COL = {"answer": (40, 200, 60), "reference": (60, 120, 255), "other": (160, 160, 160), "A": (255, 60, 60), "B": (255, 200, 0), "obj": (40, 200, 60)}


def jparse(text):
    t = (text or "").strip()
    if t.startswith("```"): t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    try: return json.loads(t)
    except Exception:
        i, j = t.find("{"), t.rfind("}"); return json.loads(t[i:j + 1])


def ask(images, text, meta, max_tokens=1024):
    import nv_gemini as NV, logging
    logging.getLogger("google_genai").setLevel(logging.ERROR)
    from google.genai import types
    from examiner import _log
    parts = []
    for im in images:
        b = io.BytesIO(); im.save(b, "JPEG", quality=85); parts.append(types.Part.from_bytes(data=b.getvalue(), mime_type="image/jpeg"))
    parts.append(text)
    kw = dict(temperature=0.0, max_output_tokens=max_tokens, response_mime_type="application/json")
    t0 = time.time(); err = None; out = None; u = {}
    for attempt in range(4):
        try:
            r = NV.client(timeout_ms=300_000).models.generate_content(model=MODEL, contents=parts, config=types.GenerateContentConfig(**kw))
            um = getattr(r, "usage_metadata", None); g = lambda k: getattr(um, k, None) if um is not None else None
            u = {"tok_in": g("prompt_token_count"), "tok_out": g("candidates_token_count"), "tok_think": g("thoughts_token_count")}
            out = r.text; err = None
            if out: break
            err = "empty"
        except Exception as e_:
            err = f"{type(e_).__name__}: {str(e_)[:200]}"
            if "429" in err or "RateLimit" in err: time.sleep(75); continue
            time.sleep(3)
    _log(cfg.OUT, "verify3d", {"model": MODEL, "latency_sec": round(time.time() - t0, 2), "error": err, **u, **meta})
    if err: return {"verdict": "error", "confidence": 0, "reason": err}
    try: return jparse(out)
    except Exception as e_: return {"verdict": "error", "confidence": 0, "reason": f"json: {str(e_)[:100]} | {out[:200]}"}


# ---- masks / rendering
def load_tracks_light(cd):
    od = Path(cd) / "sam3"; summ = json.loads((od / "tracks.json").read_text()); out = {}
    for name, info in summ["names"].items():
        if not info.get("instances"): continue
        z = np.load(od / f"{info['slug']}.npz"); hh, ww = [int(x) for x in z["hw"]]
        out[name] = {"hw": (hh, ww), "z": z}
    return out


def mask_of(tracks, name, iid, fi):
    tn = iid.rsplit("#", 1)[0] if "#" in iid else name          # 名字级别名合并后 name 可能是 canonical 名,mask 仍在原 track 名的 npz 里
    tr = tracks.get(tn) or tracks.get(name)
    if tr is None: return None
    z = tr["z"]; oid = int(iid.split("#")[-1]); ks = np.where(z["obj_ids"] == oid)[0]
    if not len(ks): return None
    k = int(ks[0]); hh, ww = tr["hw"]; pm = z["masks"][k, fi]
    if not pm.any(): return None
    return np.unpackbits(pm)[: hh * ww].reshape(hh, ww).astype(bool)


def render_marks(cd, tracks, fr, fi, marks, width=800):
    im = Image.open(Path(cd) / "frames" / fr[fi]["file"]).convert("RGB"); W, H = im.size
    ov = im.convert("RGBA"); dr = ImageDraw.Draw(ov, "RGBA")
    for name, iid, label, ck in marks:
        m = mask_of(tracks, name, iid, fi); col = COL[ck]
        if m is None: continue
        mm = Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.NEAREST)
        layer = Image.new("RGBA", (W, H), col + (70,)); ov.paste(layer, (0, 0), mm)
        ys, xs = np.nonzero(np.array(mm))
        if len(xs):
            x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
            dr.rectangle([x0, y0, x1, y1], outline=col + (255,), width=3)
            dr.rectangle([x0, max(0, y0 - 16), x0 + 8 * len(label) + 6, max(0, y0 - 16) + 16], fill=col + (230,)); dr.text((x0 + 3, max(0, y0 - 15)), label, fill=(0, 0, 0, 255))
    out = ov.convert("RGB")
    if W > width: out = out.resize((width, int(H * width / W)))
    return out


def nearest_fi(fr, T):
    return int(np.argmin([abs(f["t_abs"] - T) for f in fr]))


def thumb_strip(cd, tracks, fr, objs, names, size=220):
    """每个物体取 mask 面积最大的一帧,裁框 + 标签,拼成一条缩略图(帮 Gemini 认物体)。"""
    tiles = []
    for n in names:
        o = objs.get(n)
        if not o: continue
        best = max(o["rows"], key=lambda x: x.get("area", 0)); fi = best["fi"]
        m = mask_of(tracks, n, o["iid"], fi)
        im = Image.open(Path(cd) / "frames" / fr[fi]["file"]).convert("RGB"); W, H = im.size
        if m is not None:
            mm = np.array(Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.NEAREST)); ys, xs = np.nonzero(mm)
            if len(xs):
                pad = 40; x0, y0, x1, y1 = max(0, xs.min() - pad), max(0, ys.min() - pad), min(W, xs.max() + pad), min(H, ys.max() + pad)
                im = im.crop((x0, y0, x1, y1))
        im = im.resize((size, int(im.size[1] * size / max(im.size[0], 1)) or size)); im = im.crop((0, 0, size, min(im.size[1], size)))
        tile = Image.new("RGB", (size, size + 18), (255, 255, 255)); tile.paste(im, (0, 18)); ImageDraw.Draw(tile).text((3, 3), f"{n} (t={fr[fi]['t_abs']:.0f}s)", fill=(0, 0, 0)); tiles.append(tile)
    if not tiles: return None
    strip = Image.new("RGB", (size * len(tiles), size + 18), (255, 255, 255))
    for i, t in enumerate(tiles): strip.paste(t, (i * size, 0))
    return strip


# ---- (a) relations
def verify_relations(s, cd, tracks, fr, pos, keep=None):
    """keep = 旧 verify.json 里 eid 仍存在的核验条目(--only-missing 时沿用,只为缺的关系调用 Gemini)。"""
    objs = pos["objects"]; out = []
    idx = list(range(len(pos["relations"])))
    if len(idx) > MAX_REL: idx = sorted(random.Random(1014).sample(idx, MAX_REL))       # i = positions.json 里的原始索引
    have = {x.get("eid"): x for x in (keep or []) if x.get("eid")}
    for i in idx:
        if pos["relations"][i].get("eid") in have:
            x = dict(have[pos["relations"][i]["eid"]]); x["i"] = i; out.append(x); continue

        r = pos["relations"][i]
        T = r["T"]; fis = sorted({nearest_fi(fr, T - 2), nearest_fi(fr, T), nearest_fi(fr, T + 2)})
        ans = r["answer_object"].split(" -> ")[0]; ref = r.get("reference_object")
        marks = [(ans, objs[ans]["iid"], f"ANSWER: {ans}", "answer")] if ans in objs else []
        if ref and ref in objs: marks.append((ref, objs[ref]["iid"], f"REF: {ref}", "reference"))
        for w in (r.get("wrong") or []):
            if w in objs: marks.append((w, objs[w]["iid"], w, "other"))
        ims = [render_marks(cd, tracks, fr, fi, marks) for fi in fis]
        strip = thumb_strip(cd, tracks, fr, objs, [m[0] for m in marks])
        if strip is not None: ims.append(strip)
        rel = r["relation"]
        # 最近 / 最远 / 最左 / 最右都只在候选集(答案 + 其它候选)里比,不是全场景绝对(用户 10-15 强调);候选全列出,不截断
        cands = [ans] + [w for w in (r.get("wrong") or []) if w != ans and w in objs]; cl = ", ".join(f'"{c}"' for c in cands)
        only = f"Consider ONLY these candidate objects: {cl}. Any other object in the scene (table, wall, floor, hands, anything not in this list) must be ignored even if it would rank higher."
        allo = f'This is an ALLOCENTRIC relation: 3D scene distance relative to "{ref}", independent of where the wearer stands or looks.'
        egoc = "This is an EGOCENTRIC relation: from the camera wearer's own viewpoint at that moment, left/right/front/back are the wearer's own as the camera faces (camera forward, not body forward); it is a relative position among the candidates only."
        if rel == "nearest": claim = f'At the middle frame\'s moment, among the candidates "{ans}" is the one closest (in 3D space, metres) to "{ref}". {allo} {only}'
        elif rel == "farthest": claim = f'At the middle frame\'s moment, among the candidates "{ans}" is the one farthest (in 3D space, metres) from "{ref}". {allo} {only}'
        elif rel == "order_by_distance": claim = f'At the middle frame\'s moment, ordering the candidates by increasing 3D distance from "{ref}" gives: {r["answer_object"]}. {only}'
        elif rel == "side_right": claim = f'At the middle frame\'s moment, from the camera wearer\'s own viewpoint, among the candidates "{ans}" is the one farthest to the wearer\'s RIGHT. {egoc} {only}'
        elif rel == "side_left": claim = f'At the middle frame\'s moment, from the camera wearer\'s own viewpoint, among the candidates "{ans}" is the one farthest to the wearer\'s LEFT. {egoc} {only}'
        elif rel == "near": claim = f'At the middle frame\'s moment, "{ans}" is close to "{ref}" (their centres are within about {r.get("near_threshold_m", 0.8)} m in 3D), while the other candidates are clearly farther from "{ref}". {only}'
        elif rel == "distance": claim = f'At the middle frame\'s moment, the 3D centre-to-centre distance between "{ref}" and "{ans}" is about {r.get("d_gold_m")} m (tolerance ±{r.get("tolerance_m")} m). Judge plausibility from object sizes and layout; say insufficient if you cannot estimate metres.'
        elif rel == "ego_behind": claim = f'At the middle frame\'s moment, "{ans}" is BEHIND the camera wearer (behind their back, out of the forward view) while the other candidates are in front of them. {egoc} {only}'
        elif rel == "ego_sector": claim = f'At the middle frame\'s moment, relative to the camera wearer, "{ans}" lies in their {r.get("sector")} quadrant (front/back = along the direction they face; left/right = the wearer\'s own left/right). The other quadrants are wrong.'
        else: claim = f'At the middle frame\'s moment: {rel} -> "{ans}" (reference "{ref}"). {only}'
        text = (f"The first three images are frames from a first-person video, 2 seconds before, at, and 2 seconds after a moment. Objects are outlined where visible: green = the claimed answer, blue = the reference object, grey = other candidates. The last image is a strip of close-ups showing what each named object looks like (taken at other times in the same clip), so you can recognise them even if an outline is missing. Objects may be out of view at the moment: use the scene layout you can infer from all images.\n"
                f"CLAIM: {claim}\nIs the claim supported by what is visible? Consider real 3D distances, not just image positions. Return JSON: {{\"verdict\": \"supported\"|\"contradicted\"|\"insufficient\", \"confidence\": 0-1, \"reason\": \"<one sentence>\"}}")
        v = ask(ims, text, {"sample": s["sample_id"], "check": "relation", "relation": rel, "i": i})
        out.append({"i": i, "eid": r.get("eid"), "relation": rel, "T": T, "anchor_kind": r.get("anchor_kind"), "answer": r["answer_object"], "reference": ref, "candidates": cands, "d_gold_m": r.get("d_gold_m"), "margin_m": r.get("margin_m"), "sector": r.get("sector"), "flags": r.get("flags"), "frames": fis, "claim": claim, **{k: v.get(k) for k in ("verdict", "confidence", "reason")}})
        print(f"  rel {i:02d} {rel:18s} {ans[:18]:18s} -> {v.get('verdict')} ({v.get('confidence')})", flush=True)
    return out


# ---- (b) ordinal pairs
def verify_ordinal(s, cd, tracks, fr, pos, mode):
    """mode = depth(哪个更近)或 lr(哪个更左)。"""
    objs = pos["objects"]; rng = random.Random(2014 if mode == "depth" else 3014)
    byframe = collections.defaultdict(list)
    for n, o in objs.items():
        for x in o["rows"]:
            if not x.get("border") and x.get("hand_overlap", 0) <= cfg.HAND_OVERLAP: byframe[x["fi"]].append((n, x))
    pairs = []
    for fi, items in byframe.items():
        for a in range(len(items)):
            for b in range(a + 1, len(items)):
                (na, xa), (nb, xb) = items[a], items[b]
                if mode == "depth":
                    diff = xa["range"] - xb["range"]
                else:
                    diff = (-xa["xc"][0]) - (-xb["xc"][0])      # lateral 左正
                if abs(diff) >= 0.3: pairs.append((fi, na, nb, diff))
    rng.shuffle(pairs); pairs = pairs[:MAX_PAIR]; out = []; agree = 0
    for j, (fi, na, nb, diff) in enumerate(pairs):
        if rng.random() < 0.5: na, nb, diff = nb, na, -diff
        im = render_marks(cd, tracks, fr, fi, [(na, objs[na]["iid"], "A", "A"), (nb, objs[nb]["iid"], "B", "B")])
        if mode == "depth":
            q = "Two objects are outlined and labelled A (red) and B (yellow). Which one is physically closer to the camera (smaller distance from the camera to the object in metres)?"; geo = "A" if diff < 0 else "B"
        else:
            q = "Two objects are outlined and labelled A (red) and B (yellow). From the camera wearer's point of view, which one is more to the LEFT?"; geo = "A" if diff > 0 else "B"
        v = ask([im], q + ' Return JSON: {"answer": "A"|"B"|"unsure", "confidence": 0-1, "reason": "<one sentence>"}', {"sample": s["sample_id"], "check": f"ordinal_{mode}", "j": j})
        a_ = str(v.get("answer", "")).strip().upper()[:1]
        ok = a_ == geo; agree += ok
        ea = next((x.get("obs_eid") for x in objs[na]["rows"] if x["fi"] == fi), None); eb = next((x.get("obs_eid") for x in objs[nb]["rows"] if x["fi"] == fi), None)
        out.append({"j": j, "frame": fi, "t": fr[fi]["t_abs"], "A": na, "B": nb, "eids": [ea, eb], "diff_m": round(diff, 3), "geo_says": geo, "gemini": a_, "agree": ok, "confidence": v.get("confidence"), "reason": v.get("reason")})
        print(f"  {mode} {j:02d} {na[:14]:14s} vs {nb[:14]:14s} diff {diff:+.2f} geo {geo} gemini {a_} {'ok' if ok else 'X'}", flush=True)
    return {"n": len(out), "agree": agree, "rate": (round(agree / len(out), 3) if out else None), "items": out}


# ---- (c) static intervals + trajectory
def verify_static(s, cd, tracks, fr, pos):
    objs = pos["objects"]; ivs = [(n, iv) for n, o in objs.items() for iv in o["intervals"]]
    if len(ivs) > MAX_STATIC: rng = random.Random(4014); rng.shuffle(ivs); ivs = ivs[:MAX_STATIC]
    out = []; yes = 0
    for k, (n, iv) in enumerate(ivs):
        f0, f1 = nearest_fi(fr, iv["t0"]), nearest_fi(fr, iv["t1"])
        ims = [render_marks(cd, tracks, fr, f, [(n, objs[n]["iid"], n, "obj")]) for f in (f0, f1)]
        v = ask(ims, f'Two frames from a first-person video, {iv["t1"] - iv["t0"]:.1f} seconds apart; the outlined object is "{n}". Ignoring the camera\'s own motion, did this object stay in the same physical place during this time (not picked up, moved or carried)? Return JSON: {{"answer": "yes"|"no"|"unsure", "confidence": 0-1, "reason": "<one sentence>"}}',
                {"sample": s["sample_id"], "check": "static", "k": k})
        a_ = str(v.get("answer", "")).lower()[:3]; yes += a_ == "yes"
        out.append({"object": n, "eid": iv.get("eid"), "t0": iv["t0"], "t1": iv["t1"], "std_m": iv["std_m"], "gemini": a_, "confidence": v.get("confidence"), "reason": v.get("reason")})
        print(f"  static {k} {n[:18]:18s} {iv['t0']:.1f}-{iv['t1']:.1f} -> {a_}", flush=True)
    return {"n": len(out), "yes": yes, "rate": (round(yes / len(out), 3) if out else None), "items": out}


def verify_moves(s, cd, tracks, fr, pos):
    """每个 object_move / transition:起点区间末帧 + 终点区间首帧,问物体是否被移到了别处。"""
    objs = pos["objects"]; out = []; yes = 0
    mvs = pos.get("moves") or []
    if len(mvs) > MAX_MOVE: mvs = random.Random(5014).sample(mvs, MAX_MOVE)
    for k, mv in enumerate(mvs):
        n = mv["object"]; o = objs[n]; st, en = o["intervals"][mv["start_iv"]], o["intervals"][mv["end_iv"]]
        ims = [render_marks(cd, tracks, fr, f, [(n, o["iid"], n, "obj")]) for f in (st.get("fi1", nearest_fi(fr, st["t1"])), en.get("fi0", nearest_fi(fr, en["t0"])))]
        v = ask(ims, f'Two frames from a first-person video, {mv["gap_s"]:.1f} seconds apart; the outlined object is "{n}". Between these two moments, was this object moved to a different physical place (picked up and put down somewhere else, roughly {mv["displacement_m"]:.1f} m away), as opposed to staying where it was while only the camera moved? Return JSON: {{"answer": "yes"|"no"|"unsure", "confidence": 0-1, "reason": "<one sentence>"}}',
                {"sample": s["sample_id"], "check": "move", "k": k})
        a_ = str(v.get("answer", "")).lower()[:3]; yes += a_ == "yes"
        out.append({"object": n, "eid": mv.get("eid"), "k": mv["k"], "t_start": mv["t_start"], "t_end": mv["t_end"], "displacement_m": mv["displacement_m"], "is_transition": mv["is_transition"], "gemini": a_, "confidence": v.get("confidence"), "reason": v.get("reason")})
        print(f"  move {k} {n[:18]:18s} {mv['t_start']:.1f}->{mv['t_end']:.1f} {mv['displacement_m']} m -> {a_}", flush=True)
    return {"n": len(out), "yes": yes, "rate": (round(yes / len(out), 3) if out else None), "items": out}


def verify_trajectory(s, cd, fr, ev):
    top = Image.open(Path(cd) / "trajectory_topdown.png").convert("RGB")
    ks = [0, len(fr) // 3, 2 * len(fr) // 3, len(fr) - 1]
    ims = [top] + [Image.open(Path(cd) / "frames" / fr[k]["file"]).convert("RGB") for k in ks]
    ims = [ims[0]] + [im.resize((640, int(im.size[1] * 640 / im.size[0]))) for im in ims[1:]]
    p = ev["pose"]
    v = ask(ims, f"The first image is a top-down plot of the camera wearer's estimated path over {fr[-1]['t_abs'] - fr[0]['t_abs']:.0f} s (green start, red end; estimated path length {p['path_len_m']} m, mean speed {p['mean_speed_mps']} m/s). The next four images are frames at the start, 1/3, 2/3 and end of the clip. Does the plotted path shape and length look consistent with the motion you can infer from the frames (e.g. standing in place vs walking across a room)? Return JSON: {{\"consistent\": \"yes\"|\"partly\"|\"no\", \"confidence\": 0-1, \"reason\": \"<one or two sentences>\"}}",
            {"sample": s["sample_id"], "check": "trajectory"})
    return v


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--samples", nargs="*", default=["all"]); ap.add_argument("--skip", nargs="*", default=[]); ap.add_argument("--only-missing", action="store_true"); a = ap.parse_args()
    summ = []
    for s in cfg.samples(a.samples):
        cd = cfg.clip_dir(s["sample_id"])
        if not (cd / "eval.json").exists(): print("not ready:", s["sample_id"]); continue
        pos = json.loads((cd / "positions.json").read_text()); ev = json.loads((cd / "eval.json").read_text()); fr = cfg.load_frames(cd)["frames"]; tracks = load_tracks_light(cd)
        print(f"== {s['scenario']} {s['sample_id'][-6:]}", flush=True)
        res = {"sample_id": s["sample_id"], "scenario": s["scenario"], "model": MODEL}
        if a.skip and (cd / "verify.json").exists():      # 只重跑部分检查时,其余沿用上一次的结果
            old_res = json.loads((cd / "verify.json").read_text())
            for k, key in (("relation", "relations"), ("depth", "ordinal_depth"), ("lr", "ordinal_lr"), ("static", "static"), ("move", "moves"), ("traj", "trajectory")):
                if k in a.skip and key in old_res:
                    res[key] = old_res[key]
                    if key == "relations":                     # 重跑 derive 后关系集可能变:只留 eid 仍存在的旧核验
                        live = {x.get("eid") for x in pos["relations"]}; res[key] = [x for x in res[key] if x.get("eid") in live]
        if "relation" not in a.skip:
            keep = None
            if a.only_missing and (cd / "verify.json").exists():
                live = {x.get("eid") for x in pos["relations"]}; keep = [x for x in json.loads((cd / "verify.json").read_text()).get("relations", []) if x.get("eid") in live]
            res["relations"] = verify_relations(s, cd, tracks, fr, pos, keep=keep)
        if "depth" not in a.skip: res["ordinal_depth"] = verify_ordinal(s, cd, tracks, fr, pos, "depth")
        if "lr" not in a.skip: res["ordinal_lr"] = verify_ordinal(s, cd, tracks, fr, pos, "lr")
        if "static" not in a.skip: res["static"] = verify_static(s, cd, tracks, fr, pos)
        if "move" not in a.skip: res["moves"] = verify_moves(s, cd, tracks, fr, pos)
        if "traj" not in a.skip: res["trajectory"] = {**verify_trajectory(s, cd, fr, ev), "eid": pos.get("frame_eid")}
        res["pose_valid"] = (pos.get("quality") or {}).get("pose_valid"); res["scale_status"] = (pos.get("quality") or {}).get("scale_status")
        rc = collections.Counter(r["verdict"] for r in res.get("relations", []))
        res["summary"] = {"relations": dict(rc), "ordinal_depth_rate": (res.get("ordinal_depth") or {}).get("rate"), "ordinal_lr_rate": (res.get("ordinal_lr") or {}).get("rate"),
                          "static_yes_rate": (res.get("static") or {}).get("rate"), "move_yes_rate": (res.get("moves") or {}).get("rate"), "trajectory": (res.get("trajectory") or {}).get("consistent"),
                          "pose_valid": res.get("pose_valid"), "scale_status": res.get("scale_status")}
        (cd / "verify.json").write_text(json.dumps(res, indent=1, ensure_ascii=False)); summ.append({"sample_id": s["sample_id"], "scenario": s["scenario"], **res["summary"]})
        print("  summary:", res["summary"], flush=True)
    old = json.loads((cfg.OUT / "verify_summary.json").read_text()) if (cfg.OUT / "verify_summary.json").exists() else []
    keep = {x["sample_id"]: x for x in old}; keep.update({x["sample_id"]: x for x in summ})
    (cfg.OUT / "verify_summary.json").write_text(json.dumps(list(keep.values()), indent=1, ensure_ascii=False))
    print("VERIFY DONE", flush=True)


if __name__ == "__main__":
    main()
