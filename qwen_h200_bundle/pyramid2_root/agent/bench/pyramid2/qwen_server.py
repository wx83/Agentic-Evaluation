#!/usr/bin/env python3
"""Qwen3-Omni 本地 HTTP 服务(timechatcap env 跑;pyramid2 的 solver 用 solver_backend=qwen_http 访问)。
  /home/weihanxu/miniconda3/envs/timechatcap/bin/python qwen_server.py --port 8765
POST /ask  {"media_path": "...mp4" | null, "text": "...", "max_new_tokens": 96}  -> {"raw": "...", "meta": {latency_sec, n_input_tokens, peak_gpu_mb}}
单线程、每请求新 session(fresh context per item)。"""
import json, sys, argparse, traceback, time
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, "/mnt/work_new/weihanxu/agent/bench")
from agents.qwen_agent import QwenAgent
AGENT = None


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b'{"ok": true}')
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0")); req = json.loads(self.rfile.read(n) or b"{}")
        try:
            AGENT.max_new_tokens = int(req.get("max_new_tokens") or 96)
            sess = AGENT.start(None, media=req.get("media_path"), memory=None)
            raw, meta = sess.ask(req["text"])
            body = {"raw": raw, "meta": meta, "model": "Qwen3-Omni-30B-A3B-Instruct"}
            code = 200
        except Exception as e:
            body = {"error": f"{type(e).__name__}: {str(e)[:300]}", "trace": traceback.format_exc()[-2000:]}; code = 500
        out = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8765); a = ap.parse_args()
    AGENT = QwenAgent()
    print(f"[qwen_server] listening on {a.port}", flush=True)
    HTTPServer(("127.0.0.1", a.port), H).serve_forever()
