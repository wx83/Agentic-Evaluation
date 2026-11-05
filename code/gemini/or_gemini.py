#!/usr/bin/env python3
"""通过 OpenRouter (https://openrouter.ai/api/v1) 调 Gemini。

key 来源(按顺序):环境变量 OPENROUTER_API_KEY → $OPENROUTER_API_KEY_FILE → holi/.secrets/openrouter_key。
key 只进内存,不写日志、不进 repo。

OpenRouter **只有 OpenAI 协议**(没有 Gemini 原生 generateContent 透传,也没有 Files API),所以本模块:
  1. chat(): 直接走 /chat/completions(文本 / JSON / 图片 / 内联视频)。
  2. client(): 返回一个 *假 google-genai Client*(_Shim),只实现 .models.generate_content(model, contents, config),
     把 types.Part.from_bytes / GenerateContentConfig 翻译成 OpenAI 请求,返回带 .text / .usage_metadata /
     .model_version / .candidates[0].finish_reason 的对象。现有按 nv_gemini 写的调用
     (NV.client().models.generate_content(...))不用改;nv_gemini.client() 在 GEMINI_BACKEND=openrouter 时自动转到这里。

2026-11-01 实测(key_id 见 --probe):
  - 模型名用 OpenRouter 写法 google/gemini-3.5-flash、google/gemini-4-argon、google/gemini-3.1-pro-preview ...;
    gcp/google/ 前缀与裸 gemini-x 名会自动改写。`--list-models` 列全部 google/gemini*。
  - thinking:3.x/4 模型 reasoning 关不掉(enabled=False → 400),但 reasoning.effort="minimal" 实测
    reasoning_tokens=0,等价于 thinking_budget=0。thinking_level low/medium/high → effort;thinking_budget>0 → reasoning.max_tokens。
  - 内联视频:content 里放 {"type":"video_url","video_url":{"url":"data:video/mp4;base64,..."}},音轨能听到
    (usage.prompt_tokens_details 有 video_tokens / audio_tokens)。
  - JSON:response_mime_type=application/json → response_format json_object;response_schema → json_schema。
  - seed / top_p / temperature 都接受。usage.cost 是美元,原样放进 usage_metadata.cost。

用法:
  python3 or_gemini.py --probe
  python3 or_gemini.py --list-models
  python3 or_gemini.py -m google/gemini-3.5-flash "explain X in 3 sentences"
  GEMINI_BACKEND=openrouter python3 <任何按 nv_gemini 写的脚本>
"""
import argparse, base64, hashlib, json, os, sys, time
from pathlib import Path

BASE_URL = "https://openrouter.ai/api/v1"
MODEL = os.environ.get("OR_GEMINI_MODEL", "google/gemini-3.5-flash")
KEY_FILES = [Path(os.environ.get("OPENROUTER_API_KEY_FILE", "")),
             Path(os.environ.get("P2_REPO", ".")) / ".secrets" / "openrouter_key", Path("/mnt/work_new/weihanxu/holi/.secrets/openrouter_key")]
_client = None
_HEADERS_EXTRA = {"HTTP-Referer": "https://github.com/wx83/Agentic-Evaluation", "X-OpenRouter-Title": "pyramid2", "X-Title": "pyramid2"}   # 可选,只用于 openrouter 排行榜归属(docs/quickstart)


def load_key():
    k = os.environ.get("OPENROUTER_API_KEY", "").strip()
    for f in KEY_FILES:
        if k: break
        if str(f) and f.is_file():
            k = f.read_text().strip()
    if not k:
        raise RuntimeError(f"OpenRouter key not found: export OPENROUTER_API_KEY=... or write it to {KEY_FILES[1]}")
    return k


def key_id():
    """key 指纹(sha256 前 8 位),给用量统计用;与 nv_gemini.key_id 同一算法。"""
    return hashlib.sha256(load_key().encode()).hexdigest()[:8]


