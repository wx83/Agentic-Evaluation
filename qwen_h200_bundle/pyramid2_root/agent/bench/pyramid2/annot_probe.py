#!/usr/bin/env python3
"""标注探针(10-14 晚,用户问「Gemini 4 能完成 1014.md §14 里多少缺失标注」):
对 N 条 EgoPlan 样本的任务窗口 clip(≤120 s,288 px,带音轨),让模型一次性输出 §14 里缺的标注(声音事件 / 语音 / 人物 / 物体与属性 /
动作+手+工具+接触类型 / 状态变化 / 空间关系 / 注视 / 失败 / 结果),再用已有 GT(Ego4D narration + EgoPlan 步骤)核对能核对的部分。
  GEMINI_BACKEND=nv python3 annot_probe.py --model gcp/google/gemini-4-argon --n 10
输出 runs/annot_probe_1014/<model_tag>/{<sample>.json, summary.json, summary.md}"""
import json, re, time, argparse, collections, sys
from pathlib import Path
import p2config as P
from store import Store
import media as M
sys.path.insert(0, str(Path(__file__).parent / "adapters"))
from adapters.contact_rich import CONTACT

OUT = P.RUNS / "annot_probe_1014"
NARR = Path("/mnt/data_new/ego4d/v2/annotations/narration.json")
PICK = ["baking", "blacksmith", "carpenter", "cleaning", "cooking", "decorating", "drawing", "mechanic", "repairing", "gardening"]
STOP = {"the", "a", "an", "his", "her", "their", "its", "of", "with", "on", "in", "into", "from", "to", "at", "and", "c", "#c", "#unsure", "up", "down", "out", "off"}

SYSTEM = """You are a careful video annotator for an egocentric (first-person) clip with audio. Annotate ONLY what is directly
observable or audible. Clip time starts at 0 s. Give every item a timestamp (seconds, clip time), a confidence 0-1, and
"evidence": "video" | "audio" | "both". When something cannot be determined from the clip, do not guess: omit it, or use
"unknown". Return exactly one JSON object with these keys (empty lists allowed):

sound_events: [{t0, t1, label (natural words, e.g. "water running", "metal clink"), source (object/action producing it), evidence, confidence}]
speech: [{t0, t1, speaker: "wearer"|"other"|"unknown", transcript (verbatim words you can hear, else ""), language, confidence}]
people: [{t0, t1, n_people_visible, talking_to_wearer: bool, looking_at_wearer: bool, confidence}]
objects: [{name, attributes: [visible color / material / size words], first_seen_t, handled_by_wearer: bool, confidence}]
actions: [{t0, t1, verb, object, tool: str|null, hand: "left"|"right"|"both"|"unknown", contact_type: "squeeze"|"press"|"twist"|"knead"|"scrape"|"pour"|"stir"|"wipe"|"dip"|"other"|"none", confidence}]
state_changes: [{t, object, from_state, to_state, cause_action, confidence}]
spatial: [{t, object, relation: "left_of"|"right_of"|"in_front_of"|"behind"|"on"|"in"|"near", reference: "wearer"|<object name>, confidence}]
attention: [{t, looks_at, then_action: str|null, confidence}]   # where the wearer's view/gaze settles right before acting
failures: [{t, what_failed, recovery: str|null, confidence}]
outcomes: [{t, action, visible_outcome, confidence}]
List actions densely (every distinct manipulation, typically one every 1-5 s). Keep names short (noun phrases)."""


def pick_samples(n):
    S = json.loads((P.DATA / "egoplan_samples.json").read_text())["samples"]
    by = {s["scenario"]: s for s in S}
    out = [by[k] for k in PICK if k in by][:n]
    if len(out) < n:
        out += [s for s in S if s not in out][: n - len(out)]
    return out


