#!/usr/bin/env python3
"""通过 NVIDIA 网关 (https://inference-api.nvidia.com) 调 Gemini。

key 来源(按顺序):环境变量 NVIDIA_API_KEY → $NVIDIA_API_KEY_FILE → holi/.secrets/nvidia_key → weihanxu/gemini_api_key。
key 只进内存,不写日志、不进 repo。

两条路线(2026-10-10 实测,key_id 3948af16):
  A. gemini-native  —— google-genai SDK,只改 base_url + api_version="v1beta"。**推荐**,现有 wrapper
                       (pyramid/gemini_io、hdepic_annot/common/gemini、object_memory/stage_*_gemini)只改 client() 即可。
                       已验证可用:thinking_budget=0、response_mime_type=json、response_schema、seed/top_p、
                       Part.from_bytes 图片、Part.from_bytes 内联视频(实测 19 MB OK)、usage_metadata 含 thoughts_token_count。
                       不可用:client.files.upload → 404(网关没有 Files API)。视频请改用内联 bytes。
  B. openai-compat  —— /v1/chat/completions,纯 requests,无额外依赖。文本/JSON/图片可用;无 Files API。

注意:gemini-3.x 都是 thinking 模型,max_tokens 太小(如 16)会把配额烧在思考上,返回空 choices /
r.text=None。要么 thinking_budget=0,要么 max_tokens >= 256。

模型名必须带 gcp/google/ 前缀;`python3 nv_gemini.py --list-models` 可查。实测可用:
  gcp/google/gemini-3.1-pro-preview  gcp/google/gemini-3-flash-preview  gcp/google/gemini-2.5-pro / -flash

用法:
  python3 nv_gemini.py --probe                  # 两条路线各发一条最小请求,打印哪条通
  python3 nv_gemini.py "explain X in 3 sentences"   # 优先 A,不通自动降到 B

在别的脚本里:
  import sys; sys.path.insert(0, "/mnt/work_new/weihanxu/gemini")
  import nv_gemini as NV
  c = NV.client()                               # google-genai Client,指向 NVIDIA
  r = c.models.generate_content(model=NV.MODEL, contents="hi")
  # 或 OpenAI 协议:
  text = NV.chat("hi", system="You are terse.")
"""
import argparse, json, os, sys, time, hashlib
from pathlib import Path

BASE_URL = "https://inference-api.nvidia.com"
MODEL = os.environ.get("NV_GEMINI_MODEL", "gcp/google/gemini-3.1-pro-preview")
KEY_FILES = [Path(os.environ.get("NVIDIA_API_KEY_FILE", "")),
             Path("/mnt/work_new/weihanxu/holi/.secrets/nvidia_key"),
             Path("/mnt/work_new/weihanxu/gemini_api_key")]
_client = None


def load_key():
    k = os.environ.get("NVIDIA_API_KEY", "").strip()
    for f in KEY_FILES:
        if k: break
        if str(f) and f.is_file():
            k = f.read_text().strip()
    if not k:
        raise RuntimeError(f"NVIDIA key not found: export NVIDIA_API_KEY=... or write it to {KEY_FILES[1]}")
    return k


def key_kind():
    """只返回 key 的类型,不暴露内容。"""
    k = load_key()
    return "nvidia (nvapi-)" if k.startswith("nvapi-") else "google (AIza)" if k.startswith("AIza") else f"unknown prefix, len={len(k)}"


def key_id():
    """key 指纹(sha256 前 8 位),给用量统计用;与 pyramid/gemini_io.key_id 同一算法。"""
    return hashlib.sha256(load_key().encode()).hexdigest()[:8]


# ---------- 路线 A:google-genai SDK,base_url 指向 NVIDIA ----------
def client(timeout_ms=120_000):
    global _client
    if _client is None:
        from google import genai
        from google.genai import types
        _client = genai.Client(api_key=load_key(),
                               http_options=types.HttpOptions(base_url=BASE_URL,
                                                              api_version="v1beta",
                                                              timeout=timeout_ms))
    return _client


