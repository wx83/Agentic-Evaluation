#!/usr/bin/env python3
"""Qwen3-Omni HTTP 服务(单线程、每请求新 session)。
  python qwen_server.py --port 8799 [--host 127.0.0.1] [--model /path/to/Qwen3-Omni-30B-A3B-Instruct]
GET  /                  -> {"ok": true}
POST /ask {"media_path": "/abs/path.mp4" | null, "media_b64": "<base64 mp4>" (可选,远程调用时用), "text": "...", "system": "..."(可选), "max_new_tokens": 96}
     -> {"raw": "...", "meta": {latency_sec, n_input_tokens, n_output_tokens, peak_gpu_mb}, "model": "..."}
media_b64 优先于 media_path:写到临时文件后推理,推理完删除。"""
import json, sys, os, argparse, traceback, base64, tempfile, hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qwen_agent import QwenAgent
AGENT = None; TMP = None


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        out = b'{"ok": true}'
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0")); req = json.loads(self.rfile.read(n) or b"{}")
        tmp = None
        try:
            media = req.get("media_path")
            if req.get("media_b64"):
                tmp = os.path.join(TMP, hashlib.sha1(req["media_b64"][:4096].encode()).hexdigest()[:16] + ".mp4")
                with open(tmp, "wb") as f: f.write(base64.b64decode(req["media_b64"]))
                media = tmp
            AGENT.max_new_tokens = int(req.get("max_new_tokens") or 96)
            sess = AGENT.start(None, media=media, memory=None)
            raw, meta = sess.ask(req["text"], system=req.get("system"))
            body = {"raw": raw, "meta": meta, "model": "Qwen3-Omni-30B-A3B-Instruct"}; code = 200
        except Exception as e:
            body = {"error": f"{type(e).__name__}: {str(e)[:300]}", "trace": traceback.format_exc()[-2000:]}; code = 500
        finally:
            if tmp and os.path.exists(tmp):
                try: os.remove(tmp)
                except OSError: pass
        out = json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8799); ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--model", default=None)
    a = ap.parse_args()
    TMP = tempfile.mkdtemp(prefix="qwen_media_")
    AGENT = QwenAgent(a.model)
    print(f"[qwen_server] listening on {a.host}:{a.port}", flush=True)
    HTTPServer((a.host, a.port), H).serve_forever()