def model_id(model):
    """gcp/google/gemini-x → google/gemini-x;gemini-x → google/gemini-x;已是 google/... 原样。"""
    m = model or MODEL
    if m.startswith("gcp/"):
        m = m[len("gcp/"):]
    if "/" not in m:
        m = "google/" + m
    return m


def _headers():
    return {"Authorization": f"Bearer {load_key()}", "Content-Type": "application/json", **_HEADERS_EXTRA}


def _post(body, timeout):
    import requests
    r = requests.post(f"{BASE_URL}/chat/completions", json=body, timeout=timeout, headers=_headers())
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    j = r.json()
    if j.get("error"):
        raise RuntimeError(f"openrouter error: {json.dumps(j['error'])[:300]}")
    return j


# ---------- 路线 B:OpenAI 协议(直接用) ----------
def chat(prompt, model=None, system=None, temperature=0.0, max_tokens=1024, json_mode=False,
         images=None, videos=None, reasoning=None, timeout=300, **extra):
    """images: list[bytes](JPEG);videos: list[bytes](mp4);reasoning: None / "minimal" / "low" / "medium" / "high" / int(max_tokens)。
    返回 (text, usage_dict)。"""
    content = [{"type": "text", "text": prompt}]
    for b in images or []:
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(b).decode()}})
    for b in videos or []:
        content.append({"type": "video_url", "video_url": {"url": "data:video/mp4;base64," + base64.b64encode(b).decode()}})
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": content if (images or videos) else prompt}]
    body = {"model": model_id(model), "messages": msgs, "temperature": temperature, "max_tokens": max_tokens, **extra}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if reasoning is not None:
        body["reasoning"] = {"max_tokens": reasoning} if isinstance(reasoning, int) else {"effort": reasoning}
    j = _post(body, timeout)
    return _text(j), _usage(j)


def _text(j):
    if not j.get("choices"):
        u = j.get("usage") or {}
        raise RuntimeError(f"empty choices (raise max_tokens; reasoning used {(u.get('completion_tokens_details') or {}).get('reasoning_tokens')} tokens)")
    return j["choices"][0]["message"].get("content")


def _usage(j):
    u = j.get("usage") or {}
    return {"tok_in": u.get("prompt_tokens"), "tok_out": u.get("completion_tokens"),
            "tok_think": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "cost_usd": u.get("cost"), "model_version": j.get("model")}


# ---------- 假 google-genai Client ----------
class _Usage:
    def __init__(self, j):
        u = j.get("usage") or {}
        cd = u.get("completion_tokens_details") or {}
        pd = u.get("prompt_tokens_details") or {}
        self.prompt_token_count = u.get("prompt_tokens")
        self.candidates_token_count = (u.get("completion_tokens") or 0) - (cd.get("reasoning_tokens") or 0) if u else None
        self.thoughts_token_count = cd.get("reasoning_tokens")
        self.total_token_count = u.get("total_tokens")
        self.cached_content_token_count = pd.get("cached_tokens")
        self.cost = u.get("cost")


class _Candidate:
    def __init__(self, c):
        fr = (c or {}).get("finish_reason") or (c or {}).get("native_finish_reason")
        self.finish_reason = {"length": "MAX_TOKENS", "stop": "STOP", "content_filter": "SAFETY"}.get(fr, str(fr).upper() if fr else None)


class _Response:
    def __init__(self, j):
        self.raw = j
        self.candidates = [_Candidate(c) for c in (j.get("choices") or [])] or [_Candidate({})]
        self.text = (j.get("choices") or [{}])[0].get("message", {}).get("content") if j.get("choices") else None
        self.usage_metadata = _Usage(j)
        self.model_version = j.get("model")


