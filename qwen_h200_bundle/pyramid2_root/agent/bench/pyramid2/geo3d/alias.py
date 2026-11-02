"""同物异名 / 部件判定(10-15 spec §6.1):SAM3 按 Gemini 给的名字分别跟踪,同一个物体常被两个名字各跟一遍(carpenter: plastic bag / package)。
规则(cfg.ALIAS_*):两实例 ≥4 共同帧,中心距中位 ≤0.15 m:
  mask IoU 中位 ≥0.5 → alias(自动合并,canonical = 帧数多者);IoU <0.2 → part_of / support 候选(各自保留,打 CO_LOCATED);
  中间灰区 → Gemini 4 看两者特写判「同一物体?」(每对 1 次调用,记 usage)。
只比较不同名字的实例;同名多实例是 multi-instance,不在这里处理。"""
import json, io
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from . import cfg


def _iou(a, b):
    i = np.logical_and(a, b).sum(); u = np.logical_or(a, b).sum()
    return float(i / u) if u else 0.0


def _crop(cd, frames, inst, fi, size=240):
    m = inst["masks"][fi]; im = Image.open(Path(cd) / "frames" / frames[fi]["file"]).convert("RGB"); W, H = im.size
    mm = np.array(Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.NEAREST)); ys, xs = np.nonzero(mm)
    if len(xs):
        pad = 40; im = im.crop((max(0, xs.min() - pad), max(0, ys.min() - pad), min(W, xs.max() + pad), min(H, ys.max() + pad)))
    im = im.resize((size, max(1, int(im.size[1] * size / max(im.size[0], 1))))); return im.crop((0, 0, size, min(im.size[1], size)))


def _gemini_same(cd, frames, tracks, ca, cb, fis, s):
    """灰区:给两实例在 2 个共同帧的特写 + 整帧叠框,问是否同一物体。"""
    from .verify_gemini import ask, render_marks, load_tracks_light
    light = load_tracks_light(cd)
    ims = []
    for fi in fis[:2]:
        ims.append(render_marks(cd, light, frames, fi, [(ca["name"], ca["iid"], f"A: {ca['name']}", "A"), (cb["name"], cb["iid"], f"B: {cb['name']}", "B")]))
    txt = (f'Two outlines in each frame: A (red) was tracked under the name "{ca["name"]}", B (yellow) under the name "{cb["name"]}". '
           "Are A and B the same physical object (two names for one thing), or two different objects (e.g. a part / lid on a container, or an object resting on another)? "
           'Return JSON: {"same_object": "yes"|"no"|"unsure", "relation_if_no": "part_of"|"on_top_of"|"separate"|null, "confidence": 0-1, "reason": "<one sentence>"}')
    return ask(ims, txt, {"sample": s["sample_id"], "check": "alias", "a": ca["iid"], "b": cb["iid"]})


def merge_names(cents, aliases, parts, log):
    """名字级:两名字之间 alias 对 ≥1、且 alias 对数 ≥ 3× part 对数(或 part 为 0)→ 同一类物体,少帧名并入多帧名。返回 {alias_name: canonical_name}(无环)。"""
    import collections
    na, npart = collections.Counter(), collections.Counter()
    for r in log:
        key = tuple(sorted((cents[r["a"]]["name"], cents[r["b"]]["name"])))
        (na if r["decision"] == "alias" else npart)[key] += 1
    frames_of = collections.Counter()
    for c in cents.values(): frames_of[c["name"]] += len(c["rows"])
    parent = {}
    def root(x):
        while parent.get(x, x) != x: x = parent[x]
        return x
    for key, k in sorted(na.items(), key=lambda kv: -kv[1]):
        if k >= 1 and (npart[key] == 0 or k >= 3 * npart[key]):
            a, b = key; ra, rb = root(a), root(b)
            if ra == rb: continue
            keep, drop = (ra, rb) if frames_of[ra] >= frames_of[rb] else (rb, ra)
            parent[drop] = keep; frames_of[keep] += frames_of[drop]
    return {n: root(n) for n in set(parent) if root(n) != n}


def detect(cents, tracks, cd, frames, s, use_gemini=True):
    """cents = derive.centroids 的输出 {iid: {name, rows}}。返回 (aliases, parts, log):
    aliases = {alias_iid: {canonical, d_m, iou, n_common, method}};parts = [{a, b, d_m, iou, relation}]。"""
    inst = {}
    for iid, c in cents.items():
        name = c["name"]; tr = tracks.get(name)
        if not tr or iid not in tr["instances"]: continue
        inst[iid] = {"iid": iid, "name": name, "rows": {x["fi"]: x for x in c["rows"]}, "masks": tr["instances"][iid]["masks"], "n": len(c["rows"])}
    ids = sorted(inst, key=lambda k: -inst[k]["n"])
    aliases, parts, log = {}, [], []
    taken = set()
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            A, B = inst[a], inst[b]
            if A["name"] == B["name"] or b in taken or a in taken: continue
            common = sorted(set(A["rows"]) & set(B["rows"]) & set(A["masks"]) & set(B["masks"]))
            if len(common) < cfg.ALIAS_MIN_COMMON: continue
            d = float(np.median([np.linalg.norm(np.array(A["rows"][fi]["xyz"]) - np.array(B["rows"][fi]["xyz"])) for fi in common]))
            if d > cfg.ALIAS_D: continue
            iou = float(np.median([_iou(A["masks"][fi], B["masks"][fi]) for fi in common]))
            rec = {"a": a, "b": b, "d_m": round(d, 3), "iou": round(iou, 3), "n_common": len(common)}
            if iou >= cfg.ALIAS_IOU:
                aliases[b] = {"canonical": a, **{k: rec[k] for k in ("d_m", "iou", "n_common")}, "method": "geometry: centre distance + mask IoU"}; taken.add(b); rec["decision"] = "alias"
            elif iou < cfg.ALIAS_IOU_PART:
                parts.append({**rec, "relation": "co_located_part_or_support"}); rec["decision"] = "part"
            else:
                if use_gemini:
                    v = _gemini_same(cd, frames, tracks, A, B, common[len(common) // 2:], s)
                    same = str(v.get("same_object", "")).lower()[:3]; rec["gemini"] = {k: v.get(k) for k in ("same_object", "relation_if_no", "confidence", "reason")}
                    if same == "yes" and (v.get("confidence") or 0) >= 0.6:
                        aliases[b] = {"canonical": a, **{k: rec[k] for k in ("d_m", "iou", "n_common")}, "method": "gemini4_alias (grey-zone IoU)"}; taken.add(b); rec["decision"] = "alias"
                    else:
                        parts.append({**rec, "relation": v.get("relation_if_no") or "co_located_unsure"}); rec["decision"] = "part"
                else:
                    parts.append({**rec, "relation": "co_located_unsure"}); rec["decision"] = "part"
            log.append(rec)
    return aliases, parts, log