def narr_gt(uid, t0, t1):
    d = json.load(open(NARR)).get(uid, {})
    rows = []
    for pk, p in d.items():
        if not isinstance(p, dict): continue
        for x in p.get("narrations", []):
            if t0 - 1 <= x["timestamp_sec"] <= t1 + 1:
                t = x["narration_text"]; low = t.lower()
                m = re.search(r"#c c (\w+)", low); verb = m.group(1) if m else None
                hand = "left" if re.search(r"\bleft hand", low) else "right" if re.search(r"\bright hand", low) else "both" if re.search(r"\bboth hands", low) else None
                rows.append({"pass": pk, "t": round(x["timestamp_sec"] - t0, 2), "text": t, "verb": verb, "hand": hand, "unsure": "#unsure" in low,
                             "nouns": [w for w in re.findall(r"[a-z]+", low) if w not in STOP and len(w) > 2 and w != verb]})
    rows.sort(key=lambda r: r["t"])
    return rows


def stem(w):
    for suf in ("ing", "ies", "es", "ed", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf): return w[: -len(suf)]
    return w


def ask_video(path, model, max_tokens=16384):
    import nv_gemini as NV, logging
    logging.getLogger("google_genai").setLevel(logging.ERROR)
    from google.genai import types
    part = types.Part.from_bytes(data=open(path, "rb").read(), mime_type="video/mp4")
    kw = dict(temperature=0.0, max_output_tokens=max_tokens, system_instruction=SYSTEM, response_mime_type="application/json")
    t0 = time.time(); err = None; text = None; u = {}
    for attempt in range(4):
        try:
            r = NV.client(timeout_ms=600_000).models.generate_content(model=model, contents=[part, "\nAnnotate this clip."], config=types.GenerateContentConfig(**kw))
            um = getattr(r, "usage_metadata", None); g = lambda k: getattr(um, k, None) if um is not None else None
            u = {"tok_in": g("prompt_token_count"), "tok_out": g("candidates_token_count"), "tok_think": g("thoughts_token_count"), "model_version": getattr(r, "model_version", None),
                 "finish": str(getattr(r, "candidates", None) and r.candidates[0].finish_reason)}
            text = r.text; err = None
            if text: break
            err = f"empty ({u.get('finish')})"
        except Exception as e_:
            err = f"{type(e_).__name__}: {str(e_)[:300]}"
            if "429" in err or "RateLimit" in err: time.sleep(75); continue
            if "404" in err or "NOT_FOUND" in err or "not supported" in err.lower(): break
            time.sleep(5)
    return text, u, err, round(time.time() - t0, 1)


def jparse(text):
    t = (text or "").strip()
    if t.startswith("```"): t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    try: return json.loads(t)
    except Exception:
        i, j = t.find("{"), t.rfind("}")
        return json.loads(t[i:j + 1])


