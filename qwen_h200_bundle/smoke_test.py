#!/usr/bin/env python3
"""python smoke_test.py --url http://127.0.0.1:8799  先发纯文字,再发 sample/clip_20s.mp4(两种方式:media_path 本地路径;media_b64 远程上传)。"""
import json, sys, time, base64, argparse, urllib.request, os
ap = argparse.ArgumentParser(); ap.add_argument("--url", default="http://127.0.0.1:8799"); a = ap.parse_args()
def post(body):
    t0 = time.time(); req = urllib.request.Request(a.url + "/ask", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=1800).read()); return r, time.time() - t0
print("GET /:", urllib.request.urlopen(a.url + "/", timeout=10).read().decode())
r, dt = post({"media_path": None, "text": "Reply with the single word OK.", "max_new_tokens": 8}); print(f"text-only {dt:.1f}s ->", r.get("raw"), r.get("meta"), r.get("error"))
clip = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample", "clip_20s.mp4")
q = "What is the camera wearer doing in this clip? Answer in one short sentence."
r, dt = post({"media_path": clip, "text": q, "max_new_tokens": 64}); print(f"video via media_path {dt:.1f}s ->", r.get("raw"), r.get("meta"), r.get("error"))
r, dt = post({"media_b64": base64.b64encode(open(clip, "rb").read()).decode(), "text": q, "max_new_tokens": 64}); print(f"video via media_b64 {dt:.1f}s ->", r.get("raw"), r.get("meta"), r.get("error"))