def gen(prompt, model=None, system=None, temperature=0.0, max_tokens=1024, json_mode=False):
    """路线 A。返回 (text, usage_dict)。"""
    from google.genai import types
    kw = dict(temperature=temperature, max_output_tokens=max_tokens, system_instruction=system)
    if json_mode:
        kw["response_mime_type"] = "application/json"
    r = client().models.generate_content(model=model or MODEL, contents=prompt,
                                         config=types.GenerateContentConfig(**kw))
    u = getattr(r, "usage_metadata", None)
    g = lambda k: getattr(u, k, None) if u is not None else None
    return r.text, {"tok_in": g("prompt_token_count"), "tok_out": g("candidates_token_count"),
                    "tok_think": g("thoughts_token_count"), "model_version": getattr(r, "model_version", None)}


# ---------- 路线 B:OpenAI 协议 ----------
def chat(prompt, model=None, system=None, temperature=0.0, max_tokens=1024, json_mode=False,
         images=None, timeout=120):
    """路线 B。images: 可选 list[bytes](JPEG),走 image_url base64。返回 (text, usage_dict)。"""
    import base64, requests
    content = [{"type": "text", "text": prompt}]
    for b in images or []:
        content.append({"type": "image_url", "image_url": {
            "url": "data:image/jpeg;base64," + base64.b64encode(b).decode()}})
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": content if images else prompt}]
    body = {"model": model or MODEL, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = requests.post(f"{BASE_URL}/v1/chat/completions", json=body, timeout=timeout,
                      headers={"Authorization": f"Bearer {load_key()}", "Content-Type": "application/json"})
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    j = r.json()
    u = j.get("usage") or {}
    if not j.get("choices"):
        raise RuntimeError(f"empty choices (raise max_tokens; thinking used {(u.get('completion_tokens_details') or {}).get('reasoning_tokens')} tokens)")
    return j["choices"][0]["message"]["content"], {"tok_in": u.get("prompt_tokens"), "tok_out": u.get("completion_tokens"),
                                                   "model_version": j.get("model")}


# ---------- 自检 ----------
def probe():
    print(f"key_id={key_id()}  kind={key_kind()}  model={MODEL}  base={BASE_URL}")
    ok = {}
    for name, fn in (("A gemini-native (google-genai + base_url)", gen),
                     ("B openai-compat (/v1/chat/completions)", chat)):
        t0 = time.time()
        try:
            text, u = fn("Reply with the single word OK.", max_tokens=256)
            if not text:
                raise RuntimeError(f"empty response (thinking ate the budget?) usage={u}")
            print(f"[{name}] OK in {time.time()-t0:.1f}s -> {text.strip()!r}  usage={u}")
            ok[name[0]] = True
        except Exception as e:
            print(f"[{name}] FAIL in {time.time()-t0:.1f}s -> {type(e).__name__}: {str(e)[:400]}")
            ok[name[0]] = False
    print()
    if ok.get("A"):
        print("=> 路线 A 通:现有 wrapper 只需 genai.Client(api_key=..., http_options=HttpOptions(base_url=..., api_version='v1beta')),模型名加 gcp/google/ 前缀。")
    elif ok.get("B"):
        print("=> 只有路线 B 通:文本/JSON 任务用 nv_gemini.chat();视频 / thinking_budget / seed 等仍需 Google 原生 key。")
    else:
        print("=> 两条都不通:先核对 key 是否有效、模型名是否在该账号可用列表里(GET /v1/models 需要带 Bearer)。")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="*")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("-m", "--model", default=MODEL)
    ap.add_argument("--system")
    ap.add_argument("--openai", action="store_true", help="强制走路线 B")
    ap.add_argument("--list-models", action="store_true")
    a = ap.parse_args()
    if a.probe:
        ok = probe(); return 0 if any(ok.values()) else 1
    if a.list_models:
        import requests
        r = requests.get(f"{BASE_URL}/v1/models", headers={"Authorization": f"Bearer {load_key()}"}, timeout=30)
        print(r.status_code); print(r.text[:4000]); return 0
    prompt = " ".join(a.prompt) or sys.stdin.read()
    if not prompt.strip():
        ap.error("no prompt")
    if not a.openai:
        try:
            text, u = gen(prompt, model=a.model, system=a.system); print(text)
            print(f"[A {a.model}] {u}", file=sys.stderr); return 0
        except Exception as e:
            print(f"[A failed: {type(e).__name__}: {str(e)[:120]}] -> fallback B", file=sys.stderr)
    text, u = chat(prompt, model=a.model, system=a.system); print(text)
    print(f"[B {a.model}] {u}", file=sys.stderr); return 0


if __name__ == "__main__":
    sys.exit(main())