def _part_to_openai(p):
    """str / google.genai.types.Part / dict → OpenAI content item。"""
    if isinstance(p, str):
        return {"type": "text", "text": p}
    if isinstance(p, dict):
        return p
    t = getattr(p, "text", None)
    if t:
        return {"type": "text", "text": t}
    blob = getattr(p, "inline_data", None)
    if blob is not None and getattr(blob, "data", None) is not None:
        mime = blob.mime_type or "application/octet-stream"
        data = blob.data if isinstance(blob.data, (bytes, bytearray)) else base64.b64decode(blob.data)
        url = f"data:{mime};base64," + base64.b64encode(data).decode()
        if mime.startswith("image/"):
            return {"type": "image_url", "image_url": {"url": url}}
        if mime.startswith("video/"):
            return {"type": "video_url", "video_url": {"url": url}}
        if mime.startswith("audio/"):
            fmt = mime.split("/")[-1].replace("mpeg", "mp3")
            return {"type": "input_audio", "input_audio": {"data": base64.b64encode(data).decode(), "format": fmt}}
        return {"type": "file", "file": {"filename": "file", "file_data": url}}
    fd = getattr(p, "file_data", None)
    if fd is not None and getattr(fd, "file_uri", None):
        raise RuntimeError("OpenRouter 没有 Files API:请用 Part.from_bytes 内联,不要 files.upload / from_uri")
    raise TypeError(f"unsupported content part: {type(p)}")


def _reasoning_from_config(cfg):
    tc = getattr(cfg, "thinking_config", None)
    if tc is None:
        return None
    lvl = getattr(tc, "thinking_level", None)
    if lvl is not None:
        lvl = str(getattr(lvl, "value", lvl)).lower()
        return {"effort": {"minimal": "minimal", "low": "low", "medium": "medium", "high": "high"}.get(lvl, "low")}
    b = getattr(tc, "thinking_budget", None)
    if b is None:
        return None
    if b <= 0:                       # thinking_budget=0 → effort=minimal(实测 reasoning_tokens=0);-1(动态)→ 不指定
        return {"effort": "minimal"} if b == 0 else None
    return {"max_tokens": int(b)}


def _schema_json(s):
    if s is None:
        return None
    if isinstance(s, dict):
        return s
    if hasattr(s, "model_json_schema"):
        return s.model_json_schema()
    if hasattr(s, "model_dump"):
        return s.model_dump(exclude_none=True, by_alias=True)
    return None


class _Models:
    def __init__(self, timeout):
        self.timeout = timeout

    def generate_content(self, model, contents, config=None):
        cfg = config
        if cfg is None:
            cfg = type("C", (), {})()
        items = contents if isinstance(contents, (list, tuple)) else [contents]
        parts = []
        for it in items:
            if hasattr(it, "parts") and getattr(it, "role", None) is not None:   # types.Content
                parts.extend(it.parts)
            else:
                parts.append(it)
        content = [_part_to_openai(p) for p in parts]
        if len(content) == 1 and content[0]["type"] == "text":
            content = content[0]["text"]
        msgs = []
        si = getattr(cfg, "system_instruction", None)
        if si:
            msgs.append({"role": "system", "content": si if isinstance(si, str) else "\n".join(
                getattr(p, "text", str(p)) for p in (si.parts if hasattr(si, "parts") else [si]))})
        msgs.append({"role": "user", "content": content})
        body = {"model": model_id(model), "messages": msgs}
        for src, dst in (("temperature", "temperature"), ("top_p", "top_p"), ("max_output_tokens", "max_tokens"),
                         ("seed", "seed"), ("stop_sequences", "stop"), ("presence_penalty", "presence_penalty"),
                         ("frequency_penalty", "frequency_penalty")):
            v = getattr(cfg, src, None)
            if v is not None:
                body[dst] = v
        rs = _reasoning_from_config(cfg)
        if rs:
            body["reasoning"] = rs
        mime = getattr(cfg, "response_mime_type", None)
        schema = _schema_json(getattr(cfg, "response_schema", None) or getattr(cfg, "response_json_schema", None))
        if schema:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "out", "schema": schema}}
        elif mime == "application/json":
            body["response_format"] = {"type": "json_object"}
        return _Response(_post(body, self.timeout))