def evaluate(ann, gt, steps):
    """能核对的部分:动作召回 / 精度(±3 s + 动词或名词重合)、手、物体名、接触动作、计数;其余只计数。"""
    acts = ann.get("actions") or []
    def toks(s): return {stem(w) for w in re.findall(r"[a-z]+", (s or "").lower()) if w not in STOP and len(w) > 2}
    matched_gt = 0; hand_n = hand_ok = 0; contact_n = contact_ok = 0
    for g in gt:
        gtoks = toks(g["text"]); cand = [a for a in acts if abs(float(a.get("t0", a.get("t", -99)) or 0) - g["t"]) <= 3.0 or abs(float(a.get("t1", -99) or 0) - g["t"]) <= 3.0]
        hit = next((a for a in cand if (toks(a.get("verb")) | toks(a.get("object")) | toks(a.get("tool"))) & gtoks), None)
        if hit:
            matched_gt += 1
            if g["hand"]:
                hand_n += 1; hand_ok += (hit.get("hand") == g["hand"])
            if g["verb"] and stem(g["verb"]) in {stem(k) for k in CONTACT}:
                contact_n += 1; contact_ok += (hit.get("contact_type") not in (None, "none"))
    matched_pred = 0
    for a in acts:
        ta = float(a.get("t0", a.get("t", -99)) or 0); atoks = toks(a.get("verb")) | toks(a.get("object")) | toks(a.get("tool"))
        if any(abs(ta - g["t"]) <= 3.0 and atoks & toks(g["text"]) for g in gt): matched_pred += 1
    gt_nouns = {stem(w) for g in gt for w in g["nouns"]}; pred_objs = {stem(w) for o in (ann.get("objects") or []) for w in re.findall(r"[a-z]+", (o.get("name") or "").lower()) if w not in STOP}
    step_nouns = {stem(w) for s in steps for w in re.findall(r"[a-z]+", s["text"].lower()) if w not in STOP and len(w) > 2}
    return {"n_gt_narrations": len(gt), "n_pred_actions": len(acts), "action_recall": round(matched_gt / len(gt), 2) if gt else None,
            "action_precision": round(matched_pred / len(acts), 2) if acts else None,
            "hand_gt_n": hand_n, "hand_acc": round(hand_ok / hand_n, 2) if hand_n else None,
            "contact_gt_n": contact_n, "contact_recall": round(contact_ok / contact_n, 2) if contact_n else None,
            "object_recall_vs_narration_nouns": round(len(gt_nouns & pred_objs) / len(gt_nouns), 2) if gt_nouns else None,
            "object_recall_vs_plan_nouns": round(len(step_nouns & pred_objs) / len(step_nouns), 2) if step_nouns else None,
            "n_pred_objects": len(ann.get("objects") or []), "n_pred_with_attributes": sum(1 for o in (ann.get("objects") or []) if o.get("attributes")),
            "counts_unverifiable": {k: len(ann.get(k) or []) for k in ("sound_events", "speech", "people", "state_changes", "spatial", "attention", "failures", "outcomes")},
            "speech_with_transcript": sum(1 for s in (ann.get("speech") or []) if (s.get("transcript") or "").strip())}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", default="gcp/google/gemini-4-argon"); ap.add_argument("--n", type=int, default=10); ap.add_argument("--max-sec", type=float, default=120.0)
    a = ap.parse_args()
    tag = a.model.split("/")[-1]; od = OUT / tag; od.mkdir(parents=True, exist_ok=True)
    store = Store(); summ = []
    for s in pick_samples(a.n):
        t0, t1 = s["t0"], s["t1"]
        if t1 - t0 > a.max_sec: t0 = t1 - a.max_sec
        mat = M.materialize({"media_id": f"egoplan/{s['video_id']}", "windows": [[round(t0, 3), round(t1, 3)]]}, store)
        size = Path(mat["path"]).stat().st_size / 1e6
        text, u, err, lat = ask_video(mat["path"], a.model)
        rec = {"sample_id": s["sample_id"], "scenario": s["scenario"], "goal": s["goal"], "window": [t0, t1], "clip": str(mat["path"]), "clip_mb": round(size, 1),
               "model": a.model, "usage": u, "latency_sec": lat, "error": err, "raw": text}
        gt = narr_gt(s["video_id"], t0, t1); steps = [st for st in s["steps"] if st["t0"] >= t0 - 1]
        rec["gt_narrations"] = gt
        if text and not err:
            try:
                ann = jparse(text); rec["annotation"] = ann; rec["eval"] = evaluate(ann, gt, steps)
            except Exception as e_:
                rec["error"] = f"json: {str(e_)[:120]}"
        (od / f"{s['sample_id']}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        ev = rec.get("eval") or {}
        print(f"{s['scenario']:12s} {t1 - t0:5.0f}s {size:4.1f}MB {lat:6.1f}s err={str(err)[:60]!r} | actions {ev.get('n_pred_actions')} recall {ev.get('action_recall')} prec {ev.get('action_precision')} | hand {ev.get('hand_acc')}({ev.get('hand_gt_n')}) contact {ev.get('contact_recall')}({ev.get('contact_gt_n')}) | obj recall narr {ev.get('object_recall_vs_narration_nouns')} plan {ev.get('object_recall_vs_plan_nouns')} | unverifiable {ev.get('counts_unverifiable')}", flush=True)
        summ.append({k: rec[k] for k in ("sample_id", "scenario", "window", "clip_mb", "latency_sec", "error", "usage")} | {"eval": ev})
    (od / "summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print("DONE", tag, flush=True)


if __name__ == "__main__":
    main()