class _Shim:
    """只实现 pyramid 代码用到的 client.models.generate_content;其余属性一律报错。"""
    def __init__(self, timeout):
        self.models = _Models(timeout)

    @property
    def files(self):
        raise RuntimeError("OpenRouter 没有 Files API:请用 Part.from_bytes 内联")


def client(timeout_ms=300_000):
    global _client
    if _client is None:
        _client = _Shim(timeout=timeout_ms / 1000)
    return _client


def gen(prompt, model=None, system=None, temperature=0.0, max_tokens=1024, json_mode=False):
    """与 nv_gemini.gen 同签名:走 _Shim。返回 (text, usage_dict)。"""
    from google.genai import types
    kw = dict(temperature=temperature, max_output_tokens=max_tokens, system_instruction=system,
              thinking_config=types.ThinkingConfig(thinking_budget=0))
    if json_mode:
        kw["response_mime_type"] = "application/json"
    r = client().models.generate_content(model=model or MODEL, contents=prompt, config=types.GenerateContentConfig(**kw))
    u = r.usage_metadata
    return r.text, {"tok_in": u.prompt_token_count, "tok_out": u.candidates_token_count, "tok_think": u.thoughts_token_count,
                    "cost_usd": u.cost, "model_version": r.model_version}


def list_models():
    import requests
    r = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=30)
    r.raise_for_status()
    out = []
    for m in r.json().get("data", []):
        if "gemini" in m["id"]:
            p = m.get("pricing", {})
            out.append((m["id"], m.get("context_length"), float(p.get("prompt", 0)) * 1e6, float(p.get("completion", 0)) * 1e6,
                        (m.get("architecture") or {}).get("input_modalities")))
    return out


def credits():
    import requests
    r = requests.get(f"{BASE_URL}/auth/key", headers=_headers(), timeout=30)
    d = r.json().get("data", {})
    return {k: d.get(k) for k in ("limit", "limit_remaining", "usage", "usage_daily", "usage_monthly")}


def probe():
    print(f"key_id={key_id()}  model={MODEL}  base={BASE_URL}  credits={credits()}")
    ok = {}
    for name, fn in (("A genai-shim (client().models.generate_content)", gen),
                     ("B openai-compat (/chat/completions)", lambda p, **k: chat(p, reasoning="minimal", **k))):
        t0 = time.time()
        try:
            text, u = fn("Reply with the single word OK.", max_tokens=256)
            if not text:
                raise RuntimeError(f"empty response usage={u}")
            print(f"[{name}] OK in {time.time()-t0:.1f}s -> {text.strip()!r}  usage={u}")
            ok[name[0]] = True
        except Exception as e:
            print(f"[{name}] FAIL in {time.time()-t0:.1f}s -> {type(e).__name__}: {str(e)[:400]}")
            ok[name[0]] = False
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="*")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("-m", "--model", default=MODEL)
    ap.add_argument("--system")
    ap.add_argument("--reasoning", default="minimal", help="minimal/low/medium/high/none 或整数 token 数")
    ap.add_argument("--video", help="mp4 路径,内联发送")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--credits", action="store_true")
    a = ap.parse_args()
    if a.probe:
        ok = probe(); return 0 if any(ok.values()) else 1
    if a.list_models:
        for mid, ctx, pin, pout, mods in list_models():
            print(f"{mid:45s} ctx={ctx} in=${pin:.2f}/M out=${pout:.2f}/M {mods}")
        return 0
    if a.credits:
        print(json.dumps(credits(), indent=1)); return 0
    prompt = " ".join(a.prompt) or sys.stdin.read()
    if not prompt.strip():
        ap.error("no prompt")
    rs = None if a.reasoning == "none" else int(a.reasoning) if a.reasoning.isdigit() else a.reasoning
    text, u = chat(prompt, model=a.model, system=a.system, reasoning=rs,
                   videos=[open(a.video, "rb").read()] if a.video else None, max_tokens=2048)
    print(text); print(f"[{model_id(a.model)}] {u}", file=sys.stderr); return 0


if __name__ == "__main__":
    sys.exit(main())
